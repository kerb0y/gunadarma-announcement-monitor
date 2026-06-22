"""
scraper/pendaftaran.py
Scraper untuk website Pendaftaran Universitas Gunadarma.
URL: https://pendaftaran.gunadarma.ac.id/2026/home/berita

Proteksi: Cloudflare Managed Challenge.
Strategi utama  : FlareSolverr (jika berjalan di localhost:8191)
Strategi fallback: Playwright headless

Selector aktual (diverifikasi Juni 2026 dari user):
  List: body > div:nth-child(4) > div > div > div:nth-child(2) > div  (kartu berita)
  Detail: .post-title (judul), #startedby (author),
          body > div > ... > div:nth-child(2) > p:nth-child(2) (isi)
  Referensi: a[href*='youtube.com'], a[href*='.pdf'] → file_url

Catatan: website hanya memiliki sekitar 2 berita per Juni 2026.
Sumber: PENDAFTARAN
"""

import re
import os
from typing import List, Dict, Optional
from bs4 import BeautifulSoup

from utils.logger import logger
from utils.flaresolverr import is_flaresolverr_running, get_html_via_flaresolverr

SUMBER          = "PENDAFTARAN"
URL             = "https://pendaftaran.gunadarma.ac.id/2026/home/berita"
BASE_URL        = "https://pendaftaran.gunadarma.ac.id"
DEBUG_HTML_FILE = "debug_pendaftaran.html"


def _abs(href: str) -> str:
    if not href:
        return ""
    href = href.strip()
    if href.startswith("http"):
        return href
    if href.startswith("/"):
        return BASE_URL + href
    return BASE_URL + "/" + href


def _parse_list_html(html: str) -> List[Dict]:
    """Parse HTML halaman list Pendaftaran, kembalikan list item awal."""
    soup = BeautifulSoup(html, "html.parser")
    hasil = []
    seen = set()

    # Strategi utama: cari semua link ke detailBerita
    for a in soup.find_all("a", href=True):
        href = _abs(a["href"])
        if "detailBerita" not in href or href in seen:
            continue
        seen.add(href)

        # Coba ambil judul dari parent card
        judul = ""
        card = a.find_parent("div")
        if card:
            # Cari heading atau teks pertama yang cukup panjang
            for tag in ["h1","h2","h3","h4","h5","h6"]:
                h = card.find(tag)
                if h:
                    judul = h.get_text(strip=True)
                    break
            if not judul:
                # Ambil teks pertama yang cukup panjang dari div pertama
                first_div = card.find("div")
                if first_div:
                    t = first_div.get_text(strip=True)
                    if len(t) > 5:
                        judul = t[:100]
        if not judul:
            judul = a.get_text(strip=True) or "Berita Pendaftaran"

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

    if hasil:
        return hasil

    # Fallback: ambil kartu dari div:nth-child(2) container
    # Cari container yang punya div anak berisi link berita
    containers = soup.find_all("div")
    for cont in containers:
        children = [c for c in cont.children if hasattr(c, "find_all")]
        if len(children) >= 2:
            for child in children:
                link_el = child.find("a", href=re.compile("detailBerita"))
                if link_el:
                    href = _abs(link_el.get("href", ""))
                    if href in seen:
                        continue
                    seen.add(href)

                    judul_el = child.find(["h1","h2","h3","h4","h5","h6"])
                    judul = judul_el.get_text(strip=True) if judul_el else ""
                    if not judul:
                        # ambil teks pertama dari child
                        judul = child.get_text(strip=True)[:100]

                    isi_el = child.find("p")
                    isi = isi_el.get_text(strip=True)[:300] if isi_el else ""

                    item = {
                        "judul"   : judul,
                        "tanggal" : "",
                        "link"    : href,
                        "sumber"  : SUMBER,
                        "isi"     : isi,
                        "author"  : "",
                        "file_url": "",
                    }
                    hasil.append(item)

    return hasil


def _parse_detail_html(html: str, item: dict):
    """Parse HTML halaman detail Pendaftaran dan lengkapi field item."""
    soup = BeautifulSoup(html, "html.parser")

    # Judul: .post-title
    judul_el = soup.find(class_="post-title") or soup.find("h1") or soup.find("h2")
    if judul_el:
        t = judul_el.get_text(strip=True)
        if t:
            item["judul"] = t

    # Author: #startedby
    auth_el = soup.find(id="startedby") or soup.find(class_=re.compile("author|posted-by"))
    if auth_el:
        item["author"] = auth_el.get_text(strip=True)

    # Isi: cari paragraf utama konten
    if not item["isi"]:
        # Coba selector spesifik user: div ke-4 > div > div > div > div > div > div:nth-child(2) > p
        paras = soup.find_all("p")
        for p in paras:
            teks = p.get_text(strip=True)
            if len(teks) > 50:  # ambil paragraf yang cukup panjang
                item["isi"] = teks[:500]
                break

    # Referensi / file: YouTube, PDF, Google Drive
    if not item["file_url"]:
        ref_a = soup.find("a", href=re.compile(
            r"youtube\.com|youtu\.be|\.pdf|drive\.google|docs\.google"
        ))
        if ref_a:
            item["file_url"] = ref_a.get("href", "")


