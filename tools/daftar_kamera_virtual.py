"""
Daftarkan kamera virtual OBS supaya terdeteksi Windows.

OBS Studio menyertakan kamera virtual, tetapi pendaftarannya butuh izin
Administrator, jadi Windows akan meminta persetujuan satu kali.

Sesudah terdaftar, "OBS Virtual Camera" muncul sebagai kamera biasa dan
dapat dipakai aplikasi mana pun, termasuk TikTok LIVE Studio. Dengan
begitu TikTok memakai sumber Camera seperti biasa, tetapi gambar yang
diterimanya adalah kamera USB yang sudah berlatar AkunTuntas.

Cara pakai:
    python tools/daftar_kamera_virtual.py --cek
    python tools/daftar_kamera_virtual.py --pasang
    python tools/daftar_kamera_virtual.py --lepas
"""
from __future__ import annotations

import ctypes
import subprocess
import sys
import time
from pathlib import Path

PASANG = Path(
    r"C:\Program Files\obs-studio\data\obs-plugins\win-dshow"
    r"\virtualcam-install.bat")
LEPAS = Path(
    r"C:\Program Files\obs-studio\data\obs-plugins\win-dshow"
    r"\virtualcam-uninstall.bat")

# Kata yang menandakan kamera virtual pada nama perangkat.
TANDA_VIRTUAL = ("obs", "virtual", "unity")


def daftar_kamera() -> list[str]:
    """Baca daftar kamera yang terdeteksi Windows."""
    keluaran = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "Get-PnpDevice -Class Camera,Image -Status OK "
         "-ErrorAction SilentlyContinue | "
         "Select-Object -ExpandProperty FriendlyName"],
        capture_output=True, text=True, timeout=120)
    return [b.strip() for b in keluaran.stdout.splitlines() if b.strip()]


def ada_virtual(kamera: list[str]) -> bool:
    """Periksa apakah ada kamera virtual di daftar."""
    return any(k in nama.lower()
               for nama in kamera
               for k in TANDA_VIRTUAL)


def cek() -> int:
    print("=" * 70)
    print("  KAMERA YANG TERDETEKSI")
    print("=" * 70)
    print()

    kamera = daftar_kamera()
    if not kamera:
        print("  tidak ada kamera terdeteksi")
        return 1

    for nama in kamera:
        tanda = ""
        if any(k in nama.lower() for k in TANDA_VIRTUAL):
            tanda = "  <- kamera virtual"
        print(f"  {nama}{tanda}")

    print()
    if ada_virtual(kamera):
        print("  Kamera virtual SUDAH terdaftar dan siap dipakai.")
        print()
        print("  Langkah berikutnya:")
        print("    python tools/jendela_kamera.py --virtual")
        return 0

    print("  Kamera virtual BELUM terdaftar.")
    print()
    print(f"  Berkas pendaftaran: {PASANG.name}")
    print(f"  ada: {PASANG.exists()}")
    print()
    print("  Jalankan untuk mendaftarkan:")
    print("    python tools/daftar_kamera_virtual.py --pasang")
    print()
    print("  Windows akan meminta izin Administrator. Setujui untuk")
    print("  melanjutkan.")
    return 1


def jalankan(berkas: Path, label: str) -> int:
    if not berkas.exists():
        print(f"  GAGAL berkas tidak ada: {berkas}")
        print("  Pastikan OBS Studio terpasang.")
        return 1

    print("=" * 70)
    print(f"  {label.upper()}")
    print("=" * 70)
    print()
    print("  Windows akan meminta izin Administrator.")
    print("  Setujui untuk melanjutkan.")
    print()

    # ShellExecute dengan "runas" memunculkan permintaan izin Windows.
    hasil = ctypes.windll.shell32.ShellExecuteW(
        None, "runas", "cmd.exe", f'/c "{berkas}"', None, 1)

    if hasil <= 32:
        if hasil == 5:
            print("  izin ditolak")
        else:
            print(f"  GAGAL memulai pendaftaran (kode {hasil})")
        return 1

    print("  pendaftaran dijalankan, menunggu selesai...")

    for putaran in range(40):
        time.sleep(2)
        if ada_virtual(daftar_kamera()):
            print()
            print("  BERHASIL: kamera virtual kini terdaftar")
            print()
            print("  Langkah berikutnya:")
            print("    python tools/jendela_kamera.py --virtual")
            return 0
        if putaran % 5 == 4:
            print(f"    menunggu... ({putaran + 1} pemeriksaan)")

    print()
    print("  Belum terdeteksi. Tunggu sebentar, lalu jalankan:")
    print("    python tools/daftar_kamera_virtual.py --cek")
    return 0


def utama() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in (
            "--cek", "--pasang", "--lepas"):
        print(__doc__)
        return 1

    if sys.argv[1] == "--cek":
        return cek()
    if sys.argv[1] == "--pasang":
        return jalankan(PASANG, "mendaftarkan kamera virtual")
    return jalankan(LEPAS, "menghapus kamera virtual")


if __name__ == "__main__":
    sys.exit(utama())
