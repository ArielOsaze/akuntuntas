"""
Periksa kesiapan mesin pencari untuk seluruh ekosistem Xinet.

Ekosistem Xinet terdiri dari satu situs induk dan beberapa situs produk.
Setiap situs harus memenuhi syarat dasar agar dapat ditemukan Google:
judul dan deskripsi yang memuat istilah yang dicari, alamat tetap yang
benar, data terstruktur yang sah, serta berkas arahan robots dan sitemap.

Alat ini memeriksa situs yang sedang berjalan, bukan berkas di komputer,
supaya yang dinilai adalah keadaan yang benar benar dilihat mesin pencari.

Pemakaian:
    python tools/periksa_seo_xinet.py
    python tools/periksa_seo_xinet.py akuntuntas
"""
from __future__ import annotations

import html
import json
import re
import sys
import urllib.error
import urllib.request

# Situs yang diperiksa: induk lebih dahulu, lalu tiap produk.
SITUS = [
    ("xinet.id (induk)", "https://xinet.id", ["/"]),
    ("AkunTuntas", "https://akuntuntas.xinet.id",
     ["/", "/unduh", "/beli", "/kontak", "/privasi"]),
    ("LumaWall", "https://lumawall.xinet.id", ["/", "/en/"]),
    ("NexShop", "https://nexshop.cloud", ["/"]),
    ("SayBot", "https://saybot.nexshop.cloud", ["/"]),
]

# Panjang judul dan deskripsi yang diterima mesin pencari.
JUDUL_MIN, JUDUL_MAKS = 15, 65
DESC_MIN, DESC_MAKS = 70, 165

PENGGUNA = "Mozilla/5.0 (kompatibel; pemeriksa SEO)"


def ambil(url: str, batas: int = 45) -> tuple[str, int]:
    """Ambil isi satu alamat. Kembalikan (isi, kode HTTP)."""
    req = urllib.request.Request(url, headers={"User-Agent": PENGGUNA})
    try:
        with urllib.request.urlopen(req, timeout=batas) as r:
            return r.read().decode("utf-8", "replace"), r.status
    except urllib.error.HTTPError as e:
        return "", e.code
    except Exception:
        return "", 0


def cari(teks: str, pola: str) -> str:
    """Ambil isi grup pertama, dengan entitas HTML dikembalikan.

    Entitas seperti &amp; dan &#x27; dihitung sebagai satu huruf, bukan
    sebagai rangkaian huruf, supaya panjang judul yang diukur sama dengan
    yang dibaca mesin pencari.
    """
    m = re.search(pola, teks, re.DOTALL | re.IGNORECASE)
    return html.unescape(m.group(1).strip()) if m else ""


def jenis_schema(teks: str) -> list[str]:
    """Kumpulkan jenis data terstruktur yang dipasang halaman."""
    jenis: list[str] = []
    for blok in re.findall(
            r'<script type="application/ld\+json">(.*?)</script>', teks, re.DOTALL):
        try:
            data = json.loads(blok)
        except Exception:
            jenis.append("RUSAK")
            continue
        if "@graph" in data:
            jenis += [g.get("@type", "?") for g in data["@graph"]]
        else:
            jenis.append(data.get("@type", "?"))
    return jenis


