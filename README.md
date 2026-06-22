# Sistem Agregasi Pengumuman Universitas Gunadarma

**Penulisan Ilmiah — Sistem Berbasis Python**

Sistem backend berbasis Python yang melakukan agregasi dan monitoring pengumuman dari 5 website resmi Universitas Gunadarma secara otomatis. Sistem ini melakukan scraping secara headless menggunakan Playwright, menyimpan data ke MySQL, mendeteksi pengumuman baru, dan mengirimkan notifikasi ke Discord melalui webhook.

---

## Fitur Utama

- **Headless Scraping** — Menggunakan Playwright (Chromium) untuk mengakses website secara otomatis tanpa membuka browser
- **Multi-Website** — Memonitor 5 website resmi Universitas Gunadarma sekaligus
- **Deteksi Pengumuman Baru** — Membandingkan hasil scraping terbaru dengan data di database
- **Penyimpanan MySQL** — Semua data tersimpan rapi di database MySQL dengan kolom `isi`, `author`, dan `file_url`
- **Notifikasi Discord** — Mengirim pesan otomatis ke Discord saat ada pengumuman baru
- **Monitoring Berkala** — Berjalan setiap 60 menit secara otomatis
- **Logging Lengkap** — Mencatat semua aktivitas ke console dan file log
- **Error Isolation** — Jika satu website gagal, scraper website lain tetap berjalan
- **Debug HTML** — Jika selector tidak cocok, HTML halaman disimpan ke `debug_<sumber>.html`

---

## Website yang Dimonitor

| No | Website       | URL                                                        |
|----|---------------|------------------------------------------------------------|
| 1  | LEPKOM        | https://vm.lepkom.gunadarma.ac.id/pengumuman               |
| 2  | Kemahasiswaan | https://kemahasiswaan.gunadarma.ac.id/                     |
| 3  | Studentsite   | https://studentsite.gunadarma.ac.id/                       |
| 4  | BAAK          | https://baak.gunadarma.ac.id/beritabaak                    |
| 5  | Pendaftaran   | https://pendaftaran.gunadarma.ac.id/2026/home/berita        |

---

## Struktur Folder

```
project/
│
├── main.py                  # Entry point utama
├── config.py                # Konfigurasi sistem (membaca .env)
├── requirements.txt         # Dependensi Python
├── test_scraper.py          # Script pengujian scraper per website
├── .env.example             # Template konfigurasi environment
├── .env                     # File konfigurasi (dibuat manual, tidak di-commit)
│
├── database/
│   ├── __init__.py
│   └── db.py                # Koneksi MySQL, init tabel, simpan & cek data
│
├── scraper/
│   ├── __init__.py
│   ├── baak.py              # Scraper website BAAK
│   ├── lepkom.py            # Scraper website LEPKOM
│   ├── kemahasiswaan.py     # Scraper website Kemahasiswaan
│   ├── studentsite.py       # Scraper website Studentsite
│   └── pendaftaran.py       # Scraper website Pendaftaran
│
├── notifier/
│   ├── __init__.py
│   └── discord.py           # Pengirim notifikasi Discord webhook
│
├── services/
│   ├── __init__.py
│   └── monitor.py           # Logika monitoring (initial & berkala)
│
├── utils/
│   ├── __init__.py
│   └── logger.py            # Konfigurasi logging sistem
│
└── logs/                    # Folder log otomatis dibuat saat program berjalan
    └── sistem_YYYYMMDD.log
```

---

## Prasyarat

Pastikan sudah menginstal:

