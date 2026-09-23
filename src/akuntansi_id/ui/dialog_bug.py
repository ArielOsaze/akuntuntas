"""
AkunTuntas - Dialog Laporan Bug
===============================

Formulir untuk melaporkan masalah kepada pengembang. Keterangan sistem dan
jejak teknis terisi otomatis supaya pengguna cukup menjelaskan apa yang
terjadi; laporan dikirim lewat aplikasi email pengguna.
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPlainTextEdit, QLineEdit,
    QMessageBox,
)

from .. import config, laporan_bug as bug
from . import widgets as w


class DialogLaporBug(QDialog):
    """Formulir laporan masalah dengan keterangan teknis terisi otomatis."""

    def __init__(self, parent=None, kesalahan: str = "", jejak: str = "",
                 judul_awal: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Laporkan Masalah")
        self.setMinimumWidth(660)
        self.setMinimumHeight(600)
        self._kesalahan = kesalahan
        self._jejak = jejak or bug.jejak_terakhir()

        luar = QVBoxLayout(self)
        luar.setContentsMargins(24, 22, 24, 22)
        luar.setSpacing(13)

        j = QLabel(judul_awal or "Laporkan Masalah ke Pengembang")
        j.setObjectName("DialogTitle")
        luar.addWidget(j)

        luar.addWidget(w.label(
            "Keterangan sistem dan jejak teknis sudah terisi otomatis. "
            "Cukup jelaskan apa yang Anda lakukan sebelum masalah muncul "
            "keterangan itu yang paling membantu menelusuri penyebabnya.",
            objek="Muted", wrap=True))

        luar.addWidget(w.label("Ringkasan masalah", objek="FormLabel"))
        self.inp_judul = QLineEdit()
        self.inp_judul.setPlaceholderText(
            "mis. Halaman Kontrak tidak terbuka saat menekan Kontrak Baru")
        luar.addWidget(self.inp_judul)

        luar.addWidget(w.label("Langkah yang Anda lakukan", objek="FormLabel"))
        self.inp_langkah = QPlainTextEdit()
        self.inp_langkah.setPlaceholderText(
            "1. Buka menu Kontrak\n"
            "2. Tekan tombol Kontrak Baru\n"
            "3. Muncul pesan kesalahan")
        self.inp_langkah.setMinimumHeight(110)
        luar.addWidget(self.inp_langkah)

        luar.addWidget(w.label("Keterangan tambahan (opsional)",
                               objek="FormLabel"))
        self.inp_catatan = QPlainTextEdit()
        self.inp_catatan.setPlaceholderText(
            "Hal lain yang perlu diketahui")
        self.inp_catatan.setMinimumHeight(80)
        luar.addWidget(self.inp_catatan)

        kotak = w.Card()
        kl = kotak.body()
        kl.setSpacing(6)
        kl.addWidget(w.label("Keterangan teknis yang akan ikut terkirim",
                             objek="FormLabel"))
        sistem = bug.ringkas_sistem()
        for k, v in sistem.items():
            kl.addWidget(w.label(f"{k}: {v}", objek="Muted", wrap=True))
        if self._kesalahan:
            kl.addWidget(w.label(f"kesalahan: {self._kesalahan[:200]}",
                                 objek="Muted", wrap=True))
        kl.addWidget(w.label(
            f"Jejak log: {len(self._jejak.splitlines())} baris terakhir. "
            "Laporan juga disimpan di folder data aplikasi.",
            objek="Muted", wrap=True))
        luar.addWidget(kotak)

        luar.addStretch()

        baris = QHBoxLayout()
        baris.setSpacing(10)
        b_simpan = w.tombol("Simpan Saja", gaya="biasa", ikon="simpan")
        b_simpan.setToolTip("Simpan laporan ke berkas tanpa membuka email")
        b_simpan.clicked.connect(self._simpan)
        baris.addWidget(b_simpan)

        baris.addStretch()

        b_tutup = w.tombol("Tutup", gaya="biasa")
        b_tutup.clicked.connect(self.reject)
        baris.addWidget(b_tutup)

        b_kirim = w.tombol("Kirim lewat Email", gaya="primary", ikon="dokumen")
        b_kirim.clicked.connect(self._kirim)
        baris.addWidget(b_kirim)
        luar.addLayout(baris)

    # ------------------------------------------------------------------
    def _susun(self) -> dict:
        return bug.susun_laporan(
            kesalahan=self._kesalahan,
            jejak=self._jejak,
            catatan_pengguna=self.inp_catatan.toPlainText(),
            langkah=self.inp_langkah.toPlainText())

    def _judul(self) -> str:
        ringkas = self.inp_judul.text().strip()
        if not ringkas:
            ringkas = "Laporan masalah"
        return f"[AkunTuntas {config.APP_VERSION}] {ringkas}"

    def _simpan(self) -> None:
        laporan = self._susun()
        berkas = bug.simpan_laporan(laporan["teks"])
        if berkas is None:
            QMessageBox.warning(self, "Gagal menyimpan",
                                "Laporan tidak dapat disimpan ke berkas.")
            return
        QMessageBox.information(
            self, "Laporan tersimpan",
            f"Laporan disimpan di:\n{berkas}\n\n"
            "Berkas ini dapat Anda lampirkan sendiri saat mengirim email.")

    def _kirim(self) -> None:
        laporan = self._susun()
        berkas = bug.simpan_laporan(laporan["teks"])
        bug.simpan_metadata(self._kesalahan or self.inp_judul.text(), berkas)

        if not bug.buka_email(laporan["teks"], self._judul()):
            QMessageBox.warning(
                self, "Email tidak terbuka",
                "Aplikasi email tidak dapat dibuka otomatis.\n\n"
                + (f"Laporan sudah disimpan di:\n{berkas}\n\n" if berkas else "")
                + f"Silakan kirim laporan itu ke:\n{bug.EMAIL_PENGEMBANG}")
            return

        pesan = (
            f"Aplikasi email sudah dibuka dengan laporan terisi.\n\n"
            f"Tujuan: {bug.EMAIL_PENGEMBANG}\n\n"
            "Tekan Kirim di aplikasi email Anda untuk mengirimkannya.")
        if berkas:
            pesan += f"\n\nSalinan laporan tersimpan di:\n{berkas}"
        QMessageBox.information(self, "Email disiapkan", pesan)
        self.accept()


def lapor_kesalahan(parent, tipe, nilai, tb) -> None:
    """
    Tampilkan formulir laporan setelah terjadi kesalahan tak tertangani.

    Dipanggil dari penangkap pengecualian aplikasi supaya pengguna dapat
    langsung mengirim laporannya, bukan sekadar melihat pesan kesalahan.
    """
    import traceback as _tb
    jejak = "".join(_tb.format_exception(tipe, nilai, tb))
    dlg = DialogLaporBug(
        parent, kesalahan=f"{tipe.__name__}: {nilai}", jejak=jejak[-bug.BATAS_JEJAK:],
        judul_awal="Aplikasi mengalami kesalahan")
    dlg.exec()


def dialog_lapor(parent, kesalahan: str = "", jejak: str = "") -> None:
    """Buka formulir laporan atas permintaan pengguna."""
    DialogLaporBug(parent, kesalahan=kesalahan, jejak=jejak).exec()
