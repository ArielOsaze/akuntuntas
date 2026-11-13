"""
Uji halaman Pencarian Global: keadaan awal, hasil kosong, dan tombol buka.

Panel hasil dan detail tidak boleh tampil sebagai ruang putih kosong tanpa
keterangan. Tombol "Buka Halaman Terkait" juga harus nonaktif sampai ada
hasil yang benar-benar dipilih.

Cara pakai:
    python tests/test_pencarian_global.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("AKUNTANSIID_DATA",
                      str(Path(__file__).parent.parent / "_uitest_cari"))
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from PySide6.QtWidgets import QApplication

from akuntansi_id.ui import theme
from akuntansi_id.ui.pages import tata_kelola as tk

LULUS = 0
GAGAL = 0


def cek(nama: str, syarat: bool, keterangan: str = ""):
    global LULUS, GAGAL
    if syarat:
        LULUS += 1
        print(f"  [LULUS] {nama}")
    else:
        GAGAL += 1
        print(f"  [GAGAL] {nama}" + (f" — {keterangan}" if keterangan else ""))


class Ctx:
    company_id = 1


HASIL_CONTOH = [
    {"jenis": "Invoice", "judul": "INV/2026/0001",
     "keterangan": "PT Uji Mandiri", "halaman": "penjualan", "id": 11},
    {"jenis": "Produk", "judul": "P0001 - Jasa Konsultasi",
     "keterangan": "Jasa konsultasi", "halaman": "produk", "id": 12},
]


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyleSheet(theme.stylesheet())

    print("=" * 66)
    print("PENCARIAN GLOBAL — KEADAAN AWAL, HASIL, DAN TOMBOL")
    print("=" * 66)

    p = tk.PencarianPage(Ctx())
    p.resize(1100, 700)
    p.show()
    for _ in range(20):
        app.processEvents()

    print("\n[Keadaan awal]")
    cek("Keterangan awal tampil di daftar", p._petunjuk.isVisible())
    cek("Keterangan awal memuat panduan",
        "Hasil pencarian" in p._petunjuk.text())
    cek("Detail memuat panduan mencari",
        "Mulai pencarian" in p.detail.toPlainText())
    cek("Tombol buka nonaktif tanpa hasil", not p.btn_buka.isEnabled())
    cek("Info awal meminta minimal 2 huruf",
        "minimal 2 huruf" in p.lbl_info.text().lower())

    print("\n[Hasil kosong]")
    asli = tk.O.cari_global
    try:
        tk.O.cari_global = lambda cid, kata: []
        p.inp_cari.setText("zzz")
        p._tunda.stop()
        p._cari(diam=True)
        for _ in range(10):
            app.processEvents()
        cek("Daftar tetap menampilkan keterangan", p._petunjuk.isVisible())
        cek("Keterangan menyebut kata kunci",
            "zzz" in p._petunjuk.text())
        cek("Detail menjelaskan tidak ada hasil",
            "Tidak ada hasil" in p.detail.toPlainText())
        cek("Tombol buka tetap nonaktif", not p.btn_buka.isEnabled())

        print("\n[Hasil ditemukan]")
        tk.O.cari_global = lambda cid, kata: list(HASIL_CONTOH)
        p._cari(diam=True)
        for _ in range(10):
            app.processEvents()
        cek("Dua hasil tampil di daftar", p.hasil_list.count() == 2,
            f"jumlah={p.hasil_list.count()}")
        cek("Hasil pertama otomatis dipilih",
            p.hasil_list.currentRow() == 0)
        cek("Tombol buka aktif setelah ada pilihan", p.btn_buka.isEnabled())
        cek("Detail menampilkan hasil terpilih",
            "INV/2026/0001" in p.detail.toPlainText())
        cek("Keterangan kosong disembunyikan", not p._petunjuk.isVisible())

        pindah: list[str] = []
        p.pindah_halaman.connect(pindah.append)
        p.btn_buka.click()
        cek("Tombol membuka halaman hasil terpilih",
            pindah == ["penjualan"], str(pindah))

        p.hasil_list.setCurrentRow(1)
        p.btn_buka.click()
        cek("Pilihan kedua membuka halamannya",
            pindah == ["penjualan", "produk"], str(pindah))

        print("\n[Kembali ke keadaan awal]")
        p.inp_cari.clear()
        p._saat_mengetik("")
        for _ in range(10):
            app.processEvents()
        cek("Daftar dikosongkan", p.hasil_list.count() == 0)
        cek("Keterangan awal muncul kembali", p._petunjuk.isVisible())
        cek("Tombol buka nonaktif kembali", not p.btn_buka.isEnabled())

        print("\n[Isi berbahaya]")
        tk.O.cari_global = lambda cid, kata: [{
            "jenis": "Mitra", "judul": "<b>Nama & Co</b>",
            "keterangan": "<script>x</script>", "halaman": "mitra", "id": 1}]
        p.inp_cari.setText("uji")
        p._tunda.stop()
        p._cari(diam=True)
        for _ in range(10):
            app.processEvents()
        teks = p.detail.toPlainText()
        cek("Karakter HTML ditampilkan sebagai teks",
            "<b>Nama & Co</b>" in teks,
            teks[:80])
    finally:
        tk.O.cari_global = asli
        p.close()
        p.deleteLater()
        for _ in range(5):
            app.processEvents()

    print()
    if GAGAL:
        print(f"HASIL AKHIR: {LULUS} LULUS, {GAGAL} GAGAL")
        return 1
    print(f"HASIL AKHIR: {LULUS} LULUS, 0 GAGAL")
    return 0


if __name__ == "__main__":
    sys.exit(main())
