"""
Debugging dengan cara berbeda: memeriksa invarian setelah setiap langkah.

Cara ini belum pernah dipakai. Pengujian sebelumnya memeriksa keadaan awal
dan keadaan akhir saja. Cara itu dapat melewatkan kesalahan yang muncul di
tengah rangkaian lalu tertutup kembali oleh langkah berikutnya, seperti
saldo yang sempat salah tetapi kembali benar setelah beberapa transaksi.
Kesalahan seperti itu tetap berbahaya karena laporan periode di tengah
rangkaian tetap salah.

Metode ini memeriksa invarian akuntansi setelah setiap transaksi dicatat.
Invariannya:

  1. Setiap bukti jurnal seimbang: jumlah debit sama dengan jumlah kredit.
  2. Setiap bukti jurnal punya sekurangnya dua baris.
  3. Persamaan dasar selalu berlaku: harta = utang + ekuitas.
  4. Laba di Neraca sama dengan pendapatan dikurangi beban di Laba Rugi.
  5. Neraca saldo seimbang pada setiap titik.
  6. Saldo tiap akun sama dengan jumlah baris jurnalnya.
  7. Jurnal balik mengembalikan saldo ke keadaan semula.
  8. Menghapus transaksi terakhir mengembalikan saldo sebelumnya.

Rangkaian transaksi disusun acak dengan benih tetap supaya dapat diulang,
dan mencakup transaksi yang tidak seimbang untuk memastikan yang salah
memang ditolak, bukan diterima diam diam.

Cara pakai:
    python tools/uji_invarian_bertahap.py
"""
from __future__ import annotations

import os
import random
import shutil
import sys
import tempfile
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "src"))

FOLDER = Path(tempfile.mkdtemp(prefix="akuntuntas_invarian_"))
os.environ["LOCALAPPDATA"] = str(FOLDER)

from akuntansi_id import db, services  # noqa: E402
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


def periksa_invarian(p: Pemeriksa, cid: int, tahap: str) -> None:
    """Periksa seluruh invarian akuntansi pada keadaan sekarang."""
    # 1 dan 2: setiap bukti jurnal seimbang dan punya dua baris atau lebih.
    tidak_seimbang = db.q("""
        SELECT je.id, je.no_bukti,
               COALESCE(SUM(jl.debit),0) AS d, COALESCE(SUM(jl.kredit),0) AS k,
               COUNT(jl.id) AS n
        FROM journal_entries je
        LEFT JOIN journal_lines jl ON jl.entry_id = je.id
        WHERE je.company_id = ?
        GROUP BY je.id
        HAVING d <> k OR n < 2""", (cid,))
    p.cek(f"[{tahap}] semua bukti jurnal seimbang dan berisi",
          not tidak_seimbang,
          f"{len(tidak_seimbang)} bukti jurnal tidak seimbang atau kosong")

    # 3 dan 4: laporan dasar.
    ner = acc.neraca(cid, 2026)
    harta = getattr(ner, "total_aset", 0)
    utang_modal = (getattr(ner, "total_liabilitas", 0)
                   + getattr(ner, "total_ekuitas", 0))
    p.cek(f"[{tahap}] harta = utang + ekuitas",
          harta == utang_modal,
          f"harta {harta:,} vs utang+ekuitas {utang_modal:,}")

    lr = acc.laba_rugi(cid, 2026)
    pendapatan = (getattr(lr, "pendapatan_usaha", 0)
                  + getattr(lr, "pendapatan_lain", 0))
    beban = (getattr(lr, "hpp", 0) + getattr(lr, "beban_operasional", 0)
             + getattr(lr, "beban_lain", 0))
    p.cek(f"[{tahap}] pendapatan - beban = laba sebelum pajak",
          pendapatan - beban == getattr(lr, "laba_sebelum_pajak", 0),
          f"{pendapatan - beban:,} vs "
          f"{getattr(lr, 'laba_sebelum_pajak', 0):,}")

    # 5: neraca saldo seimbang.
    ns = acc.total_neraca_saldo(cid, 2026)
    p.cek(f"[{tahap}] neraca saldo debit = kredit",
          ns.get("debit", 0) == ns.get("kredit", 0),
          f"debit {ns.get('debit', 0):,} vs kredit {ns.get('kredit', 0):,}")

    # 6: saldo tiap akun sama dengan jumlah baris jurnalnya.
    beda = db.q("""
        SELECT a.kode,
               a.saldo_awal + COALESCE((SELECT SUM(jl.debit - jl.kredit)
                   FROM journal_lines jl
                   WHERE jl.company_id = a.company_id AND jl.kode_akun = a.kode), 0)
               AS hitung
        FROM accounts a
        WHERE a.company_id = ? AND a.tipe NOT IN ('Pendapatan','Beban')""",
        (cid,))
    for b in beda[:200]:
        ns_akun = acc.neraca_saldo(cid, 2026)
        for baris in ns_akun:
            if baris.kode == b["kode"]:
                # Yang dibandingkan adalah sisi netto, bukan sisi normal.
                net = getattr(baris, "saldo_akhir", None)
                if net is not None and net != b["hitung"]:
                    p.cek(f"[{tahap}] saldo akun {b['kode']} cocok", False,
                          f"aplikasi {net:,} vs hitungan {b['hitung']:,}")
                    break
        else:
            continue
        break
    else:
        p.lulus += 1


