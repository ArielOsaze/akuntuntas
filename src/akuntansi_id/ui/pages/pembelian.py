"""
Halaman pembelian: Purchase Order, Bill, Pembayaran Vendor, Retur,
dan Aging Utang.
"""
from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt, Signal, QDate
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit, QDateEdit,
    QDialog, QMessageBox, QGridLayout, QCheckBox, QTabWidget, QTableWidgetItem,
)

from ... import config, modules as M, modules_sales as S, modules_ops as O
from ...core import tax_engine as tx
from ... import istilah
from .. import theme, widgets as w
from .. import kalender
from ..theme import C
from .penjualan import PanelItem


class DialogPurchaseOrder(QDialog):
    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.setWindowTitle("Buat Purchase Order")
        self.setMinimumSize(1060, 660)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 20, 22, 20)
        lay.setSpacing(12)

        j = QLabel("Purchase Order Baru")
        j.setObjectName("SectionTitle")
        lay.addWidget(j)

        if ctx.beginner:
            lay.addWidget(w.HelpPanel(
                "Tentang Purchase Order",
                "Purchase Order adalah pesanan pembelian ke pemasok. Setelah barang "
                "diterima dan tagihan datang, Anda mengubahnya menjadi Bill.\n\n"
                "Alur: Purchase Order -> Bill -> Pembayaran ke Vendor.",
                "PO bukan transaksi akuntansi. Utang diakui saat bill diterima."))

        baris = QHBoxLayout()
        baris.setSpacing(11)
        baris.addWidget(w.label("Tanggal", objek="FormLabel"))
        self.inp_tanggal = kalender.pasang(QDateEdit())
        self.inp_tanggal.setDisplayFormat("dd/MM/yyyy")
        self.inp_tanggal.setDate(QDate.currentDate())
        baris.addWidget(self.inp_tanggal)

        baris.addWidget(w.label("Pemasok", objek="FormLabel"))
        self.cmb_vendor = QComboBox()
        self.cmb_vendor.setMinimumWidth(260)
        self.cmb_vendor.addItem("Pemasok Umum", None)
        for m in M.daftar_mitra(ctx.company_id, "vendor"):
            self.cmb_vendor.addItem(m["nama"], m["id"])
        baris.addWidget(self.cmb_vendor)

        baris.addWidget(w.label("Tgl Terima", objek="FormLabel"))
        self.inp_terima = kalender.pasang(QDateEdit())
        self.inp_terima.setDisplayFormat("dd/MM/yyyy")
        self.inp_terima.setDate(QDate.currentDate().addDays(7))
        baris.addWidget(self.inp_terima, 1)
        lay.addLayout(baris)

        self.panel = PanelItem(ctx)
        lay.addWidget(self.panel, 1)

        baris3 = QHBoxLayout()
        baris3.setSpacing(11)
        baris3.addWidget(w.label("Diskon (Rp)", objek="FormLabel"))
        self.inp_diskon = w.InputRupiah()
        self.inp_diskon.setMaximumWidth(160)
        self.inp_diskon.valueChanged.connect(self._update_ringkas)
        baris3.addWidget(self.inp_diskon)

        baris3.addWidget(w.label("Catatan", objek="FormLabel"))
        self.inp_catatan = QLineEdit()
        baris3.addWidget(self.inp_catatan, 1)
        lay.addLayout(baris3)

        self.panel.total_berubah.connect(lambda _: self._update_ringkas())

        self.lbl_ringkas = QLabel("")
        self.lbl_ringkas.setWordWrap(True)
        self.lbl_ringkas.setTextFormat(Qt.RichText)
        theme.latar(self.lbl_ringkas, f"background: {C.PRIMARY_SOFT}; border: 1px solid #CFE0F0; "
            f"border-radius: 8px; padding: 12px 14px; font-size: {theme.FS_BODY}px;")
        lay.addWidget(self.lbl_ringkas)

        aksi = QHBoxLayout()
        aksi.addStretch()
        b = w.tombol("Batal")
        b.clicked.connect(self.reject)
        aksi.addWidget(b)
        bs = w.tombol("Simpan Purchase Order", gaya="primary")
        bs.clicked.connect(self._simpan)
        aksi.addWidget(bs)
        lay.addLayout(aksi)

        self._update_ringkas()

    def _update_ringkas(self):
        subtotal = self.panel.subtotal()
        diskon = min(self.inp_diskon.nilai(), subtotal)
        dpp = subtotal - diskon
        ppn = int(round(dpp * config.RATE_VAT_EFFECTIVE_NORMAL))
        self.lbl_ringkas.setText(
            f"Subtotal: <b>{tx.rupiah(subtotal)}</b> &nbsp;|&nbsp; "
            f"Diskon: <b>{tx.rupiah(diskon)}</b> &nbsp;|&nbsp; "
            f"DPP: <b>{tx.rupiah(dpp)}</b> &nbsp;|&nbsp; "
            f"Perkiraan PPN: <b>{tx.rupiah(ppn)}</b> &nbsp;|&nbsp; "
            f"TOTAL: <b><font color='{C.PRIMARY}'>{tx.rupiah(dpp + ppn)}</font></b>")

    def _simpan(self):
        try:
            items = self.panel.items()
            if not items:
                QMessageBox.warning(self, "Belum ada item",
                                    "Tambahkan minimal satu baris produk.")
                return
            po = S.buat_purchase_order(
                self.ctx.company_id,
                self.inp_tanggal.date().toString("yyyy-MM-dd"),
                items, self.cmb_vendor.currentData(),
                diskon=self.inp_diskon.nilai(),
                catatan=self.inp_catatan.text().strip(),
                user_id=self.ctx.user_id, username=self.ctx.username)
            self.po_id = po
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Gagal menyimpan", str(e))


