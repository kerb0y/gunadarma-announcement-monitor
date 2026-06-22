"""
test_scraper.py
Script pengujian scraper - selalu menampilkan output di terminal.

CARA MENJALANKAN (dari folder project):
  py test_scraper.py                -> uji semua website
  py test_scraper.py lepkom         -> uji LEPKOM
  py test_scraper.py kemahasiswaan  -> uji Kemahasiswaan
  py test_scraper.py studentsite    -> uji Studentsite
  py test_scraper.py baak           -> uji BAAK
  py test_scraper.py pendaftaran    -> uji Pendaftaran
  py test_scraper.py all            -> uji semua website
  
  py test_scraper.py --fast all     -> uji semua dengan mode fast (1 item per website)
  py test_scraper.py --fast baak    -> uji BAAK dengan mode fast
"""

import sys
import os
import traceback
import importlib
import threading
import time as time_module

# Pastikan direktori project ada di path agar import modul berjalan
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── Konfigurasi encoding untuk output Windows ────────────────────────────────
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
        sys.stderr.reconfigure(encoding="utf-8", line_buffering=True)
    except Exception:
        pass  # abaikan jika terminal tidak mendukung
# ─────────────────────────────────────────────────────────────────────────────

LIMIT = 5  # Jumlah pengumuman yang diambil per website
FAST_MODE = False  # Mode fast untuk testing cepat (1 item saja)
TIMEOUT_SECONDS = 180  # Timeout per scraper (3 menit)


def garis(char="=", lebar=60):
    print(char * lebar, flush=True)


def cetak(*args, **kwargs):
    """Print dengan flush agar selalu tampil di terminal."""
    print(*args, **kwargs, flush=True)


# ── Daftar scraper yang tersedia ─────────────────────────────────────────────
DAFTAR_SCRAPER = {
    "lepkom"        : ("LEPKOM",        "scraper.lepkom",        "scrape_lepkom"),
    "kemahasiswaan" : ("KEMAHASISWAAN", "scraper.kemahasiswaan", "scrape_kemahasiswaan"),
    "studentsite"   : ("STUDENTSITE",   "scraper.studentsite",   "scrape_studentsite"),
    "baak"          : ("BAAK",          "scraper.baak",          "scrape_baak"),
    "pendaftaran"   : ("PENDAFTARAN",   "scraper.pendaftaran",   "scrape_pendaftaran"),
}
# ─────────────────────────────────────────────────────────────────────────────


