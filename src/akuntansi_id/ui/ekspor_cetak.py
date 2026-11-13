"""
Ekspor dan cetak A4 untuk seluruh halaman aplikasi.

Satu jalur dipakai semua halaman supaya hasilnya seragam: kop perusahaan,
warna yang sama dengan aplikasi, angka rata kanan, baris judul yang diulang
saat tabel berlanjut ke halaman berikutnya, dan nomor halaman di kaki.

Excel:
  - Satu lembar per tabel, angka tetap berupa angka sehingga dapat
    dijumlahkan dan dibuat grafik.
  - Lebar kolom mengikuti isi, baris judul dibekukan, dan saringan otomatis
    dipasang pada tabel.
  - Halaman Excel sudah disiapkan untuk kertas A4: skala muat lebar, judul
    kolom diulang, dan nomor halaman di kaki.

PDF dan cetak:
  - Kertas A4, otomatis mendatar bila tabelnya lebar.
  - Kop berisi merek dan nama perusahaan, kaki berisi waktu dan nomor.
  - Pratinjau ditampilkan lebih dulu sebelum kertas terpakai.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import math
import os
import re
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QByteArray, QBuffer, QMarginsF, QPointF, QRectF, Qt
from PySide6.QtGui import (QColor, QFont, QFontMetricsF, QImage, QPageLayout,
                           QPageSize, QPainter, QPen, QTextDocument)
from PySide6.QtPrintSupport import QPrinter

from .. import config
from . import popup

KARAKTER_TERLARANG = r"[:\\/?*\[\]]"

# QTextDocument menghitung tata letak pada 96 dpi, sedangkan ukuran kertas
# memakai titik (1/72 inci). Semua ukuran lukisan dokumen dikonversi ke
# satuan dokumen (px 96 dpi) agar teks tidak tercetak 33% lebih besar.
SKALA_DOKUMEN = 96.0 / 72.0
MARGIN_MM = 14.0
TINGGI_KOP = 27.0
TINGGI_KAKI = 21.0
# Tinggi blok tanda tangan pada halaman terakhir, dalam titik. Isinya kota
# dan tanggal, ruang tanda tangan, garis, nama, jabatan, serta segel.
TINGGI_TTD = 96.0
WARNA_TINTA = "#222C2F"
WARNA_TEMBAGA = "#7C4A1E"
WARNA_TEMBAGA_MUDA = "#A0622D"
WARNA_TEKS = "#1D2628"
WARNA_MUTED = "#55605E"
WARNA_GARIS = "#E3DCCF"
WARNA_BELANG = "#FCFAF5"
WARNA_TOTAL = "#F6F1E7"
WARNA_GRUP = "#F3EDE4"

_LOGO: QImage | None = None


# ==========================================================================
# ALAT BANTU
# ==========================================================================
def _px(titik: float) -> float:
    """Titik cetak (1/72 inci) ke satuan dokumen QTextDocument (96 dpi)."""
    return titik * SKALA_DOKUMEN


def _keluarga_font() -> str:
    """Nama keluarga font aplikasi, dimuat lebih dulu bila belum."""
    try:
        from . import theme
        theme.pasang_font()
        if theme.FONT_UI:
            return theme.FONT_UI
    except Exception:
        pass
    return "Segoe UI"


def _font(ukuran: float, tebal: int = 400, spasi: float = 0.0) -> QFont:
    """
    Font untuk lukisan langsung pada printer dan untuk ukuran kolom.

    Ukuran dalam titik, lalu diubah ke pixelSize karena QPainter pada
    printer memakai satuan dokumen 96 dpi. pointSize tidak dipakai agar
    ukuran tidak ikut terkalikan skala perangkat.
    """
    f = QFont(_keluarga_font())
    f.setPixelSize(max(1, int(round(_px(ukuran)))))
    f.setWeight(QFont.Weight(int(tebal)))
    if spasi:
        f.setLetterSpacing(QFont.AbsoluteSpacing, _px(spasi))
    return f


def _keluarga_serif() -> str:
    """Huruf judul cetak; jatuh ke Georgia bila huruf bawaan gagal dimuat."""
    try:
        from . import theme
        theme.pasang_font()
        return getattr(theme, "FONT_SERIF", "") or _keluarga_font()
    except Exception:
        return "Georgia"


def _font_serif(ukuran: float, tebal: int = 400, spasi: float = 0.0) -> QFont:
    f = QFont(_keluarga_serif())
    f.setPixelSize(max(1, int(round(_px(ukuran)))))
    f.setWeight(QFont.Weight(int(tebal)))
    if spasi:
        f.setLetterSpacing(QFont.AbsoluteSpacing, _px(spasi))
    return f


def _logo() -> QImage:
    global _LOGO
    if _LOGO is None:
        berkas = config.ASSET_DIR / "app_256.png"
        _LOGO = QImage(str(berkas)) if berkas.exists() else QImage()
    return _LOGO


# ==========================================================================
# IDENTITAS DOKUMEN
# ==========================================================================
def _setelan_cetak_aman() -> dict:
    """Pengaturan cetak dari basis data; aman bila basis data belum siap."""
    bawaan = {
        "air_aktif": True,
        "air_teks": "{perusahaan}",
        "air_pekat": 8,
        "ttd_aktif": True,
        "ttd_nama": "",
        "ttd_jabatan": "",
        "ttd_kota": "",
        "ttd_gambar": "",
    }
    try:
        from .. import db
        hasil = db.setelan_cetak()
        bawaan.update({k: v for k, v in hasil.items() if v is not None})
    except Exception:
        pass
    return bawaan


def _kunci_verifikasi() -> bytes:
    try:
        from .. import db
        return db.kunci_verifikasi_cetak().encode("utf-8")
    except Exception:
        return f"{config.APP_NAME}|{config.APP_VERSION}".encode("utf-8")


def _kode_dokumen(judul: str, subjudul: str, tabel_data: list,
                  perusahaan: str, nama: str = "", jabatan: str = "",
                  kota: str = "") -> str:
    """
    Kode verifikasi dokumen dari isi dan identitas penanda tangan.

    Kode dihitung dengan HMAC-SHA256 memakai kunci rahasia pemasangan, lalu
    dipendekkan menjadi empat kelompok huruf/angka. Isi yang sama pada
    komputer yang sama selalu menghasilkan kode yang sama, sedangkan satu
    angka yang diubah menghasilkan kode lain. Tanggal cetak tidak ikut
    dihitung karena keterangan waktu sudah tercetak di kaki halaman.
    """
    muatan = {
        "judul": str(judul or ""),
        "subjudul": str(subjudul or ""),
        "perusahaan": str(perusahaan or ""),
        "penanda": [str(nama or ""), str(jabatan or ""), str(kota or "")],
        "bagian": [[str(nama_bagian or ""),
                    [list(baris or []) for baris in (bagian or [])]]
                   for nama_bagian, bagian in (tabel_data or [])],
    }
    mentah = json.dumps(muatan, ensure_ascii=False, sort_keys=True,
                        separators=(",", ":"), default=str)
    sidik = hmac.new(_kunci_verifikasi(), mentah.encode("utf-8"),
                     hashlib.sha256).hexdigest().upper()
    return "-".join(sidik[i:i + 4] for i in range(0, 16, 4))


def kode_verifikasi_dokumen(judul: str, subjudul: str, tabel_data: list,
                            perusahaan: str = "", penanda: dict = None) -> str:
    """Kode yang tercetak pada segel dokumen, untuk pemeriksaan ulang."""
    return _identitas_cetak(judul, subjudul, tabel_data, perusahaan,
                            penanda)["kode"]


def _identitas_cetak(judul: str, subjudul: str, tabel_data: list,
                     perusahaan: str, penanda: dict = None) -> dict:
    st = _setelan_cetak_aman()
    p = penanda or {}
    nama = str(st.get("ttd_nama") or p.get("nama") or "").strip()
    jabatan = str(st.get("ttd_jabatan") or p.get("jabatan") or "").strip()
    kota = str(st.get("ttd_kota") or p.get("kota") or "").strip()
    gambar = str(st.get("ttd_gambar") or p.get("gambar") or "").strip()
    if gambar and not Path(gambar).exists():
        gambar = ""

    sekarang = datetime.now()
    air = str(st.get("air_teks") or "{perusahaan}")
    air = (air.replace("{perusahaan}", perusahaan or "")
           .replace("{tanggal}", f"{sekarang:%d/%m/%Y}")
           .replace("{tahun}", str(sekarang.year))).strip()
    if not air:
        air = (perusahaan or "").strip()

    return {
        "air_aktif": bool(st.get("air_aktif")) and bool(air),
        "air": air,
        "air_pekat": float(st.get("air_pekat") or 8),
        "ttd_aktif": bool(st.get("ttd_aktif")),
        "nama": nama,
        "jabatan": jabatan,
        "kota": kota,
        "gambar": gambar,
        "tanggal": sekarang,
        "kode": _kode_dokumen(judul, subjudul, tabel_data, perusahaan,
                              nama, jabatan, kota),
    }


def identitas_dokumen(judul: str, subjudul: str, tabel_data: list,
                      perusahaan: str = "", penanda: dict = None) -> dict:
    """Identitas dan kode verifikasi untuk dokumen yang dicetak modul lain."""
    return _identitas_cetak(judul, subjudul, tabel_data, perusahaan, penanda)


def gambar_segel(identitas: dict, ukuran: int = 432) -> QImage:
    """
    Segel verifikasi sebagai gambar berlatarbelakang transparan.

    Dipakai invoice yang dibuat dengan reportlab, agar segelnya sama dengan
    segel pada laporan A4. Ukuran gambar dibuat lebih besar daripada ukuran
    cetak supaya tetap tajam saat dicetak.
    """
    gambar = QImage(ukuran, ukuran, QImage.Format_ARGB32)
    gambar.fill(Qt.transparent)
    p = QPainter(gambar)
    p.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing)
    asli = 112.0
    p.scale(ukuran / asli, ukuran / asli)
    _lukis_segel(p, asli / 2.0, asli / 2.0, 44.0, identitas)
    p.end()
    return gambar


def segel_png(identitas: dict, ukuran: int = 432) -> bytes:
    """Isi berkas PNG segel, untuk disisipkan ke PDF reportlab."""
    data = QByteArray()
    buf = QBuffer(data)
    buf.open(QBuffer.WriteOnly)
    gambar_segel(identitas, ukuran).save(buf, "PNG")
    buf.close()
    return bytes(data)


def _aman_html(nilai) -> str:
    teks = "" if nilai is None else str(nilai)
    return (teks.replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;"))


def _angka_teks(nilai) -> str:
    """Format angka dengan pemisah ribuan dan desimal gaya Indonesia."""
    if isinstance(nilai, float):
        if nilai.is_integer():
            nilai = int(nilai)
        else:
            teks = f"{nilai:,.2f}"
            return (teks.replace(",", "_").replace(".", ",")
                    .replace("_", "."))
    return f"{nilai:,}".replace(",", ".")


def _angka(nilai) -> bool:
    return isinstance(nilai, (int, float)) and not isinstance(nilai, bool)


def _baris_total(data: list) -> bool:
    """Baris ringkasan dibuat tebal supaya mudah ditemukan saat dibaca."""
    for sel in data:
        if isinstance(sel, str) and sel.strip():
            teks = sel.strip().upper()
            return (teks.startswith("TOTAL") or teks.startswith("JUMLAH")
                    or teks.startswith("SALDO AKHIR")
                    or teks.startswith("LABA BERSIH")
                    or teks in ("LABA KOTOR", "LABA OPERASIONAL",
                                "LABA SEBELUM PAJAK",
                                "LABA SETELAH PAJAK",
                                "LABA TAHUN BERJALAN",
                                "TOTAL ASET", "TOTAL LIABILITAS",
                                "TOTAL EKUITAS", "TOTAL LIABILITAS & EKUITAS",
                                "KENAIKAN/(PENURUNAN) KAS"))
    return False


def _lebar_kolom(baris: list, skala: float = 1.0) -> tuple[list, list]:
    """
    Perkiraan lebar tiap kolom dan kolom mana yang berisi angka.

    Lebar dihitung dari metrik font yang benar-benar dipakai pada tabel,
    dalam satuan dokumen. Lebar dipakai untuk memilih orientasi kertas
    sekaligus membagi ruang tabel, supaya kolom angka tidak melebar dan
    kolom teks tidak terlalu sempit hingga setiap baris terlipat.
    """
    n_kolom = max((len(r) for r in baris), default=1)
    if n_kolom < 1:
        return [], []
    kolom_angka = [True] * n_kolom
    for data in baris[1:]:
        for c in range(n_kolom):
            nilai = data[c] if c < len(data) else ""
            if isinstance(nilai, str) and nilai.strip():
                kolom_angka[c] = False
            elif nilai not in (None, "") and not _angka(nilai):
                kolom_angka[c] = False

    def metrik(piksel: float, tebal: int) -> QFontMetricsF:
        f = QFont(_keluarga_font())
        f.setPixelSize(max(1, int(round(piksel * skala))))
        f.setWeight(QFont.Weight(tebal))
        return QFontMetricsF(f)

    kepala = metrik(11.8, 600)
    isi = metrik(12.2, 400)
    lebar = []
    for c in range(n_kolom):
        teks_kepala = str(baris[0][c]) if c < len(baris[0]) else ""
        butuh = kepala.horizontalAdvance(teks_kepala)
        for data in baris[1:]:
            nilai = data[c] if c < len(data) else ""
            teks = _angka_teks(nilai) if _angka(nilai) else str(nilai)
            butuh = max(butuh, isi.horizontalAdvance(teks))
        # Padding kiri-kanan sel mengikuti skala, ditambah cadangan tipis
        # untuk garis dan pembulatan.
        padding = 18.0 * skala + 6.0
        if kolom_angka[c]:
            lebar.append(max(46.0 * skala, butuh + padding))
        else:
            lebar.append(max(44.0 * skala,
                             min(270.0 * skala, butuh) + padding))
    return lebar, kolom_angka


def _skala_tabel(baris: list, lebar: float) -> float:
    """
    Skala huruf tabel agar seluruh kolom muat dalam satu baris halaman.

    Tabel lebar tetap terbaca tanpa setiap nilai terlipat. Bila isinya
    terlalu lebar, huruf diperkecil sedikit (paling kecil 72%) sebelum
    dipilih pelipatan teks sebagai jalan terakhir.
    """
    if not baris or lebar <= 0:
        return 1.0
    if sum(_lebar_kolom(baris, 1.0)[0]) <= lebar:
        return 1.0
    bawah, atas = 0.72, 1.0
    for _ in range(8):
        tengah = (bawah + atas) / 2.0
        if sum(_lebar_kolom(baris, tengah)[0]) <= lebar:
            bawah = tengah
        else:
            atas = tengah
    return bawah


def _perlu_mendatar(tabel_data: list) -> bool:
    """
    Pilih orientasi dari perkiraan lebar isi tabel, bukan hanya jumlah
    kolom. Tabel tujuh kolom yang isinya angka pendek masih muat tegak,
    sedangkan tabel delapan kolom dengan nama panjang lebih nyaman
    mendatar.
    """
    terlebar = 0.0
    for _, baris in tabel_data:
        if not baris:
            continue
        lebar, _ = _lebar_kolom(baris)
        terlebar = max(terlebar, sum(lebar))
    return terlebar > _area_cetak(False).width() - 5


def _rencana_lebar(baris: list, lebar: float,
                   skala: float = None) -> tuple[list, list, float]:
    """
    Lebar tiap kolom untuk satu tabel, dipakai semua potongan halaman.

    Satu rencana dipakai ulang agar kepala tabel pada halaman lanjutan
    tetap sejajar dengan halaman pertama.
    """
    if skala is None:
        skala = _skala_tabel(baris, lebar)
    if not baris:
        return [], [], skala
    lebar_kolom, kolom_angka = _lebar_kolom(baris, skala)
    total = sum(lebar_kolom) or 1.0
    if lebar <= 0:
        lebar = total
    faktor = lebar / total
    lebar_sel = [max(1, int(nilai * faktor)) for nilai in lebar_kolom]
    lebar_sel[-1] += max(0, int(lebar) - sum(lebar_sel))
    return lebar_sel, kolom_angka, skala


def _ukuran_kertas(mendatar: bool) -> tuple[float, float]:
    """Ukuran A4 dalam titik: tegak 595 x 842, mendatar 842 x 595."""
    return (842.0, 595.0) if mendatar else (595.0, 842.0)


def _area_cetak(mendatar: bool) -> QRectF:
    """Area cetak A4 tanpa tepi, dalam satuan dokumen 96 dpi."""
    lebar, tinggi = _ukuran_kertas(mendatar)
    tepi = MARGIN_MM * 72.0 / 25.4
    return QRectF(_px(tepi), _px(tepi),
                  _px(lebar - 2 * tepi), _px(tinggi - 2 * tepi))


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

    Setiap lembar diberi kop berisi nama tabel, perusahaan, dan waktu
    pembuatan. Halaman cetaknya juga sudah diatur agar berkas yang sama
    dapat langsung dicetak ke kertas A4 tanpa penyetelan tambahan.
    """
    try:
        import openpyxl
        from openpyxl.styles import (Alignment, Border, Font, PatternFill,
                                     Side)
        from openpyxl.utils import get_column_letter
        from openpyxl.worksheet.properties import PageSetupProperties
    except ImportError:
        raise RuntimeError("Modul openpyxl belum terpasang. "
                           "Jalankan: pip install openpyxl")

    tujuan = Path(path)
    tujuan.parent.mkdir(parents=True, exist_ok=True)

    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    font_kop = Font(name="Calibri", size=15, bold=True, color="1E282D")
    font_perusahaan = Font(name="Calibri", size=9.5, bold=True,
                           color="8A5225")
    font_info = Font(name="Calibri", size=9, color="66737A")
    font_kepala = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
    font_isi = Font(name="Calibri", size=10, color="1E282D")
    font_total = Font(name="Calibri", size=10, bold=True, color="1E282D")
    isi_kepala = PatternFill("solid", fgColor="1E282D")
    isi_belang = PatternFill("solid", fgColor="FBF8F3")
    isi_total = PatternFill("solid", fgColor="F3EDE4")
    tipis = Side(style="thin", color="E7DFD3")
    tebal = Side(style="medium", color="B37748")
    garis = Border(left=tipis, right=tipis, top=tipis, bottom=tipis)
    atas_total = Border(left=tipis, right=tipis, top=tebal, bottom=tipis)
    kiri = Alignment(horizontal="left", vertical="center")
    kanan = Alignment(horizontal="right", vertical="center")
    tengah = Alignment(horizontal="center", vertical="center")

    dipakai: set = set()
    for nama_lembar, baris in tabel_data:
        nama = str(nama_lembar or "Data")
        ws = wb.create_sheet(title=nama_lembar_aman(nama, dipakai))

        lebar_kolom = max((len(r) for r in baris), default=1)
        if lebar_kolom < 1:
            lebar_kolom = 1

        # Kop lembar.
        ws.cell(row=1, column=1, value=nama).font = font_kop
        ws.row_dimensions[1].height = 23
        if nama_perusahaan:
            ws.cell(row=2, column=1, value=nama_perusahaan).font = font_perusahaan
        info = " · ".join(x for x in (
            subjudul if subjudul and subjudul != nama else "",
            f"Dibuat {datetime.now():%d/%m/%Y %H:%M}",
            f"{config.APP_NAME} {config.APP_VERSION}") if x)
        ws.cell(row=3, column=1, value=info).font = font_info
        ws.row_dimensions[4].height = 7

        mulai = 5
        # Ketebalan angka ditentukan per kolom supaya perataan judul kolom
        # sesuai dengan isinya.
        kolom_angka = [True] * lebar_kolom
        for data in baris[1:]:
            for c in range(lebar_kolom):
                nilai = data[c] if c < len(data) else ""
                if isinstance(nilai, str) and nilai.strip():
                    kolom_angka[c] = False
                elif nilai not in (None, "") and not _angka(nilai):
                    kolom_angka[c] = False

        for r, data in enumerate(baris, start=mulai):
            total = r > mulai and _baris_total(data)
            for c in range(1, lebar_kolom + 1):
                nilai = data[c - 1] if c - 1 < len(data) else ""
                sel = ws.cell(row=r, column=c)
                angka = _angka(nilai)
                if angka:
                    sel.value = nilai
                    sel.number_format = ('#,##0;[Red]-#,##0' if isinstance(nilai, int)
                                         or float(nilai).is_integer()
                                         else '#,##0.##;[Red]-#,##0.##')
                elif isinstance(nilai, str) and nilai.startswith("="):
                    # Rumus tidak diteruskan, supaya berkas tidak
                    # menjalankan apa pun saat dibuka.
                    sel.value = nilai
                else:
                    sel.value = "" if nilai is None else str(nilai)
                sel.border = atas_total if total else garis
                if r == mulai:
                    sel.font = font_kepala
                    sel.fill = isi_kepala
                    sel.alignment = (kanan if kolom_angka[c - 1] else kiri)
                else:
                    sel.font = font_total if total else font_isi
                    if angka:
                        sel.alignment = kanan
                    elif isinstance(nilai, str) and re.fullmatch(
                            r"\d{2}/\d{2}/\d{4}", nilai.strip()):
                        sel.alignment = tengah
                    else:
                        sel.alignment = kiri
                    if total:
                        sel.fill = isi_total
                    elif (r - mulai) % 2 == 0:
                        sel.fill = isi_belang

        # Judul kolom dibekukan dan disaring.
        ws.freeze_panes = ws.cell(row=mulai + 1, column=1)
        if baris and len(baris) > 1:
            ws.auto_filter.ref = (
                f"A{mulai}:{get_column_letter(lebar_kolom)}"
                f"{mulai + len(baris) - 1}")

        for c in range(1, lebar_kolom + 1):
            if kolom_angka[c - 1]:
                lebar = 16
            else:
                terpanjang = 0
                for r in range(mulai, mulai + len(baris)):
                    nilai = ws.cell(row=r, column=c).value
                    if nilai is not None:
                        terpanjang = max(terpanjang, len(str(nilai)))
                lebar = min(max(12, terpanjang + 3), 48)
            ws.column_dimensions[get_column_letter(c)].width = lebar

        # Berkas langsung siap dicetak di kertas A4.
        ws.sheet_view.showGridLines = False
        ws.page_setup.paperSize = ws.PAPERSIZE_A4
        ws.page_setup.orientation = ("landscape" if lebar_kolom >= 6
                                     else "portrait")
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0
        ws.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
        ws.page_margins.left = 0.55
        ws.page_margins.right = 0.55
        ws.page_margins.top = 0.7
        ws.page_margins.bottom = 0.65
        ws.print_title_rows = f"{mulai}:{mulai}"
        ws.print_options.horizontalCentered = True
        ws.oddHeader.left.text = nama_perusahaan or nama
        ws.oddHeader.left.size = 9
        ws.oddHeader.left.color = "66737A"
        ws.oddHeader.right.text = f"{config.APP_NAME} {config.APP_VERSION}"
        ws.oddHeader.right.size = 9
        ws.oddHeader.right.color = "66737A"
        ws.oddFooter.left.text = f"Dicetak {datetime.now():%d/%m/%Y %H:%M}"
        ws.oddFooter.left.size = 9
        ws.oddFooter.left.color = "66737A"
        ws.oddFooter.right.text = "Halaman &P dari &N"
        ws.oddFooter.right.size = 9
        ws.oddFooter.right.color = "66737A"

    wb.save(str(tujuan))
    return tujuan


