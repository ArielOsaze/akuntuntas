"""
Buat gambar pratinjau tautan (Open Graph) berukuran 1200x630.

Gambar ini yang muncul sebagai thumbnail saat tautan situs dibagikan di
WhatsApp, Facebook, X, LinkedIn, atau Slack. Ukuran 1200x630 adalah
nisbah yang diminta layanan-layanan itu (1.91 banding 1).

Logo diambil apa adanya dari berkas logo.png dan hanya ditempatkan pada
latar, tanpa diubah bentuk maupun warnanya.

Cara pakai:
    python tools/buat_pratinjau.py
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

AKAR = Path(__file__).resolve().parent.parent
WEB = AKAR / "web"

LEBAR, TINGGI = 1200, 630

# Warna merek, diambil dari styles.css supaya tetap selaras dengan situs.
NAVY = (15, 41, 66)
NAVY_MUDA = (26, 58, 88)
BIRU = (27, 79, 138)
PUTIH = (255, 255, 255)
ABU_TERANG = (201, 216, 229)
ABU_SEDANG = (143, 167, 190)


def huruf(ukuran: int, tebal: bool = False):
    """Ambil huruf sistem yang tersedia, dengan ukuran tertentu."""
    calon = []
    if tebal:
        calon = ["segoeuib.ttf", "arialbd.ttf", "calibrib.ttf"]
    else:
        calon = ["segoeui.ttf", "arial.ttf", "calibri.ttf"]

    for nama in calon:
        try:
            return ImageFont.truetype(nama, ukuran)
        except OSError:
            continue

    # Bila tidak ada yang tersedia, pakai huruf bawaan Pillow.
    return ImageFont.load_default()


def main() -> int:
    logo_path = WEB / "logo.png"
    if not logo_path.exists():
        print(f"  logo tidak ditemukan: {logo_path}")
        return 2

    gambar = Image.new("RGB", (LEBAR, TINGGI), NAVY)
    lukis = ImageDraw.Draw(gambar)

    # Latar bergradasi halus dari navy ke navy yang sedikit lebih terang,
    # supaya gambar tidak terlihat datar.
    for y in range(TINGGI):
        t = y / TINGGI
        warna = tuple(
            int(NAVY[i] + (NAVY_MUDA[i] - NAVY[i]) * t) for i in range(3))
        lukis.line([(0, y), (LEBAR, y)], fill=warna)

    # Garis aksen biru di tepi atas, meniru garis aksen di aplikasi.
    lukis.rectangle([0, 0, LEBAR, 6], fill=BIRU)

    # Logo ditempatkan apa adanya, tanpa diubah. Latarnya putih penuh,
    # jadi diberi bingkai putih membulat supaya menyatu dengan latar navy.
    logo = Image.open(logo_path).convert("RGB")
    sisi_logo = 210
    logo = logo.resize((sisi_logo, sisi_logo), Image.LANCZOS)

    kiri_logo = 96
    atas_logo = (TINGGI - sisi_logo) // 2
    gambar.paste(logo, (kiri_logo, atas_logo))

    # Tulisan di sebelah kanan logo.
    kiri_teks = kiri_logo + sisi_logo + 56

    lukis.text((kiri_teks, 176), "AkunTuntas",
               font=huruf(72, tebal=True), fill=PUTIH)
    lukis.text((kiri_teks, 268),
               "Pembukuan dan pajak perusahaan Indonesia",
               font=huruf(31), fill=ABU_TERANG)

    # Tiga keterangan singkat, dipisah titik tengah.
    keterangan = "Lokal  ·  Sesuai aturan  ·  Sekali bayar"
    lukis.text((kiri_teks, 330), keterangan,
               font=huruf(26), fill=ABU_SEDANG)

    # Nama domain di sudut bawah, supaya sumber tautan jelas.
    lukis.text((kiri_teks, 424), "akuntuntas.xinet.id",
               font=huruf(28, tebal=True), fill=PUTIH)

    keluar = WEB / "pratinjau.png"
    gambar.save(keluar, "PNG", optimize=True)

    ukuran_kb = keluar.stat().st_size / 1024
    print("=" * 70)
    print("  GAMBAR PRATINJAU TAUTAN")
    print("=" * 70)
    print()
    print(f"  berkas : {keluar.name}")
    print(f"  ukuran : {gambar.size[0]}x{gambar.size[1]} piksel")
    print(f"  bobot  : {ukuran_kb:.0f} KB")
    print()
    print("  Dipakai oleh WhatsApp, Facebook, X, LinkedIn, dan Slack")
    print("  sebagai thumbnail saat tautan situs dibagikan.")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
