"""
main.py
Entry point utama sistem agregasi pengumuman Universitas Gunadarma.

Alur eksekusi:
1. Validasi konfigurasi (.env)
2. Inisialisasi database (buat tabel jika belum ada)
3. Initial scraping (ambil 5 pengumuman terbaru per website)
4. Masuk ke mode monitoring berkala (setiap 60 menit)
"""

import sys

from database.db import init_db
from services.monitor import initial_scraping, mulai_monitoring
from utils.logger import logger
import config


def validasi_konfigurasi() -> bool:
    """
    Memvalidasi konfigurasi yang wajib ada sebelum program berjalan.

    Returns:
        True jika semua konfigurasi valid, False jika ada yang kurang.
    """
    ada_error = False

    # Cek konfigurasi database
    if not config.DB_PASSWORD and config.DB_USER != "root":
        logger.warning("DB_PASSWORD kosong. Pastikan konfigurasi database benar di file .env")

    if not config.DB_HOST or not config.DB_NAME:
        logger.error("DB_HOST atau DB_NAME tidak dikonfigurasi. Periksa file .env")
        ada_error = True

    # Cek Discord Webhook (tidak wajib semua, hanya warning)
    webhook_aktif = sum(1 for url in config.DISCORD_WEBHOOKS.values() if url)
    if webhook_aktif == 0:
        logger.warning(
            "Tidak ada webhook Discord yang diset. Notifikasi Discord tidak akan dikirim. "
            "Tambahkan webhook di file .env jika ingin mengaktifkan notifikasi."
        )
    else:
        logger.info(f"{webhook_aktif}/5 webhook Discord aktif.")

    return not ada_error


def main():
    """
    Fungsi utama program.
    """
    logger.info("=" * 60)
    logger.info("SISTEM AGREGASI PENGUMUMAN UNIVERSITAS GUNADARMA")
    logger.info("Memulai sistem...")
    logger.info("=" * 60)

    # Langkah 1: Validasi konfigurasi
    logger.info("Memeriksa konfigurasi...")
    if not validasi_konfigurasi():
        logger.error("Konfigurasi tidak valid. Program dihentikan.")
        logger.error("Salin .env.example menjadi .env dan isi dengan nilai yang sesuai.")
        sys.exit(1)

    logger.info("Konfigurasi OK.")
    logger.info(f"  Database  : {config.DB_USER}@{config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}")
    logger.info(f"  Interval  : {config.MONITORING_INTERVAL_MINUTES} menit")
    logger.info(f"  Limit awal: {config.INITIAL_SCRAPE_LIMIT} per website")
    webhook_aktif = sum(1 for url in config.DISCORD_WEBHOOKS.values() if url)
    logger.info(f"  Discord   : {webhook_aktif}/5 webhook aktif")
    logger.info(f"  Notif initial: {'YA' if config.SEND_DISCORD_ON_INITIAL else 'TIDAK'}")

    # Langkah 2: Inisialisasi database
    logger.info("Menginisialisasi database MySQL...")
    if not init_db():
        logger.error("Gagal menginisialisasi database. Program dihentikan.")
        logger.error("Pastikan MySQL berjalan dan konfigurasi .env sudah benar.")
        sys.exit(1)

    # Langkah 3: Initial scraping
    initial_scraping()

    # Langkah 4: Mulai monitoring berkala
    mulai_monitoring()


if __name__ == "__main__":
    main()
