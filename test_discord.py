"""
test_discord.py
Test sederhana untuk Discord Webhook.
Hanya mengirim satu pesan test tanpa memakai bot token.
"""

import os
from dotenv import load_dotenv
import requests

# Load .env
load_dotenv()

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")

def test_discord_webhook():
    """Kirim pesan test ke Discord webhook."""
    
    if not DISCORD_WEBHOOK_URL:
        print("[ERROR] DISCORD_WEBHOOK_URL kosong di file .env")
        print("Tambahkan webhook URL ke file .env untuk test Discord.")
        return False
    
    print(f"[INFO] Webhook URL: {DISCORD_WEBHOOK_URL[:50]}...")
    print("[INFO] Mengirim pesan test ke Discord...")
    
    pesan = "✅ Sistem Agregasi Pengumuman Gunadarma berhasil terhubung ke Discord."
    
    try:
        response = requests.post(
            DISCORD_WEBHOOK_URL,
            json={"content": pesan},
            timeout=10,
        )
        
        if response.status_code in (200, 204):
            print("[SUCCESS] Pesan test berhasil dikirim ke Discord!")
            print(f"[INFO] Status code: {response.status_code}")
            return True
        else:
            print(f"[ERROR] Gagal kirim pesan. Status code: {response.status_code}")
            print(f"[ERROR] Response: {response.text[:200]}")
            return False
            
    except requests.exceptions.Timeout:
        print("[ERROR] Timeout saat mengirim pesan ke Discord.")
        return False
    except requests.exceptions.ConnectionError:
        print("[ERROR] Gagal koneksi ke Discord webhook. Cek URL webhook.")
        return False
    except Exception as e:
        print(f"[ERROR] Error tidak terduga: {type(e).__name__}: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("TEST DISCORD WEBHOOK")
    print("=" * 60)
    test_discord_webhook()
    print("=" * 60)
