"""
Uji pemasangan ulang: versi baru harus menggantikan versi lama, bukan menumpuk.

Yang diperiksa:
  1. folder aplikasi lama benar-benar dibersihkan sebelum berkas baru dipasang
  2. data pembukuan di folder data TIDAK tersentuh
  3. aplikasi hasil pemasangan dapat dijalankan

Pemakaian:  python tools/uji_pasang_ulang.py
"""

import os
import subprocess
import sys
import time
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
PASANG = Path(r"C:\Users\ariel\AkunTuntas")
SETUP = AKAR / "installer_output" / "AkunTuntas-1.1.1-Setup.exe"
DATA = Path(os.environ.get("LOCALAPPDATA", "")) / "AkunTuntas"


def ukuran_folder(p: Path) -> int:
    """Jumlah byte seluruh berkas di dalam folder."""
    if not p.exists():
        return 0
    total = 0
    for f in p.rglob("*"):
        if f.is_file():
            try:
                total += f.stat().st_size
            except OSError:
                pass
    return total


def main() -> int:
    print("=" * 70)
    print("UJI PEMASANGAN ULANG")
    print("=" * 70)
    print()

    if not SETUP.exists():
        print(f"  Installer tidak ditemukan: {SETUP}")
        return 1

    # ---------------------------------------------------- keadaan awal
    data_ada = DATA.exists()
    data_ukuran = ukuran_folder(DATA)
    data_berkas = len(list(DATA.glob("*"))) if data_ada else 0
    print("  Keadaan sebelum pemasangan:")
    print(f"    folder data    : {'ada' if data_ada else 'belum ada'}")
    print(f"    berkas data    : {data_berkas}")
    print(f"    ukuran data    : {data_ukuran / 1024:.1f} KB")
    print()

    # ---------------------------------------------------- pasang
    print("  Memasang installer...")
    hasil = subprocess.run(
        [str(SETUP), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"],
        capture_output=True, text=True, timeout=600)
    print(f"    kode keluar: {hasil.returncode}")
    if hasil.returncode != 0:
        print("    pemasangan gagal")
        print(f"    {hasil.stderr[:300]}")
        return 1

    time.sleep(3)

    # ---------------------------------------------------- periksa hasil
    print()
    print("  Keadaan sesudah pemasangan:")
    exe = PASANG / "AkunTuntas.exe"
    print(f"    aplikasi terpasang : {exe.exists()}")
    print(f"    ukuran aplikasi    : "
          f"{ukuran_folder(PASANG) / 1024 / 1024:.1f} MB")

    # data harus utuh
    data_ukuran2 = ukuran_folder(DATA)
    data_berkas2 = len(list(DATA.glob("*"))) if DATA.exists() else 0
    print(f"    berkas data        : {data_berkas2} "
          f"({data_ukuran2 / 1024:.1f} KB)")
    print()

    masalah = []
    if not exe.exists():
        masalah.append("aplikasi tidak terpasang")

    if data_ada and data_berkas2 == 0:
        masalah.append("data pembukuan hilang setelah pemasangan")

    # ---------------------------------------------------- jalankan
    print("  Menjalankan aplikasi hasil pemasangan...")
    proc = subprocess.Popen([str(exe)])
    time.sleep(30)
    hidup = proc.poll() is None
    print(f"    berjalan: {hidup}")
    if hidup:
        proc.terminate()
        time.sleep(2)
    else:
        masalah.append(f"aplikasi berhenti sendiri (kode {proc.returncode})")

    print()
    print("=" * 70)
    if masalah:
        print(f"HASIL: {len(masalah)} masalah")
        for m in masalah:
            print(f"   - {m}")
    else:
        print("HASIL: pemasangan ulang berhasil, data pembukuan tetap utuh")
    print("=" * 70)
    return 1 if masalah else 0


if __name__ == "__main__":
    sys.exit(main())
