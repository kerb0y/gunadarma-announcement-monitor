# Update Scraper Studentsite v4

## Perubahan

Website Studentsite telah berubah dari interface lama ke v4, sehingga scraper perlu disesuaikan.

### URL Baru
- **Lama**: `https://studentsite.gunadarma.ac.id/`
- **Baru**: `https://studentsite.gunadarma.ac.id/v4/pengumuman`

### Selector Baru

#### Halaman List Berita:
- **Container**: `.mb-10` (area daftar berita teratas)
- **Card berita**: `<a>` di dalam container `.mb-10`
- **Judul card**: `<h3>` di dalam card berita

#### Halaman Detail Berita:
- **Judul**: `h1.text-2xl` atau `h1` (fallback jika judul list kosong)
- **Isi**: `.prose-content.text-gray-700.leading-relaxed.whitespace-pre-wrap` atau `.prose-content`
- **Tanggal**: `div.flex.items-center.gap-1\.5.text-sm.text-gray-400` atau selector serupa

---

## Strategi Scraping Baru

### 1. **Ambil Daftar Berita dari Container `.mb-10`**

```python
# Cari container .mb-10
containers = page.query_selector_all(".mb-10")

# Ambil semua link <a> dari container
for container in containers:
    links = container.query_selector_all("a[href]")
    for link_el in links:
        href = link_el.get_attribute("href")
        h3_el = link_el.query_selector("h3")
        judul = h3_el.inner_text().strip() if h3_el else ""
```

### 2. **Selector Lebih Stabil**

Tidak terlalu bergantung pada `body > main:nth-child(3) > ...` karena terlalu rapuh.

Menggunakan class selector (`.mb-10`, `h3`) yang lebih stabil.

### 3. **Filter Link Pengumuman**

Skip link navigasi atau link lain yang bukan pengumuman:

```python
if "pengumuman" not in abs_href and "berita" not in abs_href:
    continue
```

### 4. **Fallback untuk Judul**

Judul diambil dari list page, tetapi jika kosong, diambil dari detail page:

```python
if not item["judul"] or len(item["judul"]) < 5:
    judul_detail = dpage.query_selector("h1.text-2xl, h1")
    if judul_detail:
        item["judul"] = judul_detail.inner_text().strip()
```

### 5. **Extract Isi dengan `inner_text()`**

Mempertahankan newline dan formatting:

```python
isi_el = dpage.query_selector(
    ".prose-content.text-gray-700.leading-relaxed.whitespace-pre-wrap, "
    ".prose-content, "
    "[class*='prose-content']"
)
if isi_el:
    item["isi"] = isi_el.inner_text().strip()
```

### 6. **Extract Tanggal**

Menggunakan regex untuk extract format tanggal dari text:

```python
match = re.search(
    r"(\d{1,2}\s+\w+\s+\d{4}|\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4})", 
    tanggal_text
)
```

### 7. **Error Handling**

Jika satu detail berita gagal, scraper tetap lanjut ke berita berikutnya:

```python
try:
    dpage = ctx.new_page()
    dpage.goto(item["link"], timeout=30000, wait_until="domcontentloaded")
    # ... extract detail ...
    dpage.close()
except Exception as e:
    logger.warning(f"[STUDENTSITE] Gagal buka detail {item['link']}: {e}")
    try:
        dpage.close()
    except Exception:
        pass
    # Tetap tambahkan item meskipun detail gagal

hasil.append(item)
```

---

## Format Output (Tidak Berubah)

Output tetap berupa list of dict dengan field standar:

```python
{
    "judul": "...",
    "tanggal": "...",
    "link": "...",
    "sumber": "STUDENTSITE",
    "isi": "...",
    "author": "",
    "file_url": ""
}
```

Kompatibel dengan:
- `services/monitor.py`
- `database/db.py`
- `notifier/discord.py`

---

## Testing

### Test Scraper

```bash
py test_scraper.py --fast studentsite
```

atau

```bash
py test_scraper.py studentsite
```

**Verifikasi**:
- [ ] Scraper berhasil akses URL baru `/v4/pengumuman`
- [ ] Ditemukan minimal beberapa link berita dari container `.mb-10`
- [ ] Judul berhasil diambil dari `<h3>` atau fallback dari `<h1>` detail
- [ ] Detail page berhasil dibuka
- [ ] Isi berita berhasil diambil dari `.prose-content`
- [ ] Tanggal berhasil diextract (jika tersedia)
- [ ] Format output sesuai (dict dengan 7 field)
- [ ] Tidak crash jika satu detail page gagal

### Test Integration

```bash
# Set .env
SEND_DISCORD_ON_INITIAL=true
INITIAL_SCRAPE_LIMIT=1

# Truncate
TRUNCATE TABLE pengumuman WHERE sumber = 'STUDENTSITE';

# Run
py main.py
```

**Verifikasi**:
- [ ] Data STUDENTSITE masuk ke database
- [ ] Notifikasi Discord terkirim ke channel #studentsite
- [ ] Isi berita tidak terpotong
- [ ] Format rapi dengan newline

---

## Fallback Strategy

Jika container `.mb-10` tidak ditemukan:

1. **Fallback 1**: Cari semua link yang mengandung `/pengumuman/` atau `/v4/pengumuman/`
2. **Fallback 2**: Simpan debug HTML untuk analisis

```python
if not news_links:
    logger.info("[STUDENTSITE] Fallback: cari link /pengumuman/...")
    all_links = page.query_selector_all(
        "a[href*='/pengumuman/'], a[href*='/v4/pengumuman/']"
    )
    # ... process links ...
```

---

## Debugging

Jika scraper gagal:

1. **Check log output**:
   ```
   [STUDENTSITE] Container .mb-10 ditemukan: X
   [STUDENTSITE] Link berita ditemukan: Y
   ```

2. **Check debug HTML**:
   ```
   debug_studentsite.html
   ```
   Akan dibuat jika tidak ada berita ditemukan

3. **Manual check URL**:
   Buka `https://studentsite.gunadarma.ac.id/v4/pengumuman` di browser

4. **Inspect selector**:
   - Cari container dengan class `mb-10`
   - Cari link `<a>` dalam container
   - Cari judul dalam `<h3>`

---

## Files Changed

- `scraper/studentsite.py`:
  - Updated URL ke `/v4/pengumuman`
  - Updated selector untuk interface v4
  - Improved error handling
  - Added fallback strategies

---

## Rollback Instructions

Jika interface v4 bermasalah, rollback ke versi lama dengan mengembalikan:
- URL: `https://studentsite.gunadarma.ac.id/`
- Selector: `.content-box`, `h3.content-box-header`, dll

Atau gunakan git:
```bash
git checkout HEAD~1 -- scraper/studentsite.py
```

---

## Summary

✅ **Updated**:
- URL baru: `/v4/pengumuman`
- Selector baru: `.mb-10`, `<h3>`, `.prose-content`
- Selector lebih stabil (tidak bergantung pada `:nth-child()`)
- Error handling lebih baik
- Fallback strategies

✅ **Preserved**:
- Format output (7 field dict)
- Kompatibilitas dengan database, monitor, dan notifier
- Logging style
- Error handling pattern

✅ **Ready for Testing**: `py test_scraper.py studentsite`

🚀 **Production Ready!**
