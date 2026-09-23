"""
Uji dampak aturan "*" dan "QWidget" polos pada waktu perpindahan halaman.

Qt menerapkan aturan stylesheet ke setiap widget yang cocok, termasuk widget
internal seperti viewport, scrollbar, dan delegate. Aturan yang cocok dengan
semua widget karena itu jauh lebih mahal daripada aturan yang menyebut jenis
atau nama tertentu.
"""

import os
import re
import sys
import time
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "src"))
os.environ.setdefault("AKUNTANSIID_DATA", str(AKAR / "_contoh"))

from PySide6.QtWidgets import QApplication      # noqa: E402


def ukur(app, jendela, kode: str, ulangan: int = 7) -> float:
    waktu = []
    for _ in range(ulangan):
        jendela._navigasi("dashboard")
        for _ in range(3):
            app.processEvents()
        t0 = time.perf_counter()
        jendela._navigasi(kode)
        for _ in range(4):
            app.processEvents()
        waktu.append((time.perf_counter() - t0) * 1000)
    waktu.sort()
    return waktu[len(waktu) // 2]


def main() -> int:
    app = QApplication([])
    app.setStyle("Fusion")

    from akuntansi_id.ui import theme
    theme.palet_terang(app)

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

    asli = theme.stylesheet()
    halaman_uji = ("audit", "payroll", "produk", "laporan")

    def uji(nama: str, gaya: str):
        app.setStyleSheet(gaya)
        for _ in range(12):
            app.processEvents()
        hasil = {k: ukur(app, jendela, k) for k in halaman_uji}
        rata = sum(hasil.values()) / len(hasil)
        print(f"  {nama:36s} " +
              " ".join(f"{hasil[k]:6.0f}" for k in halaman_uji) +
              f"   rata {rata:6.1f} ms")

    print("=" * 78)
    print("DAMPAK ATURAN STYLESHEET YANG COCOK DENGAN SEMUA WIDGET")
    print("=" * 78)
    print()
    print(f"  {'keadaan':36s} " +
          " ".join(f"{k[:6]:>6s}" for k in halaman_uji))
    print(f"  {'-' * 36} " + " ".join("-" * 6 for _ in halaman_uji))

    uji("apa adanya (128 aturan)", asli)

    # buang aturan "*" polos
    tanpa_bintang = re.sub(r"^\*\s*\{[^}]*\}\s*$", "", asli, flags=re.M)
    uji(f"tanpa aturan '*' ({len(tanpa_bintang)} chr)",
        tanpa_bintang)

    # buang aturan "QWidget" polos
    tanpa_qwidget = re.sub(r"^QWidget\s*\{[^}]*\}\s*$", "", asli, flags=re.M)
    uji(f"tanpa aturan 'QWidget' ({len(tanpa_qwidget)} chr)",
        tanpa_qwidget)

    # buang keduanya
    tanpa_dua = re.sub(r"^\*\s*\{[^}]*\}\s*$", "", asli, flags=re.M)
    tanpa_dua = re.sub(r"^QWidget\s*\{[^}]*\}\s*$", "", tanpa_dua, flags=re.M)
    uji(f"tanpa keduanya ({len(tanpa_dua)} chr)", tanpa_dua)

    print()
    print("  Catatan: aturan yang lebih hemat harus tetap memberi tampilan")
    print("  yang sama. Perbandingan warna dilakukan setelah ini.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
