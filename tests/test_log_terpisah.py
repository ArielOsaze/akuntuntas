"""
Uji pemisahan jejak audit dari log keamanan.

Jejak audit memuat dua hal berbeda: aktivitas keamanan (masuk dan keluar
aplikasi) dan aktivitas pekerjaan (perubahan data pembukuan). Keduanya
disimpan dalam satu tabel dengan kolom kategori, lalu ditampilkan pada tab
terpisah.

Yang diperiksa di sini:
  1. Kategori ditentukan dengan benar untuk setiap jenis aksi.
  2. Pencatatan masuk dan keluar aplikasi masuk ke kategori keamanan.
  3. Penyaringan per kategori benar-benar memisahkan keduanya.
  4. Aksi yang tercatat selalu punya label Indonesia, tidak tampil mentah.

Cara pakai:
    python tests/test_log_terpisah.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "src"))
os.environ.setdefault("AKUNTANSIID_DATA", str(AKAR / "_contoh"))

from akuntansi_id import db, istilah
from akuntansi_id.core import security as sec

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
    print("=" * 66)
    print("PEMISAHAN JEJAK AUDIT DAN LOG KEAMANAN")
    print("=" * 66)

    # ---------------------------------------------------- kategori aksi
    print("\n[Kategori aksi]")
    for aksi, diharap in (
            ("login.success", db.KATEGORI_KEAMANAN),
            ("login.fail", db.KATEGORI_KEAMANAN),
            ("login.locked", db.KATEGORI_KEAMANAN),
            ("logout", db.KATEGORI_KEAMANAN),
            ("journal.create", db.KATEGORI_DATA),
            ("sale.delete", db.KATEGORI_DATA),
            ("purchase.create", db.KATEGORI_DATA),
            ("asset.depreciate", db.KATEGORI_DATA),
            ("user.create", db.KATEGORI_ADMIN),
            ("user.reset_password", db.KATEGORI_ADMIN),
            ("company.update", db.KATEGORI_ADMIN)):
        dapat = db.kategori_aksi(aksi)
        cek(f"{aksi} tergolong {diharap}", dapat == diharap, f"dapat {dapat}")

    # -------------------------------------------------- catat & saring
    print("\n[Pencatatan dan penyaringan]")
    sebelum = sec.hitung_per_kategori()

    db.log_login("penguji", True, 1, "Berhasil masuk aplikasi.")
    db.log_login("penguji", False, 1, "Password salah.")
    db.log_login("penyusup", False, None, "Nama pengguna tidak dikenal.")
    sec.logout(1, "penguji")
    db.log_action(1, "penguji", 1, "journal.create", "journal_entries", "1",
                  "Jurnal uji dibuat.")

    sesudah = sec.hitung_per_kategori()
    cek("Percobaan masuk menambah log keamanan",
        sesudah[db.KATEGORI_KEAMANAN] == sebelum[db.KATEGORI_KEAMANAN] + 4,
        f"{sebelum[db.KATEGORI_KEAMANAN]} -> {sesudah[db.KATEGORI_KEAMANAN]}")
    cek("Perubahan data menambah log data",
        sesudah[db.KATEGORI_DATA] == sebelum[db.KATEGORI_DATA] + 1,
        f"{sebelum[db.KATEGORI_DATA]} -> {sesudah[db.KATEGORI_DATA]}")

    keamanan = sec.recent_audit(200, db.KATEGORI_KEAMANAN)
    data = sec.recent_audit(200, db.KATEGORI_DATA)
    admin = sec.recent_audit(200, db.KATEGORI_ADMIN)
    semua = sec.recent_audit(200)

    cek("Log keamanan hanya berisi aksi masuk dan keluar",
        all(a["aksi"] in db.AKSI_KEAMANAN for a in keamanan),
        f"aksi: {sorted({a['aksi'] for a in keamanan})}")
    cek("Log data tidak memuat aksi masuk dan keluar",
        not any(a["aksi"] in db.AKSI_KEAMANAN for a in data))
    cek("Log administrasi tidak memuat aksi masuk dan keluar",
        not any(a["aksi"] in db.AKSI_KEAMANAN for a in admin))
    cek("Log keamanan mencatat sumber komputer",
        all(a["sumber"] for a in keamanan),
        "ada catatan tanpa sumber")
    # Ketiga kategori harus mencakup seluruh catatan pada rentang yang sama.
    # Perbandingan memakai id baris, bukan penjumlahan, karena `recent_audit`
    # membatasi jumlah baris per panggilan. Menjumlahkan hasil tiga kategori
    # dengan batas 200 masing-masing dapat melebihi jumlah hasil tanpa
    # kategori yang juga dibatasi 200.
    id_terpisah = {a["id"] for a in (keamanan + data + admin)}
    id_semua = {a["id"] for a in semua}
    cek("Seluruh catatan terbagi ke dalam tiga kategori",
        id_semua.issubset(id_terpisah),
        f"{len(id_semua - id_terpisah)} catatan tidak masuk kategori mana pun")
    cek("Tidak ada catatan yang masuk dua kategori",
        len(id_terpisah) == len(keamanan) + len(data) + len(admin),
        f"{len(keamanan) + len(data) + len(admin) - len(id_terpisah)} "
        "catatan ganda")

    # ------------------------------------------------------- label aksi
    print("\n[Label aksi]")
    aksi_terpakai = sorted({a["aksi"] for a in semua})
    mentah = [a for a in aksi_terpakai if istilah.label("action", a) == a]
    cek("Seluruh aksi yang tercatat punya label Indonesia",
        not mentah, f"masih mentah: {mentah}")

    for aksi, diharap in (
            ("login.success", "Masuk aplikasi"),
            ("login.fail", "Gagal masuk"),
            ("logout", "Keluar aplikasi"),
            ("asset.create", "Aset dibuat"),
            ("sale.create", "Penjualan dibuat"),
            ("purchase.delete", "Pembelian dihapus"),
            ("tax.payment", "Pembayaran pajak dicatat"),
            ("payroll.calculate", "Payroll dihitung"),
            ("user.reset_password", "Password direset")):
        dapat = istilah.label("action", aksi)
        cek(f"Label {aksi}", dapat == diharap, f"dapat {dapat!r}")

    print()
    print("=" * 66)
    print(f"HASIL: {LULUS} LULUS, {GAGAL} GAGAL")
    print("=" * 66)
    return 1 if GAGAL else 0


if __name__ == "__main__":
    sys.exit(main())
