"""
Ukur waktu pembukaan aplikasi dan pembuatan seluruh halaman.

Kesan lambat saat memakai aplikasi tidak hanya datang dari perpindahan menu,
tetapi juga dari saat aplikasi dibuka dan saat halaman pertama kali dibuka.
Berkas ini mengukur keduanya supaya bagian yang paling terasa dapat
diperbaiki lebih dulu.
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
    print("=" * 74)
    print("WAKTU PEMBUKAAN APLIKASI")
    print("=" * 74)
    print()

    t_mulai = time.perf_counter()

    app = QApplication([])
    app.setStyle("Fusion")
    t_qt = (time.perf_counter() - t_mulai) * 1000

    from akuntansi_id.ui import theme
    theme.palet_terang(app)
    gaya = theme.stylesheet()
    app.setStyleSheet(gaya)
    t_gaya = (time.perf_counter() - t_mulai) * 1000

    from akuntansi_id.core import security as sec
    hasil = sec.login("admin", "admin123")
    t_login = (time.perf_counter() - t_mulai) * 1000

    from akuntansi_id.ui.main_window import MainWindow


    def _lisensi_uji():

        """Lisensi uji paket Enterprise agar seluruh halaman ikut diperiksa."""

        from akuntansi_id.core.license import Lisensi

        return Lisensi(kunci='ATNTUJI', paket='enterprise', fitur={})

    jendela = MainWindow(hasil, lisensi=_lisensi_uji())
    t_jendela = (time.perf_counter() - t_mulai) * 1000

    jendela.resize(1400, 900)
    jendela.show()
    for _ in range(10):
        app.processEvents()
    t_tampil = (time.perf_counter() - t_mulai) * 1000

    print(f"  QApplication dibuat     : {t_qt:7.0f} ms")
    print(f"  tema + stylesheet       : {t_gaya:7.0f} ms  "
          f"(+{t_gaya - t_qt:.0f})")
    print(f"  login                   : {t_login:7.0f} ms  "
          f"(+{t_login - t_gaya:.0f})")
    print(f"  jendela + 29 halaman    : {t_jendela:7.0f} ms  "
          f"(+{t_jendela - t_login:.0f})")
    print(f"  tampil & tergambar      : {t_tampil:7.0f} ms  "
          f"(+{t_tampil - t_jendela:.0f})")
    print()
    print(f"  TOTAL sampai terlihat   : {t_tampil:7.0f} ms")
    print()

    # berapa lama tiap halaman dibuat?
    print("  Waktu pembuatan tiap halaman (saat pertama dibuka):")
    print()
    waktu = []
    for kode in list(jendela.halaman.keys()):
        jendela.halaman.pop(kode, None)
        t0 = time.perf_counter()
        jendela.halaman[kode]
        waktu.append((kode, (time.perf_counter() - t0) * 1000))

    waktu.sort(key=lambda x: -x[1])
    for nama, ms in waktu[:10]:
        print(f"    {nama:16s} {ms:7.0f} ms")

    print()
    total = sum(ms for _, ms in waktu)
    print(f"  Total 14 halaman        : {total:7.0f} ms")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
