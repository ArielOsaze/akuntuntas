"""Deteksi nilai teknis basis data yang tampil mentah ke pengguna.

Cara pakai:
    python tools/periksa_istilah.py

Nilai seperti `login.success`, `belum_bayar`, atau `non_deductible` aman
disimpan di basis data, tetapi terlihat seperti kode bila ditampilkan apa
adanya. Pemeriksaan ini membaca tabel dan label yang benar-benar dirender,
lalu melaporkan teks yang masih berbentuk teknis.
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

from PySide6.QtWidgets import (QApplication, QLabel, QPushButton,  # noqa: E402
                               QTabBar, QTableWidget)

from akuntansi_id import config, services  # noqa: E402
from akuntansi_id.core import security as sec  # noqa: E402
from akuntansi_id.ui import theme  # noqa: E402
from akuntansi_id.ui.main_window import MainWindow, Sidebar  # noqa: E402

# Lisensi uji dipakai agar seluruh halaman ikut diperiksa, termasuk
# halaman yang hanya tersedia pada paket Enterprise.
from akuntansi_id.core.license import Lisensi as _LisensiUji
_LISENSI_UJI = _LisensiUji(kunci='ATNTUJI', paket='enterprise', fitur={})


HALAMAN = [k for _, daftar in Sidebar.MENU for k, _, _ in daftar]

# pola nilai teknis: huruf kecil semua dengan garis bawah, atau berformat
# "kata.kata" seperti pada log audit
POLA = re.compile(r"^[a-z][a-z0-9]*([._][a-z0-9]+)+$")

# istilah asing yang sah tampil apa adanya
DIKECUALIKAN = {
    "e-mail", "e-wallet", "no.", "s.d.", "dll.", "a.n.", "cv.", "pt.",
    "fifo", "lifo", "ppn", "pph", "npwp", "pkp", "spt", "csv", "pdf",
    "excel", "id", "ai", "da", "sak", "emkm", "ep", "hpp", "hpp.",
}


def teks_bermasalah(teks: str) -> bool:
    teks = teks.strip()
    if not teks or len(teks) < 4:
        return False
    if teks.lower() in DIKECUALIKAN:
        return False
    if " " in teks:
        # kalimat biasa; hanya periksa bila seluruhnya huruf kecil bergaris bawah
        return bool(re.fullmatch(r"[a-z0-9._ ]+", teks)) and "_" in teks
    return bool(POLA.match(teks))


def periksa(akar) -> list:
    temuan = []

    for lbl in akar.findChildren(QLabel):
        if not lbl.isVisible():
            continue
        teks = lbl.text().strip()
        if teks_bermasalah(teks):
            temuan.append(("label", teks))

    for b in akar.findChildren(QPushButton):
        if not b.isVisible():
            continue
        teks = b.text().strip()
        if teks_bermasalah(teks):
            temuan.append(("tombol", teks))

    for tab in akar.findChildren(QTabBar):
        if not tab.isVisible():
            continue
        for i in range(tab.count()):
            teks = tab.tabText(i).strip()
            if teks_bermasalah(teks):
                temuan.append(("tab", teks))

    for tabel in akar.findChildren(QTableWidget):
        if not tabel.isVisible():
            continue
        for baris in range(tabel.rowCount()):
            for kolom in range(tabel.columnCount()):
                item = tabel.item(baris, kolom)
                if item is None:
                    continue
                teks = item.text().strip()
                if teks_bermasalah(teks):
                    temuan.append((f"tabel[{baris},{kolom}]", teks))

    return temuan


def main() -> int:
    app = QApplication.instance() or QApplication([])
    app.setStyle("Fusion")
    app.setStyleSheet(theme.stylesheet())

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

    masalah = []
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
                print(f"  [TEKNIS] {kode:12s} {tempat:18s} '{teks[:40]}'")
        except Exception as e:
            print(f"  [ERROR] {kode}: {type(e).__name__}: {e}")

    print()
    if masalah:
        print(f"HASIL: {len(masalah)} teks masih berbentuk teknis")
        return 1
    print("HASIL: tidak ada nilai teknis yang tampil mentah")
    return 0


if __name__ == "__main__":
    sys.exit(main())
