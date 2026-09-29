"""
Potret halaman Salinan Regulasi Resmi.

Halaman ini berada di Panduan & Aturan, dipilih dari daftar isi di kiri.
Alat ini membukanya langsung supaya tampilannya dapat diperiksa dengan
mata.

Cara pakai:
    python tools/potret_regulasi.py
"""
from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "src"))

os.environ["LOCALAPPDATA"] = tempfile.mkdtemp(prefix="potret_regulasi_")

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

from akuntansi_id.ui.pages.pengaturan import BantuanPage  # noqa: E402

HASIL = AKAR / "_potret_pengaturan"
HASIL.mkdir(exist_ok=True)


def tunggu(detik=0.8):
    akhir = time.time() + detik
    while time.time() < akhir:
        app.processEvents()
        time.sleep(0.01)


class Ctx:
    company = None
    beginner = False
    user = None

    def muat_perusahaan(self):
        pass

    def daftar_perusahaan(self):
        return []


h = BantuanPage(Ctx())
h.resize(1400, 900)
h.show()
tunggu(1.4)

# Pilih Salinan Regulasi Resmi dari daftar isi.
dipilih = False
for i in range(h.daftar.count()):
    if "Regulasi" in h.daftar.item(i).text():
        h.daftar.setCurrentRow(i)
        dipilih = True
        break

if not dipilih:
    print("  GAGAL item Salinan Regulasi Resmi tidak ada di daftar isi")
    print("  daftar berisi:")
    for i in range(h.daftar.count()):
        print(f"    - {h.daftar.item(i).text()}")
    sys.exit(1)

# Beri waktu halaman regulasi dimuat dan berkas pertama dibaca.
tunggu(2.5)

berkas = HASIL / "regulasi.png"
h.grab().save(str(berkas))
print(f"  [OK] regulasi  {berkas.stat().st_size // 1024} KB")
print(f"  tersimpan di: {berkas}")
