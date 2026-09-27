"""
Periksa kesiapan situs untuk mesin pencari.

Memeriksa hal hal yang menentukan apakah Google dapat menemukan,
memahami, dan menampilkan situs dengan baik:

  1. Berkas arahan: robots.txt dan sitemap.xml sah dan sinkron.
  2. Judul dan deskripsi tiap halaman: ada, panjangnya wajar, dan unik.
  3. Alamat tetap (canonical) menunjuk ke alamat yang benar.
  4. Data terstruktur (JSON-LD) sah dan jenisnya sesuai isi halaman.
  5. Halaman yang bergantung sesi ditandai noindex.
  6. Struktur judul (satu h1 per halaman).
  7. Pratinjau tautan: gambar og:image ada dan ukurannya benar.
  8. Kelengkapan berkas yang dirujuk (logo, pratinjau, favicon).

Pemakaian:
    python tools/periksa_seo.py
"""
from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
WEB = AKAR / "web"
ALAMAT = "https://akuntuntas.xinet.id"

# Halaman yang layak muncul di hasil pencarian.
PUBLIK = {
    "index.html": "/",
    "unduh.html": "/unduh",
    "beli.html": "/beli",
    "kontak.html": "/kontak",
    "privasi.html": "/privasi",
}

# Halaman yang isinya bergantung sesi pengunjung dan tidak boleh didata.
TERTUTUP = {
    "admin.html": "halaman admin",
    "kwitansi.html": "kwitansi pesanan",
    "selesai.html": "hasil pembayaran",
    "batal.html": "pembayaran dibatalkan",
}


class Pemeriksa:
    def __init__(self) -> None:
        self.benar = 0
        self.salah = 0
        self.temuan: list[str] = []

    def cek(self, nama: str, syarat: bool, keterangan: str = "") -> None:
        if syarat:
            self.benar += 1
        else:
            self.salah += 1
            self.temuan.append(f"{nama}: {keterangan}" if keterangan else nama)


def ambil(teks: str, pola: str) -> str:
    """Ambil isi grup pertama pola, atau teks kosong."""
    m = re.search(pola, teks, re.DOTALL | re.IGNORECASE)
    return m.group(1).strip() if m else ""


