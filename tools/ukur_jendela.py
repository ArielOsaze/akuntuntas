"""
Cari bagian yang paling banyak memakan waktu saat jendela utama dibuat.

Pembuatan jendela masih memakan sekitar satu detik meskipun halaman sudah
dibuat saat dibuka. Berkas ini mengukur tiap bagian pembuatan jendela supaya
bagian yang mahal dapat diketahui dengan pasti.
"""

import os
import sys
import time
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "src"))
os.environ.setdefault("AKUNTANSIID_DATA", str(AKAR / "_contoh"))

from PySide6.QtWidgets import QApplication      # noqa: E402


def main() -> int:
    app = QApplication([])
    app.setStyle("Fusion")

    from akuntansi_id.ui import theme
    theme.palet_terang(app)
    app.setStyleSheet(theme.stylesheet())

    from akuntansi_id.core import security as sec
    hasil = sec.login("admin", "admin123")

    from akuntansi_id.ui.main_window import MainWindow



    def _lisensi_uji():

        """Lisensi uji paket Enterprise agar seluruh halaman ikut diperiksa."""

        from akuntansi_id.core.license import Lisensi

        return Lisensi(kunci='ATNTUJI', paket='enterprise', fitur={})

    print("=" * 74)
    print("RINCIAN PEMBUATAN JENDELA UTAMA")
    print("=" * 74)
    print()

    # ukur total
    t0 = time.perf_counter()
    jendela = MainWindow(hasil, lisensi=_lisensi_uji())
    total = (time.perf_counter() - t0) * 1000
    print(f"  Total MainWindow        : {total:7.0f} ms")
    print()

    # ukur bagian-bagiannya satu per satu
    print("  Bagian yang diukur terpisah:")

    # 1. dashboard saja
    t0 = time.perf_counter()
    jendela.halaman["dashboard"]
    print(f"    dashboard (sudah ada) : {(time.perf_counter() - t0) * 1000:7.0f} ms")

    # 2. buat halaman lain (yang termahal)
    termahal = []
    for kode in list(jendela.halaman.keys()):
        if kode == "dashboard":
            continue
        dict.pop(jendela.halaman, kode, None)
        t0 = time.perf_counter()
        jendela.halaman[kode]
        ms = (time.perf_counter() - t0) * 1000
        termahal.append((kode, ms))

    termahal.sort(key=lambda x: -x[1])
    for kode, ms in termahal[:6]:
        print(f"    buat [{kode:14s}]    : {ms:7.0f} ms")

    # 3. jumlah widget di sidebar yang sudah ada
    print()
    print(f"  Jumlah widget sidebar   : "
          f"{len(jendela.sidebar.findChildren(object))}")
    print(f"  Jumlah menu sidebar     : {len(jendela.sidebar.tombol)}")

    # 4. ukur dashboard baru
    from akuntansi_id.ui.pages.dashboard import DashboardPage
    t0 = time.perf_counter()
    DashboardPage(jendela.ctx)
    ms_db = (time.perf_counter() - t0) * 1000
    print(f"  Buat dashboard baru     : {ms_db:7.0f} ms")

    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
