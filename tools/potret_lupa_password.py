"""
Potret dialog Lupa Password untuk pemeriksaan tampilan.

Cara pakai:
    python tools/potret_lupa_password.py
"""
from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "src"))

FOLDER = Path(tempfile.mkdtemp(prefix="akuntuntas_lupa_"))
os.environ["LOCALAPPDATA"] = str(FOLDER)

from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication.instance() or QApplication([])

from akuntansi_id import db  # noqa: E402
from akuntansi_id.core import security as sec  # noqa: E402
from akuntansi_id.ui import theme  # noqa: E402

app.setStyle("Fusion")
theme.palet_terang(app)
app.setStyleSheet(theme.stylesheet())
db.init_db()
sec.ensure_default_admin()

from akuntansi_id.ui.login import LoginPage  # noqa: E402


def tunggu(detik=0.5):
    akhir = time.time() + detik
    while time.time() < akhir:
        app.processEvents()
        time.sleep(0.01)


halaman = LoginPage()
halaman.resize(1366, 768)
halaman.show()
tunggu()

# Buka dialog lupa password tanpa menunggu exec() selesai
from PySide6.QtCore import QTimer  # noqa: E402
from PySide6.QtWidgets import QDialog  # noqa: E402

_asli_exec = QDialog.exec
QDialog.exec = lambda self: self.show()   # tampilkan saja, jangan blokir

QTimer.singleShot(300, halaman._lupa_password)
tunggu(1.2)

hasil = AKAR / "_potret_lupa"
hasil.mkdir(exist_ok=True)

# Cari dialog yang sedang terbuka
dialog = None
for w in app.topLevelWidgets():
    if isinstance(w, QDialog) and w.isVisible():
        dialog = w
        break

if dialog is None:
    print("  Dialog tidak ditemukan")
    sys.exit(1)

berkas = hasil / "lupa_password.png"
dialog.grab().save(str(berkas))
print(f"  ukuran dialog : {dialog.width()}x{dialog.height()}")
print(f"  tersimpan     : {berkas}")

# Tutup dialog
for w in app.topLevelWidgets():
    if isinstance(w, QDialog):
        w.accept()
tunggu(0.3)
