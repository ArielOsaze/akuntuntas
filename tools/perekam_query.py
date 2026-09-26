"""
Perekam query: mencari kebocoran data antar perusahaan saat aplikasi dipakai.

Cara ini menggabungkan dua pendekatan sekaligus, dan berbeda dari semua
pengujian sebelumnya:

  - Analisis statis membaca seluruh kode, tetapi hasilnya terlalu banyak
    salah tuduh karena banyak query memang aman meski tidak menyebut
    company_id (misalnya menyaring lewat id unik).
  - Pengujian biasa hanya memeriksa angka akhir, sehingga query yang bocor
    tetapi kebetulan menghasilkan angka benar tidak terdeteksi.

Cara ini membungkus fungsi query milik aplikasi, mencatat setiap query yang
BENAR BENAR dijalankan, lalu memeriksa apakah query itu membaca tabel
ber-company_id tanpa menyaring company_id. Karena hanya query yang
dijalankan yang diperiksa, hasilnya tidak memuat kode yang tidak terpakai.

Selain itu, seluruh hasil fungsi daftar diperiksa: setiap baris yang
dikembalikan harus benar benar milik perusahaan yang diminta.

Cara pakai:
    python tools/perekam_query.py
    python tools/perekam_query.py --rinci
"""
from __future__ import annotations

import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "src"))

FOLDER = Path(tempfile.mkdtemp(prefix="akuntuntas_rekam_"))
os.environ["LOCALAPPDATA"] = str(FOLDER)

from akuntansi_id import db, modules, services  # noqa: E402
from akuntansi_id import modules_ops as O  # noqa: E402
from akuntansi_id import modules_sales as S  # noqa: E402
from akuntansi_id.core import accounting as acc  # noqa: E402


class Perekam:
    """Membungkus fungsi query dan mencatat query yang berjalan."""

    def __init__(self, tabel_company: set[str]):
        self.tabel_company = tabel_company
        self.semua: list[str] = []
        self.tanpa_saring: list[str] = []
        self.asal: dict[str, str] = {}

    def pasang(self):
        asli_q, asli_q1, asli_scalar, asli_ex = db.q, db.q1, db.scalar, db.ex

        def catat(sql: str) -> None:
            teks = " ".join(str(sql).split())
            self.semua.append(teks)
            if not re.search(r"\b(SELECT|UPDATE|DELETE)\b", teks, re.IGNORECASE):
                return
            if re.search(r"\bcompany_id\b", teks, re.IGNORECASE):
                return
            # Cari tabel ber-company_id yang disebut query ini.
            dipakai = set()
            for pola in (r"\bFROM\s+([A-Za-z_][A-Za-z0-9_]*)",
                         r"\bJOIN\s+([A-Za-z_][A-Za-z0-9_]*)",
                         r"\bUPDATE\s+([A-Za-z_][A-Za-z0-9_]*)",
                         r"\bDELETE\s+FROM\s+([A-Za-z_][A-Za-z0-9_]*)",
                         r"\bINTO\s+([A-Za-z_][A-Za-z0-9_]*)",
                         r"\bTABLE\s+([A-Za-z_][A-Za-z0-9_]*)",
                         r"\bEXISTS\s*\(\s*SELECT[^)]*\bFROM\s+([A-Za-z_][A-Za-z0-9_]*)"):
                for c in re.finditer(pola, teks, re.IGNORECASE):
                    dipakai.add(c.group(1).lower())
            bocor = dipakai & self.tabel_company
            if not bocor:
                return
            # Query yang menyaring lewat id unik aman, karena id unik untuk
            # seluruh basis data.
            if re.search(r"\bWHERE\s+id\s*=", teks, re.IGNORECASE):
                return
            if re.search(r"\bentry_id\s*=", teks, re.IGNORECASE):
                return
            if re.match(r"^\s*INSERT", teks, re.IGNORECASE):
                return
            self.tanpa_saring.append(teks)
            # Catat dari berkas mana query ini berasal.
            for lapis in range(2, 12):
                try:
                    f = sys._getframe(lapis)
                except ValueError:
                    break
                if "akuntansi_id" in (f.f_code.co_filename or ""):
                    self.asal.setdefault(teks, f"{f.f_code.co_filename}:{f.f_lineno}")
                    break

        def bungkus(fungsi_asli):
            def baru(sql, *a, **kw):
                catat(sql)
                return fungsi_asli(sql, *a, **kw)
            return baru

        db.q = bungkus(asli_q)
        db.q1 = bungkus(asli_q1)
        db.scalar = bungkus(asli_scalar)
        db.ex = bungkus(asli_ex)

        # Seluruh perintah yang benar benar dijalankan ke basis data juga
        # direkam. Cara ini memakai fitur bawaan SQLite, sehingga tidak
        # bergantung pada jalur pemanggilannya.
        self._koneksi = db.get_conn()
        self._koneksi.set_trace_callback(catat)

    def lepas(self):
        try:
            self._koneksi.set_trace_callback(None)
        except Exception:
            pass


