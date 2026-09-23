"""
Halaman entitas lanjutan: dimensi (cost center, proyek, cabang),
konsolidasi grup, tutup buku, otomasi berulang, pengingat, dan akses LAN.
"""
from __future__ import annotations

import os
from datetime import datetime

from PySide6.QtCore import Qt, Signal, QDate, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit, QDateEdit,
    QDialog, QMessageBox, QGridLayout, QCheckBox, QTabWidget, QFileDialog,
    QSpinBox,
)

from ... import config, db, modules as M, modules_ops as O
from ...core import accounting as acc
from ...core import tax_engine as tx
from ... import istilah
from .. import theme, widgets as w
from .. import kalender
from ..theme import C


# ==========================================================================
# DIALOG DASAR
# ==========================================================================
class DialogCostCenter(QDialog):
    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.setWindowTitle("Tambah Cost Center")
        self.setMinimumWidth(520)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 22, 24, 22)
        lay.setSpacing(13)

        j = QLabel("Cost Center Baru")
        j.setObjectName("SectionTitle")
        lay.addWidget(j)

        lay.addWidget(w.HelpPanel(
            "Tentang cost center",
            "Cost center adalah unit yang menyerap biaya, misalnya divisi "
            "Produksi, Marketing, atau Administrasi.\n\n"
            "Dengan menandai setiap biaya pada cost center, Anda dapat melihat "
            "unit mana yang paling banyak menghabiskan anggaran dan membandingkan "
            "realisasi dengan anggaran.",
            "Akuntansi pertanggungjawaban (responsibility accounting)."))

        g = QGridLayout()
        g.setSpacing(12)
        g.addWidget(w.label("Nama Cost Center", objek="FormLabel"), 0, 0, 1, 2)
        self.inp_nama = QLineEdit()
        self.inp_nama.setPlaceholderText("mis. Divisi Marketing")
        g.addWidget(self.inp_nama, 1, 0, 1, 2)

        g.addWidget(w.label("Penanggung Jawab", objek="FormLabel"), 2, 0)
        self.inp_pj = QLineEdit()
        g.addWidget(self.inp_pj, 3, 0)

        g.addWidget(w.label("Anggaran per Tahun (Rp)", objek="FormLabel"), 2, 1)
        self.inp_anggaran = w.InputRupiah()
        g.addWidget(self.inp_anggaran, 3, 1)
        lay.addLayout(g)

        aksi = QHBoxLayout()
        aksi.addStretch()
        b = w.tombol("Batal")
        b.clicked.connect(self.reject)
        aksi.addWidget(b)
        bs = w.tombol("Simpan", gaya="primary")
        bs.clicked.connect(self._simpan)
        aksi.addWidget(bs)
        lay.addLayout(aksi)

    def _simpan(self):
        try:
            if not self.inp_nama.text().strip():
                QMessageBox.warning(self, "Nama kosong", "Isi nama cost center.")
                return
            O.buat_cost_center(self.ctx.company_id, self.inp_nama.text().strip(),
                               penanggung_jawab=self.inp_pj.text().strip(),
                               anggaran=self.inp_anggaran.nilai())
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Gagal menyimpan", str(e))


class DialogProyek(QDialog):
    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.setWindowTitle("Tambah Proyek")
        self.setMinimumWidth(620)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 22, 24, 22)
        lay.setSpacing(13)

        j = QLabel("Proyek Baru")
        j.setObjectName("SectionTitle")
        lay.addWidget(j)

        lay.addWidget(w.HelpPanel(
            "Tentang akuntansi proyek",
            "Bila Anda mengerjakan proyek (misalnya konstruksi atau konsultasi), "
            "catat semua pendapatan dan biaya proyek tersebut agar Anda dapat "
            "menghitung laba per proyek.\n\n"
            "Ini penting untuk kontrak jangka panjang dan penagihan termin.",
            "PSAK 34 - akuntansi kontrak konstruksi. PSAK 72 - pendapatan "
            "dari kontrak dengan pelanggan."))

        g = QGridLayout()
        g.setSpacing(12)
        g.addWidget(w.label("Nama Proyek", objek="FormLabel"), 0, 0, 1, 2)
        self.inp_nama = QLineEdit()
        self.inp_nama.setPlaceholderText("mis. Pembangunan Gudang Klien ABC")
        g.addWidget(self.inp_nama, 1, 0, 1, 2)

        g.addWidget(w.label("Pelanggan", objek="FormLabel"), 2, 0)
        self.cmb_mitra = QComboBox()
        self.cmb_mitra.addItem("Tidak ada", None)
        for m in M.daftar_mitra(ctx.company_id, "customer"):
            self.cmb_mitra.addItem(m["nama"], m["id"])
        g.addWidget(self.cmb_mitra, 3, 0)

        g.addWidget(w.label("Status", objek="FormLabel"), 2, 1)
        self.cmb_status = QComboBox()
        self.cmb_status.addItem("Berjalan", "berjalan")
        self.cmb_status.addItem("Selesai", "selesai")
        self.cmb_status.addItem("Dibatalkan", "batal")
        g.addWidget(self.cmb_status, 3, 1)

        g.addWidget(w.label("Tanggal Mulai", objek="FormLabel"), 4, 0)
        self.inp_mulai = kalender.pasang(QDateEdit())
        self.inp_mulai.setDisplayFormat("dd/MM/yyyy")
        self.inp_mulai.setDate(QDate.currentDate())
        g.addWidget(self.inp_mulai, 5, 0)

        g.addWidget(w.label("Target Selesai", objek="FormLabel"), 4, 1)
        self.inp_selesai = kalender.pasang(QDateEdit())
        self.inp_selesai.setDisplayFormat("dd/MM/yyyy")
        self.inp_selesai.setDate(QDate.currentDate().addMonths(6))
        g.addWidget(self.inp_selesai, 5, 1)

        g.addWidget(w.label("Nilai Kontrak (Rp)", objek="FormLabel"), 6, 0)
        self.inp_nilai = w.InputRupiah()
        g.addWidget(self.inp_nilai, 7, 0)

        g.addWidget(w.label("Anggaran Biaya (Rp)", objek="FormLabel"), 6, 1)
        self.inp_anggaran = w.InputRupiah()
        g.addWidget(self.inp_anggaran, 7, 1)

        g.addWidget(w.label("Catatan", objek="FormLabel"), 8, 0, 1, 2)
        self.inp_catatan = QLineEdit()
        g.addWidget(self.inp_catatan, 9, 0, 1, 2)
        lay.addLayout(g)

        aksi = QHBoxLayout()
        aksi.addStretch()
        b = w.tombol("Batal")
        b.clicked.connect(self.reject)
        aksi.addWidget(b)
        bs = w.tombol("Simpan", gaya="primary")
        bs.clicked.connect(self._simpan)
        aksi.addWidget(bs)
        lay.addLayout(aksi)

    def _simpan(self):
        try:
            if not self.inp_nama.text().strip():
                QMessageBox.warning(self, "Nama kosong", "Isi nama proyek.")
                return
            O.buat_proyek(
                self.ctx.company_id, self.inp_nama.text().strip(),
                partner_id=self.cmb_mitra.currentData(),
                tanggal_mulai=self.inp_mulai.date().toString("yyyy-MM-dd"),
                tanggal_selesai=self.inp_selesai.date().toString("yyyy-MM-dd"),
                nilai_kontrak=self.inp_nilai.nilai(),
                anggaran=self.inp_anggaran.nilai(),
                status=self.cmb_status.currentData(),
                catatan=self.inp_catatan.text().strip())
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Gagal menyimpan", str(e))


