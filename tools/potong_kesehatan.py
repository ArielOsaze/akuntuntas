"""
Ukur posisi panel Kesehatan Keuangan pada gambar tangkapan layar.

Pemotongan sebelumnya salah area sehingga hasilnya tidak menggambarkan
panel yang dimaksud. Skrip ini mengukur posisi panel di Qt, lalu mengubah
koordinat itu ke koordinat gambar dan memotongnya dengan tepat.
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

_LIS = LIS.Lisensi(
    kunci="P", paket="enterprise", pemilik="X",
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

    # Ambil tangkapan dan hitung faktor skala antara ukuran Qt dan gambar
    gambar = j.grab()
    faktor_x = gambar.width() / j.width()
    faktor_y = gambar.height() / j.height()
    print(f"  jendela Qt   : {j.width()}x{j.height()}")
    print(f"  gambar       : {gambar.width()}x{gambar.height()}")
    print(f"  faktor skala : {faktor_x:.3f} x {faktor_y:.3f}")
    print()

    # Cari label judul dan badge
    target = {"Kesehatan Keuangan": None, "Kinerja Bulanan 2026": None}
    for lbl in halaman.findChildren(QLabel):
        teks = lbl.text().strip()
        if teks in target:
            kiri = lbl.mapTo(j, lbl.rect().topLeft()).x()
            atas = lbl.mapTo(j, lbl.rect().topLeft()).y()
            target[teks] = (kiri, atas, lbl.width(), lbl.height())
        if teks.startswith("GRADE"):
            print(f"  badge ditemukan: '{teks}'")
            print(f"    lebar label : {lbl.width()}px")
            print(f"    butuh teks  : {lbl.fontMetrics().horizontalAdvance(teks)}px")
            print(f"    status      : "
                  f"{'CUKUP' if lbl.width() >= lbl.fontMetrics().horizontalAdvance(teks) else 'TERPOTONG'}")

    print()
    for nama, pos in target.items():
        if pos:
            x, y, w, h = pos
            print(f"  '{nama}'")
            print(f"     posisi Qt : x={x} y={y} w={w} h={h}")
            print(f"     di gambar : x={int(x*faktor_x)} y={int(y*faktor_y)}")

    # Simpan potongan panel kesehatan memakai koordinat yang benar
    from PIL import Image
    jalur = AKAR / "store_gambar" / "01-dashboard.png"
    if jalur.exists() and target.get("Kesehatan Keuangan"):
        im = Image.open(jalur)
        x, y, w, h = target["Kesehatan Keuangan"]
        kiri = max(0, int((x - 30) * faktor_x))
        atas = max(0, int((y - 20) * faktor_y))
        kanan = min(im.width, int((x + w + 480) * faktor_x))
        bawah = min(im.height, int((y + 300) * faktor_y))
        print()
        print(f"  potong panel: x {kiri}..{kanan}  y {atas}..{bawah}")
        potong = im.crop((kiri, atas, kanan, bawah))
        potong = potong.resize((potong.width * 2, potong.height * 2),
                               Image.LANCZOS)
        keluar = AKAR / "_kesehatan.png"
        potong.save(keluar)
        print(f"  disimpan: {keluar}  ({potong.width}x{potong.height})")

    j.close()
    app.processEvents()
    return 0


if __name__ == "__main__":
    sys.exit(main())
