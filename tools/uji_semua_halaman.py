"""
Jalankan seluruh halaman dengan penangkap error yang ketat.

Cara pakai:
    python tools/uji_semua_halaman.py

Berbeda dari pemeriksaan statis, alat ini benar-benar membuka setiap halaman
dan setiap tabnya, lalu melaporkan setiap pengecualian yang tertangkap —
termasuk yang ditelan oleh blok try/except di dalam aplikasi.
"""
from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
os.environ["AKUNTANSIID_DATA"] = str(AKAR / "_contoh")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(AKAR / "src"))

from PySide6.QtWidgets import QApplication, QTabWidget

HALAMAN = ["dashboard", "analisis", "pencarian", "jurnal", "penjualan",
           "pembelian", "biaya", "bank", "mitra", "produk", "aset", "payroll",
           "dimensi", "periode", "konsolidasi", "laporan", "pajak",
           "pajak_lanjutan", "checklist",
           "pengguna", "audit", "recycle", "impor", "coa", "perusahaan", "lan",
           "pengaturan", "bantuan"]

# error yang muncul saat pemuatan halaman dikumpulkan di sini
ERROR: list = []


def pasang_penangkap():
    """Catat setiap print('[halaman] gagal memuat: ...') dari main_window."""
    import io
    asli = sys.stdout

    class Penangkap(io.TextIOBase):
        def write(self, teks):
            asli.write(teks)
            if "gagal memuat" in teks:
                ERROR.append(teks.strip())
            return len(teks)

    sys.stdout = Penangkap()


def main() -> int:
    from akuntansi_id import config, db, services
    from akuntansi_id.core import security as sec
    from akuntansi_id.ui import theme
    from akuntansi_id.ui.main_window import MainWindow


    def _lisensi_uji():
        """Lisensi uji paket Enterprise agar seluruh halaman ikut diperiksa."""
        from akuntansi_id.core.license import Lisensi
        return Lisensi(kunci='ATNTUJI', paket='enterprise', fitur={})

    app = QApplication([])
    app.setStyleSheet(theme.stylesheet())
    config.ensure_dirs()
    db.init_db()
    sec.ensure_default_admin()

    perusahaan = services.list_companies(aktif_saja=False)
    if not perusahaan:
        print("Jalankan dulu: python tools/buat_data_contoh.py")
        return 2

    cid = perusahaan[0]["id"]
    hasil = sec.login("admin", config.DEFAULT_ADMIN_PASSWORD)
    jendela = MainWindow(hasil, lisensi=_lisensi_uji())
    jendela.ctx.company_id = cid
    jendela.ctx.company = services.get_company(cid)
    jendela.resize(1600, 1000)
    jendela.show()

    pasang_penangkap()

    gagal = 0
    for kode in HALAMAN:
        jendela._navigasi(kode)
        halaman = jendela.halaman.get(kode)
        if halaman is None:
            print(f"GAGAL  halaman '{kode}' tidak terbentuk")
            gagal += 1
            continue

        # muat ulang untuk menangkap error pada pemuatan kedua
        for putaran in range(2):
            try:
                if hasattr(halaman, "muat"):
                    halaman.muat()
                for _ in range(6):
                    app.processEvents()
            except Exception as e:
                gagal += 1
                print(f"GAGAL  '{kode}' putaran {putaran + 1}: "
                      f"{type(e).__name__}: {e}")
                traceback.print_exc()

        # buka setiap tab
        for tab in halaman.findChildren(QTabWidget):
            for i in range(tab.count()):
                try:
                    tab.setCurrentIndex(i)
                    for _ in range(5):
                        app.processEvents()
                except Exception as e:
                    gagal += 1
                    print(f"GAGAL  tab '{kode}'[{i}] '{tab.tabText(i)}': "
                          f"{type(e).__name__}: {e}")

    print()
    print("=" * 70)
    if ERROR:
        print(f"Error tertangkap saat pemuatan: {len(ERROR)}")
        for e in ERROR:
            print(f"   {e}")
    if gagal:
        print(f"HASIL: {gagal} kegagalan")
    else:
        print("HASIL: seluruh halaman dan tab termuat tanpa error")
    print("=" * 70)
    return 1 if (gagal or ERROR) else 0


if __name__ == "__main__":
    sys.exit(main())
