"""
Uji migrasi basis data dari versi lama.

Bug yang dijaga di sini pernah terjadi: kolom baru dipakai oleh index dan view
yang dibuat SEBELUM migrasi menambahkan kolomnya. Pada basis data lama,
perintah itu gagal dan kegagalannya membatalkan pembukaan aplikasi — pengguna
tidak bisa masuk sama sekali.

Yang diperiksa:
  1. Basis data lama dapat dibuka tanpa kesalahan.
  2. Kolom baru benar-benar ditambahkan.
  3. Index yang bergantung pada kolom baru ikut dibuat.
  4. View yang membaca kolom baru dapat dipakai.
  5. Data lama tidak hilang.

Cara pakai:
    python tests/test_migrasi_lama.py
"""
from __future__ import annotations

import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "src"))

# Kolom yang ditambahkan setelah versi awal, beserta tabelnya. Uji ini
# menurunkan basis data dengan membuang kolom-kolom ini agar menyerupai
# basis data yang dibuat versi lama.
KOLOM_BARU = [
    ("kontrak", "nilai_jasa"),
    ("audit_log", "kategori"),
]

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


def bangun_basis_data_lama(folder: Path) -> None:
    """Bangun basis data dengan skema terbaru, lalu turunkan ke versi lama."""
    env = dict(os.environ, AKUNTANSIID_DATA=str(folder))
    subprocess.run(
        [sys.executable, "-c",
         "import sys; sys.path.insert(0, r'%s'); "
         "from akuntansi_id import db; db.init_db()" % str(AKAR / "src")],
        cwd=str(AKAR), env=env, check=True,
        capture_output=True, text=True, timeout=180)

    conn = sqlite3.connect(folder / "akuntuntas.db")
    conn.execute("DROP VIEW IF EXISTS v_kontrak_aktif")
    conn.execute("DROP INDEX IF EXISTS idx_audit_kategori")
    for tabel, kolom in KOLOM_BARU:
        try:
            conn.execute(f"ALTER TABLE {tabel} DROP COLUMN {kolom}")
        except sqlite3.OperationalError:
            pass
    conn.commit()
    conn.close()


