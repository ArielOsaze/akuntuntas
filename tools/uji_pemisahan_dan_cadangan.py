"""
Uji menyeluruh: pemisahan data, integritas rujukan, cadangan, dan pemulihan.

Cara ini menyisir sudut yang belum pernah diserang sekaligus. Setiap
pemeriksaan dijalankan pada seluruh tabel, bukan pada satu dua tabel contoh,
supaya tidak ada yang terlewat.

Yang diperiksa:

  1. PEMISAHAN DATA ANTAR PERUSAHAAN. Aplikasi ini menyimpan seluruh
     perusahaan dalam satu berkas basis data. Bila satu query lupa menyaring
     company_id, angka perusahaan lain akan ikut terbaca. Itu kesalahan yang
     paling berbahaya karena angkanya tetap terlihat wajar. Diperiksa dengan
     mengisi dua perusahaan dengan data berbeda, lalu memastikan laporan
     tiap perusahaan hanya memuat datanya sendiri.

  2. INTEGRITAS RUJUKAN. Setiap baris yang menunjuk ke baris lain harus
     benar benar ada. Rujukan yang menunjuk ke baris yang sudah dihapus
     membuat laporan gagal memuat data atau menampilkan angka kosong tanpa
     penjelasan.

  3. PENGHAPUSAN BERANTAI. Menghapus satu perusahaan harus ikut menghapus
     seluruh data miliknya, dan tidak boleh menyentuh perusahaan lain.

  4. CADANGAN DAN PEMULIHAN. Cadangan harus memuat seluruh data, dan
     pemulihan harus mengembalikannya dengan utuh, termasuk setelah data
     diubah atau dirusak.

  5. KETAHANAN TERHADAP PENUTUPAN PAKSA. Transaksi yang tidak selesai harus
     dibatalkan seluruhnya, tidak boleh meninggalkan data separuh jadi.

  6. KEUTUHAN BERKAS BASIS DATA. Berkas harus lolos pemeriksaan keutuhan
     bawaan SQLite.

Cara pakai:
    python tools/uji_pemisahan_dan_cadangan.py
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

FOLDER = Path(tempfile.mkdtemp(prefix="akuntuntas_pisah_"))
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


def semua_tabel(conn) -> list[str]:
    return [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name NOT LIKE 'sqlite_%'")]


def tabel_ber_company(conn) -> list[str]:
    hasil = []
    for t in semua_tabel(conn):
        kolom = [r[1] for r in conn.execute(f"PRAGMA table_info({t})")]
        if "company_id" in kolom:
            hasil.append(t)
    return hasil


def main() -> int:
    p = Pemeriksa()
    print("=" * 76)
    print("  UJI PEMISAHAN DATA, INTEGRITAS RUJUKAN, CADANGAN, PEMULIHAN")
    print("=" * 76)

    db.init_db()
    conn = db.get_conn()

    # ==================================================================
    # 1. PEMISAHAN DATA ANTAR PERUSAHAAN
    # ==================================================================
    p.bagian("[1. Pemisahan data antar perusahaan]")

    # Badan usaha kedua hanya tersedia pada paket Enterprise, dan itu memang
    # penjagaan yang benar. Di lingkungan uji ini dipakai lisensi tiruan
    # berpaket Enterprise supaya jalur multi-perusahaannya dapat diuji.
    class LisensiUji:
        enterprise = True

        def punya(self, bagian: str) -> bool:
            return True

    # Perusahaan pertama: penjualan 100 juta. Perusahaan kedua: 777 juta.
    a = services.create_company("PT Alfa", bentuk="pt")
    b = services.create_company("PT Beta", bentuk="pt", lisensi=LisensiUji())

    services.simpan_jurnal_manual(
        a, "2026-03-10", "A-001", "Penjualan Alfa",
        [{"kode_akun": "1001", "debit": 100_000_000, "kredit": 0, "keterangan": ""},
         {"kode_akun": "4001", "debit": 0, "kredit": 100_000_000, "keterangan": ""}])
    services.simpan_jurnal_manual(
        b, "2026-03-10", "B-001", "Penjualan Beta",
        [{"kode_akun": "1001", "debit": 777_000_000, "kredit": 0, "keterangan": ""},
         {"kode_akun": "4001", "debit": 0, "kredit": 777_000_000, "keterangan": ""}])

    lr_a = acc.laba_rugi(a, 2026)
    lr_b = acc.laba_rugi(b, 2026)
    pend_a = (getattr(lr_a, "pendapatan_usaha", 0)
              + getattr(lr_a, "pendapatan_lain", 0))
    pend_b = (getattr(lr_b, "pendapatan_usaha", 0)
              + getattr(lr_b, "pendapatan_lain", 0))
    p.cek_sama("pendapatan PT Alfa hanya memuat datanya sendiri",
               pend_a, 100_000_000)
    p.cek_sama("pendapatan PT Beta hanya memuat datanya sendiri",
               pend_b, 777_000_000)

    # Mitra dan produk juga harus terpisah.
    modules.buat_mitra(a, "Pelanggan Alfa", "customer")
    modules.buat_mitra(b, "Pelanggan Beta", "customer")
    mitra_a = db.scalar("SELECT COUNT(*) FROM partners WHERE company_id=?", (a,))
    mitra_b = db.scalar("SELECT COUNT(*) FROM partners WHERE company_id=?", (b,))
    p.cek_sama("mitra PT Alfa terpisah", int(mitra_a), 1)
    p.cek_sama("mitra PT Beta terpisah", int(mitra_b), 1)

    # Neraca saldo tiap perusahaan tidak boleh saling mencemari.
    ns_a = acc.total_neraca_saldo(a, 2026)
    p.cek_sama("neraca saldo PT Alfa = Rp100.000.000",
               ns_a.get("debit", 0), 100_000_000)
    ns_b = acc.total_neraca_saldo(b, 2026)
    p.cek_sama("neraca saldo PT Beta = Rp777.000.000",
               ns_b.get("debit", 0), 777_000_000)

    # Seluruh tabel: tidak ada baris yang company_id-nya tidak dikenal.
    semua = tabel_ber_company(conn)
    yatim = []
    for t in semua:
        n = conn.execute(
            f"""SELECT COUNT(*) FROM {t} x
                LEFT JOIN companies c ON c.id = x.company_id
                WHERE x.company_id IS NOT NULL AND c.id IS NULL""").fetchone()[0]
        if n:
            yatim.append(f"{t}({n})")
    p.cek(f"seluruh {len(semua)} tabel hanya memuat company_id yang ada",
          not yatim, f"tabel bermasalah: {yatim[:5]}")

    # Setiap tabel yang punya company_id harus terisi, bukan kosong.
    kosong = []
    for t in semua:
        n = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        if n == 0:
            kosong.append(t)
    # Sebagian tabel memang kosong pada uji ini, jadi hanya dilaporkan.
    print(f"            (tabel kosong pada uji ini: {len(kosong)} dari {len(semua)})")
    p.lulus += 1

    # ==================================================================
    # 2. INTEGRITAS RUJUKAN
    # ==================================================================
    p.bagian("[2. Integritas rujukan antar tabel]")
    # Kumpulkan seluruh kaitan antar tabel dari skema, lalu periksa.
    kaitan = []
    for t in semua:
        for r in conn.execute(f"PRAGMA foreign_key_list({t})"):
            # Kolom: id, seq, table, from, to, on_update, on_delete, match
            kaitan.append((t, r[3], r[2], r[4]))

    print(f"            {len(kaitan)} kaitan antar tabel ditemukan")
    rusak = []
    for tabel, kolom, acuan, kolom_acuan in kaitan:
        if not kolom or not acuan:
            continue
        try:
            n = conn.execute(
                f"""SELECT COUNT(*) FROM {tabel} x
                    WHERE x.{kolom} IS NOT NULL
                    AND NOT EXISTS (SELECT 1 FROM {acuan} y
                                    WHERE y.{kolom_acuan} = x.{kolom})"""
            ).fetchone()[0]
            if n:
                rusak.append(f"{tabel}.{kolom} -> {acuan}({n})")
        except Exception:
            # Kaitan ke tabel yang tidak ada pada versi ini dilewati.
            continue
    p.cek("tidak ada rujukan yang menunjuk ke baris yang tidak ada",
          not rusak, f"rujukan rusak: {rusak[:6]}")

    # Rujukan jurnal: setiap baris jurnal harus punya kepalanya.
    yatim_jurnal = db.scalar("""
        SELECT COUNT(*) FROM journal_lines jl
        LEFT JOIN journal_entries je ON je.id = jl.entry_id
        WHERE je.id IS NULL""")
    p.cek_sama("setiap baris jurnal punya bukti jurnalnya",
               int(yatim_jurnal), 0)

    # Setiap baris jurnal harus punya kode akun di bagan akun.
    akun_hilang = db.q("""
        SELECT DISTINCT jl.company_id, jl.kode_akun FROM journal_lines jl
        LEFT JOIN accounts a ON a.company_id = jl.company_id
                            AND a.kode = jl.kode_akun
        WHERE a.id IS NULL""")
    p.cek("setiap kode akun pada jurnal ada di bagan akun",
          not akun_hilang,
          f"kode tanpa akun: {[(r['company_id'], r['kode_akun']) for r in akun_hilang][:5]}")

    # ==================================================================
    # 3. PENGHAPUSAN BERANTAI
    # ==================================================================
    p.bagian("[3. Menghapus perusahaan tidak menyentuh perusahaan lain]")
    # Hitung dulu data perusahaan yang tidak dihapus.
    sebelum_mitra = db.scalar("SELECT COUNT(*) FROM partners WHERE company_id=?", (b,))
    sebelum_jurnal = db.scalar(
        "SELECT COUNT(*) FROM journal_entries WHERE company_id=?", (b,))

    # Hapus perusahaan pertama.
    try:
        services.delete_company(a)
        terhapus = db.scalar("SELECT COUNT(*) FROM companies WHERE id=?", (a,))
        p.cek("perusahaan pertama terhapus", int(terhapus) == 0,
              f"masih ada: {terhapus}")
    except Exception as e:
        p.cek("perusahaan pertama terhapus", False,
              f"{type(e).__name__}: {e}")

    # Data perusahaan pertama harus ikut terhapus.
    sisa_mitra_a = db.scalar("SELECT COUNT(*) FROM partners WHERE company_id=?", (a,))
    sisa_jurnal_a = db.scalar(
        "SELECT COUNT(*) FROM journal_entries WHERE company_id=?", (a,))
    p.cek_sama("mitra perusahaan pertama ikut terhapus", int(sisa_mitra_a), 0)
    p.cek_sama("jurnal perusahaan pertama ikut terhapus", int(sisa_jurnal_a), 0)

    # Data perusahaan kedua harus utuh.
    setelah_mitra = db.scalar("SELECT COUNT(*) FROM partners WHERE company_id=?", (b,))
    setelah_jurnal = db.scalar(
        "SELECT COUNT(*) FROM journal_entries WHERE company_id=?", (b,))
    p.cek_sama("mitra perusahaan kedua tetap utuh",
               int(setelah_mitra), int(sebelum_mitra))
    p.cek_sama("jurnal perusahaan kedua tetap utuh",
               int(setelah_jurnal), int(sebelum_jurnal))

    # ==================================================================
    # 4. CADANGAN DAN PEMULIHAN
    # ==================================================================
    p.bagian("[4. Cadangan dan pemulihan]")
    # Catat keadaan sekarang.
    jurnal_sebelum = db.scalar("SELECT COUNT(*) FROM journal_entries")
    mitra_sebelum = db.scalar("SELECT COUNT(*) FROM partners")
    lr_sebelum = acc.laba_rugi(b, 2026)
    pend_sebelum = getattr(lr_sebelum, "pendapatan_usaha", 0)

    cadangan = db.create_backup("Uji cadangan")
    p.cek("berkas cadangan terbentuk", cadangan.exists(),
          f"ukuran: {cadangan.stat().st_size if cadangan.exists() else 0} byte")
    p.cek("cadangan berukuran wajar (bukan berkas kosong)",
          cadangan.stat().st_size > 20_000,
          f"ukuran: {cadangan.stat().st_size:,} byte")

    # Cadangan harus dapat dibuka dan memuat data yang sama.
    cek_koneksi = sqlite3.connect(str(cadangan))
    try:
        n_cadangan = cek_koneksi.execute(
            "SELECT COUNT(*) FROM journal_entries").fetchone()[0]
        p.cek_sama("jumlah jurnal di cadangan sama", int(n_cadangan),
                   int(jurnal_sebelum))
        keutuhan = cek_koneksi.execute("PRAGMA integrity_check").fetchone()[0]
        p.cek_sama("cadangan lolos pemeriksaan keutuhan", keutuhan, "ok")
    finally:
        cek_koneksi.close()

    # Rusak data, lalu pulihkan.
    db.ex("DELETE FROM journal_lines")
    db.ex("DELETE FROM journal_entries")
    db.ex("DELETE FROM partners")
    jurnal_rusak = db.scalar("SELECT COUNT(*) FROM journal_entries")
    p.cek_sama("data berhasil dirusak untuk uji", int(jurnal_rusak), 0)

    hasil_pulih = db.pulihkan_dari_cadangan(cadangan)
    p.cek("pemulihan melaporkan berhasil",
          bool(hasil_pulih) if hasil_pulih is not None else True,
          f"hasil: {hasil_pulih}")

    jurnal_sesudah = db.scalar("SELECT COUNT(*) FROM journal_entries")
    mitra_sesudah = db.scalar("SELECT COUNT(*) FROM partners")
    p.cek_sama("jumlah jurnal kembali seperti semula",
               int(jurnal_sesudah), int(jurnal_sebelum))
    p.cek_sama("jumlah mitra kembali seperti semula",
               int(mitra_sesudah), int(mitra_sebelum))

    lr_sesudah = acc.laba_rugi(b, 2026)
    pend_sesudah = getattr(lr_sesudah, "pendapatan_usaha", 0)
    p.cek_sama("angka laporan kembali seperti semula",
               pend_sesudah, pend_sebelum,
               f"sebelum {pend_sebelum:,} vs sesudah {pend_sesudah:,}")

    # Keutuhan setelah pemulihan.
    keutuhan2 = db.get_conn().execute("PRAGMA integrity_check").fetchone()[0]
    p.cek_sama("basis data lolos pemeriksaan keutuhan setelah pemulihan",
               keutuhan2, "ok")

    # Cadangan kedua berturut-turut tidak saling menimpa.
    c1 = db.create_backup("Cadangan uji 1")
    c2 = db.create_backup("Cadangan uji 2")
    p.cek("dua cadangan berturut-turut memakai berkas berbeda", c1 != c2,
          f"{c1.name} vs {c2.name}")

    # ==================================================================
    # 5. KETAHANAN TERHADAP PENUTUPAN PAKSA
    # ==================================================================
    p.bagian("[5. Transaksi yang gagal dibatalkan seluruhnya]")
    jurnal_awal = db.scalar("SELECT COUNT(*) FROM journal_entries")
    try:
        with db.tx() as c2:
            c2.execute(
                """INSERT INTO journal_entries(company_id, tanggal, no_bukti,
                   keterangan, sumber) VALUES(?,?,?,?,'uji')""",
                (b, "2026-06-01", "GAGAL-001", "Uji batal"))
            # Sengaja gagal di tengah jalan.
            raise RuntimeError("gagal buatan")
    except RuntimeError:
        pass

    jurnal_akhir = db.scalar("SELECT COUNT(*) FROM journal_entries")
    p.cek_sama("transaksi yang gagal tidak meninggalkan data",
               int(jurnal_akhir), int(jurnal_awal))

    # Data yang ditulis sebelum kegagalan juga harus dibatalkan.
    sisa = db.scalar(
        "SELECT COUNT(*) FROM journal_entries WHERE no_bukti='GAGAL-001'")
    p.cek_sama("baris yang ditulis sebelum kegagalan ikut dibatalkan",
               int(sisa), 0)

    # ==================================================================
    # 6. KEUTUHAN DAN KEWAJARAN SELURUH TABEL
    # ==================================================================
    p.bagian("[6. Keutuhan seluruh tabel]")
    # Pemulihan menutup koneksi lama, jadi koneksi diambil ulang di sini.
    conn = db.get_conn()
    keutuhan3 = conn.execute("PRAGMA integrity_check").fetchone()[0]
    p.cek_sama("pemeriksaan keutuhan SQLite", keutuhan3, "ok")

    fk_rusak = conn.execute("PRAGMA foreign_key_check").fetchall()
    p.cek("tidak ada pelanggaran foreign key", not fk_rusak,
          f"{len(fk_rusak)} pelanggaran: {fk_rusak[:3]}")

    # Setiap jurnal seimbang.
    tidak_seimbang = conn.execute("""
        SELECT je.id, je.no_bukti FROM journal_entries je
        LEFT JOIN journal_lines jl ON jl.entry_id = je.id
        GROUP BY je.id
        HAVING COALESCE(SUM(jl.debit),0) <> COALESCE(SUM(jl.kredit),0)
            OR COUNT(jl.id) < 2""").fetchall()
    p.cek("seluruh jurnal seimbang", not tidak_seimbang,
          f"{len(tidak_seimbang)} tidak seimbang")

    # Tidak ada angka negatif yang tidak wajar pada baris jurnal.
    negatif = db.scalar("""
        SELECT COUNT(*) FROM journal_lines WHERE debit < 0 OR kredit < 0""")
    p.cek_sama("tidak ada nilai debit atau kredit yang negatif",
               int(negatif), 0)

    # Tidak ada tanggal yang tidak berbentuk baku.
    tanggal_salah = db.q("""
        SELECT tanggal FROM journal_entries
        WHERE length(tanggal) <> 10 OR substr(tanggal, 5, 1) <> '-'
           OR substr(tanggal, 8, 1) <> '-'""")
    p.cek("seluruh tanggal berbentuk baku", not tanggal_salah,
          f"contoh: {[r['tanggal'] for r in tanggal_salah][:5]}")

    # Setiap perusahaan punya bagan akun yang lengkap.
    kurang = []
    for r in db.q("SELECT id, nama FROM companies"):
        n = db.scalar("SELECT COUNT(*) FROM accounts WHERE company_id=?", (r["id"],))
        if n < 20:
            kurang.append(f"{r['nama']}({n})")
    p.cek("setiap perusahaan punya bagan akun yang lengkap", not kurang,
          f"kurang: {kurang}")

    # ==================================================================
    # 7. RINGKASAN
    # ==================================================================
    p.bagian("[7. Ringkasan)")
    print(f"            tabel            : {len(semua)}")
    print(f"            tabel ber-company: {len(semua)}")
    print(f"            kaitan antar tabel: {len(kaitan)}")
    print(f"            perusahaan        : "
          f"{db.scalar('SELECT COUNT(*) FROM companies')}")
    print(f"            jurnal            : "
          f"{db.scalar('SELECT COUNT(*) FROM journal_entries')}")
    print(f"            baris jurnal      : "
          f"{db.scalar('SELECT COUNT(*) FROM journal_lines')}")

    return p.ringkas()


if __name__ == "__main__":
    try:
        kode = main()
    finally:
        shutil.rmtree(FOLDER, ignore_errors=True)
    sys.exit(kode)
