"""
Audit elipsis sel tabel: pastikan tidak ada teks sel yang terpotong.

Qt mengganti teks sel yang tidak muat dengan elipsis ("Nota Kesepahaman ...").
Teks yang terpotong membuat data penting tidak terbaca, misalnya nomor
kontrak, nama mitra, atau nilai rupiah.

Lebar teks saja tidak cukup untuk menilai: Qt mengurangi lebar sel dengan
padding gaya dan margin fokus sebelum menggambar. Karena itu pemeriksaan di
sini meniru cara Qt menggambar — memakai elidedText pada kotak teks yang sama.

Cara pakai:
    python tools/audit_elipsis_sel.py
"""
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
os.environ.setdefault("AKUNTANSIID_DATA",
                      str(Path(__file__).resolve().parents[1] / "_contoh"))
os.environ.pop("QT_QPA_PLATFORM", None)

from PySide6.QtCore import Qt
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import QApplication, QStyle, QStyleOptionViewItem

from akuntansi_id.core import security as sec
from akuntansi_id.ui import theme
from akuntansi_id.ui.main_window import MainWindow, Sidebar
from akuntansi_id.ui.widgets import Tabel

# Lisensi uji dipakai agar seluruh halaman ikut diperiksa, termasuk
# halaman yang hanya tersedia pada paket Enterprise.
from akuntansi_id.core.license import Lisensi as _LisensiUji
_LISENSI_UJI = _LisensiUji(kunci='ATNTUJI', paket='enterprise', fitur={})



def periksa_halaman(jw: MainWindow) -> tuple:
    """Hitung sel tabel yang akan digambar Qt dengan elipsis."""
    total = 0
    terpotong = []
    for nama in [item[0] for _seksi, daftar in Sidebar.MENU for item in daftar]:
        try:
            jw._navigasi(nama)
        except Exception:
            continue
        for _ in range(18):
            jw.app.processEvents()
            time.sleep(0.008)
        halaman = jw.stack.currentWidget()
        if halaman is None:
            continue
        for tabel in halaman.findChildren(Tabel):
            if tabel.rowCount() == 0:
                continue
            for r in range(tabel.rowCount()):
                for c in range(tabel.columnCount()):
                    item = tabel.item(r, c)
                    if item is None or not item.text().strip():
                        continue
                    opt = QStyleOptionViewItem()
                    tabel.initViewItemOption(opt)
                    opt.rect = tabel.visualRect(tabel.model().index(r, c))
                    opt.text = item.text()
                    kotak = tabel.style().subElementRect(
                        QStyle.SE_ItemViewItemText, opt, tabel)
                    metrik = QFontMetrics(opt.font)
                    total += 1
                    if metrik.elidedText(item.text(), Qt.ElideRight,
                                         kotak.width()) != item.text():
                        terpotong.append(
                            (nama, item.text(), kotak.width(),
                             metrik.horizontalAdvance(item.text())))
    return total, terpotong


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyleSheet(theme.stylesheet())

    hasil = sec.LoginResult(ok=True, user_id=1, username="admin",
                            full_name="Admin", role="owner",
                            app_mode="expert", mode_dipilih=True)
    jw = MainWindow(hasil, lisensi=_LISENSI_UJI)
    jw.app = app
    jw.resize(1440, 900)
    jw.show()
    batas = time.time() + 2.0
    while time.time() < batas:
        app.processEvents()
        time.sleep(0.01)

    jumlah_sel = 0
    semua = []
    for lebar in (1440, 1280, 1100):
        jw.resize(lebar, 820)
        for _ in range(30):
            app.processEvents()
            time.sleep(0.015)
        total, terpotong = periksa_halaman(jw)
        jumlah_sel += total
        semua += [(lebar,) + t for t in terpotong]
        print(f"lebar {lebar}: {total} sel, {len(terpotong)} terpotong")

    print()
    for lebar, halaman, teks, lebar_kotak, perlu in semua[:20]:
        print(f"  [{lebar}px/{halaman}] {teks!r} kotak={lebar_kotak} perlu={perlu}")

    print()
    if semua:
        print(f"HASIL: {len(semua)} sel terpotong dari {jumlah_sel} sel")
        return 1
    print(f"HASIL: tidak ada sel terpotong ({jumlah_sel} sel diperiksa)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
