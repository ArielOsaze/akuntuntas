"""
AkunTuntas - Halaman Aset Tetap & Payroll
=========================================
  • Aset Tetap perolehan, penyusutan komersial & fiskal
  • Karyawan data karyawan, status PTKP, komponen BPJS
  • Payroll    - perhitungan gaji bulanan, PPh 21 skema TER
"""
from __future__ import annotations

from datetime import date, datetime

from PySide6.QtCore import Qt, Signal, QDate
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit, QDateEdit,
    QDialog, QMessageBox, QGridLayout, QCheckBox, QTableWidgetItem, QSpinBox,
    QTabWidget,
)

from ... import config, coa, services
from ...core import tax_engine as tx
from .. import theme
from .. import kalender
from ..theme import C
from .. import widgets as w
from .transaksi import HalamanDasar


# ==========================================================================
# HALAMAN ASET TETAP
# ==========================================================================
class AsetPage(HalamanDasar):
    def __init__(self, ctx, parent=None):
        super().__init__(ctx, "Aset Tetap & Penyusutan",
                         "Catat perolehan aset dan hitung penyusutan komersial "
                         "maupun fiskal sesuai PMK 72/2023.")
        b = w.tombol("Tambah Aset", gaya="primary", ikon="+")
        b.clicked.connect(self._tambah)
        self.header.tambah_aksi(b)

        b_susut = w.tombol("Hitung Penyusutan Tahun Ini", ikon="")
        b_susut.clicked.connect(self._hitung_penyusutan)
        self.header.tambah_aksi(b_susut)

        h = self._help("aset")
        if h:
            self.body_lay.addWidget(h)

        # referensi tarif
        ref = w.Card()
        rl = ref.body()
        rl.addWidget(w.label("Tarif Penyusutan Fiskal - PMK 72/PMK.03/2023",
                             objek="SectionTitle"))
        grid = QGridLayout()
        grid.setSpacing(10)
        kolom = ["Kelompok", "Masa Manfaat", "Garis Lurus", "Saldo Menurun", "Contoh Aset"]
        for i, k in enumerate(kolom):
            l = QLabel(k)
            l.setStyleSheet(f"font-size: {theme.FS_TINY}px; font-weight: 700; "
                            f"color: {C.TEXT_MUTED}; background: transparent;")
            grid.addWidget(l, 0, i)
        for r, (nama, info) in enumerate(config.FISCAL_ASSET_GROUPS.items(), start=1):
            nilai = [
                nama,
                f"{info['masa']} tahun" if info["masa"] else "",
                f"{info['garis_lurus'] * 100:g}%" if info["garis_lurus"] else "",
                f"{info['saldo_menurun'] * 100:g}%" if info["saldo_menurun"] else "",
                info["contoh"],
            ]
            for c, v in enumerate(nilai):
                l = QLabel(str(v))
                l.setStyleSheet(
                    f"font-size: {theme.FS_TINY}px; "
                    f"color: {C.TEXT if c == 0 else C.TEXT_MUTED}; "
                    "background: transparent;")
                l.setWordWrap(True)
                grid.addWidget(l, r, c)
        # Kolom "Contoh Aset" memuat kalimat panjang sehingga perlu ruang
        # paling lebar; kolom angka cukup sempit dan tidak perlu melar.
        for c in range(len(kolom) - 1):
            grid.setColumnStretch(c, 0)
        grid.setColumnStretch(len(kolom) - 1, 1)
        grid.setColumnMinimumWidth(0, 190)
        grid.setColumnMinimumWidth(len(kolom) - 1, 240)
        rl.addLayout(grid)
        self.body_lay.addWidget(ref)

        self.tabel = w.Tabel([
            ("Kode", 90), ("Nama Aset", -1), ("Tgl Perolehan", 115),
            ("Harga Perolehan", 150), ("Kelompok Fiskal", 130),
            ("Metode", 110), ("Peny. Komersial", 145), ("Peny. Fiskal", 140),
            ("Selisih", 130),
        ])
        self.body_lay.addWidget(self.tabel, 1)

        baris = QHBoxLayout()
        baris.setSpacing(9)
        b_hapus = w.tombol("Hapus Aset", gaya="danger", ikon="hapus")
        b_hapus.clicked.connect(self._hapus)
        baris.addWidget(b_hapus)
        baris.addStretch()
        self.lbl_info = QLabel("")
        self.lbl_info.setObjectName("Muted")
        baris.addWidget(self.lbl_info)
        self.body_lay.addLayout(baris)

    def muat(self):
        cid, tahun = self.ctx.company_id, self.ctx.tahun
        if not cid:
            return

        aset = services.list_aset(cid)
        susut = services.rekap_penyusutan(cid, tahun)
        peta = {r["asset_id"]: r for r in susut["rincian"]}

        baris = []
        for a in aset:
            d = peta.get(a["id"])
            baris.append([
                a["kode_aset"], a["nama_aset"], theme.tanggal_id(a["tanggal_perolehan"]),
                theme.money(a["harga_perolehan"]), a["kelompok_fiskal"],
                a["metode_fiskal"],
                theme.money(d["penyusutan_komersial"]) if d else "belum dihitung",
                theme.money(d["penyusutan_fiskal"]) if d else "belum dihitung",
                theme.money(d["penyusutan_komersial"] - d["penyusutan_fiskal"])
                if d else "",
            ])
        self.tabel.isi(baris, align_kanan={3, 6, 7, 8})

        self.lbl_info.setText(
            f"{len(aset)} aset · Total penyusutan komersial "
            f"{theme.money(susut['total_komersial'])} · fiskal "
            f"{theme.money(susut['total_fiskal'])} · selisih "
            f"{theme.money(susut['selisih'])}")

    def _tambah(self):
        if not self.ctx.company_id:
            return
        d = DialogAset(self.ctx, self)
        if d.exec():
            self.muat()

    def _hitung_penyusutan(self):
        cid, tahun = self.ctx.company_id, self.ctx.tahun
        if not cid:
            return
        aset = services.list_aset(cid)
        if not aset:
            QMessageBox.information(self, "Belum ada aset",
                                    "Tambahkan aset tetap terlebih dahulu.")
            return
        try:
            hasil = services.hitung_penyusutan_tahun(cid, tahun, self.ctx.user_id)
            total_k = sum(h["komersial"] for h in hasil)
            total_f = sum(h["fiskal"] for h in hasil)
            QMessageBox.information(
                self, "Penyusutan selesai",
                f"Penyusutan tahun {tahun} berhasil dihitung untuk {len(hasil)} aset.\n\n"
                f"Total penyusutan komersial: {theme.money(total_k)}\n"
                f"Total penyusutan fiskal: {theme.money(total_f)}\n"
                f"Selisih (menjadi koreksi fiskal): {theme.money(total_k - total_f)}\n\n"
                "Jurnal penyusutan telah dibuat otomatis.")
            self.muat()
        except Exception as e:
            QMessageBox.critical(self, "Gagal menghitung", str(e))

    def _hapus(self):
        r = self.tabel.baris_terpilih()
        if r is None:
            QMessageBox.information(self, "Belum dipilih", "Pilih satu baris aset.")
            return
        aset = services.list_aset(self.ctx.company_id)
        if r >= len(aset):
            return
        a = aset[r]
        if QMessageBox.question(
                self, "Konfirmasi Hapus",
                f"Hapus aset '{a['nama_aset']}' beserta data penyusutannya?\n\n"
                "Jurnal perolehan dan penyusutan tidak ikut terhapus otomatis "
                "perlu disesuaikan manual bila diperlukan.",
                QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return
        try:
            services.hapus_aset(a["id"], self.ctx.user_id)
            self.muat()
        except Exception as e:
            QMessageBox.critical(self, "Gagal menghapus", str(e))


class DialogAset(QDialog):
    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.setWindowTitle("Tambah Aset Tetap")
        self.setMinimumWidth(700)

        l = QVBoxLayout(self)
        l.setContentsMargins(24, 22, 24, 22)
        l.setSpacing(13)

        j = QLabel("Data Aset Tetap")
        j.setObjectName("SectionTitle")
        l.addWidget(j)

        if ctx.beginner:
            l.addWidget(w.HelpPanel(
                "Cara mengisi data aset",
                "Aset tetap adalah harta berumur lebih dari satu tahun yang dipakai "
                "usaha: komputer, kendaraan, mesin, bangunan.\n\n"
                "• Harga perolehan termasuk harga beli + biaya pengiriman + pemasangan.\n"
                "• Umur komersial menurut manajemen; umur fiskal mengikuti PMK 72/2023.\n"
                "• Nilai residu: perkiraan nilai jual di akhir masa manfaat (boleh 0).\n"
                "• Untuk aset yang sudah dimiliki sebelum memakai aplikasi, isi "
                "'Nilai Buku Fiskal Awal Tahun'.",
                "Pasal 11 UU PPh; PMK 72/PMK.03/2023; PSAK 16."))

        g = QGridLayout()
        g.setSpacing(12)

        g.addWidget(w.label("Kode Aset (opsional)", objek="FormLabel"), 0, 0)
        self.inp_kode = QLineEdit()
        self.inp_kode.setPlaceholderText("otomatis bila dikosongkan")
        g.addWidget(self.inp_kode, 1, 0)

        g.addWidget(w.label("Nama Aset", objek="FormLabel"), 0, 1, 1, 2)
        self.inp_nama = QLineEdit()
        self.inp_nama.setPlaceholderText("mis. Laptop Lenovo ThinkPad")
        g.addWidget(self.inp_nama, 1, 1, 1, 2)

        g.addWidget(w.label("Tanggal Perolehan", objek="FormLabel"), 2, 0)
        self.inp_tanggal = kalender.pasang(QDateEdit())
        self.inp_tanggal.setDisplayFormat("dd/MM/yyyy")
        self.inp_tanggal.setDate(QDate.currentDate())
        g.addWidget(self.inp_tanggal, 3, 0)

        g.addWidget(w.label("Harga Perolehan (Rp)", objek="FormLabel"), 2, 1)
        self.inp_harga = w.InputRupiah()
        self.inp_harga.valueChanged.connect(self._update_hint)
        g.addWidget(self.inp_harga, 3, 1)

        g.addWidget(w.label("Nilai Residu Komersial (Rp)", objek="FormLabel"), 2, 2)
        self.inp_residu = w.InputRupiah()
        g.addWidget(self.inp_residu, 3, 2)

        g.addWidget(w.label("Kelompok Fiskal", objek="FormLabel"), 4, 0, 1, 2)
        self.cmb_kelompok = QComboBox()
        for nama, info in config.FISCAL_ASSET_GROUPS.items():
            self.cmb_kelompok.addItem(
                f"{nama} - {info['masa']} tahun ({info['garis_lurus'] * 100:g}%/tahun)",
                nama)
        self.cmb_kelompok.currentIndexChanged.connect(self._update_hint)
        g.addWidget(self.cmb_kelompok, 5, 0, 1, 2)

        g.addWidget(w.label("Metode Fiskal", objek="FormLabel"), 4, 2)
        self.cmb_metode = QComboBox()
        self.cmb_metode.addItem("Garis Lurus", "Garis Lurus")
        self.cmb_metode.addItem("Saldo Menurun", "Saldo Menurun")
        self.cmb_metode.currentIndexChanged.connect(self._update_hint)
        g.addWidget(self.cmb_metode, 5, 2)

        g.addWidget(w.label("Umur Komersial (tahun)", objek="FormLabel"), 6, 0)
        self.spin_umur = QSpinBox()
        self.spin_umur.setRange(1, 50)
        self.spin_umur.setValue(4)
        g.addWidget(self.spin_umur, 7, 0)

        g.addWidget(w.label("Nilai Buku Fiskal Awal Tahun (Rp)", objek="FormLabel"), 6, 1)
        self.inp_nbv = w.InputRupiah()
        self.inp_nbv.setToolTip(
            "Isi hanya bila aset diperoleh sebelum tahun pajak ini berjalan.")
        g.addWidget(self.inp_nbv, 7, 1)

        g.addWidget(w.label("Akun Aset", objek="FormLabel"), 6, 2)
        self.cmb_akun_aset = w.combo_akun(ctx.company_id)
        w.set_combo_by_data(self.cmb_akun_aset, "1201")
        g.addWidget(self.cmb_akun_aset, 7, 2)

        g.addWidget(w.label("Akun Akumulasi Penyusutan", objek="FormLabel"), 8, 0, 1, 2)
        self.cmb_akun_akum = w.combo_akun(ctx.company_id)
        w.set_combo_by_data(self.cmb_akun_akum, "1202")
        g.addWidget(self.cmb_akun_akum, 9, 0, 1, 2)

        g.addWidget(w.label("Akun Beban Penyusutan", objek="FormLabel"), 8, 2)
        self.cmb_akun_beban = w.combo_akun(ctx.company_id)
        w.set_combo_by_data(self.cmb_akun_beban, "6007")
        g.addWidget(self.cmb_akun_beban, 9, 2)
        l.addLayout(g)

        self.lbl_hint = QLabel("")
        self.lbl_hint.setWordWrap(True)
        theme.latar(self.lbl_hint, f"background: {C.PRIMARY_SOFT}; border: 1px solid #CFE0F0; "
            f"border-radius: 8px; padding: 11px 13px; font-size: {theme.FS_SMALL}px; "
            f"color: {C.TEXT};")
        l.addWidget(self.lbl_hint)

        aksi = QHBoxLayout()
        aksi.addStretch()
        b = w.tombol("Batal")
        b.clicked.connect(self.reject)
        aksi.addWidget(b)
        bs = w.tombol("Simpan Aset", gaya="primary")
        bs.clicked.connect(self._simpan)
        aksi.addWidget(bs)
        l.addLayout(aksi)

        self._update_hint()

    def _update_hint(self):
        kelompok = self.cmb_kelompok.currentData()
        info = config.FISCAL_ASSET_GROUPS.get(kelompok, {})
        metode = self.cmb_metode.currentData()
        harga = self.inp_harga.nilai()

        tarif = 0
        if info:
            if metode == "Saldo Menurun" and info.get("saldo_menurun"):
                tarif = info["saldo_menurun"]
            else:
                tarif = info.get("garis_lurus", 0)

        if kelompok == "Tanah":
            self.lbl_hint.setText(
                "Tanah TIDAK disusutkan (Pasal 11 ayat 1 UU PPh). Tidak ada beban "
                "penyusutan yang akan dihitung.")
            return

        pesan = f"Tarif penyusutan fiskal: <b>{tarif * 100:g}% per tahun</b>"
        if info.get("masa"):
            pesan += f" selama {info['masa']} tahun"
        if metode == "Saldo Menurun" and not info.get("saldo_menurun"):
            pesan += ("<br><span style='color:#A15C07'>Peringatan: kelompok ini hanya "
                      "mengizinkan metode garis lurus sesuai PMK 72/2023.</span>")
        if harga > 0:
            per_tahun_fiskal = int(harga * tarif)
            pesan += (f"<br>Perkiraan penyusutan fiskal setahun: "
                      f"<b>{theme.money(per_tahun_fiskal)}</b>")
            umur = self.spin_umur.value()
            residu = self.inp_residu.nilai()
            if umur > 0:
                kom = int((harga - residu) / umur)
                pesan += (f"<br>Perkiraan penyusutan komersial setahun "
                          f"(umur {umur} tahun): <b>{theme.money(kom)}</b>")
                pesan += (f"<br><span style='color:{C.TEXT_MUTED}'>Selisih "
                          f"{theme.money(kom - per_tahun_fiskal)} akan menjadi koreksi "
                          "dalam rekonsiliasi fiskal.</span>")
        self.lbl_hint.setText(pesan)
        self.lbl_hint.setTextFormat(Qt.RichText)

    def _simpan(self):
        try:
            if not self.inp_nama.text().strip():
                QMessageBox.warning(self, "Nama kosong", "Isi nama aset.")
                return
            if self.inp_harga.nilai() <= 0:
                QMessageBox.warning(self, "Harga kosong", "Isi harga perolehan.")
                return
            kelompok = self.cmb_kelompok.currentData()
            metode = self.cmb_metode.currentData()
            if kelompok == "Tanah":
                metode = "Tidak Disusutkan"

            services.simpan_aset(
                self.ctx.company_id,
                self.inp_kode.text().strip(),
                self.inp_nama.text().strip(),
                self.inp_tanggal.date().toString("yyyy-MM-dd"),
                self.inp_harga.nilai(),
                kelompok, metode,
                self.spin_umur.value(),
                self.inp_residu.nilai(),
                self.inp_nbv.nilai(),
                self.cmb_akun_aset.currentData() or "1201",
                self.cmb_akun_akum.currentData() or "1202",
                self.cmb_akun_beban.currentData() or "6007",
                user_id=self.ctx.user_id)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Gagal menyimpan", str(e))


# ==========================================================================
# HALAMAN PAYROLL
# ==========================================================================
class PayrollPage(QWidget):
    pindah_halaman = Signal(str)

    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx

        luar = QVBoxLayout(self)
        luar.setContentsMargins(0, 0, 0, 0)
        luar.setSpacing(0)

        self.header = w.PageHeader(
            "Payroll & PPh 21",
            "Data karyawan, perhitungan gaji bulanan, dan pemotongan PPh 21 "
            "dengan skema Tarif Efektif Rata-rata.")

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

        b = w.tombol("Jalankan Payroll Bulan Ini", gaya="primary", ikon="simpan")
        b.clicked.connect(self._jalankan)
        self.header.tambah_aksi(b)
        # Halaman ini memuat judul panjang dan dua tombol aksi sekaligus.
        # Susun tombol pada barisnya sendiri agar tidak meluber keluar tepi.
        self.header.susun_aksi_terpisah()

        kepala = QWidget()
        theme.latar(kepala, f"background: {C.SURFACE}; "
                             f"border-bottom: 1px solid {C.BORDER};")
        kl = QVBoxLayout(kepala)
        kl.setContentsMargins(26, 20, 26, 18)
        # Header diberi ruang penuh supaya tombol aksinya tidak terdesak
        # keluar tepi saat jendela sedang sempit.
        kl.addWidget(self.header, 0)
        luar.addWidget(kepala)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        wadah = QWidget()
        wl = QVBoxLayout(wadah)
        wl.setContentsMargins(22, 16, 22, 22)
        wl.addWidget(self.tabs)
        luar.addWidget(wadah, 1)

        self.tab_karyawan = QWidget()
        self.tab_payroll = QWidget()
        self.tabs.addTab(self.tab_karyawan, "Data Karyawan")
        self.tabs.addTab(self.tab_payroll, "Riwayat Payroll")
        self.tabs.currentChanged.connect(self.muat)

        for t in (self.tab_karyawan, self.tab_payroll):
            l = QVBoxLayout(t)
            l.setContentsMargins(0, 12, 0, 0)
            l.setSpacing(13)

        self._bangun_karyawan()
        self._bangun_payroll()

    def _ganti_tahun(self):
        self.ctx.tahun = self.cmb_tahun.currentData()
        self.muat()

    def muat(self):
        if not self.ctx.company_id:
            return
        if self.tabs.currentIndex() == 0:
            self._muat_karyawan()
        else:
            self._muat_payroll()

    # ------------------------------------------------------------------
    def _bangun_karyawan(self):
        lay = self.tab_karyawan.layout()

        if self.ctx.beginner:
            lay.addWidget(w.HelpPanel(
                coa.HELP_TOPICS["payroll"]["judul"],
                coa.HELP_TOPICS["payroll"]["isi"],
                coa.HELP_TOPICS["payroll"]["dasar_hukum"]))

        baris = QHBoxLayout()
        baris.setSpacing(9)
        b = w.tombol("Tambah Karyawan", gaya="primary", ikon="+")
        b.clicked.connect(self._tambah_karyawan)
        baris.addWidget(b)
        b2 = w.tombol("Ubah", ikon="pengaturan")
        b2.clicked.connect(self._ubah_karyawan)
        baris.addWidget(b2)
        b3 = w.tombol("Nonaktifkan", gaya="danger", ikon="⊘")
        b3.clicked.connect(self._hapus_karyawan)
        baris.addWidget(b3)
        baris.addStretch()
        lay.addLayout(baris)

        self.tabel_karyawan = w.Tabel([
            ("NIK/NPWP", 150), ("Nama", -1), ("Jabatan", 150),
            ("Status PTKP", 115), ("Gaji Pokok", 145), ("Tunjangan", 140),
            ("BPJS", 130), ("Beban/Bulan", 155),
        ])
        lay.addWidget(self.tabel_karyawan, 1)

        self.lbl_karyawan = QLabel("")
        self.lbl_karyawan.setObjectName("Muted")
        lay.addWidget(self.lbl_karyawan)

    def _muat_karyawan(self):
        cid = self.ctx.company_id
        data = services.list_karyawan(cid)
        baris = []
        total_beban = 0
        for k in data:
            bpjs = []
            if k["bpjs_kes"]:
                bpjs.append("Kes")
            if k["bpjs_jht"]:
                bpjs.append("JHT")
            if k["bpjs_jp"]:
                bpjs.append("JP")
            upah = k["gaji_pokok"] + k["tunjangan_tetap"]
            b = tx.hitung_bpjs(upah, k["bpjs_jkk_rate"], bool(k["bpjs_kes"]),
                               bool(k["bpjs_jht"]), bool(k["bpjs_jp"]))
            beban = upah + b.total_perusahaan
            total_beban += beban
            baris.append([
                k["nik_npwp"] or "", k["nama"], k["jabatan"] or "",
                k["status_ptkp"], theme.money(k["gaji_pokok"]),
                theme.money(k["tunjangan_tetap"]),
                " + ".join(bpjs) if bpjs else "", theme.money(beban),
            ])
        self.tabel_karyawan.isi(baris, align_kanan={4, 5, 7})
        self.lbl_karyawan.setText(
            f"{len(data)} karyawan aktif · Estimasi beban payroll per bulan "
            f"{theme.money(total_beban)}")

    def _tambah_karyawan(self):
        if not self.ctx.company_id:
            return
        d = DialogKaryawan(self.ctx, self)
        if d.exec():
            self._muat_karyawan()

    def _ubah_karyawan(self):
        r = self.tabel_karyawan.baris_terpilih()
        if r is None:
            QMessageBox.information(self, "Belum dipilih", "Pilih satu karyawan.")
            return
        data = services.list_karyawan(self.ctx.company_id)
        if r >= len(data):
            return
        d = DialogKaryawan(self.ctx, self, data[r])
        if d.exec():
            self._muat_karyawan()

    def _hapus_karyawan(self):
        r = self.tabel_karyawan.baris_terpilih()
        if r is None:
            QMessageBox.information(self, "Belum dipilih", "Pilih satu karyawan.")
            return
        data = services.list_karyawan(self.ctx.company_id)
        if r >= len(data):
            return
        k = data[r]
        if QMessageBox.question(
                self, "Konfirmasi",
                f"Nonaktifkan karyawan '{k['nama']}'?\n\n"
                "Data historis payroll tetap tersimpan.",
                QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            services.hapus_karyawan(k["id"])
            self._muat_karyawan()

    # ------------------------------------------------------------------
    def _bangun_payroll(self):
        lay = self.tab_payroll.layout()

        if self.ctx.beginner:
            lay.addWidget(w.HelpPanel(
                "Cara kerja payroll di aplikasi ini",
                "Klik 'Jalankan Payroll Bulan Ini' untuk menghitung gaji seluruh "
                "karyawan aktif. Aplikasi otomatis:\n\n"
                "1. Menghitung bruto (gaji pokok + tunjangan + bonus)\n"
                "2. Menghitung potongan BPJS karyawan (Kes 1%, JHT 2%, JP 1%)\n"
                "3. Menghitung PPh 21 dengan skema TER (kecuali Desember: setahun)\n"
                "4. Menghitung take home pay\n"
                "5. Membuat jurnal payroll otomatis\n\n"
                "Setelah dijalankan, jangan lupa setor PPh 21 (tanggal 10) dan "
                "laporkan SPT Masa (tanggal 20) bulan berikutnya.",
                "PMK 168/PMK.03/2023; PP 58/2023."))

        self.tabel_payroll = w.Tabel([
            ("Masa", 110), ("Karyawan", 100), ("Bruto", 145),
            ("Potongan BPJS", 145), ("PPh 21", 130), ("Take Home Pay", 150),
            ("Beban Perusahaan", 160), ("Status", 100),
        ])
        self.tabel_payroll.doubleClicked.connect(self._detail_payroll)
        lay.addWidget(self.tabel_payroll, 1)

        baris = QHBoxLayout()
        baris.setSpacing(9)
        b = w.tombol("Lihat Rincian", ikon="")
        b.clicked.connect(self._detail_payroll)
        baris.addWidget(b)
        b2 = w.tombol("Hapus", gaya="danger", ikon="hapus")
        b2.clicked.connect(self._hapus_payroll)
        baris.addWidget(b2)
        baris.addStretch()
        self.lbl_payroll = QLabel("")
        self.lbl_payroll.setObjectName("Muted")
        baris.addWidget(self.lbl_payroll)
        lay.addLayout(baris)

    def _muat_payroll(self):
        cid, tahun = self.ctx.company_id, self.ctx.tahun
        data = services.list_payroll(cid, tahun)
        baris = []
        for p in data:
            baris.append([
                p["masa"], p["jumlah_karyawan"], theme.money(p["total_bruto"]),
                theme.money(p["total_potongan"]), "", theme.money(p["total_thp"]),
                theme.money(p["total_beban"]),
                "Sudah dijurnal" if p["status"] == "posted" else "Draft",
            ])
        # isi kolom PPh 21 dari rincian
        for i, p in enumerate(data):
            items = services.detail_payroll(p["id"])
            pph = sum(x["pph21"] for x in items)
            self.tabel_payroll.setItem(i, 4, QTableWidgetItem(theme.money(pph)))
        self.tabel_payroll.isi(baris, align_kanan={2, 3, 5, 6})
        total = sum(p["total_beban"] for p in data)
        self.lbl_payroll.setText(f"{len(data)} periode payroll · Total beban "
                                 f"{theme.money(total)}")

    def _jalankan(self):
        cid = self.ctx.company_id
        if not cid:
            QMessageBox.information(self, "Belum ada perusahaan",
                                    "Buat profil perusahaan terlebih dahulu.")
            return
        if not services.list_karyawan(cid):
            QMessageBox.information(self, "Belum ada karyawan",
                                    "Daftarkan karyawan pada tab Data Karyawan.")
            return
        d = DialogJalankanPayroll(self.ctx, self)
        if d.exec():
            self.tabs.setCurrentIndex(1)
            self.muat()

    def _detail_payroll(self):
        r = self.tabel_payroll.baris_terpilih()
        if r is None:
            QMessageBox.information(self, "Belum dipilih", "Pilih satu periode payroll.")
            return
        data = services.list_payroll(self.ctx.company_id, self.ctx.tahun)
        if r >= len(data):
            return
        run = data[r]
        items = services.detail_payroll(run["id"])

        dlg = QDialog(self)
        dlg.setWindowTitle(f"Rincian Payroll {run['masa']}")
        dlg.setMinimumSize(1050, 520)
        l = QVBoxLayout(dlg)
        l.setContentsMargins(22, 20, 22, 20)
        l.setSpacing(12)

        j = QLabel(f"Payroll Masa {run['masa']}")
        j.setObjectName("SectionTitle")
        l.addWidget(j)

        t = w.Tabel([
            ("Nama", 200), ("Status PTKP", 100), ("Gaji Pokok", 130),
            ("Tunjangan", 125), ("Bonus", 120), ("Bruto", 135),
            ("BPJS Karyawan", 130), ("PPh 21", 120), ("Take Home Pay", 140),
            ("Metode PPh 21", 145),
        ])
        baris = [[
            it["nama"], it["status_ptkp"], theme.money(it["gaji_pokok"]),
            theme.money(it["tunjangan"]), theme.money(it["bonus"]),
            theme.money(it["bruto"]), theme.money(it["bpjs_karyawan"]),
            theme.money(it["pph21"]), theme.money(it["take_home_pay"]),
            it["metode_pph21"] or "TER",
        ] for it in items]
        t.isi(baris, align_kanan={2, 3, 4, 5, 6, 7, 8})
        t.setMinimumHeight(300)
        l.addWidget(t)

        kartu = w.Card()
        b = QHBoxLayout()
        b.setSpacing(28)
        b.addWidget(w.MiniStat("Total Bruto", theme.money(run["total_bruto"])))
        b.addWidget(w.MiniStat("Total THP", theme.money(run["total_thp"])))
        b.addWidget(w.MiniStat("Total Beban Perusahaan",
                               theme.money(run["total_beban"]), C.PRIMARY))
        b.addStretch()
        kartu.body().addLayout(b)
        l.addWidget(kartu)

        bt = w.tombol("Tutup", gaya="primary")
        bt.clicked.connect(dlg.accept)
        bl = QHBoxLayout()
        bl.addStretch()
        bl.addWidget(bt)
        l.addLayout(bl)
        dlg.exec()

    def _hapus_payroll(self):
        r = self.tabel_payroll.baris_terpilih()
        if r is None:
            QMessageBox.information(self, "Belum dipilih", "Pilih satu periode payroll.")
            return
        data = services.list_payroll(self.ctx.company_id, self.ctx.tahun)
        if r >= len(data):
            return
        p = data[r]
        if QMessageBox.question(
                self, "Konfirmasi Hapus",
                f"Hapus payroll masa {p['masa']} beserta jurnalnya?",
                QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            try:
                services.hapus_payroll(p["id"], self.ctx.user_id)
                self.muat()
            except Exception as e:
                QMessageBox.critical(self, "Gagal menghapus", str(e))


class DialogKaryawan(QDialog):
    def __init__(self, ctx, parent=None, karyawan=None):
        super().__init__(parent)
        self.ctx = ctx
        self.karyawan = karyawan
        self.setWindowTitle("Data Karyawan" if not karyawan else "Ubah Data Karyawan")
        self.setMinimumWidth(620)

        l = QVBoxLayout(self)
        l.setContentsMargins(24, 22, 24, 22)
        l.setSpacing(13)

        j = QLabel("Data Karyawan")
        j.setObjectName("SectionTitle")
        l.addWidget(j)

        if ctx.beginner:
            l.addWidget(w.HelpPanel(
                "Tentang status PTKP",
                "Status PTKP menentukan besaran penghasilan tidak kena pajak, yang "
                "memengaruhi PPh 21 karyawan.\n\n"
                "• TK/0 - Tidak kawin, 0 tanggungan\n"
                "• K/0 - Kawin, 0 tanggungan\n"
                "• K/1, K/2, K/3 - Kawin dengan 1-3 tanggungan\n"
                "• K/I/0 - Kawin, istri berpenghasilan, digabung\n\n"
                "Tanggungan maksimal 3 orang (anak/keluarga sedarah dalam garis "
                "lurus). Status PTKP ditentukan oleh karyawan dan dibuktikan "
                "dengan dokumen resmi.",
                "PMK 101/PMK.010/2016; PMK 168/PMK.03/2023."))

        g = QGridLayout()
        g.setSpacing(12)

        g.addWidget(w.label("NIK / NPWP", objek="FormLabel"), 0, 0)
        self.inp_nik = QLineEdit()
        self.inp_nik.setPlaceholderText("16 digit NIK atau NPWP")
        g.addWidget(self.inp_nik, 1, 0)

        g.addWidget(w.label("Nama Lengkap", objek="FormLabel"), 0, 1)
        self.inp_nama = QLineEdit()
        g.addWidget(self.inp_nama, 1, 1)

        g.addWidget(w.label("Jabatan", objek="FormLabel"), 2, 0)
        self.inp_jabatan = QLineEdit()
        g.addWidget(self.inp_jabatan, 3, 0)

        g.addWidget(w.label("Status PTKP", objek="FormLabel"), 2, 1)
        self.cmb_ptkp = QComboBox()
        for kode, label in config.PTKP_LABELS.items():
            tahunan = config.PTKP_ANNUAL[kode]
            self.cmb_ptkp.addItem(f"{kode} - {label} ({theme.money(tahunan)}/thn)", kode)
        self.cmb_ptkp.currentIndexChanged.connect(self._update_hint)
        g.addWidget(self.cmb_ptkp, 3, 1)

        g.addWidget(w.label("Gaji Pokok per Bulan (Rp)", objek="FormLabel"), 4, 0)
        self.inp_gaji = w.InputRupiah()
        self.inp_gaji.valueChanged.connect(self._update_hint)
        g.addWidget(self.inp_gaji, 5, 0)

        g.addWidget(w.label("Tunjangan Tetap per Bulan (Rp)", objek="FormLabel"), 4, 1)
        self.inp_tunjangan = w.InputRupiah()
        self.inp_tunjangan.valueChanged.connect(self._update_hint)
        g.addWidget(self.inp_tunjangan, 5, 1)

        g.addWidget(w.label("Tanggal Masuk", objek="FormLabel"), 6, 0)
        self.inp_masuk = kalender.pasang(QDateEdit())
        self.inp_masuk.setDisplayFormat("dd/MM/yyyy")
        self.inp_masuk.setDate(QDate.currentDate())
        g.addWidget(self.inp_masuk, 7, 0)

        g.addWidget(w.label("Tarif JKK (%)", objek="FormLabel"), 6, 1)
        self.inp_jkk = QLineEdit("0,24")
        self.inp_jkk.setToolTip(
            "Tarif Jaminan Kecelakaan Kerja: 0,24% (risiko sangat rendah) sampai "
            "1,74% (risiko sangat tinggi), sesuai klasifikasi usaha.")
        self.inp_jkk.textChanged.connect(self._update_hint)
        g.addWidget(self.inp_jkk, 7, 1)
        l.addLayout(g)

        l.addWidget(w.label("Komponen BPJS yang Diikuti", objek="FormLabel"))
        bp = QHBoxLayout()
        bp.setSpacing(20)
        self.chk_kes = QCheckBox("BPJS Kesehatan (4% + 1%)")
        self.chk_kes.setChecked(True)
        bp.addWidget(self.chk_kes)
        self.chk_jht = QCheckBox("JHT (3,7% + 2%)")
        self.chk_jht.setChecked(True)
        bp.addWidget(self.chk_jht)
        self.chk_jp = QCheckBox("JP (2% + 1%)")
        self.chk_jp.setChecked(True)
        bp.addWidget(self.chk_jp)
        bp.addStretch()
        l.addLayout(bp)
        for c in (self.chk_kes, self.chk_jht, self.chk_jp):
            c.stateChanged.connect(self._update_hint)

        self.lbl_hint = QLabel("")
        self.lbl_hint.setWordWrap(True)
        self.lbl_hint.setTextFormat(Qt.RichText)
        theme.latar(self.lbl_hint, f"background: {C.PRIMARY_SOFT}; border: 1px solid #CFE0F0; "
            f"border-radius: 8px; padding: 12px 14px; font-size: {theme.FS_SMALL}px; "
            f"color: {C.TEXT};")
        l.addWidget(self.lbl_hint)

        aksi = QHBoxLayout()
        aksi.addStretch()
        b = w.tombol("Batal")
        b.clicked.connect(self.reject)
        aksi.addWidget(b)
        bs = w.tombol("Simpan", gaya="primary")
        bs.clicked.connect(self._simpan)
        aksi.addWidget(bs)
        l.addLayout(aksi)

        if karyawan:
            self._muat(karyawan)
        self._update_hint()

    def _muat(self, k):
        self.inp_nik.setText(k["nik_npwp"] or "")
        self.inp_nama.setText(k["nama"])
        self.inp_jabatan.setText(k["jabatan"] or "")
        i = self.cmb_ptkp.findData(k["status_ptkp"])
        if i >= 0:
            self.cmb_ptkp.setCurrentIndex(i)
        self.inp_gaji.set_nilai(k["gaji_pokok"])
        self.inp_tunjangan.set_nilai(k["tunjangan_tetap"])
        self.chk_kes.setChecked(bool(k["bpjs_kes"]))
        self.chk_jht.setChecked(bool(k["bpjs_jht"]))
        self.chk_jp.setChecked(bool(k["bpjs_jp"]))
        self.inp_jkk.setText(f"{k['bpjs_jkk_rate'] * 100:g}")
        if k["tanggal_masuk"]:
            try:
                y, m, d = k["tanggal_masuk"][:10].split("-")
                self.inp_masuk.setDate(QDate(int(y), int(m), int(d)))
            except Exception:
                pass

    def _update_hint(self):
        try:
            jkk = float(self.inp_jkk.text().replace(",", ".").strip() or "0") / 100
        except ValueError:
            jkk = 0.0024
        upah = self.inp_gaji.nilai() + self.inp_tunjangan.nilai()
        b = tx.hitung_bpjs(upah, jkk, self.chk_kes.isChecked(),
                           self.chk_jht.isChecked(), self.chk_jp.isChecked())

        baris = [
            f"<b>Upah bruto: {theme.money(upah)}</b>",
            f"BPJS porsi karyawan (dipotong): {theme.money(b.total_karyawan)}",
            f"&nbsp;&nbsp;- Kesehatan 1%: {theme.money(b.kes_karyawan)}",
            f"&nbsp;&nbsp;- JHT 2%: {theme.money(b.jht_karyawan)}",
            f"&nbsp;&nbsp;- JP 1%: {theme.money(b.jp_karyawan)}",
            f"BPJS porsi perusahaan (beban): {theme.money(b.total_perusahaan)}",
            f"&nbsp;&nbsp;- Kesehatan 4%: {theme.money(b.kes_perusahaan)}",
            f"&nbsp;&nbsp;- JHT 3,7%: {theme.money(b.jht_perusahaan)}",
            f"&nbsp;&nbsp;- JP 2%: {theme.money(b.jp_perusahaan)}",
            f"&nbsp;&nbsp;- JKM 0,3%: {theme.money(b.jkm_perusahaan)}",
            f"&nbsp;&nbsp;- JKK {jkk * 100:g}%: {theme.money(b.jkk_perusahaan)}",
        ]

        ptkp = self.cmb_ptkp.currentData()
        if upah > 0:
            r = tx.pph21_bulanan_ter(upah, ptkp)
            baris.append("")
            baris.append(f"<b>Perkiraan PPh 21 (skema TER): "
                         f"{theme.money(r.pph21_ter)}</b>")
            baris.append(f"Kategori TER {r.kategori_ter}, tarif efektif "
                         f"{r.tarif_ter * 100:.2f}%")
            thp = upah - b.total_karyawan - r.pph21_ter
            baris.append(f"<b>Perkiraan take home pay: {theme.money(thp)}</b>")
            beban = upah + b.total_perusahaan
            baris.append(f"Total beban perusahaan: {theme.money(beban)}")

        self.lbl_hint.setText("<br>".join(baris))

    def _simpan(self):
        try:
            if not self.inp_nama.text().strip():
                QMessageBox.warning(self, "Nama kosong", "Isi nama karyawan.")
                return
            if self.inp_gaji.nilai() <= 0:
                QMessageBox.warning(self, "Gaji kosong", "Isi gaji pokok.")
                return
            try:
                jkk = float(self.inp_jkk.text().replace(",", ".").strip() or "0") / 100
            except ValueError:
                jkk = 0.0024

            data = dict(
                nama=self.inp_nama.text().strip(),
                gaji_pokok=self.inp_gaji.nilai(),
                jabatan=self.inp_jabatan.text().strip(),
                status_ptkp=self.cmb_ptkp.currentData(),
                tunjangan_tetap=self.inp_tunjangan.nilai(),
                nik_npwp=self.inp_nik.text().strip(),
                bpjs_kes=self.chk_kes.isChecked(),
                bpjs_jht=self.chk_jht.isChecked(),
                bpjs_jp=self.chk_jp.isChecked(),
                bpjs_jkk_rate=jkk,
                tanggal_masuk=self.inp_masuk.date().toString("yyyy-MM-dd"),
            )
            if self.karyawan:
                services.update_karyawan(self.karyawan["id"], **data)
            else:
                services.simpan_karyawan(self.ctx.company_id, **data)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Gagal menyimpan", str(e))


class DialogJalankanPayroll(QDialog):
    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.setWindowTitle("Jalankan Payroll")
        self.setMinimumWidth(720)

        l = QVBoxLayout(self)
        l.setContentsMargins(24, 22, 24, 22)
        l.setSpacing(13)

        j = QLabel("Jalankan Payroll")
        j.setObjectName("SectionTitle")
        l.addWidget(j)

        if ctx.beginner:
            l.addWidget(w.HelpPanel(
                "Tentang bonus masa ini",
                "Isi kolom bonus bila ada THR, bonus tahunan, atau honor tambahan "
                "pada bulan ini. Bonus akan menambah penghasilan bruto sehingga "
                "PPh 21-nya ikut menyesuaikan.\n\n"
                "Bila tidak ada bonus, biarkan kosong.",
                "Pasal 21 UU PPh; PMK 168/PMK.03/2023."))

        g = QGridLayout()
        g.setSpacing(12)
        g.addWidget(w.label("Masa Pajak (YYYY-MM)", objek="FormLabel"), 0, 0)
        self.inp_masa = QLineEdit(date.today().strftime("%Y-%m"))
        g.addWidget(self.inp_masa, 1, 0)
        l.addLayout(g)

        self.karyawan = services.list_karyawan(ctx.company_id)
        self.inputs: dict[int, w.InputRupiah] = {}

        if self.karyawan:
            l.addWidget(w.label("Bonus / THR / Honor (kosongkan bila tidak ada)",
                                objek="FormLabel"))
            t = w.Tabel([("Nama", -1), ("Gaji Pokok", 150), ("Tunjangan", 140),
                         ("Bonus (Rp)", 180)])
            t.setRowCount(len(self.karyawan))
            for i, k in enumerate(self.karyawan):
                t.setItem(i, 0, QTableWidgetItem(k["nama"]))
                t.setItem(i, 1, QTableWidgetItem(theme.money(k["gaji_pokok"])))
                t.setItem(i, 2, QTableWidgetItem(theme.money(k["tunjangan_tetap"])))
                inp = w.InputRupiah()
                self.inputs[k["id"]] = inp
                t.setCellWidget(i, 3, inp)
            t.setMinimumHeight(240)
            l.addWidget(t)

        self.lbl_info = QLabel(
            "PPh 21 dihitung dengan skema Tarif Efektif Rata-rata (TER) bulanan. "
            "Untuk masa Desember, aplikasi otomatis memakai penghitungan setahun "
            "penuh sesuai PMK 168/2023.")
        self.lbl_info.setWordWrap(True)
        theme.latar(self.lbl_info, f"background: {C.PRIMARY_SOFT}; border: 1px solid #CFE0F0; "
            f"border-radius: 8px; padding: 11px 13px; font-size: {theme.FS_SMALL}px; "
            f"color: {C.TEXT};")
        l.addWidget(self.lbl_info)

        aksi = QHBoxLayout()
        aksi.addStretch()
        b = w.tombol("Batal")
        b.clicked.connect(self.reject)
        aksi.addWidget(b)
        bs = w.tombol("Hitung & Posting Payroll", gaya="primary")
        bs.clicked.connect(self._jalankan)
        aksi.addWidget(bs)
        l.addLayout(aksi)

    def _jalankan(self):
        try:
            masa = self.inp_masa.text().strip()
            if len(masa) != 7 or masa[4] != "-":
                QMessageBox.warning(self, "Format salah",
                                    "Format masa pajak harus YYYY-MM, contoh 2026-01.")
                return
            bonus = {eid: inp.nilai() for eid, inp in self.inputs.items()
                     if inp.nilai() > 0}
            hasil = services.hitung_payroll_bulanan(
                self.ctx.company_id, masa, bonus, self.ctx.user_id, posting=True)
            QMessageBox.information(
                self, "Payroll selesai",
                f"Payroll masa {masa} berhasil dihitung untuk "
                f"{len(hasil['items'])} karyawan.\n\n"
                f"Total bruto: {theme.money(hasil['total_bruto'])}\n"
                f"Total PPh 21: {theme.money(hasil['total_pph21'])}\n"
                f"Total take home pay: {theme.money(hasil['total_thp'])}\n"
                f"Total beban perusahaan: {theme.money(hasil['total_beban'])}\n\n"
                "Jurnal payroll telah dibuat otomatis.")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Gagal menjalankan payroll", str(e))
