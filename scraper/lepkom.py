"""
scraper/lepkom.py
Scraper untuk website LEPKOM Universitas Gunadarma.
URL: https://vm.lepkom.gunadarma.ac.id/pengumuman

Selector aktual (diverifikasi Juni 2026 dari user):
  List  : .widget.recent-posts-entry .widget-post-bx h6 a   (judul + link)
           li:nth-child(1) a di ul.media-post               (tanggal)
           li:nth-child(3) a di ul.media-post               (author)
  Detail: h5.post-title (judul), .table-responsive (isi),
          .btn.green[href] (file unduhan)
"""

import os
from typing import List, Dict, Optional

from utils.logger import logger, clean_log_text, log_content_length

SUMBER          = "LEPKOM"
URL             = "https://vm.lepkom.gunadarma.ac.id/pengumuman"
BASE_URL        = "https://vm.lepkom.gunadarma.ac.id"
DEBUG_HTML_FILE = "debug_lepkom.html"


def _abs(href: str) -> str:
    if not href:
        return ""
    href = href.strip()
    if href.startswith("http"):
        return href
    if href.startswith("/"):
        return BASE_URL + href
    return BASE_URL + "/" + href


def scrape_lepkom(limit: Optional[int] = None) -> List[Dict]:
    logger.info(f"[LEPKOM] Mulai scraping: {URL}")
    hasil = []
    browser = None

    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

        with sync_playwright() as p:
            logger.info("[LEPKOM] Launch browser...")
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

            logger.info(f"[LEPKOM] Buka: {URL}")
            try:
                page.goto(URL, timeout=60000, wait_until="domcontentloaded")
                page.wait_for_timeout(2000)
                logger.info(f"[LEPKOM] Title: {page.title()!r}")
            except PWTimeout as e:
                logger.error(f"[LEPKOM] TIMEOUT saat buka halaman: {e}")
                browser.close()
                return []

            html = page.content()
            logger.info(f"[LEPKOM] {log_content_length(html, 'HTML')}")

            # Kumpulkan link dari widget recent-posts
            logger.info("[LEPKOM] Cari link pengumuman dari widget recent-posts...")

            # Selector utama sesuai user: .widget.recent-posts-entry .widget-post-bx h6 a
            link_els = page.query_selector_all(
                ".widget.recent-posts-entry .widget-post-bx h6 a"
            )
            logger.info(f"[LEPKOM] Widget recent-posts: {len(link_els)} link.")

            # Fallback 1: widget recent-posts tanpa class .widget
            if not link_els:
                link_els = page.query_selector_all(
                    ".recent-posts-entry .widget-post-bx h6 a, "
                    "div.widget-post-bx h6 a"
                )
                logger.info(f"[LEPKOM] Fallback widget-post-bx: {len(link_els)} link.")

            # Fallback 2: posting utama di area content
            if not link_els:
                link_els = page.query_selector_all(
                    "div.blog-post div.ttr-post-info h5 a, "
                    ".post-title a, "
                    "h5.post-title a"
                )
                logger.info(f"[LEPKOM] Fallback blog-post: {len(link_els)} link.")

            # Fallback 3: semua link mengarah ke /pengumuman/
            if not link_els:
                logger.info("[LEPKOM] Fallback: cari semua link ke /pengumuman/...")
                all_a = page.query_selector_all("a[href*='/pengumuman/']")
                link_els = [
                    el for el in all_a
                    if el.inner_text().strip() and len(el.inner_text().strip()) > 5
                ]
                logger.info(f"[LEPKOM] Fallback /pengumuman/ link: {len(link_els)}")

            if not link_els:
                logger.warning("[LEPKOM] Tidak ada link ditemukan. Simpan debug HTML.")
                with open(DEBUG_HTML_FILE, "w", encoding="utf-8") as f:
                    f.write(html)
                logger.warning(f"[LEPKOM] Debug: {os.path.abspath(DEBUG_HTML_FILE)}")
                browser.close()
                return []

            links = []
            seen  = set()
            for el in link_els:
                href  = _abs(el.get_attribute("href") or "")
                judul = el.inner_text().strip()
                if href and href not in seen and judul:
                    seen.add(href)
                    links.append((judul, href))

            logger.info(f"[LEPKOM] Link unik: {len(links)}")
            if limit:
                links = links[:limit]

            logger.info(f"[LEPKOM] Akan buka {len(links)} halaman detail...")

            # Buka setiap halaman detail
            for judul_list, href in links:
                item = {
                    "judul"   : judul_list,
                    "tanggal" : "",
                    "link"    : href,
                    "sumber"  : SUMBER,
                    "isi"     : "",
                    "author"  : "",
                    "file_url": "",
                }
                try:
                    dpage = ctx.new_page()
                    dpage.goto(href, timeout=30000, wait_until="domcontentloaded")
                    dpage.wait_for_timeout(1500)

                    # Judul detail
                    judul_el = dpage.query_selector(
                        "h5.post-title a, h5.post-title, h1.post-title, "
                        ".ttr-post-title a, .ttr-post-title"
                    )
                    if judul_el:
                        t = judul_el.inner_text().strip()
                        if t:
                            item["judul"] = t

                    # Tanggal: ul.media-post li:first-child a
                    tgl_el = dpage.query_selector(
                        "ul.media-post li:first-child a, "
                        "ul.media-post li:nth-child(1) a, "
                        ".post-meta .date, time[datetime]"
                    )
                    if tgl_el:
                        item["tanggal"] = " ".join(tgl_el.inner_text().strip().split())

                    # Author: ul.media-post li:last-child a (li ke-3)
                    auth_el = dpage.query_selector(
                        "ul.media-post li:last-child a, "
                        "ul.media-post li:nth-child(3) a, "
                        ".post-meta .author"
                    )
                    if auth_el:
                        item["author"] = auth_el.inner_text().strip()

                    # Isi: .table-responsive (tabel utama konten pengumuman)
                    # Gunakan inner_text() untuk mempertahankan newline
                    isi_el = dpage.query_selector(
                        ".table-responsive, "
                        ".hoverable-table, "
                        "div.ttr-post-text, "
                        "div.post-content"
                    )
                    if isi_el:
                        item["isi"] = isi_el.inner_text().strip()

                    # File unduhan: .btn.green[href] atau tombol unduh
                    file_el = dpage.query_selector(
                        ".btn.green[href], "
                        "a.btn[href*='unduh'], "
                        "a[href*='unduh'], "
                        "a[href*='.pdf']"
                    )
                    if file_el:
                        item["file_url"] = _abs(file_el.get_attribute("href") or "")

                    dpage.close()
                    logger.info(f"[LEPKOM] OK: {clean_log_text(item['judul'], 70)}")
                    if item['isi']:
                        logger.info(f"[LEPKOM] {log_content_length(item['isi'], 'Isi')}")

                except Exception as e:
                    logger.warning(f"[LEPKOM] Gagal buka detail {href}: {e}")
                    try:
                        dpage.close()
                    except Exception:
                        pass

                hasil.append(item)

            browser.close()
            browser = None

    except Exception as e:
        logger.error(f"[LEPKOM] ERROR: {type(e).__name__}: {e}")
        import traceback as tb; logger.error(tb.format_exc())
    finally:
        if browser:
            try:
                browser.close()
            except Exception:
                pass

    logger.info(f"[LEPKOM] Selesai. Total: {len(hasil)}")
    return hasil
