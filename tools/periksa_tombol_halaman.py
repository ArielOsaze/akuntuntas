"""
Periksa tombol pada kepala halaman aplikasi.

Menjawab pertanyaan: apakah tombol tertentu benar benar ada pada halaman,
dan apakah ukurannya masuk akal (tidak nol dan tidak terpotong).

Cara pakai:
    python tools/periksa_tombol_halaman.py analisis
    python tools/periksa_tombol_halaman.py dashboard analisis
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "src"))

from akuntansi_id import db  # noqa: E402

os.environ.setdefault("AKUNTUNTAS_DATA", str(AKAR / "_data_potret"))


def main() -> int:
    kode_list = sys.argv[1:] or ["analisis", "dashboard"]

    from PySide6.QtCore import QEventLoop, QTimer, Qt
    from PySide6.QtGui import QFont
    from PySide6.QtWidgets import QApplication, QPushButton
    from akuntansi_id.ui import theme as tema
    from akuntansi_id.ui.main_window import MainWindow
    from akuntansi_id.core import security as sec
    from akuntansi_id import config
    from akuntansi_id.core import license as LIS

    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    app.setStyle("Fusion")
    tema.palet_terang(app)
    app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet(tema.stylesheet())

    db.init_db()
    akun = db.q("SELECT id, username, full_name, role, app_mode "
                "FROM users ORDER BY id LIMIT 1")
    if akun:
        a = akun[0]
        hasil = sec.LoginResult(
            ok=True, user_id=a["id"], username=a["username"],
            full_name=a["full_name"], role=a["role"],
            app_mode=a["app_mode"] or "beginner", mode_dipilih=True)
    else:
        hasil = sec.LoginResult(
            ok=True, user_id=0, username="periksa", full_name="Contoh",
            role="admin", app_mode="expert", mode_dipilih=True)

    sah, _alasan, data_lisensi = LIS.lisensi_sah(config.DATA_DIR)
    jendela = MainWindow(hasil, lisensi=data_lisensi if sah else None)
    jendela.resize(1440, 900)
    jendela.show()

    jeda = QEventLoop()
    QTimer.singleShot(2500, jeda.quit)
    jeda.exec()

    gagal = 0
    for kode in kode_list:
        jendela._navigasi(kode)
        tunggu = QEventLoop()
        QTimer.singleShot(1800, tunggu.quit)
        tunggu.exec()

        halaman = dict.get(jendela.halaman, kode)
        if halaman is None:
            print(f"  [GAGAL] {kode}: halaman tidak terbuka")
            gagal += 1
            continue

        tombol = halaman.findChildren(QPushButton)
        print(f"  --- {kode}: {len(tombol)} tombol ---")
        for t in tombol:
            teks = t.text().replace("&", "").strip()
            if not teks:
                continue
            lebar = t.width()
            tinggi = t.height()
            tanda = "OK " if lebar > 10 and tinggi > 10 else "KECIL"
            print(f"    [{tanda}] {teks[:26]:28s} {lebar}x{tinggi}")

    jendela.close()
    print()
    print(f"  selesai, {gagal} masalah")
    return 1 if gagal else 0


if __name__ == "__main__":
    sys.exit(main())
