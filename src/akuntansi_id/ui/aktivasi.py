"""
AkunTuntas - Layar Aktivasi Lisensi
====================================
Layar ini muncul sebelum halaman masuk. Pengguna memasukkan kunci lisensi
yang dibeli, lalu aplikasi meminta server memeriksanya dan mengikat kunci
itu ke komputer ini.

Setelah aktif, keterangan lisensi disimpan di komputer sehingga aplikasi
dapat dibuka tanpa internet.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget)

from .. import config
from ..core import license as LIS
from . import theme
from . import widgets as w
from .login import BrandPanel
from .theme import C


class PekerjaAktivasi(QThread):
    """
    Jalankan aktivasi di latar belakang.

    Menghubungi server bisa memakan beberapa detik. Bila dijalankan pada
    antarmuka utama, jendela akan membeku dan terlihat seperti hang.
    """

    selesai = Signal(bool, str, object)   # berhasil, pesan, lisensi

    def __init__(self, data_dir, kunci: str, parent=None):
        super().__init__(parent)
        self.data_dir = data_dir
        self.kunci = kunci

    def run(self):
        try:
            ok, pesan, lisensi = LIS.aktivasi(self.data_dir, self.kunci)
        except Exception as e:
            ok, pesan, lisensi = False, f"Gagal mengaktifkan: {e}", None
        self.selesai.emit(ok, pesan, lisensi)


def rapikan_kunci(teks: str) -> str:
    """
    Rapikan kunci saat diketik.

    Kunci ditampilkan berkelompok empat huruf supaya mudah dibaca dan
    diketik ulang dari email pembelian.
    """
    bersih = "".join(c for c in teks.upper() if c.isalnum())[:20]
    bagian = [bersih[i:i + 4] for i in range(0, len(bersih), 4)]
    return "-".join(bagian)


class HalamanAktivasi(QWidget):
    """Layar aktivasi lisensi, muncul sebelum halaman masuk."""

    berhasil = Signal(object)   # Lisensi

    def __init__(self, parent=None):
        super().__init__(parent)
        self.lisensi = None
        self.pekerja = None

        luar = QHBoxLayout(self)
        luar.setContentsMargins(0, 0, 0, 0)
        luar.setSpacing(0)

        luar.addWidget(BrandPanel())

        kanan = QWidget()
        theme.latar(kanan, f"background: {C.SURFACE};")
        kl = QVBoxLayout(kanan)
        kl.setContentsMargins(64, 56, 64, 56)
        kl.setSpacing(0)
        kl.addStretch()

        form = QWidget()
        form.setMaximumWidth(430)
        fl = QVBoxLayout(form)
        fl.setContentsMargins(0, 0, 0, 0)
        fl.setSpacing(0)

        aksen = QFrame()
        aksen.setFixedSize(28, 3)
        theme.latar(aksen, f"background: {C.PRIMARY}; border-radius: 2px;")
        fl.addWidget(aksen)
        fl.addSpacing(16)

        judul = QLabel("Aktivasi Lisensi")
        judul.setStyleSheet(
            f"font-size: 25px; font-weight: 700; color: {C.TEXT}; "
            "background: transparent;")
        fl.addWidget(judul)
        fl.addSpacing(7)

        ket = QLabel(
            "Masukkan kunci lisensi yang Anda terima setelah pembelian. "
            "Kunci ini mengikat aplikasi ke komputer ini.")
        ket.setWordWrap(True)
        ket.setStyleSheet(
            f"font-size: {theme.FS_SMALL}px; color: {C.TEXT_MUTED}; "
            "background: transparent;")
        fl.addWidget(ket)
        fl.addSpacing(26)

        # ---------------------------------------------------------- kunci
        fl.addWidget(w.label("Kunci Lisensi", objek="FormLabel"))
        fl.addSpacing(6)

        self.inp_kunci = QLineEdit()
        self.inp_kunci.setObjectName("LoginInput")
        self.inp_kunci.setPlaceholderText("ATNT-XXXX-XXXX-XXXX-XXXX")
        self.inp_kunci.setMinimumHeight(46)
        self.inp_kunci.setMaxLength(24)
        self.inp_kunci.setStyleSheet(
            "QLineEdit { font-family: 'Consolas', monospace; "
            "font-size: 16px; letter-spacing: 1px; padding-left: 12px; }")
        self.inp_kunci.textChanged.connect(self._saat_mengetik)
        self.inp_kunci.returnPressed.connect(self._aktifkan)

        # Tombol tempel: kunci lisensi panjang dan mudah salah ketik, jadi
        # menempel dari email pembelian jauh lebih aman daripada mengetik.
        baris_kunci = QHBoxLayout()
        baris_kunci.setContentsMargins(0, 0, 0, 0)
        baris_kunci.setSpacing(8)
        baris_kunci.addWidget(self.inp_kunci, 1)

        self.tombol_tempel = QPushButton("Tempel")
        self.tombol_tempel.setMinimumHeight(46)
        self.tombol_tempel.setFixedWidth(92)
        self.tombol_tempel.setCursor(Qt.PointingHandCursor)
        self.tombol_tempel.setToolTip(
            "Tempel kunci lisensi yang Anda salin dari email pembelian")
        self.tombol_tempel.setStyleSheet(
            f"QPushButton {{ background: {C.SURFACE_ALT}; color: {C.TEXT}; "
            f"border: 1px solid {C.BORDER}; border-radius: 8px; "
            f"font-size: 13px; font-weight: 600; }}"
            f"QPushButton:hover {{ background: {C.PRIMARY_TINT}; "
            f"border-color: {C.PRIMARY}; color: {C.PRIMARY_DARK}; }}")
        self.tombol_tempel.clicked.connect(self._tempel_kunci)
        baris_kunci.addWidget(self.tombol_tempel)

        fl.addLayout(baris_kunci)
        fl.addSpacing(18)

        # ---------------------------------------------------------- tombol
        self.tombol = QPushButton("Aktifkan Lisensi")
        self.tombol.setMinimumHeight(44)
        self.tombol.setCursor(Qt.PointingHandCursor)
        self.tombol.setStyleSheet(
            f"QPushButton {{ background: {C.PRIMARY}; color: {C.TEXT_INVERSE}; "
            f"border: none; border-radius: 8px; font-size: 14px; "
            f"font-weight: 600; }}"
            f"QPushButton:hover {{ background: {C.PRIMARY_DARK}; }}"
            f"QPushButton:disabled {{ background: {C.BORDER}; "
            f"color: {C.TEXT_MUTED}; }}")
        self.tombol.clicked.connect(self._aktifkan)
        self.tombol.setEnabled(False)
        fl.addWidget(self.tombol)
        fl.addSpacing(14)

        # ---------------------------------------------------------- kabar
        self.lbl_kabar = QLabel("")
        self.lbl_kabar.setWordWrap(True)
        self.lbl_kabar.setVisible(False)
        fl.addWidget(self.lbl_kabar)
        fl.addSpacing(10)

        # ---------------------------------------------------------- bantuan
        fl.addWidget(w.divider())
        fl.addSpacing(12)

        info = QLabel(
            f"Perangkat ini: {LIS.nama_perangkat()}\n"
            "Lisensi Standar untuk 1 perangkat. Lisensi Enterprise dapat "
            "dipakai di beberapa perangkat.")
        info.setWordWrap(True)
        info.setStyleSheet(
            f"font-size: {theme.FS_TINY}px; color: {C.TEXT_FAINT}; "
            "background: transparent;")
        fl.addWidget(info)
        fl.addSpacing(6)

        # Alamat email dibuat dapat diklik supaya pengguna yang belum punya
        # lisensi bisa langsung menghubungi penjual.
        self.lbl_bantuan = QLabel(
            'Belum punya lisensi? Hubungi '
            '<a href="mailto:akuntuntas@gmail.com" '
            'style="color: #1B4F8A; text-decoration: none;">'
            'akuntuntas@gmail.com</a>')
        self.lbl_bantuan.setWordWrap(True)
        self.lbl_bantuan.setOpenExternalLinks(True)
        self.lbl_bantuan.setStyleSheet(
            f"font-size: {theme.FS_TINY}px; color: {C.TEXT_FAINT}; "
            "background: transparent;")
        fl.addWidget(self.lbl_bantuan)

        kl.addWidget(form)
        kl.addStretch()

        # kaki halaman
        kaki = QLabel(f"{config.APP_LONG_NAME} - versi {config.APP_VERSION} "
                      f"({config.APP_BUILD})")
        kaki.setStyleSheet(
            f"font-size: {theme.FS_TINY}px; color: {C.TEXT_FAINT}; "
            "background: transparent;")
        kl.addWidget(kaki)

        luar.addWidget(kanan, 1)

    # ------------------------------------------------------------------
    def _tempel_kunci(self):
        """Isi kolom kunci dari papan klip."""
        from PySide6.QtGui import QGuiApplication

        papan = QGuiApplication.clipboard()
        teks = papan.text() if papan else ""
        if not teks.strip():
            self._tampilkan_kabar(
                "Papan klip kosong. Salin kunci lisensi dari email pembelian "
                "lebih dulu, lalu tekan Tempel.", "info")
            return

        self.inp_kunci.setText(rapikan_kunci(teks))
        self.inp_kunci.setFocus()

    def _buka_email(self, alamat: str):
        """Buka aplikasi email untuk menghubungi penjual lisensi."""
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices
        QDesktopServices.openUrl(QUrl(f"mailto:{alamat}"))

    def _saat_mengetik(self, teks: str):
        """Rapikan penulisan kunci sambil diperiksa kelengkapannya."""
        posisi = self.inp_kunci.cursorPosition()
        rapi = rapikan_kunci(teks)
        if rapi != teks:
            self.inp_kunci.blockSignals(True)
            self.inp_kunci.setText(rapi)
            self.inp_kunci.setCursorPosition(min(posisi + 1, len(rapi)))
            self.inp_kunci.blockSignals(False)

        lengkap = len("".join(c for c in rapi if c.isalnum())) == 20
        self.tombol.setEnabled(lengkap and self.pekerja is None)

    def _tampilkan_kabar(self, pesan: str, jenis: str = "bahaya"):
        """Tampilkan keterangan hasil aktivasi."""
        warna = {
            "bahaya": (C.DANGER, C.DANGER_BG),
            "sukses": (C.SUCCESS, C.SUCCESS_BG),
            "info": (C.PRIMARY_DARK, C.PRIMARY_TINT),
        }.get(jenis, (C.DANGER, C.DANGER_BG))

        self.lbl_kabar.setText(pesan)
        # Selector dibatasi pada label ini saja, supaya aturannya tidak ikut
        # menurun ke widget lain di dalamnya.
        self.lbl_kabar.setStyleSheet(
            f"QLabel {{ font-size: {theme.FS_SMALL}px; color: {warna[0]}; "
            f"background: {warna[1]}; border-radius: 6px; "
            f"padding: 10px 12px; }}")
        self.lbl_kabar.setVisible(True)

    def _aktifkan(self):
        if self.pekerja is not None:
            return

        kunci = self.inp_kunci.text()
        bersih = "".join(c for c in kunci.upper() if c.isalnum())
        if len(bersih) != 20:
            self._tampilkan_kabar(
                "Kunci lisensi belum lengkap. Kunci terdiri dari 20 huruf "
                "dan angka, misalnya ATNT-ABCD-EFGH-IJKL-MNOP.")
            return

        self.tombol.setEnabled(False)
        self.tombol.setText("Menghubungi server...")
        self._tampilkan_kabar(
            "Sedang memeriksa lisensi ke server. Perlu sambungan internet "
            "hanya pada saat aktivasi.", "info")

        self.pekerja = PekerjaAktivasi(config.DATA_DIR, kunci, self)
        self.pekerja.selesai.connect(self._selesai)
        self.pekerja.start()

    def _selesai(self, ok: bool, pesan: str, lisensi):
        self.pekerja = None
        self.tombol.setText("Aktifkan Lisensi")
        self.tombol.setEnabled(True)

        if not ok:
            self._tampilkan_kabar(pesan, "bahaya")
            return

        self.lisensi = lisensi
        self._tampilkan_kabar(
            f"Lisensi berhasil diaktifkan. Paket {lisensi.nama_paket}, "
            "berlaku selamanya untuk perangkat ini.", "sukses")
        self.tombol.setEnabled(False)

        # beri jeda singkat supaya keterangan berhasil terbaca
        from PySide6.QtCore import QTimer
        QTimer.singleShot(1200, lambda: self.berhasil.emit(lisensi))
