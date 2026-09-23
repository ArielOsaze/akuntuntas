"""Uji sub-kategori sidebar: default tertutup dan dibuka dengan satu klik."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
DATA = AKAR / "_ujimenu"
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
            keluar.append(w.text().replace("&&", "&"))
    return keluar


def main() -> int:
    if DATA.exists():
        shutil.rmtree(DATA, ignore_errors=True)
    db.init_db()
    sec.ensure_default_admin()
    cid = services.create_company("PT Uji Menu", "pt")
    services.set_saldo_awal(cid, {"1001": 50_000_000, "3001": 50_000_000})

    app = QApplication.instance() or QApplication([])
    app.setStyleSheet(theme.stylesheet())

    print("=== 1. Pertama kali buka, belum ada pilihan tersimpan ===")
    db.ex("DELETE FROM settings WHERE key='sidebar_lipat'")
    jendela = MainWindow(sec.login("admin", "admin123"))
    jendela.ctx.company_id = cid
    jendela.resize(1440, 940)
    jendela.show()
    for _ in range(10):
        app.processEvents()
    sidebar = jendela.findChild(Sidebar)

    terbuka = [n for n, (jd, _) in sidebar._grup.items() if jd.isChecked()]
    cek("semua kelompok tertutup saat pertama buka", not terbuka,
        f"terbuka: {terbuka}" if terbuka else "0 terbuka")
    cek("jumlah kelompok sesuai", len(sidebar._grup) == 6,
        f"{len(sidebar._grup)} kelompok")

    print("\n=== 2. Isi tersembunyi saat tertutup ===")
    tersembunyi = all(not w.isVisible() for _, w in sidebar._grup.values())
    cek("isi semua kelompok tersembunyi", tersembunyi)

    print("\n=== 3. Klik satu kelompok, isinya muncul ===")
    judul, wadah = sidebar._grup["BUKU & KAS"]
    judul.setChecked(True)
    app.processEvents()
    cek("kelompok terbuka setelah diklik", judul.isChecked())
    cek("isi kelompok terlihat", wadah.isVisible())
    isi = isi_kelompok(wadah)
    cek("isi kelompok lengkap", isi == ["Jurnal Umum", "Biaya & Pengeluaran",
                                        "Kas & Bank"], f"{isi}")

    print("\n=== 4. Klik lagi untuk menutup ===")
    judul.setChecked(False)
    app.processEvents()
    cek("isi tersembunyi setelah ditutup", not wadah.isVisible())

    print("\n=== 5. Judul kelompok tampil tanpa garis bawah ===")
    bergaris = []
    for nama, (jd, _) in sidebar._grup.items():
        tampil = jd.text().replace("&&", "&")
        if "_" in tampil:
            bergaris.append(tampil)
    cek("judul kelompok bebas garis bawah", not bergaris,
        ", ".join(bergaris[:3]))
    cek("tanda & tampil benar",
        sidebar._grup["BUKU & KAS"][0].text() == "BUKU && KAS",
        sidebar._grup["BUKU & KAS"][0].text())

    print("\n=== 6. Pilihan diingat saat aplikasi dibuka ulang ===")
    sidebar._grup["BUKU & KAS"][0].setChecked(True)
    sidebar._grup["PERPAJAKAN"][0].setChecked(True)
    app.processEvents()

    jendela2 = MainWindow(sec.login("admin", "admin123"))
    jendela2.ctx.company_id = cid
    jendela2.resize(1440, 940)
    jendela2.show()
    for _ in range(10):
        app.processEvents()
    sidebar2 = jendela2.findChild(Sidebar)
    terbuka2 = sorted(n for n, (jd, _) in sidebar2._grup.items()
                      if jd.isChecked())
    cek("pilihan buka diingat", terbuka2 == ["BUKU & KAS", "PERPAJAKAN"],
        f"{terbuka2}")

    print("\n=== 7. Navigasi ke menu membuka kelompoknya otomatis ===")
    sidebar2._grup["TATA KELOLA"][0].setChecked(False)
    app.processEvents()
    jendela2._navigasi("audit")
    app.processEvents()
    cek("kelompok terbuka saat menunya dipilih",
        sidebar2._grup["TATA KELOLA"][0].isChecked())

    print("\n=== 8. Seluruh menu tetap dapat dibuka ===")
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

    print("\n" + "=" * 74)
    total_gagal = [h for h in HASIL if not h[1]]
    if total_gagal:
        print(f"HASIL: {len(HASIL) - len(total_gagal)} LULUS, "
              f"{len(total_gagal)} GAGAL")
        for nama, _, detail in total_gagal:
            print(f"   GAGAL: {nama} {detail}")
        return 1
    print(f"HASIL: {len(HASIL)} LULUS, 0 GAGAL")
    return 0


if __name__ == "__main__":
    sys.exit(main())
