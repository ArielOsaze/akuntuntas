"""Daftar pilihan bentuk badan usaha dengan tampilan dua baris.

Setiap pilihan menampilkan nama bentuk badan pada baris pertama dan standar
akuntansi yang dipakai pada baris kedua. Tampilan dua baris dipilih karena
teks gabungan satu baris menjadi terlalu panjang sehingga meluber keluar
kotak pilihan.

Ikon dipakai untuk membedakan bentuk badan: orang pribadi, badan usaha, dan
koperasi. Warna ikon mengikuti tema aplikasi.
"""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import (
    QComboBox, QStyle, QStyledItemDelegate, QStyleOptionViewItem,
)

from . import icons
from .theme import C

# Tinggi tiap baris pilihan. Cukup lega untuk dua baris teks dan ikon.
TINGGI_BARIS = 56
LEBAR_IKON = 34


class DelegasiBentukBadan(QStyledItemDelegate):
    """Gambar satu pilihan bentuk badan: ikon, nama, dan keterangan SAK."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._font_nama = QFont()
        self._font_nama.setPointSize(10)
        self._font_nama.setWeight(QFont.DemiBold)

        self._font_kecil = QFont()
        self._font_kecil.setPointSize(8)

    def sizeHint(self, opsi: QStyleOptionViewItem, indeks) -> QSize:
        return QSize(opsi.rect.width(), TINGGI_BARIS)

    def paint(self, pelukis: QPainter, opsi: QStyleOptionViewItem, indeks):
        pelukis.save()

        data = indeks.data(Qt.UserRole) or {}
        nama = data.get("nama", indeks.data(Qt.DisplayRole) or "")
        sak = data.get("sak", "")
        nama_ikon = data.get("ikon", "perusahaan")

        dipilih = bool(opsi.state & QStyle.State_Selected)
        disorot = bool(opsi.state & QStyle.State_MouseOver)

        kotak = opsi.rect.adjusted(3, 2, -3, -2)

        if dipilih:
            pelukis.setBrush(QColor(C.PRIMARY))
            pelukis.setPen(Qt.NoPen)
            pelukis.drawRoundedRect(kotak, 7, 7)
        elif disorot:
            pelukis.setBrush(QColor(C.SURFACE_ALT))
            pelukis.setPen(Qt.NoPen)
            pelukis.drawRoundedRect(kotak, 7, 7)

        warna_teks = C.TEXT_INVERSE if dipilih else C.TEXT
        warna_sak = C.SIDEBAR_TEXT if dipilih else C.TEXT_MUTED
        warna_ikon = "#FFFFFF" if dipilih else C.PRIMARY

        # ikon di sisi kiri
        ukuran = 18
        x_ikon = kotak.left() + 11
        y_ikon = kotak.top() + (kotak.height() - ukuran) // 2
        pix = icons.pixmap(nama_ikon, warna_ikon, ukuran)
        pelukis.drawPixmap(x_ikon, y_ikon, pix)

        # nama bentuk badan
        x_teks = x_ikon + ukuran + 11
        pelukis.setFont(self._font_nama)
        pelukis.setPen(QColor(warna_teks))
        tinggi_nama = pelukis.fontMetrics().height()
        pelukis.drawText(x_teks, kotak.top() + 9 + tinggi_nama,
                         nama)

        # keterangan standar akuntansi
        if sak:
            pelukis.setFont(self._font_kecil)
            pelukis.setPen(QColor(warna_sak))
            tinggi_kecil = pelukis.fontMetrics().height()
            pelukis.drawText(x_teks,
                             kotak.top() + 13 + tinggi_nama + tinggi_kecil,
                             f"Standar: {sak}")

        pelukis.restore()


# Ikon yang mewakili tiap bentuk badan. Dipilih agar mudah dibedakan
# sekilas: orang pribadi, badan usaha, dan koperasi.
IKON_BENTUK = {
    "umkm_op": "pengguna",
    "pt_perorangan": "perusahaan",
    "pt": "perusahaan",
    "cv": "mitra",
    "koperasi": "mitra",
    "yayasan": "perusahaan",
    "perkumpulan": "mitra",
}


def combo_bentuk_badan(jenis_entitas: dict) -> QComboBox:
    """
    Buat daftar pilihan bentuk badan usaha dengan tampilan dua baris.

    `jenis_entitas` adalah kamus config.ENTITY_TYPES.
    """
    c = QComboBox()
    c.setItemDelegate(DelegasiBentukBadan(c))
    c.setMinimumHeight(38)

    for kode, info in jenis_entitas.items():
        c.addItem(info["nama"], kode)
        posisi = c.count() - 1
        c.setItemData(posisi, {
            "nama": info["nama"],
            "sak": info.get("sak", ""),
            "ikon": IKON_BENTUK.get(kode, "perusahaan"),
        }, Qt.UserRole)
        # Kode bentuk badan disimpan terpisah pada peran tersendiri, karena
        # peran utama dipakai untuk keterangan tampilan daftar pilihan.
        c.setItemData(posisi, kode, Qt.UserRole + 1)

    # Lebar daftar dihitung dari teks terpanjang yang benar-benar dirender.
    # Memakai perkiraan jumlah huruf membuat nama panjang terpotong.
    from PySide6.QtGui import QFontMetrics

    metrik_nama = QFontMetrics(DelegasiBentukBadan(c)._font_nama)
    metrik_kecil = QFontMetrics(DelegasiBentukBadan(c)._font_kecil)

    lebar_teks = 0
    for info in jenis_entitas.values():
        w_nama = metrik_nama.horizontalAdvance(info["nama"])
        w_sak = metrik_kecil.horizontalAdvance(
            f"Standar: {info.get('sak', '')}")
        lebar_teks = max(lebar_teks, w_nama, w_sak)

    # ruang untuk ikon, jarak, dan bingkai; sisakan ruang scrollbar
    lebar_daftar = lebar_teks + LEBAR_IKON + 40
    c.view().setMinimumWidth(min(560, max(340, lebar_daftar)))
    c.setMinimumWidth(300)
    return c