def main() -> int:
    p = Pemeriksa()

    print("=" * 78)
    print("  PERIKSA KESIAPAN SITUS UNTUK MESIN PENCARI")
    print("=" * 78)

    # ---------------------------------------------------------- berkas dasar
    print("\n  --- Berkas arahan ---")
    for nama in ("robots.txt", "sitemap.xml", "404.html"):
        ada = (WEB / nama).exists()
        p.cek(f"berkas {nama} ada", ada)
        print(f"    {'ADA   ' if ada else 'HILANG'} {nama}")

    # robots.txt
    robot = (WEB / "robots.txt").read_text(encoding="utf-8")
    p.cek("robots.txt mengizinkan pendataan", "Allow: /" in robot)
    p.cek("robots.txt menyebut alamat sitemap", "Sitemap:" in robot)
    p.cek("robots.txt melarang halaman admin", "Disallow: /admin" in robot)
    print(f"    robots.txt: {len(robot.splitlines())} baris")

    # sitemap.xml
    try:
        pohon = ET.parse(WEB / "sitemap.xml")
        ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        alamat_sitemap = [u.find("s:loc", ns).text
                          for u in pohon.getroot().findall("s:url", ns)]
        p.cek("sitemap.xml sah dibaca", True)
    except Exception as e:
        p.cek("sitemap.xml sah dibaca", False, str(e))
        alamat_sitemap = []

    print(f"    sitemap: {len(alamat_sitemap)} alamat")

    # Setiap halaman publik harus ada di sitemap
    for jalur in PUBLIK.values():
        lengkap = f"{ALAMAT}{jalur}"
        ada = lengkap in alamat_sitemap
        p.cek(f"sitemap memuat {jalur}", ada)
        print(f"    {'ADA   ' if ada else 'HILANG'} {jalur} di sitemap")

    # Halaman tertutup TIDAK boleh ada di sitemap
    for jalur in TERTUTUP:
        nama_jalur = "/" + jalur.replace(".html", "")
        ada = any(nama_jalur in a for a in alamat_sitemap)
        p.cek(f"sitemap tidak memuat {nama_jalur}", not ada,
              "halaman tertutup sebaiknya tidak didaftarkan")
        if ada:
            print(f"    HARUSNYA TIDAK ADA: {nama_jalur}")

    # ------------------------------------------------- judul dan deskripsi
    print("\n  --- Judul dan deskripsi ---")
    judul_terpakai: dict[str, str] = {}
    desk_terpakai: dict[str, str] = {}

    for nama, jalur in PUBLIK.items():
        berkas = WEB / nama
        if not berkas.exists():
            p.cek(f"{nama} ada", False)
            continue
        s = berkas.read_text(encoding="utf-8", errors="replace")

        judul = ambil(s, r"<title>(.*?)</title>")
        desk = ambil(s, r'<meta\s+name="description"\s+content="(.*?)"')
        canon = ambil(s, r'<link\s+rel="canonical"\s+href="(.*?)"')

        # Judul: ada, panjang wajar, dan tidak kembar dengan halaman lain
        p.cek(f"judul {nama} ada", bool(judul))
        p.cek(f"judul {nama} panjang wajar (15-65)",
             15 <= len(judul) <= 65, f"panjangnya {len(judul)}")
        p.cek(f"judul {nama} belum dipakai halaman lain",
              judul not in judul_terpakai,
              f"sama dengan {judul_terpakai.get(judul, '')}")
        judul_terpakai[judul] = nama

        # Deskripsi: ada, panjang wajar, tidak kembar
        p.cek(f"deskripsi {nama} ada", bool(desk))
        p.cek(f"deskripsi {nama} panjang wajar (70-160)",
             70 <= len(desk) <= 160, f"panjangnya {len(desk)}")
        p.cek(f"deskripsi {nama} belum dipakai halaman lain",
             desk not in desk_terpakai,
             f"sama dengan {desk_terpakai.get(desk, '')}")
        desk_terpakai[desk] = nama

        # Canonical harus menunjuk alamat yang benar
        harus = f"{ALAMAT}{jalur}"
        p.cek(f"canonical {nama} benar", canon == harus,
             f"isinya {canon!r}, seharusnya {harus!r}")

        print(f"    {nama:15} judul={len(judul):2}  desc={len(desk):3}  "
              f"canonical={'OK' if canon == harus else 'SALAH'}")

    # ------------------------------------------------------- data terstruktur
    print("\n  --- Data terstruktur (JSON-LD) ---")
    for nama in PUBLIK:
        berkas = WEB / nama
        if not berkas.exists():
            continue
        s = berkas.read_text(encoding="utf-8", errors="replace")
        jenis = []
        for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>',
                             s, re.DOTALL):
            try:
                data = json.loads(m.group(1))
                jenis.append(data.get("@type", "?"))
                p.cek(f"JSON-LD {nama} sah", True)
            except Exception as e:
                p.cek(f"JSON-LD {nama} sah", False, str(e))
        p.cek(f"JSON-LD {nama} ada", bool(jenis))
        print(f"    {nama:15} {jenis}")

    # Beranda wajib punya FAQPage karena pertanyaannya tampil di halaman
    beranda = (WEB / "index.html").read_text(encoding="utf-8", errors="replace")
    p.cek("beranda punya FAQPage", '"FAQPage"' in beranda)
    p.cek("beranda punya SoftwareApplication",
          '"SoftwareApplication"' in beranda)

    # ------------------------------------------------- halaman tertutup
    print("\n  --- Halaman tertutup (tidak boleh didata) ---")
    for nama, keterangan in TERTUTUP.items():
        berkas = WEB / nama
        if not berkas.exists():
            continue
        s = berkas.read_text(encoding="utf-8", errors="replace")
        noindex = "noindex" in s.lower()
        p.cek(f"{nama} bertanda noindex", noindex, keterangan)
        print(f"    {'OK   ' if noindex else 'HILANG'} {nama:16} {keterangan}")

    # ------------------------------------------------------- struktur judul
    print("\n  --- Struktur judul ---")
    for nama in PUBLIK:
        berkas = WEB / nama
        if not berkas.exists():
            continue
        s = berkas.read_text(encoding="utf-8", errors="replace")
        n_h1 = len(re.findall(r"<h1[\s>]", s))
        p.cek(f"{nama} punya tepat satu h1", n_h1 == 1, f"jumlahnya {n_h1}")
        print(f"    {nama:15} h1={n_h1}")

    # ------------------------------------------------------ pratinjau tautan
    print("\n  --- Pratinjau tautan ---")
    for nama in PUBLIK:
        berkas = WEB / nama
        if not berkas.exists():
            continue
        s = berkas.read_text(encoding="utf-8", errors="replace")
        og = ambil(s, r'<meta\s+property="og:image"\s+content="(.*?)"')
        p.cek(f"og:image {nama} ada", bool(og))
        if og:
            nama_berkas = og.rsplit("/", 1)[-1]
            p.cek(f"berkas og:image {nama_berkas} ada", (WEB / nama_berkas).exists())
        print(f"    {nama:15} og:image={'ADA' if og else 'KOSONG'}")

    # Gambar pratinjau harus berukuran 1200x630
    prat = WEB / "pratinjau.png"
    if prat.exists():
        try:
            from PIL import Image
            ukuran = Image.open(prat).size
            p.cek("ukuran pratinjau 1200x630", ukuran == (1200, 630),
                  f"ukurannya {ukuran}")
            print(f"    pratinjau.png   {ukuran[0]}x{ukuran[1]}")
        except ImportError:
            pass

    # ---------------------------------------------------- berkas yang dirujuk
    print("\n  --- Berkas yang dirujuk ---")
    for nama in ("favicon.ico", "logo.png", "logo-32.png", "logo-128.png",
                 "manifest.json", "pratinjau.png", "styles.css"):
        ada = (WEB / nama).exists()
        p.cek(f"berkas {nama} ada", ada)
        print(f"    {'ADA   ' if ada else 'HILANG'} {nama}")

    # ------------------------------------------------------------------ hasil
    print()
    print("=" * 78)
    if p.salah:
        print(f"  HASIL: {p.benar} BENAR, {p.salah} PERLU DIPERBAIKI")
        print()
        for t in p.temuan:
            print(f"    - {t}")
    else:
        print(f"  HASIL: {p.benar} BENAR, 0 PERLU DIPERBAIKI")
        print("  Situs siap didata mesin pencari.")
    print("=" * 78)
    return 1 if p.salah else 0


if __name__ == "__main__":
    sys.exit(main())
