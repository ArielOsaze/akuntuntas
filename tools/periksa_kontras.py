"""Ukur kontras teks terhadap latar sebenarnya sesuai standar WCAG.

Cara pakai:
    python tools/periksa_kontras.py

Halaman dirender lebih dulu, lalu latar diukur dari piksel nyata di sekitar
teks. Cara ini tidak bergantung pada palet Qt atau penelusuran stylesheet,
sehingga hasilnya sama dengan yang dilihat pengguna. Teks wajib mencapai
rasio 4,5:1 (teks normal) atau 3:1 (teks besar) agar selalu terbaca.
"""

from __future__ import annotations

import os
import sys
from collections import Counter
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
os.environ["AKUNTANSIID_DATA"] = str(AKAR / "_contoh")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(AKAR / "src"))

from PySide6.QtGui import QColor  # noqa: E402
from PySide6.QtWidgets import (QApplication, QCheckBox, QGroupBox,  # noqa: E402
                               QLabel, QPushButton, QRadioButton, QTabBar)

from akuntansi_id import config, services  # noqa: E402
from akuntansi_id.core import security as sec  # noqa: E402
from akuntansi_id.ui import theme  # noqa: E402
from akuntansi_id.ui.main_window import MainWindow, Sidebar  # noqa: E402

# Lisensi uji dipakai agar seluruh halaman ikut diperiksa, termasuk
# halaman yang hanya tersedia pada paket Enterprise.
from akuntansi_id.core.license import Lisensi as _LisensiUji
_LISENSI_UJI = _LisensiUji(kunci='ATNTUJI', paket='enterprise', fitur={})


HALAMAN = [k for _, daftar in Sidebar.MENU for k, _, _ in daftar]
MIN_NORMAL = 4.5
MIN_BESAR = 3.0
TOLERANSI = 0.05


def luminance(warna: QColor) -> float:
    """Luminansi relatif menurut WCAG 2.1."""
    kanal = []
    for c in (warna.redF(), warna.greenF(), warna.blueF()):
        kanal.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * kanal[0] + 0.7152 * kanal[1] + 0.0722 * kanal[2]


def rasio(warna_teks: QColor, warna_latar: QColor) -> float:
    a, b = luminance(warna_teks), luminance(warna_latar)
    return (max(a, b) + 0.05) / (min(a, b) + 0.05)


def warna_teks(widget) -> QColor:
    """
    Warna teks dari gaya inline, gaya tema, atau palet widget.

    Bila widget sedang dalam keadaan menyala (tombol :checked), warna yang
    benar benar tampil adalah warna pada keadaan itu, bukan warna keadaan
    normal. Tanpa memperhitungkannya, tombol yang menyala akan dinilai
    memakai warna teks keadaan normal.
    """
    gaya = widget.styleSheet()
    if gaya:
        menyala = False
        try:
            menyala = bool(widget.isChecked())
        except AttributeError:
            menyala = False

        if menyala:
            # Cari blok :checked pada gaya inline.
            for blok in gaya.split("}"):
                if ":checked" not in blok:
                    continue
                # Keadaan :checked:hover lebih khusus, jadi diperiksa lebih
                # dulu bila penunjuk sedang di atasnya; tanpa penunjuk,
                # blok :checked biasa yang dipakai.
                warna = _dari_gaya(blok.split("{")[-1], "color")
                if warna is not None:
                    return warna

        warna = _dari_gaya(gaya, "color")
        if warna is not None:
            return warna

    nama = widget.objectName()
    if nama:
        for bagian in theme.stylesheet().split("}"):
            if f"#{nama}" in bagian:
                warna = _dari_gaya(bagian, "color")
                if warna is not None:
                    return warna
    return widget.palette().color(widget.foregroundRole())


def _dari_gaya(gaya: str, properti: str) -> QColor:
    if not gaya:
        return None
    for bagian in gaya.split(";"):
        if ":" not in bagian:
            continue
        nama, nilai = bagian.split(":", 1)
        if nama.strip().lstrip("{").strip() != properti:
            continue
        nilai = nilai.strip().split()[0] if nilai.strip() else ""
        if not nilai or nilai.startswith("transparent"):
            return None
        warna = QColor(nilai)
        if warna.isValid():
            return warna
    return None


