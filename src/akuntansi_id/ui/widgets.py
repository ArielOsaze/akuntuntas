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

import re
import time
from datetime import date
from typing import Optional

from PySide6.QtCore import Qt, Signal, QSize, QTimer, QRectF, QRegularExpression
from PySide6.QtGui import (QFont, QColor, QBrush, QFontMetrics, QIcon, QPainter,
                           QPen, QPixmap, QRegularExpressionValidator)
from PySide6.QtWidgets import (
    QApplication, QFrame, QLabel, QVBoxLayout, QHBoxLayout, QPushButton,
    QWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QLineEdit, QSizePolicy, QScrollArea, QComboBox,
    QProgressBar, QStyledItemDelegate, QStyleOptionViewItem,
    QStyle, QTabWidget,
)

from .. import config
from . import icons
from . import theme
from .theme import C
from . import popup

# Warna tombol per gaya: (latar, teks, tepi, latar hover, latar tekan).
# Dipakai tombol() untuk memasang gayanya sendiri agar tidak bergantung pada
# stylesheet aplikasi. Gaya "success" dibuat berwarna lembut supaya tidak
# bersaing dengan satu tombol utama pada baris aksi yang sama.
GAYA_TOMBOL = {
    "primary": (C.PRIMARY, C.TEXT_INVERSE, C.PRIMARY, C.PRIMARY_DARK, "#0F1518"),
    "danger": (C.DANGER, C.TEXT_INVERSE, C.DANGER, "#862C26", "#6F221D"),
    "success": (C.SUCCESS_BG, C.SUCCESS, "#BFDCCB", "#DFEEE5", "#BFDCCB"),
}

# Padding sel tabel dari stylesheet (8px 8px): 8px kiri + 8px kanan. Lebar
# teks saja tidak cukup untuk menghitung lebar kolom karena Qt mengurangi
# lebar sel dengan padding ini sebelum menggambar; tanpa memperhitungkannya
# Qt memakai elipsis meski menurut hitungan teks kolomnya sudah cukup.
PADDING_SEL = 16
CADANGAN_SEL = 8

# Saat ruang tabel sempit, kolom fleksibel (kolom teks seperti keterangan
# atau nama) boleh menyusut agar seluruh kolom tetap terlihat tanpa menggeser
# mendatar. Di bawah batas ini tabel memakai lebar penuh isinya dan digeser.
MIN_LEBAR_FLEKSIBEL = 90

# Batas nominal yang boleh diketik. SQLite menyimpan uang sebagai INTEGER
# 64-bit, sedangkan nominal ini juga dipakai untuk menjumlahkan baris,
# menghitung PPN, dan menyusun laporan. Batas Rp999 triliun menyisakan
# ruang yang lebar untuk perhitungan turunan tersebut.
BATAS_NOMINAL = 999_999_999_999_999
_BATAS_DIGIT = len(str(BATAS_NOMINAL))


def _format_nominal(nilai: int) -> str:
    """Format angka dengan pemisah ribuan gaya Indonesia."""
    return f"{nilai:,}".replace(",", ".")


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

    Angka ditulis dengan huruf serif seperti angka pokok pada laporan
    keuangan, labelnya berupa huruf kecil renggang di atasnya. Ikon garis
    kecil hanya menjadi penanda, bukan keping berwarna yang menarik
    perhatian lebih besar daripada angkanya.
    """

    def __init__(self, label: str, value: str = "", hint: str = "",
                 warna: str = None, ikon: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("KpiTile")
        self.setMinimumHeight(116)
        # Lebar minimum dijaga kecil supaya kartu dalam satu baris tetap
        # muat pada layar 1366 piksel. Nilai yang terlalu besar membuat
        # kartu terakhir keluar dari tepi jendela.
        self.setMinimumWidth(110)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(17, 14, 17, 14)
        lay.setSpacing(5)

        baris_atas = QHBoxLayout()
        baris_atas.setSpacing(8)
        self.lbl_label = QLabel(label.upper())
        self.lbl_label.setObjectName("KpiLabel")
        self.lbl_label.setToolTip(label)
        self.lbl_label.setMinimumWidth(0)
        self.lbl_label.setWordWrap(True)
        baris_atas.addWidget(self.lbl_label, 1)
        if ikon:
            self.lbl_ikon = QLabel()
            self.lbl_ikon.setPixmap(icons.pixmap(ikon, C.TEXT_FAINT, 15))
            self.lbl_ikon.setFixedSize(15, 15)
            self.lbl_ikon.setAlignment(Qt.AlignCenter)
            self.lbl_ikon.setStyleSheet("background: transparent;")
            baris_atas.addWidget(self.lbl_ikon, 0, Qt.AlignTop)
        lay.addLayout(baris_atas)

        self.lbl_value = QLabel(value)
        self.lbl_value.setObjectName("KpiAngka")
        self.lbl_value.setToolTip(value)
        self.lbl_value.setMinimumWidth(0)
        self._warna_value = warna
        lay.addWidget(self.lbl_value)

        self.lbl_hint = QLabel(hint)
        self.lbl_hint.setObjectName("KpiHint")
        self.lbl_hint.setWordWrap(True)
        self.lbl_hint.setToolTip(hint)
        lay.addWidget(self.lbl_hint)
        lay.addStretch()

        self._label_penuh = label.upper()
        self._value_penuh = value
        self._hint_penuh = hint
        self._rapikan_teks()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._rapikan_teks()

    def _rapikan_teks(self):
        """
        Sesuaikan ukuran angka agar nominal selalu terbaca utuh.

        Nominal rupiah tidak boleh dipotong: angka yang terpotong membuat
        laporan salah dibaca. Bila ruangnya kurang, ukuran huruf diturunkan
        bertahap sampai angkanya muat. Elipsis hanya dipakai pada keadaan
        darurat ketika huruf sudah mencapai ukuran terkecil.
        """
        lebar = max(self.lbl_value.width(), 40)
        teks = self._value_penuh
        warna = self._warna_value or C.TEXT

        ukuran = theme.FS_DISPLAY
        while ukuran > 13:
            font = theme.font_serif_angka(ukuran)
            if QFontMetrics(font).horizontalAdvance(teks) <= lebar - 2:
                break
            ukuran -= 1

        font = theme.font_serif_angka(ukuran)
        fm = QFontMetrics(font)
        teks_tampil = teks
        if fm.horizontalAdvance(teks) > lebar - 2:
            teks_tampil = fm.elidedText(teks, Qt.ElideRight, lebar - 2)
        if self.lbl_value.text() != teks_tampil:
            self.lbl_value.setText(teks_tampil)

        self.lbl_value.setStyleSheet(
            f"font-family: '{theme.FONT_SERIF}', Georgia, serif; "
            f"font-size: {ukuran}px; font-weight: 600; color: {warna}; "
            "background: transparent;")

        perlu = (self.layout().contentsMargins().top()
                 + self.lbl_label.sizeHint().height()
                 + self.lbl_value.sizeHint().height()
                 + self.lbl_hint.sizeHint().height()
                 + self.layout().spacing() * 2
                 + self.layout().contentsMargins().bottom())
        self.setMinimumHeight(max(116, perlu))

    def set_value(self, value: str, warna: str = None):
        if warna:
            self._warna_value = warna
        self._value_penuh = value
        self.lbl_value.setToolTip(value)
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
        # Panel penjelasan tidak boleh ikut melar mengisi sisa tinggi
        # dialog; ruang lebih sebaiknya diberikan kepada tabel atau isian.
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 13, 16, 13)
        lay.setSpacing(7)

        baris = QHBoxLayout()
        baris.setSpacing(8)
        ikon = QLabel()
        ikon.setPixmap(icons.pixmap("info", icons.WARNA_MUTED, 16))
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
                f"QPushButton:hover {{ background: {C.ACCENT_SOFT}; border-radius: 11px; }}")
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
        ikon_map = {"info": "info", "ok": "centang", "success": "centang",
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
    """Label kecil berwarna untuk status.

    Bentuknya persegi dengan sudut 3 px, seperti cap pada dokumen, bukan
    pil pastel. Warna latar dipakai sangat tipis agar status tetap terbaca
    sebagai keterangan dan tidak bersaing dengan angka di sekitarnya.
    """

    def __init__(self, teks: str, tingkat: str = "netral", parent=None):
        super().__init__(teks.upper(), parent)
        warna, bg = theme.STATUS_COLORS.get(tingkat, (C.TEXT_MUTED, C.NEUTRAL_BG))
        self.setStyleSheet(
            f"QLabel {{ background: {bg}; color: {warna}; border-radius: 3px; "
            f"padding: 3px 8px; font-size: 10px; font-weight: 700; "
            "letter-spacing: 0.5px; }")
        self.setAlignment(Qt.AlignCenter)
        # Lebar minimum dikunci pada lebar teks supaya label tidak menyusut
        # sampai tulisannya terpotong saat ruang di sekitarnya sempit.
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.setMinimumWidth(
            self.fontMetrics().horizontalAdvance(teks.upper()) + 18)


class Tab(QTabWidget):
    """
    Baris tab bergaya dokumen.

    Garis dasar bawaan Qt tidak dipakai. Qt menggambarnya memakai warna
    palet sistem, berwarna putih dan tidak sebaris dengan penanda tab
    terpilih, sehingga penanda tembaga tampak melayang terpisah dari baris
    tabnya. Di sini garis pemisah digambar sendiri tepat pada baris piksel
    yang sama dengan penanda, dan bagian di bawah tab terpilih dilewati
    supaya penandanya terlihat menyambung ke isi halaman.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDocumentMode(True)
        self.tabBar().setDrawBase(False)
        self.tabBar().setExpanding(False)

    def paintEvent(self, ev):
        super().paintEvent(ev)
        bar = self.tabBar()
        if bar.count() == 0:
            return
        y = bar.geometry().bottom()
        aktif = bar.tabRect(self.currentIndex())
        aktif.moveLeft(aktif.left() + bar.x())
        p = QPainter(self)
        p.setPen(QPen(QColor(C.BORDER), 1))
        if aktif.left() > 0:
            p.drawLine(0, y, aktif.left() - 1, y)
        if aktif.right() < self.width():
            p.drawLine(aktif.right() + 1, y, self.width(), y)
        p.end()