class DialogBill(QDialog):
    def __init__(self, ctx, parent=None, po_id: int = None):
        super().__init__(parent)
        self.ctx = ctx
        self.po_id = po_id
        self.setWindowTitle("Catat Bill (Tagihan Pemasok)")
        self.setMinimumSize(1080, 720)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 20, 22, 20)
        lay.setSpacing(12)

        j = QLabel("Bill / Tagihan dari Pemasok")
        j.setObjectName("SectionTitle")
        lay.addWidget(j)

        if ctx.beginner:
            lay.addWidget(w.HelpPanel(
                "Tentang Bill",
                "Bill adalah tagihan dari pemasok yang mengakui utang usaha. "
                "Aplikasi otomatis:\n\n"
                "1. Mencatat utang usaha\n"
                "2. Menambah persediaan (bila jenis Persediaan)\n"
                "3. Mencatat PPN masukan yang dapat dikreditkan\n"
                "4. Membuat jurnal",
                "PSAK 57 - provisi dan liabilitas kontinjensi. "
                "Pasal 9 UU PPN - pengkreditan PPN masukan."))

        baris = QHBoxLayout()
        baris.setSpacing(11)
        baris.addWidget(w.label("Tanggal", objek="FormLabel"))
        self.inp_tanggal = kalender.pasang(QDateEdit())
        self.inp_tanggal.setDisplayFormat("dd/MM/yyyy")
        self.inp_tanggal.setDate(QDate.currentDate())
        baris.addWidget(self.inp_tanggal)

        baris.addWidget(w.label("Pemasok", objek="FormLabel"))
        self.cmb_vendor = QComboBox()
        self.cmb_vendor.setMinimumWidth(240)
        self.cmb_vendor.addItem("Pemasok Umum", None)
        for m in M.daftar_mitra(ctx.company_id, "vendor"):
            self.cmb_vendor.addItem(m["nama"], m["id"])
        baris.addWidget(self.cmb_vendor)

        baris.addWidget(w.label("No. Invoice Pemasok", objek="FormLabel"))
        self.inp_nomor_vendor = QLineEdit()
        self.inp_nomor_vendor.setPlaceholderText("mis. SUP-2026-0456")
        baris.addWidget(self.inp_nomor_vendor, 1)
        lay.addLayout(baris)

        baris2 = QHBoxLayout()
        baris2.setSpacing(11)
        baris2.addWidget(w.label("Jatuh Tempo", objek="FormLabel"))
        self.inp_jatuh = kalender.pasang(QDateEdit())
        self.inp_jatuh.setDisplayFormat("dd/MM/yyyy")
        self.inp_jatuh.setDate(QDate.currentDate().addDays(30))
        baris2.addWidget(self.inp_jatuh)

        baris2.addWidget(w.label("Jenis", objek="FormLabel"))
        self.cmb_jenis = QComboBox()
        self.cmb_jenis.addItem("Persediaan (barang dagang)", "Persediaan")
        self.cmb_jenis.addItem("Beban / Biaya", "Beban")
        self.cmb_jenis.addItem("Aset Tetap", "Aset Tetap")
        self.cmb_jenis.currentIndexChanged.connect(self._update_akun)
        baris2.addWidget(self.cmb_jenis)

        baris2.addWidget(w.label("Akun Beban/Aset", objek="FormLabel"))
        self.cmb_akun = w.combo_akun(ctx.company_id)
        w.set_combo_by_data(self.cmb_akun, "6008")
        baris2.addWidget(self.cmb_akun, 1)

        baris2.addWidget(w.label("Jenis PPN", objek="FormLabel"))
        self.cmb_ppn = QComboBox()
        for jp in tx.PPN_JENIS:
            self.cmb_ppn.addItem(jp, jp)
        if ctx.company and ctx.company["status_pkp"]:
            self.cmb_ppn.setCurrentIndex(1)
        baris2.addWidget(self.cmb_ppn, 1)
        lay.addLayout(baris2)

        self.panel = PanelItem(ctx)
        lay.addWidget(self.panel, 1)

        baris3 = QHBoxLayout()
        baris3.setSpacing(11)
        baris3.addWidget(w.label("Diskon (Rp)", objek="FormLabel"))
        self.inp_diskon = w.InputRupiah()
        self.inp_diskon.setMaximumWidth(160)
        self.inp_diskon.valueChanged.connect(self._update_ringkas)
        baris3.addWidget(self.inp_diskon)

        self.chk_kredit = QCheckBox("PPN Masukan dapat dikreditkan")
        self.chk_kredit.setChecked(True)
        self.chk_kredit.stateChanged.connect(self._update_ringkas)
        baris3.addWidget(self.chk_kredit)

        self.chk_stok = QCheckBox("Tambahkan ke stok")
        self.chk_stok.setChecked(True)
        baris3.addWidget(self.chk_stok)
        baris3.addStretch()
        lay.addLayout(baris3)

        baris4 = QHBoxLayout()
        baris4.addWidget(w.label("Catatan", objek="FormLabel"))
        self.inp_catatan = QLineEdit()
        baris4.addWidget(self.inp_catatan, 1)
        lay.addLayout(baris4)

        self.panel.total_berubah.connect(lambda _: self._update_ringkas())

        self.lbl_ringkas = QLabel("")
        self.lbl_ringkas.setWordWrap(True)
        self.lbl_ringkas.setTextFormat(Qt.RichText)
        theme.latar(self.lbl_ringkas, f"background: {C.PRIMARY_SOFT}; border: 1px solid #CFE0F0; "
            f"border-radius: 8px; padding: 12px 14px; font-size: {theme.FS_BODY}px;")
        lay.addWidget(self.lbl_ringkas)

        aksi = QHBoxLayout()
        aksi.addStretch()
        b = w.tombol("Batal")
        b.clicked.connect(self.reject)
        aksi.addWidget(b)
        bs = w.tombol("Simpan & Buat Jurnal", gaya="primary")
        bs.clicked.connect(self._simpan)
        aksi.addWidget(bs)
        lay.addLayout(aksi)

        self._update_ringkas()
        if po_id:
            self._muat_dari_po(po_id)

    def _update_akun(self):
        jenis = self.cmb_jenis.currentData()
        if jenis == "Persediaan":
            w.set_combo_by_data(self.cmb_akun, "1104")
        elif jenis == "Aset Tetap":
            w.set_combo_by_data(self.cmb_akun, "1201")

    def _update_ringkas(self):
        subtotal = self.panel.subtotal()
        diskon = min(self.inp_diskon.nilai(), subtotal)
        dpp = subtotal - diskon
        ppn_res = tx.hitung_ppn(dpp, self.cmb_ppn.currentData())
        kredit = ppn_res.ppn if self.chk_kredit.isChecked() else 0
        self.lbl_ringkas.setText(
            f"Subtotal: <b>{tx.rupiah(subtotal)}</b> &nbsp;|&nbsp; "
            f"Diskon: <b>{tx.rupiah(diskon)}</b> &nbsp;|&nbsp; "
            f"DPP: <b>{tx.rupiah(dpp)}</b> &nbsp;|&nbsp; "
            f"PPN: <b>{tx.rupiah(ppn_res.ppn)}</b> "
            f"(dikreditkan {tx.rupiah(kredit)}) &nbsp;|&nbsp; "
            f"TOTAL UTANG: <b><font color='{C.PRIMARY}'>"
            f"{tx.rupiah(dpp + ppn_res.ppn)}</font></b>")

    def _muat_dari_po(self, po_id: int):
        po = M.db.q1("SELECT * FROM purchase_orders WHERE id=?", (po_id,))
        if po is None:
            return
        i = self.cmb_vendor.findData(po["partner_id"])
        if i >= 0:
            self.cmb_vendor.setCurrentIndex(i)
        self.inp_catatan.setText(po["catatan"] or "")
        items = S.detail_po(po_id)
        self.panel.baris_data = []
        for it in items:
            self.panel.baris_data.append({
                "product_id": it["product_id"],
                "deskripsi": it["deskripsi"] or it["produk_nama"] or "",
                "qty": float(it["qty"]),
                "satuan": it["satuan"] or "pcs",
                "harga_satuan": int(it["harga_satuan"]),
                "diskon_persen": float(it["diskon_persen"] or 0),
            })
        self.panel._render()
        w.set_combo_by_data(self.cmb_jenis, "Persediaan")
        self._update_akun()

    def _simpan(self):
        try:
            items = self.panel.items()
            if not items:
                QMessageBox.warning(self, "Belum ada item",
                                    "Tambahkan minimal satu baris.")
                return
            S.buat_bill(
                self.ctx.company_id,
                self.inp_tanggal.date().toString("yyyy-MM-dd"),
                items, self.cmb_vendor.currentData(),
                nomor_vendor=self.inp_nomor_vendor.text().strip(),
                jatuh_tempo=self.inp_jatuh.date().toString("yyyy-MM-dd"),
                jenis=self.cmb_jenis.currentData(),
                diskon=self.inp_diskon.nilai(),
                jenis_ppn=self.cmb_ppn.currentData(),
                dapat_dikreditkan=self.chk_kredit.isChecked(),
                po_id=self.po_id,
                akun_beban=self.cmb_akun.currentData() or "6008",
                catatan=self.inp_catatan.text().strip(),
                user_id=self.ctx.user_id, username=self.ctx.username,
                tambah_stok=self.chk_stok.isChecked())
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Gagal menyimpan", str(e))


