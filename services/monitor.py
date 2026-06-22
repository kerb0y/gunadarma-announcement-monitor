"""
services/monitor.py
Modul layanan monitoring utama.
Alur: initial scraping -> simpan DB -> monitoring berkala -> notifikasi Discord.
"""

import time
from typing import List, Dict

import config
from database.db import simpan_pengumuman
from notifier.discord import kirim_notifikasi_batch, check_webhook_status
from scraper.baak import scrape_baak
from scraper.lepkom import scrape_lepkom
from scraper.kemahasiswaan import scrape_kemahasiswaan
from scraper.studentsite import scrape_studentsite
from scraper.pendaftaran import scrape_pendaftaran
from utils.logger import logger


# Mapping nama website ke fungsi scraper
SCRAPER_MAP = {
    "LEPKOM"       : scrape_lepkom,
    "STUDENTSITE"  : scrape_studentsite,
    "KEMAHASISWAAN": scrape_kemahasiswaan,
    "BAAK"         : scrape_baak,
    "PENDAFTARAN"  : scrape_pendaftaran,
}

# Scraper yang menggunakan FlareSolverr (butuh jeda lebih lama antar satu sama lain)
SCRAPER_CLOUDFLARE = {"KEMAHASISWAAN", "BAAK", "PENDAFTARAN"}

MAX_RETRY_SCRAPER = 2    # Maksimal percobaan ulang per scraper jika gagal
JEDA_ANTAR_SCRAPER = 10  # Detik jeda antar scraper (lebih lama untuk CF scrapers)
JEDA_RETRY_SCRAPER = 20  # Detik jeda sebelum retry scraper yang gagal


def jalankan_satu_scraper(nama: str, fungsi, limit: int = None) -> List[Dict]:
    """
    Jalankan satu scraper dengan retry otomatis.
    Jika gagal (hasil kosong), coba ulang hingga MAX_RETRY_SCRAPER kali.

    Returns:
        List hasil scraping (bisa kosong jika semua percobaan gagal).
    """
    for percobaan in range(1, MAX_RETRY_SCRAPER + 1):
        if percobaan > 1:
            logger.info(f"[{nama}] Retry ke-{percobaan}/{MAX_RETRY_SCRAPER}...")
            time.sleep(JEDA_RETRY_SCRAPER)
        try:
            hasil = fungsi(limit=limit)
            if hasil:
                return hasil
            logger.warning(
                f"[{nama}] Percobaan {percobaan}/{MAX_RETRY_SCRAPER}: "
                f"tidak ada data ditemukan."
            )
        except Exception as e:
            logger.error(
                f"[{nama}] Percobaan {percobaan}/{MAX_RETRY_SCRAPER} error: "
                f"{type(e).__name__}: {e}"
            )

    logger.warning(f"[{nama}] Semua {MAX_RETRY_SCRAPER} percobaan selesai, data kosong.")
    return []


def jalankan_scraper_semua(limit: int = None) -> List[Dict]:
    """
    Jalankan semua scraper satu per satu.
    Jika satu scraper gagal, program tetap lanjut ke scraper berikutnya.
    Scraper yang pakai Cloudflare/FlareSolverr diberi jeda lebih panjang.
    """
    semua_hasil = []
    nama_sebelumnya = None

    for nama, fungsi in SCRAPER_MAP.items():
        logger.info(f"--- Scraping: {nama} ---")

        # Beri jeda lebih panjang jika scraper sebelumnya pakai Cloudflare
        if nama_sebelumnya and nama_sebelumnya in SCRAPER_CLOUDFLARE:
            jeda = 30  # 30 detik untuk beri waktu FlareSolverr recovery
            logger.info(
                f"[MONITOR] Jeda {jeda} detik sebelum {nama} "
                f"(FlareSolverr recovery dari {nama_sebelumnya})..."
            )
            time.sleep(jeda)
        elif nama_sebelumnya:
            logger.info(f"[MONITOR] Jeda {JEDA_ANTAR_SCRAPER} detik sebelum {nama}...")
            time.sleep(JEDA_ANTAR_SCRAPER)

        hasil = jalankan_satu_scraper(nama, fungsi, limit=limit)
        semua_hasil.extend(hasil)
        logger.info(f"[{nama}] Selesai. Ditemukan {len(hasil)} item.")
        nama_sebelumnya = nama

    return semua_hasil


