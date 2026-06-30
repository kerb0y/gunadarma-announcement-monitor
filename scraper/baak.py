"""
scraper/baak.py
Scraper untuk website BAAK Universitas Gunadarma.
URL: https://baak.gunadarma.ac.id/beritabaak

Alur:
  1. Buka halaman list: https://baak.gunadarma.ac.id/beritabaak
  2. Tunggu Cloudflare Managed Challenge selesai (jika muncul)
  3. Kumpulkan maks. 5 link detail: /beritabaak/<angka>
  4. Buka setiap halaman detail dan ekstrak:
       - judul  : h3.text-bold
       - tanggal: .text-middle.inset-left-10.text-italic.text-black
       - author : .text-middle.inset-left-10.text-italic.text-primary
       - isi    : div.offset-md-top-20
  5. Jika detail gagal → fallback data dari halaman list

Proteksi: Website dilindungi Cloudflare Managed Challenge.
          Scraper menunggu challenge selesai hingga 25 detik.
"""

import re
import os
from typing import List, Dict, Optional

from utils.logger import logger

SUMBER          = "BAAK"
URL             = "https://baak.gunadarma.ac.id/beritabaak"
BASE_URL        = "https://baak.gunadarma.ac.id"
DEBUG_HTML_FILE = "debug_baak.html"


def _abs(href: str) -> str:
    """Normalisasi URL relatif menjadi URL absolut."""
    if not href:
        return ""
    href = href.strip()
    if href.startswith("http"):
        return href
    if href.startswith("/"):
        return BASE_URL + href
    return BASE_URL + "/" + href


def _tunggu_cloudflare(page, max_wait_ms: int = 25000):
    """
    Tunggu sampai Cloudflare challenge selesai.
    Cloudflare menampilkan halaman 'Just a moment...' / 'Tunggu sebentar...'
    sebelum redirect ke konten asli.
    """
    try:
        page.wait_for_function(
            "!document.title.includes('Just a moment') && "
            "!document.title.includes('Tunggu sebentar') && "
            "!document.title.includes('moment...')",
            timeout=max_wait_ms
        )
        logger.info(f"[BAAK] Cloudflare selesai. Title: {page.title()!r}")
    except Exception:
        logger.warning(f"[BAAK] Cloudflare belum selesai setelah {max_wait_ms}ms.")


def _masih_cloudflare(page) -> bool:
    """Cek apakah halaman masih di challenge Cloudflare."""
    title = page.title()
    return any(kw in title for kw in ["Just a moment", "Tunggu sebentar", "moment..."])


def _ambil_link_dari_list(page) -> List[tuple]:
    """
    Ambil semua link berita dari halaman list BAAK.
    Kembalikan list of (judul_list, href_absolut).
    """
    link_data = []
    seen = set()

    # === Strategi 1: link langsung dengan pola /beritabaak/<angka> ===
    all_a = page.query_selector_all("a[href]")
    logger.info(f"[BAAK] Total <a> di halaman list: {len(all_a)}")

    for el in all_a:
        href = _abs(el.get_attribute("href") or "")
        if not href or href in seen:
            continue
        if not re.search(r"/beritabaak/\d+", href):
            continue

        # Ambil teks judul dari elemen atau parent terdekat
        judul = el.inner_text().strip()

        # Jika teks link pendek, cari di parent article/div
        if not judul or len(judul) < 3:
            try:
                # Coba ambil dari h6 terdekat
                parent_art = el.evaluate_handle(
                    "el => el.closest('article') || el.closest('.post-news-body') || el.parentElement"
                )
                h6_els = page.query_selector_all("article h6, .post-news-body h6")
                if h6_els:
                    judul = h6_els[0].inner_text().strip()
            except Exception:
                pass

        if not judul:
            judul = f"Berita BAAK #{len(link_data) + 1}"

        seen.add(href)
        link_data.append((judul, href))

    # === Strategi 2: selector article h6 jika link tidak ditemukan ===
    if not link_data:
        logger.info("[BAAK] Strategi 2: cari article h6 + link...")
        articles = page.query_selector_all(
            ".cell-md-8 article, "
            "div[class*='post-news'] article, "
            ".range.text-sm-left article, "
            "div[class*='cell-sm-6'] div[class*='post-news-body']"
        )
        logger.info(f"[BAAK] Article ditemukan: {len(articles)}")
        for art in articles:
            link_el = art.query_selector("a[href]")
            h6_el   = art.query_selector("h6")
            if not link_el:
                continue
            href  = _abs(link_el.get_attribute("href") or "")
            judul = h6_el.inner_text().strip() if h6_el else link_el.inner_text().strip()
            if href and href not in seen and re.search(r"/beritabaak/\d+", href):
                seen.add(href)
                link_data.append((judul or "Berita BAAK", href))

    logger.info(f"[BAAK] Link berita ditemukan: {len(link_data)}")
    return link_data


