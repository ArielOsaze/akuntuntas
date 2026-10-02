"""
Mulai ulang TikTok LIVE Studio dengan hak pengguna biasa.

Aplikasi ini memakai manifes highestAvailable, sehingga berjalan sebagai
Administrator. Dalam keadaan itu aplikasi lain yang berjalan biasa tidak
dapat mengendalikannya, karena Windows memblokir masukan antar tingkat
hak yang berbeda. Tanda RUNASINVOKER sudah dipasang di registry, jadi
peluncuran berikutnya akan memakai hak pengguna biasa.

Cara pakai:
    python tools/mulai_ulang_tt.py --tutup      (tutup saja)
    python tools/mulai_ulang_tt.py --jalankan   (jalankan saja)
    python tools/mulai_ulang_tt.py              (tutup lalu jalankan)
"""
from __future__ import annotations

import ctypes
import os
import subprocess
import sys
import time
from ctypes import wintypes

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)

JUDUL = "TikTok LIVE Studio"
PELUNCUR = (r"C:\Program Files\TikTok LIVE Studio"
            r"\TikTok LIVE Studio Launcher.exe")

WM_CLOSE = 0x0010
WM_SYSCOMMAND = 0x0112
SC_CLOSE = 0xF060

PROSES_PENUH = 0x0400
TOKEN_QUERY = 0x0008
TokenElevation = 20


class TOKEN_ELEVATION(ctypes.Structure):
    _fields_ = [("TokenIsElevated", wintypes.DWORD)]


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
        if buf.value.strip() == JUDUL:
            hasil.append(handle)
        return True

    user32.EnumWindows(kunjungi, 0)
    return hasil


def pid_dari(handle: int) -> int:
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(handle, ctypes.byref(pid))
    return pid.value


def hak_proses(pid: int) -> str:
    proses = kernel32.OpenProcess(PROSES_PENUH, False, pid)
    if not proses:
        return "Administrator (tidak terbaca)"

    token = wintypes.HANDLE()
    if not advapi32.OpenProcessToken(proses, TOKEN_QUERY,
                                     ctypes.byref(token)):
        kernel32.CloseHandle(proses)
        return "Administrator (tidak terbaca)"

    info = TOKEN_ELEVATION()
    kembali = wintypes.DWORD()
    advapi32.GetTokenInformation(token, TokenElevation, ctypes.byref(info),
                                 ctypes.sizeof(info), ctypes.byref(kembali))
    kernel32.CloseHandle(token)
    kernel32.CloseHandle(proses)

    return "Administrator" if info.TokenIsElevated else "pengguna biasa"


def ada_proses() -> int:
    keluaran = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "(Get-Process -Name 'TikTok LIVE Studio' "
         "-ErrorAction SilentlyContinue | Measure-Object).Count"],
        capture_output=True, text=True, timeout=90)
    try:
        return int(keluaran.stdout.strip())
    except ValueError:
        return 0


def tutup() -> bool:
    jendela = daftar_jendela()
    if not jendela:
        print("  aplikasi tidak sedang berjalan")
        return True

    print("=== MENUTUP APLIKASI ===")
    for handle in jendela:
        pid = pid_dari(handle)
        print(f"  jendela {handle}  pid {pid}  hak: {hak_proses(pid)}")

    # Coba beberapa cara menutup, dari yang paling sopan.
    for handle in jendela:
        print(f"  mengirim WM_CLOSE ke {handle}")
        user32.PostMessageW(handle, WM_CLOSE, 0, 0)

    for _ in range(20):
        time.sleep(0.5)
        if not daftar_jendela():
            print("  jendela tertutup setelah WM_CLOSE")
            break
    else:
        for handle in daftar_jendela():
            print(f"  mengirim SC_CLOSE ke {handle}")
            user32.PostMessageW(handle, WM_SYSCOMMAND, SC_CLOSE, 0)

        for _ in range(20):
            time.sleep(0.5)
            if not daftar_jendela():
                print("  jendela tertutup setelah SC_CLOSE")
                break

    sisa_jendela = daftar_jendela()
    sisa_proses = ada_proses()

    print(f"  jendela tersisa: {len(sisa_jendela)}")
    print(f"  proses tersisa : {sisa_proses}")

    if sisa_jendela or sisa_proses:
        print("  -> aplikasi MASIH berjalan, perlu ditutup manual")
        return False

    print("  -> aplikasi sudah tertutup")
    return True


def jalankan() -> bool:
    print("=== MENJALANKAN APLIKASI ===")
    print(f"  berkas: {PELUNCUR}")

    # os.startfile memakai ShellExecute, sehingga tanda RUNASINVOKER
    # di registry benar-benar diterapkan saat aplikasi dimulai.
    os.startfile(PELUNCUR)

    print("  menunggu jendela muncul...")
    for _ in range(60):
        time.sleep(1)
        if daftar_jendela():
            break

    jendela = daftar_jendela()
    if not jendela:
        print("  GAGAL jendela tidak muncul dalam 60 detik")
        return False

    for handle in jendela:
        pid = pid_dari(handle)
        print(f"  jendela {handle}  pid {pid}  hak: {hak_proses(pid)}")

    return True


def utama() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "--semua"

    if mode == "--tutup":
        return 0 if tutup() else 1
    if mode == "--jalankan":
        return 0 if jalankan() else 1

    if not tutup():
        return 1

    print()
    if not jalankan():
        return 1

    print()
    print("=== SELESAI ===")
    return 0


if __name__ == "__main__":
    sys.exit(utama())