# ==========================================================================
# TABEL
# ==========================================================================
class _LencanaStatus(QStyledItemDelegate):
    """
    Gambar isi kolom status sebagai lencana kecil, bukan teks polos.

    Warna lencana mengikuti warna teks yang sudah dipasang pada sel, sehingga
    status lunas, terlambat, dan batal tetap terbaca cepat tanpa perlu
    menambah kolom baru. Latar lencana memakai warna yang sama dengan
    transparansi rendah agar tetap tenang di antara angka tabel.
    """

    def paint(self, painter, option, index):
        opsi = QStyleOptionViewItem(option)
        self.initStyleOption(opsi, index)
        teks = opsi.text
        opsi.text = ""

        gaya = (opsi.widget.style() if opsi.widget is not None
                else QApplication.style())
        gaya.drawControl(QStyle.CE_ItemViewItem, opsi, painter, opsi.widget)
        if not teks:
            return

        data_warna = index.data(Qt.ForegroundRole)
        if isinstance(data_warna, QBrush):
            warna = data_warna.color()
        elif isinstance(data_warna, QColor):
            warna = data_warna
        else:
            warna = QColor(C.TEXT_MUTED)

        font = QFont(opsi.font)
        font.setWeight(QFont.DemiBold)
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setFont(font)
        fm = painter.fontMetrics()
        lebar_teks = fm.horizontalAdvance(teks)
        tinggi = max(20, fm.height() + 5)
        # Padding lencana dibuat ringkas agar status seperti "Disetujui"
        # tetap terbaca utuh pada kolom selebar judulnya.
        lebar = min(lebar_teks + 14, max(26, opsi.rect.width() - 8))
        kotak = QRectF(opsi.rect.left() + 4,
                       opsi.rect.center().y() - tinggi / 2 + 1,
                       lebar, tinggi)

        isi = QColor(warna)
        isi.setAlpha(22)
        tepi = QColor(warna)
        tepi.setAlpha(60)
        painter.setPen(QPen(tepi, 1))
        painter.setBrush(isi)
        painter.drawRoundedRect(kotak, 3, 3)
        painter.setPen(warna)
        painter.drawText(kotak.adjusted(5, 0, -5, 0), Qt.AlignCenter,
                         fm.elidedText(teks, Qt.ElideRight,
                                       max(8, int(kotak.width()) - 10)))
        painter.restore()


# Nama bulan untuk mengenali tanggal tampilan Indonesia, mis. "25 Okt 2026".
_BULAN_URUT = {
    nama.lower(): i + 1
    for i, nama in enumerate(config.MONTH_ABBR_ID + config.MONTH_NAMES_ID)
}
_POLA_TANGGAL = re.compile(r"^(\d{1,2})\s+([A-Za-z]+)\.?\s+(\d{4})(?:\s.*)?$")
_POLA_ISO = re.compile(r"^(\d{4})-(\d{2})-(\d{2})(?:[ T].*)?$")
# Angka tampilan Indonesia: rupiah, persen, kuantitas dengan satuan pendek.
_POLA_ANGKA = re.compile(
    r"^[+-]?\s*\(?\s*(?:Rp\.?\s*)?(\d[\d.,]*)\s*\)?\s*"
    r"(%|[A-Za-z]{1,12})?\s*$", re.IGNORECASE)
_KOSONG = {"", "-", "--", "n/a", "na", "tidak ada", "belum ada"}


def _nilai_angka(teks: str) -> Optional[float]:
    """Ubah angka tampilan Indonesia menjadi float, atau None bila bukan angka."""
    t = teks.strip()
    negatif = (t.startswith("(") and t.endswith(")")) or t.startswith("-")
    cocok = _POLA_ANGKA.match(t)
    if not cocok:
        return None
    token = cocok.group(1)
    try:
        if "," in token:
            # Koma adalah desimal; titik adalah pemisah ribuan.
            nilai = float(token.replace(".", "").replace(",", "."))
        elif "." in token:
            bagian = token.split(".")
            # "1.234" dan "1.234.567" adalah ribuan; "1.5" adalah desimal.
            if (len(bagian[-1]) == 3
                    and all(len(x) == 3 for x in bagian[1:])):
                nilai = float("".join(bagian))
            else:
                nilai = float(token)
        else:
            nilai = float(token)
    except ValueError:
        return None
    return -nilai if negatif else nilai


