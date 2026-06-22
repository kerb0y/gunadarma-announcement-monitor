"""
notifier/discord.py
Modul notifikasi Discord via Webhook dengan format embed.
Multi-webhook per sumber: BAAK, LEPKOM, STUDENTSITE, KEMAHASISWAAN, PENDAFTARAN.
"""

import requests
import time
from typing import Dict, List
from datetime import datetime
from zoneinfo import ZoneInfo

import config
from utils.logger import logger
from utils.text_formatter import clean_news_text, truncate_text
from database.db import mark_as_notified


# Color untuk setiap sumber (hex format)
SOURCE_COLORS = {
    "BAAK": 0x3498db,         # Biru
    "LEPKOM": 0xe74c3c,       # Merah
    "STUDENTSITE": 0x2ecc71,  # Hijau
    "KEMAHASISWAAN": 0xf39c12, # Orange
    "PENDAFTARAN": 0x9b59b6,  # Ungu
}

# Batas maksimal panjang description untuk Discord embed
# Discord limit: 4096 karakter, kita gunakan 3500 untuk keamanan
MAX_DISCORD_DESCRIPTION = 3500


def get_webhook_by_source(sumber: str) -> str:
    """Ambil webhook URL berdasarkan sumber pengumuman."""
    return config.DISCORD_WEBHOOKS.get(sumber, "")


def check_webhook_status():
    """Tampilkan status webhook untuk setiap sumber."""
    logger.info("[DISCORD] Status Webhook:")
    for sumber, webhook_url in config.DISCORD_WEBHOOKS.items():
        status = "YA" if webhook_url else "TIDAK"
        logger.info(f"[DISCORD] Webhook {sumber:15s} aktif: {status}")


