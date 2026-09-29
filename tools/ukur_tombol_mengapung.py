"""
Ukur jalur sempit pengganti menu samping.

Menu samping dapat disembunyikan supaya area isi bertambah lebar. Sebelumnya
tombol pengembalinya mengapung di atas area isi, sehingga menimpa menu bar
di atasnya dan judul halaman di bawahnya.

Alat ini memastikan tombol pengembali kini punya jalurnya sendiri: tidak
menimpa menu bar, tidak menutupi teks halaman, utuh di dalam jendela, dan
cukup besar untuk ditekan. Seluruh pengukuran diambil langsung dari Qt,
bukan dari potret, supaya angkanya pasti.

Cara pakai:
    python tools/ukur_tombol_mengapung.py
"""
from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "src"))

os.environ["LOCALAPPDATA"] = tempfile.mkdtemp(prefix="ukur_mengapung_")

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


def tunggu(detik=0.5):
    akhir = time.time() + detik
    while time.time() < akhir:
        app.processEvents()
        time.sleep(0.01)


def kotak_di_jendela(widget, jendela):
    """
    Kotak widget dalam koordinat jendela.

    Setiap widget mengembalikan geometry relatif terhadap induknya. Widget
    yang induknya berbeda tidak dapat dibandingkan langsung, jadi semuanya
    dipetakan lebih dahulu ke jendela. Tanpa pemetaan ini, tombol yang
    sebenarnya sudah benar akan terlihat menimpa menu bar.
    """
    titik = widget.mapTo(jendela, widget.rect().topLeft())
    return widget.rect().translated(titik)


def tumpang(a, b) -> bool:
    """Apakah dua kotak saling menimpa?"""
    return not (a.right() < b.left() or b.right() < a.left()
                or a.bottom() < b.top() or b.bottom() < a.top())


hasil = sec.login(sec.DEFAULT_ADMIN_USER if hasattr(sec, "DEFAULT_ADMIN_USER")
                  else "admin", "admin123")
if not hasil.ok:
    from akuntansi_id import config
    hasil = sec.login(config.DEFAULT_ADMIN_USER, config.DEFAULT_ADMIN_PASSWORD)
if not hasil.ok:
    print("  GAGAL tidak dapat masuk sebagai admin bawaan")
    sys.exit(1)

print("=" * 76)
print("  UKUR JALUR SEMPIT PENGGANTI MENU SAMPING")
print("=" * 76)

from PySide6.QtWidgets import QLabel  # noqa: E402

for lebar, tinggi in [(1500, 940), (1366, 768), (1180, 720), (1920, 1080)]:
    win = MainWindow(hasil)
    win.resize(lebar, tinggi)
    win.show()
    tunggu(1.2)

    lebar_isi_awal = win.stack.width()
    win._sembunyikan_sidebar()
    tunggu(0.6)

    print(f"\n  --- {lebar}x{tinggi} ---")

    if not win.rel_menu.isVisible():
        cek(f"jalur sempit tampil pada {lebar}x{tinggi}", False,
            "jalur tidak tampil")
        win.close()
        continue

    tombol = win.btn_menu_mengapung
    kotak_tombol = kotak_di_jendela(tombol, win)
    kotak_menu = kotak_di_jendela(win.menuBar(), win)
    kotak_rel = kotak_di_jendela(win.rel_menu, win)
    kotak_isi = kotak_di_jendela(win.stack, win)

    print(f"      jalur sempit     : x {kotak_rel.left()}..{kotak_rel.right()}"
          f", lebar {kotak_rel.width()}")
    print(f"      tombol           : x {kotak_tombol.left()}..{kotak_tombol.right()}"
          f", y {kotak_tombol.top()}..{kotak_tombol.bottom()}")
    print(f"      menu bar         : y {kotak_menu.top()}..{kotak_menu.bottom()}")
    print(f"      lebar area isi   : {lebar_isi_awal} -> {win.stack.width()}")

    # 1. Tombol tidak menimpa menu bar.
    cek(f"tombol tidak menimpa menu bar pada {lebar}x{tinggi}",
        not tumpang(kotak_tombol, kotak_menu),
        f"tombol y {kotak_tombol.top()}..{kotak_tombol.bottom()} "
        f"vs menu bar y {kotak_menu.top()}..{kotak_menu.bottom()}")

    # 2. Tombol utuh di dalam jendela.
    dalam = (kotak_tombol.left() >= 0 and kotak_tombol.top() >= 0
             and kotak_tombol.right() <= win.width()
             and kotak_tombol.bottom() <= win.height())
    cek(f"tombol utuh di dalam jendela pada {lebar}x{tinggi}", dalam,
        f"tombol {kotak_tombol} keluar dari {win.width()}x{win.height()}")

    # 3. Tombol tidak menutupi teks halaman mana pun.
    tertutup = []
    for label in win.findChildren(QLabel):
        if not label.isVisible() or not label.text().strip():
            continue
        kotak_label = kotak_di_jendela(label, win)
        if tumpang(kotak_tombol, kotak_label):
            tertutup.append(label.text().strip()[:40])
    cek(f"tombol tidak menutupi teks halaman pada {lebar}x{tinggi}",
        not tertutup, f"menutupi: {tertutup[:3]}")

    # 4. Tombol cukup besar untuk ditekan.
    cukup = kotak_tombol.width() >= 32 and kotak_tombol.height() >= 32
    cek(f"tombol cukup besar untuk ditekan pada {lebar}x{tinggi}", cukup,
        f"ukuran {kotak_tombol.width()}x{kotak_tombol.height()}")

    # 5. Tombol berada di dalam jalur sempitnya.
    cek(f"tombol berada di dalam jalur sempit pada {lebar}x{tinggi}",
        kotak_rel.contains(kotak_tombol),
        f"tombol {kotak_tombol} vs jalur {kotak_rel}")

    # 6. Area isi bertambah lebar, tetapi tidak selebar penuh karena
    #    jalur sempit tetap memakai sedikit ruang.
    bertambah = win.stack.width() - lebar_isi_awal
    cek(f"area isi bertambah lebar pada {lebar}x{tinggi}", bertambah > 0,
        f"bertambah {bertambah}")
    cek(f"pertambahan sama dengan lebar menu dikurangi jalur sempit "
        f"pada {lebar}x{tinggi}",
        abs(bertambah - (win.sidebar.LEBAR - MainWindow.REL_LEBAR)) <= 2,
        f"bertambah {bertambah}, seharusnya "
        f"{win.sidebar.LEBAR} - {MainWindow.REL_LEBAR}")

    # 7. Menampilkan kembali mengembalikan tata letak semula.
    win._tampilkan_sidebar()
    tunggu(0.5)
    cek(f"area isi kembali seperti semula pada {lebar}x{tinggi}",
        win.stack.width() == lebar_isi_awal,
        f"{win.stack.width()} vs {lebar_isi_awal}")
    cek(f"jalur sempit tersembunyi lagi pada {lebar}x{tinggi}",
        not win.rel_menu.isVisible())

    win.close()
    tunggu(0.3)

print()
print("=" * 76)
print(f"  HASIL: {LULUS} LULUS, {GAGAL} GAGAL")
print("=" * 76)
sys.exit(1 if GAGAL else 0)
