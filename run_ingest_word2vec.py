#!/usr/bin/env python3
"""
Script untuk menjalankan ingest PDF dengan Word2Vec embedding.

Cara pakai:
    python run_ingest_word2vec.py <path_pdf>
    
Contoh:
    python run_ingest_word2vec.py "./core/data/A_Comprehensive_Empirical_Evaluation_of_Existing_W.pdf"
    python run_ingest_word2vec.py "./data/pdfs/"
"""

import sys
import subprocess

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_ingest_word2vec.py <path_pdf_or_directory>")
        print()
        print("Examples:")
        print('  python run_ingest_word2vec.py "./core/data/A_Comprehensive_Empirical_Evaluation_of_Existing_W.pdf"')
        print('  python run_ingest_word2vec.py "./data/pdfs/"')
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    print("[INFO] Menjalankan ingest dengan Word2Vec embedding...")
    print(f"[INFO] PDF/Directory: {pdf_path}")
    print()
    
    # Jalankan ingest.py dengan path PDF
    result = subprocess.run(
        [sys.executable, "ingest.py", pdf_path],
        cwd=".",
    )
    
    sys.exit(result.returncode)
