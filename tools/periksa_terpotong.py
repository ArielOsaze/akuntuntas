"""
Periksa teks terpotong saat tinggi-dari-lebar dimatikan.

Tinggi-dari-lebar membuat susunan halaman menanyakan tinggi setiap label
berbalut setiap kali ukuran berubah. Pekerjaan itu terbukti memakan sebagian
besar waktu perpindahan halaman. Berkas ini memeriksa apakah teksnya masih
terbaca utuh bila tinggi label dipatok lebih dulu, sehingga tinggi-dari-lebar
tidak lagi diperlukan.

Pemeriksaan dilakukan SELAGI tinggi-dari-lebar mati, karena bila dinyalakan
kembali, Qt menghitung tingginya sendiri dan pemotongan tidak terlihat.
"""

import os
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "src"))
os.environ.setdefault("AKUNTANSIID_DATA", str(AKAR / "_contoh"))

from PySide6.QtWidgets import QApplication, QLabel      # noqa: E402


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

    for kode in jendela.halaman:
        jendela._navigasi(kode)
        for _ in range(3):
            app.processEvents()

    print("=" * 78)
    print("PEMERIKSAAN PEMOTONGAN TEKS TANPA TINGGI-DARI-LEBAR")
    print("=" * 78)
    print()

    # ---------------------------------------------------------- keadaan awal
    label = []
    for kode, halaman in jendela.halaman.items():
        for lbl in halaman.findChildren(QLabel):
            label.append((kode, lbl))

    berbalut = [(k, l) for k, l in label if l.wordWrap() and l.text()]
    print(f"  label berbalut berisi teks : {len(berbalut)}")

    # patok tinggi seluruh label berbalut, seperti yang dilakukan
    # theme.rapikan_label dan AreaGulir
    for _, lbl in berbalut:
        tinggi = theme.tinggi_rich_text(lbl)
        if tinggi > 0 and lbl.minimumHeight() < tinggi:
            lbl.setMinimumHeight(tinggi)
    for _ in range(10):
        app.processEvents()

    # ---------------------------------------------------------- matikan HFW
    for _, lbl in berbalut:
        kebijakan = lbl.sizePolicy()
        if kebijakan.hasHeightForWidth():
            kebijakan.setHeightForWidth(False)
            lbl.setSizePolicy(kebijakan)
    for _ in range(15):
        app.processEvents()

    # ---------------------------------------------------------- periksa
    terpotong = []
    for kode, lbl in berbalut:
        if lbl.width() <= 0:
            continue
        tinggi = theme.tinggi_rich_text(lbl)
        if tinggi > lbl.height() + 2:
            terpotong.append((kode, lbl.objectName() or "(tanpa nama)",
                              lbl.text()[:52].replace("\n", " "),
                              tinggi, lbl.height()))

    print(f"  teks terpotong             : {len(terpotong)}")
    print()

    if terpotong:
        print("  Rincian yang terpotong:")
        print()
        for kode, nama, teks, perlu, ada in terpotong[:25]:
            print(f"    [{kode}] {nama}")
            print(f"      perlu {perlu}px, ada {ada}px")
            print(f"      \"{teks}...\"")
        print()
        print(f"  Total: {len(terpotong)} label")
    else:
        print("  Seluruh teks tetap terbaca utuh tanpa tinggi-dari-lebar.")

    print()

    # ---------------------------------------------------------- periksa jendela sempit
    print("  Mengulang pemeriksaan pada jendela sempit (1100x760)...")
    jendela.resize(1100, 760)
    for _ in range(20):
        app.processEvents()

    for _, lbl in berbalut:
        tinggi = theme.tinggi_rich_text(lbl)
        if tinggi > 0 and lbl.minimumHeight() < tinggi:
            lbl.setMinimumHeight(tinggi)
    for _ in range(15):
        app.processEvents()

    sempit = []
    for kode, lbl in berbalut:
        if lbl.width() <= 0:
            continue
        tinggi = theme.tinggi_rich_text(lbl)
        if tinggi > lbl.height() + 2:
            sempit.append((kode, lbl.objectName() or "(tanpa nama)",
                           lbl.text()[:52].replace("\n", " "),
                           tinggi, lbl.height()))

    print(f"  teks terpotong             : {len(sempit)}")
    if sempit:
        for kode, nama, teks, perlu, ada in sempit[:20]:
            print(f"    [{kode}] {nama}: perlu {perlu}px, ada {ada}px")
            print(f"      \"{teks}...\"")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
