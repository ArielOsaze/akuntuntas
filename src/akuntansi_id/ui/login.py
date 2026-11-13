"""
AkunTuntas - Halaman Login & Penyiapan Awal
============================================
Alur:
  1. Login (wajib - data pembukuan bersifat rahasia)
  2. Ganti password (bila pertama kali)
  3. Pilih mode penggunaan: Pemula (banyak penjelasan) atau Ahli

Tampilan dibuat seperti formulir resmi: kolom keterangan di atas kertas
hangat, kolom isian di atas permukaan terang, dipisahkan satu garis rambut.
Tanpa kartu melayang, bayangan, strip warna, atau ikon hiasan.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal, QTimer, QSize, QEvent
from PySide6.QtWidgets import (
    QSizePolicy, QScrollArea, QDialog, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QCheckBox, QFrame,
)

from .. import config
from ..core import security as sec
from . import icons
from . import theme
from .theme import C
from . import widgets as w


def capslock_menyala() -> bool:
    """
    Apakah Caps Lock sedang menyala.

    Qt tidak menyediakan cara membacanya, jadi status dibaca langsung dari
    Windows. Di luar Windows fungsi ini mengembalikan False supaya aplikasi
    tetap berjalan tanpa peringatan.
    """
    try:
        import ctypes
        return bool(ctypes.windll.user32.GetKeyState(0x14) & 1)
    except Exception:
        return False


def _label(teks: str, ukuran: float, warna: str, tebal: int = 400,
           spasi: float = 0, serif: bool = False) -> QLabel:
    """Label polos dengan latar transparan, dipakai di kolom merek."""
    lbl = QLabel(teks)
    jenis = theme.FONT_SERIF if serif else theme.FONT_UI
    lbl.setStyleSheet(
        f"font-family: '{jenis}'; font-size: {ukuran}px; font-weight: {tebal}; "
        f"color: {warna}; background: transparent; letter-spacing: {spasi}px;")
    return lbl


def _kepala_merek(tepi_kiri: int = 28, tepi_atas: int = 24) -> QWidget:
    """Baris merek kecil di kiri atas layar penyiapan."""
    kepala = QWidget()
    kl = QHBoxLayout(kepala)
    kl.setContentsMargins(tepi_kiri, tepi_atas, 28, 0)
    kl.setSpacing(8)
    kl.addWidget(w.logo_label(20), 0, Qt.AlignVCenter)
    kl.addWidget(_label("AkunTuntas", 13, C.TEXT, 600, -0.1, True), 0,
                 Qt.AlignVCenter)
    kl.addStretch()
    return kepala


# ==========================================================================
# PANEL KIRI (MEREK)
# ==========================================================================
class BrandPanel(QFrame):
    """Kolom merek: pernyataan, alur kerja, dan keterangan data lokal."""

    LEBAR_INGIN = 500

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(380)
        self.setMaximumWidth(560)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        theme.latar(self, f"background: {C.BG}; border: none;")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(52, 44, 46, 34)
        lay.setSpacing(0)
        self._lay = lay

        # ---------------------------------------------------------- merek
        kepala = QHBoxLayout()
        kepala.setSpacing(10)
        kepala.addWidget(w.logo_label(30), 0, Qt.AlignVCenter)
        kolom = QVBoxLayout()
        kolom.setSpacing(0)
        kolom.addWidget(_label("AkunTuntas", 17, C.TEXT, 600, -0.2, True))
        kolom.addWidget(_label("Akuntansi & pajak usaha", 10, C.TEXT_FAINT,
                               400, 0.2))
        kepala.addLayout(kolom)
        kepala.addStretch()
        lay.addLayout(kepala)

        lay.addStretch(3)

        # --------------------------------------------------------- judul
        judul = _label("Pembukuan dan perpajakan usaha Indonesia.", 31,
                       C.TEXT, 600, -0.4, True)
        judul.setWordWrap(True)
        lay.addWidget(judul)

        lay.addSpacing(14)
        sub = _label(
            "Catatan transaksi, laporan keuangan, dan perhitungan pajak "
            "disusun dari satu sumber data yang sama.", 12.5, C.TEXT_MUTED)
        sub.setWordWrap(True)
        lay.addWidget(sub)

        lay.addStretch(2)

        # ------------------------------------------------------- cakupan
        # Daftar ini disusun seperti daftar isi dokumen resmi: judul, uraian,
        # dan garis pemisah tipis. Tidak ada penanda berwarna.
        self.indeks = QWidget()
        il = QVBoxLayout(self.indeks)
        il.setContentsMargins(0, 0, 0, 0)
        il.setSpacing(0)
        cakupan = (
            ("Jurnal dan buku besar",
             "Transaksi harian tercatat dengan nomor bukti dan tanggal."),
            ("Laporan keuangan",
             "Laba rugi, neraca, dan arus kas dari sumber data yang sama."),
            ("Perpajakan",
             "PPN, PPh, dan rekap SPT dihitung dari pembukuan."),
        )
        for i, (nama, rincian) in enumerate(cakupan):
            if i:
                garis = QFrame()
                garis.setFixedHeight(1)
                theme.latar(garis, f"background: {C.BORDER}; border: none;")
                il.addWidget(garis)
            kol = QVBoxLayout()
            kol.setContentsMargins(0, 0 if i == 0 else 11,
                                   0, 0 if i == len(cakupan) - 1 else 11)
            kol.setSpacing(3)
            kol.addWidget(_label(nama, 12.5, C.TEXT, 600))
            kol.addWidget(_label(rincian, 11.5, C.TEXT_MUTED))
            il.addLayout(kol)
        lay.addWidget(self.indeks)

        lay.addStretch(2)

        # ------------------------------------------------------------- kaki
        lay.addWidget(_label("Data tersimpan di komputer ini dan tidak diunggah.",
                             11, C.TEXT_MUTED))
        lay.addSpacing(3)
        lay.addWidget(_label("PP 55/2022 · PMK 81/2024 · PP 20/2026",
                             10, C.TEXT_FAINT))

    def resizeEvent(self, peristiwa):
        """
        Rapatkan bantalan pada jendela sempit.

        Panel ini boleh menyusut sampai 380 piksel. Dengan bantalan 52 piksel
        judul kehilangan ruang, jadi tepi dikurangi lebih dulu sebelum
        teksnya mulai terpotong.
        """
        super().resizeEvent(peristiwa)
        tepi = 38 if self.width() < 430 else 52
        if self._lay.contentsMargins().left() != tepi:
            self._lay.setContentsMargins(tepi, 40, tepi - 6, 30)

    def sizeHint(self):
        """Lebar yang diinginkan panel merek pada jendela lapang."""
        ukuran = super().sizeHint()
        ukuran.setWidth(self.LEBAR_INGIN)
        return ukuran


# ==========================================================================
# KOLOM ISIAN
# ==========================================================================
class _BidangLogin(QFrame):
    """
    Kolom isian berbingkai dengan penanda fokus pada bingkainya.

    QFrame dipakai sebagai pembungkus supaya tombol lihat password dapat
    duduk sejajar teks, sedangkan QLineEdit-nya tanpa garis tepi. Tebal
    bingkai tidak berubah saat fokus, hanya warnanya, sehingga teks tidak
    bergeser satu piksel pun ketika kolom dipilih.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("LoginField")
        self.setFixedHeight(46)

        self.inp = QLineEdit()
        self.inp.setObjectName("LoginFieldInput")
        self.inp.installEventFilter(self)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(2, 0, 6, 0)
        lay.setSpacing(6)
        lay.addWidget(self.inp, 1)

    def tambah_kanan(self, widget: QWidget):
        """Tambahkan tombol di ujung kanan, mis. tombol lihat password."""
        self.layout().addWidget(widget, 0, Qt.AlignVCenter)

    def eventFilter(self, obj, peristiwa):
        if obj is self.inp and peristiwa.type() in (QEvent.FocusIn,
                                                     QEvent.FocusOut):
            self.setProperty("fokus", peristiwa.type() == QEvent.FocusIn)
            gaya = self.style()
            gaya.unpolish(self)
            gaya.polish(self)
            self.update()
        return super().eventFilter(obj, peristiwa)