def parse_tanggal_pengumuman(tanggal_str: str) -> datetime:
    """
    Parse berbagai format tanggal menjadi datetime object.
    
    Format yang didukung:
    - 15/05/2026
    - 2026-06-19
    - Jun 15, 2026
    - Minggu, 21 Juni 2026 (Indonesian)
    - Senin, 15 Januari 2026 (Indonesian)
    - Etc.
    
    Returns:
        datetime object atau datetime.min jika gagal parse
    """
    if not tanggal_str:
        return datetime.min
    
    # Mapping bulan Indonesia ke Inggris
    indo_month_map = {
        "Januari": "January", "Februari": "February", "Maret": "March",
        "April": "April", "Mei": "May", "Juni": "June",
        "Juli": "July", "Agustus": "August", "September": "September",
        "Oktober": "October", "November": "November", "Desember": "December"
    }
    
    # Hapus nama hari dalam bahasa Indonesia (Senin, Selasa, dst) jika ada
    hari_indo = ["Minggu", "Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu"]
    tanggal_clean = tanggal_str.strip()
    for hari in hari_indo:
        if tanggal_clean.startswith(hari + ","):
            tanggal_clean = tanggal_clean[len(hari)+1:].strip()
            break
    
    # Replace nama bulan Indonesia dengan Inggris
    tanggal_normalized = tanggal_clean
    for indo, eng in indo_month_map.items():
        if indo in tanggal_normalized:
            tanggal_normalized = tanggal_normalized.replace(indo, eng)
            break
    
    formats = [
        "%d/%m/%Y",        # 15/05/2026
        "%Y-%m-%d",        # 2026-06-19
        "%b %d, %Y",       # Jun 15, 2026
        "%d %b %Y",        # 15 Jun 2026
        "%d %B %Y",        # 15 June 2026 (full month name)
        "%d-%m-%Y",        # 15-05-2026
        "%B %d, %Y",       # June 15, 2026
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(tanggal_normalized.strip(), fmt)
        except ValueError:
            continue
    
    # Jika gagal parse, return datetime.min agar diletakkan di bawah
    logger.warning(f"[DISCORD] Gagal parse tanggal: {tanggal_str}")
    return datetime.min


def sort_by_date_desc(pengumuman_list: List[Dict]) -> List[Dict]:
    """Urutkan pengumuman berdasarkan tanggal dari terbaru ke terlama."""
    def get_sort_key(item):
        tanggal = item.get("tanggal", "")
        parsed_date = parse_tanggal_pengumuman(tanggal)
        # Return tuple: (datetime, original_index) untuk stable sort
        return parsed_date
    
    # Sort descending (terbaru di atas)
    sorted_list = sorted(pengumuman_list, key=get_sort_key, reverse=True)
    return sorted_list


def kirim_notifikasi_discord(pengumuman: Dict, mark_notified: bool = True) -> bool:
    """
    Kirim notifikasi satu pengumuman ke Discord webhook dengan format embed.

    Args:
        pengumuman: Dict dengan key: judul, tanggal, link, sumber, isi, author, file_url.
        mark_notified: Tandai sebagai sudah dikirim di database (default True).

    Returns:
        True jika berhasil, False jika gagal.
    """
    sumber = str(pengumuman.get("sumber", "")).strip() or "UNKNOWN"
    webhook_url = get_webhook_by_source(sumber)
    
    if not webhook_url:
        logger.warning(f"[DISCORD] Skip karena webhook kosong: {sumber}")
        return False
    
    judul = str(pengumuman.get("judul", "")).strip() or "Tanpa Judul"
    tanggal = str(pengumuman.get("tanggal", "")).strip() or "Tidak tersedia"
    link = str(pengumuman.get("link", "")).strip() or ""
    isi_raw = str(pengumuman.get("isi", "")).strip() or "Isi tidak tersedia"
    author = str(pengumuman.get("author", "")).strip() or "Tidak tersedia"
    file_url = str(pengumuman.get("file_url", "")).strip()
    
    # Clean dan truncate isi dengan mempertahankan newline dan list
    isi_cleaned = clean_news_text(isi_raw)
    isi_final = truncate_text(isi_cleaned, max_length=MAX_DISCORD_DESCRIPTION)
    
    # Debug log untuk panjang isi
    logger.info(f"[DISCORD] Panjang isi asli: {len(isi_raw)} karakter")
    logger.info(f"[DISCORD] Panjang description embed: {len(isi_final)} karakter")
    logger.info(f"[DISCORD] Preview description: {isi_final[:150]}...")
    
    # Timestamp dalam timezone Asia/Jakarta
    now_jakarta = datetime.now(ZoneInfo("Asia/Jakarta"))
    timestamp_iso = now_jakarta.isoformat()
    
    # Build embed
    embed = {
        "title": f"[{sumber}] {judul[:200]}",  # Max 256 for title
        "url": link if link else None,
        "description": isi_final,
        "color": SOURCE_COLORS.get(sumber, 0x95a5a6),  # Default gray
        "fields": [
            {
                "name": "Sumber",
                "value": sumber,
                "inline": True
            },
            {
                "name": "Tanggal Pengumuman",
                "value": tanggal,
                "inline": True
            },
        ],
        "footer": {
            "text": "Sistem Agregasi Pengumuman Gunadarma"
        },
        "timestamp": timestamp_iso
    }
    
    # Tambahkan field author jika ada
    if author and author != "Tidak tersedia":
        embed["fields"].append({
            "name": "Author",
            "value": author,
            "inline": True
        })
    
    # Tambahkan field file_url jika ada
    if file_url:
        embed["fields"].append({
            "name": "File/URL",
            "value": f"[Lihat File]({file_url})",
            "inline": False
        })
    
    payload = {
        "embeds": [embed]
    }
    
    try:
        response = requests.post(
            webhook_url,
            json=payload,
            timeout=10,
        )
        
        if response.status_code in (200, 204):
            logger.info(f"[DISCORD] Berhasil kirim: {judul[:60]}")
            
            # Mark as notified in database
            if mark_notified and link:
                mark_as_notified(link, sumber)
            
            return True
        else:
            logger.error(
                f"[DISCORD] Gagal kirim. Status: {response.status_code} | "
                f"Response: {response.text[:100]}"
            )
            return False

    except requests.exceptions.Timeout:
        logger.error("[DISCORD] Timeout saat kirim notifikasi.")
        return False
    except requests.exceptions.ConnectionError:
        logger.error("[DISCORD] Gagal koneksi ke Discord webhook.")
        return False
    except Exception as e:
        logger.error(f"[DISCORD] Error tidak terduga: {type(e).__name__}: {e}")
        return False


def kirim_notifikasi_batch(pengumuman_list: List[Dict], delay_seconds: int = 3) -> Dict[str, int]:
    """
    Kirim notifikasi batch per sumber dengan urutan tanggal terbaru.
    
    Args:
        pengumuman_list: List pengumuman yang akan dikirim
        delay_seconds: Jeda antar pengiriman notifikasi
        
    Returns:
        Dict statistik pengiriman per sumber
    """
    stats = {}
    
    # Group by sumber
    by_sumber = {}
    for p in pengumuman_list:
        sumber = p.get("sumber", "UNKNOWN")
        if sumber not in by_sumber:
            by_sumber[sumber] = []
        by_sumber[sumber].append(p)
    
    # Kirim per sumber dengan urutan tanggal terbaru
    for sumber, items in by_sumber.items():
        webhook_url = get_webhook_by_source(sumber)
        
        if not webhook_url:
            logger.warning(f"[DISCORD] Skip karena webhook kosong: {sumber}")
            stats[sumber] = {"sent": 0, "skipped": len(items)}
            continue
        
        # Sort by date descending (terbaru dulu)
        sorted_items = sort_by_date_desc(items)
        
        logger.info(f"[DISCORD] Sumber {sumber} -> webhook {sumber}")
        logger.info(f"[DISCORD] Mengirim {len(sorted_items)} notifikasi {sumber}, urut tanggal terbaru")
        
        sent = 0
        skipped = 0
        
        for item in sorted_items:
            # Cek apakah sudah pernah dikirim
            link = item.get("link", "")
            if not link:
                skipped += 1
                continue
            
            # Kirim notifikasi
            if kirim_notifikasi_discord(item, mark_notified=True):
                sent += 1
                # Delay antar pesan
                if sent < len(sorted_items):
                    time.sleep(delay_seconds)
            else:
                skipped += 1
        
        stats[sumber] = {"sent": sent, "skipped": skipped}
        logger.info(f"[DISCORD] {sumber}: sent {sent}, skipped {skipped}")
    
    # Summary
    logger.info("[DISCORD] Summary:")
    for sumber, stat in stats.items():
        logger.info(f"  {sumber:15s}: sent {stat['sent']}, skipped {stat['skipped']}")
    
    return stats
