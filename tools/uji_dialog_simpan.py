"""
Uji dialog secara menyeluruh: buka setiap dialog, isi kolomnya dengan nilai
wajar, lalu tekan tombol simpan — dan pastikan data benar-benar tersimpan.

Cara pakai:
    python tools/uji_dialog_simpan.py

Uji ini memakai basis data terpisah (_ujidialog) sehingga data contoh
tidak berubah.
"""
from __future__ import annotations

import os
import shutil
import sys
import traceback
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
DIR_UJI = AKAR / "_ujidialog"
if DIR_UJI.exists():
    shutil.rmtree(DIR_UJI, ignore_errors=True)
os.environ["AKUNTANSIID_DATA"] = str(DIR_UJI)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(AKAR / "src"))

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (QApplication, QComboBox, QDateEdit, QDialog,
                               QLineEdit, QMessageBox, QSpinBox, QDoubleSpinBox)

HASIL_UJI: list = []


def catat(nama: str, lulus: bool, detail: str = ""):
    HASIL_UJI.append((nama, lulus, detail))
    print(f"{'OK    ' if lulus else 'GAGAL '} {nama}  {detail}")


def isi_kolom(dialog: QDialog) -> int:
    """Isi setiap kolom teks dan angka dengan nilai yang masuk akal."""
    jumlah = 0
    for inp in dialog.findChildren(QLineEdit):
        if not inp.isEnabled() or inp.isReadOnly():
            continue
        if inp.echoMode() == QLineEdit.Password:
            continue
        if inp.text().strip():
            continue
        nama = (inp.placeholderText() or inp.objectName() or "").lower()
        if "npwp" in nama:
            inp.setText("01.234.567.8-901.000")
        elif "email" in nama:
            inp.setText("uji@contoh.co.id")
        elif "telepon" in nama:
            inp.setText("021-5551234")
        else:
            inp.setText("Data Uji")
        jumlah += 1

    for spin in dialog.findChildren(QSpinBox):
        if spin.value() == 0:
            spin.setValue(3)
            jumlah += 1

    for dspin in dialog.findChildren(QDoubleSpinBox):
        if dspin.value() == 0:
            dspin.setValue(3.0)
            jumlah += 1

    for tanggal in dialog.findChildren(QDateEdit):
        if tanggal.date() == QDate(2000, 1, 1):
            tanggal.setDate(QDate.currentDate())
            jumlah += 1

    # combo: pilih opsi pertama yang punya data (bukan kosong)
    for combo in dialog.findChildren(QComboBox):
        if combo.count() > 1 and combo.currentData() is None:
            for i in range(1, combo.count()):
                if combo.itemData(i) is not None:
                    combo.setCurrentIndex(i)
                    jumlah += 1
                    break
    return jumlah


