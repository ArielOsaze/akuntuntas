"""Uji fitur pajak lanjutan: NSFP, faktur pajak, uang muka, meterai, PBJT,
kurs, PPh 15, dan jurnal balik."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
DATA = AKAR / "_ujipajak"
os.environ["AKUNTANSIID_DATA"] = str(DATA)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(AKAR / "src"))

from akuntansi_id import db, modules as M  # noqa: E402
from akuntansi_id import modules_pajak as P, services  # noqa: E402
from akuntansi_id.core import accounting as acc  # noqa: E402
from akuntansi_id.core import security as sec  # noqa: E402

HASIL: list = []


def cek(nama, syarat, detail=""):
    HASIL.append((nama, bool(syarat), detail))
    tanda = "LULUS" if syarat else "GAGAL"
    print(f"  {tanda}  {nama}" + (f"  [{detail}]" if detail else ""))


def main() -> int:
    if DATA.exists():
        shutil.rmtree(DATA, ignore_errors=True)
    db.init_db()
    sec.ensure_default_admin()

    cid = services.create_company("PT Uji Pajak", "pt",
                                  npwp="01.111.222.3-444.000", pkp=True)
    services.set_saldo_awal(cid, {"1001": 500_000_000, "3001": 500_000_000})
    pel = M.buat_mitra(cid, "PT Pelanggan", "customer", pkp=True,
                       npwp="02.111.222.3-444.000")

    print("=== 1. Nomor Seri Faktur Pajak ===")
    nsfp = P.tambah_nsfp(cid, 2026, "010.000-26.00000001",
                         "010.000-26.00000010")
    cek("NSFP dicatat", nsfp > 0)
    cek("daftar NSFP terisi", len(P.daftar_nsfp(cid, 2026)) == 1)
    try:
        P.tambah_nsfp(cid, 2026, "010.000-26.00000020",
                      "010.000-26.00000010")
        cek("rentang terbalik ditolak", False)
    except ValueError:
        cek("rentang terbalik ditolak", True)

    print("\n=== 2. Faktur Pajak ===")
    fp = P.buat_faktur_pajak(cid, "keluaran", "2026-03-05", "PT Pelanggan",
                             10_000_000, lawan_npwp="02.111.222.3-444.000",
                             invoice_id=None)
    cek("faktur keluaran dibuat", fp > 0)
    baris = P.daftar_faktur_pajak(cid, "keluaran", 2026)
    cek("nomor seri terisi otomatis", bool(baris[0]["nomor_seri"]),
        baris[0]["nomor_seri"] if baris else "")
    cek("PPN terhitung 11%", baris[0]["ppn"] == 1_100_000,
        f"ppn={baris[0]['ppn']:,}")

    fp2 = P.buat_faktur_pajak(cid, "masukan", "2026-03-08", "PT Pemasok",
                              5_000_000, lawan_npwp="03.111.222.3-444.000")
    cek("faktur masukan dibuat", fp2 > 0)

    rekap = P.rekap_faktur_pajak(cid, 2026)
    cek("rekap keluaran benar", rekap["keluaran"]["ppn"] == 1_100_000,
        f"ppn={rekap['keluaran']['ppn']:,}")
    cek("rekap masukan benar", rekap["masukan"]["ppn"] == 550_000,
        f"ppn={rekap['masukan']['ppn']:,}")
    cek("selisih PPN benar", rekap["selisih_ppn"] == 550_000,
        f"selisih={rekap['selisih_ppn']:,}")

    print("\n=== 3. Uang Muka / Panjar ===")
    from akuntansi_id import modules_sales as S
    brg = M.buat_produk(cid, "Barang Uji", tipe="barang", satuan="unit",
                        harga_beli=1_000_000, harga_jual=1_500_000,
                        qty_awal=50, tanggal_stok_awal="2026-01-01")
    inv = S.buat_invoice(cid, "2026-03-05", [
        {"product_id": brg, "qty": 20, "harga_satuan": 1_500_000}],
        partner_id=pel, jenis_ppn="PPN Keluaran")

    dp = P.buat_uang_muka(cid, "diterima", "2026-03-01", 50_000_000,
                          partner_id=pel, akun_kas="1001")
    cek("uang muka diterima dicatat", dp > 0)
    daftar = P.daftar_uang_muka(cid, "diterima")
    cek("sisa uang muka penuh", daftar[0]["terpakai"] == 0)

    pakai = P.pakai_uang_muka(dp, "2026-03-05", 20_000_000,
                              invoice_id=inv)
    cek("pemakaian uang muka dicatat", pakai > 0)
    daftar2 = P.daftar_uang_muka(cid, "diterima")
    cek("terpakai bertambah", daftar2[0]["terpakai"] == 20_000_000,
        f"terpakai={daftar2[0]['terpakai']:,}")

    try:
        P.pakai_uang_muka(dp, "2026-03-06", 99_000_000)
        cek("pemakaian melebihi sisa ditolak", False)
    except ValueError:
        cek("pemakaian melebihi sisa ditolak", True)

    dp2 = P.buat_uang_muka(cid, "dibayar", "2026-03-02", 30_000_000,
                           akun_kas="1001")
    cek("uang muka dibayar dicatat", dp2 > 0)

    print("\n=== 4. Bea Meterai ===")
    mt = P.catat_meterai(cid, "2026-03-10", "Kontrak Sewa", 50_000_000)
    cek("meterai dicatat", mt > 0)
    daftar_mt = P.daftar_meterai(cid, 2026)
    cek("total meterai Rp10.000", daftar_mt[0]["total"] == 10_000,
        f"total={daftar_mt[0]['total']:,}")
    try:
        P.catat_meterai(cid, "2026-03-10", "Nota Kecil", 200_000)
        cek("dokumen kecil ditolak", False)
    except ValueError:
        cek("dokumen kecil ditolak", True)

    print("\n=== 5. Pajak Daerah (PBJT) ===")
    pd = P.catat_pajak_daerah(cid, "makanan_minuman", "2026-03-12", 5_000_000)
    cek("pajak daerah dicatat", pd > 0)
    daftar_pd = P.daftar_pajak_daerah(cid, 2026)
    cek("PBJT 10% dari 5jt", daftar_pd[0]["pajak"] == 500_000,
        f"pajak={daftar_pd[0]['pajak']:,}")

    print("\n=== 6. Kurs Mata Uang Asing ===")
    P.set_kurs(cid, "USD", "2026-03-01", 16_000)
    cek("kurs disimpan", P.kurs_terakhir(cid, "USD", "2026-03-05") == 16_000)
    P.set_kurs(cid, "USD", "2026-03-10", 16_500)
    cek("kurs terbaru dipakai", P.kurs_terakhir(cid, "USD", "2026-03-15") == 16_500)
    cek("kurs IDR selalu 1", P.kurs_terakhir(cid, "IDR") == 1)
    try:
        P.set_kurs(cid, "XXX", "2026-03-01", 1000)
        cek("mata uang tak dikenal ditolak", False)
    except ValueError:
        cek("mata uang tak dikenal ditolak", True)

    print("\n=== 7. PPh Pasal 15 ===")
    p15 = P.catat_pph15(cid, "pelayaran_dalam", "2026-03-15", 1_000_000_000)
    cek("PPh 15 dicatat", p15 > 0)
    daftar_15 = P.daftar_pph15(cid, 2026)
    cek("PPh 15 = 1,35% x 1 M", daftar_15[0]["pph"] == 13_500_000,
        f"pph={daftar_15[0]['pph']:,}")

    print("\n=== 8. Jurnal Balik ===")
    # buat jurnal akrual dulu
    entry = acc.simpan_jurnal(cid, "2026-03-31", "AKR-001",
                              "Akrual beban listrik",
                              [{"kode_akun": "6003", "debit": 5_000_000,
                                "kredit": 0, "catatan": "Akrual"},
                               {"kode_akun": "2013", "debit": 0,
                                "kredit": 5_000_000, "catatan": "Utang akrual"}],
                              sumber="penyesuaian")
    jb = P.tandai_jurnal_balik(cid, entry, "2099-01-01", "Balik bulan depan")
    cek("jurnal balik ditandai", jb > 0)
    cek("daftar jurnal balik terisi", len(P.daftar_jurnal_balik(cid)) == 1)

    # tanggal di masa depan: belum dijalankan
    hasil = P.jalankan_jurnal_balik(cid)
    cek("jurnal masa depan dilewati", hasil["dibuat"] == 0 and hasil["dilewati"] == 1,
        f"dibuat={hasil['dibuat']} dilewati={hasil['dilewati']}")

    # tanggal sudah lewat: dijalankan
    P.tandai_jurnal_balik(cid, entry, "2026-04-01", "Balik April")
    hasil2 = P.jalankan_jurnal_balik(cid)
    cek("jurnal balik dijalankan", hasil2["dibuat"] >= 1,
        f"dibuat={hasil2['dibuat']}")

    print("\n=== 9. Neraca tetap seimbang ===")
    nr = acc.neraca(cid, 2026)
    cek("neraca seimbang", nr.seimbang, f"selisih={nr.selisih:,}")
    tb = acc.total_neraca_saldo(cid, 2026)
    cek("neraca saldo seimbang", tb["seimbang"],
        f"debit={tb['debit']:,} kredit={tb['kredit']:,}")

    gagal = [h for h in HASIL if not h[1]]
    print("\n" + "=" * 74)
    if gagal:
        print(f"HASIL: {len(HASIL) - len(gagal)} LULUS, {len(gagal)} GAGAL")
        for nama, _, detail in gagal:
            print(f"   GAGAL: {nama} {detail}")
        return 1
    print(f"HASIL: {len(HASIL)} LULUS, 0 GAGAL")
    return 0


if __name__ == "__main__":
    sys.exit(main())
