"""
scraper/studentsite.py
Scraper untuk website Studentsite Universitas Gunadarma.
URL: https://studentsite.gunadarma.ac.id/

Selector aktual (diverifikasi Juni 2026 dari user):
  List berita: body > div:nth-child(2) > div:nth-child(9)
  Judul + href: h3.content-box-header a > b > font
  Tanggal: div.font-gray
  Isi: paragraf di content-box
  Link eksternal (di isi): simpan ke file_url
"""

import re
import os
from typing import List, Dict, Optional

from utils.logger import logger

SUMBER          = "STUDENTSITE"
URL             = "https://studentsite.gunadarma.ac.id/"
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

            # Strategi 1: div.content-box (selector yang sudah terbukti)
            logger.info("[STUDENTSITE] Cari div.content-box...")
            boxes = page.query_selector_all("div.content-box")
            logger.info(f"[STUDENTSITE] content-box ditemukan: {len(boxes)}")

            # Strategi 2: area berita sesuai user (div ke-9 di div ke-2)
            if not boxes:
                logger.info("[STUDENTSITE] Coba area berita div:nth-child(9)...")
                area = page.query_selector(
                    "body > div:nth-child(2) > div:nth-child(9)"
                )
                if area:
                    boxes_raw = area.query_selector_all("div")
                    # Filter hanya yang punya h3 atau judul
                    boxes = [b for b in boxes_raw if b.query_selector("h3, a[href]")]
                    logger.info(f"[STUDENTSITE] Dari area div[9]: {len(boxes)} elemen")

            # Strategi 3: fallback cari h3 + link
            if not boxes:
                logger.info("[STUDENTSITE] Fallback: cari semua h3 dengan link...")
                h3_els = page.query_selector_all("h3 a[href]")
                logger.info(f"[STUDENTSITE] h3 a: {len(h3_els)}")

                seen = set()
                for el in h3_els:
                    href  = _abs(el.get_attribute("href") or "")
                    # Coba ambil teks dari font atau b di dalam link
                    font_el = el.query_selector("font, b font, b b font")
                    judul = ""
                    if font_el:
                        judul = font_el.inner_text().strip()
                    if not judul:
                        judul = el.inner_text().strip()
                    if not href or href in seen or not judul or len(judul) < 5:
                        continue
                    seen.add(href)
                    item = {
                        "judul"   : judul,
                        "tanggal" : "",
                        "link"    : href,
                        "sumber"  : SUMBER,
                        "isi"     : "",
                        "author"  : "",
                        "file_url": "",
                    }
                    hasil.append(item)
                    if limit and len(hasil) >= limit:
                        break

                if hasil:
                    logger.info(f"[STUDENTSITE] Fallback h3: {len(hasil)} item")
                    browser.close()
                    return hasil

            if not boxes:
                logger.warning("[STUDENTSITE] Tidak ada konten ditemukan. Simpan debug HTML.")
                with open(DEBUG_HTML_FILE, "w", encoding="utf-8") as f:
                    f.write(html)
                logger.warning(f"[STUDENTSITE] Debug: {os.path.abspath(DEBUG_HTML_FILE)}")
                browser.close()
                return []

            if limit:
                boxes = boxes[:limit]

            for box in boxes:
                item = {
                    "judul"   : "",
                    "tanggal" : "",
                    "link"    : URL,
                    "sumber"  : SUMBER,
                    "isi"     : "",
                    "author"  : "",
                    "file_url": "",
                }
                try:
                    # Judul + link dari h3.content-box-header a
                    # Struktur: h3 > a > b > b > font
                    link_el = box.query_selector("h3.content-box-header a")

                    if link_el:
                        href = link_el.get_attribute("href") or ""
                        item["link"] = _abs(href) if href else URL

                        # Ambil teks dari nested font/b
                        font_el = box.query_selector(
                            "h3.content-box-header a font, "
                            "h3.content-box-header a b font, "
                            "h3.content-box-header a b b font"
                        )
                        if font_el:
                            item["judul"] = font_el.inner_text().strip()
                        else:
                            item["judul"] = link_el.inner_text().strip()
                    else:
                        # Coba langsung dari h3
                        h3_el = box.query_selector("h3.content-box-header, h3")
                        if h3_el:
                            a_el = h3_el.query_selector("a")
                            if a_el:
                                href = a_el.get_attribute("href") or ""
                                item["link"] = _abs(href) if href else URL
                            font_el = h3_el.query_selector("font")
                            item["judul"] = (
                                font_el.inner_text().strip() if font_el
                                else h3_el.inner_text().strip()
                            )

                    # Tanggal dari div.font-gray
                    tgl_el = box.query_selector("div.font-gray")
                    if tgl_el:
                        raw = tgl_el.inner_text().strip()
                        match = re.search(r"pada\s+(\d{4}-\d{2}-\d{2})", raw)
                        if match:
                            item["tanggal"] = match.group(1)
                        elif raw:
                            item["tanggal"] = raw[:50]

                    # Isi dari paragraf
                    isi_el = box.query_selector(
                        "p, div.content-box-body, div.content-box-content"
                    )
                    if isi_el:
                        item["isi"] = isi_el.inner_text().strip()[:300]

                    # Jika link masih homepage, cari link detail internal di dalam box
                    if item["link"] in [URL, BASE_URL, BASE_URL + "/"]:
                        detail_el = box.query_selector(
                            "a[href*='/site/berita/'], "
                            "a[href*='/berita/'], "
                            "a[href*='/news/']"
                        )
                        if detail_el:
                            d_href = detail_el.get_attribute("href") or ""
                            if d_href:
                                item["link"] = _abs(d_href)

                    # Link eksternal di dalam konten → file_url
                    # (misalnya link ke lsp.gunadarma.ac.id atau situs lain)
                    ext_links = box.query_selector_all("a[href^='http']")
                    for ext_el in ext_links:
                        ext_href = ext_el.get_attribute("href") or ""
                        if ext_href and "studentsite.gunadarma.ac.id" not in ext_href:
                            if ext_href != item["link"]:
                                item["file_url"] = ext_href
                                break  # Ambil yang pertama

                    if not item["judul"]:
                        continue

                    logger.info(f"[STUDENTSITE] OK: {item['judul'][:60]!r}")

                except Exception as e:
                    logger.warning(f"[STUDENTSITE] Error proses box: {e}")
                    continue

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
