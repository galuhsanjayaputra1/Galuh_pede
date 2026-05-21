import argparse
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
import json

# === Setup Argparse ===
parser = argparse.ArgumentParser(description="Ekstrak chunk dari Qdrant ke JSON")
parser.add_argument("--doi", type=str, default=None, help="Filter berdasarkan DOI spesifik")
args = parser.parse_args()

# Hubungkan ke database lokal
client = QdrantClient(path="./qdrant_db")
collection_name = "scientific_articles"

print(f"Mengambil data dari koleksi '{collection_name}'...")
if args.doi:
    print(f"Filter aktif: Hanya mengambil DOI '{args.doi}'")

try:
    # Buat filter jika DOI diberikan
    scroll_filter = None
    if args.doi:
        scroll_filter = Filter(
            must=[FieldCondition(key="doi", match=MatchValue(value=args.doi))]
        )

    # Mengambil chunks (scroll)
    records, next_page = client.scroll(
        collection_name=collection_name,
        scroll_filter=scroll_filter,
        limit=10000,
        with_payload=True,
        with_vectors=False # Kita tidak butuh melihat angka vektornya
    )
    
    # Format agar rapi
    output = []
    for r in records:
        output.append(r.payload)
        
    # Simpan ke JSON
    filename = "hasil_chunking.json" if not args.doi else f"chunking_{args.doi.replace('/', '_')}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=4, ensure_ascii=False)
        
    print(f"✅ Sukses! {len(output)} chunks berhasil diekstrak ke '{filename}'")
    
except Exception as e:
    print(f"Gagal mengekstrak: {e}")
