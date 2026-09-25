"""
Halaman penjualan lengkap: Sales Order, Invoice (dengan PDF), Penerimaan
Pembayaran, Nota Kredit, dan Aging Piutang.
"""
from __future__ import annotations

import os
from datetime import datetime

from PySide6.QtCore import Qt, Signal, QDate, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit, QDateEdit,
    QPushButton, QDialog, QMessageBox, QGridLayout, QCheckBox, QTabWidget,
    QTableWidgetItem, QFileDialog,
)

from ... import config, modules as M, modules_sales as S, modules_ops as O
from ...core import tax_engine as tx
from .. import theme, widgets as w
from .. import kalender
from ..theme import C


# ==========================================================================
# GENERATOR PDF INVOICE
# ==========================================================================
def buat_pdf_invoice(company_id: int, invoice_id: int, path: str) -> str:
    """Hasilkan berkas PDF invoice siap kirim ke pelanggan."""
    inv = S.get_invoice(invoice_id)
    if inv is None:
        raise ValueError("Invoice tidak ditemukan.")

    comp = M.services.get_company(company_id)
    items = S.detail_invoice(invoice_id)

    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.units import mm
        from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                        Paragraph, Spacer, Image, KeepTogether)
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    except ImportError:
        raise RuntimeError("Modul reportlab belum terpasang.")

    styles = getSampleStyleSheet()
    st_normal = ParagraphStyle("N", parent=styles["Normal"], fontSize=9,
                               leading=13, textColor=colors.HexColor("#1A2733"))
    st_kecil = ParagraphStyle("K", parent=styles["Normal"], fontSize=8,
                              leading=11, textColor=colors.HexColor("#64748B"))
    st_judul = ParagraphStyle("J", parent=styles["Title"], fontSize=22,
                              textColor=colors.HexColor("#1B4F8A"), spaceAfter=0)
    st_label = ParagraphStyle("L", parent=styles["Normal"], fontSize=8,
                              textColor=colors.HexColor("#64748B"),
                              spaceAfter=2)

    doc = SimpleDocTemplate(path, pagesize=A4,
                            leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=16 * mm, bottomMargin=16 * mm,
                            title=f"Invoice {inv['nomor']}",
                            author=comp["nama"] if comp else "AkunTuntas")

    elemen = []

    # ---- kop: logo + identitas perusahaan
    kiri = []
    logo_path = comp["logo_path"] if comp else ""
    if logo_path and os.path.isfile(logo_path):
        try:
            kiri.append(Image(logo_path, width=38 * mm, height=19 * mm,
                              kind="proportional"))
            kiri.append(Spacer(1, 4))
        except Exception:
            pass

    kiri.append(Paragraph(f"<b>{comp['nama'] if comp else ''}</b>", st_normal))
    if comp:
        if comp["alamat"]:
            kiri.append(Paragraph(comp["alamat"], st_kecil))
        kota_line = " ".join(filter(None, [comp["kota"], comp["kode_pos"]]))
        if kota_line:
            kiri.append(Paragraph(kota_line, st_kecil))
        if comp["npwp"]:
            kiri.append(Paragraph(f"NPWP: {comp['npwp']}", st_kecil))
        if comp["telepon"]:
            kiri.append(Paragraph(f"Telp: {comp['telepon']}", st_kecil))
        if comp["email"]:
            kiri.append(Paragraph(comp["email"], st_kecil))

    kanan = [
        Paragraph("INVOICE", st_judul),
        Spacer(1, 4),
        Paragraph(f"<b>{inv['nomor']}</b>", st_normal),
        Spacer(1, 6),
        Paragraph(f"Tanggal: {theme.tanggal_id(inv['tanggal'])}", st_kecil),
        Paragraph(f"Jatuh Tempo: {theme.tanggal_id(inv['jatuh_tempo'] or '')}",
                  st_kecil),
    ]
    if inv["status"] == "lunas":
        kanan.append(Spacer(1, 4))
        kanan.append(Paragraph(
            "<b><font color='#047857'>LUNAS</font></b>", st_normal))

    kop = Table([[kiri, kanan]], colWidths=[doc.width * 0.55, doc.width * 0.45])
    kop.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    elemen.append(kop)
    elemen.append(Spacer(1, 10))

    garis = Table([[""]], colWidths=[doc.width], rowHeights=[1.5])
    garis.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1),
                                colors.HexColor("#1B4F8A"))]))
    elemen.append(garis)
    elemen.append(Spacer(1, 12))

    # ---- tagihan kepada
    elemen.append(Paragraph("DITAGIHKAN KEPADA", st_label))
    pelanggan = [Paragraph(f"<b>{inv['pelanggan']}</b>", st_normal)]
    if inv["npwp_nik"]:
        pelanggan.append(Paragraph(f"NPWP/NIK: {inv['npwp_nik']}", st_kecil))
    if inv["alamat"]:
        pelanggan.append(Paragraph(inv["alamat"], st_kecil))
    elemen.append(KeepTogether(pelanggan))
    elemen.append(Spacer(1, 14))

    # ---- tabel item
    data = [["No", "Deskripsi", "Qty", "Satuan", "Harga Satuan", "Diskon",
             "Jumlah"]]
    for n, it in enumerate(items, start=1):
        diskon_teks = ""
        if it["diskon_persen"]:
            diskon_teks = f"{it['diskon_persen']:g}%"
        elif it["diskon_nilai"]:
            diskon_teks = f"{it['diskon_nilai']:,}".replace(",", ".")
        data.append([
            str(n),
            it["deskripsi"] or (it["produk_nama"] or ""),
            f"{it['qty']:g}",
            it["satuan"] or "",
            f"{it['harga_satuan']:,}".replace(",", "."),
            diskon_teks,
            f"{it['subtotal']:,}".replace(",", "."),
        ])

    lebar = [doc.width * x for x in (0.05, 0.36, 0.08, 0.09, 0.15, 0.10, 0.17)]
    tabel_item = Table(data, colWidths=lebar, repeatRows=1)
    tabel_item.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1B4F8A")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#DFE4EA")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#FAFBFC")]),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    elemen.append(tabel_item)
    elemen.append(Spacer(1, 10))

    # ---- ringkasan
    ringkas = [
        ["Subtotal", f"Rp {inv['subtotal']:,}".replace(",", ".")],
    ]
    if inv["diskon_nilai"]:
        ringkas.append(["Diskon",
                        f"- Rp {inv['diskon_nilai']:,}".replace(",", ".")])
    ringkas.append(["Dasar Pengenaan Pajak",
                    f"Rp {inv['dpp']:,}".replace(",", ".")])
    if inv["ppn"]:
        ringkas.append(["PPN", f"Rp {inv['ppn']:,}".replace(",", ".")])
    ringkas.append(["TOTAL", f"Rp {inv['total']:,}".replace(",", ".")])
    if inv["dibayar"]:
        ringkas.append(["Sudah Dibayar",
                        f"- Rp {inv['dibayar']:,}".replace(",", ".")])
        ringkas.append(["SISA TAGIHAN", f"Rp {inv['sisa']:,}".replace(",", ".")])

    tabel_ringkas = Table(ringkas, colWidths=[doc.width * 0.30, doc.width * 0.25],
                          hAlign="RIGHT")
    gaya = [
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LINEABOVE", (0, -1), (-1, -1), 0.8, colors.HexColor("#1B4F8A")),
    ]
    for i, baris in enumerate(ringkas):
        if baris[0] in ("TOTAL", "SISA TAGIHAN"):
            gaya.append(("FONTNAME", (0, i), (-1, i), "Helvetica-Bold"))
            gaya.append(("TEXTCOLOR", (0, i), (-1, i),
                         colors.HexColor("#1B4F8A")))
            gaya.append(("BACKGROUND", (0, i), (-1, i),
                         colors.HexColor("#E8F0F9")))
    tabel_ringkas.setStyle(TableStyle(gaya))
    elemen.append(tabel_ringkas)
    elemen.append(Spacer(1, 18))

    # ---- catatan & instruksi pembayaran
    if inv["catatan"]:
        elemen.append(Paragraph("CATATAN", st_label))
        elemen.append(Paragraph(inv["catatan"], st_kecil))
        elemen.append(Spacer(1, 12))

    elemen.append(Paragraph("INSTRUKSI PEMBAYARAN", st_label))
    bank_info = []
    for kb in O.daftar_kas_bank(company_id):
        if kb["tipe"] == "bank" and kb["nomor_rekening"]:
            bank_info.append(f"{kb['nama_bank'] or kb['nama']} "
                             f"{kb['nomor_rekening']} a/n {comp['nama']}")
    if bank_info:
        for b in bank_info:
            elemen.append(Paragraph(f"• {b}", st_kecil))
    else:
        elemen.append(Paragraph(
            "Pembayaran dapat dilakukan melalui transfer bank. "
            "Mohon cantumkan nomor invoice pada berita transfer.", st_kecil))

    elemen.append(Spacer(1, 16))
    elemen.append(Paragraph(
        f"Dokumen ini dihasilkan otomatis oleh {config.APP_NAME} "
        f"pada {datetime.now():%d/%m/%Y %H:%M}.", st_kecil))

    doc.build(elemen)
    return path


