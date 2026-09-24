"""
Periksa kontras seluruh teks pada halaman masuk.

Ambang yang dipakai adalah WCAG AA: 4.5 banding 1 untuk teks biasa dan
3.0 banding 1 untuk teks berukuran besar.

Cara mengukurnya: seluruh halaman digambar ke citra lebih dulu, lalu untuk
setiap widget teks diambil potongan citra pada posisinya. Dari potongan itu
warna latar ditentukan sebagai warna yang paling banyak muncul, dan warna
huruf sebagai warna yang paling berbeda dari latar. Pendekatan ini dipakai
karena stylesheet Qt sering mengatur warna tanpa memperbarui palette, dan
sebagian panel menggambar latarnya sendiri lewat paintEvent, sehingga
membaca palette menghasilkan angka yang salah.

Cara pakai:
    python tools/periksa_kontras_login.py
"""
from __future__ import annotations

import os
import sys
from collections import Counter
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "src"))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QColor, QPixmap  # noqa: E402
from PySide6.QtWidgets import (  # noqa: E402
    QApplication, QLabel, QPushButton, QCheckBox,
)

MIN_BIASA = 4.5
MIN_BESAR = 3.0


def terang(warna: QColor) -> float:
    """Kecerahan relatif menurut rumus WCAG."""
    saluran = []
    for nilai in (warna.redF(), warna.greenF(), warna.blueF()):
        saluran.append(nilai / 12.92 if nilai <= 0.03928
                       else ((nilai + 0.055) / 1.055) ** 2.4)
    return (0.2126 * saluran[0] + 0.7152 * saluran[1]
            + 0.0722 * saluran[2])


def kontras(a: QColor, b: QColor) -> float:
    """Nisbah kontras antara dua warna."""
    ta, tb = terang(a), terang(b)
    lebih, kurang = (ta, tb) if ta >= tb else (tb, ta)
    return (lebih + 0.05) / (kurang + 0.05)


def warna_dari_potongan(citra, kiri, atas, lebar, tinggi):
    """
    Tentukan warna latar dan warna huruf dari potongan citra.

    Warna latar adalah warna yang paling banyak muncul. Warna huruf adalah
    warna yang paling jauh kontrasnya dari latar. Bila keduanya sama,
    berarti potongan itu tidak memuat huruf yang terbaca.
    """
    hitungan = Counter()
    for y in range(atas, min(atas + tinggi, citra.height())):
        for x in range(kiri, min(kiri + lebar, citra.width())):
            warna = citra.pixelColor(x, y)
            if warna.alpha() < 200:
                continue
            # Warna dikumpulkan apa adanya, tanpa pembulatan, supaya
            # warnanya dapat dilaporkan dengan tepat.
            hitungan[warna.name()] += 1

    if not hitungan:
        return None, None

    latar_nama, _ = hitungan.most_common(1)[0]
    latar = QColor(latar_nama)

    # Warna huruf: warna yang paling berbeda dari latar. Warna yang hanya
    # muncul sangat sedikit dilewati karena biasanya berasal dari tepi
    # huruf yang halus, bukan dari warna huruf sebenarnya.
    ambang_muncul = max(2, sum(hitungan.values()) // 200)
    terbaik, terbaik_rasio = None, 0.0
    for nama, jumlah in hitungan.items():
        if jumlah < ambang_muncul:
            continue
        warna = QColor(nama)
        rasio = kontras(warna, latar)
        if rasio > terbaik_rasio:
            terbaik, terbaik_rasio = warna, rasio

    # Bila tidak ada warna yang cukup banyak muncul, ulangi tanpa batas
    # jumlah kemunculan supaya tetap ada hasil.
    if terbaik is None:
        for nama in hitungan:
            warna = QColor(nama)
            rasio = kontras(warna, latar)
            if rasio > terbaik_rasio:
                terbaik, terbaik_rasio = warna, rasio

    return terbaik, latar


def main() -> int:
    app = QApplication.instance() or QApplication([])

    from akuntansi_id.ui import theme
    from akuntansi_id.ui.login import LoginPage
    app.setStyleSheet(theme.stylesheet())

    halaman = LoginPage()
    halaman.resize(1120, 720)
    halaman.show()
    for _ in range(80):
        app.processEvents()

    # Gambar seluruh halaman sekali.
    gambar = QPixmap(halaman.size())
    gambar.fill(QColor("#FFFFFF"))
    halaman.render(gambar)
    citra = gambar.toImage()

    print("=" * 84)
    print("  PERIKSA KONTRAS TEKS HALAMAN MASUK (ambang WCAG AA)")
    print("=" * 84)
    print()

    calon = (halaman.findChildren(QLabel) + halaman.findChildren(QPushButton)
             + halaman.findChildren(QCheckBox))

    diperiksa = 0
    dilewati = 0
    gagal = []

    for wdg in calon:
        if not wdg.isVisible() or not hasattr(wdg, "text"):
            continue
        teks = wdg.text()
        if not teks.strip() or "<" in teks:
            continue

        # Posisi widget pada halaman.
        titik = wdg.mapTo(halaman, wdg.rect().topLeft())
        kiri, atas = titik.x(), titik.y()
        lebar, tinggi = wdg.width(), wdg.height()
        if lebar < 8 or tinggi < 8:
            continue

        warna_teks, latar = warna_dari_potongan(
            citra, kiri, atas, lebar, tinggi)

        if warna_teks is None:
            dilewati += 1
            continue

        rasio = kontras(warna_teks, latar)

        # Ukuran huruf menentukan ambang yang dipakai.
        metrik = wdg.fontMetrics()
        tinggi_huruf = metrik.height()
        tebal = wdg.font().bold()
        ambang = MIN_BESAR if (tinggi_huruf >= 24
                               or (tebal and tinggi_huruf >= 19)) \
            else MIN_BIASA

        diperiksa += 1
        if rasio + 0.01 < ambang:
            gagal.append((teks[:46], tinggi_huruf, tebal, rasio, ambang,
                          warna_teks.name(), latar.name()))

    print(f"  teks diperiksa : {diperiksa}")
    print(f"  dilewati       : {dilewati} (tidak memuat huruf terbaca)")
    print()

    if not gagal:
        print("  SELURUH teks memenuhi ambang kontras WCAG AA.")
        print("=" * 84)
        return 0

    print(f"  {len(gagal)} teks di bawah ambang:")
    print()
    for teks, tinggi_huruf, tebal, rasio, ambang, warna, latar in gagal:
        print(f"    \"{teks}\"")
        print(f"      tinggi huruf {tinggi_huruf}px"
              f"{', tebal' if tebal else ''}"
              f"  kontras {rasio:.2f} (perlu {ambang})")
        print(f"      huruf {warna} di atas latar {latar}")
    print()
    print("=" * 84)
    print("  HASIL: perbaiki warna agar memenuhi ambang")
    print("=" * 84)
    return 1


if __name__ == "__main__":
    sys.exit(main())
