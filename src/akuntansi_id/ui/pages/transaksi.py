"""
AkunTuntas - Halaman Transaksi
===============================
  • Jurnal Umum   input jurnal manual dengan validasi double-entry
  • Penjualan subledger penjualan + PPN keluaran otomatis
  • Pembelian     - subledger pembelian + PPN masukan otomatis
"""
from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt, Signal, QDate
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit, QDateEdit,
    QPushButton, QDialog, QMessageBox, QFrame, QGridLayout,
)

from ... import config, coa, services
from ...core import accounting as acc
from .. import theme
from .. import kalender
from ..theme import C
from .. import widgets as w


# ==========================================================================
# BASIS HALAMAN
# ==========================================================================
class HalamanDasar(QWidget):
    """Kerangka umum: header + toolbar + tabel."""

    pindah_halaman = Signal(str)

    def __init__(self, ctx, judul: str, subjudul: str, parent=None):
        super().__init__(parent)
        self.ctx = ctx

        luar = QVBoxLayout(self)
        luar.setContentsMargins(0, 0, 0, 0)
        luar.setSpacing(0)

        self.header = w.PageHeader(judul, subjudul)

        self.cmb_tahun = QComboBox()
        tk = datetime.now().year
        for t in range(tk - 3, tk + 2):
            self.cmb_tahun.addItem(str(t), t)
        i = self.cmb_tahun.findData(ctx.tahun)
        if i >= 0:
            self.cmb_tahun.setCurrentIndex(i)
        self.cmb_tahun.setMinimumWidth(100)
        self.cmb_tahun.currentIndexChanged.connect(self._ganti_tahun)
        self.header.tambah_aksi(self.cmb_tahun)

        self.cmb_bulan = QComboBox()
        self.cmb_bulan.addItem("Setahun", 0)
        for i, nama in enumerate(config.MONTH_NAMES_ID, start=1):
            self.cmb_bulan.addItem(nama, i)
        self.cmb_bulan.setMinimumWidth(115)
        self.cmb_bulan.currentIndexChanged.connect(self.muat)
        self.header.tambah_aksi(self.cmb_bulan)

        # Setiap halaman memakai header ini dan sebagian menambah tombol
        # sendiri. Karena itu tombol aksi disusun pada baris tersendiri di
        # bawah judul: bila disusun menyamping, tombolnya meluber keluar
        # tepi header pada lebar jendela yang lazim.
        self.header.susun_aksi_terpisah()

        kepala = QWidget()
        theme.latar(kepala, f"background: {C.SURFACE}; "
                             f"border-bottom: 1px solid {C.BORDER};")
        kl = QVBoxLayout(kepala)
        kl.setContentsMargins(26, 20, 26, 18)
        kl.addWidget(self.header)
        luar.addWidget(kepala)

        self.body = QWidget()
        self.body_lay = QVBoxLayout(self.body)
        self.body_lay.setContentsMargins(24, 20, 24, 22)
        self.body_lay.setSpacing(14)
        # Isi halaman dibungkus area gulir: penjelasan panjang dan tabel
        # besar tetap dapat dijangkau pada jendela pendek, dan tidak ada
        # label yang terpotong.
        luar.addWidget(w.scroll(self.body), 1)

    def _ganti_tahun(self):
        self.ctx.tahun = self.cmb_tahun.currentData()
        self.muat()

    def bulan(self):
        return self.cmb_bulan.currentData() or None

    def muat(self):
        pass

    def _help(self, kunci: str) -> QWidget:
        """Panel penjelasan (hanya pada mode Pemula)."""
        if not self.ctx.beginner:
            return None
        topik = coa.HELP_TOPICS.get(kunci)
        if not topik:
            return None
        return w.HelpPanel(topik["judul"], topik["isi"], topik.get("dasar_hukum", ""))


