"""
AkunTuntas - Sistem Desain (Design System)
===========================================
Palet warna, tipografi, dan stylesheet Qt terpusat.

Prinsip desain:
- Tenang & tepercaya: warna netral dominan, aksen dipakai hemat.
- Hierarki tegas: judul, isi, dan keterangan dibedakan lewat bobot dan warna,
  bukan lewat kotak dan garis yang berlebihan.
- Angka utama: nominal rupiah selalu memakai huruf lebar tetap agar digit
  sejajar dan mudah dibandingkan antarbaris.
- Ruang bernapas: jarak antarunsur konsisten mengikuti skala 4 piksel.
- Kontras memadai: seluruh teks memenuhi rasio WCAG AA.
"""
from __future__ import annotations

from PySide6.QtGui import QFont

# ==========================================================================
# PALET WARNA
# ==========================================================================
class C:
    # Palet diambil dari logo: tinta arang kehijauan dan tembaga. Tinta
    # dipakai untuk judul serta tindakan utama; tembaga hanya untuk penanda
    # aktif dan sorotan. Tidak ada gradien maupun warna pastel berderet.
    PRIMARY = "#222C2F"
    PRIMARY_DARK = "#141B1D"
    PRIMARY_LIGHT = "#43514F"
    PRIMARY_SOFT = "#F0F0F0"
    PRIMARY_TINT = "#F7F7F7"
    ACCENT = "#A0622D"
    ACCENT_DARK = "#7C4A1E"
    ACCENT_LIGHT = "#C08A56"
    ACCENT_SOFT = "#F6EFE8"
    ACCENT_TINT = "#FBF8F4"

    # Sidebar - tinta pekat dengan huruf kertas.
    SIDEBAR_BG = "#1B2426"
    SIDEBAR_HOVER = "#263234"
    SIDEBAR_ACTIVE = "#2C3A3C"
    SIDEBAR_TEXT = "#BFC9C6"
    SIDEBAR_TEXT_ACTIVE = "#F7F3EA"
    SIDEBAR_SECTION = "#7E8C89"
    SIDEBAR_LINE = "#334043"

    # Latar putih bersih; pemisah memakai garis abu tipis, bukan warna.
    BG = "#FFFFFF"
    SURFACE = "#FFFFFF"
    SURFACE_ALT = "#F7F7F7"
    BORDER = "#E5E5E5"
    BORDER_STRONG = "#CFCFCF"

    # Teks
    TEXT = "#1D2628"
    TEXT_MUTED = "#55605E"
    TEXT_FAINT = "#626D6A"
    TEXT_INVERSE = "#FFFFFF"

    # Status - warna tanah yang tenang, bukan lampu lalu lintas.
    SUCCESS = "#2F6149"
    SUCCESS_BG = "#EEF4EF"
    WARNING = "#8A5A17"
    WARNING_BG = "#F8F1E3"
    DANGER = "#9C3B31"
    DANGER_BG = "#F8ECE9"
    INFO = "#3F5C6B"
    INFO_BG = "#EEF2F4"
    NEUTRAL_BG = "#F2F2F2"

    # Angka - debit dan kredit dibedakan tanpa biru terang.
    DEBIT = "#2F5D4F"
    KREDIT = "#8A5A17"
    POSITIF = "#2F6149"
    NEGATIF = "#9C3B31"

    # Panel merek pada halaman masuk dan halaman aktivasi.
    BRAND_BG = "#1B2426"
    BRAND_BG_DEEP = "#151D1F"
    BRAND_TEXT = "#FFFFFF"
    BRAND_MUTED = "#A9B6B2"
    BRAND_LINE = "#354245"


# ==========================================================================
# SKALA RUANG DAN BENTUK
# ==========================================================================
# Jarak mengikuti kelipatan 4 piksel agar seluruh layar terasa satu irama.
R = {
    "xs": 4,
    "sm": 8,
    "md": 12,
    "lg": 16,
    "xl": 20,
    "xxl": 26,
}

# Sudut hampir tegak. Dokumen keuangan tercetak memakai sudut lurus; sudut
# kecil menjaga antarmuka tetap terasa lembut tanpa menjadi kartu templat.
SUDUT_KARTU = 3
SUDUT_KONTROL = 4

# Tinggi kontrol agar mudah diklik (pedoman aksesibilitas: minimal 32 px)
TINGGI_KONTROL = 34
TINGGI_TOMBOL_BESAR = 38


STATUS_COLORS = {
    "kritis": (C.DANGER, C.DANGER_BG),
    "peringatan": (C.WARNING, C.WARNING_BG),
    "saran": (C.INFO, C.INFO_BG),
    "baik": (C.SUCCESS, C.SUCCESS_BG),
    "info": (C.INFO, C.INFO_BG),
    "ok": (C.SUCCESS, C.SUCCESS_BG),
    "danger": (C.DANGER, C.DANGER_BG),
    "warning": (C.WARNING, C.WARNING_BG),
}

# ==========================================================================
# TIPOGRAFI
# ==========================================================================
# Source Sans 3 untuk antarmuka dan angka, Source Serif 4 untuk judul dan
# angka pokok laporan. Pasangan serif + sans memberi hierarki seperti laporan
# keuangan tercetak, bukan satu keluarga huruf yang dipakai di semua tempat.
# Bila berkas tidak ditemukan, aplikasi jatuh ke huruf sistem.
from .. import fonts as _fonts

FONT_UI = _fonts.CADANGAN
FONT_FAMILY = FONT_UI
# Nominal memakai keluarga sans dengan fitur OpenType "tnum" aktif, sehingga
# digitnya sama lebar tanpa terlihat seperti huruf kode.
FONT_MONO = FONT_UI
FONT_ANGKA = FONT_UI
FONT_SERIF = _fonts.CADANGAN_SERIF
FONT_DISPLAY = _fonts.CADANGAN_SERIF

_FONT_TERPASANG = False
_FONT_TERPAKAI = ""

# Ukuran teks nominal, dipakai agar tidak terlalu besar pada kartu ringkas.
UKURAN_ANGKA = 22


def pasang_font(app=None) -> str:
    """
    Muat huruf bawaan aplikasi dan pasang sebagai huruf antarmuka.

    Dipanggil sebelum stylesheet dibuat agar seluruh aturan font memakai
    nama keluarga yang benar. Kembaliannya nama keluarga yang terpakai.
    """
    global FONT_UI, FONT_FAMILY, FONT_MONO, FONT_ANGKA, FONT_SERIF, FONT_DISPLAY
    global _FONT_TERPASANG, _FONT_TERPAKAI

    if _FONT_TERPASANG:
        if app is not None and _FONT_TERPAKAI:
            app.setFont(_font_aplikasi())
        return _FONT_TERPAKAI

    _FONT_TERPAKAI = _fonts.CADANGAN
    try:
        from PySide6.QtWidgets import QApplication
        from PySide6.QtGui import QFontDatabase

        if QApplication.instance() is None:
            # Belum ada aplikasi Qt; huruf dimuat saat aplikasi tersedia.
            return _FONT_TERPAKAI

        terdaftar = []
        for nama in _fonts.BERKAS:
            berkas = _fonts.berkas(nama)
            if berkas is None:
                continue
            fon_id = QFontDatabase.addApplicationFont(str(berkas))
            if fon_id >= 0:
                terdaftar.extend(
                    QFontDatabase.applicationFontFamilies(fon_id))
        if _fonts.NAMA_FAMILY in terdaftar:
            _FONT_TERPAKAI = _fonts.NAMA_FAMILY
        elif terdaftar:
            _FONT_TERPAKAI = terdaftar[0]
        if _fonts.NAMA_SERIF in terdaftar:
            FONT_SERIF = _fonts.NAMA_SERIF
        if _fonts.NAMA_DISPLAY in terdaftar:
            FONT_DISPLAY = _fonts.NAMA_DISPLAY
        elif FONT_SERIF != _fonts.CADANGAN_SERIF:
            FONT_DISPLAY = FONT_SERIF
        _FONT_TERPASANG = True
    except Exception:
        # Huruf cadangan tetap dipakai; aplikasi tidak boleh gagal dibuka
        # hanya karena berkas huruf bermasalah.
        _FONT_TERPASANG = True

    FONT_UI = _FONT_TERPAKAI
    FONT_FAMILY = FONT_UI
    FONT_MONO = FONT_UI
    FONT_ANGKA = FONT_UI

    if app is not None:
        app.setFont(_font_aplikasi())
    return FONT_UI


