"""
Siapkan gambar latar kamera AkunTuntas dalam tiga bentuk rasio.

TikTok LIVE Studio punya fitur latar kamera bawaan yang bisa memakai
gambar sendiri. Gambar yang dipakai sebaiknya berbentuk sama dengan
kamera, supaya tidak terpotong dan tidak melar. Kamera USB umumnya
mengirim 4:3, sedangkan kanvas siaran berbentuk 9:16.

Skrip ini membuat tiga berkas dari satu gambar sumber:

    latar-akuntuntas-4x3.jpg    1280x960    cocok dengan kamera USB
    latar-akuntuntas-16x9.jpg   1920x1080   untuk kanvas mendatar
    latar-akuntuntas-9x16.jpg   1215x2160   untuk kanvas tegak

Berkas hasilnya ditaruh di live_overlay/gambar/siap-pakai-tiktok dan
disalin juga ke Desktop supaya mudah dipilih dari dalam TikTok.

Cara pakai:

    python tools/siapkan_latar_tiktok.py
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

from PIL import Image

AKAR = Path(__file__).resolve().parent.parent
SUMBER = AKAR / "live_overlay/gambar/latar-akuntuntas.png"
TUJUAN = AKAR / "live_overlay/gambar/siap-pakai-tiktok"
DESKTOP = Path.home() / "Desktop" / "Latar Kamera AkunTuntas"

# Warna latar AkunTuntas, dipakai untuk mengisi tepi yang kosong
NAVY = (30, 40, 45)

# Rasio kamera USB dan dua rasio kanvas siaran
BENTUK = [
    ("latar-akuntuntas-4x3.jpg", 1280, 960, "cocok dengan kamera USB"),
    ("latar-akuntuntas-16x9.jpg", 1920, 1080, "untuk kanvas mendatar"),
    ("latar-akuntuntas-9x16.jpg", 1215, 2160, "untuk kanvas tegak"),
]


def susun(gambar: Image.Image, lebar: int, tinggi: int) -> Image.Image:
    """Perbesar gambar supaya memenuhi bidang, lalu potong tengahnya.

    Cara ini menjaga bentuk asli gambar. Tidak ada bagian yang melar,
    hanya tepi yang berlebih dipotong.
    """
    rasio_bidang = lebar / tinggi
    rasio_gambar = gambar.width / gambar.height

    if rasio_gambar > rasio_bidang:
        # Gambar lebih lebar: samakan tinggi, potong kiri kanan
        skala = tinggi / gambar.height
        baru = gambar.resize(
            (max(1, round(gambar.width * skala)), tinggi), Image.LANCZOS
        )
        kiri = (baru.width - lebar) // 2
        kotak = (kiri, 0, kiri + lebar, tinggi)
    else:
        # Gambar lebih tinggi: samakan lebar, potong atas bawah
        skala = lebar / gambar.width
        baru = gambar.resize(
            (lebar, max(1, round(gambar.height * skala))), Image.LANCZOS
        )
        atas = (baru.height - tinggi) // 2
        kotak = (0, atas, lebar, atas + tinggi)

    return baru.crop(kotak)


def utama() -> int:
    if not SUMBER.exists():
        print(f"  Gambar sumber tidak ada: {SUMBER}")
        print("  Jalankan lebih dahulu: python tools/buat_latar_kamera.py")
        return 1

    asli = Image.open(SUMBER).convert("RGB")
    print(f"  Sumber: {SUMBER.name}  {asli.width}x{asli.height}")
    print()

    TUJUAN.mkdir(parents=True, exist_ok=True)
    hasil = []

    for nama, lebar, tinggi, keterangan in BENTUK:
        gambar = susun(asli, lebar, tinggi)
        jalur = TUJUAN / nama
        gambar.save(jalur, "JPEG", quality=92, optimize=True)

        ukuran_kb = jalur.stat().st_size / 1024
        rasio = lebar / tinggi
        print(f"  {nama}")
        print(f"      {lebar}x{tinggi}  rasio {rasio:.4f}  {ukuran_kb:.0f} KB  ({keterangan})")
        hasil.append(jalur)

    print()
    if DESKTOP.parent.exists():
        DESKTOP.mkdir(parents=True, exist_ok=True)
        for jalur in hasil:
            shutil.copy2(jalur, DESKTOP / jalur.name)
        print(f"  Salinan ditaruh di: {DESKTOP}")
    else:
        print("  Folder Desktop tidak ditemukan, salinan dilewati")

    print()
    print("  Di TikTok LIVE Studio:")
    print("     1. Klik sumber Camera, lalu buka bagian Background")
    print("     2. Pilih tab Custom")
    print("     3. Tambahkan gambar, arahkan ke folder di atas")
    print("     4. Pakai yang 4x3 supaya bentuknya sama dengan kamera")
    print("     5. Nyalakan Cutout supaya orang terpisah dari latar")
    return 0


if __name__ == "__main__":
    sys.exit(utama())
