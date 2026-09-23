"""
AkunTuntas - Konfigurasi Global, Konstanta Pajak & Akuntansi Indonesia
=======================================================================
Seluruh angka tarif di file ini mengacu pada peraturan resmi yang berlaku
untuk tahun pajak 2026. Setiap konstanta disertai dasar hukumnya.

Sumber resmi: pajak.go.id, peraturan.bpk.go.id, DSAK-IAI
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# --------------------------------------------------------------------------
# IDENTITAS APLIKASI
# --------------------------------------------------------------------------
APP_NAME = "AkunTuntas"
APP_LONG_NAME = "AkunTuntas - Pembukuan & Pajak Perusahaan Indonesia"
APP_VERSION = "1.0.0"
APP_BUILD = "2026.02"
APP_PUBLISHER = "AkunTuntas"
APP_EDITION = "Edisi Regulasi 2026"

# --------------------------------------------------------------------------
# LOKASI DATA (LOCAL DATABASE — tidak ada server, tidak ada cloud)
# --------------------------------------------------------------------------
def _default_data_dir() -> Path:
    """Direktori data aplikasi. Bisa dioverride lewat env AKUNTANSIID_DATA."""
    env = os.environ.get("AKUNTANSIID_DATA")
    if env:
        return Path(env)
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return base / "AkunTuntas"
    return Path.home() / ".akuntuntas"


DATA_DIR: Path = _default_data_dir()
DB_PATH: Path = DATA_DIR / "akuntuntas.db"
BACKUP_DIR: Path = DATA_DIR / "backup"
EXPORT_DIR: Path = DATA_DIR / "export"
LOG_PATH: Path = DATA_DIR / "akuntuntas.log"
ATTACH_DIR: Path = DATA_DIR / "lampiran"


# --------------------------------------------------------------------------
# ASET APLIKASI (ikon, logo) — di dalam paket saat sudah dibundel
# --------------------------------------------------------------------------
def _default_asset_dir() -> Path:
    dibundel = getattr(sys, "_MEIPASS", None)
    if dibundel:
        return Path(dibundel) / "assets"
    return Path(__file__).resolve().parent.parent.parent / "assets"


ASSET_DIR: Path = _default_asset_dir()
ICON_PATH: Path = ASSET_DIR / "app.ico"
LOGO_PATH: Path = ASSET_DIR / "app_256.png"


def ensure_dirs() -> None:
    for p in (DATA_DIR, BACKUP_DIR, EXPORT_DIR, ATTACH_DIR):
        p.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------------------------------
# TAHUN PAJAK & AMBANG BATAS
# --------------------------------------------------------------------------
DEFAULT_TAX_YEAR = 2026

# Ambang omzet Rp4,8 miliar.
# Dasar hukum: PMK 197/PMK.03/2013 jo. PP 44/2022 (batas pengusaha kecil,
# wajib dikukuhkan sebagai PKP bila peredaran bruto melebihi Rp4,8 M).
THRESHOLD_PKP = 4_800_000_000

# Batas omzet fasilitas Pasal 31E (Rp50 miliar).
# Dasar hukum: UU PPh Pasal 31E ayat (1), penjelasan SE-02/PJ/2015.
THRESHOLD_31E = 50_000_000_000

# Batas peredaran bruto tidak kena pajak PPh Final UMKM (Rp500 juta
# untuk Orang Pribadi). Dasar hukum: PP 55/2022 Pasal 3 ayat (2) jo. PP 20/2026.
THRESHOLD_FINAL_OP = 500_000_000


# --------------------------------------------------------------------------
# TARIF PPh BADAN
# --------------------------------------------------------------------------
# Tarif umum PPh Badan 22%.
# Dasar hukum: UU No. 7/2021 (UU HPP) Pasal 17 ayat (1) huruf b.
RATE_CORPORATE = 0.22

# Fasilitas Pasal 31E: pengurangan 50% dari tarif atas PKP yang berasal dari
# bagian peredaran bruto sampai Rp4,8 miliar, untuk badan dengan peredaran
# bruto sampai Rp50 miliar.
# Dasar hukum: UU PPh Pasal 31E.
FACILITY_31E_DISCOUNT = 0.50
RATE_31E_FACILITY = RATE_CORPORATE * (1 - FACILITY_31E_DISCOUNT)  # = 0,11
RATE_31E_NON_FACILITY = RATE_CORPORATE                            # = 0,22


# --------------------------------------------------------------------------
# PPh FINAL UMKM 0,5%
# --------------------------------------------------------------------------
# Dasar hukum: PP 55/2022, diubah oleh PP 20/2026 (mulai berlaku 2026).
# - Peredaran bruto sampai Rp4,8 M/tahun.
# - Untuk Orang Pribadi: bagian peredaran bruto sampai Rp500 juta tidak
#   dikenai pajak.
# - Bagi WP Badan tertentu (PT/CV/Firma/Koperasi/BUMDes) yang sudah memakai
#   PP 55/2022 sebelum 2026, masih dapat menyelesaikan masa transisi.
RATE_FINAL_UMKM = 0.005
FINAL_UMKM_MAX_YEARS = 7  # untuk OP; badan mengikuti ketentuan transisi


# --------------------------------------------------------------------------
# PPN
# --------------------------------------------------------------------------
# Tarif PPN 12% untuk tahun 2025+.
# Dasar hukum: UU No. 7/2021 (UU HPP) Pasal 7 ayat (1) huruf b.
RATE_VAT = 0.12

# Mekanisme DPP Nilai Lain untuk barang/jasa non-mewah:
#   PPN = 12% x DPP Nilai Lain, dengan DPP Nilai Lain = 11/12 x Harga Jual
#   => beban efektif 11%.
# Dasar hukum: PMK 131/PMK.03/2024.
VAT_DPP_NILAI_LAIN_FACTOR = 11 / 12          # 0,916666...
RATE_VAT_EFFECTIVE_NORMAL = RATE_VAT * VAT_DPP_NILAI_LAIN_FACTOR  # = 0,11

# Objek mewah tertentu (PPnBM/kendaraan mewah): DPP penuh, tarif 12%.
# Dasar hukum: PP 61/2020 jo. PMK 96/2025, PMK 131/2024.
RATE_VAT_LUXURY = 0.12

# PPN Final UMKM 1% (besaran tertentu) untuk pengusaha dengan peredaran bruto
# tertentu; tarif bergantung komoditas.
# Dasar hukum: PP 44/2022 Pasal 8, PMK 64/2022.
VAT_FINAL_RATES = {
    "Pedagang Eceran Tertentu": 0.011,
    "Jasa Kesenian/Entertainment": 0.02,
    "Jasa Katering": 0.01,
    "Perdagangan Kertas Rokok": 0.05,
    "Perdagangan Obat": 0.05,
}


# --------------------------------------------------------------------------
# PPh POTONG/PUNGUT
# --------------------------------------------------------------------------
# PPh Pasal 21 — skema Tarif Efektif Rata-rata (TER).
# Dasar hukum: PP 58/2023, PMK 168/PMK.03/2023 (berlaku 1 Januari 2024).
# Kategori TER bulanan: A, B, C (ditentukan oleh status PTKP).
TER_CATEGORY_A = "A"   # TK/0, K/0, K/1
TER_CATEGORY_B = "B"   # K/2, K/3
TER_CATEGORY_C = "C"   # K/I/0 sampai K/I/3

# PPh Pasal 22 (pemungutan).
# Dasar hukum: UU PPh Pasal 22, PMK 34/2017 jo. PMK 41/2022.
RATE_PPH22_IMPORT = 0.025          # impor dengan API
RATE_PPH22_IMPORT_NO_API = 0.075   # impor tanpa API
RATE_PPH22_BM = 0.075              # barang yang tidak dikuasai
RATE_PPH22_UMKM = 0.0025           # 0,25% pembelian oleh badan tertentu dari UMKM
RATE_PPH22_GOODS = 0.015           # penjualan barang (kertas, semen, baja, otomotif)
RATE_PPH22_PERTAMINA = 0.003       # pembelian BBM/BBG Pertamina

# PPh Pasal 23.
# Dasar hukum: UU PPh Pasal 23, PMK 141/PMK.03/2015 (jenis jasa).
RATE_PPH23_DIVIDEND_INTEREST_ROYALTY = 0.15
RATE_PPH23_SERVICES_RENT = 0.02

# PPh Pasal 26 (WP Luar Negeri): 20% dari jumlah bruto, atau tarif P3B.
# Dasar hukum: UU PPh Pasal 26.
RATE_PPH26 = 0.20

# PPh Pasal 4 ayat (2) — final.
# Dasar hukum: PP 34/2017 (sewa tanah/bangunan), PP 9/2022 (konstruksi),
#              PP 34/2016 (pengalihan tanah/bangunan), PP 19/2009 (bunga deposito).
RATE_PPH4_SEWA_TANAH_BANGUNAN = 0.10
RATE_PPH4_KONSTRUKSI_KECIL = 0.0175     # kualifikasi kecil, 1,75%
RATE_PPH4_KONSTRUKSI_MENENGAH = 0.02    # 2%
RATE_PPH4_KONSTRUKSI_BESAR = 0.0265     # 2,65%
RATE_PPH4_PENGALIHAN_TANAH = 0.025
RATE_PPH4_BUNGA_DEPOSITO = 0.20
RATE_PPH4_HADIAH_UNDIAN = 0.25
RATE_PPH4_DIVIDEN_OP = 0.10

# PPh Pasal 15 — norma khusus untuk pelayaran/penerbangan.
# Dasar hukum: UU PPh Pasal 15, KMK 416/KMK.04/1996 (pelayaran dalam negeri),
#              KMK 417/KMK.04/1996 (pelayaran/penebangan luar negeri).
RATE_PPH15_PELAYARAN_DALAM = 0.0135    # 1,35% dari peredaran bruto
RATE_PPH15_PELAYARAN_LUAR = 0.0275     # 2,75% dari peredaran bruto
RATE_PPH15_PENERBANGAN_DALAM = 0.018   # 1,8% dari peredaran bruto
RATE_PPH15_PENERBANGAN_LUAR = 0.0275   # 2,75% dari peredaran bruto

# PPh Pasal 25 — angsuran bulanan; dihitung dari PPh terutang tahun lalu
# dikurangi kredit pajar, dibagi 12.
# Dasar hukum: UU PPh Pasal 25.

# --------------------------------------------------------------------------
# BEA METERAI
# --------------------------------------------------------------------------
# Dasar hukum: UU No. 10/2020 tentang Bea Meterai, PP 86/2021.
METERAI_TARIF = 10_000                 # Rp10.000 per dokumen
METERAI_BATAS_NILAI = 5_000_000        # dokumen bernilai di atas Rp5 juta
METERAI_BATAS_SEDERHANA = 300_000      # dokumen bernilai s.d. Rp300.000 dikecualikan
METERAI_MAKSIMUM = 1_000_000           # batas nilai dokumen yang dikenai (Rp1 miliar
#                                        ke atas tetap Rp10.000)

# --------------------------------------------------------------------------
# PAJAK DAERAH (PB1 / PBJT)
# --------------------------------------------------------------------------
# Dasar hukum: UU No. 1/2022 (HKPD) Pasal 55 — PBJT makanan/minuman 10%.
RATE_PBJT_MAKANAN = 0.10               # maksimal 10% dari harga jual
RATE_PBJT_HIBURAN = 0.10
RATE_PBJT_PERHOTELAN = 0.10
RATE_PBJT_PARKIR = 0.10
PBJT_JENIS = [
    ("makanan_minuman", "Makanan & Minuman (PB1)", RATE_PBJT_MAKANAN),
    ("hiburan", "Hiburan (PBJT)", RATE_PBJT_HIBURAN),
    ("perhotelan", "Jasa Perhotelan (PBJT)", RATE_PBJT_PERHOTELAN),
    ("parkir", "Jasa Parkir (PBJT)", RATE_PBJT_PARKIR),
]

# --------------------------------------------------------------------------
# MATA UANG ASING
# --------------------------------------------------------------------------
# Dasar hukum: PSAK 52, PMK 196/PMK.03/2007 (kurs untuk keperluan pajak).
# Kurs disimpan per transaksi; nilai bawaan dipakai bila pengguna tidak mengisi.
MATA_UANG = ["IDR", "USD", "EUR", "SGD", "JPY", "CNY", "MYR", "AUD", "GBP"]
KURS_CONTOH = {           # indikatif; pengguna dapat mengubah di Pengaturan
    "USD": 16_000,
    "EUR": 17_300,
    "SGD": 11_900,
    "JPY": 105,
    "CNY": 2_200,
    "MYR": 3_600,
    "AUD": 10_500,
    "GBP": 20_200,
}


# --------------------------------------------------------------------------
# SANKSI ADMINISTRASI
# --------------------------------------------------------------------------
# Denda terlambat menyampaikan SPT.
# Dasar hukum: UU KUP Pasal 7 (UU No. 7/2021 UU HPP).
SANCTION_LATE_SPT_MASA_PPN = 100_000        # SPT Masa PPN
SANCTION_LATE_SPT_MASA_LAIN = 100_000       # SPT Masa PPh 21/23/dll
SANCTION_LATE_SPT_TAHUNAN_BADAN = 1_000_000
SANCTION_LATE_SPT_TAHUNAN_OP = 100_000

# Bunga terlambat/kurang bayar: suku bunga acuan + uplift 10%, dibagi 12.
# Dasar hukum: UU HPP Pasal 9 ayat (2a) & (2b), PMK 81/2024.
UPLIFT_FACTOR = 1.10   # +10% dari suku bunga acuan
BI_REFERENCE_RATE = 0.0575  # BI-Rate acuan (indikatif; dapat diubah di UI)

# Bunga keterlambatan pembayaran pajak (sanksi UP) = suku bunga acuan/12 * (1+10%)
# Contoh: 5,75% x 1,10 / 12 = 0,5271% per bulan.
LATE_INTEREST_MONTHLY = BI_REFERENCE_RATE * UPLIFT_FACTOR / 12

# Sanksi Pasal 13 ayat (2) KUP: bunga 2%/bulan maksimal 24 bulan untuk SKPKB.
SANCTION_INTEREST_KUP_2PCT = 0.02


# --------------------------------------------------------------------------
# DEADLINE PELAPORAN & PEMBAYARAN
# --------------------------------------------------------------------------
# Aturan umum (tanpa pengecualian hari libur).
DEADLINE_RULES = [
    # (kode, nama, aturan tenggat, deskripsi)
    ("ppn_setor", "Setor PPN Masa", "Akhir bulan berikutnya",
     "PPN kurang bayar disetor paling lambat akhir bulan berikutnya setelah Masa Pajak berakhir. Dasar: UU KUP Pasal 9 ayat (2a), PMK 81/2024."),
    ("ppn_lapor", "Lapor SPT Masa PPN", "Akhir bulan berikutnya",
     "SPT Masa PPN dilaporkan paling lambat akhir bulan berikutnya setelah Masa Pajak berakhir. Dasar: UU KUP Pasal 3 ayat (3) huruf b."),
    ("pph21_setor", "Setor PPh 21", "Tanggal 10 bulan berikutnya",
     "PPh 21 disetor paling lambat tanggal 10 bulan berikutnya. Dasar: UU KUP Pasal 9, PMK 81/2024."),
    ("pph21_lapor", "Lapor SPT Masa PPh 21", "Tanggal 20 bulan berikutnya",
     "SPT Masa PPh 21 dilaporkan paling lambat tanggal 20 bulan berikutnya. Dasar: UU KUP Pasal 3 ayat (3) huruf b."),
    ("pph23_setor", "Setor PPh 23/26", "Tanggal 10 bulan berikutnya",
     "PPh 23/26 disetor paling lambat tanggal 10 bulan berikutnya."),
    ("pph23_lapor", "Lapor SPT Masa PPh 23/26", "Tanggal 20 bulan berikutnya",
     "SPT Masa PPh 23/26 dilaporkan paling lambat tanggal 20 bulan berikutnya."),
    ("pph4_setor", "Setor PPh 4(2) & Final", "Tanggal 10 bulan berikutnya",
     "PPh Final disetor paling lambat tanggal 10 bulan berikutnya (PPh Final 0,5% UMKM: tanggal 15)."),
    ("pph25_setor", "Setor PPh 25", "Tanggal 15 bulan berikutnya",
     "Angsuran PPh 25 disetor paling lambat tanggal 15 bulan berikutnya."),
    ("spt_badan", "Lapor SPT Tahunan Badan", "4 bulan setelah akhir tahun pajak",
     "SPT Tahunan PPh Badan dilaporkan paling lambat akhir bulan ke-4 (30 April). Dasar: UU KUP Pasal 3 ayat (3) huruf a."),
    ("spt_op", "Lapor SPT Tahunan Orang Pribadi", "3 bulan setelah akhir tahun pajak",
     "SPT Tahunan OP dilaporkan paling lambat akhir bulan ke-3 (31 Maret)."),
]


# --------------------------------------------------------------------------
# BENTUK BADAN USAHA
# --------------------------------------------------------------------------
ENTITY_TYPES = {
    "umkm_op": {
        "kode": "umkm_op",
        "nama": "Usaha Mikro/Kecil/Menengah (Orang Pribadi)",
        "singkat": "UMKM OP",
        "sak": "SAK EMKM",
        "laporan": ["Neraca", "Laba Rugi", "CALK"],
        "deskripsi": (
            "Usaha perseorangan (tanpa badan hukum). Pemilik dan usaha adalah satu kesatuan "
            "ekonomi; modal disajikan sebagai 'Modal Pemilik' dan penarikan pribadi dicatat "
            "sebagai 'Prive'. Kewajiban pembukuan: Pasal 28 UU KUP - wajib menyelenggarakan "
            "pembukuan bila peredaran bruto dari usaha > Rp4,8 miliar, atau menyelenggarakan "
            "pencatatan bila di bawah ambang tersebut (Pasal 28 ayat 7 jo. PMK 54/2021)."
        ),
        "pajak_default": "PPh Final UMKM 0,5% (bila memenuhi syarat) atau tarif Pasal 17 OP",
    },
    "pt_perorangan": {
        "kode": "pt_perorangan",
        "nama": "Perseroan Perorangan",
        "singkat": "PT Perorangan",
        "sak": "SAK EMKM / SAK EP",
        "laporan": ["Neraca", "Laba Rugi", "CALK"],
        "deskripsi": (
            "Badan hukum perseroan terbatas yang didirikan oleh satu orang (WNI) dengan "
            "kriteria Usaha Mikro/Kecil. Dasar hukum: UU No. 11/2020 jo. UU No. 6/2023 "
            "(Cipta Kerja), PP 8/2021. Tanggung jawab terbatas; modal disetor wajib "
            "dinyatakan. Tidak ada kewajiban membentuk organ komisaris."
        ),
        "pajak_default": "PPh Badan Pasal 31E atau PPh Final 0,5% (sesuai syarat PP 20/2026)",
    },
    "pt": {
        "kode": "pt",
        "nama": "Perseroan Terbatas (PT)",
        "singkat": "PT",
        "sak": "SAK Umum / PSAK / SAK EP",
        "laporan": ["Neraca", "Laba Rugi", "Perubahan Ekuitas", "Arus Kas", "CALK"],
        "deskripsi": (
            "Badan hukum perseroan terbatas. Dasar hukum: UU No. 40/2007 jo. UU No. 6/2023. "
            "Kewajiban: pembukuan lengkap (Pasal 28 UU KUP), penyimpanan dokumen 10 tahun "
            "(UU No. 8/1997 tentang Dokumen Perusahaan), RUPS tahunan. Laporan keuangan "
            "mengikuti SAK yang berlaku (SAK Umum untuk entitas dengan akuntabilitas publik, "
            "SAK EP untuk entitas privat)."
        ),
        "pajak_default": "PPh Badan Pasal 31E (tarif 22%, fasilitas 11% s.d. omzet Rp50 M)",
    },
    "cv": {
        "kode": "cv",
        "nama": "Persekutuan Komanditer (CV)",
        "singkat": "CV",
        "sak": "SAK EMKM / SAK EP",
        "laporan": ["Neraca", "Laba Rugi", "CALK"],
        "deskripsi": (
            "Persekutuan yang terdiri dari sekutu komplementer dan sekutu komanditer. "
            "Badan hukum bukan badan hukum murni. Dasar hukum: KUHD Pasal 19-21 jo. "
            "PP 8/2021. Pajak: PPh Badan bagi persekutuan (bukan final UMKM kecuali "
            "memenuhi syarat transisi PP 55/2022)."
        ),
        "pajak_default": "PPh Badan Pasal 31E",
    },
    "koperasi": {
        "kode": "koperasi",
        "nama": "Koperasi",
        "singkat": "Koperasi",
        "sak": "SAK EMKM / SAK EP",
        "laporan": ["Neraca", "Laba Rugi", "CALK"],
        "deskripsi": (
            "Badan usaha berlandaskan asas kekeluargaan. Dasar hukum: UU No. 25/1992 jo. "
            "UU No. 6/2023. Pajak: dapat memakai PPh Final 0,5% bila memenuhi syarat "
            "(PP 20/2026), dengan pengecualian atas penghasilan dari anggota tertentu."
        ),
        "pajak_default": "PPh Final 0,5% atau PPh Badan Pasal 31E",
    },
}


# --------------------------------------------------------------------------
# FITUR YANG RELEVAN PER BENTUK BADAN USAHA
# --------------------------------------------------------------------------
# Setiap bentuk badan punya kebutuhan berbeda. Orang pribadi misalnya tidak
# mengenal RUPS, dividen, atau laporan perubahan ekuitas; koperasi punya
# simpanan anggota dan SHU; PT punya kewajiban RUPS dan pembagian dividen.
# Menu yang tidak relevan disembunyikan agar antarmuka tetap bersih dan
# pengguna tidak melihat fitur yang tidak dipakai bentuk usahanya.
#
# Kunci fitur memakai kode menu di sidebar. Fitur yang tidak disebut di sini
# dianggap relevan untuk semua bentuk badan.
FITUR_PER_BENTUK = {
    "umkm_op": {
        # orang pribadi: tanpa badan hukum, tanpa organ perseroan
        "tidak_ada": {
            "konsolidasi",   # tidak ada entitas anak
            "payroll",       # pemilik bekerja sendiri, tanpa karyawan tetap
        },
        "pajak": "PPh Final UMKM 0,5% atau tarif Pasal 17 Orang Pribadi",
        "laporan": ["Neraca", "Laba Rugi", "CALK"],
    },
    "pt_perorangan": {
        "tidak_ada": {
            "konsolidasi",   # entitas tunggal
        },
        "pajak": "PPh Badan Pasal 31E atau PPh Final 0,5%",
        "laporan": ["Neraca", "Laba Rugi", "CALK"],
    },
    "pt": {
        "tidak_ada": set(),
        "pajak": "PPh Badan Pasal 31E (22%, fasilitas 11% s.d. omzet Rp50 M)",
        "laporan": ["Neraca", "Laba Rugi", "Perubahan Ekuitas", "Arus Kas",
                    "CALK"],
    },
    "cv": {
        "tidak_ada": set(),
        "pajak": "PPh Badan Pasal 31E",
        "laporan": ["Neraca", "Laba Rugi", "CALK"],
    },
    "koperasi": {
        "tidak_ada": set(),
        "pajak": "PPh Final 0,5% atau PPh Badan Pasal 31E",
        "laporan": ["Neraca", "Laba Rugi", "CALK"],
    },
}


def fitur_tersedia(bentuk: str) -> set:
    """Kode menu yang tersedia untuk bentuk badan tertentu."""
    semua = {"dashboard", "analisis", "pencarian", "jurnal", "penjualan",
             "pembelian", "biaya", "bank", "mitra", "produk", "aset",
             "payroll", "dimensi", "periode", "konsolidasi", "laporan",
             "pajak", "pajak_lanjutan", "checklist", "pengguna", "audit",
             "recycle", "impor", "coa", "perusahaan", "lan", "pengaturan",
             "bantuan"}
    tidak_ada = FITUR_PER_BENTUK.get(bentuk, {}).get("tidak_ada", set())
    return semua - tidak_ada


def fitur_tidak_relevan(bentuk: str) -> set:
    """
    Kode menu yang tidak dipakai bentuk badan tertentu.

    Hasilnya berupa salinan. Pemanggil sering menambah isinya sesuai
    keadaan lain, dan tanpa salinan penambahan itu akan mengubah data
    bawaan sehingga memengaruhi semua pemakaian berikutnya.
    """
    return set(FITUR_PER_BENTUK.get(bentuk, {}).get("tidak_ada", set()))


# --------------------------------------------------------------------------
# STATUS PTKP (Penghasilan Tidak Kena Pajak) untuk PPh 21
# --------------------------------------------------------------------------
# Dasar hukum: PMK 101/PMK.010/2016 (masih berlaku).
PTKP_ANNUAL = {
    "TK/0": 54_000_000,
    "TK/1": 58_500_000,
    "TK/2": 63_000_000,
    "TK/3": 67_500_000,
    "K/0":  58_500_000,
    "K/1":  63_000_000,
    "K/2":  67_500_000,
    "K/3":  72_000_000,
    "K/I/0": 112_500_000,
    "K/I/1": 117_000_000,
    "K/I/2": 121_500_000,
    "K/I/3": 126_000_000,
}

PTKP_LABELS = {
    "TK/0": "Tidak Kawin, 0 tanggungan",
    "TK/1": "Tidak Kawin, 1 tanggungan",
    "TK/2": "Tidak Kawin, 2 tanggungan",
    "TK/3": "Tidak Kawin, 3 tanggungan",
    "K/0":  "Kawin, 0 tanggungan",
    "K/1":  "Kawin, 1 tanggungan",
    "K/2":  "Kawin, 2 tanggungan",
    "K/3":  "Kawin, 3 tanggungan",
    "K/I/0": "Kawin, Istri berpenghasilan, 0 tanggungan",
    "K/I/1": "Kawin, Istri berpenghasilan, 1 tanggungan",
    "K/I/2": "Kawin, Istri berpenghasilan, 2 tanggungan",
    "K/I/3": "Kawin, Istri berpenghasilan, 3 tanggungan",
}

# Kategori TER (Tarif Efektif Rata-rata) — PMK 168/PMK.03/2023 Lampiran I.
# Pemetaan mengikuti pengelompokan PTKP yang sama:
#   Kategori A  TK/0 (Rp54 jt), TK/1 & K/0 (Rp58,5 jt)
#   Kategori B  TK/2 & K/1 (Rp63 jt), TK/3 & K/2 (Rp67,5 jt)
#   Kategori C  K/3 (Rp72 jt), dan K/I/0 sampai K/I/3
TER_CATEGORY_MAP = {
    # Kategori A
    "TK/0": "A",
    "TK/1": "A",
    "K/0":  "A",
    # Kategori B
    "TK/2": "B",
    "K/1":  "B",
    "TK/3": "B",
    "K/2":  "B",
    # Kategori C
    "K/3":   "C",
    "K/I/0": "C",
    "K/I/1": "C",
    "K/I/2": "C",
    "K/I/3": "C",
}

# Tarif progresif Pasal 17 untuk Orang Pribadi.
# Dasar hukum: UU HPP Pasal 17 ayat (1) huruf a.
PPH21_BRACKETS = [
    (60_000_000, 0.05),
    (250_000_000, 0.15),
    (500_000_000, 0.25),
    (5_000_000_000, 0.30),
    (float("inf"), 0.35),
]

# Biaya jabatan: 5% dari penghasilan bruto, maksimum Rp500.000/bulan
# atau Rp6.000.000/tahun.
# Dasar hukum: PMK 250/PMK.03/2008.
BIYA_JABATAN_RATE = 0.05
BIYA_JABATAN_MAX_MONTHLY = 500_000
BIYA_JABATAN_MAX_ANNUAL = 6_000_000

# BPJS Kesehatan: 5% dari upah (4% pemberi kerja, 1% pekerja); batas atas
# upah Rp12 juta. BPJS Ketenagakerjaan: JKK 0,24%-1,74%, JKM 0,3%,
# JHT 5,7% (3,7% pemberi kerja + 2% pekerja), JP 3% (2% + 1%) batas upah
# tertentu. Dasar hukum: Perpres 64/2020, PP 44/2015, PP 46/2015.
BPJS_KES_EMPLOYER = 0.04
BPJS_KES_EMPLOYEE = 0.01
BPJS_KES_WAGE_CAP = 12_000_000
BPJS_JHT_EMPLOYER = 0.037
BPJS_JHT_EMPLOYEE = 0.02
BPJS_JKM = 0.003
BPJS_JKK_DEFAULT = 0.0024
BPJS_JP_EMPLOYER = 0.02
BPJS_JP_EMPLOYEE = 0.01
BPJS_JP_WAGE_CAP = 10_547_400  # batas atas upah JP 2026 (indikatif, dapat diubah)


# --------------------------------------------------------------------------
# PENYUSUTAN FISKAL
# --------------------------------------------------------------------------
# Kelompok aset tetap bukan bangunan (metode garis lurus & saldo menurun).
# Dasar hukum: PMK 72/PMK.03/2023 (perubahan PMK 96/PMK.03/2009).
FISCAL_ASSET_GROUPS = {
    "Kelompok 1": {
        "masa": 4, "garis_lurus": 0.25, "saldo_menurun": 0.50,
        "contoh": "Meja & kursi, komputer, printer, AC, kendaraan roda dua, alat kantor kecil",
    },
    "Kelompok 2": {
        "masa": 8, "garis_lurus": 0.125, "saldo_menurun": 0.25,
        "contoh": "Mobil, mesin industri, perabot besar, alat komunikasi, pompa, genset",
    },
    "Kelompok 3": {
        "masa": 16, "garis_lurus": 0.0625, "saldo_menurun": 0.125,
        "contoh": "Mesin berat, kapal kecil, alat pertambangan, peralatan pabrik besar",
    },
    "Kelompok 4": {
        "masa": 20, "garis_lurus": 0.05, "saldo_menurun": 0.10,
        "contoh": "Bangunan non-permanen, kapal besar, alat berat konstruksi, rel",
    },
    "Bangunan Permanen": {
        "masa": 20, "garis_lurus": 0.05, "saldo_menurun": None,
        "contoh": "Bangunan permanen (hanya garis lurus sesuai PMK 72/2023)",
    },
    "Bangunan Tidak Permanen": {
        "masa": 10, "garis_lurus": 0.10, "saldo_menurun": None,
        "contoh": "Bangunan tidak permanen (hanya garis lurus)",
    },
    "Tanah": {
        "masa": 0, "garis_lurus": 0.0, "saldo_menurun": None,
        "contoh": "Tanah - tidak disusutkan",
    },
}


# --------------------------------------------------------------------------
# KONFIGURASI UI
# --------------------------------------------------------------------------
CURRENCY_SYMBOL = "Rp"
CURRENCY_LOCALE = "id_ID"
DATE_FORMAT = "dd/MM/yyyy"
MONTH_NAMES_ID = [
    "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember",
]
MONTH_ABBR_ID = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun",
                 "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]

# Password default akun admin (user WAJIB mengganti saat login pertama)
DEFAULT_ADMIN_USER = "admin"
DEFAULT_ADMIN_PASSWORD = "admin123"
MIN_PASSWORD_LENGTH = 8

# Batas percobaan login sebelum akun terkunci sementara
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_SECONDS = 300
