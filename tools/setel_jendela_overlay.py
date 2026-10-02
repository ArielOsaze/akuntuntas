"""
Atur jendela overlay supaya isinya tepat 1080x1920 (9:16).

Sisa bingkai di kanan dan kiri muncul karena isi jendela tidak tepat 9:16.
Aplikasi siaran memperbesar sumber agar muat, dan ketidakcocokan
perbandingan menyisakan ruang kosong di kedua sisi. Gambar juga menjadi
pecah karena isi jendela yang kecil diperbesar dua kali.

Dokumen ini menyetel ukuran jendela sehingga bagian isinya (tanpa bingkai
dan bilah judul) tepat 1080x1920. Jendela memang menjadi lebih tinggi
daripada layar, tetapi Windows mengizinkannya dan peramban tetap
menggambar seluruh isinya. Dengan begitu sumber yang ditangkap sudah
berukuran penuh, sehingga tidak ada sisa ruang dan tidak ada pembesaran.

Cara pakai:
    python tools/setel_jendela_overlay.py --lihat
    python tools/setel_jendela_overlay.py --setel
    python tools/setel_jendela_overlay.py --setel --lebar 1080 --tinggi 1920
    python tools/setel_jendela_overlay.py --periksa
"""
from __future__ import annotations

import ctypes
import sys
import time
from ctypes import wintypes
from pathlib import Path

from PIL import Image

AKAR = Path(__file__).resolve().parent.parent
JUDUL = "AkunTuntas - Overlay Live"

user32 = ctypes.WinDLL("user32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)

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
user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
user32.GetWindowLongW.restype = wintypes.LONG

GWL_STYLE = -16
GWL_EXSTYLE = -20
SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010
PW_RENDERFULLCONTENT = 0x00000002


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD),
        ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [("bmiHeader", BITMAPINFOHEADER),
                ("bmiColors", wintypes.DWORD * 3)]


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


def ukuran_jendela(handle: int) -> tuple[int, int, int, int]:
    luar = wintypes.RECT()
    user32.GetWindowRect(handle, ctypes.byref(luar))
    isi = wintypes.RECT()
    user32.GetClientRect(handle, ctypes.byref(isi))
    return (luar.right - luar.left, luar.bottom - luar.top,
            isi.right - isi.left, isi.bottom - isi.top)


def selisih_bingkai(handle: int, lebar_isi: int, tinggi_isi: int
                     ) -> tuple[int, int]:
    """
    Hitung selisih antara ukuran jendela dan ukuran isinya.

    Nilai ini didapat dari jendela yang sedang berjalan, sehingga bingkai
    dan bilah judul yang sebenarnya ikut terhitung. Ukuran jendela yang
    perlu disetel lalu ditambah selisih ini.
    """
    lebar_luar, tinggi_luar, lebar_kini, tinggi_kini = ukuran_jendela(handle)
    return (lebar_luar - lebar_kini, tinggi_luar - tinggi_kini)


def setel(lebar_isi: int, tinggi_isi: int) -> int:
    handle = cari_jendela()
    if not handle:
        print(f"  GAGAL jendela '{JUDUL}' tidak ditemukan")
        return 1

    lebar_luar, tinggi_luar, lebar_kini, tinggi_kini = ukuran_jendela(handle)
    print("=== SEBELUM ===")
    print(f"  jendela : {lebar_luar}x{tinggi_luar}")
    print(f"  isi     : {lebar_kini}x{tinggi_kini}  "
          f"(rasio {lebar_kini / tinggi_kini:.4f})")

    selisih_x, selisih_y = selisih_bingkai(handle, lebar_isi, tinggi_isi)
    print(f"  bingkai : +{selisih_x} x +{selisih_y}")

    lebar_baru = lebar_isi + selisih_x
    tinggi_baru = tinggi_isi + selisih_y

    # Posisi: taruh di sudut kiri atas layar utama supaya mudah dilihat.
    posisi = wintypes.RECT()
    user32.GetWindowRect(handle, ctypes.byref(posisi))

    print()
    print("=== MENYETEL ===")
    print(f"  ukuran jendela baru: {lebar_baru}x{tinggi_baru}")
    print(f"  supaya isi tepat   : {lebar_isi}x{tinggi_isi}")

    hasil = user32.SetWindowPos(
        handle, 0, posisi.left, posisi.top, lebar_baru, tinggi_baru,
        SWP_NOZORDER | SWP_NOACTIVATE)
    if not hasil:
        print(f"  GAGAL SetWindowPos, galat {ctypes.get_last_error()}")
        return 1

    time.sleep(1.2)

    lebar_luar, tinggi_luar, lebar_kini, tinggi_kini = ukuran_jendela(handle)
    print()
    print("=== SESUDAH ===")
    print(f"  jendela : {lebar_luar}x{tinggi_luar}")
    print(f"  isi     : {lebar_kini}x{tinggi_kini}  "
          f"(rasio {lebar_kini / tinggi_kini:.4f})")

    selisih_lebar = abs(lebar_kini - lebar_isi)
    selisih_tinggi = abs(tinggi_kini - tinggi_isi)
    if selisih_lebar <= 2 and selisih_tinggi <= 2:
        print("  -> isi jendela TEPAT sesuai")
        return 0

    print(f"  -> meleset {selisih_lebar} x {selisih_tinggi} piksel, "
          f"menyetel sekali lagi")
    # Setel ulang memakai selisih yang baru terukur.
    selisih_x, selisih_y = selisih_bingkai(handle, lebar_isi, tinggi_isi)
    user32.SetWindowPos(
        handle, 0, posisi.left, posisi.top,
        lebar_isi + selisih_x, tinggi_isi + selisih_y,
        SWP_NOZORDER | SWP_NOACTIVATE)
    time.sleep(1.2)

    lebar_luar, tinggi_luar, lebar_kini, tinggi_kini = ukuran_jendela(handle)
    print(f"  percobaan kedua: isi {lebar_kini}x{tinggi_kini}")
    if abs(lebar_kini - lebar_isi) <= 2 and abs(tinggi_kini - tinggi_isi) <= 2:
        print("  -> isi jendela TEPAT sesuai")
        return 0

    print("  -> masih meleset, periksa manual")
    return 1


