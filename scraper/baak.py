"""
scraper/baak.py
Scraper untuk website BAAK Universitas Gunadarma.
URL: https://baak.gunadarma.ac.id/beritabaak

Alur:
  1. Coba buka dengan Playwright
  2. Jika terkena Cloudflare, fallback ke FlareSolverr
  3. Parse HTML dari solution.response FlareSolverr
  4. Kumpulkan maks. 5 link detail: /beritabaak/<angka>
  5. Buka setiap halaman detail dan ekstrak:
       - judul  : h3.text-bold
       - tanggal: .text-middle.inset-left-10.text-italic.text-black
       - author : .text-middle.inset-left-10.text-italic.text-primary
       - isi    : div.offset-md-top-20
  6. Jika detail gagal → fallback data dari halaman list

Proteksi: Website dilindungi Cloudflare Managed Challenge.
          Scraper mencoba Playwright dulu, lalu FlareSolverr jika gagal.
"""

import re
import os
from typing import List, Dict, Optional
from bs4 import BeautifulSoup

from utils.logger import logger, clean_log_text, log_content_length
from utils.flaresolverr import is_flaresolverr_running, get_html_via_flaresolverr

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


def _masih_cloudflare(title: str, html: str = "") -> bool:
    """
    Cek apakah halaman masih di challenge Cloudflare.
    
    Args:
        title: Title halaman
        html: HTML halaman (opsional, untuk deteksi lebih akurat)
    
    Returns:
        True jika masih di Cloudflare challenge
    """
    # Cek dari title
    cf_keywords_title = ["Just a moment", "Tunggu sebentar", "moment...", "Please Wait"]
    if any(kw in title for kw in cf_keywords_title):
        return True
    
    # Cek dari HTML jika tersedia
    if html:
        cf_keywords_html = ["cf-challenge", "cf_challenge_response", "Checking your browser"]
        if any(kw in html for kw in cf_keywords_html):
            return True
    
    return False


def _parse_list_html_bs4(html: str) -> List[tuple]:
    """
    Parse HTML halaman list BAAK menggunakan BeautifulSoup.
    
    Selector berdasarkan struktur aktual:
    - Container: .cell-md-8
    - Artikel: article dalam div.range.text-sm-left
    - Judul: h6 dalam article
    - Link: a[href] dalam article
    
    Returns:
        List of (judul_list, href_absolut) - satu tuple per artikel
    """
    soup = BeautifulSoup(html, "html.parser")
    link_data = []
    seen = set()

    # ── STRATEGI UTAMA: Cari container .cell-md-8 ─────────────────────────
    # Container utama yang berisi daftar berita
    container = soup.find("div", class_="cell-md-8")
    
    if not container:
        logger.warning("[BAAK] Container .cell-md-8 tidak ditemukan")
        # Simpan HTML untuk debug
        with open(DEBUG_HTML_FILE, "w", encoding="utf-8") as f:
            f.write(html)
        logger.warning(f"[BAAK] HTML debug disimpan: {os.path.abspath(DEBUG_HTML_FILE)}")
        return []
    
    logger.info("[BAAK] Container .cell-md-8 ditemukan")
    
    # Cari semua artikel dalam container
    # Selector: article atau div yang berisi h6 dan link
    articles = container.find_all("article")
    logger.info(f"[BAAK] Ditemukan {len(articles)} artikel pada halaman list")
    
    if not articles:
        # Fallback: cari div yang punya h6 dan link
        logger.info("[BAAK] Fallback: cari div dengan h6...")
        potential_articles = container.find_all("div", class_=re.compile(r"post|news|item|card"))
        articles = [div for div in potential_articles if div.find("h6") and div.find("a", href=True)]
        logger.info(f"[BAAK] Fallback: ditemukan {len(articles)} item dengan h6 dan link")
    
    # ── Loop setiap artikel ────────────────────────────────────────────────
    for idx, article in enumerate(articles, 1):
        # Ambil judul dari h6 dalam article ini
        h6_el = article.find("h6")
        judul = ""
        if h6_el:
            judul = h6_el.get_text(strip=True)
        
        # Ambil link dari <a> dalam article ini
        link_el = article.find("a", href=True)
        if not link_el:
            logger.warning(f"[BAAK] Artikel #{idx}: tidak ada link, skip")
            continue
        
        href = link_el.get("href", "")
        href = _abs(href)
        
        # Validasi: harus link beritabaak dengan ID
        if not re.search(r"/beritabaak/\d+", href):
            logger.debug(f"[BAAK] Artikel #{idx}: bukan link beritabaak, skip ({href})")
            continue
        
        # Skip jika sudah pernah diambil (duplikat)
        if href in seen:
            logger.debug(f"[BAAK] Artikel #{idx}: duplikat link, skip ({href})")
            continue
        
        # Fallback judul jika h6 kosong
        if not judul:
            # Coba ambil dari teks link
            judul = link_el.get_text(strip=True)
        
        if not judul:
            judul = f"Berita BAAK #{len(link_data) + 1}"
        
        # Tambahkan ke hasil
        seen.add(href)
        link_data.append((judul, href))
        logger.debug(f"[BAAK] Artikel #{idx}: {clean_log_text(judul, 50)} → {href}")
    
    # ── Log ringkasan hasil ───────────────────────────────────────────────
    if link_data:
        logger.info(f"[BAAK] Berhasil parse {len(link_data)} artikel dari halaman list")
        logger.info(f"[BAAK] Contoh 3 judul pertama:")
        for i, (judul, href) in enumerate(link_data[:3], 1):
            logger.info(f"[BAAK]   {i}. {clean_log_text(judul, 70)}")
        logger.info(f"[BAAK] Contoh 3 URL pertama:")
        for i, (judul, href) in enumerate(link_data[:3], 1):
            logger.info(f"[BAAK]   {i}. {href}")
    else:
        logger.warning("[BAAK] Tidak ada artikel yang berhasil di-parse dari halaman list")
    
    return link_data


