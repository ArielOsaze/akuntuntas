"""
Pemburu bug pada perhitungan akuntansi dan persediaan.

Angka yang diuji dihitung manual lebih dulu, lalu dibandingkan dengan hasil
aplikasi. Cara ini menangkap kesalahan logika yang tidak terlihat dari
pembacaan kode: jurnal yang arahnya terbalik, HPP yang salah ambil lapisan,
atau saldo yang tidak ikut berubah.

Jalankan:  python tools/buruh_bug_akuntansi.py
"""

import os
import shutil
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "src"))

DATA = AKAR / "_ujibug_akun"
shutil.rmtree(DATA, ignore_errors=True)
DATA.mkdir(parents=True, exist_ok=True)
os.environ["AKUNTANSIID_DATA"] = str(DATA)

from akuntansi_id import db, services as SV, modules as M, modules_sales as S  # noqa: E402

# Alat ini membuat beberapa perusahaan uji sekaligus, jadi dipakai
# lisensi uji paket Enterprise agar batas multi badan usaha tidak
# menghalangi pengujian.
from akuntansi_id.core.license import Lisensi as _Lisensi
_LISENSI_UJI = _Lisensi(kunci="ATNTUJI", paket="enterprise", fitur={})

lulus = 0
gagal = 0


def cek(hasil, harap, keterangan: str) -> None:
    global lulus, gagal
    if hasil == harap:
        lulus += 1
        print(f"  [LULUS] {keterangan}")
    else:
        gagal += 1
        print(f"  [GAGAL] {keterangan}: dapat {hasil!r}, harusnya {harap!r}")


def saldo(cid: int, kode: str) -> int:
    """Saldo akun: saldo awal + mutasi sesuai sisi normalnya."""
    a = db.q1("SELECT normal, saldo_awal FROM accounts "
              "WHERE company_id=? AND kode=?", (cid, kode))
    if a is None:
        return 0
    d = db.scalar("SELECT COALESCE(SUM(debit),0) FROM journal_lines "
                  "WHERE company_id=? AND kode_akun=?", (cid, kode))
    k = db.scalar("SELECT COALESCE(SUM(kredit),0) FROM journal_lines "
                  "WHERE company_id=? AND kode_akun=?", (cid, kode))
    return a["saldo_awal"] + (d - k if a["normal"] == "Debit" else k - d)