class DialogCabang(QDialog):
    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.setWindowTitle("Tambah Cabang")
        self.setMinimumWidth(600)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 22, 24, 22)
        lay.setSpacing(13)

        j = QLabel("Cabang Baru")
        j.setObjectName("SectionTitle")
        lay.addWidget(j)

        lay.addWidget(w.HelpPanel(
            "Tentang akuntansi cabang",
            "Bila usaha Anda memiliki beberapa lokasi, catat transaksi per cabang "
            "agar dapat membandingkan kinerja tiap lokasi.\n\n"
            "Penting untuk pajak daerah (PBB, pajak restoran) dan pemisahan "
            "administrasi bila tiap cabang punya NPWP sendiri.",
            "Pasal 28 UU KUP pembukuan di Indonesia. Per-05/PJ/2021 "
            "pendaftaran NPWP cabang."))

        g = QGridLayout()
        g.setSpacing(12)
        g.addWidget(w.label("Nama Cabang", objek="FormLabel"), 0, 0, 1, 2)
        self.inp_nama = QLineEdit()
        self.inp_nama.setPlaceholderText("mis. Cabang Surabaya")
        g.addWidget(self.inp_nama, 1, 0, 1, 2)

        g.addWidget(w.label("Kota", objek="FormLabel"), 2, 0)
        self.inp_kota = QLineEdit()
        g.addWidget(self.inp_kota, 3, 0)

        g.addWidget(w.label("Penanggung Jawab", objek="FormLabel"), 2, 1)
        self.inp_pj = QLineEdit()
        g.addWidget(self.inp_pj, 3, 1)

        g.addWidget(w.label("Alamat", objek="FormLabel"), 4, 0, 1, 2)
        self.inp_alamat = QLineEdit()
        g.addWidget(self.inp_alamat, 5, 0, 1, 2)

        g.addWidget(w.label("NPWP Cabang (bila ada)", objek="FormLabel"), 6, 0)
        self.inp_npwp = QLineEdit()
        self.inp_npwp.setPlaceholderText("00.000.000.0-000.000")
        g.addWidget(self.inp_npwp, 7, 0)
        lay.addLayout(g)

        aksi = QHBoxLayout()
        aksi.addStretch()
        b = w.tombol("Batal")
        b.clicked.connect(self.reject)
        aksi.addWidget(b)
        bs = w.tombol("Simpan", gaya="primary")
        bs.clicked.connect(self._simpan)
        aksi.addWidget(bs)
        lay.addLayout(aksi)

    def _simpan(self):
        try:
            if not self.inp_nama.text().strip():
                QMessageBox.warning(self, "Nama kosong", "Isi nama cabang.")
                return
            O.buat_cabang(self.ctx.company_id, self.inp_nama.text().strip(),
                          kota=self.inp_kota.text().strip(),
                          penanggung_jawab=self.inp_pj.text().strip(),
                          alamat=self.inp_alamat.text().strip(),
                          npwp=self.inp_npwp.text().strip())
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Gagal menyimpan", str(e))


# ==========================================================================
# HALAMAN DIMENSI
# ==========================================================================
class DimensiPage(QWidget):
    pindah_halaman = Signal(str)

    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx

        luar = QVBoxLayout(self)
        luar.setContentsMargins(0, 0, 0, 0)
        luar.setSpacing(0)

        self.header = w.PageHeader(
            "Dimensi & Pusat Biaya",
            "Cost center, proyek, dan cabang - lacak biaya dan pendapatan per "
            "unit usaha.")

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

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tab_cc = QWidget()
        self.tab_proyek = QWidget()
        self.tab_cabang = QWidget()
        self.tab_laporan = QWidget()
        self.tabs.addTab(self.tab_cc, "Cost Center")
        self.tabs.addTab(self.tab_proyek, "Proyek")
        self.tabs.addTab(self.tab_cabang, "Cabang")
        self.tabs.addTab(self.tab_laporan, "Laba Rugi per Dimensi")
        self.tabs.currentChanged.connect(self.muat)
        self.lay.addWidget(self.tabs, 1)

        self._bangun_cc()
        self._bangun_proyek()
        self._bangun_cabang()
        self._bangun_laporan()

    def _bangun_cc(self):
        lay = QVBoxLayout(self.tab_cc)
        lay.setContentsMargins(0, 12, 0, 0)
        lay.setSpacing(12)

        self.tabel_cc = w.Tabel([
            ("Kode", 105), ("Nama Cost Center", -1), ("Penanggung Jawab", 185),
            ("Anggaran/Tahun", 185), ("Realisasi", 175), ("Sisa", 175),
        ])
        lay.addWidget(self.tabel_cc, 1)

        baris = QHBoxLayout()
        b = w.tombol("Tambah Cost Center", gaya="primary", ikon="+")
        b.clicked.connect(self._tambah_cc)
        baris.addWidget(b)
        baris.addStretch()
        self.lbl_cc = QLabel("")
        self.lbl_cc.setObjectName("Muted")
        baris.addWidget(self.lbl_cc)
        lay.addLayout(baris)

    def _bangun_proyek(self):
        lay = QVBoxLayout(self.tab_proyek)
        lay.setContentsMargins(0, 12, 0, 0)
        lay.setSpacing(12)

        self.tabel_proyek = w.Tabel([
            ("Kode", 105), ("Nama Proyek", -1), ("Pelanggan", 175),
            ("Mulai", 105), ("Target Selesai", 115), ("Nilai Kontrak", 165),
            ("Anggaran", 155), ("Status", 105),
        ])
        lay.addWidget(self.tabel_proyek, 1)

        baris = QHBoxLayout()
        b = w.tombol("Tambah Proyek", gaya="primary", ikon="+")
        b.clicked.connect(self._tambah_proyek)
        baris.addWidget(b)
        b2 = w.tombol("Lihat Biaya Proyek", ikon="")
        b2.clicked.connect(self._lihat_proyek)
        baris.addWidget(b2)
        baris.addStretch()
        self.lbl_proyek = QLabel("")
        self.lbl_proyek.setObjectName("Muted")
        baris.addWidget(self.lbl_proyek)
        lay.addLayout(baris)

    def _bangun_cabang(self):
        lay = QVBoxLayout(self.tab_cabang)
        lay.setContentsMargins(0, 12, 0, 0)
        lay.setSpacing(12)

        self.tabel_cabang = w.Tabel([
            ("Kode", 105), ("Nama Cabang", -1), ("Kota", 155),
            ("Penanggung Jawab", 175), ("NPWP", 195), ("Alamat", 260),
        ])
        lay.addWidget(self.tabel_cabang, 1)

        baris = QHBoxLayout()
        b = w.tombol("Tambah Cabang", gaya="primary", ikon="+")
        b.clicked.connect(self._tambah_cabang)
        baris.addWidget(b)
        baris.addStretch()
        self.lbl_cabang = QLabel("")
        self.lbl_cabang.setObjectName("Muted")
        baris.addWidget(self.lbl_cabang)
        lay.addLayout(baris)

    def _bangun_laporan(self):
        lay = QVBoxLayout(self.tab_laporan)
        lay.setContentsMargins(0, 12, 0, 0)
        lay.setSpacing(12)

        baris = QHBoxLayout()
        baris.setSpacing(11)
        baris.addWidget(w.label("Dimensi:", objek="FormLabel"))
        self.cmb_dimensi = QComboBox()
        self.cmb_dimensi.addItem("Cost Center", "cost_center")
        self.cmb_dimensi.addItem("Proyek", "proyek")
        self.cmb_dimensi.addItem("Cabang", "cabang")
        self.cmb_dimensi.currentIndexChanged.connect(self._muat_laporan)
        baris.addWidget(self.cmb_dimensi)
        baris.addStretch()
        self.lbl_laporan = QLabel("")
        self.lbl_laporan.setObjectName("Muted")
        baris.addWidget(self.lbl_laporan)
        lay.addLayout(baris)

        self.tabel_laporan = w.Tabel([
            ("Kode", 105), ("Nama", -1), ("Beban", 185),
            ("Pendapatan", 185), ("Laba/Rugi", 185),
        ])
        lay.addWidget(self.tabel_laporan, 1)

    def muat(self):
        if not self.ctx.company_id:
            return
        idx = self.tabs.currentIndex()
        if idx == 0:
            self._muat_cc()
        elif idx == 1:
            self._muat_proyek()
        elif idx == 2:
            self._muat_cabang()
        else:
            self._muat_laporan()

    def _muat_cc(self):
        cid = self.ctx.company_id
        data = O.daftar_cost_center(cid)
        baris = []
        for c in data:
            realisasi = int(db.scalar(
                """SELECT COALESCE(SUM(jumlah),0) FROM expenses
                   WHERE company_id=? AND cost_center_id=?
                     AND substr(tanggal,1,4)=? AND status != 'ditolak'""",
                (cid, c["id"], str(self.ctx.tahun))))
            anggaran = int(c["anggaran"] or 0)
            sisa = anggaran - realisasi
            baris.append([
                c["kode"], c["nama"], c["penanggung_jawab"] or "",
                tx.rupiah(anggaran) if anggaran else "Belum dianggarkan",
                tx.rupiah(realisasi),
                tx.rupiah(sisa) if anggaran else "",
            ])
        self.tabel_cc.isi(baris, align_kanan={3, 4, 5})
        self.lbl_cc.setText(f"{len(data)} cost center")

    def _muat_proyek(self):
        data = O.daftar_proyek(self.ctx.company_id)
        baris, warna = [], {}
        for i, p in enumerate(data):
            idx = len(baris)
            baris.append([
                p["kode"], p["nama"], p["partner_nama"] or "",
                theme.tanggal_id(p["tanggal_mulai"] or ""),
                theme.tanggal_id(p["tanggal_selesai"] or ""),
                tx.rupiah(p["nilai_kontrak"] or 0),
                tx.rupiah(p["anggaran"] or 0),
                istilah.label("status", p["status"]),
            ])
            warna[idx] = {"berjalan": C.INFO, "selesai": C.SUCCESS,
                          "batal": C.TEXT_FAINT}.get(p["status"], C.TEXT)
        self.tabel_proyek.isi(baris, warna_baris=warna, align_kanan={5, 6})
        self.lbl_proyek.setText(f"{len(data)} proyek")

    def _muat_cabang(self):
        data = O.daftar_cabang(self.ctx.company_id)
        baris = [[c["kode"], c["nama"], c["kota"] or "",
                  c["penanggung_jawab"] or "", c["npwp"] or "",
                  c["alamat"] or ""] for c in data]
        self.tabel_cabang.isi(baris)
        self.lbl_cabang.setText(f"{len(data)} cabang")

    def _muat_laporan(self):
        cid = self.ctx.company_id
        if not cid:
            return
        try:
            data = O.laba_rugi_dimensi(cid, self.ctx.tahun,
                                       self.cmb_dimensi.currentData())
        except Exception as e:
            QMessageBox.critical(self, "Gagal", str(e))
            return
        baris, warna = [], {}
        for i, d in enumerate(data):
            idx = len(baris)
            baris.append([d["kode"], d["nama"], tx.rupiah(d["beban"]),
                          tx.rupiah(d["pendapatan"]), tx.rupiah(d["laba"])])
            warna[idx] = C.SUCCESS if d["laba"] >= 0 else C.DANGER
        self.tabel_laporan.isi(baris, warna_baris=warna, align_kanan={2, 3, 4})
        self.lbl_laporan.setText(
            f"Tahun {self.ctx.tahun} · {len(data)} dimensi. "
            "Catatan: hanya biaya dengan dimensi yang tercatat di sini.")

    def _tambah_cc(self):
        if not self.ctx.company_id:
            QMessageBox.information(self, "Belum ada perusahaan",
                                    "Buat profil perusahaan terlebih dahulu.")
            return
        d = DialogCostCenter(self.ctx, self)
        if d.exec():
            self.muat()

    def _tambah_proyek(self):
        if not self.ctx.company_id:
            QMessageBox.information(self, "Belum ada perusahaan",
                                    "Buat profil perusahaan terlebih dahulu.")
            return
        d = DialogProyek(self.ctx, self)
        if d.exec():
            self.muat()

    def _tambah_cabang(self):
        if not self.ctx.company_id:
            QMessageBox.information(self, "Belum ada perusahaan",
                                    "Buat profil perusahaan terlebih dahulu.")
            return
        d = DialogCabang(self.ctx, self)
        if d.exec():
            self.muat()

    def _lihat_proyek(self):
        r = self.tabel_proyek.baris_terpilih()
        if r is None:
            QMessageBox.information(self, "Belum dipilih", "Pilih satu proyek.")
            return
        data = O.daftar_proyek(self.ctx.company_id)
        if r >= len(data):
            return
        p = data[r]

        biaya = db.q("""SELECT e.*, c.nama AS kategori FROM expenses e
                        LEFT JOIN expense_categories c ON c.id = e.kategori_id
                        WHERE e.company_id=? AND e.project_id=?
                        ORDER BY e.tanggal DESC""",
                     (self.ctx.company_id, p["id"]))
        total = sum(int(b["jumlah"]) for b in biaya)

        dlg = QDialog(self)
        dlg.setWindowTitle(f"Biaya Proyek - {p['nama']}")
        dlg.setMinimumSize(880, 580)
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(22, 20, 22, 20)
        lay.setSpacing(12)

        j = QLabel(p["nama"])
        j.setObjectName("SectionTitle")
        lay.addWidget(j)

        kartu = w.Card()
        kl = kartu.body()
        b = QHBoxLayout()
        b.setSpacing(26)
        b.addWidget(w.MiniStat("Nilai Kontrak", tx.rupiah(p["nilai_kontrak"] or 0)))
        b.addWidget(w.MiniStat("Anggaran Biaya", tx.rupiah(p["anggaran"] or 0)))
        b.addWidget(w.MiniStat("Realisasi Biaya", tx.rupiah(total), C.PRIMARY))
        selisih = int(p["anggaran"] or 0) - total
        b.addWidget(w.MiniStat("Sisa Anggaran", tx.rupiah(selisih),
                               C.SUCCESS if selisih >= 0 else C.DANGER))
        b.addStretch()
        kl.addLayout(b)
        lay.addWidget(kartu)

        t = w.Tabel([
            ("Tanggal", 110), ("Nomor", 155), ("Uraian", -1),
            ("Kategori", 145), ("Jumlah", 165),
        ])
        t.isi([[theme.tanggal_id(x["tanggal"]), x["nomor"], x["uraian"],
                x["kategori"] or "", tx.rupiah(x["jumlah"])] for x in biaya],
              align_kanan={4})
        lay.addWidget(t, 1)

        bt = w.tombol("Tutup", gaya="primary")
        bt.clicked.connect(dlg.accept)
        bl = QHBoxLayout()
        bl.addStretch()
        bl.addWidget(bt)
        lay.addLayout(bl)
        dlg.exec()


