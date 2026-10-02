"""
Perbaiki tampilan overlay sekali jalan.

Menjalankan tiga hal berurutan:
  1. Memuat ulang halaman overlay, supaya perubahan terbaru terpakai
  2. Menyetel ukuran jendela agar isinya tepat 1080x1920
  3. Memeriksa hasilnya dan melaporkan keadaan

Ukuran penuh ini yang menghilangkan pita kosong di kanan kiri sekaligus
membuat gambar tetap tajam, karena aplikasi siaran tidak perlu
memperbesar sumbernya lagi.

Cara pakai:
    python tools/perbaiki_overlay.py
    python tools/perbaiki_overlay.py --tanpa-muat-ulang
"""
from __future__ import annotations

import ctypes
import sys
import time
from ctypes import wintypes
from pathlib import Path

from PIL import ImageGrab

AKAR = Path(__file__).resolve().parent.parent
JUDUL = "AkunTuntas - Overlay Live"

user32 = ctypes.WinDLL("user32", use_last_error=True)

user32.GetWindowRect.argtypes = [wintypes.HWND,
                                 ctypes.POINTER(wintypes.RECT)]
user32.GetWindowRect.restype = wintypes.BOOL
user32.GetClientRect.argtypes = [wintypes.HWND,
                                 ctypes.POINTER(wintypes.RECT)]
user32.GetClientRect.restype = wintypes.BOOL
user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND,
                                ctypes.c_int, ctypes.c_int,
                                ctypes.c_int, ctypes.c_int,
                                wintypes.UINT]
user32.SetWindowPos.restype = wintypes.BOOL
user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT,
                                wintypes.WPARAM, wintypes.LPARAM]
user32.PostMessageW.restype = wintypes.BOOL

SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010
SWP_NOSENDCHANGING = 0x0400

WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
VK_F5 = 0x74

LEBAR = 1080
TINGGI = 1920


def cari_jendela() -> int:
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
        if JUDUL.lower() in buf.value.lower():
            hasil.append(handle)
        return True

    user32.EnumWindows(kunjungi, 0)
    return hasil[0] if hasil else 0


def ukuran(handle: int) -> tuple[int, int, int, int]:
    luar = wintypes.RECT()
    user32.GetWindowRect(handle, ctypes.byref(luar))
    isi = wintypes.RECT()
    user32.GetClientRect(handle, ctypes.byref(isi))
    return (luar.right - luar.left, luar.bottom - luar.top,
            isi.right, isi.bottom)


def muat_ulang(handle: int) -> None:
    """Muat ulang halaman di jendela overlay."""
    print("=== 1. MEMUAT ULANG HALAMAN ===")
    for pesan, tombol in ((WM_KEYDOWN, VK_F5), (WM_KEYUP, VK_F5)):
        user32.PostMessageW(handle, pesan, tombol, 0)
        time.sleep(0.15)
    print("  halaman dimuat ulang")
    time.sleep(3.5)


def setel_penuh(handle: int) -> bool:
    """Setel isi jendela tepat 1080x1920."""
    print()
    print("=== 2. MENYETEL UKURAN PENUH ===")

    lebar_luar, tinggi_luar, lebar_isi, tinggi_isi = ukuran(handle)
    print(f"  sebelum : jendela {lebar_luar}x{tinggi_luar}, "
          f"isi {lebar_isi}x{tinggi_isi}  "
          f"(rasio {lebar_isi / tinggi_isi:.4f})")

    bingkai_x = lebar_luar - lebar_isi
    bingkai_y = tinggi_luar - tinggi_isi

    user32.SetWindowPos(handle, 0, 0, 0,
                        LEBAR + bingkai_x, TINGGI + bingkai_y,
                        SWP_NOZORDER | SWP_NOACTIVATE
                        | SWP_NOSENDCHANGING)
    time.sleep(1.5)

    lebar_luar, tinggi_luar, lebar_isi, tinggi_isi = ukuran(handle)
    rasio = lebar_isi / tinggi_isi
    print(f"  sesudah : jendela {lebar_luar}x{tinggi_luar}, "
          f"isi {lebar_isi}x{tinggi_isi}  (rasio {rasio:.4f})")

    tepat = abs(rasio - 9 / 16) < 0.004
    if tepat:
        print("  -> isi jendela TEPAT 9:16")
    else:
        print("  -> rasio belum tepat")

    return tepat


def periksa(handle: int) -> None:
    """Potret isi jendela dan periksa tepinya."""
    print()
    print("=== 3. MEMERIKSA HASIL ===")

    lebar_luar, tinggi_luar, lebar_isi, tinggi_isi = ukuran(handle)
    print(f"  isi jendela: {lebar_isi}x{tinggi_isi}")

    # Potret layar lalu ambil bagian isi jendela.
    posisi = wintypes.RECT()
    user32.GetWindowRect(handle, ctypes.byref(posisi))

    layar = ImageGrab.grab()
    kiri = max(0, posisi.left)
    atas = max(0, posisi.top)
    kanan = min(layar.width, posisi.right)
    bawah = min(layar.height, posisi.bottom)

    if kanan - kiri < 100 or bawah - atas < 100:
        print("  catatan: jendela di luar layar, tidak bisa dipotret")
        return

    potong = layar.crop((kiri, atas, kanan, bawah)).convert("RGB")
    berkas = AKAR / "_overlay_sesudah_perbaikan.png"
    potong.save(berkas)

    print(f"  potret: {berkas.name} ({potong.width}x{potong.height})")

    # Periksa pita gelap di tepi kiri dan kanan.
    print()
    print("  kecerahan tepi (pita kosong akan gelap):")
    for sisi, xs in (("kiri", (2, 5, 10, 20)),
                     ("kanan", (potong.width - 21,
                                potong.width - 11,
                                potong.width - 6,
                                potong.width - 3))):
        for x in xs:
            total = 0
            n = 0
            for y in range(0, potong.height, 40):
                r, g, b = potong.getpixel((x, y))
                total += (r + g + b) / 3
                n += 1
            rata = total / n
            tanda = "  <- GELAP" if rata < 15 else ""
            print(f"    {sisi} x={x:5}: {rata:6.1f}{tanda}")


def utama() -> int:
    handle = cari_jendela()
    if not handle:
        print(f"  GAGAL jendela '{JUDUL}' tidak ditemukan.")
        print("  Jalankan lebih dahulu:")
        print("    python tools/jalankan_overlay.py --chrome")
        return 1

    print("=" * 70)
    print("  PERBAIKI TAMPILAN OVERLAY")
    print("=" * 70)

    if "--tanpa-muat-ulang" not in sys.argv:
        muat_ulang(handle)

    tepat = setel_penuh(handle)
    periksa(handle)

    print()
    print("=" * 70)
    if tepat:
        print("  SELESAI. Overlay siap dipakai.")
        print()
        print("  Di TikTok LIVE Studio:")
        print("    1. Klik sumber overlay, lalu pilih Fit to screen")
        print("    2. Bila sumber ditambahkan saat ukurannya masih kecil,")
        print("       hapus lalu tambahkan ulang supaya ukurannya ikut")
        print("       menyesuaikan")
    else:
        print("  Ukuran belum tepat. Jalankan sekali lagi.")
    print("=" * 70)

    return 0 if tepat else 1


if __name__ == "__main__":
    sys.exit(utama())
