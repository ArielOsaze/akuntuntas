"""
Verifikasi independen: perhitungan pajak dihitung ulang dari rumus asli.

Tes biasa memanggil fungsi aplikasi lalu memeriksa hasilnya. Cara itu tidak
dapat menemukan kesalahan yang ada di dalam rumusnya sendiri, karena yang
memeriksa dan yang diperiksa memakai kode yang sama.

Berkas ini menghitung ulang setiap nilai memakai rumus yang ditulis
terpisah, langsung dari ketentuan perpajakan, lalu membandingkan hasilnya
dengan hasil aplikasi. Bila keduanya berbeda, salah satu pasti keliru.

Cara pakai:
    python tools/verifikasi_independen_pajak.py
"""
from __future__ import annotations

import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "src"))

from akuntansi_id.core import tax_engine as T  # noqa: E402


class Pemeriksa:
    def __init__(self):
        self.lulus = 0
        self.gagal = 0
        self.temuan: list[str] = []

    def cek(self, nama: str, benar, salah, keterangan: str = ""):
        if benar == salah:
            self.lulus += 1
            print(f"  [COCOK] {nama}")
        else:
            self.gagal += 1
            self.temuan.append(nama)
            print(f"  [BEDA]  {nama}")
            print(f"          aplikasi    : {benar}")
            print(f"          hitung ulang: {salah}")
            if keterangan:
                print(f"          {keterangan}")

    def ringkas(self) -> int:
        print()
        print("=" * 76)
        if self.gagal:
            print(f"  HASIL: {self.lulus} COCOK, {self.gagal} BEDA")
            print()
            print("  Perhitungan yang perlu diperiksa:")
            for t in self.temuan:
                print(f"    - {t}")
        else:
            print(f"  HASIL: {self.lulus} COCOK, 0 BEDA")
            print("  Seluruh perhitungan cocok dengan hitungan ulang.")
        print("=" * 76)
        return 1 if self.gagal else 0


# ==========================================================================
# RUMUS HITUNG ULANG (ditulis terpisah dari aplikasi)
# ==========================================================================
# Lapisan tarif PPh 21 menurut Pasal 17 UU HPP.
LAPISAN_PPH21 = [
    (60_000_000, 0.05),
    (250_000_000, 0.15),
    (500_000_000, 0.25),
    (5_000_000_000, 0.30),
    (float("inf"), 0.35),
]


def pph21_progresif_ulang(pkp: int) -> int:
    """
    Hitung PPh 21 progresif dari lapisan tarif, dengan rumus sendiri.

    Lapisan pertama dikenakan 5% sampai 60 juta, kelebihannya 15% sampai
    250 juta, dan seterusnya. Perhitungan dilakukan bertingkat, bukan
    mengalikan seluruh penghasilan dengan satu tarif.
    """
    sisa = max(0, int(pkp))
    batas_sebelum = 0
    pajak = 0.0
    for batas, tarif in LAPISAN_PPH21:
        if sisa <= 0:
            break
        lebar = batas - batas_sebelum
        kena = min(sisa, lebar)
        pajak += kena * tarif
        sisa -= kena
        batas_sebelum = batas
    return int(round(pajak))


def pph_badan_ulang(omzet: int, pkp: int) -> int:
    """
    Hitung PPh badan dengan rumus sendiri.

    Tarif umum 22%. Menurut Pasal 31E UU PPh, badan dengan peredaran
    bruto sampai 50 miliar mendapat pengurangan tarif 50% untuk bagian
    penghasilan dari peredaran sampai 4,8 miliar, sehingga tarifnya
    menjadi 11% untuk bagian itu.
    """
    tarif = 0.22
    if omzet <= 4_800_000_000:
        # Seluruh penghasilan mendapat fasilitas.
        return int(round(pkp * tarif * 0.5))
    if omzet <= 50_000_000_000:
        # Hanya bagian yang sebanding dengan 4,8 miliar.
        bagian_fasilitas = 4_800_000_000 / omzet
        kena_fasilitas = pkp * bagian_fasilitas
        kena_biasa = pkp - kena_fasilitas
        return int(round(kena_fasilitas * tarif * 0.5 + kena_biasa * tarif))
    return int(round(pkp * tarif))


