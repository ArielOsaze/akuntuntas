"""
Lacak mengapa tinggi-dari-lebar menyala kembali setelah halaman ditampilkan.

Perapian menghapus tinggi-dari-lebar dari seluruh label berbalut, tetapi
setelah peristiwa Qt diproses sebagian label memakainya lagi padahal tidak
ada kode Python yang menyalakannya. Berkas ini membandingkan keadaan label
sebelum dan sesudah peristiwa untuk mengetahui label mana yang berubah dan
apakah label itu memang baru dibuat.
"""

import os
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "src"))
os.environ.setdefault("AKUNTANSIID_DATA", str(AKAR / "_contoh"))

from PySide6.QtWidgets import QApplication, QLabel      # noqa: E402


def potret(halaman) -> dict:
    hasil = {}
    for lbl in halaman.findChildren(QLabel):
        hasil[id(lbl)] = (
            lbl.wordWrap(),
            lbl.sizePolicy().hasHeightForWidth(),
            lbl.minimumHeight(),
            lbl.objectName(),
            lbl.text()[:34],
        )
    return hasil


def jumlah_hfw(halaman) -> int:
    return sum(1 for lbl in halaman.findChildren(QLabel)
               if lbl.wordWrap() and lbl.sizePolicy().hasHeightForWidth())


def main() -> int:
    app = QApplication([])
    app.setStyle("Fusion")

    from akuntansi_id.ui import theme
    theme.palet_terang(app)
    app.setStyleSheet(theme.stylesheet())

    from akuntansi_id.core import security as sec
    from akuntansi_id.ui.main_window import MainWindow

    jendela = MainWindow(sec.login("admin", "admin123"))
    jendela.resize(1400, 900)
    jendela.show()
    for _ in range(20):
        app.processEvents()

    halaman = jendela.halaman["analisis"]

    jendela._navigasi("analisis")
    sebelum = potret(halaman)
    print(f"  setelah _navigasi : {len(sebelum)} label, "
          f"{jumlah_hfw(halaman)} tinggi-dari-lebar")

    app.processEvents()
    sesudah = potret(halaman)
    print(f"  setelah peristiwa : {len(sesudah)} label, "
          f"{jumlah_hfw(halaman)} tinggi-dari-lebar")
    print()

    baru = set(sesudah) - set(sebelum)
    hilang = set(sebelum) - set(sesudah)
    sama = set(sebelum) & set(sesudah)
    berubah = [k for k in sama if sebelum[k][:2] != sesudah[k][:2]]

    print(f"  label baru dibuat  : {len(baru)}")
    print(f"  label dibuang      : {len(hilang)}")
    print(f"  label berubah sifat: {len(berubah)}")
    print()

    if berubah:
        print("  Label yang sifatnya berubah:")
        for kunci in berubah[:8]:
            lama, kini = sebelum[kunci], sesudah[kunci]
            print(f"    {lama[3] or '(tanpa nama)'}: {lama[4]!r}")
            print(f"      sebelum: bungkus={lama[0]} hfw={lama[1]} "
                  f"tinggi_min={lama[2]}")
            print(f"      sesudah: bungkus={kini[0]} hfw={kini[1]} "
                  f"tinggi_min={kini[2]}")

    if baru:
        print()
        print("  Label baru yang muncul setelah peristiwa:")
        for kunci in list(baru)[:8]:
            kini = sesudah[kunci]
            print(f"    {kini[3] or '(tanpa nama)'}: {kini[4]!r} "
                  f"(bungkus={kini[0]} hfw={kini[1]})")

    return 0


if __name__ == "__main__":
    sys.exit(main())
