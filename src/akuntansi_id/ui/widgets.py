"""
AkunTuntas - Komponen Antarmuka yang Dapat Dipakai Ulang
=========================================================
Widget-widget ini dipakai di seluruh halaman agar tampilan konsisten
dan kode tetap ringkas.

Termasuk:
  • Kartu & panel
  • Panel penjelasan kontekstual (mode Pemula)
  • KPI tile dengan tren
  • Tabel dengan format rupiah otomatis
  • Input rupiah dengan pemisah ribuan
  • Badge status
  • Kartu temuan analisis
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal, QSize, QTimer, QRectF
from PySide6.QtGui import (QFont, QColor, QFontMetrics, QIcon, QPainter,
                           QPen, QPixmap)
from PySide6.QtWidgets import (
    QFrame, QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QWidget,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QLineEdit, QSizePolicy, QScrollArea, QComboBox,
    QStyleOptionViewItem, QStyle,
)

from .. import config
from . import icons
from . import theme
from .theme import C

# Warna tombol per gaya: (latar, teks, tepi). Dipakai tombol() untuk memasang
# gayanya sendiri agar tidak bergantung pada stylesheet aplikasi.
GAYA_TOMBOL = {
    "primary": (C.PRIMARY, C.TEXT_INVERSE, C.PRIMARY),
    "danger": (C.DANGER, C.TEXT_INVERSE, C.DANGER),
    "success": (C.SUCCESS, C.TEXT_INVERSE, C.SUCCESS),
}

# Padding sel tabel dari stylesheet (7px 9px): 9px kiri + 9px kanan. Lebar
# teks saja tidak cukup untuk menghitung lebar kolom karena Qt mengurangi
# lebar sel dengan padding ini sebelum menggambar; tanpa memperhitungkannya
# Qt memakai elipsis meski menurut hitungan teks kolomnya sudah cukup.
PADDING_SEL = 18


# ==========================================================================
# IKON & LOGO APLIKASI
# ==========================================================================
def ikon_aplikasi() -> QIcon:
    """Ikon aplikasi dari berkas aset; kosong bila berkas tidak ada."""
    if config.ICON_PATH.exists():
        return QIcon(str(config.ICON_PATH))
    return QIcon()


def logo_pixmap(ukuran: int = 96) -> QPixmap:
    """Pixmap logo untuk ditampilkan di halaman login dan sidebar."""
    if config.LOGO_PATH.exists():
        return QPixmap(str(config.LOGO_PATH)).scaled(
            ukuran, ukuran, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    return QPixmap()


def logo_label(ukuran: int = 96) -> QLabel:
    """Label berisi logo; jatuh kembali ke simbol teks bila berkas tiada."""
    lbl = QLabel()
    pix = logo_pixmap(ukuran)
    if pix.isNull():
        lbl.setText("▣")
        lbl.setStyleSheet(f"font-size: {int(ukuran * 0.42)}px; "
                          f"color: {C.PRIMARY_LIGHT}; background: transparent;")
    else:
        lbl.setPixmap(pix)
        lbl.setStyleSheet("background: transparent;")
    lbl.setFixedSize(ukuran, ukuran)
    lbl.setAlignment(Qt.AlignCenter)
    return lbl


# ==========================================================================
# KARTU
# ==========================================================================
class Card(QFrame):
    """Panel putih dengan sudut membulat dan bayangan halus.

    Isi kartu ditambahkan lewat body(); membuat QLayout baru dengan kartu
    sebagai induk akan menggantikan layout bawaan dan membuat isi kartu
    tidak terlihat, jadi gunakan body() atau add().
    """

    def __init__(self, parent=None, padding: int = 18, flat: bool = False,
                 spacing: int = 12):
        super().__init__(parent)
        self.setObjectName("CardFlat" if flat else "Card")
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(padding, padding, padding, padding)
        self._layout.setSpacing(spacing)

    def body(self) -> QVBoxLayout:
        return self._layout

    def add(self, widget):
        self._layout.addWidget(widget)
        return widget

    def add_layout(self, layout):
        self._layout.addLayout(layout)
        return layout

    def ganti_isi(self, layout) -> QVBoxLayout:
        """
        Kosongkan kartu lalu pasang satu layout baru berisi seluruh isinya.

        Dipakai kartu yang isinya disusun sendiri: padding bawaan dihapus
        agar isi dapat memakai seluruh tepi kartu, sementara layout bawaan
        tetap yang aktif sehingga ukuran kartu tetap terhitung benar.
        """
        while self._layout.count():
            item = self._layout.takeAt(0)
            wdg = item.widget()
            if wdg is not None:
                wdg.setParent(None)
            sub = item.layout()
            if sub is not None:
                sub.deleteLater()
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        self._layout.addLayout(layout)
        return layout


class KpiTile(QFrame):
    """Kartu ringkas berisi satu angka utama beserta label dan keterangan.

    Susunannya sengaja dibuat bertingkat: label kecil di atas, angka besar di
    tengah, keterangan di bawah. Perbedaan ukuran angka terhadap labelnya
    dibuat mencolok supaya angka dapat dipindai sekilas, bukan dibaca satu
    per satu.
    """

    def __init__(self, label: str, value: str = "", hint: str = "",
                 warna: str = None, ikon: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("KpiTile")
        self.setMinimumHeight(112)
        # Lebar minimum dijaga kecil supaya tiga kartu dalam satu baris tetap
        # muat pada layar 1366 piksel, ukuran terkecil yang didukung. Nilai
        # yang terlalu besar membuat kartu ketiga keluar dari tepi jendela.
        self.setMinimumWidth(120)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 13, 16, 13)
        lay.setSpacing(4)

        baris_atas = QHBoxLayout()
        baris_atas.setSpacing(8)
        self.lbl_label = QLabel(label.upper())
        self.lbl_label.setObjectName("KpiLabel")
        self.lbl_label.setToolTip(label)
        self.lbl_label.setMinimumWidth(0)
        self.lbl_label.setWordWrap(True)
        baris_atas.addWidget(self.lbl_label, 1)
        if ikon:
            # ikon digambar sebagai pixmap, bukan karakter teks
            warna_ikon = warna or icons.WARNA_MUTED
            self.lbl_ikon = QLabel()
            self.lbl_ikon.setPixmap(icons.pixmap(ikon, warna_ikon, 17))
            self.lbl_ikon.setFixedSize(17, 17)
            self.lbl_ikon.setStyleSheet("background: transparent;")
            baris_atas.addWidget(self.lbl_ikon, 0)
        lay.addLayout(baris_atas)

        self.lbl_value = QLabel(value)
        self.lbl_value.setObjectName("KpiValue")
        self.lbl_value.setToolTip(value)
        self.lbl_value.setMinimumWidth(0)
        # warna disimpan: ukuran huruf disesuaikan ulang setiap kali kartu
        # berubah lebar, dan stylesheet-nya ditulis ulang saat itu
        self._warna_value = warna
        if warna:
            self.lbl_value.setStyleSheet(
                f"font-family: {theme.FONT_ANGKA}; "
                f"font-size: {theme.FS_DISPLAY}px; font-weight: 700; "
                f"color: {warna}; background: transparent;")
        lay.addWidget(self.lbl_value)

        self.lbl_hint = QLabel(hint)
        self.lbl_hint.setObjectName("KpiHint")
        self.lbl_hint.setWordWrap(True)
        self.lbl_hint.setToolTip(hint)
        lay.addWidget(self.lbl_hint)
        lay.addStretch()

        # Sediakan teks asli agar dapat ditampilkan utuh saat ruang terbatas.
        self._label_penuh = label.upper()
        self._value_penuh = value
        self._hint_penuh = hint

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._rapikan_teks()

    def _rapikan_teks(self):
        """
        Sesuaikan ukuran angka agar nominal selalu terbaca utuh.

        Nominal rupiah tidak boleh dipotong: angka yang terpotong membuat
        laporan salah dibaca. Bila ruangnya kurang, ukuran huruf diturunkan
        bertahap sampai angkanya muat, bukan dipotong dengan elipsis.

        Ukuran ditulis lewat stylesheet per widget karena aturan #KpiValue
        di stylesheet utama mengalahkan setFont().
        """
        lebar = max(self.lbl_value.width(), 40)
        teks = self._value_penuh
        warna = self._warna_value or C.TEXT

        ukuran = theme.FS_DISPLAY
        while ukuran > 13:
            font = theme.font_angka(ukuran)
            if QFontMetrics(font).horizontalAdvance(teks) <= lebar - 4:
                break
            ukuran -= 1

        font = theme.font_angka(ukuran)
        fm = QFontMetrics(font)

        if fm.horizontalAdvance(teks) > lebar - 4:
            self.lbl_value.setText(fm.elidedText(teks, Qt.ElideRight,
                                                 lebar - 4))
        else:
            self.lbl_value.setText(teks)

        self.lbl_value.setStyleSheet(
            f"font-family: {theme.FONT_ANGKA}; font-size: {ukuran}px; "
            f"font-weight: 700; color: {warna}; background: transparent; "
            "letter-spacing: -0.5px;")

        # tinggi kartu mengikuti tinggi teks label + nilai + keterangan
        perlu = (self.layout().contentsMargins().top()
                 + self.lbl_label.sizeHint().height()
                 + self.lbl_value.sizeHint().height()
                 + self.lbl_hint.sizeHint().height()
                 + self.layout().spacing() * 2
                 + self.layout().contentsMargins().bottom())
        self.setMinimumHeight(max(112, perlu))

    def set_value(self, value: str, warna: str = None):
        if warna:
            self._warna_value = warna
        self._value_penuh = value
        self.lbl_value.setToolTip(value)
        self.lbl_value.setText(value)
        if warna:
            self.lbl_value.setStyleSheet(
                f"font-size: {theme.FS_DISPLAY}px; font-weight: 700; "
                f"color: {warna}; background: transparent;")
        self._rapikan_teks()

    def set_hint(self, hint: str):
        self._hint_penuh = hint
        self.lbl_hint.setToolTip(hint)
        self.lbl_hint.setText(hint)

    def set_label(self, label: str):
        self._label_penuh = label.upper()
        self.lbl_label.setToolTip(label)
        self.lbl_label.setText(self._label_penuh)
        self._rapikan_teks()


# ==========================================================================
# PANEL PENJELASAN KONTEKSTUAL (MODE PEMULA)
# ==========================================================================
class HelpPanel(QFrame):
    """
    Panel biru berisi penjelasan konsep akuntansi/pajak untuk pemula.
    Hanya ditampilkan bila aplikasi berjalan dalam mode Pemula.
    """

    def __init__(self, judul: str, isi: str, dasar_hukum: str = "",
                 parent=None, dapat_ditutup: bool = True):
        super().__init__(parent)
        self.setObjectName("HelpPanel")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 13, 16, 13)
        lay.setSpacing(7)

        baris = QHBoxLayout()
        baris.setSpacing(8)
        ikon = QLabel()
        ikon.setPixmap(icons.pixmap("info", icons.WARNA_PRIMER, 16))
        ikon.setFixedSize(16, 16)
        ikon.setStyleSheet("background: transparent;")
        baris.addWidget(ikon)

        lbl_judul = QLabel(judul)
        lbl_judul.setObjectName("HelpTitle")
        baris.addWidget(lbl_judul)
        baris.addStretch()

        if dapat_ditutup:
            btn = QPushButton("×")
            # Ukuran mengikuti kebutuhan teks "×" dengan font 17 px; memaksa
            # 22 px membuat teksnya terpotong.
            btn.setFixedSize(30, 30)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(
                f"QPushButton {{ background: transparent; border: none; "
                f"color: {C.PRIMARY_DARK}; font-size: 17px; font-weight: 700; "
                f"padding: 0; }}"
                f"QPushButton:hover {{ background: #CFE0F0; border-radius: 11px; }}")
            btn.clicked.connect(self.hide)
            baris.addWidget(btn)
        lay.addLayout(baris)

        self.lbl_isi = QLabel(isi)
        self.lbl_isi.setObjectName("HelpBody")
        self.lbl_isi.setWordWrap(True)
        self.lbl_isi.setTextInteractionFlags(Qt.TextSelectableByMouse)
        lay.addWidget(self.lbl_isi)

        if dasar_hukum:
            lbl_hukum = QLabel(f" Dasar hukum: {dasar_hukum}")
            lbl_hukum.setObjectName("HelpLegal")
            lbl_hukum.setWordWrap(True)
            lay.addWidget(lbl_hukum)


class InfoBanner(QFrame):
    """Banner status berwarna: info / sukses / peringatan / bahaya."""

    def __init__(self, teks: str, tingkat: str = "info", judul: str = "",
                 parent=None):
        super().__init__(parent)
        nama = {"info": "HelpPanel", "ok": "SuccessPanel", "success": "SuccessPanel",
                "warning": "WarningPanel", "peringatan": "WarningPanel",
                "danger": "DangerPanel", "kritis": "DangerPanel"}.get(tingkat, "HelpPanel")
        self.setObjectName(nama)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(15, 12, 15, 12)
        lay.setSpacing(11)

        # ikon garis sesuai tingkat kepentingan banner
        ikon_map = {"info": "info", "ok": "simpan", "success": "simpan",
                    "warning": "peringatan", "peringatan": "peringatan",
                    "danger": "peringatan", "kritis": "peringatan"}
        warna_map = {"info": C.INFO, "ok": C.SUCCESS, "success": C.SUCCESS,
                     "warning": C.WARNING, "peringatan": C.WARNING,
                     "danger": C.DANGER, "kritis": C.DANGER}

        warna_ikon = warna_map.get(tingkat, C.INFO)
        lbl_ikon = QLabel()
        lbl_ikon.setPixmap(icons.pixmap(ikon_map.get(tingkat, "info"),
                                        warna_ikon, 19))
        lbl_ikon.setFixedSize(24, 24)
        lbl_ikon.setStyleSheet("background: transparent;")
        lbl_ikon.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        lay.addWidget(lbl_ikon)

        kolom = QVBoxLayout()
        kolom.setSpacing(3)
        if judul:
            lbl_j = QLabel(judul)
            lbl_j.setStyleSheet(
                f"font-weight: 700; font-size: {theme.FS_BODY}px; "
                f"color: {warna_map.get(tingkat, C.INFO)}; background: transparent;")
            kolom.addWidget(lbl_j)
        self.lbl_teks = QLabel(teks)
        self.lbl_teks.setWordWrap(True)
        self.lbl_teks.setObjectName("HelpBody")
        kolom.addWidget(self.lbl_teks)
        lay.addLayout(kolom, 1)

    def set_text(self, teks: str):
        self.lbl_teks.setText(teks)


# ==========================================================================
# BADGE
# ==========================================================================
class Badge(QLabel):
    """Label kecil berwarna untuk status."""

    def __init__(self, teks: str, tingkat: str = "netral", parent=None):
        super().__init__(teks.upper(), parent)
        warna, bg = theme.STATUS_COLORS.get(tingkat, (C.TEXT_MUTED, C.NEUTRAL_BG))
        self.setStyleSheet(
            f"QLabel {{ background: {bg}; color: {warna}; border-radius: 9px; "
            f"padding: 3px 10px; font-size: {theme.FS_TINY}px; font-weight: 700; }}")
        self.setAlignment(Qt.AlignCenter)
        # Lebar minimum dikunci pada lebar teks supaya label tidak menyusut
        # sampai tulisannya terpotong saat ruang di sekitarnya sempit.
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.setMinimumWidth(
            self.fontMetrics().horizontalAdvance(teks.upper()) + 24)


# ==========================================================================
# TABEL
# ==========================================================================
class Tabel(QTableWidget):
    """
    Tabel standar aplikasi: tanpa grid mencolok, header rapi,
    kolom dapat diurutkan, baris berselang-seling.

    Tabel yang belum berisi data menampilkan keterangan di tengah, bukan
    ruang putih kosong. Tanpa keterangan itu, pengguna mengira halamannya
    rusak atau masih memuat, padahal memang belum ada datanya.
    """

    def __init__(self, kolom: list[tuple[str, int]] = None, parent=None):
        super().__init__(parent)
        self.setAlternatingRowColors(False)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setShowGrid(False)
        # hover baris memudahkan mengikuti baris pada tabel berkolom banyak
        self.setMouseTracking(True)
        self.verticalHeader().setVisible(False)
        self.verticalHeader().setDefaultSectionSize(34)
        self.verticalHeader().setMinimumSectionSize(26)
        self.horizontalHeader().setHighlightSections(False)
        self.horizontalHeader().setFixedHeight(38)
        self.setSortingEnabled(True)
        # Keterangan yang tampil saat tabel belum berisi data.
        self.pesan_kosong = "Belum ada data pada tabel ini."
        self._label_kosong = None
        if kolom:
            self.set_kolom(kolom)

    # ------------------------------------------------------------------
    def set_pesan_kosong(self, pesan: str):
        """
        Tetapkan keterangan yang tampil saat tabel belum berisi data.

        Setiap halaman dapat menyebutkan langkah yang perlu dilakukan,
        misalnya "Tekan tombol Tambah Mitra untuk memulai".
        """
        self.pesan_kosong = pesan
        self._perbarui_pesan_kosong()

    def _perbarui_pesan_kosong(self):
        """Tampilkan atau sembunyikan keterangan tabel kosong."""
        kosong = self.rowCount() == 0
        if not kosong:
            if self._label_kosong is not None:
                self._label_kosong.hide()
            return

        # Tabel kecil di dalam dialog tidak diberi keterangan, karena
        # ruangnya sempit dan keterangan itu justru menutupi isinya.
        if self.viewport().height() < 110:
            if self._label_kosong is not None:
                self._label_kosong.hide()
            return

        if self._label_kosong is None:
            self._label_kosong = QLabel(self.pesan_kosong, self.viewport())
            self._label_kosong.setAlignment(Qt.AlignCenter)
            self._label_kosong.setWordWrap(True)
            theme.latar(self._label_kosong,
                        f"color: {C.TEXT_MUTED}; background: transparent; "
                        f"font-size: {theme.FS_BODY}px;")

        self._label_kosong.setText(self.pesan_kosong)
        # Letakkan di bagian atas ruang tabel, tepat di bawah header, supaya
        # keterangannya terbaca tanpa harus mencari.
        area = self.viewport().rect()
        self._label_kosong.setGeometry(area.x() + 20, area.y() + 16,
                                       max(80, area.width() - 40), 60)
        self._label_kosong.show()
        self._label_kosong.raise_()

    def clearContents(self):
        super().clearContents()
        self._perbarui_pesan_kosong()

    def setRowCount(self, baris: int):
        super().setRowCount(baris)
        self._perbarui_pesan_kosong()

    def showEvent(self, event):
        super().showEvent(event)
        self._perbarui_pesan_kosong()

    def setCellWidget(self, baris: int, kolom: int, widget):
        """
        Pasang widget di dalam sel, lalu pastikan tingginya cukup.

        QTableWidget memaksa widget mengikuti tinggi baris bawaan (34 px).
        Kotak isian rupiah butuh ruang lebih besar, jadi teks yang diketik
        terpotong dan tidak terlihat. Tinggi baris dinaikkan mengikuti
        kebutuhan widget tertinggi pada baris itu.
        """
        super().setCellWidget(baris, kolom, widget)
        if widget is not None:
            self._sesuaikan_tinggi_baris(baris)

    def _sesuaikan_tinggi_baris(self, baris: int):
        """
        Naikkan tinggi baris agar seluruh widget di dalamnya tampil utuh.

        QTableWidget memberi jarak 6 px di atas dan bawah widget, jadi tinggi
        baris harus lebih besar dari tinggi widget. Tanpa tambahan itu, kotak
        isian rupiah terpotong dan angka yang diketik tidak terlihat.
        """
        JARAK = 12
        perlu = self.verticalHeader().defaultSectionSize()
        for kolom in range(self.columnCount()):
            widget = self.cellWidget(baris, kolom)
            if widget is None:
                continue
            tinggi = widget.sizeHint().height() + JARAK
            if tinggi > perlu:
                perlu = tinggi
        if perlu > self.rowHeight(baris):
            self.setRowHeight(baris, perlu)

    def set_kolom(self, kolom: list[tuple[str, int]]):
        self._kolom = list(kolom)
        self._perlu_isi = {}
        self.setColumnCount(len(kolom))
        self.setHorizontalHeaderLabels([k for k, _ in kolom])
        # Seluruh kolom diatur sendiri lebarnya: kolom Stretch tidak bisa
        # ditentukan lebarnya oleh program, sehingga isinya terpotong saat
        # jendela sempit. Dengan Interactive, lebar dihitung di
        # _seimbangkan_kolom dan tabel menggeser mendatar bila tidak cukup.
        for i, (_judul, lebar) in enumerate(kolom):
            self.horizontalHeader().setSectionResizeMode(i, QHeaderView.Interactive)
            if lebar > 0:
                self.setColumnWidth(i, lebar)
        self.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self._seimbangkan_kolom([], kolom)

    def resizeEvent(self, peristiwa):
        super().resizeEvent(peristiwa)
        kolom = getattr(self, "_kolom", None)
        if kolom:
            self._seimbangkan_kolom([], kolom)

    def _lebar_perlu(self, i: int, judul: str) -> int:
        """
        Lebar minimum kolom agar judul dan isinya tampil utuh.

        Lebar sel dipakai Qt untuk menggambar teks dikurangi padding gaya
        (dari stylesheet) dan margin fokus. Bila keduanya tidak diperhitungkan,
        kolom yang "cukup" menurut hitungan teks tetap memakai elipsis.
        """
        opt = QStyleOptionViewItem()
        self.initViewItemOption(opt)
        metrik = QFontMetrics(opt.font)
        margin = self.style().pixelMetric(QStyle.PM_FocusFrameHMargin, None, self)
        sisa = 2 * margin + PADDING_SEL

        perlu = metrik.horizontalAdvance(judul) + sisa + 12
        isi = self._perlu_isi.get(i, 0)
        if isi + sisa > perlu:
            perlu = isi + sisa
        return perlu

    def _seimbangkan_kolom(self, fleksibel: list, kolom: list):
        """
        Bagi lebar tabel tanpa memotong isi kolom.

        Setiap kolom punya lebar minimum: judulnya dan isi terpanjangnya harus
        muat. Bila ruang tidak cukup, tabel menggeser mendatar - jauh lebih
        berguna daripada kolom yang dipaksa sempit sampai teksnya terpotong.
        Kolom fleksibel (lebar rancangan < 0) menerima sisa ruang.
        """
        fleksibel = [i for i, (_, lebar) in enumerate(kolom) if lebar < 0]
        perlu = {}
        rancangan = {}
        for i, (judul, lebar) in enumerate(kolom):
            perlu[i] = self._lebar_perlu(i, judul)
            rancangan[i] = lebar if lebar > 0 else perlu[i]

        tersedia = self.viewport().width()
        if tersedia <= 0:
            return

        total_rancangan = sum(rancangan.values())
        total_perlu = sum(perlu.values())

        if tersedia >= total_rancangan:
            # ruang cukup: pakai lebar rancangan, sisa dibagi ke kolom fleksibel
            for i in rancangan:
                if self.columnWidth(i) != rancangan[i]:
                    self.setColumnWidth(i, rancangan[i])
            sisa = tersedia - total_rancangan
            if fleksibel and sisa > 0:
                tambah = sisa // len(fleksibel)
                for i in fleksibel:
                    self.setColumnWidth(i, rancangan[i] + tambah)
            return

        if tersedia >= total_perlu:
            # ruang cukup untuk isi: susutkan kolom tetap sampai batasnya
            kurang = total_rancangan - tersedia
            for i in sorted(rancangan, key=lambda x: -rancangan[x]):
                if kurang <= 0:
                    break
                ruang = rancangan[i] - perlu[i]
                if ruang <= 0:
                    continue
                potong = min(ruang, kurang)
                rancangan[i] -= potong
                kurang -= potong
            for i in rancangan:
                if self.columnWidth(i) != rancangan[i]:
                    self.setColumnWidth(i, rancangan[i])
            return

        # ruang tidak cukup untuk seluruh isi: pakai lebar minimum,
        # tabel menggeser mendatar agar tidak ada teks yang terpotong
        for i in perlu:
            if self.columnWidth(i) != perlu[i]:
                self.setColumnWidth(i, perlu[i])

    def isi(self, baris: list[list], warna_baris: dict = None,
            align_kanan: set = None, warna_sel: dict = None,
            tebal_kolom: set = None, kolom_penanda: int = None):
        """
        Isi tabel.
          baris        : list of list nilai
          warna_baris  : {indeks_baris: warna_teks}
          align_kanan  : set indeks kolom yang rata kanan (biasanya angka)
          warna_sel    : {(baris, kolom): warna}
          tebal_kolom  : set indeks kolom yang dicetak tebal
          kolom_penanda: kolom yang diberi warna penanda. Bila tidak diisi,
                         kolom status dicari otomatis; bila tabel tidak punya
                         kolom status, seluruh baris yang diwarnai

        Warna baris dipakai untuk dua keperluan: menandai baris judul atau
        total, dan menandai keadaan baris data. Untuk yang kedua, mewarnai
        seluruh baris membuat nama, tanggal, dan nominal ikut berwarna
        sehingga sulit dibaca. Karena itu warna penanda dibatasi ke kolom
        status saja bila kolom itu ada.
        """
        align_kanan = align_kanan or set()

        # cari kolom status pada judul kolom
        if kolom_penanda is None and warna_baris:
            for i, (judul, _) in enumerate(getattr(self, "_kolom", [])):
                if "status" in judul.lower() or "keadaan" in judul.lower():
                    kolom_penanda = i
                    break

        self.setSortingEnabled(False)
        self.setRowCount(0)
        self.setRowCount(len(baris))
        for r, data in enumerate(baris):
            for c, nilai in enumerate(data):
                if nilai is None:
                    nilai = ""
                item = QTableWidgetItem(str(nilai))
                # teks penuh selalu tersedia lewat tooltip meski kolom sempit
                item.setToolTip(str(nilai))
                if c in align_kanan:
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                else:
                    item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                if warna_sel and (r, c) in warna_sel:
                    item.setForeground(QColor(warna_sel[(r, c)]))
                elif warna_baris and r in warna_baris:
                    if kolom_penanda is None or c == kolom_penanda:
                        item.setForeground(QColor(warna_baris[r]))
                if tebal_kolom and c in tebal_kolom:
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                self.setItem(r, c, item)
        self.setSortingEnabled(True)
        self._ukur_perlu_isi(baris, align_kanan)
        self._lebarkan_kolom_angka(baris, align_kanan)
        # batas minimum kolom berubah setelah isi diukur, jadi lebarnya
        # dihitung ulang agar isi tidak terpotong
        kolom = getattr(self, "_kolom", None)
        if kolom:
            fleksibel = [i for i, (_, lebar) in enumerate(kolom) if lebar < 0]
            if fleksibel:
                self._seimbangkan_kolom(fleksibel, kolom)

    def _ukur_perlu_isi(self, baris: list[list], align_kanan: set):
        """
        Catat lebar yang dibutuhkan tiap kolom untuk menampilkan isinya.

        Dipakai sebagai batas bawah saat kolom disusutkan: tanpa ini, kolom
        yang muat judulnya tetapi tidak muat isinya akan memotong isi, seperti
        nomor kontrak atau nama mitra yang panjang.
        """
        opt = QStyleOptionViewItem()
        self.initViewItemOption(opt)
        metrik = QFontMetrics(opt.font)
        for c in range(self.columnCount()):
            perlu = 0
            for data in baris:
                if c < len(data) and data[c] is not None:
                    lebar = metrik.horizontalAdvance(str(data[c]))
                    if lebar > perlu:
                        perlu = lebar
            self._perlu_isi[c] = perlu

    def _lebarkan_kolom_angka(self, baris: list[list], align_kanan: set):
        """Pastikan kolom angka cukup lebar untuk nominal terpanjang.

        Nominal rupiah yang terpotong membuat laporan salah dibaca, jadi
        kolom angka dilebarkan sesuai isinya (tanpa mengubah kolom teks).
        """
        if not align_kanan:
            return
        for c in align_kanan:
            if c >= self.columnCount():
                continue
            perlu = 0
            for data in baris:
                if c < len(data) and data[c] is not None:
                    perlu = max(perlu, self.fontMetrics().horizontalAdvance(
                        str(data[c])) + 24)
            if perlu > self.columnWidth(c):
                self.setColumnWidth(c, perlu)

    def baris_terpilih(self) -> Optional[int]:
        rows = self.selectionModel().selectedRows() if self.selectionModel() else []
        return rows[0].row() if rows else None

    def data_baris_terpilih(self, kolom: int = 0):
        r = self.baris_terpilih()
        if r is None:
            return None
        item = self.item(r, kolom)
        return item.text() if item else None


class TabelAngka(Tabel):
    """Tabel dengan kolom angka rata kanan dan format rupiah."""

    def __init__(self, kolom: list[tuple[str, int]], kolom_uang: set = None,
                 parent=None):
        super().__init__(kolom, parent)
        self.kolom_uang = kolom_uang or set()

    def isi_rupiah(self, baris: list[dict], kunci: list[str], format_map: dict = None):
        """Isi dari list dict; kolom dalam kolom_uang diformat rupiah."""
        data = []
        for b in baris:
            r = []
            for i, k in enumerate(kunci):
                v = b.get(k, "")
                if i in self.kolom_uang and isinstance(v, (int, float)):
                    v = theme.money(v)
                elif format_map and k in format_map:
                    v = format_map[k](v)
                r.append(v)
            data.append(r)
        align = set(self.kolom_uang)
        self.isi(data, align_kanan=align)


# ==========================================================================
# INPUT RUPIAH
# ==========================================================================
class InputRupiah(QLineEdit):
    """
    Input angka rupiah dengan pemisah ribuan otomatis.
    Menyimpan nilai sebagai integer pada .nilai().
    """

    valueChanged = Signal(int)

    def __init__(self, parent=None, placeholder: str = "0"):
        super().__init__(parent)
        self.setObjectName("MoneyInput")
        self.setPlaceholderText(placeholder)
        self.setAlignment(Qt.AlignRight)
        self._nilai = 0
        self.textChanged.connect(self._on_text)
        self.setToolTip("Masukkan angka tanpa titik. Pemisah ribuan ditambahkan otomatis.")

    def _on_text(self, teks: str):
        bersih = teks.replace(".", "").replace(" ", "").replace(",", "")
        if bersih == "":
            self._nilai = 0
            return
        if not bersih.isdigit():
            # buang karakter tidak valid
            bersih = "".join(ch for ch in bersih if ch.isdigit())
        if bersih == "":
            self._nilai = 0
            return
        baru = int(bersih)
        if baru != self._nilai:
            self._nilai = baru
            self.valueChanged.emit(baru)
        terformat = f"{baru:,}".replace(",", ".")
        if teks != terformat:
            self.blockSignals(True)
            self.setText(terformat)
            self.blockSignals(False)

    def nilai(self) -> int:
        return self._nilai

    def set_nilai(self, v):
        self._nilai = int(v or 0)
        self.blockSignals(True)
        self.setText(f"{self._nilai:,}".replace(",", ".") if self._nilai else "")
        self.blockSignals(False)

    def kosongkan(self):
        self.set_nilai(0)
        self.clear()


class InputPersen(QLineEdit):
    """Input persentase (mis. 11 untuk 11%)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("0")
        self.setAlignment(Qt.AlignRight)

    def nilai(self) -> float:
        try:
            return float(self.text().replace("%", "").replace(",", ".").strip() or 0)
        except ValueError:
            return 0.0

    def set_nilai(self, v):
        self.setText(f"{float(v):g}" if v else "")