# ==========================================================================
# HALAMAN KONSOLIDASI
# ==========================================================================
class KonsolidasiPage(QWidget):
    pindah_halaman = Signal(str)

    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx

        luar = QVBoxLayout(self)
        luar.setContentsMargins(0, 0, 0, 0)
        luar.setSpacing(0)

        self.header = w.PageHeader(
            "Konsolidasi & Multi Entitas",
            "Gabungkan laporan beberapa perusahaan dalam satu grup kepemilikan.")

        b = w.tombol("Grup Baru", gaya="primary", ikon="+")
        b.clicked.connect(self._grup_baru)
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

        self.lay.addWidget(w.HelpPanel(
            "Tentang laporan konsolidasi",
            "Bila Anda memiliki beberapa perusahaan, laporan konsolidasi "
            "menjumlahkan seluruh entitas dalam satu grup sesuai persentase "
            "kepemilikan.\n\n"
            "Penting: transaksi antar-entitas (misalnya pinjaman dari induk ke "
            "anak, atau penjualan antar-perusahaan) perlu dieliminasi agar tidak "
            "terhitung ganda. Lakukan eliminasi jurnal secara manual di menu "
            "Jurnal Umum.",
            "PSAK 65 - laporan keuangan konsolidasian. PSAK 4 - laporan "
            "keuangan tersendiri."))

        # Baris pilihan: grup dan tahun.
        baris = QHBoxLayout()
        baris.setSpacing(11)
        baris.addWidget(w.label("Grup:", objek="FormLabel"))
        self.cmb_grup = QComboBox()
        self.cmb_grup.currentIndexChanged.connect(self.muat)
        baris.addWidget(self.cmb_grup, 1)

        baris.addWidget(w.label("Tahun:", objek="FormLabel"))
        self.spin_tahun = QSpinBox()
        self.spin_tahun.setRange(2000, 2100)
        self.spin_tahun.setValue(datetime.now().year)
        self.spin_tahun.valueChanged.connect(self.muat)
        baris.addWidget(self.spin_tahun)
        baris.addStretch()
        self.lay.addLayout(baris)

        # Baris tombol dipisah supaya tidak meluber saat jendela menyempit.
        baris_aksi = QHBoxLayout()
        baris_aksi.setSpacing(11)
        b2 = w.tombol("Tambah Anggota", ikon="+")
        b2.clicked.connect(self._tambah_anggota)
        baris_aksi.addWidget(b2)

        b3 = w.tombol("Tampilkan Konsolidasi", gaya="primary", ikon="laporan")
        b3.clicked.connect(self._tampilkan)
        baris_aksi.addWidget(b3)
        baris_aksi.addStretch()
        self.lay.addLayout(baris_aksi)

        self.area = QWidget()
        self.area_lay = QVBoxLayout(self.area)
        self.area_lay.setContentsMargins(0, 0, 0, 0)
        self.area_lay.setSpacing(13)
        self.lay.addWidget(self.area, 1)

    def muat(self):
        combo = self.cmb_grup
        lama = combo.currentData()
        combo.blockSignals(True)
        combo.clear()
        for g in O.daftar_grup_entitas():
            combo.addItem(g["nama"], g["id"])
        i = combo.findData(lama)
        combo.setCurrentIndex(i if i >= 0 else 0)
        combo.blockSignals(False)
        self._tampilkan()

    def _tampilkan(self):
        while self.area_lay.count():
            it = self.area_lay.takeAt(0)
            wdg = it.widget()
            if wdg is not None:
                wdg.setParent(None)
                wdg.deleteLater()

        grup_id = self.cmb_grup.currentData()
        if not grup_id:
            self.area_lay.addWidget(w.InfoBanner(
                "Belum ada grup entitas. Buat grup terlebih dahulu, lalu "
                "tambahkan perusahaan sebagai anggota.", "info",
                "Mulai dari sini"))
            return

        anggota = O.anggota_grup(grup_id)
        kartu = w.Card()
        kl = kartu.body()
        kl.addWidget(w.label("Anggota Grup", objek="SectionTitle"))
        t = w.Tabel([("Perusahaan", -1), ("Bentuk", 165),
                     ("Kepemilikan", 135)])
        t.isi([[a["nama"], a["bentuk"], f"{a['persentase_kepemilikan']:g}%"]
               for a in anggota], align_kanan={2})
        t.setMinimumHeight(140)
        kl.addWidget(t)
        self.area_lay.addWidget(kartu)

        if not anggota:
            self.area_lay.addWidget(w.InfoBanner(
                "Grup ini belum memiliki anggota. Tambahkan perusahaan.",
                "warning", "Belum ada anggota"))
            return

        try:
            laporan = O.laporan_konsolidasi(grup_id, self.spin_tahun.value())
        except Exception as e:
            self.area_lay.addWidget(w.InfoBanner(str(e), "danger",
                                                 "Gagal menyusun konsolidasi"))
            return

        kpi = QWidget()
        kpi_lay = QHBoxLayout(kpi)
        kpi_lay.setContentsMargins(0, 0, 0, 0)
        kpi_lay.setSpacing(14)
        tot = laporan["total"]
        kpi_lay.addWidget(w.KpiTile("Total Aset", tx.rupiah(tot["aset"]),
                                    f"{laporan['jumlah_entitas']} entitas",
                                    C.PRIMARY, "bank"))
        kpi_lay.addWidget(w.KpiTile("Total Liabilitas", tx.rupiah(tot["liabilitas"]),
                                    "Kewajiban gabungan", C.DANGER, "laporan_kecil"))
        kpi_lay.addWidget(w.KpiTile("Total Ekuitas", tx.rupiah(tot["ekuitas"]),
                                    "Modal gabungan", C.TEXT, ""))
        kpi_lay.addWidget(w.KpiTile("Pendapatan", tx.rupiah(tot["pendapatan"]),
                                    f"Tahun {self.spin_tahun.value()}",
                                    C.SUCCESS, "penjualan"))
        kpi_lay.addWidget(w.KpiTile("Laba Bersih", tx.rupiah(tot["laba"]),
                                    "Setelah proporsi kepemilikan",
                                    C.SUCCESS if tot["laba"] >= 0 else C.DANGER,
                                    ""))
        self.area_lay.addWidget(kpi)

        kartu2 = w.Card()
        kl2 = kartu2.body()
        kl2.addWidget(w.label("Rincian per Entitas", objek="SectionTitle"))
        t2 = w.Tabel([
            ("Perusahaan", -1), ("Kepemilikan", 120), ("Aset", 165),
            ("Liabilitas", 165), ("Ekuitas", 165), ("Pendapatan", 165),
            ("Laba", 165),
        ])
        t2.isi([[e["nama"], f"{e['persentase']:g}%", tx.rupiah(e["aset"]),
                 tx.rupiah(e["liabilitas"]), tx.rupiah(e["ekuitas"]),
                 tx.rupiah(e["pendapatan"]), tx.rupiah(e["laba"])]
                for e in laporan["per_entitas"]], align_kanan={1, 2, 3, 4, 5, 6})
        t2.setMinimumHeight(180)
        kl2.addWidget(t2)
        self.area_lay.addWidget(kartu2)

        self.area_lay.addWidget(w.InfoBanner(laporan["catatan"], "warning",
                                             "Catatan eliminasi"))
        self.area_lay.addStretch()

    def _grup_baru(self):
        d = DialogGrupBaru(self)
        if d.exec():
            self.muat()

    def _tambah_anggota(self):
        grup_id = self.cmb_grup.currentData()
        if not grup_id:
            QMessageBox.information(self, "Belum ada grup",
                                    "Buat grup terlebih dahulu.")
            return
        d = DialogTambahAnggota(self.ctx, grup_id, self)
        if d.exec():
            self.muat()


