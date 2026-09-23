"""
Pemburu bug pada mesin pajak: uji nilai tepi dan nilai ekstrem.

Angka pajak tidak boleh salah, tidak boleh error, dan tidak boleh
menghasilkan nilai negatif. Pemeriksaan ini menembakkan nilai batas —
nol, satu rupiah, tepat di ambang, dan angka sangat besar — ke setiap
fungsi perhitungan pajak yang dipakai aplikasi.

Jalankan:  python tools/buruh_bug_pajak.py
"""

import os
import sys
import traceback
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "src"))
os.environ.setdefault("AKUNTANSIID_DATA", str(AKAR / "_contoh"))

from akuntansi_id.core import tax_engine as tx       # noqa: E402

# Nilai tepi yang wajib diuji: nol, satu, tepat di ambang, dan sangat besar.
NILAI_UJI = [
    0, 1, 999, 1_000,
    500_000_000, 500_000_001,                 # ambang PPh final UMKM
    4_800_000_000, 4_800_000_001,             # ambang Pasal 31E
    50_000_000_000, 50_000_000_001,           # batas atas 31E
    999_999_999_999,                          # angka sangat besar
]

STATUS_PTKP = ("TK/0", "TK/1", "K/0", "TK/2", "K/1", "K/2", "K/3")

lulus = 0
gagal = 0


def ambil_angka(hasil):
    """Ambil angka utama dari hasil perhitungan, apa pun bentuknya."""
    if isinstance(hasil, (int, float)):
        return hasil
    if hasattr(hasil, "pph_terutang"):
        return hasil.pph_terutang
    if hasattr(hasil, "pph"):
        return hasil.pph
    if hasattr(hasil, "ppn"):
        return hasil.ppn
    if isinstance(hasil, dict):
        for kunci in ("pph", "pph_terutang", "total", "nilai", "ppn"):
            if kunci in hasil and isinstance(hasil[kunci], (int, float)):
                return hasil[kunci]
    if isinstance(hasil, tuple) and hasil:
        return ambil_angka(hasil[0])
    return None


def uji(nama: str, fn) -> None:
    """Jalankan satu fungsi pada semua nilai uji."""
    global lulus, gagal
    for nilai in NILAI_UJI:
        try:
            hasil = fn(nilai)
        except Exception as e:
            gagal += 1
            print(f"  [GAGAL] {nama}({nilai:,}): {type(e).__name__}: {e}")
            continue

        angka = ambil_angka(hasil)
        if angka is not None and angka < 0:
            gagal += 1
            print(f"  [GAGAL] {nama}({nilai:,}) menghasilkan negatif: {angka}")
        else:
            lulus += 1


def bagian(judul: str):
    print(f"[{judul}]")
    awal = lulus + gagal
    return awal


def tutup_bagian(awal: int):
    print(f"  {lulus + gagal - awal} pemeriksaan")
    print()


def main() -> int:
    print("=" * 72)
    print("PEMBURU BUG — MESIN PAJAK (nilai tepi & ekstrem)")
    print("=" * 72)
    print()

    a = bagian("PPh Final UMKM")
    for bentuk in ("umkm_op", "pt", "cv", "koperasi", "pt_perorangan"):
        uji(f"final_umkm[{bentuk}]",
            lambda v, b=bentuk: tx.hitung_pph_final_umkm(v, b))
    tutup_bagian(a)

    a = bagian("PPh Badan Pasal 31E")
    uji("pph_badan", lambda v: tx.hitung_pph_badan(v, v))
    uji("pph_badan_pkp_kecil", lambda v: tx.hitung_pph_badan(v, v // 2))
    tutup_bagian(a)

    a = bagian("PPh 21 — TER bulanan (semua status PTKP)")
    for status in STATUS_PTKP:
        uji(f"pph21_bulanan[{status}]",
            lambda v, s=status: tx.pph21_bulanan_ter(v, s))
    tutup_bagian(a)

    a = bagian("PPh 21 — harian")
    for status in STATUS_PTKP:
        uji(f"pph21_harian[{status}]",
            lambda v, s=status: tx.pph21_harian_ter(v, s))
    tutup_bagian(a)

    a = bagian("PPh 21 — setahun")
    for status in STATUS_PTKP:
        uji(f"pph21_setahun[{status}]",
            lambda v, s=status: tx.pph21_setahun(v, status_ptkp=s))
    tutup_bagian(a)

    a = bagian("PPN — semua jenis")
    for jenis in tx.PPN_JENIS:
        uji(f"ppn[{jenis}]", lambda v, j=jenis: tx.hitung_ppn(v, j))
    tutup_bagian(a)

    a = bagian("Penyusutan")
    for umur in (0, 1, 4, 8, 20, -1):
        uji(f"penyusutan_komersial[umur={umur}]",
            lambda v, u=umur: tx.penyusutan_komersial(v, 0, u))
    tutup_bagian(a)

    a = bagian("Pemotongan & pemungutan (PPh 23 / 4(2) / 22 / 26)")
    for jenis in ("jasa", "sewa", "royalti"):
        uji(f"pph23[{jenis}]", lambda v, j=jenis: tx.hitung_pph23(v, j))
    for objek in ("sewa_tanah", "sewa_bangunan", "jasa_konstruksi"):
        uji(f"pph4_2[{objek}]",
            lambda v, o=objek: tx.hitung_pph4_final(v, o))
    uji("pph22", lambda v: tx.hitung_pph22(v))
    uji("pph26", lambda v: tx.hitung_pph26(v))
    tutup_bagian(a)

    a = bagian("Sanksi & bunga keterlambatan")
    uji("bunga_keterlambatan", lambda v: tx.hitung_bunga_keterlambatan(v, 6))
    uji("sanksi_kurang_bayar", lambda v: tx.hitung_sanksi_kurang_bayar(v))
    tutup_bagian(a)

    a = bagian("Kredit pajak & PPh 25")
    uji("pph25", lambda v: tx.hitung_pph25(v, v // 3))
    tutup_bagian(a)

    a = bagian("Pajak lain: PPh 15, meterai, PBJT")
    for jenis in ("pelayaran_dalam", "pelayaran_luar", "penerbangan_dalam"):
        uji(f"pph15[{jenis}]", lambda v, j=jenis: tx.hitung_pph15(j, v))
    uji("meterai", lambda v: tx.hitung_meterai(v, 1))
    uji("pbjt_makanan", lambda v: tx.hitung_pbjt("makanan_minuman", v))
    tutup_bagian(a)

    a = bagian("BPJS")
    uji("bpjs", lambda v: tx.hitung_bpjs(v))
    tutup_bagian(a)

    print("=" * 72)
    total = lulus + gagal
    if gagal == 0:
        print(f"HASIL: {lulus} LULUS, 0 GAGAL dari {total} pemeriksaan")
        print("        mesin pajak tahan nilai tepi dan nilai ekstrem")
    else:
        print(f"HASIL: {lulus} LULUS, {gagal} GAGAL dari {total} pemeriksaan")
    print("=" * 72)
    return 1 if gagal else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc()
        sys.exit(1)