# ==========================================================================
# KARTU TEMUAN ANALISIS
# ==========================================================================
class TemuanCard(QFrame):
    """
    Kartu satu temuan hasil analisis kesehatan keuangan.

    Mode ringkas hanya menampilkan judul, angka, dan tindakan yang perlu
    dilakukan - dipakai di dashboard. Mode lengkap menambahkan penjelasan,
    dampak, dan dasar hukum, dipakai di halaman Analisis Keuangan.
    """

    # Nama halaman yang cocok untuk tiap kategori temuan, dipakai tombol
    # tindak lanjut pada kartu. Tanda "&" ditulis ganda karena Qt
    # memperlakukannya sebagai penanda tombol pintas; dengan satu tanda,
    # teksnya tampil sebagai "Buka Kas _Bank".
    NAMA_HALAMAN = {
        "jurnal": "Buka Jurnal Umum",
        "kas_bank": "Buka Kas && Bank",
        "pajak": "Buka Pajak && SPT",
        "laporan": "Buka Laporan",
        "aset": "Buka Aset Tetap",
        "penjualan": "Buka Penjualan",
        "pembelian": "Buka Pembelian",
        "mitra": "Buka Pelanggan && Pemasok",
        "produk": "Buka Produk && Persediaan",
    }

    def __init__(self, temuan, parent=None, ringkas: bool = False,
                 buka_halaman=None):
        super().__init__(parent)
        self.setObjectName("TemuanCard")
        warna, bg = theme.STATUS_COLORS.get(temuan.tingkat, (C.TEXT_MUTED, C.NEUTRAL_BG))

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # Garis warna di kiri
        isi = QWidget()
        isi.setStyleSheet("background: transparent;")
        dalam = QVBoxLayout(isi)
        dalam.setContentsMargins(16, 13, 16, 14)
        dalam.setSpacing(10)

        # Header: badge + judul
        header = QHBoxLayout()
        header.setSpacing(10)
        teks_badge = f"{temuan.ikon} {temuan.label}"
        badge = QLabel(teks_badge)
        theme.latar(badge, f"background: {bg}; color: {warna}; border-radius: 9px; "
            f"padding: 3px 10px; font-size: {theme.FS_TINY}px; font-weight: 800;")
        badge.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        badge.setMinimumWidth(
            badge.fontMetrics().horizontalAdvance(teks_badge) + 24)
        header.addWidget(badge)

        lbl_kat = QLabel(temuan.kategori)
        lbl_kat.setStyleSheet(
            f"color: {C.TEXT_FAINT}; font-size: {theme.FS_TINY}px; "
            "font-weight: 600; background: transparent;")
        header.addWidget(lbl_kat)
        header.addStretch()
        dalam.addLayout(header)

        lbl_judul = QLabel(temuan.judul)
        lbl_judul.setStyleSheet(
            f"font-size: {theme.FS_H3}px; font-weight: 700; color: {C.TEXT}; "
            "background: transparent;")
        lbl_judul.setWordWrap(True)
        dalam.addWidget(lbl_judul)

        if temuan.angka:
            lbl_angka = QLabel(temuan.angka)
            lbl_angka.setStyleSheet(
                f"font-family: {theme.FONT_ANGKA}; font-size: {theme.FS_SMALL}px; "
                f"color: {warna}; font-weight: 700; background: transparent;")
            dalam.addWidget(lbl_angka)

        # Penjelasan
        if ringkas:
            if temuan.tindakan:
                dalam.addWidget(self._blok("Yang perlu dilakukan", temuan.tindakan,
                                           C.PRIMARY_DARK))
        else:
            dalam.addWidget(self._blok("Apa artinya", temuan.penjelasan, C.TEXT))
            if temuan.tindakan:
                dalam.addWidget(self._blok("Yang perlu dilakukan", temuan.tindakan,
                                           C.PRIMARY_DARK))
            if temuan.dampak:
                dalam.addWidget(self._blok("Bila dibiarkan", temuan.dampak, "#7A4A00"))
            if temuan.dasar_hukum:
                lbl_h = QLabel(f" {temuan.dasar_hukum}")
                lbl_h.setWordWrap(True)
                lbl_h.setStyleSheet(
                    f"color: {C.PRIMARY_DARK}; font-size: {theme.FS_TINY}px; "
                    "font-style: italic; background: transparent;")
                dalam.addWidget(lbl_h)

        # Tombol tindak lanjut: membuka halaman yang paling relevan untuk
        # menindaklanjuti temuan ini. Tanpa tombol ini, pengguna harus
        # mencari sendiri halamannya dari menu.
        halaman = getattr(temuan, "halaman", "")
        if halaman and buka_halaman is not None and not ringkas:
            baris_aksi = QHBoxLayout()
            baris_aksi.setContentsMargins(0, 0, 0, 0)
            baris_aksi.setSpacing(8)

            teks_tombol = self.NAMA_HALAMAN.get(halaman, "Buka Halaman")
            btn = QPushButton(teks_tombol)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    padding: 8px 16px;
                    border-radius: 8px;
                    border: 1px solid {C.PRIMARY};
                    background: {C.SURFACE};
                    color: {C.PRIMARY_DARK};
                    font-size: {theme.FS_SMALL}px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background: {C.PRIMARY};
                    color: {C.TEXT_INVERSE};
                }}
                QPushButton:pressed {{
                    background: {C.PRIMARY_DARK};
                    color: {C.TEXT_INVERSE};
                }}
            """)
            btn.clicked.connect(lambda _=False, h=halaman: buka_halaman(h))
            baris_aksi.addWidget(btn)
            baris_aksi.addStretch()
            dalam.addLayout(baris_aksi)

        lay.addWidget(isi)
        self.setStyleSheet(
            f"QFrame#TemuanCard {{ background: {C.SURFACE}; "
            f"border: 1px solid {C.BORDER}; border-left: 4px solid {warna}; "
            "border-radius: 8px; }}")

    def _blok(self, judul: str, isi: str, warna: str) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        l = QVBoxLayout(w)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(3)
        j = QLabel(judul.upper())
        j.setStyleSheet(
            f"color: {C.TEXT_FAINT}; font-size: 10px; font-weight: 800; "
            "letter-spacing: 0.4px; background: transparent;")
        l.addWidget(j)
        t = QLabel(rata_kanan_kiri(isi))
        t.setTextFormat(Qt.RichText)
        t.setWordWrap(True)
        t.setStyleSheet(f"color: {warna}; font-size: {theme.FS_SMALL}px; "
                        "background: transparent; line-height: 150%;")
        t.setTextInteractionFlags(Qt.TextSelectableByMouse)
        l.addWidget(t)
        return w


# ==========================================================================
# SKOR GAUGE (lingkaran skor)
# ==========================================================================
class SkorGauge(QWidget):
    """
    Lingkaran progres menampilkan skor 0-100.

    Angka dan labelnya diukur lebih dulu supaya keduanya berada di dalam
    lingkaran tanpa menyentuh busurnya. Bila label lebih lebar daripada
    ruang yang tersedia, ukuran hurufnya diperkecil bertahap.
    """

    def __init__(self, parent=None, ukuran: int = 150):
        super().__init__(parent)
        self.skor = 0
        self.label = ""
        # Saat pembukuan masih kosong, lingkaran tidak menampilkan angka
        # nol, karena angka itu terbaca sebagai penilaian buruk.
        self.belum_dinilai = False
        self.ukuran = ukuran
        self.setFixedSize(ukuran, ukuran)

    def set_skor(self, skor: int, label: str = "", belum_dinilai: bool = False):
        """
        Tetapkan nilai yang ditampilkan lingkaran.

        Parameter belum_dinilai dipakai saat pembukuan masih kosong. Nilai
        nol tidak ditampilkan sebagai angka, karena angka nol terbaca
        sebagai penilaian buruk, padahal yang terjadi adalah belum ada
        yang dapat dinilai.
        """
        self.skor = max(0, min(100, int(skor)))
        self.label = label
        self.belum_dinilai = belum_dinilai
        self.update()

    def _lebar_tersedia(self, jarak_dari_pusat: float) -> float:
        """
        Lebar ruang kosong di dalam lingkaran pada jarak tertentu dari pusat.

        Dipakai untuk memastikan teks tidak menyentuh busur lingkaran.
        """
        tebal = 13
        margin = tebal // 2 + 3
        jari = (self.ukuran / 2) - margin - tebal / 2
        sisa = jari * jari - jarak_dari_pusat * jarak_dari_pusat
        if sisa <= 0:
            return 0.0
        # 0,86 memberi jarak aman dari busur
        return 2 * (sisa ** 0.5) * 0.86

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        tebal = 13
        margin = tebal // 2 + 3
        rect = self.rect().adjusted(margin, margin, -margin, -margin)

        # latar
        p.setPen(QPen(QColor(C.NEUTRAL_BG), tebal, Qt.SolidLine, Qt.RoundCap))
        p.drawArc(rect, 0, 360 * 16)

        # Saat belum ada yang dapat dinilai, busurnya digambar putus putus
        # dan tanpa warna penilaian. Lingkaran penuh berwarna akan terbaca
        # sebagai hasil penilaian, padahal belum ada datanya.
        if self.belum_dinilai:
            p.setPen(QPen(QColor(C.BORDER_STRONG), tebal, Qt.DashLine,
                          Qt.RoundCap))
            p.drawArc(rect, 0, 360 * 16)
            self._gambar_teks(p, teks_angka="?")
            return

        # warna berdasarkan skor
        if self.skor >= 70:
            warna = QColor(C.SUCCESS)
        elif self.skor >= 55:
            warna = QColor(C.WARNING)
        else:
            warna = QColor(C.DANGER)

        p.setPen(QPen(warna, tebal, Qt.SolidLine, Qt.RoundCap))
        p.drawArc(rect, 90 * 16, -int(360 * 16 * self.skor / 100))
        self._gambar_teks(p, teks_angka=str(self.skor))

    def _gambar_teks(self, p, teks_angka: str):
        """Gambar angka dan label di tengah lingkaran."""
        tengah = self.ukuran / 2

        # Ukuran angka disesuaikan dengan ruang di dalam lingkaran.
        ukuran_angka = max(15, int(self.ukuran * 0.21))
        while ukuran_angka > 13:
            f = QFont(theme.FONT_UI)
            f.setPixelSize(ukuran_angka)
            f.setBold(True)
            lebar = QFontMetrics(f).horizontalAdvance(teks_angka)
            if lebar <= self._lebar_tersedia(0):
                break
            ukuran_angka -= 1

        ada_label = bool(self.label)
        label_teks = self.label.upper()

        # Label diletakkan di bawah angka. Jaraknya ditetapkan lebih dulu
        # agar lebar yang tersedia pada posisi itu dapat dihitung.
        jarak_label = 15 if ada_label else 0
        ukuran_label = max(7, int(self.ukuran * 0.058))
        lebar_label = 0
        if ada_label:
            while ukuran_label > 6:
                f2 = QFont(theme.FONT_UI)
                f2.setPixelSize(ukuran_label)
                f2.setBold(True)
                fm2 = QFontMetrics(f2)
                lebar_label = fm2.horizontalAdvance(label_teks)
                if lebar_label <= self._lebar_tersedia(jarak_label):
                    break
                ukuran_label -= 1

        tinggi_angka = ukuran_angka
        tinggi_label = ukuran_label if ada_label else 0
        total = tinggi_angka + (jarak_label + tinggi_label if ada_label else 0)
        atas_grup = tengah - total / 2

        p.setPen(QColor(C.TEXT))
        f = QFont(theme.FONT_UI)
        f.setPixelSize(ukuran_angka)
        f.setBold(True)
        p.setFont(f)
        p.drawText(QRectF(0, atas_grup, self.ukuran, tinggi_angka + 4),
                   Qt.AlignCenter, teks_angka)

        if ada_label:
            f2 = QFont(theme.FONT_UI)
            f2.setPixelSize(ukuran_label)
            f2.setBold(True)
            p.setFont(f2)
            p.setPen(QColor(C.TEXT_MUTED))
            y_label = atas_grup + tinggi_angka + jarak_label
            p.drawText(QRectF(0, y_label, self.ukuran, tinggi_label + 3),
                       Qt.AlignHCenter | Qt.AlignTop, label_teks)
        p.end()


# ==========================================================================
# BARIS KPI MINI
# ==========================================================================
class MiniStat(QWidget):
    """Statistik kecil berjajar: label di atas, nilai di bawah.

    Label dibiarkan membungkus ke baris berikutnya alih-alih dipotong,
    sehingga nama indikator selalu terbaca utuh meski kolomnya sempit.
    """

    def __init__(self, label: str, nilai: str, warna: str = None, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)
        self._label_penuh = label.upper()
        self._nilai_penuh = nilai
        self.lbl = QLabel(self._label_penuh)
        self.lbl.setObjectName("KpiLabel")
        self.lbl.setToolTip(label)
        self.lbl.setWordWrap(True)
        self.lbl.setMinimumWidth(0)
        lay.addWidget(self.lbl)
        self.v = QLabel(nilai)
        self.v.setObjectName("KpiValue")
        self.v.setToolTip(nilai)
        self.v.setMinimumWidth(0)
        self.v.setStyleSheet(
            f"font-family: {theme.FONT_ANGKA}; font-size: {theme.FS_H3}px; "
            f"font-weight: 600; color: {warna or C.TEXT}; background: transparent;")
        lay.addWidget(self.v)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # nilai dipendekkan dengan elipsis bila ruang kurang; teks penuh
        # tetap tersedia lewat tooltip
        lebar_v = max(self.v.width(), 40)
        self.v.setText(self.v.fontMetrics().elidedText(
            self._nilai_penuh, Qt.ElideRight, lebar_v))

    def set_nilai(self, nilai: str, warna: str = None):
        self._nilai_penuh = nilai
        self.v.setToolTip(nilai)
        self.v.setText(nilai)
        if warna:
            self.v.setStyleSheet(
                f"font-family: {theme.FONT_ANGKA}; font-size: {theme.FS_H3}px; "
                f"font-weight: 600; color: {warna}; background: transparent;")

    def set_teks_label(self, label: str):
        """Ganti teks label tanpa mengubah ukuran wadahnya."""
        self._label_penuh = label.upper()
        self.lbl.setToolTip(label)
        self.lbl.setText(self._label_penuh)
        self.lbl.updateGeometry()
        self.v.updateGeometry()
        self.updateGeometry()


# ==========================================================================
# HEADER HALAMAN
# ==========================================================================
def _tombol(teks: str, gaya: str = "biasa", ikon: str = "") -> QPushButton:
    """
    Panggil tombol() yang didefinisikan di bagian bawah berkas ini.

    Dibuat terpisah supaya kelas di atasnya dapat memakainya tanpa
    bergantung pada urutan penulisan.
    """
    return tombol(teks, gaya=gaya, ikon=ikon)


class PageHeader(QWidget):
    """Judul halaman + subjudul + area tombol aksi."""

    def __init__(self, judul: str, subjudul: str = "", parent=None):
        super().__init__(parent)
        self._aksi_terpisah = False

        # Susunan menyamping: judul di kiri, tombol aksi di kanan.
        self._luar = QHBoxLayout(self)
        self._luar.setContentsMargins(0, 0, 0, 0)
        self._luar.setSpacing(14)

        self._kolom = QVBoxLayout()
        self._kolom.setSpacing(3)
        self.lbl_judul = QLabel(judul)
        self.lbl_judul.setObjectName("PageTitle")
        # Judul panjang dibiarkan membungkus ke baris kedua supaya tidak
        # mendesak tombol aksi keluar dari tepi header.
        self.lbl_judul.setWordWrap(True)
        self._kolom.addWidget(self.lbl_judul)
        self.lbl_sub = QLabel(subjudul)
        self.lbl_sub.setObjectName("PageSubtitle")
        self.lbl_sub.setWordWrap(True)
        self._kolom.addWidget(self.lbl_sub)

        self._teks = QWidget()
        self._teks.setLayout(self._kolom)
        self._luar.addWidget(self._teks, 1)

        # Wadah tombol aksi. Lebar minimumnya dijaga agar tombol tidak
        # dihimpit sampai teksnya terpotong.
        self._wadah_aksi = QWidget()
        self.aksi = QHBoxLayout(self._wadah_aksi)
        self.aksi.setContentsMargins(0, 0, 0, 0)
        self.aksi.setSpacing(8)
        self._luar.addWidget(self._wadah_aksi, 0, Qt.AlignTop)

    def tambah_aksi(self, tombol: QPushButton):
        self.aksi.addWidget(tombol)
        self._wadah_aksi.setMinimumWidth(self.aksi.sizeHint().width())
        return tombol

    def pasang_ekspor_cetak(self, halaman, judul: str = "", nama_tabel=None,
                            kumpulkan=None):
        """
        Tambahkan tombol Ekspor dan Cetak ke header halaman ini.

        Dipanggil sekali dari halaman mana pun. Isi tabel dibaca langsung
        dari tabel yang sedang tampil, sehingga halaman tidak perlu
        menyiapkan data tersendiri dan seluruh halaman memakai cara yang
        sama.

        halaman   : objek halaman, dipakai untuk judul dan kotak pesan
        judul     : judul yang tampil pada berkas, kosong berarti memakai
                    judul halaman
        nama_tabel: atribut tabel pada halaman; kosong berarti mencari
                    sendiri tabel pertama yang ditemukan
        kumpulkan : fungsi yang mengembalikan daftar (nama bagian, baris
                    tabel) untuk halaman yang isinya bukan tabel, misalnya
                    dashboard yang seluruhnya berupa kartu angka. Bila
                    diisi, nama_tabel diabaikan.
        """
        from .ekspor_cetak import (cetak_halaman, ekspor_halaman,
                                   tabel_dari_widget)

        self._halaman = halaman
        self._judul_ekspor = judul or self.lbl_judul.text()

        def ambil_data():
            # Halaman yang isinya bukan tabel menyediakan datanya sendiri.
            if kumpulkan is not None:
                try:
                    return kumpulkan()
                except Exception:
                    return []
            tabel = self._cari_tabel(nama_tabel)
            if tabel is None:
                return []
            return [(self._judul_ekspor, tabel_dari_widget(tabel))]

        def lakukan_ekspor():
            data = ambil_data()
            if not data:
                return
            sub = self.lbl_sub.text()
            ekspor_halaman(halaman, self._judul_ekspor, sub, data,
                           nama_berkas=self._judul_ekspor)

        def lakukan_cetak():
            data = ambil_data()
            if not data:
                return
            sub = self.lbl_sub.text()
            cetak_halaman(halaman, self._judul_ekspor, sub, data)

        # tombol() berada di bagian bawah berkas ini, jadi dipanggil
        # setelah modulnya selesai dimuat.
        b_ekspor = _tombol("Ekspor", ikon="ekspor")
        b_ekspor.setToolTip(
            "Simpan data yang tampil ke berkas Excel.\n"
            "Angka tersimpan sebagai angka sehingga dapat dijumlahkan.")
        b_ekspor.clicked.connect(lakukan_ekspor)

        b_cetak = _tombol("Cetak", ikon="dokumen")
        b_cetak.setToolTip(
            "Cetak data yang tampil ke kertas A4.\n"
            "Pratinjau ditampilkan lebih dulu sebelum kertas terpakai.")
        b_cetak.clicked.connect(lakukan_cetak)

        self.tambah_aksi(b_ekspor)
        self.tambah_aksi(b_cetak)

        # Dua tombol tambahan membuat baris aksi menjadi panjang. Pada
        # header yang menyusun tombolnya menyamping, tombolnya dapat keluar
        # dari tepi header. Karena itu susunannya dipindah ke baris
        # tersendiri di bawah judul.
        self.susun_aksi_terpisah()
        return b_ekspor, b_cetak

    def _cari_tabel(self, nama: str):
        """
        Temukan tabel yang akan diekspor.

        Bila namanya disebut, atribut itu yang dipakai. Bila tidak, tabel
        pertama yang ditemukan pada halaman dianggap tabel utama.
        """
        if self._halaman is None:
            return None
        if nama:
            return getattr(self._halaman, nama, None)
        # Tabel yang benar benar terlihat lebih didahulukan, karena satu
        # halaman dapat memuat beberapa tabel pada tab yang berbeda.
        kandidat = []
        for atribut in dir(self._halaman):
            if not atribut.startswith("tabel"):
                continue
            objek = getattr(self._halaman, atribut, None)
            if objek is None or not hasattr(objek, "rowCount"):
                continue
            kandidat.append((atribut, objek))
        if not kandidat:
            return None
        for _, objek in kandidat:
            try:
                if objek.isVisible():
                    return objek
            except Exception:
                continue
        return kandidat[0][1]

    def hasHeightForWidth(self) -> bool:
        """Header ikut menghitung tinggi dari pembungkusan subjudulnya."""
        return True

    def heightForWidth(self, lebar: int) -> int:
        """
        Tinggi yang dibutuhkan pada lebar tertentu.

        Subjudul membungkus kata, jadi tingginya bergantung pada lebar yang
        tersedia. Tanpa perhitungan ini, tata letak memakai tinggi satu baris
        dan baris terakhir subjudul terpotong.
        """
        sisa = max(120, lebar - self._wadah_aksi.sizeHint().width() - 20)
        tinggi = self._tinggi_judul(sisa)
        tinggi_sub = self._tinggi_sub(sisa)
        return tinggi + tinggi_sub + 3

    def _tinggi_judul(self, lebar: int) -> int:
        """Tinggi judul pada lebar tertentu, dihitung sendiri."""
        from PySide6.QtGui import QTextDocument
        doc = QTextDocument()
        doc.setDefaultFont(self.lbl_judul.font())
        doc.setPlainText(self.lbl_judul.text())
        doc.setTextWidth(max(1, lebar))
        return int(doc.size().height()) + 2

    def _tinggi_sub(self, lebar: int) -> int:
        """Tinggi subjudul pada lebar tertentu, dihitung sendiri."""
        from PySide6.QtGui import QTextDocument
        doc = QTextDocument()
        doc.setDefaultFont(self.lbl_sub.font())
        doc.setPlainText(self.lbl_sub.text())
        doc.setTextWidth(max(1, lebar))
        return int(doc.size().height()) + 2

    def susun_aksi_terpisah(self):
        """
        Pindahkan tombol aksi ke baris tersendiri di bawah judul.

        Dipakai halaman yang memiliki banyak tombol aksi: bila disusun
        menyamping, tombolnya meluber keluar tepi header. Susunan diubah
        menjadi vertikal: judul di atas, tombol aksi di baris berikutnya,
        rata kanan.
        """
        if self._aksi_terpisah:
            return
        self._aksi_terpisah = True

        # ganti susunan luar dari menyamping menjadi menurun
        lama = self.layout()
        lama.removeWidget(self._teks)
        lama.removeWidget(self._wadah_aksi)

        baru = QVBoxLayout(self)
        baru.setContentsMargins(0, 0, 0, 0)
        baru.setSpacing(10)
        baru.addWidget(self._teks)

        baris_aksi = QHBoxLayout()
        baris_aksi.setContentsMargins(0, 0, 0, 0)
        baris_aksi.addStretch()
        baris_aksi.addWidget(self._wadah_aksi)
        baru.addLayout(baris_aksi)

    def set_subjudul(self, teks: str):
        self.lbl_sub.setText(teks)


def tombol(teks: str, gaya: str = "biasa", ikon: str = "") -> QPushButton:
    """Buat tombol dengan gaya standar aplikasi.

    Parameter `ikon` menerima nama ikon garis dari modul icons
    (mis. "tambah", "simpan", "cetak"). Tanda "&" pada teks dilipatgandakan
    agar tampil apa adanya - Qt membacanya sebagai penanda tombol pintasan
    dan menghilangkannya bila tunggal.

    Tombol berwarna memasang gayanya sendiri, bukan hanya mengandalkan
    stylesheet aplikasi: bila induknya punya stylesheet, Qt tidak lagi
    menerapkan aturan aplikasi pada anaknya sehingga tombol tampil pucat
    dengan teks yang nyaris tidak terbaca.

    Lebar minimum ditetapkan dari kebutuhan teks supaya tombol tidak pernah
    terhimpit dan labelnya terpotong saat jendela menyempit.
    """
    t = QPushButton(teks.replace("&", "&&"))
    t.setCursor(Qt.PointingHandCursor)
    if gaya == "primary":
        t.setObjectName("Primary")
    elif gaya == "danger":
        t.setObjectName("Danger")
    elif gaya == "success":
        t.setObjectName("Success")
    elif gaya == "ghost":
        t.setObjectName("Ghost")
    t.setMinimumHeight(34)

    warna_latar, warna_teks, warna_tepi = GAYA_TOMBOL.get(gaya, (None, None, None))
    if warna_latar:
        aturan = (f"QPushButton {{ background: {warna_latar}; color: {warna_teks}; "
                  f"border: 1px solid {warna_tepi}; border-radius: {theme.SUDUT_KONTROL}px; "
                  f"padding: 7px 15px; font-size: {theme.FS_BODY}px; font-weight: 600; }}")
        t.setStyleSheet(aturan)

    if ikon:
        warna = {"primary": icons.WARNA_TERANG, "danger": icons.WARNA_TERANG,
                 "success": icons.WARNA_TERANG}.get(gaya, icons.WARNA_GELAP)
        t.setIcon(icons.ikon(ikon, warna, 17))
        t.setIconSize(QSize(17, 17))

    t.setMinimumWidth(t.sizeHint().width())
    return t


class AreaGulir(QScrollArea):
    """Area gulir yang menghitung tinggi isi dari pembungkusan teks.

    Label dengan word-wrap melaporkan tinggi minimum hanya satu baris,
    sehingga isi bisa terhimpit. Kelas ini menyetel tinggi minimum isi
    sesuai kebutuhan teks pada lebar yang tersedia.

    Isi halaman sering diganti setelah dimuat (mis. setelah tahun berganti),
    jadi penyesuaian juga dijalankan berkala selama area ini terlihat.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        # Catatan lebar terakhir tiap label, supaya pengukuran tinggi hanya
        # diulang saat lebarnya benar-benar berubah.
        self._lebar_label: dict[int, int] = {}
        # Timer dipakai untuk menyesuaikan tinggi setelah isi halaman
        # diganti. Intervalnya tidak perlu rapat: pengukuran hanya berjalan
        # saat ada perubahan, dan setiap pengukuran sudah memeriksa sendiri
        # apakah labelnya masih perlu diukur.
        self._timer = QTimer(self)
        self._timer.setInterval(600)
        self._timer.timeout.connect(self.sesuaikan_tinggi)

    def showEvent(self, peristiwa):
        super().showEvent(peristiwa)
        self._timer.start()
        self.sesuaikan_tinggi()

    def hideEvent(self, peristiwa):
        self._timer.stop()
        super().hideEvent(peristiwa)

    def resizeEvent(self, peristiwa):
        super().resizeEvent(peristiwa)
        self.sesuaikan_tinggi()

    def sesuaikan_tinggi(self):
        """
        Sesuaikan tinggi label ber-word-wrap dengan lebar yang tersedia.

        Label ber-word-wrap melaporkan tinggi minimum hanya satu baris,
        sehingga isi bisa terhimpit. Tinggi nyatanya dihitung untuk lebar
        yang tersedia lalu dipatok.

        Perhitungan hanya dilakukan untuk label yang lebarnya berubah sejak
        pengukuran terakhir. Tanpa itu, seluruh label dihitung ulang setiap
        kali halaman ditampilkan, dan pada halaman dengan banyak keterangan
        pekerjaan itu memakan puluhan milidetik sehingga perpindahan menu
        terasa tersendat.
        """
        isi = self.widget()
        if isi is None or isi.layout() is None:
            return
        from PySide6.QtWidgets import QLabel

        catatan = self._lebar_label
        masih_dipakai = set()

        for lbl in isi.findChildren(QLabel):
            if not lbl.wordWrap():
                continue
            lebar = lbl.width()
            if lebar <= 0:
                continue
            masih_dipakai.add(id(lbl))

            # Lewati label yang lebarnya sama seperti saat terakhir diukur.
            if catatan.get(id(lbl)) == lebar:
                continue

            perlu = lbl.heightForWidth(lebar)
            if perlu > 0 and lbl.minimumHeight() != perlu:
                lbl.setMinimumHeight(perlu)
            catatan[id(lbl)] = lebar

            # Tinggi sudah dipatok, jadi Qt tidak perlu menghitungnya lagi
            # setiap kali tata letak berubah.
            theme.matikan_tinggi_dari_lebar(lbl)

        # Buang catatan label yang sudah tidak ada supaya tidak menumpuk.
        if len(catatan) > len(masih_dipakai) * 2:
            for kunci in list(catatan):
                if kunci not in masih_dipakai:
                    del catatan[kunci]

        isi.layout().activate()
        perlu = isi.layout().minimumSize().height()
        perlu = max(perlu, isi.layout().sizeHint().height())
        if isi.minimumHeight() != perlu:
            isi.setMinimumHeight(perlu)


