"""
Ambil tangkapan layar untuk halaman listing Microsoft Store.

Partner Center mewajibkan minimal satu tangkapan layar, disarankan empat,
dengan ukuran 1366x768 piksel atau lebih besar. Skrip ini membuka aplikasi
memakai data contoh, membuka halaman yang dipilih, lalu menyimpan
tangkapan layarnya pada ukuran yang diminta.

Jendela aplikasi dirender pada layar asli, bukan mode tanpa layar, supaya
hurufnya tergambar benar. Mode tanpa layar menghasilkan kotak-kotak dan
tidak layak dipakai untuk menilai tampilan.

Cara pakai:

    python tools/buat_data_contoh.py "C:\\...\\_ssdata"
    python tools/tangkapan_store.py

Hasil disimpan di folder `store_gambar/` dan disalin ke Desktop.
"""
from __future__ import annotations

import os
import shutil
import sys
import time
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
KELUAR = AKAR / "store_gambar"
DESKTOP = Path.home() / "Desktop" / "AkunTuntas-Gambar-Store"
DATA = AKAR / "_ssdata"

# Ukuran yang diminta Partner Center. Dipakai 1366x768 karena itu ukuran
# terkecil yang diterima, sehingga berkasnya tidak terlalu besar.
LEBAR, TINGGI = 1366, 768

os.environ["AKUNTANSIID_DATA"] = str(DATA)
sys.path.insert(0, str(AKAR / "src"))

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from akuntansi_id.core import license as LIS  # noqa: E402
from akuntansi_id.core import security as sec  # noqa: E402
from akuntansi_id.ui import theme  # noqa: E402
from akuntansi_id.ui.main_window import MainWindow  # noqa: E402

# Lisensi uji supaya seluruh halaman terbuka saat pengambilan gambar.
_LISENSI = LIS.Lisensi(
    kunci="GAMBAR-STORE",
    paket="enterprise",
    pemilik="Xinet Group",
    berlaku_sampai=time.time() + 86400 * 30,
    fitur={
        "konsolidasi": True,
        "dimensi": True,
        "pajak_lanjutan": True,
        "audit_lanjutan": True,
        "multi_entitas": True,
    },
)

# Halaman yang diambil, sesuai urutan yang disarankan pada halaman Store.
# Halaman dipilih karena paling menggambarkan kegunaan aplikasi.
HALAMAN = [
    ("dashboard", "01-dashboard", "Dashboard"),
    ("penjualan", "02-penjualan", "Penjualan"),
    ("pajak", "03-pajak", "Pajak dan SPT"),
    ("laporan", "04-laporan", "Laporan Keuangan"),
    ("payroll", "05-payroll", "Payroll"),
    ("produk", "06-produk", "Produk dan Persediaan"),
]


def tunggu(app: QApplication, detik: float = 0.8) -> None:
    """Beri waktu antarmuka selesai menggambar."""
    akhir = time.time() + detik
    while time.time() < akhir:
        app.processEvents()
        time.sleep(0.01)


def main() -> int:
    if not (DATA / "akuntuntas.db").exists():
        print(f"  Data contoh belum ada di {DATA}")
        print("  Jalankan lebih dahulu:")
        print(f'    python tools/buat_data_contoh.py "{DATA}"')
        return 1

    app = QApplication.instance() or QApplication([])
    app.setStyleSheet(theme.stylesheet())

    # Sesi pemilik supaya seluruh menu terbuka.
    hasil = sec.LoginResult(
        ok=True, user_id=1, username="admin",
        full_name="Budi Santoso", role="owner",
        app_mode="expert", mode_dipilih=True)

    jendela = MainWindow(hasil, lisensi=_LISENSI)
    jendela.resize(LEBAR, TINGGI)
    jendela.show()
    tunggu(app, 1.5)

    KELUAR.mkdir(exist_ok=True)

    # Buka kelompok menu yang memuat halaman yang akan diambil, supaya
    # sidebar terlihat hidup dan menunya tampak lengkap.
    for nama in ("BUKU & KAS", "DATA USAHA", "LAPORAN"):
        pasangan = jendela.sidebar._grup.get(nama)
        if pasangan:
            pasangan[0].setChecked(True)
    tunggu(app, 0.6)

    print("=" * 70)
    print("  TANGKAPAN LAYAR UNTUK MICROSOFT STORE")
    print("=" * 70)
    print()
    print(f"  Ukuran : {LEBAR}x{TINGGI} piksel")
    print(f"  Hasil  : {KELUAR}")
    print()

    jumlah = 0
    for kode, nama_berkas, judul in HALAMAN:
        try:
            jendela._navigasi(kode)
        except Exception as e:
            print(f"  LEWAT {judul}: {e}")
            continue

        tunggu(app, 1.2)

        gambar = jendela.grab()
        jalur = KELUAR / f"{nama_berkas}.png"

        # Jendela dapat tergusur oleh penskalaan tampilan Windows, sehingga
        # gambar yang dihasilkan lebih besar dari ukuran yang diminta.
        # Ukurannya dikembalikan ke ukuran yang diminta supaya seluruh
        # berkas seragam dan sesuai syarat Partner Center.
        if gambar.width() != LEBAR or gambar.height() != TINGGI:
            gambar = gambar.scaled(
                LEBAR, TINGGI,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation)

        gambar.save(str(jalur))

        lebar, tinggi = gambar.width(), gambar.height()
        tanda = "OK" if lebar >= 1366 and tinggi >= 768 else "KECIL"
        print(f"  [{tanda}] {nama_berkas}.png  {lebar}x{tinggi}  {judul}")
        jumlah += 1

    jendela.close()
    app.processEvents()

    print()
    print(f"  {jumlah} tangkapan disimpan.")

    if jumlah == 0:
        print("  TIDAK ADA tangkapan yang berhasil dibuat.")
        return 2

    # Salin ke Desktop supaya mudah ditemukan saat mengunggah.
    if DESKTOP.parent.exists():
        if DESKTOP.exists():
            shutil.rmtree(DESKTOP, ignore_errors=True)
        DESKTOP.mkdir(parents=True, exist_ok=True)
        for berkas in sorted(KELUAR.glob("*.png")):
            shutil.copy2(berkas, DESKTOP / berkas.name)
        print(f"  Disalin ke: {DESKTOP}")

    print()
    print("  Unggah berkas dari folder tersebut ke Partner Center,")
    print("  urut sesuai nomor pada nama berkas.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
