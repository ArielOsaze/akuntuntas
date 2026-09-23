"""
Cari posisi tepat label legenda grafik, lalu potong gambarnya.

Vision dapat keliru menilai gambar utuh karena teksnya kecil. Cara yang
dapat dipercaya adalah mengukur posisi label di Qt, lalu memotong gambar
pada koordinat itu dan memperbesarnya.
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

LEBAR, TINGGI = 1366, 768
LEGENDA = ["Pendapatan", "HPP + Beban", "Laba sebelum pajak"]

_LIS = LIS.Lisensi(
    kunci="POTONG", paket="enterprise", pemilik="X",
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

    jendela = j
    halaman = j.stack.currentWidget()

    print("=" * 70)
    print("  POSISI LABEL LEGENDA")
    print("=" * 70)
    print()

    kotak = []
    for lbl in halaman.findChildren(QLabel):
        teks = lbl.text().strip()
        if teks not in LEGENDA:
            continue
        kiri = lbl.mapTo(jendela, lbl.rect().topLeft()).x()
        atas = lbl.mapTo(jendela, lbl.rect().topLeft()).y()
        kanan = lbl.mapTo(jendela, lbl.rect().bottomRight()).x()
        bawah = lbl.mapTo(jendela, lbl.rect().bottomRight()).y()
        butuh = lbl.fontMetrics().horizontalAdvance(teks)
        print(f"  '{teks}'")
        print(f"     butuh teks : {butuh}px")
        print(f"     lebar label: {lbl.width()}px")
        print(f"     posisi     : x {kiri}..{kanan}  y {atas}..{bawah}")
        print(f"     status     : "
              f"{'CUKUP' if lbl.width() >= butuh else 'TERPOTONG'}")
        print()
        kotak.append((kiri, atas, kanan, bawah))

    j.close()
    app.processEvents()

    if not kotak:
        print("  label legenda tidak ditemukan")
        return 1

    # Potong gambar pada area legenda, lalu perbesar
    from PIL import Image

    gambar = AKAR / "store_gambar" / "01-dashboard.png"
    if not gambar.exists():
        print(f"  gambar tidak ada: {gambar}")
        return 2

    im = Image.open(gambar)
    kiri = min(k[0] for k in kotak) - 14
    atas = min(k[1] for k in kotak) - 12
    kanan = max(k[2] for k in kotak) + 14
    bawah = max(k[3] for k in kotak) + 12

    kiri = max(0, kiri)
    atas = max(0, atas)
    kanan = min(im.width, kanan)
    bawah = min(im.height, bawah)

    print(f"  area potong: x {kiri}..{kanan}  y {atas}..{bawah}")
    potong = im.crop((kiri, atas, kanan, bawah))
    potong = potong.resize((potong.width * 4, potong.height * 4),
                           Image.LANCZOS)
    keluar = AKAR / "_legenda.png"
    potong.save(keluar)
    print(f"  disimpan: {keluar}  ({potong.width}x{potong.height})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
