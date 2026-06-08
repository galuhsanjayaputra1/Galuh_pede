import os
import logging
from typing import Optional
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables (e.g. GEMINI_API_KEY)
load_dotenv()

def generate_image_caption(image_path: str) -> Optional[str]:
    """
    Sends an image to Google Gemini 1.5 Flash to generate a detailed caption
    suitable for RAG search context.
    
    Returns the caption string if successful, otherwise None.
    """
    if not os.path.exists(image_path):
        logger.warning(f"Image not found for captioning: {image_path}")
        return None

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logger.warning("GEMINI_API_KEY not found in environment. Skipping image captioning.")
        return None

    try:
        from google import genai
        import PIL.Image
        
        client = genai.Client(api_key=api_key)
        # Using Gemini 2.5 Flash based on user's dashboard availability
        model_name = 'gemini-2.5-flash'
        
        img = PIL.Image.open(image_path)
        
        prompt = (
            "You are an expert scientific data extractor for a RAG system. "
            "Please describe this image in detail. "
            "If it is a graph or chart, explain the axes, legends, trends, and any significant data points. "
            "If it is a diagram, explain the workflow or architecture it depicts. "
            "If it contains a table, summarize the key findings or reproduce the data if small. "
            "If it is a mathematical formula, write it out or describe its purpose. "
            "Keep the description factual, concise, and highly detailed to maximize searchability."
        )
        
        import time
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=[prompt, img]
                )
                if response and response.text:
                    # Sleep to respect 5 RPM free tier limit (1 request every 12 seconds)
                    time.sleep(12) 
                    return response.text.strip()
                break
            except Exception as e:
                error_msg = str(e).lower()
                if "429" in error_msg or "quota" in error_msg:
                    # Usually the API tells us to wait ~30-45 seconds
                    sleep_time = 35
                    logger.warning(f"Rate limit hit (429). Sleeping for {sleep_time} seconds before retry (Attempt {attempt+1}/{max_retries})...")
                    time.sleep(sleep_time)
                else:
                    logger.error(f"Failed to generate image caption for {image_path}: {e}")
                    return None
                    
        return None
        
    except ImportError:
        logger.error("google-genai or pillow is not installed. Skipping image captioning.")
        return None
