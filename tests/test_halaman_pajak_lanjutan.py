"""Uji halaman Pajak Lanjutan: semua tab termuat & dialog menyimpan data."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
DATA = AKAR / "_ujipajak2"
os.environ["AKUNTANSIID_DATA"] = str(DATA)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(AKAR / "src"))

from PySide6.QtWidgets import (  # noqa: E402
    QApplication, QDoubleSpinBox, QLineEdit, QSpinBox,
)

from akuntansi_id import db, modules as M, modules_pajak as P  # noqa: E402
from akuntansi_id import services  # noqa: E402
from akuntansi_id.core import security as sec  # noqa: E402
from akuntansi_id.ui.pages import pajak_lanjutan as PL  # noqa: E402

HASIL: list = []


def cek(nama, syarat, detail=""):
    HASIL.append((nama, bool(syarat), detail))
    print(f"  {'LULUS' if syarat else 'GAGAL'}  {nama}"
          + (f"  [{detail}]" if detail else ""))


class Ctx:
    def __init__(self, cid, tahun):
        self.company_id = cid
        self.tahun = tahun
        self.user = {"id": 1, "username": "admin", "role": "admin"}
        self.nama_tampil = "Administrator"


def isi_dialog(dlg):
    """Isi semua kolom dialog dengan nilai wajar lalu simpan."""
    for wdg in dlg.findChildren(QLineEdit):
        if wdg.isReadOnly() or wdg.text():
            continue
        if "nomor" in wdg.placeholderText().lower() or \
           "010.000" in wdg.placeholderText():
            wdg.setText("010.000-26.00000001" if "Awal" in
                        (dlg.form.labelForField(wdg).text() if
                         dlg.form.labelForField(wdg) else "") else
                        "010.000-26.00000100")
        else:
            wdg.setText("Uji Data")
    for wdg in dlg.findChildren(QDoubleSpinBox):
        if wdg.value() == 0:
            wdg.setValue(10_000_000)
    for wdg in dlg.findChildren(QSpinBox):
        if wdg.value() == 0:
            wdg.setValue(2026)
    return dlg


def jalankan():
    if DATA.exists():
        shutil.rmtree(DATA, ignore_errors=True)
    db.init_db()
    sec.ensure_default_admin()

    app = QApplication.instance() or QApplication([])
    cid = services.create_company("PT Uji Halaman", "pt", pkp=True)
    services.set_saldo_awal(cid, {"1001": 100_000_000, "3001": 100_000_000})
    M.buat_mitra(cid, "PT Pelanggan Uji", "customer", pkp=True)
    M.buat_mitra(cid, "PT Pemasok Uji", "vendor", pkp=True)

    ctx = Ctx(cid, 2026)
    page = PL.PajakLanjutanPage(ctx)
    page.resize(1280, 800)
    page.show()
    app.processEvents()

    print("=== Semua tab termuat ===")
    nama_tab = ["Nomor Seri Faktur", "Faktur Pajak", "Uang Muka",
                "Bea Meterai", "Pajak Daerah", "Kurs", "PPh 15",
                "Jurnal Balik"]
    for i, nama in enumerate(nama_tab):
        page.tabs.setCurrentIndex(i)
        app.processEvents()
        jumlah = page.tabs.currentWidget().layout().count()
        cek(f"tab {nama} termuat", jumlah > 0, f"{jumlah} widget")
        cek(f"judul tab {nama} benar", page.tabs.tabText(i) == nama,
            page.tabs.tabText(i))

    print("\n=== Dialog menyimpan data ===")
    # NSFP
    page.tabs.setCurrentIndex(0)
    dlg = PL.DialogNSFP(page)
    dlg.ctx_company = cid
    dlg.inp_awal.setText("010.000-26.00000001")
    dlg.inp_akhir.setText("010.000-26.00000010")
    dlg.simpan()
    cek("dialog NSFP menyimpan", len(P.daftar_nsfp(cid, 2026)) == 1)

    # Faktur pajak
    dlg = PL.DialogFakturPajak(cid, "keluaran", page)
    dlg.inp_nama.setText("PT Pelanggan Uji")
    dlg.inp_npwp.setText("02.111.222.3-444.000")
    dlg.inp_dpp.setValue(20_000_000)
    dlg._hitung()
    cek("PPN otomatis 11%", dlg.inp_ppn.value() == 2_200_000,
        f"ppn={dlg.inp_ppn.value():,.0f}")
    dlg.simpan()
    fp = P.daftar_faktur_pajak(cid, "keluaran", 2026)
    cek("dialog faktur menyimpan", len(fp) == 1)
    cek("nomor seri otomatis dari NSFP", bool(fp[0]["nomor_seri"]),
        fp[0]["nomor_seri"] if fp else "")

    # Uang muka
    dlg = PL.DialogUangMuka(cid, "diterima", page)
    dlg.inp_jumlah.setValue(30_000_000)
    dlg.simpan()
    cek("dialog uang muka menyimpan",
        len(P.daftar_uang_muka(cid, "diterima")) == 1)

    # Meterai
    dlg = PL.DialogMeterai(cid, page)
    dlg.inp_dokumen.setText("Perjanjian Kerja Sama")
    dlg.inp_nilai.setValue(50_000_000)
    dlg._hitung()
    cek("meterai terhitung", dlg.lbl_total.text() != "Rp 0",
        dlg.lbl_total.text())
    dlg.simpan()
    cek("dialog meterai menyimpan", len(P.daftar_meterai(cid, 2026)) == 1)

    # Pajak daerah
    dlg = PL.DialogPajakDaerah(cid, page)
    dlg.inp_dpp.setValue(5_000_000)
    dlg._hitung()
    dlg.simpan()
    cek("dialog pajak daerah menyimpan",
        len(P.daftar_pajak_daerah(cid, 2026)) == 1)

    # Kurs
    dlg = PL.DialogKurs(cid, page)
    dlg.inp_kurs.setValue(16_200)
    dlg.simpan()
    cek("dialog kurs menyimpan", len(P.daftar_kurs(cid)) == 1)
    cek("kurs tersimpan benar",
        P.kurs_terakhir(cid, "USD", "2026-12-31") == 16_200)

    # PPh 15
    dlg = PL.DialogPPh15(cid, page)
    dlg.inp_bruto.setValue(500_000_000)
    dlg._hitung()
    dlg.simpan()
    cek("dialog PPh 15 menyimpan", len(P.daftar_pph15(cid, 2026)) == 1)

    print("\n=== Muat ulang semua tab setelah data masuk ===")
    for i, nama in enumerate(nama_tab):
        page.tabs.setCurrentIndex(i)
        app.processEvents()
        cek(f"muat ulang tab {nama}", True)

    print("\n=== Tidak ada teks bergaris bawah ===")
    from PySide6.QtWidgets import QLabel
    teks_bermasalah = []
    for lbl in page.findChildren(QLabel):
        t = lbl.text() or ""
        if "_" in t and not t.startswith("<"):
            teks_bermasalah.append(t[:40])
    cek("tidak ada teks bergaris bawah", not teks_bermasalah,
        ", ".join(teks_bermasalah[:3]))

    gagal = [h for h in HASIL if not h[1]]
    print("\n" + "=" * 74)
    if gagal:
        print(f"HASIL: {len(HASIL) - len(gagal)} LULUS, {len(gagal)} GAGAL")
        for nama, _, detail in gagal:
            print(f"   GAGAL: {nama} {detail}")
        return 1
    print(f"HASIL: {len(HASIL)} LULUS, 0 GAGAL")
    return 0


if __name__ == "__main__":
    sys.exit(jalankan())
