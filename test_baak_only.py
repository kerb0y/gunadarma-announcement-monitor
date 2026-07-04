"""
test_baak_only.py
Script test khusus untuk scraper BAAK dengan FlareSolverr.
"""

import sys
import os

# Pastikan bisa import dari direktori project
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scraper.baak import scrape_baak
from utils.logger import logger

def main():
    logger.info("=" * 80)
    logger.info("TEST SCRAPER BAAK dengan FlareSolverr")
    logger.info("=" * 80)
    
    # Test dengan limit 3 berita
    hasil = scrape_baak(limit=3)
    
    logger.info("=" * 80)
    logger.info(f"HASIL: Total {len(hasil)} berita berhasil di-scrape")
    logger.info("=" * 80)
    
    # Tampilkan ringkasan hasil
    if hasil:
        logger.info("\nRINGKASAN HASIL SCRAPING:")
        for idx, item in enumerate(hasil, 1):
            logger.info(f"\n[{idx}] {item['judul']}")
            logger.info(f"    Link: {item['link']}")
            logger.info(f"    Tanggal: {item['tanggal']}")
            logger.info(f"    Author: {item['author']}")
            logger.info(f"    Panjang isi: {len(item['isi'])} karakter")
            logger.info(f"    File URL: {item['file_url'] or '(tidak ada)'}")
    else:
        logger.warning("\nTIDAK ADA DATA yang berhasil di-scrape!")
    
    logger.info("\n" + "=" * 80)
    logger.info("TEST SELESAI")
    logger.info("=" * 80)
    
    return len(hasil)

if __name__ == "__main__":
    try:
        count = main()
        sys.exit(0 if count > 0 else 1)
    except KeyboardInterrupt:
        logger.warning("\n\nTest dibatalkan oleh user (Ctrl+C)")
        sys.exit(130)
    except Exception as e:
        logger.error(f"\n\nERROR FATAL: {type(e).__name__}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)