def periksa_alamat(alamat: str, catat) -> None:
    """Periksa satu alamat halaman."""
    isi, kode = ambil(alamat)
    if kode != 200 or not isi:
        catat(f"{alamat} dapat dibuka", False, f"HTTP {kode}")
        return
    catat(f"{alamat} dapat dibuka", True)

    judul = cari(isi, r"<title>(.*?)</title>")
    desk = cari(isi, r'<meta\s+name="description"\s+content="(.*?)"')
    canon = cari(isi, r'<link\s+rel="canonical"\s+href="(.*?)"')
    og = cari(isi, r'<meta\s+property="og:image"\s+content="(.*?)"')
    noindex = "noindex" in isi.lower()
    schema = jenis_schema(isi)
    h1 = len(re.findall(r"<h1[\s>]", isi))

    catat(f"{alamat} punya judul", bool(judul))
    catat(f"{alamat} panjang judul wajar",
          JUDUL_MIN <= len(judul) <= JUDUL_MAKS, f"{len(judul)} huruf")
    catat(f"{alamat} punya deskripsi", bool(desk))
    catat(f"{alamat} panjang deskripsi wajar",
          DESC_MIN <= len(desk) <= DESC_MAKS, f"{len(desk)} huruf")
    catat(f"{alamat} punya alamat tetap", bool(canon))
    catat(f"{alamat} punya gambar pratinjau", bool(og))
    catat(f"{alamat} boleh didata", not noindex, "bertanda noindex")
    catat(f"{alamat} punya data terstruktur", bool(schema),
          "tidak ada JSON-LD")
    catat(f"{alamat} tidak punya JSON-LD rusak", "RUSAK" not in schema)
    catat(f"{alamat} punya tepat satu judul utama", h1 == 1, f"h1={h1}")

    # Judul berbahasa Inggris pada halaman berbahasa Indonesia membuat
    # calon pengunjung Indonesia melewatinya di hasil pencarian. Halaman
    # yang memang disediakan dalam bahasa Inggris (alamatnya berisi /en/)
    # dikecualikan, karena di sana judul Inggris memang benar.
    if "/en/" not in alamat:
        kata_inggris = ("build what", "without friction", "every customer",
                        "bookkeeping you", "live wallpaper for")
        catat(f"{alamat} judul memakai bahasa Indonesia",
              not any(k in judul.lower() for k in kata_inggris),
              f"judulnya {judul[:50]!r}")

    return None


def main() -> int:
    pilih = sys.argv[1].lower() if len(sys.argv) > 1 else ""

    benar = 0
    salah = 0
    temuan: list[str] = []

    def catat(nama: str, syarat: bool, keterangan: str = "") -> None:
        nonlocal benar, salah
        if syarat:
            benar += 1
        else:
            salah += 1
            temuan.append(f"{nama}: {keterangan}" if keterangan else nama)

    print("=" * 78)
    print("  KESIAPAN MESIN PENCARI - EKOSISTEM XINET")
    print("=" * 78)

    for label, akar, jalur in SITUS:
        if pilih and pilih not in label.lower():
            continue

        print(f"\n  ============ {label} ============")
        print(f"  {akar}")

        # Berkas arahan
        for berkas in ("robots.txt", "sitemap.xml"):
            isi, kode = ambil(f"{akar}/{berkas}", batas=30)
            ada = kode == 200 and len(isi) > 20
            catat(f"{label} {berkas} ada", ada, f"HTTP {kode}")
            print(f"    {'ADA   ' if ada else 'HILANG'} {berkas}")

        # Isi sitemap: berapa alamat dan apakah halamannya hidup
        isi_sitemap, kode = ambil(f"{akar}/sitemap.xml", batas=30)
        alamat_sitemap = re.findall(r"<loc>([^<]+)</loc>", isi_sitemap)
        catat(f"{label} sitemap memuat alamat", bool(alamat_sitemap))
        print(f"    sitemap: {len(alamat_sitemap)} alamat")

        # robots harus menunjuk sitemap
        isi_robot, _ = ambil(f"{akar}/robots.txt", batas=30)
        catat(f"{label} robots menunjuk sitemap",
              "sitemap" in isi_robot.lower())

        # Periksa halaman utama tiap situs
        for halaman in jalur:
            periksa_alamat(f"{akar}{halaman}", catat)

        # Judul tiap halaman, ditampilkan supaya mudah dibaca manusia
        for halaman in jalur:
            isi, kode = ambil(f"{akar}{halaman}", batas=30)
            if kode == 200:
                j = cari(isi, r"<title>(.*?)</title>")
                d = cari(isi, r'<meta\s+name="description"\s+content="(.*?)"')
                s = jenis_schema(isi)
                print(f"\n    {halaman}")
                print(f"      judul ({len(j)}): {j[:66]}")
                print(f"      desc  ({len(d)}): {d[:66]}...")
                print(f"      schema: {s}")

    print()
    print("=" * 78)
    if salah:
        print(f"  HASIL: {benar} BENAR, {salah} PERLU DIPERBAIKI")
        print()
        for t in temuan:
            print(f"    - {t}")
    else:
        print(f"  HASIL: {benar} BENAR, 0 PERLU DIPERBAIKI")
        print("  Seluruh ekosistem siap didata mesin pencari.")
    print("=" * 78)
    return 1 if salah else 0


if __name__ == "__main__":
    sys.exit(main())
