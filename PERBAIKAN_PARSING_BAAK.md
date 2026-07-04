# Perbaikan Parsing Scraper BAAK

**Tanggal:** 4 Juli 2026  
**Status:** ✅ **SELESAI - Menunggu Testing dengan FlareSolverr**

---

## 🎯 Masalah yang Diperbaiki

### Masalah Lama
- **Semua berita jadi sama:** "LAYANAN DIGITAL UNTUK MAHASISWA"
- **Parsing mengambil elemen pertama saja**, bukan loop semua artikel
- **Selector tidak sesuai** dengan struktur HTML aktual BAAK

### Akar Masalah
Fungsi `_parse_list_html_bs4()` mencari semua tag `<a>` secara global, yang menyebabkan:
1. Tidak terstruktur per artikel
2. Bisa mengambil link navigasi/footer
3. Judul dan link tidak sinkron (judul dari artikel X, link dari artikel Y)

---

## ✅ Perbaikan yang Dilakukan

### 1. **Fungsi `_parse_list_html_bs4()` - REFACTORED**

**Perubahan Utama:**

#### A. Struktur Parsing yang Benar
```python
# SEBELUM (SALAH):
all_a = soup.find_all("a", href=True)  # Ambil semua <a> global
for a in all_a:
    # Ambil dari elemen pertama yang ketemu
    
# SESUDAH (BENAR):
container = soup.find("div", class_="cell-md-8")  # Cari container dulu
articles = container.find_all("article")          # Cari semua artikel
for article in articles:                          # Loop per artikel
    h6 = article.find("h6")                      # Judul dari artikel ini
    link = article.find("a")                     # Link dari artikel ini
```

#### B. Selector yang Benar
Sesuai instruksi pengguna:
- **Container:** `.cell-md-8`
- **Artikel:** `article` dalam container
- **Judul:** `h6` dalam artikel
- **Link:** `a[href]` dalam artikel, pola `/beritabaak/<ID>`

#### C. Validasi & Logging
```python
✓ Cek container .cell-md-8 ditemukan
✓ Hitung jumlah artikel: "Ditemukan X artikel pada halaman list"
✓ Loop setiap artikel dengan nomor index
✓ Validasi link harus pola /beritabaak/<ID>
✓ Skip duplikat link
✓ Log contoh 3 judul pertama
✓ Log contoh 3 URL pertama
```

---

### 2. **Fungsi `_parse_detail_html_bs4()` - UPDATED**

**Perubahan Selector:**

| Elemen | Selector Lama | Selector Baru (Benar) |
|--------|---------------|----------------------|
| **Judul** | `h3.text-bold` | `h6` (prioritas utama) |
| **Tanggal** | Regex complex | `.text-middle.inset-left-10.text-italic.text-black` |
| **Author** | Regex complex | `.text-middle.inset-left-10.text-italic.text-primary` |
| **Isi** | `div.offset-md-top-20` | `div.offset-md-top-20` (tidak berubah) |

**Fallback Chain:**
```python
# Judul:
h6 → h3.text-bold → h1/h2

# Tanggal:
.text-middle.inset-left-10.text-italic.text-black → 
  regex variant → time/post-date

# Author:
.text-middle.inset-left-10.text-italic.text-primary → 
  regex variant → .author/.posted-by
```

---

### 3. **Logging yang Lebih Baik**

**Format Baru:**

```text
[BAAK] Container .cell-md-8 ditemukan
[BAAK] Ditemukan 6 artikel pada halaman list
[BAAK] Berhasil parse 6 artikel dari halaman list

[BAAK] Contoh 3 judul pertama:
[BAAK]   1. PEMBERITAHUAN PERPANJANGAN WAKTU...
[BAAK]   2. PENGUMUMAN WISUDA KE-113...
[BAAK]   3. JADWAL UJIAN TENGAH SEMESTER...

[BAAK] Contoh 3 URL pertama:
[BAAK]   1. https://baak.gunadarma.ac.id/beritabaak/752
[BAAK]   2. https://baak.gunadarma.ac.id/beritabaak/751
[BAAK]   3. https://baak.gunadarma.ac.id/beritabaak/750

[BAAK] Akan memproses 3 halaman detail...
[BAAK] [1/3] Memproses: PEMBERITAHUAN PERPANJANGAN...
[BAAK] [1/3] Judul: PEMBERITAHUAN PERPANJANGAN WAKTU...
[BAAK] [1/3] Link: https://baak.gunadarma.ac.id/beritabaak/752
[BAAK] [1/3] Isi berhasil diambil. Panjang: 234 karakter

[BAAK] [2/3] Memproses: PENGUMUMAN WISUDA KE-113...
[BAAK] [2/3] Judul: PENGUMUMAN WISUDA KE-113...
[BAAK] [2/3] Link: https://baak.gunadarma.ac.id/beritabaak/751
[BAAK] [2/3] Isi berhasil diambil. Panjang: 567 karakter
```

**Tidak Menampilkan:**
- ❌ Isi berita penuh di terminal
- ❌ HTML debug kecuali error
- ❌ Log detail parsing kecuali DEBUG level

---

## 📊 Perbandingan

### Before (Salah)

