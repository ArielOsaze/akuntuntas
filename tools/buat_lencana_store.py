"""
Buat gambar lencana Microsoft Store untuk situs AkunTuntas.

Lencana digambar sendiri, bukan diambil dari internet, supaya berkasnya
ikut terpasang bersama situs dan tidak bergantung pada layanan luar.
Bentuknya mengikuti lencana resmi Microsoft: kotak hitam dengan lambang
Store di kiri dan dua baris tulisan di kanan.

Hasil:
    web/ms-store.png         lencana lebar  (untuk tombol di halaman unduh)
    web/ms-store-kecil.png   lencana ringkas (untuk kaki halaman)

Cara pakai:
    python tools/buat_lencana_store.py
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

AKAR = Path(__file__).resolve().parent.parent
WEB = AKAR / "web"

# Warna lencana resmi Microsoft Store.
HITAM = (0, 0, 0)
PUTIH = (255, 255, 255)


def font_terbaik(ukuran: int):
    """Font sistem terbaik yang tersedia, dengan cadangan bawaan."""
    pilihan = [
        r"C:\Windows\Fonts\segoeui.ttf",
        r"C:\Windows\Fonts\segoeuib.ttf",
        r"C:\Windows\Fonts\arial.ttf",
    ]
    for jalur in pilihan:
        if Path(jalur).exists():
            try:
                return ImageFont.truetype(jalur, ukuran)
            except Exception:
                continue
    return ImageFont.load_default()


def font_tebal(ukuran: int):
    pilihan = [
        r"C:\Windows\Fonts\segoeuib.ttf",
        r"C:\Windows\Fonts\segoeuibd.ttf",
        r"C:\Windows\Fonts\arialbd.ttf",
    ]
    for jalur in pilihan:
        if Path(jalur).exists():
            try:
                return ImageFont.truetype(jalur, ukuran)
            except Exception:
                continue
    return font_terbaik(ukuran)


def gambar_lambang_store(d, kiri: int, atas: int, sisi: int) -> None:
    """Lambang Microsoft Store: empat kaca bersudut miring."""
    celah = max(2, sisi // 12)
    lebar_kaca = (sisi - celah) // 2

    for kolom in range(2):
        for baris in range(2):
            x = kiri + kolom * (lebar_kaca + celah)
            y = atas + baris * (lebar_kaca + celah)

            # Bentuk jajar genjang: sisi kiri lebih pendek di atas,
            # mengikuti lambang Store yang miring.
            miring = max(1, lebar_kaca // 7)
            titik = [
                (x + (miring if baris == 0 else 0), y),
                (x + lebar_kaca, y),
                (x + lebar_kaca - (0 if baris == 0 else 0), y + lebar_kaca),
                (x, y + lebar_kaca),
            ]
            if baris == 0:
                titik = [
                    (x + miring, y),
                    (x + lebar_kaca, y),
                    (x + lebar_kaca, y + lebar_kaca),
                    (x, y + lebar_kaca),
                ]
            d.polygon(titik, fill=PUTIH)


def buat_lencana(lebar: int, tinggi: int, skala: int = 4) -> Image.Image:
    """Gambar lencana Store pada ukuran tertentu."""
    W, H = lebar * skala, tinggi * skala
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)

    radius = int(H * 0.20)
    d.rounded_rectangle([0, 0, W - 1, H - 1], radius=radius, fill=HITAM)

    # Lambang di kiri
    sisi = int(H * 0.40)
    kiri_lambang = int(W * 0.085)
    atas_lambang = (H - sisi) // 2
    gambar_lambang_store(d, kiri_lambang, atas_lambang, sisi)

    # Tulisan di kanan
    kiri_teks = kiri_lambang + sisi + int(W * 0.062)
    ukuran_kecil = max(9, int(H * 0.155))
    ukuran_besar = max(13, int(H * 0.285))

    f_kecil = font_terbaik(ukuran_kecil)
    f_besar = font_tebal(ukuran_besar)

    teks_atas = "Dapatkan dari"
    teks_bawah = "Microsoft Store"

    b_atas = d.textbbox((0, 0), teks_atas, font=f_kecil)
    b_bawah = d.textbbox((0, 0), teks_bawah, font=f_besar)
    jarak_baris = int(H * 0.055)
    tinggi_total = ((b_atas[3] - b_atas[1]) + (b_bawah[3] - b_bawah[1])
                    + jarak_baris)

    y = (H - tinggi_total) // 2
    d.text((kiri_teks, y - b_atas[1]), teks_atas, font=f_kecil, fill=PUTIH)
    y += (b_atas[3] - b_atas[1]) + jarak_baris
    d.text((kiri_teks, y - b_bawah[1]), teks_bawah, font=f_besar, fill=PUTIH)

    return im.resize((lebar, tinggi), Image.LANCZOS)


def main() -> int:
    print("=" * 74)
    print("  BUAT LENCANA MICROSOFT STORE")
    print("=" * 74)

    keluaran = [
        ("ms-store.png", 220, 66),
        ("ms-store-kecil.png", 132, 40),
    ]

    for nama, lebar, tinggi in keluaran:
        im = buat_lencana(lebar, tinggi)
        berkas = WEB / nama
        im.save(berkas, "PNG", optimize=True)
        print(f"\n  [OK] {nama}  {lebar}x{tinggi}  "
              f"{berkas.stat().st_size / 1024:.1f} KB")

    print("\n  Lencana siap dipasang di halaman unduh dan kaki halaman.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