def ppn_ulang(dpp: int, tarif: float) -> int:
    """PPN dengan rumus sendiri: tarif dikali dasar pengenaan pajak."""
    return int(round(dpp * tarif))


def penyusutan_garis_lurus_ulang(harga: int, residu: int, umur: int) -> int:
    """Penyusutan garis lurus dengan rumus sendiri."""
    if umur <= 0:
        return 0
    return int(round((harga - residu) / umur))


def main() -> int:
    p = Pemeriksa()
    print("=" * 76)
    print("  VERIFIKASI INDEPENDEN: PERHITUNGAN PAJAK")
    print("=" * 76)
    print()
    print("  Nilai aplikasi dibandingkan dengan hitungan ulang memakai")
    print("  rumus yang ditulis terpisah di berkas ini.")
    print()

    # ------------------------------------------------------- PPh 21 progresif
    print("[1. PPh 21 progresif]")
    for pkp in (0, 1, 10_000_000, 50_000_000, 60_000_000, 60_000_001,
                100_000_000, 250_000_000, 300_000_000, 500_000_000,
                600_000_000, 1_000_000_000, 5_000_000_000, 6_000_000_000,
                10_000_000_000):
        hasil_app, _ = T.pph21_progresif(pkp)
        ulang = pph21_progresif_ulang(pkp)
        p.cek(f"PKP Rp{pkp:,}", hasil_app, ulang)
    print()

    # --------------------------------------------------------- PPh badan
    # Urutan argumen aplikasi: (omzet, pkp).
    print("[2. PPh badan]")
    for omzet, pkp in (
        (1_000_000_000, 100_000_000),
        (4_800_000_000, 500_000_000),
        (10_000_000_000, 1_000_000_000),
        (50_000_000_000, 2_000_000_000),
        (100_000_000_000, 5_000_000_000),
        (1_000_000_000, 0),
        (2_000_000_000, 2_000_000_000),
    ):
        hasil = T.hitung_pph_badan(omzet, pkp)
        p.cek(f"omzet Rp{omzet:,} pkp Rp{pkp:,}",
              hasil.pph_terutang, pph_badan_ulang(omzet, pkp))
    print()

    # ------------------------------------------------------------- PPN
    # Jenis pertama adalah Non-PKP (PPN nol); yang dikenakan PPN adalah
    # "12% DPP Nilai Lain (11/12)" dengan tarif efektif 11%, dan
    # "12% DPP Penuh (Mewah)" dengan tarif 12%.
    print("[3. PPN]")
    for dpp, jenis, tarif in (
        (1_000_000, "12% DPP Nilai Lain (11/12)", 0.11),
        (10_000_000, "12% DPP Nilai Lain (11/12)", 0.11),
        (100_000_000, "12% DPP Nilai Lain (11/12)", 0.11),
        (1_000_000_000, "12% DPP Nilai Lain (11/12)", 0.11),
        (100_000_000, "12% DPP Penuh (Mewah)", 0.12),
        (1_000_000, "Non-PKP/Tidak Dipungut", 0.0),
        (0, "12% DPP Nilai Lain (11/12)", 0.11),
    ):
        hasil = T.hitung_ppn(dpp, jenis)
        p.cek(f"DPP Rp{dpp:,} {jenis[:26]}",
              hasil.ppn, ppn_ulang(dpp, tarif))
    print()

    # ----------------------------------------------------------- PPh 23
    # Kolom hasilnya bernama "pajak", bukan "pph".
    print("[4. PPh 23]")
    for dpp, jenis, tarif in (
        (10_000_000, "jasa", 0.02),
        (100_000_000, "jasa", 0.02),
        (50_000_000, "sewa", 0.02),
        (0, "jasa", 0.02),
    ):
        hasil = T.hitung_pph23(dpp, jenis)
        p.cek(f"Rp{dpp:,} {jenis} @ {tarif:.0%}",
              hasil.pajak, ppn_ulang(dpp, tarif))
    print()

    # ----------------------------------------------------------- PPh 4(2)
    print("[5. PPh 4 ayat (2) final]")
    for dpp, objek, tarif in (
        (100_000_000, "sewa_tanah", 0.10),
        (1_000_000_000, "sewa_tanah", 0.10),
        (0, "sewa_tanah", 0.10),
    ):
        hasil = T.hitung_pph4_final(dpp, objek)
        p.cek(f"Rp{dpp:,} {objek} @ {tarif:.0%}",
              hasil.pajak, ppn_ulang(dpp, tarif))
    print()

    # --------------------------------------------------------- penyusutan
    print("[6. Penyusutan garis lurus]")
    for harga, residu, umur in (
        (100_000_000, 0, 10),
        (120_000_000, 20_000_000, 5),
        (50_000_000, 0, 4),
        (0, 0, 5),
    ):
        hasil = T.penyusutan_komersial(harga, residu, umur)
        nilai = hasil.get("per_tahun") if isinstance(hasil, dict) else hasil
        p.cek(f"Rp{harga:,} residu Rp{residu:,} umur {umur} th",
              nilai, penyusutan_garis_lurus_ulang(harga, residu, umur))
    print()

    # ------------------------------------------------ nilai tepi dan ekstrem
    print("[7. Nilai tepi dan ekstrem (tidak boleh galat)]")
    for nilai in (-1_000_000, -1, 0, 1, 2 ** 40, 10 ** 15):
        try:
            T.pph21_progresif(nilai)
            T.hitung_ppn(max(0, nilai), "12% DPP Nilai Lain (11/12)")
            T.hitung_pph_badan(max(0, nilai), max(0, nilai))
            T.hitung_pph23(max(0, nilai))
            T.hitung_pph4_final(max(0, nilai))
            p.cek(f"nilai {nilai:,} tidak menimbulkan galat", True, True)
        except Exception as e:
            p.cek(f"nilai {nilai:,} tidak menimbulkan galat",
                  f"GALAT {type(e).__name__}: {e}", "tidak galat")
    print()

    # ------------------------------------------------- sifat hasil hitungan
    print("[8. Sifat hasil hitungan]")
    # PPN harus naik seiring naiknya dasar pengenaan.
    naik = all(
        T.hitung_ppn(n, "12% DPP Nilai Lain (11/12)").ppn
        <= T.hitung_ppn(n + 1_000_000, "12% DPP Nilai Lain (11/12)").ppn
        for n in range(0, 20_000_000, 1_000_000)
    )
    p.cek("PPN naik seiring naiknya DPP", naik, True)

    # PPh 21 tidak pernah negatif.
    tak_negatif = all(
        T.pph21_progresif(n)[0] >= 0
        for n in (-10_000_000, -1, 0, 1, 10 ** 12)
    )
    p.cek("PPh 21 tidak pernah negatif", tak_negatif, True)

    # PPh 21 harus konsisten: menambah PKP tidak menurunkan pajak.
    konsisten = all(
        T.pph21_progresif(n)[0] <= T.pph21_progresif(n + 1_000_000)[0]
        for n in range(0, 100_000_000, 1_000_000)
    )
    p.cek("PPh 21 tidak menurun saat PKP naik", konsisten, True)

    # PPh badan tidak pernah melebihi 22% dari PKP.
    tak_lebih = all(
        T.hitung_pph_badan(o, p_).pph_terutang <= round(p_ * 0.22)
        for o, p_ in ((1_000_000_000, 100_000_000),
                      (10_000_000_000, 1_000_000_000),
                      (100_000_000_000, 5_000_000_000))
    )
    p.cek("PPh badan tidak melebihi 22% PKP", tak_lebih, True)
    print()

    return p.ringkas()


if __name__ == "__main__":
    sys.exit(main())
