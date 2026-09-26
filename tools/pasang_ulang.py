"""Pasang ulang AkunTuntas: hapus versi lama, lalu pasang versi baru.

Cara pakai:
    python tools/pasang_ulang.py

Skrip ini:
  1. menutup aplikasi yang sedang berjalan,
  2. menjalankan uninstaller versi lama secara senyap,
  3. menunggu sampai folder program benar-benar terhapus,
  4. memasang installer terbaru secara senyap,
  5. memeriksa hasilnya.

Data pembukuan di %LOCALAPPDATA% tidak dihapus.
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
INSTALLER = AKAR / "installer_output" / "AkunTuntas-1.2.0-Setup.exe"
TUJUAN = Path(r"C:\Users\ariel\AkunTuntas")
LOG = AKAR / "_pasang_ulang.log"

NAMA_PROSES = ["AkunTuntas.exe", "AkunTuntas-1.2.0-Setup.exe", "unins000.exe"]


def jalankan(perintah: list, tunggu: int = 600) -> tuple:
    """Jalankan perintah, kembalikan (kode, keluaran)."""
    try:
        p = subprocess.run(perintah, capture_output=True, text=True,
                           timeout=tunggu, errors="replace")
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return 124, "melewati batas waktu"
    except FileNotFoundError as e:
        return 127, str(e)


def tutup_aplikasi():
    """Hentikan proses yang memakai berkas program."""
    for nama in NAMA_PROSES:
        jalankan(["taskkill", "/F", "/IM", nama], tunggu=30)
    time.sleep(2)


def cari_uninstaller() -> list:
    """Cari uninstaller AkunTuntas yang terdaftar di Windows."""
    hasil = []
    for akar_reg in (r"HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
                     r"HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
                     r"HKLM\SOFTWARE\WOW6432Node\Microsoft\Windows"
                     r"\CurrentVersion\Uninstall"):
        kode, keluaran = jalankan(["reg", "query", akar_reg, "/s", "/f",
                                   "AkunTuntas"], tunggu=60)
        if kode != 0:
            continue
        lokasi = None
        for baris in keluaran.splitlines():
            b = baris.strip()
            if b.startswith("InstallLocation"):
                lokasi = b.split("REG_SZ")[-1].strip()
            if b.startswith("UninstallString"):
                jalur = b.split("REG_SZ")[-1].strip().strip('"')
                if Path(jalur).exists():
                    hasil.append((Path(jalur), lokasi))
    return hasil


def main() -> int:
    if not INSTALLER.exists():
        print(f"Installer tidak ditemukan: {INSTALLER}")
        print("Bangun dulu dengan: pyinstaller build.spec lalu ISCC installer.iss")
        return 1

    print("=== 1. Menutup aplikasi yang berjalan ===")
    tutup_aplikasi()
    print("   selesai")

    print("\n=== 2. Mencari versi lama ===")
    lama = cari_uninstaller()
    if not lama:
        print("   tidak ada versi lama terdaftar")
    for jalur, lokasi in lama:
        print(f"   ditemukan: {jalur}")
        print(f"   folder   : {lokasi}")
        print("   menghapus (senyap)...")
        # Uninstaller ini punya dialog konfirmasi buatan sendiri yang tidak
        # ditutup oleh /SUPPRESSMSGBOXES; /SILENT yang menekan semua dialog.
        kode, keluaran = jalankan([str(jalur), "/SILENT",
                                   "/SUPPRESSMSGBOXES", "/NORESTART"],
                                  tunggu=300)
        print(f"   kode keluar: {kode}")

        if lokasi:
            folder = Path(lokasi)
            for _ in range(30):
                if not folder.exists():
                    break
                time.sleep(1)

            # Bila uninstaller menggantung karena dialog, hentikan prosesnya
            # lalu hapus foldernya langsung agar tidak menyisakan sisa.
            if folder.exists():
                print("   uninstaller belum selesai; menutup paksa...")
                for nama in ("_unins.tmp", "unins000.exe"):
                    jalankan(["taskkill", "/F", "/IM", nama], tunggu=30)
                time.sleep(3)
                for _ in range(20):
                    if not folder.exists():
                        break
                    time.sleep(1)

            if folder.exists():
                import shutil
                try:
                    shutil.rmtree(folder, ignore_errors=True)
                except Exception:
                    pass

            if folder.exists():
                print(f"   PERHATIAN: folder masih ada ({folder})")
                print("   tutup aplikasi lain lalu jalankan ulang skrip ini")
            else:
                print("   folder program sudah bersih")

    print("\n=== 3. Memasang versi baru ===")
    print(f"   installer: {INSTALLER.name}")
    if LOG.exists():
        LOG.unlink()
    kode, keluaran = jalankan([
        str(INSTALLER), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART",
        f"/DIR={TUJUAN}", f"/LOG={LOG}"], tunggu=600)
    print(f"   kode keluar: {kode}")

    berhasil = False
    if LOG.exists():
        isi = LOG.read_text(encoding="utf-8", errors="replace")
        berhasil = "Installation process succeeded" in isi
    print(f"   hasil: {'BERHASIL' if berhasil else 'PERLU DIPERIKSA'}")

    print("\n=== 4. Pemeriksaan akhir ===")
    exe = TUJUAN / "AkunTuntas.exe"
    if exe.exists():
        print(f"   aplikasi terpasang: {exe}")
        print(f"   ukuran: {exe.stat().st_size:,} byte")
        kode, keluaran = jalankan([str(exe), "--version"], tunggu=60)
        print(f"   versi: {keluaran.strip()}")
    else:
        print(f"   aplikasi TIDAK ditemukan di {TUJUAN}")
        return 1

    print("\nData pembukuan di %LOCALAPPDATA%\\AkunTuntas tidak dihapus.")
    return 0 if berhasil else 1


if __name__ == "__main__":
    sys.exit(main())
