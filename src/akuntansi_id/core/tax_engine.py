"""
AkunTuntas - Mesin Kalkulasi Perpajakan Indonesia
==================================================
Semua rumus perhitungan pajak terpusat di sini agar konsisten dan dapat diuji.

Modul ini mengimplementasikan:
  • PPh Pasal 21 skema TER bulanan + penghitungan setahun (Pasal 17)
  • PPh Pasal 22, 23, 26 potong/pungut
  • PPh Pasal 4 ayat (2) final
  • PPh Badan tarif umum 22% + fasilitas Pasal 31E
  • PPh Final UMKM 0,5% dengan gerbang kelayakan
  • PPN DPP nilai lain 11/12 & DPP penuh
  • Penyusutan fiskal & komersial
  • Sanksi administrasi & perhitungan bunga keterlambatan
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .. import config


# ==========================================================================
# UTILITAS
# ==========================================================================
def round_down_thousand(amount: int) -> int:
    """PKP dibulatkan ke ribuan penuh ke bawah (Pasal 17 ayat 4 UU PPh)."""
    if amount <= 0:
        return 0
    return (int(amount) // 1000) * 1000


def rupiah(amount) -> str:
    """
    Format angka rupiah: Rp1.234.567, dan -Rp1.234.567 bila negatif.

    Tanda minus diletakkan sebelum "Rp" mengikuti penulisan baku bahasa
    Indonesia. Bila diletakkan di dalam ("Rp-1.234.567"), angkanya sulit
    dibaca sekilas karena tanda minus tampak menyatu dengan nominalnya.
    """
    try:
        angka = int(round(float(amount)))
    except (TypeError, ValueError):
        return "Rp0"
    teks = "Rp" + f"{abs(angka):,}".replace(",", ".")
    return f"-{teks}" if angka < 0 else teks


# ==========================================================================
# PPh PASAL 21 — SKEMA TER (Tarif Efektif Rata-rata)
# ==========================================================================
# Dasar hukum: PP 58/2023, PMK 168/PMK.03/2023 (berlaku 1 Januari 2024).
#
# Tabel TER Bulanan Kategori A, B, C.
# Format: (batas_atas_bruto_bulanan, tarif)
# Semakin tinggi penghasilan bruto, semakin tinggi tarif efektifnya.

TER_TABLE_A: list[tuple[int, float]] = [
    (5_400_000, 0.0),
    (5_650_000, 0.0025),
    (5_950_000, 0.005),
    (6_300_000, 0.0075),
    (6_750_000, 0.01),
    (7_500_000, 0.0125),
    (8_550_000, 0.015),
    (9_650_000, 0.0175),
    (10_050_000, 0.02),
    (10_350_000, 0.0225),
    (10_700_000, 0.025),
    (11_050_000, 0.03),
    (11_600_000, 0.035),
    (12_500_000, 0.04),
    (13_750_000, 0.05),
    (15_100_000, 0.06),
    (16_950_000, 0.07),
    (19_750_000, 0.08),
    (24_150_000, 0.09),
    (26_450_000, 0.1),
    (28_000_000, 0.11),
    (30_050_000, 0.12),
    (32_400_000, 0.13),
    (35_400_000, 0.14),
    (39_100_000, 0.15),
    (43_850_000, 0.16),
    (47_800_000, 0.17),
    (51_400_000, 0.18),
    (56_300_000, 0.19),
    (62_200_000, 0.2),
    (68_600_000, 0.21),
    (77_500_000, 0.22),
    (89_000_000, 0.23),
    (103_000_000, 0.24),
    (125_000_000, 0.25),
    (157_000_000, 0.26),
    (206_000_000, 0.27),
    (337_000_000, 0.28),
    (454_000_000, 0.29),
    (550_000_000, 0.3),
    (695_000_000, 0.31),
    (910_000_000, 0.32),
    (1_400_000_000, 0.33),
    (float("inf"), 0.34),
]

TER_TABLE_B: list[tuple[int, float]] = [
    (6_200_000, 0.0),
    (6_500_000, 0.0025),
    (6_850_000, 0.005),
    (7_300_000, 0.0075),
    (9_200_000, 0.01),
    (10_750_000, 0.015),
    (11_250_000, 0.02),
    (11_600_000, 0.025),
    (12_600_000, 0.03),
    (13_600_000, 0.04),
    (14_950_000, 0.05),
    (16_400_000, 0.06),
    (18_450_000, 0.07),
    (21_850_000, 0.08),
    (26_000_000, 0.09),
    (27_700_000, 0.1),
    (29_350_000, 0.11),
    (31_450_000, 0.12),
    (33_950_000, 0.13),
    (37_100_000, 0.14),
    (41_100_000, 0.15),
    (45_800_000, 0.16),
    (49_500_000, 0.17),
    (53_800_000, 0.18),
    (58_500_000, 0.19),
    (64_000_000, 0.2),
    (71_000_000, 0.21),
    (80_000_000, 0.22),
    (93_000_000, 0.23),
    (109_000_000, 0.24),
    (129_000_000, 0.25),
    (163_000_000, 0.26),
    (211_000_000, 0.27),
    (374_000_000, 0.28),
    (459_000_000, 0.29),
    (555_000_000, 0.3),
    (704_000_000, 0.31),
    (957_000_000, 0.32),
    (1_405_000_000, 0.33),
    (float("inf"), 0.34),
]

TER_TABLE_C: list[tuple[int, float]] = [
    (6_600_000, 0.0),
    (6_950_000, 0.0025),
    (7_350_000, 0.005),
    (7_800_000, 0.0075),
    (8_850_000, 0.01),
    (9_800_000, 0.0125),
    (10_950_000, 0.015),
    (11_200_000, 0.0175),
    (12_050_000, 0.02),
    (12_950_000, 0.03),
    (14_150_000, 0.04),
    (15_550_000, 0.05),
    (17_050_000, 0.06),
    (19_500_000, 0.07),
    (22_700_000, 0.08),
    (26_600_000, 0.09),
    (28_100_000, 0.1),
    (30_100_000, 0.11),
    (32_600_000, 0.12),
    (35_400_000, 0.13),
    (38_900_000, 0.14),
    (43_000_000, 0.15),
    (47_400_000, 0.16),
    (51_200_000, 0.17),
    (55_800_000, 0.18),
    (60_400_000, 0.19),
    (66_700_000, 0.2),
    (74_500_000, 0.21),
    (83_200_000, 0.22),
    (95_600_000, 0.23),
    (110_000_000, 0.24),
    (134_000_000, 0.25),
    (169_000_000, 0.26),
    (221_000_000, 0.27),
    (390_000_000, 0.28),
    (463_000_000, 0.29),
    (561_000_000, 0.3),
    (709_000_000, 0.31),
    (965_000_000, 0.32),
    (1_419_000_000, 0.33),
    (float("inf"), 0.34),
]

TER_TABLES = {"A": TER_TABLE_A, "B": TER_TABLE_B, "C": TER_TABLE_C}

# --------------------------------------------------------------------------
# TER HARIAN — untuk pegawai tidak tetap / harian (PMK 168/2023)
# --------------------------------------------------------------------------
# Dasar hukum: PMK 168/PMK.03/2023, Lampiran (Tarif Efektif Harian).
# Digunakan untuk penghasilan bruto harian, bukan bulanan.
#   • s.d. Rp450.000             0%
#   • > Rp450.000 - Rp2.500.000  0,5%
#   • > Rp2.500.000              tarif progresif Pasal 17 atas (bruto − PTKP harian)
TER_HARIAN_BATAS_1 = 450_000
TER_HARIAN_BATAS_2 = 2_500_000
TER_HARIAN_TARIF_1 = 0.0
TER_HARIAN_TARIF_2 = 0.005


def _persen(v: float, desimal: int = 1) -> str:
    """Persen dengan koma desimal, sesuai penulisan angka Indonesia."""
    try:
        teks = f"{float(v) * 100:.{desimal}f}"
    except (TypeError, ValueError):
        return "0%"
    return teks.replace(".", ",") + "%"


@dataclass
class PPh21Result:
    bruto: int = 0
    kategori_ter: str = "A"
    tarif_ter: float = 0.0
    pph21_ter: int = 0
    metode: str = "TER"
    keterangan: str = ""


def ter_category(status_ptkp: str) -> str:
    return config.TER_CATEGORY_MAP.get(status_ptkp.upper().strip(), "A")


def ter_rate(bruto_bulanan: int, kategori: str = "A") -> float:
    table = TER_TABLES.get(kategori.upper(), TER_TABLE_A)
    for batas, tarif in table:
        if bruto_bulanan <= batas:
            return tarif
    return table[-1][1]


def pph21_harian_ter(bruto_harian: int, status_ptkp: str = "TK/0") -> PPh21Result:
    """
    PPh 21 atas penghasilan harian pegawai tidak tetap.
    Dasar hukum: PMK 168/PMK.03/2023 (Tarif Efektif Harian).

    Ketentuan:
      • Bruto harian sampai Rp450.000  tidak dipotong (0%)
      • Bruto harian > Rp450.000 s.d. Rp2.500.000  0,5% dari bruto
      • Bruto harian > Rp2.500.000  tarif Pasal 17 atas (bruto − PTKP harian),
        dengan PTKP harian = PTKP setahun ÷ 360
    """
    ptkp_tahunan = config.PTKP_ANNUAL.get(status_ptkp.upper(), config.PTKP_ANNUAL["TK/0"])
    if bruto_harian <= TER_HARIAN_BATAS_1:
        return PPh21Result(
            bruto=bruto_harian, kategori_ter="Harian", tarif_ter=0.0, pph21_ter=0,
            metode="TER Harian",
            keterangan="Penghasilan harian sampai Rp450.000 tidak dipotong PPh 21.",
        )
    if bruto_harian <= TER_HARIAN_BATAS_2:
        pajak = int(round(bruto_harian * TER_HARIAN_TARIF_2))
        return PPh21Result(
            bruto=bruto_harian, kategori_ter="Harian", tarif_ter=TER_HARIAN_TARIF_2,
            pph21_ter=pajak, metode="TER Harian",
            keterangan=("Penghasilan harian Rp450.000-Rp2.500.000 dipotong 0,5% "
                        "dari bruto."),
        )
    # di atas Rp2,5 juta: tarif Pasal 17 atas penghasilan setelah PTKP harian
    ptkp_harian = ptkp_tahunan / 360
    dasar = max(0, bruto_harian - ptkp_harian)
    pajak, _ = pph21_progresif(round_down_thousand(int(dasar)))
    tarif_efektif = pajak / bruto_harian if bruto_harian else 0.0
    return PPh21Result(
        bruto=bruto_harian, kategori_ter="Harian", tarif_ter=tarif_efektif,
        pph21_ter=pajak, metode="Tarif Pasal 17 (harian)",
        keterangan=("Penghasilan harian di atas Rp2.500.000 dihitung dengan tarif "
                    f"Pasal 17 atas (bruto − PTKP harian Rp{ptkp_harian:,.0f})."
                    .replace(",", ".")),
    )


def pph21_bulanan_ter(bruto_bulanan: int, status_ptkp: str = "TK/0") -> PPh21Result:
    """
    PPh 21 bulanan dengan skema TER (Januari-November).
    Dasar hukum: PMK 168/PMK.03/2023.
    """
    kategori = ter_category(status_ptkp)
    tarif = ter_rate(bruto_bulanan, kategori)
    pajak = int(round(bruto_bulanan * tarif))
    return PPh21Result(
        bruto=bruto_bulanan,
        kategori_ter=kategori,
        tarif_ter=tarif,
        pph21_ter=pajak,
        metode="TER",
        keterangan=(f"Kategori TER {kategori} (status {status_ptkp}), "
                    f"tarif efektif {_persen(tarif, 2)} atas bruto bulanan."),
    )


def pph21_progresif(pkp: int) -> tuple[int, list[tuple[str, int, float, int]]]:
    """
    PPh 21/OP dengan tarif progresif Pasal 17.
    Kembalikan (total_pajak, rincian_per_lapisan).
    Dasar hukum: UU HPP Pasal 17 ayat (1) huruf a.
    """
    total = 0
    detail: list[tuple[str, int, float, int]] = []
    lower = 0
    for batas, tarif in config.PPH21_BRACKETS:
        if pkp <= lower:
            break
        lapisan = min(pkp, batas) - lower
        pajak = int(round(lapisan * tarif))
        total += pajak
        label = (f"s.d. {rupiah(batas)}" if batas != float("inf")
                 else f"di atas {rupiah(lower)}")
        detail.append((label, lapisan, tarif, pajak))
        lower = int(batas) if batas != float("inf") else lower
    return total, detail


def biaya_jabatan(bruto_setahun: int, bulan: int = 12) -> int:
    """
    Biaya jabatan 5% dari bruto, maksimal Rp500.000/bulan atau Rp6.000.000/tahun.
    Dasar hukum: PMK 250/PMK.03/2008.
    """
    lima_persen = int(bruto_setahun * config.BIYA_JABATAN_RATE)
    batas = min(config.BIYA_JABATAN_MAX_ANNUAL, config.BIYA_JABATAN_MAX_MONTHLY * bulan)
    return min(lima_persen, batas)


@dataclass
class PPh21TahunanResult:
    bruto_setahun: int = 0
    biaya_jabatan: int = 0
    iuran_pensiun: int = 0
    neto: int = 0
    ptkp: int = 0
    pkp: int = 0
    pkp_dibulatkan: int = 0
    pph21_setahun: int = 0
    pph21_dipotong: int = 0
    pph21_desember: int = 0
    detail_lapisan: list = field(default_factory=list)
    keterangan: str = ""


def pph21_setahun(
    bruto_setahun: int,
    status_ptkp: str = "TK/0",
    iuran_pensiun_setahun: int = 0,
    pph21_sudah_dipotong: int = 0,
) -> PPh21TahunanResult:
    """
    Penghitungan PPh 21 setahun (dipakai pada masa Desember / SPT Tahunan).
    Dasar hukum: Pasal 17 UU PPh, PMK 250/PMK.03/2008, PMK 168/2023.
    """
    bj = biaya_jabatan(bruto_setahun)
    neto = max(0, bruto_setahun - bj - iuran_pensiun_setahun)
    ptkp = config.PTKP_ANNUAL.get(status_ptkp.upper(), config.PTKP_ANNUAL["TK/0"])
    pkp = max(0, neto - ptkp)
    pkp_bulat = round_down_thousand(pkp)
    pajak, detail = pph21_progresif(pkp_bulat)
    return PPh21TahunanResult(
        bruto_setahun=bruto_setahun,
        biaya_jabatan=bj,
        iuran_pensiun=iuran_pensiun_setahun,
        neto=neto,
        ptkp=ptkp,
        pkp=pkp,
        pkp_dibulatkan=pkp_bulat,
        pph21_setahun=pajak,
        pph21_dipotong=pph21_sudah_dipotong,
        pph21_desember=pajak - pph21_sudah_dipotong,
        detail_lapisan=detail,
        keterangan="Penghitungan setahun: bruto − biaya jabatan − iuran pensiun − PTKP = PKP, "
                   "lalu tarif progresif Pasal 17.",
    )


# ==========================================================================
# BPJS
# ==========================================================================
@dataclass
class BPJSResult:
    kes_karyawan: int = 0
    kes_perusahaan: int = 0
    jht_karyawan: int = 0
    jht_perusahaan: int = 0
    jp_karyawan: int = 0
    jp_perusahaan: int = 0
    jkm_perusahaan: int = 0
    jkk_perusahaan: int = 0
    total_karyawan: int = 0
    total_perusahaan: int = 0


def hitung_bpjs(upah: int, jkk_rate: float = config.BPJS_JKK_DEFAULT,
                ikut_kes: bool = True, ikut_jht: bool = True,
                ikut_jp: bool = True) -> BPJSResult:
    """
    Iuran BPJS porsi karyawan dan pemberi kerja.
    Dasar hukum: Perpres 64/2020 (Kesehatan), PP 44/2015 & PP 46/2015
    (Ketenagakerjaan), serta peraturan pelaksana terbaru.
    """
    r = BPJSResult()
    if ikut_kes:
        dasar_kes = min(upah, config.BPJS_KES_WAGE_CAP)
        r.kes_karyawan = int(round(dasar_kes * config.BPJS_KES_EMPLOYEE))
        r.kes_perusahaan = int(round(dasar_kes * config.BPJS_KES_EMPLOYER))
    if ikut_jht:
        r.jht_karyawan = int(round(upah * config.BPJS_JHT_EMPLOYEE))
        r.jht_perusahaan = int(round(upah * config.BPJS_JHT_EMPLOYER))
    if ikut_jp:
        dasar_jp = min(upah, config.BPJS_JP_WAGE_CAP)
        r.jp_karyawan = int(round(dasar_jp * config.BPJS_JP_EMPLOYEE))
        r.jp_perusahaan = int(round(dasar_jp * config.BPJS_JP_EMPLOYER))
    r.jkm_perusahaan = int(round(upah * config.BPJS_JKM))
    r.jkk_perusahaan = int(round(upah * jkk_rate))
    r.total_karyawan = r.kes_karyawan + r.jht_karyawan + r.jp_karyawan
    r.total_perusahaan = (r.kes_perusahaan + r.jht_perusahaan + r.jp_perusahaan
                          + r.jkm_perusahaan + r.jkk_perusahaan)
    return r


# ==========================================================================
# PPh BADAN — TARIF UMUM & PASAL 31E
# ==========================================================================
@dataclass
class PPhBadanResult:
    omzet: int = 0
    pkp: int = 0
    skema: str = ""
    pkp_fasilitas: int = 0
    pkp_non_fasilitas: int = 0
    pph_fasilitas: int = 0
    pph_non_fasilitas: int = 0
    pph_terutang: int = 0
    tarif_efektif: float = 0.0
    kredit_pajak: int = 0
    kurang_lebih_bayar: int = 0
    pph25_bulanan: int = 0
    keterangan: str = ""
    peringatan: list[str] = field(default_factory=list)


def hitung_pph_badan(
    omzet: int,
    pkp: int,
    kredit_pajak: int = 0,
    sudah_dibayar: int = 0,
) -> PPhBadanResult:
    """
    PPh Badan dengan tarif umum 22% + fasilitas Pasal 31E.

    Dasar hukum:
      - Pasal 17 ayat (1) huruf b & Pasal 31E UU PPh
      - UU No. 7/2021 (UU HPP) tarif 22%
      - SE-02/PJ/2015 tata cara penerapan Pasal 31E
    """
    res = PPhBadanResult(omzet=omzet, pkp=pkp, kredit_pajak=kredit_pajak)
    if pkp <= 0:
        res.skema = "Tidak ada PPh terutang (PKP nihil/rugi)"
        res.keterangan = ("PKP nihil atau rugi fiskal. Rugi dapat dikompensasikan "
                          "ke tahun berikutnya (maksimal 5 tahun - Pasal 6 ayat 2 UU PPh).")
        res.kurang_lebih_bayar = -sudah_dibayar
        return res

    if omzet <= 0:
        res.skema = "Tarif Umum 22%"
        res.pkp_non_fasilitas = pkp
        res.pph_non_fasilitas = int(round(pkp * config.RATE_CORPORATE))
        res.peringatan.append(
            "Omzet belum diisi. Fasilitas Pasal 31E tidak dapat dihitung; "
            "dipakai tarif umum 22%. Isi omzet pada data perusahaan."
        )
    elif omzet <= config.THRESHOLD_PKP:
        # Omzet ≤ Rp4,8 M  seluruh PKP memperoleh fasilitas (tarif efektif 11%)
        res.skema = "Pasal 31E - seluruh PKP fasilitas (tarif efektif 11%)"
        res.pkp_fasilitas = pkp
        res.pph_fasilitas = int(round(pkp * config.RATE_31E_FACILITY))
        res.keterangan = (
            f"Peredaran bruto {rupiah(omzet)} tidak melebihi Rp4,8 miliar, sehingga "
            "seluruh Penghasilan Kena Pajak memperoleh fasilitas pengurangan tarif 50% "
            "dan dikenai tarif efektif 11%."
        )
    elif omzet <= config.THRESHOLD_31E:
        # Omzet antara 4,8 M - 50 M  split proporsional
        res.skema = "Pasal 31E - fasilitas proporsional"
        proporsi = config.THRESHOLD_PKP / omzet
        res.pkp_fasilitas = round_down_thousand(int(pkp * proporsi))
        res.pkp_non_fasilitas = pkp - res.pkp_fasilitas
        res.pph_fasilitas = int(round(res.pkp_fasilitas * config.RATE_31E_FACILITY))
        res.pph_non_fasilitas = int(round(res.pkp_non_fasilitas * config.RATE_CORPORATE))
        res.keterangan = (
            f"Peredaran bruto {rupiah(omzet)} berada antara Rp4,8 miliar dan Rp50 miliar. "
            f"Bagian PKP yang mendapat fasilitas = (4.800.000.000 ÷ {omzet:,}) × {pkp:,} "
            f"= {res.pkp_fasilitas:,} dengan tarif 11%; sisanya {res.pkp_non_fasilitas:,} "
            "dengan tarif 22%."
        ).replace(",", ".")
    else:
        res.skema = "Tarif Umum 22% (tidak memenuhi syarat Pasal 31E)"
        res.pkp_non_fasilitas = pkp
        res.pph_non_fasilitas = int(round(pkp * config.RATE_CORPORATE))
        res.peringatan.append(
            f"Peredaran bruto melebihi Rp50 miliar ({rupiah(omzet)}), sehingga "
            "fasilitas Pasal 31E tidak berlaku."
        )

    res.pph_terutang = res.pph_fasilitas + res.pph_non_fasilitas
    res.tarif_efektif = (res.pph_terutang / pkp) if pkp else 0.0
    res.kurang_lebih_bayar = res.pph_terutang - kredit_pajak - sudah_dibayar
    # Angsuran PPh 25 tahun berikutnya ≈ PPh terutang − kredit, dibagi 12
    dasar_25 = max(0, res.pph_terutang - kredit_pajak)
    res.pph25_bulanan = int(round(dasar_25 / 12))
    return res


# ==========================================================================
# PPh FINAL UMKM 0,5%
# ==========================================================================
@dataclass
class PPhFinalResult:
    omzet: int = 0
    dasar_pengenaan: int = 0
    tarif: float = config.RATE_FINAL_UMKM
    pph_final: int = 0
    layak: bool = False
    alasan: str = ""
    peringatan: list[str] = field(default_factory=list)


def hitung_pph_final_umkm(
    omzet_setahun: int,
    bentuk_badan: str = "umkm_op",
    tahun_pemakaian: int = 1,
    final_eligible_dikonfirmasi: bool = False,
    omzet_kumulatif_op: int = 0,
) -> PPhFinalResult:
    """
    PPh Final UMKM 0,5% - PP 55/2022 jo. PP 20/2026.

    Ketentuan penting:
      - Peredaran bruto tidak melebihi Rp4,8 miliar dalam satu tahun pajak.
      - Orang Pribadi: bagian peredaran bruto sampai Rp500 juta tidak dikenai pajak.
      - WP Badan tertentu: masa pemanfaatan terbatas (transisi PP 55/2022).
      - Beberapa bentuk badan tidak lagi dapat memanfaatkan skema ini sejak 2026.

    Karena kelayakan sangat bergantung pada bentuk badan, riwayat, dan periode,
    fungsi ini MENOLAK menerapkan skema final bila belum dikonfirmasi manual.
    """
    res = PPhFinalResult(omzet=omzet_setahun)

    if not final_eligible_dikonfirmasi:
        res.alasan = (
            "Skema PPh Final 0,5% belum diaktifkan. Kelayakan harus dikonfirmasi "
            "terlebih dahulu pada menu Data Perusahaan karena bergantung pada bentuk "
            "badan, riwayat penggunaan, dan periode transisi (PP 20/2026)."
        )
        res.peringatan.append(res.alasan)
        return res

    if omzet_setahun > config.THRESHOLD_PKP:
        res.alasan = (
            f"Peredaran bruto {rupiah(omzet_setahun)} melebihi Rp4,8 miliar. "
            "Tidak dapat memakai PPh Final 0,5% dan wajib memakai tarif umum."
        )
        res.peringatan.append(res.alasan)
        return res

    res.layak = True
    keterangan = ""
    if bentuk_badan == "umkm_op":
        # Bagian omzet sampai Rp500 juta tidak dikenai pajak
        sisa = max(0, config.THRESHOLD_FINAL_OP - omzet_kumulatif_op)
        dasar = max(0, omzet_setahun - sisa)
        res.dasar_pengenaan = dasar
        keterangan = (
            f"Orang Pribadi: bagian peredaran bruto sampai Rp500 juta tidak dikenai "
            f"pajak. Sisa yang dikenai pajak: {rupiah(dasar)}."
        )
    else:
        res.dasar_pengenaan = omzet_setahun

    res.pph_final = int(round(res.dasar_pengenaan * config.RATE_FINAL_UMKM))
    res.alasan = (keterangan + " " if keterangan else "") + (
        f"PPh Final 0,5% = {rupiah(res.pph_final)}. Setor paling lambat tanggal 15 "
        "bulan berikutnya dan laporkan SPT Masa PPh Final."
    )
    if tahun_pemakaian > 7 and bentuk_badan == "umkm_op":
        res.peringatan.append(
            "Masa pemanfaatan PPh Final bagi Orang Pribadi paling lama 7 tahun "
            "(PP 55/2022). Periksa apakah jangka waktu ini masih tersedia."
        )
    return res


# ==========================================================================
# PPN
# ==========================================================================
PPN_JENIS = [
    "Non-PKP/Tidak Dipungut",
    "12% DPP Nilai Lain (11/12)",
    "12% DPP Penuh (Mewah)",
]


@dataclass
class PPNResult:
    jenis: str = ""
    dpp: int = 0
    dpp_faktur: int = 0
    tarif: float = 0.0
    ppn: int = 0
    keterangan: str = ""


def hitung_ppn(nilai_sebelum_ppn: int, jenis: str = PPN_JENIS[0]) -> PPNResult:
    """
    Hitung PPN sesuai mekanisme yang berlaku 2025+.

    Mekanisme umum (barang/jasa non-mewah):
        PPN = 12% × (11/12 × harga jual)    efektif 11%
        Dasar hukum: PMK 131/PMK.03/2024.

    Objek mewah tertentu: PPN = 12% × harga jual (DPP penuh).
        Dasar hukum: PP 61/2020 jo. PMK 96/2025.
    """
    res = PPNResult(jenis=jenis, dpp=nilai_sebelum_ppn)

    if jenis.startswith("Non-PKP") or "Tidak Dipungut" in jenis:
        res.dpp_faktur = 0
        res.tarif = 0.0
        res.ppn = 0
        res.keterangan = ("Tidak ada PPN keluaran: pengusaha belum dikukuhkan sebagai PKP, "
                          "atau penyerahan termasuk yang dibebaskan/tidak dipungut.")
        return res

    if "Nilai Lain" in jenis:
        res.dpp_faktur = int(round(nilai_sebelum_ppn * config.VAT_DPP_NILAI_LAIN_FACTOR))
        res.tarif = config.RATE_VAT_EFFECTIVE_NORMAL  # 11%
        res.ppn = int(round(res.dpp_faktur * config.RATE_VAT))
        res.keterangan = (
            f"DPP Nilai Lain = 11/12 × {rupiah(nilai_sebelum_ppn)} = {rupiah(res.dpp_faktur)}. "
            f"PPN = 12% × {rupiah(res.dpp_faktur)} = {rupiah(res.ppn)} "
            f"(beban efektif 11%)."
        )
        return res

    if "DPP Penuh" in jenis:
        res.dpp_faktur = nilai_sebelum_ppn
        res.tarif = config.RATE_VAT_LUXURY  # 12%
        res.ppn = int(round(nilai_sebelum_ppn * config.RATE_VAT))
        res.keterangan = (
            f"Objek mewah: PPN = 12% × {rupiah(nilai_sebelum_ppn)} = {rupiah(res.ppn)} "
            "dengan DPP penuh."
        )
        return res

    # fallback: tarif 11%
    res.dpp_faktur = int(round(nilai_sebelum_ppn * config.VAT_DPP_NILAI_LAIN_FACTOR))
    res.tarif = config.RATE_VAT_EFFECTIVE_NORMAL
    res.ppn = int(round(res.dpp_faktur * config.RATE_VAT))
    res.keterangan = "Mekanisme umum DPP nilai lain (efektif 11%)."
    return res


def status_pkp(omzet_setahun: int, sudah_pkp: bool) -> dict:
    """
    Tentukan status kewajiban PKP.
    Dasar hukum: PMK 197/PMK.03/2013, PP 44/2022.
    """
    if sudah_pkp:
        return {
            "wajib_pkp": True,
            "status": "Sudah PKP",
            "pesan": "Anda terdaftar sebagai Pengusaha Kena Pajak. Wajib memungut PPN, "
                     "menerbitkan faktur pajak, dan melaporkan SPT Masa PPN setiap bulan.",
            "level": "info",
        }
    if omzet_setahun > config.THRESHOLD_PKP:
        return {
            "wajib_pkp": True,
            "status": "WAJIB MENDAFTAR PKP",
            "pesan": (f"Peredaran bruto {rupiah(omzet_setahun)} telah melewati batas "
                      f"Rp4,8 miliar. Anda WAJIB melaporkan diri untuk dikukuhkan sebagai "
                      "PKP paling lambat akhir bulan berikutnya, dan wajib memungut PPN "
                      "mulai awal bulan berikutnya."),
            "level": "danger",
        }
    rasio = omzet_setahun / config.THRESHOLD_PKP if config.THRESHOLD_PKP else 0
    if rasio >= 0.8:
        return {
            "wajib_pkp": False,
            "status": "Mendekati Batas PKP",
            "pesan": (f"Peredaran bruto {rupiah(omzet_setahun)} sudah mencapai "
                      f"{_persen(rasio, 1)} dari batas Rp4,8 miliar. Bersiaplah untuk "
                      "mendaftar sebagai PKP - siapkan administrasi faktur pajak."),
            "level": "warning",
        }
    return {
        "wajib_pkp": False,
        "status": "Belum wajib PKP",
        "pesan": (f"Peredaran bruto {rupiah(omzet_setahun)} masih di bawah batas "
                  f"Rp4,8 miliar ({_persen(rasio, 1)}). Belum wajib memungut PPN."),
        "level": "ok",
    }


def rekap_ppn(ppn_keluaran: int, ppn_masukan_kredit: int,
              ppn_masukan_tidak_kredit: int = 0,
              kompensasi_masa_lalu: int = 0) -> dict:
    """
    Rekap PPN satu masa pajak.
    PPN kurang bayar disetor; lebih bayar dapat dikompensasi atau direstitusi.
    """
    kredit_total = ppn_masukan_kredit + kompensasi_masa_lalu
    selisih = ppn_keluaran - kredit_total
    return {
        "ppn_keluaran": ppn_keluaran,
        "ppn_masukan_kredit": ppn_masukan_kredit,
        "ppn_masukan_tidak_kredit": ppn_masukan_tidak_kredit,
        "kompensasi_masa_lalu": kompensasi_masa_lalu,
        "kredit_total": kredit_total,
        "kurang_bayar": max(0, selisih),
        "lebih_bayar": max(0, -selisih),
        "status": "Kurang Bayar" if selisih > 0 else ("Lebih Bayar" if selisih < 0 else "Nihil"),
    }


# ==========================================================================
# PPh POTONG/PUNGUT LAIN
# ==========================================================================
@dataclass
class PotPutResult:
    kode: str = ""
    jenis: str = ""
    dpp: int = 0
    tarif: float = 0.0
    pajak: int = 0
    kredit_pph_badan: bool = False
    keterangan: str = ""


def hitung_pph23(dpp: int, jenis: str = "jasa") -> PotPutResult:
    """PPh 23: 2% jasa/sewa harta selain tanah & bangunan; 15% bunga/royalti/hadiah."""
    if jenis.lower() in ("jasa", "sewa", "rent", "service"):
        tarif, kode, label = config.RATE_PPH23_SERVICES_RENT, "PPh23-JASA", "PPh 23 atas jasa/sewa harta (2%)"
    else:
        tarif, kode, label = config.RATE_PPH23_DIVIDEND_INTEREST_ROYALTY, "PPh23-15", "PPh 23 atas bunga/royalti/hadiah (15%)"
    return PotPutResult(
        kode=kode, jenis=label, dpp=dpp, tarif=tarif,
        pajak=int(round(dpp * tarif)), kredit_pph_badan=False,
        keterangan="Dipotong oleh pihak pembayar. Bagi penerima, menjadi kredit pajak.",
    )


def hitung_pph4_final(dpp: int, objek: str = "sewa_tanah") -> PotPutResult:
    """PPh Final Pasal 4(2) untuk berbagai objek."""
    peta = {
        "sewa_tanah": (config.RATE_PPH4_SEWA_TANAH_BANGUNAN, "PPh4-SEWA",
                       "PPh Final 4(2) sewa tanah/bangunan - 10% dari bruto (PP 34/2017)"),
        "konstruksi_kecil": (config.RATE_PPH4_KONSTRUKSI_KECIL, "PPh4-KONSTRUKSI",
                             "PPh Final jasa konstruksi kualifikasi kecil - 1,75% (PP 9/2022)"),
        "konstruksi_menengah": (config.RATE_PPH4_KONSTRUKSI_MENENGAH, "PPh4-KONSTRUKSI",
                                "PPh Final jasa konstruksi kualifikasi menengah - 2% (PP 9/2022)"),
        "konstruksi_besar": (config.RATE_PPH4_KONSTRUKSI_BESAR, "PPh4-KONSTRUKSI",
                             "PPh Final jasa konstruksi kualifikasi besar - 2,65% (PP 9/2022)"),
        "pengalihan_tanah": (config.RATE_PPH4_PENGALIHAN_TANAH, "PPh4-PENGALIHAN",
                             "PPh Final pengalihan hak atas tanah/bangunan - 2,5% (PP 34/2016)"),
        "bunga_deposito": (config.RATE_PPH4_BUNGA_DEPOSITO, "PPh4-DEPOSITO",
                           "PPh Final bunga deposito/tabungan - 20% (PP 19/2009)"),
        "hadiah_undian": (config.RATE_PPH4_HADIAH_UNDIAN, "PPh4-UNDIAN",
                          "PPh Final hadiah undian - 25% (PP 132/2000)"),
    }
    tarif, kode, label = peta.get(objek, peta["sewa_tanah"])
    return PotPutResult(
        kode=kode, jenis=label, dpp=dpp, tarif=tarif,
        pajak=int(round(dpp * tarif)), kredit_pph_badan=False,
        keterangan="Pajak final - tidak dapat dikreditkan terhadap PPh Badan.",
    )


def hitung_pph22(dpp: int, kategori: str = "impor_api") -> PotPutResult:
    """PPh 22 - pemungutan atas impor dan pembelian barang tertentu."""
    peta = {
        "impor_api": (config.RATE_PPH22_IMPORT, "PPh22-IMPOR", "PPh 22 impor dengan API - 2,5%"),
        "impor_no_api": (config.RATE_PPH22_IMPORT_NO_API, "PPh22-IMPOR",
                         "PPh 22 impor tanpa API - 7,5%"),
        "umkm": (config.RATE_PPH22_UMKM, "PPh22-UMKM",
                 "PPh 22 pembelian dari UMKM oleh badan tertentu - 0,25%"),
        "barang": (config.RATE_PPH22_GOODS, "PPh22-BARANG",
                   "PPh 22 penjualan barang tertentu (kertas, semen, baja, otomotif) - 1,5%"),
        "bbm": (config.RATE_PPH22_PERTAMINA, "PPh22-BBM",
                "PPh 22 pembelian BBM/BBG - 0,3%"),
    }
    tarif, kode, label = peta.get(kategori, peta["impor_api"])
    return PotPutResult(
        kode=kode, jenis=label, dpp=dpp, tarif=tarif,
        pajak=int(round(dpp * tarif)), kredit_pph_badan=True,
        keterangan="Dipungut pihak lain; bagi pembeli menjadi kredit pajak PPh Badan.",
    )


def hitung_pph26(dpp: int, tarif_p3b: Optional[float] = None) -> PotPutResult:
    """PPh 26 untuk Wajib Pajak Luar Negeri - 20% atau tarif P3B."""
    tarif = tarif_p3b if tarif_p3b is not None else config.RATE_PPH26
    return PotPutResult(
        kode="PPh26", jenis=f"PPh 26 WPLN - {_persen(tarif, 2)}", dpp=dpp, tarif=tarif,
        pajak=int(round(dpp * tarif)), kredit_pph_badan=False,
        keterangan="Dipotong atas penghasilan yang dibayarkan ke WPLN. "
                   "Gunakan tarif P3B bila tersedia Surat Keterangan Domisili (SKD).",
    )


# ==========================================================================
# PENYUSUTAN
# ==========================================================================
@dataclass
class PenyusutanResult:
    penyusutan_komersial: int = 0
    penyusutan_fiskal: int = 0
    selisih: int = 0
    nbv_komersial: int = 0
    nbv_fiskal: int = 0
    metode_fiskal: str = ""
    tarif_fiskal: float = 0.0
    keterangan: str = ""


def penyusutan_komersial(harga_perolehan: int, residu: int, umur_tahun: int,
                         bulan_tahun_ini: int = 12) -> int:
    """Garis lurus komersial (PSAK 16)."""
    if umur_tahun <= 0 or harga_perolehan <= 0:
        return 0
    per_tahun = max(0, harga_perolehan - residu) / umur_tahun
    return int(round(per_tahun * bulan_tahun_ini / 12))


def penyusutan_fiskal(harga_perolehan: int, kelompok: str,
                      metode: str = "Garis Lurus",
                      bulan_tahun_ini: int = 12,
                      nbv_awal: int = 0,
                      sudah_disusutkan_tahun_lalu: int = 0) -> tuple[int, float, str]:
    """
    Penyusutan fiskal menurut PMK 72/PMK.03/2023.
    Kembalikan (nilai_penyusutan, tarif, keterangan).

    Catatan: pada tahun perolehan, penyusutan dihitung secara prorata
    (pengguna mengisi bulan disusutkan tahun ini).
    """
    info = config.FISCAL_ASSET_GROUPS.get(kelompok)
    if info is None:
        return 0, 0.0, "Kelompok fiskal tidak dikenal."
    if kelompok == "Tanah":
        return 0, 0.0, "Tanah tidak disusutkan (Pasal 11 ayat 1 UU PPh)."

    dasar = nbv_awal if nbv_awal > 0 else harga_perolehan

    if "Menurun" in metode and info["saldo_menurun"]:
        tarif = info["saldo_menurun"]
        nilai = int(round(dasar * tarif * bulan_tahun_ini / 12))
        ket = (f"Saldo menurun {tarif * 100:g}% per tahun atas nilai buku fiskal "
               f"{rupiah(dasar)} (prorata {bulan_tahun_ini}/12 bulan).")
    else:
        tarif = info["garis_lurus"]
        nilai = int(round(dasar * tarif * bulan_tahun_ini / 12))
        ket = (f"Garis lurus {tarif * 100:g}% per tahun atas harga perolehan "
               f"{rupiah(dasar)} (prorata {bulan_tahun_ini}/12 bulan).")
    return nilai, tarif, ket


def hitung_penyusutan(harga_perolehan: int, residu: int, umur_komersial: int,
                      kelompok_fiskal: str, metode_fiskal: str = "Garis Lurus",
                      bulan: int = 12, nbv_fiskal_awal: int = 0) -> PenyusutanResult:
    kom = penyusutan_komersial(harga_perolehan, residu, umur_komersial, bulan)
    fis, tarif, ket = penyusutan_fiskal(harga_perolehan, kelompok_fiskal,
                                        metode_fiskal, bulan, nbv_fiskal_awal)
    dasar_fiskal = nbv_fiskal_awal if nbv_fiskal_awal > 0 else harga_perolehan
    return PenyusutanResult(
        penyusutan_komersial=kom,
        penyusutan_fiskal=fis,
        selisih=kom - fis,
        nbv_komersial=harga_perolehan - kom,
        nbv_fiskal=dasar_fiskal - fis,
        metode_fiskal=metode_fiskal,
        tarif_fiskal=tarif,
        keterangan=ket,
    )


# ==========================================================================
# SANKSI & BUNGA
# ==========================================================================
def hitung_bunga_keterlambatan(pajak: int, bulan_terlambat: int,
                               suku_bunga_acuan: float = None) -> dict:
    """
    Bunga keterlambatan pembayaran pajak.
    Dasar hukum: UU HPP Pasal 9 ayat (2a)/(2b), PMK 81/2024.
    Bunga = (suku bunga acuan × (1 + 10%)) ÷ 12 × bulan terlambat
    """
    if suku_bunga_acuan is None:
        suku_bunga_acuan = config.BI_REFERENCE_RATE
    tarif_bulanan = suku_bunga_acuan * config.UPLIFT_FACTOR / 12
    bulan = max(0, bulan_terlambat)
    bunga = int(round(pajak * tarif_bulanan * bulan))
    return {
        "pajak_pokok": pajak,
        "suku_bunga_acuan": suku_bunga_acuan,
        "tarif_bulanan": tarif_bulanan,
        "bulan": bulan,
        "bunga": bunga,
        "total_bayar": pajak + bunga,
        "keterangan": (
            f"Bunga = {_persen(suku_bunga_acuan, 2)} × (1+10%) ÷ 12 × {bulan} bulan "
            f"= {_persen(tarif_bulanan, 4)} per bulan."
        ),
    }


def hitung_sanksi_telat_lapor(jenis_spt: str) -> dict:
    """Denda telat lapor SPT - Pasal 7 UU KUP."""
    peta = {
        "ppn": (config.SANCTION_LATE_SPT_MASA_PPN, "SPT Masa PPN"),
        "pph21": (config.SANCTION_LATE_SPT_MASA_LAIN, "SPT Masa PPh 21"),
        "pph23": (config.SANCTION_LATE_SPT_MASA_LAIN, "SPT Masa PPh 23/26"),
        "pph4": (config.SANCTION_LATE_SPT_MASA_LAIN, "SPT Masa PPh 4(2)"),
        "pph25": (config.SANCTION_LATE_SPT_MASA_LAIN, "SPT Masa PPh 25"),
        "badan": (config.SANCTION_LATE_SPT_TAHUNAN_BADAN, "SPT Tahunan PPh Badan"),
        "op": (config.SANCTION_LATE_SPT_TAHUNAN_OP, "SPT Tahunan PPh Orang Pribadi"),
    }
    denda, nama = peta.get(jenis_spt, (config.SANCTION_LATE_SPT_MASA_LAIN, jenis_spt))
    return {
        "jenis": nama,
        "denda": denda,
        "keterangan": f"Denda administrasi telat lapor {nama}: {rupiah(denda)} "
                      f"(Pasal 7 UU KUP).",
    }


def hitung_sanksi_kurang_bayar(pajak_kurang_bayar: int, bulan: int = 24) -> dict:
    """
    Sanksi bunga 2%/bulan (maksimal 24 bulan) atas SKPKB.
    Dasar hukum: Pasal 13 ayat (2) UU KUP.
    """
    bulan = min(max(0, bulan), 24)
    bunga = int(round(pajak_kurang_bayar * config.SANCTION_INTEREST_KUP_2PCT * bulan))
    return {
        "pokok": pajak_kurang_bayar,
        "bulan": bulan,
        "tarif_bulanan": config.SANCTION_INTEREST_KUP_2PCT,
        "bunga": bunga,
        "total": pajak_kurang_bayar + bunga,
        "keterangan": f"Sanksi administrasi 2%/bulan × {bulan} bulan (maksimal 24 bulan) "
                      "- Pasal 13 ayat (2) UU KUP.",
    }


# ==========================================================================
# REKONSILIASI FISKAL
# ==========================================================================
@dataclass
class RekonsiliasiResult:
    laba_komersial: int = 0
    koreksi_positif_otomatis: int = 0
    koreksi_negatif_otomatis: int = 0
    koreksi_positif_penyusutan: int = 0
    koreksi_negatif_penyusutan: int = 0
    koreksi_positif_manual: int = 0
    koreksi_negatif_manual: int = 0
    total_positif: int = 0
    total_negatif: int = 0
    neto_fiskal: int = 0
    kompensasi_rugi: int = 0
    pkp_sebelum_pembulatan: int = 0
    pkp: int = 0
    rincian: list = field(default_factory=list)
    catatan: list = field(default_factory=list)


def hitung_rekonsiliasi_fiskal(
    laba_komersial: int,
    non_deductible: int = 0,
    penghasilan_final: int = 0,
    penyusutan_komersial: int = 0,
    penyusutan_fiskal: int = 0,
    koreksi_positif_manual: int = 0,
    koreksi_negatif_manual: int = 0,
    kompensasi_rugi: int = 0,
) -> RekonsiliasiResult:
    """
    Jembatani laba komersial menjadi Penghasilan Kena Pajak.
    Dasar hukum: Pasal 4, 6, 9, 11 UU PPh; Pasal 17 ayat (4) UU PPh (pembulatan).
    """
    res = RekonsiliasiResult(laba_komersial=laba_komersial)
    res.koreksi_positif_otomatis = max(0, non_deductible)
    res.koreksi_negatif_otomatis = max(0, penghasilan_final)

    selisih_susut = penyusutan_komersial - penyusutan_fiskal
    if selisih_susut > 0:
        res.koreksi_positif_penyusutan = selisih_susut
    elif selisih_susut < 0:
        res.koreksi_negatif_penyusutan = -selisih_susut

    res.koreksi_positif_manual = max(0, koreksi_positif_manual)
    res.koreksi_negatif_manual = max(0, koreksi_negatif_manual)

    res.total_positif = (res.koreksi_positif_otomatis + res.koreksi_positif_penyusutan
                         + res.koreksi_positif_manual)
    res.total_negatif = (res.koreksi_negatif_otomatis + res.koreksi_negatif_penyusutan
                         + res.koreksi_negatif_manual)

    res.neto_fiskal = laba_komersial + res.total_positif - res.total_negatif
    res.kompensasi_rugi = min(max(0, kompensasi_rugi), max(0, res.neto_fiskal))
    res.pkp_sebelum_pembulatan = res.neto_fiskal - res.kompensasi_rugi
    res.pkp = round_down_thousand(max(0, res.pkp_sebelum_pembulatan))

    res.rincian = [
        ("Laba (Rugi) Komersial sebelum pajak", laba_komersial, ""),
        ("Koreksi positif - biaya non-deductible", res.koreksi_positif_otomatis,
         "Pasal 9 UU PPh: biaya yang tidak boleh dikurangkan"),
        ("Koreksi positif - penyusutan komersial > fiskal",
         res.koreksi_positif_penyusutan, "Perbedaan temporer (PMK 72/2023)"),
        ("Koreksi positif manual", res.koreksi_positif_manual, "Input pengguna"),
        ("Koreksi negatif - penghasilan final/bukan objek",
         res.koreksi_negatif_otomatis, "Dikeluarkan dari PKP tarif umum"),
        ("Koreksi negatif - penyusutan fiskal > komersial",
         res.koreksi_negatif_penyusutan, "Perbedaan temporer"),
        ("Koreksi negatif manual", res.koreksi_negatif_manual, "Input pengguna"),
        ("Penghasilan Neto Fiskal", res.neto_fiskal, ""),
        ("Kompensasi kerugian fiskal", -res.kompensasi_rugi,
         "Pasal 6 ayat (2) UU PPh - maksimal 5 tahun"),
        ("PKP sebelum pembulatan", res.pkp_sebelum_pembulatan, ""),
        ("PENGHASILAN KENA PAJAK", res.pkp,
         "Dibulatkan ke ribuan penuh ke bawah - Pasal 17 ayat (4) UU PPh"),
    ]
    if res.neto_fiskal < 0:
        res.catatan.append(
            f"Hasil fiskal berupa RUGI {rupiah(abs(res.neto_fiskal))}. Kerugian dapat "
            "dikompensasikan ke tahun pajak berikutnya selama maksimal 5 tahun "
            "(Pasal 6 ayat (2) UU PPh)."
        )
    return res


# ==========================================================================
# ANGSURAN PPh 25
# ==========================================================================
def hitung_pph25(pph_terutang_tahun_lalu: int, kredit_pajak: int = 0) -> dict:
    """
    Angsuran PPh Pasal 25 = (PPh terutang − kredit pajak) ÷ 12.
    Dasar hukum: Pasal 25 UU PPh.
    """
    dasar = max(0, pph_terutang_tahun_lalu - kredit_pajak)
    bulanan = int(round(dasar / 12))
    return {
        "dasar": dasar,
        "bulanan": bulanan,
        "tahunan": bulanan * 12,
        "keterangan": (f"Angsuran PPh 25 = ({rupiah(pph_terutang_tahun_lalu)} − "
                       f"{rupiah(kredit_pajak)}) ÷ 12 = {rupiah(bulanan)} per bulan. "
                       "Disetor paling lambat tanggal 15 setiap bulan."),
    }


# ==========================================================================
# PPh PASAL 15 — NORMA KHUSUS PELAYARAN & PENERBANGAN
# ==========================================================================
PPH15_JENIS = [
    ("pelayaran_dalam", "Pelayaran/Penerbangan Dalam Negeri", "1,35%",
     config.RATE_PPH15_PELAYARAN_DALAM,
     "KMK 416/KMK.04/1996 - norma penghitungan khusus pelayaran dalam negeri."),
    ("pelayaran_luar", "Pelayaran/Penerbangan Luar Negeri", "2,75%",
     config.RATE_PPH15_PELAYARAN_LUAR,
     "KMK 417/KMK.04/1996 - norma penghitungan khusus pelayaran luar negeri."),
    ("penerbangan_dalam", "Penerbangan Dalam Negeri", "1,8%",
     config.RATE_PPH15_PENERBANGAN_DALAM,
     "KMK 475/KMK.04/1996 - norma penghitungan khusus penerbangan dalam negeri."),
]


def hitung_pph15(jenis: str, peredaran_bruto: int) -> dict:
    """
    PPh Pasal 15 memakai norma: tarif tetap dikali peredaran bruto, tanpa
    menghitung laba. Dipakai perusahaan pelayaran/penerbangan tertentu.

    Dasar hukum: Pasal 15 UU PPh jo. KMK 416/417/475/KMK.04/1996.
    """
    baris = next((b for b in PPH15_JENIS if b[0] == jenis), None)
    if baris is None:
        raise ValueError("Jenis PPh 15 tidak dikenal.")
    _, nama, label, tarif, dasar = baris

    bruto = int(round(float(peredaran_bruto or 0)))
    if bruto < 0:
        raise ValueError("Peredaran bruto tidak boleh negatif.")
    pph = int(round(bruto * tarif))
    return {
        "jenis": jenis, "nama": nama, "tarif": tarif, "tarif_label": label,
        "peredaran_bruto": bruto, "pph_terutang": pph,
        "dasar_hukum": dasar,
        "keterangan": (f"{nama}: {label} × {rupiah(bruto)} = {rupiah(pph)}. "
                       f"Bersifat final sehingga tidak digabung ke PPh Badan. "
                       f"{dasar}"),
    }


# ==========================================================================
# BEA METERAI
# ==========================================================================
def hitung_meterai(nilai_dokumen: int, jumlah_berkas: int = 1) -> dict:
    """
    Bea meterai Rp10.000 untuk dokumen bernilai di atas Rp5 juta.
    Dokumen bernilai sampai Rp300.000 tidak dikenai; di atas Rp1 miliar
    tetap Rp10.000.

    Dasar hukum: UU No. 10/2020 tentang Bea Meterai, PP 86/2021.
    """
    nilai = int(round(float(nilai_dokumen or 0)))
    berkas = max(1, int(jumlah_berkas))
    kena = config.METERAI_BATAS_SEDERHANA < nilai
    if not kena:
        return {
            "nilai_dokumen": nilai, "kena": False, "per_berkas": 0,
            "jumlah_berkas": berkas, "total": 0,
            "keterangan": (f"Dokumen bernilai {rupiah(nilai)} tidak dikenai bea "
                           f"meterai karena tidak melebihi "
                           f"{rupiah(config.METERAI_BATAS_SEDERHANA)}. "
                           "Dasar: Pasal 3 UU No. 10/2020."),
        }
    per = config.METERAI_TARIF
    total = per * berkas
    return {
        "nilai_dokumen": nilai, "kena": True, "per_berkas": per,
        "jumlah_berkas": berkas, "total": total,
        "keterangan": (f"Bea meterai {rupiah(per)} × {berkas} berkas = "
                       f"{rupiah(total)}. Dikenakan karena nilai dokumen "
                       f"melebihi {rupiah(config.METERAI_BATAS_NILAI)}. "
                       "Dasar: Pasal 3 & 4 UU No. 10/2020, PP 86/2021."),
    }


# ==========================================================================
# PAJAK DAERAH (PBJT)
# ==========================================================================
def hitung_pbjt(jenis: str, dpp: int, tarif_persen: float = None) -> dict:
    """
    Pajak Barang dan Jasa Tertentu (PBJT) - pengganti PB1.
    Dipungut untuk makanan/minuman, hiburan, perhotelan, dan parkir.

    Dasar hukum: UU No. 1/2022 (HKPD) Pasal 55, tarif maksimal 10%.
    """
    baris = next((b for b in config.PBJT_JENIS if b[0] == jenis), None)
    if baris is None:
        raise ValueError("Jenis PBJT tidak dikenal.")
    _, nama, tarif_bawaan = baris
    tarif = (tarif_persen / 100) if tarif_persen is not None else tarif_bawaan

    dasar = int(round(float(dpp or 0)))
    pajak = int(round(dasar * tarif))
    return {
        "jenis": jenis, "nama": nama, "dpp": dasar,
        "tarif": tarif, "tarif_persen": round(tarif * 100, 2),
        "pajak": pajak,
        "keterangan": (f"{nama}: {round(tarif * 100, 2)}% × {rupiah(dasar)} = "
                       f"{rupiah(pajak)}. Pajak daerah dipungut terpisah dari "
                       "PPN. Dasar: Pasal 55 UU No. 1/2022 (HKPD)."),
    }


# ==========================================================================
# MATA UANG ASING
# ==========================================================================
def konversi_mata_uang(jumlah: float, kurs: float, dari: str = "USD") -> dict:
    """
    Konversi nilai valuta asing ke rupiah.
    Nilai pajak wajib dalam rupiah; kurs yang dipakai adalah kurs saat
    transaksi. Dasar hukum: PMK 196/PMK.03/2007, PSAK 52.
    """
    from_ = (dari or "USD").upper()
    if from_ == "IDR":
        return {"dari": "IDR", "kurs": 1, "jumlah_valas": float(jumlah),
                "jumlah_idr": int(round(float(jumlah or 0))),
                "keterangan": "Transaksi sudah dalam rupiah."}
    if kurs <= 0:
        raise ValueError("Kurs harus lebih besar dari nol.")
    idr = int(round(float(jumlah) * float(kurs)))
    return {
        "dari": from_, "kurs": float(kurs), "jumlah_valas": float(jumlah),
        "jumlah_idr": idr,
        "keterangan": (f"{from_} {jumlah:,.2f} × kurs {kurs:,.2f} = "
                       f"{rupiah(idr)}. Kurs mengikuti saat transaksi. "
                       "Dasar: PMK 196/PMK.03/2007, PSAK 52."),
    }


def selisih_kurs(jumlah_valas: float, kurs_awal: float, kurs_akhir: float,
                 akun_laba: bool = True) -> dict:
    """
    Hitung selisih kurs saat pelunasan piutang/utang valas.
    Selisih menguntungkan bila kurs akhir lebih tinggi dari kurs awal pada
    piutang, dan sebaliknya pada utang.

    Dasar hukum: PSAK 52, SE-02/PJ/2015.
    """
    awal = int(round(float(jumlah_valas) * float(kurs_awal)))
    akhir = int(round(float(jumlah_valas) * float(kurs_akhir)))
    selisih = akhir - awal
    return {
        "nilai_awal": awal, "nilai_akhir": akhir, "selisih": selisih,
        "laba": selisih > 0 if akun_laba else selisih < 0,
        "keterangan": (f"Nilai awal {rupiah(awal)} menjadi {rupiah(akhir)}; "
                       f"selisih kurs {rupiah(abs(selisih))} "
                       f"({'laba' if selisih > 0 else 'rugi'} kurs). "
                       "Dasar: PSAK 52."),
    }
