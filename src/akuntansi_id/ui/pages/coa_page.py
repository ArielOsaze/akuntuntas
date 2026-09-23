"""
AkunTuntas - Halaman Bagan Akun & Data Perusahaan
=================================================
  • Bagan Akun (Chart of Accounts) + saldo awal
  • Data Perusahaan & pengaturan pajak
"""
from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt, Signal, QDate
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit, QDateEdit,
    QDialog, QMessageBox, QFrame, QGridLayout, QCheckBox, QTextEdit,
    QTableWidgetItem,
)

from ... import config, coa, services
from ...core import tax_engine as tx
from .. import pilihan_entitas
from .. import theme
from .. import kalender
from ..theme import C
from .. import widgets as w


# ==========================================================================
# HALAMAN BAGAN AKUN
# ==========================================================================
class CoaPage(QWidget):
    pindah_halaman = Signal(str)

    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx

        luar = QVBoxLayout(self)
        luar.setContentsMargins(0, 0, 0, 0)
        luar.setSpacing(0)

        self.header = w.PageHeader(
            "Bagan Akun (Chart of Accounts)",
            "Daftar akun yang dipakai untuk mencatat transaksi. Aplikasi menyiapkan "
            "template sesuai bentuk badan usaha Anda.")

        b = w.tombol("Tambah Akun", gaya="primary", ikon="+")
        b.clicked.connect(self._tambah)
        self.header.tambah_aksi(b)

        b2 = w.tombol("Ubah", ikon="pengaturan")
        b2.clicked.connect(self._ubah)
        self.header.tambah_aksi(b2)

        b3 = w.tombol("Kelola Saldo Awal", ikon="")
        b3.clicked.connect(self._saldo_awal)
        self.header.tambah_aksi(b3)

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

        self.banner = QWidget()
        self.banner_lay = QVBoxLayout(self.banner)
        self.banner_lay.setContentsMargins(0, 0, 0, 0)
        self.lay.addWidget(self.banner)

        if ctx.beginner:
            topik = coa.HELP_TOPICS["coa"]
            self.lay.addWidget(w.HelpPanel(topik["judul"], topik["isi"],
                                           topik["dasar_hukum"]))

        # filter
        filter_baris = QHBoxLayout()
        filter_baris.setSpacing(11)
        self.inp_cari = QLineEdit()
        self.inp_cari.setPlaceholderText("Cari kode atau nama akun…")
        self.inp_cari.setMinimumWidth(260)
        self.inp_cari.textChanged.connect(self.muat)
        filter_baris.addWidget(self.inp_cari)

        self.cmb_tipe = QComboBox()
        self.cmb_tipe.addItem("Semua Tipe", "")
        for t in ["Aset", "Liabilitas", "Ekuitas", "Pendapatan", "Beban"]:
            self.cmb_tipe.addItem(t, t)
        self.cmb_tipe.currentIndexChanged.connect(self.muat)
        filter_baris.addWidget(self.cmb_tipe)
        filter_baris.addStretch()
        self.lay.addLayout(filter_baris)

        self.tabel = w.Tabel([
            ("Kode", 90), ("Nama Akun", -1), ("Tipe", 135),
            ("Kelompok", 200), ("Saldo Awal", 155), ("Saldo Akhir", 155),
        ])
        self.tabel.doubleClicked.connect(self._ubah)
        self.lay.addWidget(self.tabel, 1)

        self.lbl_info = QLabel("")
        self.lbl_info.setObjectName("Muted")
        self.lay.addWidget(self.lbl_info)

    def muat(self):
        while self.banner_lay.count():
            it = self.banner_lay.takeAt(0)
            wdg = it.widget()
            if wdg is not None:
                wdg.setParent(None)
                wdg.deleteLater()

        cid = self.ctx.company_id
        if not cid:
            return

        # cek keseimbangan saldo awal
        cek = services.cek_keseimbangan_saldo_awal(cid)
        if not cek["seimbang"] and cek["jumlah_akun"] > 0:
            self.banner_lay.addWidget(w.InfoBanner(
                f"Saldo awal belum seimbang. Total debit {theme.money(cek['total_debit'])} "
                f"sedangkan total kredit {theme.money(cek['total_kredit'])} - selisih "
                f"{theme.money(abs(cek['selisih']))}. Neraca akan pincang sampai "
                "saldo awal diseimbangkan.",
                "danger", "Saldo awal tidak seimbang"))
        elif cek["jumlah_akun"] > 0:
            self.banner_lay.addWidget(w.InfoBanner(
                f"Saldo awal seimbang: total debit {theme.money(cek['total_debit'])} "
                f"= total kredit {theme.money(cek['total_kredit'])}.",
                "ok", "Saldo awal seimbang"))

        cari = self.inp_cari.text().strip().lower()
        tipe = self.cmb_tipe.currentData()
        akun = services.list_accounts(cid)
        saldo = {d.kode: d for d in services.laporan_neraca_saldo(cid, self.ctx.tahun)}

        baris, warna = [], {}
        for a in akun:
            if tipe and a["tipe"] != tipe:
                continue
            if cari and cari not in a["kode"].lower() and cari not in a["nama"].lower():
                continue
            idx = len(baris)
            d = saldo.get(a["kode"])
            akhir = d.saldo_akhir_normal if d else 0
            kelompok = a["grup_lr"] or a["baris_neraca"] or ""
            if a["perlakuan_fiskal"] in ("Non-Deductible (+)", "Final Income (-)"):
                kelompok = f"{kelompok} · fiskal khusus"
            baris.append([
                a["kode"], a["nama"], a["tipe"], kelompok,
                theme.money(a["saldo_awal"]), theme.money(akhir),
            ])
            if a["perlakuan_fiskal"] in ("Non-Deductible (+)", "Final Income (-)"):
                warna[idx] = C.WARNING
            elif a["perlakuan_fiskal"] == "Review Fiskal":
                warna[idx] = C.INFO

        # Warna hanya dipakai sebagai penanda pada kolom kode akun. Bila
        # seluruh baris diwarnai, nominal rupiah ikut berwarna dan sulit
        # dibaca. Keterangan fiskal tetap ditulis agar tidak bergantung warna.
        self.tabel.isi(baris, warna_baris=warna, align_kanan={4, 5},
                       kolom_penanda=0)
        self.lbl_info.setText(f"{len(baris)} akun ditampilkan dari {len(akun)} total")

    def _tambah(self):
        if not self.ctx.company_id:
            return
        d = DialogAkun(self.ctx, self)
        if d.exec():
            self.muat()

    def _ubah(self):
        r = self.tabel.baris_terpilih()
        if r is None:
            QMessageBox.information(self, "Belum dipilih", "Pilih satu akun.")
            return
        kode = self.tabel.item(r, 0).text()
        akun = services.get_account(self.ctx.company_id, kode)
        if akun:
            d = DialogAkun(self.ctx, self, akun)
            if d.exec():
                self.muat()

    def _saldo_awal(self):
        if not self.ctx.company_id:
            return
        d = DialogSaldoAwal(self.ctx, self)
        if d.exec():
            self.muat()