def _font_aplikasi() -> QFont:
    """Huruf dasar aplikasi; stylesheet mengatur ukuran per unsur."""
    f = QFont(FONT_UI)
    f.setPointSizeF(10)
    # Bobot Medium dan angka tabular membuat teks 14px tetap tegas dan
    # kolom nominal sejajar di layar Windows.
    f.setWeight(QFont.Medium)
    try:
        f.setFeature(QFont.Tag("tnum"), 1)
    except Exception:
        pass
    f.setStyleStrategy(QFont.PreferAntialias)
    return f


def font_angka(ukuran: float = None, tebal: bool = True) -> QFont:
    """
    Font untuk menampilkan nominal rupiah.

    Digit dibuat berlebar sama lewat fitur OpenType "tnum" supaya angka
    sejajar antarbaris dan mudah dibandingkan, sementara bentuk hurufnya
    tetap font antarmuka yang jelas dibaca.
    """
    if not _FONT_TERPASANG:
        pasang_font()
    f = QFont(FONT_UI)
    f.setPixelSize(int(ukuran or UKURAN_ANGKA))
    f.setWeight(QFont.DemiBold if tebal else QFont.Normal)
    try:
        f.setFeature(QFont.Tag("tnum"), 1)
    except Exception:
        # Qt lama tidak mendukung fitur huruf; angka tetap tampil normal
        pass
    return f


def font_serif(ukuran: float = 28, tebal: bool = False,
               display: bool = False) -> QFont:
    """Font judul editorial; angka juga memakai varian serif bila diminta."""
    if not _FONT_TERPASANG:
        pasang_font()
    f = QFont(FONT_DISPLAY if display else FONT_SERIF)
    f.setPixelSize(int(ukuran))
    f.setWeight(QFont.DemiBold if tebal else QFont.Normal)
    return f


def font_serif_angka(ukuran: float = 26, tebal: bool = True) -> QFont:
    """
    Font serif untuk nominal yang dibaca sebagai angka pokok.

    Fitur "tnum" membuat digit berlebar sama seperti pada angka sans,
    sehingga nominal antarbaris tetap sejajar meski bentuk hurufnya serif.
    """
    f = font_serif(ukuran, tebal=tebal, display=True)
    try:
        f.setFeature(QFont.Tag("tnum"), 1)
    except Exception:
        pass
    return f


def tinggi_rich_text(lbl) -> int:
    """
    Tinggi yang benar-benar dibutuhkan label teks berformat.

    QLabel dengan wordWrap menghitung tinggi teks berformat lebih pendek
    daripada kebutuhan sebenarnya pada lebar sempit, sehingga baris
    terakhirnya terpotong. Pengukuran lewat QTextDocument memberi tinggi
    yang tepat untuk lebar label saat ini.
    """
    from PySide6.QtGui import QTextDocument

    lebar = lbl.width() if lbl.width() > 0 else lbl.sizeHint().width()
    doc = QTextDocument()
    doc.setDefaultFont(lbl.font())
    doc.setHtml(lbl.text())
    doc.setTextWidth(max(1, lebar))
    return int(doc.size().height()) + 2


FS_DISPLAY = 26
FS_H1 = 21
FS_H2 = 16
FS_H3 = 14
FS_BODY = 14
FS_SMALL = 13
FS_TINY = 12
# Ukuran khusus popup pesan. Popup dibaca sambil lalu, sering kali saat
# pengguna sedang menyelesaikan hal lain, jadi teksnya dibuat lebih
# besar daripada teks badan biasa supaya tidak perlu dizoom.
FS_PESAN = 15

# Skala ukuran teks aplikasi; diubah dari menu Tampilan → Ukuran Teks.
UKURAN_TEKS = 1.0


# ==========================================================================
# STYLESHEET QT
# ==========================================================================
def palet_terang(app) -> None:
    """
    Paksa mode terang untuk seluruh aplikasi.

    Windows dapat diatur ke mode gelap. Bila itu terjadi, Qt memakai skema
    gelap dari sistem, dan bagian antarmuka yang tidak diatur stylesheet
    ikut menjadi gelap: bingkai popup daftar pilihan, garis tepi menu, dan
    kotak dialog bawaan. Akibatnya muncul pita hitam di sekeliling daftar
    pilihan yang tidak sesuai dengan tampilan terang aplikasi.

    Ada dua hal yang perlu disetel. Pertama, skema warna aplikasi, yang
    memberi tahu Qt agar tidak meminta bingkai jendela bergaya gelap kepada
    Windows. Kedua, palet warna, yang menentukan warna dasar bagi widget
    yang belum diatur stylesheet.
    """
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QColor, QPalette

    pasang_font(app)

    # Sejak Qt 6.5, ini cara resmi memilih skema warna. Tanpa ini, bingkai
    # jendela popup tetap digambar gelap oleh Windows walau isinya terang.
    app.styleHints().setColorScheme(Qt.ColorScheme.Light)

    p = QPalette()
    putih = QColor(C.SURFACE)
    tinta = QColor(C.TEXT)

    p.setColor(QPalette.Window, QColor(C.NEUTRAL_BG))
    p.setColor(QPalette.WindowText, tinta)
    p.setColor(QPalette.Base, putih)
    p.setColor(QPalette.AlternateBase, QColor(C.SURFACE_ALT))
    p.setColor(QPalette.Text, tinta)
    p.setColor(QPalette.PlaceholderText, QColor(C.TEXT_FAINT))
    p.setColor(QPalette.Button, QColor(C.SURFACE))
    p.setColor(QPalette.ButtonText, tinta)
    p.setColor(QPalette.ToolTipBase, putih)
    p.setColor(QPalette.ToolTipText, tinta)
    # Warna sorotan disamakan dengan warna baris terpilih pada tabel.
    # Palet ini yang dipakai baris terpilih pada daftar pilihan, karena
    # daftar itu tampil sebagai jendela tersendiri sehingga aturan
    # stylesheet pemilihan tidak selalu berlaku. Biru tua penuh dengan
    # tulisan putih membuat baris terpilih tampak seperti tajuk gelap,
    # sedangkan biru muda dengan tulisan gelap terbaca sebagai pilihan.
    p.setColor(QPalette.Highlight, QColor(C.ACCENT_SOFT))
    p.setColor(QPalette.HighlightedText, tinta)
    p.setColor(QPalette.Link, QColor(C.ACCENT_DARK))
    p.setColor(QPalette.Disabled, QPalette.Text, QColor(C.TEXT_FAINT))
    p.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(C.TEXT_FAINT))
    p.setColor(QPalette.Disabled, QPalette.WindowText, QColor(C.TEXT_FAINT))

    app.setPalette(p)


def _px(ukuran: float) -> str:
    """Ukuran teks dalam piksel, mengikuti skala ukuran teks aplikasi."""
    return f"{ukuran * UKURAN_TEKS:.1f}"


def _aset_url(nama: str) -> str:
    """Alamat berkas aset untuk properti image pada stylesheet."""
    from .. import config

    berkas = config.ASSET_DIR / nama
    return berkas.as_posix() if berkas.exists() else ""


