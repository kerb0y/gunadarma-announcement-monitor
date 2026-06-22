"""
utils/logger.py
Konfigurasi logging sistem agregasi pengumuman.
Format log: [LEVEL] YYYY-MM-DD HH:MM:SS | pesan
Output: console + file logs/sistem_YYYYMMDD.log
"""

import logging
import os
from datetime import datetime


def setup_logger(name: str = "agregasi_pengumuman") -> logging.Logger:
    logger = logging.getLogger(name)

    # Hindari duplikasi handler jika logger sudah ada
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    # Format sederhana, tanpa karakter Unicode
    formatter = logging.Formatter(
        fmt="[%(levelname)s] %(asctime)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console handler — pakai UTF-8 agar tidak ada karakter aneh di Windows
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
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

    # File handler
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    log_filename = os.path.join(
        log_dir, f"sistem_{datetime.now().strftime('%Y%m%d')}.log"
    )
    file_handler = logging.FileHandler(log_filename, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


# Logger utama yang diimpor oleh semua modul
logger = setup_logger()
