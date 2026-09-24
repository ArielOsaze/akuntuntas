"""
Uji apakah satu tanda & tunggal benar-benar hilang saat widget digambar.

Qt memperlakukan tanda & sebagai penanda pintasan papan tikus pada sebagian
jenis widget. Cara memastikan bukan dengan membaca properti text(), karena
properti itu mengembalikan teks mentah, melainkan dengan menggambar widget
ke citra lalu membandingkan hasilnya.

Caranya: gambar widget dengan teks apa adanya, lalu gambar lagi dengan
tanda & digandakan. Bila kedua citra sama persis, artinya tanda & tunggal
memang dihapus saat digambar, sehingga teks perlu memakai &&.

Cara pakai:
    python tools/uji_perilaku_amp.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "src"))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtGui import QAction, QPixmap  # noqa: E402
from PySide6.QtWidgets import (  # noqa: E402
    QApplication, QLabel, QPushButton, QTabWidget, QWidget, QCheckBox,
    QGroupBox, QRadioButton, QMenu, QLineEdit,
)

POLOS = "Pajak & SPT"
GANDa = "Pajak && SPT"


def gambar(widget, lebar=320, tinggi=48) -> bytes:
    """Gambar widget ke citra dan kembalikan isinya sebagai byte."""
    widget.resize(lebar, tinggi)
    piksel = QPixmap(lebar, tinggi)
    piksel.fill(Qt.transparent)
    widget.render(piksel)
    gambar_q = piksel.toImage()
    potongan = bytearray()
    for y in range(tinggi):
        for x in range(lebar):
            potongan.extend(gambar_q.pixelColor(x, y).getRgb())
    return bytes(potongan)


def buat(jenis: str, teks: str):
    """Buat widget sesuai jenisnya."""
    if jenis == "QLabel":
        return QLabel(teks)
    if jenis == "QLabel + buddy":
        lbl = QLabel(teks)
        lbl.setBuddy(QLineEdit())
        return lbl
    if jenis == "QPushButton":
        return QPushButton(teks)
    if jenis == "QCheckBox":
        return QCheckBox(teks)
    if jenis == "QRadioButton":
        return QRadioButton(teks)
    if jenis == "QGroupBox":
        return QGroupBox(teks)
    if jenis == "QMenu":
        return QMenu(teks)
    raise ValueError(jenis)


def main() -> int:
    QApplication.instance() or QApplication([])

    print("=" * 74)
    print("  APAKAH TANDA & TUNGGAL HILANG SAAT WIDGET DIGAMBAR?")
    print("=" * 74)
    print()

    jenis_uji = ["QLabel", "QLabel + buddy", "QPushButton", "QCheckBox",
                 "QRadioButton", "QGroupBox", "QMenu"]

    perlu_escape = []
    aman = []

    for jenis in jenis_uji:
        try:
            citra_polos = gambar(buat(jenis, POLOS))
            citra_ganda = gambar(buat(jenis, GANDa))
            sama = citra_polos == citra_ganda
        except Exception as galat:
            print(f"  {jenis:18s}: tidak dapat diuji ({galat})")
            continue

        if sama:
            perlu_escape.append(jenis)
            print(f"  {jenis:18s}: TANDA & HILANG, perlu &&")
        else:
            aman.append(jenis)
            print(f"  {jenis:18s}: aman, tanda & tetap tampil")

    # QAction dan tab diperiksa terpisah karena bukan QWidget biasa.
    print()
    print("  Diperiksa terpisah:")
    for jenis in ("QAction", "QTabWidget"):
        try:
            a1 = QAction(POLOS)
            a2 = QAction(GANDa)
            if jenis == "QAction":
                # QAction menyimpan teks mentah; yang menentukan adalah
                # lebar teks yang digambar oleh gaya Qt.
                from PySide6.QtWidgets import QApplication as A
                fm = A.fontMetrics()
                lebar_polos = fm.horizontalAdvance(a1.text())
                lebar_ganda = fm.horizontalAdvance(a2.text().replace("&&", "&"))
                sama = lebar_polos == lebar_ganda
            else:
                tw1 = QTabWidget()
                tw1.addTab(QWidget(), POLOS)
                tw2 = QTabWidget()
                tw2.addTab(QWidget(), GANDa)
                sama = tw1.tabText(0) == tw2.tabText(0)
        except Exception as galat:
            print(f"    {jenis:16s}: tidak dapat diuji ({galat})")
            continue
        if sama:
            perlu_escape.append(jenis)
            print(f"    {jenis:16s}: TANDA & HILANG, perlu &&")
        else:
            aman.append(jenis)
            print(f"    {jenis:16s}: aman")

    print()
    print("=" * 74)
    print(f"  perlu memakai && : {len(perlu_escape)} jenis")
    for j in perlu_escape:
        print(f"    - {j}")
    print()
    print(f"  aman apa adanya   : {len(aman)} jenis")
    for j in aman:
        print(f"    - {j}")
    print("=" * 74)

    return 0


if __name__ == "__main__":
    sys.exit(main())
