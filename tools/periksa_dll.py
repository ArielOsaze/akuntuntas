"""
Periksa kelengkapan DLL: pastikan semua pustaka yang dibutuhkan sudah dibundel.

Cara pakai:
    python tools/periksa_dll.py

Aplikasi yang dibundel PyInstaller kadang masih memanggil DLL dari sistem.
Bila DLL itu tidak ada di komputer pengguna, aplikasi gagal dibuka tanpa
pesan yang jelas. Alat ini menelusuri seluruh DLL di folder aplikasi, membaca
daftar impornya, lalu melaporkan pustaka yang tidak ditemukan di bundel dan
bukan bagian bawaan Windows.

DLL bawaan Windows (kernel32, user32, dan sejenisnya) dilewati karena selalu
tersedia di setiap komputer Windows.
"""

from __future__ import annotations

import struct
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
FOLDER = AKAR / "dist" / "AkunTuntas"

# Pustaka yang selalu ada di Windows dan tidak perlu dibundel
BAWAAN = {
    "kernel32.dll", "user32.dll", "gdi32.dll", "advapi32.dll", "shell32.dll",
    "ole32.dll", "oleaut32.dll", "comdlg32.dll", "comctl32.dll", "ws2_32.dll",
    "winmm.dll", "version.dll", "uxtheme.dll", "dwmapi.dll", "imm32.dll",
    "netapi32.dll", "userenv.dll", "wtsapi32.dll", "crypt32.dll", "secur32.dll",
    "bcrypt.dll", "ncrypt.dll", "dnsapi.dll", "iphlpapi.dll", "mpr.dll",
    "opengl32.dll", "glu32.dll", "setupapi.dll", "cfgmgr32.dll", "psapi.dll",
    "dbghelp.dll", "authz.dll", "shlwapi.dll", "winspool.drv", "rpcrt4.dll",
    "msvcrt.dll", "ntdll.dll", "powrprof.dll", "propsys.dll", "d3d11.dll",
    "dxgi.dll", "d2d1.dll", "dwrite.dll", "wldap32.dll", "normaliz.dll",
    "winhttp.dll", "wininet.dll", "urlmon.dll", "sechost.dll", "shcore.dll",
    "kernelbase.dll", "gdi32full.dll", "msvcp_win.dll", "ucrtbase.dll",
    "win32u.dll", "bcryptprimitives.dll", "cryptbase.dll", "profapi.dll",
    "user32.dll", "mswsock.dll", "wintrust.dll", "cabinet.dll", "imagehlp.dll",
    "pdh.dll", "wevtapi.dll", "dcomp.dll", "twinapi.dll", "coremessaging.dll",
    "wlanapi.dll", "bluetoothapis.dll", "avrt.dll", "mfplat.dll", "mf.dll",
    "mfreadwrite.dll", "mfuuid.dll", "evr.dll", "dsound.dll", "dxva2.dll",
}

# Awalan DLL sistem yang aman dilewati
AWALAN_SISTEM = ("api-ms-win-", "ext-ms-win-", "win32u", "ucrtbase")

# DLL yang berkaitan dengan perangkat keras atau grafis; bila tidak ada,
# Windows memakai cadangan perangkat lunak sehingga aplikasi tetap jalan
OPSIONAL = {
    "d3d12.dll", "d3d12core.dll", "dxcore.dll", "d3d9.dll", "d3d10.dll",
    "vulkan-1.dll", "opengl32.dll", "libegl.dll", "libglesv2.dll",
    "nvapi64.dll", "amdxc64.dll", "igd10iumd64.dll", "d3dcompiler_47.dll",
    "dxva2.dll", "mf.dll", "mfplat.dll", "mfreadwrite.dll", "mfuuid.dll",
    "evr.dll", "dsound.dll", "avrt.dll", "wlanapi.dll", "bluetoothapis.dll",
    "dwrite.dll", "d2d1.dll", "dcomp.dll", "dwmapi.dll", "uxtheme.dll",
}


