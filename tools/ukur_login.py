"""
Ukur tata letak halaman login pada beberapa ukuran jendela.

Tujuan: menemukan bagian yang terpotong, keluar dari jendela, atau tidak
mendapat ruang cukup. Pengukuran dilakukan dengan membaca geometri widget
yang benar-benar dirender, bukan dengan melihat gambar.

Cara pakai:
    python tools/ukur_login.py
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "src"))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QLineEdit  # noqa: E402
from akuntansi_id.ui import theme  # noqa: E402
from akuntansi_id.ui.login import LoginPage  # noqa: E402

# Ukuran jendela yang diuji: dari yang paling kecil sampai paling besar.
UKURAN = [
    (920, 620),      # ukuran minimum jendela menurut main_window
    (1024, 700),
    (1120, 720),     # ukuran bawaan jendela
    (1366, 768),     # layar paling umum
    (1920, 1080),    # layar besar
]


def tunggu(app, detik=0.35):
    akhir = time.time() + detik
    while time.time() < akhir:
        app.processEvents()
        time.sleep(0.01)


def periksa(halaman, lebar, tinggi):
    """Kembalikan daftar masalah tata letak pada ukuran tertentu."""
    masalah = []

    # 1. Widget yang melewati batas jendela
    for anak in halaman.findChildren(QLabel) + halaman.findChildren(QPushButton) \
            + halaman.findChildren(QLineEdit):
        if not anak.isVisible():
            continue
        kiri = anak.mapTo(halaman, anak.rect().topLeft()).x()
        atas = anak.mapTo(halaman, anak.rect().topLeft()).y()
        kanan = kiri + anak.width()
        bawah = atas + anak.height()

        if kanan > lebar + 2:
            masalah.append(
                f"keluar kanan {kanan - lebar}px: "
                f"{anak.__class__.__name__} \"{_teks(anak)[:34]}\"")
        if bawah > tinggi + 2:
            masalah.append(
                f"keluar bawah {bawah - tinggi}px: "
                f"{anak.__class__.__name__} \"{_teks(anak)[:34]}\"")
        if kiri < -2:
            masalah.append(
                f"keluar kiri {abs(kiri)}px: "
                f"{anak.__class__.__name__} \"{_teks(anak)[:34]}\"")

    # 2. Teks yang terpotong pada label satu baris.
    # Label ber-wordWrap memang membungkus ke baris berikutnya, jadi lebar
    # teksnya boleh melebihi lebar label. Yang perlu diperiksa hanyalah
    # label yang tidak membungkus, karena label seperti itu wajib cukup
    # lebar untuk memuat teksnya dalam satu baris.
    for lbl in halaman.findChildren(QLabel):
        if not lbl.isVisible() or lbl.wordWrap():
            continue
        teks = lbl.text()
        if not teks.strip() or "<" in teks:
            continue
        # Label yang teksnya memang berisi baris baru diukur per baris.
        for baris in teks.split("\n"):
            if not baris.strip():
                continue
            butuh = lbl.fontMetrics().horizontalAdvance(baris)
            if lbl.width() + 3 < butuh:
                masalah.append(
                    f"teks terpotong {butuh - lbl.width()}px: \"{baris[:38]}\"")

    return masalah


def _teks(widget) -> str:
    for nama in ("text", "placeholderText"):
        if hasattr(widget, nama):
            nilai = getattr(widget, nama)()
            if nilai:
                return nilai
    return ""


def main() -> int:
    app = QApplication.instance() or QApplication([])
    app.setStyleSheet(theme.stylesheet())

    print("=" * 78)
    print("  UKUR HALAMAN LOGIN PADA BERBAGAI UKURAN JENDELA")
    print("=" * 78)
    print()

    total_masalah = 0

    for lebar, tinggi in UKURAN:
        halaman = LoginPage()
        halaman.resize(lebar, tinggi)
        halaman.show()
        tunggu(app)

        masalah = periksa(halaman, lebar, tinggi)

        # Ukur juga lebar isian formulir.
        form_lebar = 0
        for anak in halaman.findChildren(QLineEdit):
            if anak.isVisible():
                form_lebar = max(form_lebar, anak.width())
                break

        tanda = "OK" if not masalah else f"{len(masalah)} MASALAH"
        print(f"  {lebar}x{tinggi}  lebar isian: {form_lebar}px  [{tanda}]")

        for m in masalah[:6]:
            print(f"      {m}")
        if len(masalah) > 6:
            print(f"      ... dan {len(masalah) - 6} lagi")

        total_masalah += len(masalah)
        halaman.close()
        halaman.deleteLater()
        tunggu(app, 0.1)

    print()
    print("=" * 78)
    if total_masalah == 0:
        print("  HASIL: tidak ada masalah tata letak pada semua ukuran")
    else:
        print(f"  HASIL: {total_masalah} masalah ditemukan")
    print("=" * 78)

    return 0 if total_masalah == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
