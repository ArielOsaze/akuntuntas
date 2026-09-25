"""
AkunTuntas - Halaman Laporan Keuangan
======================================
  • Neraca Saldo
  • Laba Rugi
  • Neraca (Laporan Posisi Keuangan)
  • Arus Kas
  • Perubahan Ekuitas
  • Buku Besar
  • Ringkasan Bulanan
  • Ekspor (Excel / PDF / CSV)
"""
from __future__ import annotations

import csv
import os
from datetime import datetime

from PySide6.QtCore import Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QTabWidget,
    QFileDialog, QMessageBox, QFrame, QMenu,
)

from ... import config, services
from .. import icons, theme
from ..theme import C
from .. import widgets as w


# ==========================================================================
# EKSPOR
# ==========================================================================
def ekspor_excel(judul: str, tabel_data: list[tuple[str, list[list]]],
                 path: str) -> None:
    """Ekspor beberapa tabel ke satu berkas Excel (satu sheet per tabel)."""
    try:
        import openpyxl
        from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    except ImportError:
        raise RuntimeError("Modul openpyxl belum terpasang. "
                           "Jalankan: pip install openpyxl")

    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    kepala_font = Font(bold=True, color="FFFFFF", size=11)
    kepala_fill = PatternFill("solid", fgColor="1B4F8A")
    tipis = Side(style="thin", color="DFE4EA")
    border = Border(left=tipis, right=tipis, top=tipis, bottom=tipis)

    for nama_sheet, baris in tabel_data:
        ws = wb.create_sheet(title=nama_sheet[:31])
        for r, data in enumerate(baris, start=1):
            for c, nilai in enumerate(data, start=1):
                cell = ws.cell(row=r, column=c)
                if isinstance(nilai, str) and nilai.startswith("="):
                    cell.value = nilai
                elif isinstance(nilai, (int, float)):
                    cell.value = nilai
                    if abs(nilai) >= 1000:
                        cell.number_format = '#,##0'
                else:
                    cell.value = str(nilai) if nilai is not None else ""
                cell.border = border
                if r == 1:
                    cell.font = kepala_font
                    cell.fill = kepala_fill
                    cell.alignment = Alignment(horizontal="center", vertical="center")
        for c in range(1, (len(baris[0]) if baris else 1) + 1):
            ws.column_dimensions[openpyxl.utils.get_column_letter(c)].width = 24
    wb.save(path)


def ekspor_csv(nama: str, baris: list[list], path: str) -> None:
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        wr = csv.writer(f, delimiter=";")
        for r in baris:
            wr.writerow(r)


