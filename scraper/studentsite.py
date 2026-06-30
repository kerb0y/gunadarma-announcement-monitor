"""
scraper/studentsite.py
Scraper untuk website Studentsite Universitas Gunadarma.
URL: https://studentsite.gunadarma.ac.id/v4/pengumuman

Update Juni 2026:
  Interface website berubah ke v4, selector baru:
  
  List berita:
    - Container: .mb-10 (area daftar berita teratas)
    - Card berita: <a> di dalam container .mb-10
    - Judul card: h3 di dalam card berita
  
  Detail berita:
    - Judul: h1[class='text-2xl sm:text-3xl font-bold mb-4 leading-snug']
    - Isi: .prose-content.text-gray-700.leading-relaxed.whitespace-pre-wrap
    - Tanggal: div[class='flex items-center gap-1.5 text-sm text-gray-400 mb-8 pb-6 border-b border-gray-100']
"""

import re
import os
from typing import List, Dict, Optional

from utils.logger import logger

SUMBER          = "STUDENTSITE"
URL             = "https://studentsite.gunadarma.ac.id/v4/pengumuman"
BASE_URL        = "https://studentsite.gunadarma.ac.id"
DEBUG_HTML_FILE = "debug_studentsite.html"


def _abs(href: str) -> str:
    if not href:
        return ""
    href = href.strip()
    if href.startswith("http"):
        return href
    if href.startswith("/"):
        return BASE_URL + href
    return BASE_URL + "/" + href