# ==========================================================================
# ISI CETAK
# ==========================================================================
JARAK_BAGIAN = _px(16.0)


def _css_cetak(skala_tabel: float = 1.0) -> str:
    keluarga = _keluarga_font().replace("'", "")
    serif = _keluarga_serif().replace("'", "")
    s = skala_tabel
    return f"""<style>
    body {{ font-family: '{keluarga}', Arial, sans-serif; color: {WARNA_TEKS};
           font-size: 12.2px; }}
    .judul {{ font-family: '{serif}', Georgia, serif; font-size: 26px;
              font-weight: 600; color: {WARNA_TINTA};
              letter-spacing: -0.4px; }}
    .subjudul {{ font-size: 12px; color: {WARNA_MUTED}; margin-top: 3px;
                 padding-bottom: 11px; border-bottom: 0.8px solid {WARNA_GARIS};
                 margin-bottom: 4px; }}
    .bagian-luar {{ font-family: '{serif}', Georgia, serif; font-size: 14px;
                    font-weight: 600; color: {WARNA_TINTA};
                    margin-top: 17px; padding-bottom: 5px; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 11px; }}
    th {{ background: {WARNA_TOTAL}; color: {WARNA_TINTA};
         font-size: {11.8 * s:.2f}px; font-weight: 600;
         letter-spacing: 0.18px;
         padding: {8 * s:.2f}px {10 * s:.2f}px; text-align: left;
         border-top: 0.9px solid {WARNA_TINTA};
         border-bottom: 0.7px solid {WARNA_TINTA}; }}
    th.angka {{ text-align: right; }}
    td {{ padding: {6 * s:.2f}px {10 * s:.2f}px; font-size: {12.2 * s:.2f}px;
         color: {WARNA_TEKS};
         border-bottom: 0.6px solid {WARNA_GARIS}; vertical-align: middle; }}
    td.angka {{ text-align: right; white-space: nowrap; }}
    tr.belang td {{ background: {WARNA_BELANG}; }}
    tr.total td {{ background: transparent; font-weight: 700;
                   border-top: 1px solid {WARNA_TINTA};
                   border-bottom: 0.6px solid {WARNA_GARIS}; }}
    tr.grup td {{ background: {WARNA_GRUP}; color: {WARNA_TINTA};
                  font-weight: 600; font-size: {12 * s:.2f}px;
                  padding-top: {8 * s:.2f}px;
                  padding-bottom: {8 * s:.2f}px; }}
    thead tr.bagian th {{ background: transparent; color: {WARNA_TINTA};
                          font-weight: 600; font-size: {12.4 * s:.2f}px;
                          letter-spacing: 0;
                          border-top: none;
                          border-bottom: 0.7px solid {WARNA_GARIS};
                          padding-top: 3px; padding-bottom: 5px; }}
    .kosong {{ color: {WARNA_MUTED}; font-size: 12px;
               margin-top: 6px; }}
    </style>"""


