"""
AkunTuntas - Halaman Pengaturan, Checklist Kepatuhan & Bantuan
==============================================================
  • Pengaturan  preferensi, pengguna, backup, audit log
  • Checklist daftar periksa kepatuhan bulanan/tahunan
  • Bantuan     - panduan lengkap & referensi aturan
"""
from __future__ import annotations

import os
from datetime import datetime

from PySide6.QtCore import Qt, Signal, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton,
    QDialog, QMessageBox, QInputDialog, QGridLayout, QLineEdit, QCheckBox, QTabWidget,
    QFileDialog, QListWidget, QStackedWidget, QTextEdit, QSpinBox,
)

from ... import config, coa, db, services
from ...core import security as sec
from ... import istilah
from .. import theme
from ..theme import C
from .. import widgets as w

from pathlib import Path


# ==========================================================================
# SALINAN REGULASI RESMI
# ==========================================================================
# Judul ramah pengguna untuk setiap berkas teks regulasi yang disertakan.
JUDUL_REGULASI = {
    "UU_HPP_7_2021": "UU No. 7/2021 - Harmonisasi Peraturan Perpajakan (HPP)",
    "UU_1_2026": "UU No. 1/2026",
    "PP20_2026": "PP No. 20/2026",
    "PP55_2022": "PP No. 55/2022 - Penyesuaian PPh Final UMKM",
    "PP9_2021": "PP No. 9/2021 - Perlakuan Pajak UMKM",
    "PP9_2022": "PP No. 9/2022 - PPh Final Jasa Konstruksi",
    "PP34_2016": "PP No. 34/2016 - PPh Final Pengalihan Tanah/Bangunan",
    "PP34_2017": "PP No. 34/2017 - PPh Final Sewa Tanah/Bangunan",
    "PP58_2023": "PP No. 58/2023 - Tarif Pemotongan PPh 21",
    "PMK168_2023": "PMK 168/2023 - Petunjuk PPh 21 (Tarif Efektif / TER)",
    "PMK168_2023_full": "PMK 168/2023 - Salinan Lengkap",
    "PMK105_2025": "PMK 105/2025 - PPh 21 Ditanggung Pemerintah 2026",
    "PMK114_2025": "PMK 114/2025 - Zakat, Bantuan, dan Hibahan",
    "PMK72_2025": "PMK 72/2025 - Perubahan PMK 10/2025",
    "PMK72_2025_dtp": "PMK 72/2025 - Ketentuan Tambahan",
    "PP68_2009": "PP No. 68/2009 - PPh Final UMKM (historis)",
    "PP19_2009": "PP No. 19/2009 - PPh Final UMKM (historis)",
}


def _daftar_regulasi() -> list:
    """Kumpulkan berkas teks regulasi yang tersedia beserta judulnya."""
    hasil = []
    for folder in (config.ASSET_DIR.parent / "docs" / "pajak2026",
                   Path(__file__).resolve().parents[3] / "docs" / "pajak2026"):
        if not folder.is_dir():
            continue
        for path in sorted(folder.glob("*.txt")):
            judul = JUDUL_REGULASI.get(path.stem)
            if judul is None:
                judul = path.stem.replace("_", " ")
            hasil.append((path.stem, judul, path))
        if hasil:
            break
    return hasil


def _buka_regulasi(berkas: list, baris: int) -> None:
    if 0 <= baris < len(berkas):
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(berkas[baris][2])))


