"""
utils/logger.py
Konfigurasi logging sistem agregasi pengumuman.
Format log: [LEVEL] YYYY-MM-DD HH:MM:SS | pesan
Output: console (dengan warna) + file logs/sistem_YYYYMMDD.log (plain text)
"""

import logging
import os
from datetime import datetime

try:
    from colorama import Fore, Style, init as colorama_init
    colorama_init(autoreset=True)
    COLORS_AVAILABLE = True
except ImportError:
    COLORS_AVAILABLE = False


# ═══════════════════════════════════════════════════════════════════════
# Helper Functions untuk Log Formatting
# ═══════════════════════════════════════════════════════════════════════

def clean_log_text(text, max_length=150):
    """
    Bersihkan dan rapikan teks untuk log terminal.
    
    Rules:
    - Ubah newline menjadi spasi
    - Hapus spasi berlebih
    - Batasi panjang maksimal
    - Tambahkan '...' jika dipotong
    
    Args:
        text: String yang akan dibersihkan
        max_length: Panjang maksimal output (default 150)
    
    Returns:
        String bersih yang siap ditampilkan di log
    """
    if text is None:
        return ""
    
    text = str(text)
    
    # Ubah newline dan tab menjadi spasi
    text = text.replace("\n", " ").replace("\r", " ").replace("\t", " ")
    
    # Hapus spasi berlebih (multiple spaces jadi single space)
    text = " ".join(text.split())
    
    # Potong jika terlalu panjang
    if len(text) > max_length:
        return text[:max_length].rstrip() + "..."
    
    return text


def log_content_length(content, content_type="konten"):
    """
    Helper untuk log panjang konten tanpa menampilkan isinya.
    
    Args:
        content: String konten panjang
        content_type: Nama tipe konten (default: "konten")
    
    Returns:
        String info panjang konten
    """
    if not content:
        return f"{content_type.capitalize()} kosong"
    
    length = len(str(content))
    if length < 1000:
        return f"{content_type.capitalize()} berhasil diambil. Panjang: {length} karakter"
    else:
        return f"{content_type.capitalize()} berhasil diambil. Panjang: {length:,} karakter"


# ═══════════════════════════════════════════════════════════════════════
# Custom Formatter dengan Warna untuk Terminal
# ═══════════════════════════════════════════════════════════════════════

class ColoredFormatter(logging.Formatter):
    """
    Custom formatter yang menambahkan warna ANSI ke log level.
    Warna hanya diterapkan untuk console handler, bukan file handler.
    """
    
    # Mapping level ke warna
    LEVEL_COLORS = {
        'DEBUG':    Fore.LIGHTBLACK_EX if COLORS_AVAILABLE else '',
        'INFO':     Fore.CYAN if COLORS_AVAILABLE else '',
        'WARNING':  Fore.YELLOW if COLORS_AVAILABLE else '',
        'ERROR':    Fore.RED if COLORS_AVAILABLE else '',
        'CRITICAL': Fore.RED + Style.BRIGHT if COLORS_AVAILABLE else '',
    }
    
    # Warna untuk sumber scraper
    SUMBER_COLORS = {
        'BAAK':          Fore.LIGHTBLUE_EX if COLORS_AVAILABLE else '',
        'KEMAHASISWAAN': Fore.LIGHTMAGENTA_EX if COLORS_AVAILABLE else '',
        'STUDENTSITE':   Fore.LIGHTGREEN_EX if COLORS_AVAILABLE else '',
        'LEPKOM':        Fore.LIGHTYELLOW_EX if COLORS_AVAILABLE else '',
        'PENDAFTARAN':   Fore.LIGHTCYAN_EX if COLORS_AVAILABLE else '',
        'FlareSolverr':  Fore.MAGENTA if COLORS_AVAILABLE else '',
    }
    
    def format(self, record):
        # Format base message
        formatted = super().format(record)
        
        if not COLORS_AVAILABLE:
            return formatted
        
        # Tambahkan warna pada level
        level_color = self.LEVEL_COLORS.get(record.levelname, '')
        if level_color:
            formatted = formatted.replace(
                f"[{record.levelname}]",
                f"{level_color}[{record.levelname}]{Style.RESET_ALL}"
            )
        
        # Tambahkan warna pada sumber [BAAK], [KEMAHASISWAAN], dll
        for sumber, color in self.SUMBER_COLORS.items():
            if f"[{sumber}]" in formatted:
                formatted = formatted.replace(
                    f"[{sumber}]",
                    f"{color}[{sumber}]{Style.RESET_ALL}"
                )
        
        return formatted


# ═══════════════════════════════════════════════════════════════════════
# Setup Logger
# ═══════════════════════════════════════════════════════════════════════

def setup_logger(name: str = "agregasi_pengumuman") -> logging.Logger:
    logger = logging.getLogger(name)

    # Hindari duplikasi handler jika logger sudah ada
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    # ── Console Handler (dengan warna) ──────────────────────────────────
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Gunakan ColoredFormatter untuk console
    console_formatter = ColoredFormatter(
        fmt="[%(levelname)s] %(asctime)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(console_formatter)
    
    try:
        # Windows: paksa encoding UTF-8 di stream
        import sys
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        console_handler.stream = open(
            sys.stdout.fileno(), mode="w", encoding="utf-8", closefd=False, buffering=1
        )
    except Exception:
        pass  # abaikan jika terminal tidak mendukung, gunakan default
    
    logger.addHandler(console_handler)

    # ── File Handler (plain text, tanpa warna) ──────────────────────────
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    log_filename = os.path.join(
        log_dir, f"sistem_{datetime.now().strftime('%Y%m%d')}.log"
    )
    
    file_handler = logging.FileHandler(log_filename, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    
    # Gunakan formatter biasa (tanpa warna) untuk file
    file_formatter = logging.Formatter(
        fmt="[%(levelname)s] %(asctime)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_formatter)
    
    logger.addHandler(file_handler)

    return logger


# Logger utama yang diimpor oleh semua modul
logger = setup_logger()
