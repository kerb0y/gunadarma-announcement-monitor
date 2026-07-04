"""
scraper/kemahasiswaan.py
Scraper untuk website Kemahasiswaan Universitas Gunadarma.
URL: https://kemahasiswaan.gunadarma.ac.id/

Proteksi: Cloudflare Managed Challenge.
Strategi utama  : FlareSolverr (jika berjalan di localhost:8191)
Strategi fallback: Playwright headless

Selector aktual (diverifikasi Juni 2026 dari user):
  List: article.col-lg-4 div.post-card-content a  (news cards)
        div.thumb-overlay a[title]                 (slider overlay)
  Detail: .entry-title.mb-50.font-weight-900  (judul)
          .ck-content                         (isi)
          .author-name.font-weight-bold       (author + tanggal)
          
Special handling untuk tabel delegasi:
  - Deteksi keberadaan <td> dalam konten
  - Parse struktur tabel berdasarkan <tr> dan <td>
  - Format khusus untuk tabel delegasi (5 kolom: No, Nama, NPM, Prodi, Keterangan)
"""

import re
import os
from typing import List, Dict, Optional, Tuple
from bs4 import BeautifulSoup

from utils.logger import logger, clean_log_text, log_content_length
from utils.flaresolverr import is_flaresolverr_running, get_html_via_flaresolverr

SUMBER          = "KEMAHASISWAAN"
URL             = "https://kemahasiswaan.gunadarma.ac.id/"
BASE_URL        = "https://kemahasiswaan.gunadarma.ac.id"
DEBUG_HTML_FILE = "debug_kemahasiswaan.html"


def _extract_table_cells(content_element) -> List[str]:
    """
    Extract cells dari tabel dalam content.
    
    Strategy:
    1. Cari <table> dan parse <tr> -> <td>
    2. Fallback: ambil semua <td> langsung jika table tidak jelas
    
    Returns:
        List of cell texts (stripped, non-empty)
    """
    if not content_element:
        return []
    
    cells = []
    
    # Strategy 1: Parse table structure
    tables = content_element.find_all("table")
    logger.info(f"[KEMAHASISWAAN] Jumlah <table> ditemukan: {len(tables)}")
    
    if tables:
        for table in tables:
            rows = table.find_all("tr")
            for row in rows:
                tds = row.find_all("td")
                for td in tds:
                    text = td.get_text(" ", strip=True)
                    if text:
                        cells.append(text)
    
    # Strategy 2: Fallback - ambil semua <td> jika table tidak ditemukan
    if not cells:
        all_tds = content_element.find_all("td")
        logger.info(f"[KEMAHASISWAAN] Jumlah <td> ditemukan (fallback): {len(all_tds)}")
        for td in all_tds:
            text = td.get_text(" ", strip=True)
            if text:
                cells.append(text)
    else:
        # Log jumlah td jika table ditemukan
        all_tds_count = len(content_element.find_all("td"))
        logger.info(f"[KEMAHASISWAAN] Jumlah <td> ditemukan: {all_tds_count}")
    
    return cells


