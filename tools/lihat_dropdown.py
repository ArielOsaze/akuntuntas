"""Ambil tangkapan layar dropdown bentuk badan usaha untuk diperiksa."""

from __future__ import annotations

import os
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
os.environ["AKUNTANSIID_DATA"] = str(AKAR / "_contoh")
sys.path.insert(0, str(AKAR / "src"))

from PySide6.QtWidgets import QApplication  # noqa: E402

from akuntansi_id import config  # noqa: E402
from akuntansi_id.ui import pilihan_entitas, theme  # noqa: E402


def main() -> int:
    app = QApplication.instance() or QApplication([])
    app.setStyleSheet(theme.stylesheet())

    c = pilihan_entitas.combo_bentuk_badan(config.ENTITY_TYPES)
    c.setMinimumWidth(430)
    c.resize(430, 40)
    c.show()
    for _ in range(8):
        app.processEvents()

    # buka daftar pilihan lalu ambil gambarnya
    c.showPopup()
    for _ in range(10):
        app.processEvents()

    tampilan = c.view()
    # Jangan panggil resize() pada view: itu menimpa lebar yang sudah
    # dihitung combo sehingga teks tampak terpotong. Cukup pakai ukuran
    # yang diberikan Qt, lalu atur tinggi agar semua baris terlihat.
    tinggi = min(400, tampilan.sizeHintForRow(0) * c.count() + 8)
    tampilan.setMinimumHeight(tinggi)
    for _ in range(10):
        app.processEvents()

    keluar = AKAR / "_uji_dropdown.png"
    tampilan.grab().save(str(keluar))
    print(f"tangkapan disimpan: {keluar}")
    print(f"ukuran: {tampilan.width()} x {tampilan.height()}")
    print(f"jumlah pilihan: {c.count()}")
    print(f"tinggi per baris: {pilihan_entitas.TINGGI_BARIS} px")
    c.hidePopup()
    return 0


if __name__ == "__main__":
    sys.exit(main())
