"""
Halaman biaya (expense management) dan bank (rekening, mutasi, rekonsiliasi).
"""
from __future__ import annotations

import os
from datetime import datetime

from PySide6.QtCore import Qt, Signal, QDate
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit, QDateEdit,
    QDialog, QMessageBox, QFrame, QGridLayout, QCheckBox, QTabWidget,
    QFileDialog, QTextEdit,
)

from ... import config, modules as M, modules_ops as O
from ...core import tax_engine as tx
from ... import istilah
from .. import theme, widgets as w
from .. import kalender
from ..theme import C


# ==========================================================================
# BIAYA
# ==========================================================================
class DialogBiaya(QDialog):
    def __init__(self, ctx, parent=None, biaya=None):
        super().__init__(parent)
        self.ctx = ctx
        self.biaya = biaya
        self.setWindowTitle("Ajukan Biaya" if not biaya else "Ubah Biaya")
        self.setMinimumWidth(680)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 22, 24, 22)
        lay.setSpacing(13)

        j = QLabel("Pengajuan Biaya")
        j.setObjectName("SectionTitle")
        lay.addWidget(j)

        if ctx.beginner and not biaya:
            lay.addWidget(w.HelpPanel(
                "Tentang pengajuan biaya",
                "Fitur ini untuk biaya yang perlu persetujuan sebelum dibayar "
                "(misalnya reimbursement karyawan atau pembelian di atas batas "
                "tertentu).\n\n"
                "Alur: Ajukan -> Setujui -> Bayar.\n\n"
                "Biaya di bawah batas kategori langsung berstatus 'disetujui' "
                "sehingga dapat segera dibayar.",
                "Pengendalian internal - pemisahan fungsi pengaju dan penyetuju."))

        g = QGridLayout()
        g.setSpacing(12)

        g.addWidget(w.label("Tanggal", objek="FormLabel"), 0, 0)
        self.inp_tanggal = kalender.pasang(QDateEdit())
        self.inp_tanggal.setDisplayFormat("dd/MM/yyyy")
        self.inp_tanggal.setDate(QDate.currentDate())
        g.addWidget(self.inp_tanggal, 1, 0)

        g.addWidget(w.label("Kategori", objek="FormLabel"), 0, 1)
        self.cmb_kategori = QComboBox()
        self.cmb_kategori.addItem("Tanpa Kategori", None)
        for k in O.daftar_kategori_biaya(ctx.company_id):
            self.cmb_kategori.addItem(k["nama"], k["id"])
        self.cmb_kategori.currentIndexChanged.connect(self._pilih_kategori)
        g.addWidget(self.cmb_kategori, 1, 1)

        g.addWidget(w.label("Tipe Biaya", objek="FormLabel"), 0, 2)
        self.cmb_tipe = QComboBox()
        self.cmb_tipe.addItem("Langsung", "langsung")
        self.cmb_tipe.addItem("Reimbursement", "reimbursement")
        self.cmb_tipe.addItem("Berkala (rutin)", "berkala")
        g.addWidget(self.cmb_tipe, 1, 2)

        g.addWidget(w.label("Uraian Biaya", objek="FormLabel"), 2, 0, 1, 3)
        self.inp_uraian = QLineEdit()
        self.inp_uraian.setPlaceholderText("mis. Tagihan listrik kantor Maret 2026")
        g.addWidget(self.inp_uraian, 3, 0, 1, 3)

        g.addWidget(w.label("Jumlah (Rp)", objek="FormLabel"), 4, 0)
        self.inp_jumlah = w.InputRupiah()
        g.addWidget(self.inp_jumlah, 5, 0)

        g.addWidget(w.label("Vendor / Penerima", objek="FormLabel"), 4, 1)
        self.inp_vendor = QLineEdit()
        g.addWidget(self.inp_vendor, 5, 1)

        g.addWidget(w.label("Diajukan Oleh", objek="FormLabel"), 4, 2)
        self.inp_pengaju = QLineEdit(ctx.full_name or ctx.username)
        g.addWidget(self.inp_pengaju, 5, 2)

        g.addWidget(w.label("Akun Beban", objek="FormLabel"), 6, 0)
        self.cmb_akun_beban = w.combo_akun(ctx.company_id)
        w.set_combo_by_data(self.cmb_akun_beban, "6023")
        g.addWidget(self.cmb_akun_beban, 7, 0)

        g.addWidget(w.label("Dibayar dari", objek="FormLabel"), 6, 1)
        self.cmb_akun_kas = QComboBox()
        for kb in O.daftar_kas_bank(ctx.company_id):
            self.cmb_akun_kas.addItem(f"{kb['nama']}", kb["akun_buku"])
        g.addWidget(self.cmb_akun_kas, 7, 1)

        g.addWidget(w.label("Dimensi: Proyek", objek="FormLabel"), 6, 2)
        self.cmb_proyek = QComboBox()
        self.cmb_proyek.addItem("Tidak ada", None)
        for p in O.daftar_proyek(ctx.company_id):
            self.cmb_proyek.addItem(p["nama"], p["id"])
        g.addWidget(self.cmb_proyek, 7, 2)

        g.addWidget(w.label("Dimensi: Cost Center", objek="FormLabel"), 8, 0)
        self.cmb_cc = QComboBox()
        self.cmb_cc.addItem("Tidak ada", None)
        for c in O.daftar_cost_center(ctx.company_id):
            self.cmb_cc.addItem(c["nama"], c["id"])
        g.addWidget(self.cmb_cc, 9, 0)

        g.addWidget(w.label("Dimensi: Cabang", objek="FormLabel"), 8, 1)
        self.cmb_cabang = QComboBox()
        self.cmb_cabang.addItem("Tidak ada", None)
        for c in O.daftar_cabang(ctx.company_id):
            self.cmb_cabang.addItem(c["nama"], c["id"])
        g.addWidget(self.cmb_cabang, 9, 1)

        g.addWidget(w.label("Catatan", objek="FormLabel"), 8, 2)
        self.inp_catatan = QLineEdit()
        g.addWidget(self.inp_catatan, 9, 2)
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

        if biaya:
            self._muat()

    def _pilih_kategori(self):
        kid = self.cmb_kategori.currentData()
        if not kid:
            return
        for k in O.daftar_kategori_biaya(self.ctx.company_id):
            if k["id"] == kid and k["akun_beban"]:
                w.set_combo_by_data(self.cmb_akun_beban, k["akun_beban"])

    def _muat(self):
        b = self.biaya
        try:
            y, m, d = b["tanggal"][:10].split("-")
            self.inp_tanggal.setDate(QDate(int(y), int(m), int(d)))
        except ValueError:
            pass
        i = self.cmb_kategori.findData(b["kategori_id"])
        if i >= 0:
            self.cmb_kategori.setCurrentIndex(i)
        i = self.cmb_tipe.findData(b["tipe"])
        if i >= 0:
            self.cmb_tipe.setCurrentIndex(i)
        self.inp_uraian.setText(b["uraian"])
        self.inp_jumlah.set_nilai(b["jumlah"])
        self.inp_vendor.setText(b["vendor"] or "")
        self.inp_pengaju.setText(b["diajukan_oleh"] or "")
        w.set_combo_by_data(self.cmb_akun_beban, b["akun_beban"])
        w.set_combo_by_data(self.cmb_akun_kas, b["akun_kas"])
        i = self.cmb_proyek.findData(b["project_id"])
        if i >= 0:
            self.cmb_proyek.setCurrentIndex(i)
        i = self.cmb_cc.findData(b["cost_center_id"])
        if i >= 0:
            self.cmb_cc.setCurrentIndex(i)
        i = self.cmb_cabang.findData(b["branch_id"])
        if i >= 0:
            self.cmb_cabang.setCurrentIndex(i)
        self.inp_catatan.setText(b["catatan"] or "")

    def _simpan(self):
        try:
            if not self.inp_uraian.text().strip():
                QMessageBox.warning(self, "Uraian kosong", "Isi uraian biaya.")
                return
            if self.inp_jumlah.nilai() <= 0:
                QMessageBox.warning(self, "Jumlah kosong", "Isi jumlah biaya.")
                return
            O.ajukan_biaya(
                self.ctx.company_id,
                self.inp_tanggal.date().toString("yyyy-MM-dd"),
                self.inp_uraian.text().strip(),
                self.inp_jumlah.nilai(),
                self.cmb_akun_beban.currentData() or "6023",
                self.cmb_kategori.currentData(),
                self.inp_vendor.text().strip(),
                cost_center_id=self.cmb_cc.currentData(),
                project_id=self.cmb_proyek.currentData(),
                branch_id=self.cmb_cabang.currentData(),
                tipe=self.cmb_tipe.currentData(),
                diajukan_oleh=self.inp_pengaju.text().strip(),
                akun_kas=self.cmb_akun_kas.currentData() or "1002",
                catatan=self.inp_catatan.text().strip(),
                user_id=self.ctx.user_id, username=self.ctx.username)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Gagal menyimpan", str(e))