def stylesheet() -> str:
    pasang_font()
    gambar_centang = _aset_url("centang_putih.png")
    aturan_centang = (f'image: url("{gambar_centang}");'
                      if gambar_centang else "image: none;")
    gambar_panah = _aset_url("chevron_down.png")
    aturan_panah = (f'image: url("{gambar_panah}"); width: 10px; height: 6px;'
                    if gambar_panah else "image: none;")
    gambar_panah_atas = _aset_url("chevron_up.png")
    aturan_panah_atas = (f'image: url("{gambar_panah_atas}"); '
                         'width: 9px; height: 5px;'
                         if gambar_panah_atas else "image: none;")
    return f"""
/* ---------------------------------------------------------- dasar */
* {{
    font-family: {FONT_FAMILY};
    font-size: {_px(FS_BODY)};
    color: {C.TEXT};
}}
/* Latar hanya dipasang pada wadah besar. Bila setiap QWidget diberi latar,
   wadah kosong ikut menutupi panel putih di belakangnya: judul halaman
   tampil sebagai pita abu-abu di atas header putih, dan formulir masuk
   tampak sebagai kotak abu-abu di tengah halaman putih. */
QWidget {{
    background: transparent;
}}
QMainWindow, QDialog, QStackedWidget {{
    background: {C.BG};
}}
QDialog QLabel, QMessageBox QLabel {{
    background: transparent;
}}

/* ---------------------------------------------------------- popup pesan
   Popup bawaan Qt tampak seperti kotak abu sistem: sudut tajam, tombol
   kecil berjarak rapat, dan judul tanpa penekanan. Gaya di bawah membuat
   seluruh popup di aplikasi terlihat sebagai bagian dari aplikasi ini,
   bukan jendela sistem yang menyusup. */
QMessageBox {{
    background: {C.SURFACE};
}}
QMessageBox QLabel {{
    background: transparent;
    color: {C.TEXT};
    font-size: {_px(FS_BODY)}px;
    line-height: 150%;
}}
QMessageBox QLabel#qt_msgbox_label {{
    font-size: {_px(FS_H3)}px;
    font-weight: 600;
    color: {C.TEXT};
    margin-bottom: 2px;
}}
QMessageBox QLabel#qt_msgbox_informativelabel {{
    color: {C.TEXT_MUTED};
    font-size: {_px(FS_SMALL)}px;
}}
QMessageBox QPushButton {{
    background: {C.SURFACE};
    color: {C.TEXT};
    border: 1px solid {C.BORDER_STRONG};
    border-radius: {SUDUT_KONTROL}px;
    padding: 9px 22px;
    min-width: 96px;
    font-size: {_px(FS_BODY)}px;
    font-weight: 600;
}}
QMessageBox QPushButton:hover {{
    background: {C.BG};
    border-color: {C.PRIMARY_LIGHT};
}}
QMessageBox QPushButton:default {{
    background: {C.PRIMARY};
    color: {C.TEXT_INVERSE};
    border: 1px solid {C.PRIMARY};
}}
QMessageBox QPushButton:default:hover {{
    background: {C.PRIMARY_DARK};
    border-color: {C.PRIMARY_DARK};
}}
QMessageBox QPushButton:disabled {{
    color: {C.TEXT_FAINT};
    border-color: {C.BORDER};
}}

/* Kotak pesan galat memakai judul berwarna bahaya supaya langsung
   terbaca berbeda dari pesan biasa. */
QMessageBox[pesan="galat"] QLabel#qt_msgbox_label {{
    color: {C.DANGER};
}}
QMessageBox[pesan="tanya"] QLabel#qt_msgbox_label {{
    color: {C.TEXT};
}}

/* ---------------------------------------------------------- kartu */
QFrame#Card {{
    background: {C.SURFACE};
    border: 1px solid {C.BORDER};
    border-radius: {SUDUT_KARTU}px;
}}
QFrame#CardFlat {{
    background: {C.SURFACE};
    border: none;
    border-radius: {SUDUT_KARTU}px;
}}
QFrame#KpiTile {{
    background: {C.SURFACE};
    border: 1px solid {C.BORDER};
    border-radius: {SUDUT_KARTU}px;
}}
/* Pita kinerja: satu lembar laporan, bukan deretan kartu. */
QFrame#PerformanceBand {{
    background: {C.SURFACE};
    border: 1px solid {C.BORDER};
    border-radius: {SUDUT_KARTU}px;
}}
QFrame#Hairline {{
    background: {C.BORDER};
    border: none;
    max-width: 1px;
    min-width: 1px;
}}
QFrame#HairlineRow {{
    background: {C.BORDER};
    border: none;
    max-height: 1px;
    min-height: 1px;
}}
QFrame#HelpPanel {{
    background: {C.SURFACE_ALT};
    border: 1px solid {C.BORDER};
    border-radius: {SUDUT_KARTU}px;
}}
QFrame#WarningPanel {{
    background: {C.WARNING_BG};
    border: 1px solid {C.WARNING};
    border-radius: {SUDUT_KARTU}px;
}}
QFrame#DangerPanel {{
    background: {C.DANGER_BG};
    border: 1px solid {C.DANGER};
    border-radius: {SUDUT_KARTU}px;
}}
QFrame#SuccessPanel {{
    background: {C.SUCCESS_BG};
    border: 1px solid {C.SUCCESS};
    border-radius: {SUDUT_KARTU}px;
}}
QFrame#TemuanCard {{
    background: {C.SURFACE};
    border: 1px solid {C.BORDER};
    border-radius: {SUDUT_KARTU}px;
}}
QFrame#ModeOption {{
    background: {C.SURFACE};
    border: 1px solid {C.BORDER};
    border-radius: {SUDUT_KARTU}px;
}}
QFrame#ModeOption:hover {{
    border-color: {C.ACCENT_LIGHT};
}}
QFrame#Divider {{
    background: {C.BORDER};
    max-height: 1px;
    min-height: 1px;
    border: none;
}}

/* ---------------------------------------------------------- label */
QLabel#PageTitle {{
    font-family: {FONT_DISPLAY};
    font-size: 30px;
    font-weight: 600;
    color: {C.TEXT};
    background: transparent;
    letter-spacing: 0;
}}
QLabel#PageSubtitle {{
    font-size: {_px(FS_SMALL)}px;
    color: {C.TEXT_MUTED};
    background: transparent;
    line-height: 150%;
}}
QLabel#SectionTitle {{
    font-family: {FONT_SERIF};
    font-size: 18px;
    font-weight: 600;
    color: {C.TEXT};
    background: transparent;
    letter-spacing: 0;
}}
QLabel#CardTitle {{
    font-size: 10.5px;
    font-weight: 700;
    color: {C.TEXT_MUTED};
    text-transform: uppercase;
    letter-spacing: 0.9px;
    background: transparent;
}}
/* Angka pokok laporan: serif besar dengan garis dasar tipis di bawahnya. */
QLabel#LedgerFigure {{
    font-family: {FONT_SERIF};
    font-size: {_px(FS_DISPLAY)}px;
    font-weight: 600;
    color: {C.TEXT};
    background: transparent;
}}
QLabel#LedgerLabel {{
    font-size: 10.5px;
    font-weight: 700;
    color: {C.TEXT_MUTED};
    text-transform: uppercase;
    letter-spacing: 0.9px;
    background: transparent;
}}
QLabel#LedgerHint {{
    font-size: {_px(FS_TINY)}px;
    color: {C.TEXT_FAINT};
    background: transparent;
}}
QLabel#Kicker {{
    font-size: 10px;
    font-weight: 700;
    color: {C.TEXT_FAINT};
    letter-spacing: 1.2px;
    background: transparent;
}}
QLabel#Muted {{
    color: {C.TEXT_MUTED};
    background: transparent;
}}
QLabel#Faint {{
    color: {C.TEXT_FAINT};
    background: transparent;
}}
QLabel#KpiValue {{
    font-family: {FONT_MONO};
    font-size: {_px(FS_DISPLAY)}px;
    font-weight: 600;
    color: {C.TEXT};
    background: transparent;
    letter-spacing: 0;
}}
QLabel#KpiLabel {{
    font-size: 10.5px;
    font-weight: 700;
    color: {C.TEXT_MUTED};
    letter-spacing: 0.8px;
    background: transparent;
}}
QLabel#KpiHint {{
    font-size: {_px(FS_SMALL)}px;
    color: {C.TEXT_FAINT};
    background: transparent;
}}
QLabel#HelpTitle {{
    font-size: {_px(FS_BODY)}px;
    font-weight: 600;
    color: {C.TEXT};
    background: transparent;
}}
QLabel#HelpBody {{
    font-size: {_px(FS_SMALL)}px;
    color: {C.TEXT_MUTED};
    background: transparent;
    line-height: 155%;
}}
QLabel#HelpLegal {{
    font-size: {_px(FS_TINY)}px;
    color: {C.TEXT_FAINT};
    background: transparent;
    font-style: italic;
}}
QLabel#Badge {{
    font-size: {_px(FS_TINY)}px;
    font-weight: 700;
    padding: 3px 9px;
    border-radius: {SUDUT_KARTU}px;
    background: {C.NEUTRAL_BG};
    color: {C.TEXT_MUTED};
}}
QLabel#Money {{
    font-family: {FONT_MONO};
    font-size: {_px(FS_BODY)}px;
    background: transparent;
}}
QLabel#MoneyBig {{
    font-family: {FONT_MONO};
    font-size: {_px(FS_H2)}px;
    font-weight: 700;
    background: transparent;
    letter-spacing: -0.3px;
}}
QLabel#LoginTitle {{
    font-family: {FONT_DISPLAY};
    font-size: 30px;
    font-weight: 600;
    color: {C.TEXT};
    background: transparent;
    letter-spacing: -0.2px;
}}
QLabel#LoginSub {{
    font-size: {_px(FS_BODY)}px;
    color: {C.TEXT_MUTED};
    background: transparent;
    line-height: 155%;
}}
/* Label formulir halaman masuk: kalimat biasa, bukan huruf besar
   berjarak, supaya terbaca sebagai formulir resmi dan nyaman dipindai. */
QLabel#LoginLabel {{
    font-size: {_px(FS_SMALL)}px;
    font-weight: 600;
    color: {C.TEXT};
    background: transparent;
}}
QLabel#FormLabel {{
    font-size: {_px(FS_SMALL)}px;
    font-weight: 600;
    color: {C.TEXT};
    background: transparent;
}}
/* Label isian halaman masuk: huruf besar bertracking, seperti kepala kolom
   pada formulir cetak. */
QLabel#FieldLabel {{
    font-size: 10px;
    font-weight: 700;
    color: {C.TEXT_MUTED};
    letter-spacing: 0.9px;
    background: transparent;
}}
/* Label kecil huruf besar di atas judul. Dipakai halaman masuk dan
   beberapa panel agar terbaca sebagai penanda bagian, bukan isi. */
QLabel#Eyebrow {{
    font-size: 10px;
    font-weight: 700;
    color: {C.ACCENT_DARK};
    letter-spacing: 1.6px;
    background: transparent;
}}
QLabel#LoginFooter {{
    font-size: {_px(FS_TINY)}px;
    color: {C.TEXT_FAINT};
    background: transparent;
}}
QLabel#LoginError {{
    background: {C.DANGER_BG};
    color: {C.DANGER};
    border: 1px solid {C.DANGER};
    border-radius: 4px;
    padding: 9px 11px;
    font-size: {_px(FS_SMALL)}px;
    font-weight: 600;
}}
QFrame#PathBox {{
    background: {C.SURFACE_ALT};
    border: 1px solid {C.BORDER};
    border-radius: {SUDUT_KARTU}px;
}}
QFrame#PreviewPaper {{
    background: #FFFFFF;
    border: 1px solid {C.BORDER};
    border-radius: {SUDUT_KARTU}px;
}}

/* ---------------------------------------------------------- tombol */
QPushButton {{
    background: {C.SURFACE};
    color: {C.TEXT};
    border: 1px solid {C.BORDER_STRONG};
    border-radius: {SUDUT_KONTROL}px;
    padding: 7px 15px;
    font-size: {_px(FS_BODY)}px;
    font-weight: 600;
    min-height: 20px;
}}
QPushButton:hover {{
    background: {C.SURFACE_ALT};
    border-color: {C.ACCENT_LIGHT};
}}
QPushButton:pressed {{
    background: {C.NEUTRAL_BG};
}}
QPushButton:disabled {{
    color: {C.TEXT_FAINT};
    background: {C.NEUTRAL_BG};
    border-color: {C.BORDER};
}}
QPushButton#Primary {{
    background: {C.PRIMARY};
    color: {C.TEXT_INVERSE};
    border: 1px solid {C.PRIMARY};
    font-weight: 600;
}}
QPushButton#Primary:hover {{
    background: {C.PRIMARY_DARK};
    border-color: {C.PRIMARY_DARK};
}}
QPushButton#Primary:pressed {{
    background: #0F1518;
}}
QPushButton#Danger {{
    background: {C.DANGER};
    color: {C.TEXT_INVERSE};
    border: 1px solid {C.DANGER};
    font-weight: 600;
}}
QPushButton#Danger:hover {{
    background: #862C26;
    border-color: #862C26;
}}
QPushButton#Success {{
    background: {C.SUCCESS_BG};
    color: {C.SUCCESS};
    border: 1px solid #BFDCCB;
    font-weight: 600;
}}
QPushButton#Success:hover {{
    background: #DFEEE5;
    border-color: #9CCBB2;
}}
QPushButton#Ghost {{
    background: transparent;
    border: none;
    border-bottom: 1px solid transparent;
    color: {C.ACCENT_DARK};
    font-weight: 600;
    padding: 5px 5px;
    border-radius: 0;
}}
QPushButton#Ghost:hover {{
    background: transparent;
    border-bottom-color: {C.ACCENT};
    border-radius: 0;
}}
QPushButton#ModeChoice:checked {{
    background: {C.ACCENT_SOFT};
    color: {C.ACCENT_DARK};
    border: 1px solid {C.ACCENT};
    font-weight: 700;
}}
QPushButton#ModeChoice:checked:hover {{
    background: #F1E2D3;
    border-color: {C.ACCENT_DARK};
}}
QPushButton#NavButton {{
    background: transparent;
    border: none;
    border-left: 2px solid transparent;
    border-radius: 0;
    color: {C.SIDEBAR_TEXT};
    text-align: left;
    padding: 6px 10px 6px 10px;
    font-size: {_px(FS_BODY - 0.5)}px;
    font-weight: 500;
    spacing: 10px;
}}
QPushButton#NavButton:hover {{
    background: {C.SIDEBAR_HOVER};
    color: {C.SIDEBAR_TEXT_ACTIVE};
    border-left: 2px solid transparent;
}}
QPushButton#NavButton:checked {{
    background: {C.SIDEBAR_ACTIVE};
    color: {C.SIDEBAR_TEXT_ACTIVE};
    border-left: 2px solid {C.ACCENT};
    font-weight: 600;
}}
QPushButton#NavSection {{
    background: transparent;
    border: none;
    color: {C.SIDEBAR_SECTION};
    text-align: left;
    padding: 13px 12px 4px 12px;
    font-size: {_px(FS_TINY)}px;
    font-weight: 700;
}}
QPushButton#NavGroup {{
    background: transparent;
    border: none;
    color: {C.SIDEBAR_SECTION};
    text-align: left;
    padding: 9px 10px 3px 10px;
    font-size: {_px(FS_TINY)}px;
    font-weight: 800;
    letter-spacing: 0.7px;
    spacing: 6px;
}}
QPushButton#NavGroup:hover {{
    color: {C.SIDEBAR_TEXT_ACTIVE};
}}
QPushButton#NavGroup:checked {{
    color: {C.SIDEBAR_TEXT};
}}
QPushButton#NavGroup:disabled {{
    color: {C.SIDEBAR_SECTION};
}}

/* ---------------------------------------------------------- input */
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QDateEdit, QSpinBox,
QDoubleSpinBox, QTimeEdit {{
    background: {C.SURFACE};
    border: 1px solid {C.BORDER_STRONG};
    border-radius: {SUDUT_KONTROL}px;
    padding: 7px 11px;
    min-height: 20px;
}}
/* Warna sorotan untuk kolom teks. Biru tua dengan tulisan putih dipakai
   pada teks yang disorot dengan tetikus.
   QComboBox sengaja TIDAK ikut di sini: warna sorotan yang dipasang pada
   QComboBox merambat ke daftar pilihannya, sehingga baris terpilih tertutup
   biru tua penuh dan tulisannya tidak terbaca. Daftar pilihan memakai warna
   sorotan yang lebih muda, diatur pada aturan QComboBoxListView. */
QLineEdit, QTextEdit, QPlainTextEdit, QDateEdit, QSpinBox,
QDoubleSpinBox, QTimeEdit {{
    selection-background-color: {C.PRIMARY};
    selection-color: {C.TEXT_INVERSE};
}}
QComboBox {{
    selection-background-color: {C.ACCENT_SOFT};
    selection-color: {C.TEXT};
    /* Ruang untuk panah di kanan, supaya teks panjang tidak menimpa panah. */
    padding-right: 30px;
}}
/* Bingkai bawaan tombol panah berbentuk persegi dan menimpa sudut bulat
   QComboBox. Bingkainya dibuang; panahnya tetap digambar oleh Qt. */
QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: center right;
    width: 24px;
    border: none;
    background: transparent;
}}
QComboBox::down-arrow {{
    {aturan_panah}
}}
/* Panah QDateEdit dan tombol naik/turun QSpinBox digambar sendiri. Bila
   dibiarkan bawaan, Qt menggambar garis hitam persegi yang menimpa sudut
   membulat dan terlihat seperti kotak isian yang rusak. */
QDateEdit::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: center right;
    width: 24px;
    border: none;
    background: transparent;
}}
QDateEdit::down-arrow {{
    {aturan_panah}
}}
QSpinBox, QDoubleSpinBox, QTimeEdit {{
    max-height: 36px;
    padding-right: 26px;
}}
QSpinBox::up-button, QDoubleSpinBox::up-button, QTimeEdit::up-button {{
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 20px;
    height: 16px;
    border: none;
    background: transparent;
}}
QSpinBox::down-button, QDoubleSpinBox::down-button,
QTimeEdit::down-button {{
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 20px;
    height: 16px;
    border: none;
    background: transparent;
}}
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow, QTimeEdit::up-arrow {{
    {aturan_panah_atas}
}}
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow, QTimeEdit::down-arrow {{
    {aturan_panah}
}}
QLineEdit:hover, QTextEdit:hover, QComboBox:hover, QDateEdit:hover,
QSpinBox:hover, QDoubleSpinBox:hover {{
    border-color: {C.ACCENT_LIGHT};
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus,
QDateEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QTimeEdit:focus {{
    border: 2px solid {C.ACCENT};
    padding: 6px 10px;
}}
/* Tombol panah tetap mendapat ruang saat kotak angka difokuskan, sebab
   bingkai fokus dua piksel memakan satu piksel di tiap sisi. */
QSpinBox:focus, QDoubleSpinBox:focus, QTimeEdit:focus {{
    padding: 6px 25px 6px 10px;
}}
/* Kotak pilihan sama: padding kanan dari aturan fokus di atas menimpa
   ruang panah, sehingga teks panjang kembali menimpa panah saat fokus. */
QComboBox:focus {{
    padding: 6px 30px 6px 10px;
}}
QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled {{
    background: {C.NEUTRAL_BG};
    color: {C.TEXT_FAINT};
}}
QLineEdit[readOnly="true"] {{
    background: {C.SURFACE_ALT};
}}
QLineEdit#MoneyInput {{
    font-family: {FONT_MONO};
    font-size: {_px(FS_H3)}px;
    text-align: right;
    min-height: 22px;
    max-height: 36px;
    padding: 6px 12px;
}}
/* Tinggi QDateEdit dan QComboBox mengikuti kotak isian biasa. Bawaan Qt
   membuat QDateEdit tiga piksel lebih tinggi, sehingga baris formulir yang
   mencampur tanggal, pilihan, dan teks terlihat tidak rata. */
QDateEdit {{
    /* Keterangan: lebar minimum 88 px menjaga tanggal dd/MM/yyyy utuh.
       Ruang kanan 28 px untuk panah tidak boleh memakan teks tanggal,
       sehingga kolom tanggal yang sempit tidak lagi memotong angka
       terakhir. */
    min-width: 88px;
    max-height: 36px;
    padding: 5px 28px 5px 11px;
}}
QDateEdit:focus {{
    padding: 5px 27px 5px 10px;
}}
QLineEdit#LoginInput {{
    padding: 10px 12px;
    font-size: {_px(FS_BODY)}px;
    border-radius: 10px;
    border: 1px solid {C.BORDER_STRONG};
    background: {C.SURFACE};
    min-height: 24px;
}}
QLineEdit#LoginInput:hover {{
    border-color: {C.ACCENT_LIGHT};
}}
QLineEdit#LoginInput:focus {{
    border: 2px solid {C.ACCENT};
    padding: 9px 11px;
}}
/* Kolom masuk berbingkai tipis seperti formulir resmi. Bingkainya yang
   menggambar garis agar tombol "Lihat" dapat duduk sejajar teks. */
QFrame#LoginField {{
    background: {C.SURFACE};
    border: 1px solid {C.BORDER_STRONG};
    border-radius: 6px;
}}
QFrame#LoginField:hover {{
    border: 1px solid {C.ACCENT_LIGHT};
}}
QFrame#LoginField[fokus="true"] {{
    border: 1px solid {C.ACCENT};
}}
QLineEdit#LoginFieldInput {{
    border: none;
    background: transparent;
    padding: 9px 12px;
    font-size: {_px(FS_BODY)}px;
    color: {C.TEXT};
    placeholder-text-color: {C.TEXT_FAINT};
    selection-background-color: {C.ACCENT_SOFT};
    selection-color: {C.TEXT};
}}
QLineEdit#LoginFieldInput:hover, QLineEdit#LoginFieldInput:focus {{
    border: none;
    padding: 9px 12px;
}}
QPushButton#LoginReveal {{
    background: transparent;
    border: none;
    border-radius: 0;
    color: {C.TEXT_MUTED};
    font-size: {_px(FS_TINY)}px;
    font-weight: 600;
    padding: 0 8px 0 2px;
    min-height: 28px;
}}
QPushButton#LoginReveal:hover {{
    background: transparent;
    color: {C.ACCENT_DARK};
}}
QPushButton#LoginReveal:checked {{
    color: {C.ACCENT_DARK};
    background: transparent;
}}
QFrame#LoginHintBox {{
    background: {C.SURFACE_ALT};
    border: 1px solid {C.BORDER};
    border-radius: 4px;
}}
/* Panah kotak pilihan dibiarkan digambar gaya bawaan Qt. Aturan
   ::down-arrow buatan sendiri tampil sebagai kotak kecil di Windows,
   sedangkan ::drop-down tanpa gambar panah menghilangkan panahnya. */
/* Daftar pilihan pada QComboBox.
   Selector "QComboBox QAbstractItemView" tidak dipakai karena popup daftar
   pilihan adalah jendela tersendiri (QComboBoxPrivateContainer), sehingga
   QComboBox tidak berada pada rantai induknya dan aturan itu tidak cocok.
   Akibatnya baris terpilih diwarnai biru tua penuh dari palet bawaan,
   menutupi tulisannya dan membuatnya tampak seperti tajuk gelap.

   Nama kelas di bawah adalah kelas bawaan Qt untuk popup daftar pilihan.
   Aturannya sengaja ditulis tanpa induk supaya berlaku juga pada daftar
   pilihan yang muncul sebagai jendela terpisah. */
QComboBoxListView {{
    background: {C.SURFACE};
    border: none;
    padding: 5px;
    outline: none;
    selection-background-color: {C.ACCENT_SOFT};
    selection-color: {C.TEXT};
}}
/* Tinggi tiap baris daftar pilihan.
   Tanpa aturan ini Qt memakai tinggi bawaan yang hanya menyisakan satu dua
   piksel di atas dan di bawah huruf. Pada huruf berdescender (g, j, p, y)
   bagian bawahnya terpotong sehingga pilihan sulit dibaca dan sulit
   diklik. Tinggi di bawah memberi ruang yang cukup di atas dan di bawah
   teks, sehingga seluruh huruf tampil utuh dan barisnya nyaman ditunjuk
   dengan tetikus.

   border: none wajib ada. Tanpa aturan itu gaya Fusion menggambar kotak
   fokus gelap mengelilingi baris terpilih, sehingga pilihan tampak seperti
   kotak isian di dalam daftar. Sorotan pilihan memakai warna tembaga muda
   yang tenang, bukan kotak bergaris. */
QComboBoxListView::item {{
    min-height: 32px;
    padding: 6px 12px;
    border: none;
    border-radius: 3px;
}}
QComboBoxListView::item:hover {{
    background: {C.SURFACE_ALT};
}}
QComboBoxListView::item:selected {{
    background: {C.ACCENT_SOFT};
    color: {C.TEXT};
    border: none;
}}
QComboBoxListView::item:disabled {{
    color: {C.TEXT_FAINT};
}}
QComboBoxPrivateContainer {{
    background: {C.SURFACE};
    border: 1px solid {C.BORDER_STRONG};
    border-radius: {SUDUT_KONTROL}px;
}}
QComboBoxPrivateContainer > QFrame {{
    background: {C.SURFACE};
    border: none;
}}
QCheckBox, QRadioButton {{
    background: transparent;
    spacing: 9px;
    color: {C.TEXT_MUTED};
}}
QCheckBox:hover, QRadioButton:hover {{
    color: {C.TEXT};
}}
QCheckBox::indicator, QRadioButton::indicator {{
    width: 18px;
    height: 18px;
    border: 1.5px solid {C.BORDER_STRONG};
    background: {C.SURFACE};
}}
QCheckBox::indicator {{ border-radius: 5px; }}
QRadioButton::indicator {{ border-radius: 9px; }}
QCheckBox::indicator:hover, QRadioButton::indicator:hover {{
    border-color: {C.ACCENT};
}}
QCheckBox::indicator:checked {{
    background: {C.ACCENT_DARK};
    border-color: {C.ACCENT_DARK};
    {aturan_centang}
}}
QRadioButton::indicator:checked {{
    background: {C.ACCENT_DARK};
    border: 5px solid {C.ACCENT_DARK};
}}
QCheckBox::indicator:disabled, QRadioButton::indicator:disabled {{
    background: {C.NEUTRAL_BG};
    border-color: {C.BORDER};
}}

/* ---------------------------------------------------------- tabel */
QTableWidget, QTableView, QTreeWidget, QTreeView {{
    background: {C.SURFACE};
    border: 1px solid {C.BORDER};
    border-radius: 2px;
    gridline-color: transparent;
    selection-background-color: {C.ACCENT_SOFT};
    selection-color: {C.TEXT};
    outline: none;
    alternate-background-color: #FAFAFA;
}}
QTableWidget::item, QTableView::item, QTreeWidget::item {{
    padding: 9px 10px;
    border: none;
    border-bottom: 1px solid #F0F0F0;
}}
QTableWidget::item:hover, QTableView::item:hover, QTreeWidget::item:hover {{
    background: {C.PRIMARY_TINT};
}}
QTableWidget::item:selected, QTableView::item:selected, QTreeWidget::item:selected {{
    background: {C.ACCENT_SOFT};
    color: {C.TEXT};
}}
QHeaderView::section {{
    background: {C.SURFACE};
    color: {C.TEXT_MUTED};
    padding: 9px 10px;
    border: none;
    border-bottom: 1px solid {C.BORDER_STRONG};
    font-size: 10.5px;
    font-weight: 700;
    letter-spacing: 0.7px;
}}
QHeaderView::section:last {{
    border-right: none;
}}
QTableCornerButton::section {{
    background: {C.SURFACE};
    border: none;
}}

/* ---------------------------------------------------------- tabs */
QTabWidget::pane {{
    border: none;
    background: transparent;
    top: 0;
}}
/* Garis pemisah di bawah baris tab digambar oleh widgets.Tab, bukan oleh
   Qt. Garis bawaan Qt memakai warna palet sistem dan letaknya tidak
   sebaris dengan penanda tab terpilih. */
QTabBar {{
    background: transparent;
    border: none;
}}
QTabBar::tab {{
    background: transparent;
    color: {C.TEXT_MUTED};
    padding: 9px 14px 7px 14px;
    margin-right: 4px;
    border: none;
    border-bottom: 2px solid transparent;
    font-weight: 600;
}}
QTabBar::tab:hover {{
    color: {C.ACCENT_DARK};
    background: transparent;
}}
QTabBar::tab:selected {{
    background: transparent;
    color: {C.TEXT};
    border-bottom: 2px solid {C.ACCENT};
}}

/* ---------------------------------------------------------- scroll */
QScrollBar:vertical {{
    background: transparent;
    width: 9px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: #C9C9C9;
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: #A9A9A9;
}}
/* sidebar gelap: scrollbar dibuat terang agar terlihat */
QScrollArea#SidebarScroll QScrollBar:vertical {{
    width: 6px;
    margin: 2px 1px;
}}
QScrollArea#SidebarScroll QScrollBar::handle:vertical {{
    background: #4C5A5F;
    border-radius: 3px;
    min-height: 26px;
}}
QScrollArea#SidebarScroll QScrollBar::handle:vertical:hover {{
    background: #6E7D82;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
}}
QScrollBar::handle:horizontal {{
    background: #C9C9C9;
    border-radius: 5px;
    min-width: 30px;
}}
QScrollBar::handle:horizontal:hover {{
    background: #A9A9A9;
}}
QScrollBar::add-line, QScrollBar::sub-line {{
    height: 0; width: 0;
}}
QScrollBar::add-page, QScrollBar::sub-page {{
    background: transparent;
}}

/* ---------------------------------------------------------- lain */
QScrollArea {{
    border: none;
    background: transparent;
}}
QScrollArea > QWidget > QWidget {{
    background: transparent;
}}
QGroupBox {{
    background: {C.SURFACE};
    border: 1px solid {C.BORDER};
    border-radius: {SUDUT_KARTU}px;
    margin-top: 16px;
    padding: 16px 12px 12px 12px;
    font-weight: 600;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: {C.ACCENT_DARK};
    background: {C.SURFACE};
}}
QProgressBar {{
    border: none;
    border-radius: 6px;
    background: {C.NEUTRAL_BG};
    height: 10px;
    text-align: center;
    color: transparent;
}}
QProgressBar::chunk {{
    border-radius: 6px;
    background: {C.ACCENT};
}}
QSlider {{
    background: transparent;
    min-height: 22px;
}}
QSlider::groove:horizontal {{
    height: 4px;
    background: {C.NEUTRAL_BG};
    border-radius: 2px;
}}
QSlider::sub-page:horizontal {{
    background: {C.ACCENT};
    border-radius: 2px;
}}
QSlider::add-page:horizontal {{
    background: {C.BORDER};
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    width: 16px;
    margin: -6px 0;
    border-radius: 8px;
    background: {C.SURFACE};
    border: 2px solid {C.ACCENT};
}}
QSlider::handle:horizontal:hover {{
    background: {C.SURFACE_ALT};
    border-color: {C.PRIMARY};
}}
QSlider::handle:horizontal:pressed {{
    background: {C.ACCENT};
}}
/* Menu bar menyatu dengan menu samping sehingga jendela terasa satu bingkai
   gelap yang tipis, bukan pita putih terpisah di atas antarmuka. */
QMenuBar {{
    background: {C.SIDEBAR_BG};
    border: none;
    padding: 2px 8px;
    spacing: 2px;
    font-size: {_px(FS_SMALL)}px;
}}
QMenuBar::item {{
    background: transparent;
    color: {C.SIDEBAR_TEXT};
    padding: 6px 12px;
    margin: 2px 1px;
    border-radius: 6px;
    font-weight: 500;
}}
QMenuBar::item:selected {{
    background: {C.SIDEBAR_HOVER};
    color: {C.SIDEBAR_TEXT_ACTIVE};
}}
QMenuBar::item:pressed {{
    background: {C.SIDEBAR_ACTIVE};
    color: {C.SIDEBAR_TEXT_ACTIVE};
}}

/* ------------------------------------------------- kalender popup */
QCalendarWidget QWidget#qt_calendar_navigationbar {{
    background: {C.PRIMARY};
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    padding: 5px 6px;
}}
QCalendarWidget QToolButton {{
    background: transparent;
    color: {C.TEXT_INVERSE};
    border: none;
    border-radius: 6px;
    padding: 5px 10px;
    font-size: {_px(FS_BODY)};
    font-weight: 600;
}}
QCalendarWidget QToolButton:hover {{
    background: {C.PRIMARY_LIGHT};
}}
QCalendarWidget QToolButton::menu-indicator {{
    image: none;
    width: 0px;
}}
QCalendarWidget QMenu {{
    background: {C.SURFACE};
    color: {C.TEXT};
    border: 1px solid {C.BORDER_STRONG};
    border-radius: 6px;
    padding: 4px;
}}
QCalendarWidget QSpinBox {{
    background: {C.SURFACE};
    color: {C.TEXT};
    border: 1px solid {C.BORDER_STRONG};
    border-radius: 5px;
    padding: 2px 6px;
    font-size: {_px(FS_BODY)};
    font-weight: 600;
    selection-background-color: {C.PRIMARY};
    selection-color: {C.TEXT_INVERSE};
}}
QCalendarWidget QAbstractItemView:enabled {{
    background: {C.SURFACE};
    color: {C.TEXT};
    selection-background-color: {C.ACCENT_DARK};
    selection-color: {C.TEXT_INVERSE};
    outline: none;
    font-size: {_px(FS_SMALL)};
}}
QCalendarWidget QAbstractItemView:disabled {{
    color: {C.TEXT_FAINT};
}}
QCalendarWidget QTableView {{
    border: 1px solid {C.BORDER};
    border-top: none;
    border-bottom-left-radius: 8px;
    border-bottom-right-radius: 8px;
    gridline-color: {C.BORDER};
}}
QCalendarWidget QTableView::item {{
    padding: 4px 2px;
}}
QCalendarWidget QTableView::item:selected {{
    background: {C.ACCENT_DARK};
    color: {C.TEXT_INVERSE};
    border-radius: 4px;
}}
QCalendarWidget QHeaderView::section {{
    background: {C.NEUTRAL_BG};
    color: {C.TEXT_MUTED};
    border: none;
    border-bottom: 1px solid {C.BORDER};
    padding: 5px 2px;
    font-size: {_px(FS_TINY)};
    font-weight: 700;
}}
QCalendarWidget QWidget {{
    alternate-background-color: {C.SURFACE_ALT};
}}
QMenu {{
    background: {C.SURFACE};
    border: 1px solid {C.BORDER_STRONG};
    border-radius: {SUDUT_KONTROL}px;
    padding: 5px;
}}
QMenu::item {{
    padding: 7px 22px 7px 14px;
    border-radius: 5px;
    color: {C.TEXT};
}}
QMenu::item:selected {{
    background: {C.ACCENT_SOFT};
    color: {C.ACCENT_DARK};
}}
QMenu::item:disabled {{
    color: {C.TEXT_FAINT};
}}
QMenu::separator {{
    height: 1px;
    background: {C.BORDER};
    margin: 5px 8px;
}}
QToolTip {{
    background: {C.TEXT};
    color: {C.TEXT_INVERSE};
    border: none;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: {_px(FS_SMALL)};
}}
QSplitter::handle {{
    background: {C.BORDER};
}}
QSplitter::handle:horizontal {{
    width: 3px;
}}
QSplitter::handle:vertical {{
    height: 3px;
}}
QPushButton#SplitToggle {{
    background: transparent;
    border: 1px solid transparent;
    border-radius: 3px;
    color: {C.TEXT_MUTED};
    font-size: {_px(FS_TINY)};
    font-weight: 600;
    padding: 2px 8px;
    margin-left: 8px;
}}
QPushButton#SplitToggle:hover {{
    background: {C.BG};
    border-color: {C.BORDER};
    color: {C.TEXT};
}}
QPushButton#SplitToggle:checked {{
    background: {C.ACCENT_SOFT};
    border-color: {C.ACCENT};
    color: {C.ACCENT_DARK};
}}
QStatusBar {{
    background: {C.SURFACE};
    border-top: 1px solid {C.BORDER};
    color: {C.TEXT_MUTED};
}}
QStatusBar::item {{
    border: none;
}}
"""


