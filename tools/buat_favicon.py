"""
Buat favicon.ico dan logo-32.png dari logo.

Favicon dibutuhkan agar logo muncul di tab peramban dan pada hasil
pencarian Google. Berkas .ico memuat beberapa ukuran sekaligus, supaya
tampil tajam baik di tab kecil maupun pada pintasan layar utama.

Sudut favicon dibuat membulat agar tidak tampil sebagai kotak putih
kaku di antara tab peramban. Isi dan warna logo tidak diubah.

Cara pakai:
    python tools/buat_favicon.py
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw

AKAR = Path(__file__).resolve().parent.parent
WEB = AKAR / "web"

# Ukuran yang disimpan di dalam berkas .ico
UKURAN = [16, 24, 32, 48, 64, 128, 256]

# Jari-jari sudut sebagai bagian dari sisi gambar, dan lipatan
# penggambaran agar tepi lengkung tetap halus di ukuran kecil.
RASIO_SUDUT = 0.30
SKALA_ANTIALIAS = 4


def membulatkan_sudut(gambar: Image.Image) -> Image.Image:
    lebar, tinggi = gambar.size
    besar = gambar.resize(
        (lebar * SKALA_ANTIALIAS, tinggi * SKALA_ANTIALIAS), Image.LANCZOS
    )

    topeng = Image.new("L", besar.size, 0)
    deret = ImageDraw.Draw(topeng)
    deret.rounded_rectangle(
        (0, 0, besar.size[0] - 1, besar.size[1] - 1),
        radius=round(min(besar.size) * RASIO_SUDUT),
        fill=255,
    )
    besar.putalpha(topeng)

    return besar.resize((lebar, tinggi), Image.LANCZOS)


def main() -> int:
    logo_path = WEB / "logo.png"
    if not logo_path.exists():
        print(f"  logo tidak ditemukan: {logo_path}")
        return 2

    logo = Image.open(logo_path).convert("RGBA")
    bulat = membulatkan_sudut(logo)

    favicon = WEB / "favicon.ico"
    bulat.save(favicon, format="ICO", sizes=[(u, u) for u in UKURAN])

    logo32 = WEB / "logo-32.png"
    bulat.resize((32, 32), Image.LANCZOS).save(logo32, optimize=True)

    print("=" * 70)
    print("  FAVICON")
    print("=" * 70)
    print()
    print(f"  berkas : {favicon.name}, {logo32.name}")
    print(f"  ukuran : {', '.join(str(u) for u in UKURAN)} piksel")
    print(f"  bobot  : {favicon.stat().st_size / 1024:.1f} KB")
    print()
    print(f"  Sudut membulat {int(RASIO_SUDUT * 100)}% dengan latar transparan.")
    print("  Dipakai peramban untuk tab dan pintasan, serta oleh Google")
    print("  pada hasil pencarian.")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
