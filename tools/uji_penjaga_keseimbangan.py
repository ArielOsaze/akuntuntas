"""
Uji penjaga keseimbangan jurnal di lapisan basis data.

Ide ini datang dari alat di GitHub (mkmbhs/ledger) yang menaruh penjaga
keseimbangan di tingkat basis data, sehingga berlaku untuk semua jalur
penulisan, bukan hanya jalur yang melewati kode aplikasi.

Sebelum penjaga ini ada, jurnal tidak seimbang dapat masuk lewat SQL
langsung dan membuat neraca tidak seimbang tanpa ada yang menyadari.

Yang diperiksa:

  1. Jalur biasa (lewat aplikasi) tetap menolak jurnal tidak seimbang.
  2. SQL langsung juga ditolak, padahal sebelumnya berhasil.
  3. Jurnal yang sah tetap dapat disimpan, termasuk yang barisnya lebih
     dari dua dan yang jumlahnya besar.
  4. Jurnal dua baris sederhana tetap dapat disimpan.
  5. Menghapus baris jurnal sehingga bukti itu tidak seimbang ditolak.
  6. Mengubah jurnal menjadi tidak seimbang ditolak.
  7. Pesan kesalahannya menyebut nomor bukti yang bermasalah.
  8. Seluruh rangkaian transaksi normal tetap berjalan tanpa gangguan.

Cara pakai:
    python tools/uji_penjaga_keseimbangan.py
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "src"))

FOLDER = Path(tempfile.mkdtemp(prefix="akuntuntas_penjaga_"))
os.environ["LOCALAPPDATA"] = str(FOLDER)

from akuntansi_id import db, modules, services  # noqa: E402
from akuntansi_id.core import accounting as acc  # noqa: E402


class Pemeriksa:
    def __init__(self):
        self.lulus = 0
        self.gagal = 0
        self.temuan: list[str] = []

    def cek(self, nama: str, syarat: bool, catatan: str = ""):
        if syarat:
            self.lulus += 1
            print(f"  [BENAR] {nama}")
        else:
            self.gagal += 1
            self.temuan.append(nama)
            print(f"  [SALAH] {nama}")
            if catatan:
                print(f"          {catatan}")

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


def tulis_langsung(cid: int, no_bukti: str, debit: int, kredit: int) -> str:
    """
    Tulis jurnal langsung ke tabel, melewati seluruh pemeriksaan aplikasi.

    Inilah cara yang dipakai alat lain atau perbaikan data manual, dan
    inilah celah yang harus ditutup oleh penjaga di lapisan basis data.
    """
    try:
        with db.tx() as conn:
            cur = conn.execute(
                """INSERT INTO journal_entries(company_id, tanggal, no_bukti,
                   keterangan, sumber) VALUES(?,?,?,?,'uji')""",
                (cid, "2026-01-01", no_bukti, "Uji penjaga"))
            eid = cur.lastrowid
            conn.execute("""INSERT INTO journal_lines(company_id, entry_id,
                            kode_akun, debit, kredit) VALUES(?,?,?,?,0)""",
                         (cid, eid, "1001", debit))
            conn.execute("""INSERT INTO journal_lines(company_id, entry_id,
                            kode_akun, debit, kredit) VALUES(?,?,?,0,?)""",
                         (cid, eid, "4001", kredit))
        return ""
    except Exception as e:
        return f"{type(e).__name__}: {e}"


def main() -> int:
    p = Pemeriksa()
    print("=" * 76)
    print("  UJI PENJAGA KESEIMBANGAN JURNAL DI LAPISAN BASIS DATA")
    print("=" * 76)
    print()

    db.init_db()
    b = db.q1("SELECT id FROM companies ORDER BY id LIMIT 1")
    cid = b["id"] if b else services.create_company("PT Penjaga", bentuk="pt")

    # ------------------------------------------------------------------
    print("[1. Jalur biasa tetap menolak jurnal tidak seimbang]")
    try:
        services.simpan_jurnal_manual(
            cid, "2026-01-05", "APP-001", "Tidak seimbang",
            [{"kode_akun": "1001", "debit": 10_000_000, "kredit": 0, "keterangan": ""},
             {"kode_akun": "4001", "debit": 0, "kredit": 7_000_000, "keterangan": ""}])
        p.cek("jalur aplikasi menolak jurnal tidak seimbang", False,
              "jurnal tidak seimbang diterima")
    except ValueError:
        p.cek("jalur aplikasi menolak jurnal tidak seimbang", True)
    except Exception as e:
        p.cek("jalur aplikasi menolak jurnal tidak seimbang", False,
              f"{type(e).__name__}: {e}")

    ada = db.scalar("SELECT COUNT(*) FROM journal_entries WHERE company_id=? AND no_bukti='APP-001'",
                    (cid,))
    p.cek("jurnal yang ditolak tidak meninggalkan sisa", int(ada) == 0,
          f"jumlah baris: {ada}")
    print()

    # ------------------------------------------------------------------
    print("[2. SQL langsung juga ditolak (celah yang ditutup)]")
    pesan = tulis_langsung(cid, "RAW-001", 10_000_000, 7_000_000)
    p.cek("SQL langsung ditolak", bool(pesan), "tidak ada penolakan")

    ada = db.scalar("SELECT COUNT(*) FROM journal_entries WHERE company_id=? AND no_bukti='RAW-001'",
                    (cid,))
    p.cek("jurnal tidak seimbang tidak meninggalkan sisa", int(ada) == 0,
          f"jumlah baris: {ada}")

    # Neraca harus tetap seimbang.
    ner = acc.neraca(cid, 2026)
    harta = getattr(ner, "total_aset", 0)
    um = getattr(ner, "total_liabilitas", 0) + getattr(ner, "total_ekuitas", 0)
    p.cek("neraca tetap seimbang setelah percobaan", harta == um,
          f"harta {harta:,} vs utang+modal {um:,}")
    print()

    # ------------------------------------------------------------------
    print("[3. Jurnal sah tetap dapat disimpan]")
    # Dua baris sederhana.
    try:
        e1 = services.simpan_jurnal_manual(
            cid, "2026-01-10", "SAH-001", "Dua baris",
            [{"kode_akun": "1001", "debit": 5_000_000, "kredit": 0, "keterangan": ""},
             {"kode_akun": "4001", "debit": 0, "kredit": 5_000_000, "keterangan": ""}])
        p.cek("jurnal dua baris tersimpan", e1 is not None)
    except Exception as e:
        p.cek("jurnal dua baris tersimpan", False, f"{type(e).__name__}: {e}")

    # Tiga baris (PPN).
    try:
        e2 = services.simpan_jurnal_manual(
            cid, "2026-01-11", "SAH-002", "Tiga baris",
            [{"kode_akun": "1001", "debit": 11_100_000, "kredit": 0, "keterangan": ""},
             {"kode_akun": "4001", "debit": 0, "kredit": 10_000_000, "keterangan": ""},
             {"kode_akun": "2013", "debit": 0, "kredit": 1_100_000, "keterangan": ""}])
        p.cek("jurnal tiga baris tersimpan", e2 is not None)
    except Exception as e:
        p.cek("jurnal tiga baris tersimpan", False, f"{type(e).__name__}: {e}")

    # Lima baris.
    try:
        e3 = services.simpan_jurnal_manual(
            cid, "2026-01-12", "SAH-003", "Lima baris",
            [{"kode_akun": "1001", "debit": 10_000_000, "kredit": 0, "keterangan": ""},
             {"kode_akun": "1101", "debit": 5_000_000, "kredit": 0, "keterangan": ""},
             {"kode_akun": "4001", "debit": 0, "kredit": 8_000_000, "keterangan": ""},
             {"kode_akun": "4002", "debit": 0, "kredit": 4_000_000, "keterangan": ""},
             {"kode_akun": "2013", "debit": 0, "kredit": 3_000_000, "keterangan": ""}])
        p.cek("jurnal lima baris tersimpan", e3 is not None)
    except Exception as e:
        p.cek("jurnal lima baris tersimpan", False, f"{type(e).__name__}: {e}")

    # Jumlah besar.
    try:
        e4 = services.simpan_jurnal_manual(
            cid, "2026-01-13", "SAH-004", "Nilai besar",
            [{"kode_akun": "1001", "debit": 9_999_999_999, "kredit": 0, "keterangan": ""},
             {"kode_akun": "3001", "debit": 0, "kredit": 9_999_999_999, "keterangan": ""}])
        p.cek("jurnal bernilai besar tersimpan", e4 is not None)
    except Exception as e:
        p.cek("jurnal bernilai besar tersimpan", False, f"{type(e).__name__}: {e}")
    print()

    # ------------------------------------------------------------------
    print("[4. SQL langsung untuk jurnal yang SAH tetap diterima]")
    pesan2 = tulis_langsung(cid, "RAW-002", 3_000_000, 3_000_000)
    p.cek("SQL langsung dengan jurnal seimbang diterima", not pesan2,
          f"ditolak padahal seimbang: {pesan2}")
    print()

    # ------------------------------------------------------------------
    print("[5. Menghapus baris sehingga tidak seimbang ditolak]")
    baris = db.q1("""SELECT id FROM journal_lines WHERE entry_id=?
                     ORDER BY id LIMIT 1""", (e1,))
    if baris:
        try:
            with db.tx() as conn:
                conn.execute("DELETE FROM journal_lines WHERE id=?",
                             (baris["id"],))
            p.cek("menghapus baris hingga tidak seimbang ditolak", False,
                  "penghapusan diterima")
        except ValueError:
            p.cek("menghapus baris hingga tidak seimbang ditolak", True)
        except Exception as e:
            p.cek("menghapus baris hingga tidak seimbang ditolak", False,
                  f"{type(e).__name__}: {e}")

        # Jurnal aslinya harus tetap utuh.
        utuh = db.scalar("SELECT COUNT(*) FROM journal_lines WHERE entry_id=?",
                         (e1,))
        p.cek("jurnal asli tetap utuh setelah penolakan", int(utuh) == 2,
              f"jumlah baris sekarang: {utuh}")
    print()

    # ------------------------------------------------------------------
    print("[6. Mengubah nilai menjadi tidak seimbang ditolak]")
    baris2 = db.q1("""SELECT id FROM journal_lines WHERE entry_id=?
                      ORDER BY id LIMIT 1""", (e2,))
    if baris2:
        try:
            with db.tx() as conn:
                conn.execute("UPDATE journal_lines SET debit=debit+1_000_000 WHERE id=?",
                             (baris2["id"],))
            p.cek("mengubah nilai hingga tidak seimbang ditolak", False,
                  "perubahan diterima")
        except ValueError:
            p.cek("mengubah nilai hingga tidak seimbang ditolak", True)
        except Exception as e:
            p.cek("mengubah nilai hingga tidak seimbang ditolak", False,
                  f"{type(e).__name__}: {e}")
    print()

    # ------------------------------------------------------------------
    print("[7. Pesan kesalahan menyebut nomor buktinya]")
    pesan3 = tulis_langsung(cid, "RAW-003", 1_000_000, 500_000)
    p.cek("pesan menyebut nomor bukti", "RAW-003" in pesan3,
          f"pesan: {pesan3[:120]}")
    p.cek("pesan menyebut selisihnya", "500" in pesan3 or "selisih" in pesan3.lower(),
          f"pesan: {pesan3[:120]}")
    print()

    # ------------------------------------------------------------------
    print("[8. Rangkaian transaksi normal tetap berjalan]")
    # Penjualan, pembelian, payroll: semuanya membuat jurnal.
    pid = modules.buat_produk(cid, "Barang Uji", satuan="pcs",
                              harga_beli=100_000, harga_jual=150_000)
    modules.stok_masuk(cid, pid, 50, 100_000, "2026-02-01")

    from akuntansi_id import modules_sales as S
    pl = modules.buat_mitra(cid, "Pelanggan Uji", "customer")
    try:
        inv = S.buat_invoice(cid, "2026-02-10",
                             [{"product_id": pid, "qty": 5, "harga_satuan": 150_000}],
                             partner_id=pl, jenis_ppn="Non-PKP/Tidak Dipungut",
                             username="uji")
        p.cek("invoice beserta jurnalnya berhasil dibuat", inv is not None)
    except Exception as e:
        p.cek("invoice beserta jurnalnya berhasil dibuat", False,
              f"{type(e).__name__}: {e}")

    try:
        services.simpan_karyawan(cid, "Karyawan Uji", 6_000_000,
                                 status_ptkp="TK/0", tunjangan_tetap=500_000)
        hasil = services.hitung_payroll_bulanan(cid, "2026-02", posting=True)
        p.cek("penggajian beserta jurnalnya berhasil", bool(hasil))
    except Exception as e:
        p.cek("penggajian beserta jurnalnya berhasil", False,
              f"{type(e).__name__}: {e}")

    try:
        services.simpan_pembelian(cid, "2026-02-15", "PB-001", "Pemasok Uji",
                                  10_000_000, jenis="Beban", akun_beban="6006",
                                  dibayar=True, tanggal_bayar="2026-02-15")
        p.cek("pembelian beserta jurnalnya berhasil", True)
    except Exception as e:
        p.cek("pembelian beserta jurnalnya berhasil", False,
              f"{type(e).__name__}: {e}")

    # Semua jurnal seimbang.
    tidak_seimbang = db.q("""
        SELECT je.id, je.no_bukti,
               COALESCE(SUM(jl.debit),0) AS d, COALESCE(SUM(jl.kredit),0) AS k
        FROM journal_entries je
        LEFT JOIN journal_lines jl ON jl.entry_id = je.id
        WHERE je.company_id = ?
        GROUP BY je.id HAVING d <> k""", (cid,))
    p.cek("seluruh jurnal di basis data seimbang", not tidak_seimbang,
          f"{len(tidak_seimbang)} tidak seimbang")

    # Neraca seimbang.
    ner2 = acc.neraca(cid, 2026)
    h2 = getattr(ner2, "total_aset", 0)
    um2 = getattr(ner2, "total_liabilitas", 0) + getattr(ner2, "total_ekuitas", 0)
    p.cek("neraca seimbang setelah seluruh transaksi", h2 == um2,
          f"harta {h2:,} vs utang+modal {um2:,}")
    print()

    # ------------------------------------------------------------------
    print("[9. Tutup buku dan jurnal penyesuaian tetap berjalan]")
    try:
        penutup = services.buat_jurnal_penutup(cid, 2026)
        p.cek("jurnal penutup berhasil dibuat", penutup is not None)
        if penutup:
            baris_p = db.q("SELECT * FROM journal_lines WHERE entry_id=?",
                           (penutup,))
            d = sum(int(b["debit"]) for b in baris_p)
            k = sum(int(b["kredit"]) for b in baris_p)
            p.cek("jurnal penutup seimbang", d == k,
                  f"debit {d:,} vs kredit {k:,}")
    except Exception as e:
        p.cek("jurnal penutup berhasil dibuat", False,
              f"{type(e).__name__}: {e}")
    print()

    # ------------------------------------------------------------------
    print("[10. Hapus jurnal sah tetap dapat dilakukan]")
    try:
        services.hapus_jurnal(e1)
        sisa = db.scalar("SELECT COUNT(*) FROM journal_entries WHERE id=?", (e1,))
        p.cek("menghapus jurnal sah berhasil", int(sisa) == 0,
              f"masih ada: {sisa}")
    except Exception as e:
        p.cek("menghapus jurnal sah berhasil", False,
              f"{type(e).__name__}: {e}")
    print()

    return p.ringkas()


if __name__ == "__main__":
    try:
        kode = main()
    finally:
        shutil.rmtree(FOLDER, ignore_errors=True)
    sys.exit(kode)
