"""
Halaman tata kelola: pengguna & hak akses, log audit, riwayat perubahan,
keranjang sampah, dokumen, impor massal, dan pencarian global.
"""
from __future__ import annotations

import os

from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit, QDialog,
    QMessageBox, QFrame, QGridLayout, QCheckBox, QTabWidget, QFileDialog,
    QTextEdit, QScrollArea, QListWidget, QListWidgetItem, QSplitter,
)

from ... import config, db, modules as M, modules_ops as O
from ...core import security as sec
from ... import istilah
from .. import theme, widgets as w
from ..theme import C


# ==========================================================================
# PENGGUNA & HAK AKSES
# ==========================================================================
class DialogPenggunaBaru(QDialog):
    def __init__(self, ctx, parent=None, pengguna=None):
        super().__init__(parent)
        self.ctx = ctx
        self.pengguna = pengguna
        self.setWindowTitle("Tambah Pengguna" if not pengguna else "Ubah Pengguna")
        self.setMinimumWidth(600)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 22, 24, 22)
        lay.setSpacing(13)

        j = QLabel("Pengguna Baru" if not pengguna else "Ubah Pengguna")
        j.setObjectName("SectionTitle")
        lay.addWidget(j)

        lay.addWidget(w.HelpPanel(
            "Tentang peran pengguna",
            "Peran menentukan hak akses awal:\n\n"
            "• Pemilik (owner) - akses penuh, termasuk pengaturan dan hapus data\n"
            "• Administrator - hampir penuh, kecuali pengaturan sensitif\n"
            "• Staf - dapat membuat transaksi, tidak dapat menghapus atau "
            "mengubah pengaturan\n"
            "• Hanya Lihat (viewer) - hanya membaca laporan\n\n"
            "Hak akses tiap pengguna dapat disesuaikan satu per satu setelah "
            "akun dibuat.",
            "Pengendalian internal - pemisahan tugas (segregation of duties)."))

        g = QGridLayout()
        g.setSpacing(12)

        g.addWidget(w.label("Nama Pengguna (username)", objek="FormLabel"), 0, 0)
        self.inp_username = QLineEdit()
        self.inp_username.setPlaceholderText("mis. budi.santoso")
        g.addWidget(self.inp_username, 1, 0)

        g.addWidget(w.label("Nama Lengkap", objek="FormLabel"), 0, 1)
        self.inp_nama = QLineEdit()
        self.inp_nama.setPlaceholderText("mis. Budi Santoso")
        g.addWidget(self.inp_nama, 1, 1)

        g.addWidget(w.label("Email", objek="FormLabel"), 2, 0)
        self.inp_email = QLineEdit()
        g.addWidget(self.inp_email, 3, 0)

        g.addWidget(w.label("Jabatan", objek="FormLabel"), 2, 1)
        self.inp_jabatan = QLineEdit()
        self.inp_jabatan.setPlaceholderText("mis. Staf Akuntansi")
        g.addWidget(self.inp_jabatan, 3, 1)

        g.addWidget(w.label("Peran", objek="FormLabel"), 4, 0)
        self.cmb_role = QComboBox()
        self.cmb_role.addItem("Staf", "staff")
        self.cmb_role.addItem("Administrator", "admin")
        self.cmb_role.addItem("Hanya Lihat", "viewer")
        g.addWidget(self.cmb_role, 5, 0)

        g.addWidget(w.label("Mode Tampilan", objek="FormLabel"), 4, 1)
        self.cmb_mode = QComboBox()
        self.cmb_mode.addItem("Pemula (dengan keterangan)", "beginner")
        self.cmb_mode.addItem("Ahli (tanpa keterangan)", "expert")
        g.addWidget(self.cmb_mode, 5, 1)
        lay.addLayout(g)

        self.lbl_kuat = QLabel("")
        self.lbl_kuat.setWordWrap(True)
        if not pengguna:
            lay.addWidget(w.label("Kata Sandi", objek="FormLabel"))
            self.inp_password = QLineEdit()
            self.inp_password.setEchoMode(QLineEdit.Password)
            self.inp_password.textChanged.connect(self._cek_kuat)
            lay.addWidget(self.inp_password)

            lay.addWidget(w.label("Ulangi Kata Sandi", objek="FormLabel"))
            self.inp_password2 = QLineEdit()
            self.inp_password2.setEchoMode(QLineEdit.Password)
            lay.addWidget(self.inp_password2)
            lay.addWidget(self.lbl_kuat)

        self.chk_aktif = QCheckBox("Akun aktif")
        self.chk_aktif.setChecked(True)
        lay.addWidget(self.chk_aktif)

        aksi = QHBoxLayout()
        aksi.addStretch()
        b = w.tombol("Batal")
        b.clicked.connect(self.reject)
        aksi.addWidget(b)
        bs = w.tombol("Simpan", gaya="primary")
        bs.clicked.connect(self._simpan)
        aksi.addWidget(bs)
        lay.addLayout(aksi)

        if pengguna:
            self._muat()

    def _cek_kuat(self, teks: str):
        if not teks:
            self.lbl_kuat.setText("")
            return
        skor, label, saran = sec.password_strength(teks)
        warna = [C.DANGER, C.WARNING, C.WARNING, C.SUCCESS, C.SUCCESS][skor]
        pesan = f"<b style='color:{warna}'>Kekuatan: {label}</b>"
        if saran:
            pesan += f"<br><span style='color:{C.TEXT_MUTED}'>" + \
                     " · ".join(saran[:2]) + "</span>"
        self.lbl_kuat.setText(pesan)
        self.lbl_kuat.setTextFormat(Qt.RichText)

    def _muat(self):
        p = self.pengguna
        self.inp_username.setText(p["username"])
        self.inp_username.setEnabled(False)
        self.inp_nama.setText(p["full_name"] or "")
        self.inp_email.setText(p["email"] or "")
        self.inp_jabatan.setText(p["jabatan"] or "")
        i = self.cmb_role.findData(p["role"])
        if i >= 0:
            self.cmb_role.setCurrentIndex(i)
        i = self.cmb_mode.findData(p["app_mode"])
        if i >= 0:
            self.cmb_mode.setCurrentIndex(i)
        self.chk_aktif.setChecked(bool(p["is_active"]))

    def _simpan(self):
        try:
            if self.pengguna:
                db.ex("""UPDATE users SET full_name=?, email=?, jabatan=?, role=?,
                         app_mode=?, is_active=? WHERE id=?""",
                      (self.inp_nama.text().strip(), self.inp_email.text().strip(),
                       self.inp_jabatan.text().strip(), self.cmb_role.currentData(),
                       self.cmb_mode.currentData(),
                       1 if self.chk_aktif.isChecked() else 0,
                       self.pengguna["id"]))
                M.catat_riwayat(None, "users", self.pengguna["id"], "ubah",
                                f"Peran: {self.cmb_role.currentData()}",
                                self.ctx.username)
            else:
                username = self.inp_username.text().strip()
                p1 = self.inp_password.text()
                p2 = self.inp_password2.text()
                if not username:
                    QMessageBox.warning(self, "Username kosong",
                                        "Isi nama pengguna.")
                    return
                if p1 != p2:
                    QMessageBox.warning(self, "Kata sandi berbeda",
                                        "Ulangi kata sandi dengan benar.")
                    return
                ok, saran = sec.is_password_acceptable(p1)
                if not ok:
                    QMessageBox.warning(self, "Kata sandi lemah",
                                        " ".join(saran))
                    return
                sec.create_user(username, p1, self.inp_nama.text().strip(),
                                self.cmb_role.currentData())
                baru = db.q1("SELECT id FROM users WHERE username=?", (username,))
                if baru:
                    db.ex("""UPDATE users SET email=?, jabatan=?, app_mode=?
                             WHERE id=?""",
                          (self.inp_email.text().strip(),
                           self.inp_jabatan.text().strip(),
                           self.cmb_mode.currentData(), baru["id"]))
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Gagal menyimpan", str(e))