class DialogBayarVendor(QDialog):
    def __init__(self, ctx, parent=None, bill_id: int = None, partner_id: int = None):
        super().__init__(parent)
        self.ctx = ctx
        self.bill_id = bill_id
        self.partner_id = partner_id
        self.setWindowTitle("Pembayaran ke Pemasok")
        self.setMinimumSize(840, 600)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 20, 22, 20)
        lay.setSpacing(12)

        j = QLabel("Pembayaran ke Pemasok")
        j.setObjectName("SectionTitle")
        lay.addWidget(j)

        baris = QHBoxLayout()
        baris.setSpacing(11)
        baris.addWidget(w.label("Tanggal", objek="FormLabel"))
        self.inp_tanggal = kalender.pasang(QDateEdit())
        self.inp_tanggal.setDisplayFormat("dd/MM/yyyy")
        self.inp_tanggal.setDate(QDate.currentDate())
        baris.addWidget(self.inp_tanggal)

        baris.addWidget(w.label("Jumlah Dibayar (Rp)", objek="FormLabel"))
        self.inp_jumlah = w.InputRupiah()
        self.inp_jumlah.valueChanged.connect(self._cek_alokasi)
        baris.addWidget(self.inp_jumlah)

        baris.addWidget(w.label("Dari Rekening", objek="FormLabel"))
        self.cmb_kas = QComboBox()
        for kb in O.daftar_kas_bank(ctx.company_id):
            self.cmb_kas.addItem(kb["nama"], kb["akun_buku"])
        baris.addWidget(self.cmb_kas, 1)
        lay.addLayout(baris)

        baris2 = QHBoxLayout()
        baris2.setSpacing(11)
        baris2.addWidget(w.label("Metode", objek="FormLabel"))
        self.cmb_metode = QComboBox()
        for m in ["Transfer", "Tunai", "Cek", "Giro", "Virtual Account"]:
            self.cmb_metode.addItem(m, m)
        baris2.addWidget(self.cmb_metode)

        baris2.addWidget(w.label("Referensi", objek="FormLabel"))
        self.inp_ref = QLineEdit()
        baris2.addWidget(self.inp_ref, 1)

        baris2.addWidget(w.label("Catatan", objek="FormLabel"))
        self.inp_catatan = QLineEdit()
        baris2.addWidget(self.inp_catatan, 1)
        lay.addLayout(baris2)

        lay.addWidget(w.label("Pilih Bill yang Dibayar", objek="SectionTitle"))

        self.tabel = w.Tabel([
            ("", 40), ("Bill", 175), ("No. Vendor", 145), ("Tanggal", 110),
            ("Jatuh Tempo", 115), ("Total", 150), ("Sisa", 150), ("Alokasi", 165),
        ])
        lay.addWidget(self.tabel, 1)

        self.checks: dict[int, QCheckBox] = {}
        self.inputs: dict[int, w.InputRupiah] = {}
        self._muat_bill()

        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet(f"font-size: {theme.FS_BODY}px; "
                                      "font-weight: 600; background: transparent;")
        lay.addWidget(self.lbl_status)

        aksi = QHBoxLayout()
        aksi.addStretch()
        b = w.tombol("Batal")
        b.clicked.connect(self.reject)
        aksi.addWidget(b)
        bs = w.tombol("Simpan Pembayaran", gaya="primary")
        bs.clicked.connect(self._simpan)
        aksi.addWidget(bs)
        lay.addLayout(aksi)

    def _muat_bill(self):
        cid = self.ctx.company_id
        daftar = S.daftar_bill(cid, status="belum_lunas", partner_id=self.partner_id)
        self.tabel.setRowCount(len(daftar))
        self.checks.clear()
        self.inputs.clear()

        for i, b in enumerate(daftar):
            chk = QCheckBox()
            chk.setChecked(b["id"] == self.bill_id)
            chk.stateChanged.connect(self._cek_alokasi)
            self.checks[b["id"]] = chk
            self.tabel.setCellWidget(i, 0, chk)

            self.tabel.setItem(i, 1, QTableWidgetItem(b["nomor"]))
            self.tabel.setItem(i, 2, QTableWidgetItem(b["nomor_vendor"] or ""))
            self.tabel.setItem(i, 3, QTableWidgetItem(theme.tanggal_id(b["tanggal"])))
            self.tabel.setItem(i, 4, QTableWidgetItem(
                theme.tanggal_id(b["jatuh_tempo"] or "")))
            for kolom, nilai in [(5, b["total"]), (6, b["sisa"])]:
                item = QTableWidgetItem(tx.rupiah(nilai))
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.tabel.setItem(i, kolom, item)

            inp = w.InputRupiah()
            if b["id"] == self.bill_id:
                inp.set_nilai(b["sisa"])
            inp.valueChanged.connect(self._cek_alokasi)
            self.inputs[b["id"]] = inp
            self.tabel.setCellWidget(i, 7, inp)

        if self.bill_id and self.bill_id in self.inputs:
            b = S.get_bill(self.bill_id)
            if b:
                self.inp_jumlah.set_nilai(b["sisa"])

    def _total_alokasi(self) -> int:
        return sum(inp.nilai() for bid, inp in self.inputs.items()
                   if self.checks.get(bid) and self.checks[bid].isChecked())

    def _cek_alokasi(self):
        dibayar = self.inp_jumlah.nilai()
        dialokasikan = self._total_alokasi()
        selisih = dibayar - dialokasikan

        if dibayar == 0 and dialokasikan == 0:
            self.lbl_status.setText("Masukkan jumlah dan pilih bill.")
            self.lbl_status.setStyleSheet(
                f"color: {C.TEXT_MUTED}; font-weight: 600; background: transparent;")
        elif selisih == 0:
            self.lbl_status.setText(
                f"Seimbang - {tx.rupiah(dialokasikan)} dialokasikan penuh.")
            self.lbl_status.setStyleSheet(
                f"color: {C.SUCCESS}; font-weight: 700; background: transparent;")
        elif selisih > 0:
            self.lbl_status.setText(
                f"Perhatian: {tx.rupiah(selisih)} belum dialokasikan.")
            self.lbl_status.setStyleSheet(
                f"color: {C.WARNING}; font-weight: 700; background: transparent;")
        else:
            self.lbl_status.setText(
                f"Alokasi melebihi pembayaran {tx.rupiah(-selisih)}.")
            self.lbl_status.setStyleSheet(
                f"color: {C.DANGER}; font-weight: 700; background: transparent;")

    def _simpan(self):
        try:
            jumlah = self.inp_jumlah.nilai()
            if jumlah <= 0:
                QMessageBox.warning(self, "Jumlah kosong", "Isi jumlah pembayaran.")
                return
            alokasi = [{"bill_id": bid, "jumlah": inp.nilai()}
                       for bid, inp in self.inputs.items()
                       if self.checks.get(bid) and self.checks[bid].isChecked()
                       and inp.nilai() > 0]
            if not alokasi:
                QMessageBox.warning(self, "Belum ada alokasi", "Pilih bill.")
                return
            if self._total_alokasi() > jumlah:
                QMessageBox.warning(self, "Alokasi berlebih",
                                    "Total alokasi melebihi jumlah pembayaran.")
                return

            partner_id = self.partner_id
            if not partner_id:
                b = S.get_bill(alokasi[0]["bill_id"])
                if b:
                    partner_id = b["partner_id"]

            S.bayar_vendor(
                self.ctx.company_id,
                self.inp_tanggal.date().toString("yyyy-MM-dd"),
                jumlah, alokasi, partner_id,
                akun_kas=self.cmb_kas.currentData() or "",
                metode=self.cmb_metode.currentData(),
                referensi=self.inp_ref.text().strip(),
                catatan=self.inp_catatan.text().strip(),
                user_id=self.ctx.user_id, username=self.ctx.username)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Gagal menyimpan", str(e))


