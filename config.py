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
# Multi-webhook per sumber pengumuman
DISCORD_WEBHOOK_BAAK = os.getenv("DISCORD_WEBHOOK_BAAK", "")
DISCORD_WEBHOOK_LEPKOM = os.getenv("DISCORD_WEBHOOK_LEPKOM", "")
DISCORD_WEBHOOK_STUDENTSITE = os.getenv("DISCORD_WEBHOOK_STUDENTSITE", "")
DISCORD_WEBHOOK_KEMAHASISWAAN = os.getenv("DISCORD_WEBHOOK_KEMAHASISWAAN", "")
DISCORD_WEBHOOK_PENDAFTARAN = os.getenv("DISCORD_WEBHOOK_PENDAFTARAN", "")

# Mapping sumber ke webhook
DISCORD_WEBHOOKS = {
    "BAAK": DISCORD_WEBHOOK_BAAK,
    "LEPKOM": DISCORD_WEBHOOK_LEPKOM,
    "STUDENTSITE": DISCORD_WEBHOOK_STUDENTSITE,
    "KEMAHASISWAAN": DISCORD_WEBHOOK_KEMAHASISWAAN,
    "PENDAFTARAN": DISCORD_WEBHOOK_PENDAFTARAN,
}

# Kirim Discord saat initial scraping
SEND_DISCORD_ON_INITIAL = os.getenv("SEND_DISCORD_ON_INITIAL", "false").lower() == "true"

# Jeda pengiriman notifikasi Discord
DISCORD_SEND_DELAY_SECONDS = int(os.getenv("DISCORD_SEND_DELAY_SECONDS", 3))
DISCORD_OLD_BATCH_DELAY_MINUTES = int(os.getenv("DISCORD_OLD_BATCH_DELAY_MINUTES", 5))

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
