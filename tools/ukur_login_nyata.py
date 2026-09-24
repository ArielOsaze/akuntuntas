"""
Ukur halaman login dari aplikasi yang benar-benar tampil di layar.

Cara ini dipakai karena render ke gambar tanpa jendela (offscreen) tidak
memakai font sistem, sehingga teksnya tergambar sebagai kotak kosong dan
ukurannya tidak dapat dipercaya. Dengan menampilkan jendela sungguhan,
font yang dipakai sama dengan yang dilihat pengguna.

Cara pakai:
    python tools/ukur_login_nyata.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "src"))

from PySide6.QtCore import QPoint  # noqa: E402
from PySide6.QtGui import QGuiApplication  # noqa: E402
from PySide6.QtWidgets import (  # noqa: E402
    QApplication, QLabel, QPushButton, QLineEdit, QCheckBox,
)
from akuntansi_id.ui import theme  # noqa: E402
from akuntansi_id.ui.login import LoginPage  # noqa: E402


def tunggu(app, detik=0.6):
    akhir = time.time() + detik
    while time.time() < akhir:
        app.processEvents()
        time.sleep(0.01)


def ukur(app, lebar, tinggi):
    """Tampilkan halaman login dan periksa seluruh teksnya."""
    halaman = LoginPage()
    halaman.resize(lebar, tinggi)
    halaman.show()
    tunggu(app, 0.8)

    masalah = []
    # Periksa setiap widget yang menampilkan teks
    calon = (halaman.findChildren(QLabel) + halaman.findChildren(QPushButton)
             + halaman.findChildren(QCheckBox))

    for wdg in calon:
        if not wdg.isVisible():
            continue
        if hasattr(wdg, "text"):
            teks = wdg.text()
        else:
            continue
        if not teks.strip() or "<" in teks:
            continue
        # Hanya QLabel yang punya pengaturan pembungkusan baris. Tombol dan
        # kotak centang tidak membungkus, jadi selalu diperiksa.
        if hasattr(wdg, "wordWrap") and wdg.wordWrap():
            continue

        # Ukur dari lebar teks yang benar-benar dipakai widget.
        # Label yang teksnya memuat baris baru diukur per baris, karena
        # yang menentukan terpotong atau tidak adalah baris terpanjang.
        for baris in teks.split("\n"):
            if not baris.strip():
                continue
            butuh = wdg.fontMetrics().horizontalAdvance(baris)
            dapat = wdg.width()

            if dapat + 4 < butuh:
                masalah.append(
                    f"terpotong {butuh - dapat}px: {wdg.__class__.__name__} "
                    f"\"{baris[:36]}\"")

    # Periksa batas jendela
    for wdg in list(calon) + list(halaman.findChildren(QLineEdit)):
        if not wdg.isVisible():
            continue
        titik = wdg.mapTo(halaman, QPoint(0, 0))
        kanan = titik.x() + wdg.width()
        bawah = titik.y() + wdg.height()
        if kanan > halaman.width() + 2:
            masalah.append(f"keluar kanan {kanan - halaman.width()}px: "
                           f"{wdg.__class__.__name__}")
        if bawah > halaman.height() + 2:
            masalah.append(f"keluar bawah {bawah - halaman.height()}px: "
                           f"{wdg.__class__.__name__}")

    nyata = (halaman.width(), halaman.height())
    halaman.close()
    halaman.deleteLater()
    tunggu(app, 0.2)

    return nyata, masalah


def main() -> int:
    app = QApplication.instance() or QApplication([])
    app.setStyleSheet(theme.stylesheet())

    layar = QGuiApplication.primaryScreen()
    ukuran_layar = layar.availableGeometry() if layar else None

    print("=" * 78)
    print("  UKUR HALAMAN LOGIN DENGAN FONT SUNGGUHAN")
    print("=" * 78)
    print()
    if ukuran_layar:
        print(f"  layar tersedia: {ukuran_layar.width()}x{ukuran_layar.height()}")
        print()

    # Ukuran yang diuji: dari paling sempit sampai paling lebar
    ukuran = [(920, 620), (980, 700), (1120, 720), (1280, 720), (1366, 768)]

    total = 0
    for lebar, tinggi in ukuran:
        nyata, masalah = ukur(app, lebar, tinggi)
        tanda = "OK" if not masalah else f"{len(masalah)} MASALAH"
        print(f"  {lebar}x{tinggi} -> jendela {nyata[0]}x{nyata[1]}  [{tanda}]")
        for m in masalah[:8]:
            print(f"      {m}")
        if len(masalah) > 8:
            print(f"      ... dan {len(masalah) - 8} lagi")
        total += len(masalah)

    print()
    print("=" * 78)
    if total == 0:
        print("  HASIL: seluruh teks tampil utuh pada semua ukuran")
    else:
        print(f"  HASIL: {total} masalah ditemukan")
    print("=" * 78)

    return 0 if total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