- **Python 3.10 atau lebih baru** — [Download Python](https://www.python.org/downloads/)
- **MySQL Server** — [Download MySQL](https://dev.mysql.com/downloads/mysql/) atau gunakan XAMPP
- **pip** — Sudah termasuk dalam instalasi Python

---

## Instalasi

### 1. Clone atau Download Project

```bash
git clone <url-repository>
cd project
```

### 2. Buat Virtual Environment (Disarankan)

```bash
# Buat virtual environment
python -m venv venv

# Aktifkan (Windows)
venv\Scripts\activate
```

### 3. Install Dependensi Python

```bash
pip install -r requirements.txt
```

### 4. Install Browser Playwright

```bash
playwright install chromium
```

### 5. Konfigurasi File .env

```bash
# Windows
copy .env.example .env
```

Kemudian isi file `.env`:

```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=password_mysql_anda
DB_NAME=agregasi_pengumuman

DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/xxx/xxx

MONITORING_INTERVAL_MINUTES=60
INITIAL_SCRAPE_LIMIT=5
```

---

## Cara Menjalankan

```bash
python main.py
```

---

## Cara Menguji Scraper

### Mode Fast (Recommended untuk Testing Cepat)
Uji semua scraper dengan mengambil hanya 1 data per website:

```bash
py test_scraper.py --fast all
```

**Hasil:** ✅ 5/5 website berhasil dalam ~3 menit

Uji individual dengan mode fast:

```bash
py test_scraper.py --fast lepkom
py test_scraper.py --fast kemahasiswaan
py test_scraper.py --fast studentsite
py test_scraper.py --fast baak
py test_scraper.py --fast pendaftaran
```

### Mode Normal (5 data per website)
Uji masing-masing scraper tanpa memerlukan database:

```bash
py test_scraper.py lepkom
py test_scraper.py kemahasiswaan
py test_scraper.py studentsite
py test_scraper.py baak
py test_scraper.py pendaftaran
py test_scraper.py all
```

**Catatan:** Mode normal untuk BAAK membutuhkan waktu ~10 menit karena FlareSolverr. Gunakan mode fast untuk testing cepat.

### Contoh Output

```
============================================================
  MENGUJI: LEPKOM
============================================================
  Mengimpor scraper.lepkom.scrape_lepkom ...
  Import berhasil.

  Memulai scraping, mengambil maks. 5 pengumuman...
  Timeout maksimal: 180 detik

[INFO]  Scraping selesai.
[INFO]  Jumlah pengumuman ditemukan: 5

  [1]
      Judul    : ATA 2025/2026 - Pengumuman Daftar Peserta Kursus
      Tanggal  : 01 Juni 2026
      Link     : https://vm.lepkom.gunadarma.ac.id/pengumuman/...
      Sumber   : LEPKOM
      Author   : Admin
      Isi      : No  Nama Mahasiswa  NPM  Kelas ...

[OK]  LEPKOM: 5 pengumuman berhasil diambil.
```

### Fitur Timeout Monitoring
- Timeout maksimal: 180 detik (3 menit) per scraper
- Progress update setiap 30 detik
- Jika timeout, sistem lanjut ke website berikutnya
- Summary di akhir menampilkan website yang berhasil/gagal

---

## Format Data Scraping

Setiap scraper mengembalikan list of dictionary dengan format:

```python
[
    {
        "judul"   : "Judul pengumuman",
        "tanggal" : "Tanggal jika tersedia",
        "link"    : "URL lengkap detail berita",
        "sumber"  : "Nama sumber (LEPKOM / BAAK / dst.)",
        "isi"     : "Isi singkat atau isi berita jika berhasil diambil",
        "author"  : "Author jika tersedia",
        "file_url": "URL file unduhan atau referensi jika tersedia",
    }
]
```

Field yang tidak tersedia diisi string kosong `""`, bukan `None`.

---

## Struktur Database MySQL

Tabel `pengumuman` dibuat otomatis:

```sql
CREATE TABLE pengumuman (
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
);
```

Jika tabel sudah ada dari versi sebelumnya (tanpa kolom `isi`, `author`, `file_url`), fungsi `init_db()` akan otomatis menambahkan kolom yang belum ada menggunakan `ALTER TABLE` yang aman.

---

## Format Notifikasi Discord

```
📢 Pengumuman Baru

Sumber  : BAAK
Judul   : Jadwal Ujian Semester Genap 2025/2026
Tanggal : 10 Juni 2026
Link    : https://baak.gunadarma.ac.id/beritabaak/750
```

---

## Catatan per Website

| Website       | Catatan                                                                 |
|---------------|-------------------------------------------------------------------------|
| LEPKOM        | Normal, widget recent-posts                                             |
| Kemahasiswaan | Slider + article card, perlu tunggu JS render                           |
| Studentsite   | Konten publik tanpa login, struktur `div.content-box`                   |
| BAAK          | Dilindungi Cloudflare — jika challenge aktif, data tidak bisa diambil   |
| Pendaftaran   | Hanya ~2 berita per semester, limit otomatis menyesuaikan               |

Jika website gagal diakses, scraper menyimpan HTML debug ke file `debug_<sumber>.html` di folder project untuk memudahkan inspeksi selector.

---

## Troubleshooting

**`ModuleNotFoundError`**
```bash
pip install -r requirements.txt
```

**`Executable doesn't exist` (Playwright)**
```bash
playwright install chromium
```

**`Access denied` (MySQL)**
- Periksa `DB_USER` dan `DB_PASSWORD` di `.env`
- Pastikan MySQL sedang berjalan

**Data kosong dari scraper**
1. Cek file `debug_<sumber>.html` — buka di browser untuk lihat HTML aktual
2. Cek `logs/sistem_*.log` untuk detail error
3. Selector HTML mungkin berubah — sesuaikan di file scraper

**BAAK — Cloudflare Challenge**
- BAAK menggunakan Cloudflare Managed Challenge (Turnstile)
- Headless browser biasa tidak bisa melewati challenge ini
- Jika `debug_baak.html` menampilkan "Just a moment", ini penyebabnya

---

## Tech Stack

| Komponen         | Library/Tool              |
|------------------|---------------------------|
| Bahasa           | Python 3.10+              |
| Headless Browser | Playwright (Chromium)     |
| Database         | MySQL                     |
| Koneksi DB       | mysql-connector-python    |
| HTTP Client      | requests                  |
| Konfigurasi      | python-dotenv             |
| Logging          | logging (built-in Python) |
| Scheduler        | time (built-in Python)    |