def scroll(widget: QWidget) -> QScrollArea:
    """Bungkus widget dalam area yang bisa digulir."""
    area = AreaGulir()
    area.setWidgetResizable(True)
    area.setWidget(widget)
    area.setFrameShape(QFrame.NoFrame)
    area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    return area


def divider() -> QFrame:
    f = QFrame()
    f.setObjectName("Divider")
    f.setFixedHeight(1)
    return f


class LabelTinggiOtomatis(QLabel):
    """
    Label berword-wrap yang tingginya selalu cukup untuk seluruh teksnya.

    Qt menghitung tinggi teks berformat lebih pendek daripada kebutuhan
    sebenarnya, sehingga baris terakhirnya terpotong saat lebar label
    sempit. Kelas ini mengukur ulang tinggi teks memakai QTextDocument
    setiap kali lebarnya berubah, lalu menetapkan tinggi minimum tersebut.
    """

    def resizeEvent(self, peristiwa):
        super().resizeEvent(peristiwa)
        self._sesuaikan_tinggi()

    def showEvent(self, peristiwa):
        super().showEvent(peristiwa)
        self._sesuaikan_tinggi()

    def _sesuaikan_tinggi(self):
        if not self.wordWrap() or not self.text():
            return
        lebar = self.width()
        if lebar <= 0:
            return
        from PySide6.QtGui import QTextDocument

        doc = QTextDocument()
        doc.setDefaultFont(self.font())
        if "<" in self.text():
            doc.setHtml(self.text())
        else:
            doc.setPlainText(self.text())
        doc.setTextWidth(lebar)
        perlu = int(doc.size().height()) + 2
        if self.minimumHeight() != perlu:
            self.setMinimumHeight(perlu)