# ==========================================================================
# DIALOG JURNAL
# ==========================================================================
class DialogJurnal(QDialog):
    """
    Editor jurnal umum dengan baris dinamis.
    Memvalidasi keseimbangan debit-kredit secara langsung.
    """

    def __init__(self, ctx, parent=None, entry_id: int = None):
        super().__init__(parent)
        self.ctx = ctx
        self.entry_id = entry_id
        self.setWindowTitle("Entri Jurnal" if not entry_id else "Ubah Jurnal")
        self.setMinimumSize(1000, 620)
        self.akun = services.list_accounts(ctx.company_id)
        self.baris: list[dict] = []

        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 20, 22, 20)
        lay.setSpacing(13)

        # --- header jurnal
        j = QLabel("Entri Jurnal Umum")
        j.setObjectName("SectionTitle")
        lay.addWidget(j)

        if ctx.beginner:
            lay.addWidget(w.HelpPanel(
                "Cara mengisi jurnal",
                "Setiap transaksi harus memiliki total DEBIT = total KREDIT.\n\n"
                "• Untuk menambah uang di Kas/Bank, isi kolom DEBIT.\n"
                "• Untuk mengurangi uang di Kas/Bank, isi kolom KREDIT.\n"
                "• Pendapatan menambah di KREDIT, Beban menambah di DEBIT.\n\n"
                "Kolom 'Lawan Transaksi' diisi nama pelanggan/pemasok agar mudah "
                "ditelusuri saat pemeriksaan.",
                "Pasal 28 UU KUP - kewajiban menyelenggarakan pembukuan."))

        info = QFrame()
        theme.latar(info, f"background: {C.SURFACE_ALT}; border: 1px solid {C.BORDER}; "
                           "border-radius: 8px;")
        il = QGridLayout(info)
        il.setContentsMargins(16, 14, 16, 14)
        il.setSpacing(12)

        il.addWidget(w.label("Tanggal", objek="FormLabel"), 0, 0)
        self.inp_tanggal = kalender.pasang(QDateEdit())
        self.inp_tanggal.setDisplayFormat("dd/MM/yyyy")
        self.inp_tanggal.setDate(QDate.currentDate())
        il.addWidget(self.inp_tanggal, 1, 0)

        il.addWidget(w.label("No. Bukti", objek="FormLabel"), 0, 1)
        self.inp_bukti = QLineEdit()
        self.inp_bukti.setPlaceholderText("mis. BKM-001 / JU-2026-0001")
        il.addWidget(self.inp_bukti, 1, 1)

        il.addWidget(w.label("Keterangan Transaksi", objek="FormLabel"), 0, 2)
        self.inp_ket = QLineEdit()
        self.inp_ket.setPlaceholderText("mis. Penerimaan pembayaran project website")
        il.addWidget(self.inp_ket, 1, 2)

        il.setColumnStretch(2, 2)
        lay.addWidget(info)

        # --- tabel baris
        lay.addWidget(w.label("Rincian Debit & Kredit", objek="FormLabel"))
        self.tabel = w.Tabel([
            ("Akun", 300), ("Keterangan", 250), ("Lawan Transaksi", 170),
            ("NPWP/NIK", 130), ("Debit (Rp)", 145), ("Kredit (Rp)", 145), ("", 40),
        ])
        self.tabel.setMinimumHeight(260)
        lay.addWidget(self.tabel, 1)

        # --- tombol tambah baris
        baris_tombol = QHBoxLayout()
        baris_tombol.setSpacing(9)
        b_tambah = w.tombol("Tambah Baris", ikon="tambah")
        b_tambah.clicked.connect(lambda: self._tambah_baris())
        baris_tombol.addWidget(b_tambah)

        if ctx.beginner:
            b_contoh = w.tombol("Isi Contoh Jurnal", gaya="ghost")
            b_contoh.clicked.connect(self._isi_contoh)
            baris_tombol.addWidget(b_contoh)
        baris_tombol.addStretch()
        lay.addLayout(baris_tombol)

        # --- ringkasan keseimbangan
        self.panel_cek = QFrame()
        theme.latar(self.panel_cek, f"background: {C.NEUTRAL_BG}; border-radius: 8px;")
        cl = QHBoxLayout(self.panel_cek)
        cl.setContentsMargins(16, 12, 16, 12)
        cl.setSpacing(26)
        self.lbl_debit = QLabel("Total Debit: Rp0")
        self.lbl_debit.setStyleSheet(
            f"font-family: {theme.FONT_ANGKA}; font-size: 15px; font-weight: 700; "
            f"color: {C.DEBIT}; background: transparent;")
        cl.addWidget(self.lbl_debit)
        self.lbl_kredit = QLabel("Total Kredit: Rp0")
        self.lbl_kredit.setStyleSheet(
            f"font-family: {theme.FONT_ANGKA}; font-size: 15px; font-weight: 700; "
            f"color: {C.KREDIT}; background: transparent;")
        cl.addWidget(self.lbl_kredit)
        self.lbl_status = QLabel("Jurnal kosong")
        self.lbl_status.setStyleSheet(
            f"font-size: {theme.FS_BODY}px; font-weight: 700; background: transparent;")
        cl.addWidget(self.lbl_status)
        cl.addStretch()
        lay.addWidget(self.panel_cek)

        # --- tombol aksi
        aksi = QHBoxLayout()
        aksi.addStretch()
        batal = w.tombol("Batal")
        batal.clicked.connect(self.reject)
        aksi.addWidget(batal)
        self.b_simpan = w.tombol("Simpan Jurnal", gaya="primary")
        self.b_simpan.clicked.connect(self._simpan)
        aksi.addWidget(self.b_simpan)
        lay.addLayout(aksi)

        self._tambah_baris()
        self._tambah_baris()
        if entry_id:
            self._muat_jurnal()

    # ------------------------------------------------------------------
    def _tambah_baris(self, kode="", ket="", lawan="", npwp="", debit=0, kredit=0):
        baris = {
            "kode_akun": kode, "keterangan": ket, "lawan_transaksi": lawan,
            "npwp_nik": npwp, "debit": int(debit), "kredit": int(kredit),
        }
        self.baris.append(baris)
        self._render()

    def _render(self):
        self.tabel.setRowCount(len(self.baris))
        for i, b in enumerate(self.baris):
            # combo akun
            cb = QComboBox()
            cb.setEditable(True)
            cb.setInsertPolicy(QComboBox.NoInsert)
            for a in self.akun:
                cb.addItem(f"{a['kode']} - {a['nama']}", a["kode"])
            if b["kode_akun"]:
                idx = cb.findData(b["kode_akun"])
                if idx >= 0:
                    cb.setCurrentIndex(idx)
            cb.currentIndexChanged.connect(
                lambda _, r=i: self._ubah_akun(r, self.tabel.cellWidget(r, 0)))
            self.tabel.setCellWidget(i, 0, cb)

            for kolom, kunci in [(1, "keterangan"), (2, "lawan_transaksi"),
                                 (3, "npwp_nik")]:
                e = QLineEdit(b[kunci])
                e.textChanged.connect(
                    lambda teks, r=i, k=kunci: self.baris[r].__setitem__(k, teks))
                self.tabel.setCellWidget(i, kolom, e)

            for kolom, kunci in [(4, "debit"), (5, "kredit")]:
                e = w.InputRupiah()
                e.set_nilai(b[kunci])
                e.valueChanged.connect(
                    lambda v, r=i, k=kunci: self._ubah_nilai(r, k, v))
                self.tabel.setCellWidget(i, kolom, e)

            b_hapus = QPushButton("")
            b_hapus.setStyleSheet(
                f"QPushButton {{ background: transparent; border: none; "
                f"color: {C.TEXT_FAINT}; font-size: 15px; font-weight: 700; }}"
                f"QPushButton:hover {{ color: {C.DANGER}; }}")
            b_hapus.setCursor(Qt.PointingHandCursor)
            b_hapus.clicked.connect(lambda _, r=i: self._hapus_baris(r))
            self.tabel.setCellWidget(i, 6, b_hapus)

        self._update_cek()

    def _ubah_akun(self, r: int, combo):
        if combo and r < len(self.baris):
            self.baris[r]["kode_akun"] = combo.currentData() or ""
            self._update_cek()

    def _ubah_nilai(self, r: int, kunci: str, nilai: int):
        if r >= len(self.baris):
            return
        self.baris[r][kunci] = int(nilai)
        # debit & kredit saling eksklusif
        lawan = "kredit" if kunci == "debit" else "debit"
        if nilai > 0 and self.baris[r][lawan] > 0:
            self.baris[r][lawan] = 0
            kolom = 5 if lawan == "kredit" else 4
            widget = self.tabel.cellWidget(r, kolom)
            if widget:
                widget.blockSignals(True)
                widget.set_nilai(0)
                widget.blockSignals(False)
        self._update_cek()

    def _hapus_baris(self, r: int):
        if r < len(self.baris):
            del self.baris[r]
            self._render()

    def _update_cek(self):
        td = sum(b["debit"] for b in self.baris)
        tk = sum(b["kredit"] for b in self.baris)
        self.lbl_debit.setText(f"Total Debit: {theme.money(td)}")
        self.lbl_kredit.setText(f"Total Kredit: {theme.money(tk)}")

        if td == 0 and tk == 0:
            self.lbl_status.setText("Jurnal kosong")
            self.lbl_status.setStyleSheet(
                f"color: {C.TEXT_MUTED}; font-weight: 700; background: transparent;")
            theme.latar(self.panel_cek, f"background: {C.NEUTRAL_BG}; border-radius: 8px;")
            self.b_simpan.setEnabled(False)
        elif td == tk:
            self.lbl_status.setText("SEIMBANG - selisih Rp0")
            self.lbl_status.setStyleSheet(
                f"color: {C.SUCCESS}; font-weight: 700; background: transparent;")
            theme.latar(self.panel_cek, f"background: {C.SUCCESS_BG}; border: 1px solid #B8E6D5; border-radius: 8px;")
            self.b_simpan.setEnabled(True)
        else:
            selisih = td - tk
            self.lbl_status.setText(
                f"TIDAK SEIMBANG - selisih {theme.money(abs(selisih))}")
            self.lbl_status.setStyleSheet(
                f"color: {C.DANGER}; font-weight: 700; background: transparent;")
            theme.latar(self.panel_cek, f"background: {C.DANGER_BG}; border: 1px solid #F5C2C2; border-radius: 8px;")
            self.b_simpan.setEnabled(False)

    def _isi_contoh(self):
        """Isi contoh jurnal standar untuk pembelajaran."""
        dlg = QDialog(self)
        dlg.setWindowTitle("Pilih Contoh Jurnal")
        dlg.setMinimumWidth(560)
        l = QVBoxLayout(dlg)
        l.setContentsMargins(22, 20, 22, 20)
        l.setSpacing(11)

        j = QLabel("Contoh jurnal transaksi umum UMKM & PT")
        j.setObjectName("SectionTitle")
        l.addWidget(j)

        contoh_list = [
            ("Setoran modal awal usaha",
             "Mencatat uang yang disetor pemilik sebagai modal usaha.",
             [("1001", "Setoran modal tunai", "Pemilik", 50_000_000, 0),
              ("3001", "Modal disetor pemilik", "Pemilik", 0, 50_000_000)]),
            ("Penjualan jasa tunai",
             "Menerima pembayaran jasa secara tunai.",
             [("1001", "Penerimaan jasa", "Pelanggan", 5_000_000, 0),
              ("4001", "Pendapatan jasa", "Pelanggan", 0, 5_000_000)]),
            ("Penjualan barang kredit (belum PKP)",
             "Menjual barang dengan pembayaran tempo.",
             [("1101", "Penjualan barang tempo", "Pelanggan", 10_000_000, 0),
              ("4001", "Pendapatan penjualan", "Pelanggan", 0, 10_000_000)]),
            ("Penjualan dengan PPN keluaran (PKP)",
             "Penjualan Rp10 juta + PPN 11% = Rp11,1 juta.",
             [("1001", "Penerimaan penjualan + PPN", "Pelanggan", 11_100_000, 0),
              ("4001", "Pendapatan penjualan", "Pelanggan", 0, 10_000_000),
              ("2101", "PPN keluaran 11%", "Pelanggan", 0, 1_100_000)]),
            ("Pembelian perlengkapan tunai",
             "Membeli perlengkapan kantor secara tunai.",
             [("6008", "Pembelian ATK", "Toko ATK", 750_000, 0),
              ("1001", "Pembayaran tunai", "Toko ATK", 0, 750_000)]),
            ("Pembayaran beban listrik & internet",
             "Tagihan utilitas bulanan.",
             [("6003", "Beban listrik & internet", "PLN/ISP", 1_200_000, 0),
              ("1002", "Transfer bank", "PLN/ISP", 0, 1_200_000)]),
            ("Pembayaran gaji karyawan",
             "Gaji bersih dibayarkan tunai.",
             [("6001", "Beban gaji bulan ini", "Karyawan", 5_000_000, 0),
              ("1001", "Pembayaran gaji", "Karyawan", 0, 5_000_000)]),
            ("Penerimaan pelunasan piutang",
             "Pelanggan melunasi tagihan tempo.",
             [("1002", "Penerimaan pelunasan", "Pelanggan", 10_000_000, 0),
              ("1101", "Piutang dilunasi", "Pelanggan", 0, 10_000_000)]),
            ("Membeli peralatan (aset tetap) tunai",
             "Peralatan kerja umur lebih dari satu tahun.",
             [("1201", "Perolehan peralatan", "Toko", 8_000_000, 0),
              ("1002", "Pembayaran peralatan", "Toko", 0, 8_000_000)]),
            ("Penarikan pribadi pemilik (prive)",
             "Uang usaha dipakai keperluan pribadi. BUKAN beban usaha.",
             [("3002", "Prive pemilik", "Pemilik", 2_000_000, 0),
              ("1001", "Penarikan tunai", "Pemilik", 0, 2_000_000)]),
            ("Penyusutan peralatan bulanan",
             "Mengakui beban penyusutan aset tetap.",
             [("6007", "Beban penyusutan", "", 200_000, 0),
              ("1202", "Akumulasi penyusutan", "", 0, 200_000)]),
            ("Pembayaran utang usaha",
             "Melunasi utang ke pemasok.",
             [("2001", "Pelunasan utang", "Pemasok", 3_000_000, 0),
              ("1002", "Transfer bank", "Pemasok", 0, 3_000_000)]),
        ]

        for nama, ket, baris in contoh_list:
            b = QPushButton(f"{nama}\n{ket}")
            b.setCursor(Qt.PointingHandCursor)
            b.setStyleSheet(
                f"QPushButton {{ background: {C.SURFACE}; border: 1px solid {C.BORDER}; "
                f"border-radius: 7px; padding: 10px 13px; text-align: left; "
                f"font-size: {theme.FS_SMALL}px; }}"
                f"QPushButton:hover {{ background: {C.PRIMARY_SOFT}; "
                f"border-color: {C.PRIMARY_LIGHT}; }}")
            b.clicked.connect(lambda _, bb=baris, nn=nama: self._pakai_contoh(bb, nn, dlg))
            l.addWidget(b)

        batal = w.tombol("Tutup")
        batal.clicked.connect(dlg.reject)
        baris_b = QHBoxLayout()
        baris_b.addStretch()
        baris_b.addWidget(batal)
        l.addLayout(baris_b)
        dlg.exec()

    def _pakai_contoh(self, baris: list, nama: str, dlg: QDialog):
        self.baris = [{
            "kode_akun": k, "keterangan": ket, "lawan_transaksi": lawan,
            "npwp_nik": "", "debit": d, "kredit": kr,
        } for k, ket, lawan, d, kr in baris]
        if not self.inp_ket.text():
            self.inp_ket.setText(nama)
        if not self.inp_bukti.text():
            self.inp_bukti.setText(acc.nomor_bukti_berikut(self.ctx.company_id))
        self._render()
        dlg.accept()

    def _muat_jurnal(self):
        from ... import db
        e = db.q1("SELECT * FROM journal_entries WHERE id=?", (self.entry_id,))
        if not e:
            return
        self.inp_ket.setText(e["keterangan"])
        self.inp_bukti.setText(e["no_bukti"])
        try:
            y, m, d = e["tanggal"][:10].split("-")
            self.inp_tanggal.setDate(QDate(int(y), int(m), int(d)))
        except Exception:
            pass
        lines = services.detail_jurnal(self.entry_id)
        self.baris = [{
            "kode_akun": l["kode_akun"], "keterangan": l["catatan"],
            "lawan_transaksi": l["lawan_transaksi"], "npwp_nik": l["npwp_nik"],
            "debit": l["debit"], "kredit": l["kredit"],
        } for l in lines]
        self._render()

    def _simpan(self):
        try:
            tanggal = self.inp_tanggal.date().toString("yyyy-MM-dd")
            no_bukti = self.inp_bukti.text().strip() or \
                acc.nomor_bukti_berikut(self.ctx.company_id)
            keterangan = self.inp_ket.text().strip()
            if not keterangan:
                QMessageBox.warning(self, "Keterangan kosong",
                                    "Isi keterangan transaksi agar jurnal mudah ditelusuri.")
                return

            baris = []
            for b in self.baris:
                if not b["kode_akun"]:
                    continue
                if b["debit"] == 0 and b["kredit"] == 0:
                    continue
                baris.append({
                    "kode_akun": b["kode_akun"], "debit": b["debit"],
                    "kredit": b["kredit"], "lawan_transaksi": b["lawan_transaksi"],
                    "npwp_nik": b["npwp_nik"], "catatan": b["keterangan"],
                })

            v = acc.validasi_jurnal(baris, self.ctx.company_id)
            if not v.valid:
                QMessageBox.warning(self, "Jurnal tidak valid", "\n".join(v.errors))
                return

            if self.entry_id:
                services.hapus_jurnal(self.entry_id)
            services.simpan_jurnal_manual(self.ctx.company_id, tanggal, no_bukti,
                                          keterangan, baris, self.ctx.user_id)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Gagal menyimpan", str(e))