def import_scraper(modul_path: str, fungsi_name: str):
    """
    Import modul scraper dan kembalikan fungsinya.
    Mengembalikan (fungsi, None) jika berhasil, atau (None, pesan_error) jika gagal.
    """
    try:
        modul  = importlib.import_module(modul_path)
        fungsi = getattr(modul, fungsi_name)
        return fungsi, None
    except ModuleNotFoundError as e:
        return None, f"Modul tidak ditemukan: {e}"
    except AttributeError as e:
        return None, f"Fungsi tidak ditemukan di modul: {e}"
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def test_satu_scraper(key: str) -> dict:
    """
    Menjalankan satu scraper dan mencetak hasilnya secara lengkap.
    Returns dict dengan 'nama', 'berhasil', 'jumlah', 'error' untuk summary.
    """
    if key not in DAFTAR_SCRAPER:
        cetak(f"\n[ERROR] Argumen tidak dikenali: '{key}'")
        cetak(f"  Pilihan valid : {', '.join(DAFTAR_SCRAPER.keys())} atau 'all'")
        cetak(f"  Contoh        : py test_scraper.py baak")
        return {"nama": key, "berhasil": False, "jumlah": 0, "error": "Argumen tidak valid"}

    nama, modul_path, fungsi_name = DAFTAR_SCRAPER[key]

    cetak()
    garis()
    cetak(f"  MENGUJI: {nama}")
    garis()

    # ── Import ────────────────────────────────────────────────────────────
    cetak(f"  Mengimpor {modul_path}.{fungsi_name} ...")
    fungsi, error = import_scraper(modul_path, fungsi_name)
    if error:
        cetak(f"\n[ERROR] Gagal mengimpor scraper '{nama}':")
        cetak(f"  {error}")
        cetak("\n  Kemungkinan penyebab:")
        cetak("    - Package belum terinstal (jalankan: pip install -r requirements.txt)")
        cetak("    - File scraper rusak atau ada syntax error")
        return {"nama": nama, "berhasil": False, "jumlah": 0, "error": f"Import error: {error}"}
    cetak(f"  Import berhasil.")
    cetak()

    # ── Eksekusi scraper dengan monitoring timeout ───────────────────────
    limit_aktual = 1 if FAST_MODE else LIMIT
    if key == "pendaftaran" and not FAST_MODE:
        # Website pendaftaran saat ini hanya ada 2 berita
        limit_aktual = 2
        cetak(f"  Memulai scraping, mengambil maks. {limit_aktual} pengumuman (pendaftaran hanya ada 2)...")
    else:
        mode_info = " [FAST MODE]" if FAST_MODE else ""
        cetak(f"  Memulai scraping, mengambil maks. {limit_aktual} pengumuman{mode_info}...")
    cetak(f"  Timeout maksimal: {TIMEOUT_SECONDS} detik")
    cetak()

    hasil = []
    error_msg = ""
    completed = {"flag": False, "result": None, "error": None}
    
    def run_scraper_thread():
        """Thread worker untuk menjalankan scraper."""
        try:
            result = fungsi(limit=limit_aktual)
            completed["flag"] = True
            completed["result"] = result
        except Exception as e:
            completed["flag"] = True
            completed["error"] = {
                "type": type(e).__name__,
                "message": str(e)[:100],
                "traceback": traceback.format_exc()
            }
    
    # Jalankan scraper di thread terpisah
    thread = threading.Thread(target=run_scraper_thread, daemon=True)
    thread.start()
    
    # Monitoring dengan timeout
    start_time = time_module.time()
    last_update = start_time
    
    while thread.is_alive():
        thread.join(timeout=5)  # Check setiap 5 detik
        elapsed = time_module.time() - start_time
        
        # Update progress setiap 30 detik
        if time_module.time() - last_update >= 30:
            cetak(f"  ... masih berjalan ({int(elapsed)}s / {TIMEOUT_SECONDS}s)")
            last_update = time_module.time()
        
        # Timeout check
        if elapsed >= TIMEOUT_SECONDS:
            cetak()
            cetak(f"[WARNING] Scraper '{nama}' timeout setelah {TIMEOUT_SECONDS} detik.")
            cetak(f"          Proses masih berjalan di background, lanjut ke website berikutnya...")
            cetak(f"          Catatan: Thread daemon akan dibersihkan otomatis saat program selesai.")
            cetak()
            return {"nama": nama, "berhasil": False, "jumlah": 0, "error": f"Timeout {TIMEOUT_SECONDS}s"}
    
    # Thread selesai, cek hasilnya
    if not completed["flag"]:
        cetak(f"[ERROR] Scraper '{nama}' selesai tanpa hasil.")
        return {"nama": nama, "berhasil": False, "jumlah": 0, "error": "Tidak ada hasil"}
    
    if completed["error"]:
        err = completed["error"]
        error_msg = f"{err['type']}: {err['message']}"
        cetak(f"[ERROR] Scraper '{nama}' gagal dengan exception:")
        cetak(f"  {error_msg}")
        cetak()
        cetak("--- Traceback ---")
        cetak(err["traceback"])
        cetak("--- Akhir traceback ---")
        return {"nama": nama, "berhasil": False, "jumlah": 0, "error": error_msg}
    
    hasil = completed["result"]

    # ── Hasil ─────────────────────────────────────────────────────────────
    cetak(f"[INFO]  Scraping selesai.")
    cetak(f"[INFO]  Jumlah pengumuman ditemukan: {len(hasil)}")
    cetak()

    if not hasil:
        cetak(f"[WARN]  Data kosong dari {nama}.")
        cetak(f"        Kemungkinan penyebab:")
        cetak(f"          1. Selector CSS tidak cocok dengan struktur HTML saat ini")
        cetak(f"          2. Website memerlukan login / memblokir headless browser")
        cetak(f"          3. Website sedang down atau timeout")
        cetak(f"          4. Cek file debug_*.html yang dihasilkan untuk inspeksi HTML")
        cetak(f"          5. Buka logs/sistem_*.log untuk detail error")
        return {"nama": nama, "berhasil": False, "jumlah": 0, "error": "Data kosong"}

    for i, item in enumerate(hasil, 1):
        judul    = str(item.get("judul",    "—")).strip()
        tanggal  = str(item.get("tanggal",  "")).strip() or "Tidak tersedia"
        link     = str(item.get("link",     "—")).strip()
        sumber   = str(item.get("sumber",   "—")).strip()
        isi      = str(item.get("isi",      "")).strip()
        author   = str(item.get("author",   "")).strip()
        file_url = str(item.get("file_url", "")).strip()

        cetak(f"  [{i}]")
        cetak(f"      Judul    : {judul[:90]}")
        cetak(f"      Tanggal  : {tanggal}")
        cetak(f"      Link     : {link[:100]}")
        cetak(f"      Sumber   : {sumber}")
        if author:
            cetak(f"      Author   : {author[:60]}")
        if isi:
            cetak(f"      Isi      : {isi[:120]}{'...' if len(isi) > 120 else ''}")
        if file_url:
            cetak(f"      File/URL : {file_url[:100]}")
        cetak()

    cetak(f"[OK]  {nama}: {len(hasil)} pengumuman berhasil diambil.")
    return {"nama": nama, "berhasil": True, "jumlah": len(hasil), "error": ""}


