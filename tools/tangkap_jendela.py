"""
Ambil gambar jendela aplikasi yang sedang berjalan.

Render di luar layar tidak memakai font sistem, sehingga teksnya tampil
sebagai kotak kosong dan gambarnya tidak dapat dipakai untuk memeriksa
tulisan. Alat ini menangkap jendela sungguhan, sehingga hasilnya sama
dengan yang dilihat pengguna.

Cara pakai:
    python tools/tangkap_jendela.py [nama_berkas.png]
"""
from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

# Fungsi Windows yang dipakai.
user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
user32.FindWindowW.restype = wintypes.HWND
user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]


def cari_jendela(judul_sebagian: str = "AkunTuntas") -> int:
    """Cari jendela utama aplikasi berdasarkan sebagian judulnya."""
    hasil = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def periksa(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True
        panjang = user32.GetWindowTextLengthW(hwnd)
        if panjang == 0:
            return True
        buf = ctypes.create_unicode_buffer(panjang + 1)
        user32.GetWindowTextW(hwnd, buf, panjang + 1)
        if judul_sebagian.lower() in buf.value.lower():
            hasil.append((hwnd, buf.value))
        return True

    user32.EnumWindows(periksa, 0)
    return hasil


def tangkap(hwnd: int, tujuan: Path) -> bool:
    """Simpan gambar jendela ke berkas."""
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])

    rect = wintypes.RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        print("  gagal membaca ukuran jendela")
        return False

    lebar = rect.right - rect.left
    tinggi = rect.bottom - rect.top
    print(f"  jendela: {lebar}x{tinggi} pada ({rect.left},{rect.top})")

    # Bawa jendela ke depan supaya tidak tertutup jendela lain.
    user32.ShowWindow(hwnd, 9)  # SW_RESTORE
    user32.SetForegroundWindow(hwnd)
    app.processEvents()

    layar = QGuiApplication.primaryScreen()
    gambar = layar.grabWindow(int(hwnd))
    if gambar.isNull():
        print("  gagal menangkap jendela")
        return False

    gambar.save(str(tujuan))
    print(f"  gambar disimpan: {tujuan}")
    return True


def main() -> int:
    tujuan = Path(sys.argv[1]) if len(sys.argv) > 1 else AKAR / "_jendela.png"

    print("=" * 76)
    print("  TANGKAP JENDELA APLIKASI")
    print("=" * 76)
    print()

    jendela = cari_jendela("AkunTuntas")
    if not jendela:
        print("  Jendela AkunTuntas tidak ditemukan.")
        print("  Pastikan aplikasi sedang berjalan.")
        return 1

    print(f"  jendela ditemukan: {len(jendela)}")
    for hwnd, judul in jendela:
        print(f"    {judul[:70]}")
    print()

    # Pilih jendela terbesar, biasanya jendela utama.
    def luas(item):
        r = wintypes.RECT()
        user32.GetWindowRect(item[0], ctypes.byref(r))
        return (r.right - r.left) * (r.bottom - r.top)

    utama = max(jendela, key=luas)
    print(f"  jendela utama: {utama[1][:60]}")
    print()

    return 0 if tangkap(utama[0], tujuan) else 1


if __name__ == "__main__":
    sys.exit(main())
