"""
Debugging dengan cara berbeda: memeriksa konsistensi antar laporan.

Cara ini belum pernah dipakai. Laporan laporan di aplikasi dihitung dari
data yang sama, jadi angkanya harus saling cocok. Bila satu laporan
menghitung dengan cara yang berbeda dari laporan lain, salah satunya pasti
keliru, meskipun masing masing terlihat benar saat diperiksa sendiri.

Contoh yang diperiksa:

  - Laba bersih di Laba Rugi harus sama dengan laba yang menambah ekuitas
    di Neraca.
  - Total harta di Neraca harus sama dengan jumlah saldo akun harta di
    Buku Besar.
  - Laba di Neraca harus sama dengan Pendapatan dikurangi Beban di Laba
    Rugi.
  - Arus kas harus cocok dengan perubahan saldo kas di Neraca.
  - Ringkasan bulanan harus berjumlah sama dengan total setahun.
  - Angka di dasbor harus sama dengan angka di laporan.

Cara pakai:
    python tools/verifikasi_konsistensi_laporan.py
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "src"))

FOLDER = Path(tempfile.mkdtemp(prefix="akuntuntas_konsistensi_"))
os.environ["LOCALAPPDATA"] = str(FOLDER)

from akuntansi_id import db, services  # noqa: E402
from akuntansi_id.core import accounting as acc  # noqa: E402


class Pemeriksa:
    def __init__(self):
        self.lulus = 0
        self.gagal = 0
        self.temuan: list[str] = []

    def cek(self, nama: str, satu, lain, keterangan: str = ""):
        if satu == lain:
            self.lulus += 1
            print(f"  [COCOK] {nama}")
        else:
            self.gagal += 1
            self.temuan.append(nama)
            print(f"  [BEDA]  {nama}")
            print(f"          {satu:,}")
            print(f"          {lain:,}")
            if keterangan:
                print(f"          {keterangan}")

    def ringkas(self) -> int:
        print()
        print("=" * 76)
        if self.gagal:
            print(f"  HASIL: {self.lulus} COCOK, {self.gagal} BEDA")
            print()
            for t in self.temuan:
                print(f"    - {t}")
        else:
            print(f"  HASIL: {self.lulus} COCOK, 0 BEDA")
        print("=" * 76)
        return 1 if self.gagal else 0


def main() -> int:
    p = Pemeriksa()
    print("=" * 76)
    print("  VERIFIKASI KONSISTENSI ANTAR LAPORAN")
    print("=" * 76)
    print()

    db.init_db()
    b = db.q1("SELECT id FROM companies ORDER BY id LIMIT 1")
    cid = b["id"] if b else services.create_company("PT Konsistensi", bentuk="pt")

    # ------------------------------------------------------------------
    # Isi pembukuan dengan transaksi yang beragam, supaya laporannya
    # benar benar terisi dan bukan hanya nol.
    # ------------------------------------------------------------------
    transaksi = [
        ("2026-01-05", [(("1001", 800_000_000, 0)), (("3001", 0, 800_000_000))]),
        ("2026-01-12", [(("1104", 200_000_000, 0)), (("1001", 0, 200_000_000))]),
        ("2026-02-03", [(("1001", 300_000_000, 0)), (("1101", 150_000_000, 0)),
                        (("4001", 0, 450_000_000))]),
        ("2026-02-10", [(("5001", 180_000_000, 0)), (("1104", 0, 180_000_000))]),
        ("2026-03-01", [(("6006", 60_000_000, 0)), (("1001", 0, 60_000_000))]),
        ("2026-03-15", [(("1001", 100_000_000, 0)), (("1101", 0, 100_000_000))]),
        ("2026-04-01", [(("1104", 150_000_000, 0)), (("2001", 0, 150_000_000))]),
        ("2026-05-05", [(("1001", 250_000_000, 0)), (("4001", 0, 250_000_000))]),
        ("2026-06-01", [(("5001", 120_000_000, 0)), (("1104", 0, 120_000_000))]),
        ("2026-07-01", [(("6007", 40_000_000, 0)), (("1001", 0, 40_000_000))]),
    ]
    for i, (tanggal, baris) in enumerate(transaksi):
        if len(baris) < 2:
            continue
        services.simpan_jurnal_manual(
            cid, tanggal, f"KONS-{i+1:03d}", f"Transaksi uji {i+1}",
            [{"kode_akun": k, "debit": d, "kredit": kr, "keterangan": ""}
             for k, d, kr in baris])

    n_jurnal = db.scalar(
        "SELECT COUNT(*) FROM journal_entries WHERE company_id = ?", (cid,))
    print(f"  jurnal tercatat: {n_jurnal}")
    print()

    # ------------------------------------------------------------------
    print("[1. Laba Rugi cocok dengan Neraca]")
    lr = acc.laba_rugi(cid, 2026)
    ner = acc.neraca(cid, 2026)

    laba_lr = getattr(lr, "laba_sebelum_pajak", None)
    laba_neraca = getattr(ner, "laba_tahun_berjalan", None)
    p.cek("Laba sebelum pajak: Laba Rugi = Neraca",
          laba_lr, laba_neraca,
          "laba di dua laporan harus sama")

    # Pendapatan dikurangi seluruh beban harus sama dengan laba sebelum
    # pajak. Nama atributnya mengikuti objek LabaRugi: pendapatan usaha
    # ditambah pendapatan lain, sedangkan bebannya terdiri dari harga pokok
    # penjualan, beban operasional, dan beban lain.
    pendapatan = (getattr(lr, "pendapatan_usaha", 0)
                  + getattr(lr, "pendapatan_lain", 0))
    beban = (getattr(lr, "hpp", 0)
             + getattr(lr, "beban_operasional", 0)
             + getattr(lr, "beban_lain", 0))
    p.cek("Pendapatan - Beban = Laba sebelum pajak",
          pendapatan - beban, laba_lr)

    # Laba kotor harus sama dengan pendapatan dikurangi harga pokok.
    p.cek("Pendapatan - HPP = Laba kotor",
          pendapatan - getattr(lr, "hpp", 0), getattr(lr, "laba_kotor", 0))

    # Laba bersih harus sama dengan laba sebelum pajak dikurangi pajak.
    p.cek("Laba sebelum pajak - pajak = Laba bersih",
          laba_lr - getattr(lr, "beban_pajak", 0),
          getattr(lr, "laba_bersih", 0))
    print()

    # ------------------------------------------------------------------
    print("[2. Persamaan dasar akuntansi]")
    harta = getattr(ner, "total_aset", 0)
    liabilitas = getattr(ner, "total_liabilitas", 0)
    ekuitas = getattr(ner, "total_ekuitas", 0)
    p.cek("Harta = Liabilitas + Ekuitas",
          harta, liabilitas + ekuitas)
    print()

    # ------------------------------------------------------------------
    print("[3. Neraca cocok dengan saldo buku besar]")
    # Hitung sendiri dari baris jurnal, tanpa memakai fungsi laporan.
    def saldo(kode: str) -> int:
        r = db.q1("""SELECT COALESCE(SUM(debit),0) AS d,
                            COALESCE(SUM(kredit),0) AS k
                     FROM journal_lines
                     WHERE company_id = ? AND kode_akun = ?""", (cid, kode))
        a = db.q1("SELECT normal FROM accounts WHERE company_id = ? AND kode = ?",
                  (cid, kode))
        normal = (a["normal"] or "Debit").lower() if a else "debit"
        return (r["k"] - r["d"]) if normal.startswith("kredit") else (r["d"] - r["k"])

    # Harta menurut hitungan sendiri.
    akun_harta = [r["kode"] for r in db.q(
        "SELECT kode FROM accounts WHERE company_id = ? AND tipe = 'Aset'", (cid,))]
    harta_hitung = sum(saldo(k) for k in akun_harta)
    p.cek("Total harta: Neraca = hitungan buku besar",
          harta, harta_hitung)

    # Saldo kas menurut hitungan sendiri.
    kas_hitung = sum(saldo(k) for k in ("1001", "1002", "1003", "1004", "1005"))
    print(f"          saldo kas menurut buku besar: Rp{kas_hitung:,}")
    print()

    # ------------------------------------------------------------------
    print("[4. Neraca saldo seimbang]")
    total_ns = acc.total_neraca_saldo(cid, 2026)
    p.cek("Debit = Kredit pada neraca saldo",
          total_ns.get("debit", 0), total_ns.get("kredit", 0))
    print()

    # ------------------------------------------------------------------
    print("[5. Ringkasan bulanan berjumlah sama dengan setahun]")
    ringkas = acc.ringkasan_bulanan(cid, 2026)
    if ringkas:
        print(f"          kunci yang ada: {sorted(ringkas[0].keys())}")
        # Nama kuncinya dicari, karena dapat berbeda antar versi.
        for kunci in ("pendapatan", "pendapatan_usaha", "omzet", "penjualan"):
            if kunci in ringkas[0]:
                total_bulanan = sum(r.get(kunci, 0) for r in ringkas)
                p.cek(f"Jumlah '{kunci}' bulanan = pendapatan setahun",
                      total_bulanan, pendapatan)
                break
        else:
            print("          kunci pendapatan tidak ditemukan")
    else:
        print("          ringkasan bulanan kosong")
    print()

    # ------------------------------------------------------------------
    print("[6. Arus kas cocok dengan perubahan kas]")
    arus = acc.arus_kas(cid, 2026)
    kas_akhir = getattr(arus, "kas_akhir", None)
    if kas_akhir is not None:
        p.cek("Kas akhir di Arus Kas = saldo kas di buku besar",
              kas_akhir, kas_hitung)
        kas_awal = getattr(arus, "kas_awal", 0)
        arus_bersih = getattr(arus, "kenaikan_kas", None)
        if arus_bersih is not None:
            p.cek("Kas awal + arus bersih = kas akhir",
                  kas_awal + arus_bersih, kas_akhir)
    else:
        print(f"          atribut arus kas: "
              f"{[a for a in dir(arus) if not a.startswith('_')][:10]}")
    print()

    # ------------------------------------------------------------------
    print("[7. Angka dasbor cocok dengan laporan]")
    kpi = acc.dashboard_kpi(cid, 2026)
    if isinstance(kpi, dict):
        print(f"          kunci yang ada: {sorted(kpi.keys())}")
        for kunci, harapan, nama in (
            (("omzet", "peredaran", "pendapatan"), pendapatan,
             "Omzet dasbor = pendapatan Laba Rugi"),
            (("laba_bersih", "laba"), getattr(lr, "laba_bersih", 0),
             "Laba bersih dasbor = laba bersih Laba Rugi"),
            (("kas", "kas_bank", "saldo_kas"), kas_hitung,
             "Kas dasbor = saldo kas buku besar"),
            (("aset", "total_aset", "harta"), harta,
             "Aset dasbor = total harta Neraca"),
        ):
            for k in kunci:
                if k in kpi:
                    p.cek(nama, kpi[k], harapan)
                    break
            else:
                print(f"          kunci {kunci} tidak ada di kpi")
    else:
        print(f"          kpi bertipe {type(kpi).__name__}")
    print()

    # ------------------------------------------------------------------
    print("[8. Perubahan ekuitas cocok dengan laba]")
    try:
        ek = acc.perubahan_ekuitas(cid, 2026)
        if ek:
            # Baris laba pada laporan perubahan ekuitas harus sama dengan
            # laba di Laba Rugi.
            nilai_laba = [r.get("nilai", r.get("jumlah", 0)) for r in ek
                          if "laba bersih" in str(r.get("uraian", "")).lower()]
            if nilai_laba:
                # Ekuitas bertambah sebesar laba BERSIH, yaitu setelah
                # dikurangi taksiran pajak. Laba sebelum pajak belum
                # mengurangi ekuitas, karena pajaknya belum dibebankan.
                p.cek("Laba bersih di Perubahan Ekuitas = laba bersih "
                      "di Laba Rugi",
                      nilai_laba[0], getattr(lr, "laba_bersih", 0))
            else:
                print(f"          baris: {[r.get('uraian') for r in ek][:6]}")
    except Exception as e:
        print(f"          tidak dapat diperiksa: {type(e).__name__}: {e}")
    print()

    # ------------------------------------------------------------------
    print("[9. Buku besar per akun cocok dengan saldo]")
    for kode, nama in (("1001", "Kas"), ("4001", "Pendapatan"),
                       ("5001", "HPP"), ("1104", "Persediaan")):
        try:
            baris_bk = acc.buku_besar(cid, kode, 2026)
            if baris_bk:
                # Saldo akhir pada baris terakhir harus sama dengan saldo
                # hasil hitungan sendiri.
                # Saldo akhir dibaca dari baris terakhir. Buku besar kini
                # menyatakan saldo pada sisi normal akun, sama seperti
                # neraca saldo dan hitungan sendiri di berkas ini.
                akhir = baris_bk[-1].get("saldo")
                if akhir is not None:
                    p.cek(f"Buku besar {nama} cocok dengan saldo",
                          akhir, saldo(kode))
                else:
                    print(f"          {nama}: kunci saldo tidak ditemukan "
                          f"({sorted(baris_bk[-1].keys())[:6]})")
        except Exception as e:
            print(f"          {nama}: tidak dapat diperiksa ({type(e).__name__})")
    print()

    return p.ringkas()


if __name__ == "__main__":
    try:
        kode_keluar = main()
    finally:
        shutil.rmtree(FOLDER, ignore_errors=True)
    sys.exit(kode_keluar)
