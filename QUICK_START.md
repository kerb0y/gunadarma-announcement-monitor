# Quick Start - Sistem Agregasi Pengumuman

**Last Update:** 22 Juni 2026, 13:30 PM  
**Status:** ✅ READY FOR CONFIGURATION

---

## 📌 Langkah Konfigurasi (WAJIB DIBACA)

### 1️⃣ Setup File .env

File `.env` sudah dibuat otomatis. Anda perlu mengisi konfigurasi berikut:

```bash
# Lihat file .env
notepad .env
```

**Konfigurasi yang WAJIB diisi:**

#### **A. Database MySQL**

```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=GANTI_DENGAN_PASSWORD_MYSQL_ANDA
DB_NAME=agregasi_pengumuman
```

**Cara cek password MySQL:**

**Jika pakai Laragon:**
- Buka Laragon → Menu → MySQL → MySQL Console
- Password akan ditampilkan (atau kosong jika default)
- Atau cek di: Laragon → Menu → Tools → Quick Add → Configuration

**Jika pakai XAMPP:**
- Biasanya password root adalah **kosong** (hapus teks setelah `DB_PASSWORD=`)
- Atau coba password: `root` atau yang Anda set saat install

**Test koneksi MySQL:**
```bash
python -c "import mysql.connector; conn = mysql.connector.connect(host='localhost', user='root', password='PASSWORD_ANDA'); print('MySQL OK' if conn.is_connected() else 'Gagal'); conn.close()"
```

Ganti `PASSWORD_ANDA` dengan password MySQL Anda.

#### **B. Discord Webhook (Opsional untuk Testing)**

```env
DISCORD_WEBHOOK_URL=
```

**Cara mendapatkan Discord Webhook:**

1. Buka Discord → pilih Server → klik Settings (⚙️) di samping nama channel
2. Pilih **Integrations** → **Webhooks** → **New Webhook**
3. Beri nama (misal: "Pengumuman UG Bot")
4. Pilih channel tujuan → **Copy Webhook URL**
5. Paste di `.env`:
   ```env
   DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/1234567890/AbCdEfGhIjKlMnOpQrStUvWxYz
   ```

**Catatan:** Jika `DISCORD_WEBHOOK_URL` kosong, sistem akan skip notifikasi Discord dan hanya simpan ke database. Tidak akan crash.

#### **C. Konfigurasi Testing (Sudah diatur untuk development)**

```env
MONITORING_INTERVAL_MINUTES=1
INITIAL_SCRAPE_LIMIT=1
DEBUG_MODE=true
```

**Penjelasan:**
- `MONITORING_INTERVAL_MINUTES=1` → Monitoring setiap 1 menit (untuk testing)
- `INITIAL_SCRAPE_LIMIT=1` → Ambil 1 data saja saat awal (cepat untuk testing)
- `DEBUG_MODE=true` → Tampilkan log lengkap di console

**Untuk Production/Demo Final:**
```env
MONITORING_INTERVAL_MINUTES=60
INITIAL_SCRAPE_LIMIT=5
DEBUG_MODE=false
```

---

### 2️⃣ Setup MySQL Database

Database akan dibuat **otomatis** saat pertama kali menjalankan `python main.py`.

**Yang dilakukan otomatis:**
1. ✅ Buat database `agregasi_pengumuman` (jika belum ada)
2. ✅ Buat tabel `pengumuman` dengan kolom:
   - `id` (Primary Key, Auto Increment)
   - `judul` (TEXT, NOT NULL)
   - `tanggal` (VARCHAR 100)
   - `link` (VARCHAR 500, NOT NULL)
   - `sumber` (VARCHAR 100, NOT NULL)
   - `isi` (TEXT, konten detail pengumuman)
   - `author` (VARCHAR 255, penulis/pembuat pengumuman)
   - `file_url` (VARCHAR 500, link file PDF/attachment)
   - `created_at` (TIMESTAMP, waktu insert)
3. ✅ Tambah **UNIQUE constraint** pada `(link, sumber)` → Mencegah duplikasi

**Jika ingin membuat database secara manual:**

