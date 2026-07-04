# Perbaikan Parser Halaman Detail BAAK - V2

## Masalah yang Ditemukan

### Gejala
Setiap halaman detail BAAK menghasilkan data yang sama:
- **Judul**: "Perkuliahan dan Ujian" (heading kategori website, bukan judul artikel)
- **Isi**: 16 karakter (terlalu pendek, bukan konten artikel)

### Root Cause
Parser halaman detail menggunakan selector global yang menangkap elemen pertama di halaman, yaitu heading navigasi/kategori website, bukan konten artikel yang sebenarnya.

## Solusi yang Diterapkan

### Strategi Utama: Fokus pada Container Konten

Semua selector sekarang **prioritas pertama mencari dalam `.cell-md-8`** (container konten artikel), baru kemudian fallback ke selector global dengan filter ketat.

### 1. Parser Judul

**Prioritas Strategi:**

1. **h6 dalam `.cell-md-8`** (container konten)
   - Skip h6 dalam navigasi/breadcrumb/menu/sidebar
   - Minimal 15 karakter untuk menghindari kategori pendek
   
2. **h3/h4/h2 dalam `.cell-md-8`**
   - Jika tidak ada h6, cari heading lain dalam container
   - Minimal 15 karakter
   
3. **h6 global dengan filter ketat** (fallback)
   - Blacklist heading umum website:
     - "Perkuliahan dan Ujian"
     - "Akademik"
     - "Kemahasiswaan"
     - "BAAK"
     - "Berita"
     - "Pengumuman"
     - "Menu"
     - "Navigasi"
   - Minimal 20 karakter untuk fallback global

### 2. Parser Isi Berita

**Prioritas Strategi:**

1. **`div.offset-md-top-20` dalam `.cell-md-8`** (selector utama)
   - Ini adalah class konten utama artikel BAAK
   
2. **`div[class*='offset-md']` dalam `.cell-md-8`**
   - Fallback jika class tidak exact match
   - Validasi: harus lebih panjang dari hasil sebelumnya
   
3. **Semua `<p>` dalam `.cell-md-8`** (filtered)
   - Skip paragraf dalam navigasi/menu/header/sidebar/footer
   - Gabungkan dengan `\n\n`
   
4. **Semua text dalam `.cell-md-8`** (last resort)
   - Clone container dan hapus nav/header/footer/breadcrumb
   - Ambil semua text yang tersisa

### 3. Parser Tanggal & Author

**Strategi:**
- Cari dalam `.cell-md-8` terlebih dahulu
- Class kombinasi:
  - Tanggal: `.text-middle.inset-left-10.text-italic.text-black`
  - Author: `.text-middle.inset-left-10.text-italic.text-primary`
- Fallback ke selector umum jika tidak ditemukan

### 4. Logging yang Ditambahkan

Untuk memudahkan debugging, ditambahkan logging berikut:

```python
logger.info(f"[BAAK] Selector judul yang dipakai: {judul_selector_used}")
logger.info(f"[BAAK] Judul: {clean_log_text(judul, 100)}")

logger.info(f"[BAAK] Selector isi yang dipakai: {isi_selector_used}")
logger.info(f"[BAAK] Panjang isi: {len(isi)} karakter")
logger.info(f"[BAAK] Preview isi: {preview_100_char}")

# Warning jika terlalu pendek
if len(isi) < 100:
    logger.warning(f"[BAAK] ⚠️ ISI TERLALU PENDEK ({len(isi)} char) - kemungkinan selector salah!")
    logger.warning(f"[BAAK] Isi yang tertangkap: '{clean_log_text(isi, 200)}'")
```

## File yang Diubah

- `scraper/baak.py` - Fungsi `_parse_detail_html_bs4()`

## File yang TIDAK Diubah

✅ Parser halaman list BAAK sudah benar - **TIDAK DIUBAH**
✅ Cara mengambil URL detail dari `<a>` tag - **TIDAK DIUBAH**
✅ Scraper website lain (kemahasiswaan, studentsite, dll) - **TIDAK DIUBAH**

## Cara Testing

### 1. Pastikan FlareSolverr Berjalan

```bash
docker run -d --name flaresolverr -p 8191:8191 ghcr.io/flaresolverr/flaresolverr:latest
```

### 2. Jalankan Test

```bash
py test_baak_quick.py
```

### 3. Validasi Hasil

