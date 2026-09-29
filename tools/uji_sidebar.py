"""
Uji sembunyikan/tampilkan menu samping pada beberapa ukuran jendela.

Memastikan menu dapat disembunyikan, jalur sempit pengganti muncul, dan
area isi benar-benar bertambah lebar setelah menu disembunyikan.

Saat menu disembunyikan, sebagian ruangnya dipakai jalur sempit berisi
tombol pengembali. Karena itu area isi bertambah selebar menu dikurangi
lebar jalur sempit, bukan selebar menu penuh.

Cara pakai:
    python tools/uji_sidebar.py
"""
from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "src"))

os.environ["LOCALAPPDATA"] = tempfile.mkdtemp(prefix="uji_sidebar_")

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

from akuntansi_id.ui.main_window import MainWindow  # noqa: E402

HASIL = AKAR / "_potret_sidebar"
HASIL.mkdir(exist_ok=True)

LULUS = 0
GAGAL = 0


def cek(nama: str, benar: bool, keterangan: str = ""):
    global LULUS, GAGAL
    if benar:
        LULUS += 1
        print(f"  [LULUS] {nama}")
    else:
        GAGAL += 1
        print(f"  [GAGAL] {nama}" + (f" - {keterangan}" if keterangan else ""))


def tunggu(detik=0.6):
    akhir = time.time() + detik
    while time.time() < akhir:
        app.processEvents()
        time.sleep(0.01)


hasil = sec.login(sec.DEFAULT_ADMIN_USER if hasattr(sec, "DEFAULT_ADMIN_USER")
                  else "admin", "admin123")
if not hasil.ok:
    from akuntansi_id import config
    hasil = sec.login(config.DEFAULT_ADMIN_USER, config.DEFAULT_ADMIN_PASSWORD)

print("=" * 74)
print("  UJI SEMBUNYIKAN / TAMPILKAN MENU SAMPING")
print("=" * 74)

for lebar, tinggi in ((1366, 768), (1920, 1080)):
    print()
    print(f"[Jendela {lebar}x{tinggi}]")

    w = MainWindow(hasil)
    w.resize(lebar, tinggi)
    w.show()
    tunggu(1.2)

    # ---------------------------------------------------------- keadaan awal
    cek("Menu samping tampil pada keadaan awal",
        w.sidebar.isVisible())

    lebar_isi_awal = w.stack.width()
    print(f"    lebar area isi sebelum disembunyikan: {lebar_isi_awal}")

    # -------------------------------------------------------- sembunyikan
    w._sembunyikan_sidebar()
    tunggu(0.5)

    cek("Menu samping tersembunyi", not w.sidebar.isVisible())
    cek("Tombol pengembali muncul", w.btn_menu_mengapung.isVisible())
    cek("Jalur sempit pengganti tampil", w.rel_menu.isVisible())

    lebar_isi_baru = w.stack.width()
    print(f"    lebar area isi setelah disembunyikan: {lebar_isi_baru}")
    cek("Area isi bertambah lebar",
        lebar_isi_baru > lebar_isi_awal,
        f"{lebar_isi_awal} -> {lebar_isi_baru}")
    # Sebagian ruang menu dipakai jalur sempit, jadi pertambahannya
    # adalah lebar menu dikurangi lebar jalur sempit itu.
    harapan = w.sidebar.LEBAR - MainWindow.REL_LEBAR
    cek("Pertambahan selebar menu dikurangi jalur sempit",
        abs((lebar_isi_baru - lebar_isi_awal) - harapan) <= 2,
        f"bertambah {lebar_isi_baru - lebar_isi_awal}, "
        f"seharusnya {w.sidebar.LEBAR} - {MainWindow.REL_LEBAR} = {harapan}")

    berkas = HASIL / f"tersembunyi_{lebar}.png"
    w.grab().save(str(berkas))
    print(f"    potret: {berkas.name}")

    # ------------------------------------------------------- tampilkan lagi
    w._tampilkan_sidebar()
    tunggu(0.5)

    cek("Menu samping tampil kembali", w.sidebar.isVisible())
    cek("Tombol pengembali disembunyikan",
        not w.btn_menu_mengapung.isVisible())
    cek("Jalur sempit ikut tersembunyi", not w.rel_menu.isVisible())
    cek("Lebar area isi kembali seperti semula",
        abs(w.stack.width() - lebar_isi_awal) <= 2,
        f"{w.stack.width()} vs {lebar_isi_awal}")

    berkas2 = HASIL / f"tampil_{lebar}.png"
    w.grab().save(str(berkas2))

    # ---------------------------------------------------- pilihan tersimpan
    w._sembunyikan_sidebar()
    tunggu(0.3)
    cek("Pilihan tersimpan di pengaturan",
        db.q1("SELECT value FROM settings WHERE key=?",
              ("sidebar_tersembunyi",)) is not None)

    # Bangun ulang jendela: pilihan harus terterap otomatis
    w.close()
    tunggu(0.3)
    w2 = MainWindow(hasil)
    w2.resize(lebar, tinggi)
    w2.show()
    tunggu(1.2)
    cek("Pilihan tersembunyi terterap saat dibuka lagi",
        not w2.sidebar.isVisible(),
        "menu tampil padahal sebelumnya disembunyikan")
    w2._tampilkan_sidebar()
    w2.close()
    tunggu(0.3)

print()
print("=" * 74)
if GAGAL:
    print(f"  HASIL: {LULUS} LULUS, {GAGAL} GAGAL")
else:
    print(f"  HASIL: {LULUS} LULUS, 0 GAGAL")
print("=" * 74)
sys.exit(1 if GAGAL else 0)