def initial_scraping():
    """
    Scraping awal saat program pertama kali dijalankan.
    Mengambil maksimal INITIAL_SCRAPE_LIMIT pengumuman per website.
    Kirim notifikasi Discord jika SEND_DISCORD_ON_INITIAL=true.
    """
    logger.info("=" * 60)
    logger.info("INITIAL SCRAPING DIMULAI")
    logger.info(f"Target: {config.INITIAL_SCRAPE_LIMIT} pengumuman terbaru per website")
    logger.info("=" * 60)
    
    # Check webhook status
    check_webhook_status()

    semua_hasil = jalankan_scraper_semua(limit=config.INITIAL_SCRAPE_LIMIT)

    if not semua_hasil:
        logger.warning("Initial scraping selesai, tidak ada data ditemukan.")
        return

    total_insert = 0
    total_update = 0
    total_unchanged = 0
    total_error = 0
    pengumuman_baru = []
    
    for pengumuman in semua_hasil:
        result = simpan_pengumuman(pengumuman)
        if result == "insert":
            total_insert += 1
            pengumuman_baru.append(pengumuman)
        elif result == "update":
            total_update += 1
        elif result == "unchanged":
            total_unchanged += 1
        else:
            total_error += 1

    logger.info("=" * 60)
    logger.info("Initial scraping selesai.")
    logger.info(f"Total ditemukan  : {len(semua_hasil)} pengumuman")
    logger.info(f"Total INSERT     : {total_insert} pengumuman baru")
    logger.info(f"Total UPDATE     : {total_update} pengumuman di-update")
    logger.info(f"Total UNCHANGED  : {total_unchanged} pengumuman tidak berubah")
    if total_error > 0:
        logger.warning(f"Total ERROR      : {total_error} gagal disimpan")
    
    # Kirim notifikasi Discord jika diaktifkan
    if config.SEND_DISCORD_ON_INITIAL and pengumuman_baru:
        logger.info(f"[DISCORD] SEND_DISCORD_ON_INITIAL=true, kirim {len(pengumuman_baru)} notifikasi")
        kirim_notifikasi_batch(
            pengumuman_baru, 
            delay_seconds=config.DISCORD_SEND_DELAY_SECONDS
        )
    elif config.SEND_DISCORD_ON_INITIAL and not pengumuman_baru:
        logger.info("[DISCORD] SEND_DISCORD_ON_INITIAL=true, tetapi tidak ada data baru")
    else:
        logger.info("[DISCORD] SEND_DISCORD_ON_INITIAL=false, notifikasi tidak dikirim")
    
    logger.info("Sistem masuk ke mode monitoring...")
    logger.info("=" * 60)


def siklus_monitoring():
    """
    Satu siklus monitoring:
    1. Ambil data terbaru dari semua website.
    2. Simpan ke database dengan UPSERT.
    3. Kirim notifikasi Discord untuk pengumuman INSERT baru.
    """
    logger.info("-" * 60)
    logger.info("Memulai siklus monitoring...")

    semua_hasil = jalankan_scraper_semua(limit=None)

    if not semua_hasil:
        logger.warning("Siklus monitoring: tidak ada data berhasil di-scrape.")
        return

    pengumuman_baru = []
    
    for pengumuman in semua_hasil:
        # Simpan dengan UPSERT
        result = simpan_pengumuman(pengumuman)
        
        # Hanya kirim Discord untuk INSERT baru (bukan UPDATE)
        if result == "insert":
            pengumuman_baru.append(pengumuman)
            logger.info(
                f"[NEW] [{pengumuman.get('sumber', '')}] {pengumuman.get('judul', '')[:80]}"
            )

    if pengumuman_baru:
        logger.info(f"Total {len(pengumuman_baru)} pengumuman baru. Kirim notifikasi...")
        kirim_notifikasi_batch(
            pengumuman_baru, 
            delay_seconds=config.DISCORD_SEND_DELAY_SECONDS
        )
    else:
        logger.info("Tidak ada pengumuman baru. Menunggu siklus berikutnya.")

    logger.info("-" * 60)


def mulai_monitoring():
    """
    Loop monitoring berkelanjutan.
    Menjalankan siklus_monitoring() setiap MONITORING_INTERVAL_MINUTES menit.
    """
    interval_detik = config.MONITORING_INTERVAL_MINUTES * 60
    logger.info(
        f"Mode monitoring aktif. Interval: {config.MONITORING_INTERVAL_MINUTES} menit."
    )
    logger.info("Tekan Ctrl+C untuk menghentikan program.")

    while True:
        try:
            siklus_monitoring()
            logger.info(
                f"Menunggu {config.MONITORING_INTERVAL_MINUTES} menit "
                f"untuk siklus berikutnya..."
            )
            time.sleep(interval_detik)

        except KeyboardInterrupt:
            logger.info("Program dihentikan oleh pengguna (Ctrl+C).")
            break
        except Exception as e:
            logger.error(f"Error pada loop monitoring: {type(e).__name__}: {e}")
            logger.info("Mencoba lagi dalam 5 menit...")
            time.sleep(300)
