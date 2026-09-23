"""
Halaman Kontrak & Kerja Sama
============================

Mencatat perjanjian dengan mitra: nomor kontrak, masa berlaku, nilai,
bentuk imbalan (termasuk barter dan tukar jasa), termin, serta dasar
hukumnya. Dokumen kontrak dapat diunggah dan isinya diringkas otomatis.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit, QDialog,
    QMessageBox, QGridLayout, QTabWidget, QFileDialog, QSpinBox, QDateEdit,
    QTextEdit, QTableWidgetItem,
)
from PySide6.QtCore import QDate

from ... import kontrak as kt
from ... import modules as M
from .. import theme, widgets as w
from ..theme import C


# ==========================================================================
# DIALOG KONTRAK
# ==========================================================================
class DialogKontrak(QDialog):
    """Formulir tambah/ubah kontrak."""

    def __init__(self, ctx, parent=None, kontrak: dict = None):
        super().__init__(parent)
        self.ctx = ctx
        self.kontrak = kontrak
        self.setWindowTitle("Ubah Kontrak" if kontrak else "Kontrak Baru")
        self.setMinimumWidth(860)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 22, 24, 22)
        lay.setSpacing(13)

        j = QLabel("Data Kontrak & Kerja Sama")
        j.setObjectName("SectionTitle")
        lay.addWidget(j)

        if ctx.beginner:
            lay.addWidget(w.HelpPanel(
                "Tentang kontrak",
                "Kontrak mencatat perjanjian dengan mitra, termasuk kerja sama "
                "yang tidak berbentuk uang seperti barter barang atau tukar "
                "jasa. Nomor kontrak dibuat otomatis dan dapat dicari kembali.\n\n"
                "• Tanggal berakhir dipakai untuk mengingatkan kontrak yang "
                "segera habis.\n"
                "• Bentuk imbalan menentukan perlakuan pajaknya.\n"
                "• Dasar hukum terisi otomatis sesuai jenis kontrak dan masih "
                "dapat disunting.",
                "KUHPerdata Pasal 1313 dan 1338; UU 7/2014 Pasal 33-51; "
                "PMK 68/2022 untuk sewa tanah/bangunan."))

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        # ---------------------------------------------------------- umum
        tab_umum = QWidget()
        g = QGridLayout(tab_umum)
        g.setContentsMargins(16, 16, 16, 16)
        g.setSpacing(12)

        g.addWidget(w.label("Nomor Kontrak", objek="FormLabel"), 0, 0)
        self.inp_nomor = QLineEdit()
        self.inp_nomor.setPlaceholderText("Kosongkan untuk nomor otomatis")
        g.addWidget(self.inp_nomor, 1, 0)

        g.addWidget(w.label("Judul Perjanjian", objek="FormLabel"), 0, 1, 1, 2)
        self.inp_judul = QLineEdit()
        self.inp_judul.setPlaceholderText("mis. Perjanjian Kerja Sama Distribusi")
        g.addWidget(self.inp_judul, 1, 1, 1, 2)

        g.addWidget(w.label("Jenis Kontrak", objek="FormLabel"), 2, 0)
        self.cmb_jenis = QComboBox()
        for kode, nama in kt.JENIS_KONTRAK.items():
            self.cmb_jenis.addItem(nama, kode)
        g.addWidget(self.cmb_jenis, 3, 0)

        g.addWidget(w.label("Bentuk Imbalan", objek="FormLabel"), 2, 1)
        self.cmb_bentuk = QComboBox()
        for kode, nama in kt.BENTUK_IMBALAN.items():
            self.cmb_bentuk.addItem(nama, kode)
        self.cmb_bentuk.currentIndexChanged.connect(self._ganti_bentuk)
        g.addWidget(self.cmb_bentuk, 3, 1)

        g.addWidget(w.label("Status", objek="FormLabel"), 2, 2)
        self.cmb_status = QComboBox()
        for kode, nama in kt.STATUS_KONTRAK.items():
            self.cmb_status.addItem(nama, kode)
        g.addWidget(self.cmb_status, 3, 2)

        g.addWidget(w.label("Pihak Kedua (Mitra)", objek="FormLabel"), 4, 0, 1, 2)
        self.cmb_mitra = QComboBox()
        self.cmb_mitra.addItem("pilih mitra atau isi manual", None)
        for m in M.daftar_mitra(ctx.company_id):
            self.cmb_mitra.addItem(f"{m['nama']} ({m['tipe']})", m["id"])
        g.addWidget(self.cmb_mitra, 5, 0, 1, 2)

        g.addWidget(w.label("Nama Mitra (bila belum terdaftar)",
                            objek="FormLabel"), 4, 2)
        self.inp_pihak2 = QLineEdit()
        g.addWidget(self.inp_pihak2, 5, 2)

        g.addWidget(w.label("Peran Kita", objek="FormLabel"), 6, 0)
        self.cmb_peran = QComboBox()
        for kode, nama in kt.PERAN.items():
            self.cmb_peran.addItem(nama, kode)
        g.addWidget(self.cmb_peran, 7, 0)

        g.addWidget(w.label("Tanggal Mulai", objek="FormLabel"), 6, 1)
        self.dt_mulai = QDateEdit()
        self.dt_mulai.setCalendarPopup(True)
        self.dt_mulai.setDisplayFormat("dd-MM-yyyy")
        self.dt_mulai.setDate(QDate.currentDate())
        g.addWidget(self.dt_mulai, 7, 1)

        g.addWidget(w.label("Tanggal Berakhir", objek="FormLabel"), 6, 2)
        baris_akhir = QHBoxLayout()
        self.chk_tanpa_akhir = QComboBox()
        self.chk_tanpa_akhir.addItem("Ada batas waktu", False)
        self.chk_tanpa_akhir.addItem("Tanpa batas waktu", True)
        self.chk_tanpa_akhir.currentIndexChanged.connect(self._ganti_akhir)
        baris_akhir.addWidget(self.chk_tanpa_akhir, 1)
        self.dt_akhir = QDateEdit()
        self.dt_akhir.setCalendarPopup(True)
        self.dt_akhir.setDisplayFormat("dd-MM-yyyy")
        self.dt_akhir.setDate(QDate.currentDate().addYears(1))
        baris_akhir.addWidget(self.dt_akhir, 1)
        g.addLayout(baris_akhir, 7, 2)

        g.addWidget(w.label("Pemberitahuan Berakhir (hari sebelum)",
                            objek="FormLabel"), 8, 0)
        self.spn_notif = QSpinBox()
        self.spn_notif.setRange(0, 365)
        self.spn_notif.setValue(30)
        g.addWidget(self.spn_notif, 9, 0)

        self.chk_perpanjangan = QComboBox()
        self.chk_perpanjangan.addItem("Tidak ada opsi perpanjangan", False)
        self.chk_perpanjangan.addItem("Ada opsi perpanjangan", True)
        g.addWidget(self.chk_perpanjangan, 9, 1, 1, 2)

        g.setColumnStretch(0, 1)
        g.setColumnStretch(1, 1)
        g.setColumnStretch(2, 1)
        self.tabs.addTab(tab_umum, "Umum")

        # --------------------------------------------------------- nilai
        tab_nilai = QWidget()
        n = QGridLayout(tab_nilai)
        n.setContentsMargins(16, 16, 16, 16)
        n.setSpacing(12)

        n.addWidget(w.label("Nilai Kontrak (Rp)", objek="FormLabel"), 0, 0)
        self.inp_nilai = w.InputRupiah()
        self.inp_nilai.setMinimumWidth(200)
        n.addWidget(self.inp_nilai, 1, 0)

        n.addWidget(w.label("Nilai Barang Barter (Rp)", objek="FormLabel"), 0, 1)
        self.inp_nilai_barang = w.InputRupiah()
        self.inp_nilai_barang.setMinimumWidth(200)
        n.addWidget(self.inp_nilai_barang, 1, 1)

        n.addWidget(w.label("Nilai Jasa Ditukar (Rp)", objek="FormLabel"), 0, 2)
        self.inp_nilai_jasa = w.InputRupiah()
        self.inp_nilai_jasa.setMinimumWidth(200)
        n.addWidget(self.inp_nilai_jasa, 1, 2)

        n.addWidget(w.label("Skema Pembayaran", objek="FormLabel"), 2, 0)
        self.cmb_skema = QComboBox()
        for kode, nama in kt.SKEMA_BAYAR.items():
            self.cmb_skema.addItem(nama, kode)
        self.cmb_skema.currentIndexChanged.connect(self._ganti_skema)
        n.addWidget(self.cmb_skema, 3, 0)

        n.addWidget(w.label("Jumlah Termin", objek="FormLabel"), 2, 1)
        self.spn_termin = QSpinBox()
        self.spn_termin.setRange(1, 60)
        self.spn_termin.setValue(1)
        n.addWidget(self.spn_termin, 3, 1)

        n.addWidget(w.label("Jarak Termin (hari)", objek="FormLabel"), 2, 2)
        self.spn_jarak = QSpinBox()
        self.spn_jarak.setRange(1, 730)
        self.spn_jarak.setValue(30)
        n.addWidget(self.spn_jarak, 3, 2)

        n.addWidget(w.label("Persentase Bagi Hasil (%)", objek="FormLabel"), 4, 0)
        self.inp_bagi = w.InputPersen()
        n.addWidget(self.inp_bagi, 5, 0)

        n.addWidget(w.label("Kena PPN", objek="FormLabel"), 4, 1)
        self.cmb_ppn = QComboBox()
        self.cmb_ppn.addItem("Tidak kena PPN", False)
        self.cmb_ppn.addItem("Kena PPN", True)
        n.addWidget(self.cmb_ppn, 5, 1)

        self.lbl_pajak = QLabel()
        self.lbl_pajak.setObjectName("Muted")
        self.lbl_pajak.setWordWrap(True)
        n.addWidget(self.lbl_pajak, 6, 0, 1, 3)
        self.inp_nilai.textChanged.connect(self._perbarui_pajak)
        self.cmb_ppn.currentIndexChanged.connect(self._perbarui_pajak)

        n.setColumnStretch(0, 1)
        n.setColumnStretch(1, 1)
        n.setColumnStretch(2, 1)
        self.tabs.addTab(tab_nilai, "Nilai & Pajak")

        # -------------------------------------------------- barang/jasa
        tab_item = QWidget()
        it = QVBoxLayout(tab_item)
        it.setContentsMargins(16, 16, 16, 16)
        it.setSpacing(10)
        it.addWidget(w.label(
            "Daftar barang atau jasa yang dipertukarkan. Diisi untuk kerja "
            "sama barter atau tukar jasa.", objek="Muted", wrap=True))

        self.tabel_item = w.Tabel([
            ("Arah", 110), ("Nama Barang/Jasa", -1), ("Jumlah", 90),
            ("Satuan", 90), ("Nilai Satuan", 140), ("Total", 140)])
        it.addWidget(self.tabel_item, 1)

        baris_it = QHBoxLayout()
        b_tambah_item = w.tombol("Tambah Baris", gaya="biasa", ikon="+")
        b_tambah_item.clicked.connect(self._tambah_item)
        baris_it.addWidget(b_tambah_item)
        b_hapus_item = w.tombol("Hapus Baris", gaya="biasa")
        b_hapus_item.clicked.connect(self._hapus_item)
        baris_it.addWidget(b_hapus_item)
        baris_it.addStretch()
        it.addLayout(baris_it)
        self.tabs.addTab(tab_item, "Barang & Jasa")

        # ----------------------------------------------------- dokumen
        tab_dok = QWidget()
        d = QVBoxLayout(tab_dok)
        d.setContentsMargins(16, 16, 16, 16)
        d.setSpacing(10)
        d.addWidget(w.label(
            "Unggah berkas kontrak (PDF, DOCX, atau TXT). Isinya akan dibaca "
            "dan diisi otomatis ke formulir, lalu dapat Anda periksa.",
            objek="Muted", wrap=True))

        baris_dok = QHBoxLayout()
        self.inp_dokumen = QLineEdit()
        self.inp_dokumen.setReadOnly(True)
        self.inp_dokumen.setPlaceholderText("Belum ada berkas dipilih")
        baris_dok.addWidget(self.inp_dokumen, 1)
        b_pilih = w.tombol("Pilih Berkas", gaya="biasa", ikon="dokumen")
        b_pilih.clicked.connect(self._pilih_dokumen)
        baris_dok.addWidget(b_pilih)
        b_baca = w.tombol("Baca & Isi Otomatis", gaya="primary", ikon="pengaturan")
        b_baca.clicked.connect(self._baca_dokumen)
        baris_dok.addWidget(b_baca)
        d.addLayout(baris_dok)

        self.txt_urai = QTextEdit()
        self.txt_urai.setReadOnly(True)
        self.txt_urai.setPlaceholderText(
            "Hasil pembacaan dokumen akan tampil di sini.")
        self.txt_urai.setMinimumHeight(150)
        d.addWidget(self.txt_urai, 1)
        self.tabs.addTab(tab_dok, "Dokumen")

        # ------------------------------------------------- dasar hukum
        tab_hukum = QWidget()
        h = QVBoxLayout(tab_hukum)
        h.setContentsMargins(16, 16, 16, 16)
        h.setSpacing(10)
        h.addWidget(w.label(
            "Dasar hukum terisi otomatis mengikuti jenis kontrak dan bentuk "
            "imbalannya. Sesuaikan bila perjanjian Anda merujuk pasal lain.",
            objek="Muted", wrap=True))
        self.txt_hukum = QTextEdit()
        self.txt_hukum.setMinimumHeight(180)
        h.addWidget(self.txt_hukum, 1)
        b_pulihkan = w.tombol("Isi Ulang Otomatis", gaya="biasa", ikon="segarkan")
        b_pulihkan.clicked.connect(self._isi_hukum)
        h.addWidget(b_pulihkan, 0, Qt.AlignLeft)
        self.tabs.addTab(tab_hukum, "Dasar Hukum")

        lay.addWidget(self.tabs, 1)

        # --------------------------------------------------------- aksi
        baris = QHBoxLayout()
        baris.addStretch()
        batal = w.tombol("Batal", gaya="biasa")
        batal.clicked.connect(self.reject)
        baris.addWidget(batal)
        simpan = w.tombol("Simpan Kontrak", gaya="primary", ikon="simpan")
        simpan.clicked.connect(self._simpan)
        baris.addWidget(simpan)
        lay.addLayout(baris)

        self.cmb_jenis.currentIndexChanged.connect(self._isi_hukum)
        self.cmb_bentuk.currentIndexChanged.connect(self._isi_hukum)

        if kontrak:
            self._isi_form(kontrak)
        else:
            self._isi_hukum()
            self._perbarui_pajak()

    # ------------------------------------------------------------------
    def _ganti_bentuk(self):
        bentuk = self.cmb_bentuk.currentData()
        perlu_barang = bentuk in ("barang", "barang_jasa")
        perlu_jasa = bentuk in ("jasa", "barang_jasa")
        self.inp_nilai_barang.setEnabled(perlu_barang)
        self.inp_nilai_jasa.setEnabled(perlu_jasa)
        self.tabs.setTabEnabled(2, perlu_barang or perlu_jasa or self.kontrak is not None)
        self._isi_hukum()

    def _ganti_akhir(self):
        tanpa = bool(self.chk_tanpa_akhir.currentData())
        self.dt_akhir.setEnabled(not tanpa)

    def _ganti_skema(self):
        skema = self.cmb_skema.currentData()
        bertahap = skema == "termin"
        self.spn_termin.setEnabled(bertahap)
        self.spn_jarak.setEnabled(bertahap)

    def _isi_hukum(self):
        jenis = self.cmb_jenis.currentData()
        bentuk = self.cmb_bentuk.currentData()
        self.txt_hukum.setPlainText(kt.dasar_hukum(jenis, bentuk))

    def _nilai_berlaku(self) -> int:
        """
        Nilai perjanjian yang dipakai menghitung pajak.

        Perjanjian uang memakai nilai kontrak; kerja sama non-tunai memakai
        nilai barang atau jasa yang ditukar.
        """
        nilai = self.inp_nilai.nilai() if hasattr(self.inp_nilai, "nilai") else 0
        if nilai:
            return nilai
        barang = self.inp_nilai_barang.nilai() if hasattr(self.inp_nilai_barang, "nilai") else 0
        jasa = self.inp_nilai_jasa.nilai() if hasattr(self.inp_nilai_jasa, "nilai") else 0
        return barang or jasa

    def _perbarui_pajak(self):
        nilai = self._nilai_berlaku()
        jenis = self.cmb_jenis.currentData()
        bentuk = self.cmb_bentuk.currentData()
        kena_ppn = bool(self.cmb_ppn.currentData())
        h = kt.hitung_pajak(nilai, jenis, bentuk, kena_ppn)

        if not nilai:
            self.lbl_pajak.setText(
                "Isi nilai kontrak untuk melihat perkiraan pajaknya.")
            return
        bagian = [f"Nilai Rp{theme.money(nilai)}"]
        if h["pph_pasal"]:
            bagian.append(f"{h['pph_pasal']} {h['tarif_pph']:g}% "
                          f"= Rp{theme.money(h['pph'])}")
        else:
            bagian.append("tidak ada pemotongan PPh")
        if h["kena_ppn"]:
            bagian.append(f"PPN {h['tarif_ppn']:g}% = Rp{theme.money(h['ppn'])}")
        self.lbl_pajak.setText(" · ".join(bagian))

    # ------------------------------------------------------------------
    def _tambah_item(self):
        r = self.tabel_item.rowCount()
        self.tabel_item.insertRow(r)
        for c, teks in enumerate(["kita_beri", "", "1", "unit", "0", "0"]):
            self.tabel_item.setItem(r, c, QTableWidgetItem(teks))
        self.tabel_item.setCurrentCell(r, 1)
        self.tabel_item.editItem(self.tabel_item.item(r, 1))

    def _hapus_item(self):
        r = self.tabel_item.currentRow()
        if r >= 0:
            self.tabel_item.removeRow(r)

    def _pilih_dokumen(self):
        jalur, _ = QFileDialog.getOpenFileName(
            self, "Pilih Berkas Kontrak", "",
            "Dokumen (*.pdf *.docx *.txt *.md);;Semua Berkas (*)")
        if jalur:
            self.inp_dokumen.setText(jalur)

    def _baca_dokumen(self):
        jalur = self.inp_dokumen.text().strip()
        if not jalur:
            QMessageBox.information(self, "Belum ada berkas",
                                    "Pilih berkas kontrak lebih dahulu.")
            return
        teks = kt.baca_dokumen(jalur)
        if not teks:
            QMessageBox.warning(
                self, "Tidak dapat membaca",
                "Isi berkas tidak dapat dibaca. Pastikan berkas berupa PDF "
                "berteks (bukan hasil pindai), DOCX, atau TXT.")
            return

        hasil = kt.urai_teks(teks)
        if not hasil:
            self.txt_urai.setPlainText(
                "Tidak ada data yang dapat dikenali dari dokumen ini. "
                "Silakan isi formulir secara manual.")
            return

        if hasil.get("nomor"):
            self.inp_nomor.setText(hasil["nomor"])
        if hasil.get("judul"):
            self.inp_judul.setText(hasil["judul"])
        if hasil.get("jenis"):
            i = self.cmb_jenis.findData(hasil["jenis"])
            if i >= 0:
                self.cmb_jenis.setCurrentIndex(i)
        if hasil.get("bentuk_imbalan"):
            i = self.cmb_bentuk.findData(hasil["bentuk_imbalan"])
            if i >= 0:
                self.cmb_bentuk.setCurrentIndex(i)
        if hasil.get("tanggal_mulai"):
            self.dt_mulai.setDate(QDate.fromString(hasil["tanggal_mulai"],
                                                   "yyyy-MM-dd"))
        if hasil.get("tanggal_akhir"):
            self.chk_tanpa_akhir.setCurrentIndex(0)
            self.dt_akhir.setDate(QDate.fromString(hasil["tanggal_akhir"],
                                                   "yyyy-MM-dd"))
        if hasil.get("nilai"):
            self.inp_nilai.set_nilai(hasil["nilai"])
        if hasil.get("dasar_hukum"):
            self.txt_hukum.setPlainText(hasil["dasar_hukum"])

        ringkas = "\n".join(
            f"{k.replace('_', ' ').title():20s}: {v}"
            for k, v in hasil.items())
        self.txt_urai.setPlainText(
            "Data berikut terisi otomatis dari dokumen. Periksa kembali "
            "sebelum menyimpan.\n\n" + ringkas)
        self._perbarui_pajak()

    # ------------------------------------------------------------------
    def _isi_form(self, k):
        self.inp_nomor.setText(k.get("nomor", ""))
        self.inp_judul.setText(k.get("judul", ""))
        for cmb, kunci, nilai in (
                (self.cmb_jenis, "jenis", k.get("jenis")),
                (self.cmb_bentuk, "bentuk_imbalan", k.get("bentuk_imbalan")),
                (self.cmb_status, "status", k.get("status")),
                (self.cmb_peran, "peran_kita", k.get("peran_kita")),
                (self.cmb_skema, "skema_bayar", k.get("skema_bayar"))):
            i = cmb.findData(nilai)
            if i >= 0:
                cmb.setCurrentIndex(i)
        if k.get("partner_id"):
            i = self.cmb_mitra.findData(k["partner_id"])
            if i >= 0:
                self.cmb_mitra.setCurrentIndex(i)
        self.inp_pihak2.setText(k.get("pihak_kedua", ""))
        if k.get("tanggal_mulai"):
            self.dt_mulai.setDate(QDate.fromString(k["tanggal_mulai"], "yyyy-MM-dd"))
        if k.get("tanggal_akhir"):
            self.dt_akhir.setDate(QDate.fromString(k["tanggal_akhir"], "yyyy-MM-dd"))
        else:
            self.chk_tanpa_akhir.setCurrentIndex(1)
            self._ganti_akhir()
        self.spn_notif.setValue(int(k.get("pemberitahuan_berakhir_hari") or 30))
        self.chk_perpanjangan.setCurrentIndex(1 if k.get("opsi_perpanjangan") else 0)
        self.inp_nilai.set_nilai(int(k.get("nilai") or 0))
        self.inp_nilai_barang.set_nilai(int(k.get("nilai_barang") or 0))
        self.inp_nilai_jasa.set_nilai(int(k.get("nilai_jasa") or 0))
        self.spn_termin.setValue(int(k.get("jumlah_termin") or 1))
        self.spn_jarak.setValue(int(k.get("termin_hari") or 30))
        if k.get("persentase_bagi_hasil"):
            self.inp_bagi.set_nilai(float(k["persentase_bagi_hasil"]))
        self.cmb_ppn.setCurrentIndex(1 if k.get("kena_ppn") else 0)
        self.txt_hukum.setPlainText(k.get("dasar_hukum", ""))
        self.inp_dokumen.setText(k.get("dokumen_path", ""))

        for it in kt.item(int(k["id"])):
            r = self.tabel_item.rowCount()
            self.tabel_item.insertRow(r)
            for c, teks in enumerate([
                    it["arah"], it["nama"], f"{it['jumlah']:g}", it["satuan"],
                    str(int(it["nilai_satuan"])), str(int(it["total"]))]):
                self.tabel_item.setItem(r, c, QTableWidgetItem(teks))
        self._perbarui_pajak()

    # ------------------------------------------------------------------
    def _simpan(self):
        if not self.inp_judul.text().strip():
            QMessageBox.warning(self, "Judul belum diisi",
                                "Isi judul perjanjian lebih dahulu.")
            return
        mitra_id = self.cmb_mitra.currentData()
        if not mitra_id and not self.inp_pihak2.text().strip():
            QMessageBox.warning(
                self, "Pihak kedua belum diisi",
                "Pilih mitra dari daftar atau isi nama mitra secara manual.")
            return

        tanpa_akhir = bool(self.chk_tanpa_akhir.currentData())
        data = {
            "id": (self.kontrak or {}).get("id"),
            "nomor": self.inp_nomor.text().strip(),
            "judul": self.inp_judul.text().strip(),
            "jenis": self.cmb_jenis.currentData(),
            "bentuk_imbalan": self.cmb_bentuk.currentData(),
            "partner_id": mitra_id,
            "pihak_kedua": self.inp_pihak2.text().strip(),
            "peran_kita": self.cmb_peran.currentData(),
            "tanggal_mulai": self.dt_mulai.date().toString("yyyy-MM-dd"),
            "tanggal_akhir": (None if tanpa_akhir
                              else self.dt_akhir.date().toString("yyyy-MM-dd")),
            "opsi_perpanjangan": bool(self.chk_perpanjangan.currentData()),
            "pemberitahuan_berakhir_hari": self.spn_notif.value(),
            "nilai": self.inp_nilai.nilai(),
            "nilai_barang": self.inp_nilai_barang.nilai(),
            "nilai_jasa": self.inp_nilai_jasa.nilai(),
            "skema_bayar": self.cmb_skema.currentData(),
            "jumlah_termin": self.spn_termin.value(),
            "termin_hari": self.spn_jarak.value(),
            "persentase_bagi_hasil": (self.inp_bagi.nilai()
                                      if self.cmb_bentuk.currentData() == "bagi_hasil"
                                      else None),
            "kena_ppn": bool(self.cmb_ppn.currentData()),
            "status": self.cmb_status.currentData(),
            "dokumen_path": self.inp_dokumen.text().strip(),
            "dokumen_nama": (self.inp_dokumen.text().split("/")[-1].split("\\")[-1]
                             if self.inp_dokumen.text() else ""),
            "dasar_hukum": self.txt_hukum.toPlainText().strip(),
        }

        try:
            kid = kt.simpan(self.ctx.company_id, data, user=self.ctx.username)
            if self.tabel_item.rowCount():
                kt.simpan_item(kid, self._kumpulkan_item())
            self.kontrak_id = kid
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Gagal menyimpan",
                                 f"Kontrak tidak dapat disimpan.\n\n{e}")

    def _kumpulkan_item(self) -> list:
        hasil = []
        for r in range(self.tabel_item.rowCount()):
            # Baris dikunci lewat argumen bawaan. Tanpa itu fungsi ini
            # membaca variabel r dari lingkup luar, sehingga nilainya bisa
            # berubah bila pemanggilannya dipindahkan ke luar perulangan.
            def sel(c, r=r):
                it = self.tabel_item.item(r, c)
                return it.text().strip() if it else ""
            nama = sel(1)
            if not nama:
                continue
            try:
                jumlah = float(sel(2).replace(",", ".") or 1)
            except ValueError:
                jumlah = 1.0
            try:
                nilai = int(float(sel(4) or 0))
            except ValueError:
                nilai = 0
            hasil.append({
                "arah": sel(0) or "kita_beri",
                "nama": nama,
                "jumlah": jumlah,
                "satuan": sel(3) or "unit",
                "nilai_satuan": nilai,
            })
        return hasil


# ==========================================================================
# HALAMAN KONTRAK
# ==========================================================================
class KontrakPage(QWidget):
    pindah_halaman = Signal(str)

    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx

        luar = QVBoxLayout(self)
        luar.setContentsMargins(0, 0, 0, 0)
        luar.setSpacing(0)

        self.header = w.PageHeader(
            "Kontrak & Kerja Sama",
            "Catat perjanjian dengan mitra, pantau masa berlakunya, dan "
            "simpan dokumennya di satu tempat.")

        b_baru = w.tombol("Kontrak Baru", gaya="primary", ikon="+")
        b_baru.clicked.connect(self._tambah)
        self.header.tambah_aksi(b_baru)

        b_impor = w.tombol("Impor dari Dokumen", gaya="biasa", ikon="dokumen")
        b_impor.clicked.connect(self._impor_dokumen)
        self.header.tambah_aksi(b_impor)

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
        luar.addWidget(w.scroll(isi), 1)

        self.kartu = QWidget()
        self.kartu_lay = QGridLayout(self.kartu)
        self.kartu_lay.setContentsMargins(0, 0, 0, 0)
        self.kartu_lay.setSpacing(16)
        self.lay.addWidget(self.kartu)

        self.banner = QWidget()
        self.banner_lay = QVBoxLayout(self.banner)
        self.banner_lay.setContentsMargins(0, 0, 0, 0)
        self.banner_lay.setSpacing(10)
        self.lay.addWidget(self.banner)

        # ------------------------------------------------------ pencarian
        kartu_saring = w.Card()
        sl = kartu_saring.body()
        baris = QHBoxLayout()
        baris.setSpacing(10)

        self.inp_cari = QLineEdit()
        self.inp_cari.setPlaceholderText(
            "Cari nomor kontrak, judul, atau nama mitra…")
        self.inp_cari.textChanged.connect(self._cari_otomatis)
        baris.addWidget(self.inp_cari, 1)

        self.cmb_status = QComboBox()
        self.cmb_status.addItem("Semua status", None)
        for kode, nama in kt.STATUS_KONTRAK.items():
            self.cmb_status.addItem(nama, kode)
        self.cmb_status.currentIndexChanged.connect(self.muat)
        baris.addWidget(self.cmb_status)

        self.cmb_jenis = QComboBox()
        self.cmb_jenis.addItem("Semua jenis", None)
        for kode, nama in kt.JENIS_KONTRAK.items():
            self.cmb_jenis.addItem(nama, kode)
        self.cmb_jenis.currentIndexChanged.connect(self.muat)
        baris.addWidget(self.cmb_jenis)

        sl.addLayout(baris)
        self.lay.addWidget(kartu_saring)

        # --------------------------------------------------------- tabel
        kartu_tabel = w.Card()
        tl = kartu_tabel.body()
        self.tabel = w.Tabel([
            ("Nomor Kontrak", 175), ("Judul Perjanjian", -1), ("Mitra", 165),
            ("Jenis", 175), ("Mulai", 105), ("Berakhir", 105),
            ("Nilai", 145), ("Kondisi", 145)])
        self.tabel.doubleClicked.connect(lambda _: self._ubah())
        tl.addWidget(self.tabel, 1)

        baris_aksi = QHBoxLayout()
        b_ubah = w.tombol("Ubah", gaya="biasa", ikon="pengaturan")
        b_ubah.clicked.connect(self._ubah)
        baris_aksi.addWidget(b_ubah)
        b_detail = w.tombol("Lihat Rincian", gaya="biasa")
        b_detail.clicked.connect(self._detail)
        baris_aksi.addWidget(b_detail)
        b_hapus = w.tombol("Hapus", gaya="biasa")
        b_hapus.clicked.connect(self._hapus)
        baris_aksi.addWidget(b_hapus)
        baris_aksi.addStretch()
        self.lbl_jumlah = QLabel()
        self.lbl_jumlah.setObjectName("Muted")
        baris_aksi.addWidget(self.lbl_jumlah)
        tl.addLayout(baris_aksi)
        self.lay.addWidget(kartu_tabel)

        self._timer = None
        self._isi_kartu({})

    # ------------------------------------------------------------------
    def _cari_otomatis(self, _teks: str):
        from PySide6.QtCore import QTimer
        if self._timer is None:
            self._timer = QTimer(self)
            self._timer.setSingleShot(True)
            self._timer.timeout.connect(self.muat)
        self._timer.start(300)

    def _isi_kartu(self, r: dict):
        while self.kartu_lay.count():
            it = self.kartu_lay.takeAt(0)
            wdg = it.widget()
            if wdg:
                wdg.deleteLater()

        isi = [
            ("Jumlah Kontrak", str(r.get("jumlah", 0)), None),
            ("Kontrak Aktif", str(r.get("aktif", 0)), C.POSITIF),
            ("Total Nilai", theme.money(r.get("total_nilai", 0)), None),
            ("Segera Berakhir", str(r.get("segera_berakhir", 0)),
             C.WARNING if r.get("segera_berakhir") else None),
            ("Sudah Berakhir", str(r.get("sudah_berakhir", 0)),
             C.DANGER if r.get("sudah_berakhir") else None),
        ]
        for i, (label, nilai, warna) in enumerate(isi):
            kartu = w.Card()
            kl = kartu.body()
            kl.setSpacing(6)
            lbl = QLabel(label.upper())
            lbl.setObjectName("KpiLabel")
            kl.addWidget(lbl)
            v = QLabel(nilai)
            v.setObjectName("KpiValue")
            v.setStyleSheet(
                f"font-family: {theme.FONT_ANGKA}; font-size: {theme.FS_H1}px; "
                f"font-weight: 700; background: transparent; "
                f"color: {warna or C.TEXT};")
            kl.addWidget(v)
            self.kartu_lay.addWidget(kartu, 0, i)
        self.kartu_lay.setColumnStretch(len(isi), 1)

    # ------------------------------------------------------------------
    def muat(self):
        cid = self.ctx.company_id
        if not cid:
            return

        self._isi_kartu(kt.ringkasan(cid))

        while self.banner_lay.count():
            it = self.banner_lay.takeAt(0)
            wdg = it.widget()
            if wdg:
                wdg.deleteLater()

        perhatian = kt.yang_perlu_perhatian(cid)
        if perhatian:
            dekat = [k for k in perhatian if k["kondisi"] == "Segera Berakhir"]
            lewat = [k for k in perhatian if k["kondisi"] == "Sudah Berakhir"]
            pesan = []
            if dekat:
                pesan.append(f"{len(dekat)} kontrak berakhir dalam 30 hari ke depan")
            if lewat:
                pesan.append(f"{len(lewat)} kontrak sudah melewati tanggal berakhir")
            if pesan:
                self.banner_lay.addWidget(w.InfoBanner(
                    " · ".join(pesan) + ". Periksa apakah perlu diperpanjang "
                    "atau ditutup.",
                    "warning" if dekat else "danger", "Perhatian Kontrak"))

        daftar = kt.daftar(
            cid,
            status=self.cmb_status.currentData(),
            jenis=self.cmb_jenis.currentData(),
            cari=self.inp_cari.text().strip() or None)

        baris = []
        for k in daftar:
            warna = None
            if k["kondisi"] == "Sudah Berakhir":
                warna = C.DANGER
            elif k["kondisi"] == "Segera Berakhir":
                warna = C.WARNING
            elif k["kondisi"] == "Berjalan":
                warna = C.POSITIF
            baris.append([
                k["nomor"], k["judul"], k["mitra"],
                kt.JENIS_KONTRAK.get(k["jenis"], k["jenis"]),
                theme.tanggal_id(k["tanggal_mulai"]) if k["tanggal_mulai"] else "",
                theme.tanggal_id(k["tanggal_akhir"]) if k["tanggal_akhir"] else "",
                theme.money(k.get("nilai_total") or k["nilai"]),
                k["kondisi"], warna])

        self.tabel.isi(baris, align_kanan={6}, kolom_penanda=7)
        self._daftar_kini = daftar
        self.lbl_jumlah.setText(
            f"{len(daftar)} kontrak ditampilkan" if daftar
            else "Belum ada kontrak tercatat")

    # ------------------------------------------------------------------
    def _tambah(self):
        dlg = DialogKontrak(self.ctx, self)
        if dlg.exec():
            self.muat()
            self.header.set_subjudul(
                "Kontrak tersimpan. Nomornya dapat dicari di kolom pencarian.")

    def _impor_dokumen(self):
        jalur, _ = QFileDialog.getOpenFileName(
            self, "Pilih Berkas Kontrak", "",
            "Dokumen (*.pdf *.docx *.txt *.md);;Semua Berkas (*)")
        if not jalur:
            return
        teks = kt.baca_dokumen(jalur)
        if not teks:
            QMessageBox.warning(
                self, "Tidak dapat membaca",
                "Isi berkas tidak dapat dibaca. Gunakan PDF berteks, DOCX, "
                "atau TXT.")
            return
        dlg = DialogKontrak(self.ctx, self)
        dlg.inp_dokumen.setText(jalur)
        dlg._baca_dokumen()
        dlg.tabs.setCurrentIndex(3)
        if dlg.exec():
            self.muat()

    def _terpilih(self) -> dict:
        r = self.tabel.currentRow()
        daftar = getattr(self, "_daftar_kini", [])
        if 0 <= r < len(daftar):
            return daftar[r]
        return {}

    def _ubah(self):
        k = self._terpilih()
        if not k:
            QMessageBox.information(self, "Belum dipilih",
                                    "Pilih satu kontrak pada tabel lebih dahulu.")
            return
        penuh = kt.ambil(int(k["id"]))
        dlg = DialogKontrak(self.ctx, self, penuh)
        if dlg.exec():
            self.muat()

    def _detail(self):
        k = self._terpilih()
        if not k:
            QMessageBox.information(self, "Belum dipilih",
                                    "Pilih satu kontrak pada tabel lebih dahulu.")
            return
        penuh = kt.ambil(int(k["id"]))
        baris = kt.termin(int(k["id"]))
        item = kt.item(int(k["id"]))
        berkas = kt.berkas(int(k["id"]))

        bagian = [
            f"<b>{penuh['judul']}</b>",
            f"Nomor: {penuh['nomor']}",
            f"Jenis: {kt.JENIS_KONTRAK.get(penuh['jenis'], penuh['jenis'])}",
            f"Bentuk imbalan: "
            f"{kt.BENTUK_IMBALAN.get(penuh['bentuk_imbalan'], penuh['bentuk_imbalan'])}",
            f"Mitra: {k.get('mitra') or penuh.get('pihak_kedua') or '-'}",
            f"Berlaku: {theme.tanggal_id(penuh['tanggal_mulai'])} s.d. "
            f"{theme.tanggal_id(penuh['tanggal_akhir']) if penuh['tanggal_akhir'] else 'tanpa batas waktu'}",
            f"Nilai: Rp{theme.money(penuh.get('nilai_total') or penuh['nilai'])}",
        ]
        if penuh.get("nilai_barang"):
            bagian.append(f"Nilai barang barter: Rp{theme.money(penuh['nilai_barang'])}")
        if penuh.get("nilai_jasa"):
            bagian.append(f"Nilai jasa ditukar: Rp{theme.money(penuh['nilai_jasa'])}")
        if penuh.get("pph_pasal"):
            bagian.append(f"Pajak: {penuh['pph_pasal']} "
                          f"{penuh['tarif_pph']:g}%")
        if penuh.get("dasar_hukum"):
            bagian.append(f"<br><b>Dasar hukum</b><br>{penuh['dasar_hukum']}")
        if baris:
            bagian.append("<br><b>Termin</b>")
            for t in baris:
                status = "sudah dibayar" if t["dibayar"] else "belum dibayar"
                bagian.append(
                    f"• {t['nama']} - {t['persen']:g}% "
                    f"(Rp{theme.money(t['nilai'])}) · {status}"
                    + (f" · jatuh {theme.tanggal_id(t['jatuh_tempo'])}"
                       if t["jatuh_tempo"] else ""))
        if item:
            bagian.append("<br><b>Barang & Jasa</b>")
            for it in item:
                arah = "kita beri" if it["arah"] == "kita_beri" else "kita terima"
                bagian.append(f"• [{arah}] {it['nama']} - {it['jumlah']:g} "
                              f"{it['satuan']} · Rp{theme.money(it['total'])}")
        if berkas:
            bagian.append("<br><b>Berkas</b>")
            for b in berkas:
                bagian.append(f"• {b['nama']}")

        kotak = QMessageBox(self)
        kotak.setWindowTitle("Rincian Kontrak")
        kotak.setTextFormat(Qt.RichText)
        kotak.setText("<br>".join(bagian))
        kotak.exec()

    def _hapus(self):
        k = self._terpilih()
        if not k:
            QMessageBox.information(self, "Belum dipilih",
                                    "Pilih satu kontrak pada tabel lebih dahulu.")
            return
        if QMessageBox.question(
                self, "Hapus kontrak",
                f"Hapus kontrak {k['nomor']}?\n\n"
                "Kontrak dipindahkan ke keranjang sampah dan masih dapat "
                "dipulihkan.") != QMessageBox.Yes:
            return
        kt.hapus(int(k["id"]), self.ctx.company_id)
        self.muat()
