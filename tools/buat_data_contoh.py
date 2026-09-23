"""
Buat data contoh lengkap untuk pemeriksaan tampilan dan latihan pengguna.

Cara pakai:
    python tools/buat_data_contoh.py                  # ke folder _contoh
    python tools/buat_data_contoh.py D:\\DataContoh   # ke folder pilihan

Data yang dibuat menggambarkan usaha dagang kecil yang sudah berjalan:
saldo awal seimbang, penjualan, pembelian, biaya, aset tetap, dan rekening bank.
"""
from __future__ import annotations

import os
import shutil
import sys
from datetime import date
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent


def siapkan(folder: Path) -> None:
    if folder.exists():
        shutil.rmtree(folder, ignore_errors=True)
    os.environ["AKUNTANSIID_DATA"] = str(folder)
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    sys.path.insert(0, str(AKAR / "src"))


def main() -> int:
    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else AKAR / "_contoh"
    siapkan(folder)

    from akuntansi_id import config, db, services, modules as M, modules_sales as S
    from akuntansi_id import modules_ops as O
    from akuntansi_id.core import security as sec

    config.ensure_dirs()
    db.init_db()
    sec.ensure_default_admin()

    tahun = date.today().year
    cid = services.create_company(
        "PT Maju Bersama Sejahtera", "pt",
        npwp="01.234.567.8-901.000", alamat="Jl. Jenderal Sudirman No. 45",
        kota="Jakarta", kode_pos="12190", telepon="021-5551234",
        email="keuangan@majubersama.co.id", nama_pemilik="Budi Santoso",
        status_pkp=True, nomor_pkp="S-1234567890", skema_pph="pasal31e",
        omzet_prev_year=8_500_000_000,
        tahun_buku_awal=f"{tahun}-01-01")

    # Saldo awal: total debit harus sama dengan total kredit.
    # Aset 775.000.000 = Utang 175.000.000 + Modal 600.000.000
    services.set_saldo_awal(cid, {
        "1001": 25_000_000,      # Kas
        "1002": 15_000_000,      # Kas kecil
        "1003": 285_000_000,     # Bank
        "1104": 75_000_000,      # Persediaan
        "1201": 375_000_000,     # Tanah
        "2101": 175_000_000,     # Utang bank jangka pendek
        "3001": 600_000_000,     # Modal saham
    })

    cek_awal = services.cek_keseimbangan_saldo_awal(cid)
    if not cek_awal["seimbang"]:
        print("PERINGATAN: saldo awal tidak seimbang (selisih "
              f"{cek_awal['selisih']:,})")

    pelanggan = [
        M.buat_mitra(cid, "PT Retail Nusantara", "customer",
                     npwp="02.345.678.9-012.000", kota="Jakarta",
                     termin_hari=30, batas_kredit=200_000_000),
        M.buat_mitra(cid, "Toko Elektronik Jaya", "customer", kota="Surabaya",
                     termin_hari=14),
        M.buat_mitra(cid, "CV Digital Kreasi", "customer", kota="Yogyakarta",
                     termin_hari=30),
    ]
    vendor = [
        M.buat_mitra(cid, "CV Sumber Makmur", "vendor", kota="Bandung"),
        M.buat_mitra(cid, "PT Distribusi Utama", "vendor", kota="Tangerang"),
    ]

    laptop = M.buat_produk(cid, "Laptop Pro 14 inch", tipe="barang", satuan="unit",
                           harga_beli=8_500_000, harga_jual=12_500_000,
                           qty_awal=30, metode="average")
    printer = M.buat_produk(cid, "Printer Laser A4", tipe="barang", satuan="unit",
                            harga_beli=2_400_000, harga_jual=3_750_000,
                            qty_awal=50, metode="average")
    jaringan = M.buat_produk(cid, "Instalasi Jaringan Kantor", tipe="jasa",
                             satuan="paket", harga_jual=15_000_000)
    servis = M.buat_produk(cid, "Jasa Servis & Perawatan", tipe="jasa",
                           satuan="kunjungan", harga_jual=850_000)

    penjualan = [
        (f"{tahun}-01-12", pelanggan[0], laptop, 3, 12_500_000),
        (f"{tahun}-01-25", pelanggan[1], printer, 8, 3_750_000),
        (f"{tahun}-02-05", pelanggan[0], jaringan, 1, 15_000_000),
        (f"{tahun}-02-14", pelanggan[2], laptop, 5, 12_500_000),
        (f"{tahun}-02-22", pelanggan[1], servis, 6, 850_000),
        (f"{tahun}-03-08", pelanggan[0], printer, 12, 3_750_000),
    ]
    for tanggal, mitra, produk, qty, harga in penjualan:
        S.buat_invoice(
            cid, tanggal,
            [{"product_id": produk, "deskripsi": "", "qty": qty,
              "satuan": "unit", "harga_satuan": harga, "diskon_persen": 0}],
            mitra, jenis_ppn="12% DPP Nilai Lain (11/12)")

    S.buat_bill(
        cid, f"{tahun}-01-20",
        [{"product_id": laptop, "deskripsi": "", "qty": 20, "satuan": "unit",
          "harga_satuan": 8_500_000, "diskon_persen": 0}],
        vendor[0], jenis="Persediaan", jenis_ppn="12% DPP Nilai Lain (11/12)")
    S.buat_bill(
        cid, f"{tahun}-02-18",
        [{"product_id": printer, "deskripsi": "", "qty": 30, "satuan": "unit",
          "harga_satuan": 2_400_000, "diskon_persen": 0}],
        vendor[1], jenis="Persediaan", jenis_ppn="12% DPP Nilai Lain (11/12)")

    kategori = O.buat_kategori_biaya(cid, "Operasional Kantor", akun_beban="6023")
    O.ajukan_biaya(cid, f"{tahun}-01-31", "Listrik dan air kantor Januari",
                   3_500_000, "6023", kategori, "PLN & PDAM")
    O.ajukan_biaya(cid, f"{tahun}-02-01", "Internet dan telepon kantor",
                   1_200_000, "6023", kategori, "Telkom")
    O.ajukan_biaya(cid, f"{tahun}-02-15", "Sewa kantor Februari",
                   12_000_000, "6021", kategori, "Pemilik Gedung")

    services.simpan_aset(
        cid, "AST-001", "Kendaraan Operasional Toyota Avanza",
        f"{tahun}-01-05", 280_000_000, kelompok_fiskal="Kelompok 2",
        umur_komersial=8, residu_komersial=0, akun_aset="1204",
        akun_akum="1205")

    # Rekening kas & bank sudah dibuat otomatis saat profil perusahaan dibuat
    # (satu rekening untuk setiap akun kas/bank pada bagan akun), sehingga
    # saldo awal cukup diisi pada akun COA di atas.

    O.buat_cost_center(cid, "Divisi Penjualan", penanggung_jawab="Andi Wijaya",
                       anggaran=120_000_000)
    O.buat_cost_center(cid, "Divisi Operasional", penanggung_jawab="Siti Rahayu",
                       anggaran=240_000_000)
    O.buat_proyek(cid, "Implementasi Jaringan Klien ABC",
                  partner_id=pelanggan[0], tanggal_mulai=f"{tahun}-02-01",
                  tanggal_selesai=f"{tahun}-06-30",
                  nilai_kontrak=180_000_000, anggaran=110_000_000)

    from akuntansi_id.core import accounting as acc
    tb = acc.total_neraca_saldo(cid, tahun)
    nr = acc.neraca(cid, tahun)

    # Kontrak dan kerja sama: mengisi halaman Kontrak dengan contoh yang
    # mencakup perjanjian bernilai uang, kerja sama barter, dan MoU.
    from akuntansi_id import kontrak as kt
    kt.simpan(cid, {
        "judul": "Nota Kesepahaman Distribusi Wilayah",
        "jenis": "mou", "pihak_kedua": "PT Retail Nusantara",
        "tanggal_mulai": f"{tahun}-01-01", "tanggal_akhir": f"{tahun}-12-31",
        "nilai": 250_000_000, "skema_bayar": "termin", "jumlah_termin": 4,
        "dasar_hukum": "Pasal 1320 KUH Perdata; Pasal 1338 KUH Perdata"})
    kt.simpan(cid, {
        "judul": "Kerja Sama Barter Hasil Pertanian",
        "jenis": "kerja_sama", "bentuk_imbalan": "barang",
        "pihak_kedua": "CV Sumber Makmur",
        "tanggal_mulai": f"{tahun}-02-01", "tanggal_akhir": f"{tahun}-08-31",
        "nilai_barang": 120_000_000,
        "dasar_hukum": "Pasal 1320 KUH Perdata"})
    kt.simpan(cid, {
        "judul": "Sewa Gudang Logistik Bekasi", "jenis": "sewa",
        "pihak_kedua": "PT Distribusi Utama",
        "tanggal_mulai": f"{tahun - 1}-01-01", "tanggal_akhir": f"{tahun}-01-31",
        "nilai": 180_000_000, "skema_bayar": "bulanan",
        "dasar_hukum": "Pasal 1548 KUH Perdata"})
    kt.simpan(cid, {
        "judul": "Perjanjian Kerja Sama Jasa Digital Marketing",
        "jenis": "jasa", "bentuk_imbalan": "jasa",
        "pihak_kedua": "CV Digital Kreasi",
        "tanggal_mulai": f"{tahun}-03-01", "tanggal_akhir": f"{tahun}-09-30",
        "nilai_jasa": 96_000_000, "skema_bayar": "termin", "jumlah_termin": 3,
        "dasar_hukum": "Pasal 1601 KUH Perdata"})

    print(f"Data contoh dibuat di: {folder}")
    print("   perusahaan   : PT Maju Bersama Sejahtera")
    print(f"   pelanggan    : {len(pelanggan)}")
    print(f"   pemasok      : {len(vendor)}")
    print("   produk/jasa  : 4")
    print(f"   invoice      : {len(penjualan)}")
    print("   bill         : 2")
    print(f"   neraca saldo : debit {tb['debit']:,} / kredit {tb['kredit']:,} "
          f"({'seimbang' if tb['seimbang'] else 'TIDAK SEIMBANG'})")
    print(f"   neraca       : aset {nr.total_aset:,} = liabilitas "
          f"{nr.total_liabilitas:,} + ekuitas {nr.total_ekuitas:,} "
          f"(selisih {nr.selisih:,})")
    print()
    print("Masuk aplikasi dengan: admin / admin123")
    return 0 if tb["seimbang"] and nr.selisih == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
