"""
Ekspor Excel dan cetak A4 untuk seluruh halaman aplikasi.

Sebelum modul ini ada, ekspor Excel hanya tersedia pada tiga tempat
(Laporan, Pengaturan, dan daftar aging penjualan), sedangkan cetak sama
sekali belum ada: pengguna hanya dapat menyimpan PDF lalu mencetaknya
sendiri dari aplikasi lain.

Modul ini menyediakan satu jalur untuk keduanya, sehingga seluruh halaman
memakai cara yang sama dan tidak ada yang tertinggal.

Excel:
  - Satu lembar per tabel, dengan kop berisi nama perusahaan dan periode.
  - Angka disimpan sebagai angka, bukan teks, supaya dapat dijumlahkan dan
    dibuatkan grafik di Excel.
  - Lebar kolom disesuaikan isinya, dan baris judul dibekukan.
  - Nama lembar dibersihkan dari karakter yang dilarang Excel.

Cetak:
  - Kertas A4 tegak atau mendatar, dengan pilihan pencetak bawaan sistem.
  - Tabel dipotong menjadi beberapa halaman dengan baris judul yang
    diulang di setiap halaman, sehingga tetap terbaca saat banyak baris.
  - Angka rata kanan, teks rata kiri.
  - Pratinjau bawaan sistem dipakai lebih dulu, supaya pengguna dapat
    memeriksa hasilnya sebelum kertas terpakai.
"""
from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QMarginsF, QRectF, Qt
from PySide6.QtGui import (QImage, QPainter, QPageLayout, QPageSize,
                           QTextDocument)
from PySide6.QtPrintSupport import QPrinter, QPrintPreviewDialog

# Karakter yang tidak diperbolehkan pada nama lembar Excel.
KARAKTER_TERLARANG = r"[:\\/?*\[\]]"


# ==========================================================================
# EXCEL
# ==========================================================================
def nama_lembar_aman(nama: str, dipakai: set = None) -> str:
    """
    Bersihkan nama lembar Excel.

    Excel menolak nama lembar yang memuat karakter tertentu, lebih dari 31
    huruf, atau sama dengan nama lembar lain. Nama yang bermasalah membuat
    seluruh berkas gagal disimpan, jadi dibersihkan lebih dulu.
    """
    bersih = re.sub(KARAKTER_TERLARANG, "-", str(nama or "")).strip()
    bersih = bersih.strip("'")
    if not bersih:
        bersih = "Data"
    bersih = bersih[:31]
    if dipakai is not None:
        dasar = bersih
        urut = 2
        while bersih.lower() in dipakai:
            akhiran = f" ({urut})"
            bersih = dasar[:31 - len(akhiran)] + akhiran
            urut += 1
        dipakai.add(bersih.lower())
    return bersih


