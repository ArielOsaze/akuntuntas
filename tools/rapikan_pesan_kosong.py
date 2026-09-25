"""
Rapikan penulisan keterangan tabel kosong agar mudah dibaca.

Pesan yang terpasang menjadi satu baris panjang. Kode lebih mudah dibaca
bila teksnya dipecah menjadi beberapa baris bersambung, dengan penanda
baris baru tetap di dalam teksnya.

Cara pakai:
    python tools/rapikan_pesan_kosong.py
"""
from __future__ import annotations

import re
import sys
import textwrap
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
HALAMAN = AKAR / "src" / "akuntansi_id" / "ui" / "pages"

BERKAS = [
    "produk.py", "aset.py", "penjualan.py", "pembelian.py",
    "biaya_bank.py", "laporan.py", "pajak.py", "mitra.py",
]

# Pemanggilan dengan satu baris teks panjang.
POLA = re.compile(
    r'(?P<induk>[ \t]*)(?P<var>[\w.]+)\.set_pesan_kosong\(\n'
    r'(?P<isi_induk>[ \t]*)"(?P<pesan>(?:[^"\\]|\\.)*)"\)\n',
)


def pecah(pesan: str, lebar: int = 62) -> list[str]:
    """
    Pecah pesan menjadi baris-baris kode yang mudah dibaca.

    Pemisah paragraf tetap dipertahankan pada batas paragrafnya.
    """
    paragraf = pesan.split("\\n\\n")
    baris_kode: list[str] = []

    for i, p in enumerate(paragraf):
        if i > 0:
            baris_kode.append("\\n\\n")
        # Bungkus pada spasi terdekat, jangan memotong kata.
        bungkus = textwrap.wrap(p, width=lebar)
        for j, b in enumerate(bungkus):
            # Beri spasi di akhir setiap potongan kecuali yang terakhir,
            # supaya kalimatnya tersambung kembali saat dijalankan.
            akhir = " " if j < len(bungkus) - 1 else ""
            baris_kode.append(b + akhir)

    return baris_kode


def rapikan(isi: str) -> tuple[str, int]:
    jumlah = 0

    def ganti(m):
        nonlocal jumlah
        induk = m.group("induk")
        var = m.group("var")
        pesan = m.group("pesan")

        # Hanya rapikan pesan yang cukup panjang.
        if len(pesan) < 70:
            return m.group(0)

        baris_kode = pecah(pesan)
        potongan = []
        for b in baris_kode:
            potongan.append(f'{induk}    "{b}"')

        hasil = (f"{induk}{var}.set_pesan_kosong(\n"
                 + "\n".join(potongan)
                 + ")\n")
        jumlah += 1
        return hasil

    return POLA.sub(ganti, isi), jumlah


def main() -> int:
    print("=" * 76)
    print("  RAPIKAN PENULISAN KETERANGAN TABEL KOSONG")
    print("=" * 76)
    print()

    total = 0
    for nama in BERKAS:
        berkas = HALAMAN / nama
        if not berkas.exists():
            continue

        isi = berkas.read_text(encoding="utf-8")
        if "set_pesan_kosong" not in isi:
            continue

        baru, jumlah = rapikan(isi)
        if jumlah == 0:
            print(f"  [LEWAT] {nama}")
            continue

        berkas.write_text(baru, encoding="utf-8")
        total += jumlah
        print(f"  [RAPI]  {nama}: {jumlah} keterangan")

    print()
    print(f"  total: {total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
