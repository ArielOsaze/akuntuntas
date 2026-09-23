"""Susun satu gambar promosi bergaya kartu macOS dari tangkapan layar.

Cara pakai:
    python tools/buat_promo_macos.py

Masukan  : folder _promosi/ berisi tangkapan layar halaman
Keluaran : _promosi/promo_akuntuntas.png

Komposisi memakai lima jendela: satu jendela utama di tengah, dua di kiri
dan dua di kanan dengan sudut simetris. Semua jendela berada utuh di dalam
kanvas sehingga tidak ada yang terpotong kasar.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

AKAR = Path(__file__).resolve().parent.parent
MASUK = AKAR / "_promosi"
KELUAR = MASUK / "promo_akuntuntas.png"

LEBAR, TINGGI = 2400, 1500
SKALA = 2                      # digambar 2x lalu diperkecil agar tajam

WARNA_LATAR = [(11, 30, 54), (27, 79, 138), (9, 24, 44)]
WARNA_JUDUL = (255, 255, 255)
WARNA_SUB = (168, 195, 224)
WARNA_AKSEN = (110, 231, 183)
WARNA_KET = (146, 173, 204)

MERAH = (255, 95, 87)
KUNING = (254, 188, 46)
HIJAU = (40, 200, 64)

# (berkas, judul jendela, lebar, sudut, titik tengah)
JENDELA = [
    ("laporan.png", "Laporan Keuangan", 660, -7.0, (455, 660)),
    ("pajak_lanjutan.png", "Pajak Lanjutan", 660, 7.0, (1945, 660)),
    ("penjualan.png", "Penjualan", 700, -3.5, (470, 878)),
    ("pajak.png", "Pajak & SPT", 700, 3.5, (1930, 878)),
]
JENDELA_UTAMA = ("dashboard.png", "Dashboard — AkunTuntas", 1400, (1200, 762))

LABEL_FITUR = [
    "PPN & PPh 21 (TER)",
    "PPh Badan Pasal 31E",
    "Neraca Otomatis",
    "Faktur Pajak & NSFP",
    "Uang Muka & Bea Meterai",
]


def font(ukuran: int, tebal: bool = False) -> ImageFont.FreeTypeFont:
    """Font sistem Windows; jatuh ke bawaan bila tidak tersedia."""
    nama = "segoeuib.ttf" if tebal else "segoeui.ttf"
    for folder in (r"C:\Windows\Fonts", "/usr/share/fonts/truetype"):
        jalur = Path(folder) / nama
        if jalur.exists():
            return ImageFont.truetype(str(jalur), ukuran)
    return ImageFont.load_default()


def gradien(ukuran: tuple, warna: list) -> Image.Image:
    """Latar gradien vertikal lembut dari tiga warna."""
    lebar, tinggi = ukuran
    kolom = Image.new("RGB", (1, tinggi))
    piksel = kolom.load()
    for y in range(tinggi):
        t = y / max(1, tinggi - 1)
        if t < 0.5:
            u, a, b = t / 0.5, warna[0], warna[1]
        else:
            u, a, b = (t - 0.5) / 0.5, warna[1], warna[2]
        piksel[0, y] = tuple(int(a[i] + (b[i] - a[i]) * u) for i in range(3))
    return kolom.resize((lebar, tinggi))


def cahaya(ukuran: tuple) -> Image.Image:
    """Bercak cahaya lembut supaya latar tidak terlihat datar."""
    lapis = Image.new("RGBA", ukuran, (0, 0, 0, 0))
    d = ImageDraw.Draw(lapis)
    lebar, tinggi = ukuran
    d.ellipse([lebar * 0.50, -tinggi * 0.40, lebar * 1.30, tinggi * 0.60],
              fill=(52, 118, 190, 140))
    d.ellipse([-lebar * 0.30, tinggi * 0.42, lebar * 0.50, tinggi * 1.35],
              fill=(27, 79, 138, 110))
    return lapis.filter(ImageFilter.GaussianBlur(160))


def sudut_membulat(gambar: Image.Image, radius: int) -> Image.Image:
    """Potong sudut gambar supaya membulat seperti jendela macOS."""
    gambar = gambar.convert("RGBA")
    topeng = Image.new("L", gambar.size, 0)
    ImageDraw.Draw(topeng).rounded_rectangle(
        [0, 0, gambar.width - 1, gambar.height - 1], radius=radius, fill=255)
    gambar.putalpha(topeng)
    return gambar


def bayangan(gambar: Image.Image, blur: int, geser: tuple,
             kegelapan: int) -> Image.Image:
    """Bayangan lembut; kanvas diberi ruang ekstra agar tidak terpotong."""
    pad = int(blur * 2.2)
    w, h = gambar.width + pad * 2, gambar.height + pad * 2
    kanvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    hitam = Image.new("RGBA", gambar.size, (0, 0, 0, kegelapan))
    kanvas.paste(hitam, (pad + geser[0], pad + geser[1]), gambar.split()[3])
    return kanvas.filter(ImageFilter.GaussianBlur(blur))


def bilah_judul(lebar: int, tinggi: int, teks: str) -> Image.Image:
    """Bilah judul jendela macOS dengan tiga tombol warna."""
    bilah = Image.new("RGBA", (lebar, tinggi), (237, 239, 243, 255))
    d = ImageDraw.Draw(bilah)
    d.rectangle([0, tinggi - 1, lebar, tinggi], fill=(203, 208, 216, 255))

    r = tinggi * 0.155
    pusat_y = tinggi / 2
    for i, warna in enumerate((MERAH, KUNING, HIJAU)):
        x = tinggi * 0.60 + i * (r * 3.2)
        d.ellipse([x - r, pusat_y - r, x + r, pusat_y + r], fill=warna)

    f = font(int(tinggi * 0.40), tebal=True)
    kotak = d.textbbox((0, 0), teks, font=f)
    d.text(((lebar - (kotak[2] - kotak[0])) / 2 - kotak[0],
            (tinggi - (kotak[3] - kotak[1])) / 2 - kotak[1]),
           teks, font=f, fill=(58, 64, 74, 255))
    return bilah


def buat_jendela(berkas: Path, judul: str, lebar: int,
                 derajat: float) -> Image.Image:
    """Bentuk jendela macOS (bilah judul + isi) lalu putar sedikit."""
    isi = Image.open(berkas).convert("RGB")
    isi = isi.resize((lebar, int(lebar * isi.height / isi.width)),
                     Image.LANCZOS)

    tinggi_bilah = max(34, int(lebar * 0.028))
    jendela = Image.new("RGBA", (lebar, isi.height + tinggi_bilah),
                        (255, 255, 255, 255))
    jendela.paste(bilah_judul(lebar, tinggi_bilah, judul), (0, 0))
    jendela.paste(isi, (0, tinggi_bilah))

    radius = int(lebar * 0.015)
    jendela = sudut_membulat(jendela, radius)
    if abs(derajat) > 0.01:
        jendela = jendela.rotate(derajat, resample=Image.BICUBIC, expand=True,
                                 fillcolor=(0, 0, 0, 0))
    return jendela


def tempel(kanvas: Image.Image, jendela: Image.Image, tengah: tuple,
           skala: int, kuat: bool = False):
    """Tempel jendela di titik tengah dengan dua lapis bayangan."""
    x = int(tengah[0] * skala - jendela.width / 2)
    y = int(tengah[1] * skala - jendela.height / 2)

    # bayangan lebar (menyebar) lalu bayangan rapat (menempel di bawah)
    lebar_b = bayangan(jendela, int((58 if kuat else 38) * skala),
                       (0, int((24 if kuat else 16) * skala)), 125)
    pad = int((58 if kuat else 38) * skala * 2.2)
    kanvas.alpha_composite(lebar_b, (x - pad, y - pad))
    rapat = bayangan(jendela, int(13 * skala), (0, int(5 * skala)), 155)
    pad2 = int(13 * skala * 2.2)
    kanvas.alpha_composite(rapat, (x - pad2, y - pad2))
    kanvas.alpha_composite(jendela, (x, y))


def tengah_teks(d: ImageDraw.ImageDraw, teks: str, f, y: int,
                warna, lebar_kanvas: int):
    """Tulis teks di tengah horizontal pada posisi y."""
    kotak = d.textbbox((0, 0), teks, font=f)
    d.text(((lebar_kanvas - (kotak[2] - kotak[0])) / 2 - kotak[0], y),
           teks, font=f, fill=warna)


def main() -> int:
    if not (MASUK / JENDELA_UTAMA[0]).exists():
        print("Tangkapan layar belum ada. Jalankan tools/capture_promosi.py.")
        return 1

    W, H = LEBAR * SKALA, TINGGI * SKALA
    kanvas = gradien((W, H), WARNA_LATAR).convert("RGBA")
    kanvas.alpha_composite(cahaya((W, H)))

    # jendela belakang lebih dulu supaya tertimpa jendela depan
    for berkas, judul, lebar, derajat, tengah in JENDELA:
        jalur = MASUK / berkas
        if not jalur.exists():
            continue
        tempel(kanvas, buat_jendela(jalur, judul, lebar * SKALA, derajat),
               tengah, SKALA)

    berkas, judul, lebar, tengah = JENDELA_UTAMA
    tempel(kanvas, buat_jendela(MASUK / berkas, judul, lebar * SKALA, 0.0),
           tengah, SKALA, kuat=True)

    d = ImageDraw.Draw(kanvas)
    tengah_teks(d, "AkunTuntas", font(int(52 * SKALA), tebal=True),
                int(34 * SKALA), WARNA_JUDUL, W)
    tengah_teks(d, "Pembukuan & Pajak Perusahaan Indonesia",
                font(int(21 * SKALA)), int(112 * SKALA), WARNA_SUB, W)

    # label fitur di bagian bawah
    # Pil dibuat putih solid dengan teks hijau tua dan ikon centang: teks
    # hijau muda di atas latar tembus pandang sebelumnya sulit dibaca karena
    # berbaur dengan garis tepi yang sewarna.
    f_label = font(int(23 * SKALA), tebal=True)
    pad_x, pad_y = int(24 * SKALA), int(13 * SKALA)
    jarak = int(22 * SKALA)
    ukuran = []
    for teks in LABEL_FITUR:
        k = d.textbbox((0, 0), teks, font=f_label)
        ukuran.append((teks, k[2] - k[0], k[3] - k[1]))

    # Semua label dibuat sama tinggi dan berjarak sama agar sejajar rapi.
    tinggi_label = max(h for _, _, h in ukuran) + pad_y * 2
    lebar_centang = int(26 * SKALA)
    lebar_label = [w + pad_x * 2 + lebar_centang + int(8 * SKALA)
                   for _, w, _ in ukuran]
    lebar_total = sum(lebar_label) + jarak * (len(ukuran) - 1)

    x = (W - lebar_total) / 2
    y = H - int(124 * SKALA)
    r_centang = int(9 * SKALA)
    for (teks, w_teks, h_teks), lebar_kotak in zip(ukuran, lebar_label):
        d.rounded_rectangle(
            [x, y, x + lebar_kotak, y + tinggi_label],
            radius=int(tinggi_label / 2), fill=(255, 255, 255, 255))

        # ikon centang hijau tua di sisi kiri pil
        cx = x + pad_x + r_centang
        cy = y + tinggi_label / 2
        d.ellipse([cx - r_centang, cy - r_centang,
                   cx + r_centang, cy + r_centang], fill=(4, 120, 87, 255))
        t = r_centang * 0.52
        d.line([(cx - t, cy + t * 0.05), (cx - t * 0.2, cy + t),
                (cx + t, cy - t * 0.75)],
               fill=(255, 255, 255, 255), width=max(2, int(2.4 * SKALA)),
               joint="curve")

        d.text((x + pad_x + lebar_centang + int(8 * SKALA),
                y + (tinggi_label - h_teks) / 2 - h_teks * 0.06),
               teks, font=f_label, fill=(6, 95, 70, 255))
        x += lebar_kotak + jarak

    tengah_teks(d, "Data tersimpan di komputer Anda — bekerja tanpa internet",
                font(int(19 * SKALA)), H - int(52 * SKALA),
                (186, 208, 232), W)

    kanvas = kanvas.convert("RGB").resize((LEBAR, TINGGI), Image.LANCZOS)
    kanvas.save(KELUAR, quality=95)
    print(f"Gambar promosi tersimpan: {KELUAR}")
    print(f"Ukuran: {kanvas.width} x {kanvas.height}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