class LoginPage(QWidget):
    berhasil = Signal(object)   # LoginResult

    def __init__(self, parent=None):
        super().__init__(parent)
        # Hasil login terakhir, dipakai layar berikutnya untuk menyimpan mode.
        self.hasil_terakhir = None
        luar = QHBoxLayout(self)
        luar.setContentsMargins(0, 0, 0, 0)
        luar.setSpacing(0)

        self.panel_merek = BrandPanel()
        luar.addWidget(self.panel_merek)

        pemisah = QFrame()
        pemisah.setFixedWidth(1)
        theme.latar(pemisah, f"background: {C.BORDER}; border: none;")
        luar.addWidget(pemisah)

        # --------------------------------------------------------- sisi kanan
        kanan = QWidget()
        theme.latar(kanan, f"background: {C.SURFACE}; border: none;")
        kl = QVBoxLayout(kanan)
        kl.setContentsMargins(0, 0, 0, 0)
        kl.setSpacing(0)

        # Area bergulir menjaga formulir tetap utuh pada layar pendek,
        # termasuk saat kotak pesan kesalahan muncul dan menambah tinggi.
        gulung = QScrollArea()
        gulung.setWidgetResizable(True)
        gulung.setFrameShape(QFrame.NoFrame)
        gulung.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        gulung.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollArea > QWidget > QWidget { background: transparent; }")
        gulung.viewport().setAutoFillBackground(False)

        isi = QWidget()
        il = QVBoxLayout(isi)
        il.setContentsMargins(32, 34, 32, 10)
        il.setSpacing(0)
        il.addStretch(1)

        formulir = QWidget()
        # Lebar tetap 400 px: formulir harus muat pada jendela minimum
        # 920x620 (kolom kanan masih sekitar 515 px). Lebar mengikuti ukuran
        # saran anak-anaknya membuat kolom isian menyusut menjadi 200 px
        # dan judul terlipat di tengah kata.
        formulir.setFixedWidth(400)
        fl = QVBoxLayout(formulir)
        fl.setContentsMargins(0, 0, 0, 0)
        fl.setSpacing(0)

        # --------------------------------------------------------- kepala
        judul = QLabel("Masuk ke akun")
        judul.setObjectName("LoginTitle")
        judul.setWordWrap(True)
        fl.addWidget(judul)

        fl.addSpacing(7)
        ket = QLabel("Gunakan akun yang terdaftar untuk melanjutkan pembukuan "
                     "yang tersimpan di komputer ini.")
        ket.setObjectName("LoginSub")
        ket.setWordWrap(True)
        fl.addWidget(ket)

        fl.addSpacing(28)

        # ----------------------------------------------------- nama pengguna
        fl.addWidget(w.label("Nama pengguna", objek="LoginLabel"))
        fl.addSpacing(7)
        self.bidang_user = _BidangLogin()
        self.inp_user = self.bidang_user.inp
        self.inp_user.setPlaceholderText("mis. admin")
        self.inp_user.returnPressed.connect(lambda: self.inp_pass.setFocus())
        fl.addWidget(self.bidang_user)

        fl.addSpacing(16)

        # ---------------------------------------------------------- password
        baris_label = QHBoxLayout()
        baris_label.setSpacing(8)
        baris_label.addWidget(w.label("Kata sandi", objek="LoginLabel"), 0)
        baris_label.addStretch(1)
        self.btn_lupa = QPushButton("Lupa password?")
        self.btn_lupa.setCursor(Qt.PointingHandCursor)
        self.btn_lupa.setStyleSheet(
            f"QPushButton {{ border: none; background: transparent; "
            f"color: {C.ACCENT_DARK}; font-size: {theme.FS_TINY}px; "
            "font-weight: 600; padding: 0; }}"
            f"QPushButton:hover {{ color: {C.PRIMARY_DARK}; }}")
        self.btn_lupa.clicked.connect(self._lupa_password)
        baris_label.addWidget(self.btn_lupa, 0, Qt.AlignVCenter)
        fl.addLayout(baris_label)

        fl.addSpacing(7)
        self.bidang_pass = _BidangLogin()
        self.inp_pass = self.bidang_pass.inp
        self.inp_pass.setPlaceholderText("Kata sandi")
        self.inp_pass.setEchoMode(QLineEdit.Password)
        self.inp_pass.returnPressed.connect(self._login)
        self.inp_pass.textChanged.connect(self._perbarui_capslock)

        # Tombol lihat memakai teks, bukan hanya ikon: pengguna baru belum
        # tentu mengenali lambang mata. Lebarnya mengikuti teks sehingga
        # "Sembunyikan" tidak pernah terpotong saat ditekan.
        self.btn_lihat = QPushButton("Lihat")
        self.btn_lihat.setObjectName("LoginReveal")
        self.btn_lihat.setCursor(Qt.PointingHandCursor)
        self.btn_lihat.setCheckable(True)
        self.btn_lihat.setMinimumWidth(58)
        self.btn_lihat.setFixedHeight(28)
        self.btn_lihat.setIcon(icons.ikon("mata", C.TEXT_MUTED, 14))
        self.btn_lihat.setIconSize(QSize(14, 14))
        self.btn_lihat.toggled.connect(self._ganti_lihat_password)
        self.bidang_pass.tambah_kanan(self.btn_lihat)
        fl.addWidget(self.bidang_pass)

        # Peringatan Caps Lock muncul hanya saat menyala dan kolom password
        # sedang berisi, supaya tidak menambah kebisingan tampilan.
        self.lbl_caps = QLabel("Caps Lock menyala")
        self.lbl_caps.setStyleSheet(
            f"font-size: {theme.FS_TINY}px; color: {C.WARNING}; "
            "background: transparent; font-weight: 600;")
        self.lbl_caps.hide()
        fl.addSpacing(6)
        fl.addWidget(self.lbl_caps)

        fl.addSpacing(10)
        self.chk_ingat = QCheckBox("Ingat nama pengguna")
        self.chk_ingat.setStyleSheet(
            f"QCheckBox {{ font-size: {theme.FS_SMALL}px; color: {C.TEXT_MUTED}; "
            "background: transparent; spacing: 8px; }"
            f"QCheckBox:hover {{ color: {C.TEXT}; }}"
            "QCheckBox::indicator { width: 15px; height: 15px; "
            f"border: 1px solid {C.BORDER_STRONG}; border-radius: 2px; "
            f"background: {C.SURFACE}; }}"
            f"QCheckBox::indicator:hover {{ border-color: {C.ACCENT}; }}"
            f"QCheckBox::indicator:checked {{ background: {C.PRIMARY}; "
            f"border-color: {C.PRIMARY}; }}")
        fl.addWidget(self.chk_ingat)

        fl.addSpacing(8)
        self.lbl_error = QLabel("")
        self.lbl_error.setWordWrap(True)
        self.lbl_error.setObjectName("LoginError")
        self.lbl_error.hide()
        fl.addWidget(self.lbl_error)

        fl.addSpacing(16)
        self.btn_login = QPushButton("Masuk")
        self.btn_login.setCursor(Qt.PointingHandCursor)
        self.btn_login.setMinimumHeight(46)
        self.btn_login.setStyleSheet(
            f"QPushButton {{ border: 1px solid {C.PRIMARY}; color: white; "
            f"border-radius: 4px; font-size: {theme.FS_H3}px; "
            "font-weight: 600; padding: 0 18px; min-height: 46px; "
            f"background: {C.PRIMARY}; }}"
            f"QPushButton:hover {{ background: {C.PRIMARY_DARK}; "
            f"border-color: {C.PRIMARY_DARK}; }}"
            "QPushButton:pressed { background: #0F1518; border-color: #0F1518; }"
            f"QPushButton:focus {{ border: 1px solid {C.ACCENT_LIGHT}; }}"
            f"QPushButton:disabled {{ background: {C.BORDER}; "
            f"border-color: {C.BORDER}; color: {C.TEXT_MUTED}; }}")
        self.btn_login.clicked.connect(self._login)
        fl.addWidget(self.btn_login)

        # --------------------------------------------------- akun bawaan
        fl.addSpacing(16)
        self.petunjuk = QFrame()
        self.petunjuk.setObjectName("LoginHintBox")
        pl = QVBoxLayout(self.petunjuk)
        pl.setContentsMargins(14, 11, 14, 12)
        pl.setSpacing(4)
        pl.addWidget(w.label("Akun bawaan", objek="LoginLabel"))
        kredensial = QLabel(f"{config.DEFAULT_ADMIN_USER} / "
                            f"{config.DEFAULT_ADMIN_PASSWORD}")
        kredensial.setStyleSheet(
            f"font-size: {theme.FS_SMALL}px; font-weight: 700; "
            f"color: {C.TEXT}; background: transparent;")
        pl.addWidget(kredensial)
        catatan_akun = QLabel("Anda akan diminta mengganti kata sandi.")
        catatan_akun.setWordWrap(True)
        catatan_akun.setStyleSheet(
            f"font-size: {theme.FS_TINY}px; color: {C.TEXT_MUTED}; "
            "background: transparent;")
        pl.addWidget(catatan_akun)
        fl.addWidget(self.petunjuk)

        il.addWidget(formulir, 0, Qt.AlignHCenter)
        il.addStretch(1)

        gulung.setWidget(isi)
        kl.addWidget(gulung, 1)

        # ------------------------------------------------------------ kaki
        kaki = QWidget()
        theme.latar(kaki, f"background: {C.SURFACE}; border: none;")
        kl_kaki = QHBoxLayout(kaki)
        kl_kaki.setContentsMargins(32, 6, 32, 18)
        kl_kaki.setSpacing(7)
        kl_kaki.addStretch(1)
        self.lbl_keadaan = QLabel()
        self.lbl_keadaan.setObjectName("LoginFooter")
        kl_kaki.addWidget(self.lbl_keadaan, 0)
        titik = QLabel("·")
        titik.setObjectName("LoginFooter")
        kl_kaki.addWidget(titik, 0)
        versi = QLabel(f"{config.APP_EDITION} v{config.APP_VERSION}")
        versi.setObjectName("LoginFooter")
        kl_kaki.addWidget(versi, 0)
        kl_kaki.addStretch(1)
        kl.addWidget(kaki)

        luar.addWidget(kanan, 1)

        self._perbarui_keadaan()
        self._muat_preferensi()

    def resizeEvent(self, peristiwa):
        """
        Bagi lebar jendela antara panel merek dan kolom formulir.

        Panel merek mengambil 44% lebar dengan batas 380-500 piksel. Pada
        jendela 920 piksel kolom formulir masih mendapat lebih dari 500
        piksel, cukup untuk isian selebar 400 piksel beserta bantalannya.
        """
        super().resizeEvent(peristiwa)
        lebar = max(380, min(BrandPanel.LEBAR_INGIN, int(self.width() * 0.44)))
        if self.panel_merek.width() != lebar:
            self.panel_merek.setFixedWidth(lebar)

    def _petunjuk_masih_perlu(self) -> bool:
        """
        Apakah keterangan akun bawaan masih perlu ditampilkan.

        Keterangan ini hanya berguna selama password bawaan belum diganti.
        Setelah diganti, menampilkannya justru mengundang orang mencoba
        kombinasi yang sudah tidak berlaku.
        """
        try:
            from .. import db
            r = db.q1("SELECT must_change_pw FROM users WHERE username=? "
                      "COLLATE NOCASE", (config.DEFAULT_ADMIN_USER,))
            return bool(r and r["must_change_pw"])
        except Exception:
            return False

    def _perbarui_keadaan(self):
        """
        Tampilkan jumlah pengguna dan perusahaan yang terdaftar.

        Angka ini membantu pengguna baru memastikan basis datanya sudah siap,
        dan membantu pengguna lama menyadari bila datanya tidak terbaca.
        """
        try:
            from .. import db
            pengguna = db.scalar("SELECT COUNT(*) FROM users") or 0
            perusahaan = db.scalar("SELECT COUNT(*) FROM companies") or 0
            if perusahaan:
                self.lbl_keadaan.setText(
                    f"{pengguna} pengguna · {perusahaan} perusahaan")
            else:
                self.lbl_keadaan.setText("Belum ada perusahaan")
        except Exception:
            self.lbl_keadaan.setText("Data lokal")

        self.petunjuk.setVisible(self._petunjuk_masih_perlu())

    def _muat_preferensi(self):
        try:
            from .. import db
            u = db.q1("SELECT value FROM settings WHERE key='last_user'")
            if u and u["value"]:
                self.inp_user.setText(u["value"])
                self.chk_ingat.setChecked(True)
                self.inp_pass.setFocus()
                return
        except Exception:
            pass
        self.inp_user.setFocus()

    def _ganti_lihat_password(self, terlihat: bool):
        """Tampilkan atau sembunyikan isi kolom password."""
        self.inp_pass.setEchoMode(
            QLineEdit.Normal if terlihat else QLineEdit.Password)
        self.btn_lihat.setText("Sembunyikan" if terlihat else "Lihat")
        self.btn_lihat.setIcon(icons.ikon(
            "mata_tutup" if terlihat else "mata",
            C.ACCENT_DARK if terlihat else C.TEXT_MUTED, 14))
        self.btn_lihat.setToolTip(
            "Sembunyikan kata sandi" if terlihat else "Tampilkan kata sandi")
        self.btn_lihat.updateGeometry()

    def _perbarui_capslock(self, _teks: str = ""):
        """
        Tampilkan peringatan bila Caps Lock menyala.

        Peringatan hanya muncul saat kolom password berisi sesuatu, karena
        saat kosong tidak ada huruf yang bisa salah besar-kecil.
        """
        self.lbl_caps.setVisible(capslock_menyala() and bool(self.inp_pass.text()))

    def keyPressEvent(self, peristiwa):
        """Perbarui peringatan Caps Lock setiap kali tombol ditekan."""
        if peristiwa.key() == Qt.Key_CapsLock:
            self._perbarui_capslock()
        super().keyPressEvent(peristiwa)

    def _simpan_preferensi(self, username: str):
        try:
            from .. import db
            nilai = username if self.chk_ingat.isChecked() else ""
            db.ex("INSERT INTO settings(key,value) VALUES('last_user',?) "
                  "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (nilai,))
        except Exception:
            pass

    def _tampilkan_error(self, pesan: str):
        self.lbl_error.setText(pesan)
        self.lbl_error.show()

    def _login(self):
        self.lbl_error.hide()
        user = self.inp_user.text().strip()
        pwd = self.inp_pass.text()
        if not user:
            self._tampilkan_error("Nama pengguna belum diisi.")
            self.inp_user.setFocus()
            return
        if not pwd:
            self._tampilkan_error("Password belum diisi.")
            self.inp_pass.setFocus()
            return

        self.btn_login.setEnabled(False)
        self.btn_login.setText("Memeriksa…")
        QTimer.singleShot(40, lambda: self._proses_login(user, pwd))

    def _proses_login(self, user: str, pwd: str):
        try:
            hasil = sec.login(user, pwd)
        except Exception as e:
            hasil = sec.LoginResult(ok=False, message=f"Terjadi kesalahan: {e}")
        self.btn_login.setEnabled(True)
        self.btn_login.setText("Masuk")

        if not hasil.ok:
            self._tampilkan_error(hasil.message)
            self.inp_pass.clear()
            self.inp_pass.setFocus()
            return

        self._simpan_preferensi(hasil.username)
        self.inp_pass.clear()
        self.hasil_terakhir = hasil
        self.berhasil.emit(hasil)

    def _lupa_password(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Lupa Password")
        dlg.setFixedWidth(520)
        dlg.setStyleSheet(f"QDialog {{ background: {C.SURFACE}; }}")
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(30, 28, 30, 24)
        lay.setSpacing(0)

        j = QLabel("Pemulihan akses")
        j.setStyleSheet(
            f"font-family: '{theme.FONT_SERIF}'; font-size: 25px; "
            f"font-weight: 600; color: {C.TEXT}; background: transparent; "
            "letter-spacing: -0.2px;")
        lay.addWidget(j)

        lay.addSpacing(9)
        intro = QLabel(
            "Data pembukuan tersimpan di komputer ini, sehingga tidak ada "
            "pemulihan melalui email. Gunakan salah satu cara berikut.")
        intro.setWordWrap(True)
        intro.setStyleSheet(f"font-size: {theme.FS_SMALL}px; color: {C.TEXT_MUTED}; "
                            "background: transparent;")
        lay.addWidget(intro)
        lay.addSpacing(22)

        langkah = [
            ("1.", "Minta bantuan pemilik usaha",
             "Pengguna dengan peran owner membuka Pengaturan, memilih "
             "Pengguna, lalu mereset kata sandi Anda."),
            ("2.", "Atur ulang sendiri",
             "Buat berkas reset_admin.txt di folder data, lalu jalankan "
             "ulang aplikasi. Aplikasi akan meminta kata sandi baru."),
        ]
        for nomor, judul, ket in langkah:
            baris = QHBoxLayout()
            baris.setSpacing(10)
            baris.addWidget(_label(nomor, 12, C.TEXT_MUTED, 600),
                            0, Qt.AlignTop)
            kol = QVBoxLayout()
            kol.setSpacing(3)
            l_judul = QLabel(judul)
            l_judul.setStyleSheet(
                f"font-size: {theme.FS_SMALL}px; font-weight: 600; "
                f"color: {C.TEXT}; background: transparent;")
            kol.addWidget(l_judul)
            l_ket = QLabel(ket)
            l_ket.setWordWrap(True)
            l_ket.setStyleSheet(f"font-size: {theme.FS_SMALL}px; "
                                f"color: {C.TEXT_MUTED}; background: transparent;")
            kol.addWidget(l_ket)
            baris.addLayout(kol, 1)
            lay.addLayout(baris)
            lay.addSpacing(16)

        kotak = QFrame()
        kotak.setObjectName("PathBox")
        kl = QVBoxLayout(kotak)
        kl.setContentsMargins(12, 10, 12, 10)
        kl.setSpacing(4)
        kl.addWidget(w.label("Folder data", objek="LoginLabel"))
        path = QLabel(str(config.DATA_DIR))
        path.setWordWrap(True)
        path.setTextInteractionFlags(Qt.TextSelectableByMouse)
        path.setStyleSheet(
            f"font-family: '{theme.FONT_MONO}'; font-size: {theme.FS_TINY}px; "
            f"color: {C.TEXT}; background: transparent;")
        kl.addWidget(path)
        lay.addWidget(kotak)

        lay.addSpacing(20)
        btn = w.tombol("Mengerti", gaya="primary")
        btn.setMinimumHeight(40)
        btn.clicked.connect(dlg.accept)
        baris_tombol = QHBoxLayout()
        baris_tombol.addStretch()
        baris_tombol.addWidget(btn)
        lay.addLayout(baris_tombol)
        dlg.exec()


# ==========================================================================
# HALAMAN GANTI PASSWORD (WAJIB SAAT PERTAMA KALI)
# ==========================================================================
class GantiPasswordWajib(QWidget):
    selesai = Signal()

    def __init__(self, user: sec.LoginResult, parent=None):
        super().__init__(parent)
        self.user = user
        theme.latar(self, f"background: {C.SURFACE}; border: none;")

        luar = QVBoxLayout(self)
        luar.setContentsMargins(0, 0, 0, 0)
        luar.setSpacing(0)
        luar.addWidget(_kepala_merek())

        isi = QWidget()
        lay_luar = QVBoxLayout(isi)
        lay_luar.setContentsMargins(28, 0, 28, 26)
        lay_luar.setSpacing(0)
        lay_luar.addStretch(1)

        kolom = QWidget()
        # Lebar tetap supaya isian tidak menyusut menjadi 290 px pada
        # jendela 920 px; 430 px masih muat dengan bantalan halaman.
        kolom.setFixedWidth(430)
        lay = QVBoxLayout(kolom)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        j = QLabel("Ganti kata sandi")
        j.setObjectName("LoginTitle")
        lay.addWidget(j)

        lay.addSpacing(7)
        ket = w.LabelTinggiOtomatis(
            "Anda masih memakai kata sandi bawaan. Demi keamanan data "
            "pembukuan, kata sandi wajib diganti sebelum melanjutkan."
        )
        ket.setWordWrap(True)
        ket.setTextFormat(Qt.RichText)
        ket.setStyleSheet(f"font-size: {theme.FS_SMALL}px; color: {C.TEXT_MUTED}; "
                          "background: transparent;")
        ket.setMinimumHeight(theme.tinggi_rich_text(ket))
        lay.addWidget(ket)

        lay.addSpacing(6)
        siapa = QLabel(f"Masuk sebagai {user.full_name or user.username} "
                       f"· @{user.username}")
        siapa.setStyleSheet(f"font-size: {theme.FS_TINY}px; color: {C.TEXT_FAINT}; "
                            "background: transparent;")
        lay.addWidget(siapa)

        lay.addSpacing(26)
        lay.addWidget(w.label("Kata sandi saat ini", objek="LoginLabel"))
        lay.addSpacing(6)
        self.inp_lama = QLineEdit()
        self.inp_lama.setEchoMode(QLineEdit.Password)
        self.inp_lama.setMinimumHeight(40)
        self.inp_lama.setText(config.DEFAULT_ADMIN_PASSWORD)
        lay.addWidget(self.inp_lama)

        lay.addSpacing(16)
        lay.addWidget(w.label("Kata sandi baru", objek="LoginLabel"))
        lay.addSpacing(6)
        self.inp_baru = QLineEdit()
        self.inp_baru.setEchoMode(QLineEdit.Password)
        self.inp_baru.setMinimumHeight(40)
        self.inp_baru.textChanged.connect(self._cek_kekuatan)
        lay.addWidget(self.inp_baru)

        # Kekuatan kata sandi ditampilkan sebagai empat ruas garis, bukan
        # deretan balok teks, supaya sejalan dengan garis tipis di halaman.
        self.baris_kekuatan = QWidget()
        bl = QHBoxLayout(self.baris_kekuatan)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(4)
        self._segmen = []
        for _ in range(4):
            seg = QFrame()
            seg.setFixedHeight(3)
            seg.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            theme.latar(seg, f"background: {C.BORDER}; border: none;")
            bl.addWidget(seg)
            self._segmen.append(seg)
        lay.addSpacing(8)
        lay.addWidget(self.baris_kekuatan)
        self.lbl_kekuatan = QLabel("")
        self.lbl_kekuatan.setStyleSheet(
            f"font-size: {theme.FS_TINY}px; color: {C.TEXT_FAINT}; "
            "background: transparent;")
        lay.addSpacing(5)
        lay.addWidget(self.lbl_kekuatan)

        lay.addSpacing(16)
        lay.addWidget(w.label("Ulangi kata sandi baru", objek="LoginLabel"))
        lay.addSpacing(6)
        self.inp_ulang = QLineEdit()
        self.inp_ulang.setEchoMode(QLineEdit.Password)
        self.inp_ulang.setMinimumHeight(40)
        self.inp_ulang.returnPressed.connect(self._simpan)
        lay.addWidget(self.inp_ulang)

        self.lbl_pesan = QLabel("")
        self.lbl_pesan.setWordWrap(True)
        self.lbl_pesan.setObjectName("LoginError")
        self.lbl_pesan.hide()
        lay.addSpacing(12)
        lay.addWidget(self.lbl_pesan)

        lay.addSpacing(18)
        btn = w.tombol("Simpan kata sandi baru", gaya="primary")
        btn.setMinimumHeight(44)
        btn.clicked.connect(self._simpan)
        lay.addWidget(btn)

        lay.addSpacing(12)
        syarat = QLabel(
            "Minimal 8 karakter, gabungan huruf besar dan kecil, angka, "
            "serta simbol.")
        syarat.setWordWrap(True)
        syarat.setStyleSheet(f"font-size: {theme.FS_TINY}px; color: {C.TEXT_FAINT}; "
                             "background: transparent;")
        lay.addWidget(syarat)

        tengah = QHBoxLayout()
        tengah.addStretch()
        tengah.addWidget(kolom)
        tengah.addStretch()
        lay_luar.addLayout(tengah)
        lay_luar.addStretch(1)
        luar.addWidget(isi, 1)

    def _cek_kekuatan(self, teks: str):
        if not teks:
            self.lbl_kekuatan.setText("")
            for seg in self._segmen:
                theme.latar(seg, f"background: {C.BORDER}; border: none;")
            return
        skor, label, _saran = sec.password_strength(teks)
        warna = [C.DANGER, C.DANGER, C.WARNING, C.SUCCESS, C.SUCCESS][skor]
        isi = max(1, skor)
        for i, seg in enumerate(self._segmen):
            theme.latar(
                seg,
                f"background: {warna if i < isi else C.BORDER}; border: none;")
        self.lbl_kekuatan.setText(f"Kekuatan: {label}")

    def _simpan(self):
        self.lbl_pesan.hide()
        lama, baru, ulang = self.inp_lama.text(), self.inp_baru.text(), self.inp_ulang.text()
        if baru != ulang:
            self._error("Kata sandi baru dan ulangannya tidak sama.")
            return
        try:
            sec.change_password(self.user.user_id, lama, baru)
        except ValueError as e:
            self._error(str(e))
            return
        except Exception as e:
            self._error(f"Gagal menyimpan: {e}")
            return
        self.selesai.emit()

    def _error(self, pesan: str):
        self.lbl_pesan.setText(pesan)
        self.lbl_pesan.show()


# ==========================================================================
# PEMILIHAN MODE PEMAKAIAN
# ==========================================================================
class PilihMode(QWidget):
    """
    Pemilihan mode: Pemula atau Ahli.
    Menentukan apakah panel penjelasan ditampilkan di seluruh aplikasi.
    """
    selesai = Signal(str)   # "beginner" | "expert"

    def __init__(self, user: sec.LoginResult, parent=None):
        super().__init__(parent)
        self.user = user
        theme.latar(self, f"background: {C.BG}; border: none;")

        luar = QVBoxLayout(self)
        luar.setContentsMargins(0, 0, 0, 0)
        luar.setSpacing(0)
        luar.addWidget(_kepala_merek())

        isi = QWidget()
        kisi = QVBoxLayout(isi)
        kisi.setContentsMargins(56, 0, 56, 30)
        kisi.setSpacing(0)
        kisi.addStretch(1)

        kepala = QVBoxLayout()
        kepala.setSpacing(0)
        j = QLabel("Bagaimana Anda ingin bekerja?")
        j.setAlignment(Qt.AlignCenter)
        j.setWordWrap(True)
        j.setStyleSheet(
            f"font-family: '{theme.FONT_SERIF}'; font-size: 30px; "
            f"font-weight: 600; color: {C.TEXT}; background: transparent; "
            "letter-spacing: -0.3px;")
        kepala.addWidget(j)

        kepala.addSpacing(8)
        s = w.LabelTinggiOtomatis(
            f"Selamat datang, {user.full_name or user.username}. Pilihan ini "
            "mengatur seberapa banyak penjelasan yang ditampilkan, dan dapat "
            "diubah kapan saja.")
        s.setAlignment(Qt.AlignCenter)
        s.setWordWrap(True)
        s.setStyleSheet(f"font-size: {theme.FS_SMALL}px; color: {C.TEXT_MUTED}; "
                        "background: transparent;")
        kepala.addWidget(s)
        kisi.addLayout(kepala)
        kisi.addSpacing(28)

        baris = QHBoxLayout()
        baris.setSpacing(20)

        self.kartu_pemula = self._buat_kartu(
            "Mode Pemula", "Untuk yang baru memulai pembukuan",
            [
                "Panel penjelasan konsep di setiap halaman",
                "Istilah akuntansi dijelaskan sehari-hari",
                "Langkah kerja dipandu berurutan",
                "Contoh jurnal standar di setiap formulir",
                "Dasar hukum pada fitur terkait",
            ],
            pilihan="beginner", utama=True,
        )
        baris.addWidget(self.kartu_pemula, 1)

        self.kartu_ahli = self._buat_kartu(
            "Mode Ahli", "Untuk akuntan atau yang sudah berpengalaman",
            [
                "Antarmuka ringkas tanpa panel penjelasan",
                "Fokus pada kecepatan input dan analisis",
                "Seluruh fitur tetap lengkap dan dapat diakses",
                "Referensi aturan di menu Bantuan",
                "Pintasan dan navigasi cepat",
            ],
            pilihan="expert", utama=False,
        )
        baris.addWidget(self.kartu_ahli, 1)

        kisi.addLayout(baris)
        kisi.addSpacing(22)

        catatan = QLabel("Data pembukuan tidak terpengaruh oleh pilihan ini.")
        catatan.setAlignment(Qt.AlignCenter)
        catatan.setWordWrap(True)
        catatan.setStyleSheet(f"font-size: {theme.FS_TINY}px; color: {C.TEXT_FAINT}; "
                              "background: transparent;")
        kisi.addWidget(catatan)
        kisi.addStretch(1)
        luar.addWidget(isi, 1)

    def _buat_kartu(self, judul: str, sub: str, daftar: list,
                    pilihan: str, utama: bool) -> QFrame:
        kartu = QFrame()
        kartu.setObjectName("ModeOption")
        kartu.setMinimumHeight(300)
        kartu.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        lay = QVBoxLayout(kartu)
        lay.setContentsMargins(28, 24, 28, 24)
        lay.setSpacing(0)

        baris_judul = QHBoxLayout()
        baris_judul.setSpacing(10)
        l_judul = QLabel(judul)
        l_judul.setStyleSheet(
            f"font-family: '{theme.FONT_SERIF}'; font-size: 23px; "
            f"font-weight: 600; color: {C.TEXT}; background: transparent;")
        baris_judul.addWidget(l_judul, 0, Qt.AlignVCenter)
        baris_judul.addStretch(1)
        if utama:
            tag = _label("Disarankan", 11, C.ACCENT_DARK, 600)
            baris_judul.addWidget(tag, 0, Qt.AlignVCenter)
        lay.addLayout(baris_judul)

        lay.addSpacing(3)
        l_sub = QLabel(sub)
        l_sub.setWordWrap(True)
        l_sub.setStyleSheet(f"font-size: {theme.FS_SMALL}px; color: {C.TEXT_MUTED}; "
                            "background: transparent;")
        lay.addWidget(l_sub)

        lay.addSpacing(16)
        for teks in daftar:
            tt = QLabel(f"•   {teks}")
            tt.setWordWrap(True)
            tt.setStyleSheet(f"font-size: {theme.FS_SMALL}px; color: {C.TEXT}; "
                             f"background: transparent;")
            lay.addWidget(tt)
            lay.addSpacing(6)

        lay.addStretch(1)
        btn = w.tombol("Pilih mode ini", gaya="primary" if utama else "biasa")
        btn.setMinimumHeight(40)
        btn.clicked.connect(lambda: self._pilih(pilihan))
        lay.addWidget(btn)
        return kartu

    def _pilih(self, mode: str):
        try:
            sec.update_user_mode(self.user.user_id, mode)
        except Exception:
            pass
        self.selesai.emit(mode)
