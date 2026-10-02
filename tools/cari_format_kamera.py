"""
Cari format gambar yang benar untuk kamera USB.

Sebagian kamera USB tidak mengirim gambar yang benar bila formatnya tidak
diminta secara khusus. Gejalanya khas: kamera terbuka tanpa galat, tetapi
gambar yang diterima seluruhnya hitam.

Penyebabnya, kabel USB 2.0 tidak cukup lebar untuk mengirim gambar
berukuran besar dalam format mentah. Kamera menyediakan format padat
(MJPG) untuk mengatasinya. Bila format itu tidak diminta, gambar yang
diterima rusak.

Skrip ini mencoba beberapa format dan resolusi, lalu melaporkan mana yang
menghasilkan gambar benar.

Cara pakai:
    python tools/cari_format_kamera.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import cv2

AKAR = Path(__file__).resolve().parent.parent

# Format yang umum didukung kamera USB.
FORMAT = {
    "MJPG": cv2.VideoWriter_fourcc(*"MJPG"),
    "YUY2": cv2.VideoWriter_fourcc(*"YUY2"),
}

# Kombinasi yang akan dicoba, dari yang paling diinginkan.
UJIAN = [
    ("MJPG", 1280, 720),
    ("MJPG", 640, 480),
    ("YUY2", 640, 480),
    ("YUY2", 320, 240),
    (None, 640, 480),
    (None, 1280, 720),
]


def uji(nama_format: str | None, lebar: int, tinggi: int) -> dict:
    """Coba satu kombinasi format dan resolusi."""
    hasil = {"format": nama_format or "bawaan", "diminta": (lebar, tinggi)}

    kamera = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not kamera.isOpened():
        kamera = cv2.VideoCapture(0)
    if not kamera.isOpened():
        hasil["galat"] = "kamera tidak bisa dibuka"
        return hasil

    if nama_format:
        kamera.set(cv2.CAP_PROP_FOURCC, FORMAT[nama_format])
    kamera.set(cv2.CAP_PROP_FRAME_WIDTH, lebar)
    kamera.set(cv2.CAP_PROP_FRAME_HEIGHT, tinggi)

    # Beri waktu kamera menyesuaikan diri.
    time.sleep(1.8)

    # Buang beberapa gambar pertama, biasanya masih gelap.
    for _ in range(6):
        kamera.read()
        time.sleep(0.12)

    terang = []
    gambar_terbaik = None

    for _ in range(4):
        berhasil, gambar = kamera.read()
        if not berhasil:
            continue
        terang.append(gambar.mean())
        if gambar_terbaik is None or gambar.mean() > gambar_terbaik[1]:
            gambar_terbaik = (gambar, gambar.mean())
        time.sleep(0.12)

    lebar_asli = int(kamera.get(cv2.CAP_PROP_FRAME_WIDTH))
    tinggi_asli = int(kamera.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fourcc = int(kamera.get(cv2.CAP_PROP_FOURCC))

    kamera.release()

    hasil["didapat"] = (lebar_asli, tinggi_asli)
    hasil["fourcc"] = "".join(chr((fourcc >> (8 * i)) & 0xFF)
                              for i in range(4)).strip("\x00")
    hasil["kecerahan"] = sum(terang) / len(terang) if terang else 0.0

    if gambar_terbaik and gambar_terbaik[1] > 3:
        nama = (f"_format_{hasil['format']}_"
                f"{lebar_asli}x{tinggi_asli}.jpg")
        cv2.imwrite(str(AKAR / nama), gambar_terbaik[0])
        hasil["contoh"] = nama

    return hasil


def utama() -> int:
    print("=" * 70)
    print("  CARI FORMAT GAMBAR KAMERA USB")
    print("=" * 70)
    print()
    print("  Menguji beberapa format. Tiap ujian perlu beberapa detik.")
    print()

    cocok = []

    for nama_format, lebar, tinggi in UJIAN:
        label = f"{nama_format or 'bawaan':7} {lebar}x{tinggi}"
        print(f"  {label} ...", end="", flush=True)

        hasil = uji(nama_format, lebar, tinggi)

        if "galat" in hasil:
            print(f"  GAGAL: {hasil['galat']}")
            continue

        kecerahan = hasil["kecerahan"]
        didapat = hasil["didapat"]

        if kecerahan > 25:
            tanda = "BERHASIL"
            cocok.append(hasil)
        elif kecerahan > 3:
            tanda = "redup"
        else:
            tanda = "hitam"

        print(f"  {tanda:9} didapat {didapat[0]}x{didapat[1]}  "
              f"format {hasil['fourcc']:5}  kecerahan {kecerahan:6.2f}")

    print()
    print("=" * 70)

    if not cocok:
        print("  TIDAK ADA format yang menghasilkan gambar terang.")
        print()
        print("  Berarti masalahnya bukan pada format, melainkan pada")
        print("  perangkat atau pencahayaan. Periksa:")
        print("    1. Penutup lensa sudah dibuka")
        print("    2. Ruangan cukup terang")
        print("    3. Kamera tidak sedang dipakai aplikasi lain")
        print("       (TikTok LIVE Studio, OBS, Chrome, Discord)")
        print("    4. Coba buka aplikasi Camera bawaan Windows")
        print("       Bila di sana juga hitam, kamera atau kabelnya")
        print("       yang bermasalah.")
        return 1

    print(f"  {len(cocok)} format menghasilkan gambar terang:")
    print()

    for hasil in cocok:
        print(f"    format {hasil['format']:7} "
              f"{hasil['didapat'][0]}x{hasil['didapat'][1]}  "
              f"kecerahan {hasil['kecerahan']:.1f}")

    terbaik = max(cocok, key=lambda h: h["kecerahan"])
    print()
    print("  Format terbaik:")
    print(f"    {terbaik['format']} {terbaik['didapat'][0]}x"
          f"{terbaik['didapat'][1]}")
    print()
    print("  Format ini akan dipakai oleh jendela kamera.")
    print("  Jalankan: python tools/jendela_kamera.py")

    for hasil in cocok:
        if "contoh" in hasil:
            print(f"  contoh gambar: {hasil['contoh']}")

    return 0


if __name__ == "__main__":
    sys.exit(utama())
