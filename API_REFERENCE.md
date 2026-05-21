# 🔌 PEDE API Reference

PEDE menyediakan REST API berbasis **FastAPI** ringan yang menjembatani aplikasi eksternal (seperti backend Golang Anda) dengan mesin *Semantic Search* Qdrant.

API ini akan secara otomatis memuat model *embedding* (Nomic-AI) ke dalam memori untuk memastikan proses vektorisasi berjalan dalam hitungan milidetik.

---

## 🚀 Cara Menjalankan Server

Jalankan perintah berikut di dalam direktori proyek:
```bash
python api.py
```
*Server akan menyala di `http://0.0.0.0:8000`.*

> **💡 TIPS INTERAKTIF (Swagger UI)**
> Karena dibangun menggunakan FastAPI, Anda dapat melihat dokumentasi interaktif dan mencoba langsung API ini melalui browser dengan mengunjungi: 
> **👉 http://localhost:8000/docs**

---

## 1. Health Check
Endpoint sederhana untuk memverifikasi bahwa *Vector Database* (Qdrant) dapat diakses dan model *embedding* telah termuat dengan sukses di memori.

- **URL**: `/`
- **Method**: `GET`
- **Response Code**: `200 OK`

### Contoh Response (JSON)
```json
{
  "status": "online",
  "collection": "scientific_articles",
  "total_chunks_in_db": 114
}
```

---

## 2. Semantic Search
Melakukan pencarian semantik tingkat lanjut ke dokumen-dokumen ilmiah yang telah di-*ingest*. Anda dapat membatasi pencarian pada artikel spesifik atau bahkan pada sub-bab spesifik.

- **URL**: `/search`
- **Method**: `POST`
- **Headers**: `Content-Type: application/json`

### Request Body (JSON)

| Field | Tipe Data | Wajib | Default | Deskripsi |
|-------|-----------|-------|---------|-----------|
| `query` | `string` | **Ya** | - | Kalimat pertanyaan atau kata kunci yang dicari. |
| `limit` | `int` | Tidak | `5` | Jumlah *chunks* (paragraf) maksimum yang ingin dikembalikan. |
| `article_id` | `string` | Tidak | `null` | UUID spesifik artikel jika ingin membatasi pencarian. |
| `doi` | `string` | Tidak | `null` | Filter berdasarkan DOI artikel (alternatif yang lebih mudah dibanding UUID). |
| `section_filter` | `string` | Tidak | `null` | Nama header sub-bab jika ingin membatasi pencarian. |

**Contoh Payload Request:**
```json
{
  "query": "Apa itu arsitektur neuro-symbolic?",
  "limit": 3,
  "article_id": "ae066c24-5c11-544f-8558-3aacd0a19215"
}
```

### Response Body (JSON)

| Field | Tipe Data | Deskripsi |
|-------|-----------|-----------|
| `total_found` | `int` | Jumlah *chunks* yang berhasil dikembalikan. |
| `results` | `array` | Daftar objek hasil pencarian yang diurutkan berdasarkan skor kemiripan. |

**Struktur Objek di dalam `results`:**
- `score` *(float)*: Jarak/skor kemiripan kosinus (0.0 hingga 1.0).
- `content` *(string)*: Teks asli dari paragraf/chunk PDF.
- `metadata` *(object)*: Kumpulan data pelengkap.

**Contoh Response:**
```json
{
  "total_found": 3,
  "results": [
    {
      "score": 0.8123,
      "content": "Neuro-symbolic AI adalah hibridisasi antara jaringan saraf tiruan dan logika simbolis...",
      "metadata": {
        "article_id": "ae066c24-5c11-544f-8558-3aacd0a19215",
        "title": "A review of neuro-symbolic AI integrating reasoning and learning",
        "authors": "Uzma Nawaz, Mufti Anees-ur-Rahaman, Zubair Saeed",
        "doi": "10.1016/j.iswa.2025.200541",
        "section_header": "1.2. Emergence of neuro-symbolic AI",
        "content_type": "text",
        "chunk_index": 12,
        "total_chunks": 114
      }
    }
  ]
}
```

---

## 🛠 Contoh Integrasi dengan cURL

**Mencari secara Global (Semua PDF):**
```bash
curl -X 'POST' \
  'http://localhost:8000/search' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "query": "Jelaskan metode perbandingan kinerja LLM",
  "limit": 5
}'
```

**Mencari Spesifik di 1 Artikel Saja (Menggunakan Filter UUID):**
```bash
curl -X 'POST' \
  'http://localhost:8000/search' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "query": "Berapa persen tingkat akurasinya?",
  "limit": 2,
  "article_id": "ae066c24-5c11-544f-8558-3aacd0a19215",
  "section_filter": "4. Results and Discussion"
}'
```

**Mencari Spesifik Menggunakan DOI (Sangat Praktis!):**
```bash
curl -X 'POST' \
  'http://localhost:8000/search' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "query": "Apa temuan utamanya?",
  "limit": 3,
  "doi": "10.1016/j.iswa.2025.200541"
}'
```