def rata_kanan_kiri(teks: str) -> str:
    """
    Bungkus teks berparagraf agar rata kanan-kiri saat ditampilkan.

    Teks berformat di Qt mengikuti atribut perataan di dalam HTML, jadi
    perataan dipasang pada setiap paragraf. Baris terakhir paragraf tetap
    rata kiri sesuai kaidah tipografi.
    """
    potongan = [p.strip() for p in teks.split("\n\n") if p.strip()]
    if not potongan:
        return teks
    hasil = []
    for par in potongan:
        isi = par.replace("\n", " ")
        hasil.append(
            f'<p style="text-align: justify; margin: 0 0 10px 0;">{isi}</p>')
    return "".join(hasil)


def label(teks: str, objek: str = "", wrap: bool = False, ukuran: int = None) -> QLabel:
    """Buat label teks.

    Label panjang dibungkus kata secara otomatis bila tidak diberi lebar
    tetap, supaya kalimatnya tidak terpotong di jendela sempit.
    """
    l = LabelTinggiOtomatis(teks) if wrap else QLabel(teks)
    if objek:
        l.setObjectName(objek)
    l.setWordWrap(wrap)
    if ukuran:
        l.setStyleSheet(f"font-size: {ukuran}px; background: transparent;")
    return l


def combo_akun(company_id: int, semua: bool = True, parent=None) -> QComboBox:
    """ComboBox berisi daftar akun perusahaan: '1001 - Kas'."""
    from .. import services
    c = QComboBox(parent)
    c.setMinimumWidth(230)
    akun = services.list_accounts(company_id)
    for a in akun:
        c.addItem(f"{a['kode']} - {a['nama']}", a["kode"])
    lebarkan_combo(c)
    return c


