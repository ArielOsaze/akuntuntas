"""Pastikan berkas teks aplikasi bebas dari jejak gaya penulisan AI.

Cara pakai:
    python tools/periksa_jejak_ai.py

Yang diperiksa: emoji, tanda hubung panjang, tanda panah, bullet, tanda
centang, garis kotak, dan tanda kutip melengkung. Karakter seperti itu tidak
lazim pada dokumen produk dan membuat teks terasa dibuat mesin.

Berkas yang diperiksa adalah berkas yang dibaca pengguna saat memasang dan
memakai aplikasi: README, lisensi, skrip installer, dan keterangan versi.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent

BERKAS = [
    "README.md",
    "LICENSE.txt",
    "version_info.txt",
    "app_info.json",
    "installer.iss",
]

POLA = {
    "emoji": r"[\U0001F300-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF]",
    "tanda panah": r"[\u2190-\u21FF]",
    "tanda hubung panjang": r"[\u2013\u2014]",
    "bullet": r"\u2022",
    "tanda centang": r"[\u2713\u2714]",
    "garis kotak": r"[\u2500-\u257F]",
    "kutip melengkung": r"[\u2018\u2019\u201C\u201D]",
    "elipsis tunggal": r"\u2026",
}


def main() -> int:
    semua_temuan = []
    diperiksa = 0

    for nama in BERKAS:
        berkas = AKAR / nama
        if not berkas.exists():
            continue
        diperiksa += 1
        teks = berkas.read_text(encoding="utf-8", errors="replace")
        for label, pola in POLA.items():
            for cocok in re.finditer(pola, teks):
                baris = teks[:cocok.start()].count("\n") + 1
                semua_temuan.append((nama, baris, label, cocok.group()))

    if semua_temuan:
        print(f"HASIL: {len(semua_temuan)} jejak gaya AI ditemukan")
        for nama, baris, label, karakter in semua_temuan[:20]:
            print(f"   {nama}:{baris}  {label}  {karakter!r}")
        return 1

    print(f"HASIL: {diperiksa} berkas teks bebas jejak gaya AI")
    return 0


if __name__ == "__main__":
    sys.exit(main())