def _html_bagian(nama: str, baris: list, judul: str = "",
                 subjudul: str = "", tampilkan_nama: bool = True,
                 lanjutan: bool = False, lebar: float = 0.0,
                 skala_tabel: float = 1.0, rencana=None) -> str:
    """
    Susun satu bagian cetak.

    Nama bagian dimasukkan ke kepala tabel (thead), sehingga ikut terulang
    bila tabel berlanjut ke halaman berikutnya dan pembaca tidak kehilangan
    konteks.
    """
    bagian = []
    if judul:
        bagian.append(f'<div class="judul">{_aman_html(judul)}</div>')
    if subjudul:
        bagian.append(f'<div class="subjudul">{_aman_html(subjudul)}</div>')

    nama = str(nama or "")
    if not baris:
        if nama and tampilkan_nama:
            bagian.append(f'<div class="bagian-luar">{_aman_html(nama)}</div>')
        bagian.append('<div class="kosong">Belum ada data.</div>')
        return "".join(bagian)

    n_kolom = max(len(r) for r in baris)
    if n_kolom < 1:
        n_kolom = 1
    data_isi = [r + [""] * (n_kolom - len(r)) for r in baris]

    # Lebar kolom dibagi menurut panjang isinya. Tanpa ini Qt membagi
    # kolom hampir rata, sehingga kolom teks pendek kebesaran dan kolom
    # keterangan terlalu sempit sampai terlipat di setiap baris. Qt membaca
    # lebar sel dalam satuan dokumen, bukan persen, jadi dihitung dari
    # lebar area cetak yang tersedia.
    if rencana is None:
        rencana = _rencana_lebar(baris, lebar, skala_tabel)
    lebar_sel, kolom_angka, _skala = rencana

    kepala = []
    if nama and tampilkan_nama:
        label = nama + (" · lanjutan" if lanjutan else "")
        kepala.append(
            f'<tr class="bagian"><th colspan="{n_kolom}" '
            f'style="text-align:left;">{_aman_html(label)}</th></tr>')
    kepala.append("<tr>")
    for c, nilai in enumerate(data_isi[0]):
        kelas = ' class="angka"' if kolom_angka[c] else ""
        kepala.append(
            f'<th{kelas} width="{lebar_sel[c]}">'
            f'{_aman_html(nilai)}</th>')
    kepala.append("</tr>")

    isi = []
    for urut, data in enumerate(data_isi[1:]):
        terisi = [x for x in data if str(x).strip()]
        if not terisi:
            continue
        if len(terisi) == 1 and n_kolom > 1 and not _angka(terisi[0]):
            isi.append(
                f'<tr class="grup"><td colspan="{n_kolom}">'
                f'{_aman_html(terisi[0])}</td></tr>')
            continue
        total = _baris_total(data)
        kelas = ' class="total"' if total else (
            ' class="belang"' if urut % 2 else "")
        sel = []
        for c, nilai in enumerate(data):
            kelas_sel = ' class="angka"' if kolom_angka[c] or _angka(nilai) else ""
            teks = _angka_teks(nilai) if _angka(nilai) else _aman_html(nilai)
            sel.append(f"<td{kelas_sel}>{teks}</td>")
        isi.append(f"<tr{kelas}>{''.join(sel)}</tr>")

    bagian.append(
        f'<table width="100%" cellspacing="0" cellpadding="0">'
        f'<thead>{"".join(kepala)}</thead>'
        f'<tbody>{"".join(isi)}</tbody></table>')
    return "".join(bagian)


