"""
AkunTuntas - Halaman Pajak Lanjutan
====================================
  • Nomor Seri Faktur Pajak (NSFP)
  • Faktur Pajak Keluaran & Masukan
  • Uang Muka / Panjar (DP)
  • Bea Meterai
  • Pajak Daerah (PBJT)
  • Kurs Mata Uang Asing
  • PPh Pasal 15
  • Jurnal Balik
"""
from __future__ import annotations

from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QTabWidget,
    QDialog, QDialogButtonBox, QFormLayout, QLineEdit, QDateEdit,
    QDoubleSpinBox, QSpinBox, QMessageBox,
)
from PySide6.QtCore import Qt, QDate

from ... import config, modules as M, modules_pajak as P, services
from ...core import tax_engine as tx
from .. import theme
from ..theme import C
from .. import widgets as w
from ... import istilah


# ==========================================================================
# DIALOG DASAR
# ==========================================================================
class DialogDasar(QDialog):
    """Kerangka dialog: form + tombol Simpan/Batal."""

    def __init__(self, judul: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(judul)
        self.setModal(True)
        self.setMinimumWidth(470)

        luar = QVBoxLayout(self)
        luar.setContentsMargins(22, 20, 22, 18)
        luar.setSpacing(14)

        judul_label = QLabel(judul)
        judul_label.setStyleSheet(
            f"font-size: 15px; font-weight: 700; color: {C.TEXT};")
        luar.addWidget(judul_label)

        self.form = QFormLayout()
        self.form.setSpacing(11)
        self.form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        luar.addLayout(self.form)

        self.tombol = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.tombol.button(QDialogButtonBox.Save).setText("Simpan")
        self.tombol.button(QDialogButtonBox.Cancel).setText("Batal")
        self.tombol.accepted.connect(self._simpan)
        self.tombol.rejected.connect(self.reject)
        luar.addWidget(self.tombol)

    def _simpan(self):
        try:
            self.simpan()
        except ValueError as e:
            QMessageBox.warning(self, "Data belum lengkap", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Gagal menyimpan", str(e))
        else:
            self.accept()

    def simpan(self):
        raise NotImplementedError


def _tanggal_edit(nilai: str = "") -> QDateEdit:
    e = QDateEdit()
    e.setCalendarPopup(True)
    e.setDisplayFormat("dd-MM-yyyy")
    e.setDate(QDate.fromString(nilai, "yyyy-MM-dd")
              if nilai else QDate.currentDate())
    return e


def _uang(maks: int = 9_999_999_999) -> QDoubleSpinBox:
    s = QDoubleSpinBox()
    s.setMaximum(float(maks))
    s.setDecimals(0)
    s.setGroupSeparatorShown(True)
    s.setPrefix("Rp ")
    s.setMinimumWidth(190)
    return s


# ==========================================================================
# DIALOG: NSFP
# ==========================================================================
class DialogNSFP(DialogDasar):
    def __init__(self, parent=None):
        super().__init__("Tambah Nomor Seri Faktur Pajak", parent)

        self.inp_tahun = QSpinBox()
        self.inp_tahun.setRange(2020, 2100)
        self.inp_tahun.setValue(datetime.now().year)
        self.form.addRow("Tahun", self.inp_tahun)

        self.inp_awal = QLineEdit()
        self.inp_awal.setPlaceholderText("010.000-26.00000001")
        self.form.addRow("Nomor Awal", self.inp_awal)

        self.inp_akhir = QLineEdit()
        self.inp_akhir.setPlaceholderText("010.000-26.00000050")
        self.form.addRow("Nomor Akhir", self.inp_akhir)

        self.inp_catatan = QLineEdit()
        self.inp_catatan.setPlaceholderText("Nomor dari DJP, misalnya")
        self.form.addRow("Catatan", self.inp_catatan)

    def simpan(self):
        P.tambah_nsfp(self.ctx_company, self.inp_tahun.value(),
                      self.inp_awal.text(), self.inp_akhir.text(),
                      self.inp_catatan.text())


# ==========================================================================
# DIALOG: FAKTUR PAJAK
# ==========================================================================
class DialogFakturPajak(DialogDasar):
    def __init__(self, company_id: int, jenis: str, parent=None):
        nama = "Keluaran" if jenis == "keluaran" else "Masukan"
        super().__init__(f"Faktur Pajak {nama}", parent)
        self.cid = company_id
        self.jenis = jenis

        self.inp_tanggal = _tanggal_edit()
        self.form.addRow("Tanggal", self.inp_tanggal)

        self.inp_nama = QLineEdit()
        self.inp_nama.setPlaceholderText("Nama lawan transaksi")
        self.form.addRow("Nama Lawan", self.inp_nama)

        self.inp_npwp = QLineEdit()
        self.inp_npwp.setPlaceholderText("00.000.000.0-000.000")
        self.form.addRow("NPWP", self.inp_npwp)

        self.inp_dpp = _uang()
        self.inp_dpp.valueChanged.connect(self._hitung)
        self.form.addRow("DPP", self.inp_dpp)

        self.inp_ppn = _uang()
        self.form.addRow("PPN", self.inp_ppn)

        self.inp_seri = QLineEdit()
        self.inp_seri.setPlaceholderText("Kosongkan untuk otomatis dari NSFP")
        self.form.addRow("Nomor Seri", self.inp_seri)

        self.inp_ket = QLineEdit()
        self.form.addRow("Keterangan", self.inp_ket)

    def _hitung(self):
        dpp = self.inp_dpp.value()
        self.inp_ppn.setValue(round(dpp * config.RATE_VAT_EFFECTIVE_NORMAL))

    def simpan(self):
        P.buat_faktur_pajak(
            self.cid, self.jenis,
            self.inp_tanggal.date().toString("yyyy-MM-dd"),
            self.inp_nama.text(), self.inp_dpp.value(), self.inp_ppn.value(),
            lawan_npwp=self.inp_npwp.text(), nomor_seri=self.inp_seri.text(),
            keterangan=self.inp_ket.text())


# ==========================================================================
# DIALOG: UANG MUKA
# ==========================================================================
class DialogUangMuka(DialogDasar):
    def __init__(self, company_id: int, jenis: str, parent=None):
        judul = ("Uang Muka Diterima" if jenis == "diterima"
                 else "Uang Muka Dibayar")
        super().__init__(judul, parent)
        self.cid = company_id
        self.jenis = jenis

        self.inp_tanggal = _tanggal_edit()
        self.form.addRow("Tanggal", self.inp_tanggal)

        self.cmb_mitra = QComboBox()
        self.cmb_mitra.addItem("Tanpa mitra", None)
        tipe = "customer" if jenis == "diterima" else "vendor"
        for m in M.daftar_mitra(company_id, tipe):
            self.cmb_mitra.addItem(m["nama"], m["id"])
        self.form.addRow("Mitra", self.cmb_mitra)

        self.inp_nama = QLineEdit()
        self.inp_nama.setPlaceholderText("Nama pihak (bila bukan mitra)")
        self.form.addRow("Nama Lain", self.inp_nama)

        self.inp_jumlah = _uang()
        self.form.addRow("Jumlah", self.inp_jumlah)

        self.cmb_kas = QComboBox()
        for a in services.list_accounts(company_id):
            if a["tipe"] == "Aset" and a["kode"].startswith(("1001", "1002", "1003", "1004")):
                self.cmb_kas.addItem(f"{a['kode']} - {a['nama']}", a["kode"])
        self.form.addRow("Kas/Bank", self.cmb_kas)

        self.inp_ket = QLineEdit()
        self.form.addRow("Keterangan", self.inp_ket)

    def simpan(self):
        P.buat_uang_muka(
            self.cid, self.jenis,
            self.inp_tanggal.date().toString("yyyy-MM-dd"),
            self.inp_jumlah.value(), partner_id=self.cmb_mitra.currentData(),
            nama_lawan=self.inp_nama.text(),
            akun_kas=self.cmb_kas.currentData() or "1001",
            keterangan=self.inp_ket.text())


# ==========================================================================
# DIALOG: BEA METERAI
# ==========================================================================
class DialogMeterai(DialogDasar):
    def __init__(self, company_id: int, parent=None):
        super().__init__("Catat Bea Meterai", parent)
        self.cid = company_id

        self.inp_tanggal = _tanggal_edit()
        self.form.addRow("Tanggal", self.inp_tanggal)

        self.inp_dokumen = QLineEdit()
        self.inp_dokumen.setPlaceholderText("Misalnya: Perjanjian Kerja Sama")
        self.form.addRow("Nama Dokumen", self.inp_dokumen)

        self.inp_nilai = _uang()
        self.inp_nilai.valueChanged.connect(self._hitung)
        self.form.addRow("Nilai Dokumen", self.inp_nilai)

        self.inp_berkas = QSpinBox()
        self.inp_berkas.setRange(1, 1000)
        self.inp_berkas.valueChanged.connect(self._hitung)
        self.form.addRow("Jumlah Berkas", self.inp_berkas)

        self.lbl_total = QLabel("Rp 0")
        self.lbl_total.setStyleSheet(
            f"font-weight: 700; color: {C.PRIMARY}; font-size: 14px;")
        self.form.addRow("Bea Meterai", self.lbl_total)

        self.inp_ket = QLineEdit()
        self.form.addRow("Keterangan", self.inp_ket)

    def _hitung(self):
        h = tx.hitung_meterai(self.inp_nilai.value(),
                              self.inp_berkas.value())
        self.lbl_total.setText(theme.money(h["total"]))

    def simpan(self):
        P.catat_meterai(self.cid,
                        self.inp_tanggal.date().toString("yyyy-MM-dd"),
                        self.inp_dokumen.text(), self.inp_nilai.value(),
                        self.inp_berkas.value(), keterangan=self.inp_ket.text())


# ==========================================================================
# DIALOG: PAJAK DAERAH
# ==========================================================================
class DialogPajakDaerah(DialogDasar):
    def __init__(self, company_id: int, parent=None):
        super().__init__("Catat Pajak Daerah", parent)
        self.cid = company_id

        self.inp_tanggal = _tanggal_edit()
        self.form.addRow("Tanggal", self.inp_tanggal)

        self.cmb_jenis = QComboBox()
        for kode, nama, _ in config.PBJT_JENIS:
            self.cmb_jenis.addItem(nama, kode)
        self.cmb_jenis.currentIndexChanged.connect(self._hitung)
        self.form.addRow("Jenis", self.cmb_jenis)

        self.inp_dpp = _uang()
        self.inp_dpp.valueChanged.connect(self._hitung)
        self.form.addRow("Dasar Pengenaan", self.inp_dpp)

        self.inp_tarif = QDoubleSpinBox()
        self.inp_tarif.setRange(0, 30)
        self.inp_tarif.setDecimals(2)
        self.inp_tarif.setSuffix(" %")
        self.inp_tarif.setValue(10)
        self.inp_tarif.valueChanged.connect(self._hitung)
        self.form.addRow("Tarif", self.inp_tarif)

        self.lbl_pajak = QLabel("Rp 0")
        self.lbl_pajak.setStyleSheet(
            f"font-weight: 700; color: {C.PRIMARY}; font-size: 14px;")
        self.form.addRow("Pajak", self.lbl_pajak)

        self.inp_ket = QLineEdit()
        self.form.addRow("Keterangan", self.inp_ket)

    def _hitung(self):
        try:
            h = tx.hitung_pbjt(self.cmb_jenis.currentData(),
                               self.inp_dpp.value(), self.inp_tarif.value())
            self.lbl_pajak.setText(theme.money(h["pajak"]))
        except ValueError:
            self.lbl_pajak.setText("Rp 0")

    def simpan(self):
        P.catat_pajak_daerah(
            self.cid, self.cmb_jenis.currentData(),
            self.inp_tanggal.date().toString("yyyy-MM-dd"),
            self.inp_dpp.value(), self.inp_tarif.value(),
            keterangan=self.inp_ket.text())


# ==========================================================================
# DIALOG: KURS
# ==========================================================================
class DialogKurs(DialogDasar):
    def __init__(self, company_id: int, parent=None):
        super().__init__("Tambah Kurs", parent)
        self.cid = company_id

        self.cmb_uang = QComboBox()
        for k in config.MATA_UANG:
            if k != "IDR":
                self.cmb_uang.addItem(k, k)
        self.form.addRow("Mata Uang", self.cmb_uang)

        self.inp_tanggal = _tanggal_edit()
        self.form.addRow("Tanggal", self.inp_tanggal)

        self.inp_kurs = QDoubleSpinBox()
        self.inp_kurs.setRange(0.01, 1_000_000)
        self.inp_kurs.setDecimals(2)
        self.inp_kurs.setGroupSeparatorShown(True)
        self.inp_kurs.setPrefix("Rp ")
        self.inp_kurs.setValue(config.KURS_CONTOH.get("USD", 16_000))
        self.form.addRow("Kurs", self.inp_kurs)

        self.inp_ket = QLineEdit()
        self.form.addRow("Keterangan", self.inp_ket)

    def simpan(self):
        P.set_kurs(self.cid, self.cmb_uang.currentData(),
                   self.inp_tanggal.date().toString("yyyy-MM-dd"),
                   self.inp_kurs.value(), self.inp_ket.text())


# ==========================================================================
# DIALOG: PPh 15
# ==========================================================================
class DialogPPh15(DialogDasar):
    def __init__(self, company_id: int, parent=None):
        super().__init__("Catat PPh Pasal 15", parent)
        self.cid = company_id

        self.inp_tanggal = _tanggal_edit()
        self.form.addRow("Tanggal", self.inp_tanggal)

        self.cmb_jenis = QComboBox()
        for kode, nama, label, _, _ in tx.PPH15_JENIS:
            self.cmb_jenis.addItem(f"{nama} - {label}", kode)
        self.cmb_jenis.currentIndexChanged.connect(self._hitung)
        self.form.addRow("Jenis Usaha", self.cmb_jenis)

        self.inp_bruto = _uang()
        self.inp_bruto.valueChanged.connect(self._hitung)
        self.form.addRow("Peredaran Bruto", self.inp_bruto)

        self.lbl_pph = QLabel("Rp 0")
        self.lbl_pph.setStyleSheet(
            f"font-weight: 700; color: {C.PRIMARY}; font-size: 14px;")
        self.form.addRow("PPh Terutang", self.lbl_pph)

        self.inp_ket = QLineEdit()
        self.form.addRow("Keterangan", self.inp_ket)

    def _hitung(self):
        try:
            h = tx.hitung_pph15(self.cmb_jenis.currentData(),
                                self.inp_bruto.value())
            self.lbl_pph.setText(theme.money(h["pph_terutang"]))
        except ValueError:
            self.lbl_pph.setText("Rp 0")

    def simpan(self):
        P.catat_pph15(self.cid, self.cmb_jenis.currentData(),
                      self.inp_tanggal.date().toString("yyyy-MM-dd"),
                      self.inp_bruto.value(), self.inp_ket.text())


# ==========================================================================
# HALAMAN UTAMA
# ==========================================================================
class PajakLanjutanPage(QWidget):
    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx

        luar = QVBoxLayout(self)
        luar.setContentsMargins(0, 0, 0, 0)
        luar.setSpacing(0)

        self.header = w.PageHeader(
            "Pajak Lanjutan",
            "Faktur pajak, uang muka, meterai, pajak daerah, kurs, dan PPh 15.")
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

        self.tab_nsfp = QWidget()
        self.tab_faktur = QWidget()
        self.tab_uang_muka = QWidget()
        self.tab_meterai = QWidget()
        self.tab_daerah = QWidget()
        self.tab_kurs = QWidget()
        self.tab_pph15 = QWidget()
        self.tab_balik = QWidget()

        self.tabs.addTab(self.tab_nsfp, "Nomor Seri Faktur")
        self.tabs.addTab(self.tab_faktur, "Faktur Pajak")
        self.tabs.addTab(self.tab_uang_muka, "Uang Muka")
        self.tabs.addTab(self.tab_meterai, "Bea Meterai")
        self.tabs.addTab(self.tab_daerah, "Pajak Daerah")
        self.tabs.addTab(self.tab_kurs, "Kurs")
        self.tabs.addTab(self.tab_pph15, "PPh 15")
        self.tabs.addTab(self.tab_balik, "Jurnal Balik")
        self.tabs.currentChanged.connect(self.muat)

        for t in (self.tab_nsfp, self.tab_faktur, self.tab_uang_muka,
                  self.tab_meterai, self.tab_daerah, self.tab_kurs,
                  self.tab_pph15, self.tab_balik):
            l = QVBoxLayout(t)
            l.setContentsMargins(0, 12, 0, 0)
            l.setSpacing(13)

        # Tab pertama sudah aktif sejak awal sehingga sinyal pergantian tab
        # belum terpicu; isi sekali di sini.
        self.muat()

    def _ganti_tahun(self):
        self.ctx.tahun = self.cmb_tahun.currentData()
        self.muat()

    def _bersihkan(self, widget):
        lay = widget.layout()
        while lay.count():
            it = lay.takeAt(0)
            wdg = it.widget()
            if wdg is not None:
                wdg.setParent(None)
                wdg.deleteLater()
            elif it.layout() is not None:
                self._bersihkan_layout(it.layout())

    def _bersihkan_layout(self, lay):
        while lay.count():
            it = lay.takeAt(0)
            wdg = it.widget()
            if wdg is not None:
                wdg.setParent(None)
                wdg.deleteLater()
            elif it.layout() is not None:
                self._bersihkan_layout(it.layout())

    def muat(self):
        if not self.ctx.company_id:
            idx = self.tabs.currentIndex()
            tabs = [self.tab_nsfp, self.tab_faktur, self.tab_uang_muka,
                    self.tab_meterai, self.tab_daerah, self.tab_kurs,
                    self.tab_pph15, self.tab_balik]
            self._bersihkan(tabs[idx])
            tabs[idx].layout().addWidget(w.InfoBanner(
                "Belum ada perusahaan. Buat profil perusahaan terlebih dahulu.",
                "warning", "Data belum tersedia"))
            return
        idx = self.tabs.currentIndex()
        fungsi = [self._isi_nsfp, self._isi_faktur, self._isi_uang_muka,
                  self._isi_meterai, self._isi_daerah, self._isi_kurs,
                  self._isi_pph15, self._isi_balik]
        fungsi[idx]()

    def _baris_aksi(self, label, aksi):
        baris = QHBoxLayout()
        baris.addWidget(w.tombol(label, gaya="primary", ikon="tambah"))
        baris.addStretch(1)
        return baris

    # ----------------------------------------------------------------- NSFP
    def _isi_nsfp(self):
        self._bersihkan(self.tab_nsfp)
        lay = self.tab_nsfp.layout()
        cid = self.ctx.company_id

        sisa = P.nsfp_tersedia(cid, self.ctx.tahun)
        lay.addWidget(w.InfoBanner(
            f"Sisa nomor seri faktur pajak yang belum dipakai pada tahun "
            f"{self.ctx.tahun}: {sisa} nomor. Nomor seri diberikan oleh DJP "
            "kepada Pengusaha Kena Pajak dan wajib dipakai berurutan.",
            "info", "Nomor Seri Faktur Pajak"))

        lay.addLayout(self._baris_aksi("Tambah Nomor Seri", self._tambah_nsfp))

        t = w.Tabel([("Tahun", 80), ("Nomor Awal", 210), ("Nomor Akhir", 210),
                     ("Catatan", -1)])
        baris = [[d["tahun"], d["nomor_awal"], d["nomor_akhir"],
                  d["catatan"] or ""] for d in P.daftar_nsfp(cid)]
        t.isi(baris)
        lay.addWidget(t, 1)

    def _tambah_nsfp(self):
        d = DialogNSFP(self)
        d.ctx_company = self.ctx.company_id
        if d.exec() == QDialog.Accepted:
            self.muat()

    # --------------------------------------------------------------- FAKTUR
    def _isi_faktur(self):
        self._bersihkan(self.tab_faktur)
        lay = self.tab_faktur.layout()
        cid, tahun = self.ctx.company_id, self.ctx.tahun

        rekap = P.rekap_faktur_pajak(cid, tahun)
        selisih = rekap["selisih_ppn"]
        pesan = (f"Faktur keluaran: {rekap['keluaran']['jumlah']} dokumen "
                 f"(PPN {theme.money(rekap['keluaran']['ppn'])}). "
                 f"Faktur masukan: {rekap['masukan']['jumlah']} dokumen "
                 f"(PPN {theme.money(rekap['masukan']['ppn'])}). "
                 f"PPN kurang bayar: {theme.money(selisih)}.")
        lay.addWidget(w.InfoBanner(
            pesan, "warning" if selisih > 0 else "success",
            f"Rekap Faktur Pajak {tahun}"))

        baris = QHBoxLayout()
        b1 = w.tombol("Tambah Keluaran", gaya="primary", ikon="tambah")
        b1.clicked.connect(lambda: self._tambah_faktur("keluaran"))
        baris.addWidget(b1)
        b2 = w.tombol("Tambah Masukan", gaya="sekunder", ikon="tambah")
        b2.clicked.connect(lambda: self._tambah_faktur("masukan"))
        baris.addWidget(b2)
        baris.addStretch(1)
        lay.addLayout(baris)

        t = w.Tabel([("Tanggal", 115), ("Jenis", 100), ("Nomor Seri", 175),
                     ("Lawan Transaksi", -1), ("NPWP", 175),
                     ("DPP", 130), ("PPN", 130), ("Status", 105)])
        baris_data = []
        for d in P.daftar_faktur_pajak(cid, tahun=tahun):
            baris_data.append([
                theme.tanggal_id(d["tanggal"]),
                "Keluaran" if d["jenis"] == "keluaran" else "Masukan",
                d["nomor_seri"] or "", d["lawan_nama"],
                d["lawan_npwp"] or "", theme.money(d["dpp"]),
                theme.money(d["ppn"]),
                istilah.label("status_faktur", d["status"]),
            ])
        t.isi(baris_data)
        lay.addWidget(t, 1)

    def _tambah_faktur(self, jenis):
        d = DialogFakturPajak(self.ctx.company_id, jenis, self)
        if d.exec() == QDialog.Accepted:
            self.muat()

    # ------------------------------------------------------------ UANG MUKA
    def _isi_uang_muka(self):
        self._bersihkan(self.tab_uang_muka)
        lay = self.tab_uang_muka.layout()
        cid = self.ctx.company_id

        diterima = P.daftar_uang_muka(cid, "diterima")
        dibayar = P.daftar_uang_muka(cid, "dibayar")
        sisa_diterima = sum(int(d["jumlah"]) - int(d["terpakai"])
                            for d in diterima)
        sisa_dibayar = sum(int(d["jumlah"]) - int(d["terpakai"])
                           for d in dibayar)
        lay.addWidget(w.InfoBanner(
            f"Sisa uang muka diterima dari pelanggan: "
            f"{theme.money(sisa_diterima)}. Sisa uang muka dibayar ke pemasok: "
            f"{theme.money(sisa_dibayar)}. Uang muka dapat dipakai untuk "
            "melunasi invoice atau tagihan pemasok.",
            "info", "Uang Muka / Panjar"))

        baris = QHBoxLayout()
        b1 = w.tombol("Uang Muka Diterima", gaya="primary", ikon="tambah")
        b1.clicked.connect(lambda: self._tambah_dp("diterima"))
        baris.addWidget(b1)
        b2 = w.tombol("Uang Muka Dibayar", gaya="sekunder", ikon="tambah")
        b2.clicked.connect(lambda: self._tambah_dp("dibayar"))
        baris.addWidget(b2)
        baris.addStretch(1)
        lay.addLayout(baris)

        t = w.Tabel([("Nomor", 120), ("Jenis", 105), ("Tanggal", 115),
                     ("Pihak", -1), ("Jumlah", 145), ("Terpakai", 140),
                     ("Sisa", 140)])
        baris_data = []
        for d in P.daftar_uang_muka(cid):
            sisa = int(d["jumlah"]) - int(d["terpakai"])
            baris_data.append([
                d["nomor"] or "",
                "Diterima" if d["jenis"] == "diterima" else "Dibayar",
                theme.tanggal_id(d["tanggal"]), d["nama_lawan"],
                theme.money(d["jumlah"]), theme.money(d["terpakai"]),
                theme.money(sisa),
            ])
        t.isi(baris_data)
        lay.addWidget(t, 1)

    def _tambah_dp(self, jenis):
        d = DialogUangMuka(self.ctx.company_id, jenis, self)
        if d.exec() == QDialog.Accepted:
            self.muat()

    # --------------------------------------------------------------- METERAI
    def _isi_meterai(self):
        self._bersihkan(self.tab_meterai)
        lay = self.tab_meterai.layout()
        cid, tahun = self.ctx.company_id, self.ctx.tahun

        daftar = P.daftar_meterai(cid, tahun)
        total = sum(int(d["total"]) for d in daftar)
        lay.addWidget(w.InfoBanner(
            f"Bea meterai Rp10.000 dikenakan pada dokumen bernilai di atas "
            f"Rp5.000.000. Dokumen bernilai sampai Rp300.000 tidak dikenai. "
            f"Total bea meterai tahun {tahun}: {theme.money(total)}. "
            "Dasar hukum: UU No. 10/2020 dan PP 86/2021.",
            "info", "Bea Meterai"))

        lay.addLayout(self._baris_aksi("Catat Bea Meterai",
                                       self._tambah_meterai))

        t = w.Tabel([("Tanggal", 115), ("Dokumen", -1),
                     ("Nilai Dokumen", 165), ("Berkas", 85),
                     ("Tarif", 120), ("Total", 130)])
        t.isi([[theme.tanggal_id(d["tanggal"]), d["dokumen"],
                theme.money(d["nilai_dokumen"]), d["jumlah_berkas"],
                theme.money(d["tarif"]), theme.money(d["total"])]
               for d in daftar])
        lay.addWidget(t, 1)

    def _tambah_meterai(self):
        d = DialogMeterai(self.ctx.company_id, self)
        if d.exec() == QDialog.Accepted:
            self.muat()

    # ---------------------------------------------------------------- DAERAH
    def _isi_daerah(self):
        self._bersihkan(self.tab_daerah)
        lay = self.tab_daerah.layout()
        cid, tahun = self.ctx.company_id, self.ctx.tahun

        daftar = P.daftar_pajak_daerah(cid, tahun)
        total = sum(int(d["pajak"]) for d in daftar)
        lay.addWidget(w.InfoBanner(
            f"Pajak Barang dan Jasa Tertentu (PBJT) menggantikan PB1 untuk "
            f"makanan/minuman, hiburan, perhotelan, dan parkir. Tarif paling "
            f"tinggi 10% dari dasar pengenaan. Total tahun {tahun}: "
            f"{theme.money(total)}. Dasar hukum: UU No. 1/2022 (HKPD).",
            "info", "Pajak Daerah"))

        lay.addLayout(self._baris_aksi("Catat Pajak Daerah",
                                       self._tambah_daerah))

        t = w.Tabel([("Tanggal", 115), ("Jenis", -1),
                     ("Dasar Pengenaan", 175), ("Tarif", 95),
                     ("Pajak", 145)])
        t.isi([[theme.tanggal_id(d["tanggal"]),
                istilah.label("pbjt", d["jenis"]),
                theme.money(d["dpp"]),
                f"{theme.persen(float(d['tarif']), 0)}",
                theme.money(d["pajak"])] for d in daftar])
        lay.addWidget(t, 1)

    def _tambah_daerah(self):
        d = DialogPajakDaerah(self.ctx.company_id, self)
        if d.exec() == QDialog.Accepted:
            self.muat()

    # ------------------------------------------------------------------ KURS
    def _isi_kurs(self):
        self._bersihkan(self.tab_kurs)
        lay = self.tab_kurs.layout()
        cid = self.ctx.company_id

        lay.addWidget(w.InfoBanner(
            "Kurs dipakai untuk mengubah transaksi valuta asing menjadi "
            "rupiah. Nilai pajak wajib dalam rupiah memakai kurs saat "
            "transaksi. Bila kurs belum dicatat, aplikasi memakai kurs "
            "indikatif dari Pengaturan. Dasar hukum: PMK 196/PMK.03/2007.",
            "info", "Kurs Mata Uang Asing"))

        lay.addLayout(self._baris_aksi("Tambah Kurs", self._tambah_kurs))

        t = w.Tabel([("Tanggal", 130), ("Mata Uang", 120), ("Kurs", -1),
                     ("Keterangan", 260)])
        t.isi([[theme.tanggal_id(d["tanggal"]), d["mata_uang"],
                theme.money(d["kurs"]), d["keterangan"] or ""]
               for d in P.daftar_kurs(cid)])
        lay.addWidget(t, 1)

    def _tambah_kurs(self):
        d = DialogKurs(self.ctx.company_id, self)
        if d.exec() == QDialog.Accepted:
            self.muat()

    # ---------------------------------------------------------------- PPh 15
    def _isi_pph15(self):
        self._bersihkan(self.tab_pph15)
        lay = self.tab_pph15.layout()
        cid, tahun = self.ctx.company_id, self.ctx.tahun

        daftar = P.daftar_pph15(cid, tahun)
        total = sum(int(d["pph"]) for d in daftar)
        lay.addWidget(w.InfoBanner(
            "PPh Pasal 15 memakai norma khusus: tarif tetap dikali peredaran "
            "bruto, tanpa menghitung laba. Dipakai perusahaan pelayaran dan "
            "penerbangan tertentu. Pajaknya bersifat final sehingga tidak "
            f"digabung ke PPh Badan. Total tahun {tahun}: "
            f"{theme.money(total)}.",
            "info", "PPh Pasal 15"))

        lay.addLayout(self._baris_aksi("Catat PPh 15", self._tambah_pph15))

        t = w.Tabel([("Tanggal", 115), ("Jenis Usaha", -1),
                     ("Peredaran Bruto", 175), ("Tarif", 95),
                     ("PPh Terutang", 150)])
        t.isi([[theme.tanggal_id(d["tanggal"]),
                istilah.label("pph15", d["jenis"]),
                theme.money(d["peredaran_bruto"]),
                f"{theme.persen(float(d['tarif']), 2)}",
                theme.money(d["pph"])] for d in daftar])
        lay.addWidget(t, 1)

    def _tambah_pph15(self):
        d = DialogPPh15(self.ctx.company_id, self)
        if d.exec() == QDialog.Accepted:
            self.muat()

    # ----------------------------------------------------------- JURNAL BALIK
    def _isi_balik(self):
        self._bersihkan(self.tab_balik)
        lay = self.tab_balik.layout()
        cid = self.ctx.company_id

        menunggu = P.daftar_jurnal_balik(cid, belum_saja=True)
        lay.addWidget(w.InfoBanner(
            "Jurnal balik membalik jurnal akrual pada awal periode berikutnya "
            "agar beban tidak dihitung dua kali. Tandai jurnal akrual dengan "
            "tanggal balik, lalu jalankan saat tanggalnya tiba. Jurnal yang "
            "tanggal baliknya belum tiba akan dilewati.",
            "info", "Jurnal Balik"))

        baris = QHBoxLayout()
        b = w.tombol("Jalankan Jurnal Balik", gaya="primary", ikon="transfer")
        b.clicked.connect(self._jalankan_balik)
        baris.addWidget(b)
        baris.addStretch(1)
        lay.addLayout(baris)

        t = w.Tabel([("Tanggal Balik", 140), ("No. Bukti", 130),
                     ("Tanggal Asli", 130), ("Keterangan", -1)])
        t.isi([[theme.tanggal_id(d["tanggal_balik"]), d["no_bukti"] or "",
                theme.tanggal_id(d["tanggal_asli"]),
                d["ket_asli"] or d["keterangan"] or ""]
               for d in menunggu])
        lay.addWidget(t, 1)

        if not menunggu:
            lay.addWidget(w.InfoBanner(
                "Belum ada jurnal balik yang menunggu. Tandai jurnal akrual "
                "dari halaman Jurnal Umum untuk memakainya.",
                "info", "Tidak ada jurnal balik"))

    def _jalankan_balik(self):
        hasil = P.jalankan_jurnal_balik(self.ctx.company_id)
        if hasil["dibuat"]:
            QMessageBox.information(
                self, "Jurnal balik dijalankan",
                f"{hasil['dibuat']} jurnal balik berhasil dibuat."
                + (f" {hasil['dilewati']} jurnal dilewati karena tanggalnya "
                   "belum tiba." if hasil["dilewati"] else ""))
        else:
            QMessageBox.information(
                self, "Belum waktunya",
                "Belum ada jurnal balik yang tanggalnya tiba."
                + (f" {hasil['dilewati']} jurnal menunggu tanggalnya."
                   if hasil["dilewati"] else ""))
        self.muat()
