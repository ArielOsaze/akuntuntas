"""
Potret tab Pengaturan untuk pemeriksaan tampilan.

Cara pakai:
    python tools/potret_pengaturan.py
"""
from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "src"))

os.environ["LOCALAPPDATA"] = tempfile.mkdtemp(prefix="potret_pengaturan_")

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

HASIL = AKAR / "_potret_pengaturan"
HASIL.mkdir(exist_ok=True)


def tunggu(detik=0.7):
    akhir = time.time() + detik
    while time.time() < akhir:
        app.processEvents()
        time.sleep(0.01)


# Kelas ctx tiruan sederhana supaya halaman dapat dibentuk tanpa login penuh.
class Ctx:
    company = None
    beginner = False
    user = None

    def muat_perusahaan(self):
        pass

    def daftar_perusahaan(self):
        return []


from akuntansi_id.ui.pages.pengaturan import PengaturanPage  # noqa: E402

h = PengaturanPage(Ctx())
h.resize(1400, 900)
h.show()
tunggu(1.0)

# Tab Penyimpanan Data (indeks 3)
h.tabs.setCurrentIndex(3)
tunggu(0.9)
berkas = HASIL / "penyimpanan_data.png"
h.grab().save(str(berkas))
print(f"  [OK] penyimpanan_data  {berkas.stat().st_size // 1024} KB")

# Tab Lisensi & Keamanan (indeks 5)
h.tabs.setCurrentIndex(5)
tunggu(0.9)
berkas2 = HASIL / "lisensi_keamanan.png"
h.grab().save(str(berkas2))
print(f"  [OK] lisensi_keamanan  {berkas2.stat().st_size // 1024} KB")

# Tab Panduan & Aturan, lalu buka Salinan Regulasi Resmi dari daftar isi.
from PySide6.QtWidgets import QListWidget  # noqa: E402

h.tabs.setCurrentIndex(4)
tunggu(0.9)
for daftar in h.findChildren(QListWidget):
    for i in range(daftar.count()):
        if "Regulasi" in daftar.item(i).text():
            daftar.setCurrentRow(i)
            tunggu(1.6)
            berkas3 = HASIL / "regulasi.png"
            h.grab().save(str(berkas3))
            print(f"  [OK] regulasi          {berkas3.stat().st_size // 1024} KB")
            break

print(f"\n  tersimpan di: {HASIL}")