def money(amount, prefix: str = "Rp", negatif_merah: bool = True) -> str:
    """Format angka rupiah: Rp1.234.567"""
    try:
        v = int(round(float(amount)))
    except (TypeError, ValueError):
        return f"{prefix}0"
    s = f"{prefix}{abs(v):,}".replace(",", ".")
    return f"-{s}" if v < 0 else s


def persen(v: float, desimal: int = 1) -> str:
    """Persen dengan koma desimal, sesuai penulisan angka Indonesia."""
    try:
        teks = f"{float(v) * 100:.{desimal}f}"
    except (TypeError, ValueError):
        return "0%"
    return teks.replace(".", ",") + "%"


def tanggal_id(iso: str) -> str:
    """Ubah 2026-01-15 menjadi 15 Jan 2026."""
    from ..config import MONTH_ABBR_ID
    if not iso or len(str(iso)) < 10:
        return str(iso or "")
    try:
        y, m, d = str(iso)[:10].split("-")
        return f"{int(d)} {MONTH_ABBR_ID[int(m) - 1]} {y}"
    except (ValueError, IndexError):
        return str(iso)


def latar(widget, aturan: str) -> None:
    """Pasang gaya latar pada satu widget saja, tanpa menular ke anaknya.

    Qt menerapkan stylesheet ke widget dan seluruh anaknya. Deklarasi tanpa
    selector seperti "background: #FFF;" karena itu ikut menimpa latar
    tombol, kotak isian, dan tabel di dalamnya - akibatnya tombol biru bisa
    berubah pucat dengan teks putih yang tidak terbaca.

    Selector memakai kelas widget induknya (#ObjectName) dan hanya berlaku
    untuk widget itu sendiri, sehingga anak-anaknya tetap memakai gayanya
    masing-masing.
    """
    nama = widget.objectName()
    if not nama:
        nama = f"Latar{id(widget)}"
        widget.setObjectName(nama)

    isi = aturan.strip().rstrip(";")
    if not isi:
        return
    kelas = type(widget).__name__
    widget.setStyleSheet(f"{kelas}#{nama} {{ {isi}; }}")


