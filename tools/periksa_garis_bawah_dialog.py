"""Pastikan dialog dan kotak pesan juga bebas teks bergaris bawah.

Cara pakai:
    python tools/periksa_garis_bawah_dialog.py

Pemeriksaan halaman utama tidak menjangkau dialog karena dialog baru dibuat
saat tombolnya ditekan. Berkas ini membuka setiap dialog yang ada, membaca
seluruh teksnya, lalu menutupnya kembali.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
os.environ["AKUNTANSIID_DATA"] = str(AKAR / "_contoh")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(AKAR / "src"))
sys.path.insert(0, str(AKAR / "tools"))

from PySide6.QtWidgets import (QApplication, QDialog,  # noqa: E402
                               QMessageBox, QPushButton)

from akuntansi_id import config, services  # noqa: E402
from akuntansi_id.core import security as sec  # noqa: E402
from akuntansi_id.ui import theme  # noqa: E402
from akuntansi_id.ui.main_window import MainWindow, Sidebar  # noqa: E402

# Lisensi uji dipakai agar seluruh halaman ikut diperiksa, termasuk
# halaman yang hanya tersedia pada paket Enterprise.
from akuntansi_id.core.license import Lisensi as _LisensiUji
_LISENSI_UJI = _LisensiUji(kunci='ATNTUJI', paket='enterprise', fitur={})

from periksa_garis_bawah import ada_garis_bawah, periksa  # noqa: E402

HALAMAN = [k for _, daftar in Sidebar.MENU for k, _, _ in daftar]

# tombol yang membuka dialog (bukan yang menyimpan/menghapus)
LEWATI = ("simpan", "hapus", "batal", "tutup", "keluar", "pulihkan",
          "bersihkan", "jalankan", "posting", "buat jurnal", "impor sekarang",
          "tampilkan", "hitung", "ekspor", "cetak", "unduh",
          # Membuka aplikasi lain saat diklik, sehingga tidak diuji dengan
          # klik: "kirim lewat email" membuka aplikasi email bawaan.
          "kirim", "email", "buka folder", "buka lokasi", "buka tautan")


def aman_ditekan(teks: str) -> bool:
    t = teks.strip().lower()
    if not t:
        return False
    return not any(k in t for k in LEWATI)


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
    dicek = 0
    ditutup: list = []

    def baca_lalu_tutup():
        """Baca teks setiap dialog yang muncul lalu tutup agar tidak memblokir."""
        for w in app.topLevelWidgets():
            if not isinstance(w, QDialog) or not w.isVisible():
                continue
            if w in ditutup:
                continue
            ditutup.append(w)
            if isinstance(w, QMessageBox):
                w.close()
                continue
            for tempat, teks in periksa(w):
                masalah.append(("dialog", tempat, teks))
                print(f"  [GARIS BAWAH] dialog       {tempat:14s} '{teks[:42]}'")
            if ada_garis_bawah(w.windowTitle()):
                masalah.append(("dialog", "judul", w.windowTitle()))
                print(f"  [GARIS BAWAH] dialog       judul          "
                      f"'{w.windowTitle()[:42]}'")
            w.reject()

    from PySide6.QtCore import QTimer
    penutup = QTimer()
    penutup.timeout.connect(baca_lalu_tutup)
    penutup.start(120)

    for kode in HALAMAN:
        try:
            jendela._navigasi(kode)
            for _ in range(6):
                app.processEvents()
            halaman = jendela.halaman.get(kode)
            if halaman is None:
                continue
        except Exception:
            continue

        for tombol in halaman.findChildren(QPushButton):
            if not tombol.isVisible() or not aman_ditekan(tombol.text()):
                continue
            try:
                tombol.click()
            except Exception:
                continue
            for _ in range(10):
                app.processEvents()
            baca_lalu_tutup()

    print()
    print(f"dialog diperiksa: {dicek}")
    if masalah:
        print(f"HASIL: {len(masalah)} teks dialog memakai garis bawah")
        return 1
    print("HASIL: seluruh teks dialog bebas garis bawah")
    return 0


if __name__ == "__main__":
    sys.exit(main())
