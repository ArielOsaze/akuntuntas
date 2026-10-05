"""
Periksa kamera mana yang tersedia dan apa namanya.

Sebagian kamera virtual tidak muncul di daftar perangkat Windows, tetapi
tetap dapat dibuka oleh aplikasi. Skrip ini mencari tahu kamera mana saja
yang benar-benar dapat dibuka, beserta namanya, supaya sumber kamera
dapat dipilih dengan tepat.

Cara pakai:
    python tools/cek_semua_kamera.py
"""
from __future__ import annotations

import subprocess
import sys

import cv2


def nama_perangkat() -> list[str]:
    """Daftar nama kamera dari Windows."""
    keluaran = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "Get-PnpDevice -Class Camera,Image -ErrorAction SilentlyContinue "
         "| Select-Object -ExpandProperty FriendlyName"],
        capture_output=True, text=True, timeout=120)
    return [b.strip() for b in keluaran.stdout.splitlines() if b.strip()]


def nama_dari_ffmpeg() -> list[str]:
    """Daftar nama kamera dari DirectShow, sering lebih lengkap."""
    keluaran = subprocess.run(
        ["ffmpeg", "-hide_banner", "-list_devices", "true",
         "-f", "dshow", "-i", "dummy"],
        capture_output=True, text=True, timeout=120)

    hasil = []
    for baris in keluaran.stderr.splitlines():
        if '"' in baris and ("Video" in baris or "Audio" in baris):
            awal = baris.find('"')
            akhir = baris.find('"', awal + 1)
            if awal >= 0 and akhir > awal:
                nama = baris[awal + 1:akhir]
                if nama not in hasil:
                    hasil.append(nama)
    return hasil


def utama() -> int:
    print("=" * 70)
    print("  SEMUA KAMERA YANG TERSEDIA")
    print("=" * 70)
    print()

    print("=== DARI WINDOWS ===")
    pnp = nama_perangkat()
    for nama in pnp:
        print(f"  {nama}")
    if not pnp:
        print("  (tidak ada)")

    print()
    print("=== DARI DIRECTSHOW ===")
    dshow = nama_dari_ffmpeg()
    for nama in dshow:
        print(f"  {nama}")
    if not dshow:
        print("  (tidak terbaca)")

    print()
    print("=== UJI BUKA TIAP INDEX ===")
    print()

    terbuka = []
    for i in range(5):
        kamera = cv2.VideoCapture(i, cv2.CAP_DSHOW)
        if not kamera.isOpened():
            kamera.release()
            kamera = cv2.VideoCapture(i)

        if not kamera.isOpened():
            kamera.release()
            print(f"  index {i}: tidak ada")
            continue

        lebar = int(kamera.get(cv2.CAP_PROP_FRAME_WIDTH))
        tinggi = int(kamera.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # Coba baca satu gambar untuk memastikan benar-benar hidup.
        berhasil, gambar = kamera.read()
        kecerahan = gambar.mean() if berhasil else -1

        kamera.release()

        status = "hidup" if berhasil and kecerahan > 3 else (
            "gelap" if berhasil else "tidak terbaca")

        print(f"  index {i}: TERBUKA  {lebar}x{tinggi}  "
              f"(rasio {lebar / tinggi:.4f})  gambar: {status}")
        terbuka.append((i, lebar, tinggi))

    print()
    print("=" * 70)

    if not terbuka:
        print("  TIDAK ADA kamera yang bisa dibuka")
        return 1

    print(f"  {len(terbuka)} kamera tersedia")

    if len(terbuka) >= 2:
        print()
        print("  Ada lebih dari satu kamera. Yang biasanya dipakai:")
        print("    index 0 : kamera asli (USB Camera)")
        for i, l, t in terbuka[1:]:
            print(f"    index {i} : kemungkinan kamera virtual "
                  f"({l}x{t})")
        print()
        print("  Untuk kamera virtual, jalankan:")
        print("    python tools/jendela_kamera.py --virtual")

    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(utama())
