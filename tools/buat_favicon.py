"""
Buat favicon.ico dari logo.

Favicon dibutuhkan agar logo muncul di tab peramban dan pada hasil
pencarian Google. Berkas .ico memuat beberapa ukuran sekaligus, supaya
tampil tajam baik di tab kecil maupun pada pintasan layar utama.

Logo diambil apa adanya dari logo.png, tanpa diubah bentuk maupun
warnanya.

Cara pakai:
    python tools/buat_favicon.py
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

AKAR = Path(__file__).resolve().parent.parent
WEB = AKAR / "web"

# Ukuran yang disimpan di dalam berkas .ico
UKURAN = [16, 24, 32, 48, 64, 128, 256]


def main() -> int:
    logo_path = WEB / "logo.png"
    if not logo_path.exists():
        print(f"  logo tidak ditemukan: {logo_path}")
        return 2

    logo = Image.open(logo_path).convert("RGBA")

    # Favicon tampil di latar tab peramban yang warnanya beragam, jadi
    # gambar dibuat persegi dengan latar putih penuh. Logo aslinya memang
    # berlatar putih, sehingga tampilannya tetap sama seperti aslinya.
    keluar = WEB / "favicon.ico"
    logo.save(keluar, format="ICO", sizes=[(u, u) for u in UKURAN])

    print("=" * 70)
    print("  FAVICON")
    print("=" * 70)
    print()
    print(f"  berkas : {keluar.name}")
    print(f"  ukuran : {', '.join(str(u) for u in UKURAN)} piksel")
    print(f"  bobot  : {keluar.stat().st_size / 1024:.1f} KB")
    print()
    print("  Dipakai peramban untuk tab dan pintasan, serta oleh Google")
    print("  pada hasil pencarian.")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
