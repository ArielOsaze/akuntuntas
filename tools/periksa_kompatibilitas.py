"""
Periksa kesiapan aplikasi untuk dijalankan di Windows 10 dan Windows 11.

Cara pakai:
    python tools/periksa_kompatibilitas.py

Pemeriksaan ini membaca berkas hasil build lalu memastikan:

  1. Arsitektur   - aplikasi 64-bit dan hanya dijalankan di Windows 64-bit.
  2. Versi minimum- aplikasi tidak memerlukan fitur yang hanya ada di
                    Windows 11, sehingga tetap jalan di Windows 10 1809+.
  3. Pustaka      - seluruh DLL yang dibutuhkan sudah ikut dibundel,
                    termasuk runtime Visual C++.
  4. Installer    - memeriksa versi Windows sebelum memasang dan memberi
                    pesan yang jelas bila terlalu lama.
"""

from __future__ import annotations

import struct
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
FOLDER = AKAR / "dist" / "AkunTuntas"
INSTALLER = AKAR / "installer_output" / "AkunTuntas-1.1.1-Setup.exe"
SKRIP = AKAR / "installer.iss"

NAMA_MESIN = {0x014c: "x86 (32-bit)", 0x8664: "x64 (64-bit)", 0xAA64: "ARM64"}

# Build Windows 10 versi 1809; Qt 6 memerlukan ini atau lebih baru
BUILD_MINIMUM = 17763

# Pustaka yang harus ada di bundel agar aplikasi dapat dibuka
WAJIB = {
    "python311.dll": "mesin Python",
    "Qt6Core.dll": "inti Qt",
    "Qt6Gui.dll": "antarmuka Qt",
    "Qt6Widgets.dll": "widget Qt",
    "sqlite3.dll": "basis data SQLite",
    "VCRUNTIME140.dll": "runtime Visual C++",
    "VCRUNTIME140_1.dll": "runtime Visual C++ tambahan",
}


def baca_header(path: Path) -> dict:
    """Baca header PE: arsitektur dan versi Windows minimum."""
    d = path.read_bytes()
    pe = struct.unpack_from("<I", d, 0x3C)[0]
    if d[pe:pe + 4] != b"PE\0\0":
        return {}
    mesin = struct.unpack_from("<H", d, pe + 4)[0]
    opt = pe + 24
    major_os, minor_os = struct.unpack_from("<HH", d, opt + 40)
    major_sub, minor_sub = struct.unpack_from("<HH", d, opt + 48)
    return {"mesin": mesin, "os_min": (major_os, minor_os),
            "subsistem": (major_sub, minor_sub)}


def periksa_arsitektur(temuan: list) -> None:
    """Aplikasi harus 64-bit karena Qt 6 tidak menyediakan versi 32-bit."""
    exe = FOLDER / "AkunTuntas.exe"
    if not exe.exists():
        temuan.append("AkunTuntas.exe tidak ditemukan; jalankan build dahulu")
        return

    h = baca_header(exe)
    jenis = NAMA_MESIN.get(h.get("mesin", 0), "tidak dikenal")
    print(f"  arsitektur aplikasi : {jenis}")
    print(f"  Windows minimum     : {h['os_min'][0]}.{h['os_min'][1]}")

    if h.get("mesin") != 0x8664:
        temuan.append(
            f"aplikasi bukan 64-bit ({jenis}); Qt 6 hanya tersedia untuk "
            f"Windows 64-bit")

    # versi subsistem 6.0 berarti Windows Vista ke atas; aman untuk Win 10
    if h["subsistem"][0] > 10:
        temuan.append(
            f"subsistem {h['subsistem'][0]}.{h['subsistem'][1]} memerlukan "
            f"Windows versi lebih baru")