def lebarkan_combo(c: QComboBox, maksimum: int = 520) -> QComboBox:
    """
    Sesuaikan lebar kotak pilihan dengan pilihan terpanjangnya.

    Lebar bawaan Qt sering lebih sempit dari isinya sehingga nama panjang
    terpotong dan pengguna tidak tahu pilihan apa yang sedang tampil.
    """
    if c.count() == 0:
        return c
    metrik = QFontMetrics(c.font())
    lebar = max(metrik.horizontalAdvance(c.itemText(i)) for i in range(c.count()))
    # ruang untuk tombol panah dan bingkai
    lebar += 46
    c.setMinimumWidth(min(maksimum, max(c.minimumWidth(), lebar)))
    return c


def daftar_akun_neraca(company_id: int) -> list:
    """Akun neraca (aset, liabilitas, ekuitas) untuk memilih sumber saldo awal."""
    from .. import services
    akun = services.list_accounts(company_id)
    return [(a["kode"], a["nama"]) for a in akun
            if a["tipe"] in ("Aset", "Liabilitas", "Ekuitas")]


def set_combo_by_data(combo: QComboBox, data: str) -> bool:
    idx = combo.findData(data)
    if idx >= 0:
        combo.setCurrentIndex(idx)
        return True
    return False


# ==========================================================================
# PESAN KEPADA PENGGUNA
# ==========================================================================
def belum_ada_perusahaan(parent=None, tindakan: str = "") -> None:
    """
    Beri tahu pengguna bahwa tindakan ini memerlukan profil perusahaan.

    Tanpa pesan ini, menekan tombol hanya menghasilkan diam tanpa
    penjelasan, sehingga pengguna mengira aplikasinya rusak. Pesannya
    menyebutkan langkah yang harus dilakukan lebih dulu, bukan sekadar
    menyatakan kegagalan.

    Parameter tindakan diisi nama tindakan yang sedang dicoba, misalnya
    "menambah karyawan", supaya pesannya menyesuaikan keadaan.
    """
    from PySide6.QtWidgets import QMessageBox

    awal = "Lengkapi dulu profil perusahaan."
    if tindakan:
        awal = f"Belum dapat {tindakan}, karena profil perusahaan belum ada."

    QMessageBox.information(
        parent, "Profil perusahaan belum ada",
        f"{awal}\n\n"
        "Langkah yang perlu dilakukan:\n"
        "1. Buka menu Data Usaha, lalu pilih Data Perusahaan\n"
        "2. Isi nama perusahaan dan bentuk badan usaha\n"
        "3. Tekan tombol Buat Perusahaan\n\n"
        "Setelah profil perusahaan dibuat, seluruh menu pembukuan "
        "langsung dapat dipakai.")


def perlu_dipilih(parent=None, apa: str = "satu baris data") -> None:
    """Beri tahu pengguna bahwa belum ada baris yang dipilih."""
    from PySide6.QtWidgets import QMessageBox

    QMessageBox.information(
        parent, "Belum ada yang dipilih",
        f"Pilih dulu {apa} pada tabel, lalu ulangi tindakannya.")
