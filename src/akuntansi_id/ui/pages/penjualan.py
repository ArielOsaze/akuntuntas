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
    QPushButton, QDialog, QGridLayout, QCheckBox,
    QTableWidgetItem, QFileDialog,
)

from ... import config, services, modules as M, modules_sales as S, modules_ops as O
from ...core import tax_engine as tx
from .. import ekspor_cetak as EC
from .. import theme, widgets as w
from .. import kalender
from ..theme import C
from .. import popup


# ==========================================================================
# GENERATOR PDF INVOICE
# ==========================================================================
def buat_pdf_invoice(company_id: int, invoice_id: int, path: str) -> str:
    """Hasilkan berkas PDF invoice siap kirim ke pelanggan."""
    inv = S.get_invoice(invoice_id)
    if inv is None:
        raise ValueError("Invoice tidak ditemukan.")

    comp = services.get_company(company_id)
    items = S.detail_invoice(invoice_id)
    comp_nama = comp["nama"] if comp else ""

    # Identitas dan kode verifikasi memakai jalur yang sama dengan laporan
    # A4, sehingga tanda air, pengesahan, dan segel invoice ikut pengaturan
    # dokumen di halaman Pengaturan.
    baris_kode = [["Deskripsi", "Qty", "Satuan", "Harga", "Jumlah"]]
    for it in items:
        baris_kode.append([it["deskripsi"] or (it["produk_nama"] or ""),
                           it["qty"], it["satuan"] or "", it["harga_satuan"],
                           it["subtotal"]])
    baris_kode.append(["TOTAL", "", "", "", inv["total"]])
    identitas = EC.identitas_dokumen(
        f"Invoice {inv['nomor']}",
        " ".join(filter(None, [inv["pelanggan"], inv["tanggal"]])),
        [("Rincian Invoice", baris_kode)], comp_nama)

    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.units import mm
        from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                        Paragraph, Spacer, Image, KeepTogether)
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_RIGHT
        from reportlab.platypus.flowables import Flowable
        from reportlab.pdfgen import canvas as pdfcanvas
        from reportlab.lib.utils import ImageReader
        from io import BytesIO
    except ImportError:
        raise RuntimeError("Modul reportlab belum terpasang.")

    from ... import fonts as font_app
    huruf = font_app.pasang_reportlab()
    from xml.sax.saxutils import escape as _esc

    # Palet dokumen sama dengan laporan A4: tinta hangat dan garis tipis.
    # Seluruh teks memakai tinta atau abu redup; warna hanya dipakai segel
    # verifikasi, agar dokumen terbaca sebagai surat resmi.
    TINTA = "#1D2628"
    MUTED = "#55605E"
    GARIS = "#E3DCCF"
    KEPALA = "#F3EDE4"
    TOTAL_BG = "#F6F1E7"
    BELANG = "#FCFAF5"

    styles = getSampleStyleSheet()
    st_normal = ParagraphStyle("N", parent=styles["Normal"],
                               fontName=huruf["regular"], fontSize=9,
                               leading=13, textColor=colors.HexColor(TINTA))
    st_kecil = ParagraphStyle("K", parent=styles["Normal"],
                              fontName=huruf["regular"], fontSize=7.8,
                              leading=10.8, textColor=colors.HexColor(MUTED))
    st_perusahaan = ParagraphStyle("P", parent=styles["Normal"],
                                   fontName=huruf["serif_bold"], fontSize=14,
                                   leading=17, textColor=colors.HexColor(TINTA))
    st_judul = ParagraphStyle("J", parent=styles["Title"],
                              fontName=huruf["serif_bold"], fontSize=28,
                              leading=30, textColor=colors.HexColor(TINTA),
                              spaceAfter=0)
    st_label = ParagraphStyle("L", parent=styles["Normal"],
                              fontName=huruf["semibold"], fontSize=8.6,
                              leading=11.5, textColor=colors.HexColor(TINTA),
                              spaceAfter=3)

    # Sel tabel memakai Paragraph agar deskripsi panjang terlipat rapi
    # dan tidak menimpa kolom sebelahnya.
    gaya_sel = {}
    for nama_gaya, ketebalan, warna, rata in (
            ("kiri", "regular", TINTA, 0),
            ("kanan", "regular", TINTA, TA_RIGHT),
            ("tengah", "regular", TINTA, TA_CENTER),
            ("tebal", "semibold", TINTA, 0),
            ("kepala", "semibold", TINTA, 0),
            ("kepala_kanan", "semibold", TINTA, TA_RIGHT),
            ("kepala_tengah", "semibold", TINTA, TA_CENTER)):
        gaya_sel[nama_gaya] = ParagraphStyle(
            f"Sel-{nama_gaya}", parent=st_normal, fontSize=8, leading=10.6,
            fontName=huruf[ketebalan], textColor=colors.HexColor(warna),
            alignment=rata, spaceAfter=0)

    def sel(nilai, gaya="kiri") -> Paragraph:
        teks = _esc("" if nilai is None else str(nilai))
        return Paragraph(teks.replace("\n", "<br/>"), gaya_sel[gaya])

    def teks(nilai) -> str:
        return _esc("" if nilai is None else str(nilai)).replace("\n", "<br/>")

    # Kaki halaman baru dapat ditulis setelah seluruh halaman diketahui,
    # sehingga nomor "dari" selalu tepat pada invoice berhalaman banyak.
    class NumberedCanvas(pdfcanvas.Canvas):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._states = []

        def showPage(self):
            self._states.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            total = len(self._states)
            for state in self._states:
                self.__dict__.update(state)
                self._air()
                self._kepala()
                self._kaki(total)
                pdfcanvas.Canvas.showPage(self)
            pdfcanvas.Canvas.save(self)

        def _kepala(self):
            """Kepala ringkas pada halaman lanjutan agar dokumen tetap jelas."""
            if self._pageNumber <= 1:
                return
            self.saveState()
            self.setFont(huruf["semibold"], 7.6)
            self.setFillColor(colors.HexColor(MUTED))
            self.drawString(18 * mm, A4[1] - 11 * mm, comp_nama)
            self.drawRightString(A4[0] - 18 * mm, A4[1] - 11 * mm,
                                 f"Invoice {inv['nomor']} · lanjutan")
            self.setStrokeColor(colors.HexColor(GARIS))
            self.setLineWidth(0.5)
            self.line(18 * mm, A4[1] - 13 * mm,
                      A4[0] - 18 * mm, A4[1] - 13 * mm)
            self.restoreState()

        def _air(self):
            """Tanda air diagonal yang sama dengan laporan A4."""
            if not identitas.get("air_aktif"):
                return
            teks_air = str(identitas.get("air") or "").strip().upper()
            if not teks_air:
                return
            self.saveState()
            self.setFillColor(colors.HexColor(TINTA))
            self.setFillAlpha(min(0.22, max(0.02,
                                 float(identitas.get("air_pekat") or 8)
                                 / 100.0)))
            ukuran = 80
            from reportlab.pdfbase.pdfmetrics import stringWidth
            while (ukuran > 16 and stringWidth(teks_air, huruf["serif_semibold"],
                                               ukuran) > A4[0] * 0.84):
                ukuran -= 2
            self.setFont(huruf["serif_semibold"], ukuran)
            jalur = self.beginPath()
            jalur.rect(18 * mm, 18 * mm, A4[0] - 36 * mm, A4[1] - 40 * mm)
            self.clipPath(jalur, stroke=0, fill=0)
            self.translate(A4[0] / 2, A4[1] / 2 - 8 * mm)
            self.rotate(32)
            self.drawCentredString(0, 0, teks_air)
            self.restoreState()

        def _kaki(self, total):
            self.saveState()
            self.setStrokeColor(colors.HexColor(GARIS))
            self.setLineWidth(0.6)
            self.line(18 * mm, 13 * mm, A4[0] - 18 * mm, 13 * mm)
            self.setFont(huruf["regular"], 7.4)
            self.setFillColor(colors.HexColor(MUTED))
            self.drawString(18 * mm, 8.8 * mm, inv["nomor"])
            if identitas.get("kode"):
                self.setFont(huruf["semibold"], 7.2)
                self.setFillColor(colors.HexColor(TINTA))
                self.drawCentredString(A4[0] / 2, 8.8 * mm,
                                       f"Kode dokumen {identitas['kode']}")
            self.setFont(huruf["regular"], 7.4)
            self.setFillColor(colors.HexColor(MUTED))
            self.drawRightString(A4[0] - 18 * mm, 8.8 * mm,
                                 f"Halaman {self._pageNumber} dari {total}")
            self.restoreState()

    doc = SimpleDocTemplate(path, pagesize=A4,
                            leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=16 * mm, bottomMargin=18 * mm,
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

    kiri.append(Paragraph(teks(comp["nama"] if comp else ""), st_perusahaan))
    if comp:
        if comp["alamat"]:
            kiri.append(Paragraph(teks(comp["alamat"]), st_kecil))
        kota_line = " ".join(filter(None, [comp["kota"], comp["kode_pos"]]))
        if kota_line:
            kiri.append(Paragraph(teks(kota_line), st_kecil))
        if comp["npwp"]:
            kiri.append(Paragraph(f"NPWP: {teks(comp['npwp'])}", st_kecil))
        if comp["telepon"]:
            kiri.append(Paragraph(f"Telp: {teks(comp['telepon'])}", st_kecil))
        if comp["email"]:
            kiri.append(Paragraph(teks(comp["email"]), st_kecil))

    kanan = [
        Paragraph("INVOICE", st_judul),
        Spacer(1, 2),
        Paragraph(f"<b>{teks(inv['nomor'])}</b>", st_normal),
        Spacer(1, 6),
        Paragraph(f"Tanggal: {theme.tanggal_id(inv['tanggal'])}", st_kecil),
        Paragraph(f"Jatuh Tempo: {theme.tanggal_id(inv['jatuh_tempo'] or '')}",
                  st_kecil),
    ]
    if inv["status"] == "lunas":
        kanan.append(Spacer(1, 4))
        kanan.append(Paragraph(
            "<b><font color='#2D6A4F'>LUNAS</font></b>", st_normal))

    kop = Table([[kiri, kanan]], colWidths=[doc.width * 0.55, doc.width * 0.45])
    kop.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    elemen.append(kop)
    elemen.append(Spacer(1, 9))

    garis = Table([[""]], colWidths=[doc.width], rowHeights=[0.9])
    garis.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1),
                                colors.HexColor(TINTA))]))
    elemen.append(garis)
    elemen.append(Spacer(1, 14))

    # ---- tagihan kepada
    elemen.append(Paragraph("Ditagihkan kepada", st_label))
    pelanggan = [Paragraph(f"<b>{teks(inv['pelanggan'])}</b>", st_normal)]
    if inv["npwp_nik"]:
        pelanggan.append(Paragraph(f"NPWP/NIK: {teks(inv['npwp_nik'])}",
                                   st_kecil))
    if inv["alamat"]:
        pelanggan.append(Paragraph(teks(inv["alamat"]), st_kecil))
    elemen.append(KeepTogether(pelanggan))
    elemen.append(Spacer(1, 16))

    # ---- tabel item
    # Kolom diskon hanya ditampilkan bila memang ada baris yang berdiskon,
    # supaya tabel tidak menyisakan kolom kosong.
    ada_diskon = any(it["diskon_persen"] or it["diskon_nilai"] for it in items)

    kepala = [
        sel("No", "kepala_tengah"), sel("Deskripsi", "kepala"),
        sel("Qty", "kepala_kanan"), sel("Satuan", "kepala"),
        sel("Harga Satuan", "kepala_kanan"),
    ]
    if ada_diskon:
        kepala.append(sel("Diskon", "kepala_kanan"))
    kepala.append(sel("Jumlah", "kepala_kanan"))
    data = [kepala]

    for n, it in enumerate(items, start=1):
        diskon_teks = ""
        if it["diskon_persen"]:
            diskon_teks = f"{it['diskon_persen']:g}%"
        elif it["diskon_nilai"]:
            diskon_teks = f"{it['diskon_nilai']:,}".replace(",", ".")
        baris_item = [
            sel(n, "tengah"),
            sel(it["deskripsi"] or (it["produk_nama"] or "")),
            sel(f"{it['qty']:g}", "kanan"),
            sel(it["satuan"] or ""),
            sel(f"{it['harga_satuan']:,}".replace(",", "."), "kanan"),
        ]
        if ada_diskon:
            baris_item.append(sel(diskon_teks, "kanan"))
        baris_item.append(sel(f"{it['subtotal']:,}".replace(",", "."), "kanan"))
        data.append(baris_item)

    if ada_diskon:
        lebar = [doc.width * x
                 for x in (0.05, 0.36, 0.08, 0.09, 0.15, 0.10, 0.17)]
    else:
        lebar = [doc.width * x
                 for x in (0.05, 0.44, 0.07, 0.08, 0.17, 0.19)]
    tabel_item = Table(data, colWidths=lebar, repeatRows=1)
    tabel_item.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(KEPALA)),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEABOVE", (0, 0), (-1, 0), 0.9, colors.HexColor(TINTA)),
        ("LINEBELOW", (0, 0), (-1, 0), 0.7, colors.HexColor(TINTA)),
        ("LINEBELOW", (0, 1), (-1, -1), 0.5, colors.HexColor(GARIS)),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor(BELANG)]),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
    ]))
    elemen.append(tabel_item)
    elemen.append(Spacer(1, 12))

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
        ("FONTNAME", (0, 0), (-1, -1), huruf["regular"]),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor(MUTED)),
        ("TEXTCOLOR", (1, 0), (1, -1), colors.HexColor(TINTA)),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW", (0, 0), (-1, -2), 0.4, colors.HexColor(GARIS)),
    ]
    for i, baris in enumerate(ringkas):
        if baris[0] in ("TOTAL", "SISA TAGIHAN"):
            gaya.append(("FONTNAME", (0, i), (-1, i), huruf["bold"]))
            gaya.append(("TEXTCOLOR", (0, i), (-1, i),
                         colors.HexColor(TINTA)))
            gaya.append(("BACKGROUND", (0, i), (-1, i),
                         colors.HexColor(TOTAL_BG)))
        if baris[0] == "TOTAL":
            gaya.append(("LINEABOVE", (0, i), (-1, i), 0.9,
                         colors.HexColor(TINTA)))
    tabel_ringkas.setStyle(TableStyle(gaya))
    elemen.append(tabel_ringkas)
    elemen.append(Spacer(1, 22))

    # ---- catatan & instruksi pembayaran
    if inv["catatan"]:
        elemen.append(Paragraph("Catatan", st_label))
        elemen.append(Paragraph(teks(inv["catatan"]), st_kecil))
        elemen.append(Spacer(1, 12))

    elemen.append(Paragraph("Instruksi pembayaran", st_label))
    bank_info = []
    for kb in O.daftar_kas_bank(company_id):
        if kb["tipe"] == "bank" and kb["nomor_rekening"]:
            bank_info.append(f"{kb['nama_bank'] or kb['nama']} "
                             f"{kb['nomor_rekening']} a/n {comp['nama']}")
    if bank_info:
        for b in bank_info:
            elemen.append(Paragraph(f"• {teks(b)}", st_kecil))
    else:
        elemen.append(Paragraph(
            "Pembayaran dapat dilakukan melalui transfer bank. "
            "Mohon cantumkan nomor invoice pada berita transfer.", st_kecil))

    # ---- pengesahan di dasar halaman terakhir
    class BlokPengesahan(Flowable):
        """
        Blok tanda tangan dan segel yang menempel di dasar halaman.

        Flowable biasa akan berhenti tepat di bawah isi tabel, sehingga
        pengesahan bisa menggantung di tengah halaman. Blok ini digambar
        pada ketinggian tetap dari dasar kertas; bila ruang tersisa tidak
        cukup, reportlab memindahkannya ke halaman baru.
        """
        tinggi = 44 * mm

        def __init__(self):
            super().__init__()
            self.width = doc.width
            self.height = self.tinggi

        def wrap(self, lebar, tinggi):
            return (self.width, self.height)

        def draw(self):
            c = self.canv
            _, y_sekarang = c.absolutePosition(0, 0)
            c.saveState()
            c.translate(0, 30 * mm - y_sekarang)
            kanan = doc.width
            lebar_tanda = 62 * mm

            kota = str(identitas.get("kota") or "").strip()
            tanggal = theme.tanggal_id(datetime.now().strftime("%Y-%m-%d"))
            c.setFont(huruf["regular"], 8)
            c.setFillColor(colors.HexColor(MUTED))
            c.drawRightString(
                kanan, 38 * mm,
                f"{kota + ', ' if kota else ''}{tanggal}")

            gambar = str(identitas.get("gambar") or "")
            if gambar and os.path.isfile(gambar):
                try:
                    iw, ih = ImageReader(gambar).getSize()
                    lebar_g = 38 * mm
                    tinggi_g = lebar_g * ih / iw
                    if tinggi_g > 15 * mm:
                        tinggi_g = 15 * mm
                        lebar_g = tinggi_g * iw / ih
                    c.drawImage(ImageReader(gambar),
                                kanan - lebar_g, 24 * mm,
                                width=lebar_g, height=tinggi_g, mask="auto")
                except Exception:
                    pass

            c.setStrokeColor(colors.HexColor(TINTA))
            c.setLineWidth(0.7)
            c.line(kanan - lebar_tanda, 21 * mm, kanan, 21 * mm)

            nama = str(identitas.get("nama") or "").strip()
            jabatan = str(identitas.get("jabatan") or "").strip()
            c.setFillColor(colors.HexColor(TINTA))
            if nama:
                c.setFont(huruf["bold"], 9.5)
                c.drawRightString(kanan, 15 * mm, nama)
            if jabatan:
                c.setFont(huruf["regular"], 8)
                c.setFillColor(colors.HexColor(MUTED))
                c.drawRightString(kanan, 10.5 * mm, jabatan)
            c.setFont(huruf["regular"], 7.2)
            c.setFillColor(colors.HexColor(MUTED))
            c.drawRightString(kanan, 6.5 * mm,
                              "Ditandatangani secara elektronik")
            if identitas.get("kode"):
                c.setFont(huruf["semibold"], 6.8)
                c.setFillColor(colors.HexColor(MUTED))
                c.drawRightString(kanan, 3.2 * mm,
                                  f"Kode verifikasi {identitas['kode']}")

            try:
                segel = ImageReader(BytesIO(EC.segel_png(identitas)))
                c.drawImage(segel, kanan - lebar_tanda - 29 * mm, 6 * mm,
                            width=28 * mm, height=28 * mm, mask="auto")
            except Exception:
                pass
            c.restoreState()

    if identitas.get("ttd_aktif"):
        elemen.append(Spacer(1, 18))
        elemen.append(BlokPengesahan())

    doc.build(elemen, canvasmaker=NumberedCanvas)
    return path


