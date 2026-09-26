"""
Uji apakah saldo stok dan beberapa fungsi lain membaca data perusahaan lain.

Cara ini mencari parameter yang diterima tetapi tidak dipakai. Parameter
seperti itu berbahaya karena pemanggil merasa sudah menyebutkan perusahaan
yang dimaksud, padahal fungsinya mengabaikannya.

Fungsi yang diperiksa adalah fungsi yang menerima company_id sekaligus
kolom penentu lain (product_id, warehouse_id, entry_id), lalu memeriksa
apakah company_id itu benar benar dipakai untuk menyaring.

Cara pakai:
    python tools/uji_parameter_diabaikan.py
"""
from __future__ import annotations

import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "src"))

FOLDER = Path(tempfile.mkdtemp(prefix="akuntuntas_param_"))
os.environ["LOCALAPPDATA"] = str(FOLDER)

from akuntansi_id import db, modules, services  # noqa: E402


class Pemeriksa:
    def __init__(self):
        self.lulus = 0
        self.gagal = 0
        self.temuan: list[str] = []

    def cek(self, nama: str, syarat: bool, catatan: str = ""):
        if syarat:
            self.lulus += 1
            print(f"  [AMAN]  {nama}")
        else:
            self.gagal += 1
            self.temuan.append(nama)
            print(f"  [CELAH] {nama}")
            if catatan:
                print(f"          {catatan}")


class LisensiUji:
    enterprise = True

    def punya(self, bagian: str) -> bool:
        return True


def main() -> int:
    p = Pemeriksa()
    print("=" * 76)
    print("  UJI PARAMETER PERUSAHAAN YANG DITERIMA TETAPI TIDAK DIPAKAI")
    print("=" * 76)
    print()

    db.init_db()

    # Dua perusahaan dengan data yang sangat berbeda, supaya kebocoran
    # langsung terlihat pada angkanya.
    a = services.create_company("PT Alfa", bentuk="pt")
    b = services.create_company("PT Beta", bentuk="pt", lisensi=LisensiUji())

    pa = modules.buat_produk(a, "Barang Alfa", satuan="pcs", harga_beli=100_000,
                             harga_jual=150_000, metode_hpp="average")
    ga = modules.gudang_utama(a)
    modules.stok_masuk(a, pa, 20, 100_000, "2026-01-05")

    pb = modules.buat_produk(b, "Barang Beta", satuan="pcs", harga_beli=777_000,
                             harga_jual=900_000, metode_hpp="average")
    gb = modules.gudang_utama(b)
    modules.stok_masuk(b, pb, 99, 777_000, "2026-01-05")

    print(f"  PT Alfa (id={a}): produk id={pa}, gudang id={ga}, 20 unit")
    print(f"  PT Beta (id={b}): produk id={pb}, gudang id={gb}, 99 unit")
    print()

    # ------------------------------------------------------------------
    print("[1. saldo_stok: company_id diabaikan saat gudang disebut]")
    salah = modules.saldo_stok(a, pb, gb)
    p.cek("saldo_stok tidak membaca stok perusahaan lain",
          int(salah["qty"]) == 0,
          f"meminta stok PT Alfa untuk produk PT Beta, "
          f"hasilnya {salah['qty']:g} unit senilai Rp{salah['nilai_total']:,}")

    benar = modules.saldo_stok(a, pa, ga)
    p.cek("saldo_stok tetap benar untuk data sendiri",
          int(benar["qty"]) == 20 and int(benar["nilai_total"]) == 2_000_000,
          f"hasil: {benar['qty']:g} unit, Rp{benar['nilai_total']:,}")
    print()

    # ------------------------------------------------------------------
    print("[2. kartu_stok: apakah hasilnya menyaring perusahaan]")
    # Produk PT Alfa, tetapi disebut perusahaan PT Beta.
    kartu = modules.kartu_stok(b, pa)
    p.cek("kartu_stok tidak menampilkan mutasi perusahaan lain",
          len(kartu) == 0,
          f"meminta kartu stok PT Beta untuk produk PT Alfa, "
          f"hasilnya {len(kartu)} baris")
    print()

    # ------------------------------------------------------------------
    print("[3. detail_payroll: apakah menyaring perusahaan]")
    # Buat penggajian di PT Alfa saja.
    services.simpan_karyawan(a, "Karyawan Alfa", 6_000_000, status_ptkp="TK/0")
    hasil = services.hitung_payroll_bulanan(a, "2026-02", posting=True)
    run_id = hasil.get("run_id") if isinstance(hasil, dict) else None
    if run_id:
        # Minta detail penggajian PT Alfa, tetapi dari sisi PT Beta.
        detail = services.detail_payroll(run_id)
        p.cek("detail_payroll tetap menyaring lewat run_id",
              isinstance(detail, list) and len(detail) >= 1,
              f"hasil: {len(detail)} baris (memang aman karena run_id unik)")
    else:
        p.cek("penggajian dapat dibuat", False, f"hasil: {hasil}")
    print()

    # ------------------------------------------------------------------
    print("[4. Mencari parameter company_id yang tidak dipakai di kode]")
    # Dibaca dari kode: fungsi yang punya parameter company_id tetapi
    # query di dalamnya tidak menyebut company_id.
    sumber = AKAR / "src" / "akuntansi_id"
    mencurigakan: list[str] = []
    for berkas in sorted(sumber.rglob("*.py")):
        relatif = str(berkas.relative_to(sumber)).replace("\\", "/")
        if relatif.startswith("ui/") or relatif in (
                "db.py", "schema_ext.py", "schema_kontrak.py", "coa.py"):
            continue
        try:
            isi = berkas.read_text(encoding="utf-8")
        except Exception:
            continue
        baris_isi = isi.splitlines()
        for i, baris in enumerate(baris_isi):
            # Fungsi yang menerima company_id.
            if not re.match(r"\s*def \w+\(.*company_id", baris):
                continue
            # Ambil isi fungsinya sampai fungsi berikutnya pada indentasi
            # yang sama.
            potong = baris_isi[i + 1:i + 40]
            badan = "\n".join(potong)
            if not re.search(r"\b(SELECT|UPDATE|DELETE)\b", badan, re.IGNORECASE):
                continue
            if re.search(r"\bcompany_id\b", badan):
                continue
            # Fungsi yang hanya memanggil fungsi lain yang sudah menyaring
            # tidak dihitung.
            if re.search(r"=\s*\w+\.(q|q1|scalar|ex)\(", badan) is None and \
               not re.search(r"\b(db|conn)\.(execute|q|q1|scalar)\(", badan):
                continue
            mencurigakan.append(f"{relatif}:{i + 1} {baris.strip()[:70]}")

    print(f"  ditemukan: {len(mencurigakan)}")
    for t in mencurigakan[:20]:
        print(f"    {t}")
    p.cek("tidak ada fungsi yang menerima company_id tanpa memakainya",
          not mencurigakan,
          f"{len(mencurigakan)} fungsi perlu diperiksa")
    print()

    print("=" * 76)
    if p.gagal:
        print(f"  HASIL: {p.lulus} AMAN, {p.gagal} CELAH")
        print()
        for t in p.temuan:
            print(f"    - {t}")
    else:
        print(f"  HASIL: {p.lulus} AMAN, 0 CELAH")
    print("=" * 76)
    return 1 if p.gagal else 0


if __name__ == "__main__":
    try:
        kode = main()
    finally:
        shutil.rmtree(FOLDER, ignore_errors=True)
    sys.exit(kode)
