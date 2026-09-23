"""Siklus debug: jalankan seluruh rangkaian tes berulang kali sampai bersih.

Cara pakai:
    python tools/siklus_debug.py 15        # 15 putaran
    python tools/siklus_debug.py 15 --cepat  # lewati rangkaian berat

Setiap putaran membersihkan folder data sementara, menjalankan seluruh
rangkaian, lalu melaporkan putaran mana yang gagal beserta penyebabnya.
Laporan ringkas disimpan di tests/siklus_debug.txt.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
LAPORAN = AKAR / "tests" / "siklus_debug.txt"

# _contoh sengaja tidak dihapus: alat pemeriksa antarmuka membacanya.
FOLDER_SEMENTARA = [
    "_ujidata", "_ujiexe", "_uitest", "_uitest2", "_ujidialog",
    "_integrasi", "_ujipajak", "_ujipajak2", "_ujimode", "_verimode",
    "_ujisidebar",
    "_demo",
]

# Rangkaian ringan: cepat, dijalankan setiap putaran.
RANGKAIAN_RINGAN = [
    ("backend", "tests/test_semua_fitur.py"),
    ("pajak", "tests/test_kepatuhan_pajak.py"),
    ("pajak_baru", "tests/test_pajak_baru.py"),
    ("pajak_lanjut", "tests/test_pajak_lanjut.py"),
    ("halaman_pajak_lanjutan", "tests/test_halaman_pajak_lanjutan.py"),
    ("mode_sekali", "tests/test_mode_sekali.py"),
    ("sidebar_kelompok", "tests/test_sidebar_kelompok.py"),
    ("subkategori", "tests/test_subkategori.py"),
    ("ui", "tests/test_ui.py"),
    ("ui_mendalam", "tests/test_ui_mendalam.py"),
]

# Alat pemeriksa antarmuka: dijalankan setiap putaran (sudah cepat).
PEMERIKSA = [
    "periksa_garis_bawah.py",
    "periksa_garis_bawah_dialog.py",
    "periksa_istilah.py",
    "periksa_kontras.py",
    "periksa_kontras_dialog.py",
    "periksa_teks_ikon.py",
    "periksa_latar.py",
    "periksa_sidebar.py",
    "periksa_navbar.py",
    "periksa_himpit.py",
    "periksa_tata_letak.py",
    "periksa_tumpang_tindih.py",
    "periksa_kerapian_tabel.py",
    "periksa_integrasi.py",
    "periksa_jejak_ai.py",
    "audit_garis_bawah.py",
    "audit_tinggi_label.py",
    "audit_rich_text.py",
    "uji_semua_halaman.py",
    "uji_klik_tombol.py",
    "uji_dialog_simpan.py",
]


def bersihkan_folder():
    for nama in FOLDER_SEMENTARA:
        p = AKAR / nama
        if p.exists():
            shutil.rmtree(p, ignore_errors=True)


def jalankan(perintah: list[str], batas: int = 900):
    t0 = time.time()
    try:
        p = subprocess.run(perintah, cwd=str(AKAR), capture_output=True,
                           text=True, timeout=batas, encoding="utf-8",
                           errors="replace")
        keluaran = (p.stdout or "") + (p.stderr or "")
        return p.returncode, keluaran, time.time() - t0
    except subprocess.TimeoutExpired:
        return 124, f"LEWAT BATAS WAKTU ({batas} detik)", time.time() - t0


def ringkas(keluaran: str) -> str:
    """Ambil baris ringkasan hasil terakhir."""
    for pola in (r"HASIL AKHIR:.*", r"HASIL:.*", r"HASIL AKHIR.*"):
        cocok = re.findall(pola, keluaran)
        if cocok:
            return cocok[-1].strip()
    return ""


def periksa_lulus(nama: str, kode: int, keluaran: str) -> tuple[bool, str]:
    if kode != 0:
        # ambil baris kesalahan pertama yang berguna
        for baris in keluaran.splitlines():
            b = baris.strip()
            if b.startswith(("Traceback", "Error", "error:", "GAGAL")) or \
               "Error:" in b or "Gagal" in b:
                return False, f"exit={kode} — {b[:120]}"
        return False, f"exit={kode}"
    if "GAGAL" in keluaran and "0 GAGAL" not in keluaran:
        baris = [b.strip() for b in keluaran.splitlines() if "GAGAL" in b]
        return False, baris[0][:120] if baris else "ada kegagalan"
    return True, ringkas(keluaran)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("putaran", type=int, nargs="?", default=15)
    ap.add_argument("--cepat", action="store_true",
                    help="hanya rangkaian ringan, tanpa alat pemeriksa UI")
    arg = ap.parse_args()

    laporan: list[str] = []
    putaran_gagal = 0

    # Data contoh dibutuhkan alat pemeriksa antarmuka; buat sekali di awal.
    print("Menyiapkan data contoh...")
    kode, keluaran, detik = jalankan(
        [sys.executable, "tools/buat_data_contoh.py"], batas=600)
    if kode != 0:
        print("  GAGAL menyiapkan data contoh:")
        print("  " + "\n  ".join(keluaran.splitlines()[-6:]))
        return 2
    print(f"  data contoh siap ({detik:.1f}s)\n")

    for i in range(1, arg.putaran + 1):
        kepala = f"{'=' * 74}\nPUTARAN {i} dari {arg.putaran}  —  " \
                 f"{time.strftime('%H:%M:%S')}\n{'=' * 74}"
        print(kepala)
        laporan.append(kepala)
        bersihkan_folder()

        semua_lulus = True
        for nama, berkas in RANGKAIAN_RINGAN:
            kode, keluaran, detik = jalankan([sys.executable, berkas])
            lulus, pesan = periksa_lulus(nama, kode, keluaran)
            tanda = "LULUS" if lulus else "GAGAL"
            baris = f"  [{tanda}] {nama:26s} {detik:6.1f}s  {pesan}"
            print(baris)
            laporan.append(baris)
            if not lulus:
                semua_lulus = False
                simpan = AKAR / "tests" / f"gagal_{nama}_putaran{i}.txt"
                simpan.write_text(keluaran, encoding="utf-8")
                laporan.append(f"           detail: {simpan.name}")

        if not arg.cepat:
            for alat in PEMERIKSA:
                jalur = AKAR / "tools" / alat
                if not jalur.exists():
                    continue
                kode, keluaran, detik = jalankan(
                    [sys.executable, str(jalur)], batas=600)
                lulus, pesan = periksa_lulus(alat, kode, keluaran)
                tanda = "LULUS" if lulus else "GAGAL"
                baris = f"  [{tanda}] {alat:26s} {detik:6.1f}s  {pesan}"
                print(baris)
                laporan.append(baris)
                if not lulus:
                    semua_lulus = False

        if semua_lulus:
            print(f"  >> PUTARAN {i} BERSIH\n")
            laporan.append(f"  >> PUTARAN {i} BERSIH\n")
        else:
            putaran_gagal += 1
            print(f"  >> PUTARAN {i} ADA KEGAGALAN\n")
            laporan.append(f"  >> PUTARAN {i} ADA KEGAGALAN\n")

    akhir = (f"{'=' * 74}\n"
             f"RINGKASAN: {arg.putaran} putaran dijalankan, "
             f"{putaran_gagal} putaran bermasalah\n"
             f"{'=' * 74}")
    print(akhir)
    laporan.append(akhir)
    LAPORAN.write_text("\n".join(laporan), encoding="utf-8")
    print(f"Laporan lengkap: {LAPORAN}")
    return 1 if putaran_gagal else 0


if __name__ == "__main__":
    sys.exit(main())
