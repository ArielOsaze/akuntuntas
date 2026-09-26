"""
Debugging dengan cara berbeda: menguji alat verifikasi sendiri.

Cara ini belum pernah dipakai, dan berbeda dari semua cara sebelumnya.
Sebelumnya yang diperiksa adalah aplikasinya. Kali ini yang diperiksa
adalah alat verifikasinya: apakah pemeriksaannya benar benar dapat
menangkap kesalahan, atau hanya kebetulan selalu melaporkan cocok.

Metodenya disebut pengujian mutasi, dipakai oleh perkakas seperti mutmut
dan Cosmic Ray, serta pada pengujian mesin basis data seperti SQLite.
Caranya: satu angka atau tanda di kode aplikasi diubah dengan sengaja
menjadi salah, lalu alat verifikasi dijalankan. Bila verifikasi tetap
melaporkan semuanya cocok, berarti verifikasi itu tidak memeriksa bagian
tersebut. Perubahan yang lolos disebut mutan yang bertahan.

Setiap mutan yang bertahan menunjukkan satu titik yang tidak diperiksa.
Setelah daftarnya lengkap, titik titik itu ditambahkan ke alat verifikasi,
lalu mutannya diulang. Mutasi hanya menyentuh berkas di folder src,
selalu dikembalikan seperti semula, dan diverifikasi utuh pada akhirnya.

Cara pakai:
    python tools/uji_mutasi_pajak.py
    python tools/uji_mutasi_pajak.py --daftar
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
BERKAS_TARIF = AKAR / "src" / "akuntansi_id" / "config.py"
BERKAS_MESIN = AKAR / "src" / "akuntansi_id" / "core" / "tax_engine.py"
ALAT_VERIFIKASI = AKAR / "tools" / "verifikasi_independen_pajak.py"

# Batas waktu satu kali verifikasi, dalam detik.
BATAS_DETIK = 120


class Mutasi:
    """Satu perubahan yang sengaja dibuat salah pada kode."""

    def __init__(self, berkas: Path, baris: int, lama: str, baru: str,
                 keterangan: str):
        self.berkas = berkas
        self.baris = baris          # nomor baris, mulai dari 1
        self.lama = lama            # teks yang diganti
        self.baru = baru            # penggantinya, sengaja salah
        self.keterangan = keterangan


def daftar_mutasi() -> list[Mutasi]:
    """
    Susun daftar perubahan yang sengaja salah.

    Yang diubah adalah angka dan tanda pada rumus pajak, karena kesalahan
    pada bagian itu yang paling berbahaya: hasilnya tetap berupa angka yang
    terlihat wajar, tetapi jumlahnya salah. Bila verifikasi tidak menangkap
    perubahan seperti ini, artinya verifikasi tidak benar benar menghitung
    ulang.
    """
    return [
        # --- tarif PPh badan ---
        Mutasi(BERKAS_TARIF, 91, "RATE_CORPORATE = 0.22",
               "RATE_CORPORATE = 0.25",
               "tarif PPh badan diubah 22% jadi 25%"),
        Mutasi(BERKAS_TARIF, 97, "FACILITY_31E_DISCOUNT = 0.50",
               "FACILITY_31E_DISCOUNT = 0.30",
               "pengurangan Pasal 31E diubah 50% jadi 30%"),

        # --- PPh final UMKM ---
        Mutasi(BERKAS_TARIF, 111, "RATE_FINAL_UMKM = 0.005",
               "RATE_FINAL_UMKM = 0.01",
               "tarif final UMKM diubah 0,5% jadi 1%"),

        # --- PPN ---
        Mutasi(BERKAS_TARIF, 120, "RATE_VAT = 0.12",
               "RATE_VAT = 0.11",
               "tarif PPN diubah 12% jadi 11%"),
        Mutasi(BERKAS_TARIF, 126, "VAT_DPP_NILAI_LAIN_FACTOR = 11 / 12",
               "VAT_DPP_NILAI_LAIN_FACTOR = 10 / 12",
               "faktor DPP nilai lain diubah 11/12 jadi 10/12"),

        # --- PPh potong/pungut ---
        Mutasi(BERKAS_TARIF, 157, "RATE_PPH22_IMPORT = 0.025",
               "RATE_PPH22_IMPORT = 0.05",
               "tarif PPh 22 impor diubah 2,5% jadi 5%"),
        Mutasi(BERKAS_TARIF, 166,
               "RATE_PPH23_DIVIDEND_INTEREST_ROYALTY = 0.15",
               "RATE_PPH23_DIVIDEND_INTEREST_ROYALTY = 0.20",
               "tarif PPh 23 dividen diubah 15% jadi 20%"),
        Mutasi(BERKAS_TARIF, 167,
               "RATE_PPH23_SERVICES_RENT = 0.02",
               "RATE_PPH23_SERVICES_RENT = 0.03",
               "tarif PPh 23 jasa diubah 2% jadi 3%"),
        Mutasi(BERKAS_TARIF, 171, "RATE_PPH26 = 0.20",
               "RATE_PPH26 = 0.25",
               "tarif PPh 26 diubah 20% jadi 25%"),
        Mutasi(BERKAS_TARIF, 176,
               "RATE_PPH4_SEWA_TANAH_BANGUNAN = 0.10",
               "RATE_PPH4_SEWA_TANAH_BANGUNAN = 0.15",
               "tarif PPh 4(2) sewa diubah 10% jadi 15%"),
        Mutasi(BERKAS_TARIF, 177,
               "RATE_PPH4_KONSTRUKSI_KECIL = 0.0175",
               "RATE_PPH4_KONSTRUKSI_KECIL = 0.02",
               "tarif konstruksi kecil diubah 1,75% jadi 2%"),

        # --- lapisan tarif PPh 21 progresif ---
        Mutasi(BERKAS_MESIN, 0, "def pph21_progresif(pkp: int)",
               "def pph21_progresif(pkp: int)",
               "tempat menambah mutasi lapisan tarif"),
    ]


def baca_baris(berkas: Path, nomor: int) -> str:
    return berkas.read_text(encoding="utf-8").splitlines()[nomor - 1]


def periksa_mutasi(m: Mutasi) -> str:
    """
    Jalankan satu mutasi dan kembalikan hasilnya.

    Hasilnya salah satu dari:
      "tertangkap"  - verifikasi melaporkan ada beda, mutan terbunuh
      "bertahan"    - verifikasi tetap melaporkan cocok, mutan hidup
      "tidak jalan" - verifikasi gagal dijalankan, tidak dapat disimpulkan
    """
    asli = m.berkas.read_text(encoding="utf-8")
    if m.lama not in asli:
        return "tidak jalan"

    try:
        m.berkas.write_text(asli.replace(m.lama, m.baru, 1), encoding="utf-8")
        hasil = subprocess.run(
            [sys.executable, str(ALAT_VERIFIKASI)],
            capture_output=True, text=True, timeout=BATAS_DETIK,
            cwd=str(AKAR))
        keluaran = (hasil.stdout or "") + (hasil.stderr or "")
    except subprocess.TimeoutExpired:
        return "tidak jalan"
    finally:
        m.berkas.write_text(asli, encoding="utf-8")

    # Verifikasi yang gagal dijalankan tidak dapat dijadikan bukti.
    if "Traceback" in keluaran or "SyntaxError" in keluaran:
        return "tidak jalan"

    # Ada beda yang dilaporkan berarti mutan terbunuh.
    if "BEDA" in keluaran:
        return "tertangkap"
    if "COCOK" in keluaran:
        return "bertahan"
    return "tidak jalan"


def periksa_berkas_utuh() -> bool:
    """Pastikan seluruh berkas sumber kembali seperti semula."""
    hasil = subprocess.run(["git", "status", "--porcelain", "--", "src"],
                           capture_output=True, text=True, cwd=str(AKAR))
    kembali = not hasil.stdout.strip()
    return kembali


def main() -> int:
    print("=" * 76)
    print("  UJI MUTASI: APAKAH ALAT VERIFIKASI BENAR BENAR MEMERIKSA?")
    print("=" * 76)
    print()
    print("  Satu angka pada kode pajak diubah dengan sengaja, lalu alat")
    print("  verifikasi dijalankan. Bila verifikasi tetap melaporkan cocok,")
    print("  berarti bagian itu tidak diperiksa.")
    print()

    # Pastikan kode dalam keadaan bersih sebelum mulai.
    if not periksa_berkas_utuh():
        print("  Berkas di folder src sedang berubah. Simpan atau batalkan")
        print("  perubahannya lebih dulu, lalu jalankan ulang.")
        return 1

    # Entri dengan baris 0 masih berupa tempat kosong, dilewati.
    mutasi = [m for m in daftar_mutasi() if m.baris > 0]

    tertangkap = 0
    bertahan: list[Mutasi] = []
    tidak_jalan: list[Mutasi] = []

    for i, m in enumerate(mutasi, 1):
        baris = baca_baris(m.berkas, m.baris)
        if m.lama not in baris:
            print(f"  [{i:2d}/{len(mutasi)}] LEWAT   {m.keterangan}")
            print(f"            baris tidak cocok: {baris.strip()[:60]}")
            tidak_jalan.append(m)
            continue

        hasil = periksa_mutasi(m)
        if hasil == "tertangkap":
            tertangkap += 1
            print(f"  [{i:2d}/{len(mutasi)}] TERTANGKAP  {m.keterangan}")
        elif hasil == "bertahan":
            bertahan.append(m)
            print(f"  [{i:2d}/{len(mutasi)}] BERTAHAN    {m.keterangan}")
        else:
            tidak_jalan.append(m)
            print(f"  [{i:2d}/{len(mutasi)}] TIDAK JALAN {m.keterangan}")

    print()
    print("=" * 76)
    print(f"  mutasi diuji      : {len(mutasi)}")
    print(f"  tertangkap        : {tertangkap}")
    print(f"  bertahan          : {len(bertahan)}")
    print(f"  tidak dapat diuji : {len(tidak_jalan)}")
    print("=" * 76)

    if bertahan:
        print()
        print("  TITIK YANG TIDAK DIPERIKSA (perlu ditambahkan ke verifikasi):")
        for m in bertahan:
            print(f"    - {m.keterangan}")
            print(f"      {m.berkas.name}:{m.baris}")

    print()
    if periksa_berkas_utuh():
        print("  Berkas sumber kembali utuh seperti semula.")
    else:
        print("  PERINGATAN: ada berkas sumber yang belum kembali utuh!")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
