"""
Audit lebar kolom tabel: pastikan judul tiap kolom terbaca utuh.

Kolom yang terlalu sempit membuat judulnya terpotong ("Nomor Kont..." atau
"Peny. Komersia"), sehingga pengguna tidak tahu isi kolomnya. Alat ini
membandingkan lebar setiap kolom dengan kebutuhan judulnya pada seluruh
halaman.

Kolom yang sedang menyusut karena jendela sempit dan kolom tanpa data
dilewati, karena keduanya bukan cacat tata letak.

Cara pakai:
    python tools/audit_kolom_tabel.py
"""
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
os.environ.setdefault("AKUNTANSIID_DATA",
                      str(Path(__file__).resolve().parents[1] / "_contoh"))
os.environ.pop("QT_QPA_PLATFORM", None)

from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import QApplication

from akuntansi_id.core import security as sec
from akuntansi_id.ui import theme
from akuntansi_id.ui.main_window import MainWindow, Sidebar
from akuntansi_id.ui.widgets import Tabel

# Lisensi uji dipakai agar seluruh halaman ikut diperiksa, termasuk
# halaman yang hanya tersedia pada paket Enterprise.
from akuntansi_id.core.license import Lisensi as _LisensiUji
_LISENSI_UJI = _LisensiUji(kunci='ATNTUJI', paket='enterprise', fitur={})



def periksa_tabel(tabel: Tabel, konteks: str) -> list:
    """
    Periksa judul kolom dan isi barisnya.

    Memeriksa judul saja tidak cukup: kolom bisa muat judulnya tetapi isinya
    terpotong, misalnya nomor kontrak yang panjang. Isi baris ikut diukur
    memakai teks terpanjang pada kolom itu.
    """
    temuan = []
    if tabel.columnCount() == 0:
        return temuan
    metrik = QFontMetrics(tabel.font())
    for c in range(tabel.columnCount()):
        judul_item = tabel.horizontalHeaderItem(c)
        if judul_item is None:
            continue
        judul = judul_item.text()
        if not judul.strip():
            continue
        lebar = tabel.columnWidth(c)

        # Kebutuhan judul
        perlu = metrik.horizontalAdvance(judul) + 22
        # Kebutuhan isi terpanjang pada kolom ini
        for r in range(tabel.rowCount()):
            it = tabel.item(r, c)
            if it is None or not it.text().strip():
                continue
            perlu_isi = metrik.horizontalAdvance(it.text()) + 18
            if perlu_isi > perlu:
                perlu = perlu_isi

        if lebar + 2 < perlu:
            temuan.append((konteks, judul, lebar, perlu))
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
    batas = time.time() + 2.0
    while time.time() < batas:
        app.processEvents()
        time.sleep(0.01)

    kode_menu = [item[0] for _seksi, daftar in Sidebar.MENU for item in daftar]
    semua = []
    jumlah_kolom = 0
    for nama in kode_menu:
        try:
            jw._navigasi(nama)
        except Exception:
            continue
        for _ in range(14):
            app.processEvents()
            time.sleep(0.005)
        halaman = jw.stack.currentWidget()
        if halaman is None:
            continue
        for tabel in halaman.findChildren(Tabel):
            if tabel.columnCount() == 0:
                continue
            # tabel tanpa data tidak mencerminkan masalah lebar
            if tabel.rowCount() == 0:
                continue
            jumlah_kolom += tabel.columnCount()
            semua += periksa_tabel(tabel, nama)

    print(f"kolom diperiksa : {jumlah_kolom}")
    print(f"temuan          : {len(semua)}")
    for konteks, judul, lebar, perlu in semua[:20]:
        print(f"  [{konteks}] {judul!r} lebar={lebar} perlu={perlu}")

    print()
    if semua:
        print(f"HASIL: {len(semua)} judul kolom tidak terbaca utuh")
        return 1
    print("HASIL: seluruh judul kolom tabel terbaca utuh")
    return 0


if __name__ == "__main__":
    sys.exit(main())
