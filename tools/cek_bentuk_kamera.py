"""
Periksa bentuk dan kemampuan kamera USB.

Gambar kamera yang bentuknya tidak sama dengan kotak face cam akan
terpotong saat dipaksa mengisi kotak, sehingga terlihat seperti
diperbesar. Skrip ini mencari tahu bentuk asli kamera dan resolusi apa
saja yang didukungnya, supaya kotak face cam dapat disesuaikan.

Cara pakai:
    python tools/cek_bentuk_kamera.py
"""
from __future__ import annotations

import subprocess
import sys


def resolusi_didukung() -> list[tuple[int, int]]:
    """Daftar resolusi yang didukung kamera, dari DirectShow."""
    hasil: list[tuple[int, int]] = []

    keluaran = subprocess.run(
        ["ffmpeg", "-hide_banner", "-f", "dshow",
         "-list_options", "true", "-i", "video=USB Camera"],
        capture_output=True, text=True, timeout=120)

    for baris in keluaran.stderr.splitlines():
        # Baris berisi "min s=640x480 fps=30 max s=640x480 fps=30"
        if "s=" in baris and "fps" in baris:
            for bagian in baris.split():
                if bagian.startswith("s="):
                    ukuran = bagian[2:]
                    if "x" in ukuran:
                        try:
                            l, t = ukuran.split("x")
                            pasangan = (int(l), int(t))
                            if pasangan not in hasil:
                                hasil.append(pasangan)
                        except ValueError:
                            continue

    return sorted(hasil, key=lambda p: p[0] * p[1], reverse=True)


def utama() -> int:
    import cv2

    print("=== BENTUK GAMBAR KAMERA ===")

    kamera = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not kamera.isOpened():
        kamera = cv2.VideoCapture(0)
    if not kamera.isOpened():
        print("  kamera tidak bisa dibuka")
        return 1

    berhasil, gambar = kamera.read()
    if berhasil:
        h, w = gambar.shape[:2]
        rasio = w / h
        print(f"  gambar asli: {w}x{h}")
        print(f"  rasio      : {rasio:.4f}")

        if abs(rasio - 16 / 9) < 0.02:
            print("  bentuk     : 16:9 mendatar")
        elif abs(rasio - 4 / 3) < 0.02:
            print("  bentuk     : 4:3")
        else:
            print(f"  bentuk     : lain ({rasio:.3f})")

    kamera.release()

    print()
    print("=== RESOLUSI YANG DIDUKUNG ===")
    daftar = resolusi_didukung()
    if daftar:
        for l, t in daftar:
            rasio = l / t
            if abs(rasio - 16 / 9) < 0.02:
                bentuk = "16:9"
            elif abs(rasio - 4 / 3) < 0.02:
                bentuk = "4:3"
            else:
                bentuk = f"{rasio:.3f}"
            print(f"  {l}x{t}  ({bentuk})")
    else:
        print("  tidak terbaca dari ffmpeg")

    print()
    print("=== KESIMPULAN ===")

    ada_16_9 = any(abs(l / t - 16 / 9) < 0.02 for l, t in daftar)

    if daftar and not ada_16_9:
        print("  Kamera ini hanya mendukung bentuk 4:3.")
        print("  Kotak face cam sebaiknya dibuat 4:3 juga, supaya gambar")
        print("  tidak terpotong dan tidak terlihat diperbesar.")
        print()
        print("  Jalankan untuk menyesuaikan kotak:")
        print("    python tools/sesuaikan_kotak_kamera.py")
    elif ada_16_9:
        print("  Kamera mendukung 16:9. Kamera dapat disetel ke bentuk itu")
        print("  supaya cocok dengan kotak face cam.")
        print()
        print("  Pilihan terbesar 16:9:", end=" ")
        for l, t in daftar:
            if abs(l / t - 16 / 9) < 0.02:
                print(f"{l}x{t}")
                break
    else:
        print("  Kemampuan kamera tidak terbaca. Coba jalankan ulang.")

    return 0


if __name__ == "__main__":
    sys.exit(utama())
