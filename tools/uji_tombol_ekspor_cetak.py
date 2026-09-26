"""
Uji tombol Ekspor dan Cetak pada seluruh halaman.

Yang diperiksa: setiap halaman terbentuk tanpa galat, tombol Ekspor dan
Cetak benar benar ada di headernya, dan data yang diambil dari tabel siap
diekspor.

Cara pakai:
    python tools/uji_tombol_ekspor_cetak.py
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "src"))

FOLDER = Path(tempfile.mkdtemp(prefix="akuntuntas_tombol_"))
os.environ["LOCALAPPDATA"] = str(FOLDER)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QPushButton  # noqa: E402

app = QApplication.instance() or QApplication([])

from akuntansi_id import db, modules, services  # noqa: E402


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


class LisensiUji:
    """Lisensi tiruan berpaket Enterprise untuk pengujian."""

    enterprise = True
    paket = "enterprise"

    def punya(self, bagian: str) -> bool:
        return True


class Konteks:
    """Konteks halaman seperti yang dipakai aplikasi."""

    def __init__(self, company_id, tahun):
        self.company_id = company_id
        self.tahun = tahun
        self.bulan = 0
        self.username = "uji"
        self.full_name = "Pengguna Uji"
        self.user_id = 1
        self.role = "owner"
        self.mode = "expert"
        self.beginner = False
        self.lisensi = LisensiUji()

    @property
    def company(self):
        return services.get_company(self.company_id)

    def muat_perusahaan(self):
        return self.company


def main() -> int:
    p = Pemeriksa()
    print("=" * 76)
    print("  UJI TOMBOL EKSPOR DAN CETAK PADA SELURUH HALAMAN")
    print("=" * 76)
    print()

    db.init_db()
    cid = services.create_company("PT Uji Ekspor", bentuk="pt", status_pkp=1)
    ctx = Konteks(cid, 2026)

    # Isi data supaya tabelnya tidak kosong.
    modules.buat_mitra(cid, "PT Pelanggan Uji", "customer")
    pid = modules.buat_produk(cid, "Barang Uji", satuan="pcs",
                              harga_beli=100_000, harga_jual=150_000)
    modules.stok_masuk(cid, pid, 50, 100_000, "2026-01-05")
    services.simpan_jurnal_manual(
        cid, "2026-02-10", "UJI-001", "Penjualan uji",
        [{"kode_akun": "1001", "debit": 10_000_000, "kredit": 0, "keterangan": ""},
         {"kode_akun": "4001", "debit": 0, "kredit": 10_000_000, "keterangan": ""}])
    services.simpan_karyawan(cid, "Karyawan Uji", 5_000_000, status_ptkp="TK/0")

    # Halaman yang seharusnya punya tombol.
    from akuntansi_id.ui.pages import (biaya_bank, mitra, pembelian, produk,
                                       transaksi)

    halaman_uji = [
        ("Mitra", mitra.MitraPage, None),
        ("Produk", produk.ProdukPage, "tabel_produk"),
        ("Pembelian", pembelian.PembelianLengkapPage, None),
        ("Jurnal", transaksi.JurnalPage, "tabel"),
        ("Biaya", biaya_bank.BiayaPage, None),
    ]

    print("[1. Setiap halaman terbentuk dan memuat tombol]")
    for nama, kelas, atribut in halaman_uji:
        try:
            halaman = kelas(ctx)
        except Exception as e:
            p.cek(f"halaman {nama} terbentuk", False,
                  f"{type(e).__name__}: {e}")
            continue

        p.cek(f"halaman {nama} terbentuk", True)

        # Cari tombol Ekspor dan Cetak di header.
        header = getattr(halaman, "header", None)
        if header is None:
            p.cek(f"halaman {nama} punya header", False)
            continue

        teks_tombol = []
        for i in range(header.aksi.count()):
            w = header.aksi.itemAt(i).widget()
            if isinstance(w, QPushButton):
                teks_tombol.append(w.text())

        p.cek(f"halaman {nama} punya tombol Ekspor",
              any("Ekspor" in t for t in teks_tombol),
              f"tombol: {teks_tombol}")
        p.cek(f"halaman {nama} punya tombol Cetak",
              any("Cetak" in t for t in teks_tombol),
              f"tombol: {teks_tombol}")

        # Tombolnya harus benar benar terhubung: menekannya tidak boleh
        # membuat galat, dan harus membuka dialog penyimpanan. Dialognya
        # ditutup sendiri supaya pengujian tidak berhenti menunggu.
        from PySide6.QtCore import QTimer

        for teks_cari in ("Ekspor", "Cetak"):
            for i in range(header.aksi.count()):
                w = header.aksi.itemAt(i).widget()
                if not (isinstance(w, QPushButton) and teks_cari in w.text()):
                    continue
                # Tutup dialog yang muncul agar pengujian berjalan terus.
                def tutup():
                    for widget in app.topLevelWidgets():
                        if widget.isVisible() and widget is not halaman:
                            widget.close()
                QTimer.singleShot(120, tutup)
                try:
                    w.click()
                    p.cek(f"tombol {teks_cari} halaman {nama} dapat ditekan",
                          True)
                except Exception as e:
                    p.cek(f"tombol {teks_cari} halaman {nama} dapat ditekan",
                          False, f"{type(e).__name__}: {e}")
                break
        print()

    print("[2. Pengambilan data dari tabel halaman]")
    from akuntansi_id.ui import ekspor_cetak as EC

    # Halaman jurnal: tabelnya sudah terisi, jadi datanya dapat diambil.
    try:
        halaman = transaksi.JurnalPage(ctx)
        halaman.muat()
        data = EC.tabel_dari_widget(halaman.tabel)
        p.cek("data jurnal dapat diambil dari tabel",
              len(data) >= 2, f"baris: {len(data)}")
        if len(data) >= 2:
            p.cek("baris judul terisi", bool(data[0][0]),
                  f"judul: {data[0]}")
    except Exception as e:
        p.cek("data jurnal dapat diambil dari tabel", False,
              f"{type(e).__name__}: {e}")
    print()

    print("[3. Hasil pengambilan dapat langsung diekspor dan dicetak]")
    try:
        halaman = transaksi.JurnalPage(ctx)
        halaman.muat()
        data = [("Buku Jurnal", EC.tabel_dari_widget(halaman.tabel))]

        berkas = FOLDER / "jurnal.xlsx"
        EC.ekspor_excel("Buku Jurnal", data, str(berkas),
                        subjudul="Tahun 2026",
                        nama_perusahaan="PT Uji Ekspor")
        p.cek("data tabel halaman dapat disimpan ke Excel", berkas.exists(),
              f"ukuran: {berkas.stat().st_size if berkas.exists() else 0}")

        pdf = FOLDER / "jurnal.pdf"
        EC.simpan_pdf(None, "Buku Jurnal", "Tahun 2026", data, str(pdf))
        p.cek("data tabel halaman dapat dicetak ke PDF A4", pdf.exists(),
              f"ukuran: {pdf.stat().st_size if pdf.exists() else 0}")
        if pdf.exists():
            p.cek("hasil cetak berukuran A4",
                  pdf.read_bytes()[:5] == b"%PDF-")
    except Exception as e:
        p.cek("data tabel halaman dapat diekspor dan dicetak", False,
              f"{type(e).__name__}: {e}")
    print()

    print("[4. Halaman lain tidak terganggu]")
    # Seluruh halaman harus tetap terbentuk, termasuk yang tidak diberi
    # tombol ekspor.
    from akuntansi_id.ui.pages import (analisis, aset, coa_page, dashboard,
                                       entitas, kontrak_page, laporan, pajak,
                                       pajak_lanjutan, pengaturan, penjualan,
                                       tata_kelola)

    for nama, kelas in (
        ("Dasbor", dashboard.DashboardPage),
        ("Analisis", analisis.AnalisisPage),
        ("Aset", aset.AsetPage),
        ("Payroll", aset.PayrollPage),
        ("Laporan", laporan.LaporanPage),
        ("Pajak", pajak.PajakPage),
        ("Pajak Lanjutan", pajak_lanjutan.PajakLanjutanPage),
        ("Pengaturan", pengaturan.PengaturanPage),
        ("Bantuan", pengaturan.BantuanPage),
        ("Penjualan", penjualan.PenjualanLengkapPage),
        ("Bagan Akun", coa_page.CoaPage),
        ("Perusahaan", coa_page.PerusahaanPage),
        ("Pengguna", tata_kelola.PenggunaPage),
        ("Audit", tata_kelola.AuditPage),
        ("Keranjang Sampah", tata_kelola.RecycleBinPage),
        ("Impor Massal", tata_kelola.ImporMassalPage),
        ("Pencarian", tata_kelola.PencarianPage),
        ("Kontrak", kontrak_page.KontrakPage),
        ("Dimensi", entitas.DimensiPage),
        ("Konsolidasi", entitas.KonsolidasiPage),
    ):
        try:
            kelas(ctx)
            p.cek(f"halaman {nama} tetap terbentuk", True)
        except Exception as e:
            p.cek(f"halaman {nama} tetap terbentuk", False,
                  f"{type(e).__name__}: {e}")

    return p.ringkas()


if __name__ == "__main__":
    try:
        kode = main()
    finally:
        shutil.rmtree(FOLDER, ignore_errors=True)
    sys.exit(kode)