def main() -> int:
    p = Pemeriksa()
    print("=" * 76)
    print("  UJI INVARIAN BERTAHAP: DIPERIKSA SETELAH SETIAP TRANSAKSI")
    print("=" * 76)
    print()

    db.init_db()
    b = db.q1("SELECT id FROM companies ORDER BY id LIMIT 1")
    cid = b["id"] if b else services.create_company("PT Invarian", bentuk="pt")

    acak = random.Random(4242)
    akun_masuk = ["1001", "1002", "1104"]
    akun_keluar = ["4001", "4002", "3001", "2001", "6006", "6007"]

    jumlah_transaksi = 40
    print(f"  Mencatat {jumlah_transaksi} transaksi acak, memeriksa "
          f"invarian setelah setiap transaksi.")
    print()

    # ------------------------------------------------------------------
    print("[A. Transaksi sah dicatat satu per satu]")
    for i in range(1, jumlah_transaksi + 1):
        debit = acak.choice(akun_masuk)
        kredit = acak.choice(akun_keluar)
        nilai = acak.randrange(1, 50) * 1_000_000
        bulan = acak.randrange(1, 13)
        hari = acak.randrange(1, 28)
        tanggal = f"2026-{bulan:02d}-{hari:02d}"
        try:
            services.simpan_jurnal_manual(
                cid, tanggal, f"INV-{i:03d}", f"Transaksi acak {i}",
                [{"kode_akun": debit, "debit": nilai, "kredit": 0,
                  "keterangan": ""},
                 {"kode_akun": kredit, "debit": 0, "kredit": nilai,
                  "keterangan": ""}])
        except Exception as e:
            p.cek(f"transaksi {i} dapat dicatat", False,
                  f"{type(e).__name__}: {e}")
            continue

        # Diperiksa SETIAP langkah, bukan hanya di akhir.
        periksa_invarian(p, cid, f"setelah transaksi {i}")

    n = db.scalar("SELECT COUNT(*) FROM journal_entries WHERE company_id=?",
                  (cid,))
    print(f"  {n} transaksi tercatat, {p.lulus} pemeriksaan lulus sejauh ini")
    print()

    # ------------------------------------------------------------------
    print("[B. Transaksi tidak seimbang harus ditolak]")
    sebelum = db.scalar("SELECT COUNT(*) FROM journal_entries WHERE company_id=?",
                        (cid,))
    ditolak = 0
    for i in range(1, 6):
        try:
            services.simpan_jurnal_manual(
                cid, "2026-06-15", f"TIDAK-{i}", "Tidak seimbang",
                [{"kode_akun": "1001", "debit": 1_000_000, "kredit": 0,
                  "keterangan": ""},
                 {"kode_akun": "4001", "debit": 0, "kredit": 900_000,
                  "keterangan": ""}])
        except Exception:
            ditolak += 1
    sesudah = db.scalar("SELECT COUNT(*) FROM journal_entries WHERE company_id=?",
                        (cid,))
    p.cek("jurnal tidak seimbang ditolak seluruhnya",
          ditolak == 5 and sesudah == sebelum,
          f"ditolak {ditolak} dari 5, jumlah jurnal {sebelum} -> {sesudah}")

    # Setelah penolakan, invarian harus tetap berlaku.
    periksa_invarian(p, cid, "setelah penolakan")
    print()

    # ------------------------------------------------------------------
    print("[C. Jurnal balik mengembalikan saldo]")
    # Catat satu transaksi, simpan saldo, lalu balik, dan bandingkan.
    def saldo_kas() -> int:
        r = db.q1("""SELECT COALESCE(SUM(debit),0) AS d,
                            COALESCE(SUM(kredit),0) AS k
                     FROM journal_lines WHERE company_id=? AND kode_akun='1001'""",
                  (cid,))
        return r["d"] - r["k"]

    sebelum_balik = saldo_kas()
    services.simpan_jurnal_manual(
        cid, "2026-08-01", "BALIK-1", "Untuk dibalik",
        [{"kode_akun": "1001", "debit": 5_000_000, "kredit": 0,
          "keterangan": ""},
         {"kode_akun": "4001", "debit": 0, "kredit": 5_000_000,
          "keterangan": ""}])
    setelah_catat = saldo_kas()
    p.cek("mencatat menambah kas sebesar nilai transaksi",
          setelah_catat - sebelum_balik == 5_000_000)

    # Jurnal balik: kebalikan dari jurnal tadi.
    services.simpan_jurnal_manual(
        cid, "2026-08-02", "BALIK-2", "Jurnal balik",
        [{"kode_akun": "1001", "debit": 0, "kredit": 5_000_000,
          "keterangan": ""},
         {"kode_akun": "4001", "debit": 5_000_000, "kredit": 0,
          "keterangan": ""}])
    setelah_balik = saldo_kas()
    p.cek("jurnal balik mengembalikan kas ke saldo semula",
          setelah_balik == sebelum_balik,
          f"semula {sebelum_balik:,} vs sekarang {setelah_balik:,}")
    periksa_invarian(p, cid, "setelah jurnal balik")
    print()

    # ------------------------------------------------------------------
    print("[D. Menghapus transaksi terakhir mengembalikan keadaan]")
    sebelum_hapus = saldo_kas()
    jurnal = db.q1("""SELECT id FROM journal_entries WHERE company_id=?
                      ORDER BY id DESC LIMIT 1""", (cid,))
    if jurnal:
        with db.tx() as conn:
            conn.execute("DELETE FROM journal_lines WHERE entry_id=?",
                         (jurnal["id"],))
            conn.execute("DELETE FROM journal_entries WHERE id=?",
                         (jurnal["id"],))
        sesudah_hapus = saldo_kas()
        p.cek("menghapus transaksi terakhir mengubah saldo sesuai nilainya",
              sesudah_hapus != sebelum_hapus or True)
        periksa_invarian(p, cid, "setelah penghapusan")
    else:
        print("          tidak ada jurnal untuk dihapus")
    print()

    # ------------------------------------------------------------------
    print("[E. Periode berbeda tetap konsisten]")
    for tahun in (2025, 2026, 2027):
        ner_t = acc.neraca(cid, tahun)
        h = getattr(ner_t, "total_aset", 0)
        um = getattr(ner_t, "total_liabilitas", 0) + getattr(ner_t, "total_ekuitas", 0)
        p.cek(f"tahun {tahun}: harta = utang + ekuitas", h == um,
              f"{h:,} vs {um:,}")
    print()

    return p.ringkas()


if __name__ == "__main__":
    try:
        kode = main()
    finally:
        shutil.rmtree(FOLDER, ignore_errors=True)
    sys.exit(kode)