def _kunci_urut(teks: str) -> tuple:
    """
    Kunci pengurutan yang mengikuti makna isi sel.

    Tanpa kunci ini, kolom rupiah, persen, kuantitas, dan tanggal diurutkan
    sebagai teks: "Rp9.000" muncul setelah "Rp10.000", dan "3 Okt" sebelum
    "25 Sep". Nilai kosong diletakkan paling atas pada urutan menaik.
    """
    t = str(teks or "").strip()
    if not t or t.casefold() in _KOSONG:
        return (0, 0.0, "")

    cocok = _POLA_ISO.match(t)
    if cocok:
        try:
            urut = date(int(cocok.group(1)), int(cocok.group(2)),
                        int(cocok.group(3))).toordinal()
            return (1, float(urut), t)
        except ValueError:
            pass

    cocok = _POLA_TANGGAL.match(t)
    if cocok:
        bulan = _BULAN_URUT.get(cocok.group(2).casefold())
        if bulan:
            try:
                urut = date(int(cocok.group(3)), bulan,
                            int(cocok.group(1))).toordinal()
                return (1, float(urut), t)
            except ValueError:
                pass

    angka = _nilai_angka(t)
    if angka is not None:
        return (2, angka, t.casefold())
    return (3, 0.0, t.casefold())


