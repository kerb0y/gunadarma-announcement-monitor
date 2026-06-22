"""
database/db.py
Modul untuk koneksi dan operasi database MySQL.
Menyediakan fungsi: init_db, simpan_pengumuman, cek_duplikat.

Skema tabel pengumuman (v2):
  Kolom baru: isi (TEXT), author (VARCHAR 255), file_url (VARCHAR 500)
  init_db() secara otomatis menambahkan kolom jika belum ada (safe migration).
"""

import mysql.connector
from mysql.connector import Error
from typing import List, Dict, Optional

import config
from utils.logger import logger


def get_connection() -> Optional[mysql.connector.MySQLConnection]:
    """Membuat koneksi ke database MySQL."""
    try:
        conn = mysql.connector.connect(
            host=config.DB_HOST,
            port=config.DB_PORT,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            database=config.DB_NAME,
            charset="utf8mb4",
            collation="utf8mb4_unicode_ci",
        )
        return conn
    except Error as e:
        logger.error(f"Gagal koneksi ke database: {e}")
        return None


def _tambah_kolom_jika_belum_ada(cursor, tabel: str, kolom: str, definisi: str):
    """Helper: tambahkan kolom ke tabel jika belum ada (safe ALTER TABLE)."""
    cursor.execute(
        "SELECT COUNT(*) FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND COLUMN_NAME = %s",
        (tabel, kolom)
    )
    (ada,) = cursor.fetchone()
    if not ada:
        cursor.execute(f"ALTER TABLE `{tabel}` ADD COLUMN {kolom} {definisi}")
        logger.info(f"Kolom '{kolom}' ditambahkan ke tabel '{tabel}'.")


def init_db() -> bool:
    """
    Menginisialisasi database: membuat database dan tabel jika belum ada.
    Jika tabel sudah ada, pastikan kolom baru (isi, author, file_url) sudah ada.
    Dipanggil sekali saat program pertama kali dijalankan.
    """
    try:
        conn = mysql.connector.connect(
            host=config.DB_HOST,
            port=config.DB_PORT,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            charset="utf8mb4",
        )
        cursor = conn.cursor()

        # Buat database jika belum ada
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS `{config.DB_NAME}` "
            f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        cursor.execute(f"USE `{config.DB_NAME}`")

        # Buat tabel pengumuman dengan semua kolom
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS pengumuman (
            id          INT AUTO_INCREMENT PRIMARY KEY,
            judul       TEXT NOT NULL,
            tanggal     VARCHAR(100) DEFAULT '',
            link        VARCHAR(500) NOT NULL,
            sumber      VARCHAR(100) NOT NULL,
            isi         TEXT DEFAULT NULL,
            author      VARCHAR(255) DEFAULT '',
            file_url    VARCHAR(500) DEFAULT '',
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uq_link_sumber (link(450), sumber)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """
        cursor.execute(create_table_sql)
        conn.commit()

        # Safe migration: tambahkan kolom baru jika tabel sudah ada sebelumnya
        _tambah_kolom_jika_belum_ada(cursor, "pengumuman", "isi",      "TEXT DEFAULT NULL")
        _tambah_kolom_jika_belum_ada(cursor, "pengumuman", "author",   "VARCHAR(255) DEFAULT ''")
        _tambah_kolom_jika_belum_ada(cursor, "pengumuman", "file_url", "VARCHAR(500) DEFAULT ''")
        conn.commit()

        logger.info("Database dan tabel berhasil diinisialisasi.")
        cursor.close()
        conn.close()
        return True

    except Error as e:
        logger.error(f"Gagal menginisialisasi database: {e}")
        return False


def cek_duplikat(link: str, sumber: str) -> bool:
    """
    Mengecek apakah pengumuman sudah tersimpan di database.

    Returns:
        True jika sudah ada (duplikat), False jika belum.
    """
    conn = get_connection()
    if not conn:
        return False

    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM pengumuman WHERE link = %s AND sumber = %s",
            (link, sumber)
        )
        (count,) = cursor.fetchone()
        return count > 0
    except Error as e:
        logger.error(f"Gagal mengecek duplikat: {e}")
        return False
    finally:
        cursor.close()
        conn.close()


def simpan_pengumuman(pengumuman: Dict) -> bool:
    """
    Menyimpan satu pengumuman ke database MySQL (INSERT IGNORE untuk duplikat).

    Args:
        pengumuman: Dict dengan key: judul, tanggal, link, sumber,
                    isi, author, file_url.

    Returns:
        True jika data baru berhasil disimpan, False jika duplikat atau gagal.
    """
    conn = get_connection()
    if not conn:
        return False

    try:
        cursor = conn.cursor()
        query = """
        INSERT IGNORE INTO pengumuman
            (judul, tanggal, link, sumber, isi, author, file_url)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        values = (
            pengumuman.get("judul",    "") or "",
            pengumuman.get("tanggal",  "") or "",
            pengumuman.get("link",     "") or "",
            pengumuman.get("sumber",   "") or "",
            pengumuman.get("isi",      "") or "",
            pengumuman.get("author",   "") or "",
            pengumuman.get("file_url", "") or "",
        )
        cursor.execute(query, values)
        conn.commit()
        return cursor.rowcount > 0

    except Error as e:
        logger.error(f"Gagal menyimpan pengumuman ke database: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()


def simpan_banyak_pengumuman(list_pengumuman: List[Dict]) -> int:
    """
    Menyimpan banyak pengumuman sekaligus ke database.

    Returns:
        Jumlah pengumuman baru yang berhasil disimpan.
    """
    jumlah_baru = 0
    for pengumuman in list_pengumuman:
        if simpan_pengumuman(pengumuman):
            jumlah_baru += 1
    return jumlah_baru
