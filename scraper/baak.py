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


def _parse_detail_html(html: str, item: dict, detail_url: str = ""):
    """Parse HTML halaman detail BAAK dan lengkapi field item."""
    soup = BeautifulSoup(html, "html.parser")
    
    logger.info(f"[BAAK] Detail URL: {detail_url}")

    # Judul
    h3 = soup.find("h3", class_=re.compile("text-bold"))
    if h3:
        t = h3.get_text(strip=True)
        if t:
            item["judul"] = t

    # Tanggal: .text-middle.inset-left-10.text-italic.text-black
    tgl = soup.find(class_=re.compile(
        r"text-middle.*inset-left-10.*text-italic.*text-black"
    ))
    if tgl:
        item["tanggal"] = tgl.get_text(strip=True)

    # Author: .text-middle.inset-left-10.text-italic.text-primary
    auth = soup.find(class_=re.compile(
        r"text-middle.*inset-left-10.*text-italic.*text-primary"
    ))
    if auth:
        item["author"] = auth.get_text(strip=True)

    # Isi: Strategi bertingkat dengan fallback
    isi_text = ""
    strategy_used = ""
    
    # Strategi 1: Cari semua div.offset-md-top-20
    isi_divs = soup.find_all("div", class_="offset-md-top-20")
    logger.info(f"[BAAK] Elemen div.offset-md-top-20 ditemukan: {len(isi_divs)}")
    
    if len(isi_divs) >= 2:
        # Ambil div kedua (index 1) yang biasanya berisi isi berita
        # PENTING: gunakan separator="\n" untuk mempertahankan newline
        isi_el = isi_divs[1]
        isi_text = isi_el.get_text(separator="\n", strip=True)
        strategy_used = "div.offset-md-top-20 ke-2"
        logger.info(f"[BAAK] Strategi: {strategy_used}")
        
    elif len(isi_divs) == 1:
        # Jika hanya ada 1, cek apakah berisi metadata atau isi
        first_div = isi_divs[0]
        # Jika berisi <ul> atau <li>, kemungkinan metadata, skip
        if first_div.find("ul") or first_div.find("li"):
            logger.warning("[BAAK] Div offset-md-top-20 berisi metadata (ul/li), skip")
            isi_text = ""
        else:
            isi_text = first_div.get_text(separator="\n", strip=True)
            strategy_used = "div.offset-md-top-20 ke-1"
            logger.info(f"[BAAK] Strategi: {strategy_used}")
    
    # Fallback 2: Jika isi masih kosong, coba .cell-sm-8.cell-md-8.text-left div.offset-md-top-20
    if not isi_text:
        logger.warning("[BAAK] Strategi 1 gagal, coba fallback 2: .cell-sm-8 .cell-md-8 .text-left div.offset-md-top-20")
        parent = soup.find("div", class_=re.compile(r"cell-sm-8.*cell-md-8.*text-left"))
        if parent:
            isi_divs_nested = parent.find_all("div", class_="offset-md-top-20")
            if len(isi_divs_nested) >= 2:
                isi_el = isi_divs_nested[1]
                isi_text = isi_el.get_text(separator="\n", strip=True)
                strategy_used = "fallback: parent .cell-sm-8 div ke-2"
                logger.info(f"[BAAK] Strategi: {strategy_used}")
    
    # Fallback 3: Jika masih kosong, ambil dari .cell-sm-8.cell-md-8.text-left langsung
    if not isi_text:
        logger.warning("[BAAK] Strategi 2 gagal, coba fallback 3: .cell-sm-8 .cell-md-8 .text-left")
        parent = soup.find("div", class_=re.compile(r"cell-sm-8.*cell-md-8.*text-left"))
        if parent:
            # Hapus elemen metadata (h3, ul, li) dulu
            for tag in parent.find_all(["h3", "ul", "li", "hr"]):
                tag.decompose()
            isi_text = parent.get_text(separator="\n", strip=True)
            strategy_used = "fallback: parent .cell-sm-8 (cleaned)"
            logger.info(f"[BAAK] Strategi: {strategy_used}")
    
    # Validasi: Jangan simpan jika hanya berisi tanggal/author
    if isi_text:
        # Filter jika isi HANYA berisi pola tanggal/author (contoh: "15/05/2026 Admin" atau "15/05/2026Admin")
        # Tapi cek dulu apakah ada newline - jika ada newline berarti bukan cuma tanggal/author
        if "\n" not in isi_text and re.match(r"^\d{2}/\d{2}/\d{4}\s*\w+$", isi_text):
            logger.warning(f"[BAAK] Isi hanya berisi tanggal/author: '{isi_text}', dikosongkan")
            isi_text = ""
    
    # Log hasil
    logger.info(f"[BAAK] Panjang isi: {len(isi_text)} karakter")
    
    if isi_text:
        logger.info(f"[BAAK] Preview isi: {isi_text[:200]}...")
        item["isi"] = isi_text
    else:
        logger.warning("[BAAK] Isi kosong setelah ekstraksi detail page.")
        item["isi"] = ""
        # Simpan debug HTML jika isi kosong
        with open("debug_baak_detail.html", "w", encoding="utf-8") as f:
            f.write(html)
        logger.warning(f"[BAAK] Debug HTML disimpan ke: {os.path.abspath('debug_baak_detail.html')}")

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
            "tanggal" : "",
            "link"    : href,
            "sumber"  : SUMBER,
            "isi"     : "",
            "author"  : "",
            "file_url": "",
        }
        # WAJIB ambil detail page untuk BAAK (tanggal, author, isi dari selector yang benar)
        time.sleep(3)
        detail_html = get_html_via_flaresolverr(href)
        if detail_html:
            _parse_detail_html(detail_html, item, detail_url=href)
            logger.info(f"[BAAK] OK (detail): {item['judul'][:60]}")
        else:
            logger.warning(f"[BAAK] Gagal detail: {href}")
            # Jika gagal, kosongkan atau beri placeholder
            if not item["isi"]:
                item["isi"] = "Tidak tersedia"
            if not item["tanggal"]:
                item["tanggal"] = "Tidak tersedia"
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
                    "tanggal" : "",
                    "link"    : href,
                    "sumber"  : SUMBER,
                    "isi"     : "",
                    "author"  : "",
                    "file_url": "",
                }
                # WAJIB ambil detail page untuk BAAK (tanggal, author, isi dari selector yang benar)
                try:
                    dpage = ctx.new_page()
                    dpage.goto(href, timeout=25000, wait_until="domcontentloaded")
                    _wait_cloudflare(dpage, max_wait=12000)
                    dpage.wait_for_timeout(800)
                    _parse_detail_html(dpage.content(), item, detail_url=href)
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
                    if not item["tanggal"]:
                        item["tanggal"] = "Tidak tersedia"
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