def main() -> int:
    db.init_db()
    cid = SV.create_company("PT Uji Akuntansi", "pt", lisensi=_LISENSI_UJI)

    print("=" * 72)
    print("PEMBURU BUG — PERHITUNGAN AKUNTANSI & PERSEDIAAN")
    print("=" * 72)

    # ============================================ 1. PEMBELIAN BARANG
    print()
    print("[1] Pembelian barang: beli 100 @50.000, jual 10 @80.000 + PPN 11%")
    pid = M.buat_produk(cid, "Kopi", tipe="barang", satuan="kg",
                        harga_beli=50_000, harga_jual=80_000,
                        akun_persediaan="1104", akun_pendapatan="4001",
                        akun_hpp="5001")

    # Pembelian lewat bill: inilah jalur yang membuat jurnal persediaan dan
    # sekaligus menambah stok. stok_masuk saja hanya mengubah kartu stok.
    S.buat_bill(cid, "2026-03-01",
                [{"product_id": pid, "deskripsi": "Kopi", "qty": 100,
                  "harga_satuan": 50_000}],
                vendor="PT Pemasok", jenis="Persediaan",
                jenis_ppn="Non-PKP/Tidak Dipungut",
                user_id=1, username="admin")

    s = M.saldo_stok(cid, pid)
    cek(s["qty"], 100.0, "stok 100 kg")
    cek(s["nilai_total"], 5_000_000, "nilai persediaan Rp5.000.000")
    cek(s["hpp_satuan"], 50_000, "HPP per kg Rp50.000")
    cek(saldo(cid, "1104"), 5_000_000, "jurnal Persediaan Rp5.000.000")

    # jual 10 kg @80.000; PPN 11% dengan DPP nilai lain (11/12)
    S.buat_invoice(cid, "2026-03-05",
                   [{"product_id": pid, "deskripsi": "Kopi", "qty": 10,
                     "harga_satuan": 80_000}],
                   None, jenis_ppn="11%", user_id=1, username="admin")

    print()
    print("  Setelah penjualan 10 kg:")
    s = M.saldo_stok(cid, pid)
    cek(s["qty"], 90.0, "stok berkurang jadi 90 kg")
    cek(s["nilai_total"], 4_500_000, "nilai persediaan jadi Rp4.500.000")

    # HPP = 10 kg x 50.000 = 500.000
    cek(saldo(cid, "5001"), 500_000, "HPP Rp500.000 (10 kg x Rp50.000)")
    cek(saldo(cid, "1104"), 5_000_000 - 500_000,
        "Persediaan berkurang jadi Rp4.500.000")
    cek(saldo(cid, "4001"), 800_000, "Pendapatan Rp800.000")

    # PPN keluaran memakai mekanisme umum 2025+: PPN = 12% x (11/12 x nilai).
    # Faktor 11/12 menghasilkan beban efektif 11%, sesuai PMK 131/2024.
    ppn = db.scalar("""SELECT COALESCE(SUM(jl.kredit),0) FROM journal_lines jl
                       JOIN journal_entries je ON je.id = jl.entry_id
                       WHERE je.company_id=? AND jl.kode_akun='2101'""", (cid,))
    cek(saldo(cid, "1101"), 800_000 + ppn,
        f"Piutang Rp{800_000 + ppn:,} (pendapatan + PPN)")
    cek(ppn, int(round(800_000 * 11 / 12 * 0.12)),
        f"PPN Rp{ppn:,} = 12% x (11/12 x Rp800.000)")

    # ============================================ 2. JURNAL SEIMBANG
    print()
    print("[2] Setiap jurnal seimbang")
    pincang = db.q("""
        SELECT je.no_bukti, SUM(jl.debit) AS d, SUM(jl.kredit) AS k
        FROM journal_entries je JOIN journal_lines jl ON jl.entry_id = je.id
        GROUP BY je.id HAVING d != k
    """)
    cek(len(pincang), 0, f"tidak ada jurnal pincang ({len(pincang)})")

    # ============================================ 3. FIFO
    print()
    print("[3] FIFO: lapisan tertua dipakai lebih dulu")
    cid2 = SV.create_company("PT Uji FIFO", "pt", lisensi=_LISENSI_UJI)
    pid2 = M.buat_produk(cid2, "Barang FIFO", tipe="barang", metode_hpp="fifo",
                         harga_beli=0, harga_jual=0)
    M.stok_masuk(cid2, pid2, 10, 10_000, "2026-01-01")   # lapisan 1
    M.stok_masuk(cid2, pid2, 10, 20_000, "2026-02-01")   # lapisan 2
    s = M.saldo_stok(cid2, pid2)
    cek(s["qty"], 20.0, "stok 20 unit")
    cek(s["nilai_total"], 300_000, "nilai Rp300.000 (10x10rb + 10x20rb)")

    # keluarkan 15 unit: 10 dari lapisan 1 + 5 dari lapisan 2 = 200.000
    M.stok_keluar(cid2, pid2, 15, "2026-03-01")
    s = M.saldo_stok(cid2, pid2)
    cek(s["qty"], 5.0, "stok sisa 5 unit")
    cek(s["nilai_total"], 100_000,
        "nilai sisa Rp100.000 (5 unit dari lapisan Rp20.000)")

    # ============================================ 4. AVERAGE
    print()
    print("[4] Average: harga rata-rata bergerak")
    cid3 = SV.create_company("PT Uji Average", "pt", lisensi=_LISENSI_UJI)
    pid3 = M.buat_produk(cid3, "Barang Average", tipe="barang",
                         metode_hpp="average", harga_beli=0, harga_jual=0)
    M.stok_masuk(cid3, pid3, 10, 10_000, "2026-01-01")
    M.stok_masuk(cid3, pid3, 10, 20_000, "2026-02-01")
    s = M.saldo_stok(cid3, pid3)
    cek(s["hpp_satuan"], 15_000, "HPP rata-rata Rp15.000")
    M.stok_keluar(cid3, pid3, 4, "2026-03-01")
    s = M.saldo_stok(cid3, pid3)
    cek(s["qty"], 16.0, "stok sisa 16 unit")
    cek(s["nilai_total"], 240_000, "nilai sisa Rp240.000 (16 x Rp15.000)")

    # ============================================ 5. JASA TANPA STOK
    print()
    print("[5] Jasa tidak menyentuh persediaan")
    cid4 = SV.create_company("PT Uji Jasa", "pt", lisensi=_LISENSI_UJI)
    jasa = M.buat_produk(cid4, "Konsultasi", tipe="jasa",
                         harga_jual=5_000_000)
    S.buat_invoice(cid4, "2026-03-01",
                   [{"product_id": jasa, "deskripsi": "Konsultasi",
                     "qty": 1, "harga_satuan": 5_000_000}],
                   None, jenis_ppn="Non-PKP/Tidak Dipungut",
                   user_id=1, username="admin")
    gerak = db.scalar("SELECT COUNT(*) FROM stock_movements WHERE product_id=?",
                      (jasa,))
    cek(gerak, 0, "tidak ada pergerakan stok untuk jasa")
    hpp = db.scalar("""SELECT COALESCE(SUM(jl.debit),0) FROM journal_lines jl
                       JOIN journal_entries je ON je.id = jl.entry_id
                       WHERE je.company_id=? AND jl.kode_akun LIKE '5%'""",
                    (cid4,))
    cek(hpp, 0, "tidak ada HPP untuk jasa")

    # ============================================ 6. PEMBULATAN
    print()
    print("[6] Pembulatan pajak tidak menghasilkan pecahan")
    cid5 = SV.create_company("PT Uji Bulat", "pt", lisensi=_LISENSI_UJI)
    S.buat_invoice(cid5, "2026-03-01",
                   [{"deskripsi": "Barang", "qty": 3, "harga_satuan": 33_333}],
                   None, jenis_ppn="11%", user_id=1, username="admin")
    for baris in db.q("""SELECT jl.debit, jl.kredit FROM journal_lines jl
                         JOIN journal_entries je ON je.id = jl.entry_id
                         WHERE je.company_id=?""", (cid5,)):
        if not isinstance(baris["debit"], int) or not isinstance(baris["kredit"], int):
            cek(False, True, "nilai jurnal harus bilangan bulat rupiah")
            break
    else:
        cek(True, True, "seluruh nilai jurnal bilangan bulat rupiah")

    print()
    print("=" * 72)
    if gagal == 0:
        print(f"HASIL: {lulus} LULUS, 0 GAGAL — perhitungan akuntansi benar")
    else:
        print(f"HASIL: {lulus} LULUS, {gagal} GAGAL")
    print("=" * 72)

    shutil.rmtree(DATA, ignore_errors=True)
    return 1 if gagal else 0


if __name__ == "__main__":
    sys.exit(main())