def _dokumen_bagian(nama: str, baris: list, judul: str = "",
                    subjudul: str = "", tampilkan_nama: bool = True,
                    lanjutan: bool = False, lebar: float = 0.0,
                    rencana=None, skala_tabel: float = None) -> QTextDocument:
    if rencana is None:
        rencana = _rencana_lebar(baris, lebar, skala_tabel)
    skala = rencana[2] if rencana else (skala_tabel or 1.0)
    doc = QTextDocument()
    doc.setDefaultFont(_font(9))
    doc.setDocumentMargin(0)
    doc.setHtml("<html><head>" + _css_cetak(skala) + "</head><body>" +
                _html_bagian(nama, baris, judul, subjudul, tampilkan_nama,
                             lanjutan, lebar, skala, rencana) +
                "</body></html>")
    return doc


def _baris_grup(nilai: list, n_kolom: int) -> bool:
    """Baris judul kelompok, yaitu satu teks yang membentang seluruh kolom."""
    terisi = [x for x in nilai if str(x).strip()]
    return (n_kolom > 1 and len(terisi) == 1
            and not _angka(terisi[0]))


def _bagi_bagian_panjang(nama: str, baris: list, judul: str,
                         subjudul: str, tampilkan_nama: bool,
                         lebar: float, tinggi: float,
                         rencana=None) -> list:
    """
    Pecah tabel yang lebih tinggi dari satu halaman menjadi beberapa potong.

    Setiap potong adalah dokumen baru yang muat dalam satu halaman, lengkap
    dengan kepala tabel sendiri. Dengan begitu kepala tabel benar-benar
    terulang dan tidak ada halaman kosong yang muncul dari pemotongan
    dokumen Qt. Jumlah halaman dan barisnya diperkirakan dari tinggi baris
    contoh, lalu diverifikasi saat dokumen halaman dibentuk, sehingga tabel
    besar tidak perlu ditata berulang kali dari awal.
    """
    kepala = baris[0]
    data = baris[1:]
    n_kolom = max(len(r) for r in baris)
    if rencana is None:
        rencana = _rencana_lebar(baris, lebar)

    def buat(posisi: int, jumlah: int, lanjutan: bool) -> QTextDocument:
        doc = _dokumen_bagian(
            nama, [kepala] + data[posisi:posisi + jumlah],
            judul if not lanjutan else "",
            subjudul if not lanjutan else "",
            tampilkan_nama, lanjutan, lebar, rencana)
        doc.setTextWidth(lebar)
        return doc

    def tinggi_doc(doc: QTextDocument) -> float:
        return doc.size().height()

    # Tinggi kop tabel dan tinggi baris diukur dari contoh kecil, bukan
    # dari seluruh tabel.
    tinggi_awal = tinggi_doc(buat(0, 0, False))
    tinggi_lanjut = tinggi_doc(buat(0, 0, True))
    contoh = min(10, len(data))
    if contoh:
        tinggi_baris = max(
            1.0, (tinggi_doc(buat(0, contoh, False)) - tinggi_awal) / contoh)
    else:
        tinggi_baris = 1.0

    kapasitas_awal = max(1, int((tinggi + 0.5 - tinggi_awal) / tinggi_baris))
    kapasitas_lanjut = max(
        1, int((tinggi + 0.5 - tinggi_lanjut) / tinggi_baris))
    if len(data) <= kapasitas_awal:
        jumlah_halaman = 1
    else:
        sisa = len(data) - kapasitas_awal
        jumlah_halaman = 1 + -(-sisa // kapasitas_lanjut)

    potongan: list[QTextDocument] = []
    posisi = 0
    while posisi < len(data):
        sisa = len(data) - posisi
        sisa_halaman = max(1, jumlah_halaman - len(potongan))
        ambil = min(sisa, max(1, -(-sisa // sisa_halaman)))
        kapasitas = kapasitas_awal if not potongan else kapasitas_lanjut
        ambil = min(ambil, max(1, kapasitas))

        while True:
            doc = buat(posisi, ambil, bool(potongan))
            tinggi_nyata = tinggi_doc(doc)
            if tinggi_nyata <= tinggi + 0.5 or ambil <= 1:
                break
            ambil = max(1, min(ambil - 1,
                               int(ambil * (tinggi / tinggi_nyata) * 0.99)))

        # Jangan biarkan judul kelompok tertinggal sendirian di dasar
        # halaman; barisnya dipindah ke halaman berikutnya.
        while (ambil > 1 and posisi + ambil < len(data)
               and _baris_grup(data[posisi + ambil - 1], n_kolom)):
            ambil -= 1
            doc = buat(posisi, ambil, bool(potongan))

        potongan.append(doc)
        posisi += ambil
        if len(potongan) >= jumlah_halaman and posisi < len(data):
            jumlah_halaman = len(potongan) + 1

    if not potongan:
        potongan.append(buat(0, 0, False))
    return potongan


def _susun_halaman(judul: str, subjudul: str, tabel_data: list,
                   lebar: float, tinggi: float) -> list:
    """
    Tentukan isi setiap halaman sebelum mencetak.

    Setiap bagian diukur lebih dulu. Bagian pendek tetap utuh dalam satu
    halaman, sehingga judul dan tabelnya tidak terpisah di dasar kertas.
    Bagian yang lebih tinggi dari satu halaman dipecah menjadi beberapa
    dokumen halaman, masing-masing dengan kepala tabel yang terulang.
    Rencana ini juga membuat jumlah halaman sudah diketahui saat kaki
    halaman ditulis.
    """
    if not tabel_data:
        doc = _dokumen_bagian("", [], judul, subjudul, False, False, lebar)
        doc.setTextWidth(lebar)
        return [[("utuh", doc, 0.0, doc.size().height())]]

    halaman: list = []
    terpakai = 0.0
    for i, (nama, baris) in enumerate(tabel_data):
        tampilkan = not (
            len(tabel_data) == 1
            and str(nama or "").strip().lower() == str(judul or "").strip().lower())
        judul_bagian = judul if i == 0 else ""
        sub_bagian = subjudul if i == 0 else ""
        rencana = _rencana_lebar(baris, lebar)

        # Bagian yang jelas lebih tinggi dari kertas langsung dipecah.
        # Menata seluruh tabel hanya untuk mengetahui bahwa tabel itu
        # terlalu tinggi membuang waktu pada laporan besar.
        if len(baris) <= 40:
            doc = _dokumen_bagian(nama, baris, judul_bagian, sub_bagian,
                                  tampilkan, False, lebar, rencana)
            doc.setTextWidth(lebar)
            tinggi_doc = doc.size().height()

            if tinggi_doc <= tinggi + 0.5:
                if not halaman or terpakai + tinggi_doc > tinggi + 0.5:
                    halaman.append([])
                    terpakai = 0.0
                halaman[-1].append(("utuh", doc, terpakai, tinggi_doc))
                terpakai += tinggi_doc + JARAK_BAGIAN
                continue

        # Bagian lebih tinggi dari satu halaman: setiap potongan menjadi
        # halaman sendiri, sehingga bagian sebelumnya tidak tersambung di
        # bawah tabel yang terpotong.
        for potongan in _bagi_bagian_panjang(
                nama, baris, judul_bagian, sub_bagian, tampilkan,
                lebar, tinggi, rencana):
            potongan.setTextWidth(lebar)
            halaman.append(
                [("utuh", potongan, 0.0, potongan.size().height())])
        # Bagian berikutnya dimulai di halaman baru agar tidak menyambung
        # di bawah tabel yang baru saja dipotong.
        terpakai = tinggi
    return halaman


# ==========================================================================
# GAMBAR KE KERTAS
# ==========================================================================
def _lukis_kop(p: QPainter, area: QRectF, perusahaan: str) -> None:
    """Merek di kiri, nama perusahaan di kanan, garis rambut di bawahnya."""
    logo = _logo()
    if not logo.isNull():
        p.save()
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)
        p.drawImage(QRectF(area.left(), area.top(), _px(15), _px(15)), logo)
        p.restore()

    p.setFont(_font_serif(11.5, 600))
    p.setPen(QColor(WARNA_TINTA))
    p.drawText(QRectF(area.left() + _px(19), area.top() - _px(2),
                      _px(180), _px(13)),
               Qt.AlignLeft | Qt.AlignVCenter, "AkunTuntas")

    p.setFont(_font(6.8, 400))
    p.setPen(QColor(WARNA_MUTED))
    p.drawText(QRectF(area.left() + _px(19), area.top() + _px(9),
                      _px(180), _px(8)),
               Qt.AlignLeft | Qt.AlignVCenter, "Akuntansi dan perpajakan")

    if perusahaan:
        p.setFont(_font(8.8, 600))
        p.setPen(QColor(WARNA_TINTA))
        fm = p.fontMetrics()
        teks = fm.elidedText(perusahaan, Qt.ElideRight,
                             int(area.width() * 0.5))
        p.drawText(QRectF(area.left() + area.width() * 0.5, area.top(),
                          area.width() * 0.5, _px(16)),
                   Qt.AlignRight | Qt.AlignVCenter, teks)

    # Satu garis rambut sepanjang lebar kertas, seperti kop surat resmi.
    # Tanpa potongan berwarna di ujung agar tidak terbaca sebagai hiasan.
    p.setPen(QPen(QColor(WARNA_TINTA), _px(0.6)))
    p.drawLine(QPointF(area.left(), area.top() + _px(22)),
               QPointF(area.right(), area.top() + _px(22)))


def _lukis_kaki(p: QPainter, area: QRectF, halaman: int, total: int,
                identitas: dict = None) -> None:
    y = area.bottom() - _px(TINGGI_KAKI)
    p.setPen(QPen(QColor(WARNA_GARIS), _px(0.55)))
    p.drawLine(QPointF(area.left(), y + _px(2)),
               QPointF(area.right(), y + _px(2)))
    p.setFont(_font(7.6, 400))
    p.setPen(QColor(WARNA_MUTED))
    kiri = (f"{config.APP_NAME} {config.APP_VERSION} · dicetak "
            f"{datetime.now():%d/%m/%Y %H:%M}")
    p.drawText(QRectF(area.left(), y + _px(4), area.width() * 0.38,
                      _px(TINGGI_KAKI - 4)),
               Qt.AlignLeft | Qt.AlignVCenter, kiri)

    if identitas and identitas.get("kode"):
        p.setFont(_font(7.6, 500))
        p.setPen(QColor(WARNA_TINTA))
        kode = identitas["kode"]
        p.drawText(QRectF(area.left() + area.width() * 0.36, y + _px(4),
                          area.width() * 0.4, _px(TINGGI_KAKI - 4)),
                   Qt.AlignHCenter | Qt.AlignVCenter, f"Kode dokumen {kode}")

    p.setFont(_font(7.6, 400))
    p.setPen(QColor(WARNA_MUTED))
    p.drawText(QRectF(area.left() + area.width() * 0.76, y + _px(4),
                      area.width() * 0.24, _px(TINGGI_KAKI - 4)),
               Qt.AlignRight | Qt.AlignVCenter,
               f"Halaman {halaman} dari {total}")


# ==========================================================================
# TANDA AIR, SEGEL, DAN TANDA TANGAN
# ==========================================================================
def _lukis_air(p: QPainter, area: QRectF, teks: str, pekat: float) -> None:
    """
    Tanda air diagonal di atas isi halaman.

    Huruf mengecil otomatis sampai muat pada lebar area cetak, sehingga
    nama perusahaan yang panjang tidak terpotong. Warna memakai tinta yang
    sama dengan teks dengan kepekatan rendah agar isi dokumen tetap
    terbaca paling utama.
    """
    baris = [b.strip().upper() for b in str(teks or "").splitlines()
             if b.strip()]
    if not baris:
        return
    ukuran = 84.0
    while True:
        font = _font_serif(ukuran, 600)
        fm = QFontMetricsF(font)
        lebar_maks = max(fm.horizontalAdvance(b) for b in baris)
        tinggi = fm.height() * len(baris)
        if ukuran <= 18 or (lebar_maks <= area.width() * 0.84
                            and tinggi <= area.height() * 0.62):
            break
        ukuran -= 4.0

    p.save()
    p.setClipRect(area)
    p.translate(area.center())
    p.rotate(-32)
    p.setFont(font)
    warna = QColor(WARNA_TINTA)
    warna.setAlphaF(min(0.22, max(0.02, float(pekat) / 100.0)))
    p.setPen(warna)
    tinggi_baris = fm.height()
    atas = -tinggi_baris * len(baris) / 2.0
    for i, b in enumerate(baris):
        p.drawText(QRectF(-area.width() / 2.0,
                          atas + i * tinggi_baris,
                          area.width(), tinggi_baris),
                   Qt.AlignCenter, b)
    p.restore()


def _teks_busur(p: QPainter, cx: float, cy: float, jari: float, teks: str,
                font: QFont, warna: QColor, tengah_derajat: float) -> None:
    """Tulis teks mengikuti busur lingkaran, dipakai pada segel dokumen."""
    fm = QFontMetricsF(font)
    lebar = [fm.horizontalAdvance(ch) for ch in teks]
    total = sum(lebar)
    if total <= 0 or jari <= 0:
        return
    busur = total / jari
    sudut = math.radians(tengah_derajat) - busur / 2.0
    p.save()
    p.setFont(font)
    p.setPen(warna)
    for ch, w in zip(teks, lebar):
        if ch.strip():
            tengah = sudut + (w / 2.0) / jari
            p.save()
            p.translate(cx + jari * math.cos(tengah),
                        cy + jari * math.sin(tengah))
            p.rotate(math.degrees(tengah) + 90.0)
            p.drawText(QRectF(-w, -fm.height() / 2.0, 2.0 * w, fm.height()),
                       Qt.AlignCenter, ch)
            p.restore()
        sudut += w / jari
    p.restore()


def _lukis_segel(p: QPainter, cx: float, cy: float, jari: float,
                 identitas: dict) -> None:
    """
    Segel verifikasi bundar: cincin ganda, busur "DOKUMEN TERVERIFIKASI",
    monogram, dan tanggal. Segel ini penanda bahwa kode dokumen di kaki
    halaman dihitung dari isi dokumen dan kunci pemasangan aplikasi.
    """
    tinta = QColor(WARNA_TEMBAGA)
    tinta.setAlpha(220)
    p.save()
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setBrush(Qt.NoBrush)
    p.setPen(QPen(tinta, _px(0.95)))
    p.drawEllipse(QPointF(cx, cy), jari, jari)
    p.setPen(QPen(tinta, _px(0.4)))
    p.drawEllipse(QPointF(cx, cy), jari * 0.86, jari * 0.86)

    _teks_busur(p, cx, cy, jari * 0.77, "DOKUMEN TERVERIFIKASI",
                _font(5.5, 600), tinta, -90)

    p.setPen(tinta)
    p.setFont(_font_serif(12.0, 600))
    p.drawText(QRectF(cx - jari, cy - jari * 0.34, 2 * jari, _px(14)),
               Qt.AlignCenter, "AT")

    p.setPen(QPen(tinta, _px(0.4)))
    p.drawLine(QPointF(cx - jari * 0.26, cy + jari * 0.09),
               QPointF(cx + jari * 0.26, cy + jari * 0.09))

    p.setFont(_font(5.1, 700))
    p.drawText(QRectF(cx - jari, cy + jari * 0.20, 2 * jari, _px(6)),
               Qt.AlignCenter, "AKUNTUNTAS")
    tanggal = identitas.get("tanggal") or datetime.now()
    p.setFont(_font(4.8, 500))
    p.drawText(QRectF(cx - jari, cy + jari * 0.45, 2 * jari, _px(6)),
               Qt.AlignCenter, f"{tanggal:%d.%m.%Y}")
    p.restore()


def _lukis_ttd(p: QPainter, area: QRectF, identitas: dict) -> None:
    """
    Blok pengesahan di kanan bawah halaman terakhir.

    Susunannya mengikuti dokumen resmi Indonesia: kota dan tanggal di atas,
    ruang tanda tangan, garis, lalu nama dan jabatan. Segel verifikasi
    ditempatkan di kiri garis, tidak menimpa nama.
    """
    kanan = area.right()
    kiri = kanan - _px(186)
    atas = area.bottom() - _px(TINGGI_KAKI) - _px(TINGGI_TTD)

    tanggal = identitas.get("tanggal") or datetime.now()
    nama_bulan = config.MONTH_NAMES_ID[tanggal.month - 1]
    teks_tanggal = f"{tanggal.day} {nama_bulan} {tanggal.year}"
    kota = str(identitas.get("kota") or "").strip()
    if kota:
        teks_tanggal = f"{kota}, {teks_tanggal}"

    p.setFont(_font(8.6, 400))
    p.setPen(QColor(WARNA_MUTED))
    p.drawText(QRectF(kiri, atas, kanan - kiri, _px(12)),
               Qt.AlignRight | Qt.AlignVCenter, teks_tanggal)

    garis_y = atas + _px(56)
    gambar = identitas.get("gambar") or ""
    if gambar:
        img = QImage(gambar)
        if not img.isNull():
            kotak = QRectF(kiri + _px(20), garis_y - _px(36),
                           kanan - kiri - _px(40), _px(32))
            skala = min(kotak.width() / max(1, img.width()),
                        kotak.height() / max(1, img.height()))
            lebar = img.width() * skala
            tinggi = img.height() * skala
            p.save()
            p.setRenderHint(QPainter.SmoothPixmapTransform, True)
            p.drawImage(QRectF(kotak.center().x() - lebar / 2.0,
                               kotak.bottom() - tinggi, lebar, tinggi), img)
            p.restore()

    p.setPen(QPen(QColor(WARNA_TINTA), _px(0.65)))
    p.drawLine(QPointF(kiri, garis_y), QPointF(kanan, garis_y))

    nama = str(identitas.get("nama") or "").strip()
    jabatan = str(identitas.get("jabatan") or "").strip()
    if nama:
        p.setFont(_font(9.6, 600))
        p.setPen(QColor(WARNA_TINTA))
        p.drawText(QRectF(kiri, garis_y + _px(4), kanan - kiri, _px(12)),
                   Qt.AlignRight | Qt.AlignVCenter, nama)
    if jabatan:
        p.setFont(_font(8.0, 400))
        p.setPen(QColor(WARNA_MUTED))
        p.drawText(QRectF(kiri, garis_y + _px(16), kanan - kiri, _px(10)),
                   Qt.AlignRight | Qt.AlignVCenter, jabatan)
    p.setFont(_font(7.4, 400))
    p.setPen(QColor(WARNA_MUTED))
    p.drawText(QRectF(kiri, garis_y + _px(27), kanan - kiri, _px(8)),
               Qt.AlignRight | Qt.AlignVCenter,
               "Ditandatangani secara elektronik")

    _lukis_segel(p, kiri - _px(39), garis_y - _px(11), _px(33), identitas)


def _tambah_ruang_ttd(rencana: list, area: QRectF, identitas: dict) -> list:
    """
    Sisipkan halaman pengesahan bila halaman terakhir sudah penuh.

    Blok tanda tangan selalu berada di dasar halaman. Bila isi halaman
    terakhir mencapai ruang tersebut, pengesahan dipindah ke halaman baru
    supaya tidak menimpa baris tabel. Halaman baru tetap memuat kop, tanda
    air, kaki, dan nomor halaman seperti halaman lain.
    """
    if not identitas or not identitas.get("ttd_aktif"):
        return rencana
    if not rencana:
        return [[]]
    isi = rencana[-1]
    y_akhir = max((y + h for _, _, y, h in isi), default=0.0)
    tinggi = area.height() - _px(TINGGI_KOP) - _px(TINGGI_KAKI)
    batas = tinggi - _px(TINGGI_TTD) - _px(10)
    if y_akhir > batas:
        return list(rencana) + [[]]
    return rencana


def _lukis_rencana(p: QPainter, area: QRectF, rencana: list,
                   perusahaan: str, printer: QPrinter = None,
                   maks_halaman: int = None, identitas: dict = None) -> None:
    """
    Gambar halaman sesuai rencana. Satuan di sini adalah titik; pemanggil
    yang menyesuaikan skala perangkat.
    """
    lebar = area.width()
    total = len(rencana)
    jumlah = total if maks_halaman is None else min(total, maks_halaman)

    for i in range(jumlah):
        if i and printer is not None:
            printer.newPage()
        _lukis_kop(p, area, perusahaan)
        for _, doc, nilai, tinggi_doc in rencana[i]:
            p.save()
            p.translate(area.left(), area.top() + _px(TINGGI_KOP) + nilai)
            p.setClipRect(QRectF(0, 0, lebar, tinggi_doc + 1))
            doc.drawContents(p, QRectF(0, 0, lebar, tinggi_doc + 1))
            p.restore()
        # Tanda air dilukis di atas isi, bukan di belakangnya: sel tabel
        # memakai latar sendiri sehingga tanda air di belakang tidak
        # terlihat pada tabel. Kepekatan tetap rendah agar teks terbaca,
        # dan kop, kaki, serta blok pengesahan tidak ikut tertutup.
        ttd_di_halaman = bool(identitas and identitas.get("ttd_aktif")
                              and i == total - 1)
        if identitas and identitas.get("air_aktif"):
            tinggi_air = (area.height() - _px(TINGGI_KOP)
                          - _px(TINGGI_KAKI))
            if ttd_di_halaman:
                tinggi_air -= _px(TINGGI_TTD)
            isi_area = QRectF(area.left(), area.top() + _px(TINGGI_KOP),
                              area.width(), max(_px(60), tinggi_air))
            _lukis_air(p, isi_area, identitas.get("air", ""),
                       identitas.get("air_pekat", 8))
        if ttd_di_halaman:
            _lukis_ttd(p, area, identitas)
        _lukis_kaki(p, area, i + 1, total, identitas)


def _siapkan_printer(printer: QPrinter, mendatar: bool) -> None:
    printer.setPageSize(QPageSize(QPageSize.A4))
    printer.setPageOrientation(QPageLayout.Landscape if mendatar
                               else QPageLayout.Portrait)
    printer.setPageMargins(
        QMarginsF(MARGIN_MM, MARGIN_MM, MARGIN_MM, MARGIN_MM),
        QPageLayout.Millimeter)
    printer.setDocName(config.APP_NAME)


def _gambar_ke_printer(judul: str, subjudul: str, tabel_data: list,
                       printer: QPrinter, perusahaan: str,
                       penanda: dict = None) -> None:
    # QPainter pada printer sudah dimulai dari sudut area cetak, bukan dari
    # sudut kertas. Karena itu lukisan memakai koordinat 0,0 dengan ukuran
    # area cetak; menambahkan lagi posisi area akan menggeser isi dua kali
    # dan memotong tepi kanan.
    area_kertas = printer.pageRect(QPrinter.Point)
    area = QRectF(0, 0, _px(area_kertas.width()), _px(area_kertas.height()))
    lebar = area.width()
    tinggi = area.height() - _px(TINGGI_KOP) - _px(TINGGI_KAKI)
    rencana = _susun_halaman(judul, subjudul, tabel_data, lebar, tinggi)
    identitas = _identitas_cetak(judul, subjudul, tabel_data, perusahaan,
                                 penanda)
    rencana = _tambah_ruang_ttd(rencana, area, identitas)

    p = QPainter(printer)
    try:
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.TextAntialiasing, True)
        p.scale(printer.resolution() / 96.0, printer.resolution() / 96.0)
        _lukis_rencana(p, area, rencana, perusahaan, printer=printer,
                       identitas=identitas)
    finally:
        p.end()


# ==========================================================================
# CETAK, PDF, PRATINJAU
# ==========================================================================
def cetak(parent, judul: str, subjudul: str, tabel_data: list,
          mendatar: bool = None, perusahaan: str = "",
          langsung: bool = False, penanda: dict = None) -> bool:
    """
    Cetak tabel ke kertas A4.

    Bila langsung bernilai salah, pratinjau ditampilkan lebih dulu sehingga
    pengguna dapat memeriksa hasilnya dan memilih pencetak. Bila bernilai
    benar, dialog pencetak langsung dibuka. ``penanda`` mengisi nama, jabatan,
    dan kota penanda tangan bila pengaturan cetak belum diisi.
    """
    if mendatar is None:
        mendatar = _perlu_mendatar(tabel_data)

    printer = QPrinter(QPrinter.HighResolution)
    _siapkan_printer(printer, mendatar)

    if langsung:
        from PySide6.QtPrintSupport import QPrintDialog
        dialog = QPrintDialog(printer, parent)
        dialog.setWindowTitle("Cetak A4")
        if dialog.exec() != QPrintDialog.Accepted:
            return False
        _gambar_ke_printer(judul, subjudul, tabel_data, printer, perusahaan,
                           penanda)
        return True

    from .pratinjau_cetak import DialogPratinjau

    def lukis(p):
        _gambar_ke_printer(judul, subjudul, tabel_data, p, perusahaan,
                           penanda)

    def simpan(induk) -> bool:
        return _simpan_pdf_lewat_dialog(induk, judul, subjudul, tabel_data,
                                        mendatar, perusahaan, penanda)

    dialog = DialogPratinjau(parent, printer, lukis, judul,
                             keterangan=subjudul, mendatar=mendatar,
                             atur_orientasi=_siapkan_printer, simpan=simpan)
    dialog.tampilkan()
    return True


def _simpan_pdf_lewat_dialog(parent, judul: str, subjudul: str,
                             tabel_data: list, mendatar: bool,
                             perusahaan: str, penanda: dict) -> bool:
    """Tanyakan lokasi berkas, simpan PDF, lalu tawarkan membukanya."""
    from PySide6.QtWidgets import QApplication, QFileDialog

    config.ensure_dirs()
    aman = re.sub(r"[^A-Za-z0-9_\- ]", "", str(judul)).strip() or "Dokumen"
    awal = config.EXPORT_DIR / f"{aman}_{datetime.now():%Y%m%d}"
    path, _ = QFileDialog.getSaveFileName(parent, "Simpan PDF", str(awal),
                                          "PDF (*.pdf)")
    if not path:
        return False
    path = _akhir_berkas(path, ".pdf")

    QApplication.setOverrideCursor(Qt.WaitCursor)
    try:
        simpan_pdf(judul, subjudul, tabel_data, path, mendatar=mendatar,
                   perusahaan=perusahaan, penanda=penanda)
    except Exception as e:
        QApplication.restoreOverrideCursor()
        popup.galat(parent, "Gagal menyimpan PDF", str(e))
        return False
    finally:
        if QApplication.overrideCursor() is not None:
            QApplication.restoreOverrideCursor()

    if popup.tanya(parent, "PDF tersimpan",
                   f"Berkas tersimpan di:<br><b>{path}</b>",
                   teks_ya="Buka berkas", teks_tidak="Nanti"):
        _buka_berkas(path)
    return True


def simpan_pdf(judul: str, subjudul: str, tabel_data: list, path: str,
               mendatar: bool = None, perusahaan: str = "",
               penanda: dict = None) -> Path:
    """Simpan tabel ke berkas PDF A4, tanpa membuka pencetak."""
    if mendatar is None:
        mendatar = _perlu_mendatar(tabel_data)
    printer = QPrinter(QPrinter.HighResolution)
    _siapkan_printer(printer, mendatar)
    printer.setOutputFormat(QPrinter.PdfFormat)
    printer.setOutputFileName(str(path))
    _gambar_ke_printer(judul, subjudul, tabel_data, printer, perusahaan,
                       penanda)
    return Path(path)


def pratinjau_gambar(judul: str, subjudul: str, tabel_data: list,
                     lebar: int = 800, mendatar: bool = None,
                     perusahaan: str = "", penanda: dict = None) -> QImage:
    """
    Hasilkan gambar halaman pertama untuk pemeriksaan tata letak.

    Gambar memakai ukuran halaman yang sama dengan hasil cetak, sehingga
    hasilnya dapat dipakai memeriksa kop, tabel, dan kaki halaman tanpa
    membuka pencetak.
    """
    if mendatar is None:
        mendatar = _perlu_mendatar(tabel_data)
    lebar_kertas, tinggi_kertas = _ukuran_kertas(mendatar)
    skala = lebar / _px(lebar_kertas)
    tinggi = max(1, int(round(lebar * tinggi_kertas / lebar_kertas)))
    gambar = QImage(lebar, tinggi, QImage.Format_RGB32)
    gambar.fill(Qt.white)

    area = _area_cetak(mendatar)
    rencana = _susun_halaman(
        judul, subjudul, tabel_data, area.width(),
        area.height() - _px(TINGGI_KOP) - _px(TINGGI_KAKI))
    identitas = _identitas_cetak(judul, subjudul, tabel_data, perusahaan,
                                 penanda)
    rencana = _tambah_ruang_ttd(rencana, area, identitas)

    p = QPainter(gambar)
    try:
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.TextAntialiasing, True)
        p.scale(skala, skala)
        _lukis_rencana(p, area, rencana, perusahaan, maks_halaman=1,
                       identitas=identitas)
    finally:
        p.end()
    return gambar


# ==========================================================================
# PINTASAN UNTUK HALAMAN
# ==========================================================================
def _akhir_berkas(path: str, ekstensi: str) -> str:
    """Pastikan nama berkas berakhiran sesuai format yang dipilih."""
    p = Path(path)
    if p.suffix.lower() in (".xlsx", ".pdf", ".csv"):
        return str(p.with_suffix(ekstensi))
    if not p.suffix:
        return str(p.with_suffix(ekstensi))
    return str(path) + ekstensi


def _buka_berkas(path: str) -> None:
    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QDesktopServices
    QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))