def tangkap(handle: int, berkas: Path) -> bool:
    """Potret isi jendela memakai PrintWindow."""
    _, _, lebar, tinggi = ukuran_jendela(handle)
    if lebar <= 0 or tinggi <= 0:
        return False

    jendela_dc = user32.GetWindowDC(handle)
    if not jendela_dc:
        return False

    dc_memori = gdi32.CreateCompatibleDC(jendela_dc)
    bitmap = gdi32.CreateCompatibleBitmap(jendela_dc, lebar, tinggi)
    gdi32.SelectObject(dc_memori, bitmap)

    info = BITMAPINFO()
    info.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    info.bmiHeader.biWidth = lebar
    info.bmiHeader.biHeight = -tinggi
    info.bmiHeader.biPlanes = 1
    info.bmiHeader.biBitCount = 32
    info.bmiHeader.biCompression = 0

    user32.PrintWindow(handle, dc_memori, PW_RENDERFULLCONTENT)

    penyangga = ctypes.create_string_buffer(lebar * tinggi * 4)
    gdi32.GetDIBits(dc_memori, bitmap, 0, tinggi, penyangga,
                    ctypes.byref(info), 0)

    gambar = Image.frombuffer("RGBA", (lebar, tinggi), penyangga.raw,
                              "raw", "BGRA", 0, 1).convert("RGB")
    gambar.save(berkas)

    gdi32.DeleteObject(bitmap)
    gdi32.DeleteDC(dc_memori)
    user32.ReleaseDC(handle, jendela_dc)

    return True


def periksa() -> int:
    handle = cari_jendela()
    if not handle:
        print(f"  GAGAL jendela '{JUDUL}' tidak ditemukan")
        return 1

    lebar_luar, tinggi_luar, lebar, tinggi = ukuran_jendela(handle)
    print("=== UKURAN JENDELA OVERLAY ===")
    print(f"  jendela : {lebar_luar}x{tinggi_luar}")
    print(f"  isi     : {lebar}x{tinggi}")
    print(f"  rasio   : {lebar / tinggi:.4f}   (9:16 = {9 / 16:.4f})")

    if abs(lebar / tinggi - 9 / 16) < 0.004:
        print("  -> rasio SUDAH tepat 9:16")
    else:
        print("  -> rasio BELUM tepat, jalankan --setel")

    berkas = AKAR / "_overlay_jendela.png"
    if tangkap(handle, berkas):
        im = Image.open(berkas)
        print()
        print("=== POTRET ISI JENDELA ===")
        print(f"  berkas : {berkas.name}")
        print(f"  ukuran : {im.width}x{im.height}")

        # Periksa apakah tepi kiri dan kanan terisi (bukan pita kosong).
        print()
        print("  kecerahan kolom tepi (pita kosong akan gelap):")
        for x in (0, 2, 4, 8, 16, im.width - 17, im.width - 9,
                  im.width - 5, im.width - 3, im.width - 1):
            total = 0
            n = 0
            for y in range(0, im.height, 30):
                r, g, b = im.getpixel((x, y))
                total += (r + g + b) / 3
                n += 1
            print(f"    x={x:5}: {total / n:6.1f}")

    return 0


def utama() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in (
            "--lihat", "--setel", "--periksa"):
        print(__doc__)
        return 1

    if sys.argv[1] == "--lihat":
        handle = cari_jendela()
        if not handle:
            print(f"  GAGAL jendela '{JUDUL}' tidak ditemukan")
            return 1
        lebar_luar, tinggi_luar, lebar, tinggi = ukuran_jendela(handle)
        print("=== JENDELA OVERLAY SEKARANG ===")
        print(f"  jendela : {lebar_luar}x{tinggi_luar}")
        print(f"  isi     : {lebar}x{tinggi}  (rasio {lebar / tinggi:.4f})")
        print(f"  9:16    : {9 / 16:.4f}")
        return 0

    if sys.argv[1] == "--periksa":
        return periksa()

    lebar = 1080
    tinggi = 1920
    if "--lebar" in sys.argv:
        lebar = int(sys.argv[sys.argv.index("--lebar") + 1])
    if "--tinggi" in sys.argv:
        tinggi = int(sys.argv[sys.argv.index("--tinggi") + 1])

    kode = setel(lebar, tinggi)
    if kode == 0:
        print()
        periksa()
    return kode


if __name__ == "__main__":
    sys.exit(utama())
