"""
Ukur kecepatan pembuatan seluruh dialog isian.

Dialog dibuat langsung, bukan lewat klik tombol, karena tombol memanggil
exec() yang menunggu dialog ditutup sehingga pengukuran tidak selesai.
Dengan membuatnya langsung, waktu yang terukur benar-benar waktu membuat
dan menyusun isi dialog.

Cara ini sama dengan yang dipakai alat pemeriksa antarmuka lain, yang juga
membuat dialog langsung supaya tidak terhenti oleh dialog modal.
"""

import inspect
import os
import sys
import time
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "src"))
os.environ.setdefault("AKUNTANSIID_DATA", str(AKAR / "_contoh"))

from PySide6.QtWidgets import QApplication, QDialog      # noqa: E402


def main() -> int:
    app = QApplication([])
    app.setStyle("Fusion")

    from akuntansi_id.ui import theme
    theme.palet_terang(app)
    app.setStyleSheet(theme.stylesheet())

    from akuntansi_id.core import security as sec
    from akuntansi_id.ui.main_window import MainWindow

    jendela = MainWindow(sec.login("admin", "admin123"))
    jendela.resize(1400, 900)
    jendela.show()
    for _ in range(20):
        app.processEvents()

    # kumpulkan semua kelas dialog dari modul halaman
    from akuntansi_id.ui import pages
    import akuntansi_id.ui.dialog_bug as bug

    kelas_dialog = []
    for modul in list(pages.__dict__.values()) + [bug]:
        if not inspect.ismodule(modul):
            continue
        for nama, objek in inspect.getmembers(modul, inspect.isclass):
            if not issubclass(objek, QDialog) or objek is QDialog:
                continue
            if objek.__module__ != modul.__name__:
                continue
            kelas_dialog.append((modul.__name__.split(".")[-1], nama, objek))

    # buang duplikat
    unik = {}
    for modul, nama, objek in kelas_dialog:
        unik[objek] = (modul, nama, objek)
    kelas_dialog = list(unik.values())

    print("=" * 78)
    print("KECEPATAN PEMBUATAN DIALOG ISIAN")
    print("=" * 78)
    print()
    print(f"  {len(kelas_dialog)} kelas dialog ditemukan")
    print()

    hasil = []
    gagal = []
    for modul, nama, kelas in kelas_dialog:
        # tentukan argumen yang dibutuhkan
        try:
            tanda = inspect.signature(kelas.__init__).parameters
        except (TypeError, ValueError):
            continue

        argumen = []
        for nama_arg in list(tanda)[1:]:          # lewati self
            if nama_arg in ("self", "parent", "kwargs", "args"):
                continue
            argumen.append(jendela.ctx)

        t0 = time.perf_counter()
        try:
            dlg = kelas(*argumen)
            for _ in range(3):
                app.processEvents()
            ms = (time.perf_counter() - t0) * 1000
            hasil.append((nama, ms))
            dlg.close()
            dlg.deleteLater()
        except Exception as e:
            gagal.append((nama, str(e)[:60]))
        for _ in range(2):
            app.processEvents()

    hasil.sort(key=lambda x: -x[1])
    print(f"  {'dialog':34s} {'waktu':>10s}")
    print(f"  {'-' * 34} {'-' * 10}")
    for nama, ms in hasil[:16]:
        tanda = "  <-- LAMBAT" if ms > 250 else ""
        print(f"  {nama:34s} {ms:8.1f} ms{tanda}")

    if hasil:
        rata = sum(ms for _, ms in hasil) / len(hasil)
        print()
        print(f"  Rata-rata {len(hasil)} dialog : {rata:.1f} ms")
        print(f"  Terlambat          : {max(ms for _, ms in hasil):.1f} ms")

    if gagal:
        print()
        print(f"  {len(gagal)} dialog perlu argumen lain:")
        for nama, pesan in gagal[:6]:
            print(f"    {nama}: {pesan}")

    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
