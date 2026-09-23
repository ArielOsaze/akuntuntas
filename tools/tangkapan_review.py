"""
Ambil tangkapan layar halaman aplikasi dengan teks yang benar-benar terlihat.

Cara pakai:
    python tools/tangkapan_review.py

Skrip ini menampilkan jendela aplikasi pada layar asli, bukan mode tanpa
layar (offscreen). Mode tanpa layar tidak merender huruf sehingga hasilnya
berupa kotak-kotak dan tidak layak dipakai untuk menilai tampilan.

Hasil disimpan di folder _review/ dan disalin ke Desktop.
"""

from __future__ import annotations

import os
import shutil
import sys
import time
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
KELUAR = AKAR / "_review"
DESKTOP = Path.home() / "Desktop" / "Hasil-Redesign-AkunTuntas"

os.environ["AKUNTANSIID_DATA"] = str(AKAR / "_contoh")
sys.path.insert(0, str(AKAR / "src"))

from PySide6.QtWidgets import QApplication  # noqa: E402

from akuntansi_id.core import security as sec  # noqa: E402
from akuntansi_id.ui import theme  # noqa: E402
from akuntansi_id.ui.main_window import MainWindow  # noqa: E402

# Lisensi uji dipakai agar seluruh halaman ikut diperiksa, termasuk
# halaman yang hanya tersedia pada paket Enterprise.
from akuntansi_id.core.license import Lisensi as _LisensiUji
_LISENSI_UJI = _LisensiUji(kunci='ATNTUJI', paket='enterprise', fitur={})


# Halaman yang diambil beserta nama berkasnya
HALAMAN = [
    ("dashboard", "1-Dashboard"),
    ("penjualan", "2-Penjualan"),
    ("pencarian", "3-Pencarian-Global"),
    ("laporan", "4-Laporan-Keuangan"),
    ("pajak", "5-Perpajakan"),
    ("biaya", "6-Biaya-Pengeluaran"),
]

# Halaman tambahan untuk menunjukkan menu yang menyesuaikan bentuk badan
BENTUK = [
    ("umkm_op", "dashboard", "7-Mode-UMKM-Orang-Pribadi"),
    ("pt", "dashboard", "8-Mode-PT"),
]


def tunggu(app: QApplication, detik: float = 0.6):
    """Beri waktu antarmuka selesai menggambar."""
    akhir = time.time() + detik
    while time.time() < akhir:
        app.processEvents()
        time.sleep(0.01)


def main() -> int:
    if not (AKAR / "_contoh").exists():
        print("data contoh belum ada; jalankan tools/buat_data_contoh.py dulu")
        return 1

    app = QApplication.instance() or QApplication([])
    app.setStyleSheet(theme.stylesheet())

    hasil = sec.LoginResult(ok=True, user_id=1, username="ariel",
                            full_name="Ariel Pratama", role="owner",
                            app_mode="expert", mode_dipilih=True)
    jendela = MainWindow(hasil, lisensi=_LISENSI_UJI)
    jendela.resize(1440, 900)
    jendela.show()
    tunggu(app, 1.2)

    KELUAR.mkdir(exist_ok=True)

    # buka beberapa kelompok menu supaya isinya terlihat pada tangkapan
    for nama in ("BUKU & KAS", "DATA USAHA"):
        pasangan = jendela.sidebar._grup.get(nama)
        if pasangan:
            pasangan[0].setChecked(True)
    tunggu(app, 0.5)

    jumlah = 0
    for kode, nama_berkas in HALAMAN:
        jendela._navigasi(kode)
        tunggu(app, 0.9)

        if kode == "pencarian":
            halaman = jendela.stack.currentWidget()
            halaman.inp_cari.setText("Retail")
            tunggu(app, 0.9)

        gambar = jendela.grab()
        gambar.save(str(KELUAR / f"{nama_berkas}.png"))
        jumlah += 1
        print(f"  {nama_berkas}.png")

    for bentuk, kode, nama_berkas in BENTUK:
        jendela.sidebar.terapkan_bentuk(bentuk)
        jendela._navigasi(kode)
        tunggu(app, 0.9)
        gambar = jendela.grab()
        gambar.save(str(KELUAR / f"{nama_berkas}.png"))
        jumlah += 1
        print(f"  {nama_berkas}.png")

    jendela.close()

    # salin ke Desktop agar mudah dibuka pengguna
    if DESKTOP.parent.exists():
        if DESKTOP.exists():
            shutil.rmtree(DESKTOP, ignore_errors=True)
        DESKTOP.mkdir(parents=True, exist_ok=True)
        for berkas in sorted(KELUAR.glob("*.png")):
            shutil.copy2(berkas, DESKTOP / berkas.name)
        print()
        print(f"{jumlah} tangkapan disalin ke: {DESKTOP}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
