"""
Cari fungsi yang paling banyak memakan waktu saat berpindah halaman.

Waktu yang tersisa setelah pemuatan data di-cache ternyata seragam pada
semua halaman, jadi penyebabnya bukan pemuatan data. Berkas ini merekam
seluruh pemanggilan fungsi selama perpindahan halaman, lalu menampilkan
yang paling banyak memakan waktu.
"""

import cProfile
import io
import os
import pstats
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
    from akuntansi_id.ui.main_window import MainWindow


    def _lisensi_uji():
        """Lisensi uji paket Enterprise agar seluruh halaman ikut diperiksa."""
        from akuntansi_id.core.license import Lisensi
        return Lisensi(kunci='ATNTUJI', paket='enterprise', fitur={})

    hasil = sec.login("admin", "admin123")
    jendela = MainWindow(hasil, lisensi=_lisensi_uji())
    jendela.resize(1400, 900)
    jendela.show()
    for _ in range(20):
        app.processEvents()

    # Kunjungan pertama supaya halaman sudah dimuat.
    for kode in jendela.halaman:
        jendela._navigasi(kode)
        for _ in range(3):
            app.processEvents()

    print("=" * 76)
    print("PROFIL PERPINDAHAN HALAMAN (kunjungan berulang)")
    print("=" * 76)
    print()

    # Rekam perpindahan berulang ke beberapa halaman.
    def pindah_berulang():
        for kode in ("analisis", "pajak", "penjualan", "dashboard", "laporan"):
            jendela._navigasi(kode)
            for _ in range(3):
                app.processEvents()

    # Ukur dulu berapa lama tanpa profiling.
    t0 = time.perf_counter()
    pindah_berulang()
    polos = (time.perf_counter() - t0) * 1000
    print(f"  Waktu tanpa profiling : {polos:,.0f} ms "
          f"untuk 5 perpindahan")
    print()

    # Rekam dengan profiling.
    perekam = cProfile.Profile()
    perekam.enable()
    pindah_berulang()
    perekam.disable()

    aliran = io.StringIO()
    stat = pstats.Stats(perekam, stream=aliran)
    stat.sort_stats("cumulative")
    stat.print_stats(28)

    keluaran = aliran.getvalue()
    print("  FUNGSI PALING BANYAK MEMAKAN WAKTU (cumulative):")
    print()
    for baris in keluaran.splitlines():
        # hanya baris data
        if "akuntansi_id" in baris or "PySide6" in baris:
            print(f"    {baris.strip()[:110]}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