# ==========================================================================
# HALAMAN PENGATURAN
# ==========================================================================
class PengaturanPage(QWidget):
    pindah_halaman = Signal(str)
    mode_berubah = Signal(str)

    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx

        luar = QVBoxLayout(self)
        luar.setContentsMargins(0, 0, 0, 0)
        luar.setSpacing(0)

        self.header = w.PageHeader(
            "Pengaturan",
            "Preferensi tampilan, pengelolaan pengguna, cadangan data, dan jejak audit.")

        kepala = QWidget()
        theme.latar(kepala, f"background: {C.SURFACE}; "
                             f"border-bottom: 1px solid {C.BORDER};")
        kl = QVBoxLayout(kepala)
        kl.setContentsMargins(26, 20, 26, 18)
        kl.addWidget(self.header)
        luar.addWidget(kepala)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        wadah = QWidget()
        wl = QVBoxLayout(wadah)
        wl.setContentsMargins(22, 16, 22, 22)
        wl.addWidget(self.tabs)
        luar.addWidget(wadah, 1)

        self.tab_preferensi = QWidget()
        self.tab_pengguna = QWidget()
        self.tab_backup = QWidget()
        self.tab_audit = QWidget()
        self.tabs.addTab(self.tab_preferensi, "Preferensi")
        self.tabs.addTab(self.tab_pengguna, "Pengguna")
        self.tabs.addTab(self.tab_backup, "Cadangan && Data")
        self.tabs.addTab(self.tab_audit, "Jejak Audit")
        self.tabs.currentChanged.connect(self.muat)

        for t in (self.tab_preferensi, self.tab_pengguna, self.tab_backup,
                  self.tab_audit):
            l = QVBoxLayout(t)
            l.setContentsMargins(0, 12, 0, 0)
            l.setSpacing(13)

    def muat(self):
        idx = self.tabs.currentIndex()
        if idx == 0:
            self._muat_preferensi()
        elif idx == 1:
            self._muat_pengguna()
        elif idx == 2:
            self._muat_backup()
        else:
            self._muat_audit()

    def _bersihkan(self, widget):
        """
        Kosongkan isi tab dan kembalikan tata letak tempat mengisi ulang.

        Area gulir dibuat sekali lalu dipakai terus; hanya isinya yang
        diganti. Membuat area baru setiap kali akan meninggalkan objek
        yang sudah dihapus sehingga pemuatan berikutnya gagal.
        """
        if not hasattr(widget, "_area_gulir"):
            wadah = QWidget()
            isi = QVBoxLayout(wadah)
            isi.setContentsMargins(0, 0, 0, 0)
            isi.setSpacing(14)
            area = w.scroll(wadah)
            lama = widget.layout()
            lama.addWidget(area)
            widget._area_gulir = area
            widget._wadah_gulir = wadah
            widget._isi_gulir = isi
            return isi

        isi = widget._isi_gulir
        while isi.count():
            it = isi.takeAt(0)
            wdg = it.widget()
            if wdg is not None:
                wdg.setParent(None)
                wdg.deleteLater()
            elif it.layout() is not None:
                self._bersihkan_layout(it.layout())
        return isi

    def _bersihkan_layout(self, lay):
        while lay.count():
            it = lay.takeAt(0)
            wdg = it.widget()
            if wdg is not None:
                wdg.setParent(None)
                wdg.deleteLater()
            elif it.layout():
                self._bersihkan_layout(it.layout())

    # ------------------------------------------------------------------
    # PREFERENSI
    # ------------------------------------------------------------------
    def _muat_preferensi(self):
        lay = self._bersihkan(self.tab_preferensi)

        # mode aplikasi
        kartu = w.Card()
        l = kartu.body()
        j = QLabel("Mode Penggunaan Aplikasi")
        j.setObjectName("SectionTitle")
        l.addWidget(j)

        l.addWidget(w.label(
            "Mode Pemula menampilkan panel penjelasan konsep akuntansi dan pajak di "
            "setiap halaman. Mode Ahli menyembunyikannya agar antarmuka lebih ringkas. "
            "Seluruh fitur tetap tersedia pada kedua mode.",
            objek="Muted", wrap=True))

        baris = QHBoxLayout()
        baris.setSpacing(11)
        self.rb_pemula = QPushButton("  Mode Pemula")
        self.rb_pemula.setCheckable(True)
        self.rb_pemula.setChecked(self.ctx.beginner)
        self.rb_pemula.setMinimumHeight(42)
        self.rb_pemula.clicked.connect(lambda: self._ganti_mode("beginner"))
        baris.addWidget(self.rb_pemula)

        self.rb_ahli = QPushButton("  Mode Ahli")
        self.rb_ahli.setCheckable(True)
        self.rb_ahli.setChecked(not self.ctx.beginner)
        self.rb_ahli.setMinimumHeight(42)
        self.rb_ahli.clicked.connect(lambda: self._ganti_mode("expert"))
        baris.addWidget(self.rb_ahli)
        baris.addStretch()
        l.addLayout(baris)
        l.addWidget(w.label(
            "Perubahan mode berlaku setelah halaman dimuat ulang. "
            "Buka halaman lain lalu kembali ke sini.",
            objek="Faint", wrap=True))
        lay.addWidget(kartu)

        # tampilan menu samping
        kartu_menu = w.Card()
        lm = kartu_menu.body()
        jm = QLabel("Tampilan Menu Samping")
        jm.setObjectName("SectionTitle")
        lm.addWidget(jm)
        lm.addWidget(w.label(
            "Kelompok menu dapat dibuka dan ditutup agar daftar tidak terlalu "
            "panjang. Pilihan Anda diingat otomatis. Tekan tombol di bawah "
            "untuk membuka seluruh kelompok sekaligus.",
            objek="Muted", wrap=True))

        b_baris = QHBoxLayout()
        b_baris.setSpacing(9)
        b_buka = w.tombol("Buka Semua Kelompok", ikon="panah_bawah")
        b_buka.clicked.connect(self._buka_semua_kelompok)
        b_baris.addWidget(b_buka)

        b_tutup = w.tombol("Tutup Semua Kelompok", ikon="panah_kanan")
        b_tutup.clicked.connect(self._tutup_semua_kelompok)
        b_baris.addWidget(b_tutup)
        b_baris.addStretch()
        lm.addLayout(b_baris)
        lay.addWidget(kartu_menu)

        # perusahaan aktif
        kartu2 = w.Card()
        l2 = kartu2.body()
        j2 = QLabel("Perusahaan Aktif")
        j2.setObjectName("SectionTitle")
        l2.addWidget(j2)

        perusahaan = services.list_companies()
        if perusahaan:
            self.cmb_perusahaan = QComboBox()
            for p in perusahaan:
                self.cmb_perusahaan.addItem(p["nama"], p["id"])
            i = self.cmb_perusahaan.findData(self.ctx.company_id)
            if i >= 0:
                self.cmb_perusahaan.setCurrentIndex(i)
            self.cmb_perusahaan.currentIndexChanged.connect(self._ganti_perusahaan)
            l2.addWidget(self.cmb_perusahaan)

            b_tambah = w.tombol("Tambah Perusahaan Baru", ikon="+")
            b_tambah.clicked.connect(lambda: self.pindah_halaman.emit("perusahaan"))
            l2.addWidget(b_tambah, 0, Qt.AlignLeft)
        else:
            l2.addWidget(w.label("Belum ada perusahaan.", objek="Muted"))
            b = w.tombol("Buat Perusahaan", gaya="primary")
            b.clicked.connect(lambda: self.pindah_halaman.emit("perusahaan"))
            l2.addWidget(b, 0, Qt.AlignLeft)
        lay.addWidget(kartu2)

        # tahun pajak
        kartu3 = w.Card()
        l3 = kartu3.body()
        j3 = QLabel("Tahun Pajak Aktif")
        j3.setObjectName("SectionTitle")
        l3.addWidget(j3)
        self.cmb_tahun = QComboBox()
        tk = datetime.now().year
        for t in range(tk - 3, tk + 2):
            self.cmb_tahun.addItem(str(t), t)
        i = self.cmb_tahun.findData(self.ctx.tahun)
        if i >= 0:
            self.cmb_tahun.setCurrentIndex(i)
        self.cmb_tahun.currentIndexChanged.connect(
            lambda: setattr(self.ctx, "tahun", self.cmb_tahun.currentData()))
        l3.addWidget(self.cmb_tahun)
        lay.addWidget(kartu3)

        # info lokasi data
        kartu4 = w.Card()
        l4 = kartu4.body()
        j4 = QLabel("Lokasi Penyimpanan Data")
        j4.setObjectName("SectionTitle")
        l4.addWidget(j4)
        l4.addWidget(w.label(
            "Seluruh data tersimpan di komputer Anda. Aplikasi tidak mengirim data "
            "ke internet.", objek="Muted", wrap=True))

        for label, nilai in [("Folder data", str(config.DATA_DIR)),
                             ("Basis data", str(config.DB_PATH)),
                             ("Folder cadangan", str(config.BACKUP_DIR)),
                             ("Folder ekspor", str(config.EXPORT_DIR))]:
            baris = QHBoxLayout()
            baris.setSpacing(11)
            lb = QLabel(label)
            lb.setMinimumWidth(130)
            lb.setWordWrap(True)
            lb.setStyleSheet(f"font-size: {theme.FS_SMALL}px; font-weight: 600; "
                             "background: transparent;")
            baris.addWidget(lb)
            v = QLineEdit(nilai)
            v.setReadOnly(True)
            baris.addWidget(v, 1)
            b = w.tombol("Buka", gaya="ghost")
            b.clicked.connect(lambda _, p=nilai: QDesktopServices.openUrl(
                QUrl.fromLocalFile(p)))
            baris.addWidget(b)
            l4.addLayout(baris)
        lay.addWidget(kartu4)
        lay.addStretch()

    def _cari_sidebar(self):
        """Ambil objek sidebar dari jendela utama."""
        jendela = self.window()
        if hasattr(jendela, "sidebar"):
            return jendela.sidebar
        return None

    def _buka_semua_kelompok(self):
        sidebar = self._cari_sidebar()
        if sidebar is None:
            return
        for judul, _ in sidebar._grup.values():
            judul.setChecked(True)
        sidebar.simpan_lipatan()

    def _tutup_semua_kelompok(self):
        sidebar = self._cari_sidebar()
        if sidebar is None:
            return
        for judul, _ in sidebar._grup.values():
            judul.setChecked(False)
        sidebar.simpan_lipatan()

    def _ganti_mode(self, mode: str):
        try:
            sec.update_user_mode(self.ctx.user_id, mode)
            self.ctx.beginner = (mode == "beginner")
            self.rb_pemula.setChecked(mode == "beginner")
            self.rb_ahli.setChecked(mode == "expert")
            self.mode_berubah.emit(mode)
            QMessageBox.information(
                self, "Mode diubah",
                f"Mode aplikasi diubah ke {'Pemula' if mode == 'beginner' else 'Ahli'}.\n\n"
                "Buka halaman lain lalu kembali agar tampilan menyesuaikan.")
        except Exception as e:
            QMessageBox.critical(self, "Gagal mengubah mode", str(e))

    def _ganti_perusahaan(self):
        cid = self.cmb_perusahaan.currentData()
        self.ctx.company_id = cid
        self.ctx.company = services.get_company(cid)
        QMessageBox.information(self, "Perusahaan diubah",
                                f"Sekarang menampilkan data: {self.cmb_perusahaan.currentText()}")

    # ------------------------------------------------------------------
    # PENGGUNA
    # ------------------------------------------------------------------
    def _muat_pengguna(self):
        lay = self._bersihkan(self.tab_pengguna)

        lay.addWidget(w.InfoBanner(
            "Setiap pengguna memiliki nama pengguna dan password sendiri. Hak akses "
            "diatur per peran. Seluruh aktivitas penting dicatat pada jejak audit "
            "sebagai bukti kepatuhan (Pasal 28 UU KUP).",
            "info", "Tentang pengelolaan pengguna"))

        baris = QHBoxLayout()
        baris.setSpacing(9)
        b = w.tombol("Tambah Pengguna", gaya="primary", ikon="+")
        b.clicked.connect(self._tambah_pengguna)
        baris.addWidget(b)
        b2 = w.tombol("Reset Password", ikon="pengguna")
        b2.clicked.connect(self._reset_password)
        baris.addWidget(b2)
        b3 = w.tombol("Aktifkan / Nonaktifkan", ikon="⊘")
        b3.clicked.connect(self._toggle_pengguna)
        baris.addWidget(b3)
        b4 = w.tombol("Ganti Password Saya", ikon="periode")
        b4.clicked.connect(self._ganti_password_saya)
        baris.addWidget(b4)
        baris.addStretch()
        lay.addLayout(baris)

        users = sec.list_users()
        t = w.Tabel([
            ("ID", 55), ("Nama Pengguna", 160), ("Nama Lengkap", 200),
            ("Peran", 110), ("Mode", 110), ("Status", 100),
            ("Login Terakhir", 190), ("Dibuat", 175),
        ])
        baris_t, warna = [], {}
        for i, u in enumerate(users):
            idx = len(baris_t)
            baris_t.append([
                u["id"], u["username"], u["full_name"] or "",
                {"owner": "Pemilik", "admin": "Administrator",
                 "staff": "Staf", "viewer": "Hanya Lihat"}.get(u["role"], u["role"]),
                "Pemula" if u["app_mode"] == "beginner" else "Ahli",
                "Aktif" if u["is_active"] else "Nonaktif",
                u["last_login"] or "Belum pernah",
                u["created_at"][:16] if u["created_at"] else "",
            ])
            if not u["is_active"]:
                warna[idx] = C.TEXT_FAINT
            elif u["must_change_pw"]:
                warna[idx] = C.WARNING
        t.isi(baris_t, warna_baris=warna, align_kanan={0})
        t.setMinimumHeight(280)
        lay.addWidget(t)
        lay.addWidget(w.label(
            "Keterangan peran: Pemilik = akses penuh termasuk kelola pengguna. "
            "Administrator = akses penuh kecuali hapus perusahaan. "
            "Staf = input transaksi. Hanya Lihat = tidak dapat mengubah data.",
            objek="Faint", wrap=True))
        lay.addStretch()

    def _selected_user(self):
        # ambil dari tabel pengguna
        for child in self.tab_pengguna.findChildren(w.Tabel):
            r = child.baris_terpilih()
            if r is not None:
                users = sec.list_users()
                return users[r] if r < len(users) else None
        return None

    def _tambah_pengguna(self):
        d = DialogPengguna(self.ctx, self)
        if d.exec():
            self._muat_pengguna()

    def _reset_password(self):
        u = self._selected_user()
        if u is None:
            QMessageBox.information(self, "Belum dipilih", "Pilih satu pengguna.")
            return
        d = DialogResetPassword(self.ctx, u, self)
        if d.exec():
            self._muat_pengguna()

    def _toggle_pengguna(self):
        u = self._selected_user()
        if u is None:
            QMessageBox.information(self, "Belum dipilih", "Pilih satu pengguna.")
            return
        if u["id"] == self.ctx.user_id:
            QMessageBox.warning(self, "Tidak dapat",
                                "Anda tidak dapat menonaktifkan akun sendiri.")
            return
        try:
            sec.set_user_active(u["id"], not bool(u["is_active"]),
                                self.ctx.user_id, self.ctx.username)
            self._muat_pengguna()
        except Exception as e:
            QMessageBox.critical(self, "Gagal", str(e))

    def _ganti_password_saya(self):
        d = DialogGantiPassword(self.ctx, self)
        if d.exec():
            QMessageBox.information(self, "Berhasil", "Password Anda telah diubah.")

    # ------------------------------------------------------------------
    # BACKUP
    # ------------------------------------------------------------------
    def _muat_backup(self):
        lay = self._bersihkan(self.tab_backup)

        lay.addWidget(w.InfoBanner(
            "Cadangkan data sebelum memasang pembaruan aplikasi. Setelah "
            "pembaruan terpasang, buka tab ini lalu pilih berkas cadangan "
            "untuk mengembalikan seluruh data - tanpa perlu memasukkan ulang "
            "apa pun. Simpan cadangan di lokasi lain (flashdisk, drive "
            "eksternal) agar tidak hilang bila komputernya rusak.",
            "info", "Memindahkan data ke versi baru"))

        # ------------------------------------------------- cadangan otomatis
        st = db.setelan_backup_otomatis()
        kartu_auto = w.Card()
        al = kartu_auto.body()
        j_auto = QLabel("Cadangan Otomatis")
        j_auto.setObjectName("SectionTitle")
        al.addWidget(j_auto)

        al.addWidget(w.label(
            "Aplikasi membuat cadangan sendiri saat dibuka, tanpa perlu "
            "diingatkan. Cadangan lama dihapus otomatis agar tidak menumpuk.",
            objek="Muted", wrap=True))

        baris_auto = QHBoxLayout()
        baris_auto.setSpacing(12)

        self.chk_backup_auto = QComboBox()
        self.chk_backup_auto.addItem("Aktifkan cadangan otomatis", True)
        self.chk_backup_auto.addItem("Matikan cadangan otomatis", False)
        self.chk_backup_auto.setCurrentIndex(0 if st["aktif"] else 1)
        baris_auto.addWidget(self.chk_backup_auto)

        baris_auto.addWidget(w.label("Setiap", objek="FormLabel"))
        self.spn_interval = QSpinBox()
        self.spn_interval.setRange(1, 720)
        self.spn_interval.setValue(st["interval_jam"])
        self.spn_interval.setSuffix(" jam")
        baris_auto.addWidget(self.spn_interval)

        baris_auto.addWidget(w.label("Simpan maksimal", objek="FormLabel"))
        self.spn_simpan = QSpinBox()
        self.spn_simpan.setRange(2, 100)
        self.spn_simpan.setValue(st["simpan_maks"])
        self.spn_simpan.setSuffix(" berkas")
        baris_auto.addWidget(self.spn_simpan)

        b_simpan_auto = w.tombol("Simpan Pengaturan", gaya="primary", ikon="simpan")
        b_simpan_auto.clicked.connect(self._simpan_setelan_backup)
        baris_auto.addWidget(b_simpan_auto)

        b_cadang_kini = w.tombol("Cadangkan Sekarang", gaya="biasa", ikon="segarkan")
        b_cadang_kini.clicked.connect(self._buat_backup)
        baris_auto.addWidget(b_cadang_kini)

        baris_auto.addStretch()
        al.addLayout(baris_auto)

        terakhir = db.cadangan_terakhir()
        if terakhir:
            al.addWidget(w.label(
                f"Cadangan terakhir: {terakhir['ts']} "
                f"({terakhir['size_bytes'] / 1024 / 1024:.2f} MB)",
                objek="Faint", wrap=True))
        else:
            al.addWidget(w.label("Belum ada cadangan dibuat.",
                                 objek="Faint", wrap=True))
        lay.addWidget(kartu_auto)

        kartu = w.Card()
        l = kartu.body()
        j = QLabel("Cadangkan & Pulihkan")
        j.setObjectName("SectionTitle")
        l.addWidget(j)

        baris = QHBoxLayout()
        baris.setSpacing(11)
        b = w.tombol("Buat Cadangan Sekarang", gaya="primary", ikon="simpan")
        b.clicked.connect(self._buat_backup)
        baris.addWidget(b)

        b2 = w.tombol("Pulihkan dari Cadangan", ikon="⟲")
        b2.clicked.connect(self._pulihkan_backup)
        baris.addWidget(b2)

        b3 = w.tombol("Ekspor Seluruh Data (Excel)", ikon="laporan")
        b3.clicked.connect(self._ekspor_semua)
        baris.addWidget(b3)
        baris.addStretch()
        l.addLayout(baris)

        l.addWidget(w.label(
            "Pemulihan cadangan akan MENGGANTI seluruh data saat ini. Pastikan Anda "
            "sudah membuat cadangan terbaru sebelum memulihkan.",
            objek="Faint", wrap=True))
        lay.addWidget(kartu)

        # daftar cadangan
        cadangan = db.q("SELECT * FROM backups ORDER BY id DESC LIMIT 50")
        if cadangan:
            lay.addWidget(w.label("Riwayat Cadangan", objek="SectionTitle"))
            t = w.Tabel([("Waktu", 175), ("Lokasi Berkas", -1),
                         ("Ukuran", 120), ("Keterangan", 250), ("", 100)])
            baris_t = [[
                c["ts"], c["path"],
                f"{c['size_bytes'] / 1024 / 1024:.2f} MB",
                c["keterangan"] or "", "Pulihkan",
            ] for c in cadangan]
            t.isi(baris_t, align_kanan={2})
            t.setMinimumHeight(260)
            t.cellClicked.connect(
                lambda r, c_: self._pulihkan_baris(r) if c_ == 4 else None)
            lay.addWidget(t)
        else:
            lay.addWidget(w.label(
                "Belum ada cadangan. Disarankan membuat cadangan pertama sekarang.",
                objek="Muted"))

        # ---------------------------------------------------- reset data
        # Dipakai saat aplikasi dialihkan ke perusahaan lain, atau saat data
        # percobaan ingin dibersihkan sebelum dipakai sungguhan.
        kartu_reset = w.Card()
        lr = kartu_reset.body()
        jr = QLabel("Mulai dari Data Kosong")
        jr.setObjectName("SectionTitle")
        lr.addWidget(jr)

        ringkas = self._ringkasan_reset()
        if ringkas["jumlah"]:
            lr.addWidget(w.label(
                "Menghapus seluruh transaksi dan data usaha, lalu menyisakan "
                "profil perusahaan, pengguna, dan bagan akun supaya aplikasi "
                "langsung siap dipakai untuk pembukuan baru.", wrap=True))
            lr.addWidget(w.label(
                f"Yang akan terhapus: {ringkas['rincian']}.", objek="Muted", wrap=True))
            lr.addWidget(w.label(
                "Cadangan otomatis dibuat lebih dulu, jadi data masih dapat "
                "dikembalikan lewat Pulihkan dari Cadangan.", objek="Muted", wrap=True))

            baris_reset = QHBoxLayout()
            b_reset = w.tombol("Hapus Data Usaha", gaya="danger", ikon="hapus")
            b_reset.clicked.connect(self._reset_data)
            baris_reset.addWidget(b_reset)
            baris_reset.addStretch()
            lr.addLayout(baris_reset)
        else:
            lr.addWidget(w.label(
                "Belum ada data usaha yang tercatat, jadi belum ada yang perlu "
                "dihapus.", objek="Muted", wrap=True))
        lay.addWidget(kartu_reset)

        lay.addStretch()

    def _ringkasan_reset(self) -> dict:
        """Berapa banyak data yang akan terhapus bila reset dijalankan."""
        from ...core import reset as rst
        r = rst.ringkasan(self.ctx.company_id)
        bagian = [f"{v} {k}" for k, v in r.items() if v]
        return {"jumlah": sum(r.values()),
                "rincian": ", ".join(bagian) if bagian else "tidak ada"}

    def _reset_data(self):
        """
        Hapus seluruh data usaha setelah pengguna mengetik kata konfirmasi.

        Konfirmasi memakai kata yang harus diketik, bukan sekadar tombol Ya.
        Menghapus seluruh pembukuan tidak dapat dibatalkan dari dalam
        aplikasi selain dengan memulihkan cadangan, jadi pengguna perlu
        berhenti dan membaca lebih dulu.
        """
        ringkas = self._ringkasan_reset()
        if not ringkas["jumlah"]:
            QMessageBox.information(self, "Tidak ada data",
                                    "Belum ada data usaha yang tercatat.")
            return

        pesan = (
            f"Seluruh data usaha akan dihapus:\n\n{ringkas['rincian']}\n\n"
            "Profil perusahaan, pengguna, dan bagan akun tetap disimpan.\n\n"
            "Cadangan otomatis dibuat sebelum penghapusan, tetapi tetap "
            "periksa dulu bahwa cadangan terbaru Anda sudah aman.\n\n"
            "Ketik HAPUS untuk melanjutkan."
        )
        teks, ok = QInputDialog.getText(
            self, "Hapus seluruh data usaha", pesan)
        if not ok or teks.strip().upper() != "HAPUS":
            if ok:
                QMessageBox.information(
                    self, "Dibatalkan",
                    "Data tidak dihapus karena kata konfirmasi tidak sesuai.")
            return

        try:
            from ...core import reset as rst
            hasil = rst.reset_data(self.ctx.company_id,
                                   user_id=self.ctx.user_id,
                                   username=self.ctx.username)
        except Exception as e:
            QMessageBox.critical(self, "Reset gagal", str(e))
            return

        QMessageBox.information(
            self, "Data usaha dihapus",
            f"{hasil['jumlah_baris']} baris data usaha sudah dihapus.\n\n"
            f"Cadangan sebelum penghapusan disimpan sebagai:\n"
            f"{hasil['berkas_cadangan'].name}\n\n"
            "Anda dapat memulihkannya kapan saja dari tab ini.")

        # Bila ada tabel yang tidak berhasil dibersihkan, pengguna diberi
        # tahu. Tanpa pemberitahuan, sisa data lama bisa terpakai lagi pada
        # pembukuan baru tanpa disadari.
        sisa = hasil.get("gagal_dihapus") or []
        if sisa:
            QMessageBox.warning(
                self, "Sebagian data belum terhapus",
                "Beberapa bagian data belum berhasil dibersihkan:\n\n"
                + "\n".join(f"• {s}" for s in sisa[:8])
                + "\n\nCoba jalankan sekali lagi. Bila tetap gagal, tutup "
                  "aplikasi lalu buka kembali sebelum mengulang.")
        self._muat_backup()

    def _simpan_setelan_backup(self):
        """Simpan pengaturan cadangan otomatis lalu muat ulang tabnya."""
        db.simpan_setelan_backup(
            aktif=bool(self.chk_backup_auto.currentData()),
            interval_jam=self.spn_interval.value(),
            simpan_maks=self.spn_simpan.value())
        QMessageBox.information(
            self, "Pengaturan tersimpan",
            "Pengaturan cadangan otomatis sudah disimpan.")
        self._muat_backup()

    def _buat_backup(self):
        try:
            path = db.create_backup(f"Dibuat oleh {self.ctx.username}")
            QMessageBox.information(
                self, "Cadangan berhasil",
                f"Cadangan tersimpan di:\n{path}\n\n"
                "Salin berkas ini ke lokasi lain untuk keamanan tambahan.")
            self._muat_backup()
        except Exception as e:
            QMessageBox.critical(self, "Gagal membuat cadangan", str(e))

    def _pulihkan_baris(self, r: int):
        cadangan = db.q("SELECT * FROM backups ORDER BY id DESC LIMIT 50")
        if r >= len(cadangan):
            return
        self._konfirmasi_pulihkan(cadangan[r]["path"])

    def _pulihkan_backup(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Pilih Berkas Cadangan",
            str(config.BACKUP_DIR if config.BACKUP_DIR.exists() else config.DATA_DIR),
            "Berkas Cadangan (*.db);;Semua Berkas (*)")
        if path:
            self._konfirmasi_pulihkan(path)

    def _konfirmasi_pulihkan(self, path: str):
        from pathlib import Path as _P
        berkas = _P(path)
        if not berkas.exists():
            QMessageBox.warning(self, "Berkas tidak ditemukan",
                                f"Berkas cadangan tidak ada:\n{path}")
            return

        try:
            waktu = datetime.fromtimestamp(berkas.stat().st_mtime)
            ukuran = berkas.stat().st_size / 1024
            keterangan = f"{waktu:%d %B %Y, %H:%M} · {ukuran:,.0f} KB"
        except OSError:
            keterangan = ""

        if QMessageBox.warning(
                self, "Konfirmasi Pemulihan",
                "Seluruh data yang ada sekarang akan diganti dengan isi "
                "berkas cadangan ini.\n\n"
                f"Berkas  : {berkas.name}\n"
                f"Dibuat  : {keterangan}\n\n"
                "Keadaan sekarang dicadangkan lebih dulu, jadi pemulihan ini "
                "masih bisa dibatalkan.\n\n"
                "Lanjutkan?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No) != QMessageBox.Yes:
            return

        try:
            hasil = db.pulihkan_dari_cadangan(berkas)
        except Exception as e:
            QMessageBox.critical(self, "Gagal memulihkan", str(e))
            return

        pesan = (
            "Data berhasil dipulihkan dan langsung dipakai - aplikasi tidak "
            "perlu ditutup.\n\n"
            f"Isi data sekarang:\n"
            f"• {hasil['perusahaan']} perusahaan\n"
            f"• {hasil['pengguna']} pengguna\n"
            f"• {hasil['jurnal']} jurnal\n")
        if hasil["cadangan_pengaman"]:
            pesan += ("\nKeadaan sebelum pemulihan disimpan sebagai cadangan "
                      "pengaman:\n"
                      f"{hasil['cadangan_pengaman'].name}\n\n"
                      "Bila pemulihan ini ternyata salah, pilih berkas itu "
                      "untuk kembali ke keadaan semula.")
        QMessageBox.information(self, "Pemulihan selesai", pesan)

        # Muat ulang tampilan supaya angka dan daftar mengikuti data baru.
        try:
            self.ctx.muat_perusahaan()
        except Exception:
            pass
        try:
            self._muat_backup()
        except Exception:
            pass

    def _ekspor_semua(self):
        cid = self.ctx.company_id
        if not cid:
            QMessageBox.information(self, "Belum ada perusahaan",
                                    "Buat profil perusahaan terlebih dahulu.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Ekspor Seluruh Data",
            str(config.EXPORT_DIR / f"Data_AkunTuntas_{datetime.now():%Y%m%d}.xlsx"),
            "Berkas Excel (*.xlsx)")
        if not path:
            return
        try:
            from .laporan import ekspor_excel
            comp = services.get_company(cid)
            data: list[tuple[str, list[list]]] = []

            # daftar akun
            akun = services.list_accounts(cid)
            data.append(("Bagan Akun", [["Kode", "Nama", "Tipe", "Grup L/R",
                                         "Baris Neraca", "Normal", "Saldo Awal",
                                         "Perlakuan Fiskal"]] +
                         [[a["kode"], a["nama"], a["tipe"], a["grup_lr"],
                           a["baris_neraca"], a["normal"], a["saldo_awal"],
                           a["perlakuan_fiskal"]] for a in akun]))

            # jurnal
            jurnal = services.list_jurnal(cid, limit=100000)
            baris_j = [["Tanggal", "No. Bukti", "Keterangan", "Sumber", "Debit", "Kredit"]]
            for e in jurnal:
                baris_j.append([e["tanggal"], e["no_bukti"], e["keterangan"],
                                e["sumber"], e["total_debit"], e["total_kredit"]])
            data.append(("Jurnal", baris_j))

            # rincian baris jurnal
            baris_l = [["No. Bukti", "Tanggal", "Kode Akun", "Nama Akun",
                        "Debit", "Kredit", "Lawan Transaksi", "NPWP/NIK", "Catatan"]]
            rows = db.q("""SELECT je.no_bukti, je.tanggal, jl.kode_akun, jl.nama_akun,
                                  jl.debit, jl.kredit, jl.lawan_transaksi, jl.npwp_nik,
                                  jl.catatan
                           FROM journal_lines jl
                           JOIN journal_entries je ON je.id = jl.entry_id
                           WHERE jl.company_id = ? ORDER BY je.tanggal, je.id""", (cid,))
            for r in rows:
                baris_l.append([r["no_bukti"], r["tanggal"], r["kode_akun"],
                                r["nama_akun"], r["debit"], r["kredit"],
                                r["lawan_transaksi"], r["npwp_nik"], r["catatan"]])
            data.append(("Baris Jurnal", baris_l))

            # penjualan
            penjualan = services.list_penjualan(cid)
            data.append(("Penjualan", [["Tanggal", "No. Invoice", "Pelanggan",
                                        "NPWP/NIK", "Nilai Penjualan", "Jenis PPN",
                                        "DPP Faktur", "PPN Keluaran", "Total Tagihan",
                                        "Lunas", "Tanggal Bayar"]] +
                         [[s["tanggal"], s["no_invoice"], s["pelanggan"], s["npwp_nik"],
                           s["nilai_penjualan"], s["jenis_ppn"], s["dpp_faktur"],
                           s["ppn_keluaran"], s["total_tagihan"],
                           "Ya" if s["lunas"] else "Tidak", s["tanggal_bayar"] or ""]
                          for s in penjualan]))

            # pembelian
            pembelian = services.list_pembelian(cid)
            data.append(("Pembelian", [["Tanggal", "No. Invoice", "Vendor", "Jenis",
                                        "Nilai", "Jenis PPN", "PPN Masukan",
                                        "Dikreditkan", "Total Bayar", "Dibayar"]] +
                         [[p["tanggal"], p["no_invoice"], p["vendor"], p["jenis"],
                           p["nilai_sebelum_ppn"], p["jenis_ppn"], p["ppn_masukan"],
                           p["ppn_dikreditkan"], p["total_bayar"],
                           "Ya" if p["dibayar"] else "Tidak"] for p in pembelian]))

            # aset
            aset = services.list_aset(cid)
            data.append(("Aset Tetap", [["Kode", "Nama", "Tanggal Perolehan",
                                         "Harga Perolehan", "Residu", "Umur Komersial",
                                         "Kelompok Fiskal", "Metode Fiskal"]] +
                         [[a["kode_aset"], a["nama_aset"], a["tanggal_perolehan"],
                           a["harga_perolehan"], a["residu_komersial"],
                           a["umur_komersial"], a["kelompok_fiskal"],
                           a["metode_fiskal"]] for a in aset]))

            # karyawan
            karyawan = services.list_karyawan(cid)
            data.append(("Karyawan", [["NIK/NPWP", "Nama", "Jabatan", "Status PTKP",
                                       "Gaji Pokok", "Tunjangan"]] +
                         [[k["nik_npwp"], k["nama"], k["jabatan"], k["status_ptkp"],
                           k["gaji_pokok"], k["tunjangan_tetap"]] for k in karyawan]))

            # pajak
            pajak = services.list_pajak(cid)
            data.append(("Pajak PotPut", [["Tanggal", "Masa", "Kode", "Jenis", "DPP",
                                           "Tarif", "Pajak", "Status", "No. Bupot"]] +
                         [[p["tanggal"], p["masa"], p["kode_pajak"], p["jenis"],
                           p["dpp"], p["tarif_dipakai"], p["pajak"], p["status"],
                           p["no_bupot"]] for p in pajak]))

            # pembayaran pajak
            bayar = services.list_pembayaran_pajak(cid)
            data.append(("Setoran Pajak", [["Tanggal", "Jenis", "Masa", "Jumlah",
                                            "NTPN", "Cara Bayar"]] +
                         [[b["tanggal_bayar"], b["jenis_pajak"], b["masa"], b["jumlah"],
                           b["ntpn"], b["cara_bayar"]] for b in bayar]))

            ekspor_excel(comp["nama"], data, path)
            if QMessageBox.question(
                    self, "Ekspor selesai",
                    f"Seluruh data berhasil diekspor:\n{path}\n\nBuka foldernya?",
                    QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
                QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.dirname(path)))
        except Exception as e:
            QMessageBox.critical(self, "Gagal mengekspor", str(e))

    # ------------------------------------------------------------------
    # AUDIT
    # ------------------------------------------------------------------
    def _muat_audit(self):
        lay = self._bersihkan(self.tab_audit)

        lay.addWidget(w.InfoBanner(
            "Jejak audit mencatat siapa melakukan apa dan kapan. Catatan ini penting "
            "untuk membuktikan bahwa pembukuan dijalankan secara konsisten - salah "
            "satu syarat pembukuan yang dapat dipercaya dalam pemeriksaan pajak.",
            "info", "Tentang jejak audit"))

        baris = QHBoxLayout()
        baris.setSpacing(10)
        baris.addWidget(w.label("Jenis catatan:", objek="FormLabel"))
        self.cmb_jenis_audit = QComboBox()
        self.cmb_jenis_audit.addItem("Perubahan data pembukuan", db.KATEGORI_DATA)
        self.cmb_jenis_audit.addItem("Masuk dan keluar aplikasi",
                                     db.KATEGORI_KEAMANAN)
        self.cmb_jenis_audit.addItem("Pengelolaan pengguna & perusahaan",
                                     db.KATEGORI_ADMIN)
        self.cmb_jenis_audit.addItem("Semua catatan", "")
        self.cmb_jenis_audit.currentIndexChanged.connect(self._muat_audit)
        baris.addWidget(self.cmb_jenis_audit)

        b = w.tombol("Muat Ulang", ikon="segarkan")
        b.clicked.connect(self._muat_audit)
        baris.addWidget(b)
        baris.addStretch()
        lay.addLayout(baris)

        kategori = self.cmb_jenis_audit.currentData()
        log = sec.recent_audit(500, kategori or None)
        t = w.Tabel([("Waktu", 180), ("Pengguna", 160), ("Aksi", 200),
                     ("Objek", 170), ("ID", 80), ("Keterangan", -1)])
        baris_t = [[l["ts"], l["username"] or "sistem",
                    istilah.label("action", l["action"]),
                    istilah.label("entity", l["entity"]),
                    l["entity_id"] or "", l["detail"] or ""]
                   for l in log]
        t.isi(baris_t)
        t.setMinimumHeight(420)
        lay.addWidget(t)

        jumlah = sec.hitung_per_kategori()
        lay.addWidget(w.label(
            f"Menampilkan {len(log)} catatan terakhir. "
            f"Total tercatat - perubahan data: {jumlah.get(db.KATEGORI_DATA, 0)}, "
            f"keamanan: {jumlah.get(db.KATEGORI_KEAMANAN, 0)}, "
            f"administrasi: {jumlah.get(db.KATEGORI_ADMIN, 0)}.",
            objek="Muted"))
        lay.addStretch()


