"""
Perbaiki nama ikon yang salah pada tombol.

Masalah yang diperbaiki: 41 tombol memakai nama ikon yang tidak dikenal,
sehingga tampil tanpa gambar apa pun. Tombol "Tambah" di seluruh halaman
memakai nama "+" sedangkan ikon yang tersedia bernama "tambah", sehingga
tombol tambah tampil polos tanpa penanda.

Setiap nama yang salah diganti dengan nama ikon yang benar, dan satu
parameter yang tertukar diperbaiki.

Cara pakai:
    python tools/perbaiki_ikon_salah.py
"""
from __future__ import annotations

import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
SUMBER = AKAR / "src" / "akuntansi_id"

# Pasangan nama salah dan nama yang benar.
GANTI = {
    'ikon="+"': 'ikon="tambah"',
    'ikon="⊘"': 'ikon="nonaktif"',
    'ikon="⟲"': 'ikon="segarkan"',
    'ikon="proses"': 'ikon="transfer"',
    'ikon("+"': 'ikon("tambah"',
    'ikon("⊘"': 'ikon("nonaktif"',
    'ikon("⟲"': 'ikon("segarkan"',
}


def main() -> int:
    if not SUMBER.exists():
        print(f"  folder sumber tidak ditemukan: {SUMBER}")
        return 2

    total = 0
    berkas_diubah = []

    for f in sorted(SUMBER.rglob("*.py")):
        if "__pycache__" in str(f) or f.name == "icons.py":
            continue
        teks = f.read_text(encoding="utf-8")
        asli = teks
        jumlah = 0

        for salah, benar in GANTI.items():
            n = teks.count(salah)
            if n:
                teks = teks.replace(salah, benar)
                jumlah += n

        if teks != asli:
            f.write_text(teks, encoding="utf-8")
            berkas_diubah.append((f.relative_to(AKAR), jumlah))
            total += jumlah

    print("=" * 74)
    print("  PERBAIKI NAMA IKON YANG SALAH")
    print("=" * 74)
    print()
    print(f"  berkas diubah : {len(berkas_diubah)}")
    print(f"  tombol diperbaiki: {total}")
    print()
    for nama, n in berkas_diubah:
        print(f"    {nama}: {n} tombol")
    print("=" * 74)

    return 0


if __name__ == "__main__":
    sys.exit(main())
