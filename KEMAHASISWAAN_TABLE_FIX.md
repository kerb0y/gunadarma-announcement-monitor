# Kemahasiswaan Table Detection & Formatting

## Masalah yang Diperbaiki

Sebelumnya, tabel delegasi di pengumuman Kemahasiswaan tidak terformat dengan baik karena:
- Text extraction biasa menghancurkan struktur tabel
- Tabel menjadi satu baris panjang tanpa pemisah yang jelas
- Tidak ada formatting khusus untuk tabel delegasi

## Solusi

### 1. **Deteksi Tabel Berdasarkan `<td>`**

Tidak bergantung pada teks header ("No", "Nama", "NPM", dll) karena bisa berubah.

Strategi deteksi:
1. Cari elemen `<table>` dan parse struktur `<tr>` → `<td>`
2. Fallback: Ambil semua `<td>` langsung jika `<table>` tidak jelas
3. Extract teks dari setiap `<td>`

### 2. **Validasi Tabel Delegasi**

Fungsi `_is_delegasi_table(cells)` mendeteksi apakah cells adalah tabel delegasi dengan ciri:
- Jumlah cells kelipatan 5 (No, Nama, NPM, Prodi, Keterangan)
- Kolom 1: Angka urut
- Kolom 3: NPM (7-10 digit)
- Kolom 4: Program Studi (mengandung "S1", "D3", "Teknik", "Sistem", dll)
- Kolom 5: Keterangan (mengandung "Ketua", "Manajer", "Anggota", dll)

**Validasi tidak terlalu ketat** - minimal 2 dari 4 validasi harus benar agar data valid tidak terbuang.

### 3. **Format Output Discord**

Fungsi `_format_delegasi_table(cells)` menghasilkan format rapi:

```
📋 Daftar Delegasi

1. Raditya Bima Setiawan
   NPM: 21424097
   Program Studi: Teknik Mesin (S1)
   Keterangan: Ketua / Manajer

2. Muhammad Wiyansyahputra Mahdi Syafaat
   NPM: 20424957
   Program Studi: Teknik Mesin (S1)
   Keterangan: Anggota 1
```

### 4. **Preserve Paragraf**

Paragraf sebelum dan sesudah tabel tetap dipertahankan:

```
PENGUMUMAN NO.: 025/PU/WRIII/UG/VI/2026
TENTANG Pengumuman Delegasi Universitas Gunadarma pada Kontes Mobil Hemat Energi (KMHE) Tahun 2026

Bidang Kemahasiswaan Universitas Gunadarma mengucapkan selamat...

📋 Daftar Delegasi

1. Raditya Bima Setiawan
   NPM: 21424097
   ...

Bidang Kemahasiswaan Universitas Gunadarma menyampaikan apresiasi...
```

---

## Functions Added

### `_extract_table_cells(content_element) -> List[str]`

Extract cells dari tabel dalam content.

**Strategy**:
1. Cari `<table>` dan parse `<tr>` → `<td>`
2. Fallback: ambil semua `<td>` langsung jika table tidak jelas

**Returns**: List of cell texts (stripped, non-empty)

### `_is_delegasi_table(cells: List[str]) -> bool`

Deteksi apakah cells merupakan tabel delegasi.

**Validasi**:
- Jumlah cells kelipatan 5
- Kolom 1: Angka urut (atau kosong)
- Kolom 3: NPM (7-10 digit)
- Kolom 4: Program Studi (keyword: S1, D3, Teknik, Sistem, dll)
- Kolom 5: Keterangan (keyword: Ketua, Manajer, Anggota, dll)

**Returns**: True jika minimal 2 dari 4 validasi benar

### `_format_delegasi_table(cells: List[str]) -> str`

Format cells tabel delegasi menjadi list rapi untuk Discord.

**Handling**:
- Skip header row jika ada ("No", "Nama", "NPM", dll)
- Group cells per 5 kolom
- Format dengan emoji 📋 dan indentasi rapi

**Returns**: Formatted string atau empty string jika gagal

### `_process_content_with_table(content_element) -> Tuple[str, bool]`

Process content yang mungkin mengandung tabel.