def warna_latar(bitmap, widget) -> QColor:
    """Warna latar dominan di dalam kotak widget, diukur dari piksel nyata.

    Teks menempati sebagian kecil area, sehingga warna yang paling banyak
    muncul di kotak tersebut adalah latarnya. Pengukuran dilakukan pada
    render jendela supaya latar dari induk (kartu, panel) ikut terhitung —
    widget yang digambar sendiri tidak menyertakan latar induknya.

    Widget yang tidak berada di dalam jendela yang terlihat dilewati:
    pikselnya tidak dapat diukur. Widget seperti itu diperiksa alat
    pemeriksa tata letak, bukan di sini.
    """
    wilayah = widget.visibleRegion()
    if wilayah.isEmpty():
        return None
    kotak = wilayah.boundingRect()
    if kotak.width() < 3 or kotak.height() < 3:
        return None

    # visibleRegion() sudah berupa koordinat widget. Untuk memetakannya ke
    # koordinat jendela, sudut kiri-atas wilayah dipetakan lewat widget itu
    # sendiri, bukan lewat kotak pembatasnya — sebagian widget berada di
    # dalam area gulir sehingga kedua cara itu memberi hasil berbeda.
    asal = widget.mapTo(widget.window(), kotak.topLeft())
    lebar, tinggi = kotak.width(), kotak.height()
    if asal.x() < 0 or asal.y() < 0:
        return None
    if asal.x() + lebar > bitmap.width() or asal.y() + tinggi > bitmap.height():
        return None

    contoh = Counter()
    langkah_x = max(1, lebar // 40)
    langkah_y = max(1, tinggi // 12)
    for x in range(asal.x() + 1, asal.x() + lebar, langkah_x):
        for y in range(asal.y() + 1, asal.y() + tinggi, langkah_y):
            warna = bitmap.pixelColor(x, y)
            if warna.alpha() < 200:
                continue
            contoh[warna.rgb()] += 1
    if not contoh:
        return None
    return QColor(contoh.most_common(1)[0][0])


def ukuran_dan_tebal(widget) -> tuple:
    ukuran = None
    for bagian in widget.styleSheet().split(";"):
        if ":" not in bagian:
            continue
        nama, nilai = bagian.split(":", 1)
        if nama.strip() == "font-size":
            try:
                ukuran = float(nilai.strip().replace("px", ""))
            except ValueError:
                pass
    if ukuran is None:
        ukuran = float(widget.font().pointSize())
    return ukuran, widget.font().bold()


def periksa(jendela, halaman) -> list:
    bitmap = jendela.grab().toImage()
    temuan = []
    kandidat = (halaman.findChildren(QLabel) + halaman.findChildren(QPushButton)
                + halaman.findChildren(QCheckBox) + halaman.findChildren(QRadioButton)
                + halaman.findChildren(QGroupBox) + halaman.findChildren(QTabBar))
    for widget in kandidat:
        if not widget.isVisible():
            continue
        if hasattr(widget, "text"):
            teks = widget.text()
        elif isinstance(widget, QTabBar):
            teks = " ".join(widget.tabText(i) for i in range(widget.count()))
        else:
            teks = ""
        if len(teks.strip()) <= 1:
            continue
        if "…" in teks and len(teks.strip()) <= 4:
            continue
        # label yang menampilkan pixmap ikon bukan teks; warnanya diatur
        # lewat parameter pixmap, bukan stylesheet
        if isinstance(widget, QLabel) and widget.pixmap() and not widget.pixmap().isNull():
            continue
        belakang = warna_latar(bitmap, widget)
        if belakang is None:
            continue
        depan = warna_teks(widget)
        r = rasio(depan, belakang)
        ukuran, tebal = ukuran_dan_tebal(widget)
        besar = ukuran >= 18 or (ukuran >= 14 and tebal)
        batas = MIN_BESAR if besar else MIN_NORMAL
        if r + TOLERANSI < batas:
            temuan.append((teks.strip()[:46], depan.name(), belakang.name(),
                           round(r, 2), batas))
    return temuan


def main() -> int:
    app = QApplication.instance() or QApplication([])
    app.setStyleSheet(theme.stylesheet())

    perusahaan = services.list_companies()
    if not perusahaan:
        print("Tidak ada perusahaan. Jalankan tools/buat_data_contoh.py dulu.")
        return 1
    cid = perusahaan[0]["id"]

    hasil = sec.login("admin", config.DEFAULT_ADMIN_PASSWORD)
    if not hasil.ok:
        print("Login gagal.")
        return 1

    jendela = MainWindow(hasil, lisensi=_LISENSI_UJI)
    jendela.ctx.company_id = cid
    jendela.ctx.company = services.get_company(cid)
    jendela.ctx.beginner = False
    jendela.resize(1440, 900)
    jendela.show()

    masalah = []
    for kode in HALAMAN:
        try:
            jendela._navigasi(kode)
            for _ in range(6):
                app.processEvents()
            halaman = jendela.halaman.get(kode)
            if halaman is None:
                continue
            for t in periksa(jendela, halaman):
                masalah.append((kode, *t))
                print(f"  [SAMAR] {kode:12s} '{t[0]:48s}' "
                      f"teks={t[1]} latar={t[2]} rasio={t[3]} (min {t[4]})")
        except Exception as e:
            print(f"  [ERROR] {kode}: {type(e).__name__}: {e}")

    print()
    if masalah:
        print(f"HASIL: {len(masalah)} teks kontrasnya di bawah standar")
        return 1
    print("HASIL: seluruh teks memenuhi kontras WCAG AA")
    return 0


if __name__ == "__main__":
    sys.exit(main())