# ==========================================================================
# DIALOG PENGGUNA
# ==========================================================================
class DialogPengguna(QDialog):
    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.setWindowTitle("Tambah Pengguna")
        self.setMinimumWidth(560)

        l = QVBoxLayout(self)
        l.setContentsMargins(24, 22, 24, 22)
        l.setSpacing(13)

        j = QLabel("Pengguna Baru")
        j.setObjectName("SectionTitle")
        l.addWidget(j)

        l.addWidget(w.HelpPanel(
            "Tentang peran pengguna",
            "• PEMILIK - akses penuh, termasuk mengelola pengguna dan pengaturan.\n"
            "• ADMINISTRATOR - akses penuh kecuali menghapus perusahaan.\n"
            "• STAF - dapat mencatat transaksi, tidak dapat mengubah pengaturan.\n"
            "• HANYA LIHAT - hanya dapat melihat laporan, tidak dapat mengubah data.",
            "Pasal 28 UU KUP - pemisahan tugas mendukung pengendalian internal."))

        g = QGridLayout()
        g.setSpacing(12)

        g.addWidget(w.label("Nama Pengguna", objek="FormLabel"), 0, 0)
        self.inp_username = QLineEdit()
        self.inp_username.setPlaceholderText("huruf kecil tanpa spasi")
        g.addWidget(self.inp_username, 1, 0)

        g.addWidget(w.label("Nama Lengkap", objek="FormLabel"), 0, 1)
        self.inp_nama = QLineEdit()
        g.addWidget(self.inp_nama, 1, 1)

        g.addWidget(w.label("Email", objek="FormLabel"), 2, 0)
        self.inp_email = QLineEdit()
        g.addWidget(self.inp_email, 3, 0)

        g.addWidget(w.label("Peran", objek="FormLabel"), 2, 1)
        self.cmb_role = QComboBox()
        self.cmb_role.addItem("Staf - input transaksi", "staff")
        self.cmb_role.addItem("Administrator - akses penuh", "admin")
        self.cmb_role.addItem("Pemilik - akses penuh + kelola pengguna", "owner")
        self.cmb_role.addItem("Hanya Lihat - tidak dapat mengubah", "viewer")
        g.addWidget(self.cmb_role, 3, 1)

        g.addWidget(w.label("Password", objek="FormLabel"), 4, 0)
        self.inp_password = QLineEdit()
        self.inp_password.setEchoMode(QLineEdit.Password)
        self.inp_password.textChanged.connect(self._cek)
        g.addWidget(self.inp_password, 5, 0)

        g.addWidget(w.label("Ulangi Password", objek="FormLabel"), 4, 1)
        self.inp_ulang = QLineEdit()
        self.inp_ulang.setEchoMode(QLineEdit.Password)
        g.addWidget(self.inp_ulang, 5, 1)

        g.addWidget(w.label("Mode Aplikasi", objek="FormLabel"), 6, 0, 1, 2)
        self.cmb_mode = QComboBox()
        self.cmb_mode.addItem("Pemula - tampilkan penjelasan", "beginner")
        self.cmb_mode.addItem("Ahli - antarmuka ringkas", "expert")
        g.addWidget(self.cmb_mode, 7, 0, 1, 2)
        l.addLayout(g)

        self.lbl_kekuatan = QLabel("")
        self.lbl_kekuatan.setStyleSheet(f"font-size: {theme.FS_SMALL}px; "
                                        "background: transparent;")
        l.addWidget(self.lbl_kekuatan)

        self.chk_wajib_ganti = QCheckBox(
            "Wajibkan pengguna mengganti password saat login pertama")
        self.chk_wajib_ganti.setChecked(True)
        l.addWidget(self.chk_wajib_ganti)

        aksi = QHBoxLayout()
        aksi.addStretch()
        b = w.tombol("Batal")
        b.clicked.connect(self.reject)
        aksi.addWidget(b)
        bs = w.tombol("Simpan Pengguna", gaya="primary")
        bs.clicked.connect(self._simpan)
        aksi.addWidget(bs)
        l.addLayout(aksi)

    def _cek(self, teks: str):
        if not teks:
            self.lbl_kekuatan.setText("")
            return
        skor, label, saran = sec.password_strength(teks)
        warna = [C.DANGER, C.DANGER, C.WARNING, C.SUCCESS, C.SUCCESS][skor]
        bar = "█" * (skor + 1) + "░" * (4 - skor)
        pesan = f"Kekuatan: <b style='color:{warna}'>{label}</b> " \
                f"<span style='color:{warna}'>{bar}</span>"
        if saran:
            pesan += f"<br><span style='color:{C.TEXT_MUTED}'>{' '.join(saran)}</span>"
        self.lbl_kekuatan.setText(pesan)
        self.lbl_kekuatan.setTextFormat(Qt.RichText)

    def _simpan(self):
        try:
            if self.inp_password.text() != self.inp_ulang.text():
                QMessageBox.warning(self, "Password tidak sama",
                                    "Password dan ulangannya tidak sama.")
                return
            sec.create_user(
                self.inp_username.text().strip(),
                self.inp_password.text(),
                self.inp_nama.text().strip(),
                self.cmb_role.currentData(),
                self.inp_email.text().strip(),
                self.cmb_mode.currentData(),
                1 if self.chk_wajib_ganti.isChecked() else 0)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Gagal menyimpan", str(e))