class _ItemTabel(QTableWidgetItem):
    """Item tabel yang mengurutkan nominal, persen, dan tanggal secara benar."""

    def __lt__(self, lain):
        if isinstance(lain, QTableWidgetItem):
            return _kunci_urut(self.text()) < _kunci_urut(lain.text())
        return super().__lt__(lain)

    @classmethod
    def dari(cls, item: QTableWidgetItem) -> "_ItemTabel":
        """Salin item biasa menjadi item yang dapat diurutkan secara makna."""
        baru = cls(item.text())
        baru.setTextAlignment(item.textAlignment())
        baru.setFlags(item.flags())
        baru.setFont(item.font())
        if item.foreground().style() != Qt.NoBrush:
            baru.setForeground(item.foreground())
        if item.background().style() != Qt.NoBrush:
            baru.setBackground(item.background())
        baru.setToolTip(item.toolTip())
        baru.setStatusTip(item.statusTip())
        baru.setWhatsThis(item.whatsThis())
        baru.setSizeHint(item.sizeHint())
        # Hanya salin keadaan centang bila item asal memang memilikinya.
        # Nilai bawaan QTableWidgetItem adalah "tidak dicentang", dan
        # menuliskannya kembali membuat setiap sel menampilkan kotak centang.
        if item.data(Qt.CheckStateRole) is not None:
            baru.setCheckState(item.checkState())
        if not item.icon().isNull():
            baru.setIcon(item.icon())
        data = item.data(Qt.UserRole)
        if data is not None:
            baru.setData(Qt.UserRole, data)
        return baru


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
        # Baris berselang-seling tipis: mata dapat mengikuti satu baris
        # sampai kolom terakhir tanpa kehilangan tempat.
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setShowGrid(False)
        # hover baris memudahkan mengikuti baris pada tabel berkolom banyak
        self.setMouseTracking(True)
        self.verticalHeader().setVisible(False)
        self.verticalHeader().setDefaultSectionSize(40)
        self.verticalHeader().setMinimumSectionSize(32)
        self.horizontalHeader().setHighlightSections(False)
        self.horizontalHeader().setFixedHeight(42)
        # Judul kolom mengikuti rata isinya: judul teks di kiri, judul angka
        # di kanan. Judul yang selalu di tengah membuat mata harus bergeser
        # dari judul ke angka pada setiap kolom.
        self.horizontalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        # Digit tabel memakai lebar sama supaya nominal pada baris berbeda
        # sejajar tepat di bawah satu sama lain.
        font_tabel = QFont(theme.FONT_UI)
        try:
            font_tabel.setFeature(QFont.Tag("tnum"), 1)
        except Exception:
            pass
        self.setFont(font_tabel)
        self.setSortingEnabled(True)
        self.horizontalHeader().setSortIndicatorShown(True)
        # Tabel yang memuat kotak isian tidak boleh diurutkan: Qt hanya
        # memindahkan item teks, sedangkan widget sel tetap di baris lama,
        # sehingga isian dan label barisnya bertukar tempat.
        self._punya_widget = False
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

    def _lepas_widget_sel(self, baris: int):
        """
        Buang seluruh widget sel pada satu baris.

        QTableWidget tidak membuang widget lama saat sel diganti atau baris
        dihapus. Widget itu tetap menjadi anak area gulir, tetap terlihat,
        dan tetap menerima klik. Saat tabel digambar ulang, tumpukan widget
        lama di atas sel baru dapat menutupi kolom akun atau bahkan menekan
        tombol hapus baris tanpa sengaja. Karena itu widget dilepas dan
        dihapus sendiri setiap kali sel atau baris dibuang.
        """
        for kolom in range(self.columnCount()):
            widget = self.cellWidget(baris, kolom)
            if widget is None:
                continue
            self.removeCellWidget(baris, kolom)
            widget.hide()
            widget.setParent(None)
            widget.deleteLater()

    def clearContents(self):
        for baris in range(self.rowCount()):
            self._lepas_widget_sel(baris)
        super().clearContents()
        self._perbarui_pesan_kosong()

    def setRowCount(self, baris: int):
        if baris < self.rowCount():
            for lama in range(baris, self.rowCount()):
                self._lepas_widget_sel(lama)
        super().setRowCount(baris)
        self._perbarui_pesan_kosong()

    def showEvent(self, event):
        super().showEvent(event)
        self._perbarui_pesan_kosong()

    def setItem(self, baris: int, kolom: int, item):
        """Bungkus item biasa agar seluruh kolom terurut sesuai maknanya."""
        if item is not None and not isinstance(item, _ItemTabel):
            item = _ItemTabel.dari(item)
        super().setItem(baris, kolom, item)

    def setCellWidget(self, baris: int, kolom: int, widget):
        """
        Pasang widget di dalam sel, lalu pastikan tingginya cukup.

        QTableWidget memaksa widget mengikuti tinggi baris bawaan (34 px).
        Kotak isian rupiah butuh ruang lebih besar, jadi teks yang diketik
        terpotong dan tidak terlihat. Tinggi baris dinaikkan mengikuti
        kebutuhan widget tertinggi pada baris itu.

        Tabel yang berisi widget tidak lagi dapat diurutkan. Qt hanya
        mengurutkan item teks dan tidak memindahkan widget sel, sehingga
        tombol serta kotak isian akan tertinggal di baris yang salah.
        """
        lama = self.cellWidget(baris, kolom)
        if lama is not None and lama is not widget:
            self.removeCellWidget(baris, kolom)
            lama.hide()
            lama.setParent(None)
            lama.deleteLater()
        super().setCellWidget(baris, kolom, widget)
        if widget is not None:
            self._punya_widget = True
            if self.isSortingEnabled():
                self.setSortingEnabled(False)
                self.horizontalHeader().setSortIndicatorShown(False)
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
        # Delegate menggambar sel beberapa piksel lebih lebar daripada
        # hitungan padding saja. Tanpa cadangan ini, kolom yang "pas" tetap
        # memakai elipsis meski ruang tabel masih tersisa.
        sisa = 2 * margin + PADDING_SEL + CADANGAN_SEL

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
            if self.isColumnHidden(i):
                continue
            perlu[i] = self._lebar_perlu(i, judul)
            # Lebar rancangan tidak boleh lebih sempit daripada kebutuhan isi,
            # misalnya nominal besar yang melebihi lebar kolom bawaan.
            rancangan[i] = max(lebar, perlu[i]) if lebar > 0 else perlu[i]
        fleksibel = [i for i in fleksibel if i in rancangan]

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

        # ruang tidak cukup untuk seluruh isi. Kolom teks fleksibel adalah
        # penyebab utama kelebihan lebar (keterangan panjang), sedangkan
        # kolom angka dan tanggal tidak boleh dipotong. Bila kolom fleksibel
        # masih cukup lebar setelah menyusut, pakai seluruh ruang tersedia
        # supaya semua kolom terlihat tanpa menggeser mendatar.
        sisa_fleksibel = tersedia - sum(
            perlu[i] for i in perlu if i not in fleksibel)
        if fleksibel and sisa_fleksibel >= MIN_LEBAR_FLEKSIBEL * len(fleksibel):
            for i in perlu:
                lebar = (sisa_fleksibel // len(fleksibel)
                         if i in fleksibel else perlu[i])
                if self.columnWidth(i) != lebar:
                    self.setColumnWidth(i, lebar)
            return

        # teks panjang tetap dipertahankan utuh; tabel menggeser mendatar
        for i in perlu:
            if self.columnWidth(i) != perlu[i]:
                self.setColumnWidth(i, perlu[i])

    def isi(self, baris: list[list], warna_baris: dict = None,
            align_kanan: set = None, warna_sel: dict = None,
            tebal_kolom: set = None, kolom_penanda: int = None,
            tebal_baris: set = None):
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
          tebal_baris  : set indeks baris yang dicetak tebal, misalnya baris
                         subtotal pada laporan keuangan

        Warna baris dipakai untuk dua keperluan: menandai baris judul atau
        total, dan menandai keadaan baris data. Untuk yang kedua, mewarnai
        seluruh baris membuat nama, tanggal, dan nominal ikut berwarna
        sehingga sulit dibaca. Karena itu warna penanda dibatasi ke kolom
        status saja bila kolom itu ada.
        """
        align_kanan = align_kanan or set()

        # cari kolom status pada judul kolom
        if kolom_penanda is None:
            for i, (judul, _) in enumerate(getattr(self, "_kolom", [])):
                if "status" in judul.lower() or "keadaan" in judul.lower():
                    kolom_penanda = i
                    break
        # Lencana hanya dipasang pada kolom status. Kolom nominal yang diberi
        # warna penanda (mis. saldo piutang) tetap berupa angka biasa; angka
        # di dalam lencana sulit dibandingkan dan mudah disangka status.
        for i, (judul, _) in enumerate(getattr(self, "_kolom", [])):
            if "status" in judul.lower() or "keadaan" in judul.lower():
                self._pasang_lencana(i)
                break

        self.setSortingEnabled(False)
        self.setRowCount(0)
        self.setRowCount(len(baris))
        for r, data in enumerate(baris):
            for c, nilai in enumerate(data):
                if nilai is None:
                    nilai = ""
                item = _ItemTabel(str(nilai))
                # teks penuh selalu tersedia lewat tooltip meski kolom sempit
                item.setToolTip(str(nilai))
                if c in align_kanan:
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    font_angka = QFont(self.font())
                    try:
                        font_angka.setFeature(QFont.Tag("tnum"), 1)
                    except Exception:
                        pass
                    item.setFont(font_angka)
                else:
                    item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                if warna_sel and (r, c) in warna_sel:
                    item.setForeground(QColor(warna_sel[(r, c)]))
                elif warna_baris and r in warna_baris:
                    if kolom_penanda is None or c == kolom_penanda:
                        item.setForeground(QColor(warna_baris[r]))
                if ((tebal_kolom and c in tebal_kolom)
                        or (tebal_baris and r in tebal_baris)):
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                self.setItem(r, c, item)
        if not self._punya_widget:
            self.setSortingEnabled(True)
            self.horizontalHeader().setSortIndicatorShown(True)
        self._atur_rata_judul(align_kanan)
        self._ukur_perlu_isi(baris, align_kanan, tebal_kolom, tebal_baris)
        self._lebarkan_kolom_angka(baris, align_kanan, tebal_kolom, tebal_baris)
        # batas minimum kolom berubah setelah isi diukur, jadi lebarnya
        # dihitung ulang agar isi tidak terpotong
        kolom = getattr(self, "_kolom", None)
        if kolom:
            fleksibel = [i for i, (_, lebar) in enumerate(kolom) if lebar < 0]
            if fleksibel:
                self._seimbangkan_kolom(fleksibel, kolom)

    def tinggi_konten(self) -> int:
        """Tinggi yang dibutuhkan seluruh baris beserta judul kolom."""
        tinggi = self.horizontalHeader().height() + 2 * self.frameWidth()
        for r in range(self.rowCount()):
            if not self.isRowHidden(r):
                tinggi += self.rowHeight(r)
        return tinggi

    def sesuaikan_tinggi(self, minimum: int = 120, maksimum: int = 0):
        """
        Tetapkan tinggi tabel sesuai isinya.

        Laporan keuangan dibaca sebagai satu kesatuan; bila tabel dipaksa
        pendek, baris terakhir dan totalnya tersembunyi di balik gulir
        dalam tabel. Dengan tinggi mengikuti isi, satu-satunya gulir yang
        dipakai adalah gulir halaman.
        """
        tinggi = max(minimum, self.tinggi_konten())
        if maksimum:
            tinggi = min(tinggi, maksimum)
        self.setFixedHeight(tinggi)

    def _atur_rata_judul(self, align_kanan: set):
        """Samakan rata judul kolom dengan rata isinya."""
        for c in range(self.columnCount()):
            item = self.horizontalHeaderItem(c)
            if item is None:
                continue
            rata = Qt.AlignRight if c in align_kanan else Qt.AlignLeft
            item.setTextAlignment(rata | Qt.AlignVCenter)

    def _pasang_lencana(self, kolom: int):
        """Pasang penggambar lencana pada kolom status, sekali per tabel."""
        if not hasattr(self, "_lencana"):
            self._lencana = {}
        if kolom not in self._lencana:
            delegate = _LencanaStatus(self)
            self._lencana[kolom] = delegate
            self.setItemDelegateForColumn(kolom, delegate)

    def _ukur_perlu_isi(self, baris: list[list], align_kanan: set,
                        tebal_kolom: set = None, tebal_baris: set = None):
        """
        Catat lebar yang dibutuhkan tiap kolom untuk menampilkan isinya.

        Dipakai sebagai batas bawah saat kolom disusutkan: tanpa ini, kolom
        yang muat judulnya tetapi tidak muat isinya akan memotong isi, seperti
        nomor kontrak atau nama mitra yang panjang. Sel yang dicetak tebal
        memakai huruf lebih lebar, jadi lebarnya diukur dengan huruf tebal;
        bila diukur dengan huruf biasa, nominal seperti "Rp111.000.000"
        tetap terpotong meski kolom sudah dianggap cukup.
        """
        dasar = QFont(self.font())
        tebal = QFont(dasar)
        tebal.setBold(True)
        metrik_biasa = QFontMetrics(dasar)
        metrik_tebal = QFontMetrics(tebal)
        for c in range(self.columnCount()):
            perlu = 0
            for r, data in enumerate(baris):
                if c < len(data) and data[c] is not None:
                    pakai_tebal = ((tebal_kolom and c in tebal_kolom)
                                   or (tebal_baris and r in tebal_baris))
                    metrik = metrik_tebal if pakai_tebal else metrik_biasa
                    lebar = metrik.horizontalAdvance(str(data[c]))
                    if lebar > perlu:
                        perlu = lebar
            self._perlu_isi[c] = perlu

    def _lebarkan_kolom_angka(self, baris: list[list], align_kanan: set,
                              tebal_kolom: set = None,
                              tebal_baris: set = None):
        """Pastikan kolom angka cukup lebar untuk nominal terpanjang.

        Nominal rupiah yang terpotong membuat laporan salah dibaca, jadi
        kolom angka dilebarkan sesuai isinya (tanpa mengubah kolom teks).
        Huruf tebal pada kolom saldo membutuhkan ruang tambahan.
        """
        if not align_kanan:
            return
        dasar = QFont(self.font())
        tebal = QFont(dasar)
        tebal.setBold(True)
        metrik_biasa = QFontMetrics(dasar)
        metrik_tebal = QFontMetrics(tebal)
        for c in align_kanan:
            if c >= self.columnCount():
                continue
            perlu = 0
            for r, data in enumerate(baris):
                if c < len(data) and data[c] is not None:
                    pakai_tebal = ((tebal_kolom and c in tebal_kolom)
                                   or (tebal_baris and r in tebal_baris))
                    metrik = metrik_tebal if pakai_tebal else metrik_biasa
                    perlu = max(perlu, metrik.horizontalAdvance(
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

    # Signal(int) di PySide6 memakai int 32-bit, sehingga nominal di atas
    # Rp2.147.483.647 melempar OverflowError saat emit. object meneruskan
    # int Python apa adanya.
    valueChanged = Signal(object)

    def __init__(self, parent=None, placeholder: str = "0"):
        super().__init__(parent)
        self.setObjectName("MoneyInput")
        self.setPlaceholderText(placeholder)
        self.setAlignment(Qt.AlignRight)
        self._nilai = 0
        self._waktu_peringatan = 0.0
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
        # Nol di depan tidak menambah besaran nilai, jadi dibuang lebih dulu
        # agar "0003.000.000.000" tidak dianggap melewati batas digit.
        bersih = bersih.lstrip("0") or "0"
        # Diperiksa sebelum int(): konversi teks yang sangat panjang pun
        # dapat melempar ValueError karena batas digit Python.
        if len(bersih) > _BATAS_DIGIT:
            self._kembalikan_ke_nilai_sah()
            return
        baru = int(bersih)
        if baru > BATAS_NOMINAL:
            self._kembalikan_ke_nilai_sah()
            return
        if baru != self._nilai:
            self._nilai = baru
            self.valueChanged.emit(baru)
        terformat = _format_nominal(baru)
        if teks != terformat:
            self.blockSignals(True)
            self.setText(terformat)
            self.blockSignals(False)

    def _kembalikan_ke_nilai_sah(self):
        """Tolak angka di luar batas tanpa membuat aplikasi berhenti."""
        self.blockSignals(True)
        self.setText(_format_nominal(self._nilai))
        self.end(False)
        self.blockSignals(False)
        sekarang = time.monotonic()
        if sekarang - self._waktu_peringatan >= 2.0:
            self._waktu_peringatan = sekarang
            QTimer.singleShot(0, self._tampilkan_batas)

    def _tampilkan_batas(self):
        batas = f"Rp{_format_nominal(BATAS_NOMINAL)}"
        popup.peringatkan(self,
                          "Nominal terlalu besar",
                          f"Nominal yang Anda masukkan melebihi batas maksimum {batas}.\n\n"
                          "Angka dikembalikan ke nilai sebelumnya. Bila nilai transaksi "
                          "memang lebih besar, pecah menjadi beberapa transaksi.")

    def nilai(self) -> int:
        return self._nilai

    def set_nilai(self, v):
        self._nilai = int(v or 0)
        self.blockSignals(True)
        self.setText(_format_nominal(self._nilai) if self._nilai else "")
        self.blockSignals(False)

    def kosongkan(self):
        self.set_nilai(0)
        self.clear()


class InputQty(QLineEdit):
    """Kotak isian jumlah barang yang menerima angka desimal (mis. 1,5 kg)."""

    # object, bukan float: nilai diteruskan apa adanya tanpa pembulatan Qt.
    valueChanged = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("MoneyInput")
        self.setPlaceholderText("0")
        self.setAlignment(Qt.AlignRight)
        self._nilai = 0.0
        self.setValidator(QRegularExpressionValidator(
            QRegularExpression(r"^\d{0,12}(?:[.,]\d{0,3})?$"), self))
        self.textChanged.connect(self._on_text)
        self.setToolTip(
            "Masukkan jumlah barang. Gunakan koma atau titik untuk desimal, "
            "mis. 1,5.")

    def _on_text(self, teks: str):
        bersih = teks.strip().replace(",", ".")
        if bersih in ("", "."):
            nilai = 0.0
        else:
            try:
                nilai = float(bersih)
            except ValueError:
                return
        if abs(nilai - self._nilai) > 1e-9:
            self._nilai = nilai
            self.valueChanged.emit(nilai)

    def nilai(self) -> float:
        return self._nilai

    def set_nilai(self, v):
        self._nilai = max(0.0, float(v or 0))
        self.blockSignals(True)
        self.setText(f"{self._nilai:g}".replace(".", ",") if self._nilai else "")
        self.blockSignals(False)


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
                 buka_halaman=None, datar: bool = False):
        super().__init__(parent)
        self.setObjectName("TemuanCard")
        warna, _bg = theme.STATUS_COLORS.get(
            temuan.tingkat, (C.TEXT_MUTED, C.NEUTRAL_BG))

        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Penanda tingkat berupa garis tipis, bukan blok warna. Mata dapat
        # menemukan kelompok temuan tanpa garis itu menutupi isinya.
        rail = QFrame()
        rail.setFixedWidth(2)
        theme.latar(rail, f"background: {warna}; border: none;")
        outer.addWidget(rail)

        dalam = QVBoxLayout()
        dalam.setContentsMargins(17, 14, 18, 15)
        dalam.setSpacing(7)
        outer.addLayout(dalam, 1)

        # Kepala: tingkat dan kategori sebagai keterangan, judul sebagai isi.
        header = QHBoxLayout()
        header.setSpacing(7)
        lbl_tingkat = QLabel(temuan.label.upper())
        lbl_tingkat.setStyleSheet(
            f"color: {warna}; font-size: 10px; font-weight: 800; "
            "letter-spacing: 0.8px; background: transparent;")
        header.addWidget(lbl_tingkat)
        titik = QLabel("·")
        titik.setStyleSheet(
            f"color: {C.TEXT_FAINT}; font-size: 11px; background: transparent;")
        header.addWidget(titik)
        lbl_kat = QLabel(temuan.kategori)
        lbl_kat.setStyleSheet(
            f"color: {C.TEXT_FAINT}; font-size: {theme.FS_TINY}px; "
            "background: transparent;")
        header.addWidget(lbl_kat)
        header.addStretch()
        dalam.addLayout(header)

        lbl_judul = QLabel(temuan.judul)
        lbl_judul.setStyleSheet(
            f"font-family: '{theme.FONT_SERIF}', Georgia, serif; "
            f"font-size: 16px; font-weight: 600; color: {C.TEXT}; "
            "background: transparent;")
        lbl_judul.setWordWrap(True)
        dalam.addWidget(lbl_judul)

        if temuan.angka:
            lbl_angka = QLabel(temuan.angka)
            lbl_angka.setStyleSheet(
                f"font-family: '{theme.FONT_SERIF}', Georgia, serif; "
                f"font-size: {theme.FS_BODY}px; color: {warna}; "
                "font-weight: 600; background: transparent;")
            dalam.addWidget(lbl_angka)

        if ringkas:
            if temuan.tindakan:
                dalam.addWidget(self._blok("Yang perlu dilakukan",
                                           temuan.tindakan, C.TEXT))
        else:
            dalam.addWidget(self._blok("Apa artinya", temuan.penjelasan, C.TEXT))
            if temuan.tindakan:
                dalam.addWidget(self._blok("Yang perlu dilakukan",
                                           temuan.tindakan, C.TEXT))
            if temuan.dampak:
                dalam.addWidget(self._blok("Bila dibiarkan", temuan.dampak,
                                           C.WARNING))
            if temuan.dasar_hukum:
                lbl_h = QLabel(f" {temuan.dasar_hukum}")
                lbl_h.setWordWrap(True)
                lbl_h.setStyleSheet(
                    f"color: {C.TEXT_FAINT}; font-size: {theme.FS_TINY}px; "
                    "font-style: italic; background: transparent;")
                dalam.addWidget(lbl_h)

        # Tombol tindak lanjut: membuka halaman yang paling relevan untuk
        # menindaklanjuti temuan ini. Tanpa tombol ini, pengguna harus
        # mencari sendiri halamannya dari menu.
        halaman = getattr(temuan, "halaman", "")
        if halaman and buka_halaman is not None and not ringkas:
            baris_aksi = QHBoxLayout()
            baris_aksi.setContentsMargins(0, 3, 0, 0)
            baris_aksi.setSpacing(8)

            teks_tombol = self.NAMA_HALAMAN.get(halaman, "Buka Halaman")
            btn = tombol(teks_tombol, gaya="biasa")
            btn.clicked.connect(lambda _=False, h=halaman: buka_halaman(h))
            baris_aksi.addWidget(btn)
            baris_aksi.addStretch()
            dalam.addLayout(baris_aksi)

        if datar:
            self.setStyleSheet(
                f"QFrame#TemuanCard {{ background: transparent; "
                f"border: none; border-bottom: 1px solid {C.BORDER}; "
                "border-radius: 0; }")
        else:
            self.setStyleSheet(
                f"QFrame#TemuanCard {{ background: {C.SURFACE}; "
                f"border: 1px solid {C.BORDER}; "
                "border-radius: 3px; }}")

    def _blok(self, judul: str, isi: str, warna: str) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        l = QVBoxLayout(w)
        l.setContentsMargins(0, 2, 0, 0)
        l.setSpacing(2)
        j = QLabel(judul.upper())
        j.setStyleSheet(
            f"color: {C.TEXT_FAINT}; font-size: 9.5px; font-weight: 700; "
            "letter-spacing: 0.8px; background: transparent;")
        l.addWidget(j)
        t = QLabel(rata_kanan_kiri(isi))
        t.setTextFormat(Qt.RichText)
        t.setWordWrap(True)
        t.setStyleSheet(f"color: {warna}; font-size: {theme.FS_SMALL}px; "
                        "background: transparent; line-height: 155%;")
        t.setTextInteractionFlags(Qt.TextSelectableByMouse)
        l.addWidget(t)
        return w


# ==========================================================================
# ANGKA POKOK EDITORIAL
# ==========================================================================
class AngkaBuku(QWidget):
    """
    Satu angka pokok laporan: label renggang, nominal serif besar, keterangan.

    Dipakai pada pita kinerja dan ringkasan halaman. Angka mengecil sendiri
    bila ruangnya sempit, tetapi tidak pernah dipotong selama masih ada
    ukuran huruf yang masuk akal.
    """

    def __init__(self, label: str = "", nilai: str = "", hint: str = "",
                 warna: str = None, ukuran: int = 32, parent=None):
        super().__init__(parent)
        self._label_penuh = label
        self._nilai_penuh = nilai
        self._hint_penuh = hint
        self._warna = warna or C.TEXT
        self._ukuran = max(16, int(ukuran))
        self._ukuran_terpakai = self._ukuran

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(3)

        self.lbl_label = QLabel(label.upper())
        self.lbl_label.setObjectName("LedgerLabel")
        self.lbl_label.setWordWrap(True)
        self.lbl_label.setMinimumWidth(0)
        lay.addWidget(self.lbl_label)

        self.lbl_nilai = QLabel(nilai)
        self.lbl_nilai.setObjectName("LedgerAngka")
        self.lbl_nilai.setMinimumWidth(0)
        self.lbl_nilai.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        lay.addWidget(self.lbl_nilai)

        self.lbl_hint = QLabel(hint)
        self.lbl_hint.setObjectName("LedgerHint")
        self.lbl_hint.setWordWrap(True)
        self.lbl_hint.setMinimumWidth(0)
        self.lbl_hint.setVisible(bool(hint))
        lay.addWidget(self.lbl_hint)

        self._rapikan()

    def sizeHint(self):
        ukuran = super().sizeHint()
        ukuran.setHeight(max(ukuran.height(),
                             int(self._ukuran * 1.25) + 34))
        return ukuran

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._rapikan()

    def _rapikan(self):
        lebar = max(self.lbl_nilai.width(), 40)
        ukuran = self._ukuran
        while ukuran > 15:
            if QFontMetrics(theme.font_serif_angka(ukuran)) \
                    .horizontalAdvance(self._nilai_penuh) <= lebar:
                break
            ukuran -= 1
        self._ukuran_terpakai = ukuran
        self.lbl_nilai.setText(self._nilai_penuh)
        self.lbl_nilai.setStyleSheet(
            f"font-family: '{theme.FONT_SERIF}', Georgia, serif; "
            f"font-size: {ukuran}px; font-weight: 600; "
            f"color: {self._warna}; background: transparent;")
        # Baris angka tidak boleh dipaksa lebih tinggi daripada hurufnya;
        # tanpa ini tinggi label mengikuti ukuran saran lama saat huruf
        # mengecil dan menyisakan rongga di bawah angka.
        self.lbl_nilai.setMinimumHeight(
            QFontMetrics(theme.font_serif_angka(ukuran)).height() + 2)

    def set_nilai(self, nilai: str, warna: str = None):
        self._nilai_penuh = nilai
        if warna:
            self._warna = warna
        self.lbl_nilai.setToolTip(nilai)
        self._rapikan()
        self.updateGeometry()

    def set_label(self, label: str):
        self._label_penuh = label
        self.lbl_label.setText(label.upper())
        self.lbl_label.setToolTip(label)

    def set_hint(self, hint: str):
        self._hint_penuh = hint
        self.lbl_hint.setText(hint)
        self.lbl_hint.setVisible(bool(hint))


class MeterBatas(QWidget):
    """
    Meter tipis untuk posisi sebuah nilai terhadap batas tertentu.

    Nilai di atas 100% tetap digambar penuh dengan warna batas, sedangkan
    angka persisnya dibaca dari keterangan di bawah meter. Garis kecil pada
    80% menandai wilayah waspada sebelum batas tercapai.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._nilai = 0.0
        self._warna = C.ACCENT
        self.setFixedHeight(11)
        self.setMinimumWidth(70)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def set_nilai(self, persen: float, warna: str = None):
        self._nilai = max(0.0, min(100.0, float(persen or 0)))
        if warna:
            self._warna = warna
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        kiri, kanan = 0.0, float(self.width())
        y = 4.0
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(C.BORDER))
        p.drawRoundedRect(QRectF(kiri, y, max(0.0, kanan - kiri), 4), 2, 2)
        if self._nilai > 0:
            isi = (kanan - kiri) * self._nilai / 100.0
            p.setBrush(QColor(self._warna))
            p.drawRoundedRect(QRectF(kiri, y, max(2.0, isi), 4), 2, 2)
        p.setPen(QPen(QColor(C.BORDER_STRONG), 1))
        p.drawLine(int(kiri + (kanan - kiri) * 0.8), 1,
                   int(kiri + (kanan - kiri) * 0.8), 10)
        p.end()


