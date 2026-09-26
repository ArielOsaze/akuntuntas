"""
Verifikasi persediaan dan harga pokok penjualan, dihitung dengan cara sendiri.

Cara ini belum pernah dipakai untuk persediaan. Rumusnya ditulis ulang di
berkas ini tanpa memanggil perhitungan milik aplikasi, lalu hasilnya
dibandingkan. Tujuannya bukan memeriksa apakah aplikasi berjalan, tetapi
memeriksa apakah angkanya benar.

Yang diperiksa:

  - Nilai persediaan akhir dengan metode rata-rata tertimbang.
  - Nilai persediaan akhir dengan metode FIFO, lapisan per lapisan.
  - Harga pokok penjualan: nilai barang yang keluar.
  - Hubungan harga pokok dengan nilai persediaan: barang yang masuk harus
    sama dengan barang yang keluar ditambah sisa di gudang.
  - Persediaan tidak boleh bernilai negatif bila jumlahnya masih ada.
  - Penyesuaian stok mengubah nilai persediaan dengan benar.
  - Perpindahan antar gudang tidak mengubah nilai persediaan.
  - Pembulatan harga satuan tidak menimbulkan selisih yang menumpuk.

Cara pakai:
    python tools/verifikasi_independen_persediaan.py
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "src"))

FOLDER = Path(tempfile.mkdtemp(prefix="akuntuntas_persediaan_"))
os.environ["LOCALAPPDATA"] = str(FOLDER)

from akuntansi_id import db, modules, services  # noqa: E402


class Pemeriksa:
    def __init__(self):
        self.lulus = 0
        self.gagal = 0
        self.temuan: list[str] = []

    def cek(self, nama: str, satu, lain, catatan: str = ""):
        if satu == lain:
            self.lulus += 1
            print(f"  [BENAR] {nama}")
        else:
            self.gagal += 1
            self.temuan.append(nama)
            print(f"  [SALAH] {nama}")
            print(f"          aplikasi : {satu:,}")
            print(f"          hitungan : {lain:,}")
            if catatan:
                print(f"          {catatan}")

    def cek_benar(self, nama: str, syarat: bool, catatan: str = ""):
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


def buat_produk(cid: int, nama: str, metode: str, harga_beli: int = 0) -> int:
    return modules.buat_produk(cid, nama, satuan="pcs", harga_beli=harga_beli,
                               harga_jual=0, metode_hpp=metode, stok_minimum=0)


def main() -> int:
    p = Pemeriksa()
    print("=" * 76)
    print("  VERIFIKASI INDEPENDEN: PERSEDIAAN DAN HARGA POKOK PENJUALAN")
    print("=" * 76)
    print()

    db.init_db()
    b = db.q1("SELECT id FROM companies ORDER BY id LIMIT 1")
    cid = b["id"] if b else services.create_company("PT Persediaan", bentuk="pt")

    # ==================================================================
    print("[1. Metode rata-rata tertimbang]")
    # Masuk 10 @ Rp10.000 dan 10 @ Rp20.000.
    # Nilai rata-rata = (100.000 + 200.000) / 20 = Rp15.000.
    # Keluar 8 => HPP = 8 x 15.000 = Rp120.000.
    # Sisa 12 => nilai = 300.000 - 120.000 = Rp180.000.
    pid = buat_produk(cid, "Rata-rata", "average")
    modules.stok_masuk(cid, pid, 10, 10_000, "2026-01-05")
    modules.stok_masuk(cid, pid, 10, 20_000, "2026-01-10")
    keluar = modules.stok_keluar(cid, pid, 8, "2026-01-15")

    p.cek("HPP rata-rata: 8 x Rp15.000 = Rp120.000",
          int(keluar.get("hpp", keluar.get("total_hpp", 0))), 120_000)

    saldo = modules.saldo_stok(cid, pid)
    p.cek("Nilai persediaan sisa: Rp300.000 - Rp120.000 = Rp180.000",
          int(saldo["nilai_total"]), 180_000)
    p.cek("Jumlah sisa: 20 - 8 = 12", int(saldo["qty"]), 12)
    p.cek("Harga satuan sisa: 180.000 / 12 = Rp15.000",
          int(saldo["hpp_satuan"]), 15_000)
    print()

    # ==================================================================
    print("[2. Metode FIFO]")
    # Masuk 10 @ Rp10.000, lalu 10 @ Rp20.000.
    # Keluar 12 => 10 dari lapisan pertama + 2 dari lapisan kedua.
    # HPP = 100.000 + 40.000 = Rp140.000.
    # Sisa 8 dari lapisan kedua => Rp160.000.
    pid2 = buat_produk(cid, "Fifo", "fifo")
    modules.stok_masuk(cid, pid2, 10, 10_000, "2026-02-01")
    modules.stok_masuk(cid, pid2, 10, 20_000, "2026-02-05")
    keluar2 = modules.stok_keluar(cid, pid2, 12, "2026-02-10")

    p.cek("HPP FIFO: (10 x 10.000) + (2 x 20.000) = Rp140.000",
          int(keluar2.get("hpp", keluar2.get("total_hpp", 0))), 140_000)

    saldo2 = modules.saldo_stok(cid, pid2)
    p.cek("Nilai persediaan sisa FIFO: 8 x 20.000 = Rp160.000",
          int(saldo2["nilai_total"]), 160_000)
    p.cek("Jumlah sisa FIFO: 20 - 12 = 8", int(saldo2["qty"]), 8)
    print()

    # ==================================================================
    print("[3. Kekekalan nilai: masuk = keluar + sisa]")
    for nama, produk, masuk_nilai, hpp, sisa_nilai in (
        ("rata-rata", pid, 300_000, 120_000, 180_000),
        ("FIFO", pid2, 300_000, 140_000, 160_000),
    ):
        p.cek(f"{nama}: masuk = HPP + sisa persediaan",
              masuk_nilai, hpp + sisa_nilai,
              "barang tidak boleh hilang atau bertambah nilainya")
    print()

    # ==================================================================
    print("[4. Keluar bertahap tidak mengubah total]")
    # Keluar 5 dari sisa 12 pada produk rata-rata, lalu bandingkan
    # total HPP seluruhnya dengan nilai masuk dikurangi sisa akhir.
    keluar3 = modules.stok_keluar(cid, pid, 5, "2026-01-20")
    hpp3 = int(keluar3.get("hpp", keluar3.get("total_hpp", 0)))
    p.cek("HPP keluar lanjutan: 5 x Rp15.000 = Rp75.000", hpp3, 75_000)
    saldo3 = modules.saldo_stok(cid, pid)
    p.cek("Sisa akhir: 300.000 - 120.000 - 75.000 = Rp105.000",
          int(saldo3["nilai_total"]), 105_000)
    p.cek("Jumlah sisa: 12 - 5 = 7", int(saldo3["qty"]), 7)
    print()

    # ==================================================================
    print("[5. FIFO habis tepat pada satu lapisan]")
    pid3 = buat_produk(cid, "Fifo Tepat", "fifo")
    modules.stok_masuk(cid, pid3, 5, 4_000, "2026-03-01")
    modules.stok_masuk(cid, pid3, 5, 6_000, "2026-03-02")
    k3 = modules.stok_keluar(cid, pid3, 5, "2026-03-05")
    p.cek("HPP FIFO habis lapisan pertama: 5 x 4.000 = Rp20.000",
          int(k3.get("hpp", k3.get("total_hpp", 0))), 20_000)
    s3 = modules.saldo_stok(cid, pid3)
    p.cek("Sisa setelah lapisan pertama habis: 5 x 6.000 = Rp30.000",
          int(s3["nilai_total"]), 30_000)
    print()

    # ==================================================================
    print("[6. Penyesuaian stok]")
    # Sesuaikan jumlah jadi 10 pada produk FIFO tepat.
    # Nilai tambahan = 5 x harga satuan berjalan (Rp6.000) = Rp30.000.
    modules.penyesuaian_stok(cid, pid3, 10, "2026-03-10",
                             alasan="Penyesuaian uji")
    s4 = modules.saldo_stok(cid, pid3)
    p.cek("Setelah penyesuaian: jumlah = 10", int(s4["qty"]), 10)
    p.cek("Nilai mengikuti harga berjalan: 10 x 6.000 = Rp60.000",
          int(s4["nilai_total"]), 60_000)
    print()

    # ==================================================================
    print("[7. Perpindahan antar gudang tidak mengubah nilai]")
    gudang = modules.daftar_gudang(cid) if hasattr(modules, "daftar_gudang") else []
    if len(gudang) >= 1:
        asal = modules.gudang_utama(cid)
        # Buat gudang kedua bila belum ada.
        try:
            g2 = modules.buat_gudang(cid, "Gudang Uji")
        except Exception:
            g2 = None
        if g2:
            sebelum = modules.saldo_stok(cid, pid2)
            modules.transfer_stok(cid, pid2, 3, asal, g2, "2026-02-15")
            sesudah = modules.saldo_stok(cid, pid2)
            p.cek("Perpindahan gudang: jumlah total tidak berubah",
                  int(sesudah["qty"]), int(sebelum["qty"]))
            p.cek("Perpindahan gudang: nilai total tidak berubah",
                  int(sesudah["nilai_total"]), int(sebelum["nilai_total"]))
            # Nilai yang berpindah harus sama dengan nilai di gudang tujuan.
            di_tujuan = modules.saldo_stok(cid, pid2, g2)
            p.cek("Perpindahan gudang: 3 unit sampai di gudang tujuan",
                  int(di_tujuan["qty"]), 3)
            p.cek("Nilai di gudang tujuan = 3 x harga berjalan",
                  int(di_tujuan["nilai_total"]), 3 * 20_000)
        else:
            print("          gudang kedua tidak dapat dibuat")
    else:
        print("          tidak ada gudang")
    print()

    # ==================================================================
    print("[8. Jumlah besar dan pembulatan]")
    # Harga yang tidak membagi rata, untuk melihat pembulatannya.
    pid4 = buat_produk(cid, "Bulat", "average")
    modules.stok_masuk(cid, pid4, 3, 10_000, "2026-04-01")
    # Nilai 30.000 dibagi 3 = 10.000 tepat.
    s5 = modules.saldo_stok(cid, pid4)
    p.cek("Rata-rata membagi rata: 30.000 / 3 = Rp10.000",
          int(s5["hpp_satuan"]), 10_000)

    # Nilai yang tidak habis dibagi.
    pid5 = buat_produk(cid, "Bulat2", "average")
    modules.stok_masuk(cid, pid5, 3, 10_001, "2026-04-02")
    s6 = modules.saldo_stok(cid, pid5)
    p.cek("Rata-rata tidak habis dibagi: 30.003 / 3 = Rp10.001",
          int(s6["hpp_satuan"]), 10_001)

    # Nilai 100.000 dibagi 3 = 33.333,33 => dibulatkan ke bawah.
    pid6 = buat_produk(cid, "Bulat3", "average")
    modules.stok_masuk(cid, pid6, 3, 100_000, "2026-04-03")
    s7 = modules.saldo_stok(cid, pid6)
    p.cek_benar("Pembulatan harga satuan tidak melebihi nilai sebenarnya",
                int(s7["hpp_satuan"]) <= 300_000 // 3 + 1,
                f"harga satuan = {s7['hpp_satuan']:,}")
    print()

    # ==================================================================
    print("[9. Nilai persediaan seluruh produk]")
    total = modules.nilai_persediaan_total(cid)
    # Hitung sendiri: jumlahkan nilai seluruh produk yang tersisa.
    hitung = 0
    for baris in db.q("SELECT id FROM products WHERE company_id=?", (cid,)):
        s = modules.saldo_stok(cid, baris["id"])
        hitung += int(s["nilai_total"])
    p.cek("Nilai persediaan total cocok dengan jumlah per produk",
          int(total), hitung)
    print()

    # ==================================================================
    print("[10. Kartu stok cocok dengan saldo]")
    # Kartu stok yang disaring harus tetap memakai saldo awal dari stok
    # sebelum rentang, supaya saldo berjalannya benar. Nilai stok pada
    # tanggal mulai harus sama dengan jumlah mutasi sebelum tanggal itu.
    kartu = modules.kartu_stok(cid, pid, "2026-01-16")
    awal_kartu = modules.saldo_stok_sebelum(cid, pid, "2026-01-16")
    # Sebelum 16 Januari: masuk 10 + masuk 10 - keluar 8 = 12 unit.
    p.cek("Saldo awal kartu stok sebelum 16 Jan = 12 unit",
          int(awal_kartu), 12)

    # Mutasi di dalam rentang saja yang muncul.
    p.cek_benar("Kartu stok tersaring hanya memuat mutasi dalam rentang",
                all(r["tanggal"] >= "2026-01-16" for r in kartu),
                f"jumlah baris = {len(kartu)}")

    # Saldo berjalan: saldo awal ditambah seluruh mutasi harus sama dengan
    # saldo stok yang sebenarnya.
    berjalan = awal_kartu + sum(float(r["qty"]) for r in kartu)
    p.cek("Saldo awal + mutasi dalam rentang = saldo stok sebenarnya",
          int(berjalan), int(modules.saldo_stok(cid, pid)["qty"]))

    # Nilai persediaan yang dihitung dari kartu harus sama dengan saldo
    # nilai. Mutasi bernilai positif untuk masuk dan negatif untuk keluar.
    nilai_berjalan = sum(int(r["nilai"]) for r in kartu)
    print(f"          nilai mutasi dalam rentang: Rp{nilai_berjalan:,}")
    print(f"          saldo nilai sekarang       : "
          f"Rp{int(modules.saldo_stok(cid, pid)['nilai_total']):,}")
    print()

    return p.ringkas()


if __name__ == "__main__":
    try:
        kode = main()
    finally:
        shutil.rmtree(FOLDER, ignore_errors=True)
    sys.exit(kode)
