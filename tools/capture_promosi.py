"""Ambil tangkapan layar beberapa halaman untuk bahan promosi.

Cara pakai:
    python tools/capture_promosi.py

Hasil disimpan di folder _promosi/ dalam ukuran 1280x800 (rasio kartu).
Gunakan data contoh agar isinya terlihat hidup.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
KELUAR = AKAR / "_promosi"
os.environ["AKUNTANSIID_DATA"] = str(AKAR / "_contoh")
sys.path.insert(0, str(AKAR / "src"))

from PySide6.QtWidgets import QApplication  # noqa: E402

from akuntansi_id import config, services  # noqa: E402
from akuntansi_id.core import security as sec  # noqa: E402
from akuntansi_id.ui import theme  # noqa: E402
from akuntansi_id.ui.main_window import MainWindow  # noqa: E402

# Lisensi uji dipakai agar seluruh halaman ikut diperiksa, termasuk
# halaman yang hanya tersedia pada paket Enterprise.
from akuntansi_id.core.license import Lisensi as _LisensiUji
_LISENSI_UJI = _LisensiUji(kunci='ATNTUJI', paket='enterprise', fitur={})


# Halaman yang mewakili keunggulan aplikasi, dipilih agar beragam:
# ringkasan, penjualan, pajak, laporan, dan analisis.
HALAMAN = [
    ("dashboard", "Dashboard", 0),
    ("penjualan", "Penjualan", 0),
    ("pajak", "Pajak & SPT", 0),
    ("laporan", "Laporan Keuangan", 1),
    ("analisis", "Analisis Keuangan", 0),
    ("pajak_lanjutan", "Pajak Lanjutan", 1),
]

LEBAR, TINGGI = 1280, 800


def main() -> int:
    KELUAR.mkdir(exist_ok=True)
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
    # Mode Ahli: antarmuka bersih tanpa panel keterangan, lebih pas untuk promosi.
    jendela.ctx.beginner = False
    jendela.resize(LEBAR, TINGGI)
    jendela.show()
    for _ in range(10):
        app.processEvents()

    tersimpan = []
    for kode, nama, indeks_tab in HALAMAN:
        halaman = jendela.halaman.get(kode)
        if halaman is None:
            print(f"  LEWAT {nama}: halaman tidak ditemukan")
            continue
        jendela._navigasi(kode)
        for _ in range(10):
            app.processEvents()

        # pilih tab yang mewakili bila halaman punya tab
        tabs = getattr(halaman, "tabs", None)
        if tabs is not None and 0 <= indeks_tab < tabs.count():
            tabs.setCurrentIndex(indeks_tab)
            for _ in range(10):
                app.processEvents()

        berkas = KELUAR / f"{kode}.png"
        jendela.grab().save(str(berkas))
        tersimpan.append((nama, berkas))
        print(f"  {nama:22s} -> {berkas.name}")

    print(f"\n{len(tersimpan)} tangkapan disimpan di {KELUAR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