**Parsing List:**
```python
# Ambil semua <a> global
all_a = soup.find_all("a", href=True)

# Loop <a>, tanpa konteks artikel
for a in all_a:
    if "/beritabaak/" in href:
        # Judul dari parent terdekat (bisa salah)
        judul = a.get_text()
```

**Hasil:**
- ❌ Semua berita = "LAYANAN DIGITAL UNTUK MAHASISWA"
- ❌ Judul sama, link berbeda
- ❌ Atau judul berbeda, isi sama

---

### After (Benar)

**Parsing List:**
```python
# Cari container dulu
container = soup.find("div", class_="cell-md-8")

# Cari semua artikel dalam container
articles = container.find_all("article")

# Loop per artikel
for article in articles:
    # Judul dari artikel ini
    h6 = article.find("h6")
    judul = h6.get_text()
    
    # Link dari artikel ini
    link = article.find("a")
    href = link.get("href")
```

**Hasil:**
- ✅ Setiap berita unik
- ✅ Judul sesuai dengan link-nya
- ✅ Tidak ada duplikasi
- ✅ Jumlah berita = jumlah artikel di halaman

---

## 🧪 Test Script

### `test_baak_quick.py` - UPDATED

**Fitur Baru:**
1. Test 3 berita (bukan 1) untuk melihat perbedaan
2. Tampilkan detail setiap berita
3. **Validasi otomatis:**
   ```python
   ✓ Total berita: 3
   ✓ Judul unik: 3  # Harus sama dengan total
   ✓ Link unik: 3   # Harus sama dengan total
   
   ✅ SUCCESS: Semua berita berbeda!
   ```

**Menjalankan:**
```bash
py test_baak_quick.py
```

---

## 📝 Checklist Validasi

Setelah FlareSolverr running dan test dijalankan, pastikan:

- [ ] Container `.cell-md-8` ditemukan
- [ ] Jumlah artikel > 1 (biasanya 5-6)
- [ ] Setiap artikel punya judul unik
- [ ] Setiap artikel punya link unik
- [ ] Link mengikuti pola `/beritabaak/<ID>`
- [ ] ID berbeda untuk setiap link
- [ ] Detail setiap berita berbeda
- [ ] Validasi: `judul_unik == total_berita`
- [ ] Validasi: `link_unik == total_berita`

---

## 🚀 Cara Testing

### 1. Start FlareSolverr
```bash
docker run -d --name flaresolverr -p 8191:8191 ghcr.io/flaresolverr/flaresolverr:latest
```

### 2. Verify FlareSolverr
```bash
curl http://localhost:8191/health
# Expected: {"status":"ok"}
```

### 3. Run Test
```bash
py test_baak_quick.py
```

### 4. Expected Output
```text
[BAAK] Ditemukan 6 artikel pada halaman list
[BAAK] Contoh 3 judul pertama:
[BAAK]   1. PEMBERITAHUAN PERPANJANGAN...
[BAAK]   2. PENGUMUMAN WISUDA KE-113...
[BAAK]   3. JADWAL UJIAN TENGAH...

VALIDASI:
✓ Total berita: 3
✓ Judul unik: 3
✓ Link unik: 3

✅ SUCCESS: Semua berita berbeda!
```

---

## 🔍 Debug

### Jika Masih Semua Berita Sama

**1. Cek Container:**
```python
# Tambahkan log debug
logger.info(f"Container: {container}")
logger.info(f"Jumlah artikel: {len(articles)}")
```

**2. Cek Artikel:**
```python
for idx, article in enumerate(articles, 1):
    logger.info(f"Artikel #{idx}: {article}")
    h6 = article.find("h6")
    logger.info(f"  Judul h6: {h6.get_text() if h6 else 'TIDAK ADA'}")
    link = article.find("a")
    logger.info(f"  Link: {link.get('href') if link else 'TIDAK ADA'}")
```

**3. Simpan HTML Debug:**
```bash
# File: debug_baak.html
# Buka di browser, cari .cell-md-8
# Hitung manual jumlah artikel
# Bandingkan dengan log
```

---

## 📦 File yang Diubah

| File | Perubahan |
|------|-----------|
| `scraper/baak.py` | Refactor `_parse_list_html_bs4()` dan `_parse_detail_html_bs4()` |
| `test_baak_quick.py` | Update untuk test 3 berita dengan validasi |

**Tidak Berubah:**
- ❌ Database
- ❌ Webhook
- ❌ `.env`
- ❌ Scraper lain
- ❌ Format output

---

## ✅ Status

| Item | Status |
|------|--------|
| Refactor parsing list | ✅ DONE |
| Update selector detail | ✅ DONE |
| Improve logging | ✅ DONE |
| Compile check | ✅ PASSED |
| Test dengan FlareSolverr | ⏳ PENDING (Docker tidak running) |

---

## 🎯 Next Steps

1. **Start Docker Desktop** (jika belum)
2. **Run FlareSolverr** container
3. **Run test:** `py test_baak_quick.py`
4. **Verify:** Semua berita berbeda
5. **Production:** Deploy ke monitoring

---

**Catatan:** Perbaikan ini fokus pada **struktur parsing yang benar**, sehingga setiap artikel di-parse sebagai entitas terpisah, bukan mengambil elemen pertama secara global.