def baca_impor(path: Path) -> list[str]:
    """Baca daftar DLL yang diimpor sebuah berkas PE."""
    try:
        d = path.read_bytes()
    except Exception:
        return []

    if len(d) < 0x40 or d[:2] != b"MZ":
        return []

    try:
        pe = struct.unpack_from("<I", d, 0x3C)[0]
        if d[pe:pe + 4] != b"PE\0\0":
            return []
        opt = pe + 24
        magic = struct.unpack_from("<H", d, opt)[0]
        dir_rva = opt + (112 if magic == 0x20b else 96)
        imp_rva, imp_ukuran = struct.unpack_from("<II", d, dir_rva)
        if imp_rva == 0 or imp_ukuran == 0:
            return []
        # jumlah entri impor = ukuran direktori / 20
        jumlah_entri = min(imp_ukuran // 20, 4096)

        nsek = struct.unpack_from("<H", d, pe + 6)[0]
        sek_off = opt + struct.unpack_from("<H", d, pe + 20)[0]

        def rva2off(rva: int):
            for i in range(nsek):
                o = sek_off + i * 40
                va = struct.unpack_from("<I", d, o + 12)[0]
                vs = struct.unpack_from("<I", d, o + 8)[0]
                raw = struct.unpack_from("<I", d, o + 20)[0]
                if va <= rva < va + vs:
                    return raw + (rva - va)
            return None

        hasil, off = [], rva2off(imp_rva)
        if off is None:
            return []
        for _ in range(jumlah_entri):
            entri = d[off:off + 20]
            if len(entri) < 20 or entri == b"\0" * 20:
                break
            nama_rva = struct.unpack_from("<I", entri, 12)[0]
            if nama_rva == 0:
                break
            no = rva2off(nama_rva)
            if no is None:
                break
            akhir = d.index(b"\0", no)
            nama = d[no:akhir].decode("ascii", "replace")
            # hanya nama DLL yang sah; data lain bisa terbaca sebagai nama
            if nama.lower().endswith((".dll", ".drv", ".ocx")) and len(nama) < 80:
                hasil.append(nama)
            off += 20
        return hasil
    except Exception:
        return []


def bawaan_windows(nama: str) -> bool:
    """Apakah DLL ini bagian bawaan Windows atau bersifat opsional?"""
    n = nama.lower()
    if n in BAWAAN or n in OPSIONAL:
        return True
    return any(n.startswith(a) for a in AWALAN_SISTEM)


def main() -> int:
    if not FOLDER.exists():
        print(f"folder aplikasi tidak ada: {FOLDER}")
        print("jalankan build lebih dahulu")
        return 1

    # daftar semua DLL yang dibundel, termasuk di subfolder
    tersedia = {}
    for f in FOLDER.rglob("*"):
        if f.is_file() and f.suffix.lower() in (".dll", ".pyd", ".exe", ".drv"):
            tersedia.setdefault(f.name.lower(), f)

    print(f"berkas diperiksa : {len(tersedia)}")

    hilang = {}
    diperiksa = 0
    for nama, path in sorted(tersedia.items()):
        for impor in baca_impor(path):
            diperiksa += 1
            n = impor.lower()
            if n in tersedia or bawaan_windows(n):
                continue
            hilang.setdefault(n, set()).add(nama)

    print(f"impor diperiksa  : {diperiksa}")
    print()

    if hilang:
        print(f"PUSTAKA TIDAK DITEMUKAN ({len(hilang)}):")
        for nama, pemakai in sorted(hilang.items()):
            contoh = ", ".join(sorted(pemakai)[:3])
            print(f"  - {nama}  (dipanggil oleh: {contoh})")
        print()
        print("Bila pustaka ini tidak ada di komputer pengguna, aplikasi")
        print("gagal dibuka. Tambahkan ke bundel atau pastikan tersedia.")
        return 1

    print("HASIL: seluruh pustaka yang dibutuhkan sudah dibundel")
    return 0


if __name__ == "__main__":
    sys.exit(main())
