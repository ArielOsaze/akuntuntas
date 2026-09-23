"""
Periksa apakah klaim tabel perbandingan di situs cocok dengan kode aplikasi.

Tabel di web menjanjikan pembatasan tertentu untuk paket Standar. Bila
pembatasan itu tidak benar-benar ada di kode, pembeli Standar tetap bisa
memakai fitur tersebut dan janji di web menjadi keliru.

Pemeriksaan dilakukan dengan membaca kode aplikasi, bukan dengan
menjalankannya, supaya dapat dijalankan kapan saja tanpa menyiapkan data.

Tiga bentuk penjagaan yang dikenali:

1. Panggilan langsung, misalnya
   `batas_paket.boleh_pakai(lisensi, "multi_entitas")`.
2. Panggilan dengan argumen berupa variabel, misalnya
   `boleh_buka(self.lisensi, kode)` di dalam perulangan yang menelusuri
   daftar halaman Enterprise.
3. Penjagaan di dalam berkas batas_paket.py sendiri, yaitu nama bagian
   yang terdaftar pada BAGIAN_ENTERPRISE atau HALAMAN_ENTERPRISE.
"""
from __future__ import annotations

import pathlib
import re
import sys

AKAR = pathlib.Path(__file__).resolve().parent.parent
SUMBER = AKAR / "src" / "akuntansi_id"
BATAS = SUMBER / "ui" / "batas_paket.py"
JENDELA = SUMBER / "ui" / "main_window.py"

# Bagian yang diklaim hanya untuk Enterprise di tabel situs.
KLAIM = {
    "multi_entitas": "Beberapa badan usaha",
    "dimensi": "Dimensi biaya dan proyek",
    "konsolidasi": "Konsolidasi multi-entitas",
    "pajak_lanjutan": "Pajak lanjutan",
    "audit_lanjutan": "Log audit lanjutan",
}


def _argumen_panggilan(isi: str, nama_fungsi: str) -> list[str]:
    """
    Kumpulkan seluruh argumen dari setiap panggilan nama_fungsi.

    Tanda kurung dihitung berpasangan supaya argumen yang memuat panggilan
    lain, misalnya `boleh_pakai(f(x), "fitur")`, tetap terbaca utuh.
    """
    hasil = []
    pola = re.compile(rf"\b{nama_fungsi}\s*\(")
    for cocok in pola.finditer(isi):
        mulai = cocok.end()
        dalam = 1
        pos = mulai
        while pos < len(isi) and dalam > 0:
            if isi[pos] == "(":
                dalam += 1
            elif isi[pos] == ")":
                dalam -= 1
            pos += 1
        hasil.append(isi[mulai:pos - 1])
    return hasil


def penjaga_langsung(kode: str) -> list[str]:
    """Berkas yang memanggil boleh_pakai/boleh_buka dengan nama fitur ini."""
    hasil = []
    for berkas in SUMBER.rglob("*.py"):
        if berkas.name == "batas_paket.py":
            continue
        isi = berkas.read_text(encoding="utf-8", errors="ignore")
        for arg in (_argumen_panggilan(isi, "boleh_pakai")
                    + _argumen_panggilan(isi, "boleh_buka")):
            if f'"{kode}"' in arg or f"'{kode}'" in arg:
                hasil.append(berkas.relative_to(SUMBER).as_posix())
                break
    return hasil


def penjaga_perulangan(kode: str) -> bool:
    """
    Apakah fitur ini dijaga lewat perulangan daftar halaman Enterprise.

    Halaman lanjutan dijaga sekaligus di main_window.py dengan menelusuri
    HALAMAN_ENTERPRISE, sehingga nama fiturnya tidak muncul sebagai teks
    di dekat pemanggilan boleh_buka.
    """
    if not BATAS.exists() or not JENDELA.exists():
        return False
    isi_batas = BATAS.read_text(encoding="utf-8")
    if f'"{kode}"' not in isi_batas:
        return False
    # fitur harus terdaftar sebagai kunci di HALAMAN_ENTERPRISE
    blok = re.search(r"HALAMAN_ENTERPRISE\s*=\s*\{(.*?)\n\}", isi_batas, re.S)
    if not blok or f'"{kode}"' not in blok.group(1):
        return False
    isi_jendela = JENDELA.read_text(encoding="utf-8")
    return ("in batas_paket.HALAMAN_ENTERPRISE" in isi_jendela
            or "HALAMAN_ENTERPRISE" in isi_jendela)


def dipakai_di_kode(kode: str) -> list[str]:
    """Berkas yang menyebut nama fitur, di luar berkas batas paket."""
    hasil = []
    for berkas in SUMBER.rglob("*.py"):
        if berkas.name in ("batas_paket.py", "license.py"):
            continue
        isi = berkas.read_text(encoding="utf-8", errors="ignore")
        if f'"{kode}"' in isi:
            hasil.append(berkas.relative_to(SUMBER).as_posix())
    return hasil


def main() -> int:
    print("=" * 74)
    print("  KESESUAIAN KLAIM TABEL SITUS DENGAN KODE APLIKASI")
    print("=" * 74)
    print()

    tanpa_penjaga = []

    for kode, nama in KLAIM.items():
        print(f"[{kode}] {nama}")

        langsung = penjaga_langsung(kode)
        perulangan = penjaga_perulangan(kode)

        if langsung:
            print(f"  penjaga langsung : {', '.join(sorted(set(langsung)))}")
        if perulangan:
            print("  penjaga halaman  : main_window.py (perulangan HALAMAN_ENTERPRISE)")

        if langsung or perulangan:
            print("  kesimpulan       : DIJAGA")
        else:
            print("  kesimpulan       : TIDAK DIJAGA")
            tanpa_penjaga.append((kode, nama))

        print()

    print("=" * 74)
    if tanpa_penjaga:
        print(f"  {len(tanpa_penjaga)} KLAIM TIDAK DIJAGA:")
        for kode, nama in tanpa_penjaga:
            print(f"    - {kode}: {nama}")
        print()
        print("  Fitur seperti ini tidak boleh dicantumkan sebagai pembeda paket")
        print("  pada tabel situs, atau penjaganya harus ditambahkan lebih dahulu.")
    else:
        print("  SELURUH KLAIM DIJAGA DI KODE")
    print("=" * 74)

    return 1 if tanpa_penjaga else 0


if __name__ == "__main__":
    sys.exit(main())
