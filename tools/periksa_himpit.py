"""Deteksi isi halaman yang terhimpit: tinggi nyata jauh di bawah kebutuhan.

Cara pakai:
    python tools/periksa_himpit.py

Halaman yang isinya lebih panjang dari jendela harus bisa digulir. Bila
tidak, kartu dan label akan terpotong meski tidak ada error.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
os.environ["AKUNTANSIID_DATA"] = str(AKAR / "_contoh")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(AKAR / "src"))

from PySide6.QtWidgets import QApplication, QScrollArea, QWidget  # noqa: E402

from akuntansi_id import config, services  # noqa: E402
from akuntansi_id.core import security as sec  # noqa: E402
from akuntansi_id.ui import theme  # noqa: E402
from akuntansi_id.ui.main_window import MainWindow, Sidebar  # noqa: E402

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
            laporan = periksa(halaman)
            if laporan:
                masalah.extend((kode, *m) for m in laporan)
                for m in laporan:
                    print(f"  [HIMPIT] {kode:14s} {m[0][:52]:54s} "
                          f"h={m[2]} < butuh {m[1]}")
        except Exception as e:
            print(f"  [ERROR] {kode}: {type(e).__name__}: {e}")

    print()
    if masalah:
        print(f"HASIL: {len(masalah)} isi terhimpit")
    else:
        print("HASIL: tidak ada isi yang terhimpit")
    return 0


def periksa(halaman: QWidget) -> list:
    """Kembalikan daftar (nama, tinggi_butuh, tinggi_nyata) yang terhimpit.

    Ukuran yang dipakai adalah jangkauan gulir nyata: bila posisi terbawah
    masih lebih kecil dari tinggi isi, ada bagian yang tidak bisa dicapai
    pengguna.
    """
    temuan = []
    for area in halaman.findChildren(QScrollArea):
        isi = area.widget()
        if isi is None or isi.layout() is None:
            continue
        vb = area.verticalScrollBar()
        jangkauan = vb.maximum() + area.viewport().height()
        if isi.height() > jangkauan + 8:
            temuan.append((isi.objectName() or "(isi)",
                           isi.height(), jangkauan))
    return temuan


if __name__ == "__main__":
    sys.exit(main())