class DialogResetPassword(QDialog):
    def __init__(self, ctx, user, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.user = user
        self.setWindowTitle(f"Reset Password - {user['username']}")
        self.setMinimumWidth(480)

        l = QVBoxLayout(self)
        l.setContentsMargins(24, 22, 24, 22)
        l.setSpacing(13)

        j = QLabel(f"Reset Password: {user['username']}")
        j.setObjectName("SectionTitle")
        l.addWidget(j)

        l.addWidget(w.HelpPanel(
            "Tentang reset password",
            "Gunakan fitur ini bila pengguna lupa passwordnya. Password baru akan "
            "diberikan kepada pengguna, dan ia akan diminta menggantinya saat login "
            "berikutnya.\n\n"
            "Sampaikan password baru secara aman - jangan melalui saluran yang tidak "
            "terlindungi.",
            "Kebijakan keamanan data internal."))

        l.addWidget(w.label("Password Baru", objek="FormLabel"))
        self.inp_password = QLineEdit()
        self.inp_password.setEchoMode(QLineEdit.Password)
        l.addWidget(self.inp_password)

        l.addWidget(w.label("Ulangi Password Baru", objek="FormLabel"))
        self.inp_ulang = QLineEdit()
        self.inp_ulang.setEchoMode(QLineEdit.Password)
        l.addWidget(self.inp_ulang)

        aksi = QHBoxLayout()
        aksi.addStretch()
        b = w.tombol("Batal")
        b.clicked.connect(self.reject)
        aksi.addWidget(b)
        bs = w.tombol("Reset Password", gaya="danger")
        bs.clicked.connect(self._simpan)
        aksi.addWidget(bs)
        l.addLayout(aksi)

    def _simpan(self):
        try:
            if self.inp_password.text() != self.inp_ulang.text():
                QMessageBox.warning(self, "Tidak sama",
                                    "Password dan ulangannya tidak sama.")
                return
            sec.reset_password(self.user["id"], self.inp_password.text(),
                               self.ctx.user_id, self.ctx.username)
            QMessageBox.information(
                self, "Password direset",
                f"Password pengguna '{self.user['username']}' telah direset.\n\n"
                "Sampaikan password baru kepada pengguna. Ia akan diminta "
                "menggantinya saat login.")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Gagal reset", str(e))


class DialogGantiPassword(QDialog):
    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.setWindowTitle("Ganti Password Saya")
        self.setMinimumWidth(480)

        l = QVBoxLayout(self)
        l.setContentsMargins(24, 22, 24, 22)
        l.setSpacing(13)

        j = QLabel("Ganti Password Anda")
        j.setObjectName("SectionTitle")
        l.addWidget(j)

        l.addWidget(w.label("Password Saat Ini", objek="FormLabel"))
        self.inp_lama = QLineEdit()
        self.inp_lama.setEchoMode(QLineEdit.Password)
        l.addWidget(self.inp_lama)

        l.addWidget(w.label("Password Baru", objek="FormLabel"))
        self.inp_baru = QLineEdit()
        self.inp_baru.setEchoMode(QLineEdit.Password)
        self.inp_baru.textChanged.connect(self._cek)
        l.addWidget(self.inp_baru)

        self.lbl_kekuatan = QLabel("")
        self.lbl_kekuatan.setStyleSheet(f"font-size: {theme.FS_SMALL}px; "
                                        "background: transparent;")
        l.addWidget(self.lbl_kekuatan)

        l.addWidget(w.label("Ulangi Password Baru", objek="FormLabel"))
        self.inp_ulang = QLineEdit()
        self.inp_ulang.setEchoMode(QLineEdit.Password)
        l.addWidget(self.inp_ulang)

        aksi = QHBoxLayout()
        aksi.addStretch()
        b = w.tombol("Batal")
        b.clicked.connect(self.reject)
        aksi.addWidget(b)
        bs = w.tombol("Simpan Password", gaya="primary")
        bs.clicked.connect(self._simpan)
        aksi.addWidget(bs)
        l.addLayout(aksi)

    def _cek(self, teks: str):
        if not teks:
            self.lbl_kekuatan.setText("")
            return
        skor, label, saran = sec.password_strength(teks)
        warna = [C.DANGER, C.DANGER, C.WARNING, C.SUCCESS, C.SUCCESS][skor]
        self.lbl_kekuatan.setText(f"Kekuatan: <b style='color:{warna}'>{label}</b>")
        self.lbl_kekuatan.setTextFormat(Qt.RichText)

    def _simpan(self):
        try:
            if self.inp_baru.text() != self.inp_ulang.text():
                QMessageBox.warning(self, "Tidak sama",
                                    "Password baru dan ulangannya tidak sama.")
                return
            sec.change_password(self.ctx.user_id, self.inp_lama.text(),
                                self.inp_baru.text())
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Gagal mengganti password", str(e))


# ==========================================================================
# HALAMAN CHECKLIST KEPATUHAN
# ==========================================================================
class ChecklistPage(QWidget):
    pindah_halaman = Signal(str)

    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx

        luar = QVBoxLayout(self)
        luar.setContentsMargins(0, 0, 0, 0)
        luar.setSpacing(0)

        self.header = w.PageHeader(
            "Checklist Kepatuhan",
            "Daftar periksa pembukuan dan pajak. Menjalankan checklist ini secara "
            "rutin mencegah sanksi dan menjaga kualitas pembukuan.")

        self.cmb_masa = QComboBox()
        self.cmb_masa.addItem("Semua Periode", "")
        tk = datetime.now().year
        for t in range(tk - 1, tk + 1):
            for b in range(1, 13):
                self.cmb_masa.addItem(f"{config.MONTH_NAMES_ID[b - 1]} {t}",
                                      f"{t}-{b:02d}")
        self.cmb_masa.setMinimumWidth(140)
        self.cmb_masa.currentIndexChanged.connect(self.muat)
        self.header.tambah_aksi(self.cmb_masa)

        b = w.tombol("Tambah Item", ikon="+")
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
            ("Frekuensi", 135), ("Area", 165), ("Checklist", -1),
            ("Status", 130), ("PIC", 150), ("Catatan", 200), ("Tindakan", 110),
        ])
        self.lay.addWidget(self.tabel, 1)

        self.lbl_info = QLabel("")
        self.lbl_info.setObjectName("Muted")
        self.lay.addWidget(self.lbl_info)

    def muat(self):
        cid = self.ctx.company_id
        if not cid:
            return
        masa = self.cmb_masa.currentData()
        data = services.list_checklist(cid, masa)
        baris, warna = [], {}
        for i, c in enumerate(data):
            idx = len(baris)
            baris.append([c["frekuensi"], c["area"], c["checklist"],
                          c["status"], c["pic"], c["catatan"], "Ubah Status"])
            if c["status"] == "Selesai":
                warna[idx] = C.SUCCESS
            elif c["status"] == "Belum":
                warna[idx] = C.WARNING
        self.tabel.isi(baris, warna_baris=warna)
        self.tabel.cellClicked.connect(
            lambda r, c_: self._ubah_status(r) if c_ == 6 else None)
        selesai = sum(1 for c in data if c["status"] == "Selesai")
        self.lbl_info.setText(
            f"{selesai} dari {len(data)} item selesai "
            f"({selesai / len(data) * 100:.0f}%)" if data else "Belum ada item")

    def _ubah_status(self, r: int):
        masa = self.cmb_masa.currentData()
        data = services.list_checklist(self.ctx.company_id, masa)
        if r >= len(data):
            return
        c = data[r]
        d = DialogStatusChecklist(c, self)
        if d.exec():
            services.update_checklist(c["id"], status=d.status, pic=d.pic,
                                      catatan=d.catatan, masa=d.masa)
            self.muat()

    def _tambah(self):
        d = DialogTambahChecklist(self, self)
        if d.exec():
            services.tambah_checklist(self.ctx.company_id, d.frekuensi,
                                      d.area, d.checklist)
            self.muat()


