"""
Pisahkan mana yang mahal: pembungkusan teks atau tinggi-dari-lebar.

Keduanya berkaitan tetapi bukan hal yang sama. Pembungkusan teks membuat
label memecah kalimat menjadi beberapa baris. Tinggi-dari-lebar membuat
susunan halaman menanyakan tinggi label setiap kali ukuran berubah. Berkas
ini mematikan keduanya secara terpisah untuk mengetahui mana yang menelan
waktu, sekaligus memeriksa apakah teksnya masih terbaca utuh.
"""

import os
import sys
import time
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "src"))
os.environ.setdefault("AKUNTANSIID_DATA", str(AKAR / "_contoh"))

from PySide6.QtWidgets import QApplication, QLabel      # noqa: E402

HALAMAN = ("audit", "payroll", "produk", "laporan")


def waktu(app, siapkan, aksi, ulangan: int = 7) -> float:
    hasil = []
    for _ in range(ulangan):
        siapkan()
        for _ in range(3):
            app.processEvents()
        t0 = time.perf_counter()
        aksi()
        for _ in range(4):
            app.processEvents()
        hasil.append((time.perf_counter() - t0) * 1000)
    hasil.sort()
    return hasil[len(hasil) // 2]


def main() -> int:
    app = QApplication([])
    app.setStyle("Fusion")

    from akuntansi_id.ui import theme
    theme.palet_terang(app)
    app.setStyleSheet(theme.stylesheet())

    from akuntansi_id.core import security as sec
    from akuntansi_id.ui.main_window import MainWindow

    jendela = MainWindow(sec.login("admin", "admin123"))
    jendela.resize(1400, 900)
    jendela.show()
    for _ in range(20):
        app.processEvents()

    for kode in jendela.halaman:
        jendela._navigasi(kode)
        for _ in range(3):
            app.processEvents()

    def ke_dashboard():
        jendela.stack.setCurrentWidget(jendela.halaman["dashboard"])

    def ganti(k):
        jendela.stack.setCurrentWidget(jendela.halaman[k])

    def baris(nama: str):
        hasil = {k: waktu(app, ke_dashboard, lambda k=k: ganti(k))
                 for k in HALAMAN}
        rata = sum(hasil.values()) / len(hasil)
        print(f"  {nama:34s} " +
              " ".join(f"{hasil[k]:5.0f}" for k in HALAMAN) +
              f"   rata {rata:6.1f} ms")

    print("=" * 78)
    print("MANA YANG MAHAL: PEMBUNGKUSAN TEKS ATAU TINGGI-DARI-LEBAR")
    print("=" * 78)
    print()
    print(f"  {'keadaan':34s} " +
          " ".join(f"{k[:5]:>5s}" for k in HALAMAN))
    print(f"  {'-' * 34} " + " ".join("-" * 5 for _ in HALAMAN))

    baris("apa adanya")

    # ---------------------------------------------------- catat keadaan awal
    label = []
    for k in jendela.halaman:
        label.extend(jendela.halaman[k].findChildren(QLabel))

    berbalut = [l for l in label if l.wordWrap()]

    # ---------------------------------------------------- tinggi-dari-lebar saja
    simpan_hfw = []
    for lbl in berbalut:
        kebijakan = lbl.sizePolicy()
        if kebijakan.hasHeightForWidth():
            simpan_hfw.append((lbl, kebijakan))
            kebijakan.setHeightForWidth(False)
            lbl.setSizePolicy(kebijakan)
    for _ in range(10):
        app.processEvents()
    baris(f"HFW mati, bungkus hidup ({len(simpan_hfw)})")

    # kembalikan
    for lbl, kebijakan in simpan_hfw:
        kebijakan.setHeightForWidth(True)
        lbl.setSizePolicy(kebijakan)
    for _ in range(10):
        app.processEvents()

    # ---------------------------------------------------- pembungkusan saja
    simpan_bungkus = list(berbalut)
    for lbl in simpan_bungkus:
        lbl.setWordWrap(False)
    for _ in range(10):
        app.processEvents()
    baris(f"bungkus mati, HFW hidup ({len(simpan_bungkus)})")

    for lbl in simpan_bungkus:
        lbl.setWordWrap(True)
    for _ in range(10):
        app.processEvents()

    # ---------------------------------------------------- keduanya mati
    for lbl in berbalut:
        lbl.setWordWrap(False)
        kebijakan = lbl.sizePolicy()
        kebijakan.setHeightForWidth(False)
        lbl.setSizePolicy(kebijakan)
    for _ in range(10):
        app.processEvents()
    baris("keduanya mati")

    print()
    print("  Memeriksa teks terpotong pada keadaan awal...")
    print()

    # kembalikan ke semula
    for lbl in berbalut:
        lbl.setWordWrap(True)
        kebijakan = lbl.sizePolicy()
        kebijakan.setHeightForWidth(True)
        lbl.setSizePolicy(kebijakan)
    for _ in range(10):
        app.processEvents()

    # ---------------------------------------------------- periksa terpotong
    terpotong = 0
    for lbl in berbalut:
        if not lbl.isVisible() or lbl.width() <= 0:
            continue
        perlu = lbl.heightForWidth(lbl.width())
        if perlu > lbl.height() + 2:
            terpotong += 1
    print(f"    label berbalut diperiksa : {len(berbalut)}")
    print(f"    teks terpotong           : {terpotong}")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