def _is_delegasi_table(cells: List[str]) -> bool:
    """
    Deteksi apakah cells merupakan tabel delegasi.
    
    Ciri-ciri:
    - Jumlah cells kelipatan 5 (No, Nama, NPM, Prodi, Keterangan)
    - Ada angka urut di kolom pertama
    - Ada NPM (8 digit) di kolom ketiga
    - Ada Program Studi dengan (S1) atau nama prodi
    - Ada Keterangan dengan kata kunci: Ketua, Manajer, Anggota
    
    Validasi tidak terlalu ketat agar data valid tidak terbuang.
    """
    if not cells or len(cells) < 5:
        return False
    
    # Cek apakah kelipatan 5
    if len(cells) % 5 != 0:
        return False
    
    # Ambil sample baris pertama (skip header jika ada)
    # Header biasanya: No, Nama, NPM, Program Studi, Keterangan
    sample_start = 0
    if cells[0].lower() in ["no", "no."]:
        # Skip header row
        sample_start = 5
    
    if sample_start >= len(cells):
        return False
    
    # Validasi ringan pada baris pertama data
    # Kolom 0: harus angka atau kosong (urut)
    col_0 = cells[sample_start].strip()
    is_number = col_0.isdigit() or col_0 == ""
    
    # Kolom 2: NPM (8 digit, bisa ada spasi)
    col_2 = cells[sample_start + 2].strip().replace(" ", "")
    is_npm = col_2.isdigit() and len(col_2) >= 7 and len(col_2) <= 10
    
    # Kolom 3: Program Studi (mengandung S1, D3, Teknik, Sistem, dll)
    col_3_lower = cells[sample_start + 3].lower()
    is_prodi = any(keyword in col_3_lower for keyword in ["s1", "d3", "teknik", "sistem", "informatika", "ekonomi", "manajemen", "akuntansi", "psikologi", "sastra"])
    
    # Kolom 4: Keterangan (mengandung Ketua, Manajer, Anggota, dll)
    col_4_lower = cells[sample_start + 4].lower()
    is_keterangan = any(keyword in col_4_lower for keyword in ["ketua", "manajer", "anggota", "peserta", "delegasi"])
    
    # Minimal 2 dari 4 validasi harus benar
    valid_count = sum([is_number, is_npm, is_prodi, is_keterangan])
    
    return valid_count >= 2


def _format_delegasi_table(cells: List[str]) -> str:
    """
    Format cells tabel delegasi menjadi list rapi untuk Discord.
    
    Format output:
    📋 Daftar Delegasi
    
    1. Nama Lengkap
       NPM: 12345678
       Program Studi: Teknik Mesin (S1)
       Keterangan: Ketua / Manajer
    
    2. Nama Lengkap 2
       ...
    """
    if not cells or len(cells) < 5:
        return ""
    
    # Skip header row jika ada (No, Nama, NPM, Program Studi, Keterangan)
    start_idx = 0
    if cells[0].lower() in ["no", "no."]:
        logger.info("[KEMAHASISWAAN] Header tabel terdeteksi, skip header row")
        start_idx = 5
    
    # Group cells per 5 kolom
    rows = []
    for i in range(start_idx, len(cells), 5):
        if i + 4 < len(cells):
            no = cells[i].strip()
            nama = cells[i + 1].strip()
            npm = cells[i + 2].strip()
            prodi = cells[i + 3].strip()
            keterangan = cells[i + 4].strip()
            
            # Skip jika baris kosong atau duplikat header
            if not nama or nama.lower() == "nama":
                continue
            
            rows.append({
                "no": no,
                "nama": nama,
                "npm": npm,
                "prodi": prodi,
                "keterangan": keterangan
            })
    
    if not rows:
        return ""
    
    logger.info(f"[KEMAHASISWAAN] Jumlah baris delegasi terparse: {len(rows)}")
    
    # Format output
    lines = ["📋 Daftar Delegasi\n"]
    
    for idx, row in enumerate(rows, 1):
        # Gunakan nomor urut dari data, fallback ke idx
        no_display = row["no"] if row["no"].isdigit() else str(idx)
        
        lines.append(f"{no_display}. {row['nama']}")
        lines.append(f"   NPM: {row['npm']}")
        lines.append(f"   Program Studi: {row['prodi']}")
        lines.append(f"   Keterangan: {row['keterangan']}")
        
        # Tambahkan blank line antar entry kecuali entry terakhir
        if idx < len(rows):
            lines.append("")
    
    result = "\n".join(lines)
    
    # Log preview (gunakan clean_log_text untuk batasi panjang)
    logger.info(f"[KEMAHASISWAAN] Preview tabel delegasi: {clean_log_text(result, 150)}")
    
    return result


