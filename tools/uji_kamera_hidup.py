"""
Uji apakah kamera benar-benar mengirim gambar.

Bila gambar dari kamera seluruhnya hitam, pemisah latar tidak dapat
bekerja karena tidak ada orang yang bisa dikenali. Skrip ini memeriksa
beberapa hal sekaligus supaya jelas di mana masalahnya:

  1. Apakah kamera bisa dibuka
  2. Apakah gambar yang dikirim benar-benar berisi (tidak hitam)
  3. Resolusi yang benar-benar dipakai
  4. Beberapa gambar berturut-turut, untuk memastikan kameranya hidup

Cara pakai:
    python tools/uji_kamera_hidup.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import cv2
import numpy as np

AKAR = Path(__file__).resolve().parent.parent


def utama() -> int:
    print("=== 1. MEMBUKA KAMERA ===")

    kamera = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    cara = "DirectShow"
    if not kamera.isOpened():
        kamera = cv2.VideoCapture(0)
        cara = "bawaan"
    if not kamera.isOpened():
        print("  GAGAL kamera tidak bisa dibuka")
        print("  Periksa: kabel terpasang, tidak dipakai aplikasi lain")
        return 1

    print(f"  berhasil dibuka lewat {cara}")

    # Coba minta 16:9 supaya cocok dengan kotak face cam.
    kamera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    kamera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    time.sleep(1.5)

    lebar = int(kamera.get(cv2.CAP_PROP_FRAME_WIDTH))
    tinggi = int(kamera.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"  resolusi : {lebar}x{tinggi}  (rasio {lebar / tinggi:.4f})")

    print()
    print("=== 2. MENGAMBIL 10 GAMBAR ===")

    terang = []
    tersimpan = []

    for i in range(10):
        berhasil, gambar = kamera.read()
        if not berhasil:
            print(f"  gambar {i + 1}: GAGAL dibaca")
            continue

        rata = gambar.mean()
        maks = gambar.max()
        terang.append(rata)

        h, w = gambar.shape[:2]
        print(f"  gambar {i + 1}: {w}x{h}  "
              f"kecerahan rata-rata {rata:6.2f}  maksimum {maks:3d}")

        # Simpan gambar ke-3 dan ke-10 untuk diperiksa.
        if i in (2, 9):
            berkas = AKAR / f"_kamera_uji_{i + 1}.jpg"
            cv2.imwrite(str(berkas), gambar)
            tersimpan.append(berkas)

        time.sleep(0.15)

    kamera.release()

    print()
    print("=== 3. KESIMPULAN ===")

    if not terang:
        print("  Tidak ada gambar yang berhasil dibaca.")
        return 1

    rata_semua = sum(terang) / len(terang)
    print(f"  kecerahan rata-rata keseluruhan: {rata_semua:.2f}")

    if rata_semua < 3:
        print()
        print("  GAMBAR SELURUHNYA HITAM.")
        print()
        print("  Kamera terbuka, tetapi tidak ada cahaya yang masuk.")
        print("  Kemungkinan penyebab:")
        print("    1. Penutup lensa masih terpasang")
        print("    2. Kamera menghadap permukaan gelap atau tertutup")
        print("    3. Ruangan benar-benar gelap")
        print("    4. Kamera rusak atau kabelnya hanya mengisi daya")
        print()
        print("  Yang perlu dilakukan:")
        print("    - Buka penutup lensa kamera")
        print("    - Arahkan kamera ke tempat yang terang")
        print("    - Nyalakan lampu ruangan")
        print("    - Cabut dan pasang ulang kabel kamera")
        return 1

    if rata_semua < 25:
        print()
        print("  Gambar sangat gelap, tetapi masih ada isinya.")
        print("  Tambahkan cahaya supaya pemisah latar dapat bekerja.")
        return 1

    print()
    print("  Kamera mengirim gambar dengan cahaya yang cukup.")
    print("  Pemisah latar seharusnya dapat bekerja.")
    print()
    print("  Bila orang tidak terdeteksi:")
    print("    - Pastikan ada orang di depan kamera")
    print("    - Pastikan wajah dan badan terlihat, tidak terhalang")
    print("    - Pastikan latar belakang tidak sama warnanya dengan pakaian")

    for berkas in tersimpan:
        print(f"  contoh gambar: {berkas.name}")

    return 0


if __name__ == "__main__":
    sys.exit(utama())
