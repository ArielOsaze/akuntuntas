"""
Uji regresi perbaikan terakhir.

Mencakup cacat yang pernah muncul dan mudah kembali tanpa disadari:
detail perusahaan harus berupa kamus, tabel tidak boleh menambah kotak
centang palsu, jumlah barang harus menerima desimal, selisih stock opname
harus langsung terlihat, retur tidak boleh melebihi jumlah pembelian, serta
dialog yang pernah terpotong harus muat di layar.

Cara pakai:
    python tests/test_regresi_akhir.py
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
_DIR_UJI = Path(__file__).parent.parent / "_uitest_regresi"
if _DIR_UJI.exists():
    shutil.rmtree(_DIR_UJI, ignore_errors=True)
os.environ["AKUNTANSIID_DATA"] = str(_DIR_UJI)

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtGui import QRegularExpressionValidator  # noqa: E402
from PySide6.QtWidgets import (  # noqa: E402
    QApplication, QCheckBox,
)

from akuntansi_id import config, db, services  # noqa: E402
from akuntansi_id import modules as M  # noqa: E402
from akuntansi_id import modules_sales as S  # noqa: E402
from akuntansi_id.core import security as sec  # noqa: E402
from akuntansi_id.ui import theme  # noqa: E402
from akuntansi_id.ui import widgets as w  # noqa: E402
from akuntansi_id.ui.main_window import AppContext  # noqa: E402

LULUS = 0
GAGAL = 0


def cek(nama: str, syarat: bool, keterangan: str = ""):
    global LULUS, GAGAL
    if syarat:
        LULUS += 1
        print(f"  [LULUS] {nama}")
    else:
        GAGAL += 1
        print(f"  [GAGAL] {nama}" + (f" - {keterangan}" if keterangan else ""))


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyle("Fusion")
    theme.palet_terang(app)
    app.setStyleSheet(theme.stylesheet())

    config.ensure_dirs()
    db.init_db()
    sec.ensure_default_admin()

    cid = services.create_company(
        "PT Uji Regresi", "pt", npwp="02.345.678.9-012.000",
        alamat="Jl. Uji Regresi", kota="Semarang")
    ctx = AppContext(
        company_id=cid, company=services.get_company(cid),
        tahun=config.DEFAULT_TAX_YEAR, user_id=1, username="admin",
        full_name="Administrator", role="owner", beginner=False)

    print("\n--- Detail perusahaan ---")
    perusahaan = services.get_company(cid)
    cek("detail perusahaan berbentuk kamus", isinstance(perusahaan, dict))
    cek("nama perusahaan terbaca",
        isinstance(perusahaan, dict) and perusahaan.get("nama") == "PT Uji Regresi")
    cek("kode perusahaan tersedia",
        isinstance(perusahaan, dict) and perusahaan.get("id") == cid)

    print("\n--- Tabel tanpa kotak centang palsu ---")
    tabel = w.Tabel([("Uraian", -1), ("Jumlah", 120)])
    tabel.isi([["Pendapatan", "Rp10.000"], ["Beban", "Rp4.000"]],
              align_kanan={1}, kolom_penanda=1)
    centang = [
        (r, c) for r in range(tabel.rowCount())
        for c in range(tabel.columnCount())
        if tabel.item(r, c) is not None
        and tabel.item(r, c).data(Qt.CheckStateRole) is not None
    ]
    cek("isi tabel tidak menambah kotak centang", not centang, str(centang))

    print("\n--- Jumlah barang desimal ---")
    qty = w.InputQty()
    qty.set_nilai(1.25)
    cek("nilai desimal ditampilkan dengan koma", qty.text() == "1,25", qty.text())
    qty.setText("2,75")
    app.processEvents()
    cek("ketikan desimal terbaca", abs(qty.nilai() - 2.75) < 1e-9,
        str(qty.nilai()))
    validator = qty.validator()
    cek("huruf ditolak pengisi jumlah",
        validator.validate("dua", 0)[0] == QRegularExpressionValidator.Invalid)
    cek("angka bulat diterima pengisi jumlah",
        validator.validate("12", 0)[0] == QRegularExpressionValidator.Acceptable)

    print("\n--- Selisih stock opname ---")
    produk_id = M.buat_produk(cid, "Barang Uji Opname", tipe="barang",
                              satuan="pcs", harga_beli=10000,
                              harga_jual=15000, qty_awal=0)
    M.penyesuaian_stok(cid, produk_id, 4.5, f"{config.DEFAULT_TAX_YEAR}-06-01",
                       M.gudang_utama(cid), "Stok awal uji", 1)

    from akuntansi_id.ui.pages.produk import DialogStockOpname

    opname = DialogStockOpname(ctx)
    pid, (inp, qty_lama, _nama, lbl) = next(iter(opname.inputs.items()))
    cek("stok tercatat sesuai", abs(qty_lama - 4.5) < 1e-9, str(qty_lama))
    inp.setText(f"{qty_lama + 1.5:g}".replace(".", ","))
    app.processEvents()
    cek("selisih lebih tampil langsung", lbl.text() == "+1,5", lbl.text())
    inp.setText(f"{qty_lama - 1.25:g}".replace(".", ","))
    app.processEvents()
    cek("selisih kurang tampil langsung", lbl.text() == "-1,25", lbl.text())
    inp.setText(f"{qty_lama:g}".replace(".", ","))
    app.processEvents()
    cek("selisih nol kembali netral", lbl.text() == "0", lbl.text())
    opname.close()

    print("\n--- Retur pembelian ---")
    vendor_id = M.buat_mitra(cid, "CV Pemasok Uji", "vendor",
                             kota="Surabaya")
    bill_id = S.buat_bill(
        cid, f"{config.DEFAULT_TAX_YEAR}-06-10",
        [{"product_id": produk_id, "deskripsi": "Barang Uji Opname",
          "qty": 2, "satuan": "pcs", "harga_satuan": 10000}],
        partner_id=vendor_id, vendor="CV Pemasok Uji")

    from akuntansi_id.ui.pages.pembelian import DialogReturPembelian

    retur = DialogReturPembelian(ctx)
    inp_retur, item = next(iter(retur.inputs.values()))
    cek("baris bill termuat di dialog retur",
        float(item["qty"]) == 2.0, str(item["qty"]))

    pesan = []

    def ingat_pesan(_induk, judul, isi, *a, **k):
        pesan.append((judul, isi))
        return None

    from akuntansi_id.ui import popup as _popup
    asli = _popup.peringatkan
    _popup.peringatkan = ingat_pesan
    inp_retur.set_nilai(3)
    retur._simpan()
    cek("retur melebihi jumlah pembelian ditolak",
        bool(pesan) and pesan[-1][0] == "Jumlah berlebih",
        str(pesan[-1] if pesan else ""))
    cek("bill tidak berubah setelah retur ditolak",
        abs(float(S.get_bill(bill_id)["total"]) - 20000) < 1e-6)

    inp_retur.set_nilai(1.5)
    retur._simpan()
    _popup.peringatkan = asli
    cek("retur dengan jumlah wajar tersimpan", retur.result() == 1)
    cek("total bill berkurang sesuai retur",
        abs(float(S.get_bill(bill_id)["total"]) - 5000) < 1e-6,
        str(S.get_bill(bill_id)["total"]))
    cek("stok berkurang sesuai retur",
        abs(float(M.saldo_stok(cid, produk_id)["qty"]) - 5.0) < 1e-9,
        str(M.saldo_stok(cid, produk_id)["qty"]))

    print("\n--- Dialog yang pernah terpotong ---")
    from akuntansi_id.ui.dialog_bug import DialogLaporBug
    from akuntansi_id.ui.pages.kontrak_page import DialogKontrak

    lapor = DialogLaporBug()
    cek("dialog lapor bug muat tanpa diperas",
        lapor.sizeHint().height() <= 700, str(lapor.sizeHint().height()))
    cek("kotak langkah dipatok pada tinggi yang cukup",
        lapor.inp_langkah.minimumHeight() == lapor.inp_langkah.maximumHeight()
        and lapor.inp_langkah.maximumHeight() >= 110,
        f"min={lapor.inp_langkah.minimumHeight()} "
        f"max={lapor.inp_langkah.maximumHeight()}")
    lapor.close()

    kontrak = DialogKontrak(ctx)
    cek("tanggal berakhir cukup lebar",
        kontrak.dt_akhir.minimumWidth() >= 125,
        str(kontrak.dt_akhir.minimumWidth()))
    cek("tanpa batas waktu berupa kotak centang",
        isinstance(kontrak.chk_tanpa_akhir, QCheckBox))
    cek("format tanggal berakhir lengkap",
        kontrak.dt_akhir.displayFormat() == "dd/MM/yyyy",
        kontrak.dt_akhir.displayFormat())
    cek("judul tab memakai ampersand ganda agar tampil utuh",
        kontrak.tabs.tabText(1) == "Nilai && Pajak"
        and kontrak.tabs.tabText(2) == "Barang && Jasa")
    kontrak.close()

    print(f"\nHASIL: {LULUS} LULUS, {GAGAL} GAGAL")
    return 0 if GAGAL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
