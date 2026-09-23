"""Buat dua gambar iklan dari tangkapan layar: ukuran 16:9 dan 19:6.

Cara pakai:
    python tools/buat_promo_iklan.py

Masukan  : folder _promosi/ berisi tangkapan layar halaman
Keluaran : _promosi/iklan_16_9.png  (2400 x 1350)
           _promosi/iklan_19_6.png  (2400 x 758)

Jendela dimiringkan dengan transformasi perspektif supaya terlihat seperti
foto produk sungguhan, bukan gambar tempel datar. Jendela utama diberi
pantulan tipis di bawahnya agar terkesan melayang.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

AKAR = Path(__file__).resolve().parent.parent
MASUK = AKAR / "_promosi"

WARNA_LATAR = [(10, 27, 50), (24, 71, 126), (8, 21, 40)]
WARNA_JUDUL = (255, 255, 255)
WARNA_SUB = (198, 219, 242)
WARNA_KET = (186, 208, 232)
WARNA_TEKS_PIL = (6, 95, 70)
WARNA_CENTANG = (4, 120, 87)

MERAH = (255, 95, 87)
KUNING = (254, 188, 46)
HIJAU = (40, 200, 64)

LABEL_FITUR = [
    "PPN & PPh 21 (TER)",
    "PPh Badan Pasal 31E",
    "Neraca Otomatis",
    "Faktur Pajak & NSFP",
    "Uang Muka & Bea Meterai",
]


# --------------------------------------------------------------------------
# alat hitung
# --------------------------------------------------------------------------
def selesaikan(matriks, nilai):
    """Selesaikan sistem linear dengan eliminasi Gauss-Jordan."""
    n = len(matriks)
    a = [list(matriks[i]) + [nilai[i]] for i in range(n)]
    for i in range(n):
        p = max(range(i, n), key=lambda r: abs(a[r][i]))
        if abs(a[p][i]) < 1e-12:
            continue
        a[i], a[p] = a[p], a[i]
        bagi = a[i][i]
        for c in range(i, n + 1):
            a[i][c] /= bagi
        for r in range(n):
            if r == i:
                continue
            f = a[r][i]
            if f == 0:
                continue
            for c in range(i, n + 1):
                a[r][c] -= f * a[i][c]
    return [a[i][n] for i in range(n)]


def putar_titik(titik, derajat, pusat):
    """Putar satu titik mengelilingi pusat."""
    import math
    r = math.radians(derajat)
    cos, sin = math.cos(r), math.sin(r)
    x, y = titik[0] - pusat[0], titik[1] - pusat[1]
    return (pusat[0] + x * cos - y * sin, pusat[1] + x * sin + y * cos)


def quad_jendela(lebar: int, tinggi: int, toleh: float,
                 putar: float) -> list:
    """
    Empat sudut tujuan untuk efek jendela dimiringkan.

    toleh > 0 : sisi kanan menjauh, jendela seperti menoleh ke kiri
    toleh < 0 : sisi kiri menjauh
    putar     : derajat putaran seluruh jendela
    """
    susut = abs(toleh) * 0.20
    dalam = abs(toleh) * lebar * 0.26

    if toleh >= 0:
        quad = [(0.0, 0.0),
                (lebar - dalam, tinggi * susut * 0.5),
                (lebar - dalam, tinggi - tinggi * susut * 0.5),
                (0.0, float(tinggi))]
    else:
        quad = [(dalam, tinggi * susut * 0.5),
                (float(lebar), 0.0),
                (float(lebar), float(tinggi)),
                (dalam, tinggi - tinggi * susut * 0.5)]

    if abs(putar) > 0.01:
        pusat = (lebar / 2, tinggi / 2)
        quad = [putar_titik(p, putar, pusat) for p in quad]
    return quad


def perspektif(gambar: Image.Image, quad: list):
    """
    Petakan gambar ke segi empat tujuan (memberi kesan tiga dimensi).

    Mengembalikan gambar hasil beserta titik kiri-atasnya pada kanvas.
    """
    w, h = gambar.size
    xs = [p[0] for p in quad]
    ys = [p[1] for p in quad]
    minx, miny = min(xs), min(ys)
    lebar = int(round(max(xs) - minx)) + 2
    tinggi = int(round(max(ys) - miny)) + 2
    tujuan = [(x - minx, y - miny) for x, y in quad]
    asal = [(0, 0), (w - 1, 0), (w - 1, h - 1), (0, h - 1)]

    baris, kolom = [], []
    for (x, y), (u, v) in zip(asal, tujuan):
        baris.append([u, v, 1, 0, 0, 0, -x * u, -x * v])
        kolom.append(x)
        baris.append([0, 0, 0, u, v, 1, -y * u, -y * v])
        kolom.append(y)
    k = selesaikan(baris, kolom)

    hasil = gambar.transform((lebar, tinggi), Image.PERSPECTIVE, k,
                             Image.BICUBIC, fillcolor=(0, 0, 0, 0))
    return hasil, (minx, miny)


# --------------------------------------------------------------------------
# gambar dasar
# --------------------------------------------------------------------------
def font(ukuran: int, tebal: bool = False) -> ImageFont.FreeTypeFont:
    nama = "segoeuib.ttf" if tebal else "segoeui.ttf"
    for folder in (r"C:\Windows\Fonts", "/usr/share/fonts/truetype"):
        jalur = Path(folder) / nama
        if jalur.exists():
            return ImageFont.truetype(str(jalur), ukuran)
    return ImageFont.load_default()


def gradien(ukuran: tuple) -> Image.Image:
    lebar, tinggi = ukuran
    kolom = Image.new("RGB", (1, tinggi))
    piksel = kolom.load()
    for y in range(tinggi):
        t = y / max(1, tinggi - 1)
        if t < 0.5:
            u, a, b = t / 0.5, WARNA_LATAR[0], WARNA_LATAR[1]
        else:
            u, a, b = (t - 0.5) / 0.5, WARNA_LATAR[1], WARNA_LATAR[2]
        piksel[0, y] = tuple(int(a[i] + (b[i] - a[i]) * u) for i in range(3))
    return kolom.resize((lebar, tinggi))


def cahaya(ukuran: tuple, pusat_x: float = 0.55) -> Image.Image:
    lapis = Image.new("RGBA", ukuran, (0, 0, 0, 0))
    d = ImageDraw.Draw(lapis)
    lebar, tinggi = ukuran
    d.ellipse([lebar * (pusat_x - 0.42), -tinggi * 0.45,
               lebar * (pusat_x + 0.42), tinggi * 0.62],
              fill=(56, 124, 196, 130))
    d.ellipse([-lebar * 0.30, tinggi * 0.45, lebar * 0.42, tinggi * 1.35],
              fill=(27, 79, 138, 100))
    return lapis.filter(ImageFilter.GaussianBlur(150))


def sudut_membulat(gambar: Image.Image, radius: int) -> Image.Image:
    gambar = gambar.convert("RGBA")
    topeng = Image.new("L", gambar.size, 0)
    ImageDraw.Draw(topeng).rounded_rectangle(
        [0, 0, gambar.width - 1, gambar.height - 1], radius=radius, fill=255)
    gambar.putalpha(topeng)
    return gambar


def bayangan(gambar: Image.Image, blur: int, geser: tuple,
             kegelapan: int) -> Image.Image:
    pad = int(blur * 2.2)
    kanvas = Image.new("RGBA", (gambar.width + pad * 2,
                                gambar.height + pad * 2), (0, 0, 0, 0))
    hitam = Image.new("RGBA", gambar.size, (0, 0, 0, kegelapan))
    kanvas.paste(hitam, (pad + geser[0], pad + geser[1]), gambar.split()[3])
    return kanvas.filter(ImageFilter.GaussianBlur(blur))


def pantulan(gambar: Image.Image, tinggi_pantulan: float = 0.22) -> Image.Image:
    """Pantulan tipis di bawah jendela supaya terkesan melayang."""
    potong = int(gambar.height * tinggi_pantulan)
    balik = gambar.crop((0, gambar.height - potong, gambar.width,
                         gambar.height)).transpose(Image.FLIP_TOP_BOTTOM)
    topeng = Image.new("L", balik.size, 0)
    d = ImageDraw.Draw(topeng)
    for y in range(balik.height):
        t = 1 - y / max(1, balik.height - 1)
        d.line([(0, y), (balik.width, y)], fill=int(70 * t * t))
    balik.putalpha(topeng)
    return balik


def bilah_judul(lebar: int, tinggi: int, teks: str) -> Image.Image:
    bilah = Image.new("RGBA", (lebar, tinggi), (238, 240, 244, 255))
    d = ImageDraw.Draw(bilah)
    d.rectangle([0, tinggi - 1, lebar, tinggi], fill=(202, 207, 215, 255))
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


def jendela(berkas: Path, judul: str, lebar: int,
            toleh: float = 0.0, putar: float = 0.0):
    """Bentuk jendela macOS lalu miringkan dengan perspektif."""
    isi = Image.open(berkas).convert("RGB")
    isi = isi.resize((lebar, int(lebar * isi.height / isi.width)),
                     Image.LANCZOS)
    tinggi_bilah = max(32, int(lebar * 0.026))
    wadah = Image.new("RGBA", (lebar, isi.height + tinggi_bilah),
                      (255, 255, 255, 255))
    wadah.paste(bilah_judul(lebar, tinggi_bilah, judul), (0, 0))
    wadah.paste(isi, (0, tinggi_bilah))
    wadah = sudut_membulat(wadah, int(lebar * 0.014))
    quad = quad_jendela(wadah.width, wadah.height, toleh, putar)
    return perspektif(wadah, quad)


def tempel(kanvas: Image.Image, gambar: Image.Image, posisi: tuple,
           blur: int, geser: tuple, gelap: int, pantul: bool = False):
    """Tempel jendela beserta bayangan (dan pantulan bila diminta)."""
    x, y = int(posisi[0]), int(posisi[1])
    pad = int(blur * 2.2)
    kanvas.alpha_composite(bayangan(gambar, blur, geser, gelap),
                           (x - pad, y - pad))
    if pantul:
        kanvas.alpha_composite(pantulan(gambar), (x, y + gambar.height))
    kanvas.alpha_composite(gambar, (x, y))


def tengah_teks(d, teks, f, y, warna, lebar):
    kotak = d.textbbox((0, 0), teks, font=f)
    d.text(((lebar - (kotak[2] - kotak[0])) / 2 - kotak[0], y),
           teks, font=f, fill=warna)


def pil_fitur(d: ImageDraw.ImageDraw, label: list, x_awal: float, y: float,
              skala: int, ukuran_font: int = 23, susun_vertikal: bool = False,
              x_pusat: float = None):
    """
    Gambar pil fitur: putih solid, teks hijau tua, ikon centang.

    Teks diletakkan memakai titik acuan tengah-kiri (anchor="lm") supaya
    benar-benar sebaris dengan titik tengah pil. Menghitung sendiri dari
    textbbox() membuat teks meleset karena kotak huruf punya ruang kosong
    di atas dan bawah yang tidak sama.
    """
    f = font(int(ukuran_font * skala), tebal=True)
    pad_x, pad_y = int(24 * skala), int(14 * skala)
    jarak = int(20 * skala)
    r = int(10 * skala)
    lebar_ikon = int(30 * skala)

    ukuran = []
    for teks in label:
        k = d.textbbox((0, 0), teks, font=f, anchor="ls")
        ukuran.append((teks, k[2] - k[0]))

    # tinggi pil dari tinggi baris font, bukan dari tinta huruf, supaya
    # semua pil sama tinggi dan teks selalu di tengah
    tinggi_baris = f.getbbox("Ag")[3] - f.getbbox("Ag")[1]
    tinggi_pil = tinggi_baris + pad_y * 2

    lebar_sama = max(w for _, w in ukuran) + pad_x * 2 + lebar_ikon

    def gambar_pil(teks, w_teks, x, y):
        d.rounded_rectangle([x, y, x + lebar_sama, y + tinggi_pil],
                            radius=int(tinggi_pil / 2),
                            fill=(255, 255, 255, 255))
        tengah_y = y + tinggi_pil / 2
        # ikon centang
        cx = x + pad_x + r
        d.ellipse([cx - r, tengah_y - r, cx + r, tengah_y + r],
                  fill=WARNA_CENTANG)
        t = r * 0.52
        d.line([(cx - t, tengah_y + t * 0.05), (cx - t * 0.2, tengah_y + t),
                (cx + t, tengah_y - t * 0.75)], fill=(255, 255, 255, 255),
               width=max(2, int(2.3 * skala)), joint="curve")
        # teks: titik acuan tengah-kiri, jadi pasti di tengah tinggi pil
        d.text((x + pad_x + lebar_ikon, tengah_y), teks, font=f,
               fill=WARNA_TEKS_PIL, anchor="lm")

    if susun_vertikal:
        y_now = y
        for teks, w_teks in ukuran:
            x = x_pusat - lebar_sama / 2 if x_pusat else x_awal
            gambar_pil(teks, w_teks, x, y_now)
            y_now += tinggi_pil + int(12 * skala)
        return y_now

    lebar_total = lebar_sama * len(ukuran) + jarak * (len(ukuran) - 1)
    x = x_pusat - lebar_total / 2 if x_pusat else x_awal
    for teks, w_teks in ukuran:
        gambar_pil(teks, w_teks, x, y)
        x += lebar_sama + jarak
    return y + tinggi_pil


# --------------------------------------------------------------------------
# susunan 16:9
# --------------------------------------------------------------------------
def susun_16_9() -> Image.Image:
    """
    Susunan 16:9 gaya iklan produk (horizontal).

    Jendela utama besar di depan sebagai fokus, empat jendela pendukung
    mengintip dari belakang pada sisi kiri dan kanan. Tata letak dihitung
    dari bawah ke atas supaya pil fitur dan tagline selalu muat penuh.
    """
    LEBAR, TINGGI, S = 2400, 1350, 2
    W, H = LEBAR * S, TINGGI * S
    kanvas = gradien((W, H)).convert("RGBA")
    kanvas.alpha_composite(cahaya((W, H), 0.50))

    # tata letak dari bawah ke atas
    f_pil = font(int(23 * S), tebal=True)
    tinggi_pil = (f_pil.getbbox("Ag")[3] - f_pil.getbbox("Ag")[1])         + int(14 * S) * 2
    y_tagline = H - int(46 * S)
    y_pil = y_tagline - int(52 * S) - tinggi_pil
    y_hero = int(660 * S)
    y_judul = int(46 * S)
    y_sub = int(140 * S)

    # jendela belakang: makin jauh dari tengah, makin kecil dan makin miring
    belakang = [
        ("laporan.png", "Laporan Keuangan", 880, -0.16, -4.5,
         (int(600 * S), y_hero - int(60 * S))),
        ("penjualan.png", "Penjualan", 920, -0.08, -2.0,
         (int(740 * S), y_hero + int(190 * S))),
        ("pajak_lanjutan.png", "Pajak Lanjutan", 880, 0.16, 4.5,
         (W - int(600 * S), y_hero - int(60 * S))),
        ("pajak.png", "Pajak & SPT", 920, 0.08, 2.0,
         (W - int(740 * S), y_hero + int(190 * S))),
    ]
    for berkas, judul, lebar, toleh, putar, (cx, cy) in belakang:
        jalur = MASUK / berkas
        if not jalur.exists():
            continue
        g, _ = jendela(jalur, judul, lebar * S, toleh, putar)
        tempel(kanvas, g, (cx - g.width / 2, cy - g.height / 2),
               int(30 * S), (0, int(13 * S)), 120)

    # jendela utama: paling depan, tegak, menjadi pusat perhatian
    utama, _ = jendela(MASUK / "dashboard.png", "Dashboard — AkunTuntas",
                       1210 * S, 0.0, 0.0)
    tempel(kanvas, utama, ((W - utama.width) / 2, y_hero - utama.height / 2),
           int(64 * S), (0, int(26 * S)), 140, pantul=True)

    d = ImageDraw.Draw(kanvas)
    tengah_teks(d, "AkunTuntas", font(int(62 * S), tebal=True),
                y_judul, WARNA_JUDUL, W)
    tengah_teks(d, "Pembukuan & Pajak Perusahaan Indonesia",
                font(int(25 * S)), y_sub, WARNA_SUB, W)
    pil_fitur(d, LABEL_FITUR, 0, y_pil, S, ukuran_font=23, x_pusat=W / 2)
    tengah_teks(d, "Data tersimpan di komputer Anda — bekerja tanpa internet",
                font(int(20 * S)), y_tagline, WARNA_KET, W)

    return kanvas.convert("RGB").resize((LEBAR, TINGGI), Image.LANCZOS)


# --------------------------------------------------------------------------
# susunan 19:6 (banner lebar)
# --------------------------------------------------------------------------
def susun_19_6() -> Image.Image:
    """
    Banner lebar 19:6: merek di kiri, jendela utama di kanan sebagai fokus,
    dua jendela lain mengintip dari belakang.
    """
    LEBAR, TINGGI, S = 2400, 758, 2
    W, H = LEBAR * S, TINGGI * S
    kanvas = gradien((W, H)).convert("RGBA")
    kanvas.alpha_composite(cahaya((W, H), 0.74))

    belakang = [
        ("laporan.png", "Laporan Keuangan", 700, -0.14, -4.0, (1560, 380)),
        ("pajak_lanjutan.png", "Pajak Lanjutan", 700, 0.14, 4.0, (2260, 380)),
    ]
    for berkas, judul, lebar, toleh, putar, (cx, cy) in belakang:
        jalur = MASUK / berkas
        if not jalur.exists():
            continue
        g, _ = jendela(jalur, judul, lebar * S, toleh, putar)
        tempel(kanvas, g, (cx * S - g.width / 2, cy * S - g.height / 2),
               int(26 * S), (0, int(11 * S)), 120)

    utama, _ = jendela(MASUK / "dashboard.png", "Dashboard — AkunTuntas",
                       900 * S, 0.0, 0.0)
    tempel(kanvas, utama, (int(1930 * S - utama.width / 2),
                           int(380 * S - utama.height / 2)),
           int(44 * S), (0, int(18 * S)), 140)

    d = ImageDraw.Draw(kanvas)
    kiri = int(105 * S)
    d.text((kiri, int(74 * S)), "AkunTuntas", font=font(int(60 * S), True),
           fill=WARNA_JUDUL)
    d.text((kiri, int(170 * S)), "Pembukuan & Pajak Perusahaan Indonesia",
           font=font(int(25 * S)), fill=WARNA_SUB)
    pil_fitur(d, LABEL_FITUR[:4], kiri, int(236 * S), S, ukuran_font=20,
              susun_vertikal=True, x_pusat=kiri + int(205 * S))
    d.text((kiri, H - int(50 * S)),
           "Data tersimpan di komputer Anda — bekerja tanpa internet",
           font=font(int(18 * S)), fill=WARNA_KET)

    return kanvas.convert("RGB").resize((LEBAR, TINGGI), Image.LANCZOS)


def susun_9_16() -> Image.Image:
    """
    Susunan vertikal 9:16 untuk Instagram Story.

    Lima jendela ditata agar bidang tidak terasa kosong: jendela utama besar
    di tengah, dua jendela mengintip di sisi atas, dan dua lagi di sisi bawah.
    Tata letak dihitung dari bawah ke atas supaya semua bagian pasti muat.
    """
    LEBAR, TINGGI, S = 1080, 1920, 2
    W, H = LEBAR * S, TINGGI * S
    kanvas = gradien((W, H)).convert("RGBA")
    kanvas.alpha_composite(cahaya((W, H), 0.50))

    # tata letak dari bawah ke atas
    f_pil = font(int(30 * S), tebal=True)
    tinggi_pil = (f_pil.getbbox("Ag")[3] - f_pil.getbbox("Ag")[1])         + int(14 * S) * 2
    jarak_pil = int(12 * S)

    y_tagline = H - int(84 * S)
    y_pil = y_tagline - int(64 * S) - (tinggi_pil * 5 + jarak_pil * 4)
    y_judul = int(112 * S)
    y_sub = int(228 * S)
    y_hero = int(790 * S)
    y_sisi_atas = y_hero - int(190 * S)
    y_sisi_bawah = y_hero + int(215 * S)

    # empat jendela pendukung: dua di atas, dua di bawah
    pendukung = [
        ("laporan.png", "Laporan Keuangan", 430, -0.16, -5.0,
         (int(300 * S), y_sisi_atas)),
        ("pajak.png", "Pajak & SPT", 430, 0.16, 5.0,
         (W - int(300 * S), y_sisi_atas)),
        ("penjualan.png", "Penjualan", 460, -0.09, -2.5,
         (int(360 * S), y_sisi_bawah)),
        ("pajak_lanjutan.png", "Pajak Lanjutan", 460, 0.09, 2.5,
         (W - int(360 * S), y_sisi_bawah)),
    ]
    for berkas, judul, lebar, toleh, putar, (cx, cy) in pendukung:
        jalur = MASUK / berkas
        if not jalur.exists():
            continue
        g, _ = jendela(jalur, judul, lebar * S, toleh, putar)
        tempel(kanvas, g, (cx - g.width / 2, cy - g.height / 2),
               int(28 * S), (0, int(12 * S)), 122)

    # jendela utama: pusat perhatian, tegak, muat penuh
    utama, _ = jendela(MASUK / "dashboard.png", "Dashboard — AkunTuntas",
                       1000 * S, 0.0, 0.0)
    tempel(kanvas, utama, ((W - utama.width) / 2, y_hero - utama.height / 2),
           int(58 * S), (0, int(23 * S)), 140, pantul=True)

    d = ImageDraw.Draw(kanvas)
    tengah_teks(d, "AkunTuntas", font(int(78 * S), tebal=True),
                y_judul, WARNA_JUDUL, W)
    tengah_teks(d, "Pembukuan & Pajak Perusahaan Indonesia",
                font(int(30 * S)), y_sub, WARNA_SUB, W)

    pil_fitur(d, LABEL_FITUR, 0, y_pil, S, ukuran_font=30,
              susun_vertikal=True, x_pusat=W / 2)

    tengah_teks(d, "Data tersimpan di komputer Anda — bekerja tanpa internet",
                font(int(24 * S)), y_tagline, WARNA_KET, W)

    return kanvas.convert("RGB").resize((LEBAR, TINGGI), Image.LANCZOS)


def main() -> int:
    if not (MASUK / "dashboard.png").exists():
        print("Tangkapan layar belum ada. Jalankan tools/capture_promosi.py.")
        return 1

    for nama, fungsi in (("iklan_16_9.png", susun_16_9),
                         ("iklan_9_16.png", susun_9_16)):
        gambar = fungsi()
        tujuan = MASUK / nama
        gambar.save(tujuan, quality=95)
        print(f"{nama:16s} {gambar.width} x {gambar.height}  ->  {tujuan}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