# ==========================================================================
# DIALOG PILIH PRODUK (baris item)
# ==========================================================================
class PanelItem(QWidget):
    """Panel input baris item yang dapat dipakai di SO dan Invoice."""

    total_berubah = Signal(int)

    def __init__(self, ctx, jenis_ppn_default: str = "Non-PKP/Tidak Dipungut",
                 parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.produk = M.daftar_produk(ctx.company_id)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        self.tabel = w.Tabel([
            ("Produk / Jasa", 300), ("Deskripsi", -1), ("Qty", 90),
            ("Satuan", 85), ("Harga Satuan", 150), ("Diskon %", 90),
            ("Jumlah", 160), ("", 40),
        ])
        self.tabel.setMinimumHeight(220)
        lay.addWidget(self.tabel)

        baris = QHBoxLayout()
        b_tambah = w.tombol("Tambah Baris", ikon="tambah")
        b_tambah.clicked.connect(lambda: self._tambah_baris())
        baris.addWidget(b_tambah)
        baris.addStretch()

        self.lbl_total = QLabel("Subtotal: Rp0")
        self.lbl_total.setStyleSheet(
            f"font-family: {theme.FONT_ANGKA}; font-size: 15px; font-weight: 700; "
            f"color: {C.PRIMARY}; background: transparent;")
        baris.addWidget(self.lbl_total)
        lay.addLayout(baris)

        self.baris_data: list[dict] = []
        self._tambah_baris()

    def _tambah_baris(self):
        self.baris_data.append({
            "product_id": None, "deskripsi": "", "qty": 1.0, "satuan": "pcs",
            "harga_satuan": 0, "diskon_persen": 0.0,
        })
        self._render()

    def _hapus_baris(self, r: int):
        if r < len(self.baris_data):
            del self.baris_data[r]
            if not self.baris_data:
                self._tambah_baris()
            else:
                self._render()

    def _render(self):
        self.tabel.setRowCount(len(self.baris_data))
        for i, b in enumerate(self.baris_data):
            cb = QComboBox()
            cb.addItem("Pilih Produk", None)
            for p in self.produk:
                label = f"{p['kode']} - {p['nama']}"
                if p["tipe"] == "barang":
                    label += f" (stok {p['stok']:g})"
                cb.addItem(label, p["id"])
            idx = cb.findData(b["product_id"])
            if idx >= 0:
                cb.setCurrentIndex(idx)
            cb.currentIndexChanged.connect(
                lambda _, r=i, c=cb: self._pilih_produk(r, c.currentData()))
            self.tabel.setCellWidget(i, 0, cb)

            e_desc = QLineEdit(b["deskripsi"])
            e_desc.textChanged.connect(
                lambda teks, r=i: self.baris_data[r].__setitem__("deskripsi", teks))
            self.tabel.setCellWidget(i, 1, e_desc)

            e_qty = QLineEdit(f"{b['qty']:g}")
            e_qty.setAlignment(Qt.AlignRight)
            e_qty.textChanged.connect(
                lambda teks, r=i: self._ubah_qty(r, teks))
            self.tabel.setCellWidget(i, 2, e_qty)

            e_sat = QLineEdit(b["satuan"])
            e_sat.textChanged.connect(
                lambda teks, r=i: self.baris_data[r].__setitem__("satuan", teks))
            self.tabel.setCellWidget(i, 3, e_sat)

            e_harga = w.InputRupiah()
            e_harga.set_nilai(b["harga_satuan"])
            e_harga.valueChanged.connect(
                lambda v, r=i: self._ubah_harga(r, v))
            self.tabel.setCellWidget(i, 4, e_harga)

            e_disk = QLineEdit(f"{b['diskon_persen']:g}" if b["diskon_persen"] else "")
            e_disk.setAlignment(Qt.AlignRight)
            e_disk.textChanged.connect(
                lambda teks, r=i: self._ubah_diskon(r, teks))
            self.tabel.setCellWidget(i, 5, e_disk)

            subtotal = self._subtotal_baris(b)
            item = QTableWidgetItem(tx.rupiah(subtotal))
            item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.tabel.setItem(i, 6, item)

            b_hapus = QPushButton("")
            b_hapus.setStyleSheet(
                f"QPushButton {{ background: transparent; border: none; "
                f"color: {C.TEXT_FAINT}; font-size: 15px; font-weight: 700; }}"
                f"QPushButton:hover {{ color: {C.DANGER}; }}")
            b_hapus.setCursor(Qt.PointingHandCursor)
            b_hapus.clicked.connect(lambda _, r=i: self._hapus_baris(r))
            self.tabel.setCellWidget(i, 7, b_hapus)

        self._update_total()

    def _pilih_produk(self, r: int, product_id):
        if r >= len(self.baris_data):
            return
        b = self.baris_data[r]
        b["product_id"] = product_id
        if product_id:
            p = M.get_produk(product_id)
            if p:
                b["harga_satuan"] = p["harga_jual"]
                b["satuan"] = p["satuan"] or "pcs"
                if not b["deskripsi"]:
                    b["deskripsi"] = p["nama"]
                widget = self.tabel.cellWidget(r, 4)
                if widget:
                    widget.blockSignals(True)
                    widget.set_nilai(p["harga_jual"])
                    widget.blockSignals(False)
                sat_widget = self.tabel.cellWidget(r, 3)
                if sat_widget:
                    sat_widget.setText(p["satuan"] or "pcs")
                desc_widget = self.tabel.cellWidget(r, 1)
                if desc_widget and not desc_widget.text():
                    desc_widget.setText(p["nama"])
        self._update_baris(r)

    def _ubah_qty(self, r: int, teks: str):
        try:
            self.baris_data[r]["qty"] = float(teks.replace(",", ".") or 0)
        except ValueError:
            self.baris_data[r]["qty"] = 0.0
        self._update_baris(r)

    def _ubah_harga(self, r: int, nilai: int):
        if r < len(self.baris_data):
            self.baris_data[r]["harga_satuan"] = int(nilai)
            self._update_baris(r)

    def _ubah_diskon(self, r: int, teks: str):
        try:
            self.baris_data[r]["diskon_persen"] = float(teks.replace(",", ".") or 0)
        except ValueError:
            self.baris_data[r]["diskon_persen"] = 0.0
        self._update_baris(r)

    def _subtotal_baris(self, b: dict) -> int:
        bruto = int(round(float(b["qty"]) * int(b["harga_satuan"])))
        potongan = int(round(bruto * float(b["diskon_persen"]) / 100))
        return max(0, bruto - potongan)

    def _update_baris(self, r: int):
        if r >= len(self.baris_data):
            return
        item = self.tabel.item(r, 6)
        if item is None:
            item = QTableWidgetItem()
            item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.tabel.setItem(r, 6, item)
        item.setText(tx.rupiah(self._subtotal_baris(self.baris_data[r])))
        self._update_total()

    def _update_total(self):
        total = sum(self._subtotal_baris(b) for b in self.baris_data)
        self.lbl_total.setText(f"Subtotal: {tx.rupiah(total)}")
        self.total_berubah.emit(total)

    def items(self) -> list[dict]:
        return [b for b in self.baris_data
                if b["product_id"] or (b["deskripsi"] and b["qty"] > 0)]

    def subtotal(self) -> int:
        return sum(self._subtotal_baris(b) for b in self.items())


# ==========================================================================
# DIALOG SALES ORDER
# ==========================================================================
class DialogSalesOrder(QDialog):
    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.setWindowTitle("Buat Sales Order")
        self.setMinimumSize(1080, 680)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 20, 22, 20)
        lay.setSpacing(12)

        j = QLabel("Sales Order Baru")
        j.setObjectName("SectionTitle")
        lay.addWidget(j)

        if ctx.beginner:
            lay.addWidget(w.HelpPanel(
                "Tentang Sales Order",
                "Sales Order adalah pesanan dari pelanggan yang belum menjadi "
                "tagihan. Setelah barang/jasa diserahkan, Anda mengubahnya menjadi "
                "Invoice.\n\n"
                "Alur: Sales Order -> Invoice -> Penerimaan Pembayaran.",
                "Dokumen pesanan bukan dasar pengakuan pendapatan. Pendapatan diakui "
                "saat invoice diterbitkan."))

        baris = QHBoxLayout()
        baris.setSpacing(11)
        baris.addWidget(w.label("Tanggal", objek="FormLabel"))
        self.inp_tanggal = kalender.pasang(QDateEdit())
        self.inp_tanggal.setDisplayFormat("dd/MM/yyyy")
        self.inp_tanggal.setDate(QDate.currentDate())
        baris.addWidget(self.inp_tanggal)

        baris.addWidget(w.label("Pelanggan", objek="FormLabel"))
        self.cmb_pelanggan = QComboBox()
        self.cmb_pelanggan.setMinimumWidth(260)
        self.cmb_pelanggan.addItem("Pelanggan Umum", None)
        for m in M.daftar_mitra(ctx.company_id, "customer"):
            self.cmb_pelanggan.addItem(f"{m['nama']}", m["id"])
        baris.addWidget(self.cmb_pelanggan)

        baris.addWidget(w.label("Jenis PPN", objek="FormLabel"))
        self.cmb_ppn = QComboBox()
        for jp in tx.PPN_JENIS:
            self.cmb_ppn.addItem(jp, jp)
        if ctx.company and ctx.company["status_pkp"]:
            self.cmb_ppn.setCurrentIndex(1)
        baris.addWidget(self.cmb_ppn, 1)
        lay.addLayout(baris)

        baris2 = QHBoxLayout()
        baris2.setSpacing(11)
        baris2.addWidget(w.label("Alamat Kirim", objek="FormLabel"))
        self.inp_alamat = QLineEdit()
        baris2.addWidget(self.inp_alamat, 1)

        baris2.addWidget(w.label("Tgl Kirim", objek="FormLabel"))
        self.inp_kirim = kalender.pasang(QDateEdit())
        self.inp_kirim.setDisplayFormat("dd/MM/yyyy")
        self.inp_kirim.setDate(QDate.currentDate().addDays(7))
        baris2.addWidget(self.inp_kirim)
        lay.addLayout(baris2)

        self.panel = PanelItem(ctx)
        lay.addWidget(self.panel, 1)

        baris3 = QHBoxLayout()
        baris3.setSpacing(11)
        baris3.addWidget(w.label("Diskon Keseluruhan (%)", objek="FormLabel"))
        self.inp_diskon = QLineEdit()
        self.inp_diskon.setMaximumWidth(90)
        self.inp_diskon.setAlignment(Qt.AlignRight)
        self.inp_diskon.textChanged.connect(self._update_ringkas)
        baris3.addWidget(self.inp_diskon)

        baris3.addWidget(w.label("Catatan", objek="FormLabel"))
        self.inp_catatan = QLineEdit()
        baris3.addWidget(self.inp_catatan, 1)
        lay.addLayout(baris3)

        self.panel.tabel.itemChanged.connect(lambda _: self._update_ringkas())
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
        bs = w.tombol("Simpan Sales Order", gaya="primary")
        bs.clicked.connect(self._simpan)
        aksi.addWidget(bs)
        lay.addLayout(aksi)

        self._update_ringkas()

    def _diskon_persen(self) -> float:
        try:
            return float(self.inp_diskon.text().replace(",", ".") or 0)
        except ValueError:
            return 0.0

    def _update_ringkas(self):
        subtotal = self.panel.subtotal()
        diskon = int(round(subtotal * self._diskon_persen() / 100))
        dpp = max(0, subtotal - diskon)
        ppn_res = tx.hitung_ppn(dpp, self.cmb_ppn.currentData())
        self.lbl_ringkas.setText(
            f"Subtotal: <b>{tx.rupiah(subtotal)}</b> &nbsp;|&nbsp; "
            f"Diskon: <b>{tx.rupiah(diskon)}</b> &nbsp;|&nbsp; "
            f"DPP: <b>{tx.rupiah(dpp)}</b> &nbsp;|&nbsp; "
            f"PPN: <b>{tx.rupiah(ppn_res.ppn)}</b> &nbsp;|&nbsp; "
            f"TOTAL: <b><font color='{C.PRIMARY}'>{tx.rupiah(dpp + ppn_res.ppn)}"
            "</font></b>")

    def _simpan(self):
        try:
            items = self.panel.items()
            if not items:
                QMessageBox.warning(self, "Belum ada item",
                                    "Tambahkan minimal satu baris produk atau jasa.")
                return
            so = S.buat_sales_order(
                self.ctx.company_id,
                self.inp_tanggal.date().toString("yyyy-MM-dd"),
                items,
                self.cmb_pelanggan.currentData(),
                diskon_persen=self._diskon_persen(),
                jenis_ppn=self.cmb_ppn.currentData(),
                alamat_kirim=self.inp_alamat.text().strip(),
                tanggal_kirim=self.inp_kirim.date().toString("yyyy-MM-dd"),
                catatan=self.inp_catatan.text().strip(),
                user_id=self.ctx.user_id, username=self.ctx.username)
            self.so_id = so
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Gagal menyimpan", str(e))