class DialogReturPembelian(QDialog):
    def __init__(self, ctx, parent=None, bill_id: int = None):
        super().__init__(parent)
        self.ctx = ctx
        self.bill_id = bill_id
        self.setWindowTitle("Retur Pembelian")
        self.setMinimumSize(820, 560)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 20, 22, 20)
        lay.setSpacing(12)

        j = QLabel("Retur ke Pemasok")
        j.setObjectName("SectionTitle")
        lay.addWidget(j)

        lay.addWidget(w.HelpPanel(
            "Tentang retur pembelian",
            "Retur mengurangi utang usaha dan mengeluarkan barang dari persediaan. "
            "Aplikasi otomatis membuat jurnal balik.",
            "PSAK 14 - pengurangan biaya perolehan persediaan."))

        baris = QHBoxLayout()
        baris.setSpacing(11)
        baris.addWidget(w.label("Tanggal", objek="FormLabel"))
        self.inp_tanggal = kalender.pasang(QDateEdit())
        self.inp_tanggal.setDisplayFormat("dd/MM/yyyy")
        self.inp_tanggal.setDate(QDate.currentDate())
        baris.addWidget(self.inp_tanggal)

        baris.addWidget(w.label("Bill", objek="FormLabel"))
        self.cmb_bill = QComboBox()
        self.cmb_bill.setMinimumWidth(360)
        for b in S.daftar_bill(ctx.company_id):
            if b["status"] != "batal":
                self.cmb_bill.addItem(
                    f"{b['nomor']} - {b['vendor']} ({tx.rupiah(b['total'])})",
                    b["id"])
        i = self.cmb_bill.findData(bill_id)
        if i >= 0:
            self.cmb_bill.setCurrentIndex(i)
        self.cmb_bill.currentIndexChanged.connect(self._muat_item)
        baris.addWidget(self.cmb_bill, 1)
        lay.addLayout(baris)

        baris2 = QHBoxLayout()
        baris2.addWidget(w.label("Alasan", objek="FormLabel"))
        self.inp_alasan = QLineEdit()
        self.inp_alasan.setPlaceholderText("mis. Barang cacat 10 unit")
        baris2.addWidget(self.inp_alasan, 1)
        lay.addLayout(baris2)

        lay.addWidget(w.label("Barang yang Diretur", objek="SectionTitle"))
        self.tabel = w.Tabel([("Produk", -1), ("Qty Beli", 110), ("Harga", 150),
                              ("Qty Retur", 165)])
        lay.addWidget(self.tabel, 1)

        self.inputs: dict[int, tuple] = {}
        self._muat_item()

        aksi = QHBoxLayout()
        aksi.addStretch()
        b = w.tombol("Batal")
        b.clicked.connect(self.reject)
        aksi.addWidget(b)
        bs = w.tombol("Simpan Retur", gaya="primary")
        bs.clicked.connect(self._simpan)
        aksi.addWidget(bs)
        lay.addLayout(aksi)

    def _muat_item(self):
        bid = self.cmb_bill.currentData()
        self.inputs.clear()
        if not bid:
            self.tabel.setRowCount(0)
            return
        items = S.detail_bill(bid)
        self.tabel.setRowCount(len(items))
        for i, it in enumerate(items):
            self.tabel.setItem(i, 0, QTableWidgetItem(
                it["deskripsi"] or it["produk_nama"] or ""))
            self.tabel.setItem(i, 1, QTableWidgetItem(f"{it['qty']:g}"))
            self.tabel.setItem(i, 2, QTableWidgetItem(tx.rupiah(it["harga_satuan"])))
            inp = w.InputRupiah()
            self.inputs[i] = (inp, it)
            self.tabel.setCellWidget(i, 3, inp)

    def _simpan(self):
        try:
            bid = self.cmb_bill.currentData()
            if not bid:
                QMessageBox.warning(self, "Bill kosong", "Pilih bill terlebih dahulu.")
                return
            items = []
            for i, (inp, it) in self.inputs.items():
                qty = inp.nilai()
                if qty > 0:
                    items.append({
                        "product_id": it["product_id"],
                        "qty": qty,
                        "harga_satuan": it["harga_satuan"],
                    })
            if not items:
                QMessageBox.warning(self, "Belum ada item",
                                    "Isi jumlah barang yang diretur.")
                return
            S.retur_pembelian(self.ctx.company_id,
                              self.inp_tanggal.date().toString("yyyy-MM-dd"),
                              bid, items, self.inp_alasan.text().strip(),
                              self.ctx.user_id, self.ctx.username)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Gagal menyimpan", str(e))