class DialogAkun(QDialog):
    def __init__(self, ctx, parent=None, akun=None):
        super().__init__(parent)
        self.ctx = ctx
        self.akun = akun
        self.setWindowTitle("Tambah Akun" if not akun else "Ubah Akun")
        self.setMinimumWidth(620)

        l = QVBoxLayout(self)
        l.setContentsMargins(24, 22, 24, 22)
        l.setSpacing(13)

        j = QLabel("Data Akun")
        j.setObjectName("SectionTitle")
        l.addWidget(j)

        if ctx.beginner and not akun:
            l.addWidget(w.HelpPanel(
                "Memilih tipe dan grup akun",
                "Tipe akun menentukan posisi akun di laporan:\n\n"
                "• ASET & BEBAN bersaldo normal DEBIT (bertambah di debit)\n"
                "• LIABILITAS, EKUITAS & PENDAPATAN bersaldo normal KREDIT "
                "(bertambah di kredit)\n\n"
                "'Grup L/R' menentukan posisi akun di Laba Rugi "
                "(Pendapatan Usaha / HPP / Beban Operasional / Pendapatan Lain / "
                "Beban Lain).\n\n"
                "'Baris Neraca' menentukan posisi akun di Neraca "
                "(Kas & Bank / Piutang Usaha / Persediaan / Aset Tetap / Utang Usaha / "
                "Utang Pajak / Modal / dst).\n\n"
                "Akun neraca cukup mengisi Baris Neraca; akun laba rugi cukup "
                "mengisi Grup L/R.",
                "Pasal 28 UU KUP - pembukuan yang teratur dan dapat diperiksa."))

        g = QGridLayout()
        g.setSpacing(12)

        g.addWidget(w.label("Kode Akun", objek="FormLabel"), 0, 0)
        self.inp_kode = QLineEdit()
        self.inp_kode.setPlaceholderText("mis. 6017")
        g.addWidget(self.inp_kode, 1, 0)

        g.addWidget(w.label("Nama Akun", objek="FormLabel"), 0, 1)
        self.inp_nama = QLineEdit()
        g.addWidget(self.inp_nama, 1, 1)

        g.addWidget(w.label("Tipe Akun", objek="FormLabel"), 2, 0)
        self.cmb_tipe = QComboBox()
        for t in ["Aset", "Liabilitas", "Ekuitas", "Pendapatan", "Beban"]:
            self.cmb_tipe.addItem(t, t)
        self.cmb_tipe.currentIndexChanged.connect(self._update_normal)
        g.addWidget(self.cmb_tipe, 3, 0)

        g.addWidget(w.label("Saldo Normal", objek="FormLabel"), 2, 1)
        self.cmb_normal = QComboBox()
        self.cmb_normal.addItem("Debit", "Debit")
        self.cmb_normal.addItem("Kredit", "Kredit")
        g.addWidget(self.cmb_normal, 3, 1)

        g.addWidget(w.label("Grup L/R (untuk akun laba rugi)", objek="FormLabel"), 4, 0, 1, 2)
        self.cmb_grup = QComboBox()
        self.cmb_grup.addItem("- (bukan akun laba rugi)", "")
        for g_ in ["Pendapatan Usaha", "HPP", "Beban Operasional",
                   "Pendapatan Lain", "Beban Lain"]:
            self.cmb_grup.addItem(g_, g_)
        g.addWidget(self.cmb_grup, 5, 0, 1, 2)

        g.addWidget(w.label("Baris Neraca (untuk akun neraca)", objek="FormLabel"), 6, 0, 1, 2)
        self.cmb_baris = QComboBox()
        self.cmb_baris.addItem("- (bukan akun neraca)", "")
        for b in ["Kas & Bank", "Piutang Usaha", "Persediaan", "Aset Lancar Lain",
                  "Aset Tetap", "Akumulasi Penyusutan", "Aset Lain",
                  "Utang Usaha", "Utang Pajak", "Pinjaman Jangka Pendek",
                  "Pinjaman Jangka Panjang", "Modal", "Saldo Laba", "Prive",
                  "Dividen", "Laba Tahun Berjalan"]:
            self.cmb_baris.addItem(b, b)
        g.addWidget(self.cmb_baris, 7, 0, 1, 2)

        g.addWidget(w.label("Perlakuan Fiskal", objek="FormLabel"), 8, 0, 1, 2)
        self.cmb_fiskal = QComboBox()
        for p, ket in [
            ("Deductible/Taxable", "Netral - dapat dikurangkan/dikenai pajak"),
            ("Non-Deductible (+)", "Tidak dapat dikurangkan - koreksi positif otomatis"),
            ("Final Income (-)", "Penghasilan final - koreksi negatif otomatis"),
            ("Review Fiskal", "Perlu ditinjau manual saat rekonsiliasi"),
            ("Timing/Depreciation", "Perbedaan waktu (penyusutan)"),
        ]:
            self.cmb_fiskal.addItem(f"{p} - {ket}", p)
        g.addWidget(self.cmb_fiskal, 9, 0, 1, 2)

        g.addWidget(w.label("Deskripsi (tampil sebagai bantuan)", objek="FormLabel"), 10, 0, 1, 2)
        self.inp_deskripsi = QTextEdit()
        self.inp_deskripsi.setMaximumHeight(80)
        self.inp_deskripsi.setPlaceholderText(
            "Jelaskan kegunaan akun ini agar pengguna lain memahami.")
        g.addWidget(self.inp_deskripsi, 11, 0, 1, 2)
        l.addLayout(g)

        self.chk_kas = QCheckBox("Akun ini termasuk Kas && Bank (dipakai untuk arus kas)")
        l.addWidget(self.chk_kas)

        aksi = QHBoxLayout()
        aksi.addStretch()
        b = w.tombol("Batal")
        b.clicked.connect(self.reject)
        aksi.addWidget(b)
        bs = w.tombol("Simpan", gaya="primary")
        bs.clicked.connect(self._simpan)
        aksi.addWidget(bs)
        l.addLayout(aksi)

        if akun:
            self._muat(akun)
        else:
            self._update_normal()

    def _update_normal(self):
        tipe = self.cmb_tipe.currentData()
        if tipe in ("Aset", "Beban"):
            self.cmb_normal.setCurrentIndex(0)
        else:
            self.cmb_normal.setCurrentIndex(1)

    def _muat(self, a):
        self.inp_kode.setText(a["kode"])
        self.inp_kode.setReadOnly(True)
        self.inp_nama.setText(a["nama"])
        i = self.cmb_tipe.findData(a["tipe"])
        if i >= 0:
            self.cmb_tipe.setCurrentIndex(i)
        i = self.cmb_normal.findData(a["normal"])
        if i >= 0:
            self.cmb_normal.setCurrentIndex(i)
        i = self.cmb_grup.findData(a["grup_lr"] or "")
        if i >= 0:
            self.cmb_grup.setCurrentIndex(i)
        i = self.cmb_baris.findData(a["baris_neraca"] or "")
        if i >= 0:
            self.cmb_baris.setCurrentIndex(i)
        i = self.cmb_fiskal.findData(a["perlakuan_fiskal"])
        if i >= 0:
            self.cmb_fiskal.setCurrentIndex(i)
        self.inp_deskripsi.setPlainText(a["deskripsi"] or "")
        self.chk_kas.setChecked(bool(a["is_kas_bank"]))

    def _simpan(self):
        try:
            if not self.inp_kode.text().strip() or not self.inp_nama.text().strip():
                QMessageBox.warning(self, "Data kurang",
                                    "Kode dan nama akun wajib diisi.")
                return
            data = dict(
                nama=self.inp_nama.text().strip(),
                tipe=self.cmb_tipe.currentData(),
                grup_lr=self.cmb_grup.currentData() or "",
                baris_neraca=self.cmb_baris.currentData() or "",
                normal=self.cmb_normal.currentData(),
                perlakuan_fiskal=self.cmb_fiskal.currentData(),
                deskripsi=self.inp_deskripsi.toPlainText().strip(),
                is_kas_bank=self.chk_kas.isChecked(),
            )
            if self.akun:
                services.update_account(self.ctx.company_id, self.akun["kode"], **data)
            else:
                services.create_account(self.ctx.company_id,
                                        self.inp_kode.text().strip(), **data)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Gagal menyimpan", str(e))


