"""
Uji sidebar setelah pencarian dan laporan masalah.

Memeriksa dua hal:
  1. Kelompok menu tetap lengkap setelah pencarian menu dipakai dan
     dikosongkan kembali — pilihan buka/tutup pengguna tidak boleh berubah.
  2. Laporan masalah tersusun lengkap dan dapat disiapkan untuk dikirim.

Cara pakai:
    python tests/test_sidebar_cari.py
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "src"))
os.environ.setdefault("AKUNTANSIID_DATA", str(AKAR / "_contoh"))
os.environ.pop("QT_QPA_PLATFORM", None)

from PySide6.QtWidgets import QApplication

from akuntansi_id import laporan_bug as bug
from akuntansi_id.core import security as sec
from akuntansi_id.ui import theme
from akuntansi_id.ui.main_window import MainWindow

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


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyleSheet(theme.stylesheet())

    hasil = sec.LoginResult(ok=True, user_id=1, username="admin",
                            full_name="Admin", role="owner",
                            app_mode="expert", mode_dipilih=True)
    # Paket Enterprise dipakai supaya seluruh menu ikut diuji, tanpa
    # terpotong pembatasan paket lisensi.
    from akuntansi_id.core import license as lisensi_mod
    lisensi = lisensi_mod.Lisensi(kunci="ATNTUJI", paket="enterprise", fitur={})
    jw = MainWindow(hasil, lisensi=lisensi)
    jw.resize(1440, 900)
    jw.show()
    batas = time.time() + 2.0
    while time.time() < batas:
        app.processEvents()
        time.sleep(0.01)

    sb = jw.sidebar
    jumlah_kelompok = len(sb._grup)

    def tampak() -> int:
        return sum(1 for j, _ in sb._grup.values() if not j.isHidden())

    def menu_tampak() -> int:
        return sum(1 for b in sb.tombol.values() if not b.isHidden())

    print("=" * 66)
    print("SIDEBAR — PENCARIAN MENU")
    print("=" * 66)

    cek("Seluruh judul kelompok tampak saat aplikasi dibuka",
        tampak() == jumlah_kelompok,
        f"{tampak()} dari {jumlah_kelompok}")
    cek("Seluruh menu tampak saat aplikasi dibuka",
        menu_tampak() == len(sb.tombol),
        f"{menu_tampak()} dari {len(sb.tombol)}")

    # buka satu kelompok seperti yang dilakukan pengguna
    if "DATA USAHA" in sb._grup:
        sb._grup["DATA USAHA"][0].setChecked(True)
        for _ in range(15):
            app.processEvents()
            time.sleep(0.01)
    kelompok_terbuka = [n for n, (_, wd) in sb._grup.items() if not wd.isHidden()]
    cek("Kelompok dapat dibuka pengguna", len(kelompok_terbuka) >= 1,
        f"terbuka: {kelompok_terbuka}")

    # pencarian: hasil menyempit
    sb.inp_cari.setText("kontrak")
    for _ in range(20):
        app.processEvents()
        time.sleep(0.01)
    cek("Pencarian menyaring menu", menu_tampak() < len(sb.tombol),
        f"{menu_tampak()} menu tersisa")
    cek("Pencarian menyisakan minimal satu menu", menu_tampak() >= 1,
        f"{menu_tampak()} menu")

    # ganti kata kunci
    sb.inp_cari.setText("jurnal")
    for _ in range(20):
        app.processEvents()
        time.sleep(0.01)
    cek("Kata kunci lain tetap menyaring", menu_tampak() < len(sb.tombol),
        f"{menu_tampak()} menu tersisa")

    # kosongkan: seluruh kelompok harus kembali
    sb.inp_cari.setText("")
    for _ in range(20):
        app.processEvents()
        time.sleep(0.01)
    cek("Seluruh judul kelompok kembali setelah pencarian dikosongkan",
        tampak() == jumlah_kelompok,
        f"{tampak()} dari {jumlah_kelompok}")
    cek("Seluruh menu kembali setelah pencarian dikosongkan",
        menu_tampak() == len(sb.tombol),
        f"{menu_tampak()} dari {len(sb.tombol)}")

    kelompok_kini = [n for n, (_, wd) in sb._grup.items() if not wd.isHidden()]
    cek("Pilihan buka/tutup pengguna tetap dihormati",
        kelompok_kini == kelompok_terbuka,
        f"sebelum {kelompok_terbuka}, sesudah {kelompok_kini}")

    print()
    print("=" * 66)
    print("LAPORAN MASALAH")
    print("=" * 66)

    lap = bug.susun_laporan(
        kesalahan="AttributeError: contoh",
        jejak="Traceback (most recent call last):\n  berkas contoh.py",
        catatan_pengguna="Muncul saat membuka kontrak.",
        langkah="1. Buka Kontrak\n2. Tekan Kontrak Baru")
    teks = lap["teks"]
    cek("Laporan memuat keterangan sistem", "aplikasi" in teks and "versi" in teks)
    cek("Laporan memuat langkah pengguna", "1. Buka Kontrak" in teks)
    cek("Laporan memuat pesan kesalahan", "AttributeError" in teks)
    cek("Laporan memuat jejak teknis", "Traceback" in teks)
    cek("Laporan memuat alamat pengembang",
        bug.EMAIL_PENGEMBANG in bug.tautan_email(teks))

    berkas = bug.simpan_laporan(teks, "uji")
    cek("Laporan dapat disimpan ke berkas",
        berkas is not None and berkas.exists(),
        f"berkas: {berkas}")
    if berkas and berkas.exists():
        berkas.unlink()

    cek("Tautan email memakai subjek yang jelas",
        "subject=" in bug.tautan_email(teks, "[AkunTuntas] Uji")
        and "AkunTuntas" in bug.tautan_email(teks, "[AkunTuntas] Uji"))

    print()
    print("=" * 66)
    print(f"HASIL: {LULUS} LULUS, {GAGAL} GAGAL")
    print("=" * 66)
    return 1 if GAGAL else 0


if __name__ == "__main__":
    sys.exit(main())