def pasang_penyesuai_dialog(app) -> None:
    """
    Rapikan setiap dialog tepat sebelum ditampilkan.

    Penyesuaian ukuran hanya berjalan untuk halaman, sedangkan banyak isian
    berada di dalam dialog. Akibatnya daftar pilihan di dialog tetap memakai
    tinggi baris bawaan yang mepet sehingga hurufnya terpotong.

    Dialog dibuka dari puluhan tempat berbeda, jadi penyuntingan satu per
    satu mudah terlewat dan mudah lupa saat ada dialog baru. Penyaring
    peristiwa di bawah menangani semuanya sekaligus: setiap kali sebuah
    dialog hendak ditampilkan, isinya dirapikan lebih dulu.

    Penyaring yang sama membatasi tinggi daftar pilihan yang panjang.
    Gaya Fusion mengabaikan maxVisibleItems, sehingga daftar berisi
    puluhan akun membuka setinggi layar dan menutupi halaman.
    """
    from PySide6.QtCore import QEvent, QObject, QPoint, QTimer
    from PySide6.QtWidgets import (QComboBox, QDoubleSpinBox, QDialog,
                                   QSpinBox, QTimeEdit, QWidget)

    def batasi_daftar_pilihan(kontainer) -> None:
        combo = kontainer.parentWidget()
        if not isinstance(combo, QComboBox):
            return
        baris = combo.view().sizeHintForRow(0)
        if baris <= 0:
            return
        layar = combo.screen().availableGeometry() if combo.screen() else None
        if layar is None:
            return
        # Bingkai popup: selisih tinggi kontainer dan area tampil daftar.
        # Angka ini dipakai agar daftar pendek tidak kurang satu dua piksel,
        # karena kekurangan sekecil itu sudah memunculkan panah gulir yang
        # menutupi baris terakhir.
        bingkai = kontainer.height() - combo.view().viewport().height()
        isi = baris * combo.count() + bingkai
        batas = baris * 10 + 24
        tambahan = 0
        if isi <= batas and any(
                anak.metaObject().className() == "QComboBoxPrivateScroller"
                and anak.isVisible() for anak in kontainer.findChildren(QWidget)):
            # Panah gulir memakan sepuluh piksel. Untuk daftar yang
            # seharusnya muat seluruhnya, ruang itu dikembalikan agar
            # baris terakhir tidak terpotong.
            tambahan = 10
        tinggi = min(isi + tambahan, batas, layar.height() - 16)
        if tinggi == kontainer.height():
            return
        asal = combo.mapToGlobal(QPoint(0, 0))
        bawah = asal.y() + combo.height()
        if bawah + tinggi <= layar.bottom():
            y = bawah
        elif asal.y() - tinggi >= layar.top():
            y = asal.y() - tinggi
        else:
            y = max(layar.top(),
                    min(kontainer.y(), layar.bottom() - tinggi))
        kontainer.setGeometry(kontainer.x(), y, kontainer.width(), tinggi)
        if tinggi >= isi:
            def sembunyikan_panah():
                # Pastikan seluruh pilihan benar-benar muat sebelum
                # menyembunyikan panah gulir; bila tidak, panah itu tetap
                # diperlukan untuk mencapai baris terakhir.
                if (combo.view().viewport().height()
                        < baris * combo.count()):
                    return
                for anak in kontainer.findChildren(QWidget):
                    if (anak.metaObject().className()
                            == "QComboBoxPrivateScroller"):
                        anak.hide()

            # Tunggu tata letak selesai agar tinggi area tampil daftar
            # sudah memperhitungkan ukuran baru.
            QTimer.singleShot(0, sembunyikan_panah)

    class PenyesuaiDialog(QObject):
        def eventFilter(self, objek, peristiwa):
            if peristiwa.type() == QEvent.Show:
                if isinstance(objek, (QSpinBox, QDoubleSpinBox, QTimeEdit)):
                    # Tinggi minimum bawaan QSpinBox 40 px karena tombol
                    # naik/turun, empat piksel lebih tinggi daripada kotak
                    # isian dan pilihan di sebelahnya. Batas tinggi dari
                    # stylesheet tidak menimpa tinggi minimum itu, jadi
                    # tingginya dipatok langsung agar baris formulir rata.
                    if objek.maximumHeight() > TINGGI_KONTROL:
                        objek.setMaximumHeight(TINGGI_KONTROL)
                elif (objek.metaObject().className()
                      == "QComboBoxPrivateContainer"):
                    batasi_daftar_pilihan(objek)
                elif isinstance(objek, QDialog):
                    try:
                        rapikan_label(objek)
                    except Exception:
                        # Dialog tetap boleh tampil walau penyesuaian gagal.
                        pass
            return super().eventFilter(objek, peristiwa)

    penyesuai = PenyesuaiDialog(app)
    app.installEventFilter(penyesuai)
    # Simpan rujukannya supaya tidak dibuang pengumpul sampah.
    app._penyesuai_dialog = penyesuai


