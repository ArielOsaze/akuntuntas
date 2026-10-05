"""
Cari nomor index tiap kamera beserta namanya.

Aplikasi membuka kamera berdasarkan nomor, bukan nama. Karena itu nomor
tiap kamera perlu diketahui lebih dahulu, terutama bila ada lebih dari
satu kamera terpasang.

Skrip ini mencocokkan nomor index dengan nama perangkat, dengan cara
membuka tiap nomor dan membandingkan ukuran gambar yang diterima.

Cara pakai:
    python tools/cari_index_kamera.py
"""
from __future__ import annotations

import subprocess
import sys
import time

import cv2


def nama_perangkat() -> list[str]:
    """Daftar nama kamera dari DirectShow, berurutan."""
    keluaran = subprocess.run(
        ["ffmpeg", "-hide_banner", "-list_devices", "true",
         "-f", "dshow", "-i", "dummy"],
        capture_output=True, text=True, timeout=120)

    hasil = []
    for baris in keluaran.stderr.splitlines():
        if "(video)" in baris and '"' in baris:
            awal = baris.find('"')
            akhir = baris.find('"', awal + 1)
            if awal >= 0 and akhir > awal:
                nama = baris[awal + 1:akhir]
                if nama not in hasil:
                    hasil.append(nama)
    return hasil


def utama() -> int:
    print("=" * 72)
    print("  NAMA KAMERA DARI DIRECTSHOW")
    print("=" * 72)
    print()

    nama = nama_perangkat()
    for i, n in enumerate(nama):
        tanda = ""
        if "obs" in n.lower():
            tanda = "  <- kamera virtual OBS"
        elif "virtual" in n.lower():
            tanda = "  <- kamera virtual lain"
        print(f"  {i}. {n}{tanda}")

    print()
    print("=" * 72)
    print("  UJI BUKA TIAP NOMOR INDEX")
    print("=" * 72)
    print()

    hasil = []

    for i in range(6):
        kamera = cv2.VideoCapture(i, cv2.CAP_DSHOW)
        if not kamera.isOpened():
            kamera.release()
            kamera = cv2.VideoCapture(i)

        if not kamera.isOpened():
            kamera.release()
            continue

        # Beri waktu kamera menyiapkan diri, lalu buang gambar pertama.
        time.sleep(1.2)
        for _ in range(6):
            kamera.read()
            time.sleep(0.1)

        berhasil, gambar = kamera.read()
        kamera.release()

        if not berhasil:
            print(f"  index {i}: terbuka tetapi gambar tidak terbaca")
            continue

        h, w = gambar.shape[:2]
        kecerahan = gambar.mean()

        # Cocokkan dengan nama berdasarkan urutan.
        dugaan = nama[i] if i < len(nama) else "?"

        print(f"  index {i}:")
        print(f"    ukuran    : {w}x{h}")
        print(f"    kecerahan : {kecerahan:.2f}"
              f"{'  (gelap)' if kecerahan < 3 else ''}")
        print(f"    dugaan    : {dugaan}")

        hasil.append((i, w, h, dugaan))

    print()
    print("=" * 72)

    # Cari kamera virtual OBS
    index_obs = None
    for i, w, h, dugaan in hasil:
        if "obs" in dugaan.lower():
            index_obs = i
            break

    if index_obs is not None:
        print(f"  Kamera virtual OBS ada di index {index_obs}")
        print()
        print("  Untuk memakai kamera virtual:")
        print("    python tools/jendela_kamera.py --virtual")
    else:
        print("  Kamera virtual OBS tidak terdeteksi dari daftar nomor.")
        print("  Kemungkinan nomor indexnya berbeda dari urutan nama.")
        print()
        print("  Coba jalankan dengan nomor tertentu:")
        for i, w, h, dugaan in hasil:
            print(f"    python tools/jendela_kamera.py --virtual --index {i}"
                  f"   ({w}x{h}, {dugaan})")

    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(utama())
