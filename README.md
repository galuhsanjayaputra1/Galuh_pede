# 📄 PEDE — PDF to Model Embedding

Pipeline CLI untuk mengkonversi artikel ilmiah PDF ke vector embeddings di Qdrant.

```
PDF → Markdown → Smart Chunking + Metadata → Embedding → Qdrant Vector DB
```

cek hasil chunking:

```sh
python dump_chunks.py --doi "10.1016/j.inpa.2026.02.006"
```

> **📖 BACA DOKUMENTASI LENGKAP API:** Silakan cek file [API_REFERENCE.md](API_REFERENCE.md) untuk melihat daftar lengkap *endpoint* dan cara melakukan RAG via HTTP!

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Konfigurasi Qdrant (Lokal vs Cloud)

Secara bawaan (*default*), *database* akan disimpan di folder lokal `./qdrant_db`. 
Namun, jika Anda ingin menggunakan **Qdrant Cloud** untuk skalabilitas (agar Colab dan Lokal terhubung ke *database* yang sama), Anda cukup menyalin file `.env`:

```bash
cp .env.example .env
```
Kemudian isi file `.env` tersebut dengan *Endpoint URL* dan *API Key* Anda:
```ini
QDRANT_URL="https://xxx.cloud.qdrant.io"
QDRANT_API_KEY="api_key_anda"
```

### 3. Ingesting PDFs

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

## 🚀 Menjalankan di Google Colab

Tersedia notebook siap pakai di [`notebooks/pede_colab.ipynb`](notebooks/pede_colab.ipynb) untuk menjalankan ingestion di Colab (dengan GPU gratis) tanpa perlu setup lokal.

### 1. Buka notebook & mount Drive
Buka notebook di Colab, lalu jalankan cell pertama untuk `mount` Google Drive (tempat PDF Anda berada). Cell berikutnya akan otomatis `git clone` repo ini (atau `git pull` jika sudah ada) ke `/content/PEDE`.

### 2. Set kredensial via Colab Secrets 🔑
Klik ikon **kunci (🔑 Secrets)** di sidebar kiri Colab, tambahkan secret berikut, lalu **aktifkan _Notebook access_** untuk masing-masing:

| Nama Secret | Wajib? | Keterangan |
|-------------|--------|------------|
| `QDRANT_URL` | ✅ Ya | Endpoint Qdrant Cloud (mis. `https://xxx.cloud.qdrant.io`) |
| `QDRANT_API_KEY` | ✅ Ya | API key Qdrant Cloud |
| `TELEGRAM_BOT_TOKEN` | ⬜ Opsional | Token bot dari [@BotFather](https://t.me/BotFather) untuk notifikasi |
| `TELEGRAM_CHAT_ID` | ⬜ Opsional | Chat ID tujuan notifikasi |

> Tidak ada kredensial yang ditulis di dalam notebook — semuanya dibaca dari Secrets, jadi aman dibagikan.

### 3. Tentukan folder PDF
Pada cell konfigurasi, ubah variabel `PDF_FOLDER` ke lokasi folder PDF Anda di Drive, contoh:
```python
PDF_FOLDER = "/content/drive/MyDrive/wilwor"
```

### 4. Run all
Jalankan semua cell (**Runtime → Run all**). Pipeline akan memproses semua PDF, dan **log tampil live**. Jika `TELEGRAM_*` diisi, Anda akan menerima **notifikasi otomatis** saat proses selesai (sukses/gagal) berisi ringkasan: jumlah PDF, jumlah berhasil/gagal, durasi, dan total chunk di Qdrant.

### Mendapatkan Token & Chat ID Telegram
1. **Bot token** → chat ke [@BotFather](https://t.me/BotFather) → `/newbot` → ikuti langkah → salin token `123456:ABC-DEF...`.
2. **Chat ID** → kirim 1 pesan ke bot Anda, lalu buka `https://api.telegram.org/bot<TOKEN>/getUpdates` di browser → cari `"chat":{"id":...}`.

### ♻️ Aman untuk diulang (resume)
Berkat **deduplikasi berbasis konten** (DOI / SHA-256 hash file), Anda **boleh menjalankan ulang** notebook kapan saja — mis. setelah sesi Colab terputus. PDF yang sudah masuk akan otomatis di-skip, insersi yang setengah jalan akan dibersihkan dan diproses ulang, sehingga tidak terjadi duplikat.

**Yang sudah tahan banting:**
- ✅ **Idempoten per-PDF** — ulang-jalan tidak menduplikasi; PDF selesai di-skip lewat dedup (Step 0) dan dedup pasca-metadata (Step 2.5).
- ✅ **Pembersihan insersi parsial** — jika chunk suatu artikel tersimpan sebagian (count < total), otomatis dihapus & diproses ulang.
- ✅ **Error per-PDF terisolasi** — gangguan jaringan pada satu PDF hanya menggagalkan PDF itu (ditangkap `try/except`), batch lanjut; PDF gagal akan dicoba lagi saat re-run.
- ✅ **Retry + exponential backoff** pada panggilan CrossRef & Qdrant (3x percobaan) — tahan terhadap blip jaringan / rate-limit (HTTP 429/5xx) tanpa menggagalkan PDF.
- ✅ **Notifikasi Telegram live** — pesan "🚀 mulai" yang di-update tiap PDF (`editMessageText`). Bila kernel mati di tengah, pesan tetap menampilkan **PDF terakhir yang sedang diproses**, jadi Anda tahu sampai mana prosesnya.
- ✅ **Auto-retry loop di notebook** — selama kernel masih hidup, ingestion otomatis diulang (maks. `MAX_ATTEMPTS`, jeda `RETRY_DELAY` detik) bila ada PDF gagal. Cocok untuk gangguan internet sesaat; PDF yang sudah masuk di-skip tiap putaran.

**Keterbatasan (perlu aksi manual):**
- ⚠️ **Auto-retry hanya jika kernel hidup** — jika kernel/sesi Colab benar-benar mati (bukan sekadar internet putus), proses berhenti dan Anda harus **menjalankan ulang cell secara manual** (aman, karena idempoten).
- ⚠️ **Pesan Telegram _final_ tidak terkirim saat kernel di-_kill_ mendadak** — namun pesan progress live tetap menunjukkan posisi terakhir (lihat poin di atas).
- ⚠️ **Model embedding (~2.3GB) di-unduh ulang tiap sesi baru** Colab (tidak di-cache ke Drive).
- ⚠️ **PDF tanpa DOI tertanam** (DOI hanya didapat via CrossRef) akan **dikonversi ulang (OCR)** tiap re-run sebelum di-skip di Step 2.5 — benar, tapi boros waktu.

## Architecture

| Stage | Tool | Output |
|-------|------|--------|
| PDF → Markdown | `pymupdf4llm` | Structured markdown with headings |
| Metadata Extraction | 3-layer (PDF + Regex + CrossRef API) | Title, authors, DOI, abstract, etc. |
| Chunking | Hybrid (Header + Recursive) | ~2500 char chunks with section metadata |
| Embedding | `FlagEmbedding` BGE-M3 (fallback: `sentence-transformers`) | **Dense 1024-d + Sparse/lexical** (8192 context, multilingual); konteks judul+section diprepend |
| Storage | Qdrant (named vectors: `dense` + `sparse`) | Vektor hybrid + rich payload metadata |
| Retrieval | Hybrid search (dense + sparse, **RRF fusion**) | Gabungan kemiripan semantik & pencocokan istilah eksak |

## 🌟 Advanced SOTA Features (Baru)
1. **Content-Based Deduplication**: Mencegah duplikasi artikel walaupun nama file PDF diubah-ubah. ID artikel dihasilkan secara deterministik menggunakan kombinasi DOI artikel atau _SHA-256 Byte Hash_ dari file.
2. **Page Boundary Stitching**: Otomatis menghapus nomor halaman dan _header/footer_ yang menyela kalimat di tengah perpindahan halaman PDF, lalu menyambungkan kalimat yang terputus.
3. **Reference Dropping**: Otomatis melewati (skip) bagian Daftar Pustaka untuk mencegah polusi _Semantic Search_ (kecuali flag `--include-references` diaktifkan).
4. **Table Cleanup**: Membersihkan artefak ekstraksi tabel untuk membantu LLM bernalar pada data sel.
5. **Hybrid Retrieval (Dense + Sparse)**: Memanfaatkan kemampuan native BGE-M3 menghasilkan vektor _dense_ (semantik) dan _sparse/lexical_ sekaligus. Pencarian menggabungkan keduanya via **RRF fusion** — unggul untuk istilah eksak (nama model, kode dataset, DOI) sekaligus makna. Jika `FlagEmbedding` tak terpasang, otomatis fallback ke _dense-only_.
6. **Context-Aware Embedding**: Judul artikel + _section header_ diprepend ke teks tiap chunk saat embedding (bukan ke payload), agar sub-chunk panjang tidak kehilangan konteks dan recall meningkat.

> ⚠️ **Catatan upgrade:** Versi hybrid memakai skema Qdrant _named vectors_ (`dense` + `sparse`). Jika Anda upgrade dari versi dense-only lama, **buat ulang collection** (mis. `vs.delete_collection(...)` lalu ingest ulang) karena skema vektornya berbeda.

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
  --chunk-size N         Max chunk size in chars (default: 2500)
  --chunk-overlap N      Chunk overlap in chars (default: 400)
  --list                 List articles in Qdrant
  --info                 Show collection stats
  --search QUERY         Test search
  --doi DOI              Filter search results by DOI
  --include-references   Include references (default is to SKIP them)
```

**Contoh Pencarian via CLI:**
```bash
# Pencarian global (semua jurnal)
python ingest.py --search "Apa itu neurosymbolic?"

# Pencarian spesifik ke 1 jurnal menggunakan DOI
python ingest.py --search "Apa hasil eksperimennya?" --doi "10.1016/j.inpa.2026.02.006"
```

## 🤖 Integration with Golang Agentic AI

Proyek ini telah dilengkapi dengan purwarupa **Agentic AI** berbasis Golang di dalam folder `agent-go/`. 

Agen Golang ini menggunakan SDK `github.com/google/generative-ai-go` dan dilengkapi kemampuan **Function Calling** (Tools). Ia tidak memanggil Qdrant secara langsung, melainkan menggunakan API Server Python (`api.py`) sebagai jembatan.

### Arsitektur Agentic RAG
1. **User Prompt:** Anda bertanya *"Apa hasil eksperimen jurnal X?"* di terminal Golang.
2. **Gemini Reasoning:** LLM Gemini menyadari bahwa itu adalah pertanyaan akademis, lalu ia memutuskan untuk menggunakan fungsi `query_scientific_database`.
3. **Golang Action:** Golang menangkap permintaan fungsi tersebut, lalu mengirim HTTP POST `{"query": "...", "doi": "..."}` ke `http://localhost:8000/search`.
4. **Python RAG:** FastAPI meng-embed *query* via BGE-M3, mencari 5 *chunks* terdekat di Qdrant, dan mengembalikannya ke Golang.
5. **Synthesis:** Golang menyodorkan 5 *chunks* tersebut ke Gemini, dan Gemini merangkumnya menjadi jawaban akhir yang sangat akurat.

### Cara Menjalankan Agen Golang
1. Pastikan server API Python berjalan:
   ```bash
   uvicorn api:app --port 8000
   ```
2. Buka terminal baru, masuk ke folder `agent-go`:
   ```bash
   cd agent-go
   ```
3. Set *environment variable* untuk Gemini API Key Anda:
   ```bash
   # Windows PowerShell
   $env:GEMINI_API_KEY="AIzaSy..."
   ```
4. Jalankan agen:
   ```bash
   go run .
   ```

Selamat bereksperimen dengan Agentic RAG Anda!

## License

GNU GPL v3