def _ambil_data_list(page, href: str) -> Dict:
    """
    Ambil data fallback dari halaman list (tanpa membuka detail).
    Gunakan jika halaman detail gagal dibuka.
    """
    # Coba ambil deskripsi singkat dari elemen list yang mengandung link ini
    isi_singkat = ""
    try:
        art = page.query_selector(f"article:has(a[href*='{href.split('/')[-1]}'])")
        if art:
            p_el = art.query_selector("p")
            if p_el:
                isi_singkat = p_el.inner_text().strip()[:300]
    except Exception:
        pass
    return {"isi_fallback": isi_singkat}


def _buka_detail(ctx, href: str) -> Optional[Dict]:
    """
    Buka halaman detail satu berita BAAK dan ekstrak semua field.

    Returns:
        Dict dengan judul, tanggal, author, isi — atau None jika gagal.
    """
    try:
        from playwright.sync_api import TimeoutError as PWTimeout
        dpage = ctx.new_page()
        logger.info(f"[BAAK] Buka detail: {href}")

        dpage.goto(href, timeout=30000, wait_until="domcontentloaded")
        _tunggu_cloudflare(dpage, max_wait_ms=15000)
        dpage.wait_for_timeout(1500)

        if _masih_cloudflare(dpage):
            logger.warning(f"[BAAK] Detail masih di Cloudflare: {href}")
            dpage.close()
            return None

        # ── Judul ───────────────────────────────────────────────────────
        judul = ""
        judul_el = dpage.query_selector("h3.text-bold")
        if judul_el:
            judul = judul_el.inner_text().strip()
        if not judul:
            judul_el2 = dpage.query_selector("h1, h2")
            if judul_el2:
                judul = judul_el2.inner_text().strip()

        # ── Tanggal ──────────────────────────────────────────────────────
        tanggal = ""
        tgl_el = dpage.query_selector(
            ".text-middle.inset-left-10.text-italic.text-black, "
            ".text-italic.text-black, "
            "time, .post-date, .date"
        )
        if tgl_el:
            tanggal = tgl_el.inner_text().strip()

        # ── Author ───────────────────────────────────────────────────────
        author = ""
        auth_el = dpage.query_selector(
            ".text-middle.inset-left-10.text-italic.text-primary, "
            ".text-italic.text-primary, "
            ".author, .posted-by"
        )
        if auth_el:
            author = auth_el.inner_text().strip()

        # ── Isi berita ───────────────────────────────────────────────────
        isi = ""
        isi_el = dpage.query_selector(
            "div.offset-md-top-20, "
            ".cell-sm-8.cell-md-8.text-left, "
            ".post-content, "
            "div[class*='post-body']"
        )
        if isi_el:
            isi = isi_el.inner_text().strip()

        # ── File/link unduhan ────────────────────────────────────────────
        file_url = ""
        file_el = dpage.query_selector(
            "a[href*='.pdf'], "
            "a[href*='download'], "
            "a[href*='unduh'], "
            "a[href*='drive.google']"
        )
        if file_el:
            file_url = _abs(file_el.get_attribute("href") or "")

        dpage.close()

        logger.info(f"[BAAK] OK (detail): {judul[:70]!r}")
        return {
            "judul"   : judul,
            "tanggal" : tanggal,
            "author"  : author,
            "isi"     : isi,
            "file_url": file_url,
        }

    except Exception as e:
        logger.warning(f"[BAAK] Detail gagal: {href} → {type(e).__name__}: {e}")
        try:
            dpage.close()
        except Exception:
            pass
        return None


