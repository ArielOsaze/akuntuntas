"""
Pemburu bug: buka setiap halaman, setiap tab, dan setiap dialog.

Bug yang tidak terlihat dari pembacaan kode sering muncul saat widget dibuat:
argumen salah, atribut belum ada, atau sinyal tersambung ke fungsi yang tidak
menerima parameternya.

Dialog TIDAK dibuka lewat klik tombol. Mengklik tombol yang membuka dialog
membuat proses berhenti menunggu dialog ditutup. Dialog diuji dengan
membuatnya langsung, sehingga kesalahan pembuatannya tetap tertangkap tanpa
proses berhenti.

Jalankan:  python tools/buruh_bug_ui.py
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

from PySide6.QtWidgets import QApplication, QTabWidget    # noqa: E402

# Dialog yang tidak boleh dibuka otomatis karena menjalankan tindakan nyata
# (menghapus data, memulihkan cadangan, menutup aplikasi).
DILARANG = ("reset", "pulih", "hapus", "restore", "keluar", "logout",
            "impor", "unduh", "kirim")


def daftar_halaman() -> list:
    """Baca daftar halaman dari main_window.py, sumber yang dipakai aplikasi."""
    berkas = AKAR / "src" / "akuntansi_id" / "ui" / "main_window.py"
    isi = berkas.read_text(encoding="utf-8")
    mulai = isi.find("pemetaan = [")
    akhir = isi.find("]", mulai)
    pola = re.compile(r'\("(\w+)",\s*lambda:\s*(\w+)\(self\.ctx\)\)')
    return pola.findall(isi[mulai:akhir])


def daftar_dialog() -> list:
    """Cari seluruh kelas QDialog di halaman, beserta modulnya."""
    hasil = []
    folder = AKAR / "src" / "akuntansi_id" / "ui" / "pages"
    for berkas in sorted(folder.glob("*.py")):
        isi = berkas.read_text(encoding="utf-8")
        for nama in re.findall(r"^class\s+(\w+)\(QDialog\)", isi, re.M):
            hasil.append((berkas.stem, nama))
    return hasil


def main() -> int:
    app = QApplication([])
    app.setStyle("Fusion")

    from akuntansi_id.ui import theme
    theme.palet_terang(app)
    app.setStyleSheet(theme.stylesheet())

    from akuntansi_id import db
    db.init_db()

    from akuntansi_id.core import security as sec
    from akuntansi_id.ui.main_window import MainWindow


    def _lisensi_uji():
        """Lisensi uji paket Enterprise agar seluruh halaman ikut diperiksa."""
        from akuntansi_id.core.license import Lisensi
        return Lisensi(kunci='ATNTUJI', paket='enterprise', fitur={})

    hasil_login = sec.login("admin", "admin123")
    jendela = MainWindow(hasil_login, lisensi=_lisensi_uji())
    jendela.resize(1400, 900)
    jendela.show()
    for _ in range(30):
        app.processEvents()
        time.sleep(0.02)

    masalah = []

    # ------------------------------------------------------- halaman
    daftar = daftar_halaman()
    print("=" * 72)
    print(f"PEMBURU BUG — {len(daftar)} HALAMAN")
    print("=" * 72)
    print()

    for kode, nama_kelas in daftar:
        halaman = jendela.halaman.get(kode)
        if halaman is None:
            masalah.append((kode, "halaman tidak terbentuk", ""))
            print(f"  [GAGAL] {kode:16s} tidak terbentuk")
            continue
        try:
            jendela._navigasi(kode)
            for _ in range(12):
                app.processEvents()
                time.sleep(0.01)
            print(f"  [OK]    {kode:16s} {nama_kelas}")
        except Exception as e:
            masalah.append((kode, f"{type(e).__name__}: {e}",
                            traceback.format_exc()))
            print(f"  [GAGAL] {kode:16s} {type(e).__name__}: {e}")

    # ------------------------------------------------------- tab
    print()
    print("=" * 72)
    print("SETIAP TAB")
    print("=" * 72)
    print()

    jumlah_tab = 0
    for kode, halaman in jendela.halaman.items():
        for tab in halaman.findChildren(QTabWidget):
            for i in range(tab.count()):
                try:
                    tab.setCurrentIndex(i)
                    for _ in range(4):
                        app.processEvents()
                        time.sleep(0.01)
                    jumlah_tab += 1
                except Exception as e:
                    masalah.append((f"{kode}:tab{i}", f"{type(e).__name__}: {e}",
                                    traceback.format_exc()))
                    print(f"  [GAGAL] {kode} tab {i}: {e}")
    print(f"  {jumlah_tab} tab dibuka tanpa kesalahan")

    # ------------------------------------------------------- dialog
    print()
    print("=" * 72)
    print("SETIAP DIALOG (dibuat langsung, tidak lewat klik)")
    print("=" * 72)
    print()

    jumlah_dialog = 0
    dilewati = 0
    ctx = jendela.ctx

    for modul, nama_kelas in daftar_dialog():
        if any(k in nama_kelas.lower() for k in DILARANG):
            dilewati += 1
            continue
        try:
            mod = __import__(f"akuntansi_id.ui.pages.{modul}",
                             fromlist=[nama_kelas])
            kelas = getattr(mod, nama_kelas)
            tanda = inspect.signature(kelas.__init__).parameters
            # Buang self dan argumen opsional. Dialog yang memerlukan data
            # tertentu (misalnya id invoice) dilewati: untuk membuatnya perlu
            # data nyata, dan itu diuji pada berkas uji tersendiri.
            wajib = [n for n, p in tanda.items()
                     if n != "self" and p.default is inspect.Parameter.empty
                     and p.kind in (inspect.Parameter.POSITIONAL_ONLY,
                                    inspect.Parameter.POSITIONAL_OR_KEYWORD)]
            if not wajib:
                d = kelas()
            elif wajib == ["ctx"]:
                d = kelas(ctx)
            elif wajib == ["ctx", "comp"]:
                # Dialog yang butuh profil perusahaan. Pemanggilnya di
                # aplikasi selalu memeriksa dulu bahwa profilnya ada, jadi
                # di sini pun dilewati bila belum ada.
                comp = getattr(ctx, "company", None)
                if not comp:
                    dilewati += 1
                    continue
                d = kelas(ctx, comp)
            else:
                dilewati += 1
                continue
            d.show()
            for _ in range(6):
                app.processEvents()
                time.sleep(0.01)
            d.close()
            d.deleteLater()
            app.processEvents()
            jumlah_dialog += 1
            print(f"  [OK]    {modul}.{nama_kelas}")
        except Exception as e:
            masalah.append((f"{modul}.{nama_kelas}",
                            f"{type(e).__name__}: {e}",
                            traceback.format_exc()))
            print(f"  [GAGAL] {modul}.{nama_kelas}: {type(e).__name__}: {e}")

    print()
    print(f"  {jumlah_dialog} dialog dibuat, {dilewati} dilewati "
          f"(menjalankan tindakan nyata)")

    # ------------------------------------------------------- ringkasan
    print()
    print("=" * 72)
    if masalah:
        print(f"HASIL: {len(masalah)} KESALAHAN DITEMUKAN")
        print("=" * 72)
        for kode, pesan, jejak in masalah[:8]:
            print()
            print(f"  [{kode}] {pesan}")
            for baris in jejak.splitlines()[-5:]:
                print(f"      {baris}")
        return 1

    print("HASIL: tidak ada kesalahan pada halaman, tab, maupun dialog")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
