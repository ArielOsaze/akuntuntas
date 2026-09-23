"""Deteksi label yang menampilkan nama ikon sebagai teks (bukan gambar).

Cara pakai:
    python tools/periksa_teks_ikon.py

Pemeriksaan statis tidak menangkap pola seperti QLabel(ikon) di dalam
perulangan, padahal hasilnya adalah teks "simpan" atau "peringatan" yang
tampil ke pengguna. Pemeriksaan ini membaca label yang benar-benar dirender
di setiap halaman dan jendela login.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
os.environ["AKUNTANSIID_DATA"] = str(AKAR / "_contoh")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(AKAR / "src"))

from PySide6.QtWidgets import QApplication, QLabel  # noqa: E402

from akuntansi_id import config, services  # noqa: E402
from akuntansi_id.core import security as sec  # noqa: E402
from akuntansi_id.ui import icons, theme  # noqa: E402
from akuntansi_id.ui.login import BrandPanel, LoginPage  # noqa: E402
from akuntansi_id.ui.main_window import MainWindow, Sidebar  # noqa: E402

# Lisensi uji dipakai agar seluruh halaman ikut diperiksa, termasuk
# halaman yang hanya tersedia pada paket Enterprise.
from akuntansi_id.core.license import Lisensi as _LisensiUji
_LISENSI_UJI = _LisensiUji(kunci='ATNTUJI', paket='enterprise', fitur={})


HALAMAN = [k for _, daftar in Sidebar.MENU for k, _, _ in daftar]


def label_bermasalah(akar) -> list:
    """Label yang teksnya sama persis dengan nama ikon dan tanpa gambar.

    Label ikon selalu berukuran kecil, sempit, dan berdiri sendiri. Judul
    halaman, kategori temuan, atau judul kolom yang kebetulan sama dengan
    nama ikon (mis. "Penjualan", "Pajak") tidak dilaporkan karena
    ukurannya jauh lebih besar.
    """
    nama_ikon = set(icons.semua_nama())
    temuan = []
    for lbl in akar.findChildren(QLabel):
        if not lbl.isVisible():
            continue
        teks = lbl.text().strip()
        if not teks or teks.lower() not in nama_ikon:
            continue
        # label ikon selalu kecil; teks wajar berukuran lebih besar
        if lbl.width() > 40 or lbl.height() > 22:
            continue
        gambar = lbl.pixmap()
        if gambar is not None and not gambar.isNull():
            continue
        temuan.append((teks, lbl.width(), lbl.height()))
    return temuan


def main() -> int:
    app = QApplication.instance() or QApplication([])
    app.setStyleSheet(theme.stylesheet())

    masalah = []

    for nama, kelas, ukuran in (("login", LoginPage, (620, 660)),
                                ("merek", BrandPanel, (430, 660))):
        layar = kelas()
        layar.resize(*ukuran)
        layar.show()
        for _ in range(8):
            app.processEvents()
        for t in label_bermasalah(layar):
            masalah.append((nama, *t))
            print(f"  [TEKS IKON] {nama:12s} '{t[0]}' ({t[1]}x{t[2]})")
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
    jendela.resize(1440, 900)
    jendela.show()

    for kode in HALAMAN:
        try:
            jendela._navigasi(kode)
            for _ in range(6):
                app.processEvents()
            halaman = jendela.halaman.get(kode)
            if halaman is None:
                continue
            for t in label_bermasalah(halaman):
                masalah.append((kode, *t))
                print(f"  [TEKS IKON] {kode:12s} '{t[0]}' ({t[1]}x{t[2]})")
        except Exception as e:
            print(f"  [ERROR] {kode}: {type(e).__name__}: {e}")

    print()
    if masalah:
        print(f"HASIL: {len(masalah)} label menampilkan nama ikon sebagai teks")
        return 1
    print("HASIL: tidak ada nama ikon yang tampil sebagai teks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
