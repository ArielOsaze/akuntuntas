"""
Uji tata letak tabel pada lebar jendela minimum.

Pada layar 1180 px, kolom angka, tanggal, dan status harus tetap terlihat
utuh. Kolom teks fleksibel boleh menyusut agar seluruh kolom muat, asalkan
teks utuhnya tetap tersedia lewat tooltip. Tabel yang isinya memang tidak
muat harus dapat digeser mendatar, bukan memotong teks tanpa jalan keluar.

Cara pakai:
    python tests/test_tata_letak_tabel.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("AKUNTANSIID_DATA",
                      str(Path(__file__).parent.parent / "_uitest_tabel"))
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QFontMetrics
from PySide6.QtWidgets import QApplication, QStyle, QStyleOptionViewItem

from akuntansi_id.ui import theme
from akuntansi_id.ui.widgets import MIN_LEBAR_FLEKSIBEL, Tabel

LULUS = 0
GAGAL = 0

KETERANGAN_PANJANG = (
    "Penyusutan Kendaraan Operasional Toyota Avanza tahun 2026")
KOLOM = [
    ("Tanggal", 100), ("No. Bukti", 140), ("Keterangan", -1),
    ("Debit (Rp)", 145), ("Kredit (Rp)", 145), ("Sumber", 105),
]


def cek(nama: str, syarat: bool, keterangan: str = ""):
    global LULUS, GAGAL
    if syarat:
        LULUS += 1
        print(f"  [LULUS] {nama}")
    else:
        GAGAL += 1
        print(f"  [GAGAL] {nama}" + (f" — {keterangan}" if keterangan else ""))


def proses(app, kali=8):
    for _ in range(kali):
        app.processEvents()


def tabel_jurnal() -> Tabel:
    t = Tabel(KOLOM)
    t.isi([
        ["31 Des 2026", "SUSUT-AST-001-2026", KETERANGAN_PANJANG,
         "Rp35.000.000", "Rp35.000.000", "Aset Tetap"],
        ["17 Des 2026", "INV-INV/2026/0026",
         "Penjualan INV/2026/0026 - CV Digital Kreasi",
         "Rp72.187.500", "Rp72.187.500", "Penjualan"],
    ], align_kanan={3, 4})
    return t


def kebutuhan(t: Tabel) -> tuple[int, int]:
    """(kebutuhan seluruh kolom, kebutuhan kolom tetap) pada skala layar uji."""
    perlu = [t._lebar_perlu(c, j) for c, (j, _l) in enumerate(KOLOM)]
    tetap = sum(p for p, (_j, l) in zip(perlu, KOLOM) if l > 0)
    return sum(perlu), tetap


def pasang(app, t: Tabel, lebar_area: int):
    """Tampilkan tabel dengan area tampil mendekati lebar yang diminta."""
    t.resize(lebar_area + 2, 320)
    t.show()
    proses(app, 20)


def elipsis(tabel: Tabel, baris: int, kolom: int) -> bool:
    item = tabel.item(baris, kolom)
    opt = QStyleOptionViewItem()
    tabel.initViewItemOption(opt)
    opt.rect = tabel.visualRect(tabel.model().index(baris, kolom))
    opt.text = item.text()
    kotak = tabel.style().subElementRect(
        QStyle.SE_ItemViewItemText, opt, tabel)
    return QFontMetrics(item.font()).elidedText(
        item.text(), Qt.ElideRight, kotak.width()) != item.text()


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyleSheet(theme.stylesheet())

    print("=" * 66)
    print("TATA LETAK TABEL — LEBAR MINIMUM JENDELA")
    print("=" * 66)

    print("\n[Muat seluruh kolom]")
    t = tabel_jurnal()
    total_perlu, perlu_tetap = kebutuhan(t)
    lebar_uji = perlu_tetap + MIN_LEBAR_FLEKSIBEL + 40
    cek("Skenario uji lebih sempit daripada kebutuhan isi",
        lebar_uji < total_perlu,
        f"uji={lebar_uji} perlu={total_perlu}")
    pasang(app, t, lebar_uji)

    total = sum(t.columnWidth(c) for c in range(t.columnCount()))
    cek("Seluruh kolom muat tanpa geser mendatar",
        total <= t.viewport().width() + 1,
        f"kolom={total} area={t.viewport().width()}")
    cek("Tidak ada bilah geser mendatar yang menganggur",
        t.horizontalScrollBar().maximum() == 0,
        f"maksimum={t.horizontalScrollBar().maximum()}")

    print("\n[Kolom teks fleksibel]")
    lebar_ket = t.columnWidth(2)
    cek("Kolom Keterangan menyusut agar kolom lain terlihat",
        MIN_LEBAR_FLEKSIBEL <= lebar_ket < t._lebar_perlu(2, "Keterangan"),
        f"lebar={lebar_ket} minimum={MIN_LEBAR_FLEKSIBEL}")
    cek("Keterangan panjang memakai elipsis dengan tooltip",
        elipsis(t, 0, 2)
        and t.item(0, 2).toolTip() == KETERANGAN_PANJANG,
        f"tooltip={t.item(0, 2).toolTip()!r}")

    print("\n[Data penting tetap utuh]")
    for kolom, judul in ((1, "No. Bukti"), (3, "Debit (Rp)"),
                         (4, "Kredit (Rp)"), (5, "Sumber")):
        cek(f"Kolom {judul} tidak terpotong",
            not elipsis(t, 0, kolom) and not elipsis(t, 1, kolom),
            t.item(0, kolom).text())
    cek("Kolom Sumber tetap terlihat di tepi kanan",
        t.columnViewportPosition(5) + t.columnWidth(5)
        <= t.viewport().width() + 1,
        f"tepi={t.columnViewportPosition(5) + t.columnWidth(5)} "
        f"area={t.viewport().width()}")

    print("\n[Tabel yang memang terlalu lebar]")
    t2 = tabel_jurnal()
    pasang(app, t2, perlu_tetap - 40)
    cek("Tabel memakai lebar isi penuh saat tidak mungkin muat",
        sum(t2.columnWidth(c) for c in range(t2.columnCount()))
        > t2.viewport().width(),
        f"kolom={sum(t2.columnWidth(c) for c in range(t2.columnCount()))} "
        f"area={t2.viewport().width()}")
    cek("Tabel dapat digeser mendatar",
        t2.horizontalScrollBar().maximum() > 0,
        f"maksimum={t2.horizontalScrollBar().maximum()}")
    cek("Keterangan tidak dipaksa lebih sempit dari batas",
        t2.columnWidth(2) == t2._lebar_perlu(2, "Keterangan"),
        f"lebar={t2.columnWidth(2)} perlu={t2._lebar_perlu(2, 'Keterangan')}")

    print("\n[Label status]")
    t3 = Tabel([("Keterangan", -1), ("Status", 74)])
    t3.isi([["Biaya sewa kantor", "Disetujui"]])
    t3.resize(600, 200)
    t3.show()
    proses(app, 10)
    lebar_status = t3.columnWidth(1)
    cek("Kolom status tidak lebih sempit daripada judul dan isinya",
        lebar_status >= t3._lebar_perlu(1, "Status"),
        f"lebar={lebar_status}")
    font_lencana = QFont(t3.font())
    font_lencana.setWeight(QFont.DemiBold)
    lebar_teks = QFontMetrics(font_lencana).horizontalAdvance("Disetujui")
    lebar_lencana = min(lebar_teks + 16, max(28, lebar_status - 8))
    cek("Teks lencana 'Disetujui' muat di dalam lencana",
        lebar_lencana - 10 >= lebar_teks,
        f"lencana={lebar_lencana} teks={lebar_teks}")

    t.close()
    t2.close()
    t3.close()
    proses(app, 3)

    print()
    if GAGAL:
        print(f"HASIL AKHIR: {LULUS} LULUS, {GAGAL} GAGAL")
        return 1
    print(f"HASIL AKHIR: {LULUS} LULUS, 0 GAGAL")
    return 0


if __name__ == "__main__":
    sys.exit(main())
