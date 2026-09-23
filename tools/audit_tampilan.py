"""
Audit tampilan menyeluruh: pastikan seluruh teks tampil utuh dan terbaca.

Cara pakai:
    python tools/audit_tampilan.py

Pemeriksaan ini membuka setiap halaman dan setiap dialog, lalu mengukur teks
yang BENAR-BENAR dirender pada setiap widget, bukan sekadar ukuran saran Qt.
Ukuran saran sering menyesatkan: header tabel misalnya melaporkan butuh 63 px
padahal teksnya hanya perlu 24 px, sehingga menimbulkan laporan palsu.

Yang diperiksa:

  1. Teks label terpotong     - lebar teks melebihi lebar label tanpa elipsis
                                atau pembungkusan kata.
  2. Teks tombol terpotong    - teks tombol tidak muat di dalam tombolnya.
  3. Isi kotak pilihan sempit - pilihan terpanjang tidak muat di kotak.
  4. Judul tab terpotong      - judul tab tidak muat pada lebar tabnya.
  5. Kotak isian di tabel     - tinggi kotak kurang sehingga angka yang
                                diketik tidak terlihat.
  6. Widget keluar batas      - widget melewati tepi induknya.

Temuan dicetak sebagai daftar agar mudah ditindaklanjuti.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
os.environ["AKUNTANSIID_DATA"] = str(AKAR / "_contoh")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(AKAR / "src"))

from PySide6.QtGui import QFontMetrics  # noqa: E402
from PySide6.QtWidgets import (  # noqa: E402
    QAbstractButton, QApplication, QComboBox, QDateEdit,
    QDoubleSpinBox, QLabel, QLineEdit, QScrollArea, QSpinBox, QTableWidget,
    QTabBar, QTimeEdit, QWidget,
)

JENIS_INPUT = (QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit,
               QTimeEdit)

HALAMAN = ["dashboard", "analisis", "pencarian", "jurnal", "penjualan",
           "pembelian", "biaya", "bank", "mitra", "produk", "aset", "payroll",
           "dimensi", "periode", "konsolidasi", "laporan", "pajak", "checklist",
           "pengguna", "audit", "recycle", "impor", "coa", "perusahaan", "lan",
           "pengaturan", "bantuan"]

# ruang yang dipakai bingkai, jarak dalam, dan ikon pada tombol
PADDING_TOMBOL = 26
# ruang yang dipakai tombol panah pada kotak pilihan
PADDING_KOTAK = 44


def semua_anak(widget: QWidget):
    """Semua turunan widget, termasuk yang bersarang."""
    for anak in widget.findChildren(QWidget):
        yield anak


def di_dalam(widget: QWidget, jenis) -> bool:
    """Apakah widget berada di dalam induk berjenis tertentu."""
    induk = widget.parent()
    while induk is not None:
        if isinstance(induk, jenis):
            return True
        induk = induk.parent()
    return False


def lebar_teks(widget, teks: str) -> int:
    """Lebar teks bila dirender dengan font widget."""
    return QFontMetrics(widget.font()).horizontalAdvance(teks)


def periksa_teks(x: QWidget, asal: str, temuan: list):
    """Periksa apakah teks widget muat di dalamnya."""
    # label yang membungkus kata tetap terbaca walau sempit
    if isinstance(x, QLabel):
        if x.wordWrap():
            return
        teks = x.text()
        if not teks or "<" in teks:
            return
        perlu = lebar_teks(x, teks)
        if perlu > x.width() + 2:
            temuan.append(
                f"{asal}: label \"{teks[:48]}\" perlu {perlu} px, "
                f"ruang {x.width()} px")

    # tombol: teks harus muat bersama bingkai dan ikon
    elif isinstance(x, QAbstractButton):
        teks = x.text()
        if not teks:
            return
        # Ukuran teks dihitung dari gaya tombol yang benar-benar dipakai.
        # Tombol bergaya ghost atau tombol ikon memakai padding jauh lebih
        # kecil daripada tombol biasa, jadi jaraknya tidak sama.
        nama_gaya = x.objectName()
        gaya = x.styleSheet()
        if nama_gaya == "Ghost" or "padding: 0" in gaya or "border: none" in gaya:
            jarak = 10
        else:
            jarak = PADDING_TOMBOL
        perlu = lebar_teks(x, teks) + jarak
        if perlu > x.width() + 2:
            temuan.append(
                f"{asal}: tombol \"{teks[:40]}\" perlu {perlu} px, "
                f"ruang {x.width()} px")

    # kotak pilihan: pilihan terpanjang harus muat
    elif isinstance(x, QComboBox):
        if x.count() == 0:
            return
        teks = max((x.itemText(i) for i in range(x.count())), key=len)
        perlu = lebar_teks(x, teks) + PADDING_KOTAK
        if perlu > x.width() + 2:
            temuan.append(
                f"{asal}: kotak pilihan \"{teks[:40]}\" perlu {perlu} px, "
                f"ruang {x.width()} px")

    # tab: judul tab harus muat
    elif isinstance(x, QTabBar):
        for i in range(x.count()):
            teks = x.tabText(i)
            perlu = lebar_teks(x, teks) + 24
            if perlu > x.tabRect(i).width() + 2:
                temuan.append(
                    f"{asal}: judul tab \"{teks[:40]}\" perlu {perlu} px, "
                    f"ruang {x.tabRect(i).width()} px")


def periksa_kotak_tabel(x: QWidget, asal: str, temuan: list):
    """Kotak isian di dalam tabel harus cukup tinggi agar isinya terlihat."""
    if not isinstance(x, JENIS_INPUT):
        return
    if not di_dalam(x, QTableWidget) or not x.isVisible():
        return
    perlu = x.sizeHint().height()
    if x.height() < perlu:
        temuan.append(
            f"{asal}: kotak isian di dalam tabel hanya {x.height()} px, "
            f"butuh {perlu} px")


def periksa_batas(x: QWidget, asal: str, temuan: list):
    """Widget tidak boleh melewati tepi induknya."""
    induk = x.parentWidget()
    if induk is None or not x.isVisible() or not induk.isVisible():
        return
    # induk yang belum selesai ditata (tinggi atau lebar nol) belum bisa
    # dijadikan patokan batas
    if induk.width() <= 0 or induk.height() <= 0:
        return
    # isi area gulir dan tabel memang lebih panjang dari tampilannya
    if di_dalam(x, QScrollArea) or isinstance(induk, QTableWidget):
        return
    if induk.layout() is None:
        return
    x1, y1 = x.mapTo(induk, x.rect().topLeft()).toTuple()
    x2, y2 = x.mapTo(induk, x.rect().bottomRight()).toTuple()
    if x1 < -3 or y1 < -3 or x2 > induk.width() + 3 or y2 > induk.height() + 3:
        temuan.append(
            f"{asal}: {type(x).__name__} keluar batas induk "
            f"({x1},{y1})-({x2},{y2}) di dalam {induk.width()}x{induk.height()}")


def periksa_widget(akar: QWidget, asal: str, temuan: list):
    """Periksa seluruh widget di bawah `akar`."""
    for x in semua_anak(akar):
        # hanya widget yang benar-benar tampil di layar yang diperiksa;
        # isi kalender popup misalnya belum tampil sampai pengguna membukanya
        if not x.isVisible() or x.width() <= 0 or x.height() <= 0:
            continue
        try:
            periksa_teks(x, asal, temuan)
            periksa_kotak_tabel(x, asal, temuan)
            periksa_batas(x, asal, temuan)
        except RuntimeError:
            # widget sudah dihapus di tengah pemeriksaan
            continue


def periksa_halaman(app: QApplication, temuan: list) -> int:
    """Buka setiap halaman lalu periksa isinya."""
    from akuntansi_id.core import security as sec
    from akuntansi_id.ui.main_window import MainWindow


    def _lisensi_uji():
        """Lisensi uji paket Enterprise agar seluruh halaman ikut diperiksa."""
        from akuntansi_id.core.license import Lisensi
        return Lisensi(kunci='ATNTUJI', paket='enterprise', fitur={})

    jumlah = 0
    hasil = sec.LoginResult(ok=True, user_id=1, username="audit",
                            full_name="Audit Tampilan", role="owner",
                            app_mode="expert", mode_dipilih=True)
    jendela = MainWindow(hasil, lisensi=_lisensi_uji())
    jendela.resize(1280, 800)
    jendela.show()
    for _ in range(8):
        app.processEvents()

    for nama in HALAMAN:
        try:
            jendela._navigasi(nama)
            for _ in range(6):
                app.processEvents()
            isi = jendela.stack.currentWidget()
            if isi is None:
                continue
            jumlah += 1
            periksa_widget(isi, f"halaman:{nama}", temuan)
        except Exception as e:
            temuan.append(f"halaman:{nama}: GAGAL DIBUKA - {e}")

    jendela.close()
    return jumlah


def periksa_dialog(app: QApplication, temuan: list) -> int:
    """Buka dialog-dialog utama lalu periksa isinya."""
    from akuntansi_id.ui.pages import coa_page

    jumlah = 0

    class Ctx:
        company_id = 1
        tahun = 2026
        beginner = False
        user_id = 1
        username = "audit"

    daftar = [
        ("DialogSaldoAwal", lambda: coa_page.DialogSaldoAwal(Ctx())),
        ("DialogAkun", lambda: coa_page.DialogAkun(Ctx())),
    ]

    for nama, buat in daftar:
        try:
            d = buat()
            d.resize(980, 700)
            d.show()
            for _ in range(8):
                app.processEvents()
            jumlah += 1
            periksa_widget(d, f"dialog:{nama}", temuan)
            d.close()
        except Exception as e:
            temuan.append(f"dialog:{nama}: GAGAL DIBUKA - {e}")

    return jumlah


def main() -> int:
    app = QApplication.instance() or QApplication([])

    from akuntansi_id.ui import theme
    app.setStyleSheet(theme.stylesheet())

    temuan: list = []
    h = periksa_halaman(app, temuan)
    d = periksa_dialog(app, temuan)

    print(f"halaman diperiksa : {h}")
    print(f"dialog diperiksa  : {d}")
    print()

    if temuan:
        print(f"TEMUAN ({len(temuan)}):")
        for t in temuan:
            print(f"  - {t}")
        return 1

    print("HASIL: seluruh teks tampil utuh dan tidak ada widget keluar batas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
