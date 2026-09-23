"""Ukur kontras teks pada jendela login dan dialog-dialog aplikasi.

Cara pakai:
    python tools/periksa_kontras_dialog.py

Halaman utama sudah diperiksa tools/periksa_kontras.py. Pemeriksaan ini
menjangkau jendela yang muncul di luar halaman: login, ganti password,
wajib ganti password, dan dialog formulir yang dibuka tombol halaman.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
os.environ["AKUNTANSIID_DATA"] = str(AKAR / "_contoh")
sys.path.insert(0, str(AKAR / "src"))
sys.path.insert(0, str(AKAR / "tools"))

from PySide6.QtWidgets import QApplication  # noqa: E402

from akuntansi_id import config  # noqa: E402
from akuntansi_id.core import security as sec  # noqa: E402
from akuntansi_id.ui import theme  # noqa: E402
from akuntansi_id.ui.login import (BrandPanel, GantiPasswordWajib,  # noqa: E402
                                   LoginPage, PilihMode)
from periksa_kontras import periksa  # noqa: E402

# Mode offscreen tidak menggambar latar widget dengan benar sehingga warna
# latar terbaca sama dengan warna teks. Modul periksa_kontras memasang mode
# itu saat diimpor, jadi nilainya dibersihkan setelah impor selesai.
os.environ.pop("QT_QPA_PLATFORM", None)


def bersihkan(app, jumlah=6):
    """Beri kesempatan Qt menyelesaikan render sebelum jendela diukur.

    Jendela yang baru ditampilkan belum selesai menggambar latarnya pada
    beberapa putaran pertama, sehingga pengukuran warna bisa membaca latar
    yang keliru. Jeda pendek memastikan render sudah selesai.
    """
    import time
    for _ in range(max(jumlah, 30)):
        app.processEvents()
        time.sleep(0.01)


def main() -> int:
    app = QApplication.instance() or QApplication([])
    app.setStyleSheet(theme.stylesheet())

    masalah = []

    # --- layar login dan panel mereknya ---
    for nama, kelas, ukuran in (("login", LoginPage, (620, 660)),
                                ("merek", BrandPanel, (430, 660))):
        try:
            layar = kelas()
            layar.resize(*ukuran)
            layar.show()
            bersihkan(app, 10)
            for t in periksa(layar, layar):
                masalah.append((nama, *t))
                print(f"  [SAMAR] {nama:12s} '{t[0]:48s}' teks={t[1]} "
                      f"latar={t[2]} rasio={t[3]} (min {t[4]})")
            layar.close()
        except Exception as e:
            print(f"  [ERROR] {nama}: {type(e).__name__}: {e}")

    # --- layar wajib ganti password & pilih mode ---
    hasil = sec.login("admin", config.DEFAULT_ADMIN_PASSWORD)
    if hasil.ok:
        for nama, kelas in (("ganti-password", GantiPasswordWajib),
                            ("pilih-mode", PilihMode)):
            try:
                layar = kelas(hasil)
                layar.resize(620, 640)
                layar.show()
                bersihkan(app, 10)
                for t in periksa(layar, layar):
                    masalah.append((nama, *t))
                    print(f"  [SAMAR] {nama:12s} '{t[0]:48s}' teks={t[1]} "
                          f"latar={t[2]} rasio={t[3]} (min {t[4]})")
                layar.close()
            except Exception as e:
                print(f"  [ERROR] {nama}: {type(e).__name__}: {e}")

    print()
    if masalah:
        print(f"HASIL: {len(masalah)} teks pada jendela/dialog kontrasnya kurang")
        return 1
    print("HASIL: seluruh teks jendela & dialog memenuhi kontras WCAG AA")
    return 0


if __name__ == "__main__":
    sys.exit(main())
