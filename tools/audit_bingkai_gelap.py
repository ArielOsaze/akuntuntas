"""
Periksa apakah Windows menggambar bingkai gelap pada jendela popup.

Windows 11 menyediakan atribut per jendela yang menentukan apakah bingkai
judul dan tepinya digambar gelap atau terang. Qt menyetel atribut itu dari
skema warna aplikasi. Bila aplikasi mengikuti skema gelap Windows, seluruh
popup dan dialog mendapat bingkai gelap, sehingga daftar pilihan tampak
dikelilingi garis hitam.

Berkas ini membaca atribut tersebut langsung dari Windows untuk membuktikan
apakah pemaksaan skema terang benar-benar berpengaruh.

Jalankan:  python tools/audit_bingkai_gelap.py
"""

import ctypes
import os
import sys
import time
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "src"))
os.environ.setdefault("AKUNTANSIID_DATA", str(AKAR / "_contoh"))

from PySide6.QtWidgets import QApplication             # noqa: E402

DWMWA_USE_IMMERSIVE_DARK_MODE = 20
DWMWA_USE_IMMERSIVE_DARK_MODE_LAMA = 19


def bingkai_gelap(hwnd: int):
    """
    Baca atribut mode gelap sebuah jendela dari Windows.

    Mengembalikan True bila bingkainya digambar gelap, False bila terang,
    dan None bila nilainya tidak dapat dibaca.
    """
    try:
        dwm = ctypes.windll.dwmapi
    except AttributeError:
        return None

    nilai = ctypes.c_int(0)
    for atribut in (DWMWA_USE_IMMERSIVE_DARK_MODE,
                    DWMWA_USE_IMMERSIVE_DARK_MODE_LAMA):
        hasil = dwm.DwmGetWindowAttribute(
            ctypes.c_void_p(int(hwnd)), ctypes.c_uint(atribut),
            ctypes.byref(nilai), ctypes.sizeof(nilai))
        if hasil == 0:
            return bool(nilai.value)
    return None


def main() -> int:
    app = QApplication([])
    app.setStyle("Fusion")

    from akuntansi_id.ui import theme
    tema_dipakai = "--tanpa-perbaikan" not in sys.argv
    if tema_dipakai:
        theme.palet_terang(app)
    app.setStyleSheet(theme.stylesheet())

    from akuntansi_id.ui.pages.kontrak_page import DialogKontrak

    class Ctx:
        company_id = 1
        user_id = 1
        username = "admin"
        full_name = "Admin"
        app_mode = "ahli"
        beginner = False

    d = DialogKontrak(Ctx())
    d.resize(900, 700)
    d.show()
    for _ in range(40):
        app.processEvents()
        time.sleep(0.02)

    skema = app.styleHints().colorScheme()
    print(f"  skema warna Qt   : {skema.name}")
    print(f"  perbaikan dipakai: {tema_dipakai}")
    print()

    hasil_dialog = bingkai_gelap(d.winId())
    print(f"  bingkai dialog   : {'GELAP' if hasil_dialog else 'terang'}"
          f"  (atribut Windows: {hasil_dialog})")

    cb = d.cmb_bentuk
    cb.showPopup()
    for _ in range(60):
        app.processEvents()
        time.sleep(0.02)

    popup = cb.view().window()
    hasil_popup = bingkai_gelap(popup.winId())
    print(f"  bingkai popup    : {'GELAP' if hasil_popup else 'terang'}"
          f"  (atribut Windows: {hasil_popup})")

    cb.hidePopup()
    print()

    if hasil_popup is None:
        print("HASIL: atribut bingkai tidak dapat dibaca pada sistem ini")
        return 1
    if hasil_popup:
        print("HASIL: popup masih memakai bingkai gelap")
        return 1
    print("HASIL: popup memakai bingkai terang")
    return 0


if __name__ == "__main__":
    sys.exit(main())
