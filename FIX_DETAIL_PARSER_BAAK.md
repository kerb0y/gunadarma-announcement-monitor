# Fix Parser Halaman Detail BAAK

**Tanggal:** 4 Juli 2026  
**Status:** ✅ **SELESAI - Ready for Testing**

---

## 🎯 Masalah yang Diperbaiki

### Masalah
- **Semua detail berita menangkap heading website**, bukan konten artikel
- Judul: "Perkuliahan dan Ujian" (heading kategori)
- Isi: 16 karakter (terlalu pendek)
- Selector menangkap elemen navigasi/header, bukan konten artikel

### Penyebab
- Selector `h6` global → mengambil h6 pertama (bisa dari navigasi)
- Selector `div.offset-md-top-20` tidak ditemukan atau kosong
- Tidak ada validasi panjang konten minimal

---

## ✅ Perbaikan yang Dilakukan

### Fokus: **HANYA Parser Halaman Detail**

**File yang diubah:**
- `scraper/baak.py` → Fungsi `_parse_detail_html_bs4()` ONLY

**Tidak diubah:**
- ❌ Parser halaman list (sudah benar)
- ❌ Cara mengambil URL detail (sudah benar)
- ❌ Scraper lain
- ❌ Database, webhook, .env

---

## 🔧 Perubahan Detail

### 1. **Judul - Multi-Strategy dengan Filter**

```python
# SEBELUM (SALAH):
judul_el = soup.find("h6")  # Ambil h6 pertama (bisa dari navigasi)

# SESUDAH (BENAR):
# Strategi 1: h6 dalam container konten (.cell-md-8)
content_container = soup.find("div", class_=re.compile(r"cell-md-8"))
if content_container:
    h6_el = content_container.find("h6")  # h6 dalam konten, bukan navigasi

# Strategi 2: Filter h6 - skip navigasi/header/menu
all_h6 = soup.find_all("h6")
for h6 in all_h6:
    # Skip jika parent = nav, header, menu, sidebar
    if h6.parent and "nav" not in parent_classes:
        # Dan judul harus > 10 karakter
        if len(text) > 10:
            judul = text
            break

# Strategi 3: Fallback h3.text-bold, h1, h2
```

**Logging:**
```python
logger.debug(f"[BAAK] Selector judul yang dipakai: {judul_selector_used}")
logger.debug(f"[BAAK] Judul result: {judul}")
```

---

### 2. **Isi Berita - Multi-Strategy dengan Validasi**

```python
# SEBELUM (SALAH):
isi_el = soup.find("div", class_="offset-md-top-20")
isi = isi_el.get_text()  # Tanpa validasi

# SESUDAH (BENAR):
# Strategi 1: div.offset-md-top-20
isi_el = soup.find("div", class_="offset-md-top-20")

# Strategi 2: div dengan class offset-md* (regex)
if not isi or len(isi) < 50:
    isi_el = soup.find("div", class_=re.compile(r"offset-md"))

# Strategi 3: Container .cell-md-8 → ambil semua <p>
if not isi or len(isi) < 50:
    content_container = soup.find("div", class_=re.compile(r"cell-md-8"))
    paragraphs = content_container.find_all("p")
    isi = "\n\n".join([p.get_text() for p in paragraphs])

# Strategi 4: Fallback post-content, article
if not isi or len(isi) < 50:
    isi_el = soup.find(class_="post-content") or soup.find("article")
```

**Validasi:**
```python
# Warning jika isi terlalu pendek
if len(isi) < 100:
    logger.warning(f"[BAAK] ISI TERLALU PENDEK ({len(isi)} char) - selector salah!")
    logger.warning(f"[BAAK] Isi: '{isi}'")
```

**Logging:**
```python
logger.debug(f"[BAAK] Selector isi yang dipakai: {isi_selector_used}")
logger.debug(f"[BAAK] Panjang isi: {len(isi)} karakter")
logger.debug(f"[BAAK] Preview isi: {isi[:100]}")
```

---

### 3. **Tanggal & Author - Improved Selector**

```python
# Class combination matching yang lebih akurat
for el in soup.find_all(class_=re.compile(r"text-middle")):
    classes = el.get("class", [])
    # Cek semua class harus ada
    if ("inset-left-10" in classes and 
        "text-italic" in classes and 
        "text-black" in classes):
        tgl_el = el
        break
```

---

## 📊 Logging Baru

### Level DEBUG (detail parsing)
```text
[BAAK] Selector judul yang dipakai: h6 dalam .cell-md-8
[BAAK] Judul result: PEMBERITAHUAN PERPANJANGAN WAKTU...
[BAAK] Selector isi yang dipakai: div.offset-md-top-20
[BAAK] Panjang isi: 234 karakter
[BAAK] Preview isi: Kepada seluruh mahasiswa Universitas Gunadarma, dengan ini kami sampaikan bahwa...
```