def ekspor_excel(judul: str, tabel_data: list, path: str,
                 subjudul: str = "", nama_perusahaan: str = "") -> Path:
    """
    Simpan beberapa tabel ke satu berkas Excel, satu lembar per tabel.

    Setiap tabel diberi kop berisi judul, nama perusahaan, dan waktu
    pembuatan, supaya berkas yang sudah tersimpan masih dapat dikenali
    asalnya saat dibuka beberapa bulan kemudian.
    """
    try:
        import openpyxl
        from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
        from openpyxl.utils import get_column_letter
    except ImportError:
        raise RuntimeError("Modul openpyxl belum terpasang. "
                           "Jalankan: pip install openpyxl")

    tujuan = Path(path)
    tujuan.parent.mkdir(parents=True, exist_ok=True)

    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    judul_font = Font(bold=True, size=13, color="1E282D")
    kop_font = Font(size=9, color="556577")
    kepala_font = Font(bold=True, color="FFFFFF", size=11)
    kepala_fill = PatternFill("solid", fgColor="1B4F8A")
    belang = PatternFill("solid", fgColor="F7F9FB")
    tipis = Side(style="thin", color="DFE4EA")
    garis = Border(left=tipis, right=tipis, top=tipis, bottom=tipis)
    kanan = Alignment(horizontal="right", vertical="center")
    kiri = Alignment(horizontal="left", vertical="center")
    tengah = Alignment(horizontal="center", vertical="center")

    dipakai: set = set()
    for nama_lembar, baris in tabel_data:
        ws = wb.create_sheet(title=nama_lembar_aman(nama_lembar, dipakai))

        # Kop: judul, perusahaan, waktu.
        ws.cell(row=1, column=1, value=judul).font = judul_font
        baris_kop = [subjudul] if subjudul else []
        if nama_perusahaan and nama_perusahaan != judul:
            baris_kop.insert(0, nama_perusahaan)
        baris_kop.append(
            f"Dibuat {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        ws.cell(row=2, column=1, value=" · ".join(baris_kop)).font = kop_font
        ws.cell(row=3, column=1, value=nama_lembar).font = Font(
            bold=True, size=11, color="1E282D")

        mulai = 5
        lebar = max((len(r) for r in baris), default=1)

        for r, data in enumerate(baris, start=mulai):
            for c, nilai in enumerate(data, start=1):
                sel = ws.cell(row=r, column=c)
                if isinstance(nilai, str) and nilai.startswith("="):
                    # Rumus dari aplikasi tidak diteruskan, supaya berkas
                    # yang dibuka di Excel tidak menjalankan apa pun.
                    sel.value = nilai
                elif isinstance(nilai, (int, float)) and not isinstance(nilai, bool):
                    sel.value = nilai
                    sel.number_format = '#,##0'
                elif nilai is None:
                    sel.value = ""
                else:
                    sel.value = str(nilai)
                sel.border = garis
                if r == mulai:
                    sel.font = kepala_font
                    sel.fill = kepala_fill
                    sel.alignment = tengah
                else:
                    sel.alignment = kanan if isinstance(nilai, (int, float)) \
                        and not isinstance(nilai, bool) else kiri
                    if (r - mulai) % 2 == 1:
                        sel.fill = belang

        # Lebar kolom mengikuti isi terpanjang, dibatasi supaya tidak ada
        # kolom yang terlalu lebar.
        for c in range(1, lebar + 1):
            terpanjang = 0
            for r in range(mulai, mulai + len(baris)):
                nilai = ws.cell(row=r, column=c).value
                if nilai is not None:
                    terpanjang = max(terpanjang, len(str(nilai)))
            ws.column_dimensions[get_column_letter(c)].width = min(
                max(12, terpanjang + 3), 42)

        # Baris judul dibekukan supaya tetap terlihat saat digulir.
        ws.freeze_panes = ws.cell(row=mulai + 1, column=1)

    wb.save(str(tujuan))
    return tujuan


# ==========================================================================
# CETAK A4
# ==========================================================================
def _teks_tabel_html(judul: str, subjudul: str, tabel_data: list,
                     kop: bool = True) -> str:
    """
    Susun isi cetak dalam bentuk HTML.

    HTML dipakai karena Qt sudah dapat memecahnya menjadi halaman A4
    dengan sendirinya, sehingga tabel panjang tidak perlu dipecah manual.
    """
    bagian = []
    if kop:
        bagian.append(
            f'<div class="judul">{_aman_html(judul)}</div>')
        if subjudul:
            bagian.append(
                f'<div class="subjudul">{_aman_html(subjudul)}</div>')

    for nama, baris in tabel_data:
        bagian.append(f'<div class="nama-tabel">{_aman_html(nama)}</div>')
        if not baris:
            bagian.append('<div class="kosong">Belum ada data.</div>')
            continue
        bagian.append('<table>')
        bagian.append("<thead><tr>")
        for kolom in baris[0]:
            bagian.append(f"<th>{_aman_html(kolom)}</th>")
        bagian.append("</tr></thead><tbody>")
        for r, data in enumerate(baris[1:]):
            kelas = ' class="belang"' if r % 2 else ""
            bagian.append(f"<tr{kelas}>")
            for nilai in data:
                angka = isinstance(nilai, (int, float)) and \
                    not isinstance(nilai, bool)
                kelas_sel = ' class="angka"' if angka else ""
                teks = _angka_teks(nilai) if angka else _aman_html(nilai)
                bagian.append(f"<td{kelas_sel}>{teks}</td>")
            bagian.append("</tr>")
        bagian.append("</tbody></table>")

    bagian.append(
        f'<div class="kaki">Dicetak '
        f'{datetime.now().strftime("%d/%m/%Y %H:%M")}</div>')

    return """<html><head><style>
    body { font-family: 'Segoe UI', Arial, sans-serif; color: #1E282D;
           font-size: 9pt; }
    .judul { font-size: 15pt; font-weight: bold; color: #1E282D; }
    .subjudul { font-size: 9pt; color: #556577; margin-top: 2px; }
    .nama-tabel { font-size: 11pt; font-weight: bold; margin-top: 14px;
                  color: #1E282D; }
    table { border-collapse: collapse; width: 100%%; margin-top: 6px; }
    th { background: #1B4F8A; color: #FFFFFF; font-size: 8.5pt;
         padding: 5px 6px; text-align: left; border: 1px solid #DFE4EA; }
    td { padding: 4px 6px; border: 1px solid #DFE4EA; font-size: 8.5pt; }
    td.angka { text-align: right; }
    tr.belang td { background: #F7F9FB; }
    .kosong { color: #556577; font-style: italic; margin-top: 4px; }
    .kaki { margin-top: 16px; font-size: 7.5pt; color: #5A6B7D; }
    </style></head><body>%s</body></html>""" % "".join(bagian)


def _aman_html(nilai) -> str:
    """Ubah nilai menjadi teks HTML yang aman ditampilkan."""
    teks = "" if nilai is None else str(nilai)
    return (teks.replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;"))


def _angka_teks(nilai) -> str:
    """Format angka dengan pemisah ribuan gaya Indonesia."""
    if isinstance(nilai, float) and nilai.is_integer():
        nilai = int(nilai)
    return f"{nilai:,}".replace(",", ".")


def _dokumen_cetak(judul: str, subjudul: str, tabel_data: list,
                   kop: bool = True) -> QTextDocument:
    doc = QTextDocument()
    doc.setHtml(_teks_tabel_html(judul, subjudul, tabel_data, kop))
    doc.setDocumentMargin(0)
    return doc


def _siapkan_printer(printer: QPrinter, mendatar: bool = False,
                     margin_mm: float = 12) -> None:
    """Atur kertas A4 beserta marginnya."""
    ukuran = QPageSize(QPageSize.A4)
    arah = (QPageLayout.Landscape if mendatar
            else QPageLayout.Portrait)
    printer.setPageSize(ukuran)
    printer.setPageOrientation(arah)
    printer.setPageMargins(QMarginsF(margin_mm, margin_mm, margin_mm, margin_mm),
                           QPageLayout.Millimeter)
    printer.setDocName("AkunTuntas")


def cetak(parent, judul: str, subjudul: str, tabel_data: list,
          mendatar: bool = False, langsung: bool = False) -> bool:
    """
    Cetak tabel ke kertas A4.

    Bila langsung bernilai salah, pratinjau bawaan sistem ditampilkan lebih
    dulu sehingga pengguna dapat memeriksa hasilnya dan memilih pencetak.
    Bila langsung bernilai benar, hasilnya dikirim ke pencetak bawaan.

    Kembaliannya True bila pengguna menyelesaikan pencetakan, dan False
    bila dibatalkan.
    """
    doc = _dokumen_cetak(judul, subjudul, tabel_data)

    printer = QPrinter(QPrinter.HighResolution)
    _siapkan_printer(printer, mendatar)

    if langsung:
        from PySide6.QtPrintSupport import QPrintDialog
        dialog = QPrintDialog(printer, parent)
        dialog.setWindowTitle("Cetak")
        if dialog.exec() != QPrintDialog.Accepted:
            return False
        _gambar_dokumen(doc, printer)
        return True

    pratinjau = QPrintPreviewDialog(printer, parent)
    pratinjau.setWindowTitle("Pratinjau Cetak (A4)")
    pratinjau.resize(1000, 720)
    pratinjau.paintRequested.connect(lambda p: _gambar_dokumen(doc, p))
    pratinjau.exec()
    return True


def _gambar_dokumen(doc: QTextDocument, printer: QPrinter) -> None:
    """
    Gambar isi dokumen ke halaman printer.

    Ukuran halaman diambil pada satuan yang sama dengan ukuran kertas
    printer, yaitu satuan titik (1/72 inci). Bila ukurannya diambil pada
    satuan piksel layar sementara printer memakai resolusi tinggi, lebar
    halaman menjadi jauh lebih kecil dari area cetak sebenarnya sehingga
    seluruh isi dianggap muat dalam satu halaman dan tabel panjang tidak
    pernah terpecah.
    """
    area = printer.pageRect(QPrinter.Point)
    doc.setPageSize(QRectF(0, 0, area.width(), area.height()).size())
    doc.print_(printer)


def cetak_kwitansi(parent, judul: str, baris_kwitansi: list,
                   catatan: str = "", mendatar: bool = False) -> bool:
    """
    Cetak satu dokumen (kwitansi, invoice, atau nota) pada kertas A4.

    Baris dokumen disusun sebagai pasangan label dan isi, sehingga
    tampilannya rapi seperti kwitansi pada umumnya.
    """
    isi = []
    isi.append(f'<div class="judul">{_aman_html(judul)}</div>')
    isi.append('<table class="kwitansi">')
    for label, nilai in baris_kwitansi:
        angka = isinstance(nilai, (int, float)) and not isinstance(nilai, bool)
        teks = _angka_teks(nilai) if angka else _aman_html(nilai)
        kelas = ' class="angka"' if angka else ""
        isi.append(
            f'<tr><td class="label">{_aman_html(label)}</td>'
            f'<td{kelas}>{teks}</td></tr>')
    isi.append("</table>")
    if catatan:
        isi.append(f'<div class="catatan">{_aman_html(catatan)}</div>')
    isi.append(
        f'<div class="kaki">Dicetak '
        f'{datetime.now().strftime("%d/%m/%Y %H:%M")}</div>')

    html = """<html><head><style>
    body { font-family: 'Segoe UI', Arial, sans-serif; color: #1E282D;
           font-size: 10pt; }
    .judul { font-size: 17pt; font-weight: bold; color: #1E282D;
             margin-bottom: 12px; }
    table.kwitansi { border-collapse: collapse; width: 100%%; }
    table.kwitansi td { padding: 7px 8px; border-bottom: 1px solid #DFE4EA;
                        font-size: 10pt; }
    td.label { color: #556577; width: 38%%; }
    td.angka { text-align: right; font-weight: bold; }
    .catatan { margin-top: 14px; padding: 10px; background: #F7F9FB;
               border-left: 3px solid #B07D4B; font-size: 9pt;
               color: #1E282D; }
    .kaki { margin-top: 18px; font-size: 8pt; color: #5A6B7D; }
    </style></head><body>%s</body></html>""" % "".join(isi)

    doc = QTextDocument()
    doc.setHtml(html)
    doc.setDocumentMargin(0)

    printer = QPrinter(QPrinter.HighResolution)
    _siapkan_printer(printer, mendatar, margin_mm=16)
    from PySide6.QtPrintSupport import QPrintDialog
    dialog = QPrintDialog(printer, parent)
    dialog.setWindowTitle(f"Cetak {judul}")
    if dialog.exec() != QPrintDialog.Accepted:
        return False
    _gambar_dokumen(doc, printer)
    return True


def simpan_pdf(parent, judul: str, subjudul: str, tabel_data: list,
               path: str, mendatar: bool = False) -> Path:
    """
    Simpan tabel ke berkas PDF berukuran A4, tanpa membuka pencetak.

    Dipakai bila pengguna ingin menyimpan berkasnya lebih dulu.
    """
    doc = _dokumen_cetak(judul, subjudul, tabel_data)
    printer = QPrinter(QPrinter.HighResolution)
    _siapkan_printer(printer, mendatar)
    printer.setOutputFormat(QPrinter.PdfFormat)
    printer.setOutputFileName(str(path))
    _gambar_dokumen(doc, printer)
    return Path(path)


# ==========================================================================
# PINTASAN UNTUK HALAMAN
# ==========================================================================
# Halaman halaman aplikasi memakai dua fungsi di bawah ini supaya caranya
# seragam dan tidak ada yang perlu menulis sendiri. Keduanya sudah memuat
# dialog penyimpanan, pemeriksaan galat, dan penawaran membuka berkas.
def ekspor_halaman(parent, judul: str, subjudul: str, tabel_data: list,
                   nama_berkas: str = "Data") -> bool:
    """
    Tawarkan penyimpanan Excel dan PDF dari data sebuah halaman.

    Kembaliannya True bila ada berkas yang tersimpan.
    """
    from PySide6.QtWidgets import QFileDialog, QMessageBox
    from .. import config

    if not tabel_data:
        QMessageBox.information(
            parent, "Belum ada data",
            "Tidak ada data untuk diekspor pada halaman ini.")
        return False

    config.ensure_dirs()
    aman = re.sub(r"[^A-Za-z0-9_\- ]", "", str(nama_berkas)).strip() or "Data"
    awal = config.EXPORT_DIR / f"{aman}_{datetime.now():%Y%m%d}.xlsx"

    path, _ = QFileDialog.getSaveFileName(
        parent, "Simpan sebagai Excel", str(awal),
        "Berkas Excel (*.xlsx)")
    if not path:
        return False

    try:
        ekspor_excel(judul, tabel_data, path, subjudul=subjudul)
    except Exception as e:
        QMessageBox.critical(parent, "Gagal mengekspor", str(e))
        return False

    if QMessageBox.question(
            parent, "Ekspor selesai",
            f"Data berhasil disimpan:\n{path}\n\nBuka folder penyimpanan?",
            QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
        _buka_folder(parent, path)
    return True


def cetak_halaman(parent, judul: str, subjudul: str, tabel_data: list,
                  mendatar: bool = False) -> bool:
    """
    Cetak data sebuah halaman ke kertas A4 melalui pratinjau.

    Pratinjau dipakai lebih dulu supaya pengguna dapat memeriksa hasilnya
    dan memilih pencetak sebelum kertas terpakai.
    """
    from PySide6.QtWidgets import QMessageBox

    if not tabel_data:
        QMessageBox.information(
            parent, "Belum ada data",
            "Tidak ada data untuk dicetak pada halaman ini.")
        return False
    try:
        return cetak(parent, judul, subjudul, tabel_data, mendatar=mendatar)
    except Exception as e:
        QMessageBox.critical(parent, "Gagal mencetak", str(e))
        return False


def simpan_pdf_halaman(parent, judul: str, subjudul: str, tabel_data: list,
                       nama_berkas: str = "Dokumen",
                       mendatar: bool = False) -> bool:
    """Simpan data sebuah halaman sebagai berkas PDF A4."""
    from PySide6.QtWidgets import QFileDialog, QMessageBox
    from .. import config

    if not tabel_data:
        QMessageBox.information(
            parent, "Belum ada data",
            "Tidak ada data untuk disimpan pada halaman ini.")
        return False

    config.ensure_dirs()
    aman = re.sub(r"[^A-Za-z0-9_\- ]", "", str(nama_berkas)).strip() or "Dokumen"
    awal = config.EXPORT_DIR / f"{aman}_{datetime.now():%Y%m%d}.pdf"
    path, _ = QFileDialog.getSaveFileName(
        parent, "Simpan sebagai PDF", str(awal), "Berkas PDF (*.pdf)")
    if not path:
        return False
    try:
        simpan_pdf(parent, judul, subjudul, tabel_data, path, mendatar)
    except Exception as e:
        QMessageBox.critical(parent, "Gagal menyimpan PDF", str(e))
        return False
    if QMessageBox.question(
            parent, "Penyimpanan selesai",
            f"PDF berhasil disimpan:\n{path}\n\nBuka folder penyimpanan?",
            QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
        _buka_folder(parent, path)
    return True


def _buka_folder(parent, path: str) -> None:
    """Buka folder tempat berkas disimpan, memakai penjelajah bawaan."""
    import subprocess
    import sys
    from pathlib import Path as _Path

    folder = str(_Path(path).parent)
    try:
        if sys.platform.startswith("win"):
            os.startfile(folder)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", folder])
        else:
            subprocess.Popen(["xdg-open", folder])
    except Exception:
        # Bila folder tidak dapat dibuka, berkasnya tetap sudah tersimpan.
        pass


def tabel_dari_widget(tabel) -> list:
    """
    Ambil isi sebuah tabel di layar menjadi bentuk yang siap diekspor.

    Dipakai halaman yang datanya hanya ada di tabel, tanpa fungsi
    pengumpul tersendiri.
    """
    if tabel is None:
        return []
    kolom = []
    for c in range(tabel.columnCount()):
        kepala = tabel.horizontalHeaderItem(c)
        kolom.append(kepala.text() if kepala else f"Kolom {c + 1}")

    baris = [kolom]
    for r in range(tabel.rowCount()):
        isi = []
        for c in range(tabel.columnCount()):
            sel = tabel.item(r, c)
            teks = sel.text() if sel else ""
            # Angka dikembalikan sebagai angka supaya dapat dijumlahkan
            # di Excel, bukan sebagai teks.
            angka = _teks_ke_angka(teks)
            isi.append(angka if angka is not None else teks)
        baris.append(isi)
    return baris


def _teks_ke_angka(teks: str):
    """
    Ubah teks angka gaya Indonesia menjadi angka.

    Mengembalikan None bila teksnya bukan angka, supaya teks biasa tetap
    tersimpan sebagai teks.
    """
    if not teks:
        return None
    bersih = str(teks).strip().replace("Rp", "").replace(" ", "")
    if not bersih:
        return None
    # Hanya bentuk angka yang diterima.
    if not re.fullmatch(r"-?[\d.]+(,\d+)?%?", bersih):
        return None
    persen = bersih.endswith("%")
    # Angka gaya Indonesia: titik sebagai pemisah ribuan, koma sebagai
    # pemisah desimal.
    bersih = bersih.rstrip("%").replace(".", "").replace(",", ".")
    try:
        angka = float(bersih)
    except ValueError:
        return None
    if persen:
        return angka / 100
    return int(angka) if angka.is_integer() else angka


def pratinjau_gambar(judul: str, subjudul: str, tabel_data: list,
                     lebar: int = 800) -> QImage:
    """
    Hasilkan gambar pratinjau halaman pertama, untuk diperiksa tanpa
    membuka pencetak. Dipakai oleh alat uji dan pemeriksaan tata letak.

    Ukuran halaman memakai satuan titik, sama seperti pencetakan
    sesungguhnya, supaya hasil pratinjau benar benar menggambarkan apa
    yang akan tercetak.
    """
    doc = _dokumen_cetak(judul, subjudul, tabel_data)
    printer = QPrinter(QPrinter.HighResolution)
    _siapkan_printer(printer)
    printer.setOutputFormat(QPrinter.PdfFormat)
    printer.setOutputFileName("")

    area = printer.pageRect(QPrinter.Point)
    skala = lebar / max(1.0, area.width())
    tinggi = int(area.height() * skala)

    gambar = QImage(lebar, tinggi, QImage.Format_RGB32)
    gambar.fill(Qt.white)
    pelukis = QPainter(gambar)
    try:
        pelukis.setRenderHint(QPainter.Antialiasing, True)
        pelukis.setRenderHint(QPainter.TextAntialiasing, True)
        pelukis.scale(skala, skala)
        doc.setPageSize(QRectF(0, 0, area.width(), area.height()).size())
        doc.drawContents(pelukis,
                         QRectF(0, 0, area.width(), area.height()))
    finally:
        pelukis.end()
    return gambar
