"""
Ukur area isi dashboard untuk mencari penyebab widget keluar batas.

Pemeriksaan pertama hanya melihat label. Skrip ini memeriksa wadahnya:
lebar area gulir, lebar halaman, dan lebar sidebar, sehingga penyebab
sebenarnya dapat diketahui.
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
os.environ["AKUNTANSIID_DATA"] = str(AKAR / "_ssdata")
sys.path.insert(0, str(AKAR / "src"))

from PySide6.QtWidgets import QApplication, QScrollArea, QLabel  # noqa: E402

from akuntansi_id.core import license as LIS  # noqa: E402
from akuntansi_id.core import security as sec  # noqa: E402
from akuntansi_id.ui import theme  # noqa: E402
from akuntansi_id.ui.main_window import MainWindow  # noqa: E402

LEBAR, TINGGI = 1366, 768

_LIS = LIS.Lisensi(
    kunci="U", paket="enterprise", pemilik="X",
    berlaku_sampai=time.time() + 86400,
    fitur={"konsolidasi": True, "dimensi": True, "pajak_lanjutan": True,
           "audit_lanjutan": True, "multi_entitas": True})


def tunggu(app, detik=1.5):
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
    tunggu(app)
    j._navigasi("dashboard")
    tunggu(app)

    h = j.stack.currentWidget()

    print("=" * 72)
    print("  UKUR WADAH DASHBOARD")
    print("=" * 72)
    print()
    print(f"  jendela       : {j.width()} x {j.height()}")
    print(f"  stack         : {j.stack.width()} x {j.stack.height()}")
    print(f"  halaman       : {h.width()} x {h.height()}")
    print(f"  sidebar       : {j.sidebar.width()}")

    for sa in h.findChildren(QScrollArea):
        print()
        print(f"  area gulir    : {sa.width()} x {sa.height()}")
        print(f"    viewport    : {sa.viewport().width()} x {sa.viewport().height()}")
        if sa.widget():
            print(f"    isi         : {sa.widget().width()} x {sa.widget().height()}")
        sb = sa.verticalScrollBar()
        print(f"    gulir tegak : {'TAMPIL' if sb.isVisible() else 'tidak'}"
              f"  (lebar {sb.width() if sb.isVisible() else 0}px)")
        break

    # Telusuri label KAS & BANK sampai ke akarnya
    for lbl in h.findChildren(QLabel):
        if lbl.text().strip() != "KAS & BANK":
            continue
        print()
        print("  label 'KAS & BANK':")
        print(f"    lebar widget      : {lbl.width()}")
        kiri = lbl.mapTo(j, lbl.rect().topLeft()).x()
        kanan = lbl.mapTo(j, lbl.rect().topRight()).x()
        print(f"    kiri di jendela   : {kiri}")
        print(f"    kanan di jendela  : {kanan}   (jendela {j.width()})")
        print()
        print("    rantai induk:")
        induk = lbl.parent()
        naik = 0
        while induk is not None and naik < 6:
            lebar = induk.width()
            k = induk.mapTo(j, induk.rect().topLeft()).x() if hasattr(induk, "mapTo") else 0
            print(f"      {induk.__class__.__name__:16s} lebar={lebar:5d}  kiri={k}")
            induk = induk.parent()
            naik += 1
        break

    j.close()
    app.processEvents()
    return 0


if __name__ == "__main__":
    sys.exit(main())
