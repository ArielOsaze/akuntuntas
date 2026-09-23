"""
Cari sisa penyebab lambatnya perpindahan halaman.

Waktu sudah turun setelah pengukuran tinggi label di-cache, tetapi masih ada
sisa yang seragam pada semua halaman. Berkas ini mengukur setiap langkah
yang dijalankan saat halaman ditampilkan, termasuk yang berjalan otomatis
lewat peristiwa Qt seperti showEvent dan timer.
"""

import os
import sys
import time
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "src"))
os.environ.setdefault("AKUNTANSIID_DATA", str(AKAR / "_contoh"))

from PySide6.QtWidgets import QApplication, QScrollArea   # noqa: E402


def rata(fn, ulangan: int = 6) -> float:
    total = 0.0
    for _ in range(ulangan):
        t0 = time.perf_counter()
        fn()
        total += (time.perf_counter() - t0) * 1000
    return total / ulangan


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

    print("=" * 74)
    print("LANGKAH YANG BERJALAN SAAT HALAMAN DITAMPILKAN")
    print("=" * 74)
    print()

    for kode in ("audit", "payroll", "produk", "dashboard"):
        halaman = jendela.halaman[kode]
        area = halaman.findChildren(QScrollArea)
        print(f"  [{kode}]  widget={len(halaman.findChildren(object))} "
              f"area_gulir={len(area)}")

        # Waktu showEvent area gulir (tempat sesuaikan_tinggi dipanggil)
        if area:
            a = area[0]
            ms = rata(a.sesuaikan_tinggi, 6)
            print(f"    sesuaikan_tinggi   : {ms:7.1f} ms")

        # Waktu perpindahan penuh
        def pindah():
            jendela.stack.setCurrentWidget(jendela.halaman["dashboard"])
            app.processEvents()
            jendela._navigasi(kode)
            for _ in range(4):
                app.processEvents()
        print(f"    TOTAL pindah       : {rata(pindah, 5):7.1f} ms")

        # Waktu perpindahan tanpa processEvents
        def pindah_kering():
            jendela.stack.setCurrentWidget(jendela.halaman["dashboard"])
            jendela._navigasi(kode)
        print(f"    pindah tanpa proses: {rata(pindah_kering, 5):7.1f} ms")
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
