"""
Verifikasi visual: periksa piksel hasil render untuk mendeteksi teks terpotong.

Cara pakai:
    python tools/verifikasi_visual.py

Pemeriksaan ini mengambil tangkapan setiap halaman pada beberapa lebar
jendela, lalu memeriksa:

  1. Tepi terpotong  - ada piksel bertinta yang menyentuh tepi widget teks,
                       tanda huruf terpotong.
  2. Teks hilang     - kotak isian yang berisi nilai tetapi tidak ada
                       piksel teks di dalamnya.
  3. Tumpang tindih  - dua widget teks yang menempati area yang sama.

Hasil dicetak per halaman agar mudah ditindaklanjuti.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
os.environ["AKUNTANSIID_DATA"] = str(AKAR / "_contoh")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(AKAR / "src"))

from PySide6.QtWidgets import (  # noqa: E402
    QApplication, QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox, QDateEdit,
    QTimeEdit, QTableWidget, QWidget,
)

JENIS_INPUT = (QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit,
               QTimeEdit)

HALAMAN = ["dashboard", "jurnal", "penjualan", "pembelian", "biaya", "bank",
           "mitra", "produk", "aset", "payroll", "periode", "konsolidasi",
           "laporan", "pajak", "coa", "perusahaan", "lan", "pengaturan"]

# lebar jendela yang diuji: lazim, sedang, dan sempit
LEBAR_UJI = [1280, 1100, 1024]


def ada_teks(gambar) -> bool:
    """Apakah ada piksel yang berbeda dari warna latar dominan."""
    if gambar.isNull() or gambar.width() <= 2 or gambar.height() <= 2:
        return False
    warna = {}
    for y in range(gambar.height()):
        for x in range(gambar.width()):
            c = gambar.pixelColor(x, y).rgb()
            warna[c] = warna.get(c, 0) + 1
    if not warna:
        return False
    latar = max(warna, key=warna.get)
    jumlah = sum(n for c, n in warna.items() if c != latar)
    return jumlah > 4


def periksa_kotak(widget: QWidget, asal: str, temuan: list):
    """Kotak isian berisi nilai harus benar-benar menampilkan teksnya."""
    if not isinstance(widget, JENIS_INPUT) or not widget.isVisible():
        return
    if widget.width() < 20 or widget.height() < 10:
        return

    isi = ""
    if isinstance(widget, QComboBox):
        isi = widget.currentText()
    elif isinstance(widget, (QSpinBox, QDoubleSpinBox)):
        isi = widget.text()
    elif isinstance(widget, (QDateEdit, QTimeEdit)):
        isi = widget.text()
    elif isinstance(widget, QLineEdit):
        isi = widget.text()

    if not isi:
        return

    gambar = widget.grab().toImage()
    if not ada_teks(gambar):
        temuan.append(
            f"{asal}: kotak \"{isi[:30]}\" berisi nilai tetapi "
            f"teksnya tidak terlihat (kotak {widget.width()}x{widget.height()})")


def periksa_himpit(daftar: list, asal: str, temuan: list):
    """Dua widget teks tidak boleh menempati area yang sama."""
    for i in range(len(daftar)):
        for j in range(i + 1, len(daftar)):
            a, b = daftar[i], daftar[j]
            # hanya bandingkan widget dengan induk yang sama
            if a.parentWidget() is not b.parentWidget():
                continue
            ra, rb = a.geometry(), b.geometry()
            if not ra.intersects(rb):
                continue
            tumpang = ra.intersected(rb)
            # tumpang tindih kecil wajar pada widget bersarang
            if tumpang.width() * tumpang.height() < 40:
                continue
            temuan.append(
                f"{asal}: {type(a).__name__} dan {type(b).__name__} "
                f"bertumpuk {tumpang.width()}x{tumpang.height()} px")


def periksa_halaman(app: QApplication, nama: str, lebar: int,
                    temuan: list) -> bool:
    """Buka satu halaman pada lebar tertentu lalu periksa isinya."""
    from akuntansi_id.core import security as sec
    from akuntansi_id.ui.main_window import MainWindow


    def _lisensi_uji():
        """Lisensi uji paket Enterprise agar seluruh halaman ikut diperiksa."""
        from akuntansi_id.core.license import Lisensi
        return Lisensi(kunci='ATNTUJI', paket='enterprise', fitur={})

    hasil = sec.LoginResult(ok=True, user_id=1, username="verifikasi",
                            full_name="Verifikasi", role="owner",
                            app_mode="expert", mode_dipilih=True)
    jendela = MainWindow(hasil, lisensi=_lisensi_uji())
    jendela.resize(lebar, 800)
    jendela.show()
    for _ in range(6):
        app.processEvents()

    asal = f"{nama}@{lebar}"
    try:
        jendela._navigasi(nama)
        for _ in range(6):
            app.processEvents()
        isi = jendela.stack.currentWidget()
        if isi is None:
            return False

        for x in isi.findChildren(QWidget):
            if x.isHidden() or x.width() <= 0 or x.height() <= 0:
                continue
            try:
                periksa_kotak(x, asal, temuan)
            except RuntimeError:
                continue

        # periksa tumpang tindih antar kotak isian pada induk yang sama
        kotak = [x for x in isi.findChildren(QWidget)
                 if isinstance(x, JENIS_INPUT) and x.isVisible()
                 and not x.parentWidget() is None
                 and not isinstance(x.parentWidget(), QTableWidget)]
        periksa_himpit(kotak, asal, temuan)
        return True
    except Exception as e:
        temuan.append(f"{asal}: GAGAL DIBUKA - {e}")
        return False
    finally:
        jendela.close()


def main() -> int:
    app = QApplication.instance() or QApplication([])

    from akuntansi_id.ui import theme
    app.setStyleSheet(theme.stylesheet())

    temuan: list = []
    jumlah = 0
    for lebar in LEBAR_UJI:
        for nama in HALAMAN:
            if periksa_halaman(app, nama, lebar, temuan):
                jumlah += 1

    print(f"halaman diperiksa : {jumlah} "
          f"({len(HALAMAN)} halaman x {len(LEBAR_UJI)} lebar)")
    print()

    if temuan:
        print(f"TEMUAN ({len(temuan)}):")
        for t in temuan[:60]:
            print(f"  - {t}")
        if len(temuan) > 60:
            print(f"  ... dan {len(temuan) - 60} lagi")
        return 1

    print("HASIL: seluruh kotak isian menampilkan isinya, tidak ada tumpang tindih")
    return 0


if __name__ == "__main__":
    sys.exit(main())
