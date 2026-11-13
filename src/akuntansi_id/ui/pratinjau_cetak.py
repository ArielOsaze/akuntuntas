"""
AkunTuntas - Dialog Pratinjau Cetak
===================================
Dialog pratinjau bawaan Qt (QPrintPreviewDialog) memakai bilah alat sistem
yang tidak dapat ditata. Dua akibatnya terlihat jelas di aplikasi ini:

1. Kotak pilihan perbesaran di bilah alatnya mewarisi gaya kolom isian
   aplikasi, sehingga melebar jauh, teks "100.0%" terpotong menjadi
   "1.0%", dan bingkai fokusnya tampil sebagai kotak tembaga tebal.
2. Tombol-tombolnya memakai gambar dan istilah sistem dalam bahasa Inggris,
   berbeda dari seluruh bagian aplikasi.

Dialog di modul ini memakai QPrintPreviewWidget dengan bilah alat sendiri:
istilahnya bahasa Indonesia, tombolnya memakai gaya aplikasi, dan jendelanya
tampil lebih dulu sebelum halaman dilukis sehingga penekanan tombol Cetak
langsung terasa.
"""
from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QPageLayout
from PySide6.QtPrintSupport import QPrintDialog, QPrintPreviewWidget
from PySide6.QtWidgets import (
    QApplication, QDialog, QFrame, QGraphicsView, QHBoxLayout, QLabel,
    QPushButton, QStackedWidget, QVBoxLayout, QWidget,
)

from . import icons, theme, widgets as w
from .theme import C

# Tingkat perbesaran yang dapat dipilih. Daftar tetap dipakai supaya tombol
# perbesar dan perkecil melangkah pada angka yang bulat dan mudah dibaca,
# bukan hasil perkalian yang berkoma panjang.
TINGKAT = [0.25, 0.4, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 3.0, 4.0]


def _tombol_kecil(nama_ikon: str, lebar: int = 34) -> QPushButton:
    """
    Tombol persegi untuk perbesaran dan pindah halaman.

    Lambangnya digambar sebagai ikon, bukan huruf. Tanda minus, kurang dari,
    dan lebih dari pada font antarmuka berukuran sangat kecil dan tipis,
    sehingga pada tombol 34 piksel nyaris tidak terlihat.
    """
    b = QPushButton()
    b.setIcon(icons.ikon(nama_ikon, icons.WARNA_GELAP, 18))
    b.setIconSize(QSize(18, 18))
    b.setCursor(Qt.PointingHandCursor)
    b.setFixedSize(lebar, 32)
    b.setStyleSheet(
        f"QPushButton {{ background: {C.SURFACE}; "
        f"border: 1px solid {C.BORDER_STRONG}; "
        f"border-radius: {theme.SUDUT_KONTROL}px; }}"
        f"QPushButton:hover {{ background: {C.BG}; "
        f"border-color: {C.ACCENT_LIGHT}; }}"
        f"QPushButton:disabled {{ border-color: {C.BORDER}; }}")
    return b


def _tombol_pilihan(teks: str) -> QPushButton:
    """Tombol pilihan tampilan: dapat ditekan tetap seperti sakelar."""
    b = QPushButton(teks)
    b.setCursor(Qt.PointingHandCursor)
    b.setCheckable(True)
    b.setMinimumHeight(32)
    b.setStyleSheet(
        f"QPushButton {{ background: {C.SURFACE}; color: {C.TEXT_MUTED}; "
        f"border: 1px solid {C.BORDER_STRONG}; "
        f"border-radius: {theme.SUDUT_KONTROL}px; padding: 5px 13px; "
        f"font-size: {theme.FS_SMALL}px; font-weight: 600; }}"
        f"QPushButton:hover {{ background: {C.BG}; "
        f"border-color: {C.ACCENT_LIGHT}; }}"
        f"QPushButton:checked {{ background: {C.PRIMARY}; "
        f"color: {C.TEXT_INVERSE}; border-color: {C.PRIMARY}; }}")
    return b


def _pemisah() -> QFrame:
    g = QFrame()
    g.setFixedWidth(1)
    g.setMinimumHeight(22)
    theme.latar(g, f"background: {C.BORDER}; border: none;")
    return g