```sql
CREATE DATABASE IF NOT EXISTS agregasi_pengumuman 
CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE agregasi_pengumuman;

CREATE TABLE IF NOT EXISTS pengumuman (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    judul       TEXT NOT NULL,
    tanggal     VARCHAR(100) DEFAULT '',
    link        VARCHAR(500) NOT NULL,
    sumber      VARCHAR(100) NOT NULL,
    isi         TEXT DEFAULT NULL,
    author      VARCHAR(255) DEFAULT '',
    file_url    VARCHAR(500) DEFAULT '',
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_link_sumber (link(450), sumber)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

---

### 3️⃣ Setup FlareSolverr (Docker)

FlareSolverr diperlukan untuk bypass **Cloudflare protection** di website BAAK dan Kemahasiswaan.

**Jalankan FlareSolverr:**
```bash
docker run -d --name flaresolverr -p 8191:8191 ghcr.io/flaresolverr/flaresolverr:latest
```

**Cek status:**
```bash
docker ps | findstr flaresolverr
```

**Expected output:**
```
CONTAINER ID   IMAGE                    STATUS          PORTS
abc123def456   flaresolverr:latest      Up 2 minutes    0.0.0.0:8191->8191/tcp
```

**Test FlareSolverr:**
```bash
curl http://localhost:8191/health
```
**Expected:** `{"status": "ok"}`

---

### 4️⃣ Validasi Konfigurasi

Sebelum menjalankan sistem, pastikan:

✅ File `.env` sudah diisi dengan benar  
✅ MySQL berjalan dan password benar  
✅ FlareSolverr berjalan di port 8191  
✅ Python dependencies sudah terinstall (`pip install -r requirements.txt`)

**Test koneksi MySQL:**
```bash
python -c "import mysql.connector; conn = mysql.connector.connect(host='localhost', user='root', password='PASSWORD_ANDA'); print('✅ MySQL OK'); conn.close()"
```

**Test FlareSolverr:**
```bash
python -c "import requests; r = requests.get('http://localhost:8191/health'); print('✅ FlareSolverr OK' if r.json().get('status') == 'ok' else '❌ Error')"
```

---

## 🚀 Quick Commands

### 1. Test Cepat (Recommended untuk Demo)
```bash
py test_scraper.py --fast all
```
**Expected:** 5/5 website berhasil dalam ~2-3 menit

### 2. Test Normal (Full Data)
```bash
py test_scraper.py all
```
**Expected:** 22 data dari 5 website dalam ~7-10 menit

### 3. Jalankan Program Utama
```bash
py main.py
```
**Expected:** Initial scraping → Monitoring setiap 60 menit → Discord notification

---

## 📋 Pre-Demo Checklist

```bash
# 1. Cek FlareSolverr running
docker ps | findstr flaresolverr
# Jika belum: docker run -d --name flaresolverr -p 8191:8191 ghcr.io/flaresolverr/flaresolverr:latest

# 2. Cek environment variables
type .env
# Pastikan DB_HOST, DB_USER, DB_PASSWORD, DISCORD_WEBHOOK_URL terisi

# 3. Test fast mode
py test_scraper.py --fast all
# Expected: 5/5 berhasil

# 4. Cek tidak ada syntax error
py -m compileall .
# Expected: No errors

# 5. Ready!
```

---

## 🎯 Demo Scenario

### Opening (30 detik)
"Sistem agregasi pengumuman otomatis untuk 5 website Universitas Gunadarma menggunakan Python, Playwright, FlareSolverr, MySQL, dan Discord webhook."

### Show Docker (15 detik)
```bash
docker ps | findstr flaresolverr
```
"FlareSolverr berjalan untuk bypass Cloudflare protection."

### Run Test (2-3 menit)
```bash
py test_scraper.py --fast all
```
"Test fast mode mengambil 1 data per website untuk verifikasi sistem berjalan."

### Explain Output (1 menit)
- Tunjukkan progress scraping
- Tunjukkan data yang berhasil diambil
- **Tunjukkan SUMMARY AKHIR:**
  ```
  [OK] LEPKOM        : 1 data
  [OK] KEMAHASISWAAN : 1 data
  [OK] STUDENTSITE   : 1 data
  [OK] BAAK          : 1 data
  [OK] PENDAFTARAN   : 1 data
  
  Total website berhasil : 5/5
  Total data ditemukan   : 5
  ```

### Show Database (1 menit)
```sql
SELECT judul, tanggal, sumber FROM pengumuman LIMIT 10;
```
"Data disimpan di MySQL dengan deteksi duplikat otomatis."

### Show Discord (30 detik)
"Notifikasi otomatis ke Discord channel untuk pengumuman baru."

### Explain Features (1 menit)
- Error isolation (satu gagal, lanjut berikutnya)
- Retry mechanism (max 2x)
- Timeout control (tidak hanging)
- Summary akhir (selalu muncul meskipun ada error)
- Monitoring berkala (60 menit)

### Closing (30 detik)
"Sistem sudah production-ready dengan dokumentasi lengkap, error handling robust, dan testing yang comprehensive."

**Total:** ~7-8 menit

---

## 📊 Expected Test Output

### Command:
```bash
py test_scraper.py --fast all
```

### Output Structure:
```
============================================================
  TEST SCRAPER - SISTEM AGREGASI PENGUMUMAN GUNADARMA
============================================================
  Python  : 3.12.0
  Mode    : FAST (1 item per website)
  Target  : all (semua)
  Website : lepkom, kemahasiswaan, studentsite, baak, pendaftaran