def main():
    global FAST_MODE
    
    garis()
    cetak("  TEST SCRAPER - SISTEM AGREGASI PENGUMUMAN GUNADARMA")
    garis()
    cetak(f"  Python  : {sys.version.split()[0]}")
    
    # Parse arguments
    args = sys.argv[1:]
    target = "all"
    
    if "--fast" in args:
        FAST_MODE = True
        args.remove("--fast")
        cetak(f"  Mode    : FAST (1 item per website)")
    
    if len(args) > 0:
        target = args[0].lower().strip()
    
    cetak(f"  Target  : {target if target != 'all' else 'all (semua)'}")
    cetak(f"  Website : {', '.join(DAFTAR_SCRAPER.keys())}")
    cetak()

    # Kumpulkan hasil untuk summary
    hasil_summary = []
    
    if target == "all":
        for key in DAFTAR_SCRAPER:
            result = test_satu_scraper(key)
            hasil_summary.append(result)
    else:
        result = test_satu_scraper(target)
        hasil_summary.append(result)

    # Tampilkan summary akhir
    cetak()
    garis("=")
    cetak("  SUMMARY TEST SCRAPER")
    garis("=")
    cetak()
    
    total_data = 0
    berhasil_count = 0
    gagal_list = []
    
    for res in hasil_summary:
        nama = res.get("nama", "?")
        berhasil = res.get("berhasil", False)
        jumlah = res.get("jumlah", 0)
        error = res.get("error", "")
        
        if berhasil:
            status_icon = "[OK]"
            berhasil_count += 1
            total_data += jumlah
            cetak(f"  {status_icon} {nama:15s} : {jumlah} data")
        else:
            status_icon = "[GAGAL]"
            gagal_list.append((nama, error))
            cetak(f"  {status_icon} {nama:15s} : {error[:50]}")
    
    cetak()
    garis("-")
    cetak(f"  Total website berhasil : {berhasil_count}/{len(hasil_summary)}")
    cetak(f"  Total data ditemukan   : {total_data}")
    cetak()
    
    if gagal_list:
        cetak("  Website yang gagal:")
        for nama, error in gagal_list:
            cetak(f"    - {nama}: {error[:60]}")
        cetak()
    
    garis("=")
    cetak("  TEST SELESAI")
    garis("=")
    cetak()


if __name__ == "__main__":
    main()