# ==========================================================================
# SKOR GAUGE (lingkaran skor)
# ==========================================================================
class SkorGauge(QWidget):
    """
    Skor kesehatan sebagai angka besar dan meter tipis.

    Angka adalah informasi utama, sedangkan meter hanya menunjukkan
    posisinya pada skala 0-100. Lencana dan cincin donat tidak dipakai:
    keduanya membuat penilaian terlihat seperti kartu permainan, bukan
    bagian dari laporan keuangan.
    """

    def __init__(self, parent=None, ukuran: int = 150):
        super().__init__(parent)
        self.skor = 0
        self.label = ""
        self.grade = ""
        self.belum_dinilai = False
        self.setFixedWidth(max(138, int(ukuran)))
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)

        baris = QHBoxLayout()
        baris.setSpacing(6)
        self.lbl_skor = QLabel("0")
        self.lbl_skor.setAlignment(Qt.AlignLeft | Qt.AlignBottom)
        baris.addWidget(self.lbl_skor, 0, Qt.AlignBottom)
        self.lbl_sufiks = QLabel("/ 100")
        self.lbl_sufiks.setStyleSheet(
            f"font-size: {theme.FS_SMALL}px; color: {C.TEXT_FAINT}; "
            "background: transparent; padding-bottom: 12px;")
        baris.addWidget(self.lbl_sufiks, 0, Qt.AlignBottom)
        baris.addStretch()
        lay.addLayout(baris)

        self.lbl_grade = QLabel("")
        self.lbl_grade.setWordWrap(True)
        lay.addWidget(self.lbl_grade)

        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(5)
        lay.addSpacing(5)
        lay.addWidget(self.bar)

        self.lbl_hint = QLabel("Skor kesehatan keuangan")
        self.lbl_hint.setStyleSheet(
            f"font-size: {theme.FS_TINY}px; color: {C.TEXT_FAINT}; "
            "background: transparent;")
        self.lbl_hint.setWordWrap(True)
        lay.addWidget(self.lbl_hint)
        self._terapkan()

    def set_skor(self, skor: int, label: str = "", belum_dinilai: bool = False,
                 grade: str = ""):
        self.skor = max(0, min(100, int(skor)))
        self.label = label
        self.grade = grade
        self.belum_dinilai = belum_dinilai
        self._terapkan()

    def _terapkan(self):
        if self.belum_dinilai:
            angka = "–"
            warna = C.TEXT_MUTED
            warna_bar = C.BORDER_STRONG
            grade = "Belum ada data untuk dinilai"
            hint = "Catat transaksi agar skor dapat dihitung"
        else:
            angka = str(self.skor)
            if self.skor >= 70:
                warna, warna_bar = C.SUCCESS, C.SUCCESS
            elif self.skor >= 55:
                warna, warna_bar = C.WARNING, C.WARNING
            else:
                warna, warna_bar = C.DANGER, C.DANGER
            grade = self.label or "Dinilai"
            if self.grade and self.grade != "N/A":
                grade = f"Grade {self.grade} · {grade}"
            hint = "Skor kesehatan keuangan"

        self.lbl_skor.setText(angka)
        self.lbl_skor.setStyleSheet(
            f"font-family: '{theme.FONT_SERIF}', Georgia, serif; "
            f"font-size: 52px; font-weight: 600; color: {warna}; "
            "background: transparent;")
        self.lbl_grade.setText(grade.upper())
        self.lbl_grade.setStyleSheet(
            f"font-size: 10px; font-weight: 700; "
            f"color: {warna}; letter-spacing: 0.3px; background: transparent;")
        self.lbl_hint.setText(hint)
        self.bar.setValue(0 if self.belum_dinilai else self.skor)
        self.bar.setStyleSheet(
            f"QProgressBar {{ background: {C.NEUTRAL_BG}; border: none; "
            "border-radius: 2px; }"
            f"QProgressBar::chunk {{ background: {warna_bar}; "
            "border-radius: 2px; }")


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
        self.lbl.setObjectName("LedgerLabel")
        self.lbl.setToolTip(label)
        self.lbl.setWordWrap(True)
        self.lbl.setMinimumWidth(0)
        lay.addWidget(self.lbl)
        self.v = QLabel(nilai)
        self.v.setObjectName("MiniAngka")
        self.v.setToolTip(nilai)
        self.v.setMinimumWidth(0)
        self.v.setStyleSheet(
            f"font-family: '{theme.FONT_SERIF}', Georgia, serif; "
            f"font-size: 16px; font-weight: 600; color: {warna or C.TEXT}; "
            "background: transparent;")
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
                f"font-family: '{theme.FONT_SERIF}', Georgia, serif; "
                f"font-size: 16px; font-weight: 600; color: {warna}; "
                "background: transparent;")

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
        # Halaman dengan banyak tombol mengizinkan tombolnya turun ke baris
        # kedua. Keputusan diambil dari lebar yang tersedia, bukan dipaksa:
        # dashboard lapang tetap ringkas, sedangkan tabel dengan tombol
        # panjang tidak mendesak judul keluar tepi.
        self._aksi_boleh_terpisah = False

        # Susunan luar selalu menurun. Baris judul dan tombol aksi berada di
        # dalamnya, sehingga memindahkan tombol ke baris tersendiri cukup
        # dengan memindahkan satu wadah. Mengganti layout induk saat berjalan
        # membuat Qt menolak layout baru dan seluruh header menyusut menjadi
        # tinggi nol, sehingga judul halaman hilang.
        self._luar = QVBoxLayout(self)
        self._luar.setContentsMargins(0, 0, 0, 0)
        self._luar.setSpacing(10)

        # Baris utama: judul di kiri, tombol aksi di kanan.
        self._baris = QHBoxLayout()
        self._baris.setSpacing(14)

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
        self._baris.addWidget(self._teks, 1)

        # Wadah tombol aksi. Lebar minimumnya dijaga agar tombol tidak
        # dihimpit sampai teksnya terpotong.
        self._wadah_aksi = QWidget()
        self.aksi = QHBoxLayout(self._wadah_aksi)
        self.aksi.setContentsMargins(0, 0, 0, 0)
        self.aksi.setSpacing(8)
        self._baris.addWidget(self._wadah_aksi, 0, Qt.AlignTop)
        self._luar.addLayout(self._baris)

        # Wadah baris kedua. Kosong dan tersembunyi selama tombol masih muat
        # di samping judul; wadah tombol dipindahkan ke sini bila tidak.
        self._wadah_baris_aksi = QWidget()
        self._baris_aksi = QHBoxLayout(self._wadah_baris_aksi)
        self._baris_aksi.setContentsMargins(0, 0, 0, 0)
        self._baris_aksi.addStretch()
        self._wadah_baris_aksi.hide()
        self._luar.addWidget(self._wadah_baris_aksi)

    def tambah_aksi(self, tombol: QPushButton):
        self.aksi.addWidget(tombol)
        self._wadah_aksi.setMinimumWidth(self.aksi.sizeHint().width())
        if self._aksi_boleh_terpisah:
            self._atur_aksi(self.width())
        return tombol

    def resizeEvent(self, peristiwa):
        super().resizeEvent(peristiwa)
        if self._aksi_boleh_terpisah:
            self._atur_aksi(peristiwa.size().width())

    def _atur_aksi(self, lebar: int):
        """
        Pilih posisi tombol aksi sesuai lebar header.

        Tombol tetap sejajar judul bila masih menyisakan ruang yang cukup
        untuk judul; bila tidak, tombol turun ke baris kedua. Perpindahan
        hanya dilakukan saat posisinya memang berubah, supaya tata letak
        tidak dihitung ulang tanpa henti.
        """
        # Ruang yang harus tetap tersedia untuk judul dan subjudul.
        LEBAR_JUDUL = 340
        perlu_inline = self._wadah_aksi.sizeHint().width() + LEBAR_JUDUL
        pisah = self._aksi_boleh_terpisah and perlu_inline > lebar
        if pisah == self._aksi_terpisah:
            return

        if pisah:
            self._baris.removeWidget(self._wadah_aksi)
            self._baris_aksi.addWidget(self._wadah_aksi)
            self._wadah_baris_aksi.show()
        else:
            self._baris_aksi.removeWidget(self._wadah_aksi)
            self._baris.addWidget(self._wadah_aksi, 0, Qt.AlignTop)
            self._wadah_baris_aksi.hide()

        self._aksi_terpisah = pisah
        self.updateGeometry()

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

        def nama_perusahaan() -> str:
            # Kop cetak memuat nama perusahaan. Halaman tidak perlu
            # mengirimkannya sendiri karena semua halaman memakai ctx yang
            # sama.
            ctx = getattr(halaman, "ctx", None)
            cid = getattr(ctx, "company_id", None)
            if not cid:
                return ""
            try:
                from .. import services
                comp = services.get_company(cid)
                return (comp or {}).get("nama", "")
            except Exception:
                return ""

        def penanda_dokumen() -> dict:
            # Nama pengguna yang sedang masuk menjadi penanda tangan bawaan;
            # pengaturan cetak tetap dapat menggantinya.
            ctx = getattr(halaman, "ctx", None)
            if ctx is None:
                return {}
            kota = ""
            cid = getattr(ctx, "company_id", None)
            if cid:
                try:
                    from .. import services
                    kota = (services.get_company(cid) or {}).get("kota", "")
                except Exception:
                    kota = ""
            return {
                "nama": getattr(ctx, "full_name", "")
                        or getattr(ctx, "username", ""),
                "kota": kota,
            }

        def lakukan_ekspor():
            data = ambil_data()
            if not data:
                return
            sub = self.lbl_sub.text()
            ekspor_halaman(halaman, self._judul_ekspor, sub, data,
                           nama_berkas=self._judul_ekspor,
                           perusahaan=nama_perusahaan(),
                           penanda=penanda_dokumen())

        def lakukan_cetak():
            data = ambil_data()
            if not data:
                return
            sub = self.lbl_sub.text()
            cetak_halaman(halaman, self._judul_ekspor, sub, data,
                          perusahaan=nama_perusahaan(),
                          penanda=penanda_dokumen())

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
        if self._aksi_terpisah:
            sisa = max(120, lebar)
            tinggi = self._tinggi_judul(sisa) + self._tinggi_sub(sisa) + 3
            tinggi += self._luar.spacing() + self._wadah_aksi.sizeHint().height()
            return tinggi

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
        if self._aksi_boleh_terpisah:
            return
        self._aksi_boleh_terpisah = True
        self._atur_aksi(self.width())

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

    warna_latar, warna_teks, warna_tepi, warna_hover, warna_tekan = \
        GAYA_TOMBOL.get(gaya, (None, None, None, None, None))
    if warna_latar:
        aturan = (
            f"QPushButton {{ background: {warna_latar}; color: {warna_teks}; "
            f"border: 1px solid {warna_tepi}; border-radius: {theme.SUDUT_KONTROL}px; "
            f"padding: 7px 14px; font-size: {theme.FS_BODY}px; font-weight: 600; }}"
            f"QPushButton:hover {{ background: {warna_hover}; }}"
            f"QPushButton:pressed {{ background: {warna_tekan}; }}")
        t.setStyleSheet(aturan)

    if ikon:
        warna = {"primary": icons.WARNA_TERANG,
                 "danger": icons.WARNA_TERANG}.get(gaya, icons.WARNA_GELAP)
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

            # Lewati label yang tidak berubah sejak pengukuran terakhir.
            # Ukuran huruf dan panjang teks ikut diperiksa: keduanya dapat
            # berubah tanpa mengubah lebar label, misalnya saat pengguna
            # memilih ukuran teks yang lebih besar.
            kunci = (lebar, lbl.font().pixelSize(), len(lbl.text()))
            if catatan.get(id(lbl)) == kunci:
                continue

            perlu = lbl.heightForWidth(lebar)
            if perlu > 0:
                if lbl.minimumHeight() != perlu:
                    lbl.setMinimumHeight(perlu)
                # Tinggi maksimum ikut dipatok. Qt menghitung ukuran saran
                # label berbalut pada lebar bawaan yang sempit, sehingga
                # tanpa batas atas tata letak menyisakan ruang kosong besar
                # di dalam kartu.
                if lbl.maximumHeight() != perlu:
                    lbl.setMaximumHeight(perlu)
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

    Ukuran saran Qt untuk label berbalut tidak dapat dipakai: nilainya
    dihitung pada lebar bawaan yang sempit, sehingga bisa tiga kali lebih
    tinggi daripada kebutuhan pada lebar sebenarnya. Sisa ruang itu membuat
    kartu tampak berongga. Karena itu sizeHint() memakai hasil pengukuran
    sendiri setelah label pernah ditata.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._tinggi_terukur = 0

    def sizeHint(self):
        ukuran = super().sizeHint()
        if self.wordWrap() and self._tinggi_terukur > 0:
            ukuran.setHeight(self._tinggi_terukur)
        return ukuran

    def setText(self, teks):
        super().setText(teks)
        # Teks baru belum diukur. Ukuran lama tidak boleh dipakai, karena
        # dapat memotong kalimat yang lebih panjang.
        self._tinggi_terukur = 0
        self.updateGeometry()

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
        if self._tinggi_terukur != perlu:
            self._tinggi_terukur = perlu
            self.updateGeometry()
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


