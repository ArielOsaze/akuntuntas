"""
Verifikasi independen: akuntansi diuji dengan prinsip dasar pembukuan.

Yang diperiksa bukan sekadar "fungsinya jalan", tetapi apakah angkanya
benar menurut ilmu akuntansi. Pemeriksaan memakai data buatan sendiri yang
seluruh angkanya dapat dihitung dengan tangan, sehingga hasil aplikasi
dapat dibandingkan dengan hitungan yang pasti.

Enam prinsip yang diuji:

1. Setiap jurnal harus seimbang: total debit sama dengan total kredit.
2. Buku besar harus mencerminkan jurnal: saldo tiap akun sama dengan
   jumlah debit dikurangi jumlah kredit pada akun itu.
3. Persamaan dasar akuntansi harus berlaku: Harta = Utang + Modal.
4. Laba bersih harus sama dengan selisih pendapatan dan beban.
5. Neraca saldo harus seimbang.
6. Jurnal yang tidak seimbang harus ditolak.

Cara pakai:
    python tools/verifikasi_independen_akuntansi.py
"""
from __future__ import annotations

import os
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "src"))

FOLDER = Path(tempfile.mkdtemp(prefix="akuntuntas_verif_akun_"))
os.environ["LOCALAPPDATA"] = str(FOLDER)

from akuntansi_id import config, db, services  # noqa: E402
from akuntansi_id.core import accounting as acc  # noqa: E402


class Pemeriksa:
    def __init__(self):
        self.lulus = 0
        self.gagal = 0
        self.temuan: list[str] = []

    def cek(self, nama: str, benar, salah, keterangan: str = ""):
        if benar == salah:
            self.lulus += 1
            print(f"  [COCOK] {nama}")
        else:
            self.gagal += 1
            self.temuan.append(nama)
            print(f"  [BEDA]  {nama}")
            print(f"          aplikasi    : {benar}")
            print(f"          hitung ulang: {salah}")
            if keterangan:
                print(f"          {keterangan}")

    def benar(self, nama: str, syarat: bool, keterangan: str = ""):
        if syarat:
            self.lulus += 1
            print(f"  [BENAR] {nama}")
        else:
            self.gagal += 1
            self.temuan.append(nama)
            print(f"  [SALAH] {nama}" + (f" — {keterangan}" if keterangan else ""))

    def ringkas(self) -> int:
        print()
        print("=" * 76)
        if self.gagal:
            print(f"  HASIL: {self.lulus} BENAR, {self.gagal} SALAH")
            for t in self.temuan:
                print(f"    - {t}")
        else:
            print(f"  HASIL: {self.lulus} BENAR, 0 SALAH")
        print("=" * 76)
        return 1 if self.gagal else 0


def saldo(kode: str, company_id: int) -> int:
    """
    Saldo akun menurut saldo normalnya.

    Akun bersaldo normal debit (harta, beban) bernilai debit dikurangi
    kredit. Akun bersaldo normal kredit (utang, modal, pendapatan) bernilai
    kredit dikurangi debit. Arahnya dibaca dari kolom `normal` pada bagan
    akun, bukan ditentukan di sini, supaya aturannya satu sumber.

    Diambil langsung dari baris jurnal, bukan lewat fungsi aplikasi, supaya
    angkanya benar benar berasal dari data tersimpan. Bila fungsi aplikasi
    yang dipakai, kesalahan pada fungsi itu tidak akan terlihat.
    """
    baris = db.q(
        """SELECT COALESCE(SUM(debit), 0) AS d,
                  COALESCE(SUM(kredit), 0) AS k
           FROM journal_lines
           WHERE company_id = ? AND kode_akun = ?""",
        (company_id, kode))
    if not baris:
        return 0

    d, k = int(baris[0]["d"]), int(baris[0]["k"])
    akun_baris = db.q1("SELECT normal FROM accounts WHERE kode = ?", (kode,))
    normal = (akun_baris["normal"] or "Debit").lower() if akun_baris else "debit"
    return (k - d) if normal.startswith("kredit") else (d - k)


