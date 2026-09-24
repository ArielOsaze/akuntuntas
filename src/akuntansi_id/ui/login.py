"""
AkunTuntas - Halaman Login & Penyiapan Awal
============================================
Alur:
  1. Login (wajib - data pembukuan bersifat rahasia)
  2. Ganti password (bila pertama kali)
  3. Pilih mode penggunaan: Pemula (banyak penjelasan) atau Ahli
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QPainter, QColor, QLinearGradient, QBrush
from PySide6.QtWidgets import (
    QSizePolicy,
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QCheckBox, QFrame,
)

from .. import config
from ..core import security as sec
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


# ==========================================================================
# PANEL KIRI (BRANDING)
# ==========================================================================
class BrandPanel(QFrame):
    """Panel gelap berisi nama aplikasi dan penjelasan singkat."""

    # Lebar panel merek: dipakai bila jendela lapang.
    LEBAR_INGIN = 452

    def __init__(self, parent=None):
        super().__init__(parent)
        # Panel merek memakai lebar 452 piksel bila ruang mencukupi, tetapi
        # boleh menyusut sampai 380 piksel pada jendela sempit. Di bawah
        # 380 piksel teks penjelasannya mulai terpotong, jadi batas itu
        # tidak diturunkan.
        self.setMinimumWidth(380)
        self.setMaximumWidth(452)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        theme.latar(self, f"background: {C.SIDEBAR_BG}; border: none;")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(44, 44, 44, 38)
        lay.setSpacing(0)

        # Logo
        logo = w.logo_label(64)
        lay.addWidget(logo)

        lay.addSpacing(16)
        judul = QLabel("AkunTuntas")
        judul.setObjectName("LoginTitle")
        lay.addWidget(judul)

        sub = QLabel("Pembukuan & Pajak\nPerusahaan Indonesia")
        sub.setObjectName("LoginSub")
        sub.setStyleSheet("font-size: 17px; color: #E4EDF6; background: transparent; "
                          "line-height: 150%;")
        lay.addWidget(sub)

        lay.addSpacing(12)
        versi = QLabel(f"{config.APP_EDITION} · v{config.APP_VERSION}")
        versi.setStyleSheet("font-size: 11px; color: #C3D4E4; background: transparent;")
        lay.addWidget(versi)

        # Nomor regulasi disebutkan supaya klaim "sesuai aturan terbaru" dapat
        # diperiksa, bukan sekadar tulisan. Ini yang dicari calon pengguna
        # sebelum memutuskan memakai aplikasi pembukuan.
        aturan = QLabel("PP 55/2022 · PP 20/2026 · PMK 81/2024 · PMK 168/2023")
        aturan.setWordWrap(True)
        aturan.setStyleSheet("font-size: 10px; color: #A9BCCE; "
                             "background: transparent;")
        lay.addWidget(aturan)

        lay.addSpacing(24)

        # Contoh nyata dari cara aplikasi bekerja. Angka besar seperti
        # "96 akun" tidak menjelaskan apa pun; contoh di bawah ini
        # memperlihatkan hal yang membedakan aplikasi ini — pajaknya
        # dihitung sendiri dari transaksi, bukan diketik terpisah.
        kartu = QFrame()
        theme.latar(kartu, "background: rgba(255, 255, 255, 0.05); "
                           "border: 1px solid rgba(195, 212, 228, 0.20); "
                           "border-radius: 9px;")
        kl = QVBoxLayout(kartu)
        kl.setContentsMargins(16, 14, 16, 14)
        kl.setSpacing(8)

        j = QLabel("Penjualan jasa Rp10.000.000 ke pelanggan PKP")
        j.setStyleSheet("font-size: 11px; font-weight: 700; color: #E4EDF6; "
                        "background: transparent;")
        kl.addWidget(j)

        for kiri, kanan, warna in (
                ("Piutang usaha", "11.100.000", "#D6E4F0"),
                ("PPN keluaran 11%", "1.100.000", "#6EE7B7"),
                ("Pendapatan jasa", "10.000.000", "#D6E4F0")):
            b = QHBoxLayout()
            b.setSpacing(8)
            n = QLabel(kiri)
            n.setStyleSheet("font-size: 11px; color: #D6E4F0; "
                            "background: transparent;")
            b.addWidget(n)
            b.addStretch()
            v = QLabel(kanan)
            v.setStyleSheet(f"font-size: 11px; color: {warna}; "
                            "font-family: Consolas, monospace; "
                            "background: transparent;")
            b.addWidget(v)
            kl.addLayout(b)

        cat = QLabel("PPN dihitung dengan DPP nilai lain (11/12), jurnal "
                     "tetap seimbang.")
        cat.setWordWrap(True)
        cat.setStyleSheet("font-size: 10px; color: #A9BCCE; "
                          "background: transparent;")
        kl.addWidget(cat)
        lay.addWidget(kartu)

        lay.addSpacing(22)

        # Tiga keterangan, disusun sebagai daftar bernomor supaya berbeda
        # dari blok di atas dan tidak terasa berulang.
        for nomor, judul_baris, rincian in (
                ("1", "Pajak dihitung, bukan diketik ulang",
                 "Nilai PPh dan PPN muncul dari jurnal yang Anda masukkan, "
                 "lengkap dengan pasal dan dasar hukumnya."),
                ("2", "Tersimpan di komputer Anda",
                 "Pembukuan tidak dikirim ke internet. Cadangan dibuat "
                 "otomatis agar data tidak hilang."),
                ("3", "Tercatat siapa mengubah apa",
                 "Setiap perubahan data dan setiap kali masuk aplikasi masuk "
                 "jejak audit.")):
            b = QHBoxLayout()
            b.setSpacing(12)

            no = QLabel(nomor)
            no.setFixedSize(20, 20)
            no.setAlignment(Qt.AlignCenter)
            theme.latar(no, "background: rgba(195, 212, 228, 0.14); "
                            "border-radius: 10px; color: #C3D4E4; "
                            "font-size: 11px; font-weight: 700;")
            b.addWidget(no, 0, Qt.AlignTop)

            kolom = QVBoxLayout()
            kolom.setSpacing(1)
            j = QLabel(judul_baris)
            j.setStyleSheet("font-size: 12px; font-weight: 600; color: #FFFFFF; "
                            "background: transparent;")
            kolom.addWidget(j)
            r = QLabel(rincian)
            r.setWordWrap(True)
            r.setStyleSheet("font-size: 11px; color: #A9BCCE; "
                            "background: transparent; line-height: 140%;")
            kolom.addWidget(r)
            b.addLayout(kolom, 1)

            lay.addLayout(b)
            lay.addSpacing(13)

        lay.addStretch()

        # Catatan hukum
        catatan = QLabel(
            "Aplikasi ini membantu administrasi dan estimasi perpajakan. "
            "Transaksi khusus dan interpretasi regulasi tetap perlu diverifikasi "
            "sesuai fakta dan ketentuan terbaru."
        )
        catatan.setWordWrap(True)
        catatan.setStyleSheet("font-size: 10px; color: #C3D4E4; background: transparent; "
                              "line-height: 145%;")
        lay.addWidget(catatan)

    def sizeHint(self):
        """
        Lebar yang diinginkan panel merek.

        Qt memakai isyarat ini untuk membagi ruang antara panel merek dan
        formulir. Tanpa isyarat ini, panel akan memakai ukuran minimumnya
        (380 piksel) meskipun jendela lapang, sehingga panel merek tampak
        lebih sempit daripada rancangannya.
        """
        ukuran = super().sizeHint()
        ukuran.setWidth(self.LEBAR_INGIN)
        return ukuran

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        g = QLinearGradient(0, 0, self.width(), self.height())
        g.setColorAt(0.0, QColor(C.SIDEBAR_BG))
        g.setColorAt(1.0, QColor("#0A1F33"))
        p.fillRect(self.rect(), QBrush(g))
        p.end()


# ==========================================================================
# HALAMAN LOGIN
# ==========================================================================
class LoginPage(QWidget):
    berhasil = Signal(object)   # LoginResult

    def __init__(self, parent=None):
        super().__init__(parent)
        # Hasil login terakhir, dipakai layar berikutnya untuk menyimpan mode.
        self.hasil_terakhir = None
        luar = QHBoxLayout(self)
        luar.setContentsMargins(0, 0, 0, 0)
        luar.setSpacing(0)

        luar.addWidget(BrandPanel())

        # sisi kanan: form
        kanan = QWidget()
        theme.latar(kanan, f"background: {C.SURFACE};")
        kl = QVBoxLayout(kanan)
        # Bantalan samping form menyesuaikan lebar jendela: 64 piksel bila
        # lapang, dan menyusut sampai 36 piksel pada jendela sempit supaya
        # formulir selebar 400 piksel tetap mendapat ruang penuh.
        kl.setContentsMargins(36, 40, 36, 40)
        kl.setSpacing(0)
        kl.addStretch()

        form = QWidget()
        form.setMaximumWidth(400)
        fl = QVBoxLayout(form)
        fl.setContentsMargins(0, 0, 0, 0)
        fl.setSpacing(0)

        # Garis aksen pendek di atas judul. Detail kecil ini menandai awal
        # formulir dan memberi kesan halaman yang dirancang, bukan sekadar
        # susunan kolom bawaan.
        aksen = QFrame()
        aksen.setFixedSize(28, 3)
        theme.latar(aksen, f"background: {C.PRIMARY}; border-radius: 2px;")
        fl.addWidget(aksen)
        fl.addSpacing(16)

        judul = QLabel("Masuk ke akun Anda")
        judul.setStyleSheet(f"font-size: 25px; font-weight: 700; color: {C.TEXT}; "
                            "background: transparent;")
        fl.addWidget(judul)
        fl.addSpacing(7)
        ket = QLabel("Data pembukuan Anda dilindungi. Masukkan kredensial untuk melanjutkan.")
        ket.setWordWrap(True)
        ket.setStyleSheet(f"font-size: {theme.FS_SMALL}px; color: {C.TEXT_MUTED}; "
                          "background: transparent;")
        fl.addWidget(ket)
        fl.addSpacing(30)

        fl.addWidget(w.label("Nama Pengguna", objek="FormLabel"))
        fl.addSpacing(6)
        self.inp_user = QLineEdit()
        self.inp_user.setObjectName("LoginInput")
        self.inp_user.setPlaceholderText("mis. admin")
        self.inp_user.setMinimumHeight(42)
        fl.addWidget(self.inp_user)
        fl.addSpacing(16)

        fl.addWidget(w.label("Password", objek="FormLabel"))
        fl.addSpacing(6)

        # Kolom password dengan tombol lihat/sembunyikan. Tombol ini penting:
        # salah ketik password sulit disadari karena hurufnya tersembunyi,
        # apalagi saat Caps Lock menyala tanpa disadari.
        wadah_pass = QFrame()
        theme.latar(wadah_pass, f"background: {C.SURFACE}; "
                                f"border: 1px solid {C.BORDER}; border-radius: 8px;")
        wpl = QHBoxLayout(wadah_pass)
        wpl.setContentsMargins(0, 0, 6, 0)
        wpl.setSpacing(0)

        self.inp_pass = QLineEdit()
        self.inp_pass.setPlaceholderText("••••••••")
        self.inp_pass.setEchoMode(QLineEdit.Password)
        self.inp_pass.setMinimumHeight(42)
        self.inp_pass.setStyleSheet(
            "QLineEdit { border: none; background: transparent; "
            f"padding: 0 10px; font-size: {theme.FS_BODY}px; }}")
        self.inp_pass.returnPressed.connect(self._login)
        self.inp_pass.textChanged.connect(self._perbarui_capslock)
        wpl.addWidget(self.inp_pass, 1)

        self.btn_lihat = QPushButton("Lihat")
        self.btn_lihat.setObjectName("Ghost")
        self.btn_lihat.setCursor(Qt.PointingHandCursor)
        self.btn_lihat.setCheckable(True)
        self.btn_lihat.setFixedWidth(62)
        self.btn_lihat.setStyleSheet(
            f"QPushButton {{ border: none; background: transparent; color: {C.PRIMARY}; "
            f"font-size: {theme.FS_SMALL}px; font-weight: 600; padding: 4px; }}"
            f"QPushButton:hover {{ color: {C.PRIMARY_DARK}; }}")
        self.btn_lihat.toggled.connect(self._ganti_lihat_password)
        wpl.addWidget(self.btn_lihat)

        fl.addWidget(wadah_pass)

        # Peringatan Caps Lock: muncul hanya saat menyala dan kolom password
        # sedang dipakai, supaya tidak menambah kebisingan tampilan.
        self.lbl_caps = QLabel("Caps Lock menyala")
        self.lbl_caps.setStyleSheet(
            f"font-size: {theme.FS_TINY}px; color: {C.WARNING}; "
            "background: transparent; font-weight: 600;")
        self.lbl_caps.hide()
        fl.addSpacing(5)
        fl.addWidget(self.lbl_caps)

        fl.addSpacing(10)
        baris_opsi = QHBoxLayout()
        self.chk_ingat = QCheckBox("Ingat nama pengguna")
        self.chk_ingat.setStyleSheet(f"font-size: {theme.FS_SMALL}px; "
                                     "background: transparent;")
        baris_opsi.addWidget(self.chk_ingat)
        baris_opsi.addStretch()
        self.btn_lupa = QPushButton("Lupa password?")
        self.btn_lupa.setObjectName("Ghost")
        self.btn_lupa.setCursor(Qt.PointingHandCursor)
        self.btn_lupa.clicked.connect(self._lupa_password)
        baris_opsi.addWidget(self.btn_lupa)
        fl.addLayout(baris_opsi)

        fl.addSpacing(16)
        self.lbl_error = QLabel("")
        self.lbl_error.setWordWrap(True)
        theme.latar(self.lbl_error, f"background: {C.DANGER_BG}; color: {C.DANGER}; border-radius: 7px; "
            f"padding: 10px 12px; font-size: {theme.FS_SMALL}px; font-weight: 600;")
        self.lbl_error.hide()
        fl.addWidget(self.lbl_error)

        fl.addSpacing(14)
        self.btn_login = w.tombol("Masuk", gaya="primary")
        self.btn_login.setMinimumHeight(46)
        # Tombol utama memakai gradasi halus dari warna merek ke warna yang
        # sedikit lebih tua. Tombol rata satu warna tampak datar dan murah;
        # gradasi tipis memberi kesan tombol yang bisa ditekan tanpa berlebihan.
        self.btn_login.setStyleSheet(
            f"QPushButton {{ border: none; color: white; border-radius: 8px; "
            f"font-size: {theme.FS_H3}px; font-weight: 600; padding: 0 16px; "
            f"background: qlineargradient(x1:0, y1:0, x2:0, y2:1, "
            f"stop:0 {C.PRIMARY_LIGHT}, stop:1 {C.PRIMARY}); }}"
            f"QPushButton:hover {{ background: qlineargradient(x1:0, y1:0, "
            f"x2:0, y2:1, stop:0 {C.PRIMARY}, stop:1 {C.PRIMARY_DARK}); }}"
            f"QPushButton:pressed {{ background: {C.PRIMARY_DARK}; }}"
            f"QPushButton:disabled {{ background: {C.BORDER}; color: {C.TEXT_MUTED}; }}")
        self.btn_login.clicked.connect(self._login)
        fl.addWidget(self.btn_login)

        fl.addSpacing(22)
        self.petunjuk = QFrame()
        theme.latar(self.petunjuk, f"background: {C.SURFACE_ALT}; border: 1px solid {C.BORDER}; "
            "border-radius: 8px;")
        pl = QVBoxLayout(self.petunjuk)
        pl.setContentsMargins(14, 12, 14, 12)
        pl.setSpacing(5)
        pj = QLabel("Akun bawaan sistem")
        pj.setStyleSheet(f"font-weight: 700; font-size: {theme.FS_SMALL}px; "
                         f"color: {C.TEXT}; background: transparent;")
        pl.addWidget(pj)
        pt = w.LabelTinggiOtomatis(f"Pengguna: <b>{config.DEFAULT_ADMIN_USER}</b> &nbsp;·&nbsp; "
                    f"Password: <b>{config.DEFAULT_ADMIN_PASSWORD}</b><br>"
                    "<span style='color:#64748B'>Anda akan diminta mengganti password "
                    "saat pertama kali masuk.</span>")
        pt.setWordWrap(True)
        pt.setTextFormat(Qt.RichText)
        pt.setStyleSheet(f"font-size: {theme.FS_SMALL}px; background: transparent;")
        # Tinggi minimum diambil dari sizeHint, bukan heightForWidth: Qt
        # menghitung tinggi teks berformat terlalu pendek sehingga baris
        # terakhirnya terpotong. Tanpa ini, keterangan akun bawaan tampil
        # sebagai potongan huruf.
        pt.setMinimumHeight(theme.tinggi_rich_text(pt))
        kebijakan_pt = pt.sizePolicy()
        kebijakan_pt.setVerticalPolicy(QSizePolicy.MinimumExpanding)
        pt.setSizePolicy(kebijakan_pt)
        pl.addWidget(pt)
        fl.addWidget(self.petunjuk)

        fl.addSpacing(16)

        # Keterangan singkat keadaan data: mengisi ruang bawah sekaligus
        # memberi tahu pengguna apakah ini pemasangan baru atau sudah berisi.
        self.lbl_keadaan = QLabel()
        self.lbl_keadaan.setWordWrap(True)
        self.lbl_keadaan.setAlignment(Qt.AlignCenter)
        self.lbl_keadaan.setStyleSheet(
            f"font-size: {theme.FS_TINY}px; color: {C.TEXT_MUTED}; "
            "background: transparent;")
        fl.addWidget(self.lbl_keadaan)
        self._perbarui_keadaan()

        kl.addWidget(form, 0, Qt.AlignCenter)
        kl.addStretch()
        luar.addWidget(kanan, 1)

        self._muat_preferensi()

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
                    f"{pengguna} pengguna · {perusahaan} perusahaan terdaftar "
                    f"di komputer ini")
            else:
                self.lbl_keadaan.setText(
                    "Belum ada perusahaan terdaftar. Anda akan dipandu "
                    "menambahkannya setelah masuk.")
        except Exception:
            self.lbl_keadaan.setText("")

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
        self.btn_lihat.setFixedWidth(96 if terlihat else 62)

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
        dlg.setMinimumWidth(470)
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(24, 22, 24, 22)
        lay.setSpacing(12)

        j = QLabel("Tidak dapat masuk?")
        j.setStyleSheet(f"font-size: {theme.FS_H2}px; font-weight: 700; "
                        "background: transparent;")
        lay.addWidget(j)

        isi = QLabel(
            "Aplikasi ini menyimpan data secara lokal, sehingga tidak ada pemulihan "
            "password melalui email.\n\n"
            "Langkah yang dapat dilakukan:\n"
            "1. Minta pengguna dengan peran <b>owner</b> membuka menu "
            "<b>Pengaturan -> Pengguna</b> dan mereset password Anda.\n"
            "2. Bila Anda satu-satunya pengguna, buat berkas pemulihan bernama "
            "<b>reset_admin.txt</b> di folder data aplikasi, lalu jalankan ulang "
            "aplikasi. Aplikasi akan meminta Anda membuat password baru."
        )
        isi.setWordWrap(True)
        isi.setTextFormat(Qt.RichText)
        isi.setStyleSheet(f"font-size: {theme.FS_SMALL}px; color: {C.TEXT}; "
                          "background: transparent;")
        lay.addWidget(isi)

        folder = QLabel(f"Folder data: <code>{config.DATA_DIR}</code>")
        folder.setWordWrap(True)
        folder.setTextFormat(Qt.RichText)
        folder.setStyleSheet(f"font-size: {theme.FS_TINY}px; color: {C.TEXT_MUTED}; "
                             "background: transparent;")
        lay.addWidget(folder)

        btn = w.tombol("Mengerti", gaya="primary")
        btn.clicked.connect(dlg.accept)
        baris = QHBoxLayout()
        baris.addStretch()
        baris.addWidget(btn)
        lay.addLayout(baris)
        dlg.exec()


# ==========================================================================
# HALAMAN GANTI PASSWORD (WAJIB SAAT PERTAMA KALI)
# ==========================================================================
class GantiPasswordWajib(QWidget):
    selesai = Signal()

    def __init__(self, user: sec.LoginResult, parent=None):
        super().__init__(parent)
        self.user = user
        theme.latar(self, f"background: {C.BG};")

        luar = QVBoxLayout(self)
        luar.setContentsMargins(0, 0, 0, 0)
        luar.addStretch()

        kartu = w.Card(padding=34)
        kartu.setMaximumWidth(520)
        lay = kartu.body()
        lay.setSpacing(14)

        ikon = QLabel()
        ikon.setPixmap(w.icons.pixmap("kunci", w.icons.WARNA_PRIMER, 44))
        ikon.setAlignment(Qt.AlignCenter)
        ikon.setStyleSheet("background: transparent;")
        lay.addWidget(ikon)

        j = QLabel("Amankan akun Anda")
        j.setAlignment(Qt.AlignCenter)
        j.setStyleSheet("font-size: 21px; font-weight: 700; background: transparent;")
        lay.addWidget(j)

        ket = w.LabelTinggiOtomatis(
            "Anda memakai password bawaan sistem. Demi keamanan data pembukuan, "
            "password <b>wajib</b> diganti sebelum melanjutkan."
        )
        ket.setWordWrap(True)
        ket.setTextFormat(Qt.RichText)
        ket.setAlignment(Qt.AlignCenter)
        ket.setStyleSheet(f"font-size: {theme.FS_SMALL}px; color: {C.TEXT_MUTED}; "
                          "background: transparent;")
        # Qt menghitung tinggi teks berformat lebih pendek dari kebutuhan
        # sebenarnya pada lebar sempit, sehingga baris terakhir terpotong.
        # Tinggi minimum diambil dari pengukuran dokumen teks.
        ket.setMinimumHeight(theme.tinggi_rich_text(ket))
        lay.addWidget(ket)
        lay.addSpacing(6)

        lay.addWidget(w.label("Password Saat Ini", objek="FormLabel"))
        self.inp_lama = QLineEdit()
        self.inp_lama.setEchoMode(QLineEdit.Password)
        self.inp_lama.setMinimumHeight(38)
        self.inp_lama.setText(config.DEFAULT_ADMIN_PASSWORD)
        lay.addWidget(self.inp_lama)

        lay.addWidget(w.label("Password Baru", objek="FormLabel"))
        self.inp_baru = QLineEdit()
        self.inp_baru.setEchoMode(QLineEdit.Password)
        self.inp_baru.setMinimumHeight(38)
        self.inp_baru.textChanged.connect(self._cek_kekuatan)
        lay.addWidget(self.inp_baru)

        self.bar_kekuatan = QLabel("")
        self.bar_kekuatan.setStyleSheet(f"font-size: {theme.FS_TINY}px; "
                                        "background: transparent;")
        lay.addWidget(self.bar_kekuatan)

        lay.addWidget(w.label("Ulangi Password Baru", objek="FormLabel"))
        self.inp_ulang = QLineEdit()
        self.inp_ulang.setEchoMode(QLineEdit.Password)
        self.inp_ulang.setMinimumHeight(38)
        self.inp_ulang.returnPressed.connect(self._simpan)
        lay.addWidget(self.inp_ulang)

        self.lbl_pesan = QLabel("")
        self.lbl_pesan.setWordWrap(True)
        self.lbl_pesan.hide()
        lay.addWidget(self.lbl_pesan)

        btn = w.tombol("Simpan Password Baru", gaya="primary")
        btn.setMinimumHeight(42)
        btn.clicked.connect(self._simpan)
        lay.addWidget(btn)

        syarat = QLabel(
            "Syarat password: minimal 8 karakter, gabungan huruf besar-kecil, "
            "angka, dan simbol."
        )
        syarat.setWordWrap(True)
        syarat.setStyleSheet(f"font-size: {theme.FS_TINY}px; color: {C.TEXT_FAINT}; "
                             "background: transparent;")
        lay.addWidget(syarat)

        tengah = QHBoxLayout()
        tengah.addStretch()
        tengah.addWidget(kartu)
        tengah.addStretch()
        luar.addLayout(tengah)
        luar.addStretch()

    def _cek_kekuatan(self, teks: str):
        if not teks:
            self.bar_kekuatan.setText("")
            return
        skor, label, saran = sec.password_strength(teks)
        warna = [C.DANGER, C.DANGER, C.WARNING, C.SUCCESS, C.SUCCESS][skor]
        bar = "█" * (skor + 1) + "░" * (4 - skor)
        self.bar_kekuatan.setText(f"Kekuatan: <b style='color:{warna}'>{label}</b> "
                                  f"<span style='color:{warna}'>{bar}</span>")
        self.bar_kekuatan.setTextFormat(Qt.RichText)

    def _simpan(self):
        self.lbl_pesan.hide()
        lama, baru, ulang = self.inp_lama.text(), self.inp_baru.text(), self.inp_ulang.text()
        if baru != ulang:
            self._error("Password baru dan ulangannya tidak sama.")
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
        theme.latar(self.lbl_pesan, f"background: {C.DANGER_BG}; color: {C.DANGER}; border-radius: 7px; "
            f"padding: 9px 11px; font-size: {theme.FS_SMALL}px; font-weight: 600;")
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
        theme.latar(self, f"background: {C.BG};")

        luar = QVBoxLayout(self)
        luar.setContentsMargins(60, 40, 60, 40)
        luar.addStretch()

        kepala = QVBoxLayout()
        kepala.setSpacing(8)
        j = QLabel(f"Selamat datang, {user.full_name or user.username}")
        j.setAlignment(Qt.AlignCenter)
        j.setStyleSheet("font-size: 25px; font-weight: 700; background: transparent;")
        kepala.addWidget(j)
        s = QLabel("Pilih cara Anda ingin menggunakan aplikasi ini.\n"
                   "Pilihan ini dapat diubah kapan saja dari menu Pengaturan.")
        s.setAlignment(Qt.AlignCenter)
        s.setWordWrap(True)
        s.setStyleSheet(f"font-size: {theme.FS_BODY}px; color: {C.TEXT_MUTED}; "
                        "background: transparent;")
        kepala.addWidget(s)
        luar.addLayout(kepala)
        luar.addSpacing(34)

        baris = QHBoxLayout()
        baris.setSpacing(22)

        self.kartu_pemula = self._buat_kartu(
            "", "Mode Pemula", "Untuk yang baru memulai pembukuan",
            [
                "Setiap halaman menampilkan panel penjelasan konsep",
                "Istilah akuntansi dijelaskan dengan bahasa sehari-hari",
                "Langkah-langkah kerja dipandu berurutan",
                "Contoh jurnal standar tersedia di setiap formulir",
                "Dasar hukum ditampilkan pada fitur terkait",
            ],
            "Cocok bila Anda belum pernah menyusun pembukuan atau baru beralih dari catatan sederhana.",
            pilihan="beginner",
        )
        baris.addWidget(self.kartu_pemula, 1)

        self.kartu_ahli = self._buat_kartu(
            "", "Mode Ahli", "Untuk akuntan atau yang sudah berpengalaman",
            [
                "Antarmuka ringkas tanpa panel penjelasan",
                "Fokus pada kecepatan input dan analisis",
                "Seluruh fitur tetap lengkap dan dapat diakses",
                "Referensi aturan tetap tersedia di menu Bantuan",
                "Pintasan papan tulis dan navigasi cepat",
            ],
            "Cocok bila Anda sudah memahami dasar akuntansi dan perpajakan Indonesia.",
            pilihan="expert",
        )
        baris.addWidget(self.kartu_ahli, 1)

        luar.addLayout(baris)
        luar.addStretch()

        catatan = w.LabelTinggiOtomatis(
            "Anda tetap dapat mengubah mode ini nanti melalui "
            "<b>Pengaturan -> Preferensi</b>. Data pembukuan tidak terpengaruh."
        )
        catatan.setAlignment(Qt.AlignCenter)
        catatan.setWordWrap(True)
        catatan.setTextFormat(Qt.RichText)
        catatan.setStyleSheet(f"font-size: {theme.FS_SMALL}px; color: {C.TEXT_MUTED}; "
                              "background: transparent;")
        luar.addWidget(catatan)

    def _buat_kartu(self, ikon: str, judul: str, sub: str, daftar: list,
                    catatan: str, pilihan: str) -> QFrame:
        kartu = QFrame()
        kartu.setObjectName("Card")
        kartu.setCursor(Qt.PointingHandCursor)
        kartu.setMinimumHeight(400)

        lay = QVBoxLayout(kartu)
        lay.setContentsMargins(26, 26, 26, 26)
        lay.setSpacing(12)

        l_ikon = QLabel()
        l_ikon.setPixmap(w.icons.pixmap(ikon, C.PRIMARY, 40))
        l_ikon.setFixedSize(40, 40)
        l_ikon.setStyleSheet("background: transparent;")
        lay.addWidget(l_ikon)

        l_judul = QLabel(judul)
        l_judul.setStyleSheet("font-size: 20px; font-weight: 700; background: transparent;")
        lay.addWidget(l_judul)

        l_sub = QLabel(sub)
        l_sub.setStyleSheet(f"font-size: {theme.FS_SMALL}px; color: {C.PRIMARY}; "
                            "font-weight: 600; background: transparent;")
        lay.addWidget(l_sub)
        lay.addSpacing(6)

        for teks in daftar:
            b = QHBoxLayout()
            b.setSpacing(9)
            t = QLabel()
            t.setPixmap(w.icons.pixmap("simpan", C.SUCCESS, 15))
            t.setFixedSize(15, 15)
            t.setStyleSheet("background: transparent;")
            b.addWidget(t)
            tt = QLabel(teks)
            tt.setWordWrap(True)
            tt.setStyleSheet(f"font-size: {theme.FS_SMALL}px; color: {C.TEXT}; "
                             "background: transparent;")
            b.addWidget(tt, 1)
            lay.addLayout(b)

        lay.addStretch()

        l_cat = QLabel(catatan)
        l_cat.setWordWrap(True)
        l_cat.setStyleSheet(f"font-size: {theme.FS_TINY}px; color: {C.TEXT_MUTED}; "
                            "background: transparent; font-style: italic;")
        lay.addWidget(l_cat)
        lay.addSpacing(8)

        btn = w.tombol(f"Pilih {judul}", gaya="primary")
        btn.setMinimumHeight(40)
        btn.clicked.connect(lambda: self._pilih(pilihan))
        lay.addWidget(btn)

        kartu.enterEvent = lambda e, k=kartu: k.setStyleSheet(
            f"QFrame#Card {{ background: {C.SURFACE}; border: 2px solid {C.PRIMARY}; "
            "border-radius: 12px; }}")
        kartu.leaveEvent = lambda e, k=kartu: k.setStyleSheet("")
        return kartu

    def _pilih(self, mode: str):
        try:
            sec.update_user_mode(self.user.user_id, mode)
        except Exception:
            pass
        self.selesai.emit(mode)