def ekspor_halaman(parent, judul: str, subjudul: str, tabel_data: list,
                   nama_berkas: str = "Data", perusahaan: str = "",
                   mendatar: bool = None, penanda: dict = None) -> bool:
    """
    Tawarkan penyimpanan Excel atau PDF dari data sebuah halaman.

    Satu dialog berisi dua pilihan format. Setelah berkas tersimpan,
    pengguna dapat langsung membukanya untuk diperiksa atau dibagikan.
    """
    from PySide6.QtWidgets import QApplication, QFileDialog

    if not tabel_data:
        popup.beri_tahu(parent,
                        "Belum ada data",
                        "Tidak ada data untuk diekspor pada halaman ini.")
        return False

    config.ensure_dirs()
    aman = re.sub(r"[^A-Za-z0-9_\- ]", "", str(nama_berkas)).strip() or "Data"
    awal = config.EXPORT_DIR / f"{aman}_{datetime.now():%Y%m%d}"

    path, saringan = QFileDialog.getSaveFileName(
        parent, "Simpan Data",
        str(awal),
        "Excel (*.xlsx);;PDF (*.pdf)")
    if not path:
        return False

    pdf = "pdf" in (saringan or "").lower()
    path = _akhir_berkas(path, ".pdf" if pdf else ".xlsx")

    QApplication.setOverrideCursor(Qt.WaitCursor)
    try:
        if pdf:
            simpan_pdf(judul, subjudul, tabel_data, path,
                       mendatar=mendatar, perusahaan=perusahaan,
                       penanda=penanda)
        else:
            ekspor_excel(judul, tabel_data, path, subjudul=subjudul,
                         nama_perusahaan=perusahaan)
    except Exception as e:
        QApplication.restoreOverrideCursor()
        popup.galat(parent, "Gagal mengekspor", str(e))
        return False
    finally:
        if QApplication.overrideCursor() is not None:
            QApplication.restoreOverrideCursor()

    if popup.tanya(parent,
                   "Ekspor selesai",
                   f"Berkas tersimpan:\n{path}\n\nBuka berkasnya sekarang?"):
        _buka_berkas(path)
    return True


