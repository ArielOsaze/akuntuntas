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
    # Merek - biru tua yang tenang, biasa dipakai perangkat lunak keuangan
    PRIMARY = "#1B4F8A"
    PRIMARY_DARK = "#143C6B"
    PRIMARY_LIGHT = "#2E6DB4"
    PRIMARY_SOFT = "#E8F0F9"
    PRIMARY_TINT = "#F4F8FC"
    ACCENT = "#047857"

    # Sidebar - biru malam yang dalam, bukan hitam pekat
    SIDEBAR_BG = "#0F2942"
    SIDEBAR_HOVER = "#1A3A5C"
    SIDEBAR_ACTIVE = "#1B4F8A"
    SIDEBAR_TEXT = "#D8E4EE"
    SIDEBAR_TEXT_ACTIVE = "#FFFFFF"
    SIDEBAR_SECTION = "#9CB2C6"

    # Latar
    BG = "#F4F6F9"
    SURFACE = "#FFFFFF"
    SURFACE_ALT = "#FAFBFC"
    BORDER = "#DFE4EA"
    BORDER_STRONG = "#C4CDD8"

    # Teks
    TEXT = "#1A2733"
    TEXT_MUTED = "#48586B"
    TEXT_FAINT = "#54637A"
    TEXT_INVERSE = "#FFFFFF"

    # Status
    SUCCESS = "#047857"
    SUCCESS_BG = "#E6F6F0"
    WARNING = "#A15C07"
    WARNING_BG = "#FEF3E2"
    DANGER = "#B91C1C"
    DANGER_BG = "#FDECEC"
    INFO = "#2563EB"
    INFO_BG = "#E8F0FE"
    NEUTRAL_BG = "#EEF2F6"

    # Angka
    DEBIT = "#1B4F8A"
    KREDIT = "#8A4B08"
    POSITIF = "#047857"
    NEGATIF = "#B91C1C"


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

# Sudut membulat: kartu lebih besar, kontrol lebih kecil
SUDUT_KARTU = 12
SUDUT_KONTROL = 8

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
# Font antarmuka. "Segoe UI Variable Text" adalah font sistem Windows 11 yang
# bentuk hurufnya lebih terbuka dan lebih jelas dibaca pada layar. Windows 10
# tidak memilikinya, jadi dipakai berurutan: sistem akan memilih font pertama
# yang tersedia. "Segoe UI" selalu ada di Windows 10 maupun 11.
FONT_FAMILY = "Segoe UI Variable Text, Segoe UI, Tahoma, sans-serif"

# Nama font pertama saja, untuk ditulis di stylesheet per widget. Qt hanya
# menerima satu nama keluarga di properti font-family stylesheet, jadi daftar
# berurut di FONT_FAMILY tidak berlaku di sana.
FONT_UI = FONT_FAMILY.split(",")[0].strip()

# Font angka. Nominal memakai font antarmuka yang sama dengan fitur OpenType
# "tnum" (tabular numbers) aktif, sehingga digitnya seragam lebarnya dan
# sejajar antarbaris tanpa terlihat seperti huruf kode. Fitur ini didukung
# font sistem Windows 10 maupun 11.
FONT_MONO = FONT_FAMILY
FONT_ANGKA = FONT_UI

# Ukuran teks nominal, dipakai agar tidak terlalu besar pada kartu ringkas.
UKURAN_ANGKA = 22


