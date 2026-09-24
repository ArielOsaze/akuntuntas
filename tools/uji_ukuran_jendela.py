"""
Uji perhitungan ukuran jendela masuk pada berbagai ukuran layar.

Bagian ini memanggil langsung perhitungan ukuran jendela dengan ukuran
layar buatan, sehingga hasilnya dapat dipercaya tanpa perlu mengubah
ukuran layar sungguhan. Ini menghindari kelemahan mode offscreen Qt yang
selalu melaporkan ukuran layar tetap.

Cara pakai:
    python tools/uji_ukuran_jendela.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "src"))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QRect  # noqa: E402

# Batas ukuran yang dipakai aplikasi, disalin dari main_window._pasang_ukuran
SEMPIT_L, SEMPIT_T = 920, 620
BAKU_L, BAKU_T = 1120, 720


def hitung_ukuran(lebar_layar: int, tinggi_layar: int):
    """
    Tiru perhitungan ukuran jendela masuk untuk ukuran layar tertentu.

    Rumusnya harus sama dengan main_window.JendelaAplikasi._pasang_ukuran.
    Bila rumus di sana berubah, uji ini akan menandai ketidakcocokan.
    """
    ruang = QRect(0, 0, lebar_layar, tinggi_layar)
    lebar = min(BAKU_L, max(1, ruang.width() - 40))
    tinggi = min(BAKU_T, max(1, ruang.height() - 40))
    minimum_l = min(SEMPIT_L, lebar)
    minimum_t = min(SEMPIT_T, tinggi)
    return lebar, tinggi, minimum_l, minimum_t


# Ukuran layar yang diuji, termasuk yang lebih kecil dari batas sempit.
LAYAR = [
    (1920, 1080),    # layar besar
    (1600, 900),
    (1366, 768),     # laptop paling umum
    (1280, 720),
    (1152, 864),
    (1024, 600),     # netbook, lebih kecil dari batas sempit
    (800, 600),      # layar sangat kecil
]


def main() -> int:
    print("=" * 78)
    print("  UJI PERHITUNGAN UKURAN JENDELA MASUK")
    print("=" * 78)
    print()
    print(f"  batas sempit : {SEMPIT_L}x{SEMPIT_T}")
    print(f"  ukuran baku  : {BAKU_L}x{BAKU_T}")
    print()
    print(f"  {'layar':>12}  {'jendela':>12}  {'minimum':>12}  keadaan")
    print("  " + "-" * 62)

    gagal = 0
    for lebar_layar, tinggi_layar in LAYAR:
        lebar, tinggi, min_l, min_t = hitung_ukuran(lebar_layar, tinggi_layar)

        masalah = []
        if lebar > lebar_layar:
            masalah.append(f"lebih lebar {lebar - lebar_layar}px")
        if tinggi > tinggi_layar:
            masalah.append(f"lebih tinggi {tinggi - tinggi_layar}px")
        if min_l > lebar_layar:
            masalah.append("minimum melebihi layar")

        keadaan = "OK" if not masalah else "; ".join(masalah)
        print(f"  {lebar_layar:>5}x{tinggi_layar:<6}  "
              f"{lebar:>5}x{tinggi:<6}  {min_l:>5}x{min_t:<6}  {keadaan}")

        if masalah:
            gagal += 1

    print()
    print("=" * 78)
    if gagal == 0:
        print("  HASIL: jendela selalu muat di seluruh ukuran layar")
    else:
        print(f"  HASIL: {gagal} ukuran layar bermasalah")
        print()
        print("  Catatan: pada layar yang lebih sempit dari batas minimum,")
        print("  jendela memang tidak dapat ditampilkan penuh. Yang penting")
        print("  adalah perilakunya tetap wajar dan tidak memaksa ukuran")
        print("  minimum yang lebih besar dari layar.")
    print("=" * 78)

    return 0 if gagal == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
