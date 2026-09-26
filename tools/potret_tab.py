"""
Potret satu tab tertentu pada halaman aplikasi.

Halaman bertab hanya menampilkan tab pertama pada potret biasa. Alat ini
membuka tab yang diminta lebih dulu, lalu memotretnya.

Cara pakai:
    python tools/potret_tab.py analisis "Rasio Keuangan"
    python tools/potret_tab.py analisis "Simulasi Skenario"
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "src"))

from akuntansi_id import db  # noqa: E402

os.environ.setdefault("AKUNTUNTAS_DATA", str(AKAR / "_data_potret"))
KELUARAN = AKAR / "_potret_app"


def main() -> int:
    if len(sys.argv) < 3:
        print("  pakai: python tools/potret_tab.py <halaman> <nama tab>")
        return 2

    nama_halaman = sys.argv[1]
    nama_tab = sys.argv[2]
    gulir = 0
    if "--gulir" in sys.argv:
        gulir = int(sys.argv[sys.argv.index("--gulir") + 1])

    KELUARAN.mkdir(exist_ok=True)

    from PySide6.QtCore import QEventLoop, QTimer, Qt
    from PySide6.QtGui import QFont
    from PySide6.QtWidgets import QApplication, QTabWidget, QScrollArea
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

    # Mode Pemula menampilkan keterangan tambahan pada sebagian halaman.
    mode_pemula = "--pemula" in sys.argv
    app_mode = "beginner" if mode_pemula else "expert"

    a = db.q("SELECT id, username, full_name, role, app_mode "
             "FROM users ORDER BY id LIMIT 1")[0]
    hasil = sec.LoginResult(
        ok=True, user_id=a["id"], username=a["username"],
        full_name=a["full_name"], role=a["role"],
        app_mode=app_mode, mode_dipilih=True)

    sah, _alasan, data_lisensi = LIS.lisensi_sah(config.DATA_DIR)
    jendela = MainWindow(hasil, lisensi=data_lisensi if sah else None)
    jendela.resize(1440, 900)
    jendela.show()

    for _ in range(2):
        t = QEventLoop()
        QTimer.singleShot(1500, t.quit)
        t.exec()

    jendela._navigasi(nama_halaman)
    t = QEventLoop()
    QTimer.singleShot(2500, t.quit)
    t.exec()

    halaman = dict.get(jendela.halaman, nama_halaman)
    if halaman is None:
        print(f"  ! halaman {nama_halaman} tidak terbuka")
        return 1

    # Pilih tab yang diminta.
    tab = halaman.findChild(QTabWidget)
    if tab is None:
        print(f"  ! halaman {nama_halaman} tidak memiliki tab")
        return 1

    ditemukan = False
    for i in range(tab.count()):
        if tab.tabText(i).replace("&&", "&").strip() == nama_tab:
            tab.setCurrentIndex(i)
            ditemukan = True
            break

    if not ditemukan:
        print(f"  ! tab '{nama_tab}' tidak ditemukan. Yang ada:")
        for i in range(tab.count()):
            print(f"      - {tab.tabText(i)}")
        return 1

    t = QEventLoop()
    QTimer.singleShot(1800, t.quit)
    t.exec()

    # Gulir bila diminta.
    if gulir:
        for area in halaman.findChildren(QScrollArea):
            if not area.isVisible():
                continue
            bilah = area.verticalScrollBar()
            bilah.setValue(min(bilah.maximum(), bilah.value() + gulir))
        t = QEventLoop()
        QTimer.singleShot(1200, t.quit)
        t.exec()

    nama_berkas = (f"{nama_halaman}_"
                   f"{nama_tab.lower().replace(' ', '_')}.png")
    tujuan = KELUARAN / nama_berkas
    jendela.grab().save(str(tujuan))
    jendela.close()

    if tujuan.exists():
        print(f"  [OK] {nama_tab} -> {tujuan.name} "
              f"({tujuan.stat().st_size // 1024} KB)")
        return 0
    print("  ! gambar tidak tersimpan")
    return 1


if __name__ == "__main__":
    sys.exit(main())
