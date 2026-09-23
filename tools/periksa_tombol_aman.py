"""
Buktikan tombol yang membuka aplikasi lain benar-benar dilewati pengujian.

Tombol "Kirim lewat Email" membuka aplikasi email bawaan Windows, yang di
sebagian komputer diarahkan ke OneNote. Mengkliknya saat pengujian membuat
program lain terbuka tanpa diminta, sehingga tombol seperti itu harus
dilewati.

Berkas ini memeriksa daftar penjagaan pada alat pengujian, lalu membuktikan
bahwa nama tombol yang membuka aplikasi lain benar-benar tertangkap oleh
daftar itu.
"""

import re
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent

# Alat pengujian yang mengklik tombol.
ALAT = (
    "tools/uji_klik_tombol.py",
    "tools/periksa_garis_bawah_dialog.py",
)

# Nama tombol yang membuka aplikasi lain dan wajib dilewati.
WAJIB_LEWAT = (
    "Kirim lewat Email",
    "Buka Folder Data",
    "Buka Lokasi Berkas",
    "Ekspor Seluruh Data (Excel)",
)


def baca_penjagaan(berkas: Path) -> tuple:
    """Ambil daftar kata yang dilewati dari sebuah alat pengujian."""
    isi = berkas.read_text(encoding="utf-8")
    cocok = re.search(r"(?:LEWATI|DILARANG)\s*=\s*\((.*?)\)", isi, re.S)
    if not cocok:
        return ()
    isi_daftar = cocok.group(1)
    return tuple(re.findall(r'"([^"]+)"', isi_daftar))


def main() -> int:
    print("=" * 70)
    print("PEMERIKSAAN: tombol yang membuka aplikasi lain dilewati")
    print("=" * 70)
    print()

    gagal = 0

    for relatif in ALAT:
        berkas = AKAR / relatif
        if not berkas.exists():
            print(f"  [LEWAT] {relatif} tidak ada")
            continue

        penjagaan = baca_penjagaan(berkas)
        print(f"  {relatif}")
        print(f"    {len(penjagaan)} kata penjagaan")

        for nama in WAJIB_LEWAT:
            kunci = nama.lower()
            tertangkap = any(k in kunci for k in penjagaan)
            tanda = "LULUS" if tertangkap else "GAGAL"
            if not tertangkap:
                gagal += 1
            print(f"    [{tanda}] {nama!r} dilewati")
        print()

    print("=" * 70)
    if gagal == 0:
        print("HASIL: seluruh tombol pembuka aplikasi lain sudah dilewati")
    else:
        print(f"HASIL: {gagal} tombol belum dilewati")
    print("=" * 70)
    return 1 if gagal else 0


if __name__ == "__main__":
    sys.exit(main())
