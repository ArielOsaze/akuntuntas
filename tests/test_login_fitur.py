"""
Uji halaman login: setiap fitur benar-benar berfungsi.

Yang diperiksa:
  1. Tombol lihat password menyembunyikan dan menampilkan isi kolomnya.
  2. Pilihan "ingat nama pengguna" tersimpan dan terhapus dengan benar.
  3. Login dengan kredensial benar berhasil.
  4. Login dengan password salah menampilkan pesan dan tercatat di log
     keamanan sebagai percobaan gagal.
  5. Keterangan akun bawaan hilang setelah passwordnya diganti.
  6. Peringatan Caps Lock hanya muncul saat Caps Lock menyala.

Cara pakai:
    python tests/test_login_fitur.py
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

from akuntansi_id import config, db
from akuntansi_id.core import security as sec
from akuntansi_id.ui import theme
from akuntansi_id.ui.login import LoginPage, capslock_menyala

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


def jeda(app, n=15):
    for _ in range(n):
        app.processEvents()
        time.sleep(0.01)


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyleSheet(theme.stylesheet())

    print("=" * 66)
    print("HALAMAN LOGIN — UJI SETIAP FITUR")
    print("=" * 66)

    p = LoginPage()
    p.resize(1150, 760)
    p.show()
    jeda(app, 40)

    # ---------------------------------------------- lihat password
    print("\n[Lihat password]")
    p.inp_pass.setText("rahasia123")
    jeda(app, 8)
    cek("Password tersembunyi saat halaman dibuka",
        p.inp_pass.echoMode() == p.inp_pass.EchoMode.Password,
        f"echo={p.inp_pass.echoMode().name}")

    p.btn_lihat.click()
    jeda(app, 8)
    cek("Tombol menampilkan password",
        p.inp_pass.echoMode() == p.inp_pass.EchoMode.Normal
        and p.inp_pass.displayText() == "rahasia123",
        f"teks={p.inp_pass.displayText()!r}")
    cek("Label tombol berubah menjadi Sembunyikan",
        p.btn_lihat.text() == "Sembunyikan", f"dapat {p.btn_lihat.text()!r}")

    p.btn_lihat.click()
    jeda(app, 8)
    cek("Tombol menyembunyikan password kembali",
        p.inp_pass.echoMode() == p.inp_pass.EchoMode.Password
        and p.btn_lihat.text() == "Lihat")

    # -------------------------------------------- ingat pengguna
    print("\n[Ingat nama pengguna]")
    p.inp_user.setText("admin")
    p.chk_ingat.setChecked(True)
    p._simpan_preferensi("admin")
    simpan = db.q1("SELECT value FROM settings WHERE key='last_user'")
    cek("Nama pengguna tersimpan saat dicentang",
        simpan and simpan["value"] == "admin",
        f"dapat {simpan['value']!r}" if simpan else "tidak ada")

    p.chk_ingat.setChecked(False)
    p._simpan_preferensi("admin")
    simpan = db.q1("SELECT value FROM settings WHERE key='last_user'")
    cek("Nama pengguna terhapus saat centang dilepas",
        simpan is None or not simpan["value"],
        f"dapat {simpan['value']!r}" if simpan else "tidak ada")

    # ------------------------------------------------ login gagal
    print("\n[Login gagal]")
    sebelum = len([a for a in sec.recent_audit(50, db.KATEGORI_KEAMANAN)
                   if a["aksi"] == "login.fail"])
    p2 = LoginPage()
    p2.show()
    jeda(app, 20)
    p2.inp_user.setText(config.DEFAULT_ADMIN_USER)
    p2.inp_pass.setText("password-yang-salah")
    p2._login()
    jeda(app, 20)
    cek("Pesan kesalahan ditampilkan", p2.lbl_error.isVisibleTo(p2))
    cek("Pesan menyebut sisa percobaan",
        "Sisa percobaan" in p2.lbl_error.text(),
        f"dapat {p2.lbl_error.text()!r}")
    cek("Hasil login ditandai gagal",
        p2.hasil_terakhir is None or not p2.hasil_terakhir.ok)

    sesudah = len([a for a in sec.recent_audit(50, db.KATEGORI_KEAMANAN)
                   if a["aksi"] == "login.fail"])
    cek("Percobaan gagal tercatat di log keamanan",
        sesudah == sebelum + 1, f"{sebelum} -> {sesudah}")

    # ---------------------------------------------- login berhasil
    print("\n[Login berhasil]")
    p.inp_user.setText(config.DEFAULT_ADMIN_USER)
    p.inp_pass.setText(config.DEFAULT_ADMIN_PASSWORD)
    p.chk_ingat.setChecked(True)
    p._login()
    jeda(app, 20)
    cek("Login dengan kredensial benar berhasil",
        p.hasil_terakhir is not None and p.hasil_terakhir.ok)
    cek("Tidak ada pesan kesalahan setelah berhasil",
        not p.lbl_error.isVisibleTo(p))

    # ------------------------------------------- keterangan akun
    print("\n[Keterangan akun bawaan]")
    db.ex("UPDATE users SET must_change_pw=1 WHERE username=?",
          (config.DEFAULT_ADMIN_USER,))
    p3 = LoginPage()
    p3.show()
    jeda(app, 25)
    cek("Keterangan tampil saat password bawaan belum diganti",
        p3.petunjuk.isVisibleTo(p3))

    db.ex("UPDATE users SET must_change_pw=0 WHERE username=?",
          (config.DEFAULT_ADMIN_USER,))
    p4 = LoginPage()
    p4.show()
    jeda(app, 25)
    cek("Keterangan hilang setelah password diganti",
        not p4.petunjuk.isVisibleTo(p4))

    # kembalikan keadaan awal
    db.ex("UPDATE users SET must_change_pw=1 WHERE username=?",
          (config.DEFAULT_ADMIN_USER,))

    # ------------------------------------------------ keadaan data
    print("\n[Keterangan keadaan data]")
    cek("Jumlah pengguna dan perusahaan ditampilkan",
        "pengguna" in p.lbl_keadaan.text(),
        f"dapat {p.lbl_keadaan.text()!r}")

    # -------------------------------------------------- capslock
    print("\n[Caps Lock]")
    p.inp_pass.setText("abc")
    p._perbarui_capslock()
    nyala = capslock_menyala()
    cek("Peringatan mengikuti keadaan Caps Lock",
        p.lbl_caps.isVisibleTo(p) == nyala,
        f"capslock={nyala}, label={p.lbl_caps.isVisibleTo(p)}")

    print()
    print("=" * 66)
    print(f"HASIL: {LULUS} LULUS, {GAGAL} GAGAL")
    print("=" * 66)
    return 1 if GAGAL else 0


if __name__ == "__main__":
    sys.exit(main())