def _process_content_with_table(content_element) -> Tuple[str, bool]:
    """
    Process content yang mungkin mengandung tabel.
    
    Returns:
        (processed_text, has_delegasi_table)
    """
    # Extract table cells
    cells = _extract_table_cells(content_element)
    
    if not cells:
        logger.info("[KEMAHASISWAAN] Tidak ada <td> ditemukan, gunakan text extraction biasa")
        return content_element.get_text(separator="\n", strip=True), False
    
    # Check if it's delegasi table
    is_delegasi = _is_delegasi_table(cells)
    logger.info(f"[KEMAHASISWAAN] Tabel delegasi terdeteksi dari <td>: {'YA' if is_delegasi else 'TIDAK'}")
    
    if not is_delegasi:
        logger.info("[KEMAHASISWAAN] <td> ditemukan tetapi bukan tabel delegasi. Menggunakan teks asli.")
        return content_element.get_text(separator="\n", strip=True), False
    
    # Format delegasi table
    formatted_table = _format_delegasi_table(cells)
    
    if not formatted_table:
        logger.warning("[KEMAHASISWAAN] <td> ditemukan tetapi gagal diformat sebagai tabel delegasi. Menggunakan teks asli.")
        return content_element.get_text(separator="\n", strip=True), False
    
    # Get text before and after table
    # Clone element untuk manipulasi
    import copy
    content_copy = copy.copy(content_element)
    
    # Remove table from copy untuk ambil teks paragraf
    for table in content_copy.find_all("table"):
        table.decompose()
    
    paragraphs = content_copy.get_text(separator="\n", strip=True)
    
    # Combine: paragraf + formatted table
    if paragraphs:
        result = paragraphs + "\n\n" + formatted_table
    else:
        result = formatted_table
    
    return result, True


def _is_social_share_link(href: str, judul: str) -> bool:
    """
    Filter link social media share dan link yang tidak valid.
    Returns True jika harus di-skip.
    """
    href_lower = href.lower()
    judul_lower = judul.lower()
    
    # Skip berdasarkan href
    skip_patterns = [
        "facebook.com",
        "whatsapp.com",
        "twitter.com",
        "linkedin.com",
        "sharer.php",
        "api.whatsapp.com",
    ]
    for pattern in skip_patterns:
        if pattern in href_lower:
            return True
    
    # Skip jika href hanya "#"
    if href.strip() == "#" or href.strip() == BASE_URL + "/#":
        return True
    
    # Skip berdasarkan judul
    skip_titles = [
        "facebook",
        "whatsapp",
        "share",
        "share buttons",
        "share on",
    ]
    for pattern in skip_titles:
        if pattern in judul_lower:
            return True
    
    return False


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
    """Parse HTML homepage Kemahasiswaan, kembalikan list (judul, href)."""
    soup = BeautifulSoup(html, "html.parser")
    link_data = []
    seen = set()

    # Strategi 1: article card (col-lg-4 / col-md-6)
    for article in soup.find_all("article", class_=re.compile(r"col-lg-4|col-md-6")):
        card_div = article.find("div", class_=re.compile("post-card-content"))
        targets = card_div.find_all("a") if card_div else article.find_all("a")
        for a in targets:
            href  = _abs(a.get("href", ""))
            judul = (a.get("title") or a.get_text()).strip()
            
            # Filter social media share links
            if _is_social_share_link(href, judul):
                continue
            
            if not href or href in seen or not judul or len(judul) < 5:
                continue
            if "kemahasiswaan.gunadarma.ac.id" not in href:
                continue
            if href.rstrip("/") in [BASE_URL, URL.rstrip("/")]:
                continue
            seen.add(href)
            link_data.append((judul, href))

    # Strategi 2: slider overlay thumb-overlay a[title]
    for div in soup.find_all("div", class_=re.compile("thumb-overlay|img-hover-slide")):
        for a in div.find_all("a"):
            href  = _abs(a.get("href", ""))
            judul = (a.get("title") or a.get_text()).strip()
            
            # Filter social media share links
            if _is_social_share_link(href, judul):
                continue
            
            if not href or href in seen or not judul or len(judul) < 5:
                continue
            if "kemahasiswaan.gunadarma.ac.id" not in href:
                continue
            seen.add(href)
            link_data.append((judul, href))

    # Strategi 3: fallback semua link internal panjang
    if not link_data:
        for a in soup.find_all("a", href=True):
            href  = _abs(a["href"])
            judul = (a.get("title") or a.get_text()).strip()
            
            # Filter social media share links
            if _is_social_share_link(href, judul):
                continue
            
            if not href or href in seen or not judul or len(judul) < 10:
                continue
            if "kemahasiswaan.gunadarma.ac.id" not in href:
                continue
            if href.rstrip("/") in [BASE_URL, URL.rstrip("/")]:
                continue
            seen.add(href)
            link_data.append((judul, href))

    return link_data