class DialogSaldoAwal(QDialog):
    """Kelola saldo awal seluruh akun neraca sekaligus."""

    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.setWindowTitle("Kelola Saldo Awal")
        self.setMinimumSize(900, 640)
        self.inputs: dict[str, w.InputRupiah] = {}

        l = QVBoxLayout(self)
        l.setContentsMargins(24, 22, 24, 22)
        l.setSpacing(12)

        j = QLabel("Saldo Awal Akun")
        j.setObjectName("SectionTitle")
        l.addWidget(j)

        l.addWidget(w.HelpPanel(
            "Tentang saldo awal",
            "Saldo awal adalah posisi akun pada tanggal Anda MULAI memakai aplikasi "
            "ini. Bila usaha sudah berjalan sebelumnya, isi saldo nyata saat itu.\n\n"
            "Ketentuan penting:\n"
            "• Total saldo awal akun DEBIT (aset, beban) harus SAMA dengan total "
            "akun KREDIT (liabilitas, ekuitas, pendapatan).\n"
            "• Isi nilai positif pada sisi normal akun.\n"
            "• Selisihnya biasanya ditutup ke akun Modal atau Saldo Laba.\n\n"
            "Contoh: kas Rp50 juta + peralatan Rp30 juta = modal Rp80 juta.\n"
            "Debit Rp80 juta = Kredit Rp80 juta simpan",
            "Pasal 28 UU KUP - pembukuan harus menggambarkan keadaan sebenarnya."))

        # tabel input
        self.tabel = w.Tabel([("Kode", 85), ("Nama Akun", -1), ("Normal", 80),
                              ("Saldo Awal (Rp)", 200)])
        l.addWidget(self.tabel, 1)

        self.panel = QFrame()
        theme.latar(self.panel, f"background: {C.NEUTRAL_BG}; border-radius: 8px;")
        pl = QHBoxLayout(self.panel)
        pl.setContentsMargins(14, 11, 14, 11)
        pl.setSpacing(18)
        # Lebar minimum dihitung dari nominal terpanjang yang mungkin
        # muncul. Tanpa itu, angka miliaran terpotong dan pengguna salah
        # membaca total saldo awal.
        from PySide6.QtGui import QFontMetrics

        self.lbl_debit = QLabel("Total Debit: Rp0")
        self.lbl_debit.setStyleSheet(
            f"font-family: {theme.FONT_ANGKA}; font-size: 13px; font-weight: 700; "
            f"color: {C.DEBIT}; background: transparent;")
        self.lbl_debit.setMinimumWidth(
            QFontMetrics(self.lbl_debit.font()).horizontalAdvance(
                "Total Debit: Rp999.999.999.999") + 8)
        pl.addWidget(self.lbl_debit)
        self.lbl_kredit = QLabel("Total Kredit: Rp0")
        self.lbl_kredit.setStyleSheet(
            f"font-family: {theme.FONT_ANGKA}; font-size: 13px; font-weight: 700; "
            f"color: {C.KREDIT}; background: transparent;")
        self.lbl_kredit.setMinimumWidth(
            QFontMetrics(self.lbl_kredit.font()).horizontalAdvance(
                "Total Kredit: Rp999.999.999.999") + 8)
        pl.addWidget(self.lbl_kredit)
        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("font-weight: 700; background: transparent;")
        pl.addWidget(self.lbl_status)
        pl.addStretch()
        l.addWidget(self.panel)

        aksi = QHBoxLayout()
        aksi.addStretch()
        b = w.tombol("Batal")
        b.clicked.connect(self.reject)
        aksi.addWidget(b)
        bs = w.tombol("Simpan Saldo Awal", gaya="primary")
        bs.clicked.connect(self._simpan)
        aksi.addWidget(bs)
        l.addLayout(aksi)

        self._muat()

    def _muat(self):
        akun = [a for a in services.list_accounts(self.ctx.company_id)
                if a["tipe"] in ("Aset", "Liabilitas", "Ekuitas")]
        self.tabel.setRowCount(len(akun))
        for i, a in enumerate(akun):
            self.tabel.setItem(i, 0, QTableWidgetItem(a["kode"]))
            self.tabel.setItem(i, 1, QTableWidgetItem(a["nama"]))
            self.tabel.setItem(i, 2, QTableWidgetItem(a["normal"]))
            inp = w.InputRupiah()
            inp.set_nilai(a["saldo_awal"])
            inp.valueChanged.connect(self._update_total)
            self.inputs[a["kode"]] = inp
            self.tabel.setCellWidget(i, 3, inp)
        self._update_total()

    def _update_total(self):
        total_d = total_k = 0
        for kode, inp in self.inputs.items():
            akun = services.get_account(self.ctx.company_id, kode)
            if not akun:
                continue
            if akun["normal"] == "Debit":
                total_d += inp.nilai()
            else:
                total_k += inp.nilai()
        self.lbl_debit.setText(f"Total Debit: {theme.money(total_d)}")
        self.lbl_kredit.setText(f"Total Kredit: {theme.money(total_k)}")
        selisih = total_d - total_k
        if selisih == 0:
            self.lbl_status.setText("SEIMBANG")
            self.lbl_status.setStyleSheet(
                f"color: {C.SUCCESS}; font-weight: 700; background: transparent;")
            theme.latar(self.panel, f"background: {C.SUCCESS_BG}; border: 1px solid #B8E6D5; "
                "border-radius: 8px;")
        else:
            self.lbl_status.setText(f"TIDAK SEIMBANG - selisih {theme.money(abs(selisih))}")
            self.lbl_status.setStyleSheet(
                f"color: {C.DANGER}; font-weight: 700; background: transparent;")
            theme.latar(self.panel, f"background: {C.DANGER_BG}; border: 1px solid #F5C2C2; "
                "border-radius: 8px;")

    def _simpan(self):
        try:
            total_d = total_k = 0
            for kode, inp in self.inputs.items():
                akun = services.get_account(self.ctx.company_id, kode)
                if not akun:
                    continue
                if akun["normal"] == "Debit":
                    total_d += inp.nilai()
                else:
                    total_k += inp.nilai()
            if total_d != total_k:
                if QMessageBox.question(
                        self, "Saldo awal tidak seimbang",
                        f"Total debit {theme.money(total_d)} ≠ total kredit "
                        f"{theme.money(total_k)} (selisih "
                        f"{theme.money(abs(total_d - total_k))}).\n\n"
                        "Neraca akan pincang bila disimpan. Tetap simpan?",
                        QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
                    return
            saldo = {kode: inp.nilai() for kode, inp in self.inputs.items()}
            services.set_saldo_awal(self.ctx.company_id, saldo)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Gagal menyimpan", str(e))


# ==========================================================================
# HALAMAN DATA PERUSAHAAN
# ==========================================================================
class PerusahaanPage(QWidget):
    pindah_halaman = Signal(str)

    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx

        luar = QVBoxLayout(self)
        luar.setContentsMargins(0, 0, 0, 0)
        luar.setSpacing(0)

        self.header = w.PageHeader(
            "Data Perusahaan",
            "Profil entitas dan pengaturan skema perpajakan. Data ini menentukan "
            "perhitungan pajak dan format laporan.")

        kepala = QWidget()
        theme.latar(kepala, f"background: {C.SURFACE}; "
                             f"border-bottom: 1px solid {C.BORDER};")
        kl = QVBoxLayout(kepala)
        kl.setContentsMargins(26, 20, 26, 18)
        kl.addWidget(self.header)
        luar.addWidget(kepala)

        self.isi = QWidget()
        self.lay = QVBoxLayout(self.isi)
        self.lay.setContentsMargins(24, 20, 24, 22)
        self.lay.setSpacing(14)
        luar.addWidget(w.scroll(self.isi), 1)

    def muat(self):
        while self.lay.count():
            it = self.lay.takeAt(0)
            wdg = it.widget()
            if wdg is not None:
                wdg.setParent(None)
                wdg.deleteLater()
            elif it.layout():
                self._bersihkan_layout(it.layout())

        if not self.ctx.company_id:
            self.lay.addWidget(self._form_perusahaan_baru())
            self.lay.addStretch()
            return

        comp = services.get_company(self.ctx.company_id)
        if comp is None:
            self.lay.addWidget(self._form_perusahaan_baru())
            self.lay.addStretch()
            return

        self.lay.addWidget(self._kartu_identitas(comp))
        self.lay.addWidget(self._kartu_pajak(comp))
        self.lay.addWidget(self._kartu_bentuk_badan(comp))
        self.lay.addStretch()

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
    def _form_perusahaan_baru(self) -> QWidget:
        kartu = w.Card(padding=30)
        l = kartu.body()
        l.setSpacing(15)

        j = QLabel("Buat Profil Perusahaan")
        j.setStyleSheet("font-size: 19px; font-weight: 700; background: transparent;")
        l.addWidget(j)

        ket = QLabel(
            "Langkah pertama sebelum mencatat transaksi. Aplikasi akan menyiapkan "
            "bagan akun otomatis sesuai bentuk badan usaha yang Anda pilih."
        )
        ket.setWordWrap(True)
        ket.setStyleSheet(f"font-size: {theme.FS_BODY}px; color: {C.TEXT_MUTED}; "
                          "background: transparent;")
        l.addWidget(ket)

        g = QGridLayout()
        g.setSpacing(12)
        g.addWidget(w.label("Nama Perusahaan / Usaha", objek="FormLabel"), 0, 0, 1, 2)
        self.inp_nama = QLineEdit()
        self.inp_nama.setPlaceholderText("mis. PT Maju Bersama")
        g.addWidget(self.inp_nama, 1, 0, 1, 2)

        g.addWidget(w.label("Bentuk Badan Usaha", objek="FormLabel"), 2, 0, 1, 2)
        # Pilihan dua baris: nama bentuk badan dan standar akuntansinya.
        # Teks satu baris gabungan menjadi terlalu panjang dan meluber.
        self.cmb_bentuk = pilihan_entitas.combo_bentuk_badan(
            config.ENTITY_TYPES)
        self.cmb_bentuk.currentIndexChanged.connect(self._update_bentuk)
        g.addWidget(self.cmb_bentuk, 3, 0, 1, 2)

        g.addWidget(w.label("NPWP", objek="FormLabel"), 4, 0)
        self.inp_npwp = QLineEdit()
        self.inp_npwp.setPlaceholderText("00.000.000.0-000.000")
        g.addWidget(self.inp_npwp, 5, 0)

        g.addWidget(w.label("Nama Pemilik / Direktur", objek="FormLabel"), 4, 1)
        self.inp_pemilik = QLineEdit()
        g.addWidget(self.inp_pemilik, 5, 1)

        g.addWidget(w.label("Alamat", objek="FormLabel"), 6, 0, 1, 2)
        self.inp_alamat = QLineEdit()
        g.addWidget(self.inp_alamat, 7, 0, 1, 2)

        g.addWidget(w.label("Kota", objek="FormLabel"), 8, 0)
        self.inp_kota = QLineEdit()
        g.addWidget(self.inp_kota, 9, 0)

        g.addWidget(w.label("Tanggal Mulai Pembukuan", objek="FormLabel"), 8, 1)
        self.inp_mulai = kalender.pasang(QDateEdit())
        self.inp_mulai.setDisplayFormat("dd/MM/yyyy")
        self.inp_mulai.setDate(QDate(datetime.now().year, 1, 1))
        g.addWidget(self.inp_mulai, 9, 1)
        l.addLayout(g)

        self.lbl_bentuk = QLabel("")
        self.lbl_bentuk.setWordWrap(True)
        theme.latar(self.lbl_bentuk, f"background: {C.PRIMARY_SOFT}; border: 1px solid #CFE0F0; "
            f"border-radius: 8px; padding: 13px 15px; font-size: {theme.FS_SMALL}px; "
            f"color: {C.TEXT};")
        l.addWidget(self.lbl_bentuk)

        b = w.tombol("Buat Perusahaan", gaya="primary")
        b.setMinimumHeight(42)
        b.clicked.connect(self._buat)
        l.addWidget(b)

        self._update_bentuk()
        return kartu

    def _update_bentuk(self):
        kode = self.cmb_bentuk.currentData()
        info = config.ENTITY_TYPES.get(kode, {})
        teks = (f"<b>{info.get('nama', '')}</b><br>{info.get('deskripsi', '')}"
                f"<br><br><b>Standar akuntansi:</b> {info.get('sak', '-')}"
                f"<br><b>Laporan yang dihasilkan:</b> "
                f"{', '.join(info.get('laporan', []))}"
                f"<br><b>Skema pajak umum:</b> {info.get('pajak_default', '-')}")
        if hasattr(self, "lbl_bentuk"):
            self.lbl_bentuk.setText(teks)
            self.lbl_bentuk.setTextFormat(Qt.RichText)

    def _buat(self):
        try:
            if not self.inp_nama.text().strip():
                QMessageBox.warning(self, "Nama kosong", "Isi nama perusahaan.")
                return
            cid = services.create_company(
                self.inp_nama.text().strip(),
                self.cmb_bentuk.currentData(),
                npwp=self.inp_npwp.text().strip(),
                nama_pemilik=self.inp_pemilik.text().strip(),
                alamat=self.inp_alamat.text().strip(),
                kota=self.inp_kota.text().strip(),
                tahun_buku_awal=self.inp_mulai.date().toString("yyyy-MM-dd"),
                lisensi=self.ctx.lisensi,
            )
            self.ctx.company_id = cid
            self.ctx.company = services.get_company(cid)
            QMessageBox.information(
                self, "Perusahaan dibuat",
                f"Profil '{self.inp_nama.text().strip()}' berhasil dibuat.\n\n"
                "Bagan akun telah disiapkan otomatis. Langkah berikutnya:\n"
                "1. Isi saldo awal pada menu Bagan Akun\n"
                "2. Lengkapi pengaturan pajak di halaman ini\n"
                "3. Mulai catat transaksi")
            self.muat()
            self.pindah_halaman.emit("coa")
        except Exception as e:
            QMessageBox.critical(self, "Gagal membuat perusahaan", str(e))

    # ------------------------------------------------------------------
    def _kartu_identitas(self, comp) -> QWidget:
        kartu = w.Card()
        l = kartu.body()

        baris = QHBoxLayout()
        j = QLabel("Identitas Perusahaan")
        j.setObjectName("SectionTitle")
        baris.addWidget(j)
        baris.addStretch()
        b = w.tombol("Ubah Identitas", ikon="pengaturan")
        b.clicked.connect(self._ubah_identitas)
        baris.addWidget(b)
        l.addLayout(baris)

        grid = QGridLayout()
        grid.setSpacing(14)
        data = [
            ("Nama Perusahaan", comp["nama"]),
            ("Bentuk Badan", config.ENTITY_TYPES.get(comp["bentuk"], {}).get("nama", comp["bentuk"])),
            ("NPWP", comp["npwp"] or ""),
            ("Nama Pemilik / Direktur", comp["nama_pemilik"] or ""),
            ("Alamat", comp["alamat"] or ""),
            ("Kota", comp["kota"] or ""),
            ("Telepon", comp["telepon"] or ""),
            ("Email", comp["email"] or ""),
            ("Mulai Pembukuan", theme.tanggal_id(comp["tahun_buku_awal"]) if comp["tahun_buku_awal"] else ""),
            ("Standar Akuntansi", config.ENTITY_TYPES.get(comp["bentuk"], {}).get("sak", "")),
        ]
        for i, (label, nilai) in enumerate(data):
            kotak = QWidget()
            kl = QVBoxLayout(kotak)
            kl.setContentsMargins(0, 0, 0, 0)
            kl.setSpacing(2)
            lb = QLabel(label.upper())
            lb.setObjectName("KpiLabel")
            kl.addWidget(lb)
            vl = QLabel(str(nilai))
            vl.setWordWrap(True)
            vl.setStyleSheet(f"font-size: {theme.FS_BODY}px; background: transparent;")
            kl.addWidget(vl)
            grid.addWidget(kotak, i // 3, i % 3)
        l.addLayout(grid)
        return kartu

    def _kartu_pajak(self, comp) -> QWidget:
        kartu = w.Card()
        l = kartu.body()

        baris = QHBoxLayout()
        j = QLabel("Pengaturan Perpajakan")
        j.setObjectName("SectionTitle")
        baris.addWidget(j)
        baris.addStretch()
        b = w.tombol("Ubah Pengaturan Pajak", ikon="pengaturan")
        b.clicked.connect(self._ubah_pajak)
        baris.addWidget(b)
        l.addLayout(baris)

        omzet = 0
        try:
            from ...core import accounting as acc
            omzet = acc.omzet_setahun(comp["id"], self.ctx.tahun)
        except Exception:
            pass
        st = tx.status_pkp(omzet, bool(comp["status_pkp"]))
        l.addWidget(w.InfoBanner(st["pesan"], st["level"],
                                 f"Status PKP: {st['status']}"))

        grid = QGridLayout()
        grid.setSpacing(14)
        skema_label = {
            "pasal31e": "Ketentuan Umum / Pasal 31E (tarif 22%, fasilitas 11%)",
            "final_umkm": "PPh Final UMKM 0,5% (PP 20/2026)",
            "umum": "Tarif Umum 22%",
        }.get(comp["skema_pph"], comp["skema_pph"])

        data = [
            ("Status PKP", "Ya - wajib memungut PPN" if comp["status_pkp"] else "Tidak"),
            ("Nomor PKP", comp["nomor_pkp"] or ""),
            ("Skema PPh", skema_label),
            ("Kelayakan Final 0,5%", "Sudah dikonfirmasi" if comp["final_eligible"]
             else "Belum dikonfirmasi"),
            ("Omzet Tahun Ini", theme.money(omzet)),
            ("Batas Wajib PKP", theme.money(config.THRESHOLD_PKP)),
            ("Progres ke Batas PKP",
             f"{omzet / config.THRESHOLD_PKP * 100:.1f}%"),
            ("Omzet Tahun Lalu", theme.money(comp["omzet_prev_year"])),
        ]
        for i, (label, nilai) in enumerate(data):
            kotak = QWidget()
            kl = QVBoxLayout(kotak)
            kl.setContentsMargins(0, 0, 0, 0)
            kl.setSpacing(2)
            lb = QLabel(label.upper())
            lb.setObjectName("KpiLabel")
            kl.addWidget(lb)
            vl = QLabel(str(nilai))
            vl.setWordWrap(True)
            vl.setStyleSheet(f"font-size: {theme.FS_BODY}px; background: transparent;")
            kl.addWidget(vl)
            grid.addWidget(kotak, i // 4, i % 4)
        l.addLayout(grid)

        # peringatan skema final
        if comp["skema_pph"] == "final_umkm" and not comp["final_eligible"]:
            l.addWidget(w.InfoBanner(
                "Skema PPh Final 0,5% dipilih tetapi kelayakan belum dikonfirmasi. "
                "Sejak PP 20/2026, tidak semua bentuk badan masih dapat memakai skema "
                "ini. Perhitungan pajak akan memakai tarif umum sampai kelayakan "
                "dikonfirmasi.",
                "danger", "Skema final belum dikonfirmasi"))

        return kartu

    def _kartu_bentuk_badan(self, comp) -> QWidget:
        info = config.ENTITY_TYPES.get(comp["bentuk"], {})
        kartu = w.Card()
        l = kartu.body()

        j = QLabel("Tentang Bentuk Badan Usaha Anda")
        j.setObjectName("SectionTitle")
        l.addWidget(j)

        l.addWidget(w.HelpPanel(
            info.get("nama", ""),
            info.get("deskripsi", ""),
            "UU No. 40/2007 jo. UU No. 6/2023; PP No. 8/2021; "
            "UU No. 20/2008 jo. UU No. 11/2020 (UMKM)"))

        # kewajiban hukum
        l.addWidget(w.HelpPanel(
            coa.HELP_TOPICS["legal"]["judul"],
            coa.HELP_TOPICS["legal"]["isi"],
            coa.HELP_TOPICS["legal"]["dasar_hukum"]))
        return kartu

    # ------------------------------------------------------------------
    def _ubah_identitas(self):
        comp = services.get_company(self.ctx.company_id)
        if not comp:
            return
        d = DialogIdentitas(self.ctx, comp, self)
        if d.exec():
            self.muat()

    def _ubah_pajak(self):
        comp = services.get_company(self.ctx.company_id)
        if not comp:
            return
        d = DialogPengaturanPajak(self.ctx, comp, self)
        if d.exec():
            self.muat()


class DialogIdentitas(QDialog):
    def __init__(self, ctx, comp, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.setWindowTitle("Ubah Identitas Perusahaan")
        self.setMinimumWidth(620)

        l = QVBoxLayout(self)
        l.setContentsMargins(24, 22, 24, 22)
        l.setSpacing(13)

        g = QGridLayout()
        g.setSpacing(12)

        def tambah(label, nilai, baris, kolom, span=1):
            g.addWidget(w.label(label, objek="FormLabel"), baris, kolom, 1, span)
            e = QLineEdit(str(nilai or ""))
            g.addWidget(e, baris + 1, kolom, 1, span)
            return e

        self.inp_nama = tambah("Nama Perusahaan", comp["nama"], 0, 0, 2)
        self.inp_npwp = tambah("NPWP", comp["npwp"], 2, 0)
        self.inp_pemilik = tambah("Nama Pemilik / Direktur", comp["nama_pemilik"], 2, 1)
        self.inp_alamat = tambah("Alamat", comp["alamat"], 4, 0, 2)
        self.inp_kota = tambah("Kota", comp["kota"], 6, 0)
        self.inp_telepon = tambah("Telepon", comp["telepon"], 6, 1)
        self.inp_email = tambah("Email", comp["email"], 8, 0, 2)
        l.addLayout(g)

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
        try:
            services.update_company(
                self.ctx.company_id,
                nama=self.inp_nama.text().strip(),
                npwp=self.inp_npwp.text().strip(),
                nama_pemilik=self.inp_pemilik.text().strip(),
                alamat=self.inp_alamat.text().strip(),
                kota=self.inp_kota.text().strip(),
                telepon=self.inp_telepon.text().strip(),
                email=self.inp_email.text().strip(),
            )
            self.ctx.company = services.get_company(self.ctx.company_id)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Gagal menyimpan", str(e))


class DialogPengaturanPajak(QDialog):
    def __init__(self, ctx, comp, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.comp = comp
        self.setWindowTitle("Pengaturan Perpajakan")
        self.setMinimumWidth(680)

        l = QVBoxLayout(self)
        l.setContentsMargins(24, 22, 24, 22)
        l.setSpacing(14)

        j = QLabel("Pengaturan Perpajakan")
        j.setObjectName("SectionTitle")
        l.addWidget(j)

        # status PKP
        kartu1 = w.Card()
        kartu1.body().addWidget(w.label("Status Pengusaha Kena Pajak (PKP)",
                                        objek="FormLabel"))
        self.chk_pkp = QCheckBox("Perusahaan sudah dikukuhkan sebagai PKP")
        self.chk_pkp.setChecked(bool(comp["status_pkp"]))
        kartu1.body().addWidget(self.chk_pkp)

        kartu1.body().addWidget(w.label("Nomor PKP", objek="FormLabel"))
        self.inp_nomor_pkp = QLineEdit(comp["nomor_pkp"] or "")
        kartu1.body().addWidget(self.inp_nomor_pkp)

        kartu1.body().addWidget(w.HelpPanel(
            "Kapan wajib PKP?",
            "Pengusaha wajib dikukuhkan sebagai PKP bila peredaran bruto melebihi "
            "Rp4,8 miliar dalam satu tahun buku. Kewajiban memungut PPN mulai awal "
            "bulan berikutnya setelah pengukuhan.\n\n"
            "Pengusaha di bawah ambang tersebut boleh memilih menjadi PKP secara "
            "sukarela bila ingin mengkreditkan PPN masukan.",
            "PMK 197/PMK.03/2013; PP 44/2022; Pasal 9 UU PPN."))
        l.addWidget(kartu1)

        # skema PPh
        kartu2 = w.Card()
        kartu2.body().addWidget(w.label("Skema PPh Badan", objek="FormLabel"))
        self.cmb_skema = QComboBox()
        self.cmb_skema.addItem("Ketentuan Umum / Pasal 31E (tarif 22%, fasilitas 11%)",
                               "pasal31e")
        self.cmb_skema.addItem("PPh Final UMKM 0,5% (PP 20/2026)", "final_umkm")
        self.cmb_skema.addItem("Tarif Umum 22% (tanpa fasilitas)", "umum")
        i = self.cmb_skema.findData(comp["skema_pph"])
        if i >= 0:
            self.cmb_skema.setCurrentIndex(i)
        kartu2.body().addWidget(self.cmb_skema)

        kartu2.body().addWidget(w.divider())
        self.chk_final = QCheckBox(
            "Saya sudah memverifikasi bahwa perusahaan memenuhi syarat PPh Final 0,5%")
        self.chk_final.setChecked(bool(comp["final_eligible"]))
        kartu2.body().addWidget(self.chk_final)

        kartu2.body().addWidget(w.HelpPanel(
            "Syarat PPh Final UMKM 0,5%",
            "Skema ini hanya berlaku bila MEMENUHI SEMUA syarat berikut:\n\n"
            "1. Bentuk badan termasuk yang diperbolehkan PP 20/2026 "
            "(antara lain Perseroan Perorangan dan Koperasi untuk periode tertentu).\n"
            "2. Peredaran bruto tidak melebihi Rp4,8 miliar dalam satu tahun pajak.\n"
            "3. Belum melewati masa pemanfaatan yang diizinkan.\n"
            "4. Tidak termasuk penghasilan yang dikecualikan.\n\n"
            "Bagi PT/CV/Firma yang sudah memakai PP 55/2022 sebelum 2026, masih "
            "dapat menyelesaikan masa transisi. Bila ragu, konsultasikan dengan "
            "konsultan pajak atau AR KPP Anda.\n\n"
            "Aplikasi ini TIDAK menerapkan tarif final sebelum Anda mencentang "
            "konfirmasi di atas - untuk menghindari kekeliruan perhitungan.",
            "PP 55/2022 jo. PP 20/2026."))
        l.addWidget(kartu2)

        # data omzet
        kartu3 = w.Card()
        kartu3.body().addWidget(w.label("Omzet Tahun Sebelumnya", objek="FormLabel"))
        self.inp_omzet = w.InputRupiah()
        self.inp_omzet.set_nilai(comp["omzet_prev_year"])
        kartu3.body().addWidget(self.inp_omzet)
        kartu3.body().addWidget(w.label(
            "Dipakai untuk menilai kelayakan fasilitas dan kewajiban PKP.",
            objek="Faint", wrap=True))
        l.addWidget(kartu3)

        aksi = QHBoxLayout()
        aksi.addStretch()
        b = w.tombol("Batal")
        b.clicked.connect(self.reject)
        aksi.addWidget(b)
        bs = w.tombol("Simpan Pengaturan", gaya="primary")
        bs.clicked.connect(self._simpan)
        aksi.addWidget(bs)
        l.addLayout(aksi)

    def _simpan(self):
        try:
            skema = self.cmb_skema.currentData()
            if skema == "final_umkm" and not self.chk_final.isChecked():
                QMessageBox.warning(
                    self, "Konfirmasi diperlukan",
                    "Untuk memakai skema PPh Final 0,5%, Anda harus mencentang "
                    "konfirmasi bahwa perusahaan memenuhi syarat.\n\n"
                    "Bila belum yakin, pilih skema Ketentuan Umum / Pasal 31E "
                    "ini pilihan yang aman.")
                return
            services.update_company(
                self.ctx.company_id,
                status_pkp=self.chk_pkp.isChecked(),
                nomor_pkp=self.inp_nomor_pkp.text().strip(),
                skema_pph=skema,
                final_eligible=self.chk_final.isChecked(),
                omzet_prev_year=self.inp_omzet.nilai(),
            )
            self.ctx.company = services.get_company(self.ctx.company_id)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Gagal menyimpan", str(e))