def font_angka(ukuran: float = None, tebal: bool = True) -> QFont:
    """
    Font untuk menampilkan nominal rupiah.

    Digit dibuat berlebar sama lewat fitur OpenType "tnum" supaya angka
    sejajar antarbaris dan mudah dibandingkan, sementara bentuk hurufnya
    tetap font antarmuka yang jelas dibaca.
    """
    f = QFont(FONT_UI)
    f.setPixelSize(int(ukuran or UKURAN_ANGKA))
    if tebal:
        f.setWeight(QFont.Bold)
    try:
        f.setFeature(QFont.Tag("tnum"), 1)
    except Exception:
        # Qt lama tidak mendukung fitur huruf; angka tetap tampil normal
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
FS_H1 = 20
FS_H2 = 16
FS_H3 = 14
FS_BODY = 13
FS_SMALL = 12
FS_TINY = 11

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
    p.setColor(QPalette.Highlight, QColor(C.PRIMARY_SOFT))
    p.setColor(QPalette.HighlightedText, tinta)
    p.setColor(QPalette.Link, QColor(C.PRIMARY))
    p.setColor(QPalette.Disabled, QPalette.Text, QColor(C.TEXT_FAINT))
    p.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(C.TEXT_FAINT))
    p.setColor(QPalette.Disabled, QPalette.WindowText, QColor(C.TEXT_FAINT))

    app.setPalette(p)


def _px(ukuran: float) -> str:
    """Ukuran teks dalam piksel, mengikuti skala ukuran teks aplikasi."""
    return f"{ukuran * UKURAN_TEKS:.1f}"


