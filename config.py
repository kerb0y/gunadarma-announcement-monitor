"""
config.py
Modul konfigurasi utama.
Membaca semua pengaturan dari file .env menggunakan python-dotenv.
"""

import os
from dotenv import load_dotenv

# Muat variabel dari file .env ke environment
load_dotenv()


# --- Konfigurasi Database MySQL ---
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 3306))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "agregasi_pengumuman")

# --- Konfigurasi Discord ---
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")

# --- Konfigurasi Monitoring ---
# Interval dalam menit, default 60 menit
MONITORING_INTERVAL_MINUTES = int(os.getenv("MONITORING_INTERVAL_MINUTES", 60))

# --- Konfigurasi Scraping ---
# Jumlah pengumuman yang diambil saat initial scraping per website
INITIAL_SCRAPE_LIMIT = int(os.getenv("INITIAL_SCRAPE_LIMIT", 5))

# --- Mode Debug ---
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"

# --- URL Website yang Dimonitor ---
WEBSITES = {
    "LEPKOM"       : "https://vm.lepkom.gunadarma.ac.id/pengumuman",
    "KEMAHASISWAAN": "https://kemahasiswaan.gunadarma.ac.id/",
    "STUDENTSITE"  : "https://studentsite.gunadarma.ac.id/",
    "BAAK"         : "https://baak.gunadarma.ac.id/beritabaak",
    "PENDAFTARAN"  : "https://pendaftaran.gunadarma.ac.id/2026/home/berita",
}
