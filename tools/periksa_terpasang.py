"""
Ambil gambar dashboard dari aplikasi yang benar-benar terpasang.

Pemeriksaan sebelumnya memakai kode sumber, bukan berkas EXE yang terpasang.
Skrip ini menjalankan aplikasi terpasang, membuka dashboard, lalu menyimpan
gambarnya supaya keadaan sebenarnya dapat dilihat.
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
TERPASANG = Path(r"C:\Users\ariel\AkunTuntas\AkunTuntas.exe")
DATA_ASLI = Path(os.path.expandvars(r"%LOCALAPPDATA%\AkunTuntas"))
KELUAR = AKAR / "_periksa_terpasang"
LEBAR, TINGGI = 1366, 768

sys.path.insert(0, str(AKAR / "src"))


def main() -> int:
    if not TERPASANG.exists():
        print(f"  aplikasi terpasang tidak ada: {TERPASANG}")
        return 2

    if not (DATA_ASLI / "lisensi.json").exists():
        print("  lisensi belum aktif di folder data asli")
        return 3

    KELUAR.mkdir(exist_ok=True)

    print("=" * 72)
    print("  PERIKSA APLIKASI TERPASANG")
    print("=" * 72)
    print()
    print(f"  exe  : {TERPASANG}")
    print(f"  data : {DATA_ASLI}")
    print()

    # Jalankan aplikasi terpasang memakai data asli, tanpa menyentuh datanya.
    env = dict(os.environ)
    proses = subprocess.Popen([str(TERPASANG)], env=env)

    try:
        # Beri waktu jendela terbuka
        time.sleep(18)

        if proses.poll() is not None:
            print(f"  aplikasi berhenti sendiri (kode {proses.returncode})")
            return 4

        print("  aplikasi berjalan")
        print()
        print("  Untuk memeriksa tampilannya, jalankan tangkapan layar")
        print("  memakai alat bawaan Windows, atau lihat jendela yang terbuka.")
    finally:
        # Tutup aplikasi supaya tidak mengganggu pekerjaan pengguna
        try:
            proses.terminate()
            proses.wait(timeout=10)
        except Exception:
            pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
