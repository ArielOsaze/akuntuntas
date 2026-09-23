"""Penyetelan kalender popup agar berbahasa Indonesia dan mudah dibaca.

Cara pakai:
    from akuntansi_id.ui import kalender
    kalender.pasang(self.inp_tanggal)

Qt memakai locale sistem (umumnya en_US) sehingga nama bulan tampil dalam
bahasa Inggris dan awal minggu jatuh pada hari Minggu. Penyetelan ini
mengubahnya ke kebiasaan Indonesia: nama bulan Indonesia, minggu dimulai
hari Senin, grid tanggal terlihat, dan tombol navigasi berikon garis.
"""

from __future__ import annotations

from PySide6.QtCore import QDate, QLocale, Qt
from PySide6.QtGui import QFont, QTextCharFormat
from PySide6.QtWidgets import QCalendarWidget, QDateEdit

from . import icons

BULAN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni",
         "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
HARI_SINGKAT = ["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"]


def locale_indonesia() -> QLocale:
    """Locale Indonesia dengan format tanggal dd/MM/yyyy."""
    loc = QLocale(QLocale.Indonesian, QLocale.Indonesia)
    loc.setNumberOptions(QLocale.OmitGroupSeparator)
    return loc


def siapkan(cal: QCalendarWidget) -> None:
    """Terapkan tampilan kalender yang nyaman dipakai pengguna Indonesia."""
    cal.setLocale(locale_indonesia())
    cal.setFirstDayOfWeek(Qt.Monday)
    cal.setGridVisible(True)
    cal.setNavigationBarVisible(True)
    cal.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
    cal.setHorizontalHeaderFormat(QCalendarWidget.ShortDayNames)

    # Header hari diberi font kecil agar singkatan tidak terpotong.
    format_header = QTextCharFormat()
    format_header.setFontPointSize(8.5)
    format_header.setFontWeight(QFont.Medium)
    cal.setHeaderTextFormat(format_header)

    # Tombol navigasi memakai ikon garis putih agar terlihat di header biru.
    for tombol, nama in (("qt_calendar_prevmonth", "panah_kiri"),
                         ("qt_calendar_nextmonth", "panah_kanan")):
        b = cal.findChild(type(cal), tombol)
        if b is None:
            continue
        b.setIcon(icons.ikon(nama, "#FFFFFF", 16))
        b.setText("")
        b.setFixedWidth(30)

    # Tombol nama bulan dan tahun pada bilah navigasi perlu lebar cukup.
    # Qt memberi lebar bawaan hanya 25 px sehingga nama bulan seperti
    # "September" terpotong dan pengguna tidak tahu bulan yang sedang tampil.
    from PySide6.QtWidgets import QToolButton

    for nama, lebar_min in (("qt_calendar_monthbutton", 120),
                            ("qt_calendar_yearbutton", 80)):
        b = cal.findChild(QToolButton, nama)
        if b is None:
            continue
        b.setMinimumWidth(lebar_min)
        b.setStyleSheet(
            "QToolButton { padding: 4px 10px; font-weight: 600; "
            "background: transparent; border: none; }"
            "QToolButton:hover { background: rgba(255, 255, 255, 0.18); "
            "border-radius: 6px; }")


def pasang(inp: QDateEdit) -> QDateEdit:
    """Siapkan QDateEdit: format dd/MM/yyyy, kalender popup Indonesia."""
    inp.setCalendarPopup(True)
    inp.setLocale(locale_indonesia())
    inp.setDisplayFormat("dd/MM/yyyy")
    if inp.date().isNull():
        inp.setDate(QDate.currentDate())
    cal = inp.calendarWidget()
    if cal is not None:
        siapkan(cal)
        # Popup diberi lebar cukup agar singkatan hari tidak terpotong.
        cal.setMinimumWidth(360)
        cal.setMinimumHeight(300)
    return inp


def tanggal_indonesia(tanggal: QDate) -> str:
    """Tanggal dalam bentuk '1 Maret 2026'."""
    return f"{tanggal.day()} {BULAN[tanggal.month() - 1]} {tanggal.year()}"