def periksa_pustaka(temuan: list) -> None:
    """Seluruh pustaka wajib harus ada di bundel."""
    internal = FOLDER / "_internal"
    if not internal.exists():
        temuan.append("folder _internal tidak ditemukan")
        return

    for nama, keterangan in sorted(WAJIB.items()):
        ketemu = any(internal.rglob(nama))
        status = "ada" if ketemu else "TIDAK ADA"
        print(f"  {nama:22s} {keterangan:26s} {status}")
        if not ketemu:
            temuan.append(f"{nama} ({keterangan}) tidak dibundel")


def periksa_installer(temuan: list) -> None:
    """Installer harus memeriksa versi Windows dan memberi pesan jelas."""
    if not SKRIP.exists():
        temuan.append("installer.iss tidak ditemukan")
        return

    isi = SKRIP.read_text(encoding="utf-8", errors="ignore")

    if "MinVersion=10.0" not in isi:
        temuan.append("installer tidak membatasi versi Windows minimum")

    if "GetWindowsVersionEx" not in isi:
        temuan.append(
            "installer tidak memeriksa versi Windows, sehingga pengguna "
            "Windows lama tidak mendapat penjelasan")

    if str(BUILD_MINIMUM) not in isi:
        temuan.append(
            f"installer tidak menyebut build {BUILD_MINIMUM} "
            f"(Windows 10 versi 1809)")

    if "ArchitecturesAllowed" not in isi:
        temuan.append("installer tidak memeriksa arsitektur prosesor")

    print(f"  versi minimum    : Windows 10 build {BUILD_MINIMUM} (1809)")
    print("  pemeriksaan versi: ada" if "GetWindowsVersionEx" in isi
          else "  pemeriksaan versi: TIDAK ADA")
    print("  pemeriksaan CPU  : ada" if "ArchitecturesAllowed" in isi
          else "  pemeriksaan CPU  : TIDAK ADA")


def periksa_fitur_win11(temuan: list) -> None:
    """Pastikan tidak ada ketergantungan pada API khusus Windows 11."""
    internal = FOLDER / "_internal"
    if not internal.exists():
        return

    # Pustaka yang benar-benar hanya ada di Windows 11. Berkas gaya tampilan
    # Qt Quick (mis. FluentWinUI3StyleImpl) tidak dihitung: berkas itu tidak
    # dipanggil aplikasi ini dan tidak dimuat Qt Widgets.
    khusus = ("microsoft.ui.xaml", "microsoft.ui.dll", "d3d12core.dll",
              "winui3.dll", "microsoft.web.webview2")
    ketemu = []
    for nama in khusus:
        if any(internal.rglob(f"*{nama}*")):
            ketemu.append(nama)

    if ketemu:
        temuan.append(
            "ditemukan pustaka khusus Windows 11: " + ", ".join(ketemu))
    else:
        print("  pustaka khusus Windows 11 : tidak ada")


def main() -> int:
    print("=" * 68)
    print("KESESIAPAN WINDOWS 10 DAN WINDOWS 11")
    print("=" * 68)
    print()

    if not FOLDER.exists():
        print(f"folder aplikasi tidak ada: {FOLDER}")
        print("jalankan build lebih dahulu")
        return 1

    temuan: list = []

    print("1. ARSITEKTUR")
    periksa_arsitektur(temuan)
    print()

    print("2. PUSTAKA YANG DIBUNDEL")
    periksa_pustaka(temuan)
    print()

    print("3. INSTALLER")
    periksa_installer(temuan)
    print()

    print("4. KETERGANTUNGAN WINDOWS 11")
    periksa_fitur_win11(temuan)
    print()

    print("=" * 68)
    if temuan:
        print(f"TEMUAN ({len(temuan)}):")
        for t in temuan:
            print(f"  - {t}")
        return 1

    print("HASIL: siap dijalankan di Windows 10 (1809 ke atas) dan Windows 11")
    print("       pada komputer 64-bit")
    print("=" * 68)
    return 0


if __name__ == "__main__":
    sys.exit(main())
