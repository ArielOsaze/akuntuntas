"""
Ukur kecepatan EXE terpasang seperti yang dirasakan pengguna.

Perbaikan kecepatan harus dibuktikan pada aplikasi yang benar-benar dipakai,
bukan hanya pada kode sumber. Berkas ini menjalankan EXE, menunggu jendelanya
muncul, lalu mencatat berapa lama prosesnya sampai siap.
"""

import os
import subprocess
import sys
import time
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
EXE = AKAR / "dist" / "AkunTuntas" / "AkunTuntas.exe"


def main() -> int:
    if not EXE.exists():
        print(f"  EXE tidak ditemukan: {EXE}")
        return 1

    print("=" * 74)
    print("KECEPATAN EXE TERPASANG")
    print("=" * 74)
    print()

    lingkungan = dict(os.environ)
    lingkungan["AKUNTANSIID_DATA"] = str(AKAR / "_contoh")

    t0 = time.perf_counter()
    proses = subprocess.Popen(
        [str(EXE)],
        cwd=str(EXE.parent),
        env=lingkungan,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # tunggu sampai jendela muncul, paling lama 30 detik
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    muncul = None
    batas = time.time() + 30
    while time.time() < batas:
        # cari jendela milik proses ini
        hasil = []

        @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        def kunjungi(hwnd, _):
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value == proses.pid and user32.IsWindowVisible(hwnd):
                panjang = user32.GetWindowTextLengthW(hwnd)
                if panjang > 0:
                    buf = ctypes.create_unicode_buffer(panjang + 1)
                    user32.GetWindowTextW(hwnd, buf, panjang + 1)
                    hasil.append(buf.value)
            return True

        user32.EnumWindows(kunjungi, 0)
        if hasil:
            muncul = (time.perf_counter() - t0) * 1000
            print(f"  Jendela muncul setelah : {muncul:,.0f} ms")
            print(f"  Judul jendela          : {hasil[0]}")
            break
        time.sleep(0.02)

    if muncul is None:
        print("  Jendela tidak muncul dalam 30 detik")
        proses.kill()
        return 1

    # biarkan tergambar penuh
    time.sleep(2)
    siap = (time.perf_counter() - t0) * 1000
    print(f"  Siap dipakai setelah   : {siap:,.0f} ms")
    print()

    proses.kill()
    proses.wait(timeout=10)
    print("  EXE dihentikan.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