# ==========================================================================
# DIALOG PILIH PRODUK (baris item)
# ==========================================================================
class PanelItem(QWidget):
    """Panel input baris item yang dapat dipakai di SO dan Invoice."""

    # object, bukan int: subtotal barang bisa melewati batas int 32-bit Qt.
    total_berubah = Signal(object)

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
        # Keterangan ini tampil saat tabel masih kosong, supaya
        # pengguna tahu langkah berikutnya.
        self.tabel.set_pesan_kosong(
            "Belum ada barang pada nota ini."
            "\n\n"
            "Tekan tombol Tambah Baris untuk memilih produk atau menulis "
            "deskripsi barang.")
        for kolom in (2, 4, 5, 6):
            self.tabel.horizontalHeaderItem(kolom).setTextAlignment(
                Qt.AlignRight | Qt.AlignVCenter)

        self.tabel.setMinimumHeight(220)
        lay.addWidget(self.tabel)

        baris = QHBoxLayout()
        b_tambah = w.tombol("Tambah Baris", ikon="tambah")
        b_tambah.clicked.connect(lambda: self._tambah_baris())
        baris.addWidget(b_tambah)
        baris.addStretch()
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
        theme.latar(self.lbl_ringkas,
                    f"color: {C.TEXT}; background: {C.SURFACE_ALT}; "
                    f"border: 1px solid {C.BORDER}; "
                    f"border-radius: {theme.SUDUT_KARTU}px; "
                    f"padding: 10px 12px; font-size: {theme.FS_BODY}px;")
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
                popup.peringatkan(self,
                                  "Belum ada item",
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
            popup.galat(self, "Gagal menyimpan", str(e))


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
        theme.latar(self.lbl_ringkas,
                    f"color: {C.TEXT}; background: {C.SURFACE_ALT}; "
                    f"border: 1px solid {C.BORDER}; "
                    f"border-radius: {theme.SUDUT_KARTU}px; "
                    f"padding: 10px 12px; font-size: {theme.FS_BODY}px;")
        lay.addWidget(self.lbl_ringkas)

        aksi = QHBoxLayout()
        aksi.addStretch()
        b = w.tombol("Batal")
        b.clicked.connect(self.reject)
        aksi.addWidget(b)
        bs = w.tombol("Simpan && Buat Jurnal", gaya="primary")
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
                popup.peringatkan(self,
                                  "Belum ada item",
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
            popup.galat(self, "Gagal menyimpan", str(e))


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
            ("", 34), ("Invoice", 160), ("Jatuh Tempo", 105),
            ("Total", 140), ("Sisa", 140), ("Alokasi", 165),
        ])
        self.tabel.set_pesan_kosong(
            "Tidak ada invoice yang belum lunas."
            "\n\n"
            "Seluruh tagihan pelanggan sudah dibayar penuh, atau belum ada "
            "invoice yang diterbitkan.")
        for kolom in (3, 4, 5):
            self.tabel.horizontalHeaderItem(kolom).setTextAlignment(
                Qt.AlignRight | Qt.AlignVCenter)

        lay.addWidget(self.tabel, 1)

        self.checks: dict[int, QCheckBox] = {}
        self.inputs: dict[int, w.InputRupiah] = {}
        self._muat_invoice()

        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet(f"font-size: {theme.FS_BODY}px; "
                                      "font-weight: 600; background: transparent;")
        lay.addWidget(self.lbl_status)
        self._cek_alokasi()

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
            self.tabel.setItem(i, 2, QTableWidgetItem(
                theme.tanggal_id(inv["jatuh_tempo"] or "")))
            for kolom, nilai in [(3, inv["total"]), (4, inv["sisa"])]:
                item = QTableWidgetItem(tx.rupiah(nilai))
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.tabel.setItem(i, kolom, item)

            inp = w.InputRupiah()
            if inv["id"] == self.invoice_id:
                inp.set_nilai(inv["sisa"])
            inp.valueChanged.connect(self._cek_alokasi)
            self.inputs[inv["id"]] = inp
            self.tabel.setCellWidget(i, 5, inp)

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
                popup.peringatkan(self,
                                  "Jumlah kosong",
                                  "Isi jumlah pembayaran yang diterima.")
                return

            alokasi = []
            for iid, inp in self.inputs.items():
                if self.checks.get(iid) and self.checks[iid].isChecked() and inp.nilai() > 0:
                    alokasi.append({"invoice_id": iid, "jumlah": inp.nilai()})

            if not alokasi:
                popup.peringatkan(self,
                                  "Belum ada alokasi",
                                  "Pilih minimal satu invoice untuk dibayar.")
                return

            if self._total_alokasi() > jumlah:
                popup.peringatkan(self,
                                  "Alokasi berlebih",
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
            popup.galat(self, "Gagal menyimpan", str(e))


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

        petunjuk = QLabel(
            "Retur mengembalikan barang, diskon memotong harga setelah "
            "invoice terbit, refund mengembalikan dana. Nota kredit "
            "mengurangi piutang pelanggan dan pendapatan usaha.")
        petunjuk.setWordWrap(True)
        theme.latar(petunjuk,
                    f"color: {C.TEXT_MUTED}; background: {C.SURFACE_ALT}; "
                    f"border: 1px solid {C.BORDER}; "
                    f"border-radius: {theme.SUDUT_KARTU}px; "
                    f"padding: 8px 11px; font-size: {theme.FS_SMALL}px;")
        lay.addWidget(petunjuk)

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
        self.lbl_info.setTextFormat(Qt.RichText)
        theme.latar(self.lbl_info,
                    f"color: {C.TEXT}; background: {C.SURFACE_ALT}; "
                    f"border: 1px solid {C.BORDER}; "
                    f"border-radius: {theme.SUDUT_KARTU}px; "
                    f"padding: 9px 11px; font-size: {theme.FS_SMALL}px;")
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
                f"Invoice <b>{inv['nomor']}</b> · total "
                f"{tx.rupiah(inv['total'])} · sudah dibayar "
                f"{tx.rupiah(inv['dibayar'])} · sisa "
                f"{tx.rupiah(inv['sisa'])}")
            self.lbl_info.setToolTip(
                "Sisa piutang adalah batas wajar nota kredit. Jumlah yang "
                "melebihi sisa berarti uang pelanggan perlu dikembalikan.")

    def _simpan(self):
        try:
            jumlah = self.inp_jumlah.nilai()
            if jumlah <= 0:
                popup.peringatkan(self,
                                  "Jumlah kosong",
                                  "Isi jumlah nota kredit.")
                return
            iid = self.cmb_invoice.currentData()
            if not iid:
                popup.peringatkan(self,
                                  "Invoice kosong",
                                  "Pilih invoice terkait.")
                return
            inv = S.get_invoice(iid)
            if jumlah > inv["total"]:
                popup.peringatkan(self,
                                  "Jumlah berlebih",
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
            popup.galat(self, "Gagal menyimpan", str(e))


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

        self.tabs = w.Tab()
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
        self.inp_cari_inv.setMinimumWidth(340)
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
        self.lbl_inv = w.label_ringkas()
        baris.addWidget(self.lbl_inv, 1)
        lay.addLayout(baris)

        self.tabel_inv = w.Tabel([
            ("Nomor", 175), ("Tanggal", 105), ("Pelanggan", -1),
            ("Jatuh Tempo", 110), ("Total", 150), ("Dibayar", 140),
            ("Sisa", 140), ("Status", 110),
        ])
        # Keterangan ini tampil saat tabel masih kosong, supaya
        # pengguna tahu langkah berikutnya.
        self.tabel_inv.set_pesan_kosong(
            "Belum ada invoice."
            "\n\n"
            "Tekan tombol Invoice Baru di atas untuk mencatat penjualan "
            "pertama. Jurnal dan pajaknya dihitung otomatis.")

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
            ("Nomor", 175), ("Tanggal", 105), ("Pelanggan", -1),
            ("Tgl Kirim", 110), ("Subtotal", 150), ("PPN", 140),
            ("Total", 150), ("Status", 115),
        ])
        # Keterangan ini tampil saat tabel masih kosong, supaya
        # pengguna tahu langkah berikutnya.
        self.tabel_so.set_pesan_kosong(
            "Belum ada sales order."
            "\n\n"
            "Tekan tombol Sales Order di atas untuk membuat surat pesanan. "
            "Invoice dapat dibuat dari SO yang sudah dikonfirmasi.")

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
        self.lbl_so = w.label_ringkas()
        baris.addWidget(self.lbl_so, 1)
        lay.addLayout(baris)

    def _bangun_penerimaan(self):
        lay = QVBoxLayout(self.tab_penerimaan)
        lay.setContentsMargins(0, 12, 0, 0)
        lay.setSpacing(12)

        self.tabel_rcv = w.Tabel([
            ("Nomor", 175), ("Tanggal", 110), ("Pelanggan", -1),
            ("Metode", 130), ("Jumlah", 165), ("Referensi", -1), ("Status", 105),
        ])
        # Keterangan ini tampil saat tabel masih kosong, supaya
        # pengguna tahu langkah berikutnya.
        self.tabel_rcv.set_pesan_kosong(
            "Belum ada penerimaan pembayaran."
            "\n\n"
            "Buka tab Invoice, pilih invoice, lalu tekan Terima Pembayaran "
            "untuk mencatat uang masuk.")

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
        self.lbl_rcv = w.label_ringkas()
        baris.addWidget(self.lbl_rcv, 1)
        lay.addLayout(baris)

    def _bangun_nota(self):
        lay = QVBoxLayout(self.tab_nota)
        lay.setContentsMargins(0, 12, 0, 0)
        lay.setSpacing(12)

        self.tabel_nota = w.Tabel([
            ("Nomor", 175), ("Tanggal", 110), ("Pelanggan", -1),
            ("Tipe", 120), ("Jumlah", 165), ("Alasan", -1), ("Status", 105),
        ])
        # Keterangan ini tampil saat tabel masih kosong, supaya
        # pengguna tahu langkah berikutnya.
        self.tabel_nota.set_pesan_kosong(
            "Belum ada nota kredit."
            "\n\n"
            "Tekan tombol Buat Nota Kredit untuk mencatat retur atau "
            "potongan atas invoice pelanggan.")

        lay.addWidget(self.tabel_nota, 1)

        baris = QHBoxLayout()
        b = w.tombol("Buat Nota Kredit", gaya="primary", ikon="tambah")
        b.clicked.connect(self._buat_nota)
        baris.addWidget(b)
        self.lbl_nota = w.label_ringkas()
        baris.addWidget(self.lbl_nota, 1)
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
            ("Pelanggan", -1), ("Jumlah Invoice", 130),
            ("Belum JT", 145), ("1-30 hari", 140), ("31-60 hari", 140),
            ("61-90 hari", 140), ("di atas 90", 145), ("Total", 155),
        ])
        # Keterangan ini tampil saat tabel masih kosong, supaya
        # pengguna tahu langkah berikutnya.
        self.tabel_aging.set_pesan_kosong(
            "Belum ada piutang yang perlu ditagih."
            "\n\n"
            "Seluruh tagihan pelanggan sudah lunas, atau belum ada invoice "
            "yang jatuh tempo.")

        lay.addWidget(self.tabel_aging, 1)

        baris = QHBoxLayout()
        b = w.tombol("Buat Pengingat Penagihan", gaya="primary", ikon="peringatan")
        b.clicked.connect(self._buat_pengingat)
        baris.addWidget(b)
        b2 = w.tombol("Ekspor Daftar", ikon="laporan")
        b2.clicked.connect(self._ekspor_aging)
        baris.addWidget(b2)
        self.lbl_aging = w.label_ringkas()
        baris.addWidget(self.lbl_aging, 1)
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
        baris, warna, warna_jt = [], {}, {}
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
            # Lencana menyatakan status dokumen; warna tanggal jatuh tempo
            # menyatakan urgensinya, sehingga keduanya tidak saling mengaburkan.
            warna[idx] = {"terkirim": C.INFO, "sebagian": C.WARNING,
                          "lunas": C.SUCCESS, "batal": C.TEXT_FAINT}.get(
                inv["status"], C.TEXT_MUTED)
            if inv["status"] in ("terkirim", "sebagian"):
                try:
                    jt = datetime.fromisoformat(
                        (inv["jatuh_tempo"] or inv["tanggal"])[:10]).date()
                    if jt < hari_ini:
                        warna_jt[(idx, 3)] = C.DANGER
                    elif (jt - hari_ini).days <= 7:
                        warna_jt[(idx, 3)] = C.WARNING
                except ValueError:
                    pass
        self.tabel_inv.isi(baris, warna_baris=warna, align_kanan={4, 5, 6},
                           warna_sel=warna_jt, tebal_kolom={6})
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
            elif so["status"] == "dikonfirmasi":
                warna[idx] = C.INFO
            else:
                warna[idx] = C.TEXT_MUTED
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
            else:
                warna[idx] = C.SUCCESS
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
            else:
                warna[idx] = C.INFO
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
            popup.beri_tahu(self,
                            "Belum ada perusahaan",
                            "Buat profil perusahaan terlebih dahulu.")
            return
        d = DialogSalesOrder(self.ctx, self)
        if d.exec():
            self.tabs.setCurrentIndex(1)
            self.muat()

    def _buat_invoice(self):
        if not self.ctx.company_id:
            popup.beri_tahu(self,
                            "Belum ada perusahaan",
                            "Buat profil perusahaan terlebih dahulu.")
            return
        if not M.daftar_produk(self.ctx.company_id):
            if popup.tanya(self,
                           "Belum ada produk",
                           "Belum ada produk atau jasa terdaftar.\n\n"
                           "Anda tetap dapat membuat invoice dengan deskripsi manual.\n"
                           "Ingin mendaftarkan produk terlebih dahulu?"):
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
            popup.beri_tahu(self, "Belum dipilih", "Pilih satu invoice.")
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
            if popup.tanya(self,
                           "PDF dibuat",
                           f"Invoice berhasil disimpan:\n{path}\n\nBuka berkasnya?"):
                QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        except Exception as e:
            popup.galat(self, "Gagal membuat PDF", str(e))

    def _bayar_invoice_terpilih(self):
        inv = self._invoice_terpilih()
        if inv is None:
            popup.beri_tahu(self, "Belum dipilih", "Pilih satu invoice.")
            return
        if inv["status"] == "lunas":
            popup.beri_tahu(self, "Sudah lunas", "Invoice ini sudah lunas.")
            return
        d = DialogPenerimaan(self.ctx, self, inv["id"], inv["partner_id"])
        if d.exec():
            self.muat()

    def _nota_dari_invoice(self):
        inv = self._invoice_terpilih()
        if inv is None:
            popup.beri_tahu(self, "Belum dipilih", "Pilih satu invoice.")
            return
        d = DialogNotaKredit(self.ctx, self, inv["id"])
        if d.exec():
            self.muat()

    def _void_invoice(self):
        inv = self._invoice_terpilih()
        if inv is None:
            popup.beri_tahu(self, "Belum dipilih", "Pilih satu invoice.")
            return
        if inv["dibayar"] > 0:
            popup.peringatkan(self,
                              "Tidak dapat di-void",
                              "Invoice ini sudah memiliki pembayaran. Batalkan pembayarannya "
                              "terlebih dahulu.")
            return
        if not popup.tanya(self,
                           "Konfirmasi Void",
                           f"Void invoice {inv['nomor']}?\n\n"
                           "Tindakan ini akan:\n"
                           "• Membatalkan jurnal invoice\n"
                           "• Mengembalikan stok barang\n"
                           "• Memindahkan data ke keranjang sampah\n\n"
                           "Lanjutkan?"):
            return
        try:
            S.hapus_invoice(inv["id"], self.ctx.username, self.ctx.user_id)
            self.muat()
        except Exception as e:
            popup.galat(self, "Gagal void", str(e))

    def _so_terpilih(self):
        r = self.tabel_so.baris_terpilih()
        if r is None:
            return None
        data = S.daftar_sales_order(self.ctx.company_id, self.ctx.tahun)
        return data[r] if r < len(data) else None

    def _ubah_status_so(self, status: str):
        so = self._so_terpilih()
        if so is None:
            popup.beri_tahu(self, "Belum dipilih", "Pilih satu sales order.")
            return
        try:
            S.ubah_status_so(so["id"], status)
            self.muat()
        except Exception as e:
            popup.galat(self, "Gagal", str(e))

    def _invoice_dari_so(self):
        so = self._so_terpilih()
        if so is None:
            popup.beri_tahu(self, "Belum dipilih", "Pilih satu sales order.")
            return
        if so["status"] == "batal":
            popup.peringatkan(self,
                              "SO dibatalkan",
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
        # Keterangan ini tampil saat tabel masih kosong, supaya
        # pengguna tahu langkah berikutnya.
        t.set_pesan_kosong(
            "Belum ada invoice yang dialokasikan pada penerimaan ini."
            "\n\n"
            "Alokasi dibuat saat penerimaan dicatat. Periksa kembali invoice "
            "yang dipilih.")

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
            popup.beri_tahu(self, "Belum dipilih", "Pilih satu penerimaan.")
            return
        if rcv["status"] == "void":
            popup.beri_tahu(self,
                            "Sudah void",
                            "Penerimaan ini sudah dibatalkan.")
            return
        if not popup.tanya(self,
                           "Konfirmasi Void",
                           f"Void penerimaan {rcv['nomor']}?\n\n"
                           "Status invoice terkait akan dikembalikan ke belum lunas."):
            return
        try:
            S.void_penerimaan(rcv["id"], self.ctx.username, self.ctx.user_id)
            self.muat()
        except Exception as e:
            popup.galat(self, "Gagal void", str(e))

    def _buat_pengingat(self):
        try:
            jumlah = O.buat_reminder_dari_piutang(self.ctx.company_id, 30)
            if jumlah:
                popup.beri_tahu(self,
                                "Pengingat dibuat",
                                f"{jumlah} pengingat penagihan dibuat untuk invoice yang "
                                "jatuh tempo dalam 30 hari ke depan.\n\n"
                                "Lihat di menu Pengaturan -> Pengingat.")
            else:
                popup.beri_tahu(self,
                                "Tidak ada pengingat baru",
                                "Semua invoice yang jatuh tempo sudah memiliki pengingat.")
        except Exception as e:
            popup.galat(self, "Gagal membuat pengingat", str(e))

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
            from ..ekspor_cetak import ekspor_excel
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
            comp = services.get_company(cid)
            ekspor_excel(
                "Aging Piutang", data, path,
                subjudul=f"Per {datetime.now():%d/%m/%Y}",
                nama_perusahaan=comp["nama"])
            if popup.tanya(self,
                           "Ekspor selesai",
                           f"Data disimpan:\n{path}\n\nBuka foldernya?"):
                QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.dirname(path)))
        except Exception as e:
            popup.galat(self, "Gagal mengekspor", str(e))


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
        # Keterangan ini tampil saat tabel masih kosong, supaya
        # pengguna tahu langkah berikutnya.
        t.set_pesan_kosong(
            "Invoice ini belum memiliki baris barang."
            "\n\n"
            "Ubah invoice untuk menambahkan produk atau jasa.")

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
            # Keterangan ini tampil saat tabel masih kosong, supaya
            # pengguna tahu langkah berikutnya.
            t2.set_pesan_kosong(
                "Belum ada lampiran pada invoice ini."
                "\n\n"
                "Tekan tombol Lampirkan Dokumen untuk menambahkan berkas "
                "pendukung.")

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
            popup.beri_tahu(self, "Berhasil", "Dokumen dilampirkan.")
            self.accept()
        except Exception as e:
            popup.galat(self, "Gagal melampirkan", str(e))

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
            popup.galat(self, "Gagal membuat PDF", str(e))
