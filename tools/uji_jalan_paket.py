"""
Uji jalankan aplikasi dari susunan folder paket MSIX.

Paket MSIX berisi AkunTuntas.exe beserta folder _internal, persis seperti
hasil pemasangan installer. Peninjau Microsoft membuka aplikasi dari
susunan itu. Skrip ini menjalankan EXE dari folder hasil bongkar paket,
menunggu jendela utama muncul, memastikan tidak ada galat, lalu menutupnya.

Pemakaian:
    python tools/uji_jalan_paket.py [folder_paket]

Bila folder tidak diberikan, dipakai _msix_uji.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent


def tunggu_jendela(proc: subprocess.Popen, batas: float) -> bool:
    """Tunggu sampai jendela utama muncul, atau batas waktu habis."""
    mulai = time.time()
    while time.time() - mulai < batas:
        if proc.poll() is not None:
            return False
        # Cari jendela milik proses ini lewat PowerShell
        try:
            keluaran = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 f"(Get-Process -Id {proc.pid} -ErrorAction SilentlyContinue).MainWindowTitle"],
                capture_output=True, text=True, timeout=15,
            )
            judul = keluaran.stdout.strip()
            if judul:
                print(f"    jendela muncul: {judul!r}")
                return True
        except subprocess.TimeoutExpired:
            pass
        time.sleep(2)
    return False


def main() -> int:
    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else AKAR / "_msix_uji"
    exe = folder / "AkunTuntas.exe"

    print("=" * 74)
    print("  UJI JALAN DARI SUSUNAN FOLDER PAKET MSIX")
    print("=" * 74)
    print(f"  folder : {folder}")

    if not exe.exists():
        print(f"  [GAGAL] EXE tidak ditemukan: {exe}")
        print("          Bongkar paket dahulu:")
        print("          makeappx unpack /p msix_output/AkunTuntas.msix /d _msix_uji /o")
        return 1

    print(f"  EXE    : {exe.name} ({exe.stat().st_size / 1048576:.1f} MB)")

    # Folder data sementara supaya data pembukuan pengguna tidak tersentuh
    data = Path(tempfile.mkdtemp(prefix="uji_paket_"))
    print(f"  data   : {data}")

    lingkungan = dict(os.environ)
    lingkungan["AKUNTUNTAS_DATA_DIR"] = str(data)

    print()
    print("  Menjalankan aplikasi...")
    proc = subprocess.Popen(
        [str(exe)],
        cwd=str(folder),
        env=lingkungan,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    muncul = tunggu_jendela(proc, batas=75)

    if proc.poll() is not None:
        keluaran, galat = proc.communicate(timeout=10)
        print(f"  [GAGAL] Aplikasi berhenti sendiri (kode {proc.returncode})")
        if galat:
            print("  Galat:")
            for baris in galat.decode("utf-8", "replace").splitlines()[-12:]:
                print(f"    {baris}")
        if keluaran:
            for baris in keluaran.decode("utf-8", "replace").splitlines()[-6:]:
                print(f"    {baris}")
        return 1

    if muncul:
        print("  [LULUS] Aplikasi terbuka dan jendela utama tampil")
        hasil = 0
    else:
        print("  [GAGAL] Jendela utama tidak muncul dalam batas waktu")
        hasil = 1

    print("  Menutup aplikasi...")
    proc.terminate()
    try:
        proc.wait(timeout=20)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=10)

    # Periksa keluaran galat setelah ditutup
    try:
        keluaran, galat = proc.communicate(timeout=10)
        teks = galat.decode("utf-8", "replace")
        mencurigakan = [
            b for b in teks.splitlines()
            if b.strip() and "Traceback" not in b and "Error" not in b
        ]
        if "Traceback" in teks or "Error" in teks:
            print("  [CATATAN] Ada keluaran galat:")
            for baris in teks.splitlines()[-10:]:
                print(f"    {baris}")
            hasil = 1
        elif mencurigakan:
            for baris in mencurigakan[:5]:
                print(f"    {baris}")
    except Exception:
        pass

    print()
    print("=" * 74)
    print(f"  HASIL: {'LULUS' if hasil == 0 else 'GAGAL'}")
    print("=" * 74)
    return hasil


if __name__ == "__main__":
    sys.exit(main())
