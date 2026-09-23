"""
Cari tahu label mana yang bertumpuk di dashboard.

Alat periksa melaporkan dua label bertumpuk pada koordinat (210,443) dan
(317,443). Skrip ini menelusuri label pada posisi itu dan menampilkan
teksnya, supaya penyebabnya dapat diketahui.
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
os.environ["AKUNTANSIID_DATA"] = str(AKAR / "_ssdata")
sys.path.insert(0, str(AKAR / "src"))

from PySide6.QtWidgets import QApplication, QLabel  # noqa: E402

from akuntansi_id.core import license as LIS  # noqa: E402
from akuntansi_id.core import security as sec  # noqa: E402
from akuntansi_id.ui import theme  # noqa: E402
from akuntansi_id.ui.main_window import MainWindow  # noqa: E402

LEBAR, TINGGI = 1600, 1000

_LIS = LIS.Lisensi(
    kunci="C", paket="enterprise", pemilik="X",
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
    tunggu(app, 2.0)

    halaman = j.stack.currentWidget()

    print("=" * 72)
    print("  CARI LABEL BERTUMPUK DI DASHBOARD")
    print("=" * 72)
    print()

    # Kumpulkan label beserta posisi relatif terhadap halaman
    daftar = []
    for lbl in halaman.findChildren(QLabel):
        if not lbl.isVisible() or not lbl.text().strip():
            continue
        pos = lbl.mapTo(halaman, lbl.rect().topLeft())
        daftar.append((lbl, pos.x(), pos.y(), lbl.width(), lbl.height()))

    # Cari pasangan yang berpotongan
    jumlah = 0
    for i, (a, ax, ay, aw, ah) in enumerate(daftar):
        for b, bx, by, bw, bh in daftar[i + 1:]:
            tumpang_x = not (ax + aw <= bx or bx + bw <= ax)
            tumpang_y = not (ay + ah <= by or by + bh <= ay)
            if not (tumpang_x and tumpang_y):
                continue
            # Abaikan label yang saling bersarang (induk dan anak)
            if a.parent() is b or b.parent() is a:
                continue
            jumlah += 1
            print(f"  [{jumlah}] bertumpuk:")
            print(f"      A: '{a.text()[:50]}'")
            print(f"         pos=({ax},{ay}) ukuran={aw}x{ah}")
            print(f"         induk={a.parent().__class__.__name__}")
            print(f"      B: '{b.text()[:50]}'")
            print(f"         pos=({bx},{by}) ukuran={bw}x{bh}")
            print(f"         induk={b.parent().__class__.__name__}")
            print()

    if jumlah == 0:
        print("  tidak ada label bertumpuk pada ukuran ini")

    j.close()
    app.processEvents()
    return 0


if __name__ == "__main__":
    sys.exit(main())
