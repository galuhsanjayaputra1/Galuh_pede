# Benchmark Word2Vec untuk PEDE

## A. Deskripsi Model Word2Vec
Word2Vec adalah model embedding kata berbasis neural yang memetakan setiap kata ke dalam ruang vektor berdimensi tetap. Dalam implementasi PEDE, setiap chunk dokumen di-representasikan sebagai rata-rata vektor kata yang diambil dari model Word2Vec. Metode ini cocok untuk retrieval dokumen yang mengandalkan kemiripan leksikal dan semantic sederhana.

- Tipe: dense embedding berbasis distribusi kata.
- Dimensi default: 300.
- Sumber: gensim Word2Vec (`word2vec-google-news-300`) atau model lokal `.bin` Word2Vec.
- Representasi chunk: rata-rata vektor kata setelah tokenisasi.

## B. Kelebihan dan Kekurangan

### Kelebihan
- Cepat dan ringan untuk inferensi, terutama dibanding model transformer besar.
- Kompatibel dengan pipeline Qdrant yang sudah ada tanpa perubahan besar.
- Dapat dijalankan sepenuhnya secara lokal tanpa memerlukan GPU atau akses API eksternal.
- Stabil untuk dokumen bahasa yang kosakatanya sudah tercover oleh model Word2Vec.

### Kekurangan
- Kemampuan semantic lebih lemah dibanding embedding transformer modern.
- Sensitif terhadap kata yang tidak ada dalam kosakata (`out-of-vocabulary`).
- Kurang efektif untuk query kompleks atau paraphrase yang jauh dari kata-kata asli teks.
- Tidak mendukung hybrid dense+sparse retrieval seperti BGE-M3 secara native.

## C. Konfigurasi Chunking
Chunking di PEDE tetap menggunakan mekanisme yang sama seperti benchmark umum, namun untuk Word2Vec ada beberapa rekomendasi:

- Ukuran Chunk: 500–1000 karakter.
- Overlap: 100–200 karakter.
- Metode: chunk sintaksis dengan titik/paragraf, karena Word2Vec terbaik pada konteks lokal yang kohesif.
- Prepend context: judul dan section header tetap dipasangkan dengan setiap chunk agar konteks dokumen terjaga.

Rekomendasi konfigurasi untuk evaluasi:
- `chunk_size=800`
- `chunk_overlap=150`

## D. Hasil Benchmark
Hasil benchmark dapat diukur dari beberapa metrik utama:

- Hit Rate (Recall@K)
- Rata-rata latensi pencarian
- Ukuran index Qdrant
- Support language
- Kesesuaian query jenis `Factoid`, `Paraphrased`, dan `Conversational`

Contoh hasil eksperimental untuk Word2Vec (nilai placeholder harus diisi berdasarkan pengujian riil):

- Hit Rate: 68% pada Top-K 5 untuk query simple.
- Latensi: 18–45 ms per query pada Qdrant local dengan 10.000 chunk.
- Ukuran Index DB: sekitar 90 MB per 1.000 artikel (300-dim).
- Bahasa: paling baik untuk Bahasa Inggris dan dokumen yang kosakatanya tercover.

## E. Tabel Perbandingan
| Ukuran Chunk | Overlap | Metode Chunking | Model Embedding | Dukungan Bahasa | Tipe Query Uji | Top-K | Filter Metadata | Hit Rate | Latensi | Ukuran Index DB | Catatan |
|:---:|:---:|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---|
| 800 | 150 | Sintaksis | Word2Vec (300-d) | Inggris / kosakata luas | Factoid | 5 | Ya (DOI) | 65-72% | 18-35 ms | 80-100 MB | *Cepat dan ringan untuk retrieval lokal* |
| 1000 | 200 | Hybrid | Word2Vec (300-d) | Inggris / dokumen teknis | Paraphrased | 10 | Ya (section) | 55-62% | 22-45 ms | 100-120 MB | *Cenderung underperform pada paraphrase kompleks* |
| 600 | 100 | Sintaksis | Word2Vec (300-d) | Inggris | Conversational | 5 | Tidak | 58-66% | 16-30 ms | 70-90 MB | *Meningkat bila query menggunakan istilah yang sama* |
| 1000 | 150 | Statis | BGE-M3 / SentenceTransformer | Multi-bahasa / cross-lingual | Semantic | 5 | Ya | 75-88% | 35-90 ms | 120-250 MB | *Benchmark referensi untuk perbandingan* |

## F. Kesimpulan
Word2Vec adalah opsi praktis untuk pipeline PEDE ketika kebutuhan utama adalah latensi rendah, konsumsi sumber daya kecil, dan kemudahan deploy lokal. Model ini sangat cocok untuk aplikasi retrieval dengan kueri yang relatif dekat pada kosakata dokumen.

Namun, jika target use-case membutuhkan robustness terhadap query paraphrase, kemampuan cross-lingual, atau pemahaman konsep yang lebih dalam, Word2Vec akan kalah dibandingkan model embedding transformer modern seperti BGE-M3 atau SentenceTransformer besar.

### Rekomendasi
- Gunakan Word2Vec untuk prototyping cepat, data bahasa Inggris, dan lingkungan tanpa GPU.
- Untuk dokumentasi ilmiah multi-bahasa atau retrieval semantic berat, pertahankan model transformer yang lebih kuat.
- Lakukan benchmark real-world dengan dataset dan query nyata untuk memastikan angka Hit Rate dan latensi cocok dengan kebutuhan produksi.
