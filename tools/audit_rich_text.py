"""
Cari label teks berformat (rich text) yang isinya benar-benar terpotong.

Berbeda dari audit_tinggi_label.py yang memeriksa seluruh halaman, alat ini
fokus pada satu kelas bug: QLabel berformat dengan wordWrap yang tingginya
ditekan oleh tata letak sehingga baris terakhirnya tidak terlihat. Deteksi
dilakukan dengan membandingkan tinggi yang dipakai terhadap tinggi dokumen
teks pada lebar nyata, lalu memastikan selisihnya bermakna.

Cara pakai:
    python tools/audit_rich_text.py
"""
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
os.environ.setdefault("AKUNTANSIID_DATA",
                      str(Path(__file__).resolve().parents[1] / "_contoh"))

from PySide6.QtGui import QTextDocument
from PySide6.QtWidgets import QApplication, QLabel

from akuntansi_id.core import security as sec
from akuntansi_id.ui import theme
from akuntansi_id.ui.login import GantiPasswordWajib, LoginPage, PilihMode
from akuntansi_id.ui.main_window import MainWindow, Sidebar

# Lisensi uji dipakai agar seluruh halaman ikut diperiksa, termasuk
# halaman yang hanya tersedia pada paket Enterprise.
from akuntansi_id.core.license import Lisensi as _LisensiUji
_LISENSI_UJI = _LisensiUji(kunci='ATNTUJI', paket='enterprise', fitur={})



def tinggi_dokumen(lbl: QLabel) -> int:
    doc = QTextDocument()
    doc.setDefaultFont(lbl.font())
    doc.setHtml(lbl.text())
    doc.setTextWidth(max(1, lbl.width()))
    return int(doc.size().height())


def periksa(konteks: str, akar) -> list:
    temuan = []
    for lbl in akar.findChildren(QLabel):
        if not lbl.isVisible() or not lbl.text().strip():
            continue
        if lbl.textFormat() != lbl.textFormat().RichText and "<" not in lbl.text():
            continue
        perlu = tinggi_dokumen(lbl)
        # beri toleransi 3 px untuk pembulatan baris
        if perlu > lbl.height() + 3:
            temuan.append((konteks, lbl.text()[:70], lbl.height(), perlu))
    return temuan


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyleSheet(theme.stylesheet())

    hasil = sec.LoginResult(ok=True, user_id=1, username="admin",
                            full_name="Admin", role="owner",
                            app_mode="expert", mode_dipilih=True)
    jw = MainWindow(hasil, lisensi=_LISENSI_UJI)
    jw.resize(1440, 900)
    jw.show()
    batas = time.time() + 1.5
    while time.time() < batas:
        app.processEvents()
        time.sleep(0.01)

    semua = []
    diperiksa = 0
    kode_menu = [item[0] for _seksi, daftar in Sidebar.MENU for item in daftar]
    for nama in kode_menu:
        try:
            jw._navigasi(nama)
        except Exception:
            continue
        for _ in range(6):
            app.processEvents()
        halaman = jw.stack.currentWidget()
        if halaman is None:
            continue
        for lbl in halaman.findChildren(QLabel):
            if lbl.isVisible() and lbl.text().strip() and "<" in lbl.text():
                diperiksa += 1
        semua += periksa(nama, halaman)

    for nama, buat in (("login", lambda: LoginPage()),
                       ("ganti-password", lambda: GantiPasswordWajib(1)),
                       ("pilih-mode", lambda: PilihMode(hasil))):
        try:
            w = buat()
        except Exception as e:
            print(f"  ({nama} dilewati: {e})")
            continue
        w.resize(1100, 720)
        w.show()
        batas = time.time() + 1.2
        while time.time() < batas:
            app.processEvents()
            time.sleep(0.01)
        for lbl in w.findChildren(QLabel):
            if lbl.isVisible() and lbl.text().strip() and "<" in lbl.text():
                diperiksa += 1
        semua += periksa(nama, w)

    print(f"label berformat diperiksa : {diperiksa}")
    print(f"temuan terpotong          : {len(semua)}")
    for konteks, teks, tinggi, perlu in semua[:20]:
        print(f"  [{konteks}] {teks!r}")
        print(f"      tinggi={tinggi} perlu={perlu}")
    print()
    if semua:
        print(f"HASIL: {len(semua)} teks berformat terpotong")
    else:
        print("HASIL: seluruh teks berformat tampil utuh")

    return 1 if semua else 0


if __name__ == "__main__":
    sys.exit(main())
