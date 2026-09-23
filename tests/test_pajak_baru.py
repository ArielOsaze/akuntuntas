"""Uji perhitungan fitur pajak baru: PPh 15, Bea Meterai, PBJT, dan kurs."""

import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "src"))

from akuntansi_id.core import tax_engine as tx  # noqa: E402

GAGAL = []


def cek(nama, hasil, harap):
    benar = hasil == harap
    print(f"  {'LULUS' if benar else 'GAGAL'}  {nama}: {hasil} "
          f"{'' if benar else f'(harap {harap})'}")
    if not benar:
        GAGAL.append(nama)


print("=== PPh Pasal 15 ===")
r = tx.hitung_pph15("pelayaran_dalam", 1_000_000_000)
cek("pelayaran dalam 1 M", r["pph_terutang"], 13_500_000)
r = tx.hitung_pph15("pelayaran_luar", 1_000_000_000)
cek("pelayaran luar 1 M", r["pph_terutang"], 27_500_000)
r = tx.hitung_pph15("penerbangan_dalam", 1_000_000_000)
cek("penerbangan dalam 1 M", r["pph_terutang"], 18_000_000)
try:
    tx.hitung_pph15("jenis_salah", 1_000_000)
    cek("jenis salah ditolak", False, True)
except ValueError:
    cek("jenis salah ditolak", True, True)

print("\n=== Bea Meterai ===")
cek("Rp200.000 (di bawah batas)",
    tx.hitung_meterai(200_000)["total"], 0)
cek("Rp300.000 (tepat batas)",
    tx.hitung_meterai(300_000)["total"], 0)
cek("Rp3.000.000 (kena, di bawah 5jt)",
    tx.hitung_meterai(3_000_000)["total"], 10_000)
cek("Rp6.000.000 (kena)",
    tx.hitung_meterai(6_000_000)["total"], 10_000)
cek("Rp2.000.000.000 (tetap 10rb)",
    tx.hitung_meterai(2_000_000_000)["total"], 10_000)
cek("5 berkas Rp6jt",
    tx.hitung_meterai(6_000_000, 5)["total"], 50_000)

print("\n=== Pajak Daerah (PBJT) ===")
cek("makanan 1jt", tx.hitung_pbjt("makanan_minuman", 1_000_000)["pajak"],
    100_000)
cek("hiburan 500rb", tx.hitung_pbjt("hiburan", 500_000)["pajak"], 50_000)
cek("tarif khusus 5%",
    tx.hitung_pbjt("makanan_minuman", 1_000_000, 5)["pajak"], 50_000)
try:
    tx.hitung_pbjt("jenis_salah", 1_000_000)
    cek("jenis salah ditolak", False, True)
except ValueError:
    cek("jenis salah ditolak", True, True)

print("\n=== Mata uang asing ===")
cek("1000 USD kurs 16.000",
    tx.konversi_mata_uang(1000, 16_000, "USD")["jumlah_idr"], 16_000_000)
cek("IDR tidak dikonversi",
    tx.konversi_mata_uang(5_000_000, 1, "IDR")["jumlah_idr"], 5_000_000)
cek("500 SGD kurs 11.900",
    tx.konversi_mata_uang(500, 11_900, "SGD")["jumlah_idr"], 5_950_000)
try:
    tx.konversi_mata_uang(100, 0, "USD")
    cek("kurs nol ditolak", False, True)
except ValueError:
    cek("kurs nol ditolak", True, True)

print("\n=== Selisih kurs ===")
r = tx.selisih_kurs(1000, 15_000, 16_000)
cek("naik 15rb->16rb (laba)", r["selisih"], 1_000_000)
r = tx.selisih_kurs(1000, 16_000, 15_000)
cek("turun 16rb->15rb (rugi)", r["selisih"], -1_000_000)

print()
if GAGAL:
    print(f"HASIL: {len(GAGAL)} GAGAL — {', '.join(GAGAL)}")
    sys.exit(1)
print("HASIL: seluruh perhitungan pajak baru benar")