class DialogGrupBaru(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Buat Grup Entitas")
        self.setMinimumWidth(520)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 22, 24, 22)
        lay.setSpacing(13)

        j = QLabel("Grup Entitas Baru")
        j.setObjectName("SectionTitle")
        lay.addWidget(j)

        lay.addWidget(w.HelpPanel(
            "Apa itu grup entitas?",
            "Grup entitas adalah kumpulan perusahaan yang Anda anggap satu "
            "kesatuan usaha - misalnya perusahaan induk beserta anak "
            "perusahaannya.\n\n"
            "Setelah grup dibuat, tambahkan perusahaan sebagai anggota beserta "
            "persentase kepemilikan.",
            "PSAK 65 - laporan keuangan konsolidasian."))

        lay.addWidget(w.label("Nama Grup", objek="FormLabel"))
        self.inp_nama = QLineEdit()
        self.inp_nama.setPlaceholderText("mis. Grup Usaha Keluarga Santoso")
        lay.addWidget(self.inp_nama)

        lay.addWidget(w.label("Catatan", objek="FormLabel"))
        self.inp_catatan = QLineEdit()
        lay.addWidget(self.inp_catatan)

        aksi = QHBoxLayout()
        aksi.addStretch()
        b = w.tombol("Batal")
        b.clicked.connect(self.reject)
        aksi.addWidget(b)
        bs = w.tombol("Simpan", gaya="primary")
        bs.clicked.connect(self._simpan)
        aksi.addWidget(bs)
        lay.addLayout(aksi)

    def _simpan(self):
        try:
            if not self.inp_nama.text().strip():
                QMessageBox.warning(self, "Nama kosong", "Isi nama grup.")
                return
            O.buat_grup_entitas(self.inp_nama.text().strip(),
                                self.inp_catatan.text().strip())
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Gagal menyimpan", str(e))


class DialogTambahAnggota(QDialog):
    def __init__(self, ctx, grup_id, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.grup_id = grup_id
        self.setWindowTitle("Tambah Anggota Grup")
        self.setMinimumWidth(560)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 22, 24, 22)
        lay.setSpacing(13)

        j = QLabel("Tambah Perusahaan ke Grup")
        j.setObjectName("SectionTitle")
        lay.addWidget(j)

        lay.addWidget(w.label("Perusahaan", objek="FormLabel"))
        self.cmb_company = QComboBox()
        for c in M.db.q("SELECT id, nama, bentuk FROM companies WHERE is_active=1 "
                        "ORDER BY nama"):
            self.cmb_company.addItem(f"{c['nama']} ({c['bentuk']})", c["id"])
        lay.addWidget(self.cmb_company)

        lay.addWidget(w.label("Persentase Kepemilikan (%)", objek="FormLabel"))
        self.spin_persen = QSpinBox()
        self.spin_persen.setRange(1, 100)
        self.spin_persen.setValue(100)
        self.spin_persen.setSuffix(" %")
        lay.addWidget(self.spin_persen)

        lay.addWidget(w.InfoBanner(
            "Persentase kepemilikan menentukan porsi laporan entitas yang "
            "digabungkan. Untuk entitas yang dimiliki penuh, isi 100%.",
            "info"))

        aksi = QHBoxLayout()
        aksi.addStretch()
        b = w.tombol("Batal")
        b.clicked.connect(self.reject)
        aksi.addWidget(b)
        bs = w.tombol("Tambahkan", gaya="primary")
        bs.clicked.connect(self._simpan)
        aksi.addWidget(bs)
        lay.addLayout(aksi)

    def _simpan(self):
        try:
            O.tambah_anggota_grup(self.grup_id, self.cmb_company.currentData(),
                                  self.spin_persen.value())
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Gagal menyimpan", str(e))


