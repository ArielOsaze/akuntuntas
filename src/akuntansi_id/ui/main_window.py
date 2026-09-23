"""
AkunTuntas - Jendela Utama & Navigasi
======================================
Struktur:
  • Sidebar navigasi kiri dengan pengelompokan menu
  • Area konten di kanan (QStackedWidget)
  • Status bar menampilkan perusahaan aktif, tahun pajak, dan status keseimbangan

Konteks aplikasi (AppContext) dibagikan ke seluruh halaman:
  company_id, company, tahun, user_id, username, role, beginner
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QStackedWidget, QFrame, QScrollArea, QStatusBar, QMessageBox, QApplication,
    QLineEdit,
)

from .. import config, services
from ..core import accounting as acc
from ..core import license as LIS
from ..core import security as sec
from . import theme
from .theme import C
from . import icons
from . import widgets as w
from .pages.dashboard import DashboardPage
from .pages.analisis import AnalisisPage
from .pages.transaksi import JurnalPage
from .pages.penjualan import PenjualanLengkapPage
from .pages.pembelian import PembelianLengkapPage
from .pages.laporan import LaporanPage
from .pages.pajak import PajakPage
from .pages.pajak_lanjutan import PajakLanjutanPage
from .pages.aset import AsetPage, PayrollPage
from .pages.coa_page import CoaPage, PerusahaanPage
from .pages.pengaturan import PengaturanPage, ChecklistPage, BantuanPage
from .pages.kontrak_page import KontrakPage
from .pages.mitra import MitraPage
from .pages.produk import ProdukPage
from .pages.biaya_bank import BiayaPage, BankPage
from .pages.tata_kelola import (PenggunaPage, AuditPage, RecycleBinPage,
                                ImporMassalPage, PencarianPage)
from .pages.entitas import (DimensiPage, KonsolidasiPage, PeriodePage, LanPage)


# ==========================================================================
# KONTEKS APLIKASI
# ==========================================================================
@dataclass
class AppContext:
    company_id: Optional[int] = None
    company: object = None
    tahun: int = config.DEFAULT_TAX_YEAR
    user_id: Optional[int] = None
    username: str = ""
    full_name: str = ""
    role: str = "owner"
    beginner: bool = True
    # Lisensi yang sedang aktif. Dipakai untuk menentukan fitur mana yang
    # boleh dibuka sesuai paket yang dibeli.
    lisensi: object = None

    def muat_perusahaan(self):
        perusahaan = services.list_companies()
        if perusahaan:
            self.company_id = perusahaan[0]["id"]
            self.company = services.get_company(self.company_id)


# ==========================================================================
# SIDEBAR
# ==========================================================================
class Sidebar(QFrame):
    navigasi = Signal(str)

    # Kode menu yang disembunyikan bila bentuk badan usaha tidak memakainya.
    # Diisi ulang untuk setiap jendela; disimpan sebagai atribut instance
    # supaya pengaturan satu jendela tidak memengaruhi jendela lain.
    # Setiap kelompok berisi anak yang benar-benar satu kesatuan:
    #  - Transaksi Penjualan : dokumen penjualan saja
    #  - Transaksi Pembelian : dokumen pembelian saja
    #  - Buku & Kas          : pencatatan jurnal, biaya, dan kas/bank
    #  - Data Usaha          : data induk yang dipakai transaksi
    #  - Perpajakan          : perhitungan dan pelaporan pajak
    #  - Laporan             : laporan keuangan
    #  - Tata Kelola         : pengguna, jejak, dan pemulihan data
    #  - Pengaturan          : setelan aplikasi dan profil perusahaan
    MENU = [
        ("UTAMA", [
            ("dashboard", "Dashboard", "dashboard"),
            ("analisis", "Analisis Keuangan", "analisis"),
            ("pencarian", "Pencarian Global", "pencarian"),
        ]),
        ("TRANSAKSI PENJUALAN", [
            ("penjualan", "Penjualan", "penjualan"),
        ]),
        ("TRANSAKSI PEMBELIAN", [
            ("pembelian", "Pembelian", "pembelian"),
        ]),
        ("BUKU & KAS", [
            ("jurnal", "Jurnal Umum", "jurnal"),
            ("biaya", "Biaya & Pengeluaran", "biaya"),
            ("bank", "Kas & Bank", "bank"),
        ]),
        ("DATA USAHA", [
            ("mitra", "Pelanggan & Pemasok", "mitra"),
            ("kontrak", "Kontrak", "kontrak"),
            ("produk", "Produk & Persediaan", "produk"),
            ("aset", "Aset Tetap", "aset"),
            ("payroll", "Payroll", "payroll"),
        ]),
        ("PERPAJAKAN", [
            ("pajak", "Pajak & SPT", "pajak"),
            ("pajak_lanjutan", "Pajak Lanjutan", "pajak"),
            ("checklist", "Checklist Kepatuhan", "checklist"),
        ]),
        ("LAPORAN", [
            ("laporan", "Laporan Keuangan", "laporan"),
        ]),
        ("AKUNTANSI LANJUTAN", [
            ("dimensi", "Dimensi & Biaya", "dimensi"),
            ("periode", "Tutup Buku", "periode"),
            ("konsolidasi", "Konsolidasi Grup", "konsolidasi"),
        ]),
        ("TATA KELOLA", [
            ("pengguna", "Pengguna & Akses", "pengguna"),
            ("audit", "Log Audit", "audit"),
            ("recycle", "Keranjang Sampah", "recycle"),
            ("impor", "Impor Data Massal", "impor"),
        ]),
        ("PENGATURAN", [
            ("coa", "Bagan Akun", "coa"),
            ("perusahaan", "Data Perusahaan", "perusahaan"),
            ("lan", "LAN & Cadangan", "lan"),
            ("pengaturan", "Pengaturan", "pengaturan"),
            ("bantuan", "Panduan & Aturan", "bantuan"),
        ]),
    ]

    # Kelompok yang boleh dibuka-tutup. Kelompok lain selalu terbuka agar
    # menu yang sering dipakai tidak perlu diklik dua kali.
    KELOMPOK_LIPAT = {
        "TRANSAKSI PENJUALAN", "TRANSAKSI PEMBELIAN", "BUKU & KAS",
        "DATA USAHA", "PERPAJAKAN", "LAPORAN", "AKUNTANSI LANJUTAN",
        "TATA KELOLA", "PENGATURAN",
    }

    def __init__(self, parent=None, lisensi=None):
        super().__init__(parent)
        # Lisensi dipakai untuk menentukan fitur mana yang ditampilkan.
        self.lisensi = lisensi
        # Kode menu yang disembunyikan. Dibuat per jendela supaya pengaturan
        # satu jendela tidak memengaruhi jendela lain.
        self.sembunyikan: set = set()
        # Lebar dihitung dari menu terlebar ("Biaya & Pengeluaran") pada
        # huruf 12 px: tombol 275 + margin isi 18 + margin wadah 9 +
        # scrollbar 11 = 313 px, dibulatkan ke atas.
        self.setFixedWidth(320)
        theme.latar(self, f"background: {C.SIDEBAR_BG}; border: none;")
        self.tombol: dict[str, QPushButton] = {}
        self._ikon: dict[str, str] = {}
        self._grup: dict = {}
        # Menandai bahwa pemuatan pilihan buka/tutup awal sudah selesai.
        self._siap = False
        self.aktif: Optional[str] = None

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # --- logo
        kepala = QWidget()
        theme.latar(kepala, f"background: {C.SIDEBAR_BG};")
        kl = QVBoxLayout(kepala)
        kl.setContentsMargins(18, 20, 18, 14)
        kl.setSpacing(2)

        baris = QHBoxLayout()
        baris.setSpacing(10)
        ikon = w.logo_label(28)
        baris.addWidget(ikon)
        teks = QLabel("AkunTuntas")
        teks.setStyleSheet("font-size: 16px; font-weight: 800; color: white; "
                           "background: transparent; letter-spacing: -0.2px;")
        teks.setMinimumWidth(teks.fontMetrics().horizontalAdvance("AkunTuntas") + 6)
        baris.addWidget(teks, 0)
        baris.addStretch()
        kl.addLayout(baris)

        v = QLabel(config.APP_EDITION)
        v.setStyleSheet(f"font-size: 10px; color: {C.SIDEBAR_SECTION}; "
                        "background: transparent; padding-left: 38px;")
        kl.addWidget(v)
        lay.addWidget(kepala)

        # --- pencarian menu: mempercepat akses pada daftar menu yang panjang
        cari_kotak = QWidget()
        theme.latar(cari_kotak, f"background: {C.SIDEBAR_BG};")
        ckl = QVBoxLayout(cari_kotak)
        ckl.setContentsMargins(14, 0, 14, 10)
        ckl.setSpacing(0)
        self.inp_cari = QLineEdit()
        self.inp_cari.setPlaceholderText("Cari menu")
        self.inp_cari.setClearButtonEnabled(True)
        self.inp_cari.setMinimumHeight(32)
        self.inp_cari.setStyleSheet(
            f"QLineEdit {{ background: {C.SIDEBAR_HOVER}; color: white; "
            f"border: 1px solid {C.SIDEBAR_HOVER}; border-radius: 7px; "
            "padding: 5px 9px; font-size: 12px; }"
            f"QLineEdit:focus {{ border: 1px solid {C.SIDEBAR_TEXT}; }}"
            f"QLineEdit::placeholder {{ color: {C.SIDEBAR_SECTION}; }}")
        self.inp_cari.textChanged.connect(self._saring_menu)
        ckl.addWidget(self.inp_cari)
        lay.addWidget(cari_kotak)

        lay.addWidget(self._garis())

        # --- daftar menu (scrollable)
        area = QScrollArea()
        area.setObjectName("SidebarScroll")
        area.setWidgetResizable(True)
        area.setFrameShape(QFrame.NoFrame)
        area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        area.setStyleSheet(f"QScrollArea {{ background: {C.SIDEBAR_BG}; border: none; }}"
                           f"QScrollArea > QWidget > QWidget "
                           f"{{ background: {C.SIDEBAR_BG}; }}")

        isi = QWidget()
        theme.latar(isi, f"background: {C.SIDEBAR_BG};")
        il = QVBoxLayout(isi)
        il.setContentsMargins(9, 6, 9, 8)
        il.setSpacing(1)
        self._isi_menu = il

        for seksi, item_list in self.MENU:
            if seksi in self.KELOMPOK_LIPAT:
                self._buat_kelompok_lipat(il, seksi, item_list)
            else:
                s = QLabel(seksi)
                s.setStyleSheet(
                    f"color: {C.SIDEBAR_SECTION}; font-size: 10px; font-weight: 800; "
                    "letter-spacing: 0.8px; background: transparent; "
                    "padding: 13px 10px 4px 10px;")
                il.addWidget(s)
                for kode, nama, nama_ikon in item_list:
                    self._buat_tombol(il, kode, nama, nama_ikon)

        il.addStretch()
        area.setWidget(isi)
        lay.addWidget(area, 1)

        # terapkan pilihan buka/tutup terakhir setelah semua kelompok dibuat
        self._muat_lipatan()

        # --- bagian bawah: info pengguna
        lay.addWidget(self._garis())
        kaki = QWidget()
        theme.latar(kaki, f"background: {C.SIDEBAR_BG};")
        fl = QVBoxLayout(kaki)
        fl.setContentsMargins(16, 11, 16, 13)
        fl.setSpacing(5)

        self.lbl_pengguna = QLabel("")
        self.lbl_pengguna.setStyleSheet("color: white; font-size: 12px; "
                                        "font-weight: 700; background: transparent;")
        fl.addWidget(self.lbl_pengguna)

        self.lbl_peran = QLabel("")
        self.lbl_peran.setStyleSheet(f"color: {C.SIDEBAR_SECTION}; font-size: 10px; "
                                     "background: transparent;")
        fl.addWidget(self.lbl_peran)

        b_keluar = QPushButton("Keluar Akun")
        b_keluar.setObjectName("NavButton")
        b_keluar.setCursor(Qt.PointingHandCursor)
        b_keluar.setIcon(icons.ikon("keluar", C.SIDEBAR_TEXT, 18))
        b_keluar.setIconSize(QSize(18, 18))
        b_keluar.setToolTip("Keluar dari akun ini dan kembali ke halaman masuk")
        b_keluar.clicked.connect(lambda: self.navigasi.emit("logout"))
        fl.addWidget(b_keluar)
        lay.addWidget(kaki)

    def _isi_kelompok(self, wadah) -> list:
        """Tombol menu yang ada di dalam sebuah kelompok."""
        return [b for b in self.tombol.values() if wadah.isAncestorOf(b)]

    def _kelompok_punya_isi(self, wadah) -> bool:
        """
        Apakah kelompok ini masih punya menu yang boleh tampil.

        Dipakai untuk memutuskan judul kelompok ikut disembunyikan atau tidak.

        Pemeriksaan memakai isHidden(), bukan isVisible(). isVisible() ikut
        keadaan induknya, sehingga saat wadah kelompok tertutup yang memang
        keadaan awal semua kelompok seluruh isinya terbaca tidak terlihat,
        kelompok dianggap kosong, lalu judulnya ikut disembunyikan. Akibatnya
        kelompok itu hilang dari sidebar dan tidak bisa dibuka lagi.
        """
        for b in self._isi_kelompok(wadah):
            kode = next((k for k, t in self.tombol.items() if t is b), None)
            if kode is not None and kode not in self.sembunyikan:
                return True
        return False

    def _saring_menu(self, teks: str):
        """
        Tampilkan hanya menu yang cocok dengan kata kunci pencarian.

        Kelompok yang punya menu cocok dibuka otomatis supaya hasilnya
        langsung terlihat; kelompok tanpa hasil disembunyikan sementara.
        Pilihan buka/tutup milik pengguna tidak diubah oleh pencarian, dan
        saat kata kunci dikosongkan sidebar kembali ke keadaan semula.
        """
        kunci = teks.strip().lower()
        for kode, tombol in self.tombol.items():
            if kode in self.sembunyikan:
                tombol.setVisible(False)
                continue
            cocok = not kunci or kunci in tombol.text().replace("&", "").lower()
            tombol.setVisible(cocok)

        for nama, (judul, wadah) in self._grup.items():
            ada_menu = self._kelompok_punya_isi(wadah)
            if not kunci:
                # pencarian selesai: kembalikan kelompok ke pilihan pengguna
                judul.setVisible(ada_menu)
                buka = judul.isChecked()
                wadah.setVisible(buka and ada_menu)
                continue
            # saat mencari: hanya kelompok yang punya hasil yang tampil
            ada_hasil = any(b.isHidden() is False for b in self._isi_kelompok(wadah))
            judul.setVisible(ada_menu and ada_hasil)
            wadah.setVisible(ada_hasil)

        # judul seksi biasa (di luar kelompok lipat) ikut menyesuaikan
        for lbl in self.findChildren(QLabel):
            teks_lbl = lbl.text().strip().upper()
            for seksi, item_list in self.MENU:
                if seksi in self.KELOMPOK_LIPAT or teks_lbl != seksi:
                    continue
                if kunci:
                    ada = any(not self.tombol[k].isHidden()
                              for k, _, _ in item_list if k in self.tombol)
                else:
                    ada = any(k not in self.sembunyikan for k, _, _ in item_list)
                lbl.setVisible(ada)

    def terapkan_bentuk(self, bentuk: str):
        """
        Sembunyikan menu yang tidak dipakai bentuk badan usaha tertentu.

        Orang pribadi tidak memakai konsolidasi maupun payroll karyawan;
        menampilkan menu itu membuat antarmuka terasa penuh oleh fitur yang
        tidak akan pernah dipakai.
        """
        self.sembunyikan = config.fitur_tidak_relevan(bentuk)

        # Halaman yang termasuk fitur lanjutan hanya ditampilkan pada paket
        # Enterprise. Menyembunyikannya lebih baik daripada menampilkan
        # tombol yang bila diklik hanya memunculkan penolakan.
        from . import batas_paket
        for kode in batas_paket.HALAMAN_ENTERPRISE:
            if not batas_paket.boleh_buka(self.lisensi, kode):
                self.sembunyikan.add(kode)

        for kode, tombol in self.tombol.items():
            tombol.setVisible(kode not in self.sembunyikan)

        # Kelompok yang seluruh isinya disembunyikan ikut disembunyikan.
        # Pemeriksaan memakai daftar menu, bukan isVisible() anak, karena
        # isVisible() ikut keadaan wadah yang sedang tertutup sehingga semua
        # kelompok akan terbaca kosong dan judulnya ikut hilang.
        #
        # Isi kelompok ditampilkan berdasarkan pilihan pengguna saja
        # (judul.isChecked()). Keadaan judul tidak dipakai di sini: fungsi ini
        # berjalan saat jendela belum tampil, dan pada saat itu setiap widget
        # masih terbaca tidak terlihat. Memakai isVisible() membuat semua
        # kelompok yang sudah dibuka kehilangan isinya meski panahnya
        # menunjukkan terbuka.
        for nama, (judul, wadah) in self._grup.items():
            punya_isi = self._kelompok_punya_isi(wadah)
            judul.setVisible(punya_isi)
            wadah.setVisible(punya_isi and judul.isChecked())

        # judul seksi biasa (di luar kelompok lipat)
        for lbl in self.findChildren(QLabel):
            teks = lbl.text().strip().upper()
            for seksi, item_list in self.MENU:
                if seksi in self.KELOMPOK_LIPAT or teks != seksi:
                    continue
                ada = any(k not in self.sembunyikan
                          for k, _, _ in item_list)
                lbl.setVisible(ada)

    def _garis(self) -> QFrame:
        f = QFrame()
        f.setFixedHeight(1)
        theme.latar(f, f"background: {C.SIDEBAR_HOVER}; border: none;")
        return f

    def _buat_tombol(self, induk_lay, kode: str, nama: str, nama_ikon: str):
        """Buat satu tombol menu di dalam tata letak induk."""
        # "&&" membuat Qt menampilkan satu "&" apa adanya; tanpa itu tanda &
        # dibaca sebagai penanda tombol pintasan dan hilang, menyisakan
        # garis bawah pada nama menu.
        b = QPushButton(nama.replace('&', '&&'))
        b.setObjectName("NavButton")
        b.setCursor(Qt.PointingHandCursor)
        b.setMinimumHeight(34)
        # checkable agar menu yang sedang dibuka dapat ditandai aktif oleh
        # stylesheet (:checked). autoExclusive tidak dipakai: sifat itu hanya
        # berlaku antar tombol yang satu induk, sedangkan menu tersebar di
        # beberapa kelompok sehingga penandaan aktifnya diatur manual.
        b.setCheckable(True)
        b.setIcon(icons.ikon(nama_ikon, C.SIDEBAR_TEXT, 16))
        b.setIconSize(QSize(16, 16))
        b.clicked.connect(lambda _, k=kode: self.navigasi.emit(k))
        induk_lay.addWidget(b)
        self.tombol[kode] = b
        self._ikon[kode] = nama_ikon
        return b

    def _buat_kelompok_lipat(self, induk_lay, seksi: str, item_list: list):
        """
        Buat kelompok menu yang dapat dibuka dan ditutup.

        Judul kelompok menjadi tombol dengan ikon panah; isinya disimpan
        dalam wadah tersendiri sehingga dapat disembunyikan tanpa
        mengganggu tata letak kelompok lain.

        Kelompok berisi satu menu tidak perlu dilipat: judulnya cukup
        ditampilkan sebagai judul bagian, lalu menunya langsung terlihat.
        """
        if len(item_list) <= 1:
            s = QLabel(seksi)
            s.setStyleSheet(
                f"color: {C.SIDEBAR_SECTION}; font-size: 10px; font-weight: 800; "
                "letter-spacing: 0.8px; background: transparent; "
                "padding: 14px 10px 5px 10px;")
            induk_lay.addWidget(s)
            for kode, nama, nama_ikon in item_list:
                self._buat_tombol(induk_lay, kode, nama, nama_ikon)
            return

        # "&&" membuat Qt menampilkan satu "&" apa adanya. Tanpa itu Qt
        # membacanya sebagai penanda tombol pintasan, lalu mengganti huruf
        # berikutnya dengan garis bawah sehingga judul tampak memakai "_".
        judul = QPushButton(seksi.replace('&', '&&'))
        judul.setObjectName("NavGroup")
        judul.setCursor(Qt.PointingHandCursor)
        judul.setMinimumHeight(32)
        judul.setCheckable(True)
        induk_lay.addWidget(judul)

        wadah = QWidget()
        theme.latar(wadah, "background: transparent;")
        wl = QVBoxLayout(wadah)
        wl.setContentsMargins(9, 1, 0, 3)
        wl.setSpacing(2)
        for kode, nama, nama_ikon in item_list:
            self._buat_tombol(wl, kode, nama, nama_ikon)
        # Mulai tersembunyi; pilihan buka/tutup diterapkan di _muat_lipatan()
        # supaya isi kelompok tidak sempat terlihat saat aplikasi dibuka.
        wadah.setVisible(False)
        induk_lay.addWidget(wadah)

        self._grup[seksi] = (judul, wadah)
        judul.toggled.connect(
            lambda terbuka, s=seksi: self._lipat(s, terbuka))

    def _lipat(self, seksi: str, terbuka: bool):
        """Tampilkan atau sembunyikan isi kelompok, lalu simpan pilihannya."""
        pasangan = self._grup.get(seksi)
        if pasangan is None:
            return
        judul, wadah = pasangan
        wadah.setVisible(terbuka)
        self._pasang_panah(judul, terbuka)
        # Jangan simpan saat pemuatan awal: pilihan lama belum selesai
        # diterapkan sehingga bisa tertimpa nilai bawaan.
        if self._siap:
            self.simpan_lipatan()

    def _pasang_panah(self, judul: QPushButton, terbuka: bool):
        warna = C.SIDEBAR_TEXT_ACTIVE if terbuka else C.SIDEBAR_SECTION
        nama = "panah_bawah" if terbuka else "panah_kanan"
        judul.setIcon(icons.ikon(nama, warna, 14))
        judul.setIconSize(QSize(14, 14))

    def _muat_lipatan(self):
        """
        Baca pilihan buka/tutup terakhir pengguna.

        Bila pengguna belum pernah memilih, semua kelompok ditutup supaya
        daftar menu tampil ringkas. Kategori dibuka dengan satu klik.

        Penyesuaian dilakukan langsung ke wadahnya, bukan lewat setChecked(),
        karena tombol yang nilainya sudah False tidak memancarkan sinyal
        toggled sehingga isinya tidak ikut tersembunyi.
        """
        tersimpan = None
        try:
            from .. import db
            baris = db.q1("SELECT value FROM settings WHERE key=?",
                          ("sidebar_lipat",))
            if baris and baris["value"] is not None:
                tersimpan = str(baris["value"])
        except Exception:
            pass

        terbuka = set()
        if tersimpan:
            terbuka = {n.strip() for n in tersimpan.split(",") if n.strip()}

        for nama, (judul, wadah) in self._grup.items():
            buka = nama in terbuka
            # blokir sinyal agar tidak memicu penyimpanan saat pemuatan
            judul.blockSignals(True)
            judul.setChecked(buka)
            judul.blockSignals(False)
            wadah.setVisible(buka)
            self._pasang_panah(judul, buka)
        self._siap = True

    def simpan_lipatan(self):
        """Simpan kelompok mana saja yang sedang terbuka."""
        try:
            from .. import db
            terbuka = [nama for nama, (judul, _) in self._grup.items()
                       if judul.isChecked()]
            db.ex("INSERT INTO settings(key,value) VALUES('sidebar_lipat',?) "
                  "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                  (",".join(terbuka),))
        except Exception:
            pass

    def buka_kelompok(self, kode: str):
        """Pastikan kelompok yang memuat menu ini terbuka."""
        for nama, (judul, wadah) in self._grup.items():
            if not judul.isEnabled():
                continue
            for i in range(wadah.layout().count()):
                it = wadah.layout().itemAt(i)
                wdg = it.widget() if it else None
                if wdg is not None and self.tombol.get(kode) is wdg:
                    if not judul.isChecked():
                        judul.setChecked(True)
                    return

    def set_aktif(self, kode: str):
        """
        Tandai satu menu sebagai aktif dan lepaskan tanda dari yang lain.

        autoExclusive Qt hanya berlaku antar tombol yang satu induk, sedangkan
        menu tersebar di beberapa kelompok dengan induk berbeda. Karena itu
        penandaan dilakukan manual untuk seluruh tombol agar tidak ada dua
        menu yang tampil aktif bersamaan.
        """
        for k, b in self.tombol.items():
            aktif = (k == kode)
            if b.isChecked() != aktif:
                b.blockSignals(True)
                b.setChecked(aktif)
                b.blockSignals(False)
            nama_ikon = self._ikon.get(k, "dokumen")
            warna = C.SIDEBAR_TEXT_ACTIVE if aktif else C.SIDEBAR_TEXT
            b.setIcon(icons.ikon(nama_ikon, warna, 18))
        self.aktif = kode

    def set_pengguna(self, nama: str, peran: str):
        self.lbl_pengguna.setText(nama)
        self.lbl_peran.setText(peran)


# ==========================================================================
# JENDELA UTAMA
# ==========================================================================
class PetaHalaman(dict):
    """
    Daftar halaman yang isinya dibuat saat diakses.

    Membuat seluruh halaman sekaligus saat aplikasi dibuka memakan sekitar
    tiga detik, padahal saat itu hanya satu halaman yang ditampilkan.

    Daftar ini tetap mengenali seluruh kode halaman supaya penelusuran
    seperti "semua halaman" atau "apakah halaman ini ada" tetap berjalan
    benar, tetapi widgetnya baru dibuat ketika benar-benar diminta.
    """

    def __init__(self, jendela):
        super().__init__()
        self._jendela = jendela

    def __missing__(self, kode):
        halaman = self._jendela._buat_halaman(kode)
        if halaman is None:
            raise KeyError(kode)
        return halaman

    def __contains__(self, kode) -> bool:
        return kode in self._jendela._pabrik

    def __iter__(self):
        return iter(self._jendela._pabrik)

    def __len__(self) -> int:
        return len(self._jendela._pabrik)

    def keys(self):
        return self._jendela._pabrik.keys()

    def values(self):
        return [self[kode] for kode in self._jendela._pabrik]

    def items(self):
        return [(kode, self[kode]) for kode in self._jendela._pabrik]

    def get(self, kode, bawaan=None):
        if kode in self._jendela._pabrik:
            return self[kode]
        return bawaan


class MainWindow(QMainWindow):
    # Dipancarkan saat pengguna keluar dari akunnya. Jendela pembungkus
    # memakainya untuk kembali ke halaman masuk tanpa menutup aplikasi.
    kembali_ke_login = Signal()

    def __init__(self, hasil_login: sec.LoginResult, parent=None,
                 lisensi=None):
        super().__init__(parent)
        self.ctx = AppContext(
            user_id=hasil_login.user_id,
            username=hasil_login.username,
            full_name=hasil_login.full_name,
            role=hasil_login.role,
            beginner=(hasil_login.app_mode == "beginner"),
            tahun=datetime.now().year,
            lisensi=lisensi,
        )
        self.ctx.muat_perusahaan()

        self.setWindowTitle(f"{config.APP_LONG_NAME} - {hasil_login.full_name}")
        self.setWindowIcon(w.ikon_aplikasi())
        self.resize(1500, 940)
        self.setMinimumSize(1180, 720)

        pusat = QWidget()
        self.setCentralWidget(pusat)
        lay = QHBoxLayout(pusat)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # sidebar
        self.sidebar = Sidebar(lisensi=lisensi)
        self.sidebar.navigasi.connect(self._navigasi)
        self.sidebar.set_pengguna(
            hasil_login.full_name or hasil_login.username,
            {"owner": "Pemilik", "admin": "Administrator",
             "staff": "Staf", "viewer": "Hanya Lihat"}.get(hasil_login.role,
                                                            hasil_login.role))
        # Sesuaikan menu dengan bentuk badan usaha perusahaan aktif: fitur
        # yang tidak dipakai bentuk itu disembunyikan agar antarmuka bersih.
        if self.ctx.company:
            self.sidebar.terapkan_bentuk(self.ctx.company["bentuk"])
        lay.addWidget(self.sidebar)

        # area konten
        self.stack = QStackedWidget()
        theme.latar(self.stack, f"background: {C.BG};")
        lay.addWidget(self.stack, 1)

        self.halaman = PetaHalaman(self)
        # Catatan revisi data saat tiap halaman terakhir dimuat. Halaman
        # dimuat ulang hanya bila penanda revisi basis data sudah berubah.
        self._halaman_dimuat: dict[str, int] = {}
        # Kode halaman yang sedang tampil.
        self._kode_aktif: str = ""
        self._bangun_halaman()

        # status bar
        self._bangun_status_bar()

        # menu bar
        self._bangun_menu()

        # halaman awal
        self._navigasi("dashboard")

    # ------------------------------------------------------------------
    def _bangun_halaman(self):
        """
        Siapkan daftar halaman, buat isinya saat dibuka.

        Membuat seluruh halaman sekaligus saat aplikasi dibuka memakan
        sekitar tiga detik, padahal saat itu hanya satu halaman yang
        ditampilkan. Halaman karena itu dibuat saat pertama kali dibuka,
        lalu disimpan supaya pembukaan berikutnya seketika.
        """
        self._pabrik = {
            "dashboard": lambda: DashboardPage(self.ctx),
            "analisis": lambda: AnalisisPage(self.ctx),
            "pencarian": lambda: PencarianPage(self.ctx),
            "jurnal": lambda: JurnalPage(self.ctx),
            "penjualan": lambda: PenjualanLengkapPage(self.ctx),
            "pembelian": lambda: PembelianLengkapPage(self.ctx),
            "biaya": lambda: BiayaPage(self.ctx),
            "bank": lambda: BankPage(self.ctx),
            "mitra": lambda: MitraPage(self.ctx),
            "kontrak": lambda: KontrakPage(self.ctx),
            "produk": lambda: ProdukPage(self.ctx),
            "aset": lambda: AsetPage(self.ctx),
            "payroll": lambda: PayrollPage(self.ctx),
            "dimensi": lambda: DimensiPage(self.ctx),
            "periode": lambda: PeriodePage(self.ctx),
            "konsolidasi": lambda: KonsolidasiPage(self.ctx),
            "laporan": lambda: LaporanPage(self.ctx),
            "pajak": lambda: PajakPage(self.ctx),
            "pajak_lanjutan": lambda: PajakLanjutanPage(self.ctx),
            "checklist": lambda: ChecklistPage(self.ctx),
            "pengguna": lambda: PenggunaPage(self.ctx),
            "audit": lambda: AuditPage(self.ctx),
            "recycle": lambda: RecycleBinPage(self.ctx),
            "impor": lambda: ImporMassalPage(self.ctx),
            "coa": lambda: CoaPage(self.ctx),
            "perusahaan": lambda: PerusahaanPage(self.ctx),
            "lan": lambda: LanPage(self.ctx),
            "pengaturan": lambda: PengaturanPage(self.ctx),
            "bantuan": lambda: BantuanPage(self.ctx),
        }

        # Halaman dashboard selalu dibutuhkan lebih dulu, jadi dibuat
        # sekarang supaya jendela langsung terisi saat ditampilkan.
        self.halaman["dashboard"]

    def _buat_halaman(self, kode: str) -> QWidget | None:
        """
        Buat halaman bila belum ada, lalu kembalikan.

        Pembuatan yang gagal tidak menghentikan aplikasi: halaman pengganti
        berisi keterangan kesalahan tetap dapat dibuka supaya pengguna tahu
        masalahnya.

        Halaman yang termasuk fitur lanjutan tidak dibuat bila paket lisensi
        tidak memuatnya. Pemeriksaan di sini menutup jalan masuk selain
        sidebar, misalnya dari pencarian atau dari tombol di halaman lain.
        """
        halaman = dict.get(self.halaman, kode)
        if halaman is not None:
            return halaman

        from . import batas_paket
        if not batas_paket.boleh_buka(self.ctx.lisensi, kode):
            nama = batas_paket.HALAMAN_ENTERPRISE[kode][0]
            halaman = batas_paket.halaman_terkunci(nama)
            dict.__setitem__(self.halaman, kode, halaman)
            self.stack.addWidget(halaman)
            return halaman

        pabrik = self._pabrik.get(kode)
        if pabrik is None:
            return None

        try:
            halaman = pabrik()
        except Exception as e:
            halaman = self._halaman_error(kode, e)

        # sambungkan sinyal pindah halaman bila ada
        if hasattr(halaman, "pindah_halaman"):
            halaman.pindah_halaman.connect(self._navigasi)
        if hasattr(halaman, "mode_berubah"):
            halaman.mode_berubah.connect(self._mode_berubah)

        dict.__setitem__(self.halaman, kode, halaman)
        self.stack.addWidget(halaman)
        return halaman

    def _halaman_error(self, kode: str, error: Exception) -> QWidget:
        wdg = QWidget()
        lay = QVBoxLayout(wdg)
        lay.setContentsMargins(40, 40, 40, 40)
        lay.setSpacing(14)
        lay.addStretch()
        kartu = w.Card(padding=30)
        kl = kartu.body()
        j = QLabel(f"Halaman '{kode}' tidak dapat dimuat")
        j.setStyleSheet("font-size: 18px; font-weight: 700; background: transparent;")
        kl.addWidget(j)
        t = QLabel(f"Terjadi kesalahan teknis:\n\n{type(error).__name__}: {error}\n\n"
                   "Silakan hubungi pengembang dengan menyertakan pesan di atas.")
        t.setWordWrap(True)
        t.setTextInteractionFlags(Qt.TextSelectableByMouse)
        t.setStyleSheet(f"font-size: {theme.FS_SMALL}px; color: {C.DANGER}; "
                        "background: transparent;")
        kl.addWidget(t)
        lay.addWidget(kartu)
        lay.addStretch()
        return wdg

    def _bangun_status_bar(self):
        sb = QStatusBar()
        self.setStatusBar(sb)

        self.lbl_perusahaan = QLabel("")
        self.lbl_perusahaan.setStyleSheet(f"font-size: {theme.FS_TINY}px; "
                                          f"color: {C.TEXT_MUTED}; padding-left: 8px;")
        sb.addWidget(self.lbl_perusahaan)

        self.lbl_keseimbangan = QLabel("")
        self.lbl_keseimbangan.setStyleSheet(f"font-size: {theme.FS_TINY}px; "
                                            "padding-right: 12px;")
        sb.addPermanentWidget(self.lbl_keseimbangan)

        self.lbl_mode = QLabel("")
        self.lbl_mode.setStyleSheet(f"font-size: {theme.FS_TINY}px; "
                                    f"color: {C.TEXT_MUTED}; padding-right: 12px;")
        sb.addPermanentWidget(self.lbl_mode)

        self._refresh_status()

    def _refresh_status(self):
        if self.ctx.company:
            comp = self.ctx.company
            self.lbl_perusahaan.setText(
                f"{comp['nama']} · {config.ENTITY_TYPES.get(comp['bentuk'], {}).get('singkat', comp['bentuk'])} "
                f"· Tahun pajak {self.ctx.tahun}")
            try:
                cek = acc.total_neraca_saldo(self.ctx.company_id, self.ctx.tahun)
                if cek["seimbang"]:
                    self.lbl_keseimbangan.setText("Pembukuan seimbang")
                    self.lbl_keseimbangan.setStyleSheet(
                        f"font-size: {theme.FS_TINY}px; color: {C.SUCCESS}; "
                        "font-weight: 600; padding-right: 12px;")
                else:
                    self.lbl_keseimbangan.setText(
                        f"Tidak seimbang - selisih {theme.money(cek['selisih'])}")
                    self.lbl_keseimbangan.setStyleSheet(
                        f"font-size: {theme.FS_TINY}px; color: {C.DANGER}; "
                        "font-weight: 700; padding-right: 12px;")
            except Exception:
                self.lbl_keseimbangan.setText("")
        else:
            self.lbl_perusahaan.setText("Belum ada perusahaan aktif")

        self.lbl_mode.setText(
            "Mode: Pemula" if self.ctx.beginner else "Mode: Ahli")

    def _bangun_menu(self):
        mb = self.menuBar()
        mb.setNativeMenuBar(False)

        def aksi(menu, teks, slot, pintasan=None, ikon=None):
            # "&&" agar tanda & tampil apa adanya pada item menu.
            # Menu memakai teks saja: ikon kecil di daftar menu sulit
            # dikenali dan membuat barisnya terlihat penuh. Parameter `ikon`
            # tetap diterima agar pemanggilan lama tidak perlu diubah.
            a = QAction(teks.replace("&", "&&"), self)
            if pintasan:
                a.setShortcut(QKeySequence(pintasan))
            a.triggered.connect(slot)
            menu.addAction(a)
            return a

        # ---------------------------------------------------------- Berkas
        m_berkas = mb.addMenu("&Berkas")
        aksi(m_berkas, "Perusahaan Baru", lambda: self._navigasi("perusahaan"),
             "Ctrl+N", "tambah")
        aksi(m_berkas, "Pilih Perusahaan Aktif", self._pilih_perusahaan,
             "Ctrl+P", "perusahaan")
        m_berkas.addSeparator()
        aksi(m_berkas, "Impor Data (CSV)", lambda: self._navigasi("impor"),
             "Ctrl+I", "impor")
        aksi(m_berkas, "Ekspor Laporan", lambda: self._navigasi("laporan"),
             "Ctrl+E", "ekspor")
        m_berkas.addSeparator()
        aksi(m_berkas, "Buat Cadangan Data", self._backup_cepat,
             "Ctrl+B", "simpan")
        aksi(m_berkas, "Buka Folder Data", self._buka_folder_data,
             None, "buka")
        m_berkas.addSeparator()
        aksi(m_berkas, "Tutup Aplikasi", self.close, "Ctrl+Q", "keluar")

        # -------------------------------------------------------- Tampilan
        m_tampilan = mb.addMenu("&Tampilan")
        self.a_pemula = QAction("Mode Pemula (panel penjelasan)", self, checkable=True)
        self.a_pemula.setChecked(self.ctx.beginner)
        self.a_pemula.setShortcut(QKeySequence("Ctrl+M"))
        self.a_pemula.triggered.connect(lambda: self._mode_berubah(
            "beginner" if self.a_pemula.isChecked() else "expert"))
        m_tampilan.addAction(self.a_pemula)
        m_tampilan.addSeparator()
        aksi(m_tampilan, "Muat Ulang Halaman", self._muat_halaman_aktif,
             "F5", "segarkan")
        m_tampilan.addSeparator()
        m_ukuran = m_tampilan.addMenu("Ukuran Teks")
        for label, faktor in (("Normal", 1.0), ("Besar", 1.15), ("Sangat Besar", 1.3)):
            a = QAction(label, self)
            a.triggered.connect(lambda _, f=faktor: self._ubah_ukuran_teks(f))
            m_ukuran.addAction(a)

        # ------------------------------------------------------------ Alat
        m_alat = mb.addMenu("&Alat")
        for nama, kode, ikon, pintasan in [
            ("Jurnal Umum", "jurnal", "jurnal", "Ctrl+J"),
            ("Penjualan", "penjualan", "penjualan", None),
            ("Pembelian", "pembelian", "pembelian", None),
            ("Biaya & Pengeluaran", "biaya", "biaya", None),
            ("Kas & Bank", "bank", "bank", None),
            ("Payroll", "payroll", "payroll", None),
            ("Aset Tetap", "aset", "aset", None),
        ]:
            aksi(m_alat, nama, lambda _, k=kode: self._navigasi(k), pintasan, ikon)
        m_alat.addSeparator()
        aksi(m_alat, "Laporan Keuangan", lambda: self._navigasi("laporan"),
             "Ctrl+L", "laporan")
        aksi(m_alat, "Pajak & SPT", lambda: self._navigasi("pajak"),
             "Ctrl+T", "pajak")
        aksi(m_alat, "Analisis Kesehatan Keuangan", lambda: self._navigasi("analisis"),
             "Ctrl+K", "analisis")
        m_alat.addSeparator()
        aksi(m_alat, "Tutup Buku Periode", lambda: self._navigasi("periode"),
             None, "kalender")

        # --------------------------------------------------------- Bantuan
        m_bantuan = mb.addMenu("&Bantuan")
        aksi(m_bantuan, "Panduan & Referensi Aturan", lambda: self._navigasi("bantuan"),
             "F1", "bantuan")
        aksi(m_bantuan, "Pencarian Global", lambda: self._navigasi("pencarian"),
             "Ctrl+F", "pencarian")
        m_bantuan.addSeparator()
        aksi(m_bantuan, f"Tentang {config.APP_NAME}", self._tentang, None, "info")

    def _tentang(self):
        QMessageBox.about(
            self, f"Tentang {config.APP_NAME}",
            f"<h3>{config.APP_LONG_NAME}</h3>"
            f"<p>Versi {config.APP_VERSION} ({config.APP_BUILD})<br>"
            f"{config.APP_EDITION}</p>"
            f"<p>Aplikasi pembukuan dan perpajakan untuk usaha mikro, kecil, "
            f"menengah, hingga perseroan terbatas di Indonesia.</p>"
            f"<p><b>Data tersimpan lokal:</b> {config.DATA_DIR}<br>"
            f"Tidak ada data yang dikirim ke internet.</p>"
            f"<p style='color:#64748B;font-size:11px'>Aplikasi ini membantu "
            f"administrasi dan estimasi. Transaksi khusus dan interpretasi regulasi "
            f"tetap perlu diverifikasi sesuai fakta dan ketentuan terbaru.</p>")

    def _backup_cepat(self):
        try:
            path = None
            from .. import db
            path = db.create_backup(f"Cadangan cepat oleh {self.ctx.username}")
            QMessageBox.information(self, "Cadangan dibuat",
                                    f"Cadangan tersimpan di:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Gagal membuat cadangan", str(e))

    def _mode_berubah(self, mode: str):
        self.ctx.beginner = (mode == "beginner")
        self.a_pemula.setChecked(self.ctx.beginner)
        self._refresh_status()
        QMessageBox.information(
            self, "Mode diubah",
            f"Mode aplikasi diubah ke "
            f"{'Pemula' if self.ctx.beginner else 'Ahli'}.\n\n"
            "Muat ulang halaman (F5) agar tampilan menyesuaikan.")

    def _muat_halaman_aktif(self):
        halaman = self.stack.currentWidget()
        if hasattr(halaman, "muat"):
            try:
                halaman.muat()
            except Exception as e:
                QMessageBox.warning(self, "Gagal memuat ulang", str(e))
        self._refresh_status()

    def _pilih_perusahaan(self):
        """Ganti perusahaan aktif lewat daftar singkat."""
        from .. import services
        daftar = services.list_companies()
        if not daftar:
            QMessageBox.information(
                self, "Belum ada perusahaan",
                "Belum ada perusahaan terdaftar. Buat perusahaan baru lebih dulu.")
            self._navigasi("perusahaan")
            return
        if len(daftar) == 1:
            QMessageBox.information(
                self, "Perusahaan aktif",
                f"Saat ini hanya ada satu perusahaan:\n\n{daftar[0]['nama']}")
            return

        from PySide6.QtWidgets import QInputDialog
        pilihan = [f"{p['nama']}" for p in daftar]
        kini = next((i for i, p in enumerate(daftar)
                     if p["id"] == self.ctx.company_id), 0)
        nama, ok = QInputDialog.getItem(
            self, "Pilih Perusahaan Aktif",
            "Perusahaan yang dibuka:", pilihan, kini, False)
        if not ok:
            return
        idx = pilihan.index(nama)
        self.ctx.company_id = daftar[idx]["id"]
        self.ctx.company = services.get_company(self.ctx.company_id)
        self._refresh_status()
        self._muat_halaman_aktif()

    def _buka_folder_data(self):
        """Buka folder penyimpanan data di penjelajah berkas Windows."""
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices
        from .. import config
        config.ensure_dirs()
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(config.DATA_DIR)))

    def _ubah_ukuran_teks(self, faktor: float):
        """Perbesar atau perkecil ukuran teks aplikasi."""
        from PySide6.QtGui import QFont
        dasar = QFont(theme.FONT_FAMILY, 10)
        app = QApplication.instance()
        if app is None:
            return
        font = QFont(dasar)
        font.setPointSizeF(max(7.5, 10 * faktor))
        app.setFont(font)
        theme.UKURAN_TEKS = faktor
        app.setStyleSheet(theme.stylesheet())
        self._muat_halaman_aktif()

    # ------------------------------------------------------------------
    def _navigasi(self, kode: str):
        if kode == "logout":
            self._keluar()
            return

        halaman = self._buat_halaman(kode)
        if halaman is None:
            return

        self.stack.setCurrentWidget(halaman)
        self.sidebar.buka_kelompok(kode)
        self.sidebar.set_aktif(kode)

        # Muat data hanya bila perlu, lalu rapikan tampilan.
        #
        # Memuat ulang setiap kali halaman dibuka membuat tampilan dibangun
        # ulang dari nol, padahal datanya belum tentu berubah. Pada halaman
        # dengan banyak keterangan, pekerjaan itu memakan ratusan milidetik
        # sehingga perpindahan menu terasa tersendat.
        #
        # Halaman dimuat ulang hanya bila datanya sudah berubah sejak
        # pemuatan terakhir. Perubahan diketahui dari penanda revisi data,
        # yang dinaikkan setiap ada penyimpanan, penghapusan, atau pemulihan
        # cadangan.
        #
        # Perapian dijalankan setelah pemuatan, bukan sebelumnya, karena
        # memuat data sering membuat label baru (kartu temuan, baris rasio,
        # keterangan simulasi). Label yang baru dibuat belum ikut dirapikan
        # bila perapian dijalankan lebih dulu.
        if hasattr(halaman, "muat") and self._perlu_muat(kode):
            try:
                halaman.muat()
                from .. import db
                self._halaman_dimuat[kode] = db.revisi_data()
            except Exception as e:
                print(f"[{kode}] gagal memuat: {e}")

        self._kode_aktif = kode

        # rapikan label keterangan agar tidak terpotong
        theme.rapikan_label(halaman)

        self._refresh_status()

    def _perlu_muat(self, kode: str) -> bool:
        """
        Apakah halaman ini perlu memuat datanya lagi.

        Halaman dimuat saat pertama kali dibuka, lalu dimuat lagi hanya bila
        isi basis data berubah. Perubahannya diketahui dari penanda revisi
        yang dinaikkan setiap ada penyimpanan atau penghapusan, sehingga
        membuka menu yang sama berulang kali tidak membangun ulang
        tampilannya.
        """
        from .. import db

        terakhir = self._halaman_dimuat.get(kode)
        if terakhir is None:
            return True
        return terakhir != db.revisi_data()

    def tandai_data_berubah(self):
        """Muat ulang halaman yang sedang tampil setelah data berubah."""
        kode = self._kode_aktif
        if kode:
            self._halaman_dimuat.pop(kode, None)

    def _keluar(self):
        """
        Keluar dari akun dan kembali ke halaman login.

        Ini keluar dari akun, bukan menutup aplikasi. Pengguna yang ingin
        menutup aplikasi memakai menu Berkas > Tutup Aplikasi. Membedakan
        keduanya penting: menutup aplikasi berarti harus membukanya lagi dan
        menunggu pemuatan, sedangkan keluar akun cukup satu klik.
        """
        if QMessageBox.question(
                self, "Keluar dari akun",
                f"Keluar dari akun {self.ctx.full_name or self.ctx.username}?\n\n"
                "Pekerjaan yang sudah disimpan tetap aman. Anda akan kembali "
                "ke halaman masuk untuk memakai akun lain.",
                QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return

        try:
            sec.logout(self.ctx.user_id, self.ctx.username)
        except Exception:
            pass

        # Jangan catat logout lagi saat jendela benar-benar ditutup.
        self._sudah_keluar = True
        self.kembali_ke_login.emit()

    def closeEvent(self, event):
        if not getattr(self, "_sudah_keluar", False):
            try:
                sec.logout(self.ctx.user_id, self.ctx.username)
            except Exception:
                pass
        event.accept()


# ==========================================================================
# JENDELA LOGIN (pembungkus alur login  ganti password  pilih mode  utama)
# ==========================================================================
class JendelaAplikasi(QMainWindow):
    """Mengelola alur: lisensi -> login -> (ganti password) -> (mode) -> utama."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(config.APP_LONG_NAME)
        self.resize(1120, 720)
        self.setMinimumSize(920, 620)

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.main_window: Optional[MainWindow] = None
        self.lisensi: Optional[LIS.Lisensi] = None

        self.halaman_login = None

        # Lisensi diperiksa lebih dulu. Tanpa lisensi yang sah, halaman
        # masuk tidak ditampilkan sama sekali.
        #
        # Paket yang dibungkus untuk Microsoft Store memuat mode uji coba,
        # karena peninjau tidak memiliki kunci lisensi berbayar. Mode itu
        # hanya berlaku bila berkas penanda ikut disertakan saat membungkus
        # paket, sehingga build installer biasa tidak terpengaruh.
        from ..core import uji_coba

        sah, alasan, lisensi = LIS.lisensi_sah(config.DATA_DIR)
        if sah:
            self.lisensi = lisensi
            self._siapkan_login()
        elif uji_coba.aktif(config.DATA_DIR):
            self.lisensi = uji_coba.lisensi_uji_coba(config.DATA_DIR)
            self._siapkan_login()
        else:
            self._tampilkan_aktivasi(alasan)

    # ------------------------------------------------------------------
    def _tampilkan_aktivasi(self, alasan: str = ""):
        """Tampilkan layar aktivasi lisensi."""
        from .aktivasi import HalamanAktivasi

        self.halaman_aktivasi = HalamanAktivasi()
        self.halaman_aktivasi.berhasil.connect(self._lisensi_aktif)
        self.stack.addWidget(self.halaman_aktivasi)
        self.stack.setCurrentWidget(self.halaman_aktivasi)

        if alasan:
            self.halaman_aktivasi._tampilkan_kabar(alasan, "bahaya")

    def _lisensi_aktif(self, lisensi):
        """Dipanggil setelah lisensi berhasil diaktifkan."""
        self.lisensi = lisensi
        self._siapkan_login()

    def _siapkan_login(self):
        """Siapkan halaman masuk, sekali saja."""
        if self.halaman_login is not None:
            self.stack.setCurrentWidget(self.halaman_login)
            return

        from .login import LoginPage
        self.halaman_login = LoginPage()
        self.halaman_login.berhasil.connect(self._setelah_login)
        self.stack.addWidget(self.halaman_login)
        self.stack.setCurrentWidget(self.halaman_login)

    def _setelah_login(self, hasil: sec.LoginResult):
        # belum ada perusahaan  tetap ke pemilihan mode dulu
        if hasil.must_change_pw:
            from .login import GantiPasswordWajib
            self.halaman_ganti = GantiPasswordWajib(hasil)
            self.halaman_ganti.selesai.connect(lambda: self._lanjut(hasil))
            self.stack.addWidget(self.halaman_ganti)
            self.stack.setCurrentWidget(self.halaman_ganti)
            return
        self._lanjut(hasil)

    def _lanjut(self, hasil: sec.LoginResult):
        # Tawarkan pilihan mode hanya saat pengguna belum pernah memilih.
        # Sesudah itu mode tersimpan dan dapat diubah dari Pengaturan.
        if hasil.mode_dipilih:
            self._buka_utama(hasil, hasil.app_mode)
            return

        from .login import PilihMode
        self.halaman_mode = PilihMode(hasil)
        self.halaman_mode.selesai.connect(self._mode_dipilih)
        self.stack.addWidget(self.halaman_mode)
        self.stack.setCurrentWidget(self.halaman_mode)

    def _mode_dipilih(self, mode: str):
        """Simpan pilihan mode agar tidak ditanyakan lagi pada login berikutnya."""
        hasil = self.halaman_login.hasil_terakhir
        if hasil and hasil.user_id:
            try:
                sec.update_user_mode(hasil.user_id, mode)
                hasil.app_mode = mode
                hasil.mode_dipilih = True
            except Exception:
                pass
        self._buka_utama(hasil, mode)

    def _buka_utama(self, hasil: sec.LoginResult, mode: str):
        hasil.app_mode = mode
        # Lisensi diberikan saat jendela utama dibuat supaya menu yang
        # tersedia langsung sesuai paket, tanpa sempat menampilkan menu
        # yang seharusnya terkunci.
        self.main_window = MainWindow(hasil, lisensi=self.lisensi)
        self.main_window.kembali_ke_login.connect(self._kembali_ke_login)
        self.setCentralWidget(self.main_window)
        self.main_window.showMaximized()
        self.setWindowTitle(f"{config.APP_LONG_NAME} - {hasil.full_name}")

    def _kembali_ke_login(self):
        """
        Kembalikan aplikasi ke halaman masuk tanpa menutupnya.

        Halaman login dibuat ulang supaya kolom isian dan pesan kesalahan
        dari sesi sebelumnya tidak terbawa, dan nama pengguna terakhir ikut
        terisi otomatis.
        """
        from .login import LoginPage

        self.halaman_login = LoginPage()
        self.halaman_login.berhasil.connect(self._setelah_login)
        self.stack.addWidget(self.halaman_login)
        self.stack.setCurrentWidget(self.halaman_login)
        self.setCentralWidget(self.stack)
        self.showNormal()
        self.resize(1120, 720)
        self.setWindowTitle(config.APP_LONG_NAME)

        # Buang jendela utama lama agar tidak menumpuk di memori.
        if self.main_window is not None:
            self.main_window.deleteLater()
            self.main_window = None
