"""
Ukur apakah judul peraturan tampil utuh di daftar Salinan Regulasi Resmi.

Judul peraturan panjang, misalnya "PMK 168/2023 - Petunjuk PPh 21 (Tarif
Efektif / TER)". Bila daftar terlalu sempit atau tingginya tidak
menyesuaikan, judul terpotong dengan titik-titik dan pengguna tidak dapat
membedakan dua peraturan yang mirip.

Judul ditampilkan sebagai label di dalam tiap baris, bukan sebagai teks
baris daftar, sehingga yang diperiksa adalah labelnya langsung. Setiap
label diperiksa satu per satu: seluruh teksnya harus terbaca, tanpa
pemotongan dan tanpa keluar dari kotaknya.

Cara pakai:
    python tools/ukur_daftar_regulasi.py
"""
from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "src"))

os.environ["LOCALAPPDATA"] = tempfile.mkdtemp(prefix="ukur_regulasi_")

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

for i in range(h.daftar.count()):
    if "Regulasi" in h.daftar.item(i).text():
        h.daftar.setCurrentRow(i)
        break
tunggu(2.5)

print("=" * 76)
print("  UKUR DAFTAR PERATURAN")
print("=" * 76)

from PySide6.QtWidgets import QLabel, QListWidget, QTextEdit  # noqa: E402
from PySide6.QtGui import QFontMetrics  # noqa: E402

halaman = h.stack.currentWidget()
if halaman is None:
    print("  GAGAL halaman topik tidak tampil")
    sys.exit(1)

daftar = None
for d in halaman.findChildren(QListWidget):
    if d.count() >= 15:
        daftar = d
        break

if daftar is None:
    print("  GAGAL daftar peraturan tidak ditemukan")
    sys.exit(1)

print(f"\n  jumlah baris        : {daftar.count()}")
print(f"  lebar daftar        : {daftar.width()} piksel")

# Setiap baris berisi label. Seluruh teks label harus terbaca: tidak
# terpotong dengan titik-titik, dan tidak melebihi lebar kotaknya.
terpotong = []
diperiksa = 0
for i in range(daftar.count()):
    item = daftar.item(i)
    wadah = daftar.itemWidget(item)
    if wadah is None:
        continue

    for lbl in wadah.findChildren(QLabel):
        teks = lbl.text()
        if not teks.strip():
            continue
        diperiksa += 1

        fm = QFontMetrics(lbl.font())
        lebar_tersedia = lbl.width()
        lebar_teks = fm.horizontalAdvance(teks)

        # Teks harus muat, atau dibungkus menjadi beberapa baris.
        if lebar_teks <= lebar_tersedia:
            continue
        if not lbl.wordWrap():
            terpotong.append((teks, lebar_teks, lebar_tersedia,
                              "tidak membungkus"))
            continue

        # Hitung berapa baris yang dibutuhkan.
        baris = 1
        lebar_baris = 0
        for kata in teks.split():
            wk = fm.horizontalAdvance(kata + " ")
            if lebar_baris + wk > lebar_tersedia:
                baris += 1
                lebar_baris = wk
            else:
                lebar_baris += wk

        tinggi_dibutuhkan = baris * fm.height()
        if tinggi_dibutuhkan > lbl.height():
            terpotong.append((teks, lebar_teks, lebar_tersedia,
                              f"butuh {baris} baris ({tinggi_dibutuhkan}px), "
                              f"tinggi label {lbl.height()}px"))

print(f"  label diperiksa     : {diperiksa}")
print()

if terpotong:
    print(f"  {len(terpotong)} label TERPOTONG:")
    for teks, butuh, ada, sebab in terpotong:
        print(f"    - {teks}")
        print(f"      {sebab}")
else:
    print("  Seluruh judul tampil utuh.")

print()
cek("seluruh judul peraturan tampil utuh", not terpotong,
    f"{len(terpotong)} label terpotong")
cek("setiap baris punya label judul", diperiksa >= daftar.count(),
    f"hanya {diperiksa} label untuk {daftar.count()} baris")

# Kotak teks isi peraturan
teks_isi = None
for t in halaman.findChildren(QTextEdit):
    if t.isReadOnly() and len(t.toPlainText()) > 5000:
        teks_isi = t
        break

if teks_isi is not None:
    print(f"\n  kotak teks    : {teks_isi.width()}x{teks_isi.height()} piksel")
    print(f"  panjang teks  : {len(teks_isi.toPlainText()):,} huruf"
          .replace(",", "."))

    from PySide6.QtWidgets import QTextEdit as _TE  # noqa: E402
    bungkus = teks_isi.lineWrapMode() != _TE.NoWrap
    print(f"  pembungkusan  : {'AKTIF' if bungkus else 'MENGIKUTI BERKAS'}")

    if bungkus:
        fm_isi = QFontMetrics(teks_isi.font())
        lebar_huruf = fm_isi.averageCharWidth()
        huruf_per_baris = teks_isi.width() // max(1, lebar_huruf)
        print(f"  sekitar {huruf_per_baris} huruf per baris")
        cek("lebar baris nyaman dibaca (maksimal 110 huruf)",
            huruf_per_baris <= 110,
            f"{huruf_per_baris} huruf per baris, mata sulit menemukan awal "
            f"baris berikutnya")
    else:
        teks = teks_isi.toPlainText()
        baris_terpanjang = max((len(b) for b in teks.split("\n")), default=0)
        print(f"  baris terpanjang berkas: {baris_terpanjang} huruf")
        cek("berkas peraturan sudah dibungkus pada lebar nyaman",
            baris_terpanjang <= 130,
            f"baris terpanjang {baris_terpanjang} huruf, melebihi 130")
else:
    cek("kotak teks isi peraturan ditemukan", False, "tidak ditemukan")

print()
print("=" * 76)
print(f"  HASIL: {LULUS} LULUS, {GAGAL} GAGAL")
print("=" * 76)
sys.exit(1 if GAGAL else 0)