def stylesheet() -> str:
    return f"""
/* ---------------------------------------------------------- dasar */
* {{
    font-family: {FONT_FAMILY};
    font-size: {_px(FS_BODY)};
    color: {C.TEXT};
}}
QWidget {{
    background: {C.BG};
}}
QMainWindow, QDialog {{
    background: {C.BG};
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
QFrame#HelpPanel {{
    background: {C.PRIMARY_TINT};
    border: 1px solid #D6E4F2;
    border-left: 3px solid {C.PRIMARY};
    border-radius: {SUDUT_KONTROL}px;
}}
QFrame#WarningPanel {{
    background: {C.WARNING_BG};
    border: 1px solid #F5D9AE;
    border-left: 3px solid {C.WARNING};
    border-radius: {SUDUT_KONTROL}px;
}}
QFrame#DangerPanel {{
    background: {C.DANGER_BG};
    border: 1px solid #F5C2C2;
    border-left: 3px solid {C.DANGER};
    border-radius: {SUDUT_KONTROL}px;
}}
QFrame#SuccessPanel {{
    background: {C.SUCCESS_BG};
    border: 1px solid #B8E6D5;
    border-left: 3px solid {C.SUCCESS};
    border-radius: {SUDUT_KONTROL}px;
}}
QFrame#TemuanCard {{
    background: {C.SURFACE};
    border: 1px solid {C.BORDER};
    border-radius: {SUDUT_KONTROL}px;
}}
QFrame#Divider {{
    background: {C.BORDER};
    max-height: 1px;
    min-height: 1px;
    border: none;
}}

/* ---------------------------------------------------------- label */
QLabel#PageTitle {{
    font-size: {_px(FS_H1)}px;
    font-weight: 700;
    color: {C.TEXT};
    background: transparent;
    letter-spacing: -0.2px;
}}
QLabel#PageSubtitle {{
    font-size: {_px(FS_SMALL)}px;
    color: {C.TEXT_MUTED};
    background: transparent;
    line-height: 150%;
}}
QLabel#SectionTitle {{
    font-size: {_px(FS_H3)}px;
    font-weight: 700;
    color: {C.TEXT};
    background: transparent;
    letter-spacing: -0.1px;
}}
QLabel#CardTitle {{
    font-size: {_px(FS_TINY)}px;
    font-weight: 700;
    color: {C.TEXT_MUTED};
    text-transform: uppercase;
    letter-spacing: 0.7px;
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
    font-weight: 700;
    color: {C.TEXT};
    background: transparent;
    letter-spacing: -0.5px;
}}
QLabel#KpiLabel {{
    font-size: {_px(FS_SMALL)}px;
    font-weight: 700;
    color: {C.TEXT_MUTED};
    letter-spacing: 0.3px;
    background: transparent;
}}
QLabel#KpiHint {{
    font-size: {_px(FS_SMALL)}px;
    color: {C.TEXT_FAINT};
    background: transparent;
}}
QLabel#HelpTitle {{
    font-size: {_px(FS_BODY)}px;
    font-weight: 700;
    color: {C.PRIMARY_DARK};
    background: transparent;
}}
QLabel#HelpBody {{
    font-size: {_px(FS_SMALL)}px;
    color: #2C3E50;
    background: transparent;
    line-height: 155%;
}}
QLabel#HelpLegal {{
    font-size: {_px(FS_TINY)}px;
    color: {C.PRIMARY_DARK};
    background: transparent;
    font-style: italic;
}}
QLabel#Badge {{
    font-size: {_px(FS_TINY)}px;
    font-weight: 700;
    padding: 3px 9px;
    border-radius: 10px;
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
    font-size: 28px;
    font-weight: 700;
    color: {C.TEXT_INVERSE};
    background: transparent;
}}
QLabel#LoginSub {{
    font-size: {_px(FS_BODY)};
    color: #A8C0D8;
    background: transparent;
}}
QLabel#LoginFeature {{
    font-size: {_px(FS_SMALL)};
    color: #CFE0F0;
    background: transparent;
}}
QLabel#BrandMark {{
    font-size: 22px;
    font-weight: 800;
    color: {C.PRIMARY};
    background: transparent;
}}
QLabel#FormLabel {{
    font-size: {_px(FS_SMALL)};
    font-weight: 600;
    color: {C.TEXT};
    background: transparent;
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
    border-color: {C.PRIMARY_LIGHT};
    color: {C.PRIMARY_DARK};
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
    background: {C.PRIMARY_LIGHT};
    border-color: {C.PRIMARY_LIGHT};
}}
QPushButton#Primary:pressed {{
    background: {C.PRIMARY_DARK};
}}
QPushButton#Danger {{
    background: {C.DANGER};
    color: {C.TEXT_INVERSE};
    border: 1px solid {C.DANGER};
    font-weight: 600;
}}
QPushButton#Danger:hover {{
    background: #A01818;
}}
QPushButton#Success {{
    background: {C.SUCCESS};
    color: {C.TEXT_INVERSE};
    border: 1px solid {C.SUCCESS};
    font-weight: 600;
}}
QPushButton#Success:hover {{
    background: #036B4E;
}}
QPushButton#Ghost {{
    background: transparent;
    border: none;
    color: {C.PRIMARY};
    font-weight: 600;
    padding: 5px 8px;
}}
QPushButton#Ghost:hover {{
    background: {C.PRIMARY_SOFT};
    border-radius: 6px;
}}
QPushButton#NavButton {{
    background: transparent;
    border: none;
    border-left: 3px solid transparent;
    border-radius: 7px;
    color: {C.SIDEBAR_TEXT};
    text-align: left;
    padding: 8px 10px 8px 8px;
    font-size: {_px(FS_BODY - 0.5)}px;
    font-weight: 500;
    spacing: 10px;
}}
QPushButton#NavButton:hover {{
    background: {C.SIDEBAR_HOVER};
    color: {C.SIDEBAR_TEXT_ACTIVE};
    border-left: 3px solid {C.SIDEBAR_SECTION};
}}
QPushButton#NavButton:checked {{
    background: {C.SIDEBAR_ACTIVE};
    color: {C.SIDEBAR_TEXT_ACTIVE};
    border-left: 3px solid {C.SIDEBAR_TEXT_ACTIVE};
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
    padding: 11px 10px 4px 10px;
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
    padding: 6px 10px;
    min-height: 20px;
}}
/* Warna sorotan untuk kolom teks. Biru tua dengan tulisan putih dipakai
   pada teks yang disorot dengan tetikus.
   QComboBox sengaja TIDAK ikut di sini: warna sorotan yang dipasang pada
   QComboBox merambat ke daftar pilihannya, sehingga baris terpilih tertutup
   biru tua penuh dan tulisannya tidak terbaca. Daftar pilihan memakai warna
   sorotan yang lebih muda, diatur pada aturan QComboBoxListView. */
QLineEdit, QTextEdit, QPlainTextEdit {{
    selection-background-color: {C.PRIMARY};
    selection-color: {C.TEXT_INVERSE};
}}
QComboBox {{
    selection-background-color: {C.PRIMARY_SOFT};
    selection-color: {C.TEXT};
}}
QLineEdit:hover, QTextEdit:hover, QComboBox:hover, QDateEdit:hover,
QSpinBox:hover, QDoubleSpinBox:hover {{
    border-color: {C.PRIMARY_LIGHT};
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus,
QDateEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border: 2px solid {C.PRIMARY};
    padding: 5px 9px;
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
    padding: 8px 12px;
}}
QLineEdit#LoginInput {{
    padding: 10px 12px;
    font-size: {_px(FS_H3)}px;
    border-radius: {SUDUT_KONTROL}px;
}}
QComboBox::drop-down {{
    border: none;
    width: 22px;
}}
QComboBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {C.TEXT_MUTED};
    margin-right: 8px;
}}
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
    padding: 4px;
    outline: none;
    selection-background-color: {C.PRIMARY_SOFT};
    selection-color: {C.TEXT};
}}
/* Tinggi tiap baris daftar pilihan.
   Tanpa aturan ini Qt memakai tinggi bawaan yang hanya menyisakan satu dua
   piksel di atas dan di bawah huruf. Pada huruf berdescender (g, j, p, y)
   bagian bawahnya terpotong sehingga pilihan sulit dibaca dan sulit
   diklik. Tinggi di bawah memberi ruang 7 piksel di atas dan di bawah teks
   16 piksel, sehingga seluruh huruf tampil utuh dan barisnya nyaman
   ditunjuk dengan tetikus. */
QComboBoxListView::item {{
    min-height: 30px;
    padding: 4px 10px;
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
    spacing: 8px;
}}
QCheckBox::indicator, QRadioButton::indicator {{
    width: 17px;
    height: 17px;
    border: 1.5px solid {C.BORDER_STRONG};
    background: {C.SURFACE};
}}
QCheckBox::indicator {{ border-radius: 4px; }}
QRadioButton::indicator {{ border-radius: 9px; }}
QCheckBox::indicator:checked {{
    background: {C.PRIMARY};
    border-color: {C.PRIMARY};
    image: none;
}}
QRadioButton::indicator:checked {{
    background: {C.PRIMARY};
    border: 5px solid {C.PRIMARY};
}}

/* ---------------------------------------------------------- tabel */
QTableWidget, QTableView, QTreeWidget, QTreeView {{
    background: {C.SURFACE};
    border: 1px solid {C.BORDER};
    border-radius: {SUDUT_KONTROL}px;
    gridline-color: #EDF1F5;
    selection-background-color: {C.PRIMARY_SOFT};
    selection-color: {C.TEXT};
    outline: none;
    alternate-background-color: {C.SURFACE_ALT};
}}
QTableWidget::item, QTableView::item, QTreeWidget::item {{
    padding: 7px 9px;
    border: none;
}}
QTableWidget::item:hover, QTableView::item:hover, QTreeWidget::item:hover {{
    background: {C.PRIMARY_TINT};
}}
QTableWidget::item:selected, QTableView::item:selected, QTreeWidget::item:selected {{
    background: {C.PRIMARY_SOFT};
    color: {C.TEXT};
}}
QHeaderView::section {{
    background: {C.SURFACE_ALT};
    color: {C.TEXT_MUTED};
    padding: 9px 9px;
    border: none;
    border-bottom: 1px solid {C.BORDER_STRONG};
    border-right: 1px solid {C.BORDER};
    font-size: {_px(FS_SMALL)}px;
    font-weight: 700;
    letter-spacing: 0.2px;
}}
QHeaderView::section:last {{
    border-right: none;
}}
QTableCornerButton::section {{
    background: {C.SURFACE_ALT};
    border: none;
}}

/* ---------------------------------------------------------- tabs */
QTabWidget::pane {{
    border: 1px solid {C.BORDER};
    border-radius: {SUDUT_KONTROL}px;
    background: {C.SURFACE};
    top: -1px;
}}
QTabBar::tab {{
    background: transparent;
    color: {C.TEXT_MUTED};
    padding: 9px 16px;
    margin-right: 2px;
    border: 1px solid transparent;
    border-bottom: 2px solid transparent;
    font-weight: 600;
}}
QTabBar::tab:hover {{
    color: {C.PRIMARY};
    background: {C.PRIMARY_SOFT};
    border-top-left-radius: 7px;
    border-top-right-radius: 7px;
}}
QTabBar::tab:selected {{
    background: {C.SURFACE};
    color: {C.PRIMARY};
    border: 1px solid {C.BORDER};
    border-bottom: 2px solid {C.PRIMARY};
    border-top-left-radius: 7px;
    border-top-right-radius: 7px;
}}

/* ---------------------------------------------------------- scroll */
QScrollBar:vertical {{
    background: transparent;
    width: 11px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: #C4CDD8;
    border-radius: 5px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: #A8B4C2;
}}
/* sidebar gelap: scrollbar dibuat terang agar terlihat */
QScrollArea#SidebarScroll QScrollBar::handle:vertical {{
    background: #46617F;
}}
QScrollArea#SidebarScroll QScrollBar::handle:vertical:hover {{
    background: #5D7C9E;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 11px;
}}
QScrollBar::handle:horizontal {{
    background: #C4CDD8;
    border-radius: 5px;
    min-width: 30px;
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
    border-radius: 9px;
    margin-top: 16px;
    padding: 16px 12px 12px 12px;
    font-weight: 600;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: {C.PRIMARY};
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
    background: {C.PRIMARY};
}}
QMenuBar {{
    background: {C.SURFACE};
    border: none;
    border-bottom: 1px solid {C.BORDER};
    padding: 2px 10px;
    spacing: 6px;
    font-size: {_px(FS_BODY)};
}}
QMenuBar::item {{
    background: transparent;
    color: {C.TEXT};
    padding: 7px 14px;
    margin: 0px 1px;
    border-radius: 6px;
    font-weight: 500;
}}
QMenuBar::item:selected {{
    background: {C.PRIMARY_SOFT};
    color: {C.PRIMARY_DARK};
}}
QMenuBar::item:pressed {{
    background: {C.PRIMARY};
    color: {C.TEXT_INVERSE};
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
    selection-background-color: {C.PRIMARY};
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
    background: {C.PRIMARY};
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
    border-radius: 8px;
    padding: 5px;
}}
QMenu::item {{
    padding: 7px 22px 7px 14px;
    border-radius: 5px;
    color: {C.TEXT};
}}
QMenu::item:selected {{
    background: {C.PRIMARY_SOFT};
    color: {C.PRIMARY_DARK};
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
    """
    from PySide6.QtCore import QEvent, QObject
    from PySide6.QtWidgets import QDialog

    class PenyesuaiDialog(QObject):
        def eventFilter(self, objek, peristiwa):
            if peristiwa.type() == QEvent.Show and isinstance(objek, QDialog):
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
    from PySide6.QtWidgets import QStyledItemDelegate

    delegate = getattr(baris, "_delegate_tinggi", None)
    if delegate is not None:
        delegate.tinggi = tinggi
        baris.reset()
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

    delegate = DelegateBaris(baris, tinggi)
    baris.setItemDelegate(delegate)
    baris._delegate_tinggi = delegate
    baris.reset()


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
        if lbl.objectName() in ("PageTitle", "PageSubtitle"):
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
        tinggi = max(30, metrik.height() + 14)
        baris = cmb.view()
        baris.setMinimumHeight(min(260, cmb.count() * tinggi + 10))
        _pasang_tinggi_baris(baris, tinggi)
