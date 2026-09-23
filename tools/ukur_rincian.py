"""
Ukur bagian mana dari perpindahan halaman yang paling banyak memakan waktu.

Perpindahan halaman menjalankan beberapa langkah: mengganti halaman yang
tampil, memuat data, merapikan tampilan, dan memperbarui bilah status.
Berkas ini mengukur setiap langkah secara terpisah supaya perbaikan
diarahkan ke bagian yang benar-benar lambat.
"""

import os
import sys
import time
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "src"))
os.environ.setdefault("AKUNTANSIID_DATA", str(AKAR / "_contoh"))

from PySide6.QtWidgets import QApplication      # noqa: E402


def ukur(fn, ulangan: int = 3) -> float:
    """Rata-rata waktu satu fungsi dalam milidetik."""
    total = 0.0
    for _ in range(ulangan):
        t0 = time.perf_counter()
        fn()
        total += (time.perf_counter() - t0) * 1000
    return total / ulangan


def main() -> int:
    app = QApplication([])
    app.setStyle("Fusion")

    from akuntansi_id.ui import theme
    theme.palet_terang(app)
    app.setStyleSheet(theme.stylesheet())

    from akuntansi_id.core import security as sec
    from akuntansi_id.ui.main_window import MainWindow


    def _lisensi_uji():
        """Lisensi uji paket Enterprise agar seluruh halaman ikut diperiksa."""
        from akuntansi_id.core.license import Lisensi
        return Lisensi(kunci='ATNTUJI', paket='enterprise', fitur={})

    hasil = sec.login("admin", "admin123")
    jendela = MainWindow(hasil, lisensi=_lisensi_uji())
    jendela.resize(1400, 900)
    jendela.show()
    for _ in range(20):
        app.processEvents()

    print("=" * 74)
    print("RINCIAN WAKTU PERPINDAHAN HALAMAN")
    print("=" * 74)
    print()

    # Halaman terberat dari pengukuran sebelumnya.
    for kode in ("analisis", "bank", "perusahaan"):
        halaman = jendela.halaman[kode]
        print(f"  [{kode}]")

        if hasattr(halaman, "muat"):
            ms_muat = ukur(lambda: halaman.muat(), 3)
            print(f"    memuat data          : {ms_muat:7.1f} ms")

        ms_rapi = ukur(lambda: theme.rapikan_label(halaman), 3)
        print(f"    merapikan tampilan   : {ms_rapi:7.1f} ms")

        ms_status = ukur(jendela._refresh_status, 3)
        print(f"    memperbarui status   : {ms_status:7.1f} ms")

        ms_ganti = ukur(
            lambda: jendela.stack.setCurrentWidget(halaman), 3)
        print(f"    mengganti halaman    : {ms_ganti:7.1f} ms")
        print()

    # Rincian rapikan_label
    print("  [rincian merapikan tampilan pada halaman analisis]")
    halaman = jendela.halaman["analisis"]

    from PySide6.QtWidgets import QPushButton, QComboBox, QLabel
    from PySide6.QtGui import QFontMetrics

    tombol = halaman.findChildren(QPushButton)
    kotak = halaman.findChildren(QComboBox)
    label = halaman.findChildren(QLabel)
    print(f"    jumlah tombol        : {len(tombol)}")
    print(f"    jumlah kotak pilihan : {len(kotak)}")
    print(f"    jumlah label         : {len(label)}")

    def ukur_tombol():
        for b in tombol:
            if b.objectName() in ("NavGroup", "NavItem", "NavButton"):
                continue
            if b.text() and b.minimumWidth() < b.sizeHint().width():
                b.setMinimumWidth(b.sizeHint().width())

    def ukur_kotak():
        for cmb in kotak:
            if cmb.count() == 0:
                continue
            metrik = QFontMetrics(cmb.font())
            lebar = max(metrik.horizontalAdvance(cmb.itemText(i))
                        for i in range(cmb.count())) + 46
            if lebar > cmb.minimumWidth():
                cmb.setMinimumWidth(min(300, lebar))
            cmb.view().setMinimumWidth(min(560, max(lebar, 200)))

    ms_t = ukur(ukur_tombol, 3)
    ms_k = ukur(ukur_kotak, 3)
    print(f"    -> menghitung tombol : {ms_t:7.1f} ms")
    print(f"    -> menghitung kotak  : {ms_k:7.1f} ms")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