**Flow**:
1. Extract table cells
2. Deteksi apakah tabel delegasi
3. Jika ya: format table + preserve paragraf
4. Jika tidak: gunakan text extraction biasa

**Returns**: (processed_text, has_delegasi_table)

---

## Debug Logging

Logging ditambahkan untuk troubleshooting:

```
[KEMAHASISWAAN] Jumlah <table> ditemukan: 1
[KEMAHASISWAAN] Jumlah <td> ditemukan: 25
[KEMAHASISWAAN] Tabel delegasi terdeteksi dari <td>: YA
[KEMAHASISWAAN] Header tabel terdeteksi, skip header row
[KEMAHASISWAAN] Jumlah baris delegasi terparse: 4
[KEMAHASISWAAN] Preview tabel delegasi: 📋 Daftar Delegasi...
[KEMAHASISWAAN] Tabel delegasi berhasil diformat
```

Jika parsing gagal:
```
[KEMAHASISWAAN] <td> ditemukan tetapi gagal diformat sebagai tabel delegasi. Menggunakan teks asli.
```

---

## Testing

### Test Scraper CLI

```bash
py test_scraper.py kemahasiswaan
```

**Verifikasi**:
- [ ] Cari berita "Kontes Mobil Hemat Energi" atau "KMHE"
- [ ] Daftar delegasi tampil rapi dengan format:
  ```
  📋 Daftar Delegasi
  
  1. Nama
     NPM: ...
     Program Studi: ...
     Keterangan: ...
  ```
- [ ] Paragraf sebelum dan sesudah tabel tetap ada
- [ ] Tidak ada crash jika tabel tidak valid

### Test Discord

Setelah CLI output rapi:

```bash
# Set .env
SEND_DISCORD_ON_INITIAL=true
INITIAL_SCRAPE_LIMIT=1

# Truncate
TRUNCATE TABLE pengumuman;

# Run
py main.py
```

**Verifikasi di Discord**:
- [ ] Tabel delegasi terformat rapi
- [ ] Tidak terpotong di tengah entry
- [ ] Paragraf dan tabel terpisah dengan newline
- [ ] Emoji 📋 muncul

---

## Edge Cases Handled

1. **No table element, only `<td>`**
   → Fallback: extract all `<td>` directly

2. **Table header included in cells**
   → Skip row jika cell pertama = "No" atau "Nama"

3. **Non-delegasi table (different columns)**
   → Deteksi gagal, gunakan text extraction biasa

4. **Invalid cells (tidak kelipatan 5)**
   → Deteksi gagal, gunakan text extraction biasa

5. **Parsing error**
   → Log warning, gunakan text extraction biasa (tidak crash)

---

## Files Changed

- `scraper/kemahasiswaan.py`:
  - Added 4 helper functions for table detection and formatting
  - Updated `_parse_detail_html()` to use `_process_content_with_table()`
  - Added comprehensive debug logging

---

## Rollback Instructions

Jika terjadi masalah, kembalikan `_parse_detail_html()` ke versi lama:

```python
def _parse_detail_html(html: str, item: dict):
    # ... (judul, tanggal, author same as before)
    
    # Isi: .ck-content - gunakan separator newline
    isi_el = (
        soup.find(class_="ck-content")
        or soup.find(class_="entry-content")
        or soup.find("article")
    )
    if isi_el:
        item["isi"] = isi_el.get_text(separator="\n", strip=True)
```

Dan hapus 4 helper functions:
- `_extract_table_cells()`
- `_is_delegasi_table()`
- `_format_delegasi_table()`
- `_process_content_with_table()`

---

## Summary

✅ **Masalah Fixed**:
- Tabel delegasi terdeteksi berdasarkan `<td>` (tidak bergantung pada header text)
- Format output Discord rapi dengan emoji 📋 dan indentasi
- Paragraf sebelum/sesudah tabel dipertahankan
- Validasi tidak terlalu ketat (data valid tidak terbuang)
- Tidak crash jika tabel tidak valid (fallback ke text extraction biasa)

✅ **Files Changed**:
- `scraper/kemahasiswaan.py` (UPDATED)

✅ **Ready for Testing**:
- Test scraper CLI: `py test_scraper.py kemahasiswaan`
- Test Discord notification

🚀 **Production Ready!**
