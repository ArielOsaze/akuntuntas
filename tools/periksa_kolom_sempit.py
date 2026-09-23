"""Deteksi kolom tabel yang terlalu sempit untuk isinya.

Cara pakai:
    python tools/periksa_kolom_sempit.py

Kolom yang tidak cukup lebar membuat isi tabel terpotong (mis. "Rp216.5…"),
sehingga informasi penting tidak terbaca. Pemeriksaan ini membandingkan
lebar kolom dengan lebar teks terpanjang di dalamnya.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
os.environ["AKUNTANSIID_DATA"] = str(AKAR / "_contoh")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(AKAR / "src"))

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from akuntansi_id import config, services  # noqa: E402
from akuntansi_id.core import security as sec  # noqa: E402
from akuntansi_id.ui import theme  # noqa: E402
from akuntansi_id.ui.main_window import MainWindow, Sidebar  # noqa: E402
from akuntansi_id.ui.widgets import Tabel  # noqa: E402

# Lisensi uji dipakai agar seluruh halaman ikut diperiksa, termasuk
# halaman yang hanya tersedia pada paket Enterprise.
from akuntansi_id.core.license import Lisensi as _LisensiUji
_LISENSI_UJI = _LisensiUji(kunci='ATNTUJI', paket='enterprise', fitur={})


HALAMAN = [k for _, daftar in Sidebar.MENU for k, _, _ in daftar]


def main():
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

    masalah = []
    for kode in HALAMAN:
        try:
            jendela._navigasi(kode)
            for _ in range(6):
                app.processEvents()
            halaman = jendela.halaman.get(kode)
            if halaman is None:
                continue
            for temuan in periksa(halaman):
                masalah.append((kode, *temuan))
                print(f"  [SEMPIT] {kode:12s} {temuan[0][:26]:28s} "
                      f"kolom '{temuan[1][:18]:20s}' w={temuan[3]:4d} "
                      f"butuh={temuan[2]:4d}")
        except Exception as e:
            print(f"  [ERROR] {kode}: {type(e).__name__}: {e}")

    print()
    if masalah:
        print(f"HASIL: {len(masalah)} kolom terlalu sempit")
    else:
        print("HASIL: seluruh kolom tabel cukup lebar")
    return 0


def periksa(halaman) -> list:
    """Kembalikan (nama_tabel, judul_kolom, butuh, nyata) yang terlalu sempit.

    Pemotongan dinilai dengan elidedText — cara Qt sendiri memotong teks —
    sehingga laporannya persis sama dengan yang dilihat pengguna. Teks
    panjang seperti keterangan tidak dihitung karena wajar dipotong dan
    tetap bisa dibaca lewat tooltip.
    """
    temuan = []
    for tabel in halaman.findChildren(Tabel):
        if not tabel.isVisible() or tabel.columnCount() == 0:
            continue
        fm = tabel.fontMetrics()
        for kolom in range(tabel.columnCount()):
            lebar = tabel.columnWidth(kolom)
            if lebar <= 8:
                continue
            judul = tabel.horizontalHeaderItem(kolom)
            judul = judul.text() if judul else ""
            perlu = 0
            for baris in range(tabel.rowCount()):
                item = tabel.item(baris, kolom)
                if item is None or not item.text():
                    continue
                teks = item.text()
                if len(teks) > 30:
                    continue
                if fm.elidedText(teks, Qt.ElideRight, lebar - 10) == teks:
                    continue
                perlu = max(perlu, fm.horizontalAdvance(teks) + 14)
            if perlu > lebar:
                temuan.append((tabel.objectName() or "tabel", judul, perlu, lebar))
    return temuan


if __name__ == "__main__":
    sys.exit(main())
