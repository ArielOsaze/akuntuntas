"""
Audit tinggi label: cari teks yang tingginya kurang dari kebutuhan.

sizeHint() QLabel berword-wrap mengembalikan tinggi untuk lebar ideal yang
lebih sempit daripada lebar nyata, sehingga sering melaporkan kebutuhan
tinggi berlebih. Alat ini mengukur ulang memakai lebar nyata tiap label:
QTextDocument untuk teks berformat dan QFontMetrics untuk teks biasa.

Cara pakai:
    python tools/audit_tinggi_label.py
"""
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
os.environ.setdefault("AKUNTANSIID_DATA",
                      str(Path(__file__).resolve().parents[1] / "_contoh"))

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QTextDocument
from PySide6.QtWidgets import QApplication, QLabel

from akuntansi_id.core import security as sec
from akuntansi_id.ui import theme
from akuntansi_id.ui.main_window import MainWindow, Sidebar

# Lisensi uji dipakai agar seluruh halaman ikut diperiksa, termasuk
# halaman yang hanya tersedia pada paket Enterprise.
from akuntansi_id.core.license import Lisensi as _LisensiUji
_LISENSI_UJI = _LisensiUji(kunci='ATNTUJI', paket='enterprise', fitur={})



def tinggi_dibutuhkan(lbl: QLabel) -> int:
    """Tinggi minimum agar seluruh teks label terlihat pada lebar nyatanya."""
    lebar = lbl.width()
    if lebar <= 0:
        return 0
    if lbl.textFormat() == Qt.RichText or "<" in lbl.text():
        doc = QTextDocument()
        doc.setDefaultFont(lbl.font())
        doc.setHtml(lbl.text())
        doc.setTextWidth(lebar)
        return int(doc.size().height()) + 2
    fm = lbl.fontMetrics()
    kotak = fm.boundingRect(QRect(0, 0, lebar, 100000),
                            Qt.TextWordWrap | Qt.AlignLeft, lbl.text())
    return kotak.height() + 2


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

    temuan = []
    jumlah = 0
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
            if not lbl.isVisible() or not lbl.text().strip():
                continue
            jumlah += 1
            perlu = tinggi_dibutuhkan(lbl)
            if perlu > lbl.height() + 2:
                temuan.append((nama, lbl.text()[:60], lbl.height(), perlu))

    print(f"label diperiksa : {jumlah}")
    print(f"temuan          : {len(temuan)}")
    for nama, teks, tinggi, perlu in temuan[:25]:
        print(f"  [{nama}] {teks!r}")
        print(f"      tinggi={tinggi} perlu={perlu}")

    # dialog penting
    print()
    print("=== DIALOG ===")
    from akuntansi_id.ui.login import LoginPage
    lp = LoginPage()
    lp.resize(1100, 720)
    lp.show()
    batas = time.time() + 1.2
    while time.time() < batas:
        app.processEvents()
        time.sleep(0.01)
    for lbl in lp.findChildren(QLabel):
        if not lbl.isVisible() or not lbl.text().strip():
            continue
        perlu = tinggi_dibutuhkan(lbl)
        if perlu > lbl.height() + 2:
            print(f"  [login] {lbl.text()[:60]!r} tinggi={lbl.height()} perlu={perlu}")
    print("  (bersih bila tidak ada baris di atas)")
    print()
    if temuan:
        print(f"HASIL: {len(temuan)} label terlalu pendek")
    else:
        print("HASIL: tinggi seluruh label cukup")

    return 1 if temuan else 0


if __name__ == "__main__":
    sys.exit(main())