def scrape_studentsite(limit: Optional[int] = None) -> List[Dict]:
    logger.info(f"[STUDENTSITE] Mulai scraping: {URL}")
    hasil = []
    browser = None

    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

        with sync_playwright() as p:
            logger.info("[STUDENTSITE] Launch browser...")
            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox"]
            )
            ctx = browser.new_context(user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ))
            page = ctx.new_page()

            logger.info(f"[STUDENTSITE] Buka: {URL}")
            try:
                page.goto(URL, timeout=60000, wait_until="domcontentloaded")
                page.wait_for_timeout(3000)
                logger.info(f"[STUDENTSITE] Title: {page.title()!r}")
            except PWTimeout as e:
                logger.error(f"[STUDENTSITE] TIMEOUT: {e}")
                browser.close()
                return []

            html = page.content()
            logger.info(f"[STUDENTSITE] HTML: {len(html):,} char")

            # Strategi 1: Cari container .mb-10 yang berisi daftar berita
            logger.info("[STUDENTSITE] Cari container .mb-10...")
            containers = page.query_selector_all(".mb-10")
            logger.info(f"[STUDENTSITE] Container .mb-10 ditemukan: {len(containers)}")
            
            # Ambil semua link <a> dari container .mb-10
            news_links = []
            seen = set()
            
            for container in containers:
                # Ambil semua link dalam container ini
                links = container.query_selector_all("a[href]")
                for link_el in links:
                    href = link_el.get_attribute("href") or ""
                    if not href or href in seen:
                        continue
                    
                    # Convert ke absolute URL
                    abs_href = _abs(href)
                    if abs_href in seen:
                        continue
                    
                    # Ambil judul dari h3 dalam link
                    h3_el = link_el.query_selector("h3")
                    judul = ""
                    if h3_el:
                        judul = h3_el.inner_text().strip()
                    
                    # Jika h3 tidak ada, coba ambil teks dari link
                    if not judul:
                        judul = link_el.inner_text().strip()
                    
                    # Skip jika judul terlalu pendek atau tidak valid
                    if not judul or len(judul) < 5:
                        continue
                    
                    # Skip jika bukan link pengumuman (filter navigasi, dll)
                    if "pengumuman" not in abs_href and "berita" not in abs_href:
                        continue
                    
                    seen.add(abs_href)
                    news_links.append({
                        "judul": judul,
                        "link": abs_href
                    })
            
            logger.info(f"[STUDENTSITE] Link berita ditemukan: {len(news_links)}")
            
            # Fallback: jika tidak ada link dari .mb-10, cari semua link ke /pengumuman/
            if not news_links:
                logger.info("[STUDENTSITE] Fallback: cari link /pengumuman/ atau /v4/pengumuman/...")
                all_links = page.query_selector_all("a[href*='/pengumuman/'], a[href*='/v4/pengumuman/']")
                
                for link_el in all_links:
                    href = link_el.get_attribute("href") or ""
                    abs_href = _abs(href)
                    
                    if abs_href in seen:
                        continue
                    
                    # Ambil judul
                    h3_el = link_el.query_selector("h3")
                    judul = h3_el.inner_text().strip() if h3_el else link_el.inner_text().strip()
                    
                    if not judul or len(judul) < 5:
                        continue
                    
                    seen.add(abs_href)
                    news_links.append({
                        "judul": judul,
                        "link": abs_href
                    })
                
                logger.info(f"[STUDENTSITE] Fallback: {len(news_links)} link ditemukan")
            
            if not news_links:
                logger.warning("[STUDENTSITE] Tidak ada berita ditemukan. Simpan debug HTML.")
                with open(DEBUG_HTML_FILE, "w", encoding="utf-8") as f:
                    f.write(html)
                logger.warning(f"[STUDENTSITE] Debug: {os.path.abspath(DEBUG_HTML_FILE)}")
                browser.close()
                return []
            
            # Apply limit
            if limit:
                news_links = news_links[:limit]
            
            logger.info(f"[STUDENTSITE] Akan membuka {len(news_links)} halaman detail...")
            
            # Buka setiap halaman detail
            for news in news_links:
                item = {
                    "judul"   : news["judul"],
                    "tanggal" : "",
                    "link"    : news["link"],
                    "sumber"  : SUMBER,
                    "isi"     : "",
                    "author"  : "",
                    "file_url": "",
                }
                
                try:
                    dpage = ctx.new_page()
                    dpage.goto(item["link"], timeout=30000, wait_until="domcontentloaded")
                    dpage.wait_for_timeout(2000)
                    
                    # Ambil judul dari detail page (fallback jika judul list kosong)
                    if not item["judul"] or len(item["judul"]) < 5:
                        judul_detail = dpage.query_selector("h1.text-2xl, h1")
                        if judul_detail:
                            item["judul"] = judul_detail.inner_text().strip()
                    
                    # Ambil tanggal dari div dengan class khusus
                    tanggal_el = dpage.query_selector(
                        "div.flex.items-center.gap-1\\.5.text-sm.text-gray-400, "
                        "div[class*='flex items-center'], "
                        "div[class*='text-gray-400']"
                    )
                    if tanggal_el:
                        tanggal_text = tanggal_el.inner_text().strip()
                        # Extract tanggal jika ada format tanggal
                        match = re.search(r"(\d{1,2}\s+\w+\s+\d{4}|\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4})", tanggal_text)
                        if match:
                            item["tanggal"] = match.group(1)
                        elif tanggal_text:
                            item["tanggal"] = tanggal_text[:50]
                    
                    # Ambil isi dari .prose-content
                    # Gunakan inner_text() untuk mempertahankan newline
                    isi_el = dpage.query_selector(
                        ".prose-content.text-gray-700.leading-relaxed.whitespace-pre-wrap, "
                        ".prose-content, "
                        "[class*='prose-content']"
                    )
                    if isi_el:
                        item["isi"] = isi_el.inner_text().strip()
                    
                    # Fallback isi jika selector utama tidak ditemukan
                    if not item["isi"]:
                        # Coba selector alternatif
                        isi_alt = dpage.query_selector(".content, article, main")
                        if isi_alt:
                            item["isi"] = isi_alt.inner_text().strip()
                    
                    # Link eksternal di dalam konten → file_url
                    if item["isi"]:
                        ext_links = dpage.query_selector_all("a[href^='http']")
                        for ext_el in ext_links:
                            ext_href = ext_el.get_attribute("href") or ""
                            if ext_href and "studentsite.gunadarma.ac.id" not in ext_href:
                                if ext_href != item["link"]:
                                    item["file_url"] = ext_href
                                    break  # Ambil yang pertama
                    
                    dpage.close()
                    logger.info(f"[STUDENTSITE] OK (detail): {item['judul'][:60]!r}")
                    
                except Exception as e:
                    logger.warning(f"[STUDENTSITE] Gagal buka detail {item['link']}: {e}")
                    try:
                        dpage.close()
                    except Exception:
                        pass
                    # Tetap tambahkan item meskipun detail gagal
                
                hasil.append(item)
            
            browser.close()
            browser = None

    except Exception as e:
        logger.error(f"[STUDENTSITE] ERROR: {type(e).__name__}: {e}")
        import traceback as tb; logger.error(tb.format_exc())
    finally:
        if browser:
            try:
                browser.close()
            except Exception:
                pass

    logger.info(f"[STUDENTSITE] Selesai. Total: {len(hasil)}")
    return hasil