# ==========================================================================
# HALAMAN TUTUP BUKU & OTOMASI
# ==========================================================================
class PeriodePage(QWidget):
    pindah_halaman = Signal(str)

    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx

        luar = QVBoxLayout(self)
        luar.setContentsMargins(0, 0, 0, 0)
        luar.setSpacing(0)

        self.header = w.PageHeader(
            "Tutup Buku & Otomasi",
            "Kunci periode yang sudah selesai, atur jurnal berulang, dan kelola "
            "pengingat.")

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

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tab_periode = QWidget()
        self.tab_otomasi = QWidget()
        self.tab_reminder = QWidget()
        self.tabs.addTab(self.tab_periode, "Tutup Buku")
        self.tabs.addTab(self.tab_otomasi, "Jurnal Berulang")
        self.tabs.addTab(self.tab_reminder, "Pengingat")
        self.tabs.currentChanged.connect(self.muat)
        self.lay.addWidget(self.tabs, 1)

        self._bangun_periode()
        self._bangun_otomasi()
        self._bangun_reminder()

    def _bangun_periode(self):
        lay = QVBoxLayout(self.tab_periode)
        lay.setContentsMargins(0, 12, 0, 0)
        lay.setSpacing(12)

        lay.addWidget(w.HelpPanel(
            "Tentang tutup buku",
            "Tutup buku mengunci satu periode agar tidak ada lagi perubahan. "
            "Ini melindungi laporan yang sudah diserahkan.\n\n"
            "Sebelum menutup, pastikan:\n"
            "• Semua transaksi periode tersebut sudah dicatat\n"
            "• Rekonsiliasi bank sudah selesai\n"
            "• Stok opname sudah dilakukan (bila ada persediaan)\n"
            "• Pajak masa tersebut sudah dibayar dan dilaporkan\n\n"
            "Tutup buku dapat dibuka kembali bila diperlukan, dengan catatan "
            "alasan yang jelas.",
            "Pasal 28 UU KUP - pembukuan ditutup pada akhir tahun pajak. "
            "Setiap perubahan setelah penutupan harus dapat "
            "dipertanggungjawabkan."))

        baris = QHBoxLayout()
        baris.setSpacing(11)
        baris.addWidget(w.label("Tahun:", objek="FormLabel"))
        self.spin_tahun_periode = QSpinBox()
        self.spin_tahun_periode.setRange(2000, 2100)
        self.spin_tahun_periode.setValue(self.ctx.tahun)
        self.spin_tahun_periode.valueChanged.connect(self._muat_periode)
        baris.addWidget(self.spin_tahun_periode)
        baris.addStretch()
        self.lbl_periode = QLabel("")
        self.lbl_periode.setObjectName("Muted")
        baris.addWidget(self.lbl_periode)
        lay.addLayout(baris)

        self.tabel_periode = w.Tabel([
            ("Periode", 130), ("Status", 155), ("Ditutup Oleh", 165),
            ("Tanggal Tutup", 165), ("Catatan", -1),
        ])
        lay.addWidget(self.tabel_periode, 1)

        baris2 = QHBoxLayout()
        baris2.setSpacing(9)
        b1 = w.tombol("Tutup Periode Ini", gaya="primary", ikon="periode")
        b1.clicked.connect(self._tutup)
        baris2.addWidget(b1)
        b2 = w.tombol("Buka Kembali", ikon="buka")
        b2.clicked.connect(self._buka)
        baris2.addWidget(b2)
        b3 = w.tombol("Tutup Tahun Penuh", ikon="kalender")
        b3.clicked.connect(self._tutup_tahun)
        baris2.addWidget(b3)
        baris2.addStretch()
        lay.addLayout(baris2)

    def _bangun_otomasi(self):
        lay = QVBoxLayout(self.tab_otomasi)
        lay.setContentsMargins(0, 12, 0, 0)
        lay.setSpacing(12)

        lay.addWidget(w.HelpPanel(
            "Tentang jurnal berulang",
            "Buat template untuk transaksi yang berulang secara berkala "
            "misalnya sewa kantor bulanan, gaji tetap, atau cicilan bank.\n\n"
            "Setelah template dibuat, jalankan otomasi dan aplikasi akan "
            "membuat semua transaksi yang sudah jatuh tempo secara otomatis.",
            "Efisiensi pencatatan; mengurangi risiko lupa mencatat biaya rutin."))

        baris = QHBoxLayout()
        baris.setSpacing(9)
        b1 = w.tombol("Template Baru", gaya="primary", ikon="+")
        b1.clicked.connect(self._template_baru)
        baris.addWidget(b1)
        b2 = w.tombol("Jalankan Sekarang", gaya="success", ikon="simpan")
        b2.clicked.connect(self._jalankan_otomasi)
        baris.addWidget(b2)
        b3 = w.tombol("Hentikan", gaya="danger", ikon="hapus")
        b3.clicked.connect(self._hentikan_template)
        baris.addWidget(b3)
        baris.addStretch()
        self.lbl_otomasi = QLabel("")
        self.lbl_otomasi.setObjectName("Muted")
        baris.addWidget(self.lbl_otomasi)
        lay.addLayout(baris)

        self.tabel_otomasi = w.Tabel([
            ("Nama Template", -1), ("Tipe", 120), ("Frekuensi", 135),
            ("Mulai", 110), ("Berikutnya", 115), ("Sudah Dibuat", 120),
            ("Status", 105),
        ])
        lay.addWidget(self.tabel_otomasi, 1)

    def _bangun_reminder(self):
        lay = QVBoxLayout(self.tab_reminder)
        lay.setContentsMargins(0, 12, 0, 0)
        lay.setSpacing(12)

        baris = QHBoxLayout()
        baris.setSpacing(9)
        b1 = w.tombol("Pengingat Piutang", gaya="primary", ikon="peringatan")
        b1.clicked.connect(self._reminder_piutang)
        baris.addWidget(b1)
        b2 = w.tombol("Pengingat Utang", gaya="primary", ikon="peringatan")
        b2.clicked.connect(self._reminder_utang)
        baris.addWidget(b2)
        b3 = w.tombol("Tandai Selesai", gaya="success", ikon="simpan")
        b3.clicked.connect(self._selesaikan_reminder)
        baris.addWidget(b3)
        baris.addStretch()
        self.lbl_reminder = QLabel("")
        self.lbl_reminder.setObjectName("Muted")
        baris.addWidget(self.lbl_reminder)
        lay.addLayout(baris)

        self.tabel_reminder = w.Tabel([
            ("Jatuh Tempo", 130), ("Judul", -1), ("Jenis", 130),
            ("Nilai", 165), ("Status", 125), ("Catatan", 240),
        ])
        lay.addWidget(self.tabel_reminder, 1)

    def muat(self):
        if not self.ctx.company_id:
            return
        idx = self.tabs.currentIndex()
        if idx == 0:
            self._muat_periode()
        elif idx == 1:
            self._muat_otomasi()
        else:
            self._muat_reminder()

    def _muat_periode(self):
        data = O.daftar_periode(self.ctx.company_id, self.spin_tahun_periode.value())
        baris, warna = [], {}
        jumlah_tutup = 0
        for i, p in enumerate(data):
            idx = len(baris)
            if p["status"] == "tertutup":
                jumlah_tutup += 1
            baris.append([
                p["periode"],
                "Tertutup" if p["status"] == "tertutup" else "Terbuka",
                p["ditutup_oleh"] or "",
                (p["tanggal_tutup"] or "")[:16],
                p["catatan"] or "",
            ])
            warna[idx] = C.TEXT_MUTED if p["status"] == "tertutup" else C.SUCCESS
        self.tabel_periode.isi(baris, warna_baris=warna)
        self.lbl_periode.setText(
            f"{jumlah_tutup} dari {len(data)} periode tertutup")

    def _muat_otomasi(self):
        data = O.daftar_template_berulang(self.ctx.company_id, aktif_saja=False)
        baris, warna = [], {}
        for i, t in enumerate(data):
            idx = len(baris)
            baris.append([
                t["nama"],
                istilah.label("tipe", t["tipe"]),
                t["frekuensi"].title(),
                theme.tanggal_id(t["tanggal_mulai"] or ""),
                theme.tanggal_id(t["tanggal_berikut"] or ""),
                str(t["jumlah_terbuat"]),
                "Aktif" if t["aktif"] else "Dihentikan",
            ])
            warna[idx] = C.SUCCESS if t["aktif"] else C.TEXT_FAINT
        self.tabel_otomasi.isi(baris, warna_baris=warna, align_kanan={5})
        aktif = len([t for t in data if t["aktif"]])
        self.lbl_otomasi.setText(f"{aktif} template aktif dari {len(data)}")

    def _muat_reminder(self):
        data = O.daftar_reminder(self.ctx.company_id, "")
        baris, warna = [], {}
        for i, r in enumerate(data):
            idx = len(baris)
            baris.append([
                theme.tanggal_id(r["tanggal_jatuh"]), r["judul"],
                istilah.label("tipe", r["tipe"]),
                tx.rupiah(r["jumlah"]) if r["jumlah"] else "",
                istilah.label("status", r["status"]),
                r["keterangan"] or "",
            ])
            if r["status"] == "selesai":
                warna[idx] = C.TEXT_FAINT
            else:
                try:
                    jt = datetime.fromisoformat(r["tanggal_jatuh"][:10]).date()
                    hari = (jt - datetime.now().date()).days
                    if hari < 0:
                        warna[idx] = C.DANGER
                    elif hari <= 3:
                        warna[idx] = C.WARNING
                except ValueError:
                    pass
        self.tabel_reminder.isi(baris, warna_baris=warna, align_kanan={3})
        aktif = len([r for r in data if r["status"] == "aktif"])
        self.lbl_reminder.setText(f"{aktif} pengingat aktif")

    def _periode_terpilih(self):
        r = self.tabel_periode.baris_terpilih()
        if r is None:
            return None
        data = O.daftar_periode(self.ctx.company_id, self.spin_tahun_periode.value())
        return data[r] if r < len(data) else None

    def _tutup(self):
        p = self._periode_terpilih()
        if p is None:
            QMessageBox.information(self, "Belum dipilih", "Pilih satu periode.")
            return
        if p["status"] == "tertutup":
            QMessageBox.information(self, "Sudah tertutup",
                                    "Periode ini sudah tertutup.")
            return

        saldo = acc.neraca_saldo(self.ctx.company_id, self.spin_tahun_periode.value(),
                                 bulan=int(p["periode"][5:7]))
        pesan = (f"Tutup periode {p['periode']}?\n\n"
                 "Setelah ditutup, transaksi pada periode ini tidak dapat "
                 "diubah lagi.\n\n"
                 "Pemeriksaan:\n"
                 f"• Neraca saldo seimbang: {'Ya' if saldo.seimbang else 'TIDAK'}")
        if not saldo.seimbang:
            pesan += (f"\n\nPERHATIAN: Neraca saldo tidak seimbang "
                      f"(selisih {tx.rupiah(abs(saldo.selisih))}). "
                      "Periksa jurnal Anda sebelum menutup buku.")

        if QMessageBox.question(self, "Konfirmasi Tutup Buku", pesan,
                                QMessageBox.Yes | QMessageBox.No,
                                QMessageBox.No) != QMessageBox.Yes:
            return

        from PySide6.QtWidgets import QInputDialog
        catatan, ok = QInputDialog.getText(
            self, "Catatan Tutup Buku",
            "Catatan (opsional, misal: 'Laporan sudah diserahkan ke bank'):")
        if not ok:
            return

        try:
            O.tutup_buku(self.ctx.company_id, p["periode"],
                         self.ctx.full_name or self.ctx.username, catatan,
                         self.ctx.user_id)
            self.muat()
            QMessageBox.information(self, "Berhasil",
                                    f"Periode {p['periode']} berhasil ditutup.")
        except Exception as e:
            QMessageBox.critical(self, "Gagal menutup buku", str(e))

    def _buka(self):
        p = self._periode_terpilih()
        if p is None:
            QMessageBox.information(self, "Belum dipilih", "Pilih satu periode.")
            return
        if p["status"] != "tertutup":
            QMessageBox.information(self, "Belum tertutup",
                                    "Periode ini masih terbuka.")
            return

        from PySide6.QtWidgets import QInputDialog
        alasan, ok = QInputDialog.getText(
            self, "Alasan Buka Kembali",
            "Mengapa periode ini dibuka kembali?\n"
            "(Alasan dicatat dalam log audit)")
        if not ok or not alasan.strip():
            QMessageBox.information(self, "Dibatalkan",
                                    "Alasan wajib diisi untuk membuka kembali "
                                    "periode.")
            return

        try:
            O.buka_buku(self.ctx.company_id, p["periode"],
                        self.ctx.full_name or self.ctx.username, alasan,
                        self.ctx.user_id)
            self.muat()
            QMessageBox.information(
                self, "Periode dibuka",
                f"Periode {p['periode']} dibuka kembali. Alasan tercatat di "
                "log audit.")
        except Exception as e:
            QMessageBox.critical(self, "Gagal", str(e))

    def _tutup_tahun(self):
        tahun = self.spin_tahun_periode.value()
        if QMessageBox.question(
                self, "Tutup Seluruh Tahun",
                f"Tutup semua periode tahun {tahun} yang masih terbuka?\n\n"
                "Pastikan seluruh transaksi tahun tersebut sudah lengkap.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No) != QMessageBox.Yes:
            return
        berhasil = gagal = 0
        for b in range(1, 13):
            periode = f"{tahun}-{b:02d}"
            try:
                if O.status_periode(self.ctx.company_id, periode) != "tertutup":
                    O.tutup_buku(self.ctx.company_id, periode,
                                 self.ctx.full_name or self.ctx.username,
                                 f"Penutupan massal tahun {tahun}",
                                 self.ctx.user_id)
                    berhasil += 1
            except Exception:
                gagal += 1
        self.muat()
        QMessageBox.information(
            self, "Selesai",
            f"{berhasil} periode ditutup." +
            (f"\n{gagal} periode gagal ditutup." if gagal else ""))

    def _template_baru(self):
        if not self.ctx.company_id:
            QMessageBox.information(self, "Belum ada perusahaan",
                                    "Buat profil perusahaan terlebih dahulu.")
            return
        d = DialogTemplateBerulang(self.ctx, self)
        if d.exec():
            self.muat()

    def _jalankan_otomasi(self):
        try:
            hasil = O.jalankan_template_berulang(self.ctx.company_id,
                                                 user_id=self.ctx.user_id)
            if hasil["jumlah_dibuat"]:
                pesan = f"{hasil['jumlah_dibuat']} transaksi dibuat:\n\n"
                for d in hasil["dibuat"][:10]:
                    pesan += f"• {d['template']} - {theme.tanggal_id(d['tanggal'])}\n"
                if len(hasil["dibuat"]) > 10:
                    pesan += f"\n...dan {len(hasil['dibuat']) - 10} lainnya."
                QMessageBox.information(self, "Otomasi selesai", pesan)
            else:
                QMessageBox.information(self, "Tidak ada yang jatuh tempo",
                                        "Semua template sudah dijalankan sampai "
                                        "tanggal hari ini.")
            if hasil["jumlah_gagal"]:
                g = hasil["gagal"][0]
                QMessageBox.warning(
                    self, "Sebagian gagal",
                    f"{hasil['jumlah_gagal']} template gagal dijalankan.\n\n"
                    f"Contoh: {g['template']} - {g['error']}")
            self.muat()
        except Exception as e:
            QMessageBox.critical(self, "Gagal menjalankan otomasi", str(e))

    def _hentikan_template(self):
        r = self.tabel_otomasi.baris_terpilih()
        if r is None:
            QMessageBox.information(self, "Belum dipilih", "Pilih satu template.")
            return
        data = O.daftar_template_berulang(self.ctx.company_id, aktif_saja=False)
        if r >= len(data):
            return
        t = data[r]
        if QMessageBox.question(
                self, "Konfirmasi",
                f"Hentikan template '{t['nama']}'?",
                QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            O.hapus_template_berulang(t["id"])
            self.muat()

    def _reminder_piutang(self):
        try:
            jumlah = O.buat_reminder_dari_piutang(self.ctx.company_id, 30)
            QMessageBox.information(
                self, "Selesai",
                f"{jumlah} pengingat dibuat untuk piutang yang jatuh tempo "
                "dalam 30 hari ke depan." if jumlah else
                "Semua piutang sudah memiliki pengingat.")
            self.muat()
        except Exception as e:
            QMessageBox.critical(self, "Gagal", str(e))

    def _reminder_utang(self):
        try:
            jumlah = O.buat_reminder_dari_utang(self.ctx.company_id, 30)
            QMessageBox.information(
                self, "Selesai",
                f"{jumlah} pengingat dibuat untuk utang yang jatuh tempo "
                "dalam 30 hari ke depan." if jumlah else
                "Semua utang sudah memiliki pengingat.")
            self.muat()
        except Exception as e:
            QMessageBox.critical(self, "Gagal", str(e))

    def _selesaikan_reminder(self):
        r = self.tabel_reminder.baris_terpilih()
        if r is None:
            QMessageBox.information(self, "Belum dipilih", "Pilih satu pengingat.")
            return
        data = O.daftar_reminder(self.ctx.company_id, "")
        if r >= len(data):
            return
        try:
            O.selesaikan_reminder(data[r]["id"])
            self.muat()
        except Exception as e:
            QMessageBox.critical(self, "Gagal", str(e))


class DialogTemplateBerulang(QDialog):
    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.setWindowTitle("Template Transaksi Berulang")
        self.setMinimumSize(680, 580)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 22, 24, 22)
        lay.setSpacing(13)

        j = QLabel("Template Baru")
        j.setObjectName("SectionTitle")
        lay.addWidget(j)

        lay.addWidget(w.HelpPanel(
            "Jenis template",
            "• <b>Jurnal</b> - untuk penyesuaian rutin (mis. penyusutan bulanan)\n"
            "• <b>Biaya</b> - untuk biaya rutin (mis. sewa, listrik, internet)\n"
            "• <b>Invoice</b> - untuk penagihan berlangganan ke pelanggan",
            "Otomasi pencatatan rutin."))

        g = QGridLayout()
        g.setSpacing(12)

        g.addWidget(w.label("Nama Template", objek="FormLabel"), 0, 0, 1, 2)
        self.inp_nama = QLineEdit()
        self.inp_nama.setPlaceholderText("mis. Sewa Kantor Bulanan")
        g.addWidget(self.inp_nama, 1, 0, 1, 2)

        g.addWidget(w.label("Tipe", objek="FormLabel"), 2, 0)
        self.cmb_tipe = QComboBox()
        self.cmb_tipe.addItem("Biaya (Expense)", "expense")
        self.cmb_tipe.addItem("Jurnal Umum", "jurnal")
        self.cmb_tipe.addItem("Invoice Pelanggan", "invoice")
        self.cmb_tipe.currentIndexChanged.connect(self._ganti_tipe)
        g.addWidget(self.cmb_tipe, 3, 0)

        g.addWidget(w.label("Frekuensi", objek="FormLabel"), 2, 1)
        self.cmb_frekuensi = QComboBox()
        self.cmb_frekuensi.addItem("Bulanan", "bulanan")
        self.cmb_frekuensi.addItem("Mingguan", "mingguan")
        self.cmb_frekuensi.addItem("Harian", "harian")
        self.cmb_frekuensi.addItem("Triwulanan", "triwulanan")
        self.cmb_frekuensi.addItem("Tahunan", "tahunan")
        g.addWidget(self.cmb_frekuensi, 3, 1)

        g.addWidget(w.label("Mulai Tanggal", objek="FormLabel"), 4, 0)
        self.inp_mulai = kalender.pasang(QDateEdit())
        self.inp_mulai.setDisplayFormat("dd/MM/yyyy")
        self.inp_mulai.setDate(QDate.currentDate())
        g.addWidget(self.inp_mulai, 5, 0)

        g.addWidget(w.label("Sampai Tanggal (opsional)", objek="FormLabel"), 4, 1)
        self.inp_akhir = kalender.pasang(QDateEdit())
        self.inp_akhir.setDisplayFormat("dd/MM/yyyy")
        self.inp_akhir.setDate(QDate.currentDate().addYears(1))
        self.inp_akhir.setSpecialValueText(" ")
        g.addWidget(self.inp_akhir, 5, 1)

        g.addWidget(w.label("Jumlah (Rp)", objek="FormLabel"), 6, 0)
        self.inp_jumlah = w.InputRupiah()
        g.addWidget(self.inp_jumlah, 7, 0)

        g.addWidget(w.label("Uraian", objek="FormLabel"), 6, 1)
        self.inp_uraian = QLineEdit()
        self.inp_uraian.setPlaceholderText("mis. Sewa kantor bulan ini")
        g.addWidget(self.inp_uraian, 7, 1)

        g.addWidget(w.label("Akun Beban/Debit", objek="FormLabel"), 8, 0)
        self.cmb_debit = w.combo_akun(ctx.company_id)
        w.set_combo_by_data(self.cmb_debit, "6021")
        g.addWidget(self.cmb_debit, 9, 0)

        g.addWidget(w.label("Akun Kas/Kredit", objek="FormLabel"), 8, 1)
        self.cmb_kredit = w.combo_akun(ctx.company_id)
        w.set_combo_by_data(self.cmb_kredit, "1002")
        g.addWidget(self.cmb_kredit, 9, 1)
        lay.addLayout(g)

        self.lbl_preview = QLabel("")
        self.lbl_preview.setWordWrap(True)
        self.lbl_preview.setTextFormat(Qt.RichText)
        theme.latar(self.lbl_preview, f"background: {C.PRIMARY_SOFT}; border-radius: 8px; padding: 11px 13px; "
            f"font-size: {theme.FS_SMALL}px;")
        lay.addWidget(self.lbl_preview)

        aksi = QHBoxLayout()
        aksi.addStretch()
        b = w.tombol("Batal")
        b.clicked.connect(self.reject)
        aksi.addWidget(b)
        bs = w.tombol("Simpan Template", gaya="primary")
        bs.clicked.connect(self._simpan)
        aksi.addWidget(bs)
        lay.addLayout(aksi)

        self._ganti_tipe()

    def _ganti_tipe(self):
        tipe = self.cmb_tipe.currentData()
        if tipe == "jurnal":
            self.lbl_preview.setText(
                "Template jurnal membuat entri jurnal dengan debit ke akun "
                "'Akun Beban/Debit' dan kredit ke 'Akun Kas/Kredit' sesuai "
                "uraian yang Anda isi.")
        elif tipe == "invoice":
            self.lbl_preview.setText(
                "Template invoice membuat tagihan ke pelanggan. Pastikan "
                "pelanggan dan akun pendapatan sudah benar di profil produk.")
        else:
            self.lbl_preview.setText(
                "Template biaya membuat catatan biaya berstatus disetujui "
                "sehingga siap dibayar.")

    def _simpan(self):
        try:
            if not self.inp_nama.text().strip():
                QMessageBox.warning(self, "Nama kosong", "Isi nama template.")
                return
            if self.inp_jumlah.nilai() <= 0:
                QMessageBox.warning(self, "Jumlah kosong", "Isi jumlah.")
                return

            tipe = self.cmb_tipe.currentData()
            payload = {
                "jumlah": self.inp_jumlah.nilai(),
                "uraian": self.inp_uraian.text().strip(),
                "akun_debit": self.cmb_debit.currentData(),
                "akun_kredit": self.cmb_kredit.currentData(),
            }
            O.buat_template_berulang(
                self.ctx.company_id, self.inp_nama.text().strip(), tipe,
                self.inp_mulai.date().toString("yyyy-MM-dd"), payload,
                frekuensi=self.cmb_frekuensi.currentData(),
                tanggal_akhir=self.inp_akhir.date().toString("yyyy-MM-dd"))
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Gagal menyimpan", str(e))


# ==========================================================================
# HALAMAN AKSES LAN
# ==========================================================================
class LanPage(QWidget):
    pindah_halaman = Signal(str)

    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx

        luar = QVBoxLayout(self)
        luar.setContentsMargins(0, 0, 0, 0)
        luar.setSpacing(0)

        self.header = w.PageHeader(
            "Akses Jaringan Lokal (LAN)",
            "Bagikan basis data ke beberapa komputer di kantor tanpa internet.")

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
            "Cara kerja akses LAN",
            "Aplikasi ini menyimpan data di komputer Anda (basis data lokal). "
            "Bila beberapa komputer perlu memakai data yang sama, pilih salah "
            "satu komputer sebagai <b>server</b> dan yang lain sebagai "
            "<b>klien</b>.\n\n"
            "<b>Langkah menyiapkan server:</b>\n"
            "1. Aktifkan mode server di komputer utama\n"
            "2. Catat alamat IP dan port yang muncul\n"
            "3. Izinkan aplikasi di firewall Windows\n"
            "4. Di komputer lain, aktifkan mode klien dan masukkan IP server\n\n"
            "Jaringan tetap lokal - tidak ada data yang keluar ke internet.",
            "Keamanan data - akses dibatasi pada jaringan kantor."))

        self.kartu = w.Card()
        kl2 = self.kartu.body()

        baris = QHBoxLayout()
        baris.setSpacing(11)
        self.chk_aktif = QCheckBox("Aktifkan akses LAN")
        self.chk_aktif.stateChanged.connect(self._simpan)
        baris.addWidget(self.chk_aktif)
        baris.addStretch()
        kl2.addLayout(baris)

        g = QGridLayout()
        g.setSpacing(12)

        # Kotak mode memuat keterangan panjang, jadi diberi satu baris penuh
        # agar teksnya tidak terpotong. Port dan IP diletakkan berdampingan
        # di baris berikutnya.
        g.addWidget(w.label("Mode", objek="FormLabel"), 0, 0, 1, 2)
        self.cmb_mode = QComboBox()
        self.cmb_mode.addItem("Server (komputer ini menyimpan data)", "server")
        self.cmb_mode.addItem("Klien (terhubung ke server lain)", "client")
        self.cmb_mode.currentIndexChanged.connect(self._simpan)
        g.addWidget(self.cmb_mode, 1, 0, 1, 2)

        g.addWidget(w.label("Port", objek="FormLabel"), 2, 0)
        self.spin_port = QSpinBox()
        self.spin_port.setRange(1024, 65535)
        self.spin_port.setValue(8787)
        self.spin_port.valueChanged.connect(self._simpan)
        g.addWidget(self.spin_port, 3, 0)

        g.addWidget(w.label("IP Server (untuk mode klien)", objek="FormLabel"),
                    2, 1)
        self.inp_host = QLineEdit()
        self.inp_host.setPlaceholderText("mis. 192.168.1.10")
        g.addWidget(self.inp_host, 3, 1)
        kl2.addLayout(g)

        baris2 = QHBoxLayout()
        baris2.setSpacing(9)
        b1 = w.tombol("Uji Koneksi", gaya="primary", ikon="lan")
        b1.clicked.connect(self._uji)
        baris2.addWidget(b1)
        b2 = w.tombol("Buat Token Baru", ikon="pengguna")
        b2.clicked.connect(self._token)
        baris2.addWidget(b2)
        baris2.addStretch()
        kl2.addLayout(baris2)

        self.lbl_info = QLabel("")
        self.lbl_info.setWordWrap(True)
        self.lbl_info.setTextFormat(Qt.RichText)
        theme.latar(self.lbl_info, f"background: {C.NEUTRAL_BG}; border-radius: 8px; padding: 12px 14px; "
            f"font-family: {theme.FONT_ANGKA}; font-size: {theme.FS_SMALL}px;")
        kl2.addWidget(self.lbl_info)
        self.lay.addWidget(self.kartu)

        self.kartu_backup = w.Card()
        kl3 = self.kartu_backup.body()
        kl3.addWidget(w.label("Cadangan & Pemulihan Data", objek="SectionTitle"))
        kl3.addWidget(w.label(
            "Buat cadangan rutin agar data aman. Simpan berkas cadangan di "
            "lokasi lain (flashdisk atau drive eksternal).", wrap=True))
        baris3 = QHBoxLayout()
        baris3.setSpacing(9)
        b3 = w.tombol("Buat Cadangan", gaya="primary", ikon="simpan")
        b3.clicked.connect(self._backup)
        baris3.addWidget(b3)
        b4 = w.tombol("Pulihkan dari Cadangan", ikon="segarkan")
        b4.clicked.connect(self._restore)
        baris3.addWidget(b4)
        b5 = w.tombol("Buka Folder Data", ikon="dokumen")
        b5.clicked.connect(self._buka_folder)
        baris3.addWidget(b5)
        baris3.addStretch()
        kl3.addLayout(baris3)
        self.lay.addWidget(self.kartu_backup)
        self.lay.addStretch()

    def muat(self):
        info = O.info_lan()
        self.chk_aktif.blockSignals(True)
        self.cmb_mode.blockSignals(True)
        self.spin_port.blockSignals(True)
        self.chk_aktif.setChecked(bool(info["aktif"]))
        i = self.cmb_mode.findData(info["mode"])
        if i >= 0:
            self.cmb_mode.setCurrentIndex(i)
        self.spin_port.setValue(int(info["port"]))
        self.inp_host.setText(info["server_host"] or "")
        self.chk_aktif.blockSignals(False)
        self.cmb_mode.blockSignals(False)
        self.spin_port.blockSignals(False)

        status = "aktif" if info["aktif"] else "nonaktif"
        self.lbl_info.setText(
            f"<b>Status:</b> {status}<br>"
            f"<b>Alamat IP komputer ini:</b> {info['ip_lokal']}<br>"
            f"<b>Port:</b> {info['port']}<br>"
            f"<b>Token:</b> {'sudah dibuat' if info['token'] else 'belum dibuat'}<br><br>"
            f"<b>Alamat untuk klien:</b> {info['ip_lokal']}:{info['port']}")

    def _simpan(self):
        """
        Simpan setelan LAN.

        Kegagalan dilaporkan ke pengguna. Sebelumnya kegagalan ditelan
        diam-diam, sehingga pengguna mengira setelannya tersimpan padahal
        masih memakai nilai lama, dan LAN tidak menyala tanpa penjelasan.
        """
        try:
            O.set_lan(aktif=self.chk_aktif.isChecked(),
                      port=self.spin_port.value(),
                      mode=self.cmb_mode.currentData(),
                      server_host=self.inp_host.text().strip())
        except Exception as e:
            QMessageBox.critical(
                self, "Setelan LAN gagal disimpan",
                f"Setelan LAN tidak dapat disimpan.\n\n{e}\n\n"
                "Periksa apakah port yang dipilih masih dipakai program lain, "
                "lalu coba lagi.")
            return
        QMessageBox.information(self, "Setelan tersimpan",
                                "Setelan LAN sudah disimpan.")
        self.muat()

    def _uji(self):
        host = self.inp_host.text().strip()
        if not host:
            QMessageBox.information(self, "IP kosong",
                                    "Isi alamat IP server terlebih dahulu.")
            return
        try:
            hasil = O.uji_koneksi_lan(host, self.spin_port.value())
            if hasil["ok"]:
                QMessageBox.information(self, "Berhasil", hasil["pesan"])
            else:
                QMessageBox.warning(self, "Gagal terhubung", hasil["pesan"])
        except Exception as e:
            QMessageBox.critical(self, "Gagal menguji", str(e))

    def _token(self):
        try:
            token = O.token_lan_baru()
            QMessageBox.information(
                self, "Token baru dibuat",
                f"Token: {token}\n\nBagikan token ini ke komputer klien. "
                "Token diperlukan agar hanya komputer yang diizinkan dapat "
                "mengakses data.")
            self.muat()
        except Exception as e:
            QMessageBox.critical(self, "Gagal", str(e))

    def _backup(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Simpan Cadangan",
            str(config.EXPORT_DIR /
                f"cadangan_akuntansiid_{datetime.now():%Y%m%d_%H%M}.db"),
            "Berkas Cadangan (*.db)")
        if not path:
            return
        try:
            db.create_backup(f"Cadangan manual ke {os.path.basename(path)}")
            import shutil
            shutil.copy2(config.DB_PATH, path)
            QMessageBox.information(
                self, "Cadangan dibuat",
                f"Cadangan disimpan di:\n{path}\n\n"
                "Simpan berkas ini di tempat aman (flashdisk atau drive "
                "eksternal).")
        except Exception as e:
            QMessageBox.critical(self, "Gagal membuat cadangan", str(e))

    def _restore(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Pilih Berkas Cadangan", str(config.EXPORT_DIR),
            "Berkas Cadangan (*.db);;Semua Berkas (*)")
        if not path:
            return
        if QMessageBox.warning(
                self, "Konfirmasi Pemulihan",
                "Memulihkan cadangan akan MENGGANTI seluruh data saat ini "
                "dengan isi berkas cadangan.\n\n"
                "Aplikasi perlu ditutup dan dibuka kembali setelah pemulihan.\n\n"
                "Lanjutkan?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No) != QMessageBox.Yes:
            return
        try:
            from pathlib import Path
            db.create_backup("Sebelum pemulihan dari cadangan")
            db.restore_backup(Path(path))
            QMessageBox.information(
                self, "Pemulihan selesai",
                "Data berhasil dipulihkan.\n\nTutup aplikasi lalu buka kembali "
                "agar semua perubahan tampil.")
        except Exception as e:
            QMessageBox.critical(self, "Gagal memulihkan", str(e))

    def _buka_folder(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(config.DATA_DIR)))
