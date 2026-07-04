# Changelog: Perbaikan BAAK Scraper dan Logger

**Tanggal:** 30 Juni 2026  
**Versi:** 1.1.0

---

## 📋 Ringkasan Perubahan

Dua perbaikan utama pada sistem agregasi pengumuman:

1. **Perbaikan Scraper BAAK** - Implementasi FlareSolverr yang benar
2. **Perbaikan Logger System** - Output terminal yang lebih rapi dengan warna

---

## 🔧 1. Perbaikan Scraper BAAK (`scraper/baak.py`)

### Masalah Sebelumnya
- Scraper BAAK masih menggunakan Playwright meskipun FlareSolverr sudah aktif
- Log menunjukkan "Title awal: Just a moment..." dan "Title akhir: Tunggu sebentar..."
- Cloudflare challenge tidak berhasil di-bypass
- Data BAAK selalu kosong

### Solusi Implementasi
1. **Strategi Prioritas:** FlareSolverr sebagai strategi utama, Playwright sebagai fallback
2. **Parsing dengan BeautifulSoup:** Menggunakan HTML dari `solution.response` FlareSolverr
3. **Deteksi Cloudflare:** Helper function `_masih_cloudflare()` untuk validasi HTML
4. **Logging Eksplisit:** Log detail setiap tahap proses scraping

### Alur Baru
```
FlareSolverr Running? 
  ├─ YA → Request ke FlareSolverr
  │       ├─ Parse solution.response dengan BeautifulSoup
  │       ├─ Validasi title = "BAAK Online" (bukan "Just a moment")
  │       ├─ Extract link berita dari HTML
  │       └─ Request detail setiap berita via FlareSolverr
  │
  └─ TIDAK → Fallback ke Playwright headless
            └─ (Kemungkinan tetap terkena Cloudflare)
```

### Hasil Testing
```
✅ FlareSolverr terdeteksi aktif di localhost:8191
✅ HTML berhasil diambil: 34,053 karakter
✅ Title halaman: "BAAK Online" (BERHASIL bypass Cloudflare)
✅ Link berita ditemukan: 6 item
✅ Detail artikel berhasil di-scrape
```

### Catatan Performa
- **Request FlareSolverr:** ~40-50 detik per halaman (normal untuk bypass Cloudflare)
- **Total waktu 3 berita:** ~2-3 menit
- Ini adalah trade-off yang wajar untuk bypass Cloudflare yang stabil

---

## 🎨 2. Perbaikan Logger System (`utils/logger.py`)

### Masalah Sebelumnya
- Log terminal menampilkan teks multiline panjang
- Isi pengumuman/tabel delegasi penuh ditampilkan di terminal
- Sulit membedakan level log (INFO, WARNING, ERROR)
- Output berantakan dan tidak mudah dibaca

### Fitur Baru

#### A. Helper Functions

**1. `clean_log_text(text, max_length=150)`**
- Mengubah newline menjadi spasi
- Menghapus spasi berlebih
- Membatasi panjang maksimal (default 150 karakter)
- Tambahkan `...` jika dipotong

**Contoh Penggunaan:**
```python
logger.info(f"[BAAK] Judul: {clean_log_text(judul, 70)}")
# Output: [BAAK] Judul: PEMBERITAHUAN PERPANJANGAN WAKTU PENGISIAN DAN PENCETAKAN KRS
```

**2. `log_content_length(content, content_type="konten")`**
- Menampilkan panjang konten tanpa menampilkan isinya
- Format: "Isi berhasil diambil. Panjang: 2,480 karakter"

**Contoh Penggunaan:**
```python
logger.info(f"[BAAK] {log_content_length(html, 'HTML')}")
# Output: [BAAK] HTML berhasil diambil. Panjang: 34,053 karakter
```

#### B. Colored Console Output

**Library:** `colorama` (ringan, cross-platform, kompatibel Windows)

**Warna Log Level:**
- `DEBUG` - Abu-abu terang
- `INFO` - Cyan
- `WARNING` - Kuning
- `ERROR` - Merah
- `CRITICAL` - Merah tebal

**Warna Sumber:**
- `[BAAK]` - Biru terang
- `[KEMAHASISWAAN]` - Magenta terang
- `[STUDENTSITE]` - Hijau terang
- `[LEPKOM]` - Kuning terang
- `[PENDAFTARAN]` - Cyan terang
- `[FlareSolverr]` - Magenta

#### C. Dual Output
- **Console:** Dengan warna ANSI (untuk terminal)
- **File Log:** Plain text tanpa warna (untuk Notepad/editor)

### Contoh Output

