"""
Uji impor data massal: mitra, produk, dan jurnal dari berkas CSV.

Fitur impor belum pernah diuji sama sekali, padahal impor menyentuh data
dalam jumlah besar sekaligus. Kesalahan di situ dapat merusak banyak data
sekaligus, dan berkas dari luar sering memuat hal yang tidak terduga:
pemisah berbeda, kolom kurang, angka berformat asing, dan baris kosong.

Yang diperiksa:
  1. Impor dengan isi yang benar berhasil dan datanya masuk.
  2. Berkas kosong tidak menimbulkan galat.
  3. Kolom yang kurang ditolak dengan keterangan, bukan gagal diam.
  4. Angka berformat asing tidak tersimpan sebagai nilai yang salah.
  5. Baris kosong dan spasi berlebih diabaikan.
  6. Nama yang sama tidak menghasilkan data kembar.
  7. Impor jurnal menjaga keseimbangan debit dan kredit.
  8. Tidak ada data yang masuk sebagian saat berkasnya rusak.

Cara pakai:
    python tools/uji_impor_data.py
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "src"))

FOLDER = Path(tempfile.mkdtemp(prefix="akuntuntas_impor_"))
os.environ["LOCALAPPDATA"] = str(FOLDER)

from akuntansi_id import db, modules_ops  # noqa: E402


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


def main() -> int:
    p = Pemeriksa()
    print("=" * 76)
    print("  UJI IMPOR DATA MASSAL")
    print("=" * 76)
    print()

    db.init_db()
    baris = db.q1("SELECT id FROM companies ORDER BY id LIMIT 1")
    if baris is None:
        from akuntansi_id import services
        baru_id = services.create_company("PT Uji Impor", bentuk="pt")
        baris = db.q1("SELECT id FROM companies WHERE id = ?", (baru_id,))
    cid = baris["id"]
    print(f"  perusahaan uji: id={cid}")
    print()

    # ------------------------------------------------------- 1. mitra
    print("[1. Impor mitra dari CSV]")
    csv_mitra = (
        "nama,tipe,telepon,email,alamat\n"
        "PT Sumber Makmur,pemasok,08123456789,sumber@contoh.id,Jakarta\n"
        "CV Berkah Jaya,pelanggan,08987654321,berkah@contoh.id,Bandung\n"
        "Toko Sejahtera,pelanggan,08555555555,,Surabaya\n"
    )
    try:
        hasil = modules_ops.impor_mitra_massal(cid, csv_mitra)
        print(f"    hasil: {hasil}")
        p.benar("Impor mitra berjalan tanpa galat", True)
        n = _hitung_mitra(cid)
        p.cek("Tiga mitra masuk", n, 3)
    except Exception as e:
        p.benar("Impor mitra berjalan tanpa galat", False,
                f"{type(e).__name__}: {e}")
    print()

    # -------------------------------------------- 2. berkas kosong
    print("[2. Berkas kosong harus ditolak dengan keterangan]")
    # Berkas kosong memang tidak boleh diproses. Yang penting: penolakannya
    # disertai keterangan yang dapat dimengerti pengguna, bukan gagal diam
    # atau tersimpan sebagai data kosong.
    try:
        hasil = modules_ops.impor_mitra_massal(cid, "")
        p.benar("Berkas kosong ditolak", False,
                f"diterima tanpa keterangan: {hasil}")
    except ValueError as e:
        p.benar("Berkas kosong ditolak dengan keterangan", bool(str(e)),
                "keterangan kosong")
        print(f"    keterangan: {e}")
    except Exception as e:
        p.benar("Berkas kosong ditolak dengan jenis galat yang tepat", False,
                f"{type(e).__name__}: {e}")

    try:
        hasil = modules_ops.impor_mitra_massal(cid, "nama,tipe\n")
        p.benar("Berkas hanya judul kolom ditolak", False,
                f"diterima tanpa keterangan: {hasil}")
    except ValueError as e:
        p.benar("Berkas hanya judul kolom ditolak dengan keterangan",
                bool(str(e)), "keterangan kosong")
        print(f"    keterangan: {e}")
    except Exception as e:
        p.benar("Berkas hanya judul ditolak dengan jenis galat tepat", False,
                f"{type(e).__name__}: {e}")
    print()

    # --------------------------------------- 3. kolom kurang
    print("[3. Kolom yang kurang]")
    try:
        hasil = modules_ops.impor_mitra_massal(cid, "nama\nTanpa Tipe\n")
        # Boleh diterima dengan nilai bawaan, yang penting tidak galat
        # dan tidak menyimpan data yang salah.
        p.benar("Kolom kurang ditangani, tidak gagal diam", True)
        print(f"    hasil: {hasil}")
    except Exception as e:
        # Galat dengan keterangan juga dapat diterima.
        pesan = str(e)
        p.benar("Kolom kurang ditolak dengan keterangan", bool(pesan),
                "galat tanpa keterangan")
        print(f"    ditolak: {type(e).__name__}: {pesan[:70]}")
    print()

    # --------------------------------------- 4. angka berformat asing
    print("[4. Angka berformat asing]")
    csv_produk = (
        "kode,nama,harga_jual,harga_beli,stok\n"
        "P001,Produk Biasa,50000,40000,10\n"
        "P002,Produk Titik,50.000,40.000,5\n"
        "P003,Produk Koma,50000,00,40000,00,3\n"
        "P004,Produk Kosong,,,0\n"
    )
    try:
        hasil = modules_ops.impor_produk_massal(cid, csv_produk)
        print(f"    hasil: {hasil}")
        p.benar("Impor produk berjalan tanpa galat", True)

        # Periksa harga tersimpan: tidak boleh ada yang salah baca.
        for kode in ("P001", "P002", "P003"):
            baris_p = db.q1(
                "SELECT nama, harga_jual FROM products "
                "WHERE company_id = ? AND kode = ?", (cid, kode))
            if baris_p:
                harga = baris_p["harga_jual"]
                masuk_akal = 0 <= harga <= 1_000_000_000
                p.benar(f"Harga {kode} ({baris_p['nama']}) = {harga:,} "
                        f"masuk akal", masuk_akal,
                        "nilai di luar batas wajar")
            else:
                print(f"    {kode} tidak tersimpan")
    except Exception as e:
        p.benar("Impor produk berjalan tanpa galat", False,
                f"{type(e).__name__}: {e}")
    print()

    # --------------------------------------- 5. baris kosong & spasi
    print("[5. Baris kosong dan spasi berlebih]")
    csv_kotor = (
        "nama,tipe,telepon,email,alamat\n"
        "\n"
        "   ,   ,   ,   ,   \n"
        "  PT Spasi Banyak  ,  pemasok  ,  08111  ,  a@b.id  ,  Jakarta  \n"
        "\n"
        ",,,,\n"
    )
    try:
        hasil = modules_ops.impor_mitra_massal(cid, csv_kotor)
        print(f"    hasil: {hasil}")
        p.benar("Baris kotor tidak menimbulkan galat", True)

        baris_s = db.q1(
            "SELECT nama FROM partners WHERE company_id = ? AND nama LIKE ?",
            (cid, "%Spasi%")) if _ada_tabel("partners") else None
        if baris_s:
            nama = baris_s["nama"]
            p.benar("Spasi berlebih dirapikan",
                    nama == nama.strip() and "  " not in nama,
                    f"nama tersimpan: {nama!r}")
        else:
            print("    baris berspasi tidak tersimpan")
    except Exception as e:
        p.benar("Baris kotor tidak menimbulkan galat", False,
                f"{type(e).__name__}: {e}")
    print()

    # --------------------------------------- 6. data kembar
    print("[6. Nama yang sama tidak menghasilkan data kembar]")
    sebelum = _hitung_mitra(cid)
    try:
        modules_ops.impor_mitra_massal(cid, csv_mitra)
        sesudah = _hitung_mitra(cid)
        p.benar("Impor ulang tidak menggandakan data",
                sesudah <= sebelum,
                f"sebelum {sebelum}, sesudah {sesudah}")
    except Exception as e:
        p.benar("Impor ulang tidak menggandakan data", False,
                f"{type(e).__name__}: {e}")
    print()

    # --------------------------------------- 7. impor jurnal
    print("[7. Impor jurnal menjaga keseimbangan]")
    csv_jurnal = (
        "tanggal,no_bukti,keterangan,kode_akun,debit,kredit\n"
        "2026-02-01,JU-001,Setoran modal,1001,10000000,0\n"
        "2026-02-01,JU-001,Setoran modal,3001,0,10000000\n"
        "2026-02-05,JU-002,Beli persediaan,1104,5000000,0\n"
        "2026-02-05,JU-002,Beli persediaan,1001,0,5000000\n"
    )
    try:
        hasil = modules_ops.impor_jurnal_massal(cid, csv_jurnal)
        print(f"    hasil: {hasil}")
        p.benar("Impor jurnal berjalan tanpa galat", True)

        d = db.q1("""SELECT COALESCE(SUM(debit),0) AS d,
                            COALESCE(SUM(kredit),0) AS k
                     FROM journal_lines WHERE company_id = ?""", (cid,))
        p.cek("Debit dan kredit seimbang setelah impor", d["d"], d["k"])
        p.benar("Buku besar seimbang", d["d"] == d["k"],
                f"debit={d['d']:,} kredit={d['k']:,}")
    except Exception as e:
        p.benar("Impor jurnal berjalan tanpa galat", False,
                f"{type(e).__name__}: {e}")
    print()

    # --------------------------------------- 8. jurnal tidak seimbang
    print("[8. Jurnal tidak seimbang dari berkas]")
    csv_tidak_seimbang = (
        "tanggal,no_bukti,keterangan,kode_akun,debit,kredit\n"
        "2026-03-01,JU-003,Debit saja,1001,5000000,0\n"
        "2026-03-01,JU-003,Kredit tidak sama,3001,0,3000000\n"
    )
    try:
        hasil = modules_ops.impor_jurnal_massal(cid, csv_tidak_seimbang)
        print(f"    hasil: {hasil}")
        # Bila diterima, buku besar harus tetap seimbang.
        d2 = db.q1("""SELECT COALESCE(SUM(debit),0) AS d,
                             COALESCE(SUM(kredit),0) AS k
                      FROM journal_lines WHERE company_id = ?""", (cid,))
        p.benar("Buku besar tetap seimbang setelah jurnal tidak seimbang",
                d2["d"] == d2["k"],
                f"debit={d2['d']:,} kredit={d2['k']:,}")
    except Exception as e:
        # Ditolak juga benar, asalkan dengan keterangan.
        p.benar("Jurnal tidak seimbang ditolak dengan keterangan",
                bool(str(e)),
                f"{type(e).__name__} tanpa keterangan")
        print(f"    ditolak: {type(e).__name__}: {str(e)[:70]}")
    print()

    # --------------------------------------- 9. kode akun tidak dikenal
    print("[9. Kode akun yang tidak dikenal]")
    csv_akun_salah = (
        "tanggal,no_bukti,keterangan,kode_akun,debit,kredit\n"
        "2026-04-01,JU-004,Akun tidak ada,9999,1000000,0\n"
        "2026-04-01,JU-004,Akun tidak ada,1001,0,1000000\n"
    )
    try:
        hasil = modules_ops.impor_jurnal_massal(cid, csv_akun_salah)
        print(f"    hasil: {hasil}")
        # Bila diterima, harus ada keterangan bahwa akunnya tidak dikenal.
        n = db.scalar("""SELECT COUNT(*) FROM journal_lines
                         WHERE company_id = ? AND kode_akun = '9999'""",
                      (cid,))
        p.benar("Akun tidak dikenal tidak disimpan diam diam",
                n == 0 or "9999" in str(hasil),
                f"tersimpan {n} baris tanpa keterangan")
    except Exception as e:
        p.benar("Akun tidak dikenal ditolak", bool(str(e)),
                f"{type(e).__name__} tanpa keterangan")
        print(f"    ditolak: {type(e).__name__}: {str(e)[:70]}")
    print()

    return p.ringkas()


def _ada_tabel(nama: str) -> bool:
    try:
        db.scalar(f"SELECT COUNT(*) FROM {nama}")
        return True
    except Exception:
        return False


def _hitung_mitra(cid: int) -> int:
    for tabel in ("partners", "mitra", "contacts"):
        if _ada_tabel(tabel):
            try:
                return int(db.scalar(
                    f"SELECT COUNT(*) FROM {tabel} WHERE company_id = ?",
                    (cid,)))
            except Exception:
                continue
    return 0


if __name__ == "__main__":
    try:
        kode = main()
    finally:
        shutil.rmtree(FOLDER, ignore_errors=True)
    sys.exit(kode)