def ekspor_pdf(judul: str, subjudul: str, tabel_data: list[tuple[str, list[list]]],
               path: str) -> None:
    """Ekspor laporan ke PDF dengan kop dan tata letak rapi."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.units import mm
        from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                        Paragraph, Spacer)
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    except ImportError:
        raise RuntimeError("Modul reportlab belum terpasang. "
                           "Jalankan: pip install reportlab")

    doc = SimpleDocTemplate(path, pagesize=A4,
                            leftMargin=16 * mm, rightMargin=16 * mm,
                            topMargin=15 * mm, bottomMargin=15 * mm,
                            title=judul)
    styles = getSampleStyleSheet()
    st_judul = ParagraphStyle("JudulID", parent=styles["Title"], fontSize=15,
                              spaceAfter=3, textColor=colors.HexColor("#1A2733"))
    st_sub = ParagraphStyle("SubID", parent=styles["Normal"], fontSize=9,
                            textColor=colors.HexColor("#64748B"), spaceAfter=10)
    st_seksi = ParagraphStyle("SeksiID", parent=styles["Heading2"], fontSize=11,
                              spaceBefore=12, spaceAfter=6,
                              textColor=colors.HexColor("#1B4F8A"))
    st_kecil = ParagraphStyle("KecilID", parent=styles["Normal"], fontSize=7.5,
                              textColor=colors.HexColor("#556577"))

    elemen = [Paragraph(judul, st_judul), Paragraph(subjudul, st_sub)]
    elemen.append(Paragraph(
        f"Dicetak {datetime.now().strftime('%d/%m/%Y %H:%M')} · "
        f"AkunTuntas {config.APP_VERSION}", st_kecil))

    for nama, baris in tabel_data:
        elemen.append(Paragraph(nama, st_seksi))
        if not baris:
            elemen.append(Paragraph("(tidak ada data)", st_sub))
            continue

        # konversi angka menjadi teks berformat
        data_tampil = []
        for r_i, r in enumerate(baris):
            baris_baru = []
            for nilai in r:
                if isinstance(nilai, (int, float)) and not isinstance(nilai, bool):
                    baris_baru.append(f"{nilai:,.0f}".replace(",", "."))
                else:
                    baris_baru.append(str(nilai) if nilai is not None else "")
            data_tampil.append(baris_baru)

        n_kolom = max(len(r) for r in data_tampil)
        for r in data_tampil:
            while len(r) < n_kolom:
                r.append("")

        lebar = (doc.width) / n_kolom
        t = Table(data_tampil, colWidths=[lebar] * n_kolom, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1B4F8A")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 7.5),
            ("FONTSIZE", (0, 1), (-1, -1), 7.5),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("ALIGN", (0, 0), (0, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#DFE4EA")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1),
             [colors.white, colors.HexColor("#FAFBFC")]),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        elemen.append(t)

    elemen.append(Spacer(1, 10))
    elemen.append(Paragraph(
        "Dokumen ini dihasilkan otomatis oleh AkunTuntas. Angka bersumber dari "
        "jurnal yang tercatat. Verifikasi kebenaran data sebelum digunakan untuk "
        "pelaporan resmi.", st_kecil))
    doc.build(elemen)


# ==========================================================================
# HALAMAN LAPORAN
# ==========================================================================
class LaporanPage(QWidget):
    pindah_halaman = Signal(str)

    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx

        luar = QVBoxLayout(self)
        luar.setContentsMargins(0, 0, 0, 0)
        luar.setSpacing(0)

        self.header = w.PageHeader(
            "Laporan Keuangan",
            "Seluruh laporan diturunkan dari jurnal yang sama, sehingga angkanya "
            "konsisten satu dengan yang lain.")

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

        self.cmb_periode = QComboBox()
        self.cmb_periode.addItem("Setahun", 0)
        for i, n in enumerate(config.MONTH_NAMES_ID, start=1):
            self.cmb_periode.addItem(f"s.d. {n}", i)
        self.cmb_periode.setMinimumWidth(130)
        self.cmb_periode.currentIndexChanged.connect(self.muat)
        self.header.tambah_aksi(self.cmb_periode)

        # Satu tombol ekspor dengan pilihan format. Dua tombol terpisah
        # membuat baris aksi meluber keluar tepi header.
        b_ekspor = w.tombol("Ekspor", ikon="ekspor")
        menu_ekspor = QMenu(b_ekspor)
        menu_ekspor.addAction(icons.ikon("laporan", C.TEXT, 16), "Excel (.xlsx)",
                              lambda: self._ekspor("excel"))
        menu_ekspor.addAction(icons.ikon("dokumen", C.TEXT, 16), "PDF (.pdf)",
                              lambda: self._ekspor("pdf"))
        b_ekspor.setMenu(menu_ekspor)
        self.header.tambah_aksi(b_ekspor)

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

        self.tab_neraca_saldo = QWidget()
        self.tab_laba_rugi = QWidget()
        self.tab_neraca = QWidget()
        self.tab_arus_kas = QWidget()
        self.tab_ekuitas = QWidget()
        self.tab_buku_besar = QWidget()

        self.tabs.addTab(self.tab_laba_rugi, "Laba Rugi")
        self.tabs.addTab(self.tab_neraca, "Neraca")
        self.tabs.addTab(self.tab_arus_kas, "Arus Kas")
        self.tabs.addTab(self.tab_ekuitas, "Perubahan Ekuitas")
        self.tabs.addTab(self.tab_neraca_saldo, "Neraca Saldo")
        self.tabs.addTab(self.tab_buku_besar, "Buku Besar")
        self.tabs.currentChanged.connect(self.muat)

        for t in (self.tab_neraca_saldo, self.tab_laba_rugi, self.tab_neraca,
                  self.tab_arus_kas, self.tab_ekuitas, self.tab_buku_besar):
            lay = QVBoxLayout(t)
            lay.setContentsMargins(0, 12, 0, 0)
            lay.setSpacing(12)

    def _ganti_tahun(self):
        self.ctx.tahun = self.cmb_tahun.currentData()
        self.muat()

    def periode(self):
        return self.cmb_periode.currentData() or None

    # ------------------------------------------------------------------
    def muat(self):
        cid = self.ctx.company_id
        if not cid:
            self._bersihkan(self.tab_laba_rugi)
            self.tab_laba_rugi.layout().addWidget(w.InfoBanner(
                "Belum ada perusahaan. Buat profil perusahaan terlebih dahulu.",
                "warning", "Data belum tersedia"))
            return
        idx = self.tabs.currentIndex()
        if idx == 0:
            self._isi_laba_rugi(cid)
        elif idx == 1:
            self._isi_neraca(cid)
        elif idx == 2:
            self._isi_arus_kas(cid)
        elif idx == 3:
            self._isi_ekuitas(cid)
        elif idx == 4:
            self._isi_neraca_saldo(cid)
        elif idx == 5:
            self._isi_buku_besar(cid)

    def _bersihkan(self, widget):
        lay = widget.layout()
        while lay.count():
            it = lay.takeAt(0)
            wdg = it.widget()
            if wdg is not None:
                wdg.setParent(None)
                wdg.deleteLater()
            elif it.layout():
                self._bersihkan_layout(it.layout())

    def _bersihkan_layout(self, lay):
        while lay.count():
            it = lay.takeAt(0)
            wdg = it.widget()
            if wdg is not None:
                wdg.setParent(None)
                wdg.deleteLater()
            elif it.layout():
                self._bersihkan_layout(it.layout())

    # ==================================================================
    # LABA RUGI
    # ==================================================================
    def _isi_laba_rugi(self, cid):
        self._bersihkan(self.tab_laba_rugi)
        lay = self.tab_laba_rugi.layout()
        tahun, bulan = self.ctx.tahun, self.periode()

        lr = services.laporan_laba_rugi(cid, tahun, bulan)

        # KPI atas
        kartu = w.Card()
        kl = kartu.body()
        baris = QHBoxLayout()
        baris.setSpacing(30)
        baris.addWidget(w.MiniStat("Pendapatan Usaha", theme.money(lr.pendapatan_usaha)))
        baris.addWidget(w.MiniStat("Laba Kotor", theme.money(lr.laba_kotor),
                                   C.POSITIF if lr.laba_kotor >= 0 else C.NEGATIF))
        baris.addWidget(w.MiniStat("Laba Operasional", theme.money(lr.laba_operasional),
                                   C.POSITIF if lr.laba_operasional >= 0 else C.NEGATIF))
        baris.addWidget(w.MiniStat("Laba Bersih", theme.money(lr.laba_bersih),
                                   C.POSITIF if lr.laba_bersih >= 0 else C.NEGATIF))
        baris.addWidget(w.MiniStat("Margin Bersih", theme.persen(lr.margin_bersih)))
        baris.addStretch()
        kl.addLayout(baris)
        lay.addWidget(kartu)

        # tabel laba rugi
        t = w.Tabel([("Uraian", -1), ("Jumlah (Rp)", 200), ("% Pendapatan", 140)])
        # Keterangan ini tampil saat tabel masih kosong, supaya
        # pengguna tahu langkah berikutnya.
        t.set_pesan_kosong(
            "Belum ada data untuk dilaporkan."
            "\n\n"
            "Catat dulu transaksi pada menu Jurnal Umum, Penjualan, atau "
            "Pembelian. Laporan akan terisi sendiri.")

        baris_tabel = []
        warna = {}

        def tambah(uraian, nilai, tebal=False, persen=None):
            idx = len(baris_tabel)
            p = persen if persen is not None else (
                nilai / lr.pendapatan_usaha if lr.pendapatan_usaha else 0)
            baris_tabel.append([uraian, theme.money(nilai),
                                f"{p * 100:.1f}%" if lr.pendapatan_usaha else ""])
            if tebal:
                warna[idx] = C.PRIMARY
            return idx

        tambah("PENDAPATAN USAHA", lr.pendapatan_usaha, True, 1.0)
        for kode, nama, nilai in lr.rincian_pendapatan:
            if "Pendapatan Usaha" in nama or kode.startswith("400"):
                baris_tabel.append([f"    {kode} {nama}", theme.money(nilai), ""])
        tambah("Harga Pokok Penjualan", -lr.hpp)
        tambah("LABA KOTOR", lr.laba_kotor, True)
        tambah("BEBAN OPERASIONAL", -lr.beban_operasional, True)
        for kode, nama, nilai in lr.rincian_beban:
            akun = services.get_account(cid, kode)
            if akun and akun["grup_lr"] == "Beban Operasional":
                baris_tabel.append([f"    {kode} {nama}", theme.money(nilai), ""])
        tambah("LABA OPERASIONAL", lr.laba_operasional, True)
        tambah("Pendapatan Lain-lain", lr.pendapatan_lain)
        tambah("Beban Lain-lain", -lr.beban_lain)
        tambah("LABA SEBELUM PAJAK", lr.laba_sebelum_pajak, True)
        tambah("Beban Pajak Kini (estimasi)", -lr.beban_pajak)
        tambah("LABA BERSIH SETELAH PAJAK", lr.laba_bersih, True)

        t.isi(baris_tabel, warna_baris=warna, align_kanan={1, 2})
        t.setMinimumHeight(120)
        lay.addWidget(t, 1)

        if self.ctx.beginner:
            lay.addWidget(w.HelpPanel(
                "Cara membaca Laba Rugi",
                "Laporan ini menunjukkan apakah usaha Anda untung atau rugi.\n\n"
                "• LABA KOTOR = Pendapatan − HPP. Ini laba dari penjualan sebelum "
                "beban operasional.\n"
                "• LABA OPERASIONAL = Laba kotor − beban operasional. Ini laba dari "
                "kegiatan usaha utama.\n"
                "• LABA BERSIH = setelah pajak. Ini yang benar-benar menjadi milik Anda.\n\n"
                "Kolom '% Pendapatan' membantu Anda melihat proporsi tiap pos "
                "terhadap total penjualan.",
                "SAK EMKM - laporan laba rugi; PSAK 1 - penyajian laporan keuangan."))

        lay.addStretch()

    # ==================================================================
    # NERACA
    # ==================================================================
    def _isi_neraca(self, cid):
        self._bersihkan(self.tab_neraca)
        lay = self.tab_neraca.layout()
        tahun, bulan = self.ctx.tahun, self.periode()
        n = services.laporan_neraca(cid, tahun, bulan)

        if not n.seimbang:
            lay.addWidget(w.InfoBanner(
                f"Neraca belum seimbang. Selisih {theme.money(n.selisih)} antara "
                f"total aset {theme.money(n.total_aset)} dan total liabilitas+ekuitas "
                f"{theme.money(n.total_liabilitas_ekuitas)}. Periksa saldo awal akun "
                "dan kelengkapan baris neraca pada bagan akun.",
                "danger", "Neraca tidak seimbang"))

        dua = QHBoxLayout()
        dua.setSpacing(16)

        # ---- sisi aset
        ka = w.Card()
        ka.body().addWidget(self._judul_kolom("ASET"))
        t1 = w.Tabel([("Keterangan", -1), ("Jumlah (Rp)", 165)])
        # Keterangan ini tampil saat tabel masih kosong, supaya
        # pengguna tahu langkah berikutnya.
        t1.set_pesan_kosong(
            "Belum ada data untuk dilaporkan."
            "\n\n"
            "Catat dulu transaksi pada menu Jurnal Umum, Penjualan, atau "
            "Pembelian. Laporan akan terisi sendiri.")

        baris1, warna1 = [], {}

        def tambah1(label, nilai, tebal=False, indent=True):
            idx = len(baris1)
            baris1.append([("    " if indent else "") + label, theme.money(nilai)])
            if tebal:
                warna1[idx] = C.PRIMARY
            return idx

        tambah1("ASET LANCAR", 0, True, False)
        for kode, (nama, nilai) in sorted(n.aset_lancar.items()):
            if nilai != 0:
                tambah1(f"{kode} {nama}", nilai)
        tambah1("Total Aset Lancar", n.total_aset_lancar, True, False)

        if n.aset_tetap:
            tambah1("ASET TETAP", 0, True, False)
            for kode, (nama, nilai) in sorted(n.aset_tetap.items()):
                if nilai != 0:
                    tambah1(f"{kode} {nama}", nilai)
            tambah1("Total Aset Tetap", n.total_aset_tetap, True, False)

        if n.aset_lain:
            tambah1("ASET LAIN", 0, True, False)
            for kode, (nama, nilai) in sorted(n.aset_lain.items()):
                if nilai != 0:
                    tambah1(f"{kode} {nama}", nilai)

        tambah1("TOTAL ASET", n.total_aset, True, False)
        t1.isi(baris1, warna_baris=warna1, align_kanan={1})
        t1.setMinimumHeight(380)
        ka.body().addWidget(t1, 1)
        dua.addWidget(ka, 1)

        # ---- sisi liabilitas & ekuitas
        ke = w.Card()
        ke.body().addWidget(self._judul_kolom("LIABILITAS & EKUITAS"))
        t2 = w.Tabel([("Keterangan", -1), ("Jumlah (Rp)", 165)])
        # Keterangan ini tampil saat tabel masih kosong, supaya
        # pengguna tahu langkah berikutnya.
        t2.set_pesan_kosong(
            "Belum ada data untuk dilaporkan."
            "\n\n"
            "Catat dulu transaksi pada menu Jurnal Umum, Penjualan, atau "
            "Pembelian. Laporan akan terisi sendiri.")

        baris2, warna2 = [], {}

        def tambah2(label, nilai, tebal=False, indent=True):
            idx = len(baris2)
            baris2.append([("    " if indent else "") + label, theme.money(nilai)])
            if tebal:
                warna2[idx] = C.PRIMARY
            return idx

        tambah2("LIABILITAS JANGKA PENDEK", 0, True, False)
        for kode, (nama, nilai) in sorted(n.liabilitas_pendek.items()):
            if nilai != 0:
                tambah2(f"{kode} {nama}", nilai)
        tambah2("Total Liabilitas Jangka Pendek", n.total_liabilitas_pendek, True, False)

        if n.liabilitas_panjang:
            tambah2("LIABILITAS JANGKA PANJANG", 0, True, False)
            for kode, (nama, nilai) in sorted(n.liabilitas_panjang.items()):
                if nilai != 0:
                    tambah2(f"{kode} {nama}", nilai)
            tambah2("Total Liabilitas Jangka Panjang", n.total_liabilitas_panjang, True, False)

        tambah2("TOTAL LIABILITAS", n.total_liabilitas, True, False)

        tambah2("EKUITAS", 0, True, False)
        tambah2("Modal Disetor", n.modal)
        tambah2("Saldo Laba", n.saldo_laba)
        tambah2("Laba Tahun Berjalan", n.laba_tahun_berjalan)
        if n.prive:
            tambah2("Prive (Penarikan Pemilik)", -n.prive)
        tambah2("Total Ekuitas", n.total_ekuitas, True, False)
        tambah2("TOTAL LIABILITAS & EKUITAS", n.total_liabilitas_ekuitas, True, False)

        t2.isi(baris2, warna_baris=warna2, align_kanan={1})
        t2.setMinimumHeight(380)
        ke.body().addWidget(t2, 1)
        dua.addWidget(ke, 1)
        lay.addLayout(dua)

        # kontrol keseimbangan
        cek = QFrame()
        warna_bg = C.SUCCESS_BG if n.seimbang else C.DANGER_BG
        warna_txt = C.SUCCESS if n.seimbang else C.DANGER
        border = "#B8E6D5" if n.seimbang else "#F5C2C2"
        theme.latar(cek, f"background: {warna_bg}; border: 1px solid {border}; "
                          "border-radius: 8px;")
        cl = QHBoxLayout(cek)
        cl.setContentsMargins(16, 12, 16, 12)
        cl.setSpacing(30)
        ikon = "simpan" if n.seimbang else "hapus"
        pesan = (f"{ikon} Persamaan akuntansi seimbang: "
                 f"Aset {theme.money(n.total_aset)} = Liabilitas + Ekuitas "
                 f"{theme.money(n.total_liabilitas_ekuitas)}"
                 if n.seimbang else
                 f"{ikon} Selisih {theme.money(n.selisih)}")
        l = QLabel(pesan)
        l.setStyleSheet(f"color: {warna_txt}; font-weight: 700; background: transparent;")
        cl.addWidget(l)
        cl.addStretch()
        lay.addWidget(cek)

        if self.ctx.beginner:
            lay.addWidget(w.HelpPanel(
                "Cara membaca Neraca",
                "Neraca menunjukkan apa yang DIMILIKI (aset) dan dari mana "
                "PENDANAANNYA (liabilitas + ekuitas) pada satu tanggal tertentu.\n\n"
                "Persamaan dasar akuntansi:\n"
                "    ASET = LIABILITAS + EKUITAS\n\n"
                "Ini harus selalu seimbang. Bila tidak seimbang, ada pencatatan "
                "yang salah atau saldo awal belum lengkap.\n\n"
                "• Aset lancar: dapat dicairkan dalam 12 bulan (kas, piutang, persediaan)\n"
                "• Aset tetap: dipakai jangka panjang (peralatan, kendaraan, bangunan)\n"
                "• Ekuitas: modal pemilik + laba yang belum diambil",
                "SAK EMKM; PSAK 1 - penyajian laporan posisi keuangan."))

        lay.addStretch()

    def _judul_kolom(self, teks: str) -> QLabel:
        l = QLabel(teks)
        l.setStyleSheet(
            f"font-size: 14px; font-weight: 700; color: {C.PRIMARY}; "
            f"background: transparent; padding-bottom: 4px; "
            f"border-bottom: 2px solid {C.PRIMARY_SOFT};")
        return l

    # ==================================================================
    # ARUS KAS
    # ==================================================================
    def _isi_arus_kas(self, cid):
        self._bersihkan(self.tab_arus_kas)
        lay = self.tab_arus_kas.layout()
        tahun, bulan = self.ctx.tahun, self.periode()
        a = services.laporan_arus_kas(cid, tahun, bulan)

        kartu = w.Card()
        baris = QHBoxLayout()
        baris.setSpacing(30)
        baris.addWidget(w.MiniStat("Kas Awal", theme.money(a.kas_awal)))
        baris.addWidget(w.MiniStat("Arus Kas Operasi", theme.money(a.total_operasi),
                                   C.POSITIF if a.total_operasi >= 0 else C.NEGATIF))
        baris.addWidget(w.MiniStat("Arus Kas Investasi", theme.money(a.total_investasi),
                                   C.POSITIF if a.total_investasi >= 0 else C.NEGATIF))
        baris.addWidget(w.MiniStat("Arus Kas Pendanaan", theme.money(a.total_pendanaan),
                                   C.POSITIF if a.total_pendanaan >= 0 else C.NEGATIF))
        baris.addWidget(w.MiniStat("Kas Akhir", theme.money(a.kas_akhir), C.PRIMARY))
        baris.addStretch()
        kartu.body().addLayout(baris)
        lay.addWidget(kartu)

        t = w.Tabel([("Uraian", -1), ("Jumlah (Rp)", 190)])
        # Keterangan ini tampil saat tabel masih kosong, supaya
        # pengguna tahu langkah berikutnya.
        t.set_pesan_kosong(
            "Belum ada data untuk dilaporkan."
            "\n\n"
            "Catat dulu transaksi pada menu Jurnal Umum, Penjualan, atau "
            "Pembelian. Laporan akan terisi sendiri.")

        baris_t, warna = [], {}

        def tambah(label, nilai, tebal=False, indent=0):
            idx = len(baris_t)
            baris_t.append(["    " * indent + label, theme.money(nilai)])
            if tebal:
                warna[idx] = C.PRIMARY

        tambah("AKTIVITAS OPERASI", 0, True)
        for label, nilai in a.operasi_masuk:
            tambah(f"Penerimaan - {label}", nilai, indent=1)
        for label, nilai in a.operasi_keluar:
            tambah(f"Pengeluaran - {label}", -nilai, indent=1)
        tambah("Arus Kas Bersih dari Aktivitas Operasi", a.total_operasi, True)

        tambah("AKTIVITAS INVESTASI", 0, True)
        for label, nilai in a.investasi_masuk:
            tambah(f"Penerimaan - {label}", nilai, indent=1)
        for label, nilai in a.investasi_keluar:
            tambah(f"Pengeluaran - {label}", -nilai, indent=1)
        tambah("Arus Kas Bersih dari Aktivitas Investasi", a.total_investasi, True)

        tambah("AKTIVITAS PENDANAAN", 0, True)
        for label, nilai in a.pendanaan_masuk:
            tambah(f"Penerimaan - {label}", nilai, indent=1)
        for label, nilai in a.pendanaan_keluar:
            tambah(f"Pengeluaran - {label}", -nilai, indent=1)
        tambah("Arus Kas Bersih dari Aktivitas Pendanaan", a.total_pendanaan, True)

        tambah("KENAIKAN/(PENURUNAN) KAS", a.kenaikan_kas, True)
        tambah("Kas pada Awal Periode", a.kas_awal)
        tambah("KAS PADA AKHIR PERIODE", a.kas_akhir, True)

        t.isi(baris_t, warna_baris=warna, align_kanan={1})
        t.setMinimumHeight(120)
        lay.addWidget(t, 1)

        if not a.seimbang:
            lay.addWidget(w.InfoBanner(
                f"Selisih {theme.money(a.selisih)} antara perhitungan arus kas dan "
                "saldo kas akhir. Kemungkinan ada transaksi kas yang lawan akunnya "
                "belum terpetakan, atau saldo awal akun kas belum diisi.",
                "warning", "Perlu penelusuran"))

        if self.ctx.beginner:
            lay.addWidget(w.HelpPanel(
                "Cara membaca Arus Kas",
                "Laporan ini menjawab pertanyaan: 'ke mana uang saya pergi?'\n\n"
                "Dibagi tiga aktivitas:\n"
                "• OPERASI - uang dari kegiatan usaha sehari-hari (jualan, bayar beban). "
                "Ini yang paling penting: harus positif.\n"
                "• INVESTASI - uang untuk membeli/jual aset tetap.\n"
                "• PENDANAAN - uang dari/ke pemilik dan bank (modal, pinjaman, dividen).\n\n"
                "Usaha sehat biasanya memiliki arus kas operasi yang positif dan "
                "cukup untuk membiayai investasi.",
                "PSAK 2 - laporan arus kas; SAK EMKM."))

        lay.addStretch()

    # ==================================================================
    # PERUBAHAN EKUITAS
    # ==================================================================
    def _isi_ekuitas(self, cid):
        self._bersihkan(self.tab_ekuitas)
        lay = self.tab_ekuitas.layout()
        tahun = self.ctx.tahun
        data = services.laporan_perubahan_ekuitas(cid, tahun)

        t = w.Tabel([("Uraian", -1), ("Jumlah (Rp)", 200)])
        # Keterangan ini tampil saat tabel masih kosong, supaya
        # pengguna tahu langkah berikutnya.
        t.set_pesan_kosong(
            "Belum ada data untuk dilaporkan."
            "\n\n"
            "Catat dulu transaksi pada menu Jurnal Umum, Penjualan, atau "
            "Pembelian. Laporan akan terisi sendiri.")

        baris, warna = [], {}
        for d in data:
            idx = len(baris)
            baris.append([d["uraian"], theme.money(d["nilai"])])
            if d.get("tebal"):
                warna[idx] = C.PRIMARY
        t.isi(baris, warna_baris=warna, align_kanan={1})
        t.setMinimumHeight(120)
        lay.addWidget(t, 1)

        if self.ctx.beginner:
            lay.addWidget(w.HelpPanel(
                "Cara membaca Perubahan Ekuitas",
                "Laporan ini menjelaskan mengapa ekuitas (kekayaan bersih pemilik) "
                "berubah selama satu periode.\n\n"
                "Ekuitas bertambah dari: setoran modal dan laba bersih.\n"
                "Ekuitas berkurang dari: dividen yang dibagikan dan prive "
                "(penarikan pemilik).\n\n"
                "Laporan ini menjembatani laba pada Laba Rugi dengan perubahan "
                "ekuitas pada Neraca.",
                "PSAK 1 - laporan perubahan ekuitas."))
        lay.addStretch()

    # ==================================================================
    # NERACA SALDO
    # ==================================================================
    def _isi_neraca_saldo(self, cid):
        self._bersihkan(self.tab_neraca_saldo)
        lay = self.tab_neraca_saldo.layout()
        tahun, bulan = self.ctx.tahun, self.periode()
        data = services.laporan_neraca_saldo(cid, tahun, bulan)

        t = w.Tabel([
            ("Kode", 75), ("Nama Akun", -1), ("Tipe", 100), ("Normal", 75),
            ("Saldo Awal", 140), ("Debit", 140), ("Kredit", 140), ("Saldo Akhir", 150),
        ])
        # Keterangan ini tampil saat tabel masih kosong, supaya
        # pengguna tahu langkah berikutnya.
        t.set_pesan_kosong(
            "Belum ada data untuk dilaporkan."
            "\n\n"
            "Catat dulu transaksi pada menu Jurnal Umum, Penjualan, atau "
            "Pembelian. Laporan akan terisi sendiri.")

        baris, warna = [], {}
        for d in data:
            if (d.saldo_awal == 0 and d.debit == 0 and d.kredit == 0):
                continue
            idx = len(baris)
            baris.append([d.kode, d.nama, d.tipe, d.normal,
                          theme.money(d.saldo_awal), theme.money(d.debit),
                          theme.money(d.kredit), theme.money(d.saldo_akhir_normal)])
            if d.perlakuan_fiskal in ("Non-Deductible (+)", "Final Income (-)",
                                      "Review Fiskal"):
                warna[idx] = C.WARNING

        td = sum(d.debit for d in data)
        tk = sum(d.kredit for d in data)
        idx_total = len(baris)
        baris.append(["", "TOTAL MUTASI", "", "", "", theme.money(td),
                      theme.money(tk), ""])
        warna[idx_total] = C.PRIMARY

        t.isi(baris, warna_baris=warna, align_kanan={4, 5, 6, 7})
        t.setMinimumHeight(120)
        lay.addWidget(t, 1)

        status = QFrame()
        seimbang = abs(td - tk) < 0.5
        theme.latar(status, f"background: {C.SUCCESS_BG if seimbang else C.DANGER_BG}; "
            f"border: 1px solid {'#B8E6D5' if seimbang else '#F5C2C2'}; "
            "border-radius: 8px;")
        sl = QHBoxLayout(status)
        sl.setContentsMargins(16, 12, 16, 12)
        l = QLabel(f"{'simpan' if seimbang else 'hapus'} Total debit {theme.money(td)} "
                   f"{'=' if seimbang else '≠'} total kredit {theme.money(tk)}")
        l.setStyleSheet(f"color: {C.SUCCESS if seimbang else C.DANGER}; "
                        "font-weight: 700; background: transparent;")
        sl.addWidget(l)
        sl.addStretch()
        lay.addWidget(status)

        if self.ctx.beginner:
            lay.addWidget(w.HelpPanel(
                "Cara membaca Neraca Saldo",
                "Neraca saldo adalah daftar semua akun beserta saldonya. Fungsinya "
                "untuk MEMASTIKAN total debit sama dengan total kredit.\n\n"
                "• Saldo Awal - posisi akun pada awal periode\n"
                "• Debit / Kredit - mutasi selama periode\n"
                "• Saldo Akhir - posisi akhir (disajikan pada sisi normal akun)\n\n"
                "Baris berwarna kuning menandai akun yang memerlukan perhatian "
                "khusus saat rekonsiliasi fiskal.",
                "Pasal 28 UU KUP - pembukuan harus dapat diperiksa."))
        lay.addStretch()

    # ==================================================================
    # BUKU BESAR
    # ==================================================================
    def _isi_buku_besar(self, cid):
        self._bersihkan(self.tab_buku_besar)
        lay = self.tab_buku_besar.layout()

        baris_pilih = QHBoxLayout()
        baris_pilih.setSpacing(11)
        baris_pilih.addWidget(w.label("Pilih Akun:", objek="FormLabel"))
        self.cmb_akun = w.combo_akun(cid)
        self.cmb_akun.setMinimumWidth(320)
        self.cmb_akun.currentIndexChanged.connect(self._muat_buku_besar)
        baris_pilih.addWidget(self.cmb_akun)
        baris_pilih.addStretch()
        lay.addLayout(baris_pilih)

        self.area_bb = QWidget()
        self.area_bb_lay = QVBoxLayout(self.area_bb)
        self.area_bb_lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.area_bb)
        self._muat_buku_besar()

    def _muat_buku_besar(self):
        while self.area_bb_lay.count():
            it = self.area_bb_lay.takeAt(0)
            wdg = it.widget()
            if wdg is not None:
                wdg.setParent(None)
                wdg.deleteLater()

        cid = self.ctx.company_id
        kode = self.cmb_akun.currentData() if hasattr(self, "cmb_akun") else None
        if not cid or not kode:
            return

        data = services.buku_besar(cid, kode, self.ctx.tahun, self.periode())
        akun = services.get_account(cid, kode)

        if akun and akun["deskripsi"]:
            self.area_bb_lay.addWidget(w.HelpPanel(
                f"{akun['kode']} - {akun['nama']}", akun["deskripsi"],
                f"Perlakuan fiskal: {akun['perlakuan_fiskal']}"))

        t = w.Tabel([
            ("Tanggal", 105), ("No. Bukti", 130), ("Keterangan", -1),
            ("Debit", 140), ("Kredit", 140), ("Saldo", 150),
        ])
        # Keterangan ini tampil saat tabel masih kosong, supaya
        # pengguna tahu langkah berikutnya.
        t.set_pesan_kosong(
            "Belum ada data untuk dilaporkan."
            "\n\n"
            "Catat dulu transaksi pada menu Jurnal Umum, Penjualan, atau "
            "Pembelian. Laporan akan terisi sendiri.")

        baris, warna = [], {}
        for i, d in enumerate(data):
            idx = len(baris)
            baris.append([
                theme.tanggal_id(d["tanggal"]) if not d.get("awal") else "",
                d["no_bukti"], d["keterangan"],
                theme.money(d["debit"]) if d["debit"] else "",
                theme.money(d["kredit"]) if d["kredit"] else "",
                theme.money(d["saldo"]),
            ])
            if d.get("awal"):
                warna[idx] = C.PRIMARY
        t.isi(baris, warna_baris=warna, align_kanan={3, 4, 5})
        t.setMinimumHeight(120)
        self.area_bb_lay.addWidget(t)

        total_d = sum(d["debit"] for d in data)
        total_k = sum(d["kredit"] for d in data)
        saldo_akhir = data[-1]["saldo"] if data else 0

        kartu = w.Card()
        b = QHBoxLayout()
        b.setSpacing(30)
        b.addWidget(w.MiniStat("Total Debit", theme.money(total_d)))
        b.addWidget(w.MiniStat("Total Kredit", theme.money(total_k)))
        b.addWidget(w.MiniStat("Saldo Akhir", theme.money(saldo_akhir), C.PRIMARY))
        b.addStretch()
        kartu.body().addLayout(b)
        self.area_bb_lay.addWidget(kartu)
        self.area_bb_lay.addStretch()

    # ==================================================================
    # EKSPOR
    # ==================================================================
    def _kumpulkan_data_ekspor(self) -> list[tuple[str, list[list]]]:
        """Siapkan seluruh tabel laporan untuk diekspor."""
        cid, tahun, bulan = self.ctx.company_id, self.ctx.tahun, self.periode()
        comp = services.get_company(cid)
        nama_periode = (config.MONTH_NAMES_ID[bulan - 1] + f" {tahun}"
                        if bulan else f"Tahun {tahun}")
        hasil: list[tuple[str, list[list]]] = []

        # identitas
        hasil.append(("Identitas", [
            ["Keterangan", "Nilai"],
            ["Nama Entitas", comp["nama"]],
            ["Bentuk Badan", config.ENTITY_TYPES.get(comp["bentuk"], {}).get("nama", comp["bentuk"])],
            ["NPWP", comp["npwp"] or "-"],
            ["Periode Laporan", nama_periode],
            ["Status PKP", "Ya" if comp["status_pkp"] else "Tidak"],
            ["Skema PPh", comp["skema_pph"]],
            ["SAK yang Dipakai", config.ENTITY_TYPES.get(comp["bentuk"], {}).get("sak", "-")],
        ]))

        # laba rugi
        lr = services.laporan_laba_rugi(cid, tahun, bulan)
        baris_lr = [["Uraian", "Jumlah (Rp)"]]
        baris_lr += [
            ["Pendapatan Usaha", lr.pendapatan_usaha],
            ["Harga Pokok Penjualan", -lr.hpp],
            ["LABA KOTOR", lr.laba_kotor],
            ["Beban Operasional", -lr.beban_operasional],
            ["LABA OPERASIONAL", lr.laba_operasional],
            ["Pendapatan Lain-lain", lr.pendapatan_lain],
            ["Beban Lain-lain", -lr.beban_lain],
            ["LABA SEBELUM PAJAK", lr.laba_sebelum_pajak],
            ["Beban Pajak Kini (estimasi)", -lr.beban_pajak],
            ["LABA BERSIH SETELAH PAJAK", lr.laba_bersih],
        ]
        hasil.append(("Laba Rugi", baris_lr))

        # neraca
        n = services.laporan_neraca(cid, tahun, bulan)
        baris_n = [["Keterangan", "Jumlah (Rp)"]]
        baris_n.append(["ASET", ""])
        for kode, (nama, nilai) in sorted(n.aset_lancar.items()):
            if nilai:
                baris_n.append([f"{kode} {nama}", nilai])
        for kode, (nama, nilai) in sorted(n.aset_tetap.items()):
            if nilai:
                baris_n.append([f"{kode} {nama}", nilai])
        for kode, (nama, nilai) in sorted(n.aset_lain.items()):
            if nilai:
                baris_n.append([f"{kode} {nama}", nilai])
        baris_n.append(["TOTAL ASET", n.total_aset])
        baris_n.append(["LIABILITAS", ""])
        for kode, (nama, nilai) in sorted(n.liabilitas_pendek.items()):
            if nilai:
                baris_n.append([f"{kode} {nama}", nilai])
        for kode, (nama, nilai) in sorted(n.liabilitas_panjang.items()):
            if nilai:
                baris_n.append([f"{kode} {nama}", nilai])
        baris_n.append(["TOTAL LIABILITAS", n.total_liabilitas])
        baris_n.append(["EKUITAS", ""])
        baris_n.append(["Modal Disetor", n.modal])
        baris_n.append(["Saldo Laba", n.saldo_laba])
        baris_n.append(["Laba Tahun Berjalan", n.laba_tahun_berjalan])
        if n.prive:
            baris_n.append(["Prive", -n.prive])
        baris_n.append(["TOTAL EKUITAS", n.total_ekuitas])
        baris_n.append(["TOTAL LIABILITAS & EKUITAS", n.total_liabilitas_ekuitas])
        hasil.append(("Neraca", baris_n))

        # neraca saldo
        ns = services.laporan_neraca_saldo(cid, tahun, bulan)
        baris_ns = [["Kode", "Nama Akun", "Tipe", "Saldo Awal", "Debit", "Kredit", "Saldo Akhir"]]
        for d in ns:
            if d.saldo_awal == 0 and d.debit == 0 and d.kredit == 0:
                continue
            baris_ns.append([d.kode, d.nama, d.tipe, d.saldo_awal, d.debit,
                             d.kredit, d.saldo_akhir_normal])
        hasil.append(("Neraca Saldo", baris_ns))

        # arus kas
        a = services.laporan_arus_kas(cid, tahun, bulan)
        baris_a = [["Uraian", "Jumlah (Rp)"]]
        for label, nilai in a.operasi_masuk:
            baris_a.append([f"Penerimaan operasi - {label}", nilai])
        for label, nilai in a.operasi_keluar:
            baris_a.append([f"Pengeluaran operasi - {label}", -nilai])
        baris_a.append(["Arus Kas Operasi", a.total_operasi])
        for label, nilai in a.investasi_masuk:
            baris_a.append([f"Penerimaan investasi - {label}", nilai])
        for label, nilai in a.investasi_keluar:
            baris_a.append([f"Pengeluaran investasi - {label}", -nilai])
        baris_a.append(["Arus Kas Investasi", a.total_investasi])
        for label, nilai in a.pendanaan_masuk:
            baris_a.append([f"Penerimaan pendanaan - {label}", nilai])
        for label, nilai in a.pendanaan_keluar:
            baris_a.append([f"Pengeluaran pendanaan - {label}", -nilai])
        baris_a.append(["Arus Kas Pendanaan", a.total_pendanaan])
        baris_a.append(["Kenaikan/(Penurunan) Kas", a.kenaikan_kas])
        baris_a.append(["Kas Awal", a.kas_awal])
        baris_a.append(["Kas Akhir", a.kas_akhir])
        hasil.append(("Arus Kas", baris_a))

        # jurnal
        jurnal = services.list_jurnal(cid, tahun, bulan, limit=5000)
        baris_j = [["Tanggal", "No. Bukti", "Keterangan", "Debit", "Kredit"]]
        for e in jurnal:
            baris_j.append([e["tanggal"], e["no_bukti"], e["keterangan"],
                            e["total_debit"], e["total_kredit"]])
        hasil.append(("Jurnal", baris_j))

        return hasil

    def _ekspor(self, jenis: str):
        cid = self.ctx.company_id
        if not cid:
            QMessageBox.information(self, "Belum ada perusahaan",
                                    "Buat profil perusahaan terlebih dahulu.")
            return
        comp = services.get_company(cid)
        tahun, bulan = self.ctx.tahun, self.periode()
        periode_teks = (f"{config.MONTH_NAMES_ID[bulan - 1]} {tahun}" if bulan
                        else f"Tahun {tahun}")

        config.ensure_dirs()
        nama_berkas = (f"Laporan_{comp['nama'].replace(' ', '_')}_"
                       f"{periode_teks.replace(' ', '_')}")

        try:
            data = self._kumpulkan_data_ekspor()
        except Exception as e:
            QMessageBox.critical(self, "Gagal menyiapkan data", str(e))
            return

        if jenis == "excel":
            path, _ = QFileDialog.getSaveFileName(
                self, "Simpan Laporan Excel",
                str(config.EXPORT_DIR / f"{nama_berkas}.xlsx"),
                "Berkas Excel (*.xlsx)")
            if not path:
                return
            try:
                ekspor_excel(comp["nama"], data, path)
            except Exception as e:
                QMessageBox.critical(self, "Gagal mengekspor", str(e))
                return
        elif jenis == "pdf":
            path, _ = QFileDialog.getSaveFileName(
                self, "Simpan Laporan PDF",
                str(config.EXPORT_DIR / f"{nama_berkas}.pdf"),
                "Berkas PDF (*.pdf)")
            if not path:
                return
            try:
                ekspor_pdf(f"Laporan Keuangan - {comp['nama']}",
                           f"Periode {periode_teks} · NPWP {comp['npwp'] or '-'}",
                           data, path)
            except Exception as e:
                QMessageBox.critical(self, "Gagal mengekspor", str(e))
                return
        else:
            return

        if QMessageBox.question(
                self, "Ekspor selesai",
                f"Laporan berhasil disimpan:\n{path}\n\nBuka folder penyimpanan?",
                QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.dirname(path)))
