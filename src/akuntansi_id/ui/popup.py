"""
AkunTuntas - Popup Pesan Bergaya Aplikasi
=========================================
Popup bawaan Qt (QMessageBox) tampak seperti jendela sistem: ikon besar
berwarna menyala, sudut tajam, tombol kecil berjarak rapat, dan tata letak
yang sama sekali tidak seragam dengan sisa aplikasi. Modul ini menyediakan
popup yang menyatu dengan tampilan aplikasi.

Tiga hal yang membuatnya berbeda dari bawaan:

1. **Ikon sendiri, bukan ikon sistem.** Ikon digambar memakai modul ikon
   aplikasi, dengan warna yang sesuai maksud pesan.
2. **Tombol mengikuti gaya aplikasi.** Tombol utama memakai warna merek,
   tombol batal memakai garis tepi, dan lebarnya cukup untuk ditekan.
3. **Dapat memuat tombol tambahan.** Popup dapat memuat lebih dari dua
   pilihan, misalnya "Beli lisensi", "Aktifkan lisensi", dan "Nanti".

Pemakaian:

    from . import popup

    popup.beri_tahu(self, "Judul", "Isi pesan")
    popup.peringatkan(self, "Judul", "Isi pesan")
    popup.galat(self, "Judul", "Isi pesan")
    if popup.tanya(self, "Judul", "Isi pesan"):
        ...

    pilihan = popup.pilih(self, "Judul", "Isi", [
        ("beli", "Beli lisensi", "primary"),
        ("aktifkan", "Aktifkan lisensi", "biasa"),
        ("nanti", "Nanti", "biasa"),
    ])
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

from . import theme
from .theme import C

# Jenis pesan beserta warna dan nama ikonnya.
JENIS = {
    "info": (C.PRIMARY, "info"),
    "tanya": (C.PRIMARY, "bantuan"),
    "sukses": (C.SUCCESS, "aktif"),
    "peringatan": (C.WARNING, "peringatan"),
    "galat": (C.DANGER, "peringatan"),
}


class KotakPesan(QDialog):
    """
    Popup pesan bergaya aplikasi.

    Dipakai lewat fungsi beri_tahu, peringatkan, galat, tanya, dan pilih.
    Kelas ini tidak dipakai langsung supaya pemanggilnya ringkas.
    """

    def __init__(self, induk, judul: str, isi: str, jenis: str = "info",
                 rincian: str = "", lebar: int = 540):
        super().__init__(induk)
        self.setWindowTitle(judul)
        self.setModal(True)
        self._pilihan = ""

        warna, nama_ikon = JENIS.get(jenis, JENIS["info"])

        luar = QVBoxLayout(self)
        luar.setContentsMargins(0, 0, 0, 0)
        luar.setSpacing(0)

        # ---------------------------------------------------------- kepala
        kepala = QFrame()
        theme.latar(kepala, f"background: {C.SURFACE}; border: none; "
                            f"border-bottom: 1px solid {C.BORDER};")
        kl = QHBoxLayout(kepala)
        kl.setContentsMargins(24, 20, 24, 18)
        kl.setSpacing(14)

        # Lingkaran berwarna berisi ikon: menandai maksud pesan tanpa ikon
        # sistem yang besar dan menyala.
        lencana = QLabel()
        lencana.setFixedSize(38, 38)
        lencana.setAlignment(Qt.AlignCenter)
        lencana.setPixmap(
            __import__("akuntansi_id.ui.icons", fromlist=["icons"])
            .pixmap(nama_ikon, warna, 20))
        theme.latar(lencana,
                    f"background: {C.SURFACE}; border: 2px solid {warna}; "
                    f"border-radius: 19px;")
        kl.addWidget(lencana, 0, Qt.AlignTop)

        kolom = QVBoxLayout()
        kolom.setSpacing(5)

        lbl_judul = QLabel(judul)
        lbl_judul.setWordWrap(True)
        lbl_judul.setStyleSheet(
            f"font-size: {theme.FS_H2}px; font-weight: 700; color: {C.TEXT}; "
            "background: transparent;")
        kolom.addWidget(lbl_judul)

        lbl_isi = QLabel(isi)
        lbl_isi.setWordWrap(True)
        lbl_isi.setTextFormat(Qt.RichText)
        lbl_isi.setStyleSheet(
            f"font-size: {theme.FS_PESAN}px; color: {C.TEXT}; "
            "background: transparent; line-height: 170%;")
        kolom.addWidget(lbl_isi)

        if rincian:
            lbl_rinci = QLabel(rincian)
            lbl_rinci.setWordWrap(True)
            lbl_rinci.setStyleSheet(
                f"font-size: {theme.FS_BODY}px; color: {C.TEXT_MUTED}; "
                "background: transparent; line-height: 160%;")
            kolom.addWidget(lbl_rinci)

        kl.addLayout(kolom, 1)
        luar.addWidget(kepala)

        # ------------------------------------------------------------ isi
        self.badan = QWidget()
        bl = QVBoxLayout(self.badan)
        bl.setContentsMargins(24, 18, 24, 18)
        bl.setSpacing(12)
        luar.addWidget(self.badan, 1)

        # ---------------------------------------------------------- tombol
        self.kaki = QFrame()
        theme.latar(self.kaki, f"background: {C.SURFACE_ALT}; border: none; "
                               f"border-top: 1px solid {C.BORDER};")
        kkl = QHBoxLayout(self.kaki)
        kkl.setContentsMargins(24, 16, 24, 16)
        kkl.setSpacing(12)
        kkl.addStretch()
        self._baris_tombol = kkl
        luar.addWidget(self.kaki)

        self.setMinimumWidth(lebar)
        self.setMaximumWidth(lebar + 160)

    # ------------------------------------------------------------------
    def tambah_tombol(self, kode: str, teks: str, gaya: str = "biasa",
                      utama: bool = False) -> QPushButton:
        """
        Tambahkan tombol pilihan.

        gaya: "primary" untuk tombol utama, "biasa" untuk tombol garis.
        """
        b = QPushButton(teks)
        b.setCursor(Qt.PointingHandCursor)
        b.setMinimumHeight(42)
        b.setMinimumWidth(132)

        if gaya == "primary":
            b.setStyleSheet(
                f"QPushButton {{ background: {C.PRIMARY}; color: "
                f"{C.TEXT_INVERSE}; border: 1px solid {C.PRIMARY}; "
                f"border-radius: {theme.SUDUT_KONTROL}px; "
                f"padding: 10px 24px; font-size: {theme.FS_PESAN}px; "
                "font-weight: 600; }"
                f"QPushButton:hover {{ background: {C.PRIMARY_DARK}; "
                f"border-color: {C.PRIMARY_DARK}; }}")
        else:
            b.setStyleSheet(
                f"QPushButton {{ background: {C.SURFACE}; color: {C.TEXT}; "
                f"border: 1px solid {C.BORDER_STRONG}; "
                f"border-radius: {theme.SUDUT_KONTROL}px; "
                f"padding: 10px 24px; font-size: {theme.FS_PESAN}px; "
                "font-weight: 600; }"
                f"QPushButton:hover {{ background: {C.BG}; "
                f"border-color: {C.PRIMARY_LIGHT}; }}")

        b.clicked.connect(lambda: self._pilih(kode))
        self._baris_tombol.addWidget(b)
        if utama:
            b.setDefault(True)
            b.setFocus()
        return b

    def _pilih(self, kode: str):
        self._pilihan = kode
        self.accept()

    def hasil(self) -> str:
        """Kode tombol yang ditekan, atau teks kosong bila popup ditutup."""
        return self._pilihan


# ==========================================================================
# FUNGSI RINGKAS
# ==========================================================================
def beri_tahu(induk, judul: str, isi: str, rincian: str = "",
              teks_tombol: str = "Mengerti") -> None:
    """Pesan pemberitahuan dengan satu tombol."""
    k = KotakPesan(induk, judul, isi, "info", rincian)
    k.tambah_tombol("ok", teks_tombol, "primary", utama=True)
    k.exec()


def sukses(induk, judul: str, isi: str, rincian: str = "",
           teks_tombol: str = "Selesai") -> None:
    """Pesan keberhasilan dengan satu tombol."""
    k = KotakPesan(induk, judul, isi, "sukses", rincian)
    k.tambah_tombol("ok", teks_tombol, "primary", utama=True)
    k.exec()


def peringatkan(induk, judul: str, isi: str, rincian: str = "",
                teks_tombol: str = "Mengerti") -> None:
    """Pesan peringatan dengan satu tombol."""
    k = KotakPesan(induk, judul, isi, "peringatan", rincian)
    k.tambah_tombol("ok", teks_tombol, "primary", utama=True)
    k.exec()


def galat(induk, judul: str, isi: str, rincian: str = "",
          teks_tombol: str = "Tutup") -> None:
    """Pesan kegagalan dengan satu tombol."""
    k = KotakPesan(induk, judul, isi, "galat", rincian)
    k.tambah_tombol("ok", teks_tombol, "primary", utama=True)
    k.exec()


def tanya(induk, judul: str, isi: str, rincian: str = "",
          teks_ya: str = "Ya", teks_tidak: str = "Batal") -> bool:
    """
    Pertanyaan dengan dua pilihan. Mengembalikan True bila pengguna
    memilih pilihan pertama.
    """
    k = KotakPesan(induk, judul, isi, "tanya", rincian)
    k.tambah_tombol("tidak", teks_tidak, "biasa")
    k.tambah_tombol("ya", teks_ya, "primary", utama=True)
    k.exec()
    return k.hasil() == "ya"


def pilih(induk, judul: str, isi: str, pilihan: list[tuple],
          rincian: str = "", lebar: int = 540) -> str:
    """
    Tampilkan beberapa pilihan sekaligus.

    pilihan: daftar (kode, teks, gaya). Gaya "primary" untuk tombol utama.
    Urutan tampil mengikuti urutan daftar. Mengembalikan kode yang dipilih,
    atau teks kosong bila popup ditutup tanpa memilih.
    """
    k = KotakPesan(induk, judul, isi, "tanya", rincian, lebar=lebar)
    for kode, teks, gaya in pilihan:
        k.tambah_tombol(kode, teks, gaya, utama=(gaya == "primary"))
    k.exec()
    return k.hasil()