class DialogStatusChecklist(QDialog):
    def __init__(self, item, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ubah Status Checklist")
        self.setMinimumWidth(480)
        self.status = item["status"]
        self.pic = item["pic"] or ""
        self.catatan = item["catatan"] or ""
        self.masa = item["masa"] or ""

        l = QVBoxLayout(self)
        l.setContentsMargins(24, 22, 24, 22)
        l.setSpacing(13)

        j = QLabel(item["checklist"])
        j.setWordWrap(True)
        j.setObjectName("SectionTitle")
        l.addWidget(j)

        l.addWidget(w.label("Status", objek="FormLabel"))
        self.cmb_status = QComboBox()
        for s in ["Belum", "Proses", "Selesai", "N/A"]:
            self.cmb_status.addItem(s, s)
        i = self.cmb_status.findData(item["status"])
        if i >= 0:
            self.cmb_status.setCurrentIndex(i)
        l.addWidget(self.cmb_status)

        l.addWidget(w.label("Penanggung Jawab (PIC)", objek="FormLabel"))
        self.inp_pic = QLineEdit(self.pic)
        l.addWidget(self.inp_pic)

        l.addWidget(w.label("Masa Pajak (YYYY-MM, opsional)", objek="FormLabel"))
        self.inp_masa = QLineEdit(self.masa)
        self.inp_masa.setPlaceholderText("mis. 2026-01")
        l.addWidget(self.inp_masa)

        l.addWidget(w.label("Catatan", objek="FormLabel"))
        self.inp_catatan = QLineEdit(self.catatan)
        l.addWidget(self.inp_catatan)

        aksi = QHBoxLayout()
        aksi.addStretch()
        b = w.tombol("Batal")
        b.clicked.connect(self.reject)
        aksi.addWidget(b)
        bs = w.tombol("Simpan", gaya="primary")
        bs.clicked.connect(self._simpan)
        aksi.addWidget(bs)
        l.addLayout(aksi)

    def _simpan(self):
        self.status = self.cmb_status.currentData()
        self.pic = self.inp_pic.text().strip()
        self.catatan = self.inp_catatan.text().strip()
        self.masa = self.inp_masa.text().strip()
        self.accept()


class DialogTambahChecklist(QDialog):
    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Tambah Item Checklist")
        self.setMinimumWidth(520)
        self.frekuensi = "Bulanan"
        self.area = ""
        self.checklist = ""

        l = QVBoxLayout(self)
        l.setContentsMargins(24, 22, 24, 22)
        l.setSpacing(13)

        j = QLabel("Item Checklist Baru")
        j.setObjectName("SectionTitle")
        l.addWidget(j)

        l.addWidget(w.label("Frekuensi", objek="FormLabel"))
        self.cmb_frek = QComboBox()
        for f in ["Bulanan", "Triwulanan", "Semesteran", "Tahunan", "Insidental"]:
            self.cmb_frek.addItem(f, f)
        l.addWidget(self.cmb_frek)

        l.addWidget(w.label("Area", objek="FormLabel"))
        self.inp_area = QLineEdit()
        self.inp_area.setPlaceholderText("mis. PPN, PPh 21, Persediaan")
        l.addWidget(self.inp_area)

        l.addWidget(w.label("Uraian Checklist", objek="FormLabel"))
        self.inp_checklist = QLineEdit()
        self.inp_checklist.setPlaceholderText("Apa yang harus dilakukan?")
        l.addWidget(self.inp_checklist)

        aksi = QHBoxLayout()
        aksi.addStretch()
        b = w.tombol("Batal")
        b.clicked.connect(self.reject)
        aksi.addWidget(b)
        bs = w.tombol("Tambah", gaya="primary")
        bs.clicked.connect(self._simpan)
        aksi.addWidget(bs)
        l.addLayout(aksi)

    def _simpan(self):
        if not self.inp_checklist.text().strip():
            QMessageBox.warning(self, "Kosong", "Isi uraian checklist.")
            return
        self.frekuensi = self.cmb_frek.currentData()
        self.area = self.inp_area.text().strip() or "Umum"
        self.checklist = self.inp_checklist.text().strip()
        self.accept()


# ==========================================================================
# HALAMAN BANTUAN
# ==========================================================================
class BantuanPage(QWidget):
    pindah_halaman = Signal(str)

    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx

        luar = QVBoxLayout(self)
        luar.setContentsMargins(0, 0, 0, 0)
        luar.setSpacing(0)

        self.header = w.PageHeader(
            "Panduan & Referensi",
            "Penjelasan konsep akuntansi, alur kerja, dan dasar hukum perpajakan "
            "Indonesia yang berlaku.")

        b_lapor = w.tombol("Laporkan Masalah", gaya="biasa", ikon="dokumen")
        b_lapor.setToolTip(
            "Kirim laporan kesalahan kepada pengembang beserta keterangan teknis")
        b_lapor.clicked.connect(self._lapor_masalah)
        self.header.tambah_aksi(b_lapor)

        kepala = QWidget()
        theme.latar(kepala, f"background: {C.SURFACE}; "
                             f"border-bottom: 1px solid {C.BORDER};")
        kl = QVBoxLayout(kepala)
        kl.setContentsMargins(26, 20, 26, 18)
        kl.addWidget(self.header)
        luar.addWidget(kepala)

        isi = QWidget()
        wl = QHBoxLayout(isi)
        wl.setContentsMargins(22, 18, 22, 22)
        wl.setSpacing(18)

        # daftar topik
        self.daftar = QListWidget()
        self.daftar.setFixedWidth(255)
        self.daftar.setStyleSheet(
            f"QListWidget {{ background: {C.SURFACE}; border: 1px solid {C.BORDER}; "
            f"border-radius: 8px; padding: 6px; font-size: {theme.FS_BODY}px; }}"
            f"QListWidget::item {{ padding: 10px 12px; border-radius: 6px; }}"
            f"QListWidget::item:selected {{ background: {C.PRIMARY_SOFT}; "
            f"color: {C.PRIMARY_DARK}; font-weight: 600; }}"
            f"QListWidget::item:hover {{ background: {C.SURFACE_ALT}; }}")
        wl.addWidget(self.daftar)

        self.stack = QStackedWidget()
        wl.addWidget(self.stack, 1)
        luar.addWidget(isi, 1)

        # Topik dibuat saat dipilih, bukan seluruhnya sekaligus.
        #
        # Ada lima belas topik berisi teks panjang. Membuat semuanya saat
        # halaman dibuka memakan lebih dari satu detik, padahal pengguna
        # hanya membaca satu topik. Yang belum dibuka cukup ditandai, lalu
        # isinya dibuat ketika barisnya dipilih.
        self._pembuat_topik: list = []
        self._topik_siap: dict[int, QWidget] = {}
        self._bangun_topik()
        self.daftar.currentRowChanged.connect(self._pilih_topik)
        self.daftar.setCurrentRow(0)

    def _pilih_topik(self, baris: int):
        """Tampilkan topik yang dipilih, buat isinya bila belum ada."""
        if baris < 0 or baris >= len(self._pembuat_topik):
            return
        if baris not in self._topik_siap:
            pembuat = self._pembuat_topik[baris]
            try:
                isi = pembuat()
            except Exception as e:
                isi = QLabel(f"Topik ini gagal dibuka: {e}")
                isi.setWordWrap(True)
            self._topik_siap[baris] = isi
            self.stack.addWidget(isi)
        self.stack.setCurrentWidget(self._topik_siap[baris])

    def _lapor_masalah(self):
        """Buka formulir laporan masalah untuk pengembang."""
        from ..dialog_bug import dialog_lapor
        dialog_lapor(self)

    def _bangun_topik(self):
        topik_urut = [
            ("alur", "Alur Kerja Aplikasi", self._topik_alur),
            ("coa", None, None), ("jurnal", None, None), ("penjualan", None, None),
            ("pembelian", None, None), ("aset", None, None), ("pajak", None, None),
            ("payroll", None, None), ("pph_badan", None, None), ("ppn", None, None),
            ("rekonsiliasi", None, None), ("legal", None, None),
            ("bentuk_badan", None, None),
        ]

        for kunci, judul, builder in topik_urut:
            if builder:
                self.daftar.addItem(judul)
                self._pembuat_topik.append(builder)
            else:
                topik = coa.HELP_TOPICS.get(kunci)
                if topik:
                    self.daftar.addItem(topik["judul"])
                    self._pembuat_topik.append(
                        lambda t=topik: self._topik_dari_help(t))

        # referensi aturan
        self.daftar.addItem("Referensi Aturan Lengkap")
        self._pembuat_topik.append(self._topik_referensi)

        # salinan resmi regulasi
        self.daftar.addItem("Salinan Regulasi Resmi")
        self._pembuat_topik.append(self._topik_salinan)

        # tentang aplikasi
        self.daftar.addItem("Tentang Aplikasi")
        self._pembuat_topik.append(self._topik_tentang)

    def _topik_salinan(self) -> QWidget:
        """Baca salinan teks regulasi resmi yang disertakan aplikasi."""
        wadah = QWidget()
        lay = QVBoxLayout(wadah)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(14)

        j = QLabel("Salinan Regulasi Resmi")
        j.setStyleSheet("font-size: 20px; font-weight: 700; background: transparent;")
        lay.addWidget(j)

        pengantar = QLabel(
            "Aplikasi menyertakan salinan teks peraturan resmi yang menjadi dasar "
            "seluruh perhitungan pajak. Anda dapat membacanya langsung di sini "
            "untuk memeriksa kesesuaiannya.\n\n"
            "Pilih peraturan pada daftar di bawah untuk menampilkan isinya.")
        pengantar.setWordWrap(True)
        pengantar.setStyleSheet(f"font-size: {theme.FS_BODY}px; line-height: 165%; "
                                "background: transparent;")
        lay.addWidget(pengantar)

        berkas = _daftar_regulasi()
        if not berkas:
            lay.addWidget(w.InfoBanner(
                "Berkas salinan regulasi tidak ditemukan pada pemasangan ini.",
                "warning", "Tidak tersedia"))
            lay.addStretch()
            return w.scroll(wadah)

        baris = QHBoxLayout()
        baris.setSpacing(12)

        daftar = QListWidget()
        daftar.setFixedWidth(280)
        daftar.setStyleSheet(
            f"QListWidget {{ background: {C.SURFACE}; border: 1px solid {C.BORDER}; "
            f"border-radius: 8px; padding: 6px; font-size: {theme.FS_SMALL}px; }}"
            f"QListWidget::item {{ padding: 9px 11px; border-radius: 6px; }}"
            f"QListWidget::item:selected {{ background: {C.PRIMARY_SOFT}; "
            f"color: {C.PRIMARY_DARK}; font-weight: 600; }}")
        for _, judul, _ in berkas:
            daftar.addItem(judul)
        baris.addWidget(daftar)

        isi = QTextEdit()
        isi.setReadOnly(True)
        theme.latar(isi, f"background: {C.SURFACE}; border: 1px solid {C.BORDER}; "
            f"border-radius: 8px; padding: 10px; "
            f"font-family: {theme.FONT_ANGKA}; font-size: {theme.FS_TINY}px;")
        baris.addWidget(isi, 1)
        lay.addLayout(baris)

        def tampilkan(baris_ke: int):
            if baris_ke < 0 or baris_ke >= len(berkas):
                return
            path = berkas[baris_ke][2]
            try:
                isi.setPlainText(path.read_text(encoding="utf-8", errors="replace"))
                isi.moveCursor(isi.textCursor().Start)
            except Exception as e:
                isi.setPlainText(f"Berkas tidak dapat dibaca: {e}")

        daftar.currentRowChanged.connect(tampilkan)
        daftar.setCurrentRow(0)

        tombol = QHBoxLayout()
        b = w.tombol("Buka di Aplikasi Lain", ikon="dokumen")
        b.clicked.connect(lambda: _buka_regulasi(berkas, daftar.currentRow()))
        tombol.addWidget(b)
        tombol.addStretch()
        lay.addLayout(tombol)

        return w.scroll(wadah)

    def _topik_dari_help(self, topik: dict) -> QWidget:
        wadah = QWidget()
        lay = QVBoxLayout(wadah)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(14)

        j = QLabel(topik["judul"])
        j.setStyleSheet("font-size: 20px; font-weight: 700; background: transparent;")
        lay.addWidget(j)

        isi = QLabel(topik["isi"])
        isi.setWordWrap(True)
        isi.setTextInteractionFlags(Qt.TextSelectableByMouse)
        isi.setStyleSheet(f"font-size: {theme.FS_BODY}px; line-height: 165%; "
                          "background: transparent;")
        lay.addWidget(isi)

        if topik.get("dasar_hukum"):
            lay.addWidget(w.HelpPanel("Dasar Hukum", "", topik["dasar_hukum"]))
        lay.addStretch()
        return w.scroll(wadah)

    def _topik_alur(self) -> QWidget:
        wadah = QWidget()
        lay = QVBoxLayout(wadah)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(14)

        j = QLabel("Alur Kerja Aplikasi")
        j.setStyleSheet("font-size: 20px; font-weight: 700; background: transparent;")
        lay.addWidget(j)

        isi = QLabel(
            "Ikuti urutan berikut agar pembukuan tersusun rapi sejak awal:\n\n"
            "TAHAP 1 - PENYIAPAN (sekali saja)\n"
            "1. Buat profil perusahaan di menu Data Perusahaan. Pilih bentuk badan "
            "yang tepat - aplikasi otomatis menyiapkan bagan akun sesuai bentuknya.\n"
            "2. Buka Bagan Akun, isi saldo awal bila usaha sudah berjalan sebelumnya. "
            "Pastikan total debit = total kredit.\n"
            "3. Lengkapi pengaturan pajak: status PKP, skema PPh, omzet tahun lalu.\n\n"
            "TAHAP 2 - INPUT RUTIN (harian/mingguan)\n"
            "4. Catat penjualan di menu Penjualan. PPN keluaran dihitung otomatis.\n"
            "5. Catat pembelian dan biaya di menu Pembelian. PPN masukan dihitung "
            "otomatis.\n"
            "6. Untuk transaksi lain (setoran modal, pinjaman, prive), gunakan Jurnal "
            "Umum. Tersedia 12 contoh jurnal standar bila Anda ragu.\n\n"
            "TAHAP 3 - BULANAN\n"
            "7. Jalankan Payroll untuk menghitung gaji dan PPh 21.\n"
            "8. Catat pemotongan PPh 23/4(2) bila Anda membayar jasa atau sewa.\n"
            "9. Catat setoran pajak setelah membayar melalui bank.\n"
            "10. Buka Checklist Kepatuhan dan tandai item yang sudah dikerjakan.\n"
            "11. Periksa Dashboard - bila ada temuan KRITIS, segera tangani.\n\n"
            "TAHAP 4 - TAHUNAN\n"
            "12. Hitung penyusutan aset di menu Aset Tetap.\n"
            "13. Buka Rekonsiliasi Fiskal, tinjau akun berstatus 'Review Fiskal', "
            "tambahkan koreksi manual bila perlu.\n"
            "14. Buka PPh Badan untuk melihat PPh terutang dan angsuran PPh 25 "
            "tahun berikutnya.\n"
            "15. Cetak laporan (Excel/PDF) dan siapkan SPT Tahunan.\n"
            "16. Lakukan stock opname persediaan.\n"
            "17. Buat cadangan data.\n\n"
            "TIPS: Jalankan analisis kesehatan keuangan setiap bulan. Aplikasi akan "
            "memperingatkan lebih awal bila ada masalah."
        )
        isi.setWordWrap(True)
        isi.setTextInteractionFlags(Qt.TextSelectableByMouse)
        isi.setStyleSheet(f"font-size: {theme.FS_BODY}px; line-height: 165%; "
                          "background: transparent;")
        lay.addWidget(isi)
        lay.addStretch()
        return w.scroll(wadah)

    def _topik_referensi(self) -> QWidget:
        wadah = QWidget()
        lay = QVBoxLayout(wadah)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(14)

        j = QLabel("Referensi Aturan Lengkap")
        j.setStyleSheet("font-size: 20px; font-weight: 700; background: transparent;")
        lay.addWidget(j)

        referensi = [
            ("PPh Badan", [
                ("Tarif umum 22%", "UU No. 7/2021 (UU HPP) Pasal 17 ayat (1) huruf b"),
                ("Fasilitas Pasal 31E - pengurangan 50% tarif atas PKP dari bagian "
                 "peredaran bruto sampai Rp4,8 miliar, untuk badan dengan peredaran "
                 "bruto sampai Rp50 miliar", "UU PPh Pasal 31E; SE-02/PJ/2015"),
                ("Pembulatan PKP ke ribuan penuh ke bawah",
                 "UU PPh Pasal 17 ayat (4)"),
                ("Kompensasi kerugian maksimal 5 tahun", "UU PPh Pasal 6 ayat (2)"),
                ("Angsuran PPh 25 = (PPh terutang − kredit) ÷ 12",
                 "UU PPh Pasal 25"),
            ]),
            ("PPh Final UMKM", [
                ("Tarif 0,5% atas peredaran bruto sampai Rp4,8 miliar",
                 "PP 55/2022 jo. PP 20/2026"),
                ("Bagi Orang Pribadi: peredaran bruto sampai Rp500 juta tidak "
                 "dikenai pajak", "PP 55/2022 Pasal 3 ayat (2)"),
                ("Masa pemanfaatan terbatas; kelayakan bergantung bentuk badan",
                 "PP 20/2026"),
            ]),
            ("PPN", [
                ("Tarif 12%", "UU No. 7/2021 (UU HPP) Pasal 7"),
                ("Mekanisme DPP Nilai Lain 11/12 untuk non-mewah (efektif 11%)",
                 "PMK 131/PMK.03/2024"),
                ("DPP penuh 12% untuk objek mewah tertentu",
                 "PP 61/2020 jo. PMK 96/2025"),
                ("Batas pengusaha kecil / wajib PKP Rp4,8 miliar",
                 "PMK 197/PMK.03/2013; PP 44/2022"),
                ("PPN masukan tidak dapat dikreditkan (Pasal 9 ayat 8)",
                 "UU PPN jo. UU HPP"),
            ]),
            ("PPh Potong/Pungut", [
                ("PPh 21 - skema TER bulanan kategori A/B/C; Desember dihitung "
                 "setahun penuh", "PMK 168/PMK.03/2023; PP 58/2023"),
                ("PPh 23 - 2% jasa & sewa harta selain tanah/bangunan; 15% bunga, "
                 "royalti, hadiah", "UU PPh Pasal 23; PMK 141/PMK.03/2015"),
                ("PPh 22 - 2,5% impor dengan API; 7,5% tanpa API; 0,25% pembelian "
                 "dari UMKM; 1,5% barang tertentu", "UU PPh Pasal 22; PMK 34/2017"),
                ("PPh 26 - 20% WPLN atau tarif P3B", "UU PPh Pasal 26"),
                ("PPh Final 4(2) - sewa tanah/bangunan 10%; konstruksi 1,75%-2,65%; "
                 "pengalihan tanah 2,5%; bunga deposito 20%; hadiah undian 25%",
                 "PP 34/2017; PP 9/2022; PP 34/2016; PP 19/2009"),
            ]),
            ("Penyusutan", [
                ("Kelompok 1 (4 thn) 25%/50%; Kelompok 2 (8 thn) 12,5%/25%; "
                 "Kelompok 3 (16 thn) 6,25%/12,5%; Kelompok 4 (20 thn) 5%/10%; "
                 "bangunan permanen 5%; non-permanen 10%",
                 "PMK 72/PMK.03/2023"),
                ("Metode garis lurus dan saldo menurun", "UU PPh Pasal 11"),
            ]),
            ("Sanksi Administrasi", [
                ("Denda telat lapor: SPT Masa PPN Rp100.000; SPT Masa lainnya "
                 "Rp100.000; SPT Tahunan Badan Rp1.000.000; SPT Tahunan OP Rp100.000",
                 "Pasal 7 UU KUP jo. UU HPP"),
                ("Bunga telat setor: suku bunga acuan + 10%, dibagi 12, dikali bulan "
                 "keterlambatan", "UU HPP Pasal 9 ayat (2a)/(2b); PMK 81/2024"),
                ("Bunga kurang bayar 2%/bulan, maksimal 24 bulan",
                 "Pasal 13 ayat (2) UU KUP"),
                ("Pidana tidak menyelenggarakan pembukuan: penjara 6 bulan - 6 tahun "
                 "dan denda 2x - 4x pajak", "Pasal 39 UU KUP"),
            ]),
            ("Tenggat Pelaporan", [
                ("SPT Masa PPN: akhir bulan berikutnya (setor & lapor)",
                 "Pasal 3 ayat (3) huruf b UU KUP"),
                ("PPh 21/23/26/4(2): setor tanggal 10, lapor tanggal 20 bulan "
                 "berikutnya", "Pasal 3 & 9 UU KUP"),
                ("PPh 25: setor tanggal 15 bulan berikutnya", "UU PPh Pasal 25"),
                ("SPT Tahunan Badan: paling lambat 4 bulan setelah akhir tahun "
                 "pajak (30 April)", "Pasal 3 ayat (3) huruf a UU KUP"),
                ("SPT Tahunan OP: paling lambat 3 bulan (31 Maret)",
                 "Pasal 3 ayat (3) huruf a UU KUP"),
            ]),
            ("Standar Akuntansi", [
                ("SAK EMKM - entitas mikro, kecil, menengah: 3 komponen laporan "
                 "(posisi keuangan, laba rugi, catatan atas laporan keuangan)",
                 "Keputusan Ketua DSAK IAI"),
                ("SAK Entitas Privat (SAK EP) - adopsi IFRS for SMEs, berlaku "
                 "efektif 1 Januari 2025", "DSAK IAI"),
                ("SAK Umum / PSAK - 5 komponen laporan + CALK",
                 "PSAK 1; PSAK 2; PSAK 14; PSAK 16; PSAK 46; PSAK 71; PSAK 73"),
            ]),
            ("Kewajiban Pembukuan", [
                ("WP Badan wajib menyelenggarakan pembukuan; OP yang menjalankan "
                 "usaha/praktik bebas wajib pembukuan bila peredaran bruto > Rp4,8 M",
                 "Pasal 28 UU KUP"),
                ("Wajib menyimpan buku, catatan, dan dokumen dasar selama 10 tahun",
                 "Pasal 28 ayat (8) UU KUP; UU No. 8/1997"),
                ("Penghasilan dihitung secara jabatan bila pembukuan tidak "
                 "dipercaya", "Pasal 13 UU KUP"),
            ]),
            ("Bentuk Badan Usaha", [
                ("Perseroan Terbatas", "UU No. 40/2007 jo. UU No. 6/2023"),
                ("Perseroan Perorangan (UMK) - didirikan satu orang WNI",
                 "UU No. 11/2020 jo. UU No. 6/2023; PP No. 8/2021"),
                ("Kriteria UMKM (modal tanpa tanah & bangunan)",
                 "PP No. 7/2021"),
                ("Koperasi", "UU No. 25/1992 jo. UU No. 6/2023"),
            ]),
            ("BPJS & Ketenagakerjaan", [
                ("BPJS Kesehatan 5% dari upah (4% pemberi kerja + 1% pekerja); "
                 "batas atas upah Rp12 juta", "Perpres 64/2020"),
                ("JHT 5,7% (3,7% + 2%); JKM 0,3%; JKK 0,24%-1,74%; JP 3% (2% + 1%)",
                 "PP 44/2015; PP 46/2015"),
                ("Biaya jabatan 5% dari bruto, maksimal Rp500.000/bulan",
                 "PMK 250/PMK.03/2008"),
            ]),
        ]

        for grup, item_list in referensi:
            kartu = w.Card()
            kl = kartu.body()
            g = QLabel(grup)
            g.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {C.PRIMARY}; "
                            "background: transparent;")
            kl.addWidget(g)

            for aturan, dasar in item_list:
                r = QWidget()
                rl = QVBoxLayout(r)
                rl.setContentsMargins(0, 5, 0, 5)
                rl.setSpacing(2)
                a = QLabel(aturan)
                a.setWordWrap(True)
                a.setStyleSheet(f"font-size: {theme.FS_SMALL}px; background: transparent;")
                rl.addWidget(a)
                d = QLabel(f" {dasar}")
                d.setWordWrap(True)
                d.setStyleSheet(f"font-size: {theme.FS_TINY}px; "
                                f"color: {C.PRIMARY_DARK}; font-style: italic; "
                                "background: transparent;")
                rl.addWidget(d)
                kl.addWidget(r)
            lay.addWidget(kartu)

        lay.addWidget(w.InfoBanner(
            "Selalu periksa pembaruan regulasi. Aturan perpajakan dapat berubah, dan "
            "aplikasi ini memuat ketentuan sampai edisi regulasi yang tertera pada "
            "halaman Tentang. Untuk transaksi khusus atau bernilai besar, "
            "konsultasikan dengan konsultan pajak atau Account Representative KPP Anda.",
            "warning", "Catatan penting"))
        lay.addStretch()
        return w.scroll(wadah)

    def _topik_tentang(self) -> QWidget:
        wadah = QWidget()
        lay = QVBoxLayout(wadah)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(14)

        j = QLabel("Tentang Aplikasi")
        j.setStyleSheet("font-size: 20px; font-weight: 700; background: transparent;")
        lay.addWidget(j)

        kartu = w.Card()
        kl = kartu.body()
        for label, nilai in [
            ("Nama Aplikasi", config.APP_LONG_NAME),
            ("Versi", f"{config.APP_VERSION} ({config.APP_BUILD})"),
            ("Edisi", config.APP_EDITION),
            ("Penerbit", config.APP_PUBLISHER),
            ("Mode Basis Data", "SQLite lokal - tidak ada koneksi internet"),
            ("Lokasi Data", str(config.DATA_DIR)),
        ]:
            b = QHBoxLayout()
            lb = QLabel(label)
            lb.setFixedWidth(150)
            lb.setStyleSheet(f"font-size: {theme.FS_SMALL}px; font-weight: 600; "
                             f"color: {C.TEXT_MUTED}; background: transparent;")
            b.addWidget(lb)
            v = QLabel(str(nilai))
            v.setWordWrap(True)
            v.setTextInteractionFlags(Qt.TextSelectableByMouse)
            v.setStyleSheet(f"font-size: {theme.FS_BODY}px; background: transparent;")
            b.addWidget(v, 1)
            kl.addLayout(b)
        lay.addWidget(kartu)

        lay.addWidget(w.HelpPanel(
            "Pernyataan Penggunaan",
            "Aplikasi ini dirancang untuk membantu administrasi pembukuan dan "
            "estimasi perpajakan bagi usaha mikro, kecil, menengah, hingga "
            "perseroan terbatas di Indonesia.\n\n"
            "Aplikasi membantu menyusun pembukuan berpasangan, menghasilkan laporan "
            "keuangan sesuai standar akuntansi, menghitung pajak berdasarkan "
            "ketentuan yang berlaku, serta menganalisis kesehatan keuangan usaha.\n\n"
            "Namun perlu dipahami: aplikasi TIDAK menggantikan pertimbangan "
            "profesional. Transaksi yang bersifat khusus, fasilitas perpajakan "
            "tertentu, industri dengan perlakuan khusus, serta interpretasi atas "
            "regulasi tetap perlu diverifikasi sesuai fakta dan ketentuan terbaru "
            "sebaiknya dengan bantuan konsultan pajak atau akuntan bersertifikat.",
            ""))

        lay.addWidget(w.HelpPanel(
            "Keamanan Data",
            "• Seluruh data disimpan di komputer Anda sendiri dalam berkas SQLite.\n"
            "• Tidak ada data yang dikirim ke server manapun.\n"
            "• Password disimpan dalam bentuk hash PBKDF2-HMAC-SHA256 dengan "
            "480.000 iterasi dan salt acak - tidak dapat dibalik menjadi password "
            "asli.\n"
            "• Setiap aktivitas penting dicatat pada jejak audit.\n"
            "• Disarankan membuat cadangan berkala dan menyimpannya di lokasi lain.",
            ""))

        lay.addStretch()
        return w.scroll(wadah)
