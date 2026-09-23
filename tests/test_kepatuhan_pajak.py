"""
Uji kepatuhan pajak: memverifikasi angka yang dihasilkan mesin pajak
terhadap kutipan regulasi resmi yang tersimpan di docs/pajak2026/.

Berkas regulasi adalah salinan resmi yang diunduh dari pajak.go.id dan
peraturan.bpk.go.id, sehingga hasil uji ini menjadi bukti kesesuaian.
"""
import os
import re
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["AKUNTANSIID_DATA"] = str(Path(__file__).parent.parent / "_pajaktest")

AKAR = Path(__file__).parent.parent
sys.path.insert(0, str(AKAR / "src"))

from akuntansi_id import config
from akuntansi_id.core import tax_engine as tx

lulus = 0
gagal = 0


def cek(nama, kondisi, detail=""):
    global lulus, gagal
    if kondisi:
        lulus += 1
        print(f"OK     {nama}")
    else:
        gagal += 1
        print(f"GAGAL  {nama}  {detail}")


def baca_regulasi(nama: str) -> str:
    p = AKAR / "docs" / "pajak2026" / nama
    if not p.exists():
        return ""
    return p.read_text(encoding="utf-8", errors="replace")


def main():
    print("=" * 74)
    print("UJI KEPATUHAN PAJAK TERHADAP REGULASI RESMI")
    print("=" * 74)

    # ------------------------------------------------------------------
    print("\n[1] PPh Final UMKM 0,5% — PP 55/2022 jo. PP 20/2026")
    teks = baca_regulasi("PP20_2026.txt")
    cek("Berkas PP 20/2026 tersedia", bool(teks))
    if teks:
        angka = re.findall(r"4\.?800\.?000\.?000", teks.replace(" ", ""))
        cek("PP 20/2026 memuat batas Rp4,8 miliar", len(angka) > 0,
            f"ditemukan {len(angka)} kemunculan")

    cek("Batas peredaran bruto final = Rp4,8 miliar",
        config.THRESHOLD_PKP == 4_800_000_000, f"nilai={config.THRESHOLD_PKP}")
    cek("Batas bebas pajak OP = Rp500 juta",
        config.THRESHOLD_FINAL_OP == 500_000_000,
        f"nilai={config.THRESHOLD_FINAL_OP}")
    cek("Tarif final UMKM = 0,5%",
        abs(config.RATE_FINAL_UMKM - 0.005) < 1e-9,
        f"nilai={config.RATE_FINAL_UMKM}")

    hasil = tx.hitung_pph_final_umkm(600_000_000, "umkm_op",
                                                   final_eligible_dikonfirmasi=True)
    cek("OP omzet 600jt → PPh Rp500rb (500jt bebas pajak)",
        hasil.pph_final == 500_000, f"pph={hasil.pph_final}")

    hasil = tx.hitung_pph_final_umkm(400_000_000, "umkm_op",
                                                   final_eligible_dikonfirmasi=True)
    cek("OP omzet 400jt → PPh Rp0", hasil.pph_final == 0, f"pph={hasil.pph_final}")

    hasil = tx.hitung_pph_final_umkm(2_000_000_000, "pt",
                                                   final_eligible_dikonfirmasi=True)
    cek("Badan omzet 2M → PPh Rp10jt (0,5% penuh)",
        hasil.pph_final == 10_000_000, f"pph={hasil.pph_final}")

    # ------------------------------------------------------------------
    print("\n[2] PPh 21 TER — PMK 168/2023")
    teks = baca_regulasi("PMK168_2023.txt")
    cek("Berkas PMK 168/2023 tersedia", bool(teks))
    if teks:
        cek("PMK 168 memuat 'TER A'", "TER A" in teks)
        for lapisan in ["5.400.000", "5.950.000", "11.600.000", "125.000.000"]:
            pola = lapisan.replace(".", "")
            cek(f"PMK 168 memuat lapisan {lapisan}",
                pola in teks.replace(" ", "").replace(".", ""))
        cek("PMK 168 memuat tarif 0,50%", "0,50%" in teks)
        cek("PMK 168 memuat tarif 25,00%", "25,00%" in teks)

    ter_a = tx.TER_TABLE_A
    cek("TER A memiliki 44 lapisan", len(ter_a) == 44, f"jumlah={len(ter_a)}")
    cek("TER A lapisan 1: s.d. Rp5,4jt tarif 0%",
        ter_a[0] == (5_400_000, 0.0), f"lapisan={ter_a[0]}")
    cek("TER A lapisan 2: s.d. Rp5,65jt tarif 0,25%",
        ter_a[1] == (5_650_000, 0.0025), f"lapisan={ter_a[1]}")
    cek("TER A lapisan 3: s.d. Rp5,95jt tarif 0,5%",
        ter_a[2] == (5_950_000, 0.005), f"lapisan={ter_a[2]}")
    cek("TER A lapisan 16: s.d. Rp15,1jt tarif 6%",
        ter_a[15] == (15_100_000, 0.06), f"lapisan={ter_a[15]}")
    cek("TER A lapisan 44: di atas Rp1,4M tarif 34%",
        ter_a[43][1] == 0.34, f"lapisan={ter_a[43]}")

    ter_b = tx.TER_TABLE_B
    cek("TER B memiliki 40 lapisan", len(ter_b) == 40, f"jumlah={len(ter_b)}")
    cek("TER B lapisan 1: s.d. Rp6,2jt tarif 0%",
        ter_b[0] == (6_200_000, 0.0), f"lapisan={ter_b[0]}")

    ter_c = tx.TER_TABLE_C
    cek("TER C memiliki 41 lapisan", len(ter_c) == 41, f"jumlah={len(ter_c)}")
    cek("TER C lapisan 1: s.d. Rp6,6jt tarif 0%",
        ter_c[0] == (6_600_000, 0.0), f"lapisan={ter_c[0]}")

    cek("Pemetaan TER: TK/0 → kategori A",
        config.TER_CATEGORY_MAP["TK/0"] == "A",
        f"nilai={config.TER_CATEGORY_MAP.get('TK/0')}")
    cek("Pemetaan TER: K/0 → kategori A",
        config.TER_CATEGORY_MAP["K/0"] == "A")
    cek("Pemetaan TER: K/1 → kategori B",
        config.TER_CATEGORY_MAP["K/1"] == "B")
    cek("Pemetaan TER: K/2 → kategori B",
        config.TER_CATEGORY_MAP["K/2"] == "B")
    cek("Pemetaan TER: K/3 → kategori C",
        config.TER_CATEGORY_MAP["K/3"] == "C")

    hasil = tx.pph21_bulanan_ter(5_000_000, "TK/0")
    cek("PPh21 bruto 5jt TK/0 = Rp0 (di bawah batas lapisan 1)",
        hasil.pph21_ter == 0, f"pph={hasil.pph21_ter}")
    hasil = tx.pph21_bulanan_ter(5_800_000, "TK/0")
    cek("PPh21 bruto 5,8jt TK/0 = Rp29.000 (0,5% — lapisan 3 TER A)",
        hasil.pph21_ter == 29_000, f"pph={hasil.pph21_ter}")

    # ------------------------------------------------------------------
    print("\n[3] PPh Badan Pasal 31E — UU HPP")
    hasil = tx.hitung_pph_badan(20_000_000_000, 5_000_000_000)
    cek("Pasal 31E: omzet 20M PKP 5M → Rp968 juta",
        hasil.pph_terutang == 968_000_000, f"pph={hasil.pph_terutang}")

    hasil = tx.hitung_pph_badan(4_000_000_000, 1_000_000_000)
    cek("Omzet 4M (di bawah 4,8M) → seluruh PKP tarif 11% (fasilitas 31E)",
        hasil.pph_terutang == 110_000_000, f"pph={hasil.pph_terutang}")

    hasil = tx.hitung_pph_badan(60_000_000_000, 10_000_000_000)
    cek("Omzet 60M (di atas 50M) → tarif penuh 22% = Rp2,2M",
        hasil.pph_terutang == 2_200_000_000, f"pph={hasil.pph_terutang}")

    cek("Tarif PPh badan = 22%",
        abs(config.RATE_CORPORATE - 0.22) < 1e-9,
        f"nilai={config.RATE_CORPORATE}")
    cek("Tarif fasilitas 31E = 11% (50% × 22%)",
        abs(config.RATE_31E_FACILITY - 0.11) < 1e-9,
        f"nilai={config.RATE_31E_FACILITY}")
    cek("Tarif non-fasilitas = 22%",
        abs(config.RATE_31E_NON_FACILITY - 0.22) < 1e-9,
        f"nilai={config.RATE_31E_NON_FACILITY}")

    # ------------------------------------------------------------------
    print("\n[4] PPN — PMK 131/2024 & UU HPP")
    hasil = tx.hitung_ppn(100_000_000, "12% DPP Nilai Lain (11/12)")
    cek("PPN 12% × DPP nilai lain dari 100jt → Rp11jt (efektif 11%)",
        hasil.ppn == 11_000_000, f"ppn={hasil.ppn}")

    hasil = tx.hitung_ppn(100_000_000, "12% DPP Penuh (Mewah)")
    cek("PPN 12% DPP penuh dari 100jt → Rp12jt",
        hasil.ppn == 12_000_000, f"ppn={hasil.ppn}")

    hasil = tx.hitung_ppn(100_000_000, "Non-PKP/Tidak Dipungut")
    cek("Non-PKP → PPN Rp0", hasil.ppn == 0, f"ppn={hasil.ppn}")

    cek("Tarif PPN = 12%", abs(config.RATE_VAT - 0.12) < 1e-9,
        f"nilai={config.RATE_VAT}")
    cek("Tarif efektif PPN barang umum = 11%",
        abs(config.RATE_VAT_EFFECTIVE_NORMAL - 0.11) < 1e-9,
        f"nilai={config.RATE_VAT_EFFECTIVE_NORMAL}")
    cek("Faktor DPP nilai lain = 11/12",
        abs(config.VAT_DPP_NILAI_LAIN_FACTOR - 11 / 12) < 1e-9,
        f"nilai={config.VAT_DPP_NILAI_LAIN_FACTOR}")

    # ------------------------------------------------------------------
    print("\n[5] PTKP — PMK 101/2016 jo. UU HPP")
    ptkp = config.PTKP_ANNUAL
    for status, harap in [("TK/0", 54_000_000), ("TK/1", 58_500_000),
                          ("TK/2", 63_000_000), ("TK/3", 67_500_000),
                          ("K/0", 58_500_000), ("K/1", 63_000_000),
                          ("K/2", 67_500_000), ("K/3", 72_000_000)]:
        cek(f"PTKP {status} = Rp{harap:,}".replace(",", "."),
            ptkp.get(status) == harap, f"nilai={ptkp.get(status)}")

    # ------------------------------------------------------------------
    print("\n[6] Lapisan tarif PPh 17 — UU HPP")
    lapisan = config.PPH21_BRACKETS
    cek("Lapisan 1: s.d. Rp60jt tarif 5%",
        lapisan[0] == (60_000_000, 0.05), f"lapisan={lapisan[0]}")
    cek("Lapisan 2: s.d. Rp250jt tarif 15%",
        lapisan[1] == (250_000_000, 0.15), f"lapisan={lapisan[1]}")
    cek("Tarif tertinggi 35%", abs(lapisan[-1][1] - 0.35) < 1e-9,
        f"lapisan={lapisan[-1]}")

    # ------------------------------------------------------------------
    print("\n[7] PPh 21 setahun vs tarif progresif")
    hasil = tx.pph21_setahun(120_000_000, "TK/0")
    cek("Biaya jabatan 5% dibatasi Rp6 juta setahun",
        hasil.biaya_jabatan == 6_000_000, f"nilai={hasil.biaya_jabatan}")
    cek("PKP setelah PTKP = Rp60 juta",
        hasil.pkp == 60_000_000, f"pkp={hasil.pkp}")
    cek("Bruto 120jt TK/0 → PPh Rp3 juta (5% × 60jt)",
        hasil.pph21_setahun == 3_000_000, f"pph={hasil.pph21_setahun}")

    # ------------------------------------------------------------------
    print("\n[8] Sanksi administrasi — UU KUP")
    cek("Sanksi bunga KUP tersedia",
        hasattr(config, "SANCTION_INTEREST_KUP_2PCT"))
    if hasattr(config, "SANCTION_INTEREST_KUP_2PCT"):
        cek("Sanksi bunga KUP = 2%",
            abs(config.SANCTION_INTEREST_KUP_2PCT - 0.02) < 1e-9,
            f"nilai={config.SANCTION_INTEREST_KUP_2PCT}")

    # ------------------------------------------------------------------
    print("\n[9] Salinan regulasi resmi tersimpan")
    daftar = ["PP20_2026.txt", "PMK168_2023.txt", "PMK72_2025.txt",
              "PMK114_2025.txt", "UU_HPP_7_2021.txt", "UU_1_2026.txt",
              "PP55_2022.txt", "PP9_2021.txt", "PP34_2017.txt"]
    for nama in daftar:
        p = AKAR / "docs" / "pajak2026" / nama
        cek(f"Salinan {nama}", p.exists() and p.stat().st_size > 1000,
            f"ukuran={p.stat().st_size if p.exists() else 0}")

    print(f"\n{'=' * 74}")
    print(f"HASIL: {lulus} LULUS, {gagal} GAGAL")
    print("=" * 74)
    return 1 if gagal else 0


if __name__ == "__main__":
    sys.exit(main())