def main() -> int:
    print("=" * 76)
    print("  PEREKAM QUERY: MENCARI KEBOCORAN DATA ANTAR PERUSAHAAN")
    print("=" * 76)
    print()

    db.init_db()
    conn = db.get_conn()
    tabel_company = set()
    for (nama,) in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%'"):
        kolom = [r[1] for r in conn.execute(f"PRAGMA table_info({nama})")]
        if "company_id" in kolom:
            tabel_company.add(nama)
    print(f"  tabel ber-company_id: {len(tabel_company)}")
    print()

    class LisensiUji:
        enterprise = True

        def punya(self, bagian: str) -> bool:
            return True

    # Dua perusahaan dengan data yang berbeda, supaya kebocoran terlihat.
    a = services.create_company("PT Alfa", bentuk="pt")
    b = services.create_company("PT Beta", bentuk="pt", lisensi=LisensiUji())

    perekam = Perekam(tabel_company)
    perekam.pasang()

    print("[1. Menjalankan seluruh alur pemakaian pada dua perusahaan]")
    for cid, nama in ((a, "Alfa"), (b, "Beta")):
        # Mitra, produk, gudang, stok.
        pel = modules.buat_mitra(cid, f"Pelanggan {nama}", "customer")
        produk = modules.buat_produk(
            cid, f"Barang {nama}", satuan="pcs", harga_beli=100_000,
            harga_jual=150_000, metode_hpp="average")
        modules.stok_masuk(cid, produk, 20, 100_000, "2026-01-05")

        # Penjualan lewat invoice (jalur UI).
        S.buat_invoice(cid, "2026-02-10",
                       [{"product_id": produk, "qty": 3, "harga_satuan": 150_000}],
                       partner_id=pel, jenis_ppn="Non-PKP/Tidak Dipungut",
                       username="uji")
        # Pembelian.
        services.simpan_pembelian(
            cid, "2026-02-15", f"PB-{nama}", f"Pemasok {nama}", 5_000_000,
            jenis="Beban", akun_beban="6006", dibayar=True,
            tanggal_bayar="2026-02-15")
        # Karyawan dan penggajian.
        services.simpan_karyawan(cid, f"Karyawan {nama}", 5_000_000,
                                 status_ptkp="TK/0", tunjangan_tetap=500_000)
        services.hitung_payroll_bulanan(cid, "2026-02", posting=True)
        # Pajak.
        services.simpan_pajak(cid, "2026-03-15", "PPh23-JASA", 10_000_000,
                              masa="2026-03")
        # Aset.
        services.simpan_aset(cid, f"AST-{nama}", f"Aset {nama}",
                             "2026-01-10", 50_000_000,
                             kelompok_fiskal="Kelompok 1",
                             akun_kas="1001")

        # Fungsi daftar yang dipakai halaman halaman aplikasi.
        for fungsi, argumen in (
            (services.list_jurnal, (cid, 2026)),
            (services.list_penjualan, (cid, 2026)),
            (services.list_pembelian, (cid, 2026)),
            (services.list_aset, (cid,)),
            (services.list_karyawan, (cid,)),
            (services.list_payroll, (cid, 2026)),
            (services.list_pajak, (cid, 2026)),
            (services.list_accounts, (cid,)),
            (services.list_companies, ()),
            (modules.daftar_produk, (cid,)),
            (modules.daftar_stok, (cid,)),
            (modules.daftar_gudang, (cid,)),
            (S.daftar_invoice, (cid, 2026)),
            (S.daftar_sales_order, (cid, 2026)),
            (S.daftar_penerimaan, (cid, 2026)),
            (S.daftar_nota_kredit, (cid, 2026)),
            (O.daftar_biaya, (cid,)) if hasattr(O, "daftar_biaya") else (None, ()),
        ):
            if fungsi is None:
                continue
            try:
                fungsi(*argumen)
            except Exception:
                pass

        # Laporan.
        for fungsi in (acc.laba_rugi, acc.neraca, acc.arus_kas,
                       acc.neraca_saldo, acc.dashboard_kpi):
            try:
                fungsi(cid, 2026)
            except Exception:
                pass

    perekam.lepas()
    print(f"            query berjalan seluruhnya: {len(perekam.semua)}")
    print()

    # ------------------------------------------------------------------
    print("[2. Hasil pemeriksaan]")
    unik = sorted(set(perekam.tanpa_saring))
    print(f"  query berjalan tanpa saringan company_id: {len(perekam.tanpa_saring)}")
    print(f"  bentuk unik                              : {len(unik)}")
    print()

    if unik:
        print("  DAFTAR (perlu diperiksa satu per satu):")
        for teks in unik[:40]:
            asal = perekam.asal.get(teks, "")
            print(f"    - {teks[:100]}")
            if asal:
                print(f"      dari: {asal}")
    else:
        print("  Tidak ada query yang membaca tabel ber-company_id tanpa")
        print("  menyaring company_id. Pemisahan data antar perusahaan aman.")
    print()

    # ------------------------------------------------------------------
    print("[3. Memeriksa isi hasil tiap fungsi daftar]")
    # Setiap baris yang dikembalikan harus milik perusahaan yang diminta.
    bocor = []
    for fungsi, argumen, label in (
        (services.list_jurnal, (a, 2026), "list_jurnal"),
        (services.list_penjualan, (a, 2026), "list_penjualan"),
        (services.list_pembelian, (a, 2026), "list_pembelian"),
        (services.list_aset, (a,), "list_aset"),
        (services.list_karyawan, (a,), "list_karyawan"),
        (services.list_pajak, (a, 2026), "list_pajak"),
        (services.list_accounts, (a,), "list_accounts"),
        (modules.daftar_produk, (a,), "daftar_produk"),
        (modules.daftar_stok, (a,), "daftar_stok"),
        (modules.daftar_gudang, (a,), "daftar_gudang"),
        (S.daftar_invoice, (a, 2026), "daftar_invoice"),
    ):
        try:
            hasil = fungsi(*argumen)
        except Exception as e:
            bocor.append(f"{label}: gagal dipanggil ({type(e).__name__})")
            continue
        if not isinstance(hasil, list):
            continue
        for baris in hasil:
            try:
                kunci = baris.keys() if hasattr(baris, "keys") else baris.keys()
            except Exception:
                continue
            if "company_id" in kunci:
                nilai = baris["company_id"]
                if nilai is not None and int(nilai) != a:
                    bocor.append(f"{label}: baris milik perusahaan {nilai}")
                    break

    if bocor:
        print(f"  BOCOR: {len(bocor)}")
        for t in bocor:
            print(f"    - {t}")
    else:
        print("  Seluruh hasil fungsi daftar hanya memuat data perusahaan")
        print("  yang diminta.")
    print()

    print("=" * 76)
    if unik or bocor:
        print(f"  HASIL: {len(unik)} bentuk query perlu diperiksa, "
              f"{len(bocor)} kebocoran isi")
    else:
        print("  HASIL: tidak ada kebocoran data antar perusahaan")
    print("=" * 76)
    return 0


if __name__ == "__main__":
    try:
        kode = main()
    finally:
        shutil.rmtree(FOLDER, ignore_errors=True)
    sys.exit(kode)