# ==========================================================================
# DIALOG INVOICE
# ==========================================================================
class DialogInvoice(QDialog):
    def __init__(self, ctx, parent=None, so_id: int = None):
        super().__init__(parent)
        self.ctx = ctx
        self.so_id = so_id
        self.invoice_id = None
        self.setWindowTitle("Buat Invoice")
        self.setMinimumSize(1080, 720)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 20, 22, 20)
        lay.setSpacing(12)

        j = QLabel("Invoice Baru")
        j.setObjectName("SectionTitle")
        lay.addWidget(j)

        if ctx.beginner:
            lay.addWidget(w.HelpPanel(
                "Tentang Invoice",
                "Invoice adalah tagihan resmi yang mengakui pendapatan. Saat "
                "invoice dibuat, aplikasi otomatis:\n\n"
                "1. Mencatat piutang pelanggan\n"
                "2. Mengakui pendapatan\n"
                "3. Menghitung PPN keluaran (bila PKP)\n"
                "4. Mengurangi stok dan mencatat HPP (untuk barang)",
                "PSAK 72 - pengakuan pendapatan. PMK 131/2024 PPN."))

        baris = QHBoxLayout()
        baris.setSpacing(11)
        baris.addWidget(w.label("Tanggal", objek="FormLabel"))
        self.inp_tanggal = kalender.pasang(QDateEdit())
        self.inp_tanggal.setDisplayFormat("dd/MM/yyyy")
        self.inp_tanggal.setDate(QDate.currentDate())
        self.inp_tanggal.dateChanged.connect(self._update_jatuh_tempo)
        baris.addWidget(self.inp_tanggal)

        baris.addWidget(w.label("Pelanggan", objek="FormLabel"))
        self.cmb_pelanggan = QComboBox()
        self.cmb_pelanggan.setMinimumWidth(260)
        self.cmb_pelanggan.addItem("Pelanggan Umum", None)
        for m in M.daftar_mitra(ctx.company_id, "customer"):
            self.cmb_pelanggan.addItem(f"{m['nama']}", m["id"])
        self.cmb_pelanggan.currentIndexChanged.connect(self._update_jatuh_tempo)
        baris.addWidget(self.cmb_pelanggan)

        baris.addWidget(w.label("Jatuh Tempo", objek="FormLabel"))
        self.inp_jatuh = kalender.pasang(QDateEdit())
        self.inp_jatuh.setDisplayFormat("dd/MM/yyyy")
        baris.addWidget(self.inp_jatuh)

        baris.addWidget(w.label("Jenis PPN", objek="FormLabel"))
        self.cmb_ppn = QComboBox()
        for jp in tx.PPN_JENIS:
            self.cmb_ppn.addItem(jp, jp)
        if ctx.company and ctx.company["status_pkp"]:
            self.cmb_ppn.setCurrentIndex(1)
        baris.addWidget(self.cmb_ppn, 1)
        lay.addLayout(baris)

        self.panel = PanelItem(ctx)
        lay.addWidget(self.panel, 1)

        baris3 = QHBoxLayout()
        baris3.setSpacing(11)
        baris3.addWidget(w.label("Diskon Keseluruhan (%)", objek="FormLabel"))
        self.inp_diskon = QLineEdit()
        self.inp_diskon.setMaximumWidth(90)
        self.inp_diskon.setAlignment(Qt.AlignRight)
        self.inp_diskon.textChanged.connect(self._update_ringkas)
        baris3.addWidget(self.inp_diskon)

        baris3.addWidget(w.label("Catatan", objek="FormLabel"))
        self.inp_catatan = QLineEdit()
        baris3.addWidget(self.inp_catatan, 1)
        lay.addLayout(baris3)

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

        self._update_jatuh_tempo()
        self._update_ringkas()
        if so_id:
            self._muat_dari_so(so_id)

    def _update_jatuh_tempo(self):
        tanggal = self.inp_tanggal.date().toPython()
        partner_id = self.cmb_pelanggan.currentData()
        termin = 30
        if partner_id:
            m = M.get_mitra(partner_id)
            if m:
                termin = int(m["termin_hari"] or 30)
                if m["alamat"]:
                    pass
        from datetime import timedelta
        self.inp_jatuh.setDate(QDate(tanggal + timedelta(days=termin)))

    def _diskon_persen(self) -> float:
        try:
            return float(self.inp_diskon.text().replace(",", ".") or 0)
        except ValueError:
            return 0.0

    def _update_ringkas(self):
        subtotal = self.panel.subtotal()
        diskon = int(round(subtotal * self._diskon_persen() / 100))
        dpp = max(0, subtotal - diskon)
        ppn_res = tx.hitung_ppn(dpp, self.cmb_ppn.currentData())
        self.lbl_ringkas.setText(
            f"Subtotal: <b>{tx.rupiah(subtotal)}</b> &nbsp;|&nbsp; "
            f"Diskon: <b>{tx.rupiah(diskon)}</b> &nbsp;|&nbsp; "
            f"DPP: <b>{tx.rupiah(dpp)}</b> &nbsp;|&nbsp; "
            f"PPN: <b>{tx.rupiah(ppn_res.ppn)}</b> &nbsp;|&nbsp; "
            f"TOTAL: <b><font color='{C.PRIMARY}'>{tx.rupiah(dpp + ppn_res.ppn)}"
            "</font></b>")

    def _muat_dari_so(self, so_id: int):
        so = M.db.q1("SELECT * FROM sales_orders WHERE id=?", (so_id,))
        if so is None:
            return
        i = self.cmb_pelanggan.findData(so["partner_id"])
        if i >= 0:
            self.cmb_pelanggan.setCurrentIndex(i)
        self.inp_catatan.setText(so["catatan"] or "")
        items = S.detail_so(so_id)
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

    def _simpan(self):
        try:
            items = self.panel.items()
            if not items:
                QMessageBox.warning(self, "Belum ada item",
                                    "Tambahkan minimal satu baris produk atau jasa.")
                return
            self.invoice_id = S.buat_invoice(
                self.ctx.company_id,
                self.inp_tanggal.date().toString("yyyy-MM-dd"),
                items,
                self.cmb_pelanggan.currentData(),
                jatuh_tempo=self.inp_jatuh.date().toString("yyyy-MM-dd"),
                diskon_persen=self._diskon_persen(),
                jenis_ppn=self.cmb_ppn.currentData(),
                so_id=self.so_id,
                catatan=self.inp_catatan.text().strip(),
                user_id=self.ctx.user_id, username=self.ctx.username)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Gagal menyimpan", str(e))


