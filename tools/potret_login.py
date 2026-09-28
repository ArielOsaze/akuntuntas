"""
Potret halaman login pada beberapa ukuran jendela.

Dipakai untuk memeriksa tampilan halaman login: apakah isinya terpotong,
apakah ada yang melewati tepi, dan apakah jaraknya wajar. Jendela
sungguhan dipakai supaya font yang tergambar adalah font sistem.

Cara pakai:
    python tools/potret_login.py [folder]
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "src"))

FOLDER = Path(tempfile.mkdtemp(prefix="akuntuntas_login_"))
os.environ["LOCALAPPDATA"] = str(FOLDER)

from PySide6.QtCore import QEventLoop, QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication.instance() or QApplication([])

from akuntansi_id import db  # noqa: E402
from akuntansi_id.core import security as sec  # noqa: E402
from akuntansi_id.ui import theme  # noqa: E402

app.setStyle("Fusion")
theme.palet_terang(app)

db.init_db()
sec.ensure_default_admin()

from akuntansi_id.ui.login import LoginPage  # noqa: E402

HASIL = Path(sys.argv[1]) if len(sys.argv) > 1 else AKAR / "_potret_login"
HASIL.mkdir(parents=True, exist_ok=True)

# Ukuran yang diuji: dari yang paling kecil yang didukung sampai lega.
UKURAN = [
    (1024, 640),
    (1280, 720),
    (1366, 768),
    (1600, 900),
]


def tunggu(ms: int) -> None:
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def periksa_luber(halaman, lebar: int, tinggi: int) -> list[str]:
    """Cari widget yang melewati tepi jendela."""
    temuan = []
    for w in halaman.findChildren(object):
        if not hasattr(w, "geometry") or not hasattr(w, "isVisible"):
            continue
        try:
            if not w.isVisible():
                continue
            g = w.geometry()
        except Exception:
            continue
        # Koordinat dipetakan ke jendela utama
        try:
            titik = w.mapTo(halaman, g.topLeft() - g.topLeft())
            x, y = titik.x(), titik.y()
        except Exception:
            continue
        kanan = x + g.width()
        bawah = y + g.height()
        if kanan > lebar + 2 or bawah > tinggi + 2:
            nama = w.__class__.__name__
            teks = ""
            if hasattr(w, "text"):
                try:
                    teks = str(w.text())[:28]
                except Exception:
                    teks = ""
            temuan.append(
                f"{nama} '{teks}' di ({x},{y}) {g.width()}x{g.height()} "
                f"melewati tepi {lebar}x{tinggi}")
    return temuan


for lebar, tinggi in UKURAN:
    halaman = LoginPage()
    halaman.resize(lebar, tinggi)
    halaman.show()
    tunggu(700)

    berkas = HASIL / f"login_{lebar}x{tinggi}.png"
    halaman.grab().save(str(berkas))

    luber = periksa_luber(halaman, lebar, tinggi)
    print(f"  {lebar}x{tinggi}: {berkas.name}")
    if luber:
        for t in luber[:6]:
            print(f"      LUBER: {t}")
    else:
        print("      tidak ada yang melewati tepi")

    halaman.close()
    halaman.deleteLater()
    tunggu(250)

print(f"\n  tersimpan di: {HASIL}")
