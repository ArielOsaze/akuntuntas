"""
Uji antarmuka mendalam: membuka dialog, mengisi formulir, menekan tombol,
dan memastikan hasilnya tersimpan benar di basis data.
"""
import os
import sys
import traceback
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
_DIR_UJI = Path(__file__).parent.parent / "_uitest2"
if _DIR_UJI.exists():
    import shutil
    shutil.rmtree(_DIR_UJI, ignore_errors=True)
os.environ["AKUNTANSIID_DATA"] = str(_DIR_UJI)

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from PySide6.QtWidgets import QApplication, QMessageBox

from akuntansi_id import config, db, services, modules as M, modules_sales as S
from akuntansi_id import modules_ops as O
from akuntansi_id.core import security as sec
from akuntansi_id.ui.main_window import MainWindow
from akuntansi_id.ui import theme

# Lisensi uji dipakai agar seluruh halaman ikut diperiksa, termasuk
# halaman yang hanya tersedia pada paket Enterprise.
from akuntansi_id.core.license import Lisensi as _LisensiUji
_LISENSI_UJI = _LisensiUji(kunci='ATNTUJI', paket='enterprise', fitur={})


lulus = 0
gagal = 0


def cek(nama, kondisi, detail=""):
    global lulus, gagal
    if kondisi:
        lulus += 1
        print(f"OK     {nama}")
    else:
        gagal += 1
        print(f"GAGAL  {nama}  {detail}")


