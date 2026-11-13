"""
Uji alur keluar dan masuk akun berulang.

Bug yang dijaga: ``setCentralWidget()`` menghapus widget pusat lama lewat
deleteLater. Setelah pemakaian cukup lama, ``self.stack`` sudah menjadi
objek C++ yang mati, sehingga tombol "Keluar Akun" gagal dengan
``RuntimeError: Internal C++ object (QStackedWidget) already deleted``.
Uji ini memaksa antrean DeferredDelete dieksekusi, lalu keluar-masuk
beberapa kali untuk memastikan halaman masuk selalu dibuat ulang.
"""
from __future__ import annotations

import os
import shutil
import sys
import time
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
DIR_UJI = AKAR / "_uitest_logout"
shutil.rmtree(DIR_UJI, ignore_errors=True)

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AKUNTANSIID_DATA"] = str(DIR_UJI)
os.environ["LOCALAPPDATA"] = str(AKAR / "_uitest_logout_local")

sys.path.insert(0, str(AKAR / "src"))

from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication, QStackedWidget

from akuntansi_id import config, db, services
from akuntansi_id.core import security as sec
from akuntansi_id.core.license import Lisensi
from akuntansi_id.ui import theme
import akuntansi_id.ui.main_window as mw

LULUS = 0
GAGAL = 0


def cek(nama: str, syarat: bool, keterangan: str = ""):
    global LULUS, GAGAL
    if syarat:
        LULUS += 1
        print(f"  [LULUS] {nama}")
    else:
        GAGAL += 1
        print(f"  [GAGAL] {nama}" + (f" — {keterangan}" if keterangan else ""))


def proses(app, n: int = 40):
    for _ in range(n):
        app.processEvents()
        time.sleep(0.01)


def buang_deferred(app):
    """Jalankan deleteLater seperti setelah jendela dipakai beberapa lama."""
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    app.processEvents()


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    theme.palet_terang(app)
    app.setStyleSheet(theme.stylesheet())

    print("=" * 66)
    print("ALUR KELUAR & MASUK AKUN")
    print("=" * 66)

    config.ensure_dirs()
    db.init_db()
    sec.ensure_default_admin()
    baris = db.q1("SELECT id FROM users WHERE username=?", (config.DEFAULT_ADMIN_USER,))
    db.ex("UPDATE users SET must_change_pw=0, mode_dipilih=1, app_mode='beginner' "
          "WHERE id=?", (baris["id"],))
    perlu = not services.list_companies(aktif_saja=False)
    cid = (services.create_company("PT Uji Keluar Masuk", "pt")
           if perlu else services.list_companies(aktif_saja=False)[0]["id"])

    lisensi = Lisensi(kunci="ATNTUJI", paket="enterprise", fitur={})
    mw.LIS.lisensi_sah = lambda _dir: (True, "uji", lisensi)

    print("\n[Siklus pertama]")
    jendela = mw.JendelaAplikasi()
    proses(app)
    cek("Halaman masuk tampil",
        isinstance(jendela.centralWidget(), QStackedWidget))

    hasil = sec.login(config.DEFAULT_ADMIN_USER, config.DEFAULT_ADMIN_PASSWORD)
    cek("Login uji berhasil", hasil.ok, hasil.message)
    jendela._setelah_login(hasil)
    proses(app)
    buang_deferred(app)
    cek("Jendela utama terbuka", jendela.main_window is not None)
    cek("Referensi stack lama dilepas", jendela.stack is None)
    cek("Perusahaan aktif termuat",
        jendela.main_window is not None
        and jendela.main_window.ctx.company_id == cid)

    print("\n[Keluar-masuk berulang]")
    for putaran in range(3):
        utama = jendela.main_window
        utama.kembali_ke_login.emit()
        proses(app)
        buang_deferred(app)
        cek(f"Keluar {putaran + 1} kembali ke halaman masuk",
            isinstance(jendela.centralWidget(), QStackedWidget)
            and jendela.halaman_login is not None)
        cek(f"Stack baru {putaran + 1} masih hidup",
            jendela.stack is not None and jendela.stack.count() >= 1)

        hasil = sec.login(config.DEFAULT_ADMIN_USER,
                          config.DEFAULT_ADMIN_PASSWORD)
        jendela._setelah_login(hasil)
        proses(app)
        buang_deferred(app)
        cek(f"Masuk lagi {putaran + 1} membuka jendela utama",
            jendela.main_window is not None)

    jumlah_akun = db.scalar(
        "SELECT COUNT(*) FROM accounts WHERE company_id=?", (cid,), default=0)
    cek("Bagan akun perusahaan tetap utuh", jumlah_akun > 0,
        f"akun={jumlah_akun}")

    print()
    print(f"HASIL: {LULUS} LULUS, {GAGAL} GAGAL")
    return 0 if GAGAL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
