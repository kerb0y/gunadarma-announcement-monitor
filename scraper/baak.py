"""
scraper/baak.py
Scraper untuk website BAAK Universitas Gunadarma.
URL: https://baak.gunadarma.ac.id/beritabaak

Proteksi: Cloudflare Managed Challenge.
Strategi utama  : FlareSolverr (jika berjalan di localhost:8191)
Strategi fallback: Playwright headless (jika FlareSolverr tidak tersedia)

Selector aktual (diverifikasi Juni 2026):
  List  : .cell-md-8 article h6 + a[href*=/beritabaak/]
  Detail: h3.text-bold (judul), div.offset-md-top-20 (isi),
          .text-italic.text-black (tanggal), .text-italic.text-primary (author)
"""

import re
import os
import time
from typing import List, Dict, Optional
from bs4 import BeautifulSoup

from utils.logger import logger
from utils.flaresolverr import is_flaresolverr_running, get_html_via_flaresolverr

SUMBER          = "BAAK"
URL             = "https://baak.gunadarma.ac.id/beritabaak"
BASE_URL        = "https://baak.gunadarma.ac.id"
DEBUG_HTML_FILE = "debug_baak.html"


def _abs(href: str) -> str:
    if not href:
        return ""
    href = href.strip()
    if href.startswith("http"):
        return href
    if href.startswith("/"):
        return BASE_URL + href
    return BASE_URL + "/" + href


def _parse_list_html(html: str) -> List[tuple]:
    """
    Parse HTML halaman list BAAK.
    Kembalikan list tuple: (judul, href, tanggal, isi_singkat)
    """
    soup = BeautifulSoup(html, "html.parser")
    link_data = []
    seen = set()

    for a in soup.find_all("a", href=True):
        href = _abs(a["href"])
        if not re.search(r"/beritabaak/\d+", href) or href in seen:
            continue
        seen.add(href)

        judul   = ""
        tanggal = ""
        isi     = ""

        # Cari judul dari h6 di ancestor article atau div post-news
        ancestor = (
            a.find_parent("article")
            or a.find_parent("div", class_=re.compile("post-news"))
            or a.find_parent("div", class_=re.compile("cell-sm"))
        )
        if ancestor:
            h6 = ancestor.find("h6")
            if h6:
                judul = h6.get_text(strip=True)
            span = ancestor.find("span", class_=re.compile("date|time|tanggal"))
            if span:
                tanggal = span.get_text(strip=True)
            p = ancestor.find("p")
            if p:
                isi = p.get_text(strip=True)[:300]

        if not judul:
            judul = a.get_text(strip=True)

        if judul and len(judul) >= 3:
            link_data.append((judul, href, tanggal, isi))

    return link_data


def _parse_detail_html(html: str, item: dict):
    """Parse HTML halaman detail BAAK dan lengkapi field item."""
    soup = BeautifulSoup(html, "html.parser")

    # Judul
    h3 = soup.find("h3", class_=re.compile("text-bold"))
    if h3:
        t = h3.get_text(strip=True)
        if t:
            item["judul"] = t

    # Tanggal
    tgl = soup.find(class_=re.compile(
        r"text-italic.*text-black|text-black.*text-italic"
    ))
    if tgl:
        item["tanggal"] = tgl.get_text(strip=True)

    # Author
    auth = soup.find(class_=re.compile(
        r"text-italic.*text-primary|text-primary.*text-italic"
    ))
    if auth:
        item["author"] = auth.get_text(strip=True)

    # Isi
    isi_el = (
        soup.find("div", class_="offset-md-top-20")
        or soup.find(class_=re.compile(r"cell-sm-8.*cell-md-8.*text-left"))
        or soup.find(class_="post-content")
    )
    if isi_el:
        item["isi"] = isi_el.get_text(strip=True)[:500]

    # File
    file_a = soup.find("a", href=re.compile(r"\.pdf|download|unduh"))
    if file_a:
        item["file_url"] = _abs(file_a.get("href", ""))


def _scrape_dengan_flaresolverr(limit: Optional[int]) -> List[Dict]:
    """Scraping menggunakan FlareSolverr."""
    logger.info("[BAAK] Strategi: FlareSolverr")

    html = get_html_via_flaresolverr(URL)
    if not html:
        logger.error("[BAAK] FlareSolverr gagal ambil halaman list.")
        return []

    logger.info(f"[BAAK] HTML list: {len(html):,} char")
    link_data = _parse_list_html(html)
    logger.info(f"[BAAK] Link berita ditemukan: {len(link_data)}")

    if not link_data:
        with open(DEBUG_HTML_FILE, "w", encoding="utf-8") as f:
            f.write(html)
        logger.warning(f"[BAAK] Tidak ada link. Debug: {os.path.abspath(DEBUG_HTML_FILE)}")
        return []

    if limit:
        link_data = link_data[:limit]

    hasil = []
    for judul_list, href, tanggal_list, isi_list in link_data:
        item = {
            "judul"   : judul_list,
            "tanggal" : tanggal_list or "Tidak tersedia",
            "link"    : href,
            "sumber"  : SUMBER,
            "isi"     : isi_list,
            "author"  : "",
            "file_url": "",
        }
        # OPTIMISASI: Hanya ambil detail jika isi kosong atau sangat pendek
        # Ini mengurangi request FlareSolverr dan menghemat waktu
        if not item["isi"] or len(item["isi"]) < 50:
            # Jeda singkat sebelum request berikutnya
            time.sleep(3)
            detail_html = get_html_via_flaresolverr(href)
            if detail_html:
                _parse_detail_html(detail_html, item)
                logger.info(f"[BAAK] OK (detail): {item['judul'][:60]}")
            else:
                logger.warning(f"[BAAK] Gagal detail, pakai data list: {href}")
                # Jika isi masih kosong, beri placeholder
                if not item["isi"]:
                    item["isi"] = "Tidak tersedia"
        else:
            # Data dari list sudah cukup
            logger.info(f"[BAAK] OK (list): {item['judul'][:60]}")
        hasil.append(item)

    return hasil


