"""
Periksa: seluruh kode akun yang dipakai kode harus ada di bagan akun.

Kode akun yang ditulis di dalam program, misalnya pada modul pajak dan
penjualan, harus benar benar ada di bagan akun. Bila tidak ada, jurnal yang
dibuat otomatis akan gagal disimpan, atau tersimpan tanpa nama akun
sehingga laporannya salah.

Pemeriksaan ini menemukan ketidakcocokan seperti itu sebelum sampai ke
pengguna.

Cara pakai:
    python tools/periksa_kode_akun.py
"""
from __future__ import annotations

import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "src"))

FOLDER = Path(tempfile.mkdtemp(prefix="akuntuntas_kode_akun_"))
os.environ["LOCALAPPDATA"] = str(FOLDER)

from akuntansi_id import db, services  # noqa: E402

# Berkas yang diperiksa: kode program, bukan berkas uji.
LEWATI = {"coa.py", "schema_ext.py", "db.py"}


# Kode akun yang dibuat sendiri oleh program saat dibutuhkan. Kode seperti
# ini memang tidak ada pada bagan akun bawaan, jadi tidak dianggap hilang.
DIBUAT_SENDIRI = {"3900"}


def kode_akun_dipakai() -> dict[str, list[str]]:
    """
    Kumpulkan kode akun yang ditulis di dalam kode program.

    Dua bentuk pemakaian ditangkap: sebagai bagian permintaan jurnal
    ("kode_akun": "1001"), dan sebagai kode yang ditetapkan langsung
    (kode = "1001"). Bentuk kedua mudah terlewat, padahal justru di situ
    ditemukan kode yang tidak ada pada bagan akun.

    Mengembalikan kamus kode -> daftar berkas yang memakainya.
    """
    hasil: dict[str, list[str]] = {}
    pola = (
        re.compile(r'"kode_akun":\s*"(\d{4})"'),
        re.compile(r'kode(?:_laba|_akun)?\s*=\s*"(\d{4})"'),
    )

    for f in (AKAR / "src").rglob("*.py"):
        if f.name in LEWATI:
            continue
        try:
            isi = f.read_text(encoding="utf-8")
        except Exception:
            continue
        for p in pola:
            for kode in p.findall(isi):
                if kode in DIBUAT_SENDIRI:
                    continue
                hasil.setdefault(kode, [])
                nama = str(f.relative_to(AKAR / "src"))
                if nama not in hasil[kode]:
                    hasil[kode].append(nama)
    return hasil


def main() -> int:
    print("=" * 76)
    print("  PERIKSA KODE AKUN YANG DIPAKAI PROGRAM")
    print("=" * 76)
    print()

    db.init_db()
    baris = db.q1("SELECT id FROM companies ORDER BY id LIMIT 1")
    if baris is None:
        cid = services.create_company("PT Periksa Akun", bentuk="pt")
    else:
        cid = baris["id"]

    tersedia = {
        r["kode"]: r["nama"] for r in db.q(
            "SELECT kode, nama FROM accounts WHERE company_id = ?", (cid,))
    }
    print(f"  akun pada bagan akun: {len(tersedia)}")
    print()

    dipakai = kode_akun_dipakai()
    print(f"  kode akun yang dipakai program: {len(dipakai)}")
    print()

    hilang = []
    for kode in sorted(dipakai):
        nama = tersedia.get(kode)
        if nama is None:
            hilang.append((kode, dipakai[kode]))
            print(f"  [HILANG] {kode}  dipakai di: {', '.join(dipakai[kode])}")
        else:
            print(f"  [ADA]    {kode}  {nama[:44]}")

    print()
    print("=" * 76)
    if hilang:
        print(f"  HASIL: {len(hilang)} kode akun dipakai tetapi tidak ada")
        print()
        print("  Yang perlu ditambahkan ke bagan akun:")
        for kode, berkas in hilang:
            print(f"    - {kode}  ({', '.join(berkas)})")
    else:
        print("  HASIL: seluruh kode akun yang dipakai sudah ada")
    print("=" * 76)

    return 1 if hilang else 0


if __name__ == "__main__":
    try:
        kode_keluar = main()
    finally:
        shutil.rmtree(FOLDER, ignore_errors=True)
    sys.exit(kode_keluar)