def _scrape_dengan_flaresolverr(limit: Optional[int]) -> List[Dict]:
    logger.info("[PENDAFTARAN] Menggunakan FlareSolverr...")

    html = get_html_via_flaresolverr(URL)
    if not html:
        logger.error("[PENDAFTARAN] FlareSolverr gagal.")
        return []

    logger.info(f"[PENDAFTARAN] HTML: {len(html):,} char")

    # Cek apakah masih Cloudflare
    if "Just a moment" in html or "cf-browser-verification" in html:
        logger.warning("[PENDAFTARAN] FlareSolverr tidak berhasil bypass Cloudflare.")
        with open(DEBUG_HTML_FILE, "w", encoding="utf-8") as f:
            f.write(html)
        return []

    items = _parse_list_html(html)
    logger.info(f"[PENDAFTARAN] Item ditemukan: {len(items)}")

    if not items:
        with open(DEBUG_HTML_FILE, "w", encoding="utf-8") as f:
            f.write(html)
        logger.warning(f"[PENDAFTARAN] Tidak ada item. Debug: {os.path.abspath(DEBUG_HTML_FILE)}")
        return []

    if limit:
        items = items[:limit]

    # Buka detail setiap item
    for item in items:
        href = item.get("link", "")
        if not href or "detailBerita" not in href:
            continue
        detail_html = get_html_via_flaresolverr(href)
        if detail_html:
            _parse_detail_html(detail_html, item)
            logger.info(f"[PENDAFTARAN] OK: {item['judul'][:60]!r}")
        else:
            logger.warning(f"[PENDAFTARAN] Gagal detail: {href}")

    return items


def _wait_cloudflare(page, max_wait: int = 30000):
    try:
        page.wait_for_function(
            "!document.title.includes('Just a moment') && "
            "!document.title.includes('Tunggu sebentar')",
            timeout=max_wait
        )
        logger.info(f"[PENDAFTARAN] Cloudflare selesai: {page.title()!r}")
    except Exception:
        logger.warning(f"[PENDAFTARAN] Cloudflare masih aktif setelah {max_wait}ms.")


def _scrape_dengan_playwright(limit: Optional[int]) -> List[Dict]:
    logger.info("[PENDAFTARAN] Menggunakan Playwright (fallback)...")
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
            ctx = browser.new_context(user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
            ))
            page = ctx.new_page()
            try:
                from playwright_stealth import Stealth
                Stealth().apply_stealth_sync(page)
            except Exception:
                pass

            try:
                page.goto(URL, timeout=60000, wait_until="domcontentloaded")
                _wait_cloudflare(page, max_wait=30000)
                page.wait_for_timeout(3000)
            except PWTimeout as e:
                logger.error(f"[PENDAFTARAN] TIMEOUT: {e}")
                browser.close()
                return []

            html = page.content()
            if "Just a moment" in page.title() or "Tunggu sebentar" in page.title():
                logger.warning("[PENDAFTARAN] Cloudflare aktif. Simpan debug HTML.")
                with open(DEBUG_HTML_FILE, "w", encoding="utf-8") as f:
                    f.write(html)
                browser.close()
                return []

            items = _parse_list_html(html)
            logger.info(f"[PENDAFTARAN] Item: {len(items)}")
            if not items:
                with open(DEBUG_HTML_FILE, "w", encoding="utf-8") as f:
                    f.write(html)
                browser.close()
                return []

            if limit:
                items = items[:limit]

            for item in items:
                href = item.get("link", "")
                if not href or "detailBerita" not in href:
                    hasil.append(item)
                    continue
                try:
                    dpage = ctx.new_page()
                    dpage.goto(href, timeout=30000, wait_until="domcontentloaded")
                    _wait_cloudflare(dpage, max_wait=20000)
                    dpage.wait_for_timeout(2000)
                    _parse_detail_html(dpage.content(), item)
                    dpage.close()
                    logger.info(f"[PENDAFTARAN] OK: {item['judul'][:60]!r}")
                except Exception as e:
                    logger.warning(f"[PENDAFTARAN] Gagal detail {href}: {e}")
                    try:
                        dpage.close()
                    except Exception:
                        pass
                hasil.append(item)

            browser.close()

    except Exception as e:
        logger.error(f"[PENDAFTARAN] Playwright ERROR: {type(e).__name__}: {e}")
        if browser:
            try:
                browser.close()
            except Exception:
                pass

    return hasil


def scrape_pendaftaran(limit: Optional[int] = None) -> List[Dict]:
    logger.info(f"[PENDAFTARAN] Mulai scraping: {URL}")

    if is_flaresolverr_running():
        logger.info("[PENDAFTARAN] FlareSolverr terdeteksi.")
        hasil = _scrape_dengan_flaresolverr(limit)
        if hasil:
            logger.info(f"[PENDAFTARAN] Selesai via FlareSolverr. Total: {len(hasil)}")
            return hasil
        logger.warning("[PENDAFTARAN] FlareSolverr gagal, coba Playwright...")
    else:
        logger.warning("[PENDAFTARAN] FlareSolverr tidak berjalan. "
                       "Jalankan: docker run -d --name flaresolverr -p 8191:8191 "
                       "ghcr.io/flaresolverr/flaresolverr:latest")

    hasil = _scrape_dengan_playwright(limit)
    logger.info(f"[PENDAFTARAN] Selesai via Playwright. Total: {len(hasil)}")
    return hasil