# ==========================================================================
# HALAMAN JURNAL UMUM
# ==========================================================================
class JurnalPage(HalamanDasar):
    def __init__(self, ctx, parent=None):
        super().__init__(ctx, "Jurnal Umum",
                         "Sumber utama seluruh laporan keuangan. Setiap transaksi "
                         "harus seimbang antara debit dan kredit.")
        b = w.tombol("Entri Jurnal Baru", gaya="primary", ikon="tambah")
        b.clicked.connect(self._baru)
        self.header.tambah_aksi(b)

        self.inp_cari = QLineEdit()
        self.inp_cari.setPlaceholderText("Cari keterangan atau nomor bukti…")
        self.inp_cari.setMinimumWidth(240)
        self.inp_cari.textChanged.connect(self.muat)
        self.header.tambah_aksi(self.inp_cari)
        self.header.pasang_ekspor_cetak(self, "Buku Jurnal", "tabel")

        # panel kontrol keseimbangan
        self.panel_cek = QFrame()
        theme.latar(self.panel_cek, f"background: {C.SUCCESS_BG}; "
                                     "border: 1px solid #B8E6D5; border-radius: 8px;")
        self.cek_lay = QHBoxLayout(self.panel_cek)
        self.cek_lay.setContentsMargins(16, 11, 16, 11)
        self.cek_lay.setSpacing(28)
        self.body_lay.addWidget(self.panel_cek)

        help_panel = self._help("jurnal")
        if help_panel:
            self.body_lay.addWidget(help_panel)

        self.tabel = w.Tabel([
            ("Tanggal", 100), ("No. Bukti", 140), ("Keterangan", -1),
            ("Debit (Rp)", 145), ("Kredit (Rp)", 145), ("Sumber", 105),
        ])
        self.tabel.doubleClicked.connect(self._ubah)
        self.body_lay.addWidget(self.tabel, 1)

        baris_aksi = QHBoxLayout()
        baris_aksi.setSpacing(9)
        b_detail = w.tombol("Lihat Detail", ikon="")
        b_detail.clicked.connect(self._detail)
        baris_aksi.addWidget(b_detail)
        b_ubah = w.tombol("Ubah", ikon="pengaturan")
        b_ubah.clicked.connect(self._ubah)
        baris_aksi.addWidget(b_ubah)
        b_hapus = w.tombol("Hapus", gaya="danger", ikon="hapus")
        b_hapus.clicked.connect(self._hapus)
        baris_aksi.addWidget(b_hapus)
        baris_aksi.addStretch()
        self.lbl_info = QLabel("")
        self.lbl_info.setObjectName("Muted")
        baris_aksi.addWidget(self.lbl_info)
        self.body_lay.addLayout(baris_aksi)

    def muat(self):
        cid, tahun = self.ctx.company_id, self.ctx.tahun
        if not cid:
            return
        data = services.list_jurnal(cid, tahun, self.bulan(), self.inp_cari.text().strip())
        baris, warna = [], {}
        for i, e in enumerate(data):
            sumber = {"manual": "Manual", "penjualan": "Penjualan",
                      "pembelian": "Pembelian", "payroll": "Payroll",
                      "aset": "Aset Tetap", "pajak": "Pajak",
                      "penutup": "Penutup"}.get(e["sumber"], e["sumber"])
            seimbang = abs(e["total_debit"] - e["total_kredit"]) < 0.5
            baris.append([theme.tanggal_id(e["tanggal"]), e["no_bukti"],
                          e["keterangan"], theme.money(e["total_debit"]),
                          theme.money(e["total_kredit"]), sumber])
            if not seimbang:
                warna[i] = C.DANGER
        self.tabel.isi(baris, warna_baris=warna, align_kanan={3, 4})
        self._refresh_cek()
        self.lbl_info.setText(f"{len(data)} entri jurnal ditampilkan")

    def _refresh_cek(self):
        while self.cek_lay.count():
            it = self.cek_lay.takeAt(0)
            wdg = it.widget()
            if wdg is not None:
                wdg.setParent(None)
                wdg.deleteLater()

        cek = acc.total_neraca_saldo(self.ctx.company_id, self.ctx.tahun, self.bulan())
        tdk_seimbang = acc.cek_jurnal_tidak_seimbang(self.ctx.company_id)

        if cek["seimbang"] and not tdk_seimbang:
            theme.latar(self.panel_cek, f"background: {C.SUCCESS_BG}; border: 1px solid #B8E6D5; "
                "border-radius: 8px;")
            l = QLabel(f"Pembukuan seimbang - total debit {theme.money(cek['debit'])} "
                       f"= total kredit {theme.money(cek['kredit'])}")
            l.setStyleSheet(f"color: {C.SUCCESS}; font-weight: 700; "
                            "background: transparent;")
            self.cek_lay.addWidget(l)
        else:
            theme.latar(self.panel_cek, f"background: {C.DANGER_BG}; border: 1px solid #F5C2C2; "
                "border-radius: 8px;")
            l = QLabel(f"Terdapat ketidakseimbangan: {len(tdk_seimbang)} bukti jurnal "
                       f"tidak seimbang. Selisih total {theme.money(cek['selisih'])}.")
            l.setStyleSheet(f"color: {C.DANGER}; font-weight: 700; "
                            "background: transparent;")
            self.cek_lay.addWidget(l)
        self.cek_lay.addStretch()

    def _baru(self):
        if not self.ctx.company_id:
            QMessageBox.information(self, "Belum ada perusahaan",
                                    "Buat profil perusahaan terlebih dahulu.")
            return
        d = DialogJurnal(self.ctx, self)
        if d.exec():
            self.muat()

    def _selected_id(self):
        r = self.tabel.baris_terpilih()
        if r is None:
            return None
        data = services.list_jurnal(self.ctx.company_id, self.ctx.tahun,
                                    self.bulan(), self.inp_cari.text().strip())
        return data[r]["id"] if r < len(data) else None

    def _detail(self):
        eid = self._selected_id()
        if eid is None:
            QMessageBox.information(self, "Belum dipilih", "Pilih satu baris jurnal.")
            return
        lines = services.detail_jurnal(eid)
        from ... import db
        e = db.q1("SELECT * FROM journal_entries WHERE id=?", (eid,))

        dlg = QDialog(self)
        dlg.setWindowTitle(f"Detail Jurnal {e['no_bukti']}")
        dlg.setMinimumSize(820, 460)
        l = QVBoxLayout(dlg)
        l.setContentsMargins(22, 20, 22, 20)
        l.setSpacing(11)

        j = QLabel(f"{e['no_bukti']} · {theme.tanggal_id(e['tanggal'])}")
        j.setObjectName("SectionTitle")
        l.addWidget(j)
        k = QLabel(e["keterangan"])
        k.setObjectName("Muted")
        k.setWordWrap(True)
        l.addWidget(k)

        t = w.Tabel([("Kode", 80), ("Nama Akun", -1), ("Lawan Transaksi", 180),
                     ("NPWP/NIK", 130), ("Debit", 135), ("Kredit", 135)])
        baris = [[x["kode_akun"], x["nama_akun"], x["lawan_transaksi"],
                  x["npwp_nik"], theme.money(x["debit"]), theme.money(x["kredit"])]
                 for x in lines]
        td = sum(x["debit"] for x in lines)
        tk = sum(x["kredit"] for x in lines)
        baris.append(["", "TOTAL", "", "", theme.money(td), theme.money(tk)])
        t.isi(baris, align_kanan={4, 5}, warna_baris={len(baris) - 1: C.PRIMARY})
        t.setMinimumHeight(260)
        l.addWidget(t)

        b = w.tombol("Tutup", gaya="primary")
        b.clicked.connect(dlg.accept)
        bl = QHBoxLayout()
        bl.addStretch()
        bl.addWidget(b)
        l.addLayout(bl)
        dlg.exec()

    def _ubah(self):
        eid = self._selected_id()
        if eid is None:
            QMessageBox.information(self, "Belum dipilih", "Pilih satu baris jurnal.")
            return
        from ... import db
        e = db.q1("SELECT sumber FROM journal_entries WHERE id=?", (eid,))
        if e and e["sumber"] not in ("manual",):
            QMessageBox.information(
                self, "Jurnal otomatis",
                f"Jurnal ini dibuat otomatis oleh modul '{e['sumber']}'.\n\n"
                "Untuk mengubahnya, ubah datanya pada halaman terkait "
                "(Penjualan/Pembelian/Payroll/Aset Tetap/Pajak) agar jurnal "
                "ikut diperbarui.")
            return
        d = DialogJurnal(self.ctx, self, entry_id=eid)
        if d.exec():
            self.muat()

    def _hapus(self):
        eid = self._selected_id()
        if eid is None:
            QMessageBox.information(self, "Belum dipilih", "Pilih satu baris jurnal.")
            return
        if QMessageBox.question(
                self, "Konfirmasi Hapus",
                "Hapus jurnal ini beserta seluruh barisnya?\n\n"
                "Tindakan ini tidak dapat dibatalkan.",
                QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return
        try:
            services.hapus_jurnal(eid, self.ctx.user_id)
            self.muat()
        except Exception as e:
            QMessageBox.critical(self, "Gagal menghapus", str(e))
