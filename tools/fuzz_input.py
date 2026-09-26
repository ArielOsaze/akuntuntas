"""
Debugging dengan cara berbeda: menyerang aplikasi dengan input acak.

Cara ini berbeda dari pengujian sebelumnya. Pengujian sebelumnya memakai
nilai yang sudah dipikirkan: angka bulat, tanggal wajar, nama normal.
Cara ini justru mengirim nilai yang tidak masuk akal dan berbahaya:
teks kosong, angka negatif, angka sangat besar, tanggal ngawur, karakter
khusus, teks yang sangat panjang, dan nilai yang bukan tipe yang diminta.

Yang dicari bukan hasil yang benar, melainkan dua hal:
  1. Galat yang tidak tertangani (aplikasi berhenti atau menampilkan jejak
     galat ke pengguna).
  2. Data rusak yang tetap tersimpan, misalnya nilai negatif yang lolos,
     teks kosong yang masuk, atau jurnal yang tidak seimbang.

Cara pakai:
    python tools/fuzz_input.py
"""
from __future__ import annotations

import os
import random
import shutil
import sys
import tempfile
import traceback
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "src"))

FOLDER = Path(tempfile.mkdtemp(prefix="akuntuntas_fuzz_"))
os.environ["LOCALAPPDATA"] = str(FOLDER)

from akuntansi_id import db, services  # noqa: E402

# Benih tetap supaya hasilnya dapat diulang.
ACAK = random.Random(20260101)

# Nilai nilai yang dipakai untuk menyerang. Sengaja memuat hal hal yang
# tidak masuk akal, karena di situlah kesalahan biasanya muncul.
TEKS = [
    "", " ", "   ", "\t", "\n", "\r\n",
    "a", "A" * 500, "x" * 5000,
    "0", "-1", "1e10", "NaN", "Infinity", "None", "null", "true",
    "<script>alert(1)</script>", "'; DROP TABLE users; --",
    "../../../etc/passwd", "%s%s%s", "{0}", "{}", "${x}", "`id`",
    "\x00", "\ufeff", "日本語", "émoji 😀", "阿拉伯语",
    "Rp 1.000.000", "1,000,000.50", "1.000,50", "-0", "+5",
    "1e308", "9" * 30, "0x10", "0b101", "０１２３", "  spasi  ",
]

ANGKA = [
    0, 1, -1, -1_000_000, 2 ** 31 - 1, 2 ** 31, 2 ** 63 - 1,
    10 ** 15, 10 ** 18, -2 ** 63, 999_999_999_999,
]

TANGGAL = [
    "", " ", "bukan tanggal", "2026", "2026-13-45", "2026-02-30",
    "0000-00-00", "9999-12-31", "1900-01-01", "2099-12-31",
    "2026-01-01T00:00:00Z", "01/01/2026", "1 Januari 2026",
    "2026-1-1", "' OR 1=1 --", "2026-01-01; DROP TABLE",
]


class Pencatat:
    def __init__(self):
        self.dicoba = 0
        self.galat = 0
        self.diterima_aneh = 0
        self.rusak = 0
        self.temuan: list[str] = []

    def catat_galat(self, nama: str, galat: Exception):
        """
        Galat tak terduga yang lolos sampai ke pemanggil.

        Galat jenis ValueError dan TypeError dari pemeriksaan masukan masih
        wajar: aplikasi memang menolak nilai yang salah. Yang tidak wajar
        adalah galat lain, misalnya KeyError, AttributeError, IndexError,
        atau OperationalError, karena itu menandakan ada yang terlewat.
        """
        if isinstance(galat, (ValueError, TypeError)):
            return  # penolakan yang wajar
        self.galat += 1
        ringkas = f"{nama}: {type(galat).__name__}: {str(galat)[:90]}"
        if ringkas not in self.temuan:
            self.temuan.append(ringkas)

    def catat_rusak(self, nama: str, keterangan: str):
        self.rusak += 1
        pesan = f"{nama}: {keterangan}"
        if pesan not in self.temuan:
            self.temuan.append(pesan)

    def ringkas(self) -> int:
        print()
        print("=" * 76)
        print(f"  percobaan            : {self.dicoba}")
        print(f"  galat tak tertangani : {self.galat}")
        print(f"  data rusak tersimpan : {self.rusak}")
        print("=" * 76)
        if self.temuan:
            print()
            print("  TEMUAN:")
            for t in self.temuan[:30]:
                print(f"    - {t}")
        else:
            print("  Tidak ada temuan.")
        print("=" * 76)
        return 1 if self.temuan else 0


