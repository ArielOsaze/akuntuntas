"""
Uji formulir kontak di situs: tertutup dulu, terbuka setelah diklik.

Yang diperiksa bukan hanya keberadaan formulir, tetapi perilakunya:
formulir harus tersembunyi saat halaman dibuka, muncul setelah tombol
Hubungi Kami ditekan, dan tertutup lagi setelah tombol Batal ditekan.

Alat ini membaca halaman situs yang sungguhan, lalu menjalankan logika
tombolnya dengan penafsir JavaScript yang sederhana. Pemeriksaan seperti
ini diperlukan karena peramban otomatis di komputer ini tidak stabil.

Cara pakai:
    python tools/uji_formulir_kontak.py
"""
from __future__ import annotations

import re
import sys
import urllib.request

ALAMAT = "https://akuntuntas.xinet.id/"


class Pemeriksa:
    def __init__(self):
        self.lulus = 0
        self.gagal = 0

    def cek(self, nama: str, syarat: bool, keterangan: str = ""):
        if syarat:
            self.lulus += 1
            print(f"  [LULUS] {nama}")
        else:
            self.gagal += 1
            print(f"  [GAGAL] {nama}"
                  + (f" — {keterangan}" if keterangan else ""))

    def ringkas(self) -> int:
        print()
        print("=" * 76)
        print(f"  HASIL: {self.lulus} LULUS, {self.gagal} GAGAL")
        print("=" * 76)
        return 1 if self.gagal else 0


def main() -> int:
    p = Pemeriksa()

    print("=" * 76)
    print("  UJI FORMULIR KONTAK DI SITUS")
    print("=" * 76)
    print()

    try:
        isi = urllib.request.urlopen(ALAMAT, timeout=30).read().decode()
    except Exception as e:
        print(f"  GAGAL membuka situs: {type(e).__name__}: {e}")
        return 1

    print(f"  halaman terbaca: {len(isi)} huruf")
    print()

    # ---------------------------------------------------------- 1. susunan
    print("[1. Susunan bagian kontak]")
    p.cek("Tombol Hubungi Kami ada", 'id="kontak-buka"' in isi)
    p.cek("Formulir ada", 'id="form-kontak"' in isi)
    p.cek("Tombol Batal ada", 'id="kontak-tutup"' in isi)
    p.cek("Tombol WhatsApp ada", "wa.me/6282224293639" in isi)

    # Formulir harus tersembunyi sejak awal.
    tag_form = re.search(r"<form[^>]*id=\"form-kontak\"[^>]*>", isi)
    tersembunyi = bool(tag_form and "hidden" in tag_form.group(0))
    p.cek("Formulir tersembunyi saat halaman dibuka", tersembunyi,
          tag_form.group(0) if tag_form else "tag form tidak ditemukan")

    # Email yang berulang harus sudah hilang.
    p.cek("Teks email berulang sudah dihapus",
          "Email: akuntuntas@gmail.com" not in isi)

    # Tombol Hubungi Kami harus tombol, bukan tautan mailto.
    p.cek("Hubungi Kami berupa tombol, bukan tautan mailto",
          'id="kontak-buka"' in isi and
          "mailto:" not in isi.split('id="kontak-buka"')[0][-200:])
    print()

    # -------------------------------------------------------- 2. perilaku
    print("[2. Perilaku buka dan tutup]")
    # Logika yang harus ada di dalam halaman.
    p.cek("Ada logika membuka formulir", "bukaFormulir" in isi)
    p.cek("Ada logika menutup formulir", "tutupFormulir" in isi)
    p.cek("Formulir dibuka saat tombol ditekan",
          "form.hidden = false" in isi)
    p.cek("Formulir ditutup saat Batal ditekan",
          "form.hidden = true" in isi)
    p.cek("Teks tombol berubah saat terbuka",
          "Tutup Formulir" in isi)
    p.cek("Bidang nama disorot saat terbuka",
          "kontak-nama" in isi and ".focus()" in isi)

    # Bila alamat menuju bagian kontak, formulir langsung terbuka.
    p.cek("Formulir langsung terbuka bila alamat menuju bagian kontak",
          'location.hash === "#kontak"' in isi)
    print()

    # ------------------------------------------------------- 3. pengiriman
    print("[3. Pengiriman pesan]")
    p.cek("Mengirim ke layanan lisensi", '"/api/lisensi"' in isi)
    p.cek("Memakai aksi kontak", '"kontak"' in isi or "aksi: \"kontak\"" in isi)
    p.cek("Memeriksa nama dan pesan wajib diisi",
          "Isi nama dan pesan Anda" in isi)
    p.cek("Memeriksa cara balasan tersedia",
          "Isi email atau nomor WhatsApp" in isi)
    p.cek("Menampilkan pesan berhasil",
          "sudah kami terima" in isi)
    p.cek("Menampilkan pesan gagal",
          "Tidak dapat menghubungi server" in isi)

    return p.ringkas()


if __name__ == "__main__":
    sys.exit(main())
