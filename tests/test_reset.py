"""
Uji reset data usaha.

Reset dipakai saat aplikasi dialihkan ke perusahaan lain, atau saat data
percobaan dibersihkan sebelum dipakai sungguhan. Yang diuji di sini:
transaksi terhapus, profil perusahaan dan bagan akun tetap ada, cadangan
pengaman dibuat, dan nomor dokumen dimulai ulang dari satu.
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "src"))

DATA = AKAR / "_ujireset"
if DATA.exists():
    shutil.rmtree(DATA, ignore_errors=True)
DATA.mkdir(parents=True, exist_ok=True)
os.environ["AKUNTANSIID_DATA"] = str(DATA)

from akuntansi_id import db, modules as M, modules_sales as S   # noqa: E402
from akuntansi_id.core import reset as rst                       # noqa: E402

lulus = 0
gagal = 0


def cek(syarat: bool, keterangan: str) -> None:
    global lulus, gagal
    if syarat:
        lulus += 1
        print(f"  [LULUS] {keterangan}")
    else:
        gagal += 1
        print(f"  [GAGAL] {keterangan}")


def main() -> int:
    db.init_db()

    # Siapkan seperti aplikasi baru dipasang: pengguna bawaan dan perusahaan
    # dengan bagan akun lengkap, supaya dapat dibuktikan keduanya bertahan
    # setelah reset.
    from akuntansi_id.core import security as sec
    from akuntansi_id import services as SV

    sec.ensure_default_admin()
    cid = SV.create_company("PT Uji Reset", "pt", npwp="0123456789012345")

    # ---------------------------------------------------- siapkan data
    M.buat_mitra(cid, "PT Pelanggan Utama", "customer")
    M.buat_mitra(cid, "CV Pemasok Jaya", "vendor")
    pid = M.buat_produk(cid, "Kopi Arabika", tipe="barang",
                        harga_beli=50_000, harga_jual=80_000)
    M.stok_masuk(cid, pid, 100, 50_000, "2026-03-01", no_ref="PO-001")
    S.buat_invoice(cid, "2026-03-05",
                   [{"product_id": pid, "deskripsi": "Kopi Arabika",
                     "qty": 10, "harga_satuan": 80_000}],
                   None, jenis_ppn="11%", user_id=1, username="admin")

    print("[Data disiapkan]")
    sebelum = rst.ringkasan(cid)
    cek(sebelum["mitra"] == 2, "dua mitra tercatat")
    cek(sebelum["produk"] == 1, "satu produk tercatat")
    cek(sebelum["jurnal"] >= 1, "jurnal tercatat")

    # ---------------------------------------------------- jalankan reset
    print()
    print("[Reset dijalankan]")
    hasil = rst.reset_data(cid, user_id=1, username="admin")
    cek(hasil["jumlah_baris"] > 0, f"{hasil['jumlah_baris']} baris terhapus")
    cek(hasil["berkas_cadangan"].exists(),
        f"cadangan pengaman dibuat: {hasil['berkas_cadangan'].name}")

    # ---------------------------------------------------- sesudah reset
    print()
    print("[Sesudah reset]")
    sesudah = rst.ringkasan(cid)
    cek(sesudah["mitra"] == 0, "mitra terhapus")
    cek(sesudah["produk"] == 0, "produk terhapus")
    cek(sesudah["penjualan"] == 0, "penjualan terhapus")
    cek(sesudah["jurnal"] == 0, "jurnal terhapus")

    # yang harus TETAP ada
    cek(db.scalar("SELECT COUNT(*) FROM companies WHERE id=?", (cid,)) == 1,
        "profil perusahaan tetap ada")
    cek(db.scalar("SELECT COUNT(*) FROM users") >= 1,
        "pengguna tetap ada")
    cek(db.scalar("SELECT COUNT(*) FROM accounts WHERE company_id=?",
                  (cid,)) > 0,
        "bagan akun tetap ada")

    # stok ikut bersih
    cek(db.scalar("SELECT COUNT(*) FROM stock_balances WHERE company_id=?",
                  (cid,)) == 0, "saldo stok ikut terhapus")

    # nomor dokumen dimulai ulang
    cek(db.scalar("SELECT COUNT(*) FROM number_sequences WHERE company_id=?",
                  (cid,)) == 0, "nomor dokumen dimulai ulang")

    # ---------------------------------------------------- cadangan bisa dipulihkan
    print()
    print("[Cadangan pengaman dapat dipulihkan]")
    db.pulihkan_dari_cadangan(hasil["berkas_cadangan"])
    kembali = rst.ringkasan(cid)
    cek(kembali["mitra"] == 2, "mitra kembali setelah pemulihan")
    cek(kembali["produk"] == 1, "produk kembali setelah pemulihan")
    cek(kembali["jurnal"] >= 1, "jurnal kembali setelah pemulihan")

    # ---------------------------------------------------- reset perusahaan kosong
    print()
    print("[Reset pada perusahaan tanpa data]")
    db.ex("INSERT INTO companies(nama,bentuk) VALUES('PT Kosong','pt')")
    cid2 = db.scalar("SELECT id FROM companies WHERE nama='PT Kosong'")
    kosong = rst.ringkasan(cid2)
    cek(sum(kosong.values()) == 0, "perusahaan tanpa data tidak punya apa pun")

    print()
    print("=" * 66)
    if gagal == 0:
        print(f"HASIL: {lulus} LULUS, 0 GAGAL — reset data bekerja")
    else:
        print(f"HASIL: {lulus} LULUS, {gagal} GAGAL")
    print("=" * 66)

    shutil.rmtree(DATA, ignore_errors=True)
    return 1 if gagal else 0


if __name__ == "__main__":
    sys.exit(main())
