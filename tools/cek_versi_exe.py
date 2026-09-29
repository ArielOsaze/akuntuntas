"""
Baca versi yang tertanam di dalam berkas EXE.

Dipakai untuk memastikan berkas yang dibangun benar-benar membawa nomor
versi terbaru, bukan nomor lama yang tertinggal.

Cara pakai:
    python tools/cek_versi_exe.py [berkas.exe]
"""
from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
BAWAAN = AKAR / "dist" / "AkunTuntas" / "AkunTuntas.exe"


class VsFixedFileInfo(ctypes.Structure):
    """Struktur VS_FIXEDFILEINFO dari Windows."""

    _fields_ = [
        ("dwSignature", wintypes.DWORD),
        ("dwStrucVersion", wintypes.DWORD),
        ("dwFileVersionMS", wintypes.DWORD),
        ("dwFileVersionLS", wintypes.DWORD),
        ("dwProductVersionMS", wintypes.DWORD),
        ("dwProductVersionLS", wintypes.DWORD),
        ("dwFileFlagsMask", wintypes.DWORD),
        ("dwFileFlags", wintypes.DWORD),
        ("dwFileOS", wintypes.DWORD),
        ("dwFileType", wintypes.DWORD),
        ("dwFileSubtype", wintypes.DWORD),
        ("dwFileDateMS", wintypes.DWORD),
        ("dwFileDateLS", wintypes.DWORD),
    ]


def versi_tertanam(path: Path) -> tuple[int, int, int, int] | None:
    """Kembalikan versi tertanam sebagai empat angka, atau None bila gagal."""
    ver = ctypes.WinDLL("version")
    ukuran = ver.GetFileVersionInfoSizeW(str(path), None)
    if not ukuran:
        return None

    buf = ctypes.create_string_buffer(ukuran)
    if not ver.GetFileVersionInfoW(str(path), 0, ukuran, buf):
        return None

    penunjuk = ctypes.c_void_p()
    panjang = wintypes.UINT()
    if not ver.VerQueryValueW(buf, "\\", ctypes.byref(penunjuk),
                              ctypes.byref(panjang)):
        return None

    info = ctypes.cast(penunjuk, ctypes.POINTER(VsFixedFileInfo)).contents
    return (info.dwFileVersionMS >> 16,
            info.dwFileVersionMS & 0xFFFF,
            info.dwFileVersionLS >> 16,
            info.dwFileVersionLS & 0xFFFF)


def teks_versi(path: Path, nama: str) -> str:
    """Ambil satu kolom teks versi, misalnya FileVersion."""
    ver = ctypes.WinDLL("version")
    ukuran = ver.GetFileVersionInfoSizeW(str(path), None)
    if not ukuran:
        return ""
    buf = ctypes.create_string_buffer(ukuran)
    if not ver.GetFileVersionInfoW(str(path), 0, ukuran, buf):
        return ""

    penunjuk = ctypes.c_void_p()
    panjang = wintypes.UINT()
    kunci = f"\\StringFileInfo\\040904B0\\{nama}"
    if not ver.VerQueryValueW(buf, kunci, ctypes.byref(penunjuk),
                              ctypes.byref(panjang)):
        return ""
    return ctypes.wstring_at(penunjuk, panjang.value)


def utama() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else BAWAAN

    print("=" * 70)
    print("  VERSI TERTANAM DI BERKAS")
    print("=" * 70)

    if not path.exists():
        print(f"\n  berkas tidak ada: {path}")
        return 1

    print(f"\n  berkas : {path}")
    print(f"  ukuran : {path.stat().st_size:,} byte".replace(",", "."))

    v = versi_tertanam(path)
    if v is None:
        print("\n  versi tertanam tidak terbaca")
        return 1

    print(f"\n  versi  : {v[0]}.{v[1]}.{v[2]}.{v[3]}")

    for kolom in ("FileVersion", "ProductVersion", "FileDescription",
                  "CompanyName"):
        nilai = teks_versi(path, kolom)
        if nilai:
            print(f"  {kolom:16}: {nilai}")

    # Bandingkan dengan versi.json sebagai sumber kebenaran.
    import json
    baku = json.loads((AKAR / "versi.json").read_text(encoding="utf-8"))["versi"]
    harap = tuple(int(x) for x in (baku.split(".") + ["0", "0", "0"])[:4])
    cocok = v[:3] == harap[:3]
    print()
    print(f"  versi baku (versi.json): {baku}")
    print(f"  cocok                  : {cocok}")
    return 0 if cocok else 1


if __name__ == "__main__":
    sys.exit(utama())