def _parse_detail_html_bs4(html: str, href: str) -> Optional[Dict]:
    """
    Parse HTML halaman detail BAAK menggunakan BeautifulSoup.
    
    PENTING: Fokus pada konten artikel dalam container .cell-md-8,
    hindari mengambil heading/navigasi umum website seperti "Perkuliahan dan Ujian".
    
    Returns:
        Dict dengan judul, tanggal, author, isi — atau None jika gagal.
    """
    try:
        soup = BeautifulSoup(html, "html.parser")
        
        # ══════════════════════════════════════════════════════════════════
        # STRATEGI: Fokus pada container konten utama terlebih dahulu
        # ══════════════════════════════════════════════════════════════════
        # Container konten artikel biasanya di .cell-md-8 (bukan navigasi/header)
        content_container = soup.find("div", class_=re.compile(r"cell-md-8"))
        
        if not content_container:
            logger.warning(f"[BAAK] Container .cell-md-8 tidak ditemukan pada halaman detail: {href}")
            # Simpan HTML untuk debugging
            debug_file = "debug_baak_detail.html"
            with open(debug_file, "w", encoding="utf-8") as f:
                f.write(html)
            logger.warning(f"[BAAK] HTML debug detail disimpan: {os.path.abspath(debug_file)}")
        
        # ══════════════════════════════════════════════════════════════════
        # JUDUL - h6 dalam container konten, BUKAN di navigasi/header
        # ══════════════════════════════════════════════════════════════════
        judul = ""
        judul_selector_used = "none"
        
        # Strategi 1: h6 dalam content_container (prioritas tertinggi)
        if content_container:
            # Cari h6 yang bukan bagian dari navigasi/breadcrumb
            h6_candidates = content_container.find_all("h6")
            for h6 in h6_candidates:
                # Skip h6 yang parent-nya adalah navigasi
                parent = h6.parent
                if parent:
                    parent_classes = " ".join(parent.get("class", []))
                    # Skip jika ada kata kunci navigasi
                    skip_words = ["breadcrumb", "nav", "menu", "header", "sidebar"]
                    if any(word in parent_classes.lower() for word in skip_words):
                        continue
                
                text = h6.get_text(strip=True)
                # Judul berita minimal 15 karakter untuk menghindari kategori pendek
                if text and len(text) >= 15:
                    judul = text
                    judul_selector_used = "h6 dalam .cell-md-8 (artikel)"
                    break
        
        # Strategi 2: Jika tidak ada h6 dalam container, cari h3/h4 dalam container
        if not judul and content_container:
            for tag_name in ["h3", "h4", "h2"]:
                h_el = content_container.find(tag_name)
                if h_el:
                    text = h_el.get_text(strip=True)
                    if text and len(text) >= 15:
                        judul = text
                        judul_selector_used = f"{tag_name} dalam .cell-md-8"
                        break
        
        # Strategi 3: Fallback - cari h6 global tapi filter ketat
        if not judul:
            all_h6 = soup.find_all("h6")
            for h6 in all_h6:
                text = h6.get_text(strip=True)
                
                # Filter: TOLAK jika teks adalah heading umum website
                heading_blacklist = [
                    "Perkuliahan dan Ujian",
                    "Akademik",
                    "Kemahasiswaan",
                    "BAAK",
                    "Berita",
                    "Pengumuman",
                    "Menu",
                    "Navigasi"
                ]
                if any(blacklist_word.lower() in text.lower() for blacklist_word in heading_blacklist):
                    logger.debug(f"[BAAK] Skip judul blacklist: '{text}'")
                    continue
                
                # Harus minimal 20 karakter untuk fallback global
                if text and len(text) >= 20:
                    judul = text
                    judul_selector_used = "h6 global (filtered ketat)"
                    break
        
        logger.info(f"[BAAK] Selector judul yang dipakai: {judul_selector_used}")
        if judul:
            logger.info(f"[BAAK] Judul: {clean_log_text(judul, 100)}")
        else:
            logger.warning(f"[BAAK] Judul TIDAK DITEMUKAN pada {href}")

        # ══════════════════════════════════════════════════════════════════
        # TANGGAL - .text-middle.inset-left-10.text-italic.text-black
        # ══════════════════════════════════════════════════════════════════
        tanggal = ""
        
        # Cari dalam container konten terlebih dahulu
        if content_container:
            for el in content_container.find_all(class_=re.compile(r"text-middle|text-italic")):
                classes = el.get("class", [])
                # Kombinasi class yang spesifik untuk tanggal
                if ("text-middle" in classes and "inset-left-10" in classes and 
                    "text-italic" in classes and "text-black" in classes):
                    tanggal = el.get_text(strip=True)
                    break
        
        # Fallback: cari global
        if not tanggal:
            tgl_el = soup.find("time") or soup.find(class_="post-date") or soup.find(class_="date")
            if tgl_el:
                tanggal = tgl_el.get_text(strip=True)

        # ══════════════════════════════════════════════════════════════════
        # AUTHOR - .text-middle.inset-left-10.text-italic.text-primary
        # ══════════════════════════════════════════════════════════════════
        author = ""
        
        # Cari dalam container konten terlebih dahulu
        if content_container:
            for el in content_container.find_all(class_=re.compile(r"text-middle|text-italic")):
                classes = el.get("class", [])
                # Kombinasi class yang spesifik untuk author
                if ("text-middle" in classes and "inset-left-10" in classes and 
                    "text-italic" in classes and "text-primary" in classes):
                    author = el.get_text(strip=True)
                    break
        
        # Fallback: cari global
        if not author:
            auth_el = soup.find(class_="author") or soup.find(class_="posted-by")
            if auth_el:
                author = auth_el.get_text(strip=True)

        # ══════════════════════════════════════════════════════════════════
        # ISI BERITA - div.offset-md-top-20 (konten utama artikel)
        # ══════════════════════════════════════════════════════════════════
        isi = ""
        isi_selector_used = "none"
        
        # Strategi 1: div.offset-md-top-20 dalam container (PRIORITAS UTAMA)
        if content_container:
            isi_el = content_container.find("div", class_="offset-md-top-20")
            if isi_el:
                isi = isi_el.get_text(separator="\n", strip=True)
                isi_selector_used = "div.offset-md-top-20"
        
        # Strategi 2: div dengan class yang mengandung "offset-md"
        if (not isi or len(isi) < 100) and content_container:
            isi_el = content_container.find("div", class_=re.compile(r"offset-md"))
            if isi_el:
                text = isi_el.get_text(separator="\n", strip=True)
                # Validasi: harus lebih panjang dari sebelumnya
                if len(text) > len(isi):
                    isi = text
                    isi_selector_used = "div[class*='offset-md'] dalam .cell-md-8"
        
        # Strategi 3: Kumpulkan semua <p> dalam container (skip navigasi)
        if (not isi or len(isi) < 100) and content_container:
            paragraphs = []
            for p in content_container.find_all("p"):
                # Skip paragraf dalam navigasi/menu
                parent = p.parent
                if parent:
                    parent_classes = " ".join(parent.get("class", []))
                    skip_words = ["breadcrumb", "nav", "menu", "header", "sidebar", "footer"]
                    if any(word in parent_classes.lower() for word in skip_words):
                        continue
                
                text = p.get_text(strip=True)
                if text:
                    paragraphs.append(text)
            
            if paragraphs:
                text = "\n\n".join(paragraphs)
                if len(text) > len(isi):
                    isi = text
                    isi_selector_used = "semua <p> dalam .cell-md-8 (filtered)"
        
        # Strategi 4: Ambil semua text dalam container (last resort)
        if (not isi or len(isi) < 100) and content_container:
            # Clone container untuk manipulasi
            container_copy = BeautifulSoup(str(content_container), "html.parser")
            
            # Hapus elemen yang bukan konten artikel
            for selector in ["nav", "header", "footer", ".breadcrumb", ".menu", ".sidebar"]:
                for el in container_copy.select(selector):
                    el.decompose()
            
            text = container_copy.get_text(separator="\n", strip=True)
            if len(text) > len(isi):
                isi = text
                isi_selector_used = ".cell-md-8 (cleaned text)"
        
        logger.info(f"[BAAK] Selector isi yang dipakai: {isi_selector_used}")
        logger.info(f"[BAAK] Panjang isi: {len(isi)} karakter")
        
        # Preview 100 karakter pertama
        if isi:
            preview = clean_log_text(isi, 100)
            logger.info(f"[BAAK] Preview isi: {preview}")
        else:
            logger.warning(f"[BAAK] Isi KOSONG pada {href}")
        
        # Warning jika isi terlalu pendek
        if len(isi) < 100:
            logger.warning(f"[BAAK] ⚠️ ISI TERLALU PENDEK ({len(isi)} char) - kemungkinan selector salah!")
            if isi:
                logger.warning(f"[BAAK] Isi yang tertangkap: '{clean_log_text(isi, 200)}'")

        # ══════════════════════════════════════════════════════════════════
        # FILE/LINK UNDUHAN
        # ══════════════════════════════════════════════════════════════════
        file_url = ""
        # Cari link download dalam container
        if content_container:
            file_el = content_container.find("a", href=re.compile(r"\.pdf|\.doc|\.xls|download|unduh|drive\.google", re.I))
            if file_el:
                file_url = _abs(file_el.get("href", ""))

        return {
            "judul": judul,
            "tanggal": tanggal,
            "author": author,
            "isi": isi,
            "file_url": file_url,
        }

    except Exception as e:
        logger.warning(f"[BAAK] Parse detail gagal: {href} → {type(e).__name__}: {e}")
        import traceback
        logger.warning(traceback.format_exc())
        return None


