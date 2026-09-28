"""
Diagnosa penyebab formulir login menyusut dan kotak petunjuk meluber.

Mengukur sizeHint dan minimumSizeHint setiap elemen supaya penyebabnya
diketahui pasti, bukan diduga duga.

Cara pakai:
    python tools/diagnosa_login.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "src"))

from PySide6.QtWidgets import QApplication  # noqa: E402
from akuntansi_id.ui import theme  # noqa: E402
from akuntansi_id.ui.login import LoginPage  # noqa: E402


def tunggu(app, detik=0.4):
    akhir = time.time() + detik
    while time.time() < akhir:
        app.processEvents()
        time.sleep(0.01)


app = QApplication.instance() or QApplication([])
app.setStyle("Fusion")
theme.palet_terang(app)
app.setStyleSheet(theme.stylesheet())

halaman = LoginPage()
halaman.resize(1366, 768)
halaman.show()
tunggu(app)

form = halaman.inp_user.parent()
petunjuk = halaman.petunjuk

print("=" * 78)
print("  DIAGNOSA FORMULIR LOGIN (jendela 1366x768)")
print("=" * 78)

for nama, w in (
        ("halaman", halaman),
        ("form", form),
        ("petunjuk (kotak abu)", petunjuk),
        ("inp_user", halaman.inp_user),
        ("btn_login", halaman.btn_login),
):
    print(f"\n  {nama}")
    print(f"    lebar sekarang   : {w.width()}")
    print(f"    sizeHint         : {w.sizeHint().width()}")
    print(f"    minimumSizeHint  : {w.minimumSizeHint().width()}")
    print(f"    minimumWidth     : {w.minimumWidth()}")
    print(f"    maximumWidth     : {w.maximumWidth()}")
    print(f"    sizePolicy       : {w.sizePolicy().horizontalPolicy()}")

# Label di dalam kotak petunjuk
print("\n  --- label di dalam kotak petunjuk ---")
for anak in petunjuk.findChildren(type(halaman.inp_user).__mro__[1]):
    pass

from PySide6.QtWidgets import QLabel  # noqa: E402
for lbl in petunjuk.findChildren(QLabel):
    print(f"\n    {lbl.__class__.__name__}")
    print(f"      teks (potong)  : {lbl.text()[:60]!r}")
    print(f"      lebar sekarang : {lbl.width()}")
    print(f"      sizeHint       : {lbl.sizeHint().width()}")
    print(f"      minimumSizeHint: {lbl.minimumSizeHint().width()}")
    print(f"      wordWrap       : {lbl.wordWrap()}")
    print(f"      minimumWidth   : {lbl.minimumWidth()}")

halaman.close()
