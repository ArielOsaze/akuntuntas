"""
Ukur lebar sebenarnya setiap elemen formulir login.

Membaca geometri widget yang benar-benar dirender, bukan menebak dari
gambar. Dipakai untuk memastikan formulir memakai lebar yang direncanakan
dan seluruh elemennya rata pada satu garis.

Cara pakai:
    python tools/ukur_lebar_login.py
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "src"))

from PySide6.QtWidgets import QApplication, QFrame, QLineEdit, QPushButton  # noqa: E402
from akuntansi_id.ui import theme  # noqa: E402
from akuntansi_id.ui.login import LoginPage  # noqa: E402


def tunggu(app, detik=0.4):
    akhir = time.time() + detik
    while time.time() < akhir:
        app.processEvents()
        time.sleep(0.01)


def main() -> int:
    app = QApplication.instance() or QApplication([])
    app.setStyle("Fusion")
    theme.palet_terang(app)
    app.setStyleSheet(theme.stylesheet())

    print("=" * 78)
    print("  LEBAR SEBENARNYA ELEMEN FORMULIR LOGIN")
    print("=" * 78)

    for lebar, tinggi in ((1024, 700), (1366, 768), (1920, 1080)):
        halaman = LoginPage()
        halaman.resize(lebar, tinggi)
        halaman.show()
        tunggu(app)

        # Panel merek (kiri) dan panel formulir (kanan)
        panel = halaman.findChildren(QFrame)
        merek = next((p for p in panel if p.width() >= 300 and p.x() == 0), None)
        form = halaman.inp_user.parent()

        print()
        print(f"  --- jendela {lebar}x{tinggi} ---")
        if merek:
            print(f"    panel merek   : lebar {merek.width()}")
        print(f"    form          : lebar {form.width()}  "
              f"(batas maksimum {form.maximumWidth()})")
        print(f"    kolom pengguna: lebar {halaman.inp_user.width()}")
        print(f"    tombol masuk  : lebar {halaman.btn_login.width()}")

        if hasattr(halaman, "petunjuk"):
            print(f"    kotak petunjuk: lebar {halaman.petunjuk.width()}")

        # Bandingkan dengan ruang yang tersedia
        ruang = lebar - (merek.width() if merek else 0)
        print(f"    ruang tersedia: {ruang}")
        if form.width() < form.maximumWidth() - 2:
            print(f"    >>> FORM MENYUSUT: {form.width()}px dari "
                  f"{form.maximumWidth()}px yang direncanakan")

        # Kerataan tepi
        kiri = {}
        kanan = {}
        for nama, w in (("pengguna", halaman.inp_user),
                        ("password", halaman.inp_pass.parent()),
                        ("masuk", halaman.btn_login),
                        ("petunjuk", getattr(halaman, "petunjuk", None))):
            if w is None:
                continue
            t = w.mapTo(halaman, w.rect().topLeft())
            kiri[nama] = t.x()
            kanan[nama] = t.x() + w.width()

        print(f"    tepi kiri : {kiri}")
        print(f"    tepi kanan: {kanan}")
        selisih_kiri = max(kiri.values()) - min(kiri.values())
        selisih_kanan = max(kanan.values()) - min(kanan.values())
        if selisih_kiri > 1 or selisih_kanan > 1:
            print(f"    >>> TIDAK RATA: kiri beda {selisih_kiri}px, "
                  f"kanan beda {selisih_kanan}px")

        halaman.close()
        halaman.deleteLater()
        tunggu(app, 0.15)

    return 0


if __name__ == "__main__":
    sys.exit(main())