def label_ringkas(teks: str = "") -> QLabel:
    """Label keterangan yang mengisi sisa baris dan rata kanan.

    Dipakai untuk ringkasan seperti "25 invoice · total piutang ...".
    Label ini diberi faktor regang 1 oleh pemanggil, sehingga memakai
    seluruh ruang yang tersisa: tetap satu baris saat lapang, dan hanya
    membungkus bila jendela benar-benar sempit.
    """
    l = QLabel(teks)
    l.setObjectName("Muted")
    l.setWordWrap(True)
    l.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
    l.setMinimumWidth(0)
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


def set_combo_kandidat(combo: QComboBox, kandidat: list[str]) -> str:
    """
    Pilih kode akun pertama yang memang ada pada bagan akun perusahaan.

    Kode akun bawaan berbeda antar bentuk badan usaha. Memilih satu kode
    secara tetap membuat pilihan kosong atau salah pada bentuk lain, jadi
    daftar kandidat dicoba berurutan dan pilihan yang berlaku dikembalikan.
    """
    for data in kandidat:
        if set_combo_by_data(combo, data):
            return data
    return combo.currentData() or ""


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

    awal = "Lengkapi dulu profil perusahaan."
    if tindakan:
        awal = f"Belum dapat {tindakan}, karena profil perusahaan belum ada."

    popup.beri_tahu(parent,
                    "Profil perusahaan belum ada",
                    f"{awal}\n\n"
                    "Langkah yang perlu dilakukan:\n"
                    "1. Buka menu Data Usaha, lalu pilih Data Perusahaan\n"
                    "2. Isi nama perusahaan dan bentuk badan usaha\n"
                    "3. Tekan tombol Buat Perusahaan\n\n"
                    "Setelah profil perusahaan dibuat, seluruh menu pembukuan "
                    "langsung dapat dipakai.")


def perlu_dipilih(parent=None, apa: str = "satu baris data") -> None:
    """Beri tahu pengguna bahwa belum ada baris yang dipilih."""

    popup.beri_tahu(parent,
                    "Belum ada yang dipilih",
                    f"Pilih dulu {apa} pada tabel, lalu ulangi tindakannya.")
