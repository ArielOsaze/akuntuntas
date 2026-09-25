"""
Tambahkan keterangan tabel kosong pada halaman yang belum memilikinya.

Tabel yang belum berisi data tampil sebagai ruang putih kosong. Pengguna
mengira halamannya rusak atau masih memuat, padahal memang belum ada
datanya. Keterangan yang menyebutkan langkah berikutnya membuat pengguna
tahu harus berbuat apa.

Cara pakai:
    python tools/pasang_pesan_kosong.py          # terapkan
    python tools/pasang_pesan_kosong.py --periksa # hanya periksa
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
HALAMAN = AKAR / "src" / "akuntansi_id" / "ui" / "pages"

# Pesan untuk setiap halaman, disesuaikan dengan isi halamannya.
PESAN = {
    "produk.py": (
        "Belum ada produk atau jasa yang terdaftar.\n\n"
        "Tekan tombol Tambah Produk untuk mencatat barang atau jasa yang "
        "Anda jual."),
    "aset.py": (
        "Belum ada aset tetap yang terdaftar.\n\n"
        "Tekan tombol Tambah Aset untuk mencatat peralatan, kendaraan, "
        "atau bangunan milik usaha Anda."),
    "penjualan.py": (
        "Belum ada transaksi penjualan.\n\n"
        "Tekan tombol Tambah Penjualan untuk mencatat penjualan pertama "
        "Anda. Jurnal dan pajaknya dihitung otomatis."),
    "pembelian.py": (
        "Belum ada transaksi pembelian.\n\n"
        "Tekan tombol Tambah Pembelian untuk mencatat pembelian barang "
        "atau jasa dari pemasok."),
    "biaya_bank.py": (
        "Belum ada catatan biaya atau mutasi bank.\n\n"
        "Tekan tombol Tambah untuk mencatat pengeluaran usaha atau "
        "mutasi rekening bank."),
    "laporan.py": (
        "Belum ada data untuk dilaporkan.\n\n"
        "Catat dulu transaksi pada menu Jurnal Umum, Penjualan, atau "
        "Pembelian. Laporan akan terisi sendiri."),
    "pajak.py": (
        "Belum ada data perpajakan.\n\n"
        "Catat dulu transaksi pada menu Jurnal Umum atau Penjualan. "
        "Perhitungan pajak akan muncul di sini."),
}


def sisipkan(isi: str, pesan: str) -> tuple[str, int]:
    """
    Sisipkan pemanggilan set_pesan_kosong setelah setiap pembuatan tabel.

    Pembuatan tabel dapat memakan satu baris atau beberapa baris, jadi
    penutup kurung dicari lebih dulu, baru baris berikutnya diperiksa.
    Pemanggilan hanya ditambahkan bila tabel itu belum memilikinya.
    """
    baris = isi.split("\n")
    keluaran = []
    jumlah = 0

    pola_buka = re.compile(
        r"^(?P<induk>[ \t]*)(?P<var>[\w.]+) = w\.Tabel(?:Angka)?\(")

    i = 0
    while i < len(baris):
        b = baris[i]
        keluaran.append(b)
        m = pola_buka.match(b)

        if m:
            induk = m.group("induk")
            var = m.group("var")

            # Cari baris penutup kurung pembuatan tabel.
            jeluk = b.count("(") - b.count(")")
            akhir = i
            while jeluk > 0 and akhir + 1 < len(baris):
                akhir += 1
                keluaran.append(baris[akhir])
                jeluk += baris[akhir].count("(") - baris[akhir].count(")")

            # Sisipkan keterangan sebelum baris berikutnya yang memakai
            # tabel itu, supaya urutannya tetap wajar.
            berikut = akhir + 1
            if berikut < len(baris) and "set_pesan_kosong" not in baris[berikut]:
                keluaran.append(
                    f"{induk}# Keterangan ini tampil saat tabel masih kosong, "
                    f"supaya\n"
                    f"{induk}# pengguna tahu langkah berikutnya.\n"
                    f"{induk}{var}.set_pesan_kosong(\n"
                    f'{induk}    "{pesan}")\n')
                jumlah += 1

            i = akhir + 1
            continue

        i += 1

    return "\n".join(keluaran), jumlah


def main() -> int:
    periksa_saja = "--periksa" in sys.argv

    print("=" * 76)
    print("  PASANG KETERANGAN TABEL KOSONG")
    print("=" * 76)
    print()

    total = 0
    for nama, pesan in PESAN.items():
        berkas = HALAMAN / nama
        if not berkas.exists():
            print(f"  [LEWAT] {nama}: berkas tidak ada")
            continue

        isi = berkas.read_text(encoding="utf-8")

        if "set_pesan_kosong" in isi:
            print(f"  [SUDAH] {nama}")
            continue

        baru, jumlah = sisipkan(isi, pesan)
        if jumlah == 0:
            print(f"  [LEWAT] {nama}: pola tabel tidak cocok")
            continue

        if not periksa_saja:
            berkas.write_text(baru, encoding="utf-8")
        total += jumlah
        print(f"  [{'DIPERIKSA' if periksa_saja else 'DIPASANG'}] "
              f"{nama}: {jumlah} tabel")

    print()
    print(f"  total tabel: {total}")
    if periksa_saja:
        print("  (mode periksa, tidak ada berkas yang diubah)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
