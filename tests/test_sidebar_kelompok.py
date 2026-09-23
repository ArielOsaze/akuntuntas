"""Uji sub-kategori sidebar: pengelompokan, buka-tutup, dan pengingatan.

Yang diperiksa:
  1. Setiap kelompok berisi menu yang benar-benar satu kesatuan.
  2. Kelompok dapat dibuka dan ditutup.
  3. Membuka menu dari kelompok tertutup otomatis membuka kelompoknya.
  4. Pilihan buka/tutup diingat saat aplikasi dibuka ulang.
  5. Semua menu tetap dapat dijangkau.
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
DATA = AKAR / "_ujisidebar"
os.environ["AKUNTANSIID_DATA"] = str(DATA)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(AKAR / "src"))

from PySide6.QtWidgets import QApplication  # noqa: E402

from akuntansi_id import db, services  # noqa: E402
from akuntansi_id.core import security as sec  # noqa: E402
from akuntansi_id.ui import theme  # noqa: E402
from akuntansi_id.ui.main_window import MainWindow, Sidebar  # noqa: E402

HASIL: list = []


def cek(nama, syarat, detail=""):
    HASIL.append((nama, bool(syarat), detail))
    print(f"  {'LULUS' if syarat else 'GAGAL'}  {nama}"
          + (f"  [{detail}]" if detail else ""))


def isi_kelompok(wadah) -> list:
    keluar = []
    for i in range(wadah.layout().count()):
        it = wadah.layout().itemAt(i)
        w = it.widget() if it else None
        if w is not None:
            keluar.append(w)
    return keluar


def main() -> int:
    if DATA.exists():
        shutil.rmtree(DATA, ignore_errors=True)
    db.init_db()
    sec.ensure_default_admin()
    cid = services.create_company("PT Uji Sidebar", "pt")
    services.set_saldo_awal(cid, {"1001": 10_000_000, "3001": 10_000_000})

    app = QApplication.instance() or QApplication([])
    app.setStyleSheet(theme.stylesheet())

    print("=== Pengelompokan menu ===")
    jendela = MainWindow(sec.login("admin", "admin123"))
    jendela.resize(1440, 940)
    jendela.show()
    app.processEvents()
    sidebar = jendela.findChild(Sidebar)

    harapan = {
        "BUKU & KAS": {"jurnal", "biaya", "bank"},
        "DATA USAHA": {"mitra", "kontrak", "produk", "aset", "payroll"},
        "PERPAJAKAN": {"pajak", "pajak_lanjutan", "checklist"},
        "AKUNTANSI LANJUTAN": {"dimensi", "periode", "konsolidasi"},
        "TATA KELOLA": {"pengguna", "audit", "recycle", "impor"},
        "PENGATURAN": {"coa", "perusahaan", "lan", "pengaturan", "bantuan"},
    }
    for nama, kode_harap in harapan.items():
        pasangan = sidebar._grup.get(nama)
        cek(f"kelompok {nama} ada", pasangan is not None)
        if pasangan is None:
            continue
        dapat = set()
        for w in isi_kelompok(pasangan[1]):
            for kode, b in sidebar.tombol.items():
                if b is w:
                    dapat.add(kode)
        cek(f"isi {nama} tepat", dapat == kode_harap,
            f"dapat {sorted(dapat)}")

    print("\n=== Menu berdiri sendiri (bukan kelompok) ===")
    for kode, nama in (("dashboard", "Dashboard"), ("penjualan", "Penjualan"),
                       ("pembelian", "Pembelian"), ("laporan", "Laporan Keuangan")):
        b = sidebar.tombol.get(kode)
        cek(f"{nama} dapat dijangkau", b is not None)

    print("\n=== Buka dan tutup ===")
    grup = sidebar._grup["DATA USAHA"]
    judul, wadah = grup
    judul.setChecked(False)
    app.processEvents()
    cek("kelompok dapat ditutup", not wadah.isVisible())
    judul.setChecked(True)
    app.processEvents()
    cek("kelompok dapat dibuka", wadah.isVisible())

    print("\n=== Buka otomatis saat menunya dipilih ===")
    judul.setChecked(False)
    app.processEvents()
    jendela._navigasi("mitra")
    app.processEvents()
    cek("navigasi membuka kelompoknya", judul.isChecked())
    cek("halaman mitra tampil",
        jendela.stack.currentWidget() is jendela.halaman.get("mitra"))

    print("\n=== Pilihan diingat saat dibuka ulang ===")
    sidebar._grup["DATA USAHA"][0].setChecked(False)
    sidebar._grup["TATA KELOLA"][0].setChecked(True)
    app.processEvents()

    jendela2 = MainWindow(sec.login("admin", "admin123"))
    jendela2.resize(1440, 940)
    jendela2.show()
    app.processEvents()
    sidebar2 = jendela2.findChild(Sidebar)
    cek("pilihan tutup diingat",
        not sidebar2._grup["DATA USAHA"][0].isChecked())
    cek("pilihan buka diingat",
        sidebar2._grup["TATA KELOLA"][0].isChecked())
    # BUKU & KAS tidak diubah pada langkah di atas, jadi harus tetap seperti
    # keadaan sebelumnya: tertutup (bawaan bagi pengguna yang belum memilih).
    cek("kelompok lain tidak berubah",
        not sidebar2._grup["BUKU & KAS"][0].isChecked())

    print("\n=== Seluruh menu tetap dapat dibuka ===")
    gagal = []
    for kode in sidebar2.tombol:
        try:
            jendela2._navigasi(kode)
            app.processEvents()
            if jendela2.stack.currentWidget() is not jendela2.halaman.get(kode):
                gagal.append(kode)
        except Exception as e:
            gagal.append(f"{kode}: {e}")
    cek(f"seluruh {len(sidebar2.tombol)} menu dapat dibuka", not gagal,
        ", ".join(gagal[:4]))

    print("\n=== Judul kelompok tidak terpotong ===")
    from PySide6.QtGui import QFontMetrics
    sempit = []
    for nama, (judul, _) in sidebar2._grup.items():
        butuh = QFontMetrics(judul.font()).horizontalAdvance(nama) + 34
        if judul.width() < butuh:
            sempit.append(f"{nama} ({judul.width()}<{butuh})")
    cek("semua judul kelompok muat", not sempit, ", ".join(sempit[:3]))

    print("\n=== Tidak ada garis bawah pada nama menu ===")
    bergaris = [b.text().replace("&&", "&") for b in sidebar2.tombol.values()
                if "_" in b.text()]
    cek("nama menu bebas garis bawah", not bergaris,
        ", ".join(bergaris[:3]))

    gagal_total = [h for h in HASIL if not h[1]]
    print("\n" + "=" * 74)
    if gagal_total:
        print(f"HASIL: {len(HASIL) - len(gagal_total)} LULUS, "
              f"{len(gagal_total)} GAGAL")
        for nama, _, detail in gagal_total:
            print(f"   GAGAL: {nama} {detail}")
        return 1
    print(f"HASIL: {len(HASIL)} LULUS, 0 GAGAL")
    return 0


if __name__ == "__main__":
    sys.exit(main())
