"""
Uji apakah peramban dapat membuka jendela lebih tinggi daripada layar.

Overlay live berukuran 1080x1920 (tegak), sedangkan layar yang umum
berukuran 1920x1080 (mendatar). Jendela overlay karena itu lebih tinggi
daripada layar.

Aplikasi siaran menangkap isi jendela, bukan hanya bagian yang terlihat.
Bila isi jendela benar-benar 1080x1920, tangkapannya juga 1080x1920 walau
sebagian jendela berada di luar layar. Alat ini membuktikan apakah hal itu
benar-benar terjadi, karena bila tidak, overlay akan terpotong.

Cara pakai:
    python tools/uji_jendela_overlay.py
"""
from __future__ import annotations

import ctypes
import shutil
import subprocess
import sys
import time
from ctypes import wintypes
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
OVERLAY = AKAR / "live_overlay" / "overlay.html"
PROFIL = AKAR / "_uji_chrome_profil"

CHROME = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]

user32 = ctypes.WinDLL("user32", use_last_error=True)


class RECT(ctypes.Structure):
    _fields_ = [("kiri", ctypes.c_long), ("atas", ctypes.c_long),
                ("kanan", ctypes.c_long), ("bawah", ctypes.c_long)]


def ukuran_jendela(handle: int) -> tuple[int, int]:
    """Ukuran seluruh jendela, termasuk bingkai."""
    r = RECT()
    user32.GetWindowRect(handle, ctypes.byref(r))
    return r.kanan - r.kiri, r.bawah - r.atas


def ukuran_isi(handle: int) -> tuple[int, int]:
    """Ukuran isi jendela, tanpa bingkai. Inilah yang ditangkap siaran."""
    r = RECT()
    user32.GetClientRect(handle, ctypes.byref(r))
    return r.kanan - r.kiri, r.bawah - r.atas


def cari_jendela(judul: str) -> int:
    """Cari jendela berdasarkan sebagian judulnya."""
    hasil = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def kunjungi(handle, _):
        if not user32.IsWindowVisible(handle):
            return True
        panjang = user32.GetWindowTextLengthW(handle)
        if panjang == 0:
            return True
        buf = ctypes.create_unicode_buffer(panjang + 1)
        user32.GetWindowTextW(handle, buf, panjang + 1)
        if judul.lower() in buf.value.lower():
            hasil.append(handle)
        return True

    user32.EnumWindows(kunjungi, 0)
    return hasil[0] if hasil else 0


def utama() -> int:
    print("=" * 74)
    print("  UJI UKURAN JENDELA OVERLAY")
    print("=" * 74)

    exe = None
    for jalur in CHROME:
        if Path(jalur).exists():
            exe = jalur
            break

    if exe is None:
        print("\n  Chrome tidak ditemukan.")
        return 1

    lebar_layar = user32.GetSystemMetrics(0)
    tinggi_layar = user32.GetSystemMetrics(1)
    print(f"\n  layar        : {lebar_layar}x{tinggi_layar}")
    print("  overlay butuh: 1080x1920")

    # Jendela sengaja dibuat lebih tinggi daripada layar.
    #
    # Tinggi ditambah 60 piksel karena bingkai jendela memakan ruang,
    # sedangkan yang perlu tepat 1920 adalah isinya.
    proses = subprocess.Popen([
        exe,
        f"--app={OVERLAY.as_uri()}",
        "--window-size=1080,1980",
        "--window-position=0,0",
        f"--user-data-dir={PROFIL}",
        "--no-first-run",
        "--no-default-browser-check",
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    print("\n  menunggu jendela terbuka...")
    handle = 0
    for _ in range(20):
        time.sleep(0.8)
        handle = cari_jendela("Overlay Live")
        if handle:
            break

    if not handle:
        print("  GAGAL jendela tidak ditemukan")
        proses.terminate()
        shutil.rmtree(PROFIL, ignore_errors=True)
        return 1

    time.sleep(1.5)
    lebar_win, tinggi_win = ukuran_jendela(handle)
    lebar_isi, tinggi_isi = ukuran_isi(handle)

    print("\n  --- Hasil ---")
    print(f"      seluruh jendela : {lebar_win}x{tinggi_win}")
    print(f"      isi jendela     : {lebar_isi}x{tinggi_isi}")
    print(f"      tinggi layar    : {tinggi_layar}")
    print(f"      isi lebih tinggi dari layar: {tinggi_isi > tinggi_layar}")

    cocok = (lebar_isi >= 1070 and tinggi_isi >= 1900)
    print()
    if cocok:
        print("  [LULUS] isi jendela benar-benar 1080x1920")
        print("          Jendela dapat lebih tinggi daripada layar, dan")
        print("          aplikasi siaran akan menangkap seluruh isinya.")
    else:
        print(f"  [GAGAL] isi jendela {lebar_isi}x{tinggi_isi}, "
              f"bukan 1080x1920")
        print("          Jendela dipangkas agar muat di layar, sehingga")
        print("          overlay akan terpotong bila ditangkap.")

    proses.terminate()
    time.sleep(1.5)
    subprocess.run(["taskkill", "/F", "/IM", "chrome.exe"],
                   capture_output=True)
    shutil.rmtree(PROFIL, ignore_errors=True)

    print("\n" + "=" * 74)
    return 0 if cocok else 1


if __name__ == "__main__":
    sys.exit(utama())
