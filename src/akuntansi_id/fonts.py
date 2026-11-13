"""
Huruf aplikasi
==============
Dua keluarga huruf dibundel bersama aplikasi supaya tampilan sama di semua
komputer:

  • Public Sans - antarmuka, tabel, dan nominal rupiah
  • Source Serif 4 - judul halaman dan angka pokok laporan

Public Sans dipilih karena dibuat untuk formulir dan data pemerintahan:
x-height tinggi, celah huruf terbuka, bentuk 1, l, dan I mudah dibedakan,
serta angka tabular tersedia lewat fitur "tnum". Pada ukuran kecil huruf
ini tetap jernih, sehingga cocok untuk tabel pembukuan yang padat.
Source Serif 4 tetap dipakai untuk judul agar nuansa laporan tercetak
tidak hilang. Keduanya berlisensi SIL Open Font License, dan dipakai
sebagai berkas statis agar hasilnya sama di Qt, reportlab, dan PyInstaller.
Bila berkas tidak ditemukan, aplikasi memakai huruf sistem sebagai
cadangan dan tetap berjalan normal.
"""
from __future__ import annotations

from pathlib import Path

NAMA_FAMILY = "Public Sans"
NAMA_SERIF = "Source Serif 4"
NAMA_DISPLAY = "Source Serif 4 Display"
CADANGAN = "Segoe UI"
CADANGAN_SERIF = "Georgia"

# Nama gaya yang dipakai Qt dan reportlab. Kunci "family" dan "serif" dipakai
# pemanggil yang membutuhkan satu nama keluarga, bukan satu berkas.
BERKAS = {
    "Sans": "PublicSans-Regular.ttf",
    "Sans-Medium": "PublicSans-Medium.ttf",
    "Sans-Semibold": "PublicSans-SemiBold.ttf",
    "Sans-Bold": "PublicSans-Bold.ttf",
    "Sans-Italic": "PublicSans-Italic.ttf",
    "Serif": "SourceSerif4-Regular.ttf",
    "Serif-Semibold": "SourceSerif4-Semibold.ttf",
    "Serif-Bold": "SourceSerif4-Bold.ttf",
    "Serif-Italic": "SourceSerif4-It.ttf",
    "Serif-Display": "SourceSerif4Display-Semibold.ttf",
}

_terdaftar_reportlab: dict | None = None


def folder() -> Path:
    from . import config
    return config.ASSET_DIR / "fonts"


def berkas(nama: str) -> Path | None:
    """Alamat berkas huruf, atau None bila tidak dibundel."""
    nama_berkas = BERKAS.get(nama)
    if not nama_berkas:
        return None
    p = folder() / nama_berkas
    return p if p.is_file() else None


def tersedia() -> bool:
    return all(berkas(nama) is not None for nama in BERKAS)


def pasang_reportlab() -> dict:
    """
    Daftarkan kedua keluarga huruf pada reportlab dan kembalikan nama gaya
    yang siap pakai.

    Bila huruf tidak tersedia, nama gaya diganti huruf bawaan reportlab
    supaya pembuatan PDF tidak pernah gagal hanya karena huruf hilang.
    """
    global _terdaftar_reportlab
    if _terdaftar_reportlab is not None:
        return _terdaftar_reportlab

    gaya = {
        "regular": "Helvetica",
        "medium": "Helvetica",
        "semibold": "Helvetica-Bold",
        "bold": "Helvetica-Bold",
        "extrabold": "Helvetica-Bold",
        "italic": "Helvetica-Oblique",
        "family": "Helvetica",
        "serif": "Times-Roman",
        "serif_semibold": "Times-Bold",
        "serif_bold": "Times-Bold",
    }
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont

        if tersedia():
            for nama in BERKAS:
                pdfmetrics.registerFont(TTFont(nama, str(berkas(nama))))
            pdfmetrics.registerFontFamily(
                "Sans",
                normal="Sans",
                bold="Sans-Bold",
                italic="Sans-Italic",
                boldItalic="Sans-Bold")
            pdfmetrics.registerFontFamily(
                "Serif",
                normal="Serif",
                bold="Serif-Bold",
                italic="Serif-Italic",
                boldItalic="Serif-Bold")
            gaya.update({
                "regular": "Sans",
                "medium": "Sans-Medium",
                "semibold": "Sans-Semibold",
                "bold": "Sans-Bold",
                "extrabold": "Sans-Bold",
                "italic": "Sans-Italic",
                "family": "Sans",
                "serif": "Serif",
                "serif_semibold": "Serif-Semibold",
                "serif_bold": "Serif-Bold",
            })
    except Exception:
        # Nama gaya cadangan di atas tetap dipakai; PDF tetap dapat dibuat.
        pass
    _terdaftar_reportlab = gaya
    return gaya
