"""
Uji halaman login pada layar kecil dengan penskalaan tampilan Windows.

Banyak pengguna Windows memakai penskalaan 125 persen atau 150 persen pada
layar kecil. Penskalaan itu memperbesar seluruh teks dan kotak, sehingga
tata letak yang muat pada 100 persen dapat terpotong pada 125 atau 150.

Skrip ini menjalankan aplikasi dengan variabel penskalaan Qt, lalu mengukur
apakah ada teks yang terpotong atau widget yang keluar jendela.

Cara pakai:
    python tools/uji_login_skala.py
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent

# Penskalaan yang diuji, mengikuti pilihan Windows:
#   1.0  = 100 persen
#   1.25 = 125 persen (umum pada layar 1366x768)
#   1.5  = 150 persen (umum pada layar 1920x1080 berukuran kecil)
SKALA = [1.0, 1.25, 1.5]

# Ukuran jendela yang diuji, dalam piksel logis.
UKURAN = [(920, 620), (1120, 720), (1366, 768)]

PROGRAM = r'''
import os, sys, time
sys.path.insert(0, {akar!r})
from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QLineEdit, QCheckBox
from akuntansi_id.ui import theme
from akuntansi_id.ui.login import LoginPage

app = QApplication([])
app.setStyleSheet(theme.stylesheet())

masalah_semua = 0
for lebar, tinggi in {ukuran!r}:
    h = LoginPage()
    h.resize(lebar, tinggi)
    h.show()
    akhir = time.time() + 0.7
    while time.time() < akhir:
        app.processEvents(); time.sleep(0.01)

    masalah = []
    calon = (h.findChildren(QLabel) + h.findChildren(QPushButton)
             + h.findChildren(QCheckBox))
    for wdg in calon:
        if not wdg.isVisible() or not hasattr(wdg, "text"):
            continue
        t = wdg.text()
        if not t.strip() or "<" in t:
            continue
        if hasattr(wdg, "wordWrap") and wdg.wordWrap():
            continue
        # Teks berbaris baru diukur per baris, sesuai cara Qt menggambarnya.
        for baris in t.split("\n"):
            if not baris.strip():
                continue
            butuh = wdg.fontMetrics().horizontalAdvance(baris)
            if wdg.width() + 4 < butuh:
                masalah.append("terpotong {{}}px: {{}}".format(
                    butuh - wdg.width(), baris[:34]))

    for wdg in list(calon) + list(h.findChildren(QLineEdit)):
        if not wdg.isVisible():
            continue
        p = wdg.mapTo(h, QPoint(0, 0))
        if p.x() + wdg.width() > h.width() + 2:
            masalah.append("keluar kanan: {{}}".format(wdg.__class__.__name__))
        if p.y() + wdg.height() > h.height() + 2:
            masalah.append("keluar bawah: {{}}".format(wdg.__class__.__name__))

    print("    {{}}x{{}} -> jendela {{}}x{{}}  [{{}}]".format(
        lebar, tinggi, h.width(), h.height(),
        "OK" if not masalah else "{{}} MASALAH".format(len(masalah))))
    for m in masalah[:5]:
        print("        " + m)
    masalah_semua += len(masalah)
    h.close(); h.deleteLater()

print("  TOTAL MASALAH:", masalah_semua)
'''


def main() -> int:
    print("=" * 78)
    print("  UJI HALAMAN LOGIN PADA BERBAGAI PENSKALAAN TAMPILAN")
    print("=" * 78)
    print()

    total_gagal = 0

    for skala in SKALA:
        persen = int(skala * 100)
        print(f"  --- penskalaan {persen} persen ---")

        lingkungan = dict(os.environ)
        # Qt memakai variabel ini untuk menskalakan seluruh antarmuka.
        lingkungan["QT_SCALE_FACTOR"] = str(skala)
        lingkungan["QT_ENABLE_HIGHDPI_SCALING"] = "1"

        kode = PROGRAM.format(akar=str(AKAR / "src"), ukuran=UKURAN)

        hasil = subprocess.run(
            [sys.executable, "-c", kode],
            capture_output=True, text=True, env=lingkungan, timeout=300)

        keluaran = hasil.stdout.strip()
        if keluaran:
            print(keluaran)
        if hasil.returncode != 0:
            print(f"    (proses gagal, kode {hasil.returncode})")
            if hasil.stderr:
                print("    " + hasil.stderr.strip().splitlines()[-1])
            total_gagal += 1
        print()

    print("=" * 78)
    if total_gagal == 0:
        print("  HASIL: seluruh ukuran lulus pada semua penskalaan")
    else:
        print(f"  HASIL: {total_gagal} penskalaan bermasalah")
    print("=" * 78)

    return 0 if total_gagal == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