class DialogIzinPengguna(QDialog):
    def __init__(self, ctx, pengguna, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.pengguna = pengguna
        self.setWindowTitle(f"Hak Akses - {pengguna['full_name'] or pengguna['username']}")
        self.setMinimumSize(760, 660)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 20, 22, 20)
        lay.setSpacing(12)

        j = QLabel("Hak Akses per Modul")
        j.setObjectName("SectionTitle")
        lay.addWidget(j)

        lay.addWidget(w.HelpPanel(
            "Cara kerja hak akses",
            f"Peran pengguna saat ini: <b>{pengguna['role']}</b>.\n\n"
            "Centang berarti pengguna memiliki izin. Izin di sini menimpa "
            "izin bawaan peran, sehingga Anda dapat memberi izin tambahan "
            "atau mencabut izin tertentu tanpa mengubah peran.\n\n"
            "Perubahan berlaku saat pengguna berikutnya login.",
            "Pengendalian internal - prinsip hak akses minimum (least privilege)."))

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        isi = QWidget()
        self.lay_isi = QVBoxLayout(isi)
        self.lay_isi.setContentsMargins(0, 0, 8, 0)
        self.lay_isi.setSpacing(10)

        self.checks: dict[str, QCheckBox] = {}
        izin_pengguna = M.izin_pengguna(pengguna["id"], pengguna["role"])
        izin_peran = M.izin_peran(pengguna["role"])

        for modul in M.modul_izin():
            kartu = w.Card()
            kl = kartu.body()
            judul = QLabel(modul.title())
            judul.setStyleSheet(f"font-size: {theme.FS_H3}px; font-weight: 700; "
                                "background: transparent;")
            kl.addWidget(judul)

            grid = QGridLayout()
            grid.setSpacing(6)
            for i, p in enumerate(M.daftar_izin(modul)):
                chk = QCheckBox(f"{p['nama']}")
                chk.setChecked(p["kode"] in izin_pengguna)
                chk.setToolTip(p["deskripsi"] or "")
                if p["kode"] not in izin_peran:
                    chk.setStyleSheet(f"color: {C.INFO};")
                self.checks[p["kode"]] = chk
                grid.addWidget(chk, i // 2, i % 2)
            kl.addLayout(grid)
            self.lay_isi.addWidget(kartu)

        self.lay_isi.addStretch()
        self.scroll.setWidget(isi)
        lay.addWidget(self.scroll, 1)

        baris = QHBoxLayout()
        baris.setSpacing(9)
        b1 = w.tombol("Ikuti Peran Saja", ikon="segarkan")
        b1.clicked.connect(self._reset_peran)
        baris.addWidget(b1)
        b2 = w.tombol("Pilih Semua", ikon="simpan")
        b2.clicked.connect(lambda: self._set_semua(True))
        baris.addWidget(b2)
        b3 = w.tombol("Kosongkan", ikon="")
        b3.clicked.connect(lambda: self._set_semua(False))
        baris.addWidget(b3)
        baris.addStretch()
        lay.addLayout(baris)

        aksi = QHBoxLayout()
        aksi.addStretch()
        b = w.tombol("Batal")
        b.clicked.connect(self.reject)
        aksi.addWidget(b)
        bs = w.tombol("Simpan Hak Akses", gaya="primary")
        bs.clicked.connect(self._simpan)
        aksi.addWidget(bs)
        lay.addLayout(aksi)

    def _set_semua(self, nilai: bool):
        for chk in self.checks.values():
            chk.setChecked(nilai)

    def _reset_peran(self):
        izin_peran = M.izin_peran(self.pengguna["role"])
        for kode, chk in self.checks.items():
            chk.setChecked(kode in izin_peran)

    def _simpan(self):
        try:
            for kode, chk in self.checks.items():
                M.set_izin_pengguna(self.pengguna["id"], kode, chk.isChecked())
            M.catat_riwayat(None, "users", self.pengguna["id"], "ubah",
                            "Hak akses diperbarui", self.ctx.username)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Gagal menyimpan", str(e))


class PenggunaPage(QWidget):
    pindah_halaman = Signal(str)

    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx

        luar = QVBoxLayout(self)
        luar.setContentsMargins(0, 0, 0, 0)
        luar.setSpacing(0)

        self.header = w.PageHeader(
            "Pengguna & Hak Akses",
            "Kelola akun pengguna, peran, dan izin per modul.")

        b = w.tombol("Tambah Pengguna", gaya="primary", ikon="+")
        b.clicked.connect(self._tambah)
        self.header.tambah_aksi(b)

        kepala = QWidget()
        theme.latar(kepala, f"background: {C.SURFACE}; "
                             f"border-bottom: 1px solid {C.BORDER};")
        kl = QVBoxLayout(kepala)
        kl.setContentsMargins(26, 20, 26, 18)
        kl.addWidget(self.header)
        luar.addWidget(kepala)

        isi = QWidget()
        self.lay = QVBoxLayout(isi)
        self.lay.setContentsMargins(24, 20, 24, 22)
        self.lay.setSpacing(13)
        luar.addWidget(isi, 1)

        self.tabel = w.Tabel([
            ("Username", 155), ("Nama Lengkap", -1), ("Jabatan", 165),
            ("Peran", 135), ("Mode", 115), ("Status", 105), ("Login Terakhir", 155),
        ])
        self.tabel.doubleClicked.connect(self._ubah)
        self.lay.addWidget(self.tabel, 1)

        baris = QHBoxLayout()
        baris.setSpacing(9)
        b1 = w.tombol("Ubah", ikon="pengaturan")
        b1.clicked.connect(self._ubah)
        baris.addWidget(b1)
        b2 = w.tombol("Atur Hak Akses", gaya="primary", ikon="pengguna")
        b2.clicked.connect(self._izin)
        baris.addWidget(b2)
        b3 = w.tombol("Reset Kata Sandi", ikon="segarkan")
        b3.clicked.connect(self._reset_password)
        baris.addWidget(b3)
        b4 = w.tombol("Aktifkan/Nonaktifkan", ikon="keluar")
        b4.clicked.connect(self._toggle_aktif)
        baris.addWidget(b4)
        baris.addStretch()
        self.lbl_info = QLabel("")
        self.lbl_info.setObjectName("Muted")
        baris.addWidget(self.lbl_info)
        self.lay.addLayout(baris)

    def muat(self):
        data = sec.list_users()
        baris, warna = [], {}
        for i, p in enumerate(data):
            idx = len(baris)
            baris.append([
                p["username"], p["full_name"] or "", p["jabatan"] or "",
                {"owner": "Pemilik", "admin": "Administrator",
                 "staff": "Staf", "viewer": "Hanya Lihat"}.get(p["role"], p["role"]),
                "Pemula" if p["app_mode"] == "beginner" else "Ahli",
                "Aktif" if p["is_active"] else "Nonaktif",
                (p["last_login"] or "")[:16],
            ])
            if not p["is_active"]:
                warna[idx] = C.TEXT_FAINT
        self.tabel.isi(baris, warna_baris=warna)
        self.lbl_info.setText(f"{len(data)} pengguna terdaftar")

    def _pengguna_terpilih(self):
        r = self.tabel.baris_terpilih()
        if r is None:
            return None
        data = sec.list_users()
        return data[r] if r < len(data) else None

    def _tambah(self):
        d = DialogPenggunaBaru(self.ctx, self)
        if d.exec():
            self.muat()

    def _ubah(self):
        p = self._pengguna_terpilih()
        if p is None:
            QMessageBox.information(self, "Belum dipilih", "Pilih satu pengguna.")
            return
        d = DialogPenggunaBaru(self.ctx, self, p)
        if d.exec():
            self.muat()

    def _izin(self):
        p = self._pengguna_terpilih()
        if p is None:
            QMessageBox.information(self, "Belum dipilih", "Pilih satu pengguna.")
            return
        d = DialogIzinPengguna(self.ctx, p, self)
        if d.exec():
            self.muat()

    def _reset_password(self):
        p = self._pengguna_terpilih()
        if p is None:
            QMessageBox.information(self, "Belum dipilih", "Pilih satu pengguna.")
            return
        d = DialogResetPassword(self.ctx, p, self)
        if d.exec():
            QMessageBox.information(
                self, "Kata sandi direset",
                f"Kata sandi {p['username']} berhasil diubah. Sampaikan kata sandi "
                "baru kepada pengguna secara aman.")

    def _toggle_aktif(self):
        p = self._pengguna_terpilih()
        if p is None:
            QMessageBox.information(self, "Belum dipilih", "Pilih satu pengguna.")
            return
        if p["id"] == self.ctx.user_id:
            QMessageBox.warning(self, "Tidak diizinkan",
                                "Anda tidak dapat menonaktifkan akun sendiri.")
            return
        if p["role"] == "owner":
            jumlah_owner = len([x for x in sec.list_users()
                                if x["role"] == "owner" and x["is_active"]])
            if p["is_active"] and jumlah_owner <= 1:
                QMessageBox.warning(
                    self, "Tidak diizinkan",
                    "Minimal harus ada satu akun Pemilik yang aktif.")
                return
        aksi = "nonaktifkan" if p["is_active"] else "aktifkan"
        if QMessageBox.question(
                self, "Konfirmasi",
                f"Yakin ingin {aksi} akun '{p['username']}'?",
                QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return
        try:
            sec.set_user_active(p["id"], not p["is_active"], self.ctx.user_id,
                                self.ctx.username)
            self.muat()
        except Exception as e:
            QMessageBox.critical(self, "Gagal", str(e))


class DialogResetPassword(QDialog):
    def __init__(self, ctx, pengguna, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.pengguna = pengguna
        self.setWindowTitle("Reset Kata Sandi")
        self.setMinimumWidth(520)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 22, 24, 22)
        lay.setSpacing(13)

        j = QLabel(f"Reset Kata Sandi - {pengguna['username']}")
        j.setObjectName("SectionTitle")
        lay.addWidget(j)

        lay.addWidget(w.label("Kata Sandi Baru", objek="FormLabel"))
        self.inp1 = QLineEdit()
        self.inp1.setEchoMode(QLineEdit.Password)
        self.inp1.textChanged.connect(self._cek)
        lay.addWidget(self.inp1)

        lay.addWidget(w.label("Ulangi Kata Sandi", objek="FormLabel"))
        self.inp2 = QLineEdit()
        self.inp2.setEchoMode(QLineEdit.Password)
        lay.addWidget(self.inp2)

        self.lbl = QLabel("")
        self.lbl.setWordWrap(True)
        lay.addWidget(self.lbl)

        aksi = QHBoxLayout()
        aksi.addStretch()
        b = w.tombol("Batal")
        b.clicked.connect(self.reject)
        aksi.addWidget(b)
        bs = w.tombol("Reset", gaya="primary")
        bs.clicked.connect(self._simpan)
        aksi.addWidget(bs)
        lay.addLayout(aksi)

    def _cek(self, teks: str):
        if not teks:
            self.lbl.setText("")
            return
        skor, label, saran = sec.password_strength(teks)
        warna = [C.DANGER, C.WARNING, C.WARNING, C.SUCCESS, C.SUCCESS][skor]
        pesan = f"<b style='color:{warna}'>Kekuatan: {label}</b>"
        if saran:
            pesan += f"<br><span style='color:{C.TEXT_MUTED}'>" + \
                     " · ".join(saran[:2]) + "</span>"
        self.lbl.setText(pesan)
        self.lbl.setTextFormat(Qt.RichText)

    def _simpan(self):
        if self.inp1.text() != self.inp2.text():
            QMessageBox.warning(self, "Kata sandi berbeda",
                                "Ulangi kata sandi dengan benar.")
            return
        ok, saran = sec.is_password_acceptable(self.inp1.text())
        if not ok:
            QMessageBox.warning(self, "Kata sandi lemah", " ".join(saran))
            return
        try:
            sec.reset_password(self.pengguna["id"], self.inp1.text(),
                               self.ctx.user_id, self.ctx.username)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Gagal", str(e))


# ==========================================================================
# LOG AUDIT & RIWAYAT
# ==========================================================================
class AuditPage(QWidget):
    pindah_halaman = Signal(str)

    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx

        luar = QVBoxLayout(self)
        luar.setContentsMargins(0, 0, 0, 0)
        luar.setSpacing(0)

        self.header = w.PageHeader(
            "Log Audit & Riwayat Perubahan",
            "Jejak semua aktivitas pengguna dan perubahan data - bukti "
            "pengendalian internal.")

        b = w.tombol("Ekspor CSV", ikon="ekspor")
        b.clicked.connect(self._ekspor)
        self.header.tambah_aksi(b)

        kepala = QWidget()
        theme.latar(kepala, f"background: {C.SURFACE}; "
                             f"border-bottom: 1px solid {C.BORDER};")
        kl = QVBoxLayout(kepala)
        kl.setContentsMargins(26, 20, 26, 18)
        kl.addWidget(self.header)
        luar.addWidget(kepala)

        isi = QWidget()
        self.lay = QVBoxLayout(isi)
        self.lay.setContentsMargins(24, 20, 24, 22)
        self.lay.setSpacing(13)
        luar.addWidget(isi, 1)

        if ctx.beginner:
            self.lay.addWidget(w.HelpPanel(
                "Mengapa log audit penting",
                "Log audit merekam siapa mengerjakan apa dan kapan. Ini "
                "melindungi Anda: bila ada selisih, Anda dapat menelusuri asal "
                "perubahan.\n\n"
                "Untuk kepatuhan pajak, pembukuan dan bukti pendukung wajib "
                "disimpan. Log audit memperkuat posisi Anda bila ada pemeriksaan.",
                "Pasal 28 ayat (1) dan (11) UU KUP - kewajiban menyelenggarakan "
                "pembukuan dan menyimpan dokumen selama 10 tahun."))

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tab_keamanan = QWidget()
        self.tab_data = QWidget()
        self.tab_admin = QWidget()
        self.tab_riwayat = QWidget()
        self.tabs.addTab(self.tab_keamanan, "Log Keamanan")
        self.tabs.addTab(self.tab_data, "Log Perubahan Data")
        self.tabs.addTab(self.tab_admin, "Log Administrasi")

        # Riwayat perubahan data menyertakan penelusuran lanjutan, sehingga
        # hanya tersedia pada paket Enterprise. Tab lain tetap terbuka karena
        # termasuk pemantauan dasar.
        from .. import batas_paket
        if batas_paket.boleh_pakai(self.ctx.lisensi, "audit_lanjutan"):
            self.tabs.addTab(self.tab_riwayat, "Riwayat Perubahan Data")

        self.tabs.currentChanged.connect(self.muat)
        self.lay.addWidget(self.tabs, 1)

        self._bangun_audit()
        self._bangun_riwayat()

    def _bangun_audit(self):
        """
        Bangun tiga tab jejak audit: keamanan, perubahan data, administrasi.

        Ketiganya dipisah karena pertanyaannya berbeda. Log keamanan menjawab
        "siapa mengakses aplikasi ini dan kapan", log data menjawab "siapa
        mengubah angka ini", dan log administrasi menjawab "siapa mengubah
        akun atau perusahaan". Mencampur ketiganya membuat catatan penting
        tenggelam di antara aktivitas yang tidak sedang dicari.
        """
        self.tabel_audit = {}
        self.lbl_audit = {}
        self.inp_cari_audit = {}

        for kategori, wadah, kolom, petunjuk in (
                (db.KATEGORI_KEAMANAN, self.tab_keamanan,
                 [("Waktu", 165), ("Pengguna", 150), ("Kejadian", 190),
                  ("Dari Komputer", 165), ("Keterangan", -1)],
                 "Cari pengguna atau kejadian…"),
                (db.KATEGORI_DATA, self.tab_data,
                 [("Waktu", 165), ("Pengguna", 150), ("Aksi", 180),
                  ("Objek", 150), ("Keterangan", -1)],
                 "Cari pengguna, aksi, atau objek…"),
                (db.KATEGORI_ADMIN, self.tab_admin,
                 [("Waktu", 165), ("Pengguna", 150), ("Aksi", 180),
                  ("Objek", 150), ("Keterangan", -1)],
                 "Cari pengguna atau aksi…")):
            lay = QVBoxLayout(wadah)
            lay.setContentsMargins(0, 12, 0, 0)
            lay.setSpacing(12)

            lay.addWidget(w.label(self._keterangan_kategori(kategori),
                                  objek="Muted", wrap=True))

            baris = QHBoxLayout()
            baris.setSpacing(10)
            cari = QLineEdit()
            cari.setPlaceholderText(petunjuk)
            cari.setMinimumWidth(300)
            cari.textChanged.connect(self.muat)
            baris.addWidget(cari)
            baris.addStretch()
            lbl = QLabel("")
            lbl.setObjectName("Muted")
            baris.addWidget(lbl)
            lay.addLayout(baris)

            tabel = w.Tabel(kolom)
            lay.addWidget(tabel, 1)

            self.inp_cari_audit[kategori] = cari
            self.lbl_audit[kategori] = lbl
            self.tabel_audit[kategori] = tabel

    @staticmethod
    def _keterangan_kategori(kategori: str) -> str:
        if kategori == db.KATEGORI_KEAMANAN:
            return ("Catatan percobaan masuk dan keluar aplikasi, termasuk "
                    "percobaan yang gagal. Berguna untuk memeriksa apakah ada "
                    "yang mencoba mengakses data tanpa izin.")
        if kategori == db.KATEGORI_ADMIN:
            return ("Catatan pengelolaan akun pengguna dan data perusahaan, "
                    "mis. pembuatan pengguna, penggantian password, dan "
                    "perubahan identitas perusahaan.")
        return ("Catatan pembuatan, perubahan, dan penghapusan data pembukuan. "
                "Berguna untuk menelusuri asal sebuah angka bila ada selisih.")

    def _bangun_riwayat(self):
        lay = QVBoxLayout(self.tab_riwayat)
        lay.setContentsMargins(0, 12, 0, 0)
        lay.setSpacing(12)

        baris = QHBoxLayout()
        baris.setSpacing(10)
        baris.addWidget(w.label("Tabel:", objek="FormLabel"))
        self.cmb_tabel = QComboBox()
        self.cmb_tabel.addItem("Semua Tabel", "")
        for t in ["invoices", "bills", "sales_orders", "purchase_orders",
                  "partners", "products", "expenses", "fixed_assets",
                  "journal_entries", "users"]:
            self.cmb_tabel.addItem(t, t)
        self.cmb_tabel.currentIndexChanged.connect(self.muat)
        baris.addWidget(self.cmb_tabel)

        self.inp_cari_riwayat = QLineEdit()
        self.inp_cari_riwayat.setPlaceholderText("Cari keterangan perubahan…")
        self.inp_cari_riwayat.setMinimumWidth(260)
        self.inp_cari_riwayat.textChanged.connect(self.muat)
        baris.addWidget(self.inp_cari_riwayat)
        baris.addStretch()
        self.lbl_riwayat = QLabel("")
        self.lbl_riwayat.setObjectName("Muted")
        baris.addWidget(self.lbl_riwayat)
        lay.addLayout(baris)

        self.tabel_riwayat = w.Tabel([
            ("Waktu", 165), ("Tabel", 145), ("ID", 75), ("Aksi", 115),
            ("Perubahan", -1), ("Oleh", 145),
        ])
        lay.addWidget(self.tabel_riwayat, 1)

    def muat(self):
        if not self.ctx.company_id:
            return
        if self.tabs.currentIndex() == 3:
            self._muat_riwayat()
        else:
            self._muat_audit()

    def _muat_audit(self):
        """
        Isi tabel jejak audit sesuai tab yang sedang dibuka.

        Setiap tab memuat kategorinya sendiri, sehingga log keamanan tidak
        tercampur dengan perubahan data.
        """
        kategori = (db.KATEGORI_KEAMANAN, db.KATEGORI_DATA,
                    db.KATEGORI_ADMIN)[self.tabs.currentIndex()]
        data = sec.recent_audit(500, kategori)
        cari = self.inp_cari_audit[kategori].text().strip().lower()
        keamanan = kategori == db.KATEGORI_KEAMANAN

        baris, warna = [], {}
        for a in data:
            teks = f"{a['username'] or ''} {a['aksi'] or ''} " \
                   f"{a['objek'] or ''} {a['keterangan'] or ''}".lower()
            if cari and cari not in teks:
                continue
            idx = len(baris)
            isi = [
                (a["ts"] or "")[:19].replace("T", " "),
                a["username"] or "",
                istilah.label("action", a["aksi"]),
            ]
            if keamanan:
                isi.append(a["sumber"] or "")
            else:
                isi.append(istilah.label("entity", a["objek"]))
            isi.append(a["keterangan"] or "")
            baris.append(isi)

            # Warna penanda: percobaan masuk yang gagal dan penghapusan data
            # perlu langsung terlihat, sedangkan pencatatan biasa tidak
            # diwarnai agar tidak semua baris tampak sama pentingnya.
            if a["aksi"] in ("login.fail", "login.locked"):
                warna[idx] = C.DANGER
            elif a["aksi"] == "logout":
                warna[idx] = C.TEXT_MUTED
            elif a["aksi"].endswith((".delete", ".hapus", ".void")):
                warna[idx] = C.DANGER
            elif a["aksi"].endswith((".create", ".posting")):
                warna[idx] = C.SUCCESS

        self.tabel_audit[kategori].isi(baris, warna_baris=warna)
        jumlah = sec.hitung_per_kategori()
        self.lbl_audit[kategori].setText(
            f"{len(baris)} catatan ditampilkan · "
            f"total {jumlah.get(kategori, 0)}")

    def _muat_riwayat(self):
        data = O.riwayat_perubahan(self.ctx.company_id,
                                   self.cmb_tabel.currentData(), limit=500)
        cari = self.inp_cari_riwayat.text().strip().lower()
        baris, warna = [], {}
        for i, r in enumerate(data):
            if cari and cari not in (r["perubahan"] or "").lower():
                continue
            idx = len(baris)
            baris.append([
                (r["ts"] or "")[:19].replace("T", " "), r["tabel"],
                str(r["record_id"]), r["aksi"] or "",
                r["perubahan"] or "", r["oleh"] or "",
            ])
            warna[idx] = {"hapus": C.DANGER, "restore": C.SUCCESS,
                          "ubah": C.WARNING}.get(r["aksi"], C.TEXT)
        self.tabel_riwayat.isi(baris, warna_baris=warna)
        self.lbl_riwayat.setText(f"{len(baris)} perubahan tercatat")

    def _ekspor(self):
        """Ekspor jejak audit ke berkas CSV, lengkap dengan kategorinya."""
        kategori = (db.KATEGORI_KEAMANAN, db.KATEGORI_DATA,
                    db.KATEGORI_ADMIN)[min(self.tabs.currentIndex(), 2)]
        path, _ = QFileDialog.getSaveFileName(
            self, "Simpan Log Audit",
            str(config.EXPORT_DIR / f"log_{kategori}.csv"),
            "Berkas CSV (*.csv)")
        if not path:
            return
        try:
            import csv
            data = sec.recent_audit(2000, kategori)
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                wr = csv.writer(f, delimiter=";")
                wr.writerow(["waktu", "kategori", "pengguna", "aksi", "objek",
                             "keterangan", "sumber"])
                for a in data:
                    wr.writerow([a["ts"], a["kategori"], a["username"],
                                 a["aksi"], a["objek"], a["keterangan"],
                                 a["sumber"]])
            QMessageBox.information(
                self, "Ekspor selesai",
                f"Log {kategori} ({len(data)} catatan) disimpan di:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Gagal mengekspor", str(e))


# ==========================================================================
# KERANJANG SAMPAH
# ==========================================================================
class RecycleBinPage(QWidget):
    pindah_halaman = Signal(str)

    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx

        luar = QVBoxLayout(self)
        luar.setContentsMargins(0, 0, 0, 0)
        luar.setSpacing(0)

        self.header = w.PageHeader(
            "Keranjang Sampah",
            "Data yang dihapus dapat dipulihkan. Pemulihan mengembalikan data "
            "beserta statusnya.")

        b = w.tombol("Pulihkan", gaya="success", ikon="segarkan")
        b.clicked.connect(self._pulihkan)
        self.header.tambah_aksi(b)

        b2 = w.tombol("Bersihkan Lama", gaya="danger", ikon="hapus")
        b2.clicked.connect(self._bersihkan)
        self.header.tambah_aksi(b2)

        kepala = QWidget()
        theme.latar(kepala, f"background: {C.SURFACE}; "
                             f"border-bottom: 1px solid {C.BORDER};")
        kl = QVBoxLayout(kepala)
        kl.setContentsMargins(26, 20, 26, 18)
        kl.addWidget(self.header)
        luar.addWidget(kepala)

        isi = QWidget()
        self.lay = QVBoxLayout(isi)
        self.lay.setContentsMargins(24, 20, 24, 22)
        self.lay.setSpacing(13)
        luar.addWidget(isi, 1)

        if ctx.beginner:
            self.lay.addWidget(w.HelpPanel(
                "Tentang keranjang sampah",
                "Saat Anda menghapus data (invoice, bill, mitra, produk), data "
                "tidak langsung hilang - data dipindahkan ke sini.\n\n"
                "Anda dapat memulihkannya kapan saja. Data yang sudah dipulihkan "
                "akan kembali seperti semula, termasuk nomor dan statusnya.\n\n"
                "Gunakan 'Bersihkan Lama' untuk menghapus permanen data yang sudah "
                "lebih dari 90 hari.",
                "Pasal 28 UU KUP - pembukuan harus dapat ditelusuri; penghapusan "
                "data harus terkendali."))

        baris = QHBoxLayout()
        baris.setSpacing(10)
        baris.addWidget(w.label("Filter Tabel:", objek="FormLabel"))
        self.cmb_tabel = QComboBox()
        self.cmb_tabel.addItem("Semua", "")
        self.cmb_tabel.currentIndexChanged.connect(self.muat)
        baris.addWidget(self.cmb_tabel)

        self.chk_tampil_dipulihkan = QCheckBox("Tampilkan yang sudah dipulihkan")
        self.chk_tampil_dipulihkan.stateChanged.connect(self.muat)
        baris.addWidget(self.chk_tampil_dipulihkan)
        baris.addStretch()
        self.lbl_info = QLabel("")
        self.lbl_info.setObjectName("Muted")
        baris.addWidget(self.lbl_info)
        self.lay.addLayout(baris)

        self.tabel = w.Tabel([
            ("Waktu Dihapus", 165), ("Tabel", 145), ("ID", 75),
            ("Judul", -1), ("Dihapus Oleh", 155), ("Status", 125),
        ])
        self.lay.addWidget(self.tabel, 1)

        baris2 = QHBoxLayout()
        b1 = w.tombol("Lihat Isi Data", ikon="")
        b1.clicked.connect(self._lihat)
        baris2.addWidget(b1)
        b2 = w.tombol("Pulihkan", gaya="success", ikon="segarkan")
        b2.clicked.connect(self._pulihkan)
        baris2.addWidget(b2)
        baris2.addStretch()
        self.lay.addLayout(baris2)

    def muat(self):
        if not self.ctx.company_id:
            return

        tabel_sekarang = self.cmb_tabel.currentData()
        if self.cmb_tabel.count() <= 1:
            for t in M.db.q("""SELECT DISTINCT tabel FROM recycle_bin
                               WHERE company_id=? ORDER BY tabel""",
                            (self.ctx.company_id,)):
                self.cmb_tabel.addItem(t["tabel"], t["tabel"])

        semua = O.daftar_recycle_bin(self.ctx.company_id, tabel_sekarang or "")
        if self.chk_tampil_dipulihkan.isChecked():
            if tabel_sekarang:
                data = M.db.q("""SELECT * FROM recycle_bin WHERE company_id=?
                                AND tabel=? ORDER BY ts DESC""",
                              (self.ctx.company_id, tabel_sekarang))
            else:
                data = M.db.q("""SELECT * FROM recycle_bin WHERE company_id=?
                                ORDER BY ts DESC""", (self.ctx.company_id,))
        else:
            data = semua

        baris, warna = [], {}
        for i, r in enumerate(data):
            idx = len(baris)
            baris.append([
                (r["ts"] or "")[:19].replace("T", " "), r["tabel"],
                str(r["record_id"]), r["judul"] or "",
                r["dihapus_oleh"] or "",
                "Dipulihkan" if r["dipulihkan"] else "Menunggu",
            ])
            warna[idx] = C.TEXT_FAINT if r["dipulihkan"] else C.DANGER
        self.tabel.isi(baris, warna_baris=warna)
        aktif = len([r for r in data if not r["dipulihkan"]])
        self.lbl_info.setText(f"{aktif} data menunggu dipulihkan")

    def _data(self):
        tabel_sekarang = self.cmb_tabel.currentData()
        if self.chk_tampil_dipulihkan.isChecked():
            if tabel_sekarang:
                return M.db.q("""SELECT * FROM recycle_bin WHERE company_id=?
                                 AND tabel=? ORDER BY ts DESC""",
                              (self.ctx.company_id, tabel_sekarang))
            return M.db.q("""SELECT * FROM recycle_bin WHERE company_id=?
                             ORDER BY ts DESC""", (self.ctx.company_id,))
        return O.daftar_recycle_bin(self.ctx.company_id, tabel_sekarang or "")

    def _terpilih(self):
        r = self.tabel.baris_terpilih()
        if r is None:
            return None
        data = self._data()
        return data[r] if r < len(data) else None

    def _lihat(self):
        r = self._terpilih()
        if r is None:
            QMessageBox.information(self, "Belum dipilih", "Pilih satu data.")
            return
        import json
        dlg = QDialog(self)
        dlg.setWindowTitle(f"Isi Data - {r['tabel']} #{r['record_id']}")
        dlg.setMinimumSize(660, 540)
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(22, 20, 22, 20)
        lay.setSpacing(12)

        j = QLabel(f"{r['judul'] or '-'}")
        j.setObjectName("SectionTitle")
        lay.addWidget(j)

        teks = QTextEdit()
        teks.setReadOnly(True)
        teks.setStyleSheet(f"font-family: {theme.FONT_ANGKA}; "
                           f"font-size: {theme.FS_SMALL}px;")
        try:
            data = json.loads(r["data_json"])
            baris_teks = []
            for k, v in data.items():
                baris_teks.append(f"{k:28s} : {v}")
            teks.setPlainText("\n".join(baris_teks))
        except Exception:
            teks.setPlainText(r["data_json"] or "")
        lay.addWidget(teks, 1)

        bt = w.tombol("Tutup", gaya="primary")
        bt.clicked.connect(dlg.accept)
        bl = QHBoxLayout()
        bl.addStretch()
        bl.addWidget(bt)
        lay.addLayout(bl)
        dlg.exec()

    def _pulihkan(self):
        r = self._terpilih()
        if r is None:
            QMessageBox.information(self, "Belum dipilih", "Pilih satu data.")
            return
        if r["dipulihkan"]:
            QMessageBox.information(self, "Sudah dipulihkan",
                                    "Data ini sudah dipulihkan sebelumnya.")
            return
        if QMessageBox.question(
                self, "Konfirmasi Pemulihan",
                f"Pulihkan '{r['judul']}' ({r['tabel']})?",
                QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return
        try:
            hasil = O.pulihkan_dari_recycle(r["id"], self.ctx.username)
            QMessageBox.information(self, "Berhasil", hasil["pesan"])
            self.muat()
        except Exception as e:
            QMessageBox.critical(self, "Gagal memulihkan", str(e))

    def _bersihkan(self):
        if QMessageBox.question(
                self, "Konfirmasi Bersihkan",
                "Hapus permanen semua data di keranjang sampah yang lebih tua "
                "dari 90 hari?\n\nTindakan ini tidak dapat dibatalkan.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No) != QMessageBox.Yes:
            return
        try:
            jumlah = O.bersihkan_recycle_bin(self.ctx.company_id, 90)
            QMessageBox.information(self, "Selesai",
                                    f"{jumlah} catatan dihapus permanen.")
            self.muat()
        except Exception as e:
            QMessageBox.critical(self, "Gagal", str(e))


# ==========================================================================
# IMPOR MASSAL
# ==========================================================================
class ImporMassalPage(QWidget):
    pindah_halaman = Signal(str)

    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx

        luar = QVBoxLayout(self)
        luar.setContentsMargins(0, 0, 0, 0)
        luar.setSpacing(0)

        self.header = w.PageHeader(
            "Impor Data Massal",
            "Unggah data pelanggan, pemasok, produk, dan jurnal dari berkas CSV.")

        kepala = QWidget()
        theme.latar(kepala, f"background: {C.SURFACE}; "
                             f"border-bottom: 1px solid {C.BORDER};")
        kl = QVBoxLayout(kepala)
        kl.setContentsMargins(26, 20, 26, 18)
        kl.addWidget(self.header)
        luar.addWidget(kepala)

        isi = QWidget()
        self.lay = QVBoxLayout(isi)
        self.lay.setContentsMargins(24, 20, 24, 22)
        self.lay.setSpacing(13)
        # Isi dibungkus area gulir agar penjelasan panjang tidak terpotong
        # pada jendela pendek.
        luar.addWidget(w.scroll(isi), 1)

        self.lay.addWidget(w.HelpPanel(
            "Cara mengimpor data massal",
            "1. Pilih jenis data yang akan diimpor.\n"
            "2. Unduh template CSV, lalu isi dengan data Anda.\n"
            "3. Unggah berkas, atau tempelkan isinya langsung.\n"
            "4. Periksa pratinjau sebelum menekan Impor.\n\n"
            "Baris yang duplikat (nama/kode sama) otomatis dilewati sehingga "
            "tidak terjadi data ganda. Pemisah kolom yang didukung: titik koma "
            "(;), koma (,), atau tab.",
            "Pasal 28 UU KUP - data pembukuan harus lengkap dan dapat "
            "dipertanggungjawabkan."))

        baris = QHBoxLayout()
        baris.setSpacing(11)
        baris.addWidget(w.label("Jenis Data", objek="FormLabel"))
        self.cmb_jenis = QComboBox()
        self.cmb_jenis.addItem("Pelanggan (Customer)", "customer")
        self.cmb_jenis.addItem("Pemasok (Vendor)", "vendor")
        self.cmb_jenis.addItem("Produk & Jasa", "produk")
        self.cmb_jenis.addItem("Jurnal Umum", "jurnal")
        self.cmb_jenis.currentIndexChanged.connect(self._ganti_jenis)
        baris.addWidget(self.cmb_jenis)

        b1 = w.tombol("Unduh Template", ikon="ekspor")
        b1.clicked.connect(self._unduh_template)
        baris.addWidget(b1)

        b2 = w.tombol("Pilih Berkas CSV", gaya="primary", ikon="dokumen")
        b2.clicked.connect(self._pilih_berkas)
        baris.addWidget(b2)
        baris.addStretch()
        lay = baris
        self.lay.addLayout(lay)

        self.lbl_panduan = QLabel("")
        self.lbl_panduan.setWordWrap(True)
        theme.latar(self.lbl_panduan, f"background: {C.NEUTRAL_BG}; border-radius: 8px; padding: 11px 13px; "
            f"font-family: {theme.FONT_ANGKA}; font-size: {theme.FS_SMALL}px;")
        self.lay.addWidget(self.lbl_panduan)

        self.teks = QTextEdit()
        self.teks.setPlaceholderText(
            "Tempelkan isi CSV di sini, atau gunakan tombol 'Pilih Berkas CSV'.")
        self.teks.setMinimumHeight(240)
        self.teks.setStyleSheet(f"font-family: {theme.FONT_ANGKA}; "
                                f"font-size: {theme.FS_SMALL}px;")
        self.lay.addWidget(self.teks, 1)

        self.lbl_hasil = QLabel("")
        self.lbl_hasil.setWordWrap(True)
        self.lbl_hasil.setTextFormat(Qt.RichText)
        self.lay.addWidget(self.lbl_hasil)

        aksi = QHBoxLayout()
        aksi.addStretch()
        b3 = w.tombol("Kosongkan", ikon="")
        b3.clicked.connect(lambda: (self.teks.clear(), self.lbl_hasil.setText("")))
        aksi.addWidget(b3)
        b4 = w.tombol("Impor Sekarang", gaya="primary", ikon="simpan")
        b4.clicked.connect(self._impor)
        aksi.addWidget(b4)
        self.lay.addLayout(aksi)

        self._ganti_jenis()

    def _ganti_jenis(self):
        jenis = self.cmb_jenis.currentData()
        contoh = O.template_csv(jenis)
        self.lbl_panduan.setText(
            "<b>Format kolom yang diharapkan:</b><br>"
            + (contoh.split("\n")[0].replace(";", " | ") if contoh else ""))

    def _unduh_template(self):
        jenis = self.cmb_jenis.currentData()
        path, _ = QFileDialog.getSaveFileName(
            self, "Simpan Template CSV",
            str(config.EXPORT_DIR / f"template_{jenis}.csv"),
            "Berkas CSV (*.csv)")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8-sig") as f:
                f.write(O.template_csv(jenis))
            QMessageBox.information(self, "Template disimpan",
                                    f"Template disimpan di:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Gagal menyimpan", str(e))

    def _pilih_berkas(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Pilih Berkas CSV", str(config.EXPORT_DIR),
            "Berkas CSV/Teks (*.csv *.txt);;Semua Berkas (*)")
        if not path:
            return
        try:
            with open(path, encoding="utf-8-sig", errors="replace") as f:
                self.teks.setPlainText(f.read())
            self.lbl_hasil.setText(
                f"<span style='color:{C.INFO}'>Berkas dimuat: "
                f"{os.path.basename(path)}</span>")
        except Exception as e:
            QMessageBox.critical(self, "Gagal membaca berkas", str(e))

    def _impor(self):
        jenis = self.cmb_jenis.currentData()
        isi = self.teks.toPlainText().strip()
        if not isi:
            QMessageBox.warning(self, "Belum ada data",
                                "Pilih berkas CSV atau tempelkan isinya.")
            return
        try:
            if jenis in ("customer", "vendor"):
                hasil = O.impor_mitra_massal(self.ctx.company_id, isi, jenis,
                                             self.ctx.user_id)
            elif jenis == "produk":
                hasil = O.impor_produk_massal(self.ctx.company_id, isi,
                                              self.ctx.user_id)
            else:
                hasil = O.impor_jurnal_massal(self.ctx.company_id, isi,
                                              self.ctx.user_id)

            pesan = (f"<b>Impor selesai</b><br>"
                     f"Berhasil: <b style='color:{C.SUCCESS}'>{hasil['berhasil']}"
                     f"</b> baris<br>"
                     f"Dilewati (duplikat/invalid): "
                     f"<b style='color:{C.WARNING}'>{hasil.get('dilewati', 0)}</b> "
                     f"baris<br>"
                     f"Total diperiksa: {hasil.get('total', 0)}")
            self.lbl_hasil.setText(pesan)
            if hasil.get("galat"):
                galat = hasil["galat"][:5]
                self.lbl_hasil.setText(
                    pesan + "<br><br><b>Contoh masalah:</b><br>" +
                    "<br>".join(f"• {g}" for g in galat))
            theme.latar(self.lbl_hasil, f"background: {C.SUCCESS_BG}; border: 1px solid #B8E6D5; "
                f"border-radius: 8px; padding: 11px 13px; "
                f"font-size: {theme.FS_SMALL}px;")
            self.muat_terkait()
        except Exception as e:
            QMessageBox.critical(self, "Gagal mengimpor", str(e))

    def muat_terkait(self):
        pass

    def muat(self):
        pass


# ==========================================================================
# PENCARIAN GLOBAL
# ==========================================================================
class PencarianPage(QWidget):
    pindah_halaman = Signal(str)

    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.hasil_terakhir: list = []

        luar = QVBoxLayout(self)
        luar.setContentsMargins(0, 0, 0, 0)
        luar.setSpacing(0)

        self.header = w.PageHeader(
            "Pencarian Global",
            "Cari di seluruh data: invoice, bill, pelanggan, produk, jurnal, "
            "aset, dan lainnya.")

        kepala = QWidget()
        theme.latar(kepala, f"background: {C.SURFACE}; "
                             f"border-bottom: 1px solid {C.BORDER};")
        kl = QVBoxLayout(kepala)
        kl.setContentsMargins(26, 20, 26, 18)
        kl.addWidget(self.header)
        luar.addWidget(kepala)

        isi = QWidget()
        self.lay = QVBoxLayout(isi)
        self.lay.setContentsMargins(24, 20, 24, 22)
        self.lay.setSpacing(13)
        luar.addWidget(isi, 1)

        baris = QHBoxLayout()
        baris.setSpacing(10)
        self.inp_cari = QLineEdit()
        self.inp_cari.setPlaceholderText(
            "Ketik untuk mencari: nomor invoice, nama pelanggan, kode produk, akun")
        self.inp_cari.setMinimumHeight(38)
        self.inp_cari.setClearButtonEnabled(True)
        self.inp_cari.returnPressed.connect(self._cari)

        # Pencarian berjalan sendiri saat pengguna mengetik. Jeda 300 ms
        # dipakai agar tidak menjalankan kueri pada setiap ketukan tombol.
        self._tunda = QTimer(self)
        self._tunda.setSingleShot(True)
        self._tunda.setInterval(300)
        self._tunda.timeout.connect(lambda: self._cari(diam=True))
        self.inp_cari.textChanged.connect(self._saat_mengetik)

        baris.addWidget(self.inp_cari, 1)

        b = w.tombol("Cari", gaya="primary", ikon="analisis")
        b.clicked.connect(self._cari)
        baris.addWidget(b)
        self.lay.addLayout(baris)

        self.lbl_info = QLabel("")
        self.lbl_info.setObjectName("Muted")
        self.lay.addWidget(self.lbl_info)

        self.splitter = QSplitter(Qt.Horizontal)
        self.hasil_list = QListWidget()
        self.hasil_list.setStyleSheet(
            f"QListWidget {{ background: {C.SURFACE}; border: 1px solid {C.BORDER}; "
            f"border-radius: 8px; font-size: {theme.FS_BODY}px; }}"
            f"QListWidget::item {{ padding: 9px 11px; "
            f"border-bottom: 1px solid {C.BORDER}; }}"
            f"QListWidget::item:selected {{ background: {C.PRIMARY_SOFT}; "
            f"color: {C.PRIMARY}; }}")
        self.hasil_list.currentRowChanged.connect(self._pilih)
        self.hasil_list.itemDoubleClicked.connect(lambda _: self._buka())
        self.splitter.addWidget(self.hasil_list)

        self.detail = QTextEdit()
        self.detail.setReadOnly(True)
        theme.latar(self.detail, f"background: {C.SURFACE}; border: 1px solid {C.BORDER}; "
            f"border-radius: 8px; padding: 12px; "
            f"font-size: {theme.FS_SMALL}px;")
        self.splitter.addWidget(self.detail)
        self.splitter.setSizes([420, 620])
        self.lay.addWidget(self.splitter, 1)

        aksi = QHBoxLayout()
        aksi.addStretch()
        b2 = w.tombol("Buka Halaman Terkait", gaya="primary", ikon="")
        b2.clicked.connect(self._buka)
        aksi.addWidget(b2)
        self.lay.addLayout(aksi)

    def muat(self):
        pass

    def _saat_mengetik(self, teks: str):
        """Jalankan pencarian setelah pengguna berhenti mengetik sejenak."""
        if len(teks.strip()) < 2:
            # bersihkan hasil lama supaya layar tidak menampilkan sisa
            # pencarian sebelumnya saat kata kunci dihapus
            self.hasil_list.clear()
            self.detail.clear()
            self.hasil_terakhir = []
            self.lbl_info.setText("")
            self._tunda.stop()
            return
        self._tunda.start()

    def _cari(self, diam: bool = False):
        """
        Cari kata kunci.

        `diam` dipakai saat pencarian berjalan otomatis sambil mengetik:
        kata kunci yang masih pendek tidak perlu memunculkan kotak pesan.
        """
        kata = self.inp_cari.text().strip()
        if len(kata) < 2:
            if not diam:
                QMessageBox.information(self, "Kata kunci terlalu pendek",
                                        "Masukkan minimal 2 huruf untuk mencari.")
            return
        try:
            self.hasil_terakhir = O.cari_global(self.ctx.company_id, kata)
        except Exception as e:
            QMessageBox.critical(self, "Pencarian gagal", str(e))
            return

        self.hasil_list.clear()
        self.detail.clear()
        for h in self.hasil_terakhir:
            item = QListWidgetItem(f"[{h['jenis']}]  {h['judul']}\n"
                                   f"      {h['keterangan']}")
            self.hasil_list.addItem(item)

        if not self.hasil_terakhir:
            self.lbl_info.setText(f"Tidak ada hasil untuk '{kata}'.")
            self.detail.setHtml(
                f"<div style='color:{C.TEXT_MUTED}'>Tidak ada hasil untuk "
                f"<b>{kata}</b>.<br><br>Coba kata kunci lain, atau periksa ejaan."
                "</div>")
        else:
            jumlah_jenis: dict[str, int] = {}
            for h in self.hasil_terakhir:
                jumlah_jenis[h["jenis"]] = jumlah_jenis.get(h["jenis"], 0) + 1
            ringkas = " · ".join(f"{k}: {v}" for k, v in jumlah_jenis.items())
            self.lbl_info.setText(f"{len(self.hasil_terakhir)} hasil - {ringkas}")
            self.hasil_list.setCurrentRow(0)

    def _pilih(self, baris: int):
        if baris < 0 or baris >= len(self.hasil_terakhir):
            self.detail.clear()
            return
        h = self.hasil_terakhir[baris]
        self.detail.setHtml(
            f"<h3 style='color:{C.PRIMARY}; margin-bottom:4px;'>{h['judul']}</h3>"
            f"<p style='color:{C.TEXT_MUTED}; margin-top:0;'>"
            f"<b>Jenis:</b> {h['jenis']}<br>"
            f"<b>Keterangan:</b> {h['keterangan'] or '-'}<br>"
            f"<b>Halaman:</b> {h['halaman']}<br>"
            f"<b>ID:</b> {h['id']}</p>"
            f"<hr>"
            f"<p style='color:{C.TEXT_MUTED}'>Klik 'Buka Halaman Terkait' untuk "
            f"membuka data ini di halamannya.</p>")

    def _buka(self):
        baris = self.hasil_list.currentRow()
        if baris < 0 or baris >= len(self.hasil_terakhir):
            return
        h = self.hasil_terakhir[baris]
        self.pindah_halaman.emit(h["halaman"])
