"""
Periksa bahwa catatan rilis publik tidak memuat info sensitif.

Catatan rilis publik ada di dua tempat yang harus sama isinya:
    - docs/catatan-rilis.md
    - web/rilis.html

Catatan teknis yang boleh memuat hal sensitif ada di
docs/catatan-rilis-internal.md dan tidak diperiksa alat ini.

Cara pakai:
    python tools/periksa_catatan_rilis.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent

# Setiap pola disertai alasan mengapa tidak boleh tampil ke publik.
TERLARANG = [
    (r"\buji_coba\b", "menyebut nama berkas internal"),
    (r"\bpenanda\b", "memberi tahu ada berkas pembuka lisensi"),
    (r"\bbypass\b|\bdi-?bypass\b|\bbypass\b", "menyebut cara menembus"),
    (r"\bcelah\b", "mengakui sistem pernah dapat ditembus"),
    (r"\bbocor\b|\bkebocoran\b", "menyebut kebocoran"),
    (r"\bbajak\b|\bdibajak\b|\bpembajakan\b", "menyebut pembajakan"),
    (r"\bcrack\b|\bhack\b|\bretas\b", "menyebut pembobolan"),
    (r"\bmemundurkan\b", "mengajari cara mengakali jam"),
    (r"\bjam komputer\b", "mengajari cara mengakali jam"),
    (r"\bmenghapus catatan\b", "mengajari cara mengakali catatan"),
    (r"\bkecolongan\b", "menyebut kelalaian"),
    (r"\btanpa membayar\b", "menyebut pemakaian tanpa bayar"),
    (r"lisensi\s+\w*\s*gratis", "menyebut lisensi gratis"),
    (r"\bsidik perangkat\b", "membuka detail perlindungan"),
    (r"\bregistry\b|\bHKCU\b", "membuka detail sistem"),
    (r"\bMSIX\b|\bmakeappx\b", "membuka perkakas pembungkusan"),
    (r"\bpeninjau\b", "membuka alur peninjauan Store"),
    (r"\b\d+\s+celah keamanan", "menyebut angka perbaikan keamanan"),
    (r"\bkata sandi demo\b|\badmin123\b", "membuka kredensial"),
]

# Kata yang wajar muncul, walau sepintas mirip. Diabaikan saat pencocokan.
PENGECUALIAN = [
    r"penanda baris perbandingan",   # soal tabel di situs, bukan lisensi
    r"penanda untuk fitur",          # idem
]

# Bagian yang memang TIDAK tayang ke publik, jadi boleh memuat hal teknis.
# Pada berkas teks-siap-tempel.md, bagian "Catatan untuk sertifikasi" hanya
# dibaca peninjau Microsoft, dan justru WAJIB memuat kata sandi demo supaya
# peninjau dapat masuk. Karena itu bagian ini dilewati saat pemeriksaan.
BAGIAN_DIKECUALIKAN = {
    "docs/teks-siap-tempel.md": [
        ("### Catatan untuk sertifikasi", "### Informasi harga"),
    ],
}


def buang_bagian_dikecualikan(nama: str, teks: str) -> str:
    """Buang bagian yang memang bukan untuk publik."""
    for judul, sampai in BAGIAN_DIKECUALIKAN.get(nama, []):
        while judul in teks:
            awal = teks.index(judul)
            akhir = teks.find(sampai, awal)
            if akhir == -1:
                akhir = len(teks)
            teks = teks[:awal] + teks[akhir:]
    return teks


def bersihkan(teks: str) -> str:
    """Buang bagian yang tidak dibaca pengunjung."""
    teks = re.sub(r"<!--.*?-->", "", teks, flags=re.S)
    teks = re.sub(r"<style>.*?</style>", "", teks, flags=re.S)
    teks = re.sub(r"<script.*?</script>", "", teks, flags=re.S)
    teks = re.sub(r"<[^>]+>", " ", teks)
    return teks


def periksa(nama: str, teks: str) -> list[tuple[str, str, str]]:
    """Kembalikan daftar (pola, alasan, potongan teks)."""
    temuan = []
    for pola, alasan in TERLARANG:
        for m in re.finditer(pola, teks, re.I):
            awal = max(0, m.start() - 70)
            akhir = min(len(teks), m.end() + 70)
            potongan = " ".join(teks[awal:akhir].split())
            if any(re.search(p, potongan, re.I) for p in PENGECUALIAN):
                continue
            temuan.append((pola, alasan, potongan))
    return temuan


def utama() -> int:
    print("=" * 78)
    print("  PEMERIKSAAN CATATAN RILIS PUBLIK")
    print("=" * 78)

    berkas = [
        ("docs/catatan-rilis.md", False),
        ("web/rilis.html", True),
        ("docs/teks-siap-tempel.md", False),
        ("docs/catatan-rilis-internal.md", False),
    ]

    jumlah_lulus = 0
    jumlah_gagal = 0

    for nama, perlu_bersih in berkas:
        p = AKAR / nama
        print(f"\n  --- {nama} ---")

        if not p.exists():
            print(f"      GAGAL berkas tidak ada")
            jumlah_gagal += 1
            continue

        isi = p.read_text(encoding="utf-8")
        teks = bersihkan(isi) if perlu_bersih else isi
        teks = buang_bagian_dikecualikan(nama, teks)

        if nama.endswith("internal.md"):
            # Berkas ini justru harus ada dan diberi tanda peringatan,
            # supaya catatan teknis tidak tercampur ke berkas publik.
            if "TIDAK UNTUK DIPUBLIKASIKAN" in isi[:600]:
                print("      LULUS ada, dan sudah diberi tanda peringatan")
                jumlah_lulus += 1
            else:
                print("      GAGAL belum diberi tanda peringatan di awal")
                jumlah_gagal += 1
            continue

        temuan = periksa(nama, teks)
        if temuan:
            for pola, alasan, potongan in temuan:
                print(f"      GAGAL [{pola}] {alasan}")
                print(f"            ...{potongan}...")
                jumlah_gagal += 1
        else:
            print("      LULUS tidak memuat info sensitif")
            jumlah_lulus += 1

    print()
    print("=" * 78)
    print(f"  HASIL: {jumlah_lulus} LULUS, {jumlah_gagal} GAGAL")
    if jumlah_gagal == 0:
        print("  Catatan rilis publik aman disalin ke Partner Center.")
    else:
        print("  Perbaiki sebelum dipublikasikan.")
    print("=" * 78)
    return 0 if jumlah_gagal == 0 else 1


if __name__ == "__main__":
    sys.exit(utama())