# ==========================================================================
# DIALOG PENERIMAAN PEMBAYARAN
# ==========================================================================
class DialogPenerimaan(QDialog):
    def __init__(self, ctx, parent=None, invoice_id: int = None,
                 partner_id: int = None):
        super().__init__(parent)
        self.ctx = ctx
        self.invoice_id = invoice_id
        self.partner_id = partner_id
        self.setWindowTitle("Terima Pembayaran")
        self.setMinimumSize(820, 600)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 20, 22, 20)
        lay.setSpacing(12)

        j = QLabel("Penerimaan Pembayaran Pelanggan")
        j.setObjectName("SectionTitle")
        lay.addWidget(j)

        if ctx.beginner:
            lay.addWidget(w.HelpPanel(
                "Tentang pembayaran sebagian",
                "Anda dapat menerima pembayaran sebagian. Aplikasi akan "
                "mengalokasikan jumlah yang diterima ke invoice yang Anda pilih, "
                "lalu memperbarui sisa piutang.\n\n"
                "Total alokasi tidak boleh melebihi jumlah yang diterima.",
                "PSAK 71 - penghentian pengakuan aset keuangan saat hak "
                "kontraktual berakhir."))

        baris = QHBoxLayout()
        baris.setSpacing(11)
        baris.addWidget(w.label("Tanggal", objek="FormLabel"))
        self.inp_tanggal = kalender.pasang(QDateEdit())
        self.inp_tanggal.setDisplayFormat("dd/MM/yyyy")
        self.inp_tanggal.setDate(QDate.currentDate())
        baris.addWidget(self.inp_tanggal)

        baris.addWidget(w.label("Jumlah Diterima (Rp)", objek="FormLabel"))
        self.inp_jumlah = w.InputRupiah()
        self.inp_jumlah.valueChanged.connect(self._cek_alokasi)
        baris.addWidget(self.inp_jumlah)

        baris.addWidget(w.label("Masuk ke Rekening", objek="FormLabel"))
        self.cmb_kas = QComboBox()
        for kb in O.daftar_kas_bank(ctx.company_id):
            self.cmb_kas.addItem(f"{kb['nama']}", kb["akun_buku"])
        baris.addWidget(self.cmb_kas, 1)
        lay.addLayout(baris)

        baris2 = QHBoxLayout()
        baris2.setSpacing(11)
        baris2.addWidget(w.label("Metode", objek="FormLabel"))
        self.cmb_metode = QComboBox()
        for m in ["Transfer", "Tunai", "QRIS", "Kartu", "Cek", "Virtual Account"]:
            self.cmb_metode.addItem(m, m)
        baris2.addWidget(self.cmb_metode)

        baris2.addWidget(w.label("Referensi / No. Bukti", objek="FormLabel"))
        self.inp_ref = QLineEdit()
        baris2.addWidget(self.inp_ref, 1)

        baris2.addWidget(w.label("Catatan", objek="FormLabel"))
        self.inp_catatan = QLineEdit()
        baris2.addWidget(self.inp_catatan, 1)
        lay.addLayout(baris2)

        lay.addWidget(w.label("Pilih Invoice yang Dibayar", objek="SectionTitle"))

        self.tabel = w.Tabel([
            ("", 40), ("Invoice", 175), ("Tanggal", 110), ("Jatuh Tempo", 115),
            ("Total", 155), ("Sudah Bayar", 145), ("Sisa", 155), ("Alokasi", 165),
        ])
        lay.addWidget(self.tabel, 1)

        self.checks: dict[int, QCheckBox] = {}
        self.inputs: dict[int, w.InputRupiah] = {}
        self._muat_invoice()

        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet(f"font-size: {theme.FS_BODY}px; "
                                      "font-weight: 600; background: transparent;")
        lay.addWidget(self.lbl_status)

        aksi = QHBoxLayout()
        aksi.addStretch()
        b = w.tombol("Batal")
        b.clicked.connect(self.reject)
        aksi.addWidget(b)
        bs = w.tombol("Simpan Penerimaan", gaya="primary")
        bs.clicked.connect(self._simpan)
        aksi.addWidget(bs)
        lay.addLayout(aksi)

    def _muat_invoice(self):
        cid = self.ctx.company_id
        daftar = S.daftar_invoice(cid, status="belum_lunas",
                                  partner_id=self.partner_id)
        self.tabel.setRowCount(len(daftar))
        self.checks.clear()
        self.inputs.clear()

        for i, inv in enumerate(daftar):
            chk = QCheckBox()
            chk.setChecked(inv["id"] == self.invoice_id)
            chk.stateChanged.connect(self._cek_alokasi)
            self.checks[inv["id"]] = chk
            self.tabel.setCellWidget(i, 0, chk)

            self.tabel.setItem(i, 1, QTableWidgetItem(inv["nomor"]))
            self.tabel.setItem(i, 2, QTableWidgetItem(theme.tanggal_id(inv["tanggal"])))
            self.tabel.setItem(i, 3, QTableWidgetItem(
                theme.tanggal_id(inv["jatuh_tempo"] or "")))
            for kolom, nilai in [(4, inv["total"]), (5, inv["dibayar"]),
                                 (6, inv["sisa"])]:
                item = QTableWidgetItem(tx.rupiah(nilai))
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.tabel.setItem(i, kolom, item)

            inp = w.InputRupiah()
            if inv["id"] == self.invoice_id:
                inp.set_nilai(inv["sisa"])
            inp.valueChanged.connect(self._cek_alokasi)
            self.inputs[inv["id"]] = inp
            self.tabel.setCellWidget(i, 7, inp)

        if self.invoice_id and self.invoice_id in self.inputs:
            inv = S.get_invoice(self.invoice_id)
            if inv:
                self.inp_jumlah.set_nilai(inv["sisa"])
                i = self.cmb_kas.findData("1002")
                if i >= 0:
                    self.cmb_kas.setCurrentIndex(i)

    def _total_alokasi(self) -> int:
        return sum(inp.nilai() for iid, inp in self.inputs.items()
                   if self.checks.get(iid) and self.checks[iid].isChecked())

    def _cek_alokasi(self):
        diterima = self.inp_jumlah.nilai()
        dialokasikan = self._total_alokasi()
        selisih = diterima - dialokasikan

        if diterima == 0 and dialokasikan == 0:
            self.lbl_status.setText("Masukkan jumlah pembayaran dan pilih invoice.")
            self.lbl_status.setStyleSheet(
                f"color: {C.TEXT_MUTED}; font-weight: 600; background: transparent;")
        elif selisih == 0:
            self.lbl_status.setText(
                f"Seimbang - {tx.rupiah(dialokasikan)} dialokasikan penuh.")
            self.lbl_status.setStyleSheet(
                f"color: {C.SUCCESS}; font-weight: 700; background: transparent;")
        elif selisih > 0:
            self.lbl_status.setText(
                f"Perhatian: {tx.rupiah(selisih)} belum dialokasikan ke invoice mana pun.")
            self.lbl_status.setStyleSheet(
                f"color: {C.WARNING}; font-weight: 700; background: transparent;")
        else:
            self.lbl_status.setText(
                f"Alokasi melebihi jumlah diterima sebesar "
                f"{tx.rupiah(-selisih)}.")
            self.lbl_status.setStyleSheet(
                f"color: {C.DANGER}; font-weight: 700; background: transparent;")

    def _simpan(self):
        try:
            jumlah = self.inp_jumlah.nilai()
            if jumlah <= 0:
                QMessageBox.warning(self, "Jumlah kosong",
                                    "Isi jumlah pembayaran yang diterima.")
                return

            alokasi = []
            for iid, inp in self.inputs.items():
                if self.checks.get(iid) and self.checks[iid].isChecked() and inp.nilai() > 0:
                    alokasi.append({"invoice_id": iid, "jumlah": inp.nilai()})

            if not alokasi:
                QMessageBox.warning(self, "Belum ada alokasi",
                                    "Pilih minimal satu invoice untuk dibayar.")
                return

            if self._total_alokasi() > jumlah:
                QMessageBox.warning(
                    self, "Alokasi berlebih",
                    "Total alokasi melebihi jumlah yang diterima.")
                return

            partner_id = self.partner_id
            if not partner_id and alokasi:
                inv = S.get_invoice(alokasi[0]["invoice_id"])
                if inv:
                    partner_id = inv["partner_id"]

            S.terima_pembayaran(
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


# ==========================================================================
# DIALOG NOTA KREDIT
# ==========================================================================
class DialogNotaKredit(QDialog):
    def __init__(self, ctx, parent=None, invoice_id: int = None):
        super().__init__(parent)
        self.ctx = ctx
        self.invoice_id = invoice_id
        self.setWindowTitle("Buat Nota Kredit / Retur")
        self.setMinimumWidth(620)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 22, 24, 22)
        lay.setSpacing(13)

        j = QLabel("Nota Kredit / Retur Penjualan")
        j.setObjectName("SectionTitle")
        lay.addWidget(j)

        lay.addWidget(w.HelpPanel(
            "Kapan memakai nota kredit",
            "• RETUR - pelanggan mengembalikan barang karena rusak atau tidak sesuai.\n"
            "• DISKON - Anda memberi potongan setelah invoice diterbitkan.\n"
            "• REFUND - Anda mengembalikan uang yang sudah diterima.\n\n"
            "Nota kredit mengurangi piutang pelanggan dan pendapatan usaha.",
            "PSAK 72 - pengurangan harga transaksi. Pasal 4 UU PPh "
            "pengurangan penghasilan bruto."))

        g = QGridLayout()
        g.setSpacing(12)

        g.addWidget(w.label("Tanggal", objek="FormLabel"), 0, 0)
        self.inp_tanggal = kalender.pasang(QDateEdit())
        self.inp_tanggal.setDisplayFormat("dd/MM/yyyy")
        self.inp_tanggal.setDate(QDate.currentDate())
        g.addWidget(self.inp_tanggal, 1, 0)

        g.addWidget(w.label("Tipe", objek="FormLabel"), 0, 1)
        self.cmb_tipe = QComboBox()
        self.cmb_tipe.addItem("Retur Barang", "retur")
        self.cmb_tipe.addItem("Diskon Setelah Invoice", "diskon")
        self.cmb_tipe.addItem("Refund (pengembalian dana)", "refund")
        g.addWidget(self.cmb_tipe, 1, 1)

        g.addWidget(w.label("Invoice Terkait", objek="FormLabel"), 2, 0, 1, 2)
        self.cmb_invoice = QComboBox()
        self.cmb_invoice.setMinimumWidth(420)
        for inv in S.daftar_invoice(ctx.company_id):
            if inv["status"] != "batal":
                self.cmb_invoice.addItem(
                    f"{inv['nomor']} - {inv['pelanggan']} "
                    f"({tx.rupiah(inv['total'])})", inv["id"])
        i = self.cmb_invoice.findData(invoice_id)
        if i >= 0:
            self.cmb_invoice.setCurrentIndex(i)
        g.addWidget(self.cmb_invoice, 3, 0, 1, 2)

        g.addWidget(w.label("Jumlah (Rp)", objek="FormLabel"), 4, 0)
        self.inp_jumlah = w.InputRupiah()
        g.addWidget(self.inp_jumlah, 5, 0)

        g.addWidget(w.label("Alasan", objek="FormLabel"), 4, 1)
        self.inp_alasan = QLineEdit()
        self.inp_alasan.setPlaceholderText("mis. Barang rusak 5 pcs")
        g.addWidget(self.inp_alasan, 5, 1)
        lay.addLayout(g)

        self.lbl_info = QLabel("")
        self.lbl_info.setWordWrap(True)
        theme.latar(self.lbl_info, f"background: {C.PRIMARY_SOFT}; border: 1px solid #CFE0F0; "
            f"border-radius: 8px; padding: 11px 13px; font-size: {theme.FS_SMALL}px;")
        lay.addWidget(self.lbl_info)
        self.cmb_invoice.currentIndexChanged.connect(self._update_info)
        self._update_info()

        aksi = QHBoxLayout()
        aksi.addStretch()
        b = w.tombol("Batal")
        b.clicked.connect(self.reject)
        aksi.addWidget(b)
        bs = w.tombol("Simpan Nota Kredit", gaya="primary")
        bs.clicked.connect(self._simpan)
        aksi.addWidget(bs)
        lay.addLayout(aksi)

    def _update_info(self):
        iid = self.cmb_invoice.currentData()
        if not iid:
            self.lbl_info.setText("Pilih invoice terlebih dahulu.")
            return
        inv = S.get_invoice(iid)
        if inv:
            self.lbl_info.setText(
                f"Invoice <b>{inv['nomor']}</b> · Total {tx.rupiah(inv['total'])} · "
                f"Sudah dibayar {tx.rupiah(inv['dibayar'])} · "
                f"Sisa {tx.rupiah(inv['sisa'])}")
            self.lbl_info.setTextFormat(Qt.RichText)

    def _simpan(self):
        try:
            jumlah = self.inp_jumlah.nilai()
            if jumlah <= 0:
                QMessageBox.warning(self, "Jumlah kosong", "Isi jumlah nota kredit.")
                return
            iid = self.cmb_invoice.currentData()
            if not iid:
                QMessageBox.warning(self, "Invoice kosong", "Pilih invoice terkait.")
                return
            inv = S.get_invoice(iid)
            if jumlah > inv["total"]:
                QMessageBox.warning(
                    self, "Jumlah berlebih",
                    f"Jumlah nota kredit tidak boleh melebihi total invoice "
                    f"({tx.rupiah(inv['total'])}).")
                return
            S.buat_nota_kredit(
                self.ctx.company_id,
                self.inp_tanggal.date().toString("yyyy-MM-dd"),
                jumlah, iid, inv["partner_id"], self.cmb_tipe.currentData(),
                self.inp_alasan.text().strip(),
                user_id=self.ctx.user_id, username=self.ctx.username)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Gagal menyimpan", str(e))


