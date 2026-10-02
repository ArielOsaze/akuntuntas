"""
Jaga ukuran jendela overlay supaya selalu tepat 1080x1920.

Windows mengembalikan ukuran jendela ke ukuran yang muat layar setiap
kali jendela dipulihkan dari keadaan diminimalkan. Akibatnya isi jendela
tidak lagi 9:16, dan aplikasi siaran menyisakan pita kosong di kanan kiri
sambil memperbesar gambar sehingga tampak pecah.

Skrip ini berjalan di latar belakang, memeriksa ukuran jendela overlay
setiap dua detik, dan menyetelnya kembali bila terdeteksi menyimpang.
Jendela yang sedang diminimalkan sengaja tidak disentuh, karena ukuran
kecil pada keadaan itu wajar.

Cara pakai:
    python tools/pantau_overlay.py              (berjalan terus)
    python tools/pantau_overlay.py --sekali     (periksa sekali saja)
    python tools/pantau_overlay.py --jeda 3     (jeda 3 detik)
"""
from __future__ import annotations

import ctypes
import sys
import time
from ctypes import wintypes

JUDUL = "AkunTuntas - Overlay Live"

LEBAR = 1080
TINGGI = 1920
RASIO = LEBAR / TINGGI

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

SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010
SWP_NOSENDCHANGING = 0x0400



# Nama mutex: penanda bahwa pemantau sudah berjalan. Mutex dipakai
# karena hanya satu proses yang bisa memegangnya, dan Windows melepasnya
# otomatis begitu prosesnya berhenti. Berkas penanda biasa bisa tertinggal
# dalam keadaan basi, mutex tidak.
NAMA_MUTEX = "Global\\AkunTuntasPantauOverlay"

_mutex = None


def ambil_mutex() -> bool:
    """
    Coba pegang mutex pemantau.

    Mengembalikan True bila berhasil, False bila pemantau lain sedang
    berjalan. Tanpa ini, menjalankan peluncur berulang kali akan
    menumpuk banyak pemantau yang saling berebut menyetel ukuran.
    """
    global _mutex

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL,
                                      wintypes.LPCWSTR]
    kernel32.CreateMutexW.restype = wintypes.HANDLE

    ERROR_ALREADY_EXISTS = 183

    ctypes.set_last_error(0)
    _mutex = kernel32.CreateMutexW(None, True, NAMA_MUTEX)
    galat = ctypes.get_last_error()

    if not _mutex:
        # Mutex tidak bisa dibuat. Lebih baik berhenti daripada berjalan
        # tanpa jaminan hanya satu pemantau.
        return False

    return galat != ERROR_ALREADY_EXISTS


def lepas_mutex() -> None:
    """Lepaskan mutex supaya pemantau berikutnya bisa berjalan."""
    global _mutex

    if not _mutex:
        return

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.ReleaseMutex(_mutex)
    kernel32.CloseHandle(_mutex)
    _mutex = None


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
        if buf.value.strip() == JUDUL:
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


def setel_ulang(handle: int, bisik: bool = False) -> bool:
    """Setel isi jendela supaya tepat 1080x1920."""
    lebar_luar, tinggi_luar, lebar_isi, tinggi_isi = ukuran(handle)

    bingkai_x = lebar_luar - lebar_isi
    bingkai_y = tinggi_luar - tinggi_isi

    if not bisik:
        print(f"  ukuran menyimpang: isi {lebar_isi}x{tinggi_isi} "
              f"(rasio {lebar_isi / tinggi_isi:.4f})")
        print(f"  menyetel ulang ke {LEBAR}x{TINGGI}...")

    user32.SetWindowPos(handle, 0, 0, 0,
                        LEBAR + bingkai_x, TINGGI + bingkai_y,
                        SWP_NOZORDER | SWP_NOACTIVATE
                        | SWP_NOSENDCHANGING)
    time.sleep(1.0)

    lebar_luar, tinggi_luar, lebar_isi, tinggi_isi = ukuran(handle)
    if not bisik:
        print(f"  hasil: isi {lebar_isi}x{tinggi_isi} "
              f"(rasio {lebar_isi / tinggi_isi:.4f})")

    return abs(lebar_isi - LEBAR) <= 2 and abs(tinggi_isi - TINGGI) <= 2


def periksa(handle: int, bisik: bool = False) -> bool:
    """
    Periksa ukuran jendela, setel ulang bila menyimpang.

    Mengembalikan True bila ukurannya sudah benar atau berhasil disetel.
    """
    # Jendela yang diminimalkan tidak diperiksa: ukurannya kecil karena
    # memang sedang disembunyikan, bukan karena menyimpang.
    if user32.IsIconic(handle):
        return True

    lebar_luar, tinggi_luar, lebar_isi, tinggi_isi = ukuran(handle)

    if tinggi_isi == 0 or lebar_isi == 0:
        return True

    rasio = lebar_isi / tinggi_isi
    if abs(rasio - RASIO) < 0.004:
        return True

    return setel_ulang(handle, bisik)


def utama() -> int:
    jeda = 2.0
    if "--jeda" in sys.argv:
        try:
            jeda = float(sys.argv[sys.argv.index("--jeda") + 1])
        except (ValueError, IndexError):
            print("  jeda tidak sah, memakai 2 detik")

    sekali = "--sekali" in sys.argv

    # Hanya satu pemantau yang boleh berjalan.
    if not sekali:
        if not ambil_mutex():
            print("  pemantau lain sudah berjalan, yang ini berhenti")
            return 0

    if sekali:
        handle = cari_jendela()
        if not handle:
            print(f"  jendela '{JUDUL}' tidak ditemukan")
            return 1
        lebar_luar, tinggi_luar, lebar_isi, tinggi_isi = ukuran(handle)
        print(f"  isi jendela: {lebar_isi}x{tinggi_isi} "
              f"(rasio {lebar_isi / tinggi_isi:.4f})")
        return 0 if periksa(handle) else 1

    print("=" * 70)
    print("  PEMANTAU UKURAN OVERLAY")
    print("=" * 70)
    print()
    print(f"  sasaran    : isi {LEBAR}x{TINGGI} "
          f"(rasio {RASIO:.4f})")
    print(f"  jeda periksa: {jeda} detik")
    print()
    print("  Jendela overlay dijaga supaya ukurannya selalu tepat.")
    print("  Ini perlu karena Windows mengembalikan ukuran jendela ke")
    print("  ukuran layar setiap kali jendela dipulihkan dari keadaan")
    print("  diminimalkan.")
    print()
    print("  Tekan Ctrl+C untuk berhenti.")
    print("=" * 70)
    print()

    belum_ada = 0

    try:
        while True:
            handle = cari_jendela()

            if not handle:
                belum_ada += 1
                # Setelah beberapa kali tidak ditemukan, kemungkinan
                # jendelanya memang sudah ditutup.
                if belum_ada >= 5:
                    print("  jendela overlay tidak ada, pemantau berhenti")
                    lepas_mutex()
                    return 0
                time.sleep(jeda)
                continue

            belum_ada = 0
            periksa(handle)
            time.sleep(jeda)

    except KeyboardInterrupt:
        print()
        print("  dihentikan")
        lepas_mutex()
        return 0


if __name__ == "__main__":
    sys.exit(utama())
