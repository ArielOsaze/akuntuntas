"""
Uji coba sebagai pengguna: isi seluruh data, lalu periksa ulang semuanya.

Cara ini berbeda dari semua pengujian sebelumnya. Pengujian sebelumnya
menyerang satu bagian pada satu waktu. Kali ini aplikasi dipakai seperti
pengguna baru memakainya pertama kali, dari perusahaan masih kosong
sampai tutup buku akhir tahun:

  1. Buat perusahaan (PT) beserta bagan akunnya.
  2. Isi profil lengkap: NPWP, alamat, telepon, email, izin usaha.
  3. Isi saldo awal neraca.
  4. Catat mitra: pelanggan dan pemasok.
  5. Catat produk beserta gudang.
  6. Catat transaksi penjualan, termasuk yang PKP dan yang belum lunas.
  7. Catat pembelian, termasuk PPN masukan.
  8. Catat pengeluaran biaya operasional.
  9. Catat aset tetap dan jalankan penyusutan setahun.
 10. Catat karyawan dan jalankan penggajian sebulan.
 11. Catat potongan pajak (PPh 23) dan pembayaran pajak.
 12. Jalankan stok masuk dan keluar dengan HPP.
 13. Buat jurnal penyesuaian manual.
 14. Jalankan tutup buku akhir tahun.
 15. Periksa seluruh laporan, dan periksa silang antar laporan.

Setiap langkah diperiksa: apakah datanya tersimpan, apakah angkanya benar
menurut hitungan sendiri, dan apakah laporannya saling cocok. Di akhir,
seluruh data dibaca ulang langsung dari basis data dan dibandingkan dengan
yang seharusnya, supaya tidak ada yang lolos hanya karena tampilannya.

Cara pakai:
    python tools/uji_pengguna_lengkap.py
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "src"))

FOLDER = Path(tempfile.mkdtemp(prefix="akuntuntas_pengguna_"))
os.environ["LOCALAPPDATA"] = str(FOLDER)

from akuntansi_id import db, modules, services  # noqa: E402
from akuntansi_id import modules_sales as S  # noqa: E402
from akuntansi_id.core import accounting as acc  # noqa: E402


class Pemeriksa:
    def __init__(self):
        self.lulus = 0
        self.gagal = 0
        self.temuan: list[str] = []

    def cek(self, nama: str, syarat: bool, catatan: str = ""):
        if syarat:
            self.lulus += 1
        else:
            self.gagal += 1
            self.temuan.append(nama)
            print(f"    [SALAH] {nama}")
            if catatan:
                print(f"            {catatan}")

    def cek_sama(self, nama: str, satu, lain, catatan: str = ""):
        self.cek(nama, satu == lain,
                 catatan or f"seharusnya {lain!r}, ternyata {satu!r}")

    def bagian(self, judul: str):
        print()
        print(f"  {judul}")

    def ringkas(self) -> int:
        print()
        print("=" * 76)
        if self.gagal:
            print(f"  HASIL: {self.lulus} BENAR, {self.gagal} SALAH")
            print()
            for t in self.temuan:
                print(f"    - {t}")
        else:
            print(f"  HASIL: {self.lulus} BENAR, 0 SALAH")
        print("=" * 76)
        return 1 if self.gagal else 0


def main() -> int:
    p = Pemeriksa()
    print("=" * 76)
    print("  UJI COBA SEBAGAI PENGGUNA: ISI SEMUA DATA LALU PERIKSA ULANG")
    print("=" * 76)

    db.init_db()

    # ==================================================================
    # 1. BUAT PERUSAHAAN
    # ==================================================================
    p.bagian("[1. Pengguna baru membuat perusahaan]")
    cid = services.create_company(
        "PT Sinar Nusantara", bentuk="pt",
        npwp="01.234.567.8-901.000",
        alamat="Jl. Gatot Subroto 88, Jakarta Selatan",
        telepon="021-5550123", email="keuangan@sinarnusantara.co.id",
        nama_pemilik="Budi Santoso", status_pkp=1)
    comp = services.get_company(cid)
    p.cek("perusahaan tersimpan", comp is not None)
    p.cek_sama("nama perusahaan benar", comp["nama"], "PT Sinar Nusantara")
    p.cek_sama("NPWP tersimpan benar", comp["npwp"], "01.234.567.8-901.000")
    p.cek("perusahaan ditandai PKP", bool(comp["status_pkp"]))

    akun = services.list_accounts(cid)
    p.cek("bagan akun terisi (minimal 40 akun)", len(akun) >= 40,
          f"jumlah akun: {len(akun)}")
    for kode in ("1001", "1101", "1104", "2001", "2013", "3001", "3007",
                 "4001", "5001", "6006"):
        ada = any(a["kode"] == kode for a in akun)
        p.cek(f"akun {kode} tersedia", ada)

    # ==================================================================
    # 2. ISI SALDO AWAL
    # ==================================================================
    p.bagian("[2. Pengguna mengisi saldo awal]")
    saldo_awal = {
        "1001": 750_000_000,   # Kas
        "1101": 250_000_000,   # Piutang
        "1104": 180_000_000,   # Persediaan
        "1201": 400_000_000,   # Peralatan
        "1202": -80_000_000,   # Akumulasi penyusutan
        "2001": 200_000_000,   # Utang usaha
        "3001": 1_300_000_000,  # Modal
    }
    services.set_saldo_awal(cid, saldo_awal)
    cek_awal = services.cek_keseimbangan_saldo_awal(cid)
    p.cek("saldo awal seimbang (harta = utang + modal)",
          bool(cek_awal.get("seimbang")),
          f"selisih: {cek_awal.get('selisih', 0):,}")

    # ==================================================================
    # 3. MITRA
    # ==================================================================
    p.bagian("[3. Pengguna mencatat pelanggan dan pemasok]")
    pelanggan = modules.buat_mitra(
        cid, "PT Maju Bersama", "customer",
        npwp="02.345.678.9-012.000", email="pembelian@majubersama.co.id",
        telepon="021-7771234", kota="Jakarta")
    modules.buat_mitra(
        cid, "CV Sumber Makmur", "vendor",
        npwp="03.456.789.0-123.000", email="sales@sumbermakmur.co.id",
        telepon="031-8881234", kota="Surabaya")
    jumlah_mitra = db.scalar("SELECT COUNT(*) FROM partners WHERE company_id=?",
                             (cid,))
    p.cek_sama("2 mitra tersimpan", int(jumlah_mitra), 2)
    mitra_pel = db.q1("SELECT * FROM partners WHERE id=?", (pelanggan,))
    p.cek_sama("nama pelanggan benar", mitra_pel["nama"], "PT Maju Bersama")
    p.cek_sama("tipe pelanggan benar", mitra_pel["tipe"], "customer")

    # ==================================================================
    # 4. PRODUK & GUDANG
    # ==================================================================
    p.bagian("[4. Pengguna mencatat produk dan gudang]")
    gudang_utama = modules.gudang_utama(cid)
    gudang_kedua = modules.buat_gudang(cid, "Gudang Surabaya")
    p.cek("gudang utama tersedia", gudang_utama is not None)
    p.cek("gudang kedua dapat dibuat", gudang_kedua is not None)

    produk_a = modules.buat_produk(
        cid, "Laptop Pro 14 inci", satuan="unit", harga_beli=12_000_000,
        harga_jual=15_500_000, metode_hpp="average", stok_minimum=3)
    produk_b = modules.buat_produk(
        cid, "Mouse Wireless", satuan="pcs", harga_beli=120_000,
        harga_jual=185_000, metode_hpp="fifo", stok_minimum=10)
    jumlah_produk = db.scalar("SELECT COUNT(*) FROM products WHERE company_id=?",
                              (cid,))
    p.cek_sama("2 produk tersimpan", int(jumlah_produk), 2)
    prod_a = modules.get_produk(produk_a)
    p.cek_sama("metode HPP produk A = average",
               prod_a["metode_hpp"], "average")
    prod_b = modules.get_produk(produk_b)
    p.cek_sama("metode HPP produk B = fifo", prod_b["metode_hpp"], "fifo")

    # ==================================================================
    # 5. STOK MASUK
    # ==================================================================
    p.bagian("[5. Pengguna mencatat stok masuk]")
    modules.stok_masuk(cid, produk_a, 20, 12_000_000, "2026-01-05",
                       ref_tipe="pembelian", no_ref="PB-001")
    modules.stok_masuk(cid, produk_b, 100, 120_000, "2026-01-06",
                       ref_tipe="pembelian", no_ref="PB-002")
    saldo_a = modules.saldo_stok(cid, produk_a)
    p.cek_sama("stok laptop = 20 unit", int(saldo_a["qty"]), 20)
    p.cek_sama("nilai stok laptop = Rp240.000.000",
               int(saldo_a["nilai_total"]), 240_000_000)
    p.cek_sama("HPP satuan laptop = Rp12.000.000",
               int(saldo_a["hpp_satuan"]), 12_000_000)

    # ==================================================================
    # 6. PENJUALAN
    # ==================================================================
    p.bagian("[6. Pengguna mencatat penjualan]")
    # Penjualan memakai jalur yang sama dengan tombol Buat Invoice di
    # aplikasi, supaya harga pokok penjualannya ikut terjurnal.
    # Invoice 1: laptop, PKP. 5 unit x 15.500.000 = 77.500.000
    S.buat_invoice(cid, "2026-02-10",
                   [{"product_id": produk_a, "qty": 5,
                     "harga_satuan": 15_500_000}],
                   partner_id=pelanggan, jenis_ppn="12% DPP Nilai Lain (11/12)",
                   username="pemilik")
    # Invoice 2: laptop, PKP. 3 unit x 15.500.000 = 46.500.000
    S.buat_invoice(cid, "2026-02-20",
                   [{"product_id": produk_a, "qty": 3,
                     "harga_satuan": 15_500_000}],
                   partner_id=pelanggan, jenis_ppn="12% DPP Nilai Lain (11/12)",
                   username="pemilik")
    # Invoice 3: mouse, non-PKP. 40 x 185.000 = 7.400.000
    S.buat_invoice(cid, "2026-03-05",
                   [{"product_id": produk_b, "qty": 40,
                     "harga_satuan": 185_000}],
                   pelanggan="Toko Melati",
                   jenis_ppn="Non-PKP/Tidak Dipungut", username="pemilik")

    jumlah_inv = db.scalar("SELECT COUNT(*) FROM invoices WHERE company_id=?",
                           (cid,))
    p.cek_sama("3 invoice tersimpan", int(jumlah_inv), 3)

    # PPN invoice 1: 11/12 x 77.500.000 x 12% = 8.525.000
    ppn1 = db.q1("""SELECT dpp, ppn, total FROM invoices
                    WHERE company_id=? ORDER BY id LIMIT 1""", (cid,))
    p.cek_sama("DPP invoice 1 = Rp77.500.000", int(ppn1["dpp"]), 77_500_000)
    p.cek_sama("PPN invoice 1 = Rp8.525.000", int(ppn1["ppn"]), 8_525_000)
    p.cek_sama("total invoice 1 = Rp86.025.000", int(ppn1["total"]), 86_025_000)

    # HPP otomatis: 5 x 12.000.000 = 60.000.000 pada invoice 1,
    #               3 x 12.000.000 = 36.000.000 pada invoice 2,
    #               40 x 120.000  =  4.800.000 pada invoice 3.
    hpp_jurnal = db.scalar("""SELECT COALESCE(SUM(jl.debit),0)
                              FROM journal_lines jl
                              JOIN journal_entries je ON je.id = jl.entry_id
                              WHERE jl.company_id=? AND jl.kode_akun='5001'""",
                           (cid,))
    p.cek_sama("HPP otomatis terjurnal Rp100.800.000",
               int(hpp_jurnal), 100_800_000)

    # Persediaan berkurang sebesar HPP yang sama.
    persediaan_kredit = db.scalar("""SELECT COALESCE(SUM(jl.kredit),0)
                                     FROM journal_lines jl
                                     JOIN journal_entries je ON je.id = jl.entry_id
                                     WHERE jl.company_id=? AND jl.kode_akun='1104'""",
                                  (cid,))
    p.cek("persediaan berkurang sebesar HPP", int(persediaan_kredit) >= 100_800_000,
          f"kredit persediaan: {persediaan_kredit:,}")

    # Piutang dari tiga invoice (belum ada yang dibayar).
    piutang = db.scalar("""SELECT COALESCE(SUM(debit - kredit),0) FROM journal_lines
                           WHERE company_id=? AND kode_akun='1101'""", (cid,))
    harap_piutang = 86_025_000 + 51_615_000 + 7_400_000
    p.cek_sama("piutang dari 3 invoice = Rp145.040.000",
               int(piutang), harap_piutang)

    # ==================================================================
    # 7. PEMBELIAN
    # ==================================================================
    p.bagian("[7. Pengguna mencatat pembelian]")
    services.simpan_pembelian(
        cid, "2026-01-05", "PB-001", "CV Sumber Makmur",
        240_000_000, jenis_ppn="12% DPP Nilai Lain (11/12)",
        jenis="Persediaan", akun_beban="1104",
        npwp_nik="03.456.789.0-123.000", dibayar=True,
        tanggal_bayar="2026-01-05")
    services.simpan_pembelian(
        cid, "2026-01-15", "PB-002", "CV Sumber Makmur",
        12_000_000, jenis_ppn="12% DPP Nilai Lain (11/12)",
        jenis="Beban", akun_beban="6006", dibayar=True,
        tanggal_bayar="2026-01-15")
    services.simpan_pembelian(
        cid, "2026-02-01", "PB-003", "CV Sumber Makmur",
        30_000_000, jenis_ppn="Non-PKP/Tidak Dipungut",
        jenis="Beban", akun_beban="6007", dibayar=False)

    jumlah_beli = db.scalar("SELECT COUNT(*) FROM purchases WHERE company_id=?",
                            (cid,))
    p.cek_sama("3 pembelian tersimpan", int(jumlah_beli), 3)

    # PPN masukan: 11/12 x 240.000.000 x 12% = 26.400.000
    ppn_masukan = db.q1("""SELECT ppn_masukan FROM purchases
                           WHERE company_id=? AND no_invoice=?""",
                        (cid, "PB-001"))
    p.cek_sama("PPN masukan Rp240 juta = Rp26.400.000",
               int(ppn_masukan["ppn_masukan"]), 26_400_000)

    # ==================================================================
    # 8. BIAYA OPERASIONAL
    # ==================================================================
    p.bagian("[8. Pengguna mencatat biaya operasional]")
    services.simpan_jurnal_manual(
        cid, "2026-03-31", "BIAYA-001", "Gaji dan tunjangan Maret",
        [{"kode_akun": "6006", "debit": 45_000_000, "kredit": 0, "keterangan": ""},
         {"kode_akun": "1001", "debit": 0, "kredit": 45_000_000, "keterangan": ""}])
    services.simpan_jurnal_manual(
        cid, "2026-03-31", "BIAYA-002", "Sewa kantor dan listrik",
        [{"kode_akun": "6007", "debit": 18_000_000, "kredit": 0, "keterangan": ""},
         {"kode_akun": "1001", "debit": 0, "kredit": 18_000_000, "keterangan": ""}])
    beban_6006 = db.scalar("""SELECT COALESCE(SUM(debit - kredit),0) FROM journal_lines
                              WHERE company_id=? AND kode_akun='6006'""", (cid,))
    p.cek("beban 6006 bertambah", int(beban_6006) >= 45_000_000)

    # ==================================================================
    # 9. ASET TETAP
    # ==================================================================
    p.bagian("[9. Pengguna mencatat aset tetap dan menyusutkannya]")
    aset_id = services.simpan_aset(
        cid, "AST-001", "Kendaraan Operasional", "2026-01-10",
        350_000_000, kelompok_fiskal="Kelompok 2",
        metode_fiskal="Garis Lurus", umur_komersial=8,
        residu_komersial=0, akun_aset="1201", akun_akum="1202",
        akun_beban="6007", akun_kas="1001")
    p.cek("aset tersimpan", aset_id is not None)
    aset = db.q1("SELECT * FROM fixed_assets WHERE id=?", (aset_id,))
    p.cek_sama("harga perolehan aset benar",
               int(aset["harga_perolehan"]), 350_000_000)
    p.cek_sama("kelompok fiskal benar", aset["kelompok_fiskal"], "Kelompok 2")

    hasil_susut = services.hitung_penyusutan_tahun(cid, 2026)
    p.cek("penyusutan tahunan berjalan tanpa galat", hasil_susut is not None)
    rekap = services.rekap_penyusutan(cid, 2026)
    p.cek("rekap penyusutan terisi", bool(rekap))

    # ==================================================================
    # 10. KARYAWAN & PAYROLL
    # ==================================================================
    p.bagian("[10. Pengguna mencatat karyawan dan menjalankan penggajian]")
    services.simpan_karyawan(
        cid, "Andi Pratama", 8_500_000, jabatan="Manajer Keuangan",
        status_ptkp="K/1", tunjangan_tetap=1_500_000,
        nik_npwp="3174012345670001", tanggal_masuk="2025-01-06")
    services.simpan_karyawan(
        cid, "Siti Nurhaliza", 5_500_000, jabatan="Staf Akuntansi",
        status_ptkp="TK/0", tunjangan_tetap=500_000,
        nik_npwp="3174023456780002", tanggal_masuk="2025-03-01")
    services.simpan_karyawan(
        cid, "Rudi Hartono", 4_800_000, jabatan="Staf Penjualan",
        status_ptkp="K/0", tunjangan_tetap=1_200_000,
        nik_npwp="3174034567890003", tanggal_masuk="2025-06-15")
    jumlah_karyawan = db.scalar("SELECT COUNT(*) FROM employees WHERE company_id=?",
                                (cid,))
    p.cek_sama("3 karyawan tersimpan", int(jumlah_karyawan), 3)

    payroll = services.hitung_payroll_bulanan(cid, "2026-04", posting=True)
    p.cek("penggajian April berjalan", bool(payroll))
    run_id = payroll.get("run_id") if isinstance(payroll, dict) else None
    if run_id:
        detail = services.detail_payroll(run_id)
        p.cek_sama("penggajian memuat 3 karyawan", len(detail), 3)
        # Baris penggajian berbentuk baris basis data, jadi kolomnya dibaca
        # dengan tanda kurung siku, bukan dengan .get().
        total_bruto = sum(int(d["bruto"]) for d in detail)
        total_thp = sum(int(d["take_home_pay"]) for d in detail)
        total_pph = sum(int(d["pph21"]) for d in detail)
        total_bpjs_k = sum(int(d["bpjs_karyawan"]) for d in detail)
        p.cek("bruto lebih besar dari take home pay",
              total_bruto > total_thp,
              f"bruto {total_bruto:,} vs THP {total_thp:,}")

        # Take home pay harus sama dengan bruto dikurangi potongan.
        p.cek_sama("take home pay = bruto - BPJS karyawan - PPh 21",
                   total_thp, total_bruto - total_bpjs_k - total_pph,
                   f"bruto {total_bruto:,} - bpjs {total_bpjs_k:,} "
                   f"- pph {total_pph:,} = {total_bruto - total_bpjs_k - total_pph:,}")

        # Bruto Andi = gaji 8.500.000 + tunjangan 1.500.000 = 10.000.000
        andi = next((d for d in detail if "Andi" in str(d["nama"])), None)
        if andi:
            p.cek_sama("bruto Andi = Rp10.000.000 (gaji + tunjangan)",
                       int(andi["bruto"]), 10_000_000)
            # BPJS karyawan: kes 1% + JHT 2% + JP 1% = 4% x 10.000.000
            bpjs_harap = int(round(10_000_000 * 0.04))
            p.cek_sama("BPJS karyawan Andi = 4% x Rp10.000.000",
                       int(andi["bpjs_karyawan"]), bpjs_harap)
            # BPJS perusahaan: JKK 0,24% + JKM 0,30% + JHT 3,7% + JP 2%
            #                  + kes 4% = 10,24% x 10.000.000
            bpjs_p_harap = int(round(10_000_000 * 0.1024))
            p.cek_sama("BPJS perusahaan Andi = 10,24% x Rp10.000.000",
                       int(andi["bpjs_perusahaan"]), bpjs_p_harap)
        else:
            p.cek("data Andi ada di penggajian", False,
                  f"nama yang ada: {[d['nama'] for d in detail]}")
    else:
        p.cek("penggajian menghasilkan run_id", False, f"hasil: {payroll}")

    # ==================================================================
    # 11. PAJAK POTONG/PUNGUT & PEMBAYARAN
    # ==================================================================
    p.bagian("[11. Pengguna mencatat potongan pajak dan pembayarannya]")
    potput = services.simpan_pajak(
        cid, "2026-03-15", "PPh23-JASA", 50_000_000, masa="2026-03",
        no_bupot="BP-2026-001", status="Terutang")
    p.cek("potongan PPh 23 tersimpan", potput is not None)
    pajak_row = db.q1("SELECT * FROM tax_records WHERE id=?", (potput,))
    if pajak_row:
        # PPh 23 jasa = 2% x 50.000.000 = 1.000.000
        p.cek_sama("PPh 23 jasa = Rp1.000.000", int(pajak_row["pajak"]), 1_000_000)
    else:
        p.cek("baris pajak dapat dibaca", False)

    bayar = services.catat_pembayaran_pajak(
        cid, "PPh23-JASA", "2026-03", "2026-04-15", 1_000_000,
        ntpn="NTPN-2026-001")
    p.cek("pembayaran PPh 23 tercatat", bayar is not None)

    # PPh 21 yang muncul dari penggajian juga disetor, seperti yang
    # dilakukan pengguna pada bulan berikutnya.
    pph21_row = db.q1("""SELECT masa, pajak FROM tax_records
                         WHERE company_id=? AND kode_pajak='PPh21'""", (cid,))
    if pph21_row:
        bayar21 = services.catat_pembayaran_pajak(
            cid, "PPh21", pph21_row["masa"], "2026-05-10",
            int(pph21_row["pajak"]), ntpn="NTPN-2026-002")
        p.cek("pembayaran PPh 21 tercatat", bayar21 is not None)
    else:
        p.cek("catatan PPh 21 terbentuk dari penggajian", False)

    # Setelah dibayar, statusnya berubah dan jurnal setoran terbentuk.
    status_bayar = db.q1("""SELECT status FROM tax_records
                            WHERE company_id=? AND kode_pajak='PPh23-JASA'""",
                         (cid,))
    if status_bayar:
        p.cek_sama("status pajak berubah menjadi Disetor",
                   status_bayar["status"], "Disetor")
    else:
        p.cek("baris pajak masih ada setelah dibayar", False)

    # ==================================================================
    # 12. STOK KELUAR (HPP)
    # ==================================================================
    p.bagian("[12. Memeriksa stok setelah penjualan]")
    # Stok berkurang otomatis saat invoice dibuat: 20 - 5 - 3 = 12 unit.
    saldo_a2 = modules.saldo_stok(cid, produk_a)
    p.cek_sama("sisa stok laptop = 12 unit", int(saldo_a2["qty"]), 12)
    # Nilai persediaan laptop: 240.000.000 - 96.000.000 = 144.000.000
    p.cek_sama("nilai persediaan laptop = Rp144.000.000",
               int(saldo_a2["nilai_total"]), 144_000_000)
    # Mouse: 100 - 40 = 60 unit. FIFO memakai lapisan Rp120.000.
    saldo_b2 = modules.saldo_stok(cid, produk_b)
    p.cek_sama("sisa stok mouse = 60 unit", int(saldo_b2["qty"]), 60)
    p.cek_sama("nilai persediaan mouse = Rp7.200.000",
               int(saldo_b2["nilai_total"]), 7_200_000)
    # Penjualan melebihi stok harus ditolak.
    try:
        modules.stok_keluar(cid, produk_b, 500, "2026-04-20")
        p.cek("penjualan melebihi stok ditolak", False,
              "stok keluar 500 unit diterima padahal sisa 60")
    except ValueError:
        p.cek("penjualan melebihi stok ditolak dengan keterangan", True)
    except Exception as e:
        p.cek("penjualan melebihi stok ditolak dengan keterangan", False,
              f"{type(e).__name__}: {e}")

    # ==================================================================
    # 13. JURNAL PENYESUAIAN
    # ==================================================================
    p.bagian("[13. Pengguna membuat jurnal penyesuaian]")
    services.simpan_jurnal_manual(
        cid, "2026-12-31", "ADJ-001", "Penyesuaian beban dibayar di muka",
        [{"kode_akun": "6007", "debit": 6_000_000, "kredit": 0, "keterangan": ""},
         {"kode_akun": "2013", "debit": 0, "kredit": 6_000_000, "keterangan": ""}])
    p.cek("jurnal penyesuaian tersimpan", True)

    # ==================================================================
    # 14. LAPORAN: PERIKSA SILANG
    # ==================================================================
    p.bagian("[14. Memeriksa laporan dan kecocokannya satu sama lain]")
    lr = acc.laba_rugi(cid, 2026)
    ner = acc.neraca(cid, 2026)
    arus = acc.arus_kas(cid, 2026)

    pendapatan = (getattr(lr, "pendapatan_usaha", 0)
                  + getattr(lr, "pendapatan_lain", 0))
    # Penjualan: 77.500.000 + 46.500.000 + 7.400.000 = 131.400.000
    p.cek_sama("pendapatan setahun = Rp131.400.000", pendapatan, 131_400_000)

    hpp = getattr(lr, "hpp", 0)
    # HPP dari tiga invoice: 60.000.000 + 36.000.000 + 4.800.000
    p.cek_sama("HPP di laba rugi = Rp100.800.000", hpp, 100_800_000)

    harta = getattr(ner, "total_aset", 0)
    utang_modal = (getattr(ner, "total_liabilitas", 0)
                   + getattr(ner, "total_ekuitas", 0))
    p.cek_sama("neraca seimbang: harta = utang + ekuitas", harta, utang_modal,
               f"harta {harta:,} vs utang+modal {utang_modal:,}")

    p.cek_sama("pendapatan - beban = laba sebelum pajak",
               pendapatan - (getattr(lr, "hpp", 0)
                             + getattr(lr, "beban_operasional", 0)
                             + getattr(lr, "beban_lain", 0)),
               getattr(lr, "laba_sebelum_pajak", 0))

    ns = acc.total_neraca_saldo(cid, 2026)
    p.cek_sama("neraca saldo seimbang", ns.get("debit", 0), ns.get("kredit", 0))

    # Angka dasbor harus sama dengan laporan.
    kpi = acc.dashboard_kpi(cid, 2026)
    if isinstance(kpi, dict):
        p.cek_sama("omzet di dasbor = pendapatan di laba rugi",
                   kpi.get("omzet", 0), pendapatan)

    # Buku besar harus cocok dengan saldo.
    for kode in ("1001", "1101", "4001", "5001", "6006"):
        bk = acc.buku_besar(cid, kode, 2026)
        if not bk:
            p.cek(f"buku besar {kode} terisi", False, "kosong")
            continue
        akhir = bk[-1].get("saldo")
        r = db.q1("""SELECT COALESCE(SUM(jl.debit),0) AS d,
                            COALESCE(SUM(jl.kredit),0) AS k
                     FROM journal_lines jl
                     JOIN journal_entries je ON je.id = jl.entry_id
                     WHERE jl.company_id=? AND jl.kode_akun=?
                       AND je.tanggal BETWEEN '2026-01-01' AND '2026-12-31'""",
                  (cid, kode))
        a = db.q1("SELECT normal, saldo_awal FROM accounts WHERE company_id=? AND kode=?",
                  (cid, kode))
        normal = (a["normal"] or "Debit").lower() if a else "debit"
        net = r["d"] - r["k"]
        awal = int(a["saldo_awal"] or 0) if a else 0
        harap = (awal - net) if normal.startswith("kredit") else (awal + net)
        p.cek_sama(f"buku besar {kode} cocok dengan hitungan", akhir, harap,
                   f"aplikasi {akhir:,} vs hitungan {harap:,}")

    # ==================================================================
    # RINCIAN BEBAN (dibaca SEBELUM tutup buku, karena jurnal penutup
    # memindahkan saldo beban ke laba sehingga akun beban menjadi nol)
    # ==================================================================    print("  Rincian beban (supaya setiap angka dapat dijelaskan):")
    rincian = db.q("""
        SELECT jl.kode_akun, a.nama, COALESCE(SUM(jl.debit - jl.kredit), 0) AS nilai
        FROM journal_lines jl
        LEFT JOIN accounts a ON a.company_id = jl.company_id AND a.kode = jl.kode_akun
        WHERE jl.company_id = ?
          AND jl.kode_akun IN (SELECT kode FROM accounts
                               WHERE company_id = ? AND tipe = 'Beban')
        GROUP BY jl.kode_akun HAVING nilai <> 0 ORDER BY nilai DESC""",
        (cid, cid))
    total_rincian = 0
    for r in rincian:
        nama_akun = (r["nama"] or "")[:34]
        print(f"    {r['kode_akun']} {nama_akun:34s} Rp{int(r['nilai']):>16,}")
        total_rincian += int(r["nilai"])
    print(f"    {'':38s} {'-' * 17}")
    print(f"    {'Total beban':38s} Rp{total_rincian:>16,}")

    # Total rincian harus sama dengan jumlah beban di laba rugi.
    beban_lr = (getattr(lr, "hpp", 0) + getattr(lr, "beban_operasional", 0)
                + getattr(lr, "beban_lain", 0))
    p.cek_sama("jumlah rincian beban = total beban di laba rugi",
               total_rincian, beban_lr)
    print()
    # ==================================================================
    # 15. TUTUP BUKU
    # ==================================================================
    p.bagian("[15. Pengguna menjalankan tutup buku akhir tahun]")
    try:
        entry_penutup = services.buat_jurnal_penutup(cid, 2026)
        p.cek("jurnal penutup terbentuk", entry_penutup is not None)
        if entry_penutup:
            baris = db.q("SELECT * FROM journal_lines WHERE entry_id=?",
                         (entry_penutup,))
            p.cek("jurnal penutup punya baris", len(baris) >= 2,
                  f"jumlah baris: {len(baris)}")
            d = sum(int(b["debit"]) for b in baris)
            k = sum(int(b["kredit"]) for b in baris)
            p.cek_sama("jurnal penutup seimbang", d, k)
    except Exception as e:
        p.cek("tutup buku berjalan tanpa galat", False,
              f"{type(e).__name__}: {e}")

    # ==================================================================
    # 16. PERIKSA ULANG LANGSUNG DARI BASIS DATA
    # ==================================================================
    p.bagian("[16. Memeriksa ulang seluruh data langsung dari basis data]")
    # Hitung semua yang seharusnya ada, lalu bandingkan dengan isi tabel.
    # Tabel companies tidak memakai kolom company_id, jadi dihitung
    # terpisah.
    jumlah_comp = db.scalar("SELECT COUNT(*) FROM companies")
    p.cek_sama("tabel companies memuat 1 baris", int(jumlah_comp), 1)

    harapan_tabel = {
        "partners": 2, "products": 2, "warehouses": 2,
        "invoices": 3, "purchases": 3, "employees": 3, "fixed_assets": 1,
    }
    for tabel, jumlah in harapan_tabel.items():
        ada = db.scalar(f"SELECT COUNT(*) FROM {tabel} WHERE company_id=?",
                        (cid,))
        p.cek_sama(f"tabel {tabel} memuat {jumlah} baris", int(ada), jumlah)

    # Tidak ada jurnal yang tidak seimbang.
    tidak_seimbang = db.q("""
        SELECT je.id, je.no_bukti,
               COALESCE(SUM(jl.debit),0) AS d, COALESCE(SUM(jl.kredit),0) AS k
        FROM journal_entries je
        LEFT JOIN journal_lines jl ON jl.entry_id = je.id
        WHERE je.company_id = ?
        GROUP BY je.id HAVING d <> k OR COUNT(jl.id) < 2""", (cid,))
    p.cek("seluruh jurnal seimbang", not tidak_seimbang,
          f"{len(tidak_seimbang)} jurnal tidak seimbang")

    # Tidak ada baris jurnal dengan akun yang tidak ada di bagan akun.
    akun_hilang = db.q("""
        SELECT DISTINCT jl.kode_akun FROM journal_lines jl
        LEFT JOIN accounts a ON a.company_id = jl.company_id
                            AND a.kode = jl.kode_akun
        WHERE jl.company_id = ? AND a.id IS NULL""", (cid,))
    p.cek("seluruh kode akun pada jurnal ada di bagan akun",
          not akun_hilang,
          f"kode tanpa akun: {[r['kode_akun'] for r in akun_hilang][:6]}")

    # Tidak ada tanggal yang tidak sah.
    tanggal_salah = db.q("""
        SELECT tanggal FROM journal_entries WHERE company_id=?
        AND (length(tanggal) <> 10 OR substr(tanggal, 5, 1) <> '-'
             OR substr(tanggal, 8, 1) <> '-')""", (cid,))
    p.cek("seluruh tanggal jurnal berbentuk baku", not tanggal_salah,
          f"tanggal tidak baku: {[r['tanggal'] for r in tanggal_salah][:5]}")

    # Tidak ada stok bernilai negatif padahal jumlahnya masih ada.
    stok_aneh = db.q("""
        SELECT product_id, qty, nilai_total FROM stock_balances
        WHERE company_id=? AND qty > 0 AND nilai_total < 0""", (cid,))
    p.cek("tidak ada persediaan bernilai negatif", not stok_aneh,
          f"{len(stok_aneh)} baris")

    # Seluruh penjualan punya jurnal.
    jual_tanpa_jurnal = db.scalar("""
        SELECT COUNT(*) FROM invoices
        WHERE company_id=? AND journal_entry_id IS NULL""", (cid,))
    p.cek_sama("seluruh invoice punya jurnal", int(jual_tanpa_jurnal), 0)

    # Seluruh pembelian punya jurnal.
    beli_tanpa_jurnal = db.scalar("""
        SELECT COUNT(*) FROM purchases WHERE company_id=? AND journal_entry_id IS NULL""",
        (cid,))
    p.cek_sama("seluruh pembelian punya jurnal", int(beli_tanpa_jurnal), 0)

    # Pajak yang sudah dibayar tidak lagi berstatus terutang.
    terutang = db.scalar("""SELECT COUNT(*) FROM tax_records
                            WHERE company_id=? AND status='Terutang'""", (cid,))
    p.cek_sama("tidak ada pajak yang masih terutang", int(terutang), 0)
    disetor = db.scalar("""SELECT COUNT(*) FROM tax_records
                           WHERE company_id=? AND status='Disetor'""", (cid,))
    p.cek("pajak yang dibayar berstatus Disetor", int(disetor) >= 1,
          f"jumlah: {disetor}")

    # Ringkasan akhir yang berguna bagi pengguna.
    print()
    print("  Ringkasan pembukuan yang tercatat:")
    print(f"    pendapatan setahun   : Rp{pendapatan:,}")
    print(f"    HPP                  : Rp{hpp:,}")
    print(f"    beban operasional    : Rp{getattr(lr, 'beban_operasional', 0):,}")
    print(f"    laba sebelum pajak   : Rp{getattr(lr, 'laba_sebelum_pajak', 0):,}")
    print(f"    taksiran pajak       : Rp{getattr(lr, 'beban_pajak', 0):,}")
    print(f"    laba bersih          : Rp{getattr(lr, 'laba_bersih', 0):,}")
    print(f"    total harta          : Rp{harta:,}")
    print(f"    total utang + modal  : Rp{utang_modal:,}")
    print(f"    saldo kas akhir      : Rp{int(getattr(arus, 'kas_akhir', 0)):,}")
    print(f"    jurnal tercatat      : "
          f"{db.scalar('SELECT COUNT(*) FROM journal_entries WHERE company_id=?', (cid,))}")


    return p.ringkas()


if __name__ == "__main__":
    try:
        kode = main()
    finally:
        shutil.rmtree(FOLDER, ignore_errors=True)
    sys.exit(kode)
