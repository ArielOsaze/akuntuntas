"""Periksa integrasi antar-fitur: data satu modul mengalir ke modul lain.

Cara pakai:
    python tools/periksa_integrasi.py

Aplikasi pembukuan baru benar bila setiap transaksi langsung terhubung:
penjualan menambah piutang dan jurnal, pembelian menambah utang dan
persediaan, biaya masuk ke laba rugi, dan seluruhnya bertemu di laporan
serta pajak. Pemeriksaan ini menjalankan rantai itu dari awal sampai akhir
lalu memastikan angkanya konsisten di setiap tahap.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
os.environ["AKUNTANSIID_DATA"] = str(AKAR / "_integrasi")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(AKAR / "src"))

from akuntansi_id import db, modules as M, modules_ops as O  # noqa: E402
from akuntansi_id import modules_sales as S, services  # noqa: E402
from akuntansi_id.core import accounting as acc  # noqa: E402
from akuntansi_id.core import tax_engine as tx  # noqa: E402

HASIL: list = []


def cek(nama: str, syarat: bool, detail: str = ""):
    HASIL.append((nama, syarat, detail))
    print(f"  {'LULUS' if syarat else 'GAGAL'}  {nama}"
          + (f"  [{detail}]" if detail and not syarat else ""))


def main() -> int:
    import shutil
    if Path(os.environ["AKUNTANSIID_DATA"]).exists():
        shutil.rmtree(os.environ["AKUNTANSIID_DATA"], ignore_errors=True)

    db.init_db()
    from akuntansi_id.core import security as sec
    sec.ensure_default_admin()

    print("=== 1. Perusahaan & saldo awal ===")
    cid = services.create_company(
        "PT Integrasi Uji", "pt",
        npwp="01.234.567.8-901.000", tahun_buku_awal="2026-01-01",
        alamat="Jl. Uji 1", kota="Jakarta", pkp=True)
    services.set_saldo_awal(cid, {"1001": 500_000_000, "3001": 500_000_000})
    cek("perusahaan dibuat", cid > 0)
    neraca0 = acc.neraca(cid, 2026)
    cek("neraca awal seimbang", neraca0.seimbang, f"selisih {neraca0.selisih}")

    print("\n=== 2. Master data ===")
    pel = M.buat_mitra(cid, "PT Pelanggan Uji", "customer", pkp=True,
                       npwp="02.111.222.3-444.000")
    pem = M.buat_mitra(cid, "PT Pemasok Uji", "vendor", pkp=True,
                       npwp="03.111.222.3-444.000")
    brg = M.buat_produk(cid, "Barang Uji", tipe="barang", satuan="unit",
                        harga_beli=1_000_000, harga_jual=1_500_000,
                        qty_awal=100, tanggal_stok_awal="2026-01-01")
    cek("pelanggan dibuat", pel > 0)
    cek("pemasok dibuat", pem > 0)
    cek("produk dibuat", brg > 0)
    stok0 = M.saldo_stok(cid, brg)["qty"]
    cek("stok awal tercatat", stok0 == 100, f"stok={stok0}")

    print("\n=== 3. Penjualan -> piutang, stok, jurnal ===")
    inv = S.buat_invoice(cid, "2026-03-05", [
        {"product_id": brg, "qty": 10, "harga_satuan": 1_500_000}],
        partner_id=pel, jenis_ppn="PPN Keluaran")
    cek("invoice dibuat", inv > 0)
    stok1 = M.saldo_stok(cid, brg)["qty"]
    cek("stok berkurang setelah jual", stok1 == 90, f"stok={stok1}")
    piutang = sum(p["sisa"] for p in S.piutang_per_pelanggan(cid))
    cek("piutang bertambah", piutang > 0, f"piutang={piutang}")

    print("\n=== 4. Pembelian -> utang, stok, jurnal ===")
    bill = S.buat_bill(cid, "2026-03-08", [
        {"product_id": brg, "qty": 20, "harga_satuan": 1_000_000}],
        partner_id=pem, jenis_ppn="PPN Masukan")
    cek("bill dibuat", bill > 0)
    stok2 = M.saldo_stok(cid, brg)["qty"]
    cek("stok bertambah setelah beli", stok2 == 110, f"stok={stok2}")
    utang = S.aging_utang(cid).get("total", 0)
    cek("utang bertambah", utang > 0, f"utang={utang}")

    print("\n=== 5. Biaya -> laba rugi ===")
    exp = O.ajukan_biaya(cid, "2026-03-10", "Beban Listrik Uji", 2_000_000,
                         "6003")
    O.bayar_biaya(exp, "2026-03-10")
    cek("biaya dicatat & dibayar", exp > 0)
    lr = acc.laba_rugi(cid, 2026, beban_pajak=0)
    cek("biaya muncul di laba rugi", lr.beban_operasional >= 2_000_000,
        f"beban={lr.beban_operasional}")

    print("\n=== 6. Pembayaran -> piutang & utang turun ===")
    S.terima_pembayaran(cid, "2026-03-15", 5_000_000,
                        [{"invoice_id": inv, "jumlah": 5_000_000}],
                        partner_id=pel, akun_kas="1001")
    piutang2 = sum(p["sisa"] for p in S.piutang_per_pelanggan(cid))
    cek("piutang turun setelah bayar", piutang2 < piutang,
        f"{piutang:,} -> {piutang2:,}")

    S.bayar_vendor(cid, "2026-03-16", 3_000_000,
                   [{"bill_id": bill, "jumlah": 3_000_000}],
                   partner_id=pem, akun_kas="1001")
    utang2 = S.aging_utang(cid).get("total", 0)
    cek("utang turun setelah bayar", utang2 < utang,
        f"{utang:,} -> {utang2:,}")

    print("\n=== 7. Neraca & arus kas tetap seimbang ===")
    nr = acc.neraca(cid, 2026)
    cek("neraca seimbang", nr.seimbang, f"selisih {nr.selisih}")
    tb = acc.total_neraca_saldo(cid, 2026)
    cek("neraca saldo seimbang", tb["seimbang"],
        f"debit {tb['debit']} vs kredit {tb['kredit']}")

    print("\n=== 8. Pajak terhubung ke jurnal ===")
    ppn_bulanan = acc.rekap_ppn_bulanan(cid, 2026)
    keluaran = sum(b.get("ppn_keluaran", 0) for b in ppn_bulanan)
    masukan = sum(b.get("ppn_masukan_kredit", 0) for b in ppn_bulanan)
    cek("PPN keluaran terbaca dari penjualan", keluaran > 0,
        f"keluaran={keluaran:,}")
    cek("PPN masukan terbaca dari pembelian", masukan > 0,
        f"masukan={masukan:,}")
    cek("PPN keluaran sesuai invoice (Rp1.650.000)",
        keluaran == 1_650_000, f"keluaran={keluaran:,}")
    cek("PPN masukan sesuai bill (Rp2.200.000)",
        masukan == 2_200_000, f"masukan={masukan:,}")
    pph = tx.hitung_pph_badan(cid, 2026)
    cek("PPh Badan terhitung", pph is not None and pph.pph_terutang >= 0,
        f"PPh={getattr(pph, 'pph_terutang', 0):,}")

    print("\n=== 9. Buku besar & kartu stok ===")
    bb = acc.buku_besar(cid, "1101", 2026)
    cek("buku besar piutang ada isinya", len(bb) > 0, f"{len(bb)} baris")
    kartu = M.kartu_stok(cid, brg)
    cek("kartu stok ada isinya", len(kartu) > 0, f"{len(kartu)} baris")

    print("\n=== 10. Analisis kesehatan membaca data nyata ===")
    a = services.analisis(cid, 2026)
    cek("analisis berjalan", a is not None)
    cek("skor dalam rentang 0-100", 0 <= a.skor <= 100, f"skor={a.skor}")

    print("\n=== 11. Data contoh bawaan aplikasi ===")
    contoh = services.list_companies()
    cek("perusahaan terdaftar", len(contoh) >= 1)

    gagal = [h for h in HASIL if not h[1]]
    print("\n" + "=" * 74)
    if gagal:
        print(f"HASIL: {len(HASIL) - len(gagal)} LULUS, {len(gagal)} GAGAL")
        for nama, _, detail in gagal:
            print(f"   GAGAL: {nama} {detail}")
        return 1
    print(f"HASIL: {len(HASIL)} LULUS, 0 GAGAL — seluruh modul terintegrasi")
    return 0


if __name__ == "__main__":
    sys.exit(main())
