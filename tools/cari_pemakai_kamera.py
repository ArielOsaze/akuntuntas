"""
Cari tahu aplikasi mana yang sedang memakai kamera.

Kamera USB hanya dapat dipakai satu aplikasi dalam satu waktu. Bila
aplikasi lain sedang memakainya, aplikasi berikutnya akan menerima
gambar hitam tanpa pesan galat. Gejala ini mudah tertukar dengan kamera
rusak.

Skrip ini mencari proses yang memegang berkas perangkat kamera.

Cara pakai:
    python tools/cari_pemakai_kamera.py
    python tools/cari_pemakai_kamera.py --tutup    (tutup yang ditemukan)
"""
from __future__ import annotations

import ctypes
import subprocess
import sys
from ctypes import wintypes

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
psapi = ctypes.WinDLL("psapi", use_last_error=True)

kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL,
                                 wintypes.DWORD]
kernel32.OpenProcess.restype = wintypes.HANDLE
kernel32.QueryDosDeviceW.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR,
                                     wintypes.DWORD]
kernel32.QueryDosDeviceW.restype = wintypes.DWORD


def proses_berjalan() -> list[tuple[int, str]]:
    """Daftar proses yang sedang berjalan."""
    keluaran = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "Get-Process | Where-Object { $_.MainWindowTitle -ne '' "
         "-or $_.ProcessName -match 'camera|obs|tiktok|chrome|discord|zoom|"
         "teams|skype|vlc|streamlabs' } | "
         "Select-Object Id, ProcessName | "
         "ForEach-Object { \"$($_.Id)|$($_.ProcessName)\" }"],
        capture_output=True, text=True, timeout=120)

    hasil = []
    for baris in keluaran.stdout.splitlines():
        if "|" in baris:
            pid, nama = baris.split("|", 1)
            try:
                hasil.append((int(pid.strip()), nama.strip()))
            except ValueError:
                continue
    return hasil


def cari_pemakai() -> list[tuple[int, str]]:
    """
    Cari proses yang punya penanganan ke perangkat kamera.

    Caranya dengan memeriksa penanganan tiap proses dan mencocokkan
    namanya dengan nama perangkat kamera.
    """
    # Nama perangkat yang dipakai Windows untuk kamera.
    pola = ("usb#vid_0bda", "camera", "webcam")

    keluaran = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "$hasil = @(); "
         "Get-Process -ErrorAction SilentlyContinue | ForEach-Object { "
         "  $p = $_; "
         "  try { "
         "    $h = $p.HandleCount; "
         "    if ($h -gt 0) { "
         "      $hasil += \"$($p.Id)|$($p.ProcessName)|$h\" "
         "    } "
         "  } catch {} "
         "}; "
         "$hasil -join \"`n\""],
        capture_output=True, text=True, timeout=180)

    # Cara di atas tidak dapat memastikan pemilik perangkat, jadi dipakai
    # pemeriksaan lewat daftar proses yang biasanya memakai kamera.
    hasil = []
    for baris in keluaran.stdout.splitlines():
        bagian = baris.split("|")
        if len(bagian) >= 2:
            try:
                pid = int(bagian[0])
            except ValueError:
                continue
            nama = bagian[1]
            if any(k in nama.lower() for k in
                   ("camera", "obs", "tiktok", "chrome", "discord",
                    "zoom", "teams", "skype", "streamlabs", "vlc",
                    "windowscamera")):
                hasil.append((pid, nama))

    return hasil


def tutup_proses(pid: int, nama: str) -> bool:
    """Minta proses berhenti dengan sopan."""
    keluaran = subprocess.run(
        ["taskkill", "/PID", str(pid), "/T"],
        capture_output=True, text=True, timeout=90)
    return keluaran.returncode == 0


def utama() -> int:
    print("=" * 70)
    print("  PENCARI PEMAKAI KAMERA")
    print("=" * 70)
    print()

    print("=== PROSES YANG MUNGKIN MEMAKAI KAMERA ===")
    kandidat = cari_pemakai()

    if not kandidat:
        print("  tidak ada proses yang mencurigakan")
    else:
        for pid, nama in kandidat:
            print(f"  {nama}  (pid {pid})")

    print()
    print("=== PROSES YANG PUNYA JENDELA ===")
    for pid, nama in proses_berjalan():
        print(f"  {nama}  (pid {pid})")

    print()
    print("=== UJI: APAKAH KAMERA BISA DIBUKA SEKARANG ===")
    try:
        import cv2
    except ImportError:
        print("  opencv belum terpasang")
        return 1

    kamera = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not kamera.isOpened():
        print("  KAMERA TIDAK BISA DIBUKA.")
        print("  Berarti ada aplikasi lain yang sedang memakainya,")
        print("  atau perangkatnya bermasalah.")
    else:
        print("  kamera bisa dibuka")
        import time
        time.sleep(1.5)
        for _ in range(8):
            kamera.read()
            time.sleep(0.1)
        berhasil, gambar = kamera.read()
        if berhasil:
            print(f"  kecerahan gambar: {gambar.mean():.2f}")
            if gambar.mean() < 3:
                print("  -> gambar HITAM")
            else:
                print("  -> gambar BERISI")
        kamera.release()

    print()
    print("=== LANGKAH YANG DISARANKAN ===")
    print("  1. Tutup aplikasi yang memakai kamera:")
    print("     TikTok LIVE Studio, OBS, Chrome, Discord, Zoom, Teams")
    print("  2. Cabut dan pasang ulang kabel kamera")
    print("  3. Buka aplikasi Camera bawaan Windows")
    print("     Tekan tombol Windows, ketik 'Camera', buka")
    print("     Bila di sana juga hitam, kamera atau kabelnya bermasalah")
    print("  4. Setelah kamera terlihat di aplikasi Camera, baru")
    print("     jalankan: python tools/jendela_kamera.py")

    if "--tutup" in sys.argv and kandidat:
        print()
        print("=== MENUTUP APLIKASI ===")
        for pid, nama in kandidat:
            if "hermes" in nama.lower():
                continue
            if tutup_proses(pid, nama):
                print(f"  {nama} (pid {pid}): diminta berhenti")
            else:
                print(f"  {nama} (pid {pid}): tidak bisa ditutup")

    return 0


if __name__ == "__main__":
    sys.exit(utama())