def _scrape_dengan_flaresolverr(limit: Optional[int]) -> List[Dict]:
    """
    Scraping BAAK menggunakan FlareSolverr untuk bypass Cloudflare.
    
    Returns:
        List[Dict] dengan field: judul, tanggal, link, sumber, isi, author, file_url.
    """
    logger.info("[BAAK] Menggunakan FlareSolverr untuk bypass Cloudflare...")
    
    # ── Tahap 1: Ambil HTML halaman list via FlareSolverr ────────────────
    logger.info(f"[BAAK] Request FlareSolverr untuk: {URL}")
    html_list = get_html_via_flaresolverr(URL)
    
    if not html_list:
        logger.error("[BAAK] FlareSolverr gagal mendapatkan HTML halaman list.")
        return []
    
    logger.info(f"[BAAK] {log_content_length(html_list, 'HTML list')}")
    
    # ── Tahap 2: Validasi HTML bukan halaman Cloudflare ──────────────────
    # Parse title dari HTML
    soup_check = BeautifulSoup(html_list, "html.parser")
    title_tag = soup_check.find("title")
    title = title_tag.get_text(strip=True) if title_tag else ""
    
    logger.info(f"[BAAK] Title halaman dari FlareSolverr: '{title}'")
    
    if _masih_cloudflare(title, html_list):
        logger.error(
            "[BAAK] FlareSolverr mengembalikan halaman Cloudflare challenge. "
            "Kemungkinan FlareSolverr gagal bypass atau timeout."
        )
        # Simpan HTML debug
        with open(DEBUG_HTML_FILE, "w", encoding="utf-8") as f:
            f.write(html_list)
        logger.warning(f"[BAAK] HTML debug disimpan: {os.path.abspath(DEBUG_HTML_FILE)}")
        return []
    
    # ── Tahap 3: Parse link berita dari HTML list ─────────────────────────
    logger.info("[BAAK] Parsing HTML list untuk mengambil link berita...")
    link_data = _parse_list_html_bs4(html_list)
    
    if not link_data:
        logger.warning("[BAAK] Tidak ada link berita ditemukan dalam HTML.")
        with open(DEBUG_HTML_FILE, "w", encoding="utf-8") as f:
            f.write(html_list)
        logger.warning(f"[BAAK] HTML debug disimpan: {os.path.abspath(DEBUG_HTML_FILE)}")
        return []
    
    # ── Tahap 4: Batasi jumlah jika limit ditentukan ──────────────────────
    if limit:
        link_data = link_data[:limit]
        logger.info(f"[BAAK] Dibatasi maksimal {limit} berita.")
    
    logger.info(f"[BAAK] Akan memproses {len(link_data)} halaman detail...")
    
    # ── Tahap 5: Ambil detail setiap berita ───────────────────────────────
    hasil = []
    
    for idx, (judul_list, href) in enumerate(link_data, 1):
        logger.info(f"[BAAK] [{idx}/{len(link_data)}] Memproses: {clean_log_text(judul_list, 70)}")
        
        # Ambil HTML detail via FlareSolverr
        html_detail = get_html_via_flaresolverr(href)
        
        if not html_detail:
            logger.warning(f"[BAAK] [{idx}/{len(link_data)}] FlareSolverr gagal untuk detail: {href}")
            # Fallback: gunakan data minimal dari list
            item = {
                "judul": judul_list,
                "tanggal": "",
                "link": href,
                "sumber": SUMBER,
                "isi": "",
                "author": "",
                "file_url": "",
            }
            hasil.append(item)
            continue
        
        # Parse detail dari HTML
        detail = _parse_detail_html_bs4(html_detail, href)
        
        if detail:
            item = {
                "judul": detail["judul"] or judul_list,
                "tanggal": detail["tanggal"],
                "link": href,
                "sumber": SUMBER,
                "isi": detail["isi"],
                "author": detail["author"],
                "file_url": detail["file_url"],
            }
            # Log hasil parse (tanpa menampilkan isi penuh)
            logger.info(f"[BAAK] [{idx}/{len(link_data)}] Judul: {clean_log_text(item['judul'], 70)}")
            logger.info(f"[BAAK] [{idx}/{len(link_data)}] Link: {href}")
            if detail['isi']:
                logger.info(f"[BAAK] [{idx}/{len(link_data)}] {log_content_length(detail['isi'], 'Isi')}")
        else:
            # Fallback jika parse gagal
            logger.warning(f"[BAAK] [{idx}/{len(link_data)}] Parse detail gagal, gunakan data list")
            item = {
                "judul": judul_list,
                "tanggal": "",
                "link": href,
                "sumber": SUMBER,
                "isi": "",
                "author": "",
                "file_url": "",
            }
        
        hasil.append(item)
    
    return hasil


