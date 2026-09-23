"""
Uji cadangan dan pemulihan data.

Alur yang diuji meniru keadaan sebenarnya saat aplikasi dijual ke klien:
pengguna mengerjakan pembukuan, mencadangkan datanya, memasang pembaruan
aplikasi, lalu memulihkan datanya kembali.

Yang diperiksa:
  1. Cadangan dibuat dan berisi seluruh data.
  2. Data yang berubah setelah pencadangan benar-benar berbeda.
  3. Pemulihan mengembalikan data persis seperti saat dicadangkan.
  4. Pemulihan langsung berlaku tanpa perlu menutup aplikasi.
  5. Keadaan sebelum pemulihan disimpan sebagai cadangan pengaman sehingga
     pemulihan yang salah pilih masih bisa dibatalkan.
  6. Cadangan dapat dipulihkan dari lokasi mana pun, bukan hanya folder
     cadangan bawaan.

Cara pakai:
    python tests/test_backup_restore.py
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "src"))

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
    print("CADANGAN DAN PEMULIHAN DATA")
    print("=" * 66)

    folder = Path(tempfile.mkdtemp(prefix="akuntuntas_backup_"))
    os.environ["AKUNTANSIID_DATA"] = str(folder)

    from akuntansi_id import db

    db.init_db()

    # ------------------------------------------------------ siapkan data
    print("\n[Menyiapkan data awal]")
    db.ex("INSERT INTO companies(nama, bentuk) VALUES('PT Sinar Abadi','pt')")
    cid = db.scalar("SELECT id FROM companies WHERE nama='PT Sinar Abadi'")
    for i in range(5):
        db.ex("INSERT INTO accounts(company_id, kode, nama, tipe, normal) "
              "VALUES(?,?,?,'aset','debit')",
              (cid, f"1-{i:04d}", f"Akun {i}"))
    for i in range(4):
        db.ex("INSERT INTO journal_entries(company_id, tanggal, no_bukti, "
              "keterangan) VALUES(?,?,?,?)",
              (cid, f"2026-01-{i + 1:02d}", f"J-{i + 1}", f"Transaksi {i + 1}"))

    akun_awal = db.scalar(f"SELECT COUNT(*) FROM accounts WHERE company_id={cid}")
    jurnal_awal = db.scalar(
        f"SELECT COUNT(*) FROM journal_entries WHERE company_id={cid}")
    cek("Data awal siap", akun_awal == 5 and jurnal_awal == 4,
        f"akun={akun_awal}, jurnal={jurnal_awal}")

    # -------------------------------------------------------- mencadangkan
    print("\n[Mencadangkan data]")
    cadangan = db.create_backup("Cadangan sebelum pembaruan")
    cek("Berkas cadangan dibuat", cadangan.exists(), f"di {cadangan}")
    cek("Berkas cadangan berisi data",
        cadangan.stat().st_size > 10_000,
        f"{cadangan.stat().st_size:,} byte")
    cek("Cadangan tercatat di daftar", db.cadangan_terakhir() is not None)

    # ---------------------------------------------- mengubah data
    print("\n[Mengubah data setelah pencadangan]")
    db.ex("INSERT INTO accounts(company_id, kode, nama, tipe, normal) "
          "VALUES(?,'2-0000','Akun Baru','aset','debit')", (cid,))
    db.ex("DELETE FROM journal_entries WHERE company_id=? AND no_bukti='J-1'",
          (cid,))
    db.ex("INSERT INTO companies(nama, bentuk) VALUES('PT Lain','pt')")

    akun_ubah = db.scalar(f"SELECT COUNT(*) FROM accounts WHERE company_id={cid}")
    jurnal_ubah = db.scalar(
        f"SELECT COUNT(*) FROM journal_entries WHERE company_id={cid}")
    perusahaan_ubah = db.scalar("SELECT COUNT(*) FROM companies")
    cek("Data benar-benar berubah setelah pencadangan",
        akun_ubah != akun_awal or jurnal_ubah != jurnal_awal,
        f"akun {akun_awal}->{akun_ubah}, jurnal {jurnal_awal}->{jurnal_ubah}")
    cek("Perusahaan tambahan tercatat sebelum pemulihan",
        perusahaan_ubah == 2, f"dapat {perusahaan_ubah}")

    # ------------------------------------------------------- memulihkan
    print("\n[Memulihkan dari cadangan]")
    hasil = db.pulihkan_dari_cadangan(cadangan)
    cek("Pemulihan melaporkan isi data",
        hasil["perusahaan"] == 1 and hasil["jurnal"] == 4,
        f"perusahaan={hasil['perusahaan']}, jurnal={hasil['jurnal']}")

    akun_pulih = db.scalar(f"SELECT COUNT(*) FROM accounts WHERE company_id={cid}")
    jurnal_pulih = db.scalar(
        f"SELECT COUNT(*) FROM journal_entries WHERE company_id={cid}")
    perusahaan_pulih = db.scalar("SELECT COUNT(*) FROM companies")
    nama_pulih = db.scalar("SELECT nama FROM companies LIMIT 1")

    cek("Jumlah akun kembali seperti semula", akun_pulih == akun_awal,
        f"{akun_pulih} != {akun_awal}")
    cek("Jumlah jurnal kembali seperti semula", jurnal_pulih == jurnal_awal,
        f"{jurnal_pulih} != {jurnal_awal}")
    cek("Perusahaan yang ditambah setelah cadangan hilang",
        perusahaan_pulih == 1, f"dapat {perusahaan_pulih}")
    cek("Nama perusahaan kembali benar", nama_pulih == "PT Sinar Abadi",
        f"dapat {nama_pulih!r}")

    j1 = db.scalar(f"SELECT COUNT(*) FROM journal_entries "
                   f"WHERE company_id={cid} AND no_bukti='J-1'")
    cek("Jurnal yang terhapus kembali ada", j1 == 1)
    akun_baru = db.scalar(f"SELECT COUNT(*) FROM accounts "
                          f"WHERE company_id={cid} AND kode='2-0000'")
    cek("Akun yang ditambah setelah cadangan hilang", akun_baru == 0)

    # --------------------------------------- langsung berlaku tanpa restart
    print("\n[Pemulihan langsung berlaku]")
    cek("Koneksi basis data masih dapat dipakai setelah pemulihan",
        db.scalar("SELECT COUNT(*) FROM companies") == 1)

    # ------------------------------------------------ cadangan pengaman
    print("\n[Cadangan pengaman]")
    cek("Keadaan sebelum pemulihan dicadangkan",
        hasil["cadangan_pengaman"] is not None
        and hasil["cadangan_pengaman"].exists(),
        "tidak ada cadangan pengaman")

    # -------------------------------------------- pulihkan dari lokasi lain
    print("\n[Memulihkan dari lokasi lain]")
    luar = folder / "cadangan_di_luar"
    luar.mkdir(exist_ok=True)
    salinan = luar / "cadangan_client.db"
    shutil.copy2(cadangan, salinan)
    db.ex("DELETE FROM accounts")
    cek("Data terhapus sebelum uji", db.scalar("SELECT COUNT(*) FROM accounts") == 0)
    db.pulihkan_dari_cadangan(salinan)
    cek("Cadangan dari lokasi lain dapat dipulihkan",
        db.scalar("SELECT COUNT(*) FROM accounts") == akun_awal,
        f"dapat {db.scalar('SELECT COUNT(*) FROM accounts')}")

    shutil.rmtree(folder, ignore_errors=True)

    print()
    print("=" * 66)
    print(f"HASIL: {LULUS} LULUS, {GAGAL} GAGAL")
    print("=" * 66)
    return 1 if GAGAL else 0


if __name__ == "__main__":
    sys.exit(main())
