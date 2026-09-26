"""
Uji: perusahaan lama mendapat akun baru tanpa kehilangan data.

Bagan akun ditulis saat perusahaan dibuat. Ketika aplikasi diperbarui dan
bagan akunnya bertambah, perusahaan yang sudah ada tidak otomatis mendapat
akun baru itu. Akibatnya fitur yang memakai akun tersebut gagal di komputer
pengguna lama, padahal pada perusahaan baru berjalan normal.

Yang diperiksa:
  1. Perusahaan baru mendapat seluruh akun bawaan.
  2. Perusahaan lama yang kekurangan akun dilengkapi.
  3. Akun yang sudah ada tidak disentuh, termasuk saldonya.
  4. Jurnal dan saldo pengguna tidak berubah.
  5. Melengkapi dua kali tidak menggandakan akun.
  6. Akun buatan pengguna sendiri tidak dihapus atau diubah.

Cara pakai:
    python tools/uji_lengkapi_akun.py
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "src"))

FOLDER = Path(tempfile.mkdtemp(prefix="akuntuntas_lengkapi_"))
os.environ["LOCALAPPDATA"] = str(FOLDER)

from akuntansi_id import coa, db, services  # noqa: E402


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
            print(f"          hasil   : {benar}")
            print(f"          harapan : {salah}")
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


def _buat_perusahaan_kosong(bentuk: str) -> int:
    """
    Buat perusahaan uji yang bagan akunnya sengaja dikosongkan.

    Dipakai untuk memeriksa bahwa pelengkapan benar benar mengisi seluruh
    akun template, bukan hanya sebagian.
    """
    cid = db.q1("SELECT id FROM companies ORDER BY id DESC LIMIT 1")["id"]
    # Perusahaan baru dari create_company sudah terisi; untuk pengujian ini
    # akunnya dikosongkan lebih dulu.
    db.ex("DELETE FROM accounts WHERE company_id = ?", (cid,))
    return cid


def hitung_akun(cid: int) -> int:
    return int(db.scalar(
        "SELECT COUNT(*) FROM accounts WHERE company_id = ?", (cid,)))


def main() -> int:
    p = Pemeriksa()
    print("=" * 76)
    print("  UJI: PERUSAHAAN LAMA MENDAPAT AKUN BARU")
    print("=" * 76)
    print()

    db.init_db()
    baris = db.q1("SELECT id, bentuk FROM companies ORDER BY id LIMIT 1")
    if baris is None:
        cid = services.create_company("PT Uji Lengkapi", bentuk="pt")
        baris = db.q1("SELECT id, bentuk FROM companies WHERE id = ?", (cid,))
    cid = baris["id"]
    bentuk = baris["bentuk"] or "pt"
    print(f"  perusahaan uji: id={cid} bentuk={bentuk}")
    print()

    # ------------------------------------------------ 1. perusahaan baru
    print("[1. Perusahaan baru mendapat seluruh akun bawaan]")
    n_awal = hitung_akun(cid)
    kurang = coa.akun_belum_ada(cid, bentuk)
    p.cek("Perusahaan baru tidak kekurangan akun", len(kurang), 0)
    print(f"    jumlah akun: {n_awal}")
    print()

    # ------------------------------ 2. tiru perusahaan lama yang kurang
    print("[2. Perusahaan lama yang kekurangan akun]")
    # Hapus dua akun untuk meniru perusahaan yang dibuat versi lama,
    # sebelum kedua akun itu ada.
    for kode in ("2013", "3007"):
        db.ex("DELETE FROM accounts WHERE company_id = ? AND kode = ?",
              (cid, kode))
    n_kurang = hitung_akun(cid)
    p.cek("Dua akun terhapus untuk pengujian", n_awal - n_kurang, 2)

    kurang = coa.akun_belum_ada(cid, bentuk)
    p.cek("Kekurangan terdeteksi", len(kurang), 2)
    kode_kurang = sorted(b[0] for b in kurang)
    p.benar(f"Kode yang kurang benar: {kode_kurang}",
            kode_kurang == ["2013", "3007"], f"hasil: {kode_kurang}")
    print()

    # ------------------------------------------- 3. lengkapi akunnya
    print("[3. Melengkapi akun yang kurang]")
    # Catat keadaan sebelum, untuk memastikan tidak ada yang berubah.
    akun_sebelum = {
        r["kode"]: (r["nama"], r["tipe"], r["saldo_awal"])
        for r in db.q("SELECT kode, nama, tipe, saldo_awal FROM accounts "
                      "WHERE company_id = ?", (cid,))
    }

    n_ditambah = coa.lengkapi_akun_bawaan(cid, bentuk)
    p.cek("Akun yang ditambahkan", n_ditambah, 2)
    p.cek("Jumlah akun kembali seperti semula", hitung_akun(cid), n_awal)

    # Periksa akun barunya benar.
    for kode, nama_diharapkan in (("2013", "Utang Akrual"),
                                  ("3007", "Laba Tahun Berjalan")):
        a = db.q1("SELECT nama, tipe FROM accounts WHERE company_id = ? "
                  "AND kode = ?", (cid, kode))
        p.benar(f"Akun {kode} ada dengan nama benar",
                bool(a) and a["nama"] == nama_diharapkan,
                f"hasil: {dict(a) if a else 'tidak ada'}")
    print()

    # --------------------------- 4. akun lama tidak berubah
    print("[4. Akun yang sudah ada tidak disentuh]")
    berubah = []
    for kode, nilai_sebelum in akun_sebelum.items():
        a = db.q1("SELECT nama, tipe, saldo_awal FROM accounts "
                  "WHERE company_id = ? AND kode = ?", (cid, kode))
        if a is None:
            berubah.append(f"{kode} hilang")
            continue
        nilai_sesudah = (a["nama"], a["tipe"], a["saldo_awal"])
        if nilai_sesudah != nilai_sebelum:
            berubah.append(f"{kode}: {nilai_sebelum} -> {nilai_sesudah}")

    p.cek("Tidak ada akun lama yang berubah", len(berubah), 0)
    if berubah:
        for b in berubah[:5]:
            print(f"      {b}")
    print()

    # --------------------------- 5. melengkapi dua kali aman
    print("[5. Melengkapi dua kali tidak menggandakan]")
    n_sebelum = hitung_akun(cid)
    n_lagi = coa.lengkapi_akun_bawaan(cid, bentuk)
    p.cek("Tidak ada akun ditambahkan pada pemanggilan kedua", n_lagi, 0)
    p.cek("Jumlah akun tidak bertambah", hitung_akun(cid), n_sebelum)
    print()

    # --------------------------- 6. akun buatan pengguna aman
    print("[6. Akun buatan pengguna sendiri tidak diganggu]")
    services.create_account(
        cid, "9900", "Akun Khusus Pengguna", "Aset", "", "Aset Lancar",
        "Debit", "Deductible/Taxable", "Akun buatan sendiri", 0, True)
    a = db.q1("SELECT nama FROM accounts WHERE company_id = ? AND kode = '9900'",
              (cid,))
    p.benar("Akun buatan pengguna tetap ada", a is not None,
            "akun pengguna hilang")

    # Lengkapi lagi, akun pengguna tidak boleh tersentuh.
    coa.lengkapi_akun_bawaan(cid, bentuk)
    a2 = db.q1("SELECT nama FROM accounts WHERE company_id = ? AND kode = '9900'",
               (cid,))
    p.benar("Akun pengguna tetap utuh setelah pelengkapan",
            a2 is not None and a2["nama"] == "Akun Khusus Pengguna",
            f"hasil: {dict(a2) if a2 else 'hilang'}")
    print()

    # --------------------------- 7. jurnal pengguna tidak berubah
    print("[7. Jurnal dan saldo pengguna tidak berubah]")
    services.simpan_jurnal_manual(cid, "2026-05-01", "UJI-001", "Uji", [
        {"kode_akun": "1001", "debit": 1_000_000, "kredit": 0, "keterangan": ""},
        {"kode_akun": "3001", "debit": 0, "kredit": 1_000_000, "keterangan": ""},
    ])

    d_sebelum = db.q1("""SELECT COALESCE(SUM(debit),0) AS d,
                                COALESCE(SUM(kredit),0) AS k
                         FROM journal_lines WHERE company_id = ?""", (cid,))

    coa.lengkapi_akun_bawaan(cid, bentuk)

    d_sesudah = db.q1("""SELECT COALESCE(SUM(debit),0) AS d,
                                COALESCE(SUM(kredit),0) AS k
                         FROM journal_lines WHERE company_id = ?""", (cid,))

    p.cek("Total debit tidak berubah", d_sesudah["d"], d_sebelum["d"])
    p.cek("Total kredit tidak berubah", d_sesudah["k"], d_sebelum["k"])
    p.benar("Buku besar tetap seimbang", d_sesudah["d"] == d_sesudah["k"],
            f"debit={d_sesudah['d']:,} kredit={d_sesudah['k']:,}")
    print()

    # --------------------------- 8. pelengkapan sesuai bentuk badan
    print("[8. Pelengkapan mengikuti bentuk badan]")
    # Template ringkas memang sengaja memuat lebih sedikit akun, supaya
    # pemula tidak tersesat. Yang penting: pelengkapan hanya menambahkan
    # akun yang memang ada pada template bentuk badan itu.
    for b in ("umkm_op", "pt_perorangan", "pt"):
        template = {r[0] for r in coa.get_coa_template(b)}
        # Perusahaan dengan bentuk ini, yang bagan akunnya kosong.
        kosong = _buat_perusahaan_kosong(b)
        kurang = {r[0] for r in coa.akun_belum_ada(kosong, b)}
        p.cek(f"Akun yang kurang sama dengan template {b}",
              kurang, template)

        n = coa.lengkapi_akun_bawaan(kosong, b)
        p.cek(f"Seluruh akun template {b} terpasang", n, len(template))

        # Setelah dilengkapi, tidak boleh ada yang kurang lagi.
        sisa = coa.akun_belum_ada(kosong, b)
        p.cek(f"Tidak ada kekurangan setelah dilengkapi ({b})", len(sisa), 0)
    print()

    return p.ringkas()


if __name__ == "__main__":
    try:
        kode_keluar = main()
    finally:
        shutil.rmtree(FOLDER, ignore_errors=True)
    sys.exit(kode_keluar)
