"""Deteksi tanda "&" yang berubah jadi garis bawah pada teks antarmuka.

Cara pakai:
    python tools/periksa_ampersand.py

Qt membaca "&" pada tombol, kotak centang, dan tab sebagai penanda tombol
pintasan: huruf sesudahnya digarisbawahi, dan bila "&" diikuti spasi tanda
itu hilang sama sekali sehingga "Biaya & Pengeluaran" tampil menjadi
"Biaya  Pengeluaran" atau menyisakan garis bawah yang mengganggu. Teks
bertanda "&" harus dikirim ganda ("&&") agar tampil apa adanya.

Pemeriksaan ini membaca widget yang benar-benar dirender lalu melaporkan
teks yang masih memakai satu "&".
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
os.environ["AKUNTANSIID_DATA"] = str(AKAR / "_contoh")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(AKAR / "src"))

from PySide6.QtWidgets import (QApplication, QCheckBox, QGroupBox,  # noqa: E402
                               QPushButton, QRadioButton, QTabBar)

from akuntansi_id import config, services  # noqa: E402
from akuntansi_id.core import security as sec  # noqa: E402
from akuntansi_id.ui import theme  # noqa: E402
from akuntansi_id.ui.login import LoginPage  # noqa: E402
from akuntansi_id.ui.main_window import MainWindow, Sidebar  # noqa: E402

# Lisensi uji dipakai agar seluruh halaman ikut diperiksa, termasuk
# halaman yang hanya tersedia pada paket Enterprise.
from akuntansi_id.core.license import Lisensi as _LisensiUji
_LISENSI_UJI = _LisensiUji(kunci='ATNTUJI', paket='enterprise', fitur={})


HALAMAN = [k for _, daftar in Sidebar.MENU for k, _, _ in daftar]


def ampersand_tunggal(teks: str) -> bool:
    """True bila ada "&" tunggal yang akan ditafsirkan Qt sebagai pintasan."""
    if "&" not in teks:
        return False
    # "&&" adalah cara resmi menampilkan satu "&"
    return "&" in teks.replace("&&", "")


def periksa(akar) -> list:
    temuan = []
    kelas = (QPushButton, QCheckBox, QRadioButton, QGroupBox)

    for widget in akar.findChildren(kelas[0]):
        if widget.isVisible() and ampersand_tunggal(widget.text()):
            temuan.append((type(widget).__name__, widget.text()))

    for tipe in kelas[1:]:
        for widget in akar.findChildren(tipe):
            if widget.isVisible() and ampersand_tunggal(widget.text()):
                temuan.append((type(widget).__name__, widget.text()))

    for tab in akar.findChildren(QTabBar):
        if not tab.isVisible():
            continue
        for i in range(tab.count()):
            teks = tab.tabText(i)
            if ampersand_tunggal(teks):
                temuan.append(("QTabBar", teks))

    return temuan


def main() -> int:
    app = QApplication.instance() or QApplication([])
    app.setStyle("Fusion")
    app.setStyleSheet(theme.stylesheet())

    masalah = []

    layar = LoginPage()
    layar.resize(620, 660)
    layar.show()
    for _ in range(8):
        app.processEvents()
    for jenis, teks in periksa(layar):
        masalah.append(("login", jenis, teks))
        print(f"  [AMPERSAND] login        {jenis:14s} '{teks[:44]}'")
    layar.close()

    perusahaan = services.list_companies()
    if not perusahaan:
        print("Tidak ada perusahaan. Jalankan tools/buat_data_contoh.py dulu.")
        return 1
    cid = perusahaan[0]["id"]

    hasil = sec.login("admin", config.DEFAULT_ADMIN_PASSWORD)
    if not hasil.ok:
        print("Login gagal.")
        return 1

    jendela = MainWindow(hasil, lisensi=_LISENSI_UJI)
    jendela.ctx.company_id = cid
    jendela.ctx.company = services.get_company(cid)
    jendela.ctx.beginner = False
    jendela.resize(1500, 950)
    jendela.show()

    for kode in HALAMAN:
        try:
            jendela._navigasi(kode)
            for _ in range(6):
                app.processEvents()
            halaman = jendela.halaman.get(kode)
            if halaman is None:
                continue
            for jenis, teks in periksa(halaman):
                masalah.append((kode, jenis, teks))
                print(f"  [AMPERSAND] {kode:12s} {jenis:14s} '{teks[:44]}'")
        except Exception as e:
            print(f"  [ERROR] {kode}: {type(e).__name__}: {e}")

    print()
    if masalah:
        print(f"HASIL: {len(masalah)} teks memakai '&' tunggal")
        return 1
    print("HASIL: tidak ada '&' tunggal yang mengubah tampilan teks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
