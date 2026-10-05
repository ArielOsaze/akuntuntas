"""
Tutup TikTok LIVE Studio sepenuhnya, termasuk proses latar.

Aplikasi ini menjalankan banyak proses sekaligus, dan jendelanya dapat
ditutup sementara prosesnya masih hidup. Untuk menjalankannya ulang
dengan hak pengguna biasa, semua prosesnya harus berhenti lebih dahulu.

Cara pakai:
    python tools/tutup_tt_penuh.py --cek
    python tools/tutup_tt_penuh.py --tutup
"""
from __future__ import annotations

import ctypes
import subprocess
import sys
import time
from ctypes import wintypes

JUDUL = "TikTok LIVE Studio"

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

WM_CLOSE = 0x0010


def daftar_proses() -> list[tuple[int, str]]:
    """Daftar proses TikTok yang sedang berjalan."""
    keluaran = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "Get-CimInstance Win32_Process "
         "| Where-Object { $_.Name -like 'TikTok*' } "
         "| ForEach-Object { \"$($_.ProcessId)|$($_.Name)\" }"],
        capture_output=True, text=True, timeout=120)

    hasil = []
    for baris in keluaran.stdout.splitlines():
        if "|" in baris:
            pid, nama = baris.split("|", 1)
            try:
                hasil.append((int(pid.strip()), nama.strip()))
            except ValueError:
                continue
    return hasil


def daftar_jendela() -> list[int]:
    hasil: list[int] = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def kunjungi(handle, _):
        if not user32.IsWindowVisible(handle):
            return True
        panjang = user32.GetWindowTextLengthW(handle)
        if panjang == 0:
            return True
        buf = ctypes.create_unicode_buffer(panjang + 1)
        user32.GetWindowTextW(handle, buf, panjang + 1)
        if JUDUL in buf.value:
            hasil.append(handle)
        return True

    user32.EnumWindows(kunjungi, 0)
    return hasil


def tingkat_hak(pid: int) -> str:
    proses = kernel32.OpenProcess(0x0400, False, pid)
    if not proses:
        return "Administrator"
    kernel32.CloseHandle(proses)
    return "pengguna biasa"


def cek() -> int:
    proses = daftar_proses()
    jendela = daftar_jendela()

    print("=== PROSES TIKTOK ===")
    if not proses:
        print("  tidak ada proses berjalan")
        return 0

    print(f"  {len(proses)} proses:")
    for pid, nama in proses[:6]:
        print(f"    pid {pid:6}  {nama}")
    if len(proses) > 6:
        print(f"    ... dan {len(proses) - 6} lainnya")

    print()
    print("=== TINGKAT HAK PROSES UTAMA ===")
    utama = [p for p, n in proses if n == "TikTok LIVE Studio.exe"]
    if utama:
        print(f"  {tingkat_hak(utama[0])}")

    print()
    print(f"  jendela terlihat: {len(jendela)}")
    return 0


def tutup() -> int:
    jendela = daftar_jendela()

    print("=== MENUTUP JENDELA ===")
    if jendela:
        for handle in jendela:
            print(f"  mengirim WM_CLOSE ke {handle}")
            user32.PostMessageW(handle, WM_CLOSE, 0, 0)
        time.sleep(3)
    else:
        print("  tidak ada jendela")

    print()
    print("=== MENUNGGU PROSES BERHENTI ===")
    for putaran in range(20):
        proses = daftar_proses()
        if not proses:
            print("  semua proses sudah berhenti")
            return 0
        if putaran % 4 == 0:
            print(f"  masih ada {len(proses)} proses...")
        time.sleep(1.5)

    sisa = daftar_proses()
    print(f"  {len(sisa)} proses masih berjalan")
    print()
    print("  Proses ini berjalan sebagai Administrator, sehingga hanya")
    print("  dapat ditutup dengan cara berikut:")
    print()
    print("  1. Buka Task Manager (Ctrl+Shift+Esc)")
    print("  2. Cari 'TikTok LIVE Studio'")
    print("  3. Klik kanan, pilih End task")
    print("  4. Jalankan MULAI-OVERLAY.bat lagi")
    return 1


def utama() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in ("--cek", "--tutup"):
        print(__doc__)
        return 1

    if sys.argv[1] == "--cek":
        return cek()
    return tutup()


if __name__ == "__main__":
    sys.exit(utama())
