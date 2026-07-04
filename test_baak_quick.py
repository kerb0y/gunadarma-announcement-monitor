"""
test_baak_quick.py
Test cepat scraper BAAK (hanya 1 berita untuk demonstrasi)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scraper.baak import scrape_baak
from utils.logger import logger

def main():
    logger.info("=" * 80)
    logger.info("TEST CEPAT - SCRAPER BAAK dengan FlareSolverr (3 berita)")
    logger.info("=" * 80)
    
    # Test dengan limit 3 berita untuk melihat perbedaan
    hasil = scrape_baak(limit=3)
    
    logger.info("=" * 80)
    logger.info(f"HASIL: {len(hasil)} berita berhasil di-scrape")
    logger.info("=" * 80)
    
    # Tampilkan detail lengkap
    if hasil:
        logger.info("\n📰 DETAIL BERITA:\n")
        
        for idx, item in enumerate(hasil, 1):
            logger.info(f"{'─' * 80}")
            logger.info(f"BERITA #{idx}")
            logger.info(f"{'─' * 80}")
            logger.info(f"\n📌 Judul:")
            logger.info(f"   {item['judul']}")
            logger.info(f"\n🔗 Link:")
            logger.info(f"   {item['link']}")
            logger.info(f"\n📅 Tanggal:")
            logger.info(f"   {item['tanggal'] or '(tidak tersedia)'}")
            logger.info(f"\n👤 Author:")
            logger.info(f"   {item['author'] or '(tidak tersedia)'}")
            logger.info(f"\n📄 Isi:")
            logger.info(f"   Panjang: {len(item['isi'])} karakter")
            if item['isi']:
                preview = item['isi'][:200].replace('\n', ' ')
                logger.info(f"   Preview: {preview}...")
            logger.info(f"\n📎 File URL:")
            logger.info(f"   {item['file_url'] or '(tidak ada)'}")
            logger.info(f"\n🏷️  Sumber:")
            logger.info(f"   {item['sumber']}\n")
        
        # Validasi: pastikan setiap berita berbeda
        logger.info("=" * 80)
        logger.info("VALIDASI:")
        logger.info("=" * 80)
        
        judul_set = set([item['judul'] for item in hasil])
        link_set = set([item['link'] for item in hasil])
        
        logger.info(f"✓ Total berita: {len(hasil)}")
        logger.info(f"✓ Judul unik: {len(judul_set)}")
        logger.info(f"✓ Link unik: {len(link_set)}")
        
        if len(judul_set) == len(hasil) and len(link_set) == len(hasil):
            logger.info("\n✅ SUCCESS: Semua berita berbeda!")
        else:
            logger.warning("\n⚠️  WARNING: Ada berita yang duplikat!")
            
    else:
        logger.error("\n❌ TIDAK ADA DATA yang berhasil di-scrape!")
    
    logger.info("\n" + "=" * 80)
    logger.info("✅ TEST SELESAI")
    logger.info("=" * 80)
    
    return len(hasil)

if __name__ == "__main__":
    try:
        count = main()
        sys.exit(0 if count > 0 else 1)
    except KeyboardInterrupt:
        logger.warning("\n\n⚠️  Test dibatalkan oleh user (Ctrl+C)")
        sys.exit(130)
    except Exception as e:
        logger.error(f"\n\n❌ ERROR FATAL: {type(e).__name__}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)
