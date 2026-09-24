"""
Uji halaman masuk pada layar sempit dengan mensimulasikan ukuran layar.

Masalah yang dicari: jendela masuk meminta lebar 1120 piksel. Bila layar
lebih sempit, jendela melewati tepi layar dan bagian kanannya tidak dapat
dijangkau pengguna. Skrip ini menjalankan aplikasi dengan ukuran layar
buatan yang lebih kecil untuk memastikan jendela tetap muat.

Cara pakai:
    python tools/uji_jendela_sempit.py
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent

# Ukuran layar yang diuji, meniru layar sungguhan yang lazim dipakai:
#   1366x768  = layar laptop paling umum
#   1280x720  = layar laptop lama
#   1024x600  = netbook dan tablet Windows kecil
LAYAR = [(1366, 768), (1280, 720), (1024, 600)]

PROGRAM = r'''
import os, sys, time
sys.path.insert(0, {akar!r})

# Ukuran layar buatan: Qt membaca variabel ini sebelum jendela dibuat.
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication
from akuntansi_id.ui import theme

app = QApplication([])
app.setStyleSheet(theme.stylesheet())

layar = QGuiApplication.primaryScreen()
ruang = layar.availableGeometry()
print("    layar terdeteksi: {{}}x{{}}".format(ruang.width(), ruang.height()))

from akuntansi_id.ui.main_window import JendelaAplikasi
j = JendelaAplikasi()
j.show()
akhir = time.time() + 1.2
while time.time() < akhir:
    app.processEvents(); time.sleep(0.01)

print("    jendela masuk: {{}}x{{}}".format(j.width(), j.height()))
print("    minimum      : {{}}x{{}}".format(
    j.minimumWidth(), j.minimumHeight()))

masalah = []
if j.width() > ruang.width():
    masalah.append("jendela lebih lebar {{}}px dari layar".format(
        j.width() - ruang.width()))
if j.height() > ruang.height():
    masalah.append("jendela lebih tinggi {{}}px dari layar".format(
        j.height() - ruang.height()))
if j.minimumWidth() > ruang.width():
    masalah.append("lebar minimum melebihi layar")

print("    HASIL: " + ("OK" if not masalah else "; ".join(masalah)))
j.close()
'''


def main() -> int:
    print("=" * 78)
    print("  UJI JENDELA MASUK PADA LAYAR SEMPIT")
    print("=" * 78)
    print()

    total = 0
    for lebar, tinggi in LAYAR:
        print(f"  --- layar {lebar}x{tinggi} ---")

        lingkungan = dict(os.environ)
        # QT_QPA_PLATFORM=offscreen tidak memakai ukuran layar sungguhan,
        # jadi ukuran layar diatur lewat variabel khusus Qt.
        lingkungan["QT_QPA_PLATFORM"] = "offscreen"
        lingkungan["QT_OPENGL"] = "software"
        # Nilai ini dipakai Qt untuk ukuran layar virtual pada mode offscreen.
        lingkungan["QT_QPA_OFFSCREEN_SIZE"] = f"{lebar}x{tinggi}"

        kode = PROGRAM.format(akar=str(AKAR / "src"))
        hasil = subprocess.run(
            [sys.executable, "-c", kode],
            capture_output=True, text=True, env=lingkungan, timeout=300)

        keluaran = (hasil.stdout or "").strip()
        if keluaran:
            print(keluaran)
        if hasil.returncode != 0:
            baris = (hasil.stderr or "").strip().splitlines()
            print(f"    (gagal, kode {hasil.returncode})")
            if baris:
                print("    " + baris[-1])
            total += 1
        elif "OK" not in keluaran:
            total += 1
        print()

    print("=" * 78)
    if total == 0:
        print("  HASIL: jendela masuk muat pada seluruh ukuran layar")
    else:
        print(f"  HASIL: {total} ukuran layar bermasalah")
    print("=" * 78)

    return 0 if total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
