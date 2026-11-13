"""
Uji pengurutan tabel: nominal, persen, kuantitas, dan tanggal.

Pengurutan bawaan QTableWidget membandingkan teks, sehingga "Rp9.000"
muncul setelah "Rp10.000" dan "3 Okt" sebelum "25 Sep". Tabel aplikasi
harus mengurutkan berdasarkan nilai yang sebenarnya.

Cara pakai:
    python tests/test_urut_tabel.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("AKUNTANSIID_DATA",
                      str(Path(__file__).parent.parent / "_uitest_urut"))
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication, QLineEdit, QTableWidgetItem

from akuntansi_id.ui import theme
from akuntansi_id.ui.widgets import Tabel, _ItemTabel, _kunci_urut

LULUS = 0
GAGAL = 0


def cek(nama: str, syarat: bool, keterangan: str = ""):
    global LULUS, GAGAL
    if syarat:
        LULUS += 1
        print(f"  [LULUS] {nama}")
    else:
        GAGAL += 1
        print(f"  [GAGAL] {nama}" + (f" — {keterangan}" if keterangan else ""))


def isi_teks(tabel: Tabel, nilai: list[str]):
    tabel.setRowCount(len(nilai))
    for i, teks in enumerate(nilai):
        tabel.setItem(i, 0, QTableWidgetItem(teks))


def urut(tabel: Tabel, arah=Qt.AscendingOrder) -> list[str]:
    tabel.sortItems(0, arah)
    return [tabel.item(i, 0).text() for i in range(tabel.rowCount())]


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyleSheet(theme.stylesheet())

    print("=" * 66)
    print("PENGURUTAN TABEL — NILAI, PERSEN, KUANTITAS, TANGGAL")
    print("=" * 66)

    print("\n[Kunci pengurutan]")
    cek("Rupiah dikenali sebagai angka",
        _kunci_urut("Rp10.000")[:2] == (2, 10000.0),
        str(_kunci_urut("Rp10.000")))
    cek("Rupiah negatif tetap negatif",
        _kunci_urut("-Rp2.000")[:2] == (2, -2000.0),
        str(_kunci_urut("-Rp2.000")))
    cek("Persen memakai nilai angka",
        _kunci_urut("12,5%")[:2] == (2, 12.5),
        str(_kunci_urut("12,5%")))
    cek("Kuantitas dengan satuan tetap angka",
        _kunci_urut("1.234 unit")[:2] == (2, 1234.0),
        str(_kunci_urut("1.234 unit")))
    cek("Tanggal Indonesia dikenali",
        _kunci_urut("25 Sep 2026")[0] == 1,
        str(_kunci_urut("25 Sep 2026")))
    cek("Tanggal ISO dikenali",
        _kunci_urut("2026-09-25")[0] == 1,
        str(_kunci_urut("2026-09-25")))
    cek("Nilai kosong dipisahkan dari teks",
        _kunci_urut("")[0] == 0 and _kunci_urut("Catatan")[0] == 3)

    print("\n[Rupiah]")
    t = Tabel([("Nilai", 160)])
    isi_teks(t, ["Rp9.000", "Rp10.000", "Rp1.000.000", "Rp1.234"])
    cek("Naik mengikuti nominal",
        urut(t) == ["Rp1.234", "Rp9.000", "Rp10.000", "Rp1.000.000"],
        str(urut(t)))
    cek("Turun mengikuti nominal",
        urut(t, Qt.DescendingOrder)
        == ["Rp1.000.000", "Rp10.000", "Rp9.000", "Rp1.234"],
        str(urut(t, Qt.DescendingOrder)))

    t2 = Tabel([("Nilai", 160)])
    t2.isi([["Rp9.000"], ["Rp10.000"], ["-Rp2.000"]], align_kanan={0})
    cek("Item dari isi() juga terurut",
        urut(t2) == ["-Rp2.000", "Rp9.000", "Rp10.000"], str(urut(t2)))

    print("\n[Tanggal]")
    t3 = Tabel([("Tanggal", 140)])
    isi_teks(t3, ["3 Okt 2025", "25 Sep 2026", "1 Jan 2026", "15 Agu 2026"])
    cek("Tanggal terurut kronologis",
        urut(t3) == ["3 Okt 2025", "1 Jan 2026", "15 Agu 2026", "25 Sep 2026"],
        str(urut(t3)))

    print("\n[Persen dan kuantitas]")
    t4 = Tabel([("Persen", 120)])
    isi_teks(t4, ["9%", "12,5%", "100%", "2,25%"])
    cek("Persen terurut menurut nilainya",
        urut(t4) == ["2,25%", "9%", "12,5%", "100%"], str(urut(t4)))

    t5 = Tabel([("Qty", 120)])
    isi_teks(t5, ["12 pcs", "3 pcs", "1.234 pcs", "100 pcs"])
    cek("Kuantitas terurut menurut nilainya",
        urut(t5) == ["3 pcs", "12 pcs", "100 pcs", "1.234 pcs"],
        str(urut(t5)))

    print("\n[Item buatan halaman]")
    t6 = Tabel([("Status", 120)])
    t6.setRowCount(2)
    item = QTableWidgetItem("Rp2.000")
    item.setForeground(QColor("#A23A32"))
    item.setToolTip("Baris penting")
    t6.setItem(0, 0, item)
    t6.setItem(1, 0, QTableWidgetItem("Rp10.000"))
    baru = t6.item(0, 0)
    cek("Item biasa dibungkus agar dapat diurutkan",
        isinstance(baru, _ItemTabel), type(baru).__name__)
    cek("Warna dan tooltip item dipertahankan",
        baru.foreground().color().name().lower() == "#a23a32"
        and baru.toolTip() == "Baris penting")
    cek("Item yang dibungkus tetap terurut",
        urut(t6) == ["Rp2.000", "Rp10.000"], str(urut(t6)))

    print("\n[Tabel berisi kotak isian]")
    t7 = Tabel([("Nilai", 120)])
    isi_teks(t7, ["Rp2.000", "Rp10.000"])
    cek("Tabel data dapat diurutkan", t7.isSortingEnabled())
    t7.setCellWidget(0, 0, QLineEdit("ubah"))
    cek("Tabel dengan kotak isian tidak diurutkan",
        not t7.isSortingEnabled(),
        "header dapat memindahkan teks tanpa widgetnya")
    cek("Widget tetap berada di baris semula",
        isinstance(t7.cellWidget(0, 0), QLineEdit))

    print()
    if GAGAL:
        print(f"HASIL AKHIR: {LULUS} LULUS, {GAGAL} GAGAL")
        return 1
    print(f"HASIL AKHIR: {LULUS} LULUS, 0 GAGAL")
    return 0


if __name__ == "__main__":
    sys.exit(main())