def scrape_baak(limit: Optional[int] = None) -> List[Dict]:
    """
    Scraping berita dari BAAK Gunadarma.

    Alur:
      1. Cek apakah FlareSolverr berjalan.
      2. Jika ya, gunakan FlareSolverr (strategi utama).
      3. Jika tidak, gunakan Playwright sebagai fallback.
      4. Parse HTML dan ekstrak data berita.

    Returns:
        List[Dict] dengan field: judul, tanggal, link, sumber, isi, author, file_url.
    """
    logger.info(f"[BAAK] ── Mulai scraping: {URL}")
    
    # ── Strategi 1: FlareSolverr (prioritas utama) ────────────────────────
    if is_flaresolverr_running():
        logger.info("[BAAK] FlareSolverr terdeteksi aktif di localhost:8191")
        hasil = _scrape_dengan_flaresolverr(limit)
        
        if hasil:
            logger.info(f"[BAAK] ── Selesai via FlareSolverr. Total: {len(hasil)} berita")
            return hasil
        
        logger.warning("[BAAK] FlareSolverr gagal atau tidak ada data. Coba fallback Playwright...")
    else:
        logger.warning(
            "[BAAK] FlareSolverr tidak berjalan di localhost:8191. "
            "Untuk hasil terbaik, jalankan FlareSolverr: "
            "docker run -d --name flaresolverr -p 8191:8191 "
            "ghcr.io/flaresolverr/flaresolverr:latest"
        )
    
    # ── Strategi 2: Playwright (fallback) ─────────────────────────────────
    logger.info("[BAAK] Menggunakan Playwright sebagai fallback...")
    hasil = _scrape_dengan_playwright(limit)
    
    logger.info(f"[BAAK] ── Selesai via Playwright. Total: {len(hasil)} berita")
    return hasil


