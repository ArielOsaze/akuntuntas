"""
Periksa kesesuaian nama kolom antara kode dan skema basis data.

Cara pakai:
    python tools/periksa_kolom.py

Alat ini membaca setiap kunci yang diakses dari hasil query (mis. r["nama"])
pada halaman antarmuka, lalu membandingkannya dengan kolom tabel yang
benar-benar ada. Kesalahan nama kolom biasanya muncul sebagai
IndexError: No item with that key.
"""
from __future__ import annotations

import os
import re
import sqlite3
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
os.environ["AKUNTANSIID_DATA"] = str(AKAR / "_contoh")
sys.path.insert(0, str(AKAR / "src"))

# pola akses kolom: variabel["nama_kolom"]
POLA = re.compile(r"""\b([a-z_]{1,4})\[\s*["']([a-z_]+)["']\s*\]""")


def kolom_semua(conn) -> set:
    kumpulan = set()
    for (nama,) in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"):
        if nama.startswith("sqlite_"):
            continue
        for info in conn.execute(f"PRAGMA table_info('{nama}')"):
            kumpulan.add(info[1])
    return kumpulan


def main() -> int:
    from akuntansi_id import config, db

    config.ensure_dirs()
    db.init_db()

    conn = sqlite3.connect(str(config.DB_PATH))
    kolom = kolom_semua(conn)
    conn.close()

    print(f"kolom dikenali dari skema: {len(kolom)}")
    print()

    # kata yang bukan nama kolom (variabel biasa, dict lokal, dsb.)
    abaikan = {
        "id", "nama", "kode", "nilai", "data", "hasil", "isi", "teks", "kunci",
        "jenis", "tipe", "status", "total", "jumlah", "catatan", "label",
        "warna", "level", "pesan", "baris", "kolom", "judul", "sumber",
    }

    total = 0
    for p in sorted((AKAR / "src").rglob("*.py")):
        teks = p.read_text(encoding="utf-8")
        baris = teks.splitlines()
        temuan = []
        for i, b in enumerate(baris, 1):
            if b.lstrip().startswith("#"):
                continue
            for m in POLA.finditer(b):
                nama = m.group(2)
                if nama in kolom or nama in abaikan:
                    continue
                if nama.startswith("_") or len(nama) < 3:
                    continue
                temuan.append((i, nama, b.strip()[:80]))
        if temuan:
            total += len(temuan)
            print(f"{p.relative_to(AKAR)}")
            for n, nama, teks_b in temuan:
                print(f"   baris {n:4d}: ['{nama}']  {teks_b}")

    print()
    print("=" * 70)
    if total:
        print(f"HASIL: {total} akses kolom perlu diperiksa")
    else:
        print("HASIL: seluruh akses kolom cocok dengan skema")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
