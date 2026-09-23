"""
Cari tahu kapan ukuran jendela berubah saat halaman dibuka.

Pada pengambilan tangkapan layar, dua halaman terakhir menghasilkan gambar
1920x1057 padahal jendela disetel 1366x768. Skrip ini mencatat ukuran
jendela sebelum dan sesudah setiap halaman dibuka, supaya halaman penyebab
perubahan dapat diketahui.
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
os.environ["AKUNTANSIID_DATA"] = str(AKAR / "_ssdata")
sys.path.insert(0, str(AKAR / "src"))

from PySide6.QtWidgets import QApplication  # noqa: E402

from akuntansi_id.core import license as LIS  # noqa: E402
from akuntansi_id.core import security as sec  # noqa: E402
from akuntansi_id.ui import theme  # noqa: E402
from akuntansi_id.ui.main_window import MainWindow, Sidebar  # noqa: E402

LEBAR, TINGGI = 1366, 768

_LIS = LIS.Lisensi(
    kunci="UKUR", paket="enterprise", pemilik="X",
    berlaku_sampai=time.time() + 86400,
    fitur={"konsolidasi": True, "dimensi": True, "pajak_lanjutan": True,
           "audit_lanjutan": True, "multi_entitas": True})


def tunggu(app, detik=0.8):
    akhir = time.time() + detik
    while time.time() < akhir:
        app.processEvents()
        time.sleep(0.01)


def main() -> int:
    app = QApplication.instance() or QApplication([])
    app.setStyleSheet(theme.stylesheet())

    hasil = sec.LoginResult(ok=True, user_id=1, username="admin",
                            full_name="Budi", role="owner",
                            app_mode="expert", mode_dipilih=True)
    j = MainWindow(hasil, lisensi=_LIS)
    j.resize(LEBAR, TINGGI)
    j.show()
    tunggu(app, 1.5)

    print("=" * 70)
    print("  PANTAU UKURAN JENDELA TIAP HALAMAN")
    print("=" * 70)
    print()
    print(f"  ukuran awal: {j.width()} x {j.height()}")
    print()

    kode_halaman = [kode for _, isi in Sidebar.MENU for kode, _, _ in isi]

    berubah = []
    sebelumnya = (j.width(), j.height())

    for kode in kode_halaman:
        try:
            j._navigasi(kode)
        except Exception:
            continue
        tunggu(app, 0.7)

        sekarang = (j.width(), j.height())
        if sekarang != sebelumnya:
            berubah.append((kode, sebelumnya, sekarang))
            print(f"  BERUBAH di '{kode}': "
                  f"{sebelumnya[0]}x{sebelumnya[1]} -> "
                  f"{sekarang[0]}x{sekarang[1]}")
        sebelumnya = sekarang

    print()
    if berubah:
        print(f"  {len(berubah)} halaman mengubah ukuran jendela:")
        for kode, a, b in berubah:
            print(f"    {kode}: {a[0]}x{a[1]} -> {b[0]}x{b[1]}")
    else:
        print("  ukuran jendela tetap sepanjang pengujian")

    print()
    print(f"  ukuran akhir: {j.width()} x {j.height()}")

    j.close()
    app.processEvents()
    return 0


if __name__ == "__main__":
    sys.exit(main())