def _parse_detail_html(html: str, item: dict):
    """Parse HTML halaman detail Kemahasiswaan dan isi field item."""
    soup = BeautifulSoup(html, "html.parser")

    # Judul: .entry-title.mb-50.font-weight-900
    judul_el = (
        soup.find(class_=re.compile(r"entry-title.*font-weight-900|font-weight-900.*entry-title"))
        or soup.find(class_="entry-title")
        or soup.find("h1")
    )
    if judul_el:
        t = judul_el.get_text(strip=True)
        if t:
            item["judul"] = t

    # Tanggal: .mr-10 (selector yang benar sesuai user)
    tgl_el = soup.find(class_="mr-10")
    if tgl_el:
        raw = tgl_el.get_text(strip=True)
        item["tanggal"] = raw
        # Coba extract format tanggal jika ada
        match = re.search(r"(\d{1,2}\s+\w+\s+\d{4}|\d{4}-\d{2}-\d{2})", raw)
        if match:
            item["tanggal"] = match.group(0)

    # Tanggal alternatif jika .mr-10 tidak ada
    if not item["tanggal"]:
        tgl_alt = soup.find("time")
        if tgl_alt:
            item["tanggal"] = tgl_alt.get("datetime", tgl_alt.get_text(strip=True))

    # Author: .author-name.font-weight-bold
    auth_el = soup.find(class_=re.compile(r"author-name.*font-weight-bold|author-name"))
    if auth_el:
        item["author"] = auth_el.get_text(strip=True)

    # Isi: .ck-content - dengan special handling untuk tabel delegasi
    isi_el = (
        soup.find(class_="ck-content")
        or soup.find(class_="entry-content")
        or soup.find("article")
    )
    if isi_el:
        # Process content with table detection
        processed_text, has_table = _process_content_with_table(isi_el)
        item["isi"] = processed_text
        
        if has_table:
            logger.info(f"[KEMAHASISWAAN] Tabel delegasi berhasil diformat. {log_content_length(processed_text, 'Total konten')}")
        else:
            logger.info(f"[KEMAHASISWAAN] {log_content_length(processed_text, 'Isi')}")
    else:
        item["isi"] = ""

    # File
    file_a = soup.find("a", href=re.compile(r"\.pdf|download|unduh"))
    if file_a:
        item["file_url"] = _abs(file_a.get("href", ""))


def _scrape_dengan_flaresolverr(limit: Optional[int]) -> List[Dict]:
    logger.info("[KEMAHASISWAAN] Menggunakan FlareSolverr...")

    html = get_html_via_flaresolverr(URL)
    if not html:
        logger.error("[KEMAHASISWAAN] FlareSolverr gagal.")
        return []

    logger.info(f"[KEMAHASISWAAN] HTML: {len(html):,} char")
    link_data = _parse_list_html(html)
    logger.info(f"[KEMAHASISWAAN] Link ditemukan: {len(link_data)}")

    if not link_data:
        with open(DEBUG_HTML_FILE, "w", encoding="utf-8") as f:
            f.write(html)
        logger.warning(f"[KEMAHASISWAAN] Tidak ada link. Debug: {os.path.abspath(DEBUG_HTML_FILE)}")
        return []

    if limit:
        link_data = link_data[:limit]

    hasil = []
    for judul_list, href in link_data:
        item = {
            "judul"   : judul_list,
            "tanggal" : "",
            "link"    : href,
            "sumber"  : SUMBER,
            "isi"     : "",
            "author"  : "",
            "file_url": "",
        }
        detail_html = get_html_via_flaresolverr(href)
        if detail_html:
            _parse_detail_html(detail_html, item)
            logger.info(f"[KEMAHASISWAAN] OK: {clean_log_text(item['judul'], 60)}")
        else:
            logger.warning(f"[KEMAHASISWAAN] Gagal detail: {href}")
        hasil.append(item)

    return hasil