**Sebelum:**
```text
[INFO] 2026-06-30 10:45:25 | [KEMAHASISWAAN] Preview tabel delegasi: 📋 Daftar Delegasi

1. Rafi Annas Purnomo
   NPM: 11424113
   Program Studi: Teknik Elektro (S1)
   Keterangan: Ketua

2. Indra Maulana
   NPM: 10424573
   ...
```

**Sesudah:**
```text
[INFO] 2026-06-30 10:45:25 | [KEMAHASISWAAN] Preview tabel delegasi: Daftar Delegasi | 1. Rafi Annas Purnomo NPM: 11424113 Program Studi: Teknik Elektro...
[INFO] 2026-06-30 10:45:26 | [KEMAHASISWAAN] Tabel delegasi berhasil diformat. Total konten berhasil diambil. Panjang: 2,480 karakter
```

---

## 📦 3. Update Dependencies (`requirements.txt`)

**Ditambahkan:**
```
colorama==0.4.6
```

**Instalasi:**
```bash
pip install -r requirements.txt
```

---

## 🔄 4. Update Scraper Lain

### `scraper/kemahasiswaan.py`
- Menggunakan `clean_log_text()` untuk preview tabel delegasi
- Menggunakan `log_content_length()` untuk log isi berita
- Import helper functions dari `utils.logger`

**Perubahan:**
```python
# Sebelum
logger.info(f"[KEMAHASISWAAN] OK: {item['judul'][:60]!r}")

# Sesudah
logger.info(f"[KEMAHASISWAAN] OK: {clean_log_text(item['judul'], 60)}")
```

---

## ✅ Validasi

### 1. Compile Check
```bash
py -m py_compile scraper/baak.py
py -m py_compile utils/logger.py
py -m py_compile scraper/kemahasiswaan.py
```
**Status:** ✅ Berhasil tanpa error

### 2. Test Scraper BAAK
```bash
py test_baak_only.py
```
**Status:** ✅ Berhasil scraping 3 berita dengan FlareSolverr

### 3. File Log
- **Lokasi:** `logs/sistem_YYYYMMDD.log`
- **Format:** Plain text tanpa ANSI color code ✅
- **Encoding:** UTF-8 ✅

---

## 🎯 Manfaat

### Scraper BAAK
✅ **Bypass Cloudflare berhasil** menggunakan FlareSolverr  
✅ **Data BAAK lengkap** (judul, tanggal, author, isi, file_url)  
✅ **Error handling** yang lebih baik  
✅ **Logging detail** untuk debugging  

### Logger System
✅ **Terminal rapi** tanpa multiline panjang  
✅ **Mudah dibaca** dengan warna dan format konsisten  
✅ **File log bersih** tanpa kode warna  
✅ **Reusable helpers** untuk semua scraper  

---

## 🚀 Cara Penggunaan

### Menjalankan Scraper BAAK
```bash
# Pastikan FlareSolverr berjalan
docker ps | findstr flaresolverr

# Test scraper BAAK
py test_baak_only.py

# Jalankan monitoring lengkap
py main.py
```

### Helper Functions di Scraper Lain

**1. Import:**
```python
from utils.logger import logger, clean_log_text, log_content_length
```

**2. Gunakan untuk preview:**
```python
# Judul/teks pendek
logger.info(f"[SUMBER] Judul: {clean_log_text(judul, 70)}")

# Isi panjang
logger.info(f"[SUMBER] {log_content_length(isi, 'Isi berita')}")
```

---

## 📝 Catatan Penting

1. **FlareSolverr wajib running** untuk scraper BAAK
2. **Waktu scraping lebih lama** (~40-50 detik per halaman) tapi stabil
3. **Warna log hanya di terminal**, file log tetap plain text
4. **Helper functions tersedia** untuk semua scraper lain
5. **Tidak ada perubahan** pada database, webhook, atau `.env`

---

## 🐛 Troubleshooting

### FlareSolverr tidak running
```bash
docker run -d --name flaresolverr -p 8191:8191 ghcr.io/flaresolverr/flaresolverr:latest
```

### Scraper masih gagal
1. Cek log di `logs/sistem_YYYYMMDD.log`
2. Cek file debug: `debug_baak.html`
3. Pastikan FlareSolverr status OK: `curl http://localhost:8191/health`

### Warna tidak muncul di terminal
- Windows Terminal / PowerShell: OK ✅
- CMD lama: Mungkin tidak support ANSI colors
- File log tetap plain text (tidak terpengaruh)

---

**Perubahan ini tidak mengubah:**
- Database schema atau koneksi
- Discord webhook
- File `.env`
- Scraper lain (kecuali KEMAHASISWAAN untuk demo helper)
- Alur monitoring utama

**Status:** ✅ **PRODUCTION READY**