def scrape_baak(limit: Optional[int] = None) -> List[Dict]:
    """
    Scraping berita dari BAAK Gunadarma.

    Alur:
      1. Buka halaman list, tunggu Cloudflare.
      2. Kumpulkan link detail /beritabaak/<id>.
      3. Buka setiap halaman detail → ekstrak judul, tanggal, author, isi.
      4. Fallback ke data list jika detail gagal.

    Returns:
        List[Dict] dengan field: judul, tanggal, link, sumber, isi, author, file_url.
    """
    logger.info(f"[BAAK] ── Mulai scraping: {URL}")
    hasil = []
    browser = None

    try:
        logger.info("[BAAK] Tahap 1 - Import Playwright...")
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
        logger.info("[BAAK] Playwright OK.")

        with sync_playwright() as p:
            logger.info("[BAAK] Tahap 2 - Launch browser Chromium headless...")
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                ]
            )
            ctx = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/125.0.0.0 Safari/537.36"
                ),
                extra_http_headers={
                    "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8",
                }
            )
            list_page = ctx.new_page()

            # ── Tahap 3: Buka halaman list ────────────────────────────────
            logger.info(f"[BAAK] Tahap 3 - Buka halaman list: {URL}")
            try:
                list_page.goto(URL, timeout=60000, wait_until="domcontentloaded")
                logger.info(f"[BAAK] Title awal: {list_page.title()!r}")
                _tunggu_cloudflare(list_page, max_wait_ms=25000)
                list_page.wait_for_timeout(2000)
                logger.info(f"[BAAK] Title akhir : {list_page.title()!r}")
                logger.info(f"[BAAK] URL akhir   : {list_page.url}")
            except PWTimeout as e:
                logger.error(f"[BAAK] TIMEOUT saat buka list: {e}")
                browser.close(); browser = None
                return []
            except Exception as e:
                logger.error(f"[BAAK] Error buka list: {type(e).__name__}: {e}")
                browser.close(); browser = None
                return []

            # Cek masih di Cloudflare?
            if _masih_cloudflare(list_page):
                html = list_page.content()
                logger.warning("[BAAK] Cloudflare Managed Challenge aktif. Tidak bisa bypass.")
                logger.warning(f"[BAAK] Simpan HTML debug → {os.path.abspath(DEBUG_HTML_FILE)}")
                with open(DEBUG_HTML_FILE, "w", encoding="utf-8") as f:
                    f.write(html)
                browser.close(); browser = None
                return []

            html_list = list_page.content()
            logger.info(f"[BAAK] HTML list: {len(html_list):,} char")

            # ── Tahap 4: Kumpulkan link berita dari halaman list ──────────
            logger.info("[BAAK] Tahap 4 - Kumpulkan link berita dari halaman list...")
            link_data = _ambil_link_dari_list(list_page)

            if not link_data:
                logger.warning("[BAAK] Tidak ada link berita ditemukan. Simpan debug HTML.")
                with open(DEBUG_HTML_FILE, "w", encoding="utf-8") as f:
                    f.write(html_list)
                logger.warning(f"[BAAK] Debug: {os.path.abspath(DEBUG_HTML_FILE)}")
                browser.close(); browser = None
                return []

            if limit:
                link_data = link_data[:limit]
                logger.info(f"[BAAK] Dibatasi maks. {limit} berita.")

            logger.info(f"[BAAK] Akan membuka {len(link_data)} halaman detail...")

            # ── Tahap 5: Buka setiap halaman detail ──────────────────────
            for judul_list, href in link_data:
                detail = _buka_detail(ctx, href)

                if detail is not None:
                    # Data dari halaman detail (lengkap)
                    item = {
                        "judul"   : detail["judul"]    or judul_list,
                        "tanggal" : detail["tanggal"],
                        "link"    : href,
                        "sumber"  : SUMBER,
                        "isi"     : detail["isi"],
                        "author"  : detail["author"],
                        "file_url": detail["file_url"],
                    }
                else:
                    # Fallback: data minimal dari halaman list
                    logger.warning(f"[BAAK] Detail gagal, menggunakan data list: {judul_list[:60]!r}")
                    fb = _ambil_data_list(list_page, href)
                    item = {
                        "judul"   : judul_list,
                        "tanggal" : "",
                        "link"    : href,
                        "sumber"  : SUMBER,
                        "isi"     : fb.get("isi_fallback", ""),
                        "author"  : "",
                        "file_url": "",
                    }

                hasil.append(item)

            list_page.close()
            browser.close(); browser = None

    except Exception as e:
        logger.error(f"[BAAK] ERROR tidak terduga: {type(e).__name__}: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        if browser:
            try:
                browser.close()
            except Exception:
                pass

    logger.info(f"[BAAK] Tahap 6 - Selesai. Total dikembalikan: {len(hasil)}")
    return hasil
