"""
Buat gambar latar AkunTuntas untuk kamera siaran.

Gambar ini dipakai sebagai latar belakang kamera, sehingga saat siaran
yang tampak hanya orangnya dengan latar bernuansa AkunTuntas.

Dua bentuk dihasilkan:
  1. latar-hijau.png   warna hijau rata, untuk aplikasi siaran yang
                       menghapus latar dengan chroma key
  2. latar-akuntuntas.png  latar bermerek AkunTuntas, untuk aplikasi
                       siaran yang punya fitur Virtual Background

Ukuran gambar 1600x1200 (4:3), sama seperti bentuk kotak face cam.

Cara pakai:
    python tools/buat_latar_kamera.py
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

AKAR = Path(__file__).resolve().parent.parent
KELUARAN = AKAR / "live_overlay" / "gambar"
LOGO = KELUARAN / "logo.png"

LEBAR = 1600
TINGGI = 1200

NAVY = (30, 40, 45)
NAVY_TUA = (15, 41, 66)
BIRU = (27, 79, 138)
BIRU_MUDA = (23, 57, 92)
COKELAT = (176, 125, 75)
PUTIH = (255, 255, 255)

# Hijau chroma key. Nilai ini dipilih yang paling jarang muncul pada
# kulit dan pakaian, sehingga orangnya tidak ikut terhapus.
HIJAU = (0, 177, 64)


def font_terbaik(ukuran: int) -> ImageFont.FreeTypeFont:
    """Ambil font sistem terbaik yang tersedia."""
    for nama in ("segoeuib.ttf", "segoeui.ttf", "arialbd.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(nama, ukuran)
        except OSError:
            continue
    return ImageFont.load_default()


def buat_hijau() -> Path:
    """Latar hijau rata untuk chroma key."""
    gambar = Image.new("RGB", (LEBAR, TINGGI), HIJAU)
    berkas = KELUARAN / "latar-hijau.png"
    gambar.save(berkas, optimize=True)
    return berkas


def buat_akuntuntas() -> Path:
    """
    Latar bermerek AkunTuntas untuk kamera siaran.

    Latar ini tampil di dalam kotak face cam yang kecil pada hasil siaran.
    Karena itu hanya dua hal yang ditampilkan: nama merek dan tautan situs.
    Keduanya dibuat besar supaya tetap terbaca setelah diperkecil. Teks
    tambahan justru menghilang saat diperkecil dan membuat tampilan penuh.
    """
    gambar = Image.new("RGB", (LEBAR, TINGGI), NAVY)

    # ---- Bentuk miring dua warna merek, dilembutkan ----
    lapis = Image.new("RGB", (LEBAR, TINGGI), NAVY)
    lukis_lapis = ImageDraw.Draw(lapis)
    lukis_lapis.polygon(
        [(0, TINGGI), (0, int(TINGGI * 0.40)),
         (int(LEBAR * 0.70), TINGGI)], fill=NAVY_TUA)
    lukis_lapis.polygon(
        [(LEBAR, 0), (LEBAR, TINGGI), (int(LEBAR * 0.44), TINGGI)],
        fill=BIRU_MUDA)
    lapis = lapis.filter(ImageFilter.GaussianBlur(50))
    gambar = Image.blend(gambar, lapis, 0.88)

    # ---- Cahaya cokelat di sudut kanan atas ----
    lapis_cahaya = Image.new("RGBA", (LEBAR, TINGGI), (0, 0, 0, 0))
    lukis_cahaya = ImageDraw.Draw(lapis_cahaya)
    cx, cy = int(LEBAR * 0.90), int(TINGGI * 0.14)
    for radius, alpha in ((620, 34), (440, 46)):
        lukis_cahaya.ellipse(
            [cx - radius, cy - radius, cx + radius, cy + radius],
            fill=(*COKELAT, alpha))
    lapis_cahaya = lapis_cahaya.filter(ImageFilter.GaussianBlur(90))
    gambar = Image.alpha_composite(
        gambar.convert("RGBA"), lapis_cahaya).convert("RGB")

    # ---- Sisi kiri digelapkan supaya teks menonjol ----
    gradasi = Image.new("L", (LEBAR, TINGGI), 0)
    lukis_gradasi = ImageDraw.Draw(gradasi)
    for x in range(LEBAR):
        nilai = int(165 * max(0.0, 1.0 - x / (LEBAR * 0.72)))
        lukis_gradasi.line([(x, 0), (x, TINGGI)], fill=nilai)
    gelap = Image.new("RGB", (LEBAR, TINGGI), (5, 12, 22))
    gambar = Image.composite(gelap, gambar, gradasi)
    lukis = ImageDraw.Draw(gambar)

    # ---- Hanya dua elemen: nama merek dan tautan situs ----

    # Nama merek, sangat besar, di bagian atas.
    font_nama = font_terbaik(168)
    lukis.text((120, 128), "AkunTuntas", font=font_nama, fill=PUTIH)

    # Garis aksen cokelat di bawah nama.
    kotak_nama = lukis.textbbox((120, 128), "AkunTuntas", font=font_nama)
    lukis.rectangle(
        [122, kotak_nama[3] + 34, 122 + 330, kotak_nama[3] + 34 + 12],
        fill=COKELAT)

    # Tautan situs, besar, di bagian bawah, dalam kotak biru.
    font_tautan = font_terbaik(96)
    teks_tautan = "akuntuntas.xinet.id"
    kotak_tautan = lukis.textbbox((0, 0), teks_tautan, font=font_tautan)
    lebar_tautan = kotak_tautan[2] - kotak_tautan[0]

    x_tautan = 122
    y_tautan = TINGGI - 290

    lukis.rounded_rectangle(
        [x_tautan - 40, y_tautan - 40,
         x_tautan + lebar_tautan + 40, y_tautan + 138],
        radius=28, fill=BIRU)
    lukis.text((x_tautan, y_tautan), teks_tautan, font=font_tautan,
               fill=PUTIH)

    berkas = KELUARAN / "latar-akuntuntas.png"
    gambar.save(berkas, optimize=True)
    return berkas


def buat_pratinjau() -> Path:
    """
    Buat pratinjau ukuran sebenarnya (400x300).

    Kotak face cam di overlay hanya 400x300. Pratinjau ini memperlihatkan
    bagaimana latar terlihat pada ukuran itu, supaya keterbacaannya dapat
    diperiksa sebelum siaran.
    """
    sumber = KELUARAN / "latar-akuntuntas.png"
    gambar = Image.open(sumber).convert("RGB")
    kecil = gambar.resize((400, 300), Image.LANCZOS)

    # Susun bersebelahan dengan versi penuh untuk pembanding.
    kanvas = Image.new("RGB", (400, 300 * 2 + 20), (20, 20, 22))
    kanvas.paste(kecil, (0, 0))

    tengah = Image.open(sumber).convert("RGB").resize(
        (400, 300), Image.LANCZOS)
    kanvas.paste(tengah, (0, 320))

    berkas = KELUARAN / "latar-pratinjau-400x300.png"
    kanvas.save(berkas)
    return berkas


def utama() -> int:
    if not KELUARAN.exists():
        print(f"  GAGAL folder tidak ada: {KELUARAN}")
        return 1

    print("=== MEMBUAT GAMBAR LATAR KAMERA ===")
    print()

    berkas_hijau = buat_hijau()
    im = Image.open(berkas_hijau)
    print(f"  1. {berkas_hijau.name}")
    print(f"     {im.width}x{im.height}  warna hijau {HIJAU}")
    print("     untuk chroma key di aplikasi siaran")

    berkas_merek = buat_akuntuntas()
    im = Image.open(berkas_merek)
    print()
    print(f"  2. {berkas_merek.name}")
    print(f"     {im.width}x{im.height}  bernuansa AkunTuntas")
    print("     untuk fitur Virtual Background")

    berkas_pratinjau = buat_pratinjau()
    print()
    print(f"  3. {berkas_pratinjau.name}")
    print("     pratinjau ukuran sebenarnya di kotak face cam (400x300)")

    print()
    print("=== CARA PAKAI DI TIKTOK LIVE STUDIO ===")
    print("  1. Buka efek, pilih kategori background")
    print("  2. Pilih 'Virtual Background (Static/Dynamic)'")
    print(f"  3. Pilih gambar: {berkas_merek.name}")
    print("  4. Atur Similarity dan Smoothness sesuai kebutuhan")
    print()
    print("  Untuk latar hijau, pilih gambar latar-hijau.png lalu atur")
    print("  warna kunci hijau pada pengaturan chroma key.")

    return 0


if __name__ == "__main__":
    sys.exit(utama())
