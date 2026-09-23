"""
Uji apakah ukuran stylesheet mempengaruhi waktu perpindahan halaman.

Qt mencocokkan setiap widget terhadap seluruh aturan stylesheet saat widget
ditampilkan. Bila aturannya banyak, pekerjaan itu berulang untuk setiap
widget di halaman yang dibuka. Berkas ini membandingkan waktu perpindahan
dengan stylesheet penuh dan dengan stylesheet yang lebih ringkas.
"""

import os
import sys
import time
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "src"))
os.environ.setdefault("AKUNTANSIID_DATA", str(AKAR / "_contoh"))

from PySide6.QtWidgets import QApplication      # noqa: E402


def ukur_pindah(app, jendela, kode: str, ulangan: int = 5) -> float:
    """Rata-rata waktu mengganti halaman."""
    halaman = jendela.halaman[kode]
    total = 0.0
    for _ in range(ulangan):
        t0 = time.perf_counter()
        jendela.stack.setCurrentWidget(halaman)
        total += (time.perf_counter() - t0) * 1000
    return total / ulangan


def main() -> int:
    app = QApplication([])
    app.setStyle("Fusion")

    from akuntansi_id.ui import theme
    theme.palet_terang(app)

    from akuntansi_id.core import security as sec
    from akuntansi_id.ui.main_window import MainWindow


    def _lisensi_uji():
        """Lisensi uji paket Enterprise agar seluruh halaman ikut diperiksa."""
        from akuntansi_id.core.license import Lisensi
        return Lisensi(kunci='ATNTUJI', paket='enterprise', fitur={})

    hasil = sec.login("admin", "admin123")

    # ---------------------------------------------- dengan stylesheet penuh
    penuh = theme.stylesheet()
    app.setStyleSheet(penuh)
    jendela = MainWindow(hasil, lisensi=_lisensi_uji())
    jendela.resize(1400, 900)
    jendela.show()
    for _ in range(20):
        app.processEvents()

    print("=" * 74)
    print("PENGARUH UKURAN STYLESHEET TERHADAP WAKTU PINDAH HALAMAN")
    print("=" * 74)
    print()
    print(f"  Stylesheet penuh: {len(penuh):,} karakter, "
          f"{penuh.count('{')} aturan")
    print()

    for kode in ("analisis", "pajak", "dashboard"):
        ms = ukur_pindah(app, jendela, kode)
        print(f"    {kode:12s}: {ms:6.1f} ms")

    # ---------------------------------------------- tanpa stylesheet
    print()
    print("  Tanpa stylesheet sama sekali:")
    app.setStyleSheet("")
    for _ in range(20):
        app.processEvents()

    for kode in ("analisis", "pajak", "dashboard"):
        ms = ukur_pindah(app, jendela, kode)
        print(f"    {kode:12s}: {ms:6.1f} ms")

    # ---------------------------------------------- stylesheet ringkas
    print()
    print("  Stylesheet ringkas (hanya dasar):")
    ringkas = """
    QWidget { font-family: "Segoe UI"; font-size: 13px; }
    QLabel { color: #1A2733; }
    """
    app.setStyleSheet(ringkas)
    for _ in range(20):
        app.processEvents()

    for kode in ("analisis", "pajak", "dashboard"):
        ms = ukur_pindah(app, jendela, kode)
        print(f"    {kode:12s}: {ms:6.1f} ms")

    print()
    print("  (bila 'tanpa stylesheet' jauh lebih cepat, penyebabnya")
    print("   adalah jumlah aturan stylesheet yang harus dicocokkan Qt)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