def _wait_cloudflare(page, max_wait: int = 25000):
    try:
        page.wait_for_function(
            "!document.title.includes('Just a moment') && "
            "!document.title.includes('Tunggu sebentar')",
            timeout=max_wait
        )
        logger.info(f"[KEMAHASISWAAN] Cloudflare selesai: {page.title()!r}")
    except Exception:
        logger.warning(f"[KEMAHASISWAAN] Cloudflare masih aktif setelah {max_wait}ms.")


def _scrape_dengan_playwright(limit: Optional[int]) -> List[Dict]:
    logger.info("[KEMAHASISWAAN] Menggunakan Playwright (fallback)...")
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
                _wait_cloudflare(page, max_wait=25000)
                page.wait_for_timeout(4000)
            except PWTimeout as e:
                logger.error(f"[KEMAHASISWAAN] TIMEOUT: {e}")
                browser.close()
                return []

            html = page.content()
            if "Just a moment" in page.title() or "Tunggu sebentar" in page.title():
                logger.warning("[KEMAHASISWAAN] Cloudflare aktif. Simpan debug HTML.")
                with open(DEBUG_HTML_FILE, "w", encoding="utf-8") as f:
                    f.write(html)
                browser.close()
                return []

            link_data = _parse_list_html(html)
            logger.info(f"[KEMAHASISWAAN] Link: {len(link_data)}")
            if not link_data:
                with open(DEBUG_HTML_FILE, "w", encoding="utf-8") as f:
                    f.write(html)
                browser.close()
                return []

            if limit:
                link_data = link_data[:limit]

            for judul_list, href in link_data:
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
                    _wait_cloudflare(dpage, max_wait=15000)
                    dpage.wait_for_timeout(2000)
                    _parse_detail_html(dpage.content(), item)
                    dpage.close()
                    logger.info(f"[KEMAHASISWAAN] OK: {clean_log_text(item['judul'], 60)}")
                except Exception as e:
                    logger.warning(f"[KEMAHASISWAAN] Gagal detail {href}: {e}")
                    try:
                        dpage.close()
                    except Exception:
                        pass
                hasil.append(item)

            browser.close()

    except Exception as e:
        logger.error(f"[KEMAHASISWAAN] Playwright ERROR: {type(e).__name__}: {e}")
        if browser:
            try:
                browser.close()
            except Exception:
                pass

    return hasil


def scrape_kemahasiswaan(limit: Optional[int] = None) -> List[Dict]:
    logger.info(f"[KEMAHASISWAAN] Mulai scraping: {URL}")

    if is_flaresolverr_running():
        logger.info("[KEMAHASISWAAN] FlareSolverr terdeteksi.")
        hasil = _scrape_dengan_flaresolverr(limit)
        if hasil:
            logger.info(f"[KEMAHASISWAAN] Selesai via FlareSolverr. Total: {len(hasil)}")
            return hasil
        logger.warning("[KEMAHASISWAAN] FlareSolverr gagal, coba Playwright...")
    else:
        logger.warning("[KEMAHASISWAAN] FlareSolverr tidak berjalan. "
                       "Jalankan: docker run -d --name flaresolverr -p 8191:8191 "
                       "ghcr.io/flaresolverr/flaresolverr:latest")

    hasil = _scrape_dengan_playwright(limit)
    logger.info(f"[KEMAHASISWAAN] Selesai via Playwright. Total: {len(hasil)}")
    return hasil