def cetak_halaman(parent, judul: str, subjudul: str, tabel_data: list,
                  mendatar: bool = None, perusahaan: str = "",
                  penanda: dict = None) -> bool:
    """Cetak data sebuah halaman ke kertas A4 melalui pratinjau."""

    if not tabel_data:
        popup.beri_tahu(parent,
                        "Belum ada data",
                        "Tidak ada data untuk dicetak pada halaman ini.")
        return False
    try:
        return cetak(parent, judul, subjudul, tabel_data,
                     mendatar=mendatar, perusahaan=perusahaan,
                     penanda=penanda)
    except Exception as e:
        popup.galat(parent, "Gagal mencetak", str(e))
        return False


def simpan_pdf_halaman(parent, judul: str, subjudul: str, tabel_data: list,
                       nama_berkas: str = "Dokumen", perusahaan: str = "",
                       mendatar: bool = None, penanda: dict = None) -> bool:
    """Simpan data sebuah halaman sebagai berkas PDF A4."""
    from PySide6.QtWidgets import QFileDialog

    if not tabel_data:
        popup.beri_tahu(parent,
                        "Belum ada data",
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
        simpan_pdf(judul, subjudul, tabel_data, path,
                   mendatar=mendatar, perusahaan=perusahaan, penanda=penanda)
    except Exception as e:
        popup.galat(parent, "Gagal menyimpan PDF", str(e))
        return False
    if popup.tanya(parent,
                   "Penyimpanan selesai",
                   f"PDF tersimpan:\n{path}\n\nBuka berkasnya sekarang?"):
        _buka_berkas(path)
    return True


def _buka_folder(parent, path: str) -> None:
    """Buka folder tempat berkas disimpan, memakai penjelajah bawaan."""
    import subprocess
    import sys

    folder = str(Path(path).parent)
    try:
        if sys.platform.startswith("win"):
            os.startfile(folder)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", folder])
        else:
            subprocess.Popen(["xdg-open", folder])
    except Exception:
        pass


def tabel_dari_widget(tabel) -> list:
    """
    Ambil isi sebuah tabel di layar menjadi bentuk yang siap diekspor.

    Angka dikembalikan sebagai angka agar dapat dijumlahkan, sedangkan
    persentase dan kode tetap berupa teks supaya tidak berubah arti.
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
            angka = _teks_ke_angka(teks)
            isi.append(angka if angka is not None else teks)
        baris.append(isi)
    return baris


def _teks_ke_angka(teks: str):
    """
    Ubah teks angka gaya Indonesia menjadi angka.

    Persentase tidak diubah karena nilainya tidak boleh kehilangan tanda
    persen saat dibuka di Excel. Teks lain juga dikembalikan sebagai None.
    """
    if not teks:
        return None
    bersih = str(teks).strip().replace("Rp", "").replace(" ", "")
    if not bersih or bersih.endswith("%"):
        return None
    if not re.fullmatch(r"-?[\d.]+(,\d+)?", bersih):
        return None
    bersih = bersih.replace(".", "").replace(",", ".")
    try:
        angka = float(bersih)
    except ValueError:
        return None
    return int(angka) if angka.is_integer() else angka
