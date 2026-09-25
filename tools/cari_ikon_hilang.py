"""
Cari nama ikon yang dipakai di kode tetapi belum digambar di icons.py.

Ikon yang namanya tidak dikenal akan tampil kosong tanpa gambar apa pun,
sehingga tombolnya terlihat polos dan pengguna tidak tahu fungsinya.
Masalah ini tidak menimbulkan pesan galat, jadi mudah terlewat.

Cara pakai:
    python tools/cari_ikon_hilang.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
SUMBER = AKAR / "src" / "akuntansi_id"

# Ikon yang memang digambar, dibaca dari icons.py.
ICONS = SUMBER / "ui" / "icons.py"

# Pola pemakaian ikon di kode.
# Hanya parameter bernama ikon="..." dan pemanggilan ikon("...") yang
# diperiksa. Pemanggilan pixmap(nama, warna, ukuran) tidak diperiksa
# karena parameter keduanya memang warna, bukan nama ikon.
# Batas kata (\b) dipakai supaya "warna_ikon = ..." tidak ikut terbaca
# sebagai parameter ikon.
POLA = [
    re.compile(r'\bikon\s*=\s*"([^"]*)"'),         # parameter ikon="..."
    re.compile(r'\bikon\(\s*"([^"]*)"'),           # pemanggilan ikon("...")
]


def main() -> int:
    if not ICONS.exists():
        print(f"  icons.py tidak ditemukan: {ICONS}")
        return 2

    isi_ikon = ICONS.read_text(encoding="utf-8")
    tersedia = set(re.findall(r'nama\s*==\s*"([^"]*)"', isi_ikon))

    print("=" * 76)
    print("  CARI NAMA IKON YANG BELUM DIGAMBAR")
    print("=" * 76)
    print()
    print(f"  ikon tersedia: {len(tersedia)}")
    print()

    hilang: dict[str, list[str]] = {}

    for f in sorted(SUMBER.rglob("*.py")):
        if "__pycache__" in str(f) or f.name == "icons.py":
            continue
        for i, baris in enumerate(
                f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            for pola in POLA:
                for m in pola.finditer(baris):
                    nama = m.group(1)
                    # Nama kosong berarti memang tanpa ikon, bukan masalah.
                    if not nama.strip():
                        continue
                    if nama not in tersedia:
                        kunci = nama
                        hilang.setdefault(kunci, []).append(
                            f"{f.relative_to(AKAR)}:{i}")

    if not hilang:
        print("  SELURUH nama ikon yang dipakai sudah tersedia.")
        print("=" * 76)
        return 0

    print(f"  {len(hilang)} nama ikon dipakai tetapi belum digambar:")
    print()
    for nama, tempat in sorted(hilang.items()):
        print(f"    \"{nama}\"  dipakai di {len(tempat)} tempat")
        for t in tempat[:6]:
            print(f"      {t}")
        if len(tempat) > 6:
            print(f"      ... dan {len(tempat) - 6} lagi")
    print()
    print("=" * 76)
    print("  HASIL: gambar ikon tersebut di ui/icons.py, atau ganti namanya")
    print("=" * 76)
    return 1


if __name__ == "__main__":
    sys.exit(main())