def main() -> int:
    from akuntansi_id import config, db, services, modules as M
    from akuntansi_id.core import security as sec
    from akuntansi_id.ui import theme
    from akuntansi_id.ui.main_window import AppContext

    app = QApplication([])
    app.setStyleSheet(theme.stylesheet())
    QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.Ok)
    QMessageBox.warning = staticmethod(lambda *a, **k: QMessageBox.Ok)
    QMessageBox.critical = staticmethod(lambda *a, **k: QMessageBox.Ok)
    QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.Yes)

    config.ensure_dirs()
    db.init_db()
    sec.ensure_default_admin()

    cid = services.create_company(
        "PT Uji Dialog", "pt", npwp="01.234.567.8-901.000",
        alamat="Jl. Uji 1", kota="Jakarta", status_pkp=True)
    M.buat_mitra(cid, "PT Pelanggan Uji", "customer", kota="Jakarta")
    M.buat_mitra(cid, "CV Pemasok Uji", "vendor", kota="Bandung")
    M.buat_produk(cid, "Produk Uji", tipe="barang", satuan="pcs",
                  harga_beli=10000, harga_jual=18000, qty_awal=100)

    hasil_login = sec.login("admin", config.DEFAULT_ADMIN_PASSWORD)
    ctx = AppContext(company_id=cid, company=services.get_company(cid),
                     tahun=QDate.currentDate().year(),
                     user_id=hasil_login.user_id,
                     username=hasil_login.username,
                     full_name=hasil_login.full_name, role="owner",
                     beginner=True)

    # ---------------------------------------------------------------- mitra
    from akuntansi_id.ui.pages.mitra import DialogMitra
    d = DialogMitra(ctx)
    d.inp_nama.setText("PT Mitra Uji Simpan")
    d.inp_kota.setText("Surabaya")
    d._simpan()
    ada = db.q1("SELECT * FROM partners WHERE company_id=? AND nama=?",
                (cid, "PT Mitra Uji Simpan"))
    catat("DialogMitra menyimpan data", ada is not None)

    # ---------------------------------------------------------------- produk
    from akuntansi_id.ui.pages.produk import DialogProduk
    d = DialogProduk(ctx)
    d.inp_nama.setText("Produk Uji Simpan")
    d.inp_beli.set_nilai(25000)
    d.inp_jual.set_nilai(42000)
    d.inp_stok_awal.set_nilai(15)
    d._simpan()
    p = db.q1("SELECT * FROM products WHERE company_id=? AND nama=?",
              (cid, "Produk Uji Simpan"))
    catat("DialogProduk menyimpan data", p is not None)
    if p:
        catat("DialogProduk menyimpan stok awal",
              M.saldo_stok(cid, p["id"])["qty"] == 15,
              f"qty={M.saldo_stok(cid, p['id'])['qty']}")

    # ---------------------------------------------------------------- gudang
    from akuntansi_id.ui.pages.produk import DialogGudang
    d = DialogGudang(ctx)
    d.inp_nama.setText("Gudang Uji")
    d._simpan()
    g = db.q1("SELECT * FROM warehouses WHERE company_id=? AND nama=?",
              (cid, "Gudang Uji"))
    catat("DialogGudang menyimpan data", g is not None)

    # ---------------------------------------------------------------- biaya
    from akuntansi_id.ui.pages.biaya_bank import (DialogBiaya, DialogKategoriBaru,
                                                  DialogRekeningBaru)
    d = DialogKategoriBaru(ctx)
    d.inp_nama.setText("Kategori Uji Simpan")
    d.inp_batas.set_nilai(1000000)
    d._simpan()
    kat = db.q1("SELECT * FROM expense_categories WHERE company_id=? AND nama=?",
                (cid, "Kategori Uji Simpan"))
    catat("DialogKategoriBaru menyimpan data", kat is not None)

    d = DialogBiaya(ctx)
    d.inp_uraian.setText("Biaya Uji Simpan")
    d.inp_jumlah.set_nilai(750000)
    d._simpan()
    e = db.q1("SELECT * FROM expenses WHERE company_id=? AND uraian=?",
              (cid, "Biaya Uji Simpan"))
    catat("DialogBiaya menyimpan data", e is not None)

    d = DialogRekeningBaru(ctx)
    d.inp_nama.setText("Bank Uji Simpan")
    d.inp_rek.setText("123456789")
    d.inp_saldo.set_nilai(5000000)
    d._simpan()
    bank = db.q1("SELECT * FROM cash_accounts WHERE company_id=? AND nama=?",
                 (cid, "Bank Uji Simpan"))
    catat("DialogRekeningBaru menyimpan data", bank is not None)
    if bank:
        catat("Rekening baru tertaut ke akun buku",
              bool(bank["akun_buku"]), f"akun={bank['akun_buku']}")

    # ---------------------------------------------------------------- dimensi
    from akuntansi_id.ui.pages.entitas import (DialogCabang, DialogCostCenter,
                                               DialogGrupBaru, DialogProyek)
    d = DialogCostCenter(ctx)
    d.inp_nama.setText("Divisi Uji Simpan")
    d.inp_anggaran.set_nilai(10000000)
    d._simpan()
    cc = db.q1("SELECT * FROM cost_centers WHERE company_id=? AND nama=?",
               (cid, "Divisi Uji Simpan"))
    catat("DialogCostCenter menyimpan data", cc is not None)

    d = DialogProyek(ctx)
    d.inp_nama.setText("Proyek Uji Simpan")
    d.inp_nilai.set_nilai(50000000)
    d._simpan()
    prj = db.q1("SELECT * FROM projects WHERE company_id=? AND nama=?",
                (cid, "Proyek Uji Simpan"))
    catat("DialogProyek menyimpan data", prj is not None)

    d = DialogCabang(ctx)
    d.inp_nama.setText("Cabang Uji Simpan")
    d.inp_kota.setText("Medan")
    d._simpan()
    cab = db.q1("SELECT * FROM branches WHERE company_id=? AND nama=?",
                (cid, "Cabang Uji Simpan"))
    catat("DialogCabang menyimpan data", cab is not None)

    d = DialogGrupBaru()
    d.inp_nama.setText("Grup Uji Simpan")
    d._simpan()
    gr = db.q1("SELECT * FROM entity_groups WHERE nama=?",
               ("Grup Uji Simpan",))
    catat("DialogGrupBaru menyimpan data", gr is not None)

    # ---------------------------------------------------------------- pengguna
    from akuntansi_id.ui.pages.tata_kelola import DialogPenggunaBaru
    d = DialogPenggunaBaru(ctx)
    d.inp_username.setText("staf.uji.simpan")
    d.inp_nama.setText("Staf Uji Simpan")
    d.inp_password.setText("Staf#Uji2026")
    d.inp_password2.setText("Staf#Uji2026")
    d._simpan()
    u = db.q1("SELECT * FROM users WHERE username=?", ("staf.uji.simpan",))
    catat("DialogPenggunaBaru menyimpan data", u is not None)

    # ---------------------------------------------------------------- template
    from akuntansi_id.ui.pages.entitas import DialogTemplateBerulang
    d = DialogTemplateBerulang(ctx)
    d.inp_nama.setText("Template Uji Simpan")
    d.inp_jumlah.set_nilai(2000000)
    d.inp_uraian.setText("Sewa uji")
    d._simpan()
    t = db.q1("SELECT * FROM recurring_templates WHERE company_id=? AND nama=?",
              (cid, "Template Uji Simpan"))
    catat("DialogTemplateBerulang menyimpan data", t is not None)

    # ---------------------------------------------------------------- invoice
    from akuntansi_id.ui.pages.penjualan import DialogInvoice
    mitra = db.q1("SELECT id FROM partners WHERE company_id=? AND tipe='customer'",
                  (cid,))
    produk = db.q1("SELECT id FROM products WHERE company_id=? AND tipe='barang'",
                   (cid,))
    if mitra and produk:
        d = DialogInvoice(ctx)
        d.cmb_pelanggan.setCurrentIndex(d.cmb_pelanggan.findData(mitra["id"]))
        d.panel.baris_data = [{
            "product_id": produk["id"], "deskripsi": "Produk Uji", "qty": 3,
            "satuan": "pcs", "harga_satuan": 18000, "diskon_persen": 0}]
        d.panel._render()
        d._simpan()
        inv = db.q1("SELECT * FROM invoices WHERE company_id=? ORDER BY id DESC",
                    (cid,))
        catat("DialogInvoice menyimpan invoice", inv is not None)
        if inv:
            catat("Invoice membuat jurnal otomatis",
                  inv["journal_entry_id"] is not None)

    # ---------------------------------------------------------------- bill
    from akuntansi_id.ui.pages.pembelian import DialogBill
    vendor = db.q1("SELECT id FROM partners WHERE company_id=? AND tipe='vendor'",
                   (cid,))
    if vendor and produk:
        d = DialogBill(ctx)
        d.cmb_vendor.setCurrentIndex(d.cmb_vendor.findData(vendor["id"]))
        d.panel.baris_data = [{
            "product_id": produk["id"], "deskripsi": "Produk Uji", "qty": 10,
            "satuan": "pcs", "harga_satuan": 10000, "diskon_persen": 0}]
        d.panel._render()
        d._simpan()
        bill = db.q1("SELECT * FROM bills WHERE company_id=? ORDER BY id DESC",
                     (cid,))
        catat("DialogBill menyimpan bill", bill is not None)

    print()
    print("=" * 70)
    lulus = sum(1 for _, l, _ in HASIL_UJI if l)
    gagal = len(HASIL_UJI) - lulus
    print(f"HASIL: {lulus} LULUS, {gagal} GAGAL")
    print("=" * 70)
    return 1 if gagal else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc()
        sys.exit(2)