def _pasang_tinggi_baris(baris, tinggi: int) -> None:
    """
    Tetapkan tinggi setiap baris pada daftar pilihan.

    QListView tidak punya pengaturan tinggi baris seperti tabel, jadi
    tingginya diambil dari ukuran yang diminta delegate. Delegate bawaan
    mengembalikan tinggi teks saja tanpa ruang tambahan, sehingga huruf
    berdescender terpotong. Delegate di bawah menambahkan ruang itu.

    Delegate dipasang sekali saja per daftar, supaya pemanggilan berulang
    tidak menumpuk pembungkus di atas pembungkus.
    """
    from PySide6.QtCore import QSize
    from PySide6.QtWidgets import (QStyle, QStyledItemDelegate,
                                   QStyleOptionViewItem)

    delegate = getattr(baris, "_delegate_tinggi", None)
    if delegate is not None:
        delegate.tinggi = tinggi
        # doItemsLayout menghitung ulang tinggi baris tanpa mengosongkan
        # pilihan. reset() juga menghitung ulang, tetapi membuang indeks
        # terpilih sehingga daftar terbuka tanpa sorotan pada pilihan aktif.
        baris.doItemsLayout()
        return

    class DelegateBaris(QStyledItemDelegate):
        """
        Delegate dengan tinggi baris tetap.

        Mewarisi QStyledItemDelegate, bukan delegate bawaan daftar. Delegate
        bawaan dimiliki oleh tampilan dan dapat dibuang Qt kapan saja; kelas
        yang mewarisinya lalu dipakai sebagai delegate baru menjadi tidak
        sah dan membuat aplikasi berhenti mendadak.
        """

        def __init__(self, induk, tinggi_baris: int):
            super().__init__(induk)
            self.tinggi = tinggi_baris

        def sizeHint(self, opsi, indeks):
            ukuran = super().sizeHint(opsi, indeks)
            return QSize(ukuran.width(), self.tinggi)

        def paint(self, pelukis, opsi, indeks):
            # Gaya Fusion menggambar kotak fokus gelap mengelilingi baris
            # terpilih. Sorotan pilihan sudah jelas dari warna latar, jadi
            # kotak fokus itu dibuang supaya daftar terlihat bersih.
            opsi_bersih = QStyleOptionViewItem(opsi)
            opsi_bersih.state &= ~QStyle.State_HasFocus
            super().paint(pelukis, opsi_bersih, indeks)

    delegate = DelegateBaris(baris, tinggi)
    baris.setItemDelegate(delegate)
    baris._delegate_tinggi = delegate