# ==========================================================================
# HALAMAN PENJUALAN
# ==========================================================================
class PenjualanLengkapPage(QWidget):
    pindah_halaman = Signal(str)

    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx

        luar = QVBoxLayout(self)
        luar.setContentsMargins(0, 0, 0, 0)
        luar.setSpacing(0)

        self.header = w.PageHeader(
            "Penjualan",
            "Sales order, invoice, penerimaan pembayaran, nota kredit, dan "
            "analisis umur piutang.")

        b_so = w.tombol("Sales Order", ikon="jurnal")
        b_so.clicked.connect(self._buat_so)
        self.header.tambah_aksi(b_so)

        b_inv = w.tombol("Invoice Baru", gaya="primary", ikon="tambah")
        b_inv.clicked.connect(self._buat_invoice)
        self.header.tambah_aksi(b_inv)

        b_rcv = w.tombol("Terima Pembayaran", gaya="success", ikon="simpan")
        b_rcv.clicked.connect(self._terima_pembayaran)
        self.header.tambah_aksi(b_rcv)

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
        self.tab_invoice = QWidget()
        self.tab_so = QWidget()
        self.tab_penerimaan = QWidget()
        self.tab_nota = QWidget()
        self.tab_aging = QWidget()
        self.tabs.addTab(self.tab_invoice, "Invoice")
        self.tabs.addTab(self.tab_so, "Sales Order")
        self.tabs.addTab(self.tab_penerimaan, "Penerimaan")
        self.tabs.addTab(self.tab_nota, "Nota Kredit")
        self.tabs.addTab(self.tab_aging, "Aging Piutang")
        self.tabs.currentChanged.connect(self.muat)
        self.lay.addWidget(self.tabs, 1)

        self._bangun_invoice()
        self._bangun_so()
        self._bangun_penerimaan()
        self._bangun_nota()
        self._bangun_aging()

    def _bangun_invoice(self):
        lay = QVBoxLayout(self.tab_invoice)
        lay.setContentsMargins(0, 12, 0, 0)
        lay.setSpacing(12)

        baris = QHBoxLayout()
        baris.setSpacing(10)
        self.inp_cari_inv = QLineEdit()
        self.inp_cari_inv.setPlaceholderText("Cari nomor invoice atau pelanggan…")
        self.inp_cari_inv.setMinimumWidth(280)
        self.inp_cari_inv.textChanged.connect(self.muat)
        baris.addWidget(self.inp_cari_inv)

        self.cmb_status_inv = QComboBox()
        self.cmb_status_inv.addItem("Semua Status", "")
        self.cmb_status_inv.addItem("Belum Lunas", "belum_lunas")
        self.cmb_status_inv.addItem("Terkirim", "terkirim")
        self.cmb_status_inv.addItem("Sebagian", "sebagian")
        self.cmb_status_inv.addItem("Lunas", "lunas")
        self.cmb_status_inv.currentIndexChanged.connect(self.muat)
        baris.addWidget(self.cmb_status_inv)
        baris.addStretch()
        self.lbl_inv = QLabel("")
        self.lbl_inv.setObjectName("Muted")
        baris.addWidget(self.lbl_inv)
        lay.addLayout(baris)

        self.tabel_inv = w.Tabel([
            ("Nomor", 175), ("Tanggal", 105), ("Pelanggan", 130),
            ("Jatuh Tempo", 110), ("Total", 150), ("Dibayar", 140),
            ("Sisa", 140), ("Status", 110),
        ])
        self.tabel_inv.doubleClicked.connect(self._detail_invoice)
        lay.addWidget(self.tabel_inv, 1)

        baris2 = QHBoxLayout()
        baris2.setSpacing(9)
        b1 = w.tombol("Lihat Detail", ikon="")
        b1.clicked.connect(self._detail_invoice)
        baris2.addWidget(b1)
        b2 = w.tombol("Cetak PDF", ikon="dokumen")
        b2.clicked.connect(self._pdf_invoice)
        baris2.addWidget(b2)
        b3 = w.tombol("Terima Pembayaran", gaya="success", ikon="simpan")
        b3.clicked.connect(self._bayar_invoice_terpilih)
        baris2.addWidget(b3)
        b4 = w.tombol("Nota Kredit", ikon="")
        b4.clicked.connect(self._nota_dari_invoice)
        baris2.addWidget(b4)
        b5 = w.tombol("Void", gaya="danger", ikon="nonaktif")
        b5.clicked.connect(self._void_invoice)
        baris2.addWidget(b5)
        baris2.addStretch()
        lay.addLayout(baris2)

    def _bangun_so(self):
        lay = QVBoxLayout(self.tab_so)
        lay.setContentsMargins(0, 12, 0, 0)
        lay.setSpacing(12)

        self.tabel_so = w.Tabel([
            ("Nomor", 175), ("Tanggal", 105), ("Pelanggan", 130),
            ("Tgl Kirim", 110), ("Subtotal", 150), ("PPN", 140),
            ("Total", 150), ("Status", 115),
        ])
        lay.addWidget(self.tabel_so, 1)

        baris = QHBoxLayout()
        baris.setSpacing(9)
        b1 = w.tombol("Konfirmasi SO", gaya="success", ikon="simpan")
        b1.clicked.connect(lambda: self._ubah_status_so("dikonfirmasi"))
        baris.addWidget(b1)
        b2 = w.tombol("Buat Invoice dari SO", gaya="primary", ikon="")
        b2.clicked.connect(self._invoice_dari_so)
        baris.addWidget(b2)
        b3 = w.tombol("Batalkan SO", gaya="danger", ikon="nonaktif")
        b3.clicked.connect(lambda: self._ubah_status_so("batal"))
        baris.addWidget(b3)
        baris.addStretch()
        self.lbl_so = QLabel("")
        self.lbl_so.setObjectName("Muted")
        baris.addWidget(self.lbl_so)
        lay.addLayout(baris)

    def _bangun_penerimaan(self):
        lay = QVBoxLayout(self.tab_penerimaan)
        lay.setContentsMargins(0, 12, 0, 0)
        lay.setSpacing(12)

        self.tabel_rcv = w.Tabel([
            ("Nomor", 175), ("Tanggal", 110), ("Pelanggan", 130),
            ("Metode", 130), ("Jumlah", 165), ("Referensi", 175), ("Status", 105),
        ])
        self.tabel_rcv.doubleClicked.connect(self._detail_penerimaan)
        lay.addWidget(self.tabel_rcv, 1)

        baris = QHBoxLayout()
        baris.setSpacing(9)
        b1 = w.tombol("Lihat Alokasi", ikon="")
        b1.clicked.connect(self._detail_penerimaan)
        baris.addWidget(b1)
        b2 = w.tombol("Void Penerimaan", gaya="danger", ikon="nonaktif")
        b2.clicked.connect(self._void_penerimaan)
        baris.addWidget(b2)
        baris.addStretch()
        self.lbl_rcv = QLabel("")
        self.lbl_rcv.setObjectName("Muted")
        baris.addWidget(self.lbl_rcv)
        lay.addLayout(baris)

    def _bangun_nota(self):
        lay = QVBoxLayout(self.tab_nota)
        lay.setContentsMargins(0, 12, 0, 0)
        lay.setSpacing(12)

        self.tabel_nota = w.Tabel([
            ("Nomor", 175), ("Tanggal", 110), ("Pelanggan", 130),
            ("Tipe", 120), ("Jumlah", 165), ("Alasan", 280), ("Status", 105),
        ])
        lay.addWidget(self.tabel_nota, 1)

        baris = QHBoxLayout()
        b = w.tombol("Buat Nota Kredit", gaya="primary", ikon="tambah")
        b.clicked.connect(self._buat_nota)
        baris.addWidget(b)
        baris.addStretch()
        self.lbl_nota = QLabel("")
        self.lbl_nota.setObjectName("Muted")
        baris.addWidget(self.lbl_nota)
        lay.addLayout(baris)

    def _bangun_aging(self):
        lay = QVBoxLayout(self.tab_aging)
        lay.setContentsMargins(0, 12, 0, 0)
        lay.setSpacing(12)

        self.panel_aging = QWidget()
        self.panel_aging_lay = QVBoxLayout(self.panel_aging)
        self.panel_aging_lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.panel_aging)

        self.tabel_aging = w.Tabel([
            ("Pelanggan", 130), ("Jumlah Invoice", 130),
            ("Belum JT", 145), ("1-30 hari", 140), ("31-60 hari", 140),
            ("61-90 hari", 140), ("di atas 90", 145), ("Total", 155),
        ])
        lay.addWidget(self.tabel_aging, 1)

        baris = QHBoxLayout()
        b = w.tombol("Buat Pengingat Penagihan", gaya="primary", ikon="peringatan")
        b.clicked.connect(self._buat_pengingat)
        baris.addWidget(b)
        b2 = w.tombol("Ekspor Daftar", ikon="laporan")
        b2.clicked.connect(self._ekspor_aging)
        baris.addWidget(b2)
        baris.addStretch()
        self.lbl_aging = QLabel("")
        self.lbl_aging.setObjectName("Muted")
        baris.addWidget(self.lbl_aging)
        lay.addLayout(baris)

    # ------------------------------------------------------------------
    def muat(self):
        cid = self.ctx.company_id
        if not cid:
            return
        idx = self.tabs.currentIndex()
        if idx == 0:
            self._muat_invoice()
        elif idx == 1:
            self._muat_so()
        elif idx == 2:
            self._muat_penerimaan()
        elif idx == 3:
            self._muat_nota()
        else:
            self._muat_aging()

    def _muat_invoice(self):
        cid = self.ctx.company_id
        data = S.daftar_invoice(cid, self.ctx.tahun,
                                self.cmb_status_inv.currentData(),
                                cari=self.inp_cari_inv.text().strip())
        baris, warna = [], {}
        total_sisa = 0
        hari_ini = datetime.now().date()
        for i, inv in enumerate(data):
            idx = len(baris)
            total_sisa += inv["sisa"]
            baris.append([
                inv["nomor"], theme.tanggal_id(inv["tanggal"]), inv["pelanggan"],
                theme.tanggal_id(inv["jatuh_tempo"] or ""),
                tx.rupiah(inv["total"]), tx.rupiah(inv["dibayar"]),
                tx.rupiah(inv["sisa"]),
                {"terkirim": "Terkirim", "sebagian": "Sebagian",
                 "lunas": "Lunas", "batal": "Batal"}.get(inv["status"], inv["status"]),
            ])
            if inv["status"] == "lunas":
                warna[idx] = C.SUCCESS
            elif inv["status"] == "batal":
                warna[idx] = C.TEXT_FAINT
            else:
                try:
                    jt = datetime.fromisoformat(
                        (inv["jatuh_tempo"] or inv["tanggal"])[:10]).date()
                    if jt < hari_ini:
                        warna[idx] = C.DANGER
                    elif (jt - hari_ini).days <= 7:
                        warna[idx] = C.WARNING
                except ValueError:
                    pass
        self.tabel_inv.isi(baris, warna_baris=warna, align_kanan={4, 5, 6})
        self.lbl_inv.setText(f"{len(data)} invoice · total piutang "
                             f"{tx.rupiah(total_sisa)}")

    def _muat_so(self):
        cid = self.ctx.company_id
        data = S.daftar_sales_order(cid, self.ctx.tahun)
        baris, warna = [], {}
        for i, so in enumerate(data):
            idx = len(baris)
            baris.append([
                so["nomor"], theme.tanggal_id(so["tanggal"]), so["pelanggan"],
                theme.tanggal_id(so["tanggal_kirim"] or ""),
                tx.rupiah(so["subtotal"]), tx.rupiah(so["ppn"]),
                tx.rupiah(so["total"]),
                {"draft": "Draft", "dikonfirmasi": "Dikonfirmasi",
                 "selesai": "Selesai", "batal": "Batal"}.get(so["status"],
                                                              so["status"]),
            ])
            if so["status"] == "selesai":
                warna[idx] = C.SUCCESS
            elif so["status"] == "batal":
                warna[idx] = C.TEXT_FAINT
        self.tabel_so.isi(baris, warna_baris=warna, align_kanan={4, 5, 6})
        self.lbl_so.setText(f"{len(data)} sales order")

    def _muat_penerimaan(self):
        cid = self.ctx.company_id
        data = S.daftar_penerimaan(cid, self.ctx.tahun)
        baris, warna = [], {}
        total = 0
        for i, r in enumerate(data):
            idx = len(baris)
            total += r["jumlah"] if r["status"] == "aktif" else 0
            baris.append([
                r["nomor"], theme.tanggal_id(r["tanggal"]), r["pelanggan"],
                r["metode"], tx.rupiah(r["jumlah"]), r["referensi"],
                "Aktif" if r["status"] == "aktif" else "Void",
            ])
            if r["status"] == "void":
                warna[idx] = C.TEXT_FAINT
        self.tabel_rcv.isi(baris, warna_baris=warna, align_kanan={4})
        self.lbl_rcv.setText(f"{len(data)} penerimaan · total "
                             f"{tx.rupiah(total)}")

    def _muat_nota(self):
        cid = self.ctx.company_id
        data = S.daftar_nota_kredit(cid, self.ctx.tahun)
        baris, warna = [], {}
        for i, n in enumerate(data):
            idx = len(baris)
            baris.append([
                n["nomor"], theme.tanggal_id(n["tanggal"]), n["pelanggan"],
                {"retur": "Retur", "diskon": "Diskon",
                 "refund": "Refund"}.get(n["tipe"], n["tipe"]),
                tx.rupiah(n["jumlah"]), n["alasan"],
                "Aktif" if n["status"] == "aktif" else "Void",
            ])
            if n["status"] == "void":
                warna[idx] = C.TEXT_FAINT
        self.tabel_nota.isi(baris, warna_baris=warna, align_kanan={4})
        self.lbl_nota.setText(f"{len(data)} nota kredit")

    def _muat_aging(self):
        while self.panel_aging_lay.count():
            it = self.panel_aging_lay.takeAt(0)
            wdg = it.widget()
            if wdg is not None:
                wdg.setParent(None)
                wdg.deleteLater()

        cid = self.ctx.company_id
        ag = S.aging_piutang(cid)

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
        self.panel_aging_lay.addWidget(kartu)

        if ag["bermasalah"]:
            total_brm = sum(r["sisa"] for r in ag["bermasalah"])
            self.panel_aging_lay.addWidget(w.InfoBanner(
                f"{len(ag['bermasalah'])} invoice sudah melewati 90 hari dengan "
                f"total {tx.rupiah(total_brm)}. Piutang berumur di atas 90 hari "
                "berisiko tinggi tidak tertagih - pertimbangkan penagihan intensif "
                "atau penghapusan sesuai ketentuan fiskal.",
                "danger", "Piutang bermasalah"))

        baris, warna = [], {}
        for p in ag["per_pelanggan"]:
            idx = len(baris)
            baris.append([
                p["pelanggan"], str(p["jumlah_invoice"]),
                tx.rupiah(p["Belum Jatuh Tempo"]), tx.rupiah(p["1-30 hari"]),
                tx.rupiah(p["31-60 hari"]), tx.rupiah(p["61-90 hari"]),
                tx.rupiah(p["Di atas 90 hari"]), tx.rupiah(p["total"]),
            ])
            if p["Di atas 90 hari"] > 0:
                warna[idx] = C.DANGER
            elif p["61-90 hari"] > 0:
                warna[idx] = C.WARNING
        self.tabel_aging.isi(baris, warna_baris=warna, align_kanan={1, 2, 3, 4, 5, 6, 7})
        self.lbl_aging.setText(f"{len(ag['per_pelanggan'])} pelanggan · total "
                               f"piutang {tx.rupiah(ag['total'])}")

    # ------------------------------------------------------------------
    def _buat_so(self):
        if not self.ctx.company_id:
            QMessageBox.information(self, "Belum ada perusahaan",
                                    "Buat profil perusahaan terlebih dahulu.")
            return
        d = DialogSalesOrder(self.ctx, self)
        if d.exec():
            self.tabs.setCurrentIndex(1)
            self.muat()

    def _buat_invoice(self):
        if not self.ctx.company_id:
            QMessageBox.information(self, "Belum ada perusahaan",
                                    "Buat profil perusahaan terlebih dahulu.")
            return
        if not M.daftar_produk(self.ctx.company_id):
            if QMessageBox.question(
                    self, "Belum ada produk",
                    "Belum ada produk atau jasa terdaftar.\n\n"
                    "Anda tetap dapat membuat invoice dengan deskripsi manual.\n"
                    "Ingin mendaftarkan produk terlebih dahulu?",
                    QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
                self.pindah_halaman.emit("produk")
                return
        d = DialogInvoice(self.ctx, self)
        if d.exec():
            self.muat()

    def _terima_pembayaran(self):
        if not self.ctx.company_id:
            w.belum_ada_perusahaan(self, "terima pembayaran")
            return
        d = DialogPenerimaan(self.ctx, self)
        if d.exec():
            self.muat()

    def _buat_nota(self):
        d = DialogNotaKredit(self.ctx, self)
        if d.exec():
            self.muat()

    def _invoice_terpilih(self):
        r = self.tabel_inv.baris_terpilih()
        if r is None:
            return None
        data = S.daftar_invoice(self.ctx.company_id, self.ctx.tahun,
                                self.cmb_status_inv.currentData(),
                                cari=self.inp_cari_inv.text().strip())
        return data[r] if r < len(data) else None

    def _detail_invoice(self):
        inv = self._invoice_terpilih()
        if inv is None:
            return
        DialogDetailInvoice(self.ctx, inv["id"], self).exec()

    def _pdf_invoice(self):
        inv = self._invoice_terpilih()
        if inv is None:
            QMessageBox.information(self, "Belum dipilih", "Pilih satu invoice.")
            return
        config.ensure_dirs()
        saran = os.path.join(config.EXPORT_DIR,
                             f"Invoice_{inv['nomor'].replace('/', '-')}.pdf")
        path, _ = QFileDialog.getSaveFileName(
            self, "Simpan Invoice PDF", saran, "Berkas PDF (*.pdf)")
        if not path:
            return
        try:
            buat_pdf_invoice(self.ctx.company_id, inv["id"], path)
            if QMessageBox.question(
                    self, "PDF dibuat",
                    f"Invoice berhasil disimpan:\n{path}\n\nBuka berkasnya?",
                    QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
                QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        except Exception as e:
            QMessageBox.critical(self, "Gagal membuat PDF", str(e))

    def _bayar_invoice_terpilih(self):
        inv = self._invoice_terpilih()
        if inv is None:
            QMessageBox.information(self, "Belum dipilih", "Pilih satu invoice.")
            return
        if inv["status"] == "lunas":
            QMessageBox.information(self, "Sudah lunas", "Invoice ini sudah lunas.")
            return
        d = DialogPenerimaan(self.ctx, self, inv["id"], inv["partner_id"])
        if d.exec():
            self.muat()

    def _nota_dari_invoice(self):
        inv = self._invoice_terpilih()
        if inv is None:
            QMessageBox.information(self, "Belum dipilih", "Pilih satu invoice.")
            return
        d = DialogNotaKredit(self.ctx, self, inv["id"])
        if d.exec():
            self.muat()

    def _void_invoice(self):
        inv = self._invoice_terpilih()
        if inv is None:
            QMessageBox.information(self, "Belum dipilih", "Pilih satu invoice.")
            return
        if inv["dibayar"] > 0:
            QMessageBox.warning(
                self, "Tidak dapat di-void",
                "Invoice ini sudah memiliki pembayaran. Batalkan pembayarannya "
                "terlebih dahulu.")
            return
        if QMessageBox.question(
                self, "Konfirmasi Void",
                f"Void invoice {inv['nomor']}?\n\n"
                "Tindakan ini akan:\n"
                "• Membatalkan jurnal invoice\n"
                "• Mengembalikan stok barang\n"
                "• Memindahkan data ke keranjang sampah\n\n"
                "Lanjutkan?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No) != QMessageBox.Yes:
            return
        try:
            S.hapus_invoice(inv["id"], self.ctx.username, self.ctx.user_id)
            self.muat()
        except Exception as e:
            QMessageBox.critical(self, "Gagal void", str(e))

    def _so_terpilih(self):
        r = self.tabel_so.baris_terpilih()
        if r is None:
            return None
        data = S.daftar_sales_order(self.ctx.company_id, self.ctx.tahun)
        return data[r] if r < len(data) else None

    def _ubah_status_so(self, status: str):
        so = self._so_terpilih()
        if so is None:
            QMessageBox.information(self, "Belum dipilih", "Pilih satu sales order.")
            return
        try:
            S.ubah_status_so(so["id"], status)
            self.muat()
        except Exception as e:
            QMessageBox.critical(self, "Gagal", str(e))

    def _invoice_dari_so(self):
        so = self._so_terpilih()
        if so is None:
            QMessageBox.information(self, "Belum dipilih", "Pilih satu sales order.")
            return
        if so["status"] == "batal":
            QMessageBox.warning(self, "SO dibatalkan",
                                "Sales order yang dibatalkan tidak dapat diinvoice.")
            return
        d = DialogInvoice(self.ctx, self, so_id=so["id"])
        if d.exec():
            self.tabs.setCurrentIndex(0)
            self.muat()

    def _penerimaan_terpilih(self):
        r = self.tabel_rcv.baris_terpilih()
        if r is None:
            return None
        data = S.daftar_penerimaan(self.ctx.company_id, self.ctx.tahun)
        return data[r] if r < len(data) else None

    def _detail_penerimaan(self):
        rcv = self._penerimaan_terpilih()
        if rcv is None:
            return
        alokasi = S.alokasi_penerimaan(rcv["id"])

        dlg = QDialog(self)
        dlg.setWindowTitle(f"Alokasi Penerimaan {rcv['nomor']}")
        dlg.setMinimumSize(780, 460)
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(22, 20, 22, 20)
        lay.setSpacing(12)

        j = QLabel(f"{rcv['nomor']} · {theme.tanggal_id(rcv['tanggal'])}")
        j.setObjectName("SectionTitle")
        lay.addWidget(j)

        kartu = w.Card()
        kl = kartu.body()
        b = QHBoxLayout()
        b.setSpacing(28)
        b.addWidget(w.MiniStat("Pelanggan", rcv["pelanggan"]))
        b.addWidget(w.MiniStat("Jumlah Diterima", tx.rupiah(rcv["jumlah"])))
        b.addWidget(w.MiniStat("Metode", rcv["metode"]))
        b.addWidget(w.MiniStat("Referensi", rcv["referensi"] or ""))
        b.addStretch()
        kl.addLayout(b)
        lay.addWidget(kartu)

        t = w.Tabel([("Invoice", 190), ("Jatuh Tempo", 120), ("Total Invoice", 165),
                     ("Dialokasikan", 165)])
        t.isi([[a["invoice_nomor"], theme.tanggal_id(a["jatuh_tempo"] or ""),
                tx.rupiah(a["total"]), tx.rupiah(a["jumlah"])] for a in alokasi],
              align_kanan={2, 3})
        t.setMinimumHeight(220)
        lay.addWidget(t)

        bt = w.tombol("Tutup", gaya="primary")
        bt.clicked.connect(dlg.accept)
        bl = QHBoxLayout()
        bl.addStretch()
        bl.addWidget(bt)
        lay.addLayout(bl)
        dlg.exec()

    def _void_penerimaan(self):
        rcv = self._penerimaan_terpilih()
        if rcv is None:
            QMessageBox.information(self, "Belum dipilih", "Pilih satu penerimaan.")
            return
        if rcv["status"] == "void":
            QMessageBox.information(self, "Sudah void",
                                    "Penerimaan ini sudah dibatalkan.")
            return
        if QMessageBox.question(
                self, "Konfirmasi Void",
                f"Void penerimaan {rcv['nomor']}?\n\n"
                "Status invoice terkait akan dikembalikan ke belum lunas.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No) != QMessageBox.Yes:
            return
        try:
            S.void_penerimaan(rcv["id"], self.ctx.username, self.ctx.user_id)
            self.muat()
        except Exception as e:
            QMessageBox.critical(self, "Gagal void", str(e))

    def _buat_pengingat(self):
        try:
            jumlah = O.buat_reminder_dari_piutang(self.ctx.company_id, 30)
            if jumlah:
                QMessageBox.information(
                    self, "Pengingat dibuat",
                    f"{jumlah} pengingat penagihan dibuat untuk invoice yang "
                    "jatuh tempo dalam 30 hari ke depan.\n\n"
                    "Lihat di menu Pengaturan -> Pengingat.")
            else:
                QMessageBox.information(
                    self, "Tidak ada pengingat baru",
                    "Semua invoice yang jatuh tempo sudah memiliki pengingat.")
        except Exception as e:
            QMessageBox.critical(self, "Gagal membuat pengingat", str(e))

    def _ekspor_aging(self):
        cid = self.ctx.company_id
        ag = S.aging_piutang(cid)
        config.ensure_dirs()
        path, _ = QFileDialog.getSaveFileName(
            self, "Ekspor Aging Piutang",
            str(config.EXPORT_DIR / f"Aging_Piutang_{datetime.now():%Y%m%d}.xlsx"),
            "Berkas Excel (*.xlsx)")
        if not path:
            return
        try:
            from .laporan import ekspor_excel
            data = [
                ("Ringkasan Umur", [["Kelompok", "Jumlah (Rp)"]] +
                 [[k, v] for k, v in ag["kelompok"].items()] +
                 [["TOTAL", ag["total"]]]),
                ("Per Pelanggan",
                 [["Pelanggan", "Jumlah Invoice", "Belum JT", "1-30", "31-60",
                   "61-90", ">90", "Total"]] +
                 [[p["pelanggan"], p["jumlah_invoice"], p["Belum Jatuh Tempo"],
                   p["1-30 hari"], p["31-60 hari"], p["61-90 hari"],
                   p["Di atas 90 hari"], p["total"]] for p in ag["per_pelanggan"]]),
                ("Rincian Invoice",
                 [["Invoice", "Pelanggan", "Tanggal", "Jatuh Tempo", "Total",
                   "Dibayar", "Sisa", "Umur (hari)", "Kelompok"]] +
                 [[r["nomor"], r["pelanggan"], r["tanggal"], r["jatuh_tempo"],
                   r["total"], r["dibayar"], r["sisa"], r["umur_hari"],
                   r["kelompok"]] for r in ag["rincian"]]),
            ]
            comp = M.services.get_company(cid)
            ekspor_excel(comp["nama"], data, path)
            if QMessageBox.question(
                    self, "Ekspor selesai",
                    f"Data disimpan:\n{path}\n\nBuka foldernya?",
                    QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
                QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.dirname(path)))
        except Exception as e:
            QMessageBox.critical(self, "Gagal mengekspor", str(e))


# ==========================================================================
# DIALOG DETAIL INVOICE
# ==========================================================================
class DialogDetailInvoice(QDialog):
    def __init__(self, ctx, invoice_id: int, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.invoice_id = invoice_id
        self.setWindowTitle("Detail Invoice")
        self.setMinimumSize(980, 680)

        inv = S.get_invoice(invoice_id)
        items = S.detail_invoice(invoice_id)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 20, 22, 20)
        lay.setSpacing(12)

        j = QLabel(f"Invoice {inv['nomor']}")
        j.setObjectName("SectionTitle")
        lay.addWidget(j)

        kartu = w.Card()
        kl = kartu.body()
        grid = QGridLayout()
        grid.setSpacing(14)
        info = [
            ("Pelanggan", inv["pelanggan"]),
            ("NPWP/NIK", inv["npwp_nik"] or ""),
            ("Tanggal", theme.tanggal_id(inv["tanggal"])),
            ("Jatuh Tempo", theme.tanggal_id(inv["jatuh_tempo"] or "")),
            ("Status", {"terkirim": "Terkirim", "sebagian": "Sebagian",
                        "lunas": "Lunas", "batal": "Batal"}.get(inv["status"],
                                                                 inv["status"])),
            ("Jenis PPN", inv["jenis_ppn"]),
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

        t = w.Tabel([("Produk/Jasa", -1), ("Qty", 85), ("Satuan", 85),
                     ("Harga Satuan", 150), ("Diskon", 110), ("Jumlah", 160),
                     ("HPP", 150)])
        t.isi([[it["deskripsi"] or it["produk_nama"] or "", f"{it['qty']:g}",
                it["satuan"] or "", tx.rupiah(it["harga_satuan"]),
                f"{it['diskon_persen']:g}%" if it["diskon_persen"]
                else tx.rupiah(it["diskon_nilai"]),
                tx.rupiah(it["subtotal"]), tx.rupiah(it["hpp"])]
               for it in items],
              align_kanan={1, 3, 4, 5, 6})
        t.setMinimumHeight(240)
        lay.addWidget(t)

        ringkas = w.Card()
        rl = ringkas.body()
        b = QHBoxLayout()
        b.setSpacing(28)
        b.addWidget(w.MiniStat("Subtotal", tx.rupiah(inv["subtotal"])))
        b.addWidget(w.MiniStat("Diskon", tx.rupiah(inv["diskon_nilai"])))
        b.addWidget(w.MiniStat("DPP", tx.rupiah(inv["dpp"])))
        b.addWidget(w.MiniStat("PPN", tx.rupiah(inv["ppn"])))
        b.addWidget(w.MiniStat("Total", tx.rupiah(inv["total"]), C.PRIMARY))
        b.addWidget(w.MiniStat("Dibayar", tx.rupiah(inv["dibayar"]), C.SUCCESS))
        b.addWidget(w.MiniStat("Sisa", tx.rupiah(inv["sisa"]),
                               C.DANGER if inv["sisa"] else C.SUCCESS))
        b.addStretch()
        rl.addLayout(b)
        lay.addWidget(ringkas)

        # lampiran
        docs = O.daftar_dokumen(ctx.company_id, "invoices", invoice_id)
        if docs:
            lay.addWidget(w.label(f"Lampiran ({len(docs)} berkas)",
                                  objek="SectionTitle"))
            t2 = w.Tabel([("Nama Berkas", -1), ("Tipe", 130), ("Versi", 85),
                          ("Diunggah", 165)])
            t2.isi([[d["nama_berkas"], d["tipe"] or "", str(d["versi"]),
                     d["created_at"][:16]] for d in docs])
            t2.setMinimumHeight(120)
            lay.addWidget(t2)

        aksi = QHBoxLayout()
        b_lampir = w.tombol("Lampirkan Dokumen", ikon="dokumen")
        b_lampir.clicked.connect(self._lampirkan)
        aksi.addWidget(b_lampir)

        b_pdf = w.tombol("Cetak PDF", ikon="dokumen")
        b_pdf.clicked.connect(self._pdf)
        aksi.addWidget(b_pdf)
        aksi.addStretch()

        b_tutup = w.tombol("Tutup", gaya="primary")
        b_tutup.clicked.connect(self.accept)
        aksi.addWidget(b_tutup)
        lay.addLayout(aksi)

    def _lampirkan(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Pilih Berkas", "", "Semua Berkas (*)")
        if not path:
            return
        try:
            O.lampirkan_dokumen(self.ctx.company_id, "invoices", self.invoice_id,
                                path, "invoice", "", self.ctx.username)
            QMessageBox.information(self, "Berhasil", "Dokumen dilampirkan.")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Gagal melampirkan", str(e))

    def _pdf(self):
        config.ensure_dirs()
        inv = S.get_invoice(self.invoice_id)
        saran = os.path.join(config.EXPORT_DIR,
                             f"Invoice_{inv['nomor'].replace('/', '-')}.pdf")
        path, _ = QFileDialog.getSaveFileName(
            self, "Simpan Invoice PDF", saran, "Berkas PDF (*.pdf)")
        if not path:
            return
        try:
            buat_pdf_invoice(self.ctx.company_id, self.invoice_id, path)
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        except Exception as e:
            QMessageBox.critical(self, "Gagal membuat PDF", str(e))