class PembelianLengkapPage(QWidget):
    pindah_halaman = Signal(str)

    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx

        luar = QVBoxLayout(self)
        luar.setContentsMargins(0, 0, 0, 0)
        luar.setSpacing(0)

        self.header = w.PageHeader(
            "Pembelian",
            "Purchase order, bill, pembayaran ke pemasok, retur, dan aging utang.")

        b_po = w.tombol("Purchase Order", ikon="jurnal")
        b_po.clicked.connect(self._buat_po)
        self.header.tambah_aksi(b_po)

        b_bill = w.tombol("Bill Baru", gaya="primary", ikon="+")
        b_bill.clicked.connect(self._buat_bill)
        self.header.tambah_aksi(b_bill)

        b_pay = w.tombol("Bayar Pemasok", gaya="success", ikon="simpan")
        b_pay.clicked.connect(self._bayar)
        self.header.tambah_aksi(b_pay)

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
        self.tab_bill = QWidget()
        self.tab_po = QWidget()
        self.tab_bayar = QWidget()
        self.tab_aging = QWidget()
        self.tabs.addTab(self.tab_bill, "Bill")
        self.tabs.addTab(self.tab_po, "Purchase Order")
        self.tabs.addTab(self.tab_bayar, "Pembayaran")
        self.tabs.addTab(self.tab_aging, "Aging Utang")
        self.tabs.currentChanged.connect(self.muat)
        self.lay.addWidget(self.tabs, 1)

        self._bangun_bill()
        self._bangun_po()
        self._bangun_bayar()
        self._bangun_aging()

    def _bangun_bill(self):
        lay = QVBoxLayout(self.tab_bill)
        lay.setContentsMargins(0, 12, 0, 0)
        lay.setSpacing(12)

        baris = QHBoxLayout()
        baris.setSpacing(10)
        self.inp_cari_bill = QLineEdit()
        self.inp_cari_bill.setPlaceholderText("Cari nomor bill, vendor, atau nomor invoice…")
        self.inp_cari_bill.setMinimumWidth(300)
        self.inp_cari_bill.textChanged.connect(self.muat)
        baris.addWidget(self.inp_cari_bill)

        self.cmb_status_bill = QComboBox()
        self.cmb_status_bill.addItem("Semua Status", "")
        self.cmb_status_bill.addItem("Belum Lunas", "belum_lunas")
        self.cmb_status_bill.addItem("Terbuka", "terbuka")
        self.cmb_status_bill.addItem("Sebagian", "sebagian")
        self.cmb_status_bill.addItem("Lunas", "lunas")
        self.cmb_status_bill.currentIndexChanged.connect(self.muat)
        baris.addWidget(self.cmb_status_bill)
        baris.addStretch()
        self.lbl_bill = QLabel("")
        self.lbl_bill.setObjectName("Muted")
        baris.addWidget(self.lbl_bill)
        lay.addLayout(baris)

        self.tabel_bill = w.Tabel([
            ("Nomor", 165), ("No. Vendor", 145), ("Tanggal", 105),
            ("Pemasok", -1), ("Jatuh Tempo", 110), ("Total", 150),
            ("Sisa", 140), ("Status", 105),
        ])
        self.tabel_bill.doubleClicked.connect(self._detail_bill)
        lay.addWidget(self.tabel_bill, 1)

        baris2 = QHBoxLayout()
        baris2.setSpacing(9)
        b1 = w.tombol("Lihat Detail", ikon="")
        b1.clicked.connect(self._detail_bill)
        baris2.addWidget(b1)
        b2 = w.tombol("Bayar", gaya="success", ikon="simpan")
        b2.clicked.connect(self._bayar_bill_terpilih)
        baris2.addWidget(b2)
        b3 = w.tombol("Retur", ikon="")
        b3.clicked.connect(self._retur_bill)
        baris2.addWidget(b3)
        baris2.addStretch()
        lay.addLayout(baris2)

    def _bangun_po(self):
        lay = QVBoxLayout(self.tab_po)
        lay.setContentsMargins(0, 12, 0, 0)
        lay.setSpacing(12)

        self.tabel_po = w.Tabel([
            ("Nomor", 175), ("Tanggal", 105), ("Pemasok", -1),
            ("Tgl Terima", 110), ("Subtotal", 150), ("PPN", 140),
            ("Total", 150), ("Status", 115),
        ])
        lay.addWidget(self.tabel_po, 1)

        baris = QHBoxLayout()
        baris.setSpacing(9)
        b1 = w.tombol("Konfirmasi PO", gaya="success", ikon="simpan")
        b1.clicked.connect(lambda: self._ubah_status_po("dikonfirmasi"))
        baris.addWidget(b1)
        b2 = w.tombol("Buat Bill dari PO", gaya="primary", ikon="")
        b2.clicked.connect(self._bill_dari_po)
        baris.addWidget(b2)
        b3 = w.tombol("Batalkan PO", gaya="danger", ikon="⊘")
        b3.clicked.connect(lambda: self._ubah_status_po("batal"))
        baris.addWidget(b3)
        baris.addStretch()
        self.lbl_po = QLabel("")
        self.lbl_po.setObjectName("Muted")
        baris.addWidget(self.lbl_po)
        lay.addLayout(baris)

    def _bangun_bayar(self):
        lay = QVBoxLayout(self.tab_bayar)
        lay.setContentsMargins(0, 12, 0, 0)
        lay.setSpacing(12)

        self.tabel_bayar = w.Tabel([
            ("Nomor", 175), ("Tanggal", 110), ("Pemasok", -1),
            ("Metode", 130), ("Jumlah", 165), ("Referensi", 175), ("Status", 105),
        ])
        lay.addWidget(self.tabel_bayar, 1)

        baris = QHBoxLayout()
        b = w.tombol("Void Pembayaran", gaya="danger", ikon="⊘")
        b.clicked.connect(self._void_bayar)
        baris.addWidget(b)
        baris.addStretch()
        self.lbl_bayar = QLabel("")
        self.lbl_bayar.setObjectName("Muted")
        baris.addWidget(self.lbl_bayar)
        lay.addLayout(baris)

    def _bangun_aging(self):
        lay = QVBoxLayout(self.tab_aging)
        lay.setContentsMargins(0, 12, 0, 0)
        lay.setSpacing(12)

        self.panel_aging_ap = QWidget()
        self.panel_aging_ap_lay = QVBoxLayout(self.panel_aging_ap)
        self.panel_aging_ap_lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.panel_aging_ap)

        self.tabel_aging_ap = w.Tabel([
            ("Pemasok", -1), ("Jumlah Bill", 120),
            ("Belum JT", 145), ("1-30 hari", 140), ("31-60 hari", 140),
            ("61-90 hari", 140), ("di atas 90", 145), ("Total", 155),
        ])
        lay.addWidget(self.tabel_aging_ap, 1)

        baris = QHBoxLayout()
        b = w.tombol("Buat Pengingat Pembayaran", gaya="primary", ikon="peringatan")
        b.clicked.connect(self._buat_pengingat)
        baris.addWidget(b)
        baris.addStretch()
        self.lbl_aging_ap = QLabel("")
        self.lbl_aging_ap.setObjectName("Muted")
        baris.addWidget(self.lbl_aging_ap)
        lay.addLayout(baris)

    def muat(self):
        if not self.ctx.company_id:
            return
        idx = self.tabs.currentIndex()
        if idx == 0:
            self._muat_bill()
        elif idx == 1:
            self._muat_po()
        elif idx == 2:
            self._muat_bayar()
        else:
            self._muat_aging()

    def _muat_bill(self):
        cid = self.ctx.company_id
        data = S.daftar_bill(cid, self.ctx.tahun,
                             self.cmb_status_bill.currentData(),
                             cari=self.inp_cari_bill.text().strip())
        baris, warna = [], {}
        total_sisa = 0
        hari_ini = datetime.now().date()
        for i, b in enumerate(data):
            idx = len(baris)
            total_sisa += b["sisa"]
            baris.append([
                b["nomor"], b["nomor_vendor"] or "",
                theme.tanggal_id(b["tanggal"]), b["vendor"],
                theme.tanggal_id(b["jatuh_tempo"] or ""),
                tx.rupiah(b["total"]), tx.rupiah(b["sisa"]),
                {"terbuka": "Terbuka", "sebagian": "Sebagian",
                 "lunas": "Lunas", "batal": "Batal"}.get(b["status"], b["status"]),
            ])
            if b["status"] == "lunas":
                warna[idx] = C.SUCCESS
            elif b["status"] == "batal":
                warna[idx] = C.TEXT_FAINT
            else:
                try:
                    jt = datetime.fromisoformat(
                        (b["jatuh_tempo"] or b["tanggal"])[:10]).date()
                    if jt < hari_ini:
                        warna[idx] = C.DANGER
                    elif (jt - hari_ini).days <= 7:
                        warna[idx] = C.WARNING
                except ValueError:
                    pass
        self.tabel_bill.isi(baris, warna_baris=warna, align_kanan={5, 6})
        self.lbl_bill.setText(f"{len(data)} bill · total utang {tx.rupiah(total_sisa)}")

    def _muat_po(self):
        data = S.daftar_purchase_order(self.ctx.company_id, self.ctx.tahun)
        baris, warna = [], {}
        for i, po in enumerate(data):
            idx = len(baris)
            baris.append([
                po["nomor"], theme.tanggal_id(po["tanggal"]), po["vendor"],
                theme.tanggal_id(po["tanggal_terima"] or ""),
                tx.rupiah(po["subtotal"]), tx.rupiah(po["ppn"]),
                tx.rupiah(po["total"]),
                {"draft": "Draft", "dikonfirmasi": "Dikonfirmasi",
                 "selesai": "Selesai", "batal": "Batal"}.get(po["status"],
                                                              po["status"]),
            ])
            if po["status"] == "selesai":
                warna[idx] = C.SUCCESS
            elif po["status"] == "batal":
                warna[idx] = C.TEXT_FAINT
        self.tabel_po.isi(baris, warna_baris=warna, align_kanan={4, 5, 6})
        self.lbl_po.setText(f"{len(data)} purchase order")

    def _muat_bayar(self):
        data = S.daftar_pembayaran_vendor(self.ctx.company_id, self.ctx.tahun)
        baris, warna = [], {}
        total = 0
        for i, p in enumerate(data):
            idx = len(baris)
            total += p["jumlah"] if p["status"] == "aktif" else 0
            baris.append([
                p["nomor"], theme.tanggal_id(p["tanggal"]), p["vendor"],
                p["metode"], tx.rupiah(p["jumlah"]), p["referensi"],
                "Aktif" if p["status"] == "aktif" else "Void",
            ])
            if p["status"] == "void":
                warna[idx] = C.TEXT_FAINT
        self.tabel_bayar.isi(baris, warna_baris=warna, align_kanan={4})
        self.lbl_bayar.setText(f"{len(data)} pembayaran · total {tx.rupiah(total)}")

    def _muat_aging(self):
        while self.panel_aging_ap_lay.count():
            it = self.panel_aging_ap_lay.takeAt(0)
            wdg = it.widget()
            if wdg is not None:
                wdg.setParent(None)
                wdg.deleteLater()

        ag = S.aging_utang(self.ctx.company_id)
        kartu = w.Card()
        kl = kartu.body()
        b = QHBoxLayout()
        b.setSpacing(26)
        for nama, nilai in ag["kelompok"].items():
            warna = C.TEXT
            if nama == "Belum Jatuh Tempo":
                warna = C.SUCCESS
            elif nama == "Di atas 90 hari":
                warna = C.DANGER
            elif nama != "1-30 hari":
                warna = C.WARNING
            b.addWidget(w.MiniStat(nama, tx.rupiah(nilai), warna))
        b.addStretch()
        kl.addLayout(b)
        self.panel_aging_ap_lay.addWidget(kartu)

        baris, warna = [], {}
        for p in ag["per_vendor"]:
            idx = len(baris)
            baris.append([
                p["vendor"], str(p["jumlah_bill"]),
                tx.rupiah(p["Belum Jatuh Tempo"]), tx.rupiah(p["1-30 hari"]),
                tx.rupiah(p["31-60 hari"]), tx.rupiah(p["61-90 hari"]),
                tx.rupiah(p["Di atas 90 hari"]), tx.rupiah(p["total"]),
            ])
            if p["Di atas 90 hari"] > 0:
                warna[idx] = C.DANGER
            elif p["61-90 hari"] > 0:
                warna[idx] = C.WARNING
        self.tabel_aging_ap.isi(baris, warna_baris=warna,
                                align_kanan={1, 2, 3, 4, 5, 6, 7})
        self.lbl_aging_ap.setText(f"{len(ag['per_vendor'])} pemasok · total utang "
                                  f"{tx.rupiah(ag['total'])}")

    def _buat_po(self):
        if not self.ctx.company_id:
            QMessageBox.information(self, "Belum ada perusahaan",
                                    "Buat profil perusahaan terlebih dahulu.")
            return
        d = DialogPurchaseOrder(self.ctx, self)
        if d.exec():
            self.tabs.setCurrentIndex(1)
            self.muat()

    def _buat_bill(self):
        if not self.ctx.company_id:
            QMessageBox.information(self, "Belum ada perusahaan",
                                    "Buat profil perusahaan terlebih dahulu.")
            return
        d = DialogBill(self.ctx, self)
        if d.exec():
            self.muat()

    def _bayar(self):
        d = DialogBayarVendor(self.ctx, self)
        if d.exec():
            self.muat()

    def _bill_terpilih(self):
        r = self.tabel_bill.baris_terpilih()
        if r is None:
            return None
        data = S.daftar_bill(self.ctx.company_id, self.ctx.tahun,
                             self.cmb_status_bill.currentData(),
                             cari=self.inp_cari_bill.text().strip())
        return data[r] if r < len(data) else None

    def _detail_bill(self):
        b = self._bill_terpilih()
        if b is None:
            return
        items = S.detail_bill(b["id"])

        dlg = QDialog(self)
        dlg.setWindowTitle(f"Detail Bill {b['nomor']}")
        dlg.setMinimumSize(940, 620)
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(22, 20, 22, 20)
        lay.setSpacing(12)

        j = QLabel(f"Bill {b['nomor']}")
        j.setObjectName("SectionTitle")
        lay.addWidget(j)

        kartu = w.Card()
        kl = kartu.body()
        grid = QGridLayout()
        grid.setSpacing(14)
        info = [
            ("Pemasok", b["vendor"]),
            ("No. Invoice Vendor", b["nomor_vendor"] or ""),
            ("Tanggal", theme.tanggal_id(b["tanggal"])),
            ("Jatuh Tempo", theme.tanggal_id(b["jatuh_tempo"] or "")),
            ("Jenis", b["jenis"]),
            ("Status", istilah.label("status", b["status"])),
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
            vl.setStyleSheet(f"font-size: {theme.FS_BODY}px; background: transparent;")
            kl2.addWidget(vl)
            grid.addWidget(kotak, i // 3, i % 3)
        kl.addLayout(grid)
        lay.addWidget(kartu)

        t = w.Tabel([("Produk", -1), ("Qty", 90), ("Satuan", 85),
                     ("Harga Satuan", 155), ("Subtotal", 165)])
        t.isi([[it["deskripsi"] or it["produk_nama"] or "", f"{it['qty']:g}",
                it["satuan"] or "", tx.rupiah(it["harga_satuan"]),
                tx.rupiah(it["subtotal"])] for it in items],
              align_kanan={1, 3, 4})
        t.setMinimumHeight(220)
        lay.addWidget(t)

        kartu2 = w.Card()
        kl3 = kartu2.body()
        b2 = QHBoxLayout()
        b2.setSpacing(28)
        b2.addWidget(w.MiniStat("Subtotal", tx.rupiah(b["subtotal"])))
        b2.addWidget(w.MiniStat("Diskon", tx.rupiah(b["diskon"])))
        b2.addWidget(w.MiniStat("DPP", tx.rupiah(b["dpp"])))
        b2.addWidget(w.MiniStat("PPN", tx.rupiah(b["ppn"])))
        b2.addWidget(w.MiniStat("Total", tx.rupiah(b["total"]), C.PRIMARY))
        b2.addWidget(w.MiniStat("Dibayar", tx.rupiah(b["dibayar"]), C.SUCCESS))
        b2.addWidget(w.MiniStat("Sisa", tx.rupiah(b["sisa"]),
                                C.DANGER if b["sisa"] else C.SUCCESS))
        b2.addStretch()
        kl3.addLayout(b2)
        lay.addWidget(kartu2)

        bt = w.tombol("Tutup", gaya="primary")
        bt.clicked.connect(dlg.accept)
        bl = QHBoxLayout()
        bl.addStretch()
        bl.addWidget(bt)
        lay.addLayout(bl)
        dlg.exec()

    def _bayar_bill_terpilih(self):
        b = self._bill_terpilih()
        if b is None:
            QMessageBox.information(self, "Belum dipilih", "Pilih satu bill.")
            return
        if b["status"] == "lunas":
            QMessageBox.information(self, "Sudah lunas", "Bill ini sudah lunas.")
            return
        d = DialogBayarVendor(self.ctx, self, b["id"], b["partner_id"])
        if d.exec():
            self.muat()

    def _retur_bill(self):
        b = self._bill_terpilih()
        if b is None:
            QMessageBox.information(self, "Belum dipilih", "Pilih satu bill.")
            return
        d = DialogReturPembelian(self.ctx, self, b["id"])
        if d.exec():
            self.muat()

    def _po_terpilih(self):
        r = self.tabel_po.baris_terpilih()
        if r is None:
            return None
        data = S.daftar_purchase_order(self.ctx.company_id, self.ctx.tahun)
        return data[r] if r < len(data) else None

    def _ubah_status_po(self, status: str):
        po = self._po_terpilih()
        if po is None:
            QMessageBox.information(self, "Belum dipilih", "Pilih satu purchase order.")
            return
        try:
            S.ubah_status_po(po["id"], status)
            self.muat()
        except Exception as e:
            QMessageBox.critical(self, "Gagal", str(e))

    def _bill_dari_po(self):
        po = self._po_terpilih()
        if po is None:
            QMessageBox.information(self, "Belum dipilih", "Pilih satu purchase order.")
            return
        if po["status"] == "batal":
            QMessageBox.warning(self, "PO dibatalkan",
                                "PO yang dibatalkan tidak dapat dibuatkan bill.")
            return
        d = DialogBill(self.ctx, self, po_id=po["id"])
        if d.exec():
            self.tabs.setCurrentIndex(0)
            self.muat()

    def _bayar_terpilih(self):
        r = self.tabel_bayar.baris_terpilih()
        if r is None:
            return None
        data = S.daftar_pembayaran_vendor(self.ctx.company_id, self.ctx.tahun)
        return data[r] if r < len(data) else None

    def _void_bayar(self):
        p = self._bayar_terpilih()
        if p is None:
            QMessageBox.information(self, "Belum dipilih", "Pilih satu pembayaran.")
            return
        if p["status"] == "void":
            QMessageBox.information(self, "Sudah void",
                                    "Pembayaran ini sudah dibatalkan.")
            return
        if QMessageBox.question(
                self, "Konfirmasi Void",
                f"Void pembayaran {p['nomor']}?\n\n"
                "Status bill terkait akan dikembalikan.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No) != QMessageBox.Yes:
            return
        try:
            S.void_pembayaran_vendor(p["id"], self.ctx.username, self.ctx.user_id)
            self.muat()
        except Exception as e:
            QMessageBox.critical(self, "Gagal void", str(e))

    def _buat_pengingat(self):
        try:
            jumlah = O.buat_reminder_dari_utang(self.ctx.company_id, 30)
            if jumlah:
                QMessageBox.information(
                    self, "Pengingat dibuat",
                    f"{jumlah} pengingat pembayaran dibuat untuk bill yang jatuh "
                    "tempo dalam 30 hari ke depan.")
            else:
                QMessageBox.information(self, "Tidak ada pengingat baru",
                                        "Semua bill sudah memiliki pengingat.")
        except Exception as e:
            QMessageBox.critical(self, "Gagal", str(e))