def _wait_cloudflare(page, max_wait: int = 20000):
    """Tunggu sampai Cloudflare challenge selesai."""
    try:
        page.wait_for_function(
            "!document.title.includes('Just a moment') && "
            "!document.title.includes('Tunggu sebentar')",
            timeout=max_wait
        )
        logger.info(f"[BAAK] Cloudflare selesai. Title: {page.title()}")
    except Exception:
        logger.warning(f"[BAAK] Cloudflare masih aktif setelah {max_wait}ms.")


def _scrape_dengan_playwright(limit: Optional[int]) -> List[Dict]:
    """Scraping menggunakan Playwright (fallback)."""
    logger.info("[BAAK] Strategi: Playwright (fallback)")
    hasil = []
    browser = None

    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox",
                      "--disable-blink-features=AutomationControlled"]
            )
            ctx = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/125.0.0.0 Safari/537.36"
                ),
                extra_http_headers={
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8",
                }
            )
            page = ctx.new_page()
            try:
                from playwright_stealth import Stealth
                Stealth().apply_stealth_sync(page)
            except Exception:
                pass

            try:
                page.goto(URL, timeout=50000, wait_until="domcontentloaded")
                _wait_cloudflare(page, max_wait=20000)
                page.wait_for_timeout(1500)
            except PWTimeout as e:
                logger.error(f"[BAAK] Timeout buka halaman: {e}")
                browser.close()
                return []

            html = page.content()
            title = page.title()
            if "Just a moment" in title or "Tunggu sebentar" in title:
                logger.warning("[BAAK] Cloudflare aktif, tidak bisa bypass. Simpan debug HTML.")
                with open(DEBUG_HTML_FILE, "w", encoding="utf-8") as f:
                    f.write(html)
                logger.warning(f"[BAAK] Debug: {os.path.abspath(DEBUG_HTML_FILE)}")
                browser.close()
                return []

            link_data = _parse_list_html(html)
            logger.info(f"[BAAK] Link berita: {len(link_data)}")
            if not link_data:
                with open(DEBUG_HTML_FILE, "w", encoding="utf-8") as f:
                    f.write(html)
                browser.close()
                return []

            if limit:
                link_data = link_data[:limit]

            # Loop dengan tuple 4 elemen (judul, href, tanggal, isi)
            for judul_list, href, tanggal_list, isi_list in link_data:
                item = {
                    "judul"   : judul_list,
                    "tanggal" : tanggal_list or "Tidak tersedia",
                    "link"    : href,
                    "sumber"  : SUMBER,
                    "isi"     : isi_list,
                    "author"  : "",
                    "file_url": "",
                }
                # OPTIMISASI: Skip detail jika isi sudah cukup dari list
                if item["isi"] and len(item["isi"]) >= 50:
                    logger.info(f"[BAAK] OK (list): {item['judul'][:60]}")
                    hasil.append(item)
                    continue
                    
                try:
                    dpage = ctx.new_page()
                    dpage.goto(href, timeout=25000, wait_until="domcontentloaded")
                    _wait_cloudflare(dpage, max_wait=12000)
                    dpage.wait_for_timeout(800)
                    _parse_detail_html(dpage.content(), item)
                    dpage.close()
                    logger.info(f"[BAAK] OK (detail): {item['judul'][:60]}")
                except Exception as e:
                    logger.warning(f"[BAAK] Gagal detail {href}: {e}")
                    try:
                        dpage.close()
                    except Exception:
                        pass
                    # Jika isi masih kosong, beri placeholder
                    if not item["isi"]:
                        item["isi"] = "Tidak tersedia"
                hasil.append(item)

            browser.close()

    except Exception as e:
        logger.error(f"[BAAK] Playwright ERROR: {type(e).__name__}: {e}")
        if browser:
            try:
                browser.close()
            except Exception:
                pass

    return hasil


def scrape_baak(limit: Optional[int] = None) -> List[Dict]:
    logger.info(f"[BAAK] Mulai scraping: {URL}")

    if is_flaresolverr_running():
        logger.info("[BAAK] FlareSolverr terdeteksi di localhost:8191.")
        hasil = _scrape_dengan_flaresolverr(limit)
        if hasil:
            logger.info(f"[BAAK] Selesai via FlareSolverr. Total: {len(hasil)}")
            return hasil
        logger.warning("[BAAK] FlareSolverr gagal, coba Playwright...")
    else:
        logger.warning(
            "[BAAK] FlareSolverr tidak berjalan. "
            "Jalankan: docker run -d --name flaresolverr -p 8191:8191 "
            "ghcr.io/flaresolverr/flaresolverr:latest"
        )

    hasil = _scrape_dengan_playwright(limit)
    logger.info(f"[BAAK] Selesai via Playwright. Total: {len(hasil)}")
    return hasil
