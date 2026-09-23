"""
Cari widget QFrame yang bertumpuk di dashboard pada kondisi yang sama
dengan alat periksa tumpang tindih.

Alat periksa memakai data contoh di folder _contoh, mode tanpa layar, dan
berpindah halaman tiga kali. Skrip ini meniru keadaan itu lalu menampilkan
widget yang bertumpuk beserta teks di dalamnya.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
os.environ["AKUNTANSIID_DATA"] = str(AKAR / "_contoh")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(AKAR / "src"))

from PySide6.QtWidgets import QApplication, QFrame, QLabel  # noqa: E402


def main() -> int:
    from akuntansi_id import config, db, services
    from akuntansi_id.core import security as sec
    from akuntansi_id.core.license import Lisensi
    from akuntansi_id.ui import theme
    from akuntansi_id.ui.main_window import MainWindow

    if not (AKAR / "_contoh").exists():
        print("  data contoh belum ada:")
        print(f'    python tools/buat_data_contoh.py "{AKAR / "_contoh"}"')
        return 2

    app = QApplication([])
    app.setStyleSheet(theme.stylesheet())
    config.ensure_dirs()
    db.init_db()
    sec.ensure_default_admin()

    perusahaan = services.list_companies(aktif_saja=False)
    cid = perusahaan[0]["id"]
    hasil = sec.login("admin", config.DEFAULT_ADMIN_PASSWORD)
    jendela = MainWindow(hasil, lisensi=Lisensi(
        kunci="ATNTUJI", paket="enterprise", fitur={}))
    jendela.ctx.company_id = cid
    jendela.ctx.company = services.get_company(cid)
    jendela.resize(1600, 1000)
    jendela.show()

    halaman = jendela.halaman.get("dashboard")

    # Tiru alat periksa: navigasi tiga kali
    for putaran in range(3):
        jendela._navigasi("dashboard")
        if hasattr(halaman, "muat"):
            halaman.muat()
        for _ in range(8):
            app.processEvents()

    print("=" * 72)
    print("  LABEL BERTUMPUK DI DASHBOARD")
    print("=" * 72)
    print()

    jumlah = 0
    # Alat periksa memakai QWidget sebagai jenis blok, jadi semua anak
    # diperiksa, bukan hanya QFrame.
    from PySide6.QtWidgets import QWidget
    for induk in halaman.findChildren(QWidget):
        anak = [x for x in induk.children()
                if isinstance(x, QWidget) and x.isVisible()
                and x.parent() is induk]
        for i in range(len(anak)):
            for k in range(i + 1, len(anak)):
                a, b = anak[i], anak[k]
                ga, gb = a.geometry(), b.geometry()
                if ga.width() == 0 or gb.width() == 0:
                    continue
                kiri = max(ga.left(), gb.left())
                atas = max(ga.top(), gb.top())
                kanan = min(ga.right(), gb.right())
                bawah = min(ga.bottom(), gb.bottom())
                if kanan - kiri > 2 and bawah - atas > 2:
                    jumlah += 1
                    print(f"  [{jumlah}] bertumpuk di induk "
                          f"{induk.__class__.__name__}:")
                    for nama, w, g in (("A", a, ga), ("B", b, gb)):
                        teks = ""
                        if isinstance(w, QLabel):
                            teks = w.text()[:46]
                        else:
                            for lbl in w.findChildren(QLabel)[:3]:
                                if lbl.text().strip():
                                    teks = lbl.text()[:46]
                                    break
                        print(f"      {nama}: {w.__class__.__name__} "
                              f"geom={g.getRect()}  teks='{teks}'")
                    print()
                    if jumlah >= 8:
                        break
            if jumlah >= 8:
                break
        if jumlah >= 8:
            break

    if jumlah == 0:
        print("  tidak ada frame bertumpuk")

    jendela.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
