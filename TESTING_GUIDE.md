# Panduan Testing Sistem Agregasi Pengumuman

Dokumen ini menjelaskan cara menguji setiap komponen sistem scraping.

---

## Quick Start Testing

### 1. Test Scraper Individual (Tanpa Database)

```bash
# Test satu website
py test_scraper.py lepkom
py test_scraper.py kemahasiswaan
py test_scraper.py studentsite
py test_scraper.py baak
py test_scraper.py pendaftaran

# Test semua website
py test_scraper.py all

# Test mode cepat (hanya 1 item per website)
py test_scraper.py --fast all
py test_scraper.py --fast baak
```

### 2. Test Kompilasi Python

```bash
py -m compileall .
```

### 3. Test Koneksi Database

```bash
py -c "from database.db import init_db; init_db(); print('Database OK')"
```

### 4. Test Discord Webhook

```bash
py -c "from notifier.discord import kirim_notifikasi_discord; kirim_notifikasi_discord({'judul':'Test','sumber':'TEST','tanggal':'2026-06-01','link':'https://example.com','file_url':''})"
```

---

## Expected Output per Scraper

### LEPKOM
- ✅ Ambil 5 pengumuman dari widget recent-posts
- ✅ Setiap item harus punya: judul, tanggal, link, author, isi, file_url
- ✅ Playwright headless, tidak perlu FlareSolverr
- ✅ Waktu: ~15-20 detik

### Kemahasiswaan
- ✅ Ambil 5 pengumuman dari artikel dan slider
- ✅ Setiap item harus punya: judul, link, author (dengan tanggal), isi
- ✅ Memerlukan FlareSolverr atau Playwright dengan stealth
- ⚠️ Kadang timeout jika Cloudflare challenge aktif
- ⏱️ Waktu: ~60-180 detik (tergantung FlareSolverr)

### Studentsite
- ✅ Ambil 5 pengumuman dari div.content-box
- ✅ Setiap item harus punya: judul, tanggal, link, file_url (link eksternal)
- ✅ Playwright headless, tidak perlu FlareSolverr
- ✅ Waktu: ~10-15 detik

### BAAK
- ✅ Ambil 5 berita dari halaman list
- ✅ Setiap item harus punya: judul, tanggal, link, isi
- ✅ Memerlukan FlareSolverr karena Cloudflare Managed Challenge
- ⚠️ Kadang timeout (120s), tetapi data list biasanya cukup
- ⏱️ Waktu: ~30-120 detik (tergantung Cloudflare)
- 🚀 Optimisasi: Skip detail page jika data list sudah lengkap

### Pendaftaran
- ✅ Ambil 2 berita (website hanya ada 2)
- ✅ Setiap item harus punya: judul, link, author, isi, file_url
- ✅ Memerlukan FlareSolverr karena Cloudflare Managed Challenge
- ⏱️ Waktu: ~40-90 detik

---

## FlareSolverr Setup

BAAK, Kemahasiswaan, dan Pendaftaran memerlukan FlareSolverr untuk bypass Cloudflare.

### Install dan Jalankan FlareSolverr (Docker)

```bash
# Jalankan FlareSolverr
docker run -d --name flaresolverr -p 8191:8191 -e LOG_LEVEL=info ghcr.io/flaresolverr/flaresolverr:latest

# Cek status
docker ps | findstr flaresolverr

# Restart jika perlu
docker restart flaresolverr

# Stop
docker stop flaresolverr
```

### Cek FlareSolverr Running

```bash
curl http://localhost:8191/health
```

Output: `{"status":"ok"}`

---

## Troubleshooting

### Scraper Timeout
- Cek FlareSolverr: `docker ps | findstr flaresolverr`
- Restart FlareSolverr: `docker restart flaresolverr`
- Cek log: `logs/sistem_YYYYMMDD.log`
- BAAK timeout normal jika Cloudflare challenge berat, tetapi data list sudah cukup

### Data Kosong
- Cek `debug_<sumber>.html` untuk melihat HTML aktual
- Selector mungkin berubah, perlu update kode scraper
- Jika HTML menampilkan "Just a moment", Cloudflare masih aktif

### Cloudflare Challenge
- BAAK, Kemahasiswaan, dan Pendaftaran dilindungi Cloudflare
- Jika headless browser gagal, sistem otomatis fallback ke FlareSolverr
- Jika FlareSolverr timeout, scraper akan retry 2 kali
- Jika masih gagal, sistem lanjut ke scraper berikutnya

### Unicode / Encoding Error
- Semua log sudah menggunakan ASCII: `[INFO]`, `[OK]`, `[WARNING]`, `[ERROR]`
- Jika masih ada karakter aneh di terminal, coba: `chcp 65001`

---

## Catatan Penting

1. **FlareSolverr** wajib untuk BAAK, Kemahasiswaan, dan Pendaftaran
2. **Timeout** FlareSolverr: 120 detik untuk Managed Challenge
3. **Retry** maksimal 2 kali per FlareSolverr request, 2 kali per scraper
4. **Jeda antar scraper**:
   - 10 detik (normal)
   - 30 detik (setelah scraper Cloudflare untuk recovery)
5. **Optimisasi BAAK**: Skip detail page jika data list sudah cukup (isi >= 50 karakter)

---

## Test Workflow Lengkap

```bash
# 1. Pastikan FlareSolverr running
docker ps | findstr flaresolverr
# Jika belum running:
docker run -d --name flaresolverr -p 8191:8191 ghcr.io/flaresolverr/flaresolverr:latest

# 2. Kompilasi check
py -m compileall .

# 3. Test scraper tanpa Cloudflare dulu (cepat)
py test_scraper.py --fast lepkom
py test_scraper.py --fast studentsite

# 4. Test scraper dengan Cloudflare (lambat)
py test_scraper.py --fast kemahasiswaan
py test_scraper.py --fast baak
py test_scraper.py --fast pendaftaran

# 5. Test semua website mode normal
py test_scraper.py all

# 6. Jalankan program utama
py main.py
```

---

## Expected Test Results

### Test Semua (Fast Mode)
```
py test_scraper.py --fast all
```

**Expected Output:**
- LEPKOM: 1 item (~15s)
- STUDENTSITE: 1 item (~10s)
- KEMAHASISWAAN: 1 item (~60s)
- BAAK: 1 item (~30s)
- PENDAFTARAN: 1 item (~40s)
- Total: 5 items dalam ~2-3 menit

### Test Semua (Normal Mode)
```
py test_scraper.py all
```

**Expected Output:**
- LEPKOM: 5 items (~20s)
- STUDENTSITE: 5 items (~15s)
- KEMAHASISWAAN: 5 items (~180s)
- BAAK: 5 items (~120s)
- PENDAFTARAN: 2 items (~90s)
- Total: 22 items dalam ~7-10 menit

---

## Monitoring Logs

Cek log sistem untuk detail error:

```bash
# Lihat log hari ini
type "logs\sistem_20260622.log"

# Filter hanya error
type "logs\sistem_20260622.log" | findstr ERROR

# Filter hanya warning
type "logs\sistem_20260622.log" | findstr WARNING
```

---

## Debug HTML Files

Jika scraper gagal ambil data, sistem otomatis menyimpan HTML ke:

- `debug_lepkom.html`
- `debug_kemahasiswaan.html`
- `debug_studentsite.html`
- `debug_baak.html`
- `debug_pendaftaran.html`

Buka file tersebut di browser untuk inspeksi selector CSS yang perlu diperbaiki.
