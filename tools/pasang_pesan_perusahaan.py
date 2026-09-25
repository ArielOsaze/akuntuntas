"""
Pasang pesan pemberitahuan pada tempat yang sebelumnya gagal senyap.

Masalah yang diperbaiki: tempat di antarmuka berhenti begitu saja ketika
profil perusahaan belum dibuat, tanpa memberi tahu pengguna apa pun.
Yang terjadi hanyalah tombol yang tidak bereaksi, sehingga pengguna
mengira aplikasinya rusak.

Pesan disisipkan SEBELUM baris return, bukan sesudahnya. Salah urutan
membuat pesannya tidak pernah dijalankan, dan itu justru lebih buruk
daripada tidak ada pesan sama sekali karena tampak sudah diperbaiki.

Cara pakai:
    python tools/pasang_pesan_perusahaan.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
HALAMAN = AKAR / "src" / "akuntansi_id" / "ui" / "pages"

# Nama tindakan untuk setiap fungsi, dibaca dari nama fungsi terdekat.
TINDAKAN = {
    "_tambah_karyawan": "menambah karyawan",
    "_ubah_karyawan": "mengubah data karyawan",
    "_hapus_karyawan": "menghapus data karyawan",
    "_tambah": "menambah data",
    "_ubah": "mengubah data",
    "_hapus": "menghapus data",
    "_simpan": "menyimpan data",
    "_jalankan": "menjalankan proses",
    "_ekspor": "mengekspor data",
    "_impor": "mengimpor data",
    "_buat": "membuat data",
    "_catat": "mencatat transaksi",
    "_proses": "memproses data",
    "_hitung": "menghitung",
    "_muat": "",
    "muat": "",
    "_pilih": "memilih data",
    "_cetak": "mencetak",
    "_buka": "membuka",
    "_buat_jurnal": "membuat jurnal",
    "_posting": "memposting",
}


def nama_tindakan(baris: list[str], posisi: int) -> str:
    """Cari nama fungsi terdekat di atas, lalu terjemahkan jadi tindakan."""
    for i in range(posisi, max(0, posisi - 100), -1):
        m = re.match(r"\s*def (\w+)\(", baris[i])
        if m:
            nama = m.group(1)
            if nama in TINDAKAN:
                return TINDAKAN[nama]
            return ""
    return ""


def main() -> int:
    if not HALAMAN.exists():
        print(f"  folder tidak ditemukan: {HALAMAN}")
        return 2

    total = 0
    berkas_diubah = []

    for f in sorted(HALAMAN.glob("*.py")):
        baris = f.read_text(encoding="utf-8").splitlines()
        hasil: list[str] = []
        diubah = 0

        i = 0
        while i < len(baris):
            sekarang = baris[i]

            # Pola yang dicari: baris pemeriksaan, lalu baris return.
            # Pesan disisipkan SEBELUM return supaya benar-benar dijalankan.
            if (sekarang.strip() == "if not self.ctx.company_id:"
                    and i + 1 < len(baris)
                    and baris[i + 1].strip() == "return"):
                indent = " " * (len(sekarang) - len(sekarang.lstrip()))

                # Periksa apakah pesan sudah ada di antara pemeriksaan
                # dan return (urutan yang benar).
                sudah_benar = False
                j = i + 1
                while j < len(baris) and baris[j].strip() not in (
                        "return", ""):
                    if "belum_ada_perusahaan" in baris[j]:
                        sudah_benar = True
                        break
                    j += 1

                if sudah_benar:
                    hasil.append(sekarang)
                    i += 1
                    continue

                tindakan = nama_tindakan(baris, i)
                if tindakan:
                    pesan = (f'{indent}    w.belum_ada_perusahaan('
                             f'self, "{tindakan}")')
                else:
                    pesan = f"{indent}    w.belum_ada_perusahaan(self)"

                hasil.append(sekarang)
                hasil.append(pesan)
                hasil.append(baris[i + 1])       # baris return
                diubah += 1
                i += 2
                continue

            hasil.append(sekarang)
            i += 1

        if diubah:
            f.write_text("\n".join(hasil) + "\n", encoding="utf-8")
            berkas_diubah.append((f.name, diubah))
            total += diubah

    print("=" * 74)
    print("  PASANG PESAN PADA TEMPAT YANG GAGAL SENYAP")
    print("=" * 74)
    print()
    print(f"  berkas diubah  : {len(berkas_diubah)}")
    print(f"  tempat dipasang: {total}")
    print()
    for nama, n in berkas_diubah:
        print(f"    {nama}: {n} tempat")
    print("=" * 74)

    return 0


if __name__ == "__main__":
    sys.exit(main())