def main() -> int:
    print("=" * 66)
    print("MIGRASI BASIS DATA DARI VERSI LAMA")
    print("=" * 66)

    folder = Path(tempfile.mkdtemp(prefix="akuntuntas_lama_"))
    try:
        print("\n[Menyiapkan basis data versi lama]")
        bangun_basis_data_lama(folder)

        conn = sqlite3.connect(folder / "akuntuntas.db")
        kol_k = [r[1] for r in conn.execute("PRAGMA table_info(kontrak)")]
        kol_a = [r[1] for r in conn.execute("PRAGMA table_info(audit_log)")]
        conn.close()
        cek("Basis data uji benar-benar tanpa nilai_jasa",
            "nilai_jasa" not in kol_k)
        cek("Basis data uji benar-benar tanpa kategori",
            "kategori" not in kol_a)

        # ---------------------------------------------------- buka lama
        print("\n[Membuka basis data lama dengan versi terbaru]")
        env = dict(os.environ, AKUNTANSIID_DATA=str(folder))
        hasil = subprocess.run(
            [sys.executable, "-c",
             "import sys; sys.path.insert(0, r'%s'); "
             "from akuntansi_id import db; db.init_db(); "
             "print('OK')" % str(AKAR / "src")],
            cwd=str(AKAR), env=env, capture_output=True, text=True, timeout=180)
        keluaran = hasil.stdout + hasil.stderr

        cek("Basis data lama dapat dibuka tanpa kesalahan",
            hasil.returncode == 0 and "OK" in hasil.stdout,
            f"keluar={hasil.returncode}: {keluaran.strip()[-200:]}")
        cek("Tidak ada kesalahan kolom tidak ditemukan",
            "no such column" not in keluaran,
            keluaran.strip()[-200:])

        # -------------------------------------------------- kolom baru
        print("\n[Kolom baru ditambahkan]")
        conn = sqlite3.connect(folder / "akuntuntas.db")
        conn.row_factory = sqlite3.Row
        kol_k = [r[1] for r in conn.execute("PRAGMA table_info(kontrak)")]
        kol_a = [r[1] for r in conn.execute("PRAGMA table_info(audit_log)")]
        cek("Kolom nilai_jasa ditambahkan", "nilai_jasa" in kol_k)
        cek("Kolom kategori ditambahkan", "kategori" in kol_a)

        # ------------------------------------------------------ index
        print("\n[Index dan view]")
        idx = conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='index' "
            "AND name='idx_audit_kategori'").fetchone()[0]
        cek("Index kategori dibuat", idx == 1)

        view = conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='view' "
            "AND name='v_kontrak_aktif'").fetchone()[0]
        cek("View kontrak dibuat ulang", view == 1)

        try:
            conn.execute("SELECT nilai_total FROM v_kontrak_aktif LIMIT 1")
            bisa = True
        except sqlite3.OperationalError:
            bisa = False
        cek("View dapat membaca kolom nilai gabungan", bisa)

        # -------------------------------------------------- data lama
        print("\n[Data lama tetap utuh]")
        tabel = conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
        ).fetchone()[0]
        cek("Seluruh tabel ada", tabel >= 70, f"dapat {tabel} tabel")

        # Daftar izin harus terisi. Bila urutan pemuatan skema salah, tabel
        # permissions belum ada saat pengisian dijalankan sehingga dialog hak
        # akses pengguna tampil kosong tanpa satu pun pilihan.
        jumlah_izin = conn.execute(
            "SELECT COUNT(*) FROM permissions").fetchone()[0]
        cek("Daftar izin terisi", jumlah_izin > 0, f"dapat {jumlah_izin} izin")
        jumlah_peran = conn.execute(
            "SELECT COUNT(*) FROM role_permissions").fetchone()[0]
        cek("Izin bawaan peran terisi", jumlah_peran > 0,
            f"dapat {jumlah_peran} pemetaan")

        # View inti harus ada supaya laporan tetap bisa dibuka.
        for nama_view in ("v_kontrak_aktif", "v_account_balances"):
            ada = conn.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='view' "
                "AND name=?", (nama_view,)).fetchone()[0]
            cek(f"View {nama_view} ada", ada == 1)

        try:
            conn.execute("INSERT INTO audit_log(ts, username, action, detail) "
                         "VALUES('2026-01-01 00:00:00','uji','login.success','')")
            conn.commit()
            r = conn.execute("SELECT kategori FROM audit_log "
                             "WHERE username='uji'").fetchone()
            cek("Catatan baru memakai kategori bawaan 'data'",
                r is not None and r["kategori"] == "data",
                f"dapat {r['kategori'] if r else None}")
        except sqlite3.Error as e:
            cek("Catatan baru dapat disimpan", False, str(e))
        conn.close()

        # ------------------------------------------- buka kedua kalinya
        print("\n[Membuka ulang untuk memastikan idempoten]")
        hasil2 = subprocess.run(
            [sys.executable, "-c",
             "import sys; sys.path.insert(0, r'%s'); "
             "from akuntansi_id import db; db.init_db(); "
             "print('OK')" % str(AKAR / "src")],
            cwd=str(AKAR), env=env, capture_output=True, text=True, timeout=180)
        cek("Pembukaan kedua tetap berhasil",
            hasil2.returncode == 0 and "OK" in hasil2.stdout,
            (hasil2.stdout + hasil2.stderr).strip()[-200:])
    finally:
        shutil.rmtree(folder, ignore_errors=True)

    print()
    print("=" * 66)
    print(f"HASIL: {LULUS} LULUS, {GAGAL} GAGAL")
    print("=" * 66)
    return 1 if GAGAL else 0


if __name__ == "__main__":
    sys.exit(main())