[Progress scraping LEPKOM...]
[OK]  LEPKOM: 1 pengumuman berhasil diambil.

[Progress scraping KEMAHASISWAAN...]
[OK]  KEMAHASISWAAN: 1 pengumuman berhasil diambil.

[Progress scraping STUDENTSITE...]
[OK]  STUDENTSITE: 1 pengumuman berhasil diambil.

[Progress scraping BAAK...]
[OK]  BAAK: 1 pengumuman berhasil diambil.

[Progress scraping PENDAFTARAN...]
[OK]  PENDAFTARAN: 1 pengumuman berhasil diambil.

============================================================
  SUMMARY TEST SCRAPER
============================================================

  [OK] LEPKOM          : 1 data
  [OK] KEMAHASISWAAN   : 1 data
  [OK] STUDENTSITE     : 1 data
  [OK] BAAK            : 1 data
  [OK] PENDAFTARAN     : 1 data

------------------------------------------------------------
  Total website berhasil : 5/5
  Total data ditemukan   : 5

============================================================
  TEST SELESAI
============================================================
```

---

## 🎓 Q&A Preparation

### Q: Kenapa BAAK kadang timeout?
**A:** "BAAK dilindungi Cloudflare Managed Challenge yang kadang butuh >120 detik. Sistem sudah dioptimasi untuk ambil data dari halaman list, sehingga tidak perlu buka halaman detail yang lebih lambat."

### Q: Bagaimana jika struktur website berubah?
**A:** "Sistem menyimpan debug HTML otomatis. Developer tinggal inspeksi selector CSS baru dari debug HTML dan update kode scraper."

### Q: Apakah scraping legal?
**A:** "Ya, untuk keperluan akademik (Penulisan Ilmiah) dan data publik. Sistem juga sudah diberi jeda antar request agar tidak membebani server."

### Q: Bagaimana error handling?
**A:** "Sistem punya 3 layer: retry otomatis (max 2x), fallback strategy (FlareSolverr → Playwright), dan error isolation (satu gagal, lanjut berikutnya). Summary akhir selalu menampilkan berapa yang berhasil dan gagal."

### Q: Kenapa tidak pakai API resmi?
**A:** "Website Universitas Gunadarma tidak menyediakan API publik untuk pengumuman. Scraping adalah satu-satunya cara untuk mengakses data secara otomatis."

### Q: Bagaimana monitoring berkala?
**A:** "Program utama (main.py) melakukan initial scraping untuk baseline data, kemudian monitoring setiap 60 menit. Jika ada pengumuman baru (belum ada di database), otomatis kirim notifikasi ke Discord."

---

## 📁 Important Files

- **test_scraper.py** - Script testing (NEW: summary akhir)
- **main.py** - Program utama (initial + monitoring)
- **README.md** - Overview project
- **TESTING_GUIDE.md** - Panduan testing lengkap
- **STATUS_SUMMARY.md** - Status project
- **UPDATE_LOG.md** - Log perubahan terbaru
- **PROGRESS_REPORT.md** - Laporan progress
- **QUICK_START.md** - File ini (quick reference)

---

## 🔧 Troubleshooting

### Issue: FlareSolverr tidak running
```bash
docker run -d --name flaresolverr -p 8191:8191 ghcr.io/flaresolverr/flaresolverr:latest
```

### Issue: FlareSolverr "Error solving challenge"
```bash
docker restart flaresolverr
# Tunggu 10 detik
py test_scraper.py --fast all
```

### Issue: Database connection error
```bash
# Cek .env file
type .env
# Pastikan DB_HOST, DB_USER, DB_PASSWORD benar
```

### Issue: Python import error
```bash
pip install -r requirements.txt
```

### Issue: Unicode error di terminal
```bash
chcp 65001
py test_scraper.py --fast all
```

---

## ✅ System Status

**Last Test:** 22 Juni 2026, 12:51 PM  
**Test Command:** `py test_scraper.py --fast all`  
**Result:** ✅ 5/5 website berhasil  
**Time:** ~2.5 menit  
**Data:** 5 pengumuman (1 per website)

**Conclusion:** ✅ **SISTEM STABIL DAN SIAP DEMO**

---

**Tips untuk Demo:**
1. Siapkan terminal window yang besar agar output jelas
2. Jalankan `py test_scraper.py --fast all` sebelum demo untuk warmup
3. Jika ada yang tanya detail, buka log file `logs/sistem_YYYYMMDD.log`
4. Jika ada yang tanya database, siapkan query SQL di MySQL Workbench
5. Jika ada yang tanya Discord, siapkan screenshot notifikasi

**Good luck dengan demo dan Penulisan Ilmiah! 🎓**

