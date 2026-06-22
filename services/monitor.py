"""
services/monitor.py
Modul layanan monitoring utama.
Alur: initial scraping -> simpan DB -> monitoring berkala -> notifikasi Discord.
"""

import time
from typing import List, Dict

import config
from database.db import simpan_pengumuman, cek_duplikat
from notifier.discord import kirim_notifikasi_discord
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
    Tidak mengirim notifikasi Discord (data dianggap sebagai baseline).
    """
    logger.info("=" * 60)
    logger.info("INITIAL SCRAPING DIMULAI")
    logger.info(f"Target: {config.INITIAL_SCRAPE_LIMIT} pengumuman terbaru per website")
    logger.info("=" * 60)

    semua_hasil = jalankan_scraper_semua(limit=config.INITIAL_SCRAPE_LIMIT)

    if not semua_hasil:
        logger.warning("Initial scraping selesai, tidak ada data ditemukan.")
        return

    jumlah_disimpan = 0
    for pengumuman in semua_hasil:
        if simpan_pengumuman(pengumuman):
            jumlah_disimpan += 1

    logger.info("=" * 60)
    logger.info("Initial scraping selesai.")
    logger.info(f"Total ditemukan : {len(semua_hasil)} pengumuman")
    logger.info(f"Total disimpan  : {jumlah_disimpan} pengumuman baru ke database")
    logger.info("Sistem masuk ke mode monitoring...")
    logger.info("=" * 60)


def siklus_monitoring():
    """
    Satu siklus monitoring:
    1. Ambil data terbaru dari semua website.
    2. Cek apakah ada pengumuman baru (belum ada di database).
    3. Simpan yang baru dan kirim notifikasi Discord.
    """
    logger.info("-" * 60)
    logger.info("Memulai siklus monitoring...")

    semua_hasil = jalankan_scraper_semua(limit=None)

    if not semua_hasil:
        logger.warning("Siklus monitoring: tidak ada data berhasil di-scrape.")
        return

    pengumuman_baru = []
    for pengumuman in semua_hasil:
        link   = pengumuman.get("link",   "")
        sumber = pengumuman.get("sumber", "")
        if not link:
            continue
        if not cek_duplikat(link, sumber):
            if simpan_pengumuman(pengumuman):
                pengumuman_baru.append(pengumuman)
                logger.info(
                    f"[NEW] [{sumber}] {pengumuman.get('judul', '')[:80]}"
                )

    if pengumuman_baru:
        logger.info(f"Total {len(pengumuman_baru)} pengumuman baru. Kirim notifikasi...")
        for p in pengumuman_baru:
            kirim_notifikasi_discord(p)
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
