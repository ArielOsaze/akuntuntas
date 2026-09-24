"""
Ambil gambar halaman login pada beberapa ukuran jendela.

Gambar ini dipakai untuk melihat sendiri bagian mana yang terpotong,
karena pengukuran angka saja tidak menunjukkan bagaimana hasilnya terlihat.

Cara pakai:
    python tools/gambar_login.py
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "src"))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QPixmap  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402
from akuntansi_id.ui import theme  # noqa: E402
from akuntansi_id.ui.login import LoginPage  # noqa: E402

KELUAR = AKAR / "_gambar_login"

UKURAN = [
    (1120, 720),     # ukuran bawaan jendela login
    (980, 700),      # tepat di batas kebutuhan
    (920, 620),      # ukuran minimum yang diizinkan
    (1366, 768),     # layar paling umum
]


def main() -> int:
    app = QApplication.instance() or QApplication([])
    app.setStyleSheet(theme.stylesheet())

    KELUAR.mkdir(exist_ok=True)

    print("=" * 74)
    print("  GAMBAR HALAMAN LOGIN")
    print("=" * 74)
    print()

    for lebar, tinggi in UKURAN:
        halaman = LoginPage()
        halaman.resize(lebar, tinggi)
        halaman.show()
        akhir = time.time() + 0.5
        while time.time() < akhir:
            app.processEvents()
            time.sleep(0.01)

        nyata_l = halaman.width()
        nyata_t = halaman.height()

        gambar = QPixmap(nyata_l, nyata_t)
        halaman.render(gambar)
        nama = KELUAR / f"login-{lebar}x{tinggi}.png"
        gambar.save(str(nama))

        catatan = "" if (nyata_l, nyata_t) == (lebar, tinggi) else \
            f"  (menjadi {nyata_l}x{nyata_t}, dipaksa ukuran minimum isi)"
        print(f"  {lebar}x{tinggi} -> {nama.name}{catatan}")

        halaman.close()
        halaman.deleteLater()

    print()
    print(f"  gambar disimpan di: {KELUAR}")
    print("=" * 74)

    return 0


if __name__ == "__main__":
    sys.exit(main())
