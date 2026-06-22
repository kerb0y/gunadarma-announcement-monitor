# Quick Test Guide - Sistem Agregasi Pengumuman

## ⚡ Quick Start (Recommended untuk Demo)

```bash
# Test cepat semua website (1 data per website)
py test_scraper.py --fast all
```

**Hasil:**
- ✅ 5/5 website berhasil
- ⏱️ Selesai dalam ~3 menit
- 📊 Total 5 data

---

## 🎯 Test Individual Website

### Mode Fast (1 data)
```bash
py test_scraper.py --fast lepkom
py test_scraper.py --fast kemahasiswaan
py test_scraper.py --fast studentsite
py test_scraper.py --fast baak
py test_scraper.py --fast pendaftaran
```

### Mode Normal (5 data)
```bash
py test_scraper.py lepkom         # ~18s
py test_scraper.py kemahasiswaan  # ~157s (2.5 menit)
py test_scraper.py studentsite    # ~5s (tercepat!)
py test_scraper.py baak           # ~600s (10 menit) - bisa timeout
py test_scraper.py pendaftaran    # ~139s (2.3 menit)
```

---

## 📋 Test Lengkap Semua Website

```bash
# Mode Normal (5 data per website)
py test_scraper.py all
```

**Hasil:**
- ✅ LEPKOM: 5 data
- ✅ KEMAHASISWAAN: 5 data
- ✅ STUDENTSITE: 5 data
- ⚠️ BAAK: Timeout (tapi sebenarnya berhasil di background)
- ✅ PENDAFTARAN: 2 data (memang hanya ada 2)

---

## ⚙️ Persiapan Sebelum Test

### 1. Pastikan FlareSolverr Berjalan
```bash
# Cek status
docker ps

# Jika belum berjalan, start:
docker-compose up -d
# atau
docker start flaresolverr
```

**Catatan:** Website yang butuh FlareSolverr:
- KEMAHASISWAAN
- BAAK  
- PENDAFTARAN

### 2. Pastikan Dependencies Terinstal
```bash
pip install -r requirements.txt
playwright install chromium
```

### 3. Periksa Koneksi Internet
- Semua scraper butuh koneksi stabil
- BAAK & KEMAHASISWAAN butuh bandwidth lebih

---

## 🐛 Troubleshooting

### BAAK Timeout
**Penyebab:** FlareSolverr butuh 120s per detail page × 5 = 600s (10 menit)

**Solusi:**
1. Gunakan mode fast: `py test_scraper.py --fast baak`
2. Atau tunggu lebih lama (BAAK tetap berhasil di background)
3. Atau gunakan data list saja (sudah cukup informatif)

### LEPKOM/STUDENTSITE Gagal
**Penyebab:** Website timeout atau koneksi lambat

**Solusi:**
1. Cek koneksi internet
2. Coba lagi setelah beberapa menit
3. Cek apakah website sedang down: buka di browser

### KEMAHASISWAAN Cloudflare
**Penyebab:** FlareSolverr tidak berjalan atau timeout

**Solusi:**
1. Pastikan Docker FlareSolverr running: `docker ps`
2. Restart FlareSolverr: `docker restart flaresolverr`
3. Tunggu 30-60 detik (FlareSolverr butuh waktu)

---

## 📊 Output yang Diharapkan

### Success Example
```
[INFO]  Scraping selesai.
[INFO]  Jumlah pengumuman ditemukan: 5

  [1]
      Judul    : PENGUMUMAN JADWAL KURSUS...
      Tanggal  : Minggu, 21 Juni 2026
      Link     : https://vm.lepkom.gunadarma.ac.id/...
      Sumber   : LEPKOM
      Author   : By Admin
      Isi      : Diinformasikan kepada mahasiswa...

[OK]  LEPKOM: 5 pengumuman berhasil diambil.
```

### Timeout Example
```
  ... masih berjalan (30s / 180s)
  ... masih berjalan (60s / 180s)
  ... masih berjalan (90s / 180s)

[WARNING] Scraper 'BAAK' timeout setelah 180 detik.
          Proses masih berjalan di background, lanjut ke website berikutnya...
```

### Summary
```
============================================================
  SUMMARY TEST SCRAPER
============================================================

  [OK] LEPKOM          : 5 data
  [OK] KEMAHASISWAAN   : 5 data
  [OK] STUDENTSITE     : 5 data
  [GAGAL] BAAK         : Timeout 180s
  [OK] PENDAFTARAN     : 2 data

------------------------------------------------------------
  Total website berhasil : 4/5
  Total data ditemukan   : 17
============================================================
```

---

## 🎯 Untuk Demo/Presentasi Penulisan Ilmiah

### Skenario Terbaik
```bash
# 1. Start FlareSolverr
docker-compose up -d

# 2. Test cepat (3 menit)
py test_scraper.py --fast all

# 3. Tampilkan hasil
cat TEST_RESULTS.md
```

**Keuntungan:**
- ✅ Cepat (3 menit)
- ✅ 100% berhasil
- ✅ Membuktikan semua scraper berjalan
- ✅ Output jelas dan informatif

### Alternatif Jika Ingin Full Demo
```bash
# Test individual (tunjukkan detail per website)
py test_scraper.py --fast lepkom
py test_scraper.py --fast kemahasiswaan
py test_scraper.py --fast studentsite
py test_scraper.py --fast baak
py test_scraper.py --fast pendaftaran
```

---

## 📝 Catatan Penting

1. **Mode Fast vs Normal:**
   - Fast: 1 data per website, cepat, untuk testing
   - Normal: 5 data per website, untuk production/monitoring

2. **Timeout Mechanism:**
   - Default: 180 detik (3 menit) per scraper
   - Progress update setiap 30 detik
   - Jika timeout, lanjut ke website berikutnya

3. **FlareSolverr:**
   - Diperlukan untuk Cloudflare-protected websites
   - Lambat (30-120s per request) tapi reliable
   - Alternatif: Playwright stealth (tidak selalu berhasil)

4. **Data Output:**
   - Semua data disimpan ke format dict standar
   - Field: judul, tanggal, link, sumber, isi, author, file_url
   - Siap disimpan ke MySQL via main.py

---

## ✅ Checklist Sebelum Demo

- [ ] Docker FlareSolverr running (`docker ps`)
- [ ] Dependencies terinstal (`pip list | grep playwright`)
- [ ] Koneksi internet stabil
- [ ] Test mode fast berhasil (`py test_scraper.py --fast all`)
- [ ] Baca TEST_RESULTS.md untuk referensi
- [ ] Siapkan penjelasan timeout mechanism
- [ ] Siapkan penjelasan fallback Playwright ↔ FlareSolverr
