"""
utils/flaresolverr.py
Helper untuk mengirim request melalui FlareSolverr proxy.
FlareSolverr harus berjalan di http://localhost:8191

Cara menjalankan FlareSolverr (Docker):
  docker run -d --name flaresolverr -p 8191:8191 -e LOG_LEVEL=info ghcr.io/flaresolverr/flaresolverr:latest

Referensi: https://github.com/FlareSolverr/FlareSolverr
"""

import time
import requests
from typing import Optional

from utils.logger import logger

FLARESOLVERR_URL = "http://localhost:8191/v1"
TIMEOUT_SECONDS  = 120   # FlareSolverr butuh 15-120 detik untuk Managed Challenge
MAX_RETRY        = 2     # Maksimal percobaan ulang jika gagal
JEDA_RETRY       = 8     # Detik jeda sebelum retry


def is_flaresolverr_running() -> bool:
    """Cek apakah FlareSolverr sedang berjalan di localhost:8191."""
    try:
        r = requests.get("http://localhost:8191/health", timeout=5)
        return r.status_code == 200
    except Exception:
        return False


def get_html_via_flaresolverr(url: str) -> Optional[str]:
    """
    Ambil HTML halaman melalui FlareSolverr untuk bypass Cloudflare.
    Melakukan retry otomatis hingga MAX_RETRY kali jika gagal.

    Args:
        url: URL yang ingin diakses.

    Returns:
        HTML string jika berhasil, None jika semua percobaan gagal.
    """
    payload = {
        "cmd"       : "request.get",
        "url"       : url,
        "maxTimeout": TIMEOUT_SECONDS * 1000,  # milidetik
    }

    for percobaan in range(1, MAX_RETRY + 1):
        try:
            if percobaan > 1:
                logger.info(f"[FlareSolverr] Retry ke-{percobaan} untuk: {url}")
                time.sleep(JEDA_RETRY)

            r = requests.post(
                FLARESOLVERR_URL,
                json=payload,
                timeout=TIMEOUT_SECONDS + 15
            )
            data = r.json()

            if data.get("status") != "ok":
                msg = data.get("message", "")
                logger.warning(
                    f"[FlareSolverr] Percobaan {percobaan}/{MAX_RETRY} gagal: "
                    f"{data.get('status')} - {msg[:80]}"
                )
                continue  # lanjut ke retry

            solution = data.get("solution", {})
            html     = solution.get("response", "")
            status   = solution.get("status", 0)

            if not html:
                logger.warning(f"[FlareSolverr] Percobaan {percobaan}: HTML kosong.")
                continue

            logger.info(
                f"[FlareSolverr] OK (percobaan {percobaan}) - "
                f"HTTP {status}, HTML: {len(html):,} char"
            )
            return html

        except requests.exceptions.ConnectionError:
            logger.error(
                "[FlareSolverr] Tidak bisa terhubung ke localhost:8191. "
                "Pastikan FlareSolverr sudah berjalan via Docker."
            )
            return None  # Tidak perlu retry jika server tidak berjalan

        except requests.exceptions.Timeout:
            logger.warning(
                f"[FlareSolverr] Percobaan {percobaan}/{MAX_RETRY} timeout "
                f"setelah {TIMEOUT_SECONDS + 15}s."
            )

        except Exception as e:
            logger.error(f"[FlareSolverr] Error tidak terduga: {type(e).__name__}: {e}")
            return None

    logger.error(
        f"[FlareSolverr] Semua {MAX_RETRY} percobaan gagal untuk: {url}"
    )
    return None
