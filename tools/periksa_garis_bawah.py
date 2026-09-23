"""Pastikan tidak ada teks yang tampil memakai garis bawah sebagai spasi.

Cara pakai:
    python tools/periksa_garis_bawah.py

Nilai basis data seperti `belum_bayar` atau `journal.create` aman disimpan
apa adanya, tetapi terlihat seperti kode bila ditampilkan. Pemeriksaan ini
membaca SEMUA teks yang benar-benar dirender — label, tombol, tab, sel
tabel, judul kolom, isi kotak pilihan, judul dialog, dan menu — lalu
melaporkan yang masih mengandung garis bawah.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
os.environ["AKUNTANSIID_DATA"] = str(AKAR / "_contoh")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(AKAR / "src"))

from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox,  # noqa: E402
                               QGroupBox, QLabel, QPushButton, QRadioButton,
                               QTabBar, QTableWidget, QWidget)

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

# pola nilai teknis: huruf kecil semua dengan garis bawah atau titik pemisah
POLA_TEKNIS = re.compile(r"^[a-z][a-z0-9]*([._][a-z0-9]+)+$")

# istilah asing/singkatan yang sah tampil apa adanya
DIKECUALIKAN = {
    "e-mail", "e-wallet", "no.", "s.d.", "dll.", "a.n.", "cv.", "pt.",
    "fifo", "lifo", "ppn", "pph", "npwp", "pkp", "spt", "csv", "pdf",
    "excel", "sak", "emkm", "e-faktur", "e-bupot", "e-spt", "e-filing",
    "e-billing", "non-pkp", "non-ppn", "k-i", "k-ii", "k-iii", "k-iv",
}


def ada_garis_bawah(teks: str) -> bool:
    """True bila teks mengandung garis bawah yang terlihat pengguna.

    Nama berkas dan folder tidak dilaporkan: garis bawah di sana memang
    bagian dari path yang sah dan bukan istilah teknis basis data.
    """
    teks = teks.strip()
    if "_" not in teks:
        return False
    if teks.lower() in DIKECUALIKAN:
        return False
    # path Windows ("C:\...") atau path mirip folder: abaikan
    if "\\" in teks or teks.startswith("/") or ":/" in teks:
        return False
    if "…" in teks or teks.endswith((".csv", ".xlsx", ".pdf", ".db")):
        return False
    return True


def periksa(akar) -> list:
    temuan = []

    def catat(tempat: str, teks: str):
        if ada_garis_bawah(teks):
            temuan.append((tempat, teks.strip()))

    for lbl in akar.findChildren(QLabel):
        if lbl.isVisible():
            catat("label", lbl.text())

    for tipe, nama in ((QPushButton, "tombol"), (QCheckBox, "centang"),
                       (QRadioButton, "pilihan"), (QGroupBox, "grup")):
        for w in akar.findChildren(tipe):
            if w.isVisible():
                catat(nama, w.text())

    for combo in akar.findChildren(QComboBox):
        if not combo.isVisible():
            continue
        for i in range(combo.count()):
            catat("kotak-pilihan", combo.itemText(i))

    for tab in akar.findChildren(QTabBar):
        if not tab.isVisible():
            continue
        for i in range(tab.count()):
            catat("tab", tab.tabText(i))

    for tabel in akar.findChildren(QTableWidget):
        if not tabel.isVisible():
            continue
        for kolom in range(tabel.columnCount()):
            judul = tabel.horizontalHeaderItem(kolom)
            if judul is not None:
                catat("judul-kolom", judul.text())
        for baris in range(tabel.rowCount()):
            for kolom in range(tabel.columnCount()):
                item = tabel.item(baris, kolom)
                if item is not None:
                    catat(f"sel[{baris},{kolom}]", item.text())

    for w in akar.findChildren(QWidget):
        judul = w.windowTitle()
        if judul and w.isWindow():
            catat("judul-jendela", judul)

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
    for tempat, teks in periksa(layar):
        masalah.append(("login", tempat, teks))
        print(f"  [GARIS BAWAH] login        {tempat:14s} '{teks[:44]}'")
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
            for tempat, teks in periksa(halaman):
                masalah.append((kode, tempat, teks))
                print(f"  [GARIS BAWAH] {kode:12s} {tempat:14s} '{teks[:44]}'")
        except Exception as e:
            print(f"  [ERROR] {kode}: {type(e).__name__}: {e}")

    print()
    if masalah:
        print(f"HASIL: {len(masalah)} teks memakai garis bawah sebagai spasi")
        return 1
    print("HASIL: tidak ada teks yang memakai garis bawah sebagai spasi")
    return 0


if __name__ == "__main__":
    sys.exit(main())