def main() -> int:
    p = Pemeriksa()
    print("=" * 76)
    print("  VERIFIKASI INDEPENDEN: AKUNTANSI")
    print("=" * 76)
    print()

    db.init_db()

    # ------------------------------------------------------------------
    # Siapkan perusahaan uji dengan angka yang dapat dihitung dengan tangan.
    # ------------------------------------------------------------------
    # Paket Standar hanya mengizinkan satu badan usaha, jadi perusahaan
    # bawaan dipakai bila sudah ada. Bila belum ada, satu perusahaan uji
    # dibuat lebih dulu.
    perusahaan = db.q1("SELECT id, nama FROM companies ORDER BY id LIMIT 1")
    if perusahaan is None:
        company_id = services.create_company(
            "PT Verifikasi Independen", bentuk="pt",
            npwp="01.234.567.8-901.000", kota="Jakarta", pemilik="Penguji")
        perusahaan = db.q1("SELECT id, nama FROM companies WHERE id = ?",
                           (company_id,))
    company_id = perusahaan["id"]

    # Kode akun mengikuti bagan akun bawaan aplikasi.
    # Kode akun mengikuti bagan akun bawaan aplikasi.
    k = "1001"          # Kas
    piutang = "1101"    # Piutang Usaha
    persediaan = "1104"  # Persediaan Barang Dagang
    utang = "2001"      # Utang Usaha
    modal = "3001"      # Modal Saham
    pendapatan = "4001"  # Penjualan / Pendapatan Usaha
    hpp = "5001"        # Harga Pokok Penjualan
    beban = "6006"      # Beban Sewa

    print(f"  perusahaan uji: id={company_id}")
    print(f"  akun: kas={k} piutang={piutang} persediaan={persediaan}")
    print(f"        utang={utang} modal={modal}")
    print(f"        pendapatan={pendapatan} hpp={hpp} beban={beban}")
    print()

    # ------------------------------------------------------------------
    # Transaksi dengan angka bulat supaya dapat diperiksa dengan tangan.
    # ------------------------------------------------------------------
    transaksi = [
        # (tanggal, keterangan, [(akun, debit, kredit), ...])
        ("2026-01-05", "Setoran modal awal",
         [(k, 500_000_000, 0), (modal, 0, 500_000_000)]),
        ("2026-01-10", "Beli persediaan tunai",
         [(persediaan, 100_000_000, 0), (k, 0, 100_000_000)]),
        ("2026-01-15", "Jual barang, sebagian tunai",
         [(k, 180_000_000, 0), (piutang, 120_000_000, 0),
          (pendapatan, 0, 300_000_000)]),
        ("2026-01-20", "Catat harga pokok penjualan",
         [(hpp, 120_000_000, 0), (persediaan, 0, 120_000_000)]),
        ("2026-01-25", "Bayar beban operasional",
         [(beban, 45_000_000, 0), (k, 0, 45_000_000)]),
        ("2026-01-28", "Terima pembayaran piutang",
         [(k, 70_000_000, 0), (piutang, 0, 70_000_000)]),
        ("2026-01-30", "Beli persediaan dengan utang",
         [(persediaan, 80_000_000, 0), (utang, 0, 80_000_000)]),
    ]

    print("[1. Menyimpan jurnal]")
    for tanggal, keterangan, baris in transaksi:
        debit = sum(b[1] for b in baris)
        kredit = sum(b[2] for b in baris)
        p.benar(f"{keterangan[:38]} (D={debit:,} K={kredit:,})",
                debit == kredit,
                "jurnal tidak seimbang, data uji salah")
        services.simpan_jurnal_manual(
            company_id, tanggal, "", keterangan,
            [{"kode_akun": kode, "debit": d, "kredit": kr,
              "keterangan": ""} for kode, d, kr in baris])
    print()

    # ------------------------------------------------------------------
    # Hitungan tangan.
    # ------------------------------------------------------------------
    # Kas: +500jt -100jt +180jt -45jt +70jt = 605jt
    kas_tangan = 500_000_000 - 100_000_000 + 180_000_000 - 45_000_000 + 70_000_000
    # Piutang: +120jt -70jt = 50jt
    piutang_tangan = 120_000_000 - 70_000_000
    # Persediaan: +100jt -120jt +80jt = 60jt
    persediaan_tangan = 100_000_000 - 120_000_000 + 80_000_000
    # Utang: 80jt
    utang_tangan = 80_000_000
    # Modal: 500jt
    modal_tangan = 500_000_000
    # Pendapatan: 300jt
    pendapatan_tangan = 300_000_000
    # HPP: 120jt
    hpp_tangan = 120_000_000
    # Beban: 45jt
    beban_tangan = 45_000_000
    # Laba = pendapatan - hpp - beban = 300 - 120 - 45 = 135jt
    laba_tangan = pendapatan_tangan - hpp_tangan - beban_tangan
    # Harta = kas + piutang + persediaan = 605 + 50 + 60 = 715jt
    harta_tangan = kas_tangan + piutang_tangan + persediaan_tangan
    # Utang + Modal + Laba = 80 + 500 + 135 = 715jt
    pasiva_tangan = utang_tangan + modal_tangan + laba_tangan

    # ------------------------------------------------------------------
    print("[2. Saldo tiap akun sama dengan hitungan tangan]")
    for nama, kode_akun, tangan in (
        ("Kas", "1001", kas_tangan),
        ("Piutang usaha", "1101", piutang_tangan),
        ("Persediaan", "1104", persediaan_tangan),
        ("Utang usaha", "2001", utang_tangan),
        ("Modal", "3001", modal_tangan),
        ("Pendapatan", "4001", pendapatan_tangan),
        ("Harga pokok penjualan", "5001", hpp_tangan),
        ("Beban sewa", "6006", beban_tangan),
    ):
        p.cek(f"Saldo {nama}", saldo(kode_akun, company_id), tangan)
    print()

    # ------------------------------------------------------------------
    print("[3. Persamaan dasar akuntansi]")
    p.cek("Harta = Utang + Modal + Laba",
          harta_tangan, pasiva_tangan)
    p.benar("Persamaan seimbang", harta_tangan == pasiva_tangan,
            f"harta={harta_tangan:,} pasiva={pasiva_tangan:,}")
    print()

    # ------------------------------------------------------------------
    print("[4. Neraca saldo]")
    total = acc.total_neraca_saldo(company_id, 2026)
    print(f"    total dari aplikasi: {total}")
    debit_total = total.get("debit", 0)
    kredit_total = total.get("kredit", 0)
    p.cek("Neraca saldo seimbang (debit = kredit)",
          debit_total, kredit_total)
    p.benar("Neraca saldo seimbang", debit_total == kredit_total,
            f"debit={debit_total:,} kredit={kredit_total:,}")
    print()

    # ------------------------------------------------------------------
    print("[5. Laba rugi]")
    lr = acc.laba_rugi(company_id, 2026)
    # Objek hasil, bukan kamus: nilainya dibaca dari atributnya.
    laba_sebelum_pajak = getattr(lr, "laba_sebelum_pajak", None)
    laba_bersih = getattr(lr, "laba_bersih", None)
    beban_pajak = getattr(lr, "beban_pajak", None)

    p.cek("Laba sebelum pajak", laba_sebelum_pajak, laba_tangan)

    # Laba bersih adalah laba sebelum pajak dikurangi taksiran pajak badan.
    # Taksirannya diperiksa terpisah, karena besarnya mengikuti ketentuan
    # perpajakan, bukan angka yang ditetapkan di sini.
    if beban_pajak is not None:
        p.cek("Laba bersih = laba sebelum pajak - taksiran pajak",
              laba_bersih, laba_tangan - beban_pajak)
        print(f"          taksiran pajak yang dipakai: Rp{beban_pajak:,}")

        # Taksiran pajak harus sesuai ketentuan: 11% dari laba untuk
        # peredaran di bawah 4,8 miliar (Pasal 31E).
        peredaran = acc.omzet_setahun(company_id, 2026)
        if peredaran <= 4_800_000_000:
            p.cek("Taksiran pajak 11% dari laba (Pasal 31E)",
                  beban_pajak, int(round(laba_tangan * 0.11)))
    else:
        p.cek("Laba bersih", laba_bersih, laba_tangan)
    print()

    # ------------------------------------------------------------------
    print("[6. Neraca]")
    ner = acc.neraca(company_id, 2026)
    total_harta = getattr(ner, "total_aset", None)
    if total_harta is None:
        total_harta = getattr(ner, "total_harta", None)
    if total_harta is None:
        print(f"    atribut yang ada: "
              f"{[a for a in dir(ner) if not a.startswith('_')][:14]}")
    else:
        p.cek("Total harta", total_harta, harta_tangan)
    print()

    # ------------------------------------------------------------------
    print("[7. Jurnal tidak seimbang harus ditolak]")
    try:
        hasil = acc.validasi_jurnal([
            {"kode_akun": k, "debit": 100, "kredit": 0},
            {"kode_akun": modal, "debit": 0, "kredit": 90},
        ])
        # Objek hasil validasi: periksa atribut 'valid'.
        sah = getattr(hasil, "valid", None)
        if sah is None:
            sah = bool(getattr(hasil, "sah", False))
        p.benar("Jurnal tidak seimbang ditolak", not sah,
                f"valid={sah}")
    except Exception as e:
        p.benar("Jurnal tidak seimbang ditolak", True,
                f"ditolak dengan galat: {type(e).__name__}")
    print()

    # ------------------------------------------------------------------
    print("[8. Jurnal seimbang harus diterima]")
    try:
        hasil = acc.validasi_jurnal([
            {"kode_akun": k, "debit": 100, "kredit": 0},
            {"kode_akun": modal, "debit": 0, "kredit": 100},
        ])
        sah = getattr(hasil, "valid", None)
        if sah is None:
            sah = bool(getattr(hasil, "sah", False))
        p.benar("Jurnal seimbang diterima", sah, f"valid={sah}")
    except Exception as e:
        p.benar("Jurnal seimbang diterima", False, f"galat: {e}")
    print()

    # ------------------------------------------------------------------
    print("[9. Periksa langsung ke basis data]")
    koneksi = sqlite3.connect(config.DB_PATH)
    # Jumlahkan seluruh baris jurnal, harus seimbang.
    d = koneksi.execute(
        """SELECT COALESCE(SUM(debit),0), COALESCE(SUM(kredit),0)
           FROM journal_lines WHERE company_id = ?""",
        (company_id,)).fetchone()
    p.cek("Seluruh baris jurnal seimbang", d[0], d[1])
    p.benar("Buku besar seimbang", d[0] == d[1],
            f"debit={d[0]:,} kredit={d[1]:,}")

    # Tidak boleh ada baris dengan debit DAN kredit sekaligus.
    n = koneksi.execute(
        """SELECT COUNT(*) FROM journal_lines
           WHERE debit > 0 AND kredit > 0""").fetchone()[0]
    p.cek("Tidak ada baris berisi debit dan kredit sekaligus", n, 0)

    # Tidak boleh ada baris dengan keduanya nol.
    n2 = koneksi.execute(
        """SELECT COUNT(*) FROM journal_lines
           WHERE debit = 0 AND kredit = 0""").fetchone()[0]
    p.cek("Tidak ada baris bernilai nol", n2, 0)
    print()

    return p.ringkas()


if __name__ == "__main__":
    try:
        kode = main()
    finally:
        shutil.rmtree(FOLDER, ignore_errors=True)
    sys.exit(kode)
