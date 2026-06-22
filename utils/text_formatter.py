"""
utils/text_formatter.py
Utilitas untuk membersihkan dan memformat teks berita
agar newline dan list bernomor tidak hilang.
"""

import re


def clean_news_text(text: str) -> str:
    """
    Bersihkan teks berita dengan mempertahankan newline dan list.
    
    Rules:
    - Pertahankan newline untuk paragraf
    - Pertahankan list bernomor (1. 2. 3.)
    - Rapikan spasi horizontal tanpa menghapus newline
    - Pastikan list berada di baris baru
    
    Args:
        text: Teks mentah dari scraper
        
    Returns:
        Teks yang sudah dibersihkan dengan newline yang rapi
    """
    if not text:
        return ""
    
    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    
    # Rapikan spasi horizontal (space dan tab), tapi jangan hapus newline
    text = re.sub(r"[ \t]+", " ", text)
    
    # Pastikan nomor list seperti "1. 2. 3." berada di baris baru
    # Cari pola: bukan newline diikuti angka dan titik
    text = re.sub(r"(?<!\n)(\d+\.\s+)", r"\n\1", text)
    
    # Jika setelah titik dua (:) langsung ada angka list, beri newline
    text = re.sub(r":\s*(?=\d+\.\s)", ":\n", text)
    
    # Rapikan newline berlebihan (max 2 newline berturut-turut)
    text = re.sub(r"\n{3,}", "\n\n", text)
    
    # Hapus spasi di awal/akhir setiap baris
    lines = text.split("\n")
    lines = [line.strip() for line in lines]
    text = "\n".join(lines)
    
    return text.strip()


def truncate_text(text: str, max_length: int = 3500) -> str:
    """
    Potong teks panjang dengan tetap mempertahankan struktur list/paragraf.
    
    Args:
        text: Teks yang akan dipotong
        max_length: Panjang maksimal karakter (default 3500 untuk Discord embed)
        
    Returns:
        Teks yang sudah dipotong dengan suffix "Baca selengkapnya"
    """
    if not text:
        return "Isi pengumuman tidak tersedia."
    
    # Jika teks pendek, return as-is
    if len(text) <= max_length:
        return text
    
    # Potong di max_length dan hapus spasi trailing
    cut = text[:max_length].rstrip()
    
    # Usahakan potong di newline terakhir agar list/paragraf tidak rusak
    # Cari newline terakhir di 70% sampai 100% dari max_length
    min_cut_pos = int(max_length * 0.7)
    last_newline = cut.rfind("\n", min_cut_pos)
    
    if last_newline > min_cut_pos:
        # Potong di newline terakhir
        cut = cut[:last_newline].rstrip()
    else:
        # Jika tidak ada newline di range tersebut, coba potong di spasi terakhir
        last_space = cut.rfind(" ", min_cut_pos)
        if last_space > min_cut_pos:
            cut = cut[:last_space].rstrip()
    
    # Tambahkan suffix
    return cut + "\n\n...\nBaca selengkapnya melalui link pengumuman."


def preserve_newlines_from_html(element, separator: str = "\n") -> str:
    """
    Helper untuk BeautifulSoup: extract text dengan separator newline.
    
    Args:
        element: BeautifulSoup element
        separator: Separator antar elemen (default: newline)
        
    Returns:
        Teks dengan newline yang dipertahankan
    """
    if not element:
        return ""
    
    # Gunakan get_text dengan separator newline
    text = element.get_text(separator=separator, strip=True)
    
    # Clean dengan fungsi clean_news_text
    return clean_news_text(text)
