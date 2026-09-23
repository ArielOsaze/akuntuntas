"""
Cari panel dashboard yang membuat isi lebih lebar dari ruang tersedia.

Isi dashboard terukur 1182px sementara ruang tersedia 1035px, sehingga ada
panel yang memaksa lebar melebihi jendela. Skrip ini menelusuri setiap anak
langsung area gulir dan melaporkan lebar minimumnya, supaya panel penyebab
dapat diketahui dengan pasti.
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
os.environ["AKUNTANSIID_DATA"] = str(AKAR / "_ssdata")
sys.path.insert(0, str(AKAR / "src"))

from PySide6.QtWidgets import QApplication, QScrollArea, QWidget  # noqa: E402

from akuntansi_id.core import license as LIS  # noqa: E402
from akuntansi_id.core import security as sec  # noqa: E402
from akuntansi_id.ui import theme  # noqa: E402
from akuntansi_id.ui.main_window import MainWindow  # noqa: E402

_LIS = LIS.Lisensi(
    kunci="CARI", paket="enterprise", pemilik="X",
    berlaku_sampai=time.time() + 86400,
    fitur={"konsolidasi": True, "dimensi": True, "pajak_lanjutan": True,
           "audit_lanjutan": True, "multi_entitas": True})


def tunggu(app, detik=1.5):
    akhir = time.time() + detik
    while time.time() < akhir:
        app.processEvents()
        time.sleep(0.01)


def minimum_efektif(w: QWidget) -> int:
    """Lebar minimum yang benar-benar dipakai widget."""
    return max(w.minimumWidth(), w.minimumSizeHint().width())


def telusuri(w: QWidget, kedalaman: int = 0, maks: int = 4):
    """Telusuri anak langsung dan laporkan yang menyumbang lebar besar."""
    if kedalaman > maks:
        return
    for anak in w.children():
        if not isinstance(anak, QWidget) or not anak.isVisible():
            continue
        minw = minimum_efektif(anak)
        if minw > 300:
            print(f"    {'  ' * kedalaman}{anak.__class__.__name__:18s}"
                  f" lebar={anak.width():5d} min={minw:5d}")
        telusuri(anak, kedalaman + 1, maks)


def main() -> int:
    app = QApplication.instance() or QApplication([])
    app.setStyleSheet(theme.stylesheet())

    hasil = sec.LoginResult(ok=True, user_id=1, username="admin",
                            full_name="Budi", role="owner",
                            app_mode="expert", mode_dipilih=True)
    j = MainWindow(hasil, lisensi=_LIS)
    j.resize(1366, 768)
    j.show()
    tunggu(app)
    j._navigasi("dashboard")
    tunggu(app, 2.0)

    halaman = j.stack.currentWidget()

    print("=" * 72)
    print("  CARI PANEL YANG MEMAKSA LEBAR")
    print("=" * 72)
    print()

    for sa in halaman.findChildren(QScrollArea):
        isi = sa.widget()
        if isi is None:
            continue
        print(f"  viewport : {sa.viewport().width()}px")
        print(f"  isi      : {isi.width()}px  (kelebihan "
              f"{isi.width() - sa.viewport().width()}px)")
        print()
        print("  widget dengan lebar minimum > 300px:")
        telusuri(isi)
        print()
        print("  anak langsung isi:")
        for anak in isi.children():
            if isinstance(anak, QWidget) and anak.isVisible():
                print(f"    {anak.__class__.__name__:20s} "
                      f"lebar={anak.width():5d} "
                      f"min={minimum_efektif(anak):5d}")
        break

    j.close()
    app.processEvents()
    return 0


if __name__ == "__main__":
    sys.exit(main())
