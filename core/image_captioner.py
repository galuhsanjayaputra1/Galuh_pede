import os
import logging
import threading
from typing import Optional
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables (optional overrides; no API key needed anymore)
load_dotenv()

# ---------------------------------------------------------------------------
# Image captioning for Multimodal RAG — LOCAL model (Qwen2.5-VL).
#
# Tidak ada lagi API key / billing Gemini. Model dijalankan lokal (GPU Colab /
# PC ber-GPU), persis seperti BGE-M3. Tanpa GPU tetap jalan di CPU tapi lambat.
#
# Override via environment (opsional):
#   CAPTION_MODEL          : nama model HF (default Qwen/Qwen2.5-VL-3B-Instruct)
#   DISABLE_IMAGE_CAPTION  : "1"/"true" untuk melewati captioning sepenuhnya
#   CAPTION_MAX_NEW_TOKENS : panjang maksimum caption (default 512)
# ---------------------------------------------------------------------------

DEFAULT_MODEL = os.environ.get("CAPTION_MODEL", "Qwen/Qwen2.5-VL-3B-Instruct")
MAX_NEW_TOKENS = int(os.environ.get("CAPTION_MAX_NEW_TOKENS", "512"))
# Gambar besar di-downscale agar hemat memori (sisi terpanjang, dalam piksel).
MAX_IMAGE_SIDE = 1536

PROMPT = (
    "You are an expert scientific data extractor for a RAG system. "
    "Please describe this image in detail. "
    "If it is a graph or chart, explain the axes, legends, trends, and any significant data points. "
    "If it is a diagram, explain the workflow or architecture it depicts. "
    "If it contains a table, summarize the key findings or reproduce the data if small. "
    "If it is a mathematical formula, write it out or describe its purpose. "
    "Keep the description factual, concise, and highly detailed to maximize searchability."
)

# Singleton (model dimuat sekali, dipakai ulang untuk semua gambar).
_model = None
_processor = None
_load_lock = threading.Lock()
_load_failed = False


def _disabled() -> bool:
    return os.environ.get("DISABLE_IMAGE_CAPTION", "").strip().lower() in {"1", "true", "yes"}


def _load_model():
    """Muat Qwen2.5-VL sekali (lazy). Return (model, processor) atau (None, None)."""
    global _model, _processor, _load_failed
    if _model is not None and _processor is not None:
        return _model, _processor
    if _load_failed:
        return None, None

    with _load_lock:
        if _model is not None and _processor is not None:
            return _model, _processor
        if _load_failed:
            return None, None
        try:
            import torch
            from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration

            if torch.cuda.is_available():
                dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
                device_map = "auto"
                logger.info(f"Loading caption model '{DEFAULT_MODEL}' on GPU ({dtype}).")
            else:
                dtype = torch.float32
                device_map = None
                logger.warning(
                    f"Loading caption model '{DEFAULT_MODEL}' on CPU — ini lambat. "
                    "Gunakan GPU/Colab, atau set DISABLE_IMAGE_CAPTION=1 untuk melewati."
                )

            _processor = AutoProcessor.from_pretrained(DEFAULT_MODEL)
            _model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
                DEFAULT_MODEL,
                torch_dtype=dtype,
                device_map=device_map,
            )
            if device_map is None:
                _model = _model.to("cpu")
            _model.eval()
            return _model, _processor
        except Exception as e:
            _load_failed = True
            logger.error(
                f"Gagal memuat caption model '{DEFAULT_MODEL}': {e}. "
                "Pastikan 'transformers>=4.49' dan 'accelerate' terpasang. "
                "Captioning dilewati (teks dokumen tetap diproses normal)."
            )
            return None, None


def generate_image_caption(image_path: str) -> Optional[str]:
    """
    Hasilkan caption ilmiah detail dari sebuah gambar menggunakan Qwen2.5-VL
    (model lokal, tanpa API key). Cocok sebagai konteks pencarian RAG.

    Returns caption string bila sukses, atau None (gambar dibiarkan apa adanya).
    """
    if _disabled():
        return None

    if not os.path.exists(image_path):
        logger.warning(f"Image not found for captioning: {image_path}")
        return None

    model, processor = _load_model()
    if model is None or processor is None:
        return None

    try:
        import torch
        import PIL.Image

        img = PIL.Image.open(image_path).convert("RGB")
        # Downscale gambar besar agar hemat VRAM/RAM tanpa kehilangan keterbacaan.
        if max(img.size) > MAX_IMAGE_SIDE:
            ratio = MAX_IMAGE_SIDE / max(img.size)
            new_size = (int(img.width * ratio), int(img.height * ratio))
            img = img.resize(new_size, PIL.Image.LANCZOS)

        messages = [{
            "role": "user",
            "content": [
                {"type": "image"},
                {"type": "text", "text": PROMPT},
            ],
        }]
        text = processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        inputs = processor(text=[text], images=[img], padding=True, return_tensors="pt")
        inputs = inputs.to(model.device)

        with torch.inference_mode():
            generated = model.generate(**inputs, max_new_tokens=MAX_NEW_TOKENS)

        # Buang token prompt, sisakan jawaban model saja.
        trimmed = [out[len(inp):] for inp, out in zip(inputs.input_ids, generated)]
        caption = processor.batch_decode(
            trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
        )[0].strip()

        return caption or None

    except Exception as e:
        logger.error(f"Failed to generate image caption for {image_path}: {e}")
        return None
