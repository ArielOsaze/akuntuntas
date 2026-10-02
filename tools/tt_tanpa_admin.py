"""
Jalankan aplikasi dengan hak pengguna biasa, melewati permintaan elevasi.

TikTok LIVE Studio memakai manifes "highestAvailable". Pada akun
Administrator, Windows akan menjalankannya elevated. Akibatnya aplikasi
lain yang berjalan biasa tidak bisa mengendalikannya, karena Windows
memblokir masukan antar tingkat hak yang berbeda.

Windows menyediakan cara resmi untuk mengabaikan permintaan elevasi:
menambahkan tanda RUNASINVOKER pada daftar kompatibilitas aplikasi di
registry pengguna. Tanda ini bisa dihapus kapan saja.

Cara pakai:
    python tools/tt_tanpa_admin.py --pasang     (tambah tanda)
    python tools/tt_tanpa_admin.py --lepas      (hapus tanda)
    python tools/tt_tanpa_admin.py --lihat      (lihat tanda sekarang)
"""
from __future__ import annotations

import subprocess
import sys

KUNCI = (r"HKCU:\Software\Microsoft\Windows NT\CurrentVersion"
         r"\AppCompatFlags\Layers")
BERKAS = [
    r"C:\Program Files\TikTok LIVE Studio\TikTok LIVE Studio.exe",
    r"C:\Program Files\TikTok LIVE Studio\TikTok LIVE Studio Launcher.exe",
]


def jalankan(perintah: list[str]) -> tuple[int, str, str]:
    hasil = subprocess.run(perintah, capture_output=True, text=True,
                           timeout=120)
    return hasil.returncode, hasil.stdout.strip(), hasil.stderr.strip()


def lihat() -> int:
    print("=== TANDA KOMPATIBILITAS SEKARANG ===")
    kode, keluar, galat = jalankan([
        "powershell", "-NoProfile", "-Command",
        f"$p='{KUNCI}'; "
        f"if (Test-Path $p) {{ "
        f"  $k = Get-ItemProperty -Path $p; "
        f"  $k.PSObject.Properties | "
        f"  Where-Object {{ $_.Name -like '*TikTok*' }} | "
        f"  ForEach-Object {{ Write-Output \"$($_.Name) = $($_.Value)\" }} "
        f"}} else {{ Write-Output '(kunci belum ada)' }}"
    ])
    if galat:
        print(f"  galat: {galat}")
        return 1
    if keluar:
        for baris in keluar.splitlines():
            print(f"  {baris}")
    else:
        print("  (belum ada tanda untuk TikTok)")
    return 0


def pasang() -> int:
    print("=== MEMASANG TANDA RUNASINVOKER ===")
    for berkas in BERKAS:
        kode, keluar, galat = jalankan([
            "powershell", "-NoProfile", "-Command",
            f"$p='{KUNCI}'; "
            f"if (-not (Test-Path $p)) {{ New-Item -Path $p -Force | Out-Null }}; "
            f"New-ItemProperty -Path $p -Name '{berkas}' "
            f"-Value 'RUNASINVOKER' -PropertyType String -Force | Out-Null; "
            f"Write-Output 'ok'"
        ])
        nama = berkas.split("\\")[-1]
        if kode == 0 and "ok" in keluar:
            print(f"  {nama}: tanda dipasang")
        else:
            print(f"  {nama}: GAGAL  {galat}")
            return 1

    print()
    print("  Artinya: aplikasi akan berjalan dengan hak pengguna biasa,")
    print("  sehingga bisa dikendalikan dan bisa menangkap jendela biasa.")
    print("  Tanda ini bisa dihapus dengan: --lepas")
    return 0


def lepas() -> int:
    print("=== MENGHAPUS TANDA RUNASINVOKER ===")
    for berkas in BERKAS:
        kode, keluar, galat = jalankan([
            "powershell", "-NoProfile", "-Command",
            f"$p='{KUNCI}'; "
            f"if (Test-Path $p) {{ "
            f"  Remove-ItemProperty -Path $p -Name '{berkas}' "
            f"  -ErrorAction SilentlyContinue; "
            f"}}; Write-Output 'ok'"
        ])
        nama = berkas.split("\\")[-1]
        if kode == 0:
            print(f"  {nama}: tanda dihapus")
        else:
            print(f"  {nama}: GAGAL  {galat}")
            return 1
    return 0


def utama() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in (
            "--pasang", "--lepas", "--lihat"):
        print(__doc__)
        return 1

    if sys.argv[1] == "--lihat":
        return lihat()
    if sys.argv[1] == "--pasang":
        return pasang()
    return lepas()


if __name__ == "__main__":
    sys.exit(utama())
