"""
notifier/discord.py
Modul notifikasi Discord via Webhook.
Mengirim informasi penting saja: sumber, judul, tanggal, link, file_url.
Isi berita tidak dikirim ke Discord (terlalu panjang).
"""

import requests
from typing import Dict

import config
from utils.logger import logger


def kirim_notifikasi_discord(pengumuman: Dict) -> bool:
    """
    Kirim notifikasi satu pengumuman baru ke Discord webhook.

    Args:
        pengumuman: Dict dengan key: judul, tanggal, link, sumber, file_url.

    Returns:
        True jika berhasil, False jika gagal.
    """
    if not config.DISCORD_WEBHOOK_URL:
        logger.warning("DISCORD_WEBHOOK_URL belum diset di .env. Notifikasi dilewati.")
        return False

    sumber   = str(pengumuman.get("sumber",   "") or "").strip() or "Unknown"
    judul    = str(pengumuman.get("judul",    "") or "").strip() or "Tanpa Judul"
    tanggal  = str(pengumuman.get("tanggal",  "") or "").strip() or "Tidak tersedia"
    link     = str(pengumuman.get("link",     "") or "").strip() or "-"
    file_url = str(pengumuman.get("file_url", "") or "").strip()

    # Format pesan — singkat dan informatif
    baris = [
        "**Pengumuman Baru**",
        "",
        f"**Sumber  :** {sumber}",
        f"**Judul   :** {judul}",
        f"**Tanggal :** {tanggal}",
        f"**Link    :** {link}",
    ]
    if file_url:
        baris.append(f"**File/Ref :** {file_url}")

    pesan = "\n".join(baris)

    # Discord message limit: 2000 karakter
    if len(pesan) > 1900:
        pesan = pesan[:1900] + "\n...[dipotong]"

    try:
        response = requests.post(
            config.DISCORD_WEBHOOK_URL,
            json={"content": pesan},
            timeout=10,
        )
        # Discord mengembalikan 204 No Content jika berhasil
        if response.status_code in (200, 204):
            logger.info(f"[Discord] Notifikasi terkirim: [{sumber}] {judul[:60]}")
            return True
        else:
            logger.error(
                f"[Discord] Gagal kirim. Status: {response.status_code} | "
                f"Response: {response.text[:100]}"
            )
            return False

    except requests.exceptions.Timeout:
        logger.error("[Discord] Timeout saat kirim notifikasi.")
        return False
    except requests.exceptions.ConnectionError:
        logger.error("[Discord] Gagal koneksi ke Discord webhook.")
        return False
    except Exception as e:
        logger.error(f"[Discord] Error tidak terduga: {type(e).__name__}: {e}")
        return False