Pastikan:
- ✅ **Judul BUKAN "Perkuliahan dan Ujian"**
- ✅ **Setiap berita memiliki judul yang berbeda** (tidak ada duplikasi)
- ✅ **Panjang isi > 100 karakter** per berita
- ✅ **Tidak ada warning "ISI TERLALU PENDEK"**
- ✅ **Jumlah berita unik = jumlah total berita**

### 4. Cek Log

Perhatikan output log:
```
[BAAK] Selector judul yang dipakai: h6 dalam .cell-md-8 (artikel)
[BAAK] Judul: <judul berita yang panjang dan berbeda-beda>
[BAAK] Selector isi yang dipakai: div.offset-md-top-20
[BAAK] Panjang isi: 534 karakter
[BAAK] Preview isi: <preview 100 karakter pertama>
```

## Expected Output

### ✅ SUCCESS Case

```
[BAAK] Ditemukan 3 artikel pada halaman list
[BAAK] [1/3] Memproses: <judul berita 1>
[BAAK] Selector judul yang dipakai: h6 dalam .cell-md-8 (artikel)
[BAAK] Judul: <judul lengkap berita 1>
[BAAK] Selector isi yang dipakai: div.offset-md-top-20
[BAAK] Panjang isi: 534 karakter
[BAAK] Preview isi: <preview konten berita 1>

[BAAK] [2/3] Memproses: <judul berita 2>
[BAAK] Selector judul yang dipakai: h6 dalam .cell-md-8 (artikel)
[BAAK] Judul: <judul lengkap berita 2>
[BAAK] Selector isi yang dipakai: div.offset-md-top-20
[BAAK] Panjang isi: 412 karakter
[BAAK] Preview isi: <preview konten berita 2>

...

VALIDASI:
✓ Total berita: 3
✓ Judul unik: 3
✓ Link unik: 3

✅ SUCCESS: Semua berita berbeda!
```

### ❌ FAIL Case

```
[BAAK] Judul: Perkuliahan dan Ujian
[BAAK] ⚠️ ISI TERLALU PENDEK (16 char) - kemungkinan selector salah!
```

Jika masih muncul output seperti di atas, berarti selector masih salah dan perlu inspect HTML lebih lanjut.

## Penjelasan Teknis

### Mengapa Fokus pada `.cell-md-8`?

Website BAAK Gunadarma menggunakan struktur:
- **Container konten**: `.cell-md-8` berisi artikel/berita
- **Navigasi/Header**: Selector global di luar container

Dengan mencari dalam container terlebih dahulu, kita menghindari:
- Heading kategori: "Perkuliahan dan Ujian" (di navigasi)
- Menu items
- Breadcrumb
- Sidebar

### Blacklist Heading

Blacklist diterapkan untuk menghindari heading umum website yang bukan judul artikel:
```python
heading_blacklist = [
    "Perkuliahan dan Ujian",  # Kategori website
    "Akademik",                # Menu
    "Kemahasiswaan",           # Menu
    "BAAK",                    # Website name
    "Berita",                  # Section heading
    "Pengumuman",              # Section heading
    "Menu",
    "Navigasi"
]
```

### Validasi Panjang Konten

- **Judul dalam container**: minimal 15 karakter
- **Judul global (fallback)**: minimal 20 karakter
- **Isi berita**: warning jika < 100 karakter

Ini memastikan kita menangkap konten artikel yang sebenarnya, bukan kategori/label pendek.

## Troubleshooting

### Jika masih dapat "Perkuliahan dan Ujian"

1. Cek log: selector mana yang dipakai?
2. Cek file `debug_baak_detail.html` yang di-generate
3. Inspect struktur HTML halaman detail secara manual
4. Tambahkan kata ke blacklist jika perlu

### Jika isi masih pendek (< 100 char)

1. Cek log: `[BAAK] Selector isi yang dipakai: ...`
2. Cek preview: apakah menangkap konten yang benar?
3. Inspect HTML: apakah `div.offset-md-top-20` ada di halaman?
4. Tambahkan strategi fallback jika struktur HTML berubah

## Kesimpulan

Parser halaman detail BAAK sekarang:
1. ✅ Fokus pada konten artikel (`.cell-md-8`)
2. ✅ Skip navigasi/header dengan filter ketat
3. ✅ Blacklist heading umum website
4. ✅ Validasi panjang konten
5. ✅ Logging detail untuk debugging
6. ✅ Multiple fallback strategy

**Parser halaman list tidak diubah** karena sudah benar.