class BiayaPage(QWidget):
    pindah_halaman = Signal(str)

    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx

        luar = QVBoxLayout(self)
        luar.setContentsMargins(0, 0, 0, 0)
        luar.setSpacing(0)

        self.header = w.PageHeader(
            "Biaya & Pengeluaran",
            "Catat biaya operasional dengan alur pengajuan, persetujuan, dan "
            "pembayaran.")

        b = w.tombol("Ajukan Biaya", gaya="primary", ikon="+")
        b.clicked.connect(self._tambah)
        self.header.tambah_aksi(b)

        b2 = w.tombol("Kategori Biaya", ikon="")
        b2.clicked.connect(self._kategori)
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

        self.banner = QWidget()
        self.banner_lay = QVBoxLayout(self.banner)
        self.banner_lay.setContentsMargins(0, 0, 0, 0)
        self.lay.addWidget(self.banner)

        filter_baris = QHBoxLayout()
        filter_baris.setSpacing(10)
        self.inp_cari = QLineEdit()
        self.inp_cari.setPlaceholderText("Cari uraian, nomor, atau vendor…")
        # Kotak pencarian mengisi sisa ruang, bukan dipaksa lebar tertentu.
        # Lebar tetap membuatnya bertumpuk dengan kotak status di sebelahnya
        # saat jendela menyempit.
        self.inp_cari.setMinimumWidth(160)
        self.inp_cari.textChanged.connect(self.muat)
        filter_baris.addWidget(self.inp_cari, 1)

        self.cmb_status = QComboBox()
        self.cmb_status.addItem("Semua Status", "")
        self.cmb_status.addItem("Diajukan (menunggu)", "diajukan")
        self.cmb_status.addItem("Disetujui", "disetujui")
        self.cmb_status.addItem("Ditolak", "ditolak")
        self.cmb_status.addItem("Dibayar", "dibayar")
        self.cmb_status.addItem("Reimbursed", "reimbursed")
        self.cmb_status.currentIndexChanged.connect(self.muat)
        filter_baris.addWidget(self.cmb_status)

        self.cmb_kategori_filter = QComboBox()
        self.cmb_kategori_filter.addItem("Semua Kategori", None)
        self.cmb_kategori_filter.currentIndexChanged.connect(self.muat)
        filter_baris.addWidget(self.cmb_kategori_filter)
        filter_baris.addStretch()
        self.lbl_info = QLabel("")
        self.lbl_info.setObjectName("Muted")
        filter_baris.addWidget(self.lbl_info)
        self.lay.addLayout(filter_baris)

        self.tabel = w.Tabel([
            ("Nomor", 155), ("Tanggal", 105), ("Uraian", -1), ("Kategori", 140),
            ("Vendor", 155), ("Jumlah", 155), ("Status", 130), ("Pengaju", 130),
        ])
        self.tabel.doubleClicked.connect(self._detail)
        self.lay.addWidget(self.tabel, 1)

        baris = QHBoxLayout()
        baris.setSpacing(9)
        b1 = w.tombol("Lihat Detail", ikon="")
        b1.clicked.connect(self._detail)
        baris.addWidget(b1)
        b2 = w.tombol("Setujui", gaya="success", ikon="simpan")
        b2.clicked.connect(lambda: self._setujui(True))
        baris.addWidget(b2)
        b3 = w.tombol("Tolak", ikon="")
        b3.clicked.connect(lambda: self._setujui(False))
        baris.addWidget(b3)
        b4 = w.tombol("Bayar", gaya="primary", ikon="bank")
        b4.clicked.connect(self._bayar)
        baris.addWidget(b4)
        b5 = w.tombol("Hapus", gaya="danger", ikon="hapus")
        b5.clicked.connect(self._hapus)
        baris.addWidget(b5)
        baris.addStretch()
        self.lay.addLayout(baris)

    def muat(self):
        cid = self.ctx.company_id
        if not cid:
            return

        while self.banner_lay.count():
            it = self.banner_lay.takeAt(0)
            wdg = it.widget()
            if wdg is not None:
                wdg.setParent(None)
                wdg.deleteLater()

        self._refresh_kategori_filter()

        menunggu = O.daftar_biaya(cid, self.ctx.tahun, status="diajukan")
        if menunggu:
            total = sum(b["jumlah"] for b in menunggu)
            self.banner_lay.addWidget(w.InfoBanner(
                f"{len(menunggu)} pengajuan biaya menunggu persetujuan dengan total "
                f"{tx.rupiah(total)}.",
                "warning", "Perlu persetujuan"))

        data = O.daftar_biaya(cid, self.ctx.tahun,
                              self.cmb_status.currentData(),
                              self.cmb_kategori_filter.currentData(),
                              self.inp_cari.text().strip())
        baris, warna = [], {}
        total_dibayar = 0
        for i, b in enumerate(data):
            idx = len(baris)
            if b["dibayar"]:
                total_dibayar += b["jumlah"]
            baris.append([
                b["nomor"], theme.tanggal_id(b["tanggal"]), b["uraian"],
                b["kategori_nama"] or "", b["vendor"] or "",
                tx.rupiah(b["jumlah"]),
                {"draft": "Draft", "diajukan": "Menunggu",
                 "disetujui": "Disetujui", "ditolak": "Ditolak",
                 "dibayar": "Dibayar", "reimbursed": "Reimbursed"}.get(
                     istilah.label("status", b["status"]), istilah.label("status", b["status"])),
                b["diajukan_oleh"] or "",
            ])
            warna[idx] = {"diajukan": C.WARNING, "disetujui": C.INFO,
                          "ditolak": C.DANGER, "dibayar": C.SUCCESS,
                          "reimbursed": C.SUCCESS}.get(b["status"], C.TEXT)
        self.tabel.isi(baris, warna_baris=warna, align_kanan={5})
        self.lbl_info.setText(
            f"{len(data)} catatan biaya · total dibayar {tx.rupiah(total_dibayar)}")

    def _refresh_kategori_filter(self):
        combo = self.cmb_kategori_filter
        data_lama = combo.currentData()
        combo.blockSignals(True)
        combo.clear()
        combo.addItem("Semua Kategori", None)
        for k in O.daftar_kategori_biaya(self.ctx.company_id):
            combo.addItem(k["nama"], k["id"])
        i = combo.findData(data_lama)
        combo.setCurrentIndex(i if i >= 0 else 0)
        combo.blockSignals(False)

    def _biaya_terpilih(self):
        r = self.tabel.baris_terpilih()
        if r is None:
            return None
        data = O.daftar_biaya(self.ctx.company_id, self.ctx.tahun,
                              self.cmb_status.currentData(),
                              self.cmb_kategori_filter.currentData(),
                              self.inp_cari.text().strip())
        return data[r] if r < len(data) else None

    def _tambah(self):
        if not self.ctx.company_id:
            QMessageBox.information(self, "Belum ada perusahaan",
                                    "Buat profil perusahaan terlebih dahulu.")
            return
        d = DialogBiaya(self.ctx, self)
        if d.exec():
            self.muat()

    def _kategori(self):
        d = DialogKategoriBiaya(self.ctx, self)
        if d.exec():
            self.muat()

    def _detail(self):
        b = self._biaya_terpilih()
        if b is None:
            return
        dlg = QDialog(self)
        dlg.setWindowTitle(f"Detail Biaya {b['nomor']}")
        dlg.setMinimumSize(720, 520)
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(22, 20, 22, 20)
        lay.setSpacing(12)

        j = QLabel(f"{b['nomor']} - {b['uraian']}")
        j.setObjectName("SectionTitle")
        lay.addWidget(j)

        kartu = w.Card()
        kl = kartu.body()
        grid = QGridLayout()
        grid.setSpacing(14)
        info = [
            ("Tanggal", theme.tanggal_id(b["tanggal"])),
            ("Kategori", b["kategori_nama"] or ""),
            ("Tipe", istilah.label("tipe", b["tipe"])),
            ("Jumlah", tx.rupiah(b["jumlah"])),
            ("Vendor", b["vendor"] or ""),
            ("Status", istilah.label("status", b["status"])),
            ("Diajukan Oleh", b["diajukan_oleh"] or ""),
            ("Disetujui Oleh", b["disetujui_oleh"] or ""),
            ("Tanggal Bayar", theme.tanggal_id(b["tanggal_bayar"] or "")),
            ("Akun Beban", b["akun_beban"]),
            ("Dibayar Dari", b["akun_kas"]),
            ("Catatan", b["catatan"] or ""),
        ]
        for i, (label, nilai) in enumerate(info):
            kotak = QWidget()
            kl2 = QVBoxLayout(kotak)
            kl2.setContentsMargins(0, 0, 0, 0)
            kl2.setSpacing(2)
            lb = QLabel(label.upper())
            lb.setObjectName("KpiLabel")
            kl2.addWidget(lb)
            vl = QLabel(str(nilai))
            vl.setWordWrap(True)
            vl.setStyleSheet(f"font-size: {theme.FS_BODY}px; background: transparent;")
            kl2.addWidget(vl)
            grid.addWidget(kotak, i // 3, i % 3)
        kl.addLayout(grid)
        lay.addWidget(kartu)

        docs = O.daftar_dokumen(self.ctx.company_id, "expenses", b["id"])
        if docs:
            lay.addWidget(w.label(f"Lampiran ({len(docs)})", objek="SectionTitle"))
            t = w.Tabel([("Nama Berkas", -1), ("Tipe", 130), ("Diunggah", 165)])
            t.isi([[d["nama_berkas"], d["tipe"] or "", d["created_at"][:16]]
                   for d in docs])
            t.setMinimumHeight(130)
            lay.addWidget(t)

        aksi = QHBoxLayout()
        b_lampir = w.tombol("Lampirkan Bukti", ikon="dokumen")
        b_lampir.clicked.connect(lambda: self._lampirkan(b["id"]))
        aksi.addWidget(b_lampir)
        aksi.addStretch()
        bt = w.tombol("Tutup", gaya="primary")
        bt.clicked.connect(dlg.accept)
        aksi.addWidget(bt)
        lay.addLayout(aksi)
        dlg.exec()

    def _lampirkan(self, expense_id: int):
        path, _ = QFileDialog.getOpenFileName(
            self, "Pilih Bukti", "", "Semua Berkas (*)")
        if not path:
            return
        try:
            O.lampirkan_dokumen(self.ctx.company_id, "expenses", expense_id,
                                path, "bukti", "", self.ctx.username)
            QMessageBox.information(self, "Berhasil", "Bukti dilampirkan.")
        except Exception as e:
            QMessageBox.critical(self, "Gagal melampirkan", str(e))

    def _setujui(self, disetujui: bool):
        b = self._biaya_terpilih()
        if b is None:
            QMessageBox.information(self, "Belum dipilih", "Pilih satu catatan biaya.")
            return
        if b["status"] not in ("diajukan", "draft"):
            QMessageBox.information(
                self, "Tidak dapat diproses",
                f"Biaya berstatus '{b['status']}' tidak dapat disetujui lagi.")
            return

        if disetujui:
            d = DialogPersetujuan(self.ctx, b, self)
            if not d.exec():
                return
            catatan = d.catatan
        else:
            from PySide6.QtWidgets import QInputDialog
            catatan, ok = QInputDialog.getText(
                self, "Alasan Penolakan", "Alasan penolakan:")
            if not ok:
                return

        try:
            O.setujui_biaya(b["id"], disetujui, self.ctx.full_name or self.ctx.username,
                            catatan)
            self.muat()
        except Exception as e:
            QMessageBox.critical(self, "Gagal", str(e))

    def _bayar(self):
        b = self._biaya_terpilih()
        if b is None:
            QMessageBox.information(self, "Belum dipilih", "Pilih satu catatan biaya.")
            return
        if b["dibayar"]:
            QMessageBox.information(self, "Sudah dibayar", "Biaya ini sudah dibayar.")
            return
        if b["status"] not in ("disetujui", "reimbursement"):
            QMessageBox.warning(
                self, "Belum disetujui",
                f"Biaya berstatus '{b['status']}' belum dapat dibayar. "
                "Setujui terlebih dahulu.")
            return
        if QMessageBox.question(
                self, "Konfirmasi Pembayaran",
                f"Bayar biaya '{b['uraian']}' sebesar {tx.rupiah(b['jumlah'])}?\n\n"
                "Jurnal pembayaran akan dibuat otomatis.",
                QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return
        try:
            O.bayar_biaya(b["id"], user_id=self.ctx.user_id,
                          username=self.ctx.username)
            self.muat()
        except Exception as e:
            QMessageBox.critical(self, "Gagal membayar", str(e))

    def _hapus(self):
        b = self._biaya_terpilih()
        if b is None:
            QMessageBox.information(self, "Belum dipilih", "Pilih satu catatan biaya.")
            return
        if b["dibayar"]:
            QMessageBox.warning(
                self, "Tidak dapat dihapus",
                "Biaya yang sudah dibayar tidak dapat dihapus.")
            return
        if QMessageBox.question(
                self, "Konfirmasi Hapus",
                f"Hapus biaya '{b['uraian']}'?",
                QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            try:
                O.hapus_biaya(b["id"], self.ctx.username)
                self.muat()
            except Exception as e:
                QMessageBox.critical(self, "Gagal menghapus", str(e))


class DialogPersetujuan(QDialog):
    def __init__(self, ctx, biaya, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.setWindowTitle("Setujui Biaya")
        self.setMinimumWidth(520)
        self.catatan = ""

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 22, 24, 22)
        lay.setSpacing(13)

        j = QLabel("Persetujuan Biaya")
        j.setObjectName("SectionTitle")
        lay.addWidget(j)

        kartu = w.Card()
        kl = kartu.body()
        b = QHBoxLayout()
        b.setSpacing(26)
        b.addWidget(w.MiniStat("Uraian", biaya["uraian"]))
        b.addWidget(w.MiniStat("Jumlah", tx.rupiah(biaya["jumlah"]), C.PRIMARY))
        b.addStretch()
        kl.addLayout(b)
        lay.addWidget(kartu)

        lay.addWidget(w.label("Catatan Persetujuan", objek="FormLabel"))
        self.inp_catatan = QLineEdit()
        self.inp_catatan.setPlaceholderText("mis. Disetujui, harap lampirkan kuitansi")
        lay.addWidget(self.inp_catatan)

        aksi = QHBoxLayout()
        aksi.addStretch()
        b1 = w.tombol("Batal")
        b1.clicked.connect(self.reject)
        aksi.addWidget(b1)
        b2 = w.tombol("Setujui", gaya="success")
        b2.clicked.connect(self._simpan)
        aksi.addWidget(b2)
        lay.addLayout(aksi)

    def _simpan(self):
        self.catatan = self.inp_catatan.text().strip()
        self.accept()


class DialogKategoriBiaya(QDialog):
    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.setWindowTitle("Kategori Biaya")
        self.setMinimumSize(760, 520)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 20, 22, 20)
        lay.setSpacing(12)

        j = QLabel("Kategori Biaya")
        j.setObjectName("SectionTitle")
        lay.addWidget(j)

        lay.addWidget(w.HelpPanel(
            "Tentang kategori biaya",
            "Kategori membantu mengelompokkan biaya untuk analisis dan pelaporan.\n\n"
            "Atur 'batas nilai' dan 'perlu persetujuan' untuk mengendalikan "
            "pengeluaran: pengajuan di atas batas akan otomatis menunggu "
            "persetujuan.",
            "Pengendalian internal dan pemisahan tugas."))

        self.tabel = w.Tabel([
            ("Nama Kategori", -1), ("Akun Beban", 145), ("Batas Nilai", 165),
            ("Perlu Persetujuan", 175),
        ])
        lay.addWidget(self.tabel, 1)

        baris = QHBoxLayout()
        baris.setSpacing(9)
        b = w.tombol("Tambah Kategori", gaya="primary", ikon="+")
        b.clicked.connect(self._tambah)
        baris.addWidget(b)
        b2 = w.tombol("Hapus", gaya="danger", ikon="hapus")
        b2.clicked.connect(self._hapus)
        baris.addWidget(b2)
        baris.addStretch()
        lay.addLayout(baris)

        bt = w.tombol("Tutup")
        bt.clicked.connect(self.accept)
        bl = QHBoxLayout()
        bl.addStretch()
        bl.addWidget(bt)
        lay.addLayout(bl)

        self.muat()

    def muat(self):
        data = O.daftar_kategori_biaya(self.ctx.company_id)
        baris = []
        for k in data:
            baris.append([
                k["nama"], k["akun_beban"] or "",
                tx.rupiah(k["batas_nilai"]) if k["batas_nilai"] else "Tanpa batas",
                "Ya" if k["perlu_persetujuan"] else "Tidak",
            ])
        self.tabel.isi(baris, align_kanan={2})

    def _tambah(self):
        d = DialogKategoriBaru(self.ctx, self)
        if d.exec():
            self.muat()

    def _hapus(self):
        r = self.tabel.baris_terpilih()
        if r is None:
            QMessageBox.information(self, "Belum dipilih", "Pilih satu kategori.")
            return
        data = O.daftar_kategori_biaya(self.ctx.company_id)
        if r >= len(data):
            return
        k = data[r]
        if QMessageBox.question(
                self, "Konfirmasi Hapus",
                f"Hapus kategori '{k['nama']}'?",
                QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            M.db.ex("DELETE FROM expense_categories WHERE id=?", (k["id"],))
            self.muat()


class DialogKategoriBaru(QDialog):
    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.setWindowTitle("Tambah Kategori Biaya")
        self.setMinimumWidth(520)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 22, 24, 22)
        lay.setSpacing(13)

        g = QGridLayout()
        g.setSpacing(12)
        g.addWidget(w.label("Nama Kategori", objek="FormLabel"), 0, 0, 1, 2)
        self.inp_nama = QLineEdit()
        self.inp_nama.setPlaceholderText("mis. Operasional Kantor")
        g.addWidget(self.inp_nama, 1, 0, 1, 2)

        g.addWidget(w.label("Akun Beban", objek="FormLabel"), 2, 0)
        self.cmb_akun = w.combo_akun(ctx.company_id)
        w.set_combo_by_data(self.cmb_akun, "6023")
        g.addWidget(self.cmb_akun, 3, 0)

        g.addWidget(w.label("Batas Nilai (Rp)", objek="FormLabel"), 2, 1)
        self.inp_batas = w.InputRupiah()
        self.inp_batas.setToolTip("Kosongkan bila tidak ada batas.")
        g.addWidget(self.inp_batas, 3, 1)
        lay.addLayout(g)

        self.chk_setuju = QCheckBox("Selalu perlu persetujuan")
        lay.addWidget(self.chk_setuju)

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
                QMessageBox.warning(self, "Nama kosong", "Isi nama kategori.")
                return
            O.buat_kategori_biaya(self.ctx.company_id, self.inp_nama.text().strip(),
                                  akun_beban=self.cmb_akun.currentData() or "6023",
                                  batas_nilai=self.inp_batas.nilai(),
                                  perlu_persetujuan=self.chk_setuju.isChecked())
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Gagal menyimpan", str(e))


# ==========================================================================
# BANK & REKONSILIASI
# ==========================================================================
class DialogRekeningBaru(QDialog):
    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.setWindowTitle("Tambah Rekening Kas/Bank")
        self.setMinimumWidth(560)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 22, 24, 22)
        lay.setSpacing(13)

        j = QLabel("Rekening Kas / Bank Baru")
        j.setObjectName("SectionTitle")
        lay.addWidget(j)

        lay.addWidget(w.HelpPanel(
            "Tentang rekening kas/bank",
            "Setiap rekening terhubung ke satu akun di bagan akun. Ini "
            "memungkinkan Anda memisahkan kas tunai, beberapa rekening bank, dan "
            "dompet digital - semuanya tetap terhubung ke laporan keuangan.",
            "Pasal 28 UU KUP - pembukuan harus mencatat posisi kas secara benar."))

        g = QGridLayout()
        g.setSpacing(12)

        g.addWidget(w.label("Nama Rekening", objek="FormLabel"), 0, 0, 1, 2)
        self.inp_nama = QLineEdit()
        self.inp_nama.setPlaceholderText("mis. BCA Operasional")
        g.addWidget(self.inp_nama, 1, 0, 1, 2)

        g.addWidget(w.label("Tipe", objek="FormLabel"), 2, 0)
        self.cmb_tipe = QComboBox()
        self.cmb_tipe.addItem("Kas Tunai", "kas")
        self.cmb_tipe.addItem("Rekening Bank", "bank")
        self.cmb_tipe.addItem("Dompet Digital / E-Wallet", "ewallet")
        g.addWidget(self.cmb_tipe, 3, 0)

        g.addWidget(w.label("Nama Bank", objek="FormLabel"), 2, 1)
        self.inp_bank = QLineEdit()
        self.inp_bank.setPlaceholderText("mis. BCA")
        g.addWidget(self.inp_bank, 3, 1)

        g.addWidget(w.label("Nomor Rekening", objek="FormLabel"), 4, 0)
        self.inp_rek = QLineEdit()
        g.addWidget(self.inp_rek, 5, 0)

        g.addWidget(w.label("Atas Nama", objek="FormLabel"), 4, 1)
        self.inp_pemilik = QLineEdit()
        g.addWidget(self.inp_pemilik, 5, 1)

        g.addWidget(w.label("Saldo Awal (Rp)", objek="FormLabel"), 6, 0)
        self.inp_saldo = w.InputRupiah()
        g.addWidget(self.inp_saldo, 7, 0)

        g.addWidget(w.label("Penanggung Jawab", objek="FormLabel"), 6, 1)
        self.inp_pic = QLineEdit()
        g.addWidget(self.inp_pic, 7, 1)

        # Akun lawan menjaga neraca tetap seimbang saat saldo awal diisi.
        g.addWidget(w.label("Sumber Saldo Awal", objek="FormLabel"), 8, 0, 1, 2)
        self.cmb_lawan = QComboBox()
        self.cmb_lawan.addItem("Belum ditentukan (catat sebagai saldo akun)", "")
        for kode, nama in w.daftar_akun_neraca(ctx.company_id):
            self.cmb_lawan.addItem(f"{kode} - {nama}", kode)
        g.addWidget(self.cmb_lawan, 9, 0, 1, 2)
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
                QMessageBox.warning(self, "Nama kosong", "Isi nama rekening.")
                return
            O.buat_kas_bank(
                self.ctx.company_id, self.inp_nama.text().strip(),
                self.cmb_tipe.currentData(),
                nama_bank=self.inp_bank.text().strip(),
                nomor_rekening=self.inp_rek.text().strip(),
                pemilik=self.inp_pemilik.text().strip(),
                saldo_awal=self.inp_saldo.nilai(),
                akun_lawan=self.cmb_lawan.currentData() or "",
                penanggung_jawab=self.inp_pic.text().strip(),
                user_id=self.ctx.user_id, username=self.ctx.username)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Gagal menyimpan", str(e))


class DialogImporMutasi(QDialog):
    def __init__(self, ctx, parent=None, bank_account_id: int = None):
        super().__init__(parent)
        self.ctx = ctx
        self.setWindowTitle("Impor Mutasi Rekening Koran")
        self.setMinimumSize(780, 620)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 20, 22, 20)
        lay.setSpacing(12)

        j = QLabel("Impor Mutasi Bank")
        j.setObjectName("SectionTitle")
        lay.addWidget(j)

        lay.addWidget(w.HelpPanel(
            "Cara mengimpor mutasi",
            "Unduh mutasi rekening dari internet banking (format CSV), lalu unggah "
            "di sini. Aplikasi akan mengenali kolom secara otomatis.\n\n"
            "Kolom yang dikenali: tanggal, uraian/keterangan, referensi, "
            "debit/masuk, kredit/keluar, saldo.\n\n"
            "Mutasi yang sudah pernah diimpor akan dilewati (deteksi duplikat).",
            "Rekonsiliasi bank - praktik pengendalian internal yang penting."))

        baris = QHBoxLayout()
        baris.setSpacing(11)
        baris.addWidget(w.label("Rekening Bank", objek="FormLabel"))
        self.cmb_bank = QComboBox()
        for b in O.daftar_kas_bank(ctx.company_id):
            if b["bank_account_id"]:
                self.cmb_bank.addItem(f"{b['nama']} ({b['nomor_rekening'] or '-'})",
                                      b["bank_account_id"])
        i = self.cmb_bank.findData(bank_account_id)
        if i >= 0:
            self.cmb_bank.setCurrentIndex(i)
        baris.addWidget(self.cmb_bank, 1)
        lay.addLayout(baris)

        baris2 = QHBoxLayout()
        baris2.setSpacing(9)
        b1 = w.tombol("Pilih Berkas CSV", gaya="primary", ikon="dokumen")
        b1.clicked.connect(self._pilih_berkas)
        baris2.addWidget(b1)

        b2 = w.tombol("Tempel Teks CSV", ikon="audit")
        b2.clicked.connect(self._mode_teks)
        baris2.addWidget(b2)
        baris2.addStretch()
        lay.addLayout(baris2)

        self.lbl_berkas = QLabel("Belum ada berkas dipilih.")
        self.lbl_berkas.setObjectName("Muted")
        lay.addWidget(self.lbl_berkas)

        self.teks = QTextEdit()
        self.teks.setPlaceholderText(
            "Tempelkan isi CSV di sini, atau pilih berkas di atas.\n"
            "Contoh:\n"
            "tanggal;uraian;referensi;debit;kredit;saldo\n"
            "2026-01-05;Transfer masuk;TRF001;5000000;0;5000000")
        self.teks.setMinimumHeight(260)
        lay.addWidget(self.teks, 1)

        self.lbl_hasil = QLabel("")
        self.lbl_hasil.setWordWrap(True)
        lay.addWidget(self.lbl_hasil)

        aksi = QHBoxLayout()
        aksi.addStretch()
        b = w.tombol("Batal")
        b.clicked.connect(self.reject)
        aksi.addWidget(b)
        bs = w.tombol("Impor Sekarang", gaya="primary")
        bs.clicked.connect(self._impor)
        aksi.addWidget(bs)
        lay.addLayout(aksi)

    def _pilih_berkas(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Pilih Berkas Mutasi", str(config.EXPORT_DIR),
            "Berkas CSV/Teks (*.csv *.txt);;Semua Berkas (*)")
        if not path:
            return
        try:
            with open(path, encoding="utf-8-sig", errors="replace") as f:
                isi = f.read()
            self.teks.setPlainText(isi)
            self.lbl_berkas.setText(f"Berkas dipilih: {os.path.basename(path)}")
        except Exception as e:
            QMessageBox.critical(self, "Gagal membaca berkas", str(e))

    def _mode_teks(self):
        self.teks.setFocus()
        self.lbl_berkas.setText("Mode tempel teks - salin isi CSV ke kotak di bawah.")

    def _impor(self):
        bank_id = self.cmb_bank.currentData()
        if not bank_id:
            QMessageBox.warning(self, "Rekening belum dipilih",
                                "Pilih rekening bank tujuan impor.")
            return
        isi = self.teks.toPlainText().strip()
        if not isi:
            QMessageBox.warning(self, "Belum ada data",
                                "Pilih berkas CSV atau tempelkan isinya.")
            return
        try:
            hasil = O.impor_mutasi_dari_csv(self.ctx.company_id, bank_id, isi,
                                            self.ctx.user_id)
            pesan = (f"<b>Impor selesai</b><br><br>"
                     f"Berhasil diimpor: <b>{hasil['berhasil']}</b> baris<br>"
                     f"Duplikat dilewati: <b>{hasil['duplikat']}</b> baris<br>"
                     f"Total baris diperiksa: {hasil['total']}")
            self.lbl_hasil.setText(pesan)
            self.lbl_hasil.setTextFormat(Qt.RichText)
            theme.latar(self.lbl_hasil, f"background: {C.SUCCESS_BG}; border: 1px solid #B8E6D5; "
                f"border-radius: 8px; padding: 11px 13px; font-size: {theme.FS_SMALL}px;")
            if hasil["berhasil"] > 0:
                QMessageBox.information(
                    self, "Impor berhasil",
                    f"{hasil['berhasil']} mutasi diimpor.\n"
                    f"{hasil['duplikat']} duplikat dilewati.\n\n"
                    "Lanjutkan ke rekonsiliasi untuk mencocokkan dengan jurnal.")
                self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Gagal mengimpor", str(e))