class DialogPratinjau(QDialog):
    """
    Pratinjau halaman A4 sebelum dicetak.

    lukis           : fungsi yang melukis dokumen ke QPrinter yang diberikan
    atur_orientasi  : fungsi (printer, mendatar) untuk mengganti arah kertas
    simpan          : fungsi tanpa argumen untuk menyimpan PDF, boleh kosong
    """

    def __init__(self, induk, printer, lukis, judul: str,
                 keterangan: str = "", mendatar: bool = False,
                 atur_orientasi=None, simpan=None):
        super().__init__(induk)
        self.setWindowTitle("Pratinjau Cetak A4")
        self.setModal(True)
        self._printer = printer
        self._lukis = lukis
        self._mendatar = mendatar
        self._atur_orientasi = atur_orientasi
        self._simpan = simpan
        self._siap = False

        luar = QVBoxLayout(self)
        luar.setContentsMargins(0, 0, 0, 0)
        luar.setSpacing(0)

        luar.addWidget(self._kepala(judul, keterangan))
        luar.addWidget(self._bilah())

        # ------------------------------------------------------------- isi
        self.pratinjau = QPrintPreviewWidget(printer)
        self.pratinjau.setZoomMode(QPrintPreviewWidget.FitInView)
        self.pratinjau.paintRequested.connect(self._gambar)
        self.pratinjau.previewChanged.connect(self._perbarui)
        # Latar bawaan area pratinjau abu-abu sistem. Warnanya diganti agar
        # kertas putih tetap menonjol tanpa kotak kelabu yang asing.
        papan = self.pratinjau.findChild(QGraphicsView)
        if papan is not None:
            papan.setBackgroundBrush(QColor(C.BG))
            papan.setFrameShape(QFrame.NoFrame)

        tunggu = QLabel("Menyiapkan halaman cetak\u2026")
        tunggu.setAlignment(Qt.AlignCenter)
        tunggu.setStyleSheet(
            f"QLabel {{ color: {C.TEXT_MUTED}; "
            f"font-size: {theme.FS_H3}px; background: {C.BG}; }}")

        self.tumpuk = QStackedWidget()
        self.tumpuk.addWidget(tunggu)
        self.tumpuk.addWidget(self.pratinjau)
        theme.latar(self.tumpuk, f"background: {C.BG}; border: none; "
                                 f"border-top: 1px solid {C.BORDER};")
        luar.addWidget(self.tumpuk, 1)

        luar.addWidget(self._kaki())
        self.resize(1060, 780)
        self.setMinimumSize(860, 600)

    # ------------------------------------------------------------------
    def _kepala(self, judul: str, keterangan: str) -> QWidget:
        kepala = QFrame()
        theme.latar(kepala, f"background: {C.SURFACE}; border: none;")
        lay = QHBoxLayout(kepala)
        lay.setContentsMargins(22, 16, 22, 12)
        lay.setSpacing(14)

        kolom = QVBoxLayout()
        kolom.setSpacing(2)
        lbl = QLabel(judul)
        lbl.setStyleSheet(
            f"font-family: {theme.FONT_DISPLAY}; "
            f"font-size: {theme.FS_H2}px; font-weight: 600; "
            f"color: {C.TEXT}; background: transparent;")
        kolom.addWidget(lbl)
        if keterangan:
            sub = QLabel(keterangan)
            sub.setStyleSheet(
                f"font-size: {theme.FS_SMALL}px; color: {C.TEXT_MUTED}; "
                "background: transparent;")
            kolom.addWidget(sub)
        lay.addLayout(kolom, 1)

        self.lbl_kertas = QLabel()
        self.lbl_kertas.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_kertas.setStyleSheet(
            f"font-size: {theme.FS_SMALL}px; color: {C.TEXT_MUTED}; "
            "background: transparent;")
        lay.addWidget(self.lbl_kertas, 0, Qt.AlignVCenter)
        return kepala

    def _bilah(self) -> QWidget:
        bilah = QFrame()
        theme.latar(bilah, f"background: {C.SURFACE_ALT}; border: none; "
                           f"border-top: 1px solid {C.BORDER};")
        lay = QHBoxLayout(bilah)
        lay.setContentsMargins(22, 10, 22, 10)
        lay.setSpacing(8)

        b_kecil = _tombol_kecil("kurang")
        b_kecil.setToolTip("Perkecil tampilan")
        b_kecil.clicked.connect(lambda: self._langkah_zoom(-1))
        lay.addWidget(b_kecil)

        self.lbl_zoom = QLabel("100%")
        self.lbl_zoom.setAlignment(Qt.AlignCenter)
        self.lbl_zoom.setFixedWidth(56)
        self.lbl_zoom.setStyleSheet(
            f"font-size: {theme.FS_SMALL}px; font-weight: 600; "
            f"color: {C.TEXT}; background: transparent;")
        lay.addWidget(self.lbl_zoom)

        b_besar = _tombol_kecil("tambah")
        b_besar.setToolTip("Perbesar tampilan")
        b_besar.clicked.connect(lambda: self._langkah_zoom(1))
        lay.addWidget(b_besar)

        lay.addSpacing(6)
        lay.addWidget(_pemisah())
        lay.addSpacing(6)

        self.b_lebar = _tombol_pilihan("Selebar jendela")
        self.b_lebar.clicked.connect(self._pas_lebar)
        lay.addWidget(self.b_lebar)

        self.b_satu = _tombol_pilihan("Satu halaman")
        self.b_satu.setChecked(True)
        self.b_satu.clicked.connect(self._satu_halaman)
        lay.addWidget(self.b_satu)

        self.b_semua = _tombol_pilihan("Semua halaman")
        self.b_semua.clicked.connect(self._semua_halaman)
        lay.addWidget(self.b_semua)

        lay.addSpacing(6)
        lay.addWidget(_pemisah())
        lay.addSpacing(6)

        self.b_arah = _tombol_pilihan("Putar ke lanskap")
        self.b_arah.setChecked(False)
        self.b_arah.clicked.connect(self._putar)
        lay.addWidget(self.b_arah)

        lay.addStretch()

        self.b_mundur = _tombol_kecil("panah_kiri")
        self.b_mundur.setToolTip("Halaman sebelumnya")
        self.b_mundur.clicked.connect(lambda: self._pindah(-1))
        lay.addWidget(self.b_mundur)

        self.lbl_halaman = QLabel("Halaman \u2013")
        self.lbl_halaman.setAlignment(Qt.AlignCenter)
        self.lbl_halaman.setMinimumWidth(132)
        self.lbl_halaman.setStyleSheet(
            f"font-size: {theme.FS_SMALL}px; color: {C.TEXT}; "
            "background: transparent;")
        lay.addWidget(self.lbl_halaman)

        self.b_maju = _tombol_kecil("panah_kanan")
        self.b_maju.setToolTip("Halaman berikutnya")
        self.b_maju.clicked.connect(lambda: self._pindah(1))
        lay.addWidget(self.b_maju)
        return bilah

    def _kaki(self) -> QWidget:
        kaki = QFrame()
        theme.latar(kaki, f"background: {C.SURFACE}; border: none; "
                          f"border-top: 1px solid {C.BORDER};")
        lay = QHBoxLayout(kaki)
        lay.setContentsMargins(22, 14, 22, 14)
        lay.setSpacing(10)

        catatan = QLabel("Tanda air, tanda tangan, dan kode dokumen "
                         "mengikuti Pengaturan \u203a Dokumen cetak.")
        catatan.setStyleSheet(
            f"font-size: {theme.FS_TINY}px; color: {C.TEXT_FAINT}; "
            "background: transparent;")
        lay.addWidget(catatan)
        lay.addStretch()

        if self._simpan is not None:
            b_pdf = w.tombol("Simpan PDF", ikon="ekspor")
            b_pdf.clicked.connect(self._simpan_pdf)
            lay.addWidget(b_pdf)

        b_tutup = w.tombol("Tutup")
        b_tutup.clicked.connect(self.reject)
        lay.addWidget(b_tutup)

        b_cetak = w.tombol("Cetak", gaya="primary", ikon="cetak")
        b_cetak.clicked.connect(self._cetak)
        lay.addWidget(b_cetak)
        return kaki

    # ------------------------------------------------------------------
    def tampilkan(self) -> bool:
        """
        Tampilkan jendela lebih dulu, lukis halamannya sesudah itu.

        Melukis dokumen pada kertas A4 beresolusi tinggi memakan waktu
        sekitar satu detik untuk tabel panjang. Bila jendela baru tampil
        setelah lukisan selesai, penekanan tombol Cetak terasa tidak
        bersambut. Karena itu jendela dan bilah alatnya tampil lebih dulu
        dengan keterangan sedang menyiapkan, baru halamannya dilukis.
        """
        self.show()
        QApplication.processEvents()
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            self.tumpuk.setCurrentIndex(1)
            self.pratinjau.updatePreview()
        finally:
            QApplication.restoreOverrideCursor()
        self._siap = True
        self._perbarui()
        return bool(self.exec())

    # ------------------------------------------------------------------
    def _gambar(self, printer):
        self._lukis(printer)

    def _perbarui(self):
        jumlah = self.pratinjau.pageCount()
        kini = self.pratinjau.currentPage()
        satu = self.pratinjau.viewMode() == QPrintPreviewWidget.SinglePageView
        if jumlah:
            self.lbl_halaman.setText(f"Halaman {kini} dari {jumlah}")
        else:
            self.lbl_halaman.setText("Halaman \u2013")
        self.b_mundur.setEnabled(satu and kini > 1)
        self.b_maju.setEnabled(satu and kini < jumlah)
        self.lbl_zoom.setText(f"{round(self.pratinjau.zoomFactor() * 100):d}%")
        arah = "Lanskap" if self._mendatar else "Potret"
        jm = f" \u00b7 {jumlah} halaman" if jumlah else ""
        self.lbl_kertas.setText(f"A4 \u00b7 {arah}{jm}")

    def _langkah_zoom(self, arah: int):
        kini = self.pratinjau.zoomFactor()
        if arah > 0:
            urut = [t for t in TINGKAT if t > kini + 0.001]
            nilai = urut[0] if urut else TINGKAT[-1]
        else:
            urut = [t for t in TINGKAT if t < kini - 0.001]
            nilai = urut[-1] if urut else TINGKAT[0]
        self.pratinjau.setZoomFactor(nilai)
        self.b_lebar.setChecked(False)
        self._perbarui()

    def _pas_lebar(self):
        self.b_lebar.setChecked(True)
        self.pratinjau.setZoomMode(QPrintPreviewWidget.FitToWidth)
        self._perbarui()

    def _satu_halaman(self):
        self.b_satu.setChecked(True)
        self.b_semua.setChecked(False)
        self.pratinjau.setViewMode(QPrintPreviewWidget.SinglePageView)
        self._perbarui()

    def _semua_halaman(self):
        self.b_semua.setChecked(True)
        self.b_satu.setChecked(False)
        self.b_lebar.setChecked(False)
        self.pratinjau.setViewMode(QPrintPreviewWidget.AllPagesView)
        self._perbarui()

    def _pindah(self, langkah: int):
        tujuan = self.pratinjau.currentPage() + langkah
        if 1 <= tujuan <= self.pratinjau.pageCount():
            self.pratinjau.setCurrentPage(tujuan)
            self._perbarui()

    def _putar(self):
        """Ganti arah kertas lalu lukis ulang seluruh halaman."""
        self._mendatar = not self._mendatar
        self.b_arah.setChecked(False)
        self.b_arah.setText("Putar ke potret" if self._mendatar
                            else "Putar ke lanskap")
        if self._atur_orientasi is not None:
            self._atur_orientasi(self._printer, self._mendatar)
        else:
            self._printer.setPageOrientation(
                QPageLayout.Landscape if self._mendatar
                else QPageLayout.Portrait)
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            self.pratinjau.updatePreview()
        finally:
            QApplication.restoreOverrideCursor()
        self._perbarui()

    def _cetak(self):
        dialog = QPrintDialog(self._printer, self)
        dialog.setWindowTitle("Cetak A4")
        if dialog.exec() != QPrintDialog.Accepted:
            return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            self.pratinjau.print_()
        finally:
            QApplication.restoreOverrideCursor()
        self.accept()

    def _simpan_pdf(self):
        if self._simpan is None:
            return
        if self._simpan(self):
            self.accept()