### Level WARNING (jika ada masalah)
```text
[WARNING] [BAAK] ISI TERLALU PENDEK (16 char) - kemungkinan selector salah!
[WARNING] [BAAK] Isi: 'Perkuliahan dan Ujian'
```

---

## 🧪 Testing

### Compile Check
```bash
py -m py_compile scraper/baak.py
```
✅ **PASSED**

### Test Scraper (saat FlareSolverr ready)
```bash
py test_baak_quick.py
```

### Expected Output

**BENAR (isi panjang):**
```text
[BAAK] [1/3] Judul: PEMBERITAHUAN PERPANJANGAN WAKTU...
[BAAK] [1/3] Link: https://baak.gunadarma.ac.id/beritabaak/752
[BAAK] [1/3] Isi berhasil diambil. Panjang: 234 karakter

[BAAK] [2/3] Judul: PENGUMUMAN WISUDA KE-113...
[BAAK] [2/3] Link: https://baak.gunadarma.ac.id/beritabaak/751
[BAAK] [2/3] Isi berhasil diambil. Panjang: 567 karakter
```

**SALAH (isi pendek - akan ada WARNING):**
```text
[BAAK] [1/3] Judul: Perkuliahan dan Ujian
[BAAK] [1/3] Link: https://baak.gunadarma.ac.id/beritabaak/752
[WARNING] [BAAK] ISI TERLALU PENDEK (16 char) - selector salah!
```

---

## ✅ Checklist Validasi

Saat test dengan FlareSolverr, pastikan:

**Judul:**
- [ ] Bukan "Perkuliahan dan Ujian" (heading website)
- [ ] Bukan heading navigasi/kategori
- [ ] Judul spesifik per berita
- [ ] Panjang > 10 karakter

**Isi:**
- [ ] Panjang > 100 karakter (minimal)
- [ ] Bukan hanya heading/kategori
- [ ] Konten lengkap artikel
- [ ] Berbeda per berita

**Setiap berita:**
- [ ] Judul unik
- [ ] Link unik
- [ ] Isi unik dan lengkap
- [ ] Tidak ada warning "ISI TERLALU PENDEK"

---

## 🎯 Strategi Selector

### Urutan Priority

**Judul:**
1. h6 dalam `.cell-md-8` (konten)
2. h6 yang bukan dalam nav/header (filter)
3. h3.text-bold
4. h1/h2

**Isi:**
1. `div.offset-md-top-20`
2. `div[class*='offset-md']` (regex)
3. `.cell-md-8` → semua `<p>`
4. `.post-content` atau `article`

### Validasi
- ✅ Panjang isi minimal 100 karakter
- ✅ Skip elemen dalam nav/header/menu
- ✅ Log selector yang dipakai
- ✅ Log preview isi

---

## 📝 Debug Helper

### Jika isi masih pendek/salah

**1. Cek log DEBUG:**
```bash
# Lihat selector mana yang dipakai
[BAAK] Selector isi yang dipakai: ...
[BAAK] Panjang isi: ...
[BAAK] Preview isi: ...
```

**2. Inspect HTML:**
```bash
# Buka debug_baak_detail.html (jika disimpan)
# Cari struktur konten artikel
# Cari selector yang benar
```

**3. Test manual:**
```python
from bs4 import BeautifulSoup

with open("debug_baak_detail.html") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")

# Test selector
isi_el = soup.find("div", class_="offset-md-top-20")
print(f"Found: {isi_el is not None}")
if isi_el:
    print(f"Length: {len(isi_el.get_text())}")
    print(f"Preview: {isi_el.get_text()[:100]}")
```

---

## 🚀 Next Steps

**Untuk testing:**

1. **Start FlareSolverr:**
   ```bash
   docker run -d --name flaresolverr -p 8191:8191 ghcr.io/flaresolverr/flaresolverr:latest
   ```

2. **Test scraper:**
   ```bash
   py test_baak_quick.py
   ```

3. **Verify hasil:**
   - Setiap berita punya judul berbeda
   - Setiap berita punya isi > 100 char
   - Tidak ada warning "ISI TERLALU PENDEK"

4. **Jika masih ada masalah:**
   - Cek log DEBUG
   - Lihat selector yang dipakai
   - Inspect HTML manual

---

## 📦 Summary

**Perubahan:**
- ✅ Parser detail: multi-strategy + filter + validasi
- ✅ Logging: selector used, panjang isi, preview
- ✅ Warning: jika isi < 100 char
- ✅ Compile: passed

**Tidak berubah:**
- ❌ Parser list (sudah benar)
- ❌ Cara dapat URL (sudah benar)
- ❌ Scraper lain
- ❌ Database/webhook/.env

**Status:** ✅ Ready for testing dengan FlareSolverr

---

**Key Improvement:** Parser detail sekarang fokus pada **konten artikel** dalam container, bukan heading/navigasi website global.

