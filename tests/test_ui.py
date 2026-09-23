"""
Uji muat semua halaman antarmuka secara headless.
Memastikan setiap halaman dapat dibuat, dimuat, dan berpindah tanpa error.
"""
import os
import sys
import traceback
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
_DIR_UJI = Path(__file__).parent.parent / "_uitest"
if _DIR_UJI.exists():
    import shutil
    shutil.rmtree(_DIR_UJI, ignore_errors=True)
os.environ["AKUNTANSIID_DATA"] = str(_DIR_UJI)

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from PySide6.QtWidgets import QApplication

from akuntansi_id import config, db, services
from akuntansi_id.core import security as sec
from akuntansi_id.ui.main_window import MainWindow
from akuntansi_id.ui import theme

# Lisensi uji dipakai agar seluruh halaman ikut diperiksa, termasuk
# halaman yang hanya tersedia pada paket Enterprise.
from akuntansi_id.core.license import Lisensi as _LisensiUji
_LISENSI_UJI = _LisensiUji(kunci='ATNTUJI', paket='enterprise', fitur={})


HALAMAN = [
    "dashboard", "analisis", "pencarian", "jurnal", "penjualan", "pembelian",
    "biaya", "bank", "mitra", "produk", "aset", "payroll", "dimensi",
    "periode", "konsolidasi", "laporan", "pajak", "checklist", "pengguna",
    "audit", "recycle", "impor", "coa", "perusahaan", "lan", "pengaturan",
    "bantuan",
]

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


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyleSheet(theme.stylesheet())

    config.ensure_dirs()
    db.init_db()
    sec.ensure_default_admin()

    perusahaan = services.list_companies(aktif_saja=False)
    if not perusahaan:
        cid = services.create_company(
            "PT Uji Antarmuka", "pt", npwp="01.234.567.8-901.000",
            alamat="Jl. Uji 1", kota="Jakarta", pkp=True)
    else:
        cid = perusahaan[0]["id"]

    hasil_login = sec.login("admin", config.DEFAULT_ADMIN_PASSWORD)
    if not hasil_login.ok:
        sec.ensure_default_admin()
        hasil_login = sec.login("admin", config.DEFAULT_ADMIN_PASSWORD)

    jendela = MainWindow(hasil_login, lisensi=_LISENSI_UJI)
    jendela.ctx.company_id = cid
    jendela.ctx.company = services.get_company(cid)
    jendela.ctx.beginner = True

    for kode in HALAMAN:
        try:
            jendela._navigasi(kode)
            halaman = jendela.halaman.get(kode)
            cek(f"halaman '{kode}' termuat",
                halaman is not None and jendela.stack.currentWidget() is halaman)
            if halaman is not None and hasattr(halaman, "muat"):
                halaman.muat()
                cek(f"halaman '{kode}' muat() berhasil", True)
        except Exception as e:
            cek(f"halaman '{kode}' termuat", False, f"{type(e).__name__}: {e}")
            traceback.print_exc()

    for kode in HALAMAN:
        try:
            jendela._navigasi(kode)
            cek(f"navigasi ulang ke '{kode}'", True)
        except Exception as e:
            cek(f"navigasi ulang ke '{kode}'", False, str(e))

    jendela.ctx.beginner = False
    for kode in HALAMAN:
        try:
            halaman = jendela.halaman.get(kode)
            if halaman is not None and hasattr(halaman, "muat"):
                halaman.muat()
            cek(f"mode ahli '{kode}'", True)
        except Exception as e:
            cek(f"mode ahli '{kode}'", False, f"{type(e).__name__}: {e}")

    print(f"\nHASIL: {lulus} LULUS, {gagal} GAGAL")
    return 1 if gagal else 0


if __name__ == "__main__":
    sys.exit(main())