def _scrape_dengan_playwright(limit: Optional[int]) -> List[Dict]:
    """
    Fallback: scraping BAAK menggunakan Playwright headless.
    Digunakan jika FlareSolverr tidak tersedia atau gagal.
    
    Returns:
        List[Dict] dengan field: judul, tanggal, link, sumber, isi, author, file_url.
    """
    logger.info("[BAAK] Inisialisasi Playwright...")
    hasil = []
    browser = None

    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

        with sync_playwright() as p:
            logger.info("[BAAK] Launch browser Chromium headless...")
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
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8",
                }
            )
            
            # Apply stealth jika tersedia
            try:
                from playwright_stealth import Stealth
                stealth = Stealth()
                logger.info("[BAAK] Stealth mode tersedia, akan diterapkan...")
            except ImportError:
                stealth = None
                logger.info("[BAAK] Stealth mode tidak tersedia, lanjut tanpa stealth")
            
            list_page = ctx.new_page()
            
            if stealth:
                try:
                    stealth.apply_stealth_sync(list_page)
                    logger.info("[BAAK] Stealth mode diterapkan")
                except Exception as e:
                    logger.warning(f"[BAAK] Stealth mode gagal diterapkan: {e}")

            # ── Buka halaman list ──────────────────────────────────────────
            logger.info(f"[BAAK] Buka halaman list: {URL}")
            try:
                list_page.goto(URL, timeout=60000, wait_until="domcontentloaded")
                logger.info(f"[BAAK] Title awal: '{list_page.title()}'")
                
                # Tunggu Cloudflare selesai (max 25 detik)
                try:
                    list_page.wait_for_function(
                        "!document.title.includes('Just a moment') && "
                        "!document.title.includes('Tunggu sebentar') && "
                        "!document.title.includes('moment...')",
                        timeout=25000
                    )
                    logger.info("[BAAK] Cloudflare challenge selesai (via Playwright)")
                except Exception:
                    logger.warning("[BAAK] Cloudflare masih aktif setelah 25 detik")
                
                list_page.wait_for_timeout(2000)
                logger.info(f"[BAAK] Title akhir: '{list_page.title()}'")
                logger.info(f"[BAAK] URL akhir: {list_page.url}")
                
            except PWTimeout as e:
                logger.error(f"[BAAK] TIMEOUT saat buka list: {e}")
                browser.close()
                return []
            except Exception as e:
                logger.error(f"[BAAK] Error buka list: {type(e).__name__}: {e}")
                browser.close()
                return []

            # Cek masih di Cloudflare?
            if _masih_cloudflare(list_page.title(), list_page.content()):
                logger.error(
                    "[BAAK] Playwright tidak bisa bypass Cloudflare. "
                    "Harap gunakan FlareSolverr untuk hasil yang lebih baik."
                )
                html = list_page.content()
                with open(DEBUG_HTML_FILE, "w", encoding="utf-8") as f:
                    f.write(html)
                logger.warning(f"[BAAK] HTML debug disimpan: {os.path.abspath(DEBUG_HTML_FILE)}")
                browser.close()
                return []

            # Parse HTML list
            html_list = list_page.content()
            logger.info(f"[BAAK] {log_content_length(html_list, 'HTML list')}")
            
            link_data = _parse_list_html_bs4(html_list)

            if not link_data:
                logger.warning("[BAAK] Tidak ada link berita ditemukan.")
                with open(DEBUG_HTML_FILE, "w", encoding="utf-8") as f:
                    f.write(html_list)
                logger.warning(f"[BAAK] HTML debug disimpan: {os.path.abspath(DEBUG_HTML_FILE)}")
                browser.close()
                return []

            if limit:
                link_data = link_data[:limit]
                logger.info(f"[BAAK] Dibatasi maksimal {limit} berita.")

            logger.info(f"[BAAK] Akan membuka {len(link_data)} halaman detail...")

            # ── Buka setiap halaman detail ─────────────────────────────────
            for idx, (judul_list, href) in enumerate(link_data, 1):
                logger.info(f"[BAAK] [{idx}/{len(link_data)}] Buka detail: {clean_log_text(judul_list, 70)}")
                
                try:
                    dpage = ctx.new_page()
                    if stealth:
                        try:
                            stealth.apply_stealth_sync(dpage)
                        except Exception:
                            pass
                    
                    dpage.goto(href, timeout=30000, wait_until="domcontentloaded")
                    
                    # Tunggu Cloudflare (max 15 detik)
                    try:
                        dpage.wait_for_function(
                            "!document.title.includes('Just a moment') && "
                            "!document.title.includes('Tunggu sebentar')",
                            timeout=15000
                        )
                    except Exception:
                        pass
                    
                    dpage.wait_for_timeout(1500)

                    # Cek masih Cloudflare?
                    if _masih_cloudflare(dpage.title(), dpage.content()):
                        logger.warning(f"[BAAK] [{idx}/{len(link_data)}] Detail masih di Cloudflare, skip")
                        dpage.close()
                        # Fallback data list
                        hasil.append({
                            "judul": judul_list,
                            "tanggal": "",
                            "link": href,
                            "sumber": SUMBER,
                            "isi": "",
                            "author": "",
                            "file_url": "",
                        })
                        continue

                    # Parse detail
                    html_detail = dpage.content()
                    detail = _parse_detail_html_bs4(html_detail, href)
                    dpage.close()

                    if detail:
                        item = {
                            "judul": detail["judul"] or judul_list,
                            "tanggal": detail["tanggal"],
                            "link": href,
                            "sumber": SUMBER,
                            "isi": detail["isi"],
                            "author": detail["author"],
                            "file_url": detail["file_url"],
                        }
                        logger.info(f"[BAAK] [{idx}/{len(link_data)}] {log_content_length(detail['isi'], 'Isi')}")
                    else:
                        item = {
                            "judul": judul_list,
                            "tanggal": "",
                            "link": href,
                            "sumber": SUMBER,
                            "isi": "",
                            "author": "",
                            "file_url": "",
                        }

                    hasil.append(item)

                except Exception as e:
                    logger.warning(f"[BAAK] [{idx}/{len(link_data)}] Detail gagal: {type(e).__name__}: {e}")
                    try:
                        dpage.close()
                    except Exception:
                        pass
                    # Fallback data list
                    hasil.append({
                        "judul": judul_list,
                        "tanggal": "",
                        "link": href,
                        "sumber": SUMBER,
                        "isi": "",
                        "author": "",
                        "file_url": "",
                    })

            list_page.close()
            browser.close()

    except Exception as e:
        logger.error(f"[BAAK] Playwright ERROR: {type(e).__name__}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        if browser:
            try:
                browser.close()
            except Exception:
                pass

    return hasil
