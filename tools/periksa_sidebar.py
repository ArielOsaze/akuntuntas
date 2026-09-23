"""Deteksi label di sidebar yang terpotong karena kolomnya terlalu sempit.

Cara pakai:
    python tools/periksa_sidebar.py

Nama menu dan merek aplikasi harus terbaca utuh. Label yang lebar
teksnya melebihi lebar kotaknya akan tampil terpotong di aplikasi.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
os.environ["AKUNTANSIID_DATA"] = str(AKAR / "_contoh")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(AKAR / "src"))

from PySide6.QtGui import QFont, QFontMetrics  # noqa: E402
from PySide6.QtWidgets import QApplication, QLabel  # noqa: E402

from akuntansi_id import config, services  # noqa: E402
from akuntansi_id.core import security as sec  # noqa: E402
from akuntansi_id.ui import theme  # noqa: E402
from akuntansi_id.ui.main_window import MainWindow  # noqa: E402

# Lisensi uji dipakai agar seluruh halaman ikut diperiksa, termasuk
# halaman yang hanya tersedia pada paket Enterprise.
from akuntansi_id.core.license import Lisensi as _LisensiUji
_LISENSI_UJI = _LisensiUji(kunci='ATNTUJI', paket='enterprise', fitur={})


LEBAR_SIDEBAR = 250


def lebar_teks(lbl, teks: str) -> int:
    """Lebar teks memakai font efektif label.

    fontMetrics() memakai font default widget, bukan ukuran dari stylesheet,
    sehingga hasilnya bisa jauh lebih kecil dari tampilan sebenarnya.
    """
    font = QFont(lbl.font())
    gaya = lbl.styleSheet()
    for bagian in gaya.split(";"):
        if ":" not in bagian:
            continue
        nama, nilai = bagian.split(":", 1)
        nama = nama.strip()
        nilai = nilai.strip()
        if nama == "font-size":
            try:
                font.setPixelSize(int(float(nilai.replace("px", ""))))
            except ValueError:
                pass
        elif nama == "font-weight":
            try:
                font.setWeight(QFont.Weight(int(nilai)))
            except ValueError:
                pass
    return QFontMetrics(font).horizontalAdvance(teks)


def main() -> int:
    app = QApplication.instance() or QApplication([])
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
    jendela.resize(1440, 900)
    jendela.show()
    for _ in range(8):
        app.processEvents()

    masalah = []
    for lbl in jendela.findChildren(QLabel):
        if not lbl.isVisible():
            continue
        teks = lbl.text().strip()
        if len(teks) < 4:
            continue
        if lbl.mapTo(jendela, lbl.rect().topLeft()).x() > LEBAR_SIDEBAR:
            continue
        perlu = lebar_teks(lbl, teks)
        if perlu > lbl.width() + 2:
            masalah.append((teks, perlu, lbl.width()))
            print(f"  [POTONG] '{teks[:34]:36s}' lebar={lbl.width():4d} "
                  f"butuh={perlu:4d}")

    # Periksa judul kelompok sub-kategori: harus terbaca utuh juga.
    from akuntansi_id.ui.main_window import Sidebar
    sidebar = jendela.findChild(Sidebar)
    if sidebar is not None:
        for nama, (judul, _) in sidebar._grup.items():
            if not judul.isVisible():
                continue
            perlu = lebar_teks(judul, nama) + 22
            if perlu > judul.width() + 2:
                masalah.append((nama, perlu, judul.width()))
                print(f"  [POTONG] kelompok '{nama[:28]:30s}' "
                      f"lebar={judul.width():4d} butuh={perlu:4d}")

    print()
    if masalah:
        print(f"HASIL: {len(masalah)} label sidebar terpotong")
        return 1
    print("HASIL: seluruh label sidebar terbaca utuh")
    return 0


if __name__ == "__main__":
    sys.exit(main())