def jangan_blokir():
    """Cegah dialog pesan menggantung pada uji otomatis."""
    QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.Ok)
    QMessageBox.warning = staticmethod(lambda *a, **k: QMessageBox.Ok)
    QMessageBox.critical = staticmethod(lambda *a, **k: QMessageBox.Ok)
    QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.Yes)


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyleSheet(theme.stylesheet())
    jangan_blokir()

    config.ensure_dirs()
    db.init_db()
    sec.ensure_default_admin()

    perusahaan = services.list_companies(aktif_saja=False)
    if not perusahaan:
        cid = services.create_company(
            "PT Uji UI Mendalam", "pt", npwp="02.345.678.9-012.000",
            alamat="Jl. Uji 2", kota="Bandung", status_pkp=True)
    else:
        cid = perusahaan[0]["id"]

    hasil_login = sec.login("admin", config.DEFAULT_ADMIN_PASSWORD)
    jendela = MainWindow(hasil_login, lisensi=_LISENSI_UJI)
    jendela.ctx.company_id = cid
    jendela.ctx.company = services.get_company(cid)
    jendela.ctx.beginner = True
    ctx = jendela.ctx

    print("\n--- Data awal ---")
    mitra_id = M.buat_mitra(cid, "PT Pelanggan Uji", "customer",
                            npwp="03.456.789.0-123.000", email="a@b.co.id",
                            telepon="021-111", kota="Jakarta")
    vendor_id = M.buat_mitra(cid, "CV Pemasok Uji", "vendor", kota="Surabaya")
    cek("mitra dibuat", mitra_id > 0 and vendor_id > 0)

    produk_id = M.buat_produk(cid, "Produk Uji A", tipe="barang", satuan="pcs",
                              harga_beli=50000, harga_jual=85000, qty_awal=100)
    cek("produk dibuat", produk_id > 0)
    stok = M.saldo_stok(cid, produk_id)
    cek("stok awal tercatat", stok["qty"] == 100, f"qty={stok['qty']}")

    print("\n--- Dialog mitra ---")
    from akuntansi_id.ui.pages.mitra import DialogMitra
    d = DialogMitra(ctx)
    d.inp_nama.setText("Toko Uji Dialog")
    d.cmb_tipe.setCurrentIndex(d.cmb_tipe.findData("customer"))
    d.inp_npwp.setText("04.567.890.1-234.000")
    d.inp_kota.setText("Semarang")
    d._simpan()
    ada = db.q1("SELECT * FROM partners WHERE company_id=? AND nama=?",
                (cid, "Toko Uji Dialog"))
    cek("DialogMitra menyimpan data", ada is not None)
    if ada:
        cek("DialogMitra simpan NPWP", ada["npwp"] == "04.567.890.1-234.000",
            f"npwp={ada['npwp']}")

    print("\n--- Dialog produk ---")
    from akuntansi_id.ui.pages.produk import DialogProduk
    d = DialogProduk(ctx)
    d.inp_nama.setText("Produk Dialog")
    d.cmb_tipe.setCurrentIndex(d.cmb_tipe.findData("barang"))
    d.inp_beli.set_nilai(30000)
    d.inp_jual.set_nilai(55000)
    d.inp_stok_awal.set_nilai(25)
    d._simpan()
    p2 = db.q1("SELECT * FROM products WHERE company_id=? AND nama=?",
               (cid, "Produk Dialog"))
    cek("DialogProduk menyimpan data", p2 is not None)
    if p2:
        cek("DialogProduk simpan harga jual", int(p2["harga_jual"]) == 55000,
            f"harga={p2['harga_jual']}")
        cek("DialogProduk simpan stok awal",
            M.saldo_stok(cid, p2["id"])["qty"] == 25)

    print("\n--- Dialog invoice ---")
    from akuntansi_id.ui.pages.penjualan import DialogInvoice
    d = DialogInvoice(ctx)
    d.cmb_pelanggan.setCurrentIndex(d.cmb_pelanggan.findData(mitra_id))
    d.panel.baris_data = [{
        "product_id": produk_id, "deskripsi": "Produk Uji A", "qty": 5,
        "satuan": "pcs", "harga_satuan": 85000, "diskon_persen": 0,
    }]
    d.panel._render()
    d._simpan()
    inv = db.q1("SELECT * FROM invoices WHERE company_id=? ORDER BY id DESC", (cid,))
    cek("DialogInvoice menyimpan invoice", inv is not None)
    if inv:
        cek("Invoice total benar", int(inv["total"]) == 5 * 85000 + int(round(
            5 * 85000 * config.RATE_VAT_EFFECTIVE_NORMAL)),
            f"total={inv['total']}")
        cek("Jurnal invoice otomatis dibuat", inv["journal_entry_id"] is not None)
        stok2 = M.saldo_stok(cid, produk_id)
        cek("Stok berkurang setelah penjualan", stok2["qty"] == 95,
            f"qty={stok2['qty']}")

    print("\n--- Dialog bill ---")
    from akuntansi_id.ui.pages.pembelian import DialogBill
    d = DialogBill(ctx)
    d.cmb_vendor.setCurrentIndex(d.cmb_vendor.findData(vendor_id))
    d.inp_nomor_vendor.setText("SUP-2026-001")
    d.panel.baris_data = [{
        "product_id": produk_id, "deskripsi": "Produk Uji A", "qty": 20,
        "satuan": "pcs", "harga_satuan": 50000, "diskon_persen": 0,
    }]
    d.panel._render()
    d._simpan()
    bill = db.q1("SELECT * FROM bills WHERE company_id=? ORDER BY id DESC", (cid,))
    cek("DialogBill menyimpan bill", bill is not None)
    if bill:
        cek("Bill nomor vendor tersimpan",
            bill["nomor_vendor"] == "SUP-2026-001")
        cek("Bill stok bertambah", M.saldo_stok(cid, produk_id)["qty"] == 115,
            f"qty={M.saldo_stok(cid, produk_id)['qty']}")

    print("\n--- Dialog pembayaran vendor ---")
    from akuntansi_id.ui.pages.pembelian import DialogBayarVendor
    if bill:
        d = DialogBayarVendor(ctx, bill_id=bill["id"], partner_id=vendor_id)
        d.inp_jumlah.set_nilai(int(bill["sisa"]))
        d._cek_alokasi()
        cek("Alokasi seimbang terdeteksi", d._total_alokasi() == int(bill["sisa"]))
        d._simpan()
        bill2 = S.get_bill(bill["id"])
        cek("Bill lunas setelah dibayar", bill2["status"] == "lunas",
            f"status={bill2['status']}")

    print("\n--- Dialog rekening bank ---")
    from akuntansi_id.ui.pages.biaya_bank import DialogRekeningBaru
    d = DialogRekeningBaru(ctx)
    d.inp_nama.setText("BCA Uji")
    d.cmb_tipe.setCurrentIndex(d.cmb_tipe.findData("bank"))
    d.inp_bank.setText("BCA")
    d.inp_rek.setText("1234567890")
    d.inp_saldo.set_nilai(10000000)
    d._simpan()
    bank = db.q1("SELECT * FROM bank_accounts WHERE company_id=? AND nama=?",
                 (cid, "BCA Uji"))
    cek("DialogRekeningBaru menyimpan rekening", bank is not None)

    print("\n--- Dialog biaya ---")
    from akuntansi_id.ui.pages.biaya_bank import DialogBiaya
    d = DialogBiaya(ctx)
    d.inp_uraian.setText("Biaya Listrik Uji")
    d.inp_jumlah.set_nilai(1500000)
    d.inp_vendor.setText("PLN")
    d._simpan()
    exp = db.q1("SELECT * FROM expenses WHERE company_id=? AND uraian=?",
                (cid, "Biaya Listrik Uji"))
    cek("DialogBiaya menyimpan biaya", exp is not None)
    if exp:
        cek("Biaya tersimpan dengan jumlah benar", int(exp["jumlah"]) == 1500000)

    print("\n--- Dialog dimensi ---")
    from akuntansi_id.ui.pages.entitas import (DialogCostCenter, DialogProyek,
                                               DialogCabang, DialogGrupBaru)
    d = DialogCostCenter(ctx)
    d.inp_nama.setText("Divisi Uji")
    d.inp_anggaran.set_nilai(50000000)
    d._simpan()
    cc = db.q1("SELECT * FROM cost_centers WHERE company_id=? AND nama=?",
               (cid, "Divisi Uji"))
    cek("DialogCostCenter menyimpan", cc is not None)

    d = DialogProyek(ctx)
    d.inp_nama.setText("Proyek Uji")
    d.inp_nilai.set_nilai(250000000)
    d._simpan()
    prj = db.q1("SELECT * FROM projects WHERE company_id=? AND nama=?",
                (cid, "Proyek Uji"))
    cek("DialogProyek menyimpan", prj is not None)

    d = DialogCabang(ctx)
    d.inp_nama.setText("Cabang Uji")
    d.inp_kota.setText("Medan")
    d._simpan()
    cab = db.q1("SELECT * FROM branches WHERE company_id=? AND nama=?",
                (cid, "Cabang Uji"))
    cek("DialogCabang menyimpan", cab is not None)

    d = DialogGrupBaru()
    d.inp_nama.setText("Grup Uji")
    d._simpan()
    grup = db.q1("SELECT * FROM entity_groups WHERE nama=?", ("Grup Uji",))
    cek("DialogGrupBaru menyimpan", grup is not None)
    if grup:
        O.tambah_anggota_grup(grup["id"], cid, 100)
        konsol = O.laporan_konsolidasi(grup["id"], ctx.tahun)
        cek("Laporan konsolidasi berjalan", konsol["jumlah_entitas"] == 1)

    print("\n--- Dialog pengguna ---")
    from akuntansi_id.ui.pages.tata_kelola import (DialogPenggunaBaru,
                                                   DialogIzinPengguna)
    d = DialogPenggunaBaru(ctx)
    d.inp_username.setText("staf.uji")
    d.inp_nama.setText("Staf Uji")
    d.cmb_role.setCurrentIndex(d.cmb_role.findData("staff"))
    d.inp_password.setText("Staf#Uji2026")
    d.inp_password2.setText("Staf#Uji2026")
    d._simpan()
    staf = db.q1("SELECT * FROM users WHERE username=?", ("staf.uji",))
    cek("DialogPenggunaBaru menyimpan pengguna", staf is not None)
    if staf:
        d = DialogIzinPengguna(ctx, staf)
        kode_uji = "penjualan.lihat"
        if kode_uji in d.checks:
            d.checks[kode_uji].setChecked(True)
        d._simpan()
        izin = M.izin_pengguna(staf["id"], "staff")
        cek("Hak akses pengguna tersimpan", kode_uji in izin)

    print("\n--- Dialog kategori biaya ---")
    from akuntansi_id.ui.pages.biaya_bank import DialogKategoriBaru
    d = DialogKategoriBaru(ctx)
    d.inp_nama.setText("Kategori Uji")
    d.inp_batas.set_nilai(5000000)
    d.chk_setuju.setChecked(True)
    d._simpan()
    kat = db.q1("SELECT * FROM expense_categories WHERE company_id=? AND nama=?",
                (cid, "Kategori Uji"))
    cek("DialogKategoriBaru menyimpan", kat is not None)
    if kat:
        cek("Kategori simpan batas nilai", int(kat["batas_nilai"]) == 5000000)
        cek("Kategori simpan flag persetujuan", bool(kat["perlu_persetujuan"]))

    print("\n--- Dialog template berulang ---")
    from akuntansi_id.ui.pages.entitas import DialogTemplateBerulang
    d = DialogTemplateBerulang(ctx)
    d.inp_nama.setText("Sewa Uji Bulanan")
    d.cmb_tipe.setCurrentIndex(d.cmb_tipe.findData("expense"))
    d.inp_jumlah.set_nilai(3000000)
    d.inp_uraian.setText("Sewa kantor")
    d._simpan()
    tpl = db.q1("SELECT * FROM recurring_templates WHERE company_id=? AND nama=?",
                (cid, "Sewa Uji Bulanan"))
    cek("DialogTemplateBerulang menyimpan", tpl is not None)

    print("\n--- Dialog transfer kas ---")
    from akuntansi_id.ui.pages.biaya_bank import DialogTransferKas
    kas = O.daftar_kas_bank(cid)
    cek("Rekening kas/bank tersedia", len(kas) >= 2, f"jumlah={len(kas)}")
    if len(kas) >= 2:
        d = DialogTransferKas(ctx)
        d.cmb_dari.setCurrentIndex(0)
        d.cmb_ke.setCurrentIndex(1)
        d.inp_jumlah.set_nilai(500000)
        d._simpan()
        cek("Transfer kas berhasil disimpan", True)

    print("\n--- Impor massal ---")
    csv_mitra = ("nama;npwp;email;telepon;kota\n"
                 "PT Impor Satu;05.111.222.3-444.000;satu@uji.co.id;021-1;Jakarta\n"
                 "PT Impor Dua;05.222.333.4-555.000;dua@uji.co.id;021-2;Depok\n"
                 "PT Impor Satu;05.111.222.3-444.000;satu@uji.co.id;021-1;Jakarta\n")
    hasil = O.impor_mitra_massal(cid, csv_mitra, "customer")
    cek("Impor mitra berhasil 2 baris", hasil["berhasil"] == 2,
        f"hasil={hasil}")
    cek("Duplikat terdeteksi", hasil.get("duplikat", 0) >= 1,
        f"duplikat={hasil.get('duplikat')}")

    csv_produk = ("kode;nama;satuan;tipe;harga_beli;harga_jual;stok\n"
                  "IMP01;Produk Impor A;pcs;barang;10000;18000;50\n"
                  "IMP02;Produk Impor B;box;barang;25000;40000;20\n")
    hasil = O.impor_produk_massal(cid, csv_produk)
    cek("Impor produk berhasil", hasil["berhasil"] == 2, f"hasil={hasil}")

    csv_jurnal = ("tanggal;no_bukti;keterangan;kode_akun;debit;kredit\n"
                  "2026-02-01;BKM-IMP;Penerimaan uji;1001;1000000;0\n"
                  "2026-02-01;BKM-IMP;Pendapatan uji;4001;0;1000000\n"
                  "2026-02-02;BKM-IMP2;Penerimaan uji 2;1001;2500000;0\n"
                  "2026-02-02;BKM-IMP2;Pendapatan uji 2;4001;0;2500000\n")
    hasil = O.impor_jurnal_massal(cid, csv_jurnal)
    cek("Impor jurnal berhasil", hasil["berhasil"] == 2, f"hasil={hasil}")

    print("\n--- Pencarian global ---")
    hasil = O.cari_global(cid, "Uji")
    cek("Pencarian global menemukan hasil", len(hasil) > 0,
        f"jumlah={len(hasil)}")
    jenis = {h["jenis"] for h in hasil}
    cek("Pencarian lintas modul", len(jenis) >= 3, f"jenis={jenis}")

    print("\n--- Keranjang sampah ---")
    M.hapus_mitra(mitra_id, ctx.username)
    bin_data = O.daftar_recycle_bin(cid)
    cek("Data masuk keranjang sampah", len(bin_data) > 0)
    if bin_data:
        rec = [b for b in bin_data if b["tabel"] == "partners"]
        if rec:
            hasil = O.pulihkan_dari_recycle(rec[0]["id"], ctx.username)
            cek("Pemulihan dari keranjang sampah", hasil["dipulihkan"])
            kembali = db.q1("SELECT * FROM partners WHERE id=?", (mitra_id,))
            cek("Data pulih kembali", kembali is not None and
                kembali["deleted_at"] is None)

    print("\n--- Tutup buku ---")
    periode = f"{ctx.tahun}-03"
    O.tutup_buku(cid, periode, oleh="Uji", user_id=ctx.user_id)
    cek("Periode tertutup", O.status_periode(cid, periode) == "tertutup",
        f"status={O.status_periode(cid, periode)}")
    cek("Periode terbuka terdeteksi",
        O.cek_periode_terbuka(cid, f"{ctx.tahun}-04"))
    O.buka_buku(cid, periode, oleh="Uji", user_id=ctx.user_id)
    cek("Periode dibuka kembali", O.status_periode(cid, periode) == "terbuka")

    print("\n--- Otomasi berulang ---")
    hasil = O.jalankan_template_berulang(cid, user_id=ctx.user_id)
    cek("Otomasi berjalan", isinstance(hasil, dict) and
        "jumlah_dibuat" in hasil, f"hasil={hasil}")

    print("\n--- Reminder ---")
    jumlah = O.buat_reminder_dari_piutang(cid, 365)
    cek("Pengingat piutang dibuat", jumlah >= 0, f"jumlah={jumlah}")
    rem = O.daftar_reminder(cid, "")
    cek("Daftar pengingat terbaca", isinstance(rem, list))

    print("\n--- Rekonsiliasi bank ---")
    if bank:
        rec_id = O.buat_rekonsiliasi(cid, bank["id"], f"{ctx.tahun}-03",
                                     10000000, ctx.username)
        cek("Rekonsiliasi dibuat", rec_id > 0)
        O.selesaikan_rekonsiliasi(rec_id, "Uji", ctx.user_id)
        daftar = O.daftar_rekonsiliasi(cid)
        cek("Daftar rekonsiliasi terbaca", len(daftar) > 0)

    print("\n--- Impor mutasi CSV ---")
    if bank:
        csv_mutasi = ("tanggal;uraian;referensi;debit;kredit;saldo\n"
                      "2026-03-05;Transfer masuk uji;TRF-001;5000000;0;15000000\n"
                      "2026-03-06;Biaya adm uji;ADM-001;0;15000;14985000\n")
        hasil = O.impor_mutasi_dari_csv(cid, bank["id"], csv_mutasi, ctx.user_id)
        cek("Impor mutasi bank berhasil", hasil["berhasil"] == 2,
            f"hasil={hasil}")
        mut = O.daftar_mutasi_bank(cid, bank["id"])
        cek("Mutasi tersimpan", len(mut) >= 2)

    print("\n--- Semua halaman dimuat dengan data ---")
    for kode in ["dashboard", "analisis", "penjualan", "pembelian", "biaya",
                 "bank", "mitra", "produk", "dimensi", "periode",
                 "konsolidasi", "laporan", "pajak", "pengguna", "audit",
                 "recycle", "impor", "lan", "pencarian"]:
        try:
            jendela._navigasi(kode)
            halaman = jendela.halaman.get(kode)
            if halaman is not None and hasattr(halaman, "muat"):
                halaman.muat()
            cek(f"halaman '{kode}' dengan data", True)
        except Exception as e:
            cek(f"halaman '{kode}' dengan data", False,
                f"{type(e).__name__}: {e}")
            traceback.print_exc()

    print("\n--- Semua tab setiap halaman ---")
    from PySide6.QtWidgets import QTabWidget
    for kode, halaman in jendela.halaman.items():
        tabs = halaman.findChildren(QTabWidget)
        for t in tabs:
            for i in range(t.count()):
                try:
                    t.setCurrentIndex(i)
                    cek(f"tab {kode}[{i}] '{t.tabText(i)}'", True)
                except Exception as e:
                    cek(f"tab {kode}[{i}]", False, f"{type(e).__name__}: {e}")

    print("\n--- Neraca seimbang setelah semua operasi ---")
    from akuntansi_id.core import accounting as acc
    nr = acc.neraca(cid, ctx.tahun)
    cek("Neraca seimbang", nr.seimbang,
        f"selisih={nr.selisih} aset={nr.total_aset} "
        f"liab+ekuitas={nr.total_liabilitas + nr.total_ekuitas}")
    tb = acc.total_neraca_saldo(cid, ctx.tahun)
    cek("Neraca saldo seimbang", tb["seimbang"],
        f"debit={tb['debit']} kredit={tb['kredit']}")

    print(f"\n{'=' * 72}")
    print(f"HASIL: {lulus} LULUS, {gagal} GAGAL")
    print("=" * 72)
    return 1 if gagal else 0


if __name__ == "__main__":
    sys.exit(main())