def matikan_tinggi_dari_lebar(lbl) -> None:
    """
    Matikan tinggi-dari-lebar pada label berbalut setelah tingginya dipatok.

    Qt menyalakan tinggi-dari-lebar secara otomatis begitu pembungkusan teks
    dinyalakan. Akibatnya setiap perhitungan tata letak menanyakan tinggi
    setiap label berbalut, dan pada halaman dengan ratusan label pekerjaan
    itu memakan ratusan milidetik sehingga perpindahan menu terasa tersendat.

    Tinggi label sudah dipatok lewat tinggi minimum dari pengukuran dokumen
    teks, jadi Qt tidak perlu menghitungnya lagi.
    """
    kebijakan = lbl.sizePolicy()
    if kebijakan.hasHeightForWidth():
        kebijakan.setHeightForWidth(False)
        lbl.setSizePolicy(kebijakan)


def rapikan_label(akar) -> None:
    """Rapikan seluruh widget agar tidak ada teks yang terpotong.

    Dipanggil setelah halaman selesai disusun. Yang dikerjakan:

    1. Label keterangan dibiarkan membungkus ke baris berikutnya sehingga
       teksnya selalu terbaca utuh, termasuk saat jendela diperkecil.
    2. Label panjang yang belum membungkus diaktifkan pembungkusannya.
    3. Tombol diberi lebar minimum sesuai teksnya supaya tidak terhimpit.
    4. Kotak pilihan dilebarkan sesuai pilihan terpanjangnya.
    """
    from PySide6.QtGui import QFontMetrics
    from PySide6.QtWidgets import QComboBox, QLabel, QPushButton

    for lbl in akar.findChildren(QLabel):
        if lbl.objectName() in ("KpiLabel", "KpiHint", "Muted", "Faint"):
            # Label ringkas (mis. "25 invoice · total piutang ...") harus
            # tetap satu baris. Membungkusnya membuat baris alat dan kaki
            # tabel meninggi hanya karena Qt memberi lebar sebesar sizeHint.
            # Label keterangan yang panjang tetap dibungkus oleh aturan
            # berikutnya, jadi teksnya tidak pernah terpotong.
            if len(lbl.text()) >= 60:
                lbl.setWordWrap(True)
            lbl.setMinimumWidth(0)

    # Label penjelasan panjang tidak boleh terpotong di jendela sempit.
    for lbl in akar.findChildren(QLabel):
        if lbl.wordWrap() or not lbl.text() or "<" in lbl.text():
            continue
        if lbl.objectName() in ("SectionTitle", "PageTitle", "KpiValue"):
            continue
        teks = lbl.text()
        if "\n" in teks or len(teks) < 60:
            continue
        lbl.setWordWrap(True)

    # Label teks berformat: tinggi minimum diambil dari pengukuran dokumen
    # teks pada lebar nyatanya. Qt menghitung tinggi teks berformat lebih
    # pendek dari kebutuhan sebenarnya, sehingga baris terakhirnya terpotong.
    #
    # Tinggi dipatok lewat tinggi minimum, lalu tinggi-dari-lebar dimatikan.
    # Tinggi-dari-lebar memaksa Qt menanyakan tinggi setiap label berbalut
    # pada setiap perhitungan tata letak. Dengan ratusan label di satu
    # halaman, pekerjaan itu memakan ratusan milidetik dan perpindahan menu
    # terasa tersendat. Tinggi minimum memberi hasil tampilan yang sama
    # tanpa beban tersebut.
    for lbl in akar.findChildren(QLabel):
        if not lbl.wordWrap() or not lbl.text():
            continue
        # Judul dan subjudul header dikecualikan. Tata letak header dihitung
        # oleh PageHeader.heightForWidth, dan perhitungan itu bergantung pada
        # label anaknya yang boleh meminta tinggi sendiri. Mematikannya di
        # sini membuat header kehilangan tingginya.
        # Label panel penjelasan juga dikecualikan: ukuran panelnya kecil,
        # sehingga perhitungan tinggi-dari-lebar tidak membebani, sedangkan
        # tanpa perhitungan itu panel menyisakan ruang kosong yang besar.
        if lbl.objectName() in ("PageTitle", "PageSubtitle",
                                "HelpBody", "HelpLegal"):
            continue
        if "<" in lbl.text():
            tinggi = tinggi_rich_text(lbl)
            if lbl.minimumHeight() < tinggi:
                lbl.setMinimumHeight(tinggi)
        matikan_tinggi_dari_lebar(lbl)

    # Tombol: lebar minimum mengikuti teksnya. Tombol navigasi sidebar
    # dikecualikan karena lebarnya sudah ditentukan oleh lebar sidebar;
    # memaksakan lebar minimum membuat isinya meluber keluar panel.
    for btn in akar.findChildren(QPushButton):
        if btn.objectName() in ("NavGroup", "NavItem", "NavButton"):
            continue
        if btn.text() and btn.minimumWidth() < btn.sizeHint().width():
            btn.setMinimumWidth(btn.sizeHint().width())

    # Kotak pilihan: lebar daftar mengikuti pilihan terpanjang, tetapi lebar
    # kotaknya sendiri dibatasi. Bila kotak ikut dilebarkan sampai ratusan
    # piksel, baris tombol di sebelahnya terdesak keluar tepi halaman.
    for cmb in akar.findChildren(QComboBox):
        if cmb.count() == 0:
            continue
        metrik = QFontMetrics(cmb.font())
        lebar = max(metrik.horizontalAdvance(cmb.itemText(i))
                    for i in range(cmb.count())) + 46
        if lebar > cmb.minimumWidth():
            cmb.setMinimumWidth(min(300, lebar))
        # Daftar pilihan tetap dapat menampilkan teks utuh saat dibuka.
        cmb.view().setMinimumWidth(min(560, max(lebar, 200)))

        # Tinggi baris daftar pilihan.
        #
        # Tinggi bawaan Qt hanya menyisakan satu dua piksel di atas dan di
        # bawah huruf, sehingga huruf berdescender seperti g, j, p, dan y
        # terpotong dan barisnya sulit ditunjuk. Tinggi di bawah memberi
        # ruang yang cukup untuk huruf 16 piksel.
        #
        # Diatur melalui ukuran petunjuk delegate, karena daftar pilihan
        # memakai QListView yang tidak punya pengaturan tinggi baris
        # langsung. Sekaligus ditetapkan tinggi minimum barisnya.
        tinggi = max(32, metrik.height() + 16)
        baris = cmb.view()
        baris.setMinimumHeight(min(260, cmb.count() * tinggi + 10))
        if not cmb.property("delegasi_pilihan"):
            _pasang_tinggi_baris(baris, tinggi)
