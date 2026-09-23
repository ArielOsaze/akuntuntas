"""
Periksa perilaku tinggi PageHeader setelah tinggi-dari-lebar dimatikan.

Judul dan subjudul header tidak lagi memakai tinggi-dari-lebar. Berkas ini
memeriksa nilai yang dikembalikan tiap bagian header supaya cara perbaikan
yang tepat dapat ditentukan.
"""

import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "src"))

from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout   # noqa: E402


def main() -> int:
    app = QApplication([])
    app.setStyle("Fusion")

    from akuntansi_id.ui import theme
    theme.palet_terang(app)
    app.setStyleSheet(theme.stylesheet())

    from akuntansi_id.ui import widgets as w

    luar = QWidget()
    lay = QVBoxLayout(luar)
    header = w.PageHeader(
        "Produk & Persediaan",
        "Kelola produk, gudang, stok, dan perhitungan HPP dengan metode "
        "yang Anda pilih.")
    lay.addWidget(header)
    luar.resize(1000, 600)
    luar.show()
    for _ in range(10):
        app.processEvents()

    print("=" * 74)
    print("PERILAKU TINGGI PAGEHEADER")
    print("=" * 74)
    print()
    print(f"  tinggi PageHeader          : {header.height()}")
    print(f"  minimumHeight PageHeader   : {header.minimumHeight()}")
    print(f"  sizeHint PageHeader        : "
          f"{header.sizeHint().width()}x{header.sizeHint().height()}")
    print(f"  hasHeightForWidth (virtual): {header.hasHeightForWidth()}")
    print(f"  sizePolicy HFW             : "
          f"{header.sizePolicy().hasHeightForWidth()}")
    print(f"  heightForWidth(1000)       : {header.heightForWidth(1000)}")
    print()
    print(f"  judul  : tinggi={header.lbl_judul.height()} "
          f"hfw={header.lbl_judul.sizePolicy().hasHeightForWidth()} "
          f"heightForWidth={header.lbl_judul.heightForWidth(900)} "
          f"sizeHint={header.lbl_judul.sizeHint().height()}")
    print(f"  subjudul: tinggi={header.lbl_sub.height()} "
          f"hfw={header.lbl_sub.sizePolicy().hasHeightForWidth()} "
          f"heightForWidth={header.lbl_sub.heightForWidth(900)} "
          f"sizeHint={header.lbl_sub.sizeHint().height()}")
    print()

    # bandingkan: bila tinggi-dari-lebar dinyalakan lagi
    for lbl, nama in ((header.lbl_judul, "judul"),
                      (header.lbl_sub, "subjudul")):
        pol = lbl.sizePolicy()
        pol.setHeightForWidth(True)
        lbl.setSizePolicy(pol)
    for _ in range(10):
        app.processEvents()
    print("  Setelah tinggi-dari-lebar dinyalakan lagi:")
    print(f"    tinggi PageHeader        : {header.height()}")
    print(f"    heightForWidth(1000)     : {header.heightForWidth(1000)}")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
