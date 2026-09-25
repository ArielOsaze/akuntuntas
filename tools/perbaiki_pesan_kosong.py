"""
Perbaiki keterangan tabel kosong yang terpasang sebagai baris baru.

Teks pesan memuat penanda baris baru, tetapi saat disisipkan penanda itu
berubah menjadi baris sungguhan sehingga berkasnya tidak dapat dijalankan.
Alat ini menyatukan kembali pesan yang terpecah menjadi satu kalimat
dengan penanda yang benar.

Cara pakai:
    python tools/perbaiki_pesan_kosong.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
HALAMAN = AKAR / "src" / "akuntansi_id" / "ui" / "pages"

BERKAS = [
    "produk.py", "aset.py", "penjualan.py", "pembelian.py",
    "biaya_bank.py", "laporan.py", "pajak.py",
]

# Pola pemanggilan yang rusak: pesan terpecah menjadi beberapa baris.
POLA = re.compile(
    r'(?P<awal>[ \t]*\w[\w.]*\.set_pesan_kosong\(\n'
    r'[ \t]*")'
    r'(?P<isi>.*?)'
    r'(?P<akhir>")',
    re.DOTALL,
)


def rapikan(isi: str) -> tuple[str, int]:
    jumlah = 0

    def ganti(m):
        nonlocal jumlah
        pesan = m.group("isi")
        # Baris baru sungguhan diubah kembali menjadi penanda, dan
        # pemisah baris Windows dinormalkan.
        pesan = pesan.replace("\r\n", "\n")
        # Baris kosong yang dihasilkan menjadi pemisah paragraf.
        bagian = [b.strip() for b in pesan.split("\n")]
        bagian = [b for b in bagian if b]
        teks = "\\n\\n".join(bagian)
        # Tanda kutip di dalam teks harus dilindungi.
        teks = teks.replace('"', '\\"')
        jumlah += 1
        return m.group("awal") + teks + m.group("akhir")

    return POLA.sub(ganti, isi), jumlah


def main() -> int:
    print("=" * 76)
    print("  PERBAIKI KETERANGAN TABEL KOSONG")
    print("=" * 76)
    print()

    total = 0
    for nama in BERKAS:
        berkas = HALAMAN / nama
        if not berkas.exists():
            print(f"  [LEWAT] {nama}: tidak ada")
            continue

        isi = berkas.read_text(encoding="utf-8")
        if "set_pesan_kosong" not in isi:
            print(f"  [LEWAT] {nama}: tidak memakai keterangan")
            continue

        baru, jumlah = rapikan(isi)
        if jumlah == 0:
            print(f"  [LEWAT] {nama}: tidak ada yang perlu dirapikan")
            continue

        berkas.write_text(baru, encoding="utf-8")
        total += jumlah
        print(f"  [RAPI]  {nama}: {jumlah} keterangan")

    print()
    print(f"  total dirapikan: {total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
