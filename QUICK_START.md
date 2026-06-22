# Quick Start - Sistem Agregasi Pengumuman

**Last Update:** 22 Juni 2026, 12:55 PM  
**Status:** ✅ READY FOR DEMO

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