def teks_acak() -> str:
    return ACAK.choice(TEKS)


def angka_acak() -> int:
    return ACAK.choice(ANGKA)


def tanggal_acak() -> str:
    return ACAK.choice(TANGGAL)


def main() -> int:
    p = Pencatat()
    print("=" * 76)
    print("  FUZZ: MENYERANG APLIKASI DENGAN INPUT ACAK")
    print("=" * 76)
    print()

    db.init_db()
    baris = db.q1("SELECT id FROM companies ORDER BY id LIMIT 1")
    if baris is None:
        cid = services.create_company("PT Fuzz", bentuk="pt")
    else:
        cid = baris["id"]
    print(f"  perusahaan uji: id={cid}")
    print()

    # ==================================================================
    print("[1. Data perusahaan dengan nilai ngawur]")
    for _ in range(60):
        p.dicoba += 1
        try:
            services.create_company(
                teks_acak(), bentuk=ACAK.choice(["pt", "cv", "koperasi",
                                                 "umkm_op", "pt_perorangan",
                                                 "", "xxx", None]),
                npwp=teks_acak(), kota=teks_acak(), nama_pemilik=teks_acak(),
                telepon=teks_acak(), email=teks_acak())
        except Exception as e:
            p.catat_galat("create_company", e)
    print(f"  selesai: {p.galat} galat tak tertangani sejauh ini")
    print()

    # ==================================================================
    print("[2. Akun dengan kode dan nama ngawur]")
    for _ in range(80):
        p.dicoba += 1
        try:
            services.create_account(
                cid, teks_acak(), teks_acak(),
                ACAK.choice(["Aset", "Liabilitas", "Ekuitas", "Pendapatan",
                             "Beban", "", "xxx", None]),
                "", "Kas & Bank", "Debit", "Deductible/Taxable", teks_acak())
        except Exception as e:
            p.catat_galat("create_account", e)

    # Periksa: apakah ada akun dengan kode kosong yang tersimpan?
    kosong = db.scalar(
        "SELECT COUNT(*) FROM accounts WHERE company_id = ? AND (kode = '' "
        "OR kode IS NULL OR nama = '' OR nama IS NULL)", (cid,))
    if kosong:
        p.catat_rusak("create_account", f"{kosong} akun tanpa kode/nama tersimpan")
    print(f"  akun tanpa kode/nama yang lolos: {kosong}")
    print()

    # ==================================================================
    print("[3. Jurnal dengan nilai ngawur]")
    for _ in range(80):
        p.dicoba += 1
        try:
            services.simpan_jurnal_manual(
                cid, tanggal_acak(), teks_acak(), teks_acak(),
                [{"kode_akun": teks_acak(), "debit": angka_acak(),
                  "kredit": 0, "keterangan": teks_acak()},
                 {"kode_akun": "1001", "debit": 0,
                  "kredit": abs(angka_acak()), "keterangan": ""}])
        except Exception as e:
            p.catat_galat("simpan_jurnal_manual", e)

    # Invarian: buku besar harus tetap seimbang, tidak boleh ada nilai
    # negatif, dan tidak boleh ada baris yang debit dan kreditnya nol.
    d = db.q1("""SELECT COALESCE(SUM(debit),0) AS d, COALESCE(SUM(kredit),0) AS k
                 FROM journal_lines WHERE company_id = ?""", (cid,))
    if d["d"] != d["k"]:
        p.catat_rusak("jurnal", f"buku besar tidak seimbang: {d['d']} vs {d['k']}")

    negatif = db.scalar(
        "SELECT COUNT(*) FROM journal_lines WHERE company_id = ? "
        "AND (debit < 0 OR kredit < 0)", (cid,))
    if negatif:
        p.catat_rusak("jurnal", f"{negatif} baris bernilai negatif tersimpan")

    nol = db.scalar(
        "SELECT COUNT(*) FROM journal_lines WHERE company_id = ? "
        "AND debit = 0 AND kredit = 0", (cid,))
    if nol:
        p.catat_rusak("jurnal", f"{nol} baris bernilai nol tersimpan")

    # Akun tidak dikenal tidak boleh tersimpan.
    asing = db.scalar(
        """SELECT COUNT(*) FROM journal_lines jl
           WHERE jl.company_id = ?
             AND jl.kode_akun NOT IN
                 (SELECT kode FROM accounts WHERE company_id = ?)""",
        (cid, cid))
    if asing:
        p.catat_rusak("jurnal", f"{asing} baris memakai akun tidak dikenal")

    # Tanggal harus berformat benar.
    tanggal_aneh = db.scalar(
        """SELECT COUNT(*) FROM journal_entries
           WHERE company_id = ?
             AND (tanggal = '' OR tanggal IS NULL
                  OR tanggal NOT GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]')""",
        (cid,))
    if tanggal_aneh:
        p.catat_rusak("jurnal", f"{tanggal_aneh} entri bertanggal tidak sah")
    print(f"  buku besar seimbang: {d['d'] == d['k']}")
    print(f"  baris negatif      : {negatif}")
    print(f"  baris nol          : {nol}")
    print(f"  akun asing         : {asing}")
    print(f"  tanggal aneh       : {tanggal_aneh}")
    print()

    # ==================================================================
    print("[4. Penjualan dengan nilai ngawur]")
    for _ in range(60):
        p.dicoba += 1
        try:
            services.simpan_penjualan(
                cid, tanggal_acak(), teks_acak(), teks_acak(),
                [{"nama": teks_acak(), "qty": ACAK.choice(ANGKA),
                  "harga": ACAK.choice(ANGKA)}])
        except Exception as e:
            p.catat_galat("simpan_penjualan", e)
    print(f"  selesai: {p.galat} galat tak tertangani sejauh ini")
    print()

    # ==================================================================
    print("[5. Karyawan dengan gaji ngawur]")
    for _ in range(60):
        p.dicoba += 1
        try:
            services.simpan_karyawan(
                cid, teks_acak(), ACAK.choice(ANGKA), jabatan=teks_acak())
        except Exception as e:
            p.catat_galat("simpan_karyawan", e)

    # Gaji tidak boleh negatif.
    gaji_negatif = db.scalar(
        "SELECT COUNT(*) FROM employees WHERE company_id = ? AND gaji_pokok < 0",
        (cid,)) if _ada("employees") else 0
    if gaji_negatif:
        p.catat_rusak("simpan_karyawan", f"{gaji_negatif} karyawan bergaji negatif")
    print(f"  karyawan bergaji negatif: {gaji_negatif}")
    print()

    # ==================================================================
    print("[6. Aset dengan umur dan nilai ngawur]")
    for _ in range(60):
        p.dicoba += 1
        try:
            services.simpan_aset(
                cid, teks_acak(), teks_acak(), tanggal_acak(),
                ACAK.choice(ANGKA), umur_tahun=ACAK.choice(ANGKA),
                residu=ACAK.choice(ANGKA))
        except Exception as e:
            p.catat_galat("simpan_aset", e)
    print(f"  selesai: {p.galat} galat tak tertangani sejauh ini")
    print()

    # ==================================================================
    print("[7. Pajak dengan DPP ngawur]")
    for _ in range(60):
        p.dicoba += 1
        try:
            services.simpan_pajak(
                cid, tanggal_acak(), teks_acak(), ACAK.choice(ANGKA))
        except Exception as e:
            p.catat_galat("simpan_pajak", e)
    print(f"  selesai: {p.galat} galat tak tertangani sejauh ini")
    print()

    # ==================================================================
    print("[8. Perhitungan pajak dengan nilai tepi]")
    from akuntansi_id.core import tax_engine as T

    nilai_tepi = [
        -10 ** 18, -1, 0, 1, 2 ** 31, 2 ** 63 - 1, 10 ** 18,
        10 ** 20, -(10 ** 20),
    ]
    for n in nilai_tepi:
        p.dicoba += 1
        try:
            hasil, _ = T.pph21_progresif(n)
            if hasil < 0:
                p.catat_rusak("pph21_progresif", f"hasil negatif untuk {n}")
        except Exception as e:
            p.catat_galat(f"pph21_progresif({n})", e)

        p.dicoba += 1
        try:
            r = T.hitung_pph_badan(max(0, n), max(0, n))
            if r.pph_terutang < 0:
                p.catat_rusak("hitung_pph_badan", f"hasil negatif untuk {n}")
        except Exception as e:
            p.catat_galat(f"hitung_pph_badan({n})", e)

        p.dicoba += 1
        try:
            r = T.hitung_ppn(max(0, n), "12% DPP Nilai Lain (11/12)")
            if r.ppn < 0:
                p.catat_rusak("hitung_ppn", f"hasil negatif untuk {n}")
        except Exception as e:
            p.catat_galat(f"hitung_ppn({n})", e)
    print(f"  selesai: {p.galat} galat tak tertangani sejauh ini")
    print()

    # ==================================================================
    print("[9. Invarian menyeluruh]")
    # Setiap jurnal harus seimbang, satu per satu.
    tidak_seimbang = db.q(
        """SELECT je.id, je.no_bukti,
                  COALESCE(SUM(jl.debit),0) AS d,
                  COALESCE(SUM(jl.kredit),0) AS k
           FROM journal_entries je
           LEFT JOIN journal_lines jl ON jl.entry_id = je.id
           WHERE je.company_id = ?
           GROUP BY je.id
           HAVING d != k""", (cid,))
    if tidak_seimbang:
        p.catat_rusak("invarian", f"{len(tidak_seimbang)} jurnal tidak seimbang")
    print(f"  jurnal tidak seimbang: {len(tidak_seimbang)}")

    # Setiap jurnal harus punya minimal dua baris.
    terlalu_pendek = db.q(
        """SELECT je.id FROM journal_entries je
           LEFT JOIN journal_lines jl ON jl.entry_id = je.id
           WHERE je.company_id = ?
           GROUP BY je.id HAVING COUNT(jl.id) < 2""", (cid,))
    if terlalu_pendek:
        p.catat_rusak("invarian", f"{len(terlalu_pendek)} jurnal kurang dari 2 baris")
    print(f"  jurnal kurang 2 baris: {len(terlalu_pendek)}")

    # Tidak boleh ada baris jurnal yang menggantung tanpa entri.
    yatim = db.scalar(
        """SELECT COUNT(*) FROM journal_lines jl
           WHERE NOT EXISTS (SELECT 1 FROM journal_entries je
                             WHERE je.id = jl.entry_id)""")
    if yatim:
        p.catat_rusak("invarian", f"{yatim} baris jurnal tanpa entri")
    print(f"  baris jurnal tanpa entri: {yatim}")
    print()

    return p.ringkas()


def _ada(tabel: str) -> bool:
    try:
        db.scalar(f"SELECT COUNT(*) FROM {tabel}")
        return True
    except Exception:
        return False


if __name__ == "__main__":
    try:
        kode = main()
    except Exception:
        traceback.print_exc()
        kode = 1
    finally:
        shutil.rmtree(FOLDER, ignore_errors=True)
    sys.exit(kode)