class DialogRekonsiliasi(QDialog):
    def __init__(self, ctx, parent=None, bank_account_id: int = None):
        super().__init__(parent)
        self.ctx = ctx
        self.setWindowTitle("Rekonsiliasi Bank")
        self.setMinimumSize(900, 560)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 20, 22, 20)
        lay.setSpacing(12)

        j = QLabel("Rekonsiliasi Bank")
        j.setObjectName("SectionTitle")
        lay.addWidget(j)

        lay.addWidget(w.HelpPanel(
            "Tentang rekonsiliasi bank",
            "Rekonsiliasi membandingkan saldo menurut rekening koran dengan saldo "
            "menurut pembukuan Anda. Selisih bisa muncul karena:\n\n"
            "• Biaya administrasi bank yang belum dicatat\n"
            "• Bunga bank yang belum dicatat\n"
            "• Transfer yang belum masuk (in transit)\n"
            "• Cek yang belum dicairkan\n\n"
            "Selisih harus ditelusuri hingga nol agar pembukuan akurat.",
            "Praktik pengendalian internal - Pasal 28 UU KUP."))

        baris = QHBoxLayout()
        baris.setSpacing(11)
        baris.addWidget(w.label("Rekening", objek="FormLabel"))
        self.cmb_bank = QComboBox()
        for b in O.daftar_kas_bank(ctx.company_id):
            if b["bank_account_id"]:
                self.cmb_bank.addItem(b["nama"], b["bank_account_id"])
        i = self.cmb_bank.findData(bank_account_id)
        if i >= 0:
            self.cmb_bank.setCurrentIndex(i)
        baris.addWidget(self.cmb_bank)

        baris.addWidget(w.label("Periode", objek="FormLabel"))
        self.cmb_periode = QComboBox()
        tahun = datetime.now().year
        for t in (tahun - 1, tahun, tahun + 1):
            for m in range(1, 13):
                self.cmb_periode.addItem(f"{t}-{m:02d}", f"{t}-{m:02d}")
        i = self.cmb_periode.findData(datetime.now().strftime("%Y-%m"))
        if i >= 0:
            self.cmb_periode.setCurrentIndex(i)
        baris.addWidget(self.cmb_periode)

        baris.addWidget(w.label("Saldo Menurut Bank (Rp)", objek="FormLabel"))
        self.inp_saldo_bank = w.InputRupiah()
        self.inp_saldo_bank.valueChanged.connect(self._hitung)
        baris.addWidget(self.inp_saldo_bank, 1)
        lay.addLayout(baris)

        self.panel = QFrame()
        theme.latar(self.panel, f"background: {C.NEUTRAL_BG}; border-radius: 8px;")
        pl = QHBoxLayout(self.panel)
        pl.setContentsMargins(18, 14, 18, 14)
        pl.setSpacing(32)
        self.lbl_bank = QLabel("Saldo Bank: Rp0")
        self.lbl_buku = QLabel("Saldo Buku: Rp0")
        self.lbl_selisih = QLabel("Selisih: Rp0")
        for x in (self.lbl_bank, self.lbl_buku, self.lbl_selisih):
            x.setStyleSheet(f"font-family: {theme.FONT_ANGKA}; font-size: 15px; "
                            "font-weight: 700; background: transparent;")
            pl.addWidget(x)
        pl.addStretch()
        lay.addWidget(self.panel)

        lay.addWidget(w.label("Mutasi Belum Dicocokkan", objek="SectionTitle"))
        self.tabel = w.Tabel([
            ("Tanggal", 110), ("Uraian", -1), ("Referensi", 145),
            ("Masuk", 140), ("Keluar", 140), ("Status", 120),
        ])
        lay.addWidget(self.tabel, 1)

        aksi = QHBoxLayout()
        aksi.setSpacing(9)
        b1 = w.tombol("Buat Jurnal dari Mutasi", gaya="primary", ikon="+")
        b1.clicked.connect(self._jurnal_dari_mutasi)
        aksi.addWidget(b1)
        b2 = w.tombol("Tandai Dikecualikan", ikon="⊘")
        b2.clicked.connect(self._kecualikan)
        aksi.addWidget(b2)
        aksi.addStretch()
        b3 = w.tombol("Simpan Rekonsiliasi", gaya="success", ikon="simpan")
        b3.clicked.connect(self._simpan)
        aksi.addWidget(b3)
        lay.addLayout(aksi)

        self.cmb_bank.currentIndexChanged.connect(self._muat)
        self.cmb_periode.currentIndexChanged.connect(self._muat)
        self._muat()

    def _muat(self):
        bank_id = self.cmb_bank.currentData()
        if not bank_id:
            return
        periode = self.cmb_periode.currentData()

        bank = M.db.q1("SELECT * FROM bank_accounts WHERE id=?", (bank_id,))
        akun = M.db.q1("SELECT saldo_awal FROM accounts WHERE company_id=? AND kode=?",
                       (self.ctx.company_id, bank["akun_buku"])) if bank else None
        saldo_awal = int(akun["saldo_awal"]) if akun else 0
        mutasi_jurnal = int(M.db.scalar(
            """SELECT COALESCE(SUM(jl.debit - jl.kredit),0) FROM journal_lines jl
               JOIN journal_entries je ON je.id = jl.entry_id
               WHERE jl.company_id=? AND jl.kode_akun=? AND substr(je.tanggal,1,7)=?""",
            (self.ctx.company_id, bank["akun_buku"] if bank else "", periode)))
        saldo_buku = saldo_awal + mutasi_jurnal

        self.lbl_buku.setText(f"Saldo Buku: {tx.rupiah(saldo_buku)}")
        self._hitung()

        data = O.daftar_mutasi_bank(self.ctx.company_id, bank_id, periode=periode)
        baris, warna = [], {}
        for i, r in enumerate(data):
            idx = len(baris)
            baris.append([
                theme.tanggal_id(r["tanggal"]), r["uraian"], r["referensi"],
                tx.rupiah(r["debit"]) if r["debit"] else "",
                tx.rupiah(r["kredit"]) if r["kredit"] else "",
                istilah.label("status", r["status"]),
            ])
            if r["status"] == "belum":
                warna[idx] = C.WARNING
            elif r["status"] == "tercocok":
                warna[idx] = C.SUCCESS
            else:
                warna[idx] = C.TEXT_FAINT
        self.tabel.isi(baris, warna_baris=warna, align_kanan={3, 4})

    def _hitung(self):
        bank_id = self.cmb_bank.currentData()
        if not bank_id:
            return
        periode = self.cmb_periode.currentData()
        bank = M.db.q1("SELECT * FROM bank_accounts WHERE id=?", (bank_id,))
        akun = M.db.q1("SELECT saldo_awal FROM accounts WHERE company_id=? AND kode=?",
                       (self.ctx.company_id, bank["akun_buku"])) if bank else None
        saldo_awal = int(akun["saldo_awal"]) if akun else 0
        mutasi = int(M.db.scalar(
            """SELECT COALESCE(SUM(jl.debit - jl.kredit),0) FROM journal_lines jl
               JOIN journal_entries je ON je.id = jl.entry_id
               WHERE jl.company_id=? AND jl.kode_akun=? AND substr(je.tanggal,1,7)=?""",
            (self.ctx.company_id, bank["akun_buku"] if bank else "", periode)))
        saldo_buku = saldo_awal + mutasi
        bank_saldo = self.inp_saldo_bank.nilai()
        selisih = bank_saldo - saldo_buku

        self.lbl_bank.setText(f"Saldo Bank: {tx.rupiah(bank_saldo)}")
        self.lbl_buku.setText(f"Saldo Buku: {tx.rupiah(saldo_buku)}")
        self.lbl_selisih.setText(f"Selisih: {tx.rupiah(selisih)}")
        warna = C.SUCCESS if selisih == 0 else C.DANGER
        self.lbl_selisih.setStyleSheet(
            f"font-family: {theme.FONT_ANGKA}; font-size: 15px; font-weight: 700; "
            f"color: {warna}; background: transparent;")
        theme.latar(self.panel, f"background: {C.SUCCESS_BG if selisih == 0 else C.DANGER_BG}; "
            f"border: 1px solid {'#B8E6D5' if selisih == 0 else '#F5C2C2'}; "
            "border-radius: 8px;")

    def _mutasi_terpilih(self):
        r = self.tabel.baris_terpilih()
        if r is None:
            return None
        data = O.daftar_mutasi_bank(self.ctx.company_id,
                                    self.cmb_bank.currentData(),
                                    periode=self.cmb_periode.currentData())
        return data[r] if r < len(data) else None

    def _jurnal_dari_mutasi(self):
        trx = self._mutasi_terpilih()
        if trx is None:
            QMessageBox.information(self, "Belum dipilih", "Pilih satu mutasi.")
            return
        if trx["status"] == "tercocok":
            QMessageBox.information(self, "Sudah tercocok",
                                    "Mutasi ini sudah dicocokkan dengan jurnal.")
            return

        d = DialogPilihAkunLawan(self.ctx, trx, self)
        if not d.exec():
            return
        try:
            O.jurnal_dari_mutasi(self.ctx.company_id, trx["id"],
                                 d.akun_terpilih, self.ctx.user_id)
            self._muat()
        except Exception as e:
            QMessageBox.critical(self, "Gagal membuat jurnal", str(e))

    def _kecualikan(self):
        trx = self._mutasi_terpilih()
        if trx is None:
            QMessageBox.information(self, "Belum dipilih", "Pilih satu mutasi.")
            return
        if QMessageBox.question(
                self, "Tandai Dikecualikan",
                "Tandai mutasi ini sebagai dikecualikan (tidak perlu dicocokkan)?",
                QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            try:
                O.cocokkan_mutasi(trx["id"], None, self.ctx.user_id)
                self._muat()
            except Exception as e:
                QMessageBox.critical(self, "Gagal", str(e))

    def _simpan(self):
        try:
            bank_id = self.cmb_bank.currentData()
            if not bank_id:
                return
            rec_id = O.buat_rekonsiliasi(
                self.ctx.company_id, bank_id, self.cmb_periode.currentData(),
                self.inp_saldo_bank.nilai(),
                self.ctx.full_name or self.ctx.username)

            bank = M.db.q1("SELECT * FROM bank_accounts WHERE id=?", (bank_id,))
            akun = M.db.q1("SELECT saldo_awal FROM accounts WHERE company_id=? AND kode=?",
                           (self.ctx.company_id, bank["akun_buku"]))
            saldo_awal = int(akun["saldo_awal"]) if akun else 0
            mutasi = int(M.db.scalar(
                """SELECT COALESCE(SUM(jl.debit - jl.kredit),0) FROM journal_lines jl
                   JOIN journal_entries je ON je.id = jl.entry_id
                   WHERE jl.company_id=? AND jl.kode_akun=? AND substr(je.tanggal,1,7)=?""",
                (self.ctx.company_id, bank["akun_buku"], self.cmb_periode.currentData())))
            selisih = self.inp_saldo_bank.nilai() - (saldo_awal + mutasi)

            if selisih == 0:
                O.selesaikan_rekonsiliasi(rec_id, "Selisih nol", self.ctx.user_id)
                QMessageBox.information(
                    self, "Rekonsiliasi selesai",
                    "Saldo bank dan saldo buku sudah cocok. Rekonsiliasi ditandai "
                    "selesai.")
            else:
                QMessageBox.information(
                    self, "Rekonsiliasi disimpan",
                    f"Rekonsiliasi disimpan dengan selisih {tx.rupiah(selisih)}.\n\n"
                    "Telusuri penyebab selisih: biaya bank, bunga, transfer "
                    "in transit, atau cek belum dicairkan.")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Gagal menyimpan", str(e))


class DialogPilihAkunLawan(QDialog):
    def __init__(self, ctx, transaksi, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.transaksi = transaksi
        self.akun_terpilih = ""
        self.setWindowTitle("Pilih Akun Lawan")
        self.setMinimumWidth(560)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 22, 24, 22)
        lay.setSpacing(13)

        j = QLabel("Akun Lawan untuk Mutasi Bank")
        j.setObjectName("SectionTitle")
        lay.addWidget(j)

        masuk = int(transaksi["debit"] or 0)
        keluar = int(transaksi["kredit"] or 0)
        arah = "UANG MASUK" if masuk > 0 else "UANG KELUAR"
        nilai = masuk or keluar

        kartu = w.Card()
        kl = kartu.body()
        b = QHBoxLayout()
        b.setSpacing(26)
        b.addWidget(w.MiniStat("Arah", arah,
                               C.SUCCESS if masuk else C.DANGER))
        b.addWidget(w.MiniStat("Jumlah", tx.rupiah(nilai)))
        b.addWidget(w.MiniStat("Uraian", transaksi["uraian"] or ""))
        b.addStretch()
        kl.addLayout(b)
        lay.addWidget(kartu)

        saran = ("Pendapatan / Piutang (uang masuk)" if masuk
                 else "Beban / Utang (uang keluar)")
        lay.addWidget(w.HelpPanel(
            "Memilih akun lawan",
            f"Mutasi ini adalah {arah.lower()} sebesar {tx.rupiah(nilai)}. "
            f"Pilih akun yang menjadi lawan transaksi.\n\n"
            f"Contoh untuk kasus ini: {saran}.\n\n"
            "Setelah jurnal dibuat, mutasi akan ditandai tercocok.",
            "Pasal 28 UU KUP - setiap transaksi harus memiliki bukti dan penjelasan."))

        lay.addWidget(w.label("Akun Lawan", objek="FormLabel"))
        self.cmb_akun = w.combo_akun(ctx.company_id)
        lay.addWidget(self.cmb_akun)

        aksi = QHBoxLayout()
        aksi.addStretch()
        b1 = w.tombol("Batal")
        b1.clicked.connect(self.reject)
        aksi.addWidget(b1)
        b2 = w.tombol("Buat Jurnal", gaya="primary")
        b2.clicked.connect(self._simpan)
        aksi.addWidget(b2)
        lay.addLayout(aksi)

    def _simpan(self):
        self.akun_terpilih = self.cmb_akun.currentData() or ""
        if not self.akun_terpilih:
            QMessageBox.warning(self, "Akun belum dipilih", "Pilih akun lawan.")
            return
        self.accept()


class BankPage(QWidget):
    pindah_halaman = Signal(str)

    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx

        luar = QVBoxLayout(self)
        luar.setContentsMargins(0, 0, 0, 0)
        luar.setSpacing(0)

        self.header = w.PageHeader(
            "Kas & Bank",
            "Kelola rekening kas, bank, dan dompet digital; impor mutasi rekening "
            "koran dan lakukan rekonsiliasi.")

        b1 = w.tombol("Rekening Baru", gaya="primary", ikon="+")
        b1.clicked.connect(self._rekening_baru)
        self.header.tambah_aksi(b1)

        b2 = w.tombol("Impor Mutasi", ikon="impor")
        b2.clicked.connect(self._impor_mutasi)
        self.header.tambah_aksi(b2)

        b3 = w.tombol("Rekonsiliasi", ikon="")
        b3.clicked.connect(self._rekonsiliasi)
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

        self.kpi_area = QWidget()
        self.kpi_lay = QHBoxLayout(self.kpi_area)
        self.kpi_lay.setContentsMargins(0, 0, 0, 0)
        self.kpi_lay.setSpacing(14)
        self.lay.addWidget(self.kpi_area)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tab_rekening = QWidget()
        self.tab_mutasi = QWidget()
        self.tab_rekonsiliasi = QWidget()
        self.tabs.addTab(self.tab_rekening, "Rekening")
        self.tabs.addTab(self.tab_mutasi, "Mutasi Bank")
        self.tabs.addTab(self.tab_rekonsiliasi, "Riwayat Rekonsiliasi")
        self.tabs.currentChanged.connect(self.muat)
        self.lay.addWidget(self.tabs, 1)

        self._bangun_rekening()
        self._bangun_mutasi()
        self._bangun_rekonsiliasi()

    def _bangun_rekening(self):
        lay = QVBoxLayout(self.tab_rekening)
        lay.setContentsMargins(0, 12, 0, 0)
        lay.setSpacing(12)

        self.tabel_rek = w.Tabel([
            ("Kode", 105), ("Nama Rekening", -1), ("Tipe", 110),
            ("Bank", 130), ("No. Rekening", 155), ("Akun Buku", 105),
            ("Saldo Buku", 175),
        ])
        lay.addWidget(self.tabel_rek, 1)

        baris = QHBoxLayout()
        baris.setSpacing(9)
        b1 = w.tombol("Transfer Antar Rekening", ikon="transfer")
        b1.clicked.connect(self._transfer)
        baris.addWidget(b1)
        b2 = w.tombol("Buat Penyesuaian Saldo", ikon="pengaturan")
        b2.clicked.connect(self._penyesuaian)
        baris.addWidget(b2)
        baris.addStretch()
        lay.addLayout(baris)

    def _bangun_mutasi(self):
        lay = QVBoxLayout(self.tab_mutasi)
        lay.setContentsMargins(0, 12, 0, 0)
        lay.setSpacing(12)

        baris = QHBoxLayout()
        baris.setSpacing(10)
        baris.addWidget(w.label("Rekening:", objek="FormLabel"))
        self.cmb_bank_mutasi = QComboBox()
        self.cmb_bank_mutasi.currentIndexChanged.connect(self.muat)
        baris.addWidget(self.cmb_bank_mutasi)

        self.cmb_status_mutasi = QComboBox()
        self.cmb_status_mutasi.addItem("Semua Status", "")
        self.cmb_status_mutasi.addItem("Belum Dicocokkan", "belum")
        self.cmb_status_mutasi.addItem("Tercocok", "tercocok")
        self.cmb_status_mutasi.addItem("Dikecualikan", "dikecualikan")
        self.cmb_status_mutasi.currentIndexChanged.connect(self.muat)
        baris.addWidget(self.cmb_status_mutasi)
        baris.addStretch()
        self.lbl_mutasi = QLabel("")
        self.lbl_mutasi.setObjectName("Muted")
        baris.addWidget(self.lbl_mutasi)
        lay.addLayout(baris)

        self.tabel_mutasi = w.Tabel([
            ("Tanggal", 110), ("Uraian", -1), ("Referensi", 155),
            ("Masuk", 145), ("Keluar", 145), ("Status", 145),
        ])
        lay.addWidget(self.tabel_mutasi, 1)

        baris2 = QHBoxLayout()
        b1 = w.tombol("Buat Jurnal", gaya="primary", ikon="+")
        b1.clicked.connect(self._jurnal_mutasi)
        baris2.addWidget(b1)
        b2 = w.tombol("Dikecualikan", ikon="⊘")
        b2.clicked.connect(self._kecualikan_mutasi)
        baris2.addWidget(b2)
        baris2.addStretch()
        lay.addLayout(baris2)

    def _bangun_rekonsiliasi(self):
        lay = QVBoxLayout(self.tab_rekonsiliasi)
        lay.setContentsMargins(0, 12, 0, 0)
        lay.setSpacing(12)

        self.tabel_rekons = w.Tabel([
            ("Periode", 115), ("Rekening", -1), ("Saldo Bank", 175),
            ("Saldo Buku", 175), ("Selisih", 165), ("Status", 120),
            ("Dibuat Oleh", 145),
        ])
        lay.addWidget(self.tabel_rekons, 1)

        baris = QHBoxLayout()
        b = w.tombol("Selesaikan Rekonsiliasi", gaya="success", ikon="simpan")
        b.clicked.connect(self._selesaikan)
        baris.addWidget(b)
        baris.addStretch()
        lay.addLayout(baris)

    def muat(self):
        cid = self.ctx.company_id
        if not cid:
            return

        while self.kpi_lay.count():
            it = self.kpi_lay.takeAt(0)
            wdg = it.widget()
            if wdg is not None:
                wdg.setParent(None)
                wdg.deleteLater()

        saldo = O.saldo_kas_bank(cid)
        self.kpi_lay.addWidget(w.KpiTile("Total Kas & Bank", tx.rupiah(saldo["total"]),
                                         "Seluruh rekening aktif", C.PRIMARY, "bank"))
        self.kpi_lay.addWidget(w.KpiTile("Kas Tunai", tx.rupiah(saldo["kas"]),
                                         "Uang tunai di tangan", C.TEXT, "uang"))
        self.kpi_lay.addWidget(w.KpiTile("Rekening Bank", tx.rupiah(saldo["bank"]),
                                         "Saldo seluruh rekening bank", C.TEXT, "bank"))
        self.kpi_lay.addWidget(w.KpiTile("Dompet Digital", tx.rupiah(saldo["ewallet"]),
                                         "E-wallet dan QRIS", C.TEXT, "bank"))

        belum = O.mutasi_belum_cocok(cid)
        if belum:
            total = sum(int(b["debit"] or 0) + int(b["kredit"] or 0) for b in belum)
            self.kpi_lay.addWidget(w.KpiTile(
                "Belum Dicocokkan", str(len(belum)),
                f"Total {tx.rupiah(total)}", C.WARNING, "peringatan"))

        idx = self.tabs.currentIndex()
        if idx == 0:
            self._muat_rekening()
        elif idx == 1:
            self._muat_mutasi()
        else:
            self._muat_rekonsiliasi()

    def _muat_rekening(self):
        data = O.daftar_kas_bank(self.ctx.company_id)
        baris = []
        for k in data:
            baris.append([
                k["kode"], k["nama"],
                istilah.label("tipe", k["tipe"]),
                k["nama_bank"] or "", k["nomor_rekening"] or "",
                k["akun_buku"], tx.rupiah(k["saldo_buku"] or 0),
            ])
        self.tabel_rek.isi(baris, align_kanan={6})

    def _muat_mutasi(self):
        cid = self.ctx.company_id
        self._refresh_bank_combo()
        bank_id = self.cmb_bank_mutasi.currentData()
        data = O.daftar_mutasi_bank(cid, bank_id, self.cmb_status_mutasi.currentData())
        baris, warna = [], {}
        total_masuk = total_keluar = 0
        for i, r in enumerate(data):
            idx = len(baris)
            total_masuk += int(r["debit"] or 0)
            total_keluar += int(r["kredit"] or 0)
            baris.append([
                theme.tanggal_id(r["tanggal"]), r["uraian"], r["referensi"],
                tx.rupiah(r["debit"]) if r["debit"] else "",
                tx.rupiah(r["kredit"]) if r["kredit"] else "",
                {"belum": "Belum dicocokkan", "tercocok": "Tercocok",
                 "dikecualikan": "Dikecualikan"}.get(r["status"], r["status"]),
            ])
            warna[idx] = {"belum": C.WARNING, "tercocok": C.SUCCESS,
                          "dikecualikan": C.TEXT_FAINT}.get(r["status"], C.TEXT)
        self.tabel_mutasi.isi(baris, warna_baris=warna, align_kanan={3, 4})
        self.lbl_mutasi.setText(
            f"{len(data)} mutasi · masuk {tx.rupiah(total_masuk)} · "
            f"keluar {tx.rupiah(total_keluar)}")

    def _refresh_bank_combo(self):
        combo = self.cmb_bank_mutasi
        data_lama = combo.currentData()
        combo.blockSignals(True)
        combo.clear()
        combo.addItem("Semua Rekening", None)
        for b in O.daftar_kas_bank(self.ctx.company_id):
            if b["bank_account_id"]:
                combo.addItem(b["nama"], b["bank_account_id"])
        i = combo.findData(data_lama)
        combo.setCurrentIndex(i if i >= 0 else 0)
        combo.blockSignals(False)

    def _muat_rekonsiliasi(self):
        data = O.daftar_rekonsiliasi(self.ctx.company_id)
        baris, warna = [], {}
        for i, r in enumerate(data):
            idx = len(baris)
            baris.append([
                r["periode"], r["nama_rekening"],
                tx.rupiah(r["saldo_bank"]), tx.rupiah(r["saldo_buku"]),
                tx.rupiah(r["selisih"]),
                "Selesai" if r["status"] == "selesai" else "Dalam Proses",
                r["dibuat_oleh"] or "",
            ])
            if r["selisih"] == 0:
                warna[idx] = C.SUCCESS
            else:
                warna[idx] = C.WARNING
        self.tabel_rekons.isi(baris, warna_baris=warna, align_kanan={2, 3, 4})

    def _rekening_baru(self):
        if not self.ctx.company_id:
            QMessageBox.information(self, "Belum ada perusahaan",
                                    "Buat profil perusahaan terlebih dahulu.")
            return
        d = DialogRekeningBaru(self.ctx, self)
        if d.exec():
            self.muat()

    def _impor_mutasi(self):
        bank_id = self.cmb_bank_mutasi.currentData() if hasattr(
            self, "cmb_bank_mutasi") else None
        d = DialogImporMutasi(self.ctx, self, bank_id)
        if d.exec():
            self.tabs.setCurrentIndex(1)
            self.muat()

    def _rekonsiliasi(self):
        bank_id = self.cmb_bank_mutasi.currentData() if hasattr(
            self, "cmb_bank_mutasi") else None
        d = DialogRekonsiliasi(self.ctx, self, bank_id)
        if d.exec():
            self.muat()

    def _transfer(self):
        d = DialogTransferKas(self.ctx, self)
        if d.exec():
            self.muat()

    def _penyesuaian(self):
        QMessageBox.information(
            self, "Penyesuaian Saldo",
            "Untuk menyesuaikan saldo rekening, buat jurnal manual di menu "
            "Jurnal Umum:\n\n"
            "• Saldo bertambah -> DEBIT akun kas/bank, KREDIT akun lawan\n"
            "• Saldo berkurang -> DEBIT akun lawan, KREDIT akun kas/bank\n\n"
            "Cantumkan keterangan dan bukti pendukung yang jelas.")

    def _mutasi_terpilih(self):
        r = self.tabel_mutasi.baris_terpilih()
        if r is None:
            return None
        data = O.daftar_mutasi_bank(self.ctx.company_id,
                                    self.cmb_bank_mutasi.currentData(),
                                    self.cmb_status_mutasi.currentData())
        return data[r] if r < len(data) else None

    def _jurnal_mutasi(self):
        trx = self._mutasi_terpilih()
        if trx is None:
            QMessageBox.information(self, "Belum dipilih", "Pilih satu mutasi.")
            return
        if trx["status"] == "tercocok":
            QMessageBox.information(self, "Sudah tercocok",
                                    "Mutasi ini sudah dicocokkan.")
            return
        d = DialogPilihAkunLawan(self.ctx, trx, self)
        if not d.exec():
            return
        try:
            O.jurnal_dari_mutasi(self.ctx.company_id, trx["id"],
                                 d.akun_terpilih, self.ctx.user_id)
            self.muat()
        except Exception as e:
            QMessageBox.critical(self, "Gagal", str(e))

    def _kecualikan_mutasi(self):
        trx = self._mutasi_terpilih()
        if trx is None:
            QMessageBox.information(self, "Belum dipilih", "Pilih satu mutasi.")
            return
        try:
            O.cocokkan_mutasi(trx["id"], None, self.ctx.user_id)
            self.muat()
        except Exception as e:
            QMessageBox.critical(self, "Gagal", str(e))

    def _selesaikan(self):
        r = self.tabel_rekons.aris_terpilih() if hasattr(
            self.tabel_rekons, "aris_terpilih") else self.tabel_rekons.baris_terpilih()
        if r is None:
            QMessageBox.information(self, "Belum dipilih",
                                    "Pilih satu rekonsiliasi.")
            return
        data = O.daftar_rekonsiliasi(self.ctx.company_id)
        if r >= len(data):
            return
        rec = data[r]
        if rec["selisih"] != 0:
            if QMessageBox.question(
                    self, "Selisih belum nol",
                    f"Rekonsiliasi ini masih memiliki selisih "
                    f"{tx.rupiah(rec['selisih'])}.\n\nTetap tandai selesai?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No) != QMessageBox.Yes:
                return
        try:
            O.selesaikan_rekonsiliasi(rec["id"], "Ditandai selesai",
                                      self.ctx.user_id)
            self.muat()
        except Exception as e:
            QMessageBox.critical(self, "Gagal", str(e))


class DialogTransferKas(QDialog):
    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.setWindowTitle("Transfer Antar Rekening")
        self.setMinimumWidth(560)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 22, 24, 22)
        lay.setSpacing(13)

        j = QLabel("Transfer Antar Rekening")
        j.setObjectName("SectionTitle")
        lay.addWidget(j)

        g = QGridLayout()
        g.setSpacing(12)

        g.addWidget(w.label("Dari Rekening", objek="FormLabel"), 0, 0)
        self.cmb_dari = QComboBox()
        for kb in O.daftar_kas_bank(ctx.company_id):
            self.cmb_dari.addItem(f"{kb['nama']} ({tx.rupiah(kb['saldo_buku'] or 0)})",
                                  kb["akun_buku"])
        g.addWidget(self.cmb_dari, 1, 0)

        g.addWidget(w.label("Ke Rekening", objek="FormLabel"), 0, 1)
        self.cmb_ke = QComboBox()
        for kb in O.daftar_kas_bank(ctx.company_id):
            self.cmb_ke.addItem(f"{kb['nama']}", kb["akun_buku"])
        if self.cmb_ke.count() > 1:
            self.cmb_ke.setCurrentIndex(1)
        g.addWidget(self.cmb_ke, 1, 1)

        g.addWidget(w.label("Tanggal", objek="FormLabel"), 2, 0)
        self.inp_tanggal = kalender.pasang(QDateEdit())
        self.inp_tanggal.setDisplayFormat("dd/MM/yyyy")
        self.inp_tanggal.setDate(QDate.currentDate())
        g.addWidget(self.inp_tanggal, 3, 0)

        g.addWidget(w.label("Jumlah (Rp)", objek="FormLabel"), 2, 1)
        self.inp_jumlah = w.InputRupiah()
        g.addWidget(self.inp_jumlah, 3, 1)

        g.addWidget(w.label("Biaya Transfer (Rp)", objek="FormLabel"), 4, 0)
        self.inp_biaya = w.InputRupiah()
        g.addWidget(self.inp_biaya, 5, 0)

        g.addWidget(w.label("Keterangan", objek="FormLabel"), 4, 1)
        self.inp_ket = QLineEdit()
        g.addWidget(self.inp_ket, 5, 1)
        lay.addLayout(g)

        aksi = QHBoxLayout()
        aksi.addStretch()
        b = w.tombol("Batal")
        b.clicked.connect(self.reject)
        aksi.addWidget(b)
        bs = w.tombol("Transfer", gaya="primary")
        bs.clicked.connect(self._simpan)
        aksi.addWidget(bs)
        lay.addLayout(aksi)

    def _simpan(self):
        try:
            if self.cmb_dari.currentData() == self.cmb_ke.currentData():
                QMessageBox.warning(self, "Rekening sama",
                                    "Rekening asal dan tujuan harus berbeda.")
                return
            if self.inp_jumlah.nilai() <= 0:
                QMessageBox.warning(self, "Jumlah kosong", "Isi jumlah transfer.")
                return
            O.transfer_kas_bank(
                self.ctx.company_id,
                self.inp_tanggal.date().toString("yyyy-MM-dd"),
                self.cmb_dari.currentData(), self.cmb_ke.currentData(),
                self.inp_jumlah.nilai(), self.inp_ket.text().strip(),
                self.inp_biaya.nilai(), self.ctx.user_id)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Gagal transfer", str(e))
