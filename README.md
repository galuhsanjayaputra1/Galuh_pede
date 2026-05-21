# 📄 PEDE — PDF to Model Embedding

Pipeline CLI untuk mengkonversi artikel ilmiah PDF ke vector embeddings di Qdrant.

```
PDF → Markdown → Smart Chunking + Metadata → Embedding → Qdrant Vector DB
```

> **📖 BACA DOKUMENTASI LENGKAP API:** Silakan cek file [API_REFERENCE.md](file:///c:/Users/Rolly%20Maulana%20Awangg/Documents/if/pede/API_REFERENCE.md) untuk melihat daftar lengkap *endpoint* dan cara melakukan RAG via HTTP!

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Ingest PDFs

```bash
# Single file
python ingest.py paper.pdf

# Entire directory
python ingest.py ./papers/

# Multiple files
python ingest.py paper1.pdf paper2.pdf paper3.pdf
```

### 4. Check Results

```bash
# List all ingested articles
python ingest.py --list

# Collection statistics
python ingest.py --info

# Test search
python ingest.py --search "neurosymbolic AI"
```

## Architecture

| Stage | Tool | Output |
|-------|------|--------|
| PDF → Markdown | `pymupdf4llm` | Structured markdown with headings |
| Metadata Extraction | 3-layer (PDF + Regex + CrossRef API) | Title, authors, DOI, abstract, etc. |
| Chunking | Hybrid (Header + Recursive) | ~1000 char chunks with section metadata |
| Embedding | `sentence-transformers` (nomic-embed-text-v1.5) | 768-dim vectors (8192 context) |
| Storage | Qdrant | Vectors + rich payload metadata |

## 🌟 Advanced SOTA Features (Baru)
1. **Content-Based Deduplication**: Mencegah duplikasi artikel walaupun nama file PDF diubah-ubah. ID artikel dihasilkan secara deterministik menggunakan kombinasi DOI artikel atau _SHA-256 Byte Hash_ dari file.
2. **Page Boundary Stitching**: Otomatis menghapus nomor halaman dan _header/footer_ yang menyela kalimat di tengah perpindahan halaman PDF, lalu menyambungkan kalimat yang terputus.
3. **Reference Dropping**: Otomatis melewati (skip) bagian Daftar Pustaka untuk mencegah polusi _Semantic Search_ (kecuali flag `--include-references` diaktifkan).
4. **Table Cleanup**: Membersihkan artefak ekstraksi tabel untuk membantu LLM bernalar pada data sel.

## Chunk Metadata

Each chunk stored in Qdrant carries:

- `article_id` — UUID per artikel (untuk filter retrieval)
- `title`, `authors`, `doi` — identitas artikel
- `section_header` — "Introduction", "Methods", "Results", dll
- `section_hierarchy` — "Methods > Data Collection > Survey"
- `content_type` — "text", "table", "references", "figure_caption"
- `chunk_index` / `total_chunks` — posisi dalam dokumen

## CLI Options

```
python ingest.py [paths] [options]

positional:
  paths                  PDF file(s) or directory

options:
  --qdrant-path PATH     Qdrant local DB path (default: ./qdrant_db)
  --collection NAME      Collection name (default: scientific_articles)
  --chunk-size N         Max chunk size in chars (default: 1000)
  --chunk-overlap N      Chunk overlap in chars (default: 200)
  --list                 List articles in Qdrant
  --info                 Show collection stats
  --search QUERY         Test search
  --include-references   Include references (default is to SKIP them)
```

## 🤖 Integration with Golang Agentic AI

Karena pipeline ini menggunakan model *embedding* lokal dan Qdrant, agen AI berbahasa Golang Anda dapat dengan mudah melakukan kueri (RAG) ke database ini.

### Prasyarat di Golang
1. **Library Qdrant Go**: Gunakan SDK resmi `github.com/qdrant/go-client` atau cukup gunakan HTTP REST API Qdrant.
2. **Embedding API (Ollama / Python)**: Karena Golang tidak memiliki pustaka native yang efisien untuk _Sentence-Transformers_, cara termudah mem-vektorisasi pertanyaan (_query_) di Golang adalah dengan **Ollama**.
   - Jalankan: `ollama run nomic-embed-text`

### Langkah-langkah (Workflow Agent Golang)

**1. Vektorisasi Pertanyaan (Query Embedding)**
Ubah pertanyaan pengguna menjadi vektor 768-dimensi.
> ⚠️ **CRITICAL:** Model Nomic-AI v1.5 mengharuskan Anda menambahkan *prefix* `"search_query: "` di depan setiap pertanyaan pencarian.

```go
package main

import (
	"bytes"
	"encoding/json"
	"net/http"
)

func embedQuery(query string) ([]float32, error) {
    // Ingat prefix wajib untuk nomic-embed-text!
	prompt := "search_query: " + query
	
	reqBody, _ := json.Marshal(map[string]string{
		"model":  "nomic-embed-text",
		"prompt": prompt,
	})

	resp, err := http.Post("http://localhost:11434/api/embeddings", "application/json", bytes.NewBuffer(reqBody))
	// Parse response JSON dan kembalikan array of floats
    // ...
}
```

**2. Pencarian Semantik ke Qdrant**
Kirim vektor tersebut ke Qdrant REST API (Port 6333) atau via gRPC (Port 6334).

```go
func searchQdrant(vector []float32) {
    reqBody, _ := json.Marshal(map[string]interface{}{
		"vector": vector,
		"limit":  5, // Ambil 5 chunk paling relevan
		"with_payload": true,
	})
	
	resp, _ := http.Post("http://localhost:6333/collections/scientific_articles/points/search", "application/json", bytes.NewBuffer(reqBody))
	
    // Hasilnya akan memuat "payload" (berisi text asli, doi, section_header, dll)
}
```

**3. Injeksi Konteks ke Agen LLM**
Setelah Qdrant mengembalikan 5 _chunks_ terbaik, gabungkan payload `content` tersebut ke dalam *System Prompt* agen AI Anda.

```go
// Contoh System Prompt Agent:
systemPrompt := `Anda adalah asisten AI Peneliti. Gunakan konteks saintifik berikut untuk menjawab pertanyaan pengguna.
Konteks didapatkan dari jurnal ilmiah:
`

for _, hit := range qdrantHits {
    // Inject teks beserta info metadatanya!
    systemPrompt += fmt.Sprintf("\n[Bagian: %s | Sumber: %s]\n%s\n", 
        hit.Payload["section_header"], 
        hit.Payload["title"], 
        hit.Payload["content"],
    )
}

// Terakhir, kirim systemPrompt ini ke OpenAI / Gemini / Claude via Go SDK!
```

## License

GNU GPL v3
