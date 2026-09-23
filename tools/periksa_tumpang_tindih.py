"""
Periksa tumpang tindih widget: pastikan tidak ada kartu atau panel yang
saling menimpa setelah halaman dimuat berulang kali.

Cara pakai:
    python tools/periksa_tumpang_tindih.py

Halaman dimuat dua kali (simulasi pindah halaman bolak-balik) karena
masalah tumpang tindih biasanya baru muncul pada pemuatan ulang.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
os.environ["AKUNTANSIID_DATA"] = str(AKAR / "_contoh")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(AKAR / "src"))

from PySide6.QtWidgets import QApplication, QFrame, QWidget

HALAMAN = ["dashboard", "analisis", "penjualan", "pembelian", "biaya", "bank",
           "mitra", "produk", "aset", "payroll", "dimensi", "periode",
           "konsolidasi", "laporan", "pajak", "checklist", "pengguna", "audit",
           "recycle", "impor", "coa", "perusahaan", "lan", "pengaturan",
           "bantuan", "jurnal", "pencarian"]

# jenis widget yang membentuk blok visual
BLOK = (QFrame,)


def tumpang_tindih(halaman: QWidget) -> list:
    """Cari blok visual bersaudara yang kotaknya saling menimpa."""
    masalah = []
    for induk in halaman.findChildren(QWidget):
        anak = [x for x in induk.children()
                if isinstance(x, BLOK) and x.isVisible()
                and x.parent() is induk]
        for i in range(len(anak)):
            for k in range(i + 1, len(anak)):
                a, b = anak[i], anak[k]
                ga = a.geometry()
                gb = b.geometry()
                if ga.width() == 0 or gb.width() == 0:
                    continue
                kiri = max(ga.left(), gb.left())
                atas = max(ga.top(), gb.top())
                kanan = min(ga.right(), gb.right())
                bawah = min(ga.bottom(), gb.bottom())
                if kanan - kiri > 2 and bawah - atas > 2:
                    masalah.append(
                        (type(a).__name__, ga.getRect(), type(b).__name__,
                         gb.getRect()))
    return masalah


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

    total = 0
    for kode in HALAMAN:
        halaman = jendela.halaman.get(kode)
        if halaman is None:
            continue
        # muat tiga kali: meniru pengguna berpindah halaman bolak-balik
        for putaran in range(3):
            jendela._navigasi(kode)
            if hasattr(halaman, "muat"):
                halaman.muat()
            for _ in range(8):
                app.processEvents()
        masalah = tumpang_tindih(halaman)
        if masalah:
            total += len(masalah)
            print(f"\n[{kode}] {len(masalah)} tumpang tindih")
            unik = set()
            for a, ra, b, rb in masalah:
                kunci = (a, b)
                if kunci in unik:
                    continue
                unik.add(kunci)
                print(f"   {a} {ra} vs {b} {rb}")

    print()
    print("=" * 70)
    if total:
        print(f"HASIL: {total} tumpang tindih ditemukan")
    else:
        print("HASIL: tidak ada widget bertumpuk")
    print("=" * 70)
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
