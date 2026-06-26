#!/usr/bin/env python3
"""
Script untuk menjalankan ingest dengan 5 konfigurasi chunk berbeda.

Menggunakan Word2Vec embedding dan menguji kombinasi:
1. chunk_size=512, chunk_overlap=100
2. chunk_size=768, chunk_overlap=150
3. chunk_size=1024, chunk_overlap=200
4. chunk_size=256, chunk_overlap=50
5. chunk_size=1500, chunk_overlap=300

Hasil akan disimpan ke Qdrant dengan collection name berbeda per config.
"""

import os
import sys
import time
import logging
from pathlib import Path
from core.pdf_converter import convert_pdf_to_markdown, get_pdf_native_metadata
from core.metadata_extractor import extract_metadata, ArticleMetadata
from core.chunker import chunk_markdown
from core.vector_store import VectorStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# === Konfigurasi 5 Case ===
CHUNK_CONFIGS = [
    {"chunk_size": 512, "chunk_overlap": 100, "name": "Case1_512_100"},
    {"chunk_size": 768, "chunk_overlap": 150, "name": "Case2_768_150"},
    {"chunk_size": 1024, "chunk_overlap": 200, "name": "Case3_1024_200"},
    {"chunk_size": 256, "chunk_overlap": 50, "name": "Case4_256_50"},
    {"chunk_size": 1500, "chunk_overlap": 300, "name": "Case5_1500_300"},
]

DATA_DIR = Path("./data")
MARKDOWN_DIR = DATA_DIR / "markdown"
IMAGE_DIR = DATA_DIR / "images"
META_DIR = DATA_DIR / "metadata"


def setup_directories():
    """Create necessary directories."""
    for d in [DATA_DIR, MARKDOWN_DIR, IMAGE_DIR, META_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def process_pdf_with_config(pdf_path: str, config: dict) -> None:
    """Process PDF dengan konfigurasi chunk tertentu."""
    chunk_size = config["chunk_size"]
    chunk_overlap = config["chunk_overlap"]
    case_name = config["name"]
    
    logger.info(f"\n{'='*70}")
    logger.info(f"[{case_name}] Processing dengan chunk_size={chunk_size}, overlap={chunk_overlap}")
    logger.info(f"{'='*70}")
    
    start_time = time.time()
    
    try:
        # === Step 1: PDF -> Markdown ===
        logger.info("[1/4] Converting PDF to Markdown...")
        markdown_text = convert_pdf_to_markdown(
            pdf_path,
            image_dir=str(IMAGE_DIR),
            write_images=True,
        )
        logger.info(f"  -> Markdown: {len(markdown_text):,} chars")
        
        # === Step 2: Extract Metadata ===
        logger.info("[2/4] Extracting metadata...")
        pdf_native_meta = get_pdf_native_metadata(pdf_path)
        article_meta = extract_metadata(pdf_path, markdown_text, pdf_native_meta)
        logger.info(f"  -> Title: {article_meta.title}")
        logger.info(f"  -> DOI: {article_meta.doi or 'Not found'}")
        
        # === Step 3: Chunking ===
        logger.info("[3/4] Chunking markdown...")
        chunks = chunk_markdown(
            markdown_text, article_meta,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        logger.info(f"  -> {len(chunks)} chunks created")
        
        # === Step 4: Store in Qdrant ===
        logger.info("[4/4] Embedding & storing in Qdrant...")
        collection_name = f"scientific_articles_{case_name}".lower()
        vector_store = VectorStore(
            qdrant_path="./qdrant_db",
            embedding_model="word2vec-google-news-300",
            collection_name=collection_name,
        )
        vector_store.ensure_collection()
        stored = vector_store.add_chunks(chunks)
        
        elapsed = time.time() - start_time
        logger.info(f"  -> {stored} chunks stored in Qdrant")
        logger.info(f"  -> Collection: {collection_name}")
        logger.info(f"  -> Total time: {elapsed:.1f}s")
        logger.info(f"  -> Result: SUCCESS ✅")
        
        return True
        
    except Exception as e:
        logger.error(f"  -> Error: {e}")
        logger.error(f"  -> Result: FAILED ❌")
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python run_5_cases.py <pdf_path_or_directory>")
        print()
        print("Examples:")
        print('  python run_5_cases.py "./core/data/A_Comprehensive_Empirical_Evaluation_of_Existing_W.pdf"')
        print('  python run_5_cases.py "./core/data"')
        sys.exit(1)
    
    source_path = sys.argv[1]
    setup_directories()
    
    # Temukan file PDF
    pdf_files = []
    source = Path(source_path)
    
    if source.is_file() and source.suffix.lower() == ".pdf":
        pdf_files = [str(source)]
    elif source.is_dir():
        pdf_files = [str(f) for f in source.rglob("*.pdf")]
    
    if not pdf_files:
        logger.error(f"No PDF files found in {source_path}")
        sys.exit(1)
    
    logger.info(f"Found {len(pdf_files)} PDF file(s)")
    
    # Jalankan setiap config
    results = {}
    for config in CHUNK_CONFIGS:
        for pdf_file in pdf_files:
            success = process_pdf_with_config(pdf_file, config)
            results[config["name"]] = "SUCCESS" if success else "FAILED"
    
    # Summary
    logger.info(f"\n{'='*70}")
    logger.info("SUMMARY - 5 CASE RESULTS")
    logger.info(f"{'='*70}")
    for case_name, status in results.items():
        logger.info(f"  {case_name}: {status}")
    logger.info(f"{'='*70}\n")


if __name__ == "__main__":
    main()
