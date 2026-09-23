"""
Ukur kecepatan respons saat mengeklik di dalam halaman.

Delay tidak hanya terasa saat berpindah menu, tetapi juga saat mengeklik
tombol, membuka daftar pilihan, atau mengetik di kotak isian. Berkas ini
mengukur ketiganya supaya bagian yang lambat dapat diketahui.
"""

import os
import sys
import time
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "src"))
os.environ.setdefault("AKUNTANSIID_DATA", str(AKAR / "_contoh"))

from PySide6.QtCore import Qt, QEvent            # noqa: E402
from PySide6.QtGui import QMouseEvent            # noqa: E402
from PySide6.QtWidgets import (                  # noqa: E402
    QApplication, QComboBox, QLineEdit, QPushButton)

HALAMAN = ("jurnal", "penjualan", "produk", "mitra", "pajak")


def main() -> int:
    app = QApplication([])
    app.setStyle("Fusion")

    from akuntansi_id.ui import theme
    theme.palet_terang(app)
    app.setStyleSheet(theme.stylesheet())

    from akuntansi_id.core import security as sec
    from akuntansi_id.ui.main_window import MainWindow

    jendela = MainWindow(sec.login("admin", "admin123"))
    jendela.resize(1400, 900)
    jendela.show()
    for _ in range(20):
        app.processEvents()

    for kode in jendela.halaman:
        jendela._navigasi(kode)
        for _ in range(3):
            app.processEvents()

    print("=" * 76)
    print("KECEPATAN RESPONS KLIK DI DALAM HALAMAN")
    print("=" * 76)
    print()

    for kode in HALAMAN:
        halaman = jendela.halaman[kode]
        jendela._navigasi(kode)
        for _ in range(4):
            app.processEvents()

        print(f"  [{kode}]")

        # 1. membuka daftar pilihan
        combo = [c for c in halaman.findChildren(QComboBox) if c.count() > 1]
        if combo:
            waktu = []
            for _ in range(5):
                t0 = time.perf_counter()
                combo[0].showPopup()
                app.processEvents()
                waktu.append((time.perf_counter() - t0) * 1000)
                combo[0].hidePopup()
                app.processEvents()
            print(f"    buka daftar pilihan : {sum(waktu) / len(waktu):6.1f} ms")

        # 2. mengetik di kotak isian
        kotak = [k for k in halaman.findChildren(QLineEdit) if k.isEnabled()]
        if kotak:
            waktu = []
            for _ in range(5):
                t0 = time.perf_counter()
                kotak[0].setText("pengujian kecepatan")
                app.processEvents()
                waktu.append((time.perf_counter() - t0) * 1000)
                kotak[0].clear()
                app.processEvents()
            print(f"    ketik di kotak isian: {sum(waktu) / len(waktu):6.1f} ms")

        # 3. mengarahkan kursor ke tombol (hover)
        tombol = [t for t in halaman.findChildren(QPushButton)
                  if t.isVisible() and t.isEnabled()]
        if tombol:
            waktu = []
            for _ in range(5):
                t0 = time.perf_counter()
                titik = tombol[0].rect().center()
                peristiwa = QMouseEvent(
                    QEvent.MouseMove, titik, Qt.NoButton,
                    Qt.NoButton, Qt.NoModifier)
                app.sendEvent(tombol[0], peristiwa)
                app.processEvents()
                waktu.append((time.perf_counter() - t0) * 1000)
            print(f"    sorot tombol        : {sum(waktu) / len(waktu):6.1f} ms")

        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
