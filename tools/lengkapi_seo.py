"""
Lengkapi meta SEO pada seluruh halaman situs.

Yang ditambahkan pada setiap halaman:
  - Open Graph lengkap (WhatsApp, Facebook, LinkedIn, Slack)
  - Twitter Card
  - alamat kanonis, supaya isi ganda tidak menurunkan peringkat
  - favicon untuk berbagai perangkat
  - data terstruktur JSON-LD pada halaman utama

Alamat gambar dan halaman ditulis penuh (bukan relatif), karena layanan
pratinjau tautan tidak dapat membaca alamat relatif.

Cara pakai:
    python tools/lengkapi_seo.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
WEB = AKAR / "web"
SITUS = "https://akuntuntas.xinet.id"
PRATINJAU = f"{SITUS}/pratinjau.png"

# Keterangan tiap halaman: judul, ringkasan, dan alamatnya.
HALAMAN = {
    "index.html": {
        "alamat": f"{SITUS}/",
        "judul": "AkunTuntas - Pembukuan & Pajak Perusahaan Indonesia",
        "ringkas": ("Pembukuan lengkap dan perhitungan pajak akurat untuk "
                    "UMKM, PT Perorangan, dan PT. Data tersimpan di komputer "
                    "Anda sendiri."),
    },
    "unduh.html": {
        "alamat": f"{SITUS}/unduh",
        "judul": "Unduh AkunTuntas - Pembukuan & Pajak Perusahaan",
        "ringkas": ("Unduh aplikasi pembukuan AkunTuntas untuk Windows. "
                    "Periksa kunci lisensi Anda, lalu pasang aplikasinya."),
    },
    "beli.html": {
        "alamat": f"{SITUS}/beli",
        "judul": "Beli Lisensi AkunTuntas",
        "ringkas": ("Beli lisensi AkunTuntas seumur hidup. Paket Standar "
                    "untuk satu perangkat, paket Enterprise untuk sepuluh "
                    "perangkat dengan fitur lengkap."),
    },
    "privasi.html": {
        "alamat": f"{SITUS}/privasi",
        "judul": "Kebijakan Privasi - AkunTuntas",
        "ringkas": ("Kebijakan privasi AkunTuntas: data pembukuan tersimpan "
                    "di komputer Anda dan tidak dikirim ke mana pun."),
    },
}

# Halaman yang tidak perlu didata mesin pencari.
TANPA_INDEKS = ("selesai.html", "batal.html", "admin.html", "kwitansi.html")

FAVICON = """<link rel="icon" href="logo-32.png" type="image/png">
<link rel="apple-touch-icon" href="logo-128.png">
<link rel="manifest" href="manifest.json">"""


def blok_og(info: dict, noindex: bool = False) -> str:
    """Susun blok meta Open Graph dan Twitter Card."""
    baris = [
        '<meta property="og:type" content="website">',
        '<meta property="og:site_name" content="AkunTuntas">',
        f'<meta property="og:title" content="{info["judul"]}">',
        f'<meta property="og:description" content="{info["ringkas"]}">',
        f'<meta property="og:image" content="{PRATINJAU}">',
        '<meta property="og:image:width" content="1200">',
        '<meta property="og:image:height" content="630">',
        '<meta property="og:image:alt" '
        'content="AkunTuntas - Pembukuan dan Pajak Perusahaan Indonesia">',
        f'<meta property="og:url" content="{info["alamat"]}">',
        '<meta property="og:locale" content="id_ID">',
        "",
        '<meta name="twitter:card" content="summary_large_image">',
        f'<meta name="twitter:title" content="{info["judul"]}">',
        f'<meta name="twitter:description" content="{info["ringkas"]}">',
        f'<meta name="twitter:image" content="{PRATINJAU}">',
        "",
        f'<link rel="canonical" href="{info["alamat"]}">',
    ]
    if noindex:
        baris.append('<meta name="robots" content="noindex, nofollow">')
    return "\n".join(baris)


DATA_STRUKTUR = """<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  "name": "AkunTuntas",
  "applicationCategory": "BusinessApplication",
  "applicationSubCategory": "Accounting",
  "operatingSystem": "Windows 10, Windows 11",
  "softwareVersion": "1.0.0",
  "description": "Aplikasi pembukuan dan perpajakan untuk UMKM, PT Perorangan, dan PT di Indonesia. Bekerja sepenuhnya offline.",
  "url": "https://akuntuntas.xinet.id/",
  "image": "https://akuntuntas.xinet.id/pratinjau.png",
  "inLanguage": "id",
  "publisher": {
    "@type": "Organization",
    "name": "Xinet Group"
  },
  "offers": [
    {
      "@type": "Offer",
      "name": "Paket Standar",
      "price": "3499000",
      "priceCurrency": "IDR",
      "availability": "https://schema.org/InStock"
    },
    {
      "@type": "Offer",
      "name": "Paket Enterprise",
      "price": "5499000",
      "priceCurrency": "IDR",
      "availability": "https://schema.org/InStock"
    }
  ],
  "featureList": [
    "Pembukuan berpasangan lengkap",
    "Perhitungan PPh 21, PPh Badan, dan PPN",
    "Laporan laba rugi, neraca, arus kas, dan ekuitas",
    "Payroll dan pemotongan PPh 21",
    "Persediaan, aset tetap, dan kontrak",
    "Penyimpanan data lokal tanpa internet"
  ]
}
</script>"""


def bersihkan_meta_lama(teks: str) -> str:
    """Buang meta SEO lama supaya tidak ada yang berganda."""
    pola = [
        r'\n<meta property="og:[^"]*"[^>]*>',
        r'\n<meta name="twitter:[^"]*"[^>]*>',
        r'\n<link rel="canonical"[^>]*>',
        r'\n<link rel="icon"[^>]*>',
        r'\n<link rel="apple-touch-icon"[^>]*>',
        r'\n<link rel="manifest"[^>]*>',
    ]
    for p in pola:
        teks = re.sub(p, "", teks)
    return teks


def main() -> int:
    print("=" * 74)
    print("  LENGKAPI META SEO SELURUH HALAMAN")
    print("=" * 74)
    print()

    diubah = []

    for nama, info in HALAMAN.items():
        berkas = WEB / nama
        if not berkas.exists():
            print(f"  {nama}: tidak ditemukan, dilewati")
            continue

        teks = berkas.read_text(encoding="utf-8")
        teks = bersihkan_meta_lama(teks)

        # Sisipkan sebelum </head>
        tambahan = FAVICON + "\n\n" + blok_og(info)
        if nama == "index.html":
            tambahan += "\n\n" + DATA_STRUKTUR
        tambahan += "\n"

        teks = teks.replace("</head>", tambahan + "</head>", 1)
        berkas.write_text(teks, encoding="utf-8")
        diubah.append(nama)
        print(f"  {nama}: meta lengkap ditambahkan")

    # Halaman yang tidak perlu didata tetap diberi meta agar tautannya
    # tampil rapi saat dibagikan, tetapi diberi penanda noindex.
    for nama in TANPA_INDEKS:
        berkas = WEB / nama
        if not berkas.exists():
            continue
        teks = berkas.read_text(encoding="utf-8")
        if 'name="robots"' in teks:
            print(f"  {nama}: sudah ada penanda noindex")
            continue

        judul = re.search(r"<title>([^<]*)</title>", teks)
        info = {
            "alamat": f"{SITUS}/{nama.replace('.html', '')}",
            "judul": judul.group(1) if judul else "AkunTuntas",
            "ringkas": "Halaman AkunTuntas.",
        }
        teks = bersihkan_meta_lama(teks)
        tambahan = FAVICON + "\n\n" + blok_og(info, noindex=True) + "\n"
        teks = teks.replace("</head>", tambahan + "</head>", 1)
        berkas.write_text(teks, encoding="utf-8")
        diubah.append(nama)
        print(f"  {nama}: meta ditambahkan dengan penanda noindex")

    print()
    print(f"  halaman diperbarui: {len(diubah)}")
    print("=" * 74)

    return 0


if __name__ == "__main__":
    sys.exit(main())
