"""
Periksa tinggi baris setiap daftar pilihan, di halaman maupun di dialog.

Baris daftar pilihan pernah terlalu mepet sehingga huruf berdescender
(g, j, p, y) terpotong dan barisnya sulit ditunjuk. Pemeriksaan ini membuka
setiap daftar pilihan di seluruh halaman DAN di dalam dialog, lalu
memastikan tinggi barisnya cukup untuk menampilkan huruf secara utuh.

Dialog ikut diperiksa karena banyak isian berada di sana, dan penyaring
peristiwa yang merapikannya hanya berjalan saat dialog benar-benar
ditampilkan.

Jalankan:  python tools/audit_tinggi_baris_pilihan.py
"""

import inspect
import os
import re
import sys
import time
import traceback
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "src"))
os.environ.setdefault("AKUNTANSIID_DATA", str(AKAR / "_contoh"))

from PySide6.QtWidgets import QApplication, QComboBox   # noqa: E402

# Tinggi huruf pada aplikasi ini 16 piksel. Baris daftar pilihan harus
# menyisakan ruang di atas dan di bawah huruf, karena huruf berdescender
# (g, j, p, y) memakai ruang di bawah garis dasar. Tinggi 26 piksel adalah
# batas terendah yang masih menampilkan huruf utuh; di bawah itu bagian
# bawah huruf mulai terpotong.
TINGGI_MINIMUM = 26

# Dialog yang tidak boleh dibuka otomatis karena menjalankan tindakan nyata.
DILARANG = ("reset", "pulih", "hapus", "restore", "keluar", "logout",
            "impor", "unduh", "kirim")


def daftar_kelas_dialog() -> list:
    """Cari seluruh kelas QDialog di halaman, beserta modulnya."""
    hasil = []
    folder = AKAR / "src" / "akuntansi_id" / "ui" / "pages"
    for berkas in sorted(folder.glob("*.py")):
        isi = berkas.read_text(encoding="utf-8")
        for nama in re.findall(r"^class\s+(\w+)\(QDialog\)", isi, re.M):
            hasil.append((berkas.stem, nama))
    return hasil


def periksa_kotak(cb: QComboBox) -> list:
    """Kembalikan daftar masalah pada satu daftar pilihan."""
    masalah = []
    if cb.count() == 0:
        return masalah
    tinggi = cb.view().sizeHintForRow(0)
    if tinggi < TINGGI_MINIMUM:
        masalah.append((cb.itemText(0)[:28], tinggi))
    return masalah


def main() -> int:
    app = QApplication([])
    app.setStyle("Fusion")

    from akuntansi_id.ui import theme
    theme.palet_terang(app)
    app.setStyleSheet(theme.stylesheet())
    theme.pasang_penyesuai_dialog(app)

    from akuntansi_id.core import security as sec
    from akuntansi_id.ui.main_window import MainWindow


    def _lisensi_uji():
        """Lisensi uji paket Enterprise agar seluruh halaman ikut diperiksa."""
        from akuntansi_id.core.license import Lisensi
        return Lisensi(kunci='ATNTUJI', paket='enterprise', fitur={})

    try:
        hasil = sec.login("admin", "admin123")
    except Exception as e:
        print(f"Tidak dapat masuk: {e}")
        print("Jalankan tools/buat_data_contoh.py dulu.")
        return 1

    jendela = MainWindow(hasil, lisensi=_lisensi_uji())
    jendela.resize(1400, 900)
    jendela.show()
    for _ in range(30):
        app.processEvents()
        time.sleep(0.02)

    masalah = []
    jumlah_halaman = 0
    jumlah_dialog = 0
    jumlah_kotak = 0

    # ------------------------------------------------------------- halaman
    for kode, halaman in jendela.halaman.items():
        try:
            jendela._navigasi(kode)
            for _ in range(12):
                app.processEvents()
                time.sleep(0.01)
            jumlah_halaman += 1
        except Exception:
            continue

        for cb in halaman.findChildren(QComboBox):
            if not cb.isVisible():
                continue
            jumlah_kotak += 1
            for teks, tinggi in periksa_kotak(cb):
                masalah.append((kode, teks, tinggi))

    # -------------------------------------------------------------- dialog
    ctx = jendela.ctx
    for modul, nama_kelas in daftar_kelas_dialog():
        if any(k in nama_kelas.lower() for k in DILARANG):
            continue
        try:
            mod = __import__(f"akuntansi_id.ui.pages.{modul}",
                             fromlist=[nama_kelas])
            kelas = getattr(mod, nama_kelas)
            tanda = inspect.signature(kelas.__init__).parameters
            wajib = [n for n, p in tanda.items()
                     if n != "self" and p.default is inspect.Parameter.empty
                     and p.kind in (inspect.Parameter.POSITIONAL_ONLY,
                                    inspect.Parameter.POSITIONAL_OR_KEYWORD)]
            if not wajib:
                d = kelas()
            elif wajib == ["ctx"]:
                d = kelas(ctx)
            elif wajib == ["ctx", "comp"]:
                comp = getattr(ctx, "company", None)
                if not comp:
                    continue
                d = kelas(ctx, comp)
            else:
                continue

            d.show()
            for _ in range(8):
                app.processEvents()
                time.sleep(0.01)
            jumlah_dialog += 1

            for cb in d.findChildren(QComboBox):
                jumlah_kotak += 1
                for teks, tinggi in periksa_kotak(cb):
                    masalah.append((f"dialog {nama_kelas}", teks, tinggi))

            d.close()
            d.deleteLater()
            app.processEvents()
        except Exception as e:
            masalah.append((f"dialog {nama_kelas}", "gagal dibuka",
                            f"{type(e).__name__}: {e}"))

    print(f"{jumlah_kotak} daftar pilihan diperiksa "
          f"({jumlah_halaman} halaman, {jumlah_dialog} dialog)")
    print()

    if masalah:
        print(f"HASIL: {len(masalah)} daftar pilihan barisnya terlalu mepet "
              f"(minimum {TINGGI_MINIMUM}px)")
        for kode, teks, tinggi in masalah[:15]:
            print(f"   [{kode}] {teks!r} — {tinggi}")
        return 1

    print(f"HASIL: seluruh daftar pilihan barisnya minimal "
          f"{TINGGI_MINIMUM}px, huruf tampil utuh")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc()
        sys.exit(1)
