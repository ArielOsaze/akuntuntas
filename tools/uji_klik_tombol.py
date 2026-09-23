"""
Uji interaksi menyeluruh: buka setiap halaman, klik setiap tombol yang aman,
dan laporkan setiap error yang muncul.

Cara pakai:
    python tools/uji_klik_tombol.py

Tombol yang membuka dialog akan dites; dialog segera ditutup otomatis.
Tombol yang bersifat merusak (hapus, void, tutup buku, pulihkan) dilewati
agar data contoh tidak berubah.
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

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (QApplication, QDialog, QMessageBox, QPushButton,
                               QTabWidget)

HALAMAN = ["dashboard", "analisis", "pencarian", "jurnal", "penjualan",
           "pembelian", "biaya", "bank", "mitra", "produk", "aset", "payroll",
           "dimensi", "periode", "konsolidasi", "laporan", "pajak",
           "pajak_lanjutan", "checklist",
           "pengguna", "audit", "recycle", "impor", "coa", "perusahaan", "lan",
           "pengaturan", "bantuan"]

# tombol yang tidak boleh diklik otomatis (mengubah/menghapus data)
LEWATI = ("hapus", "void", "batal", "tolak", "tutup periode", "tutup tahun",
          "bersihkan", "pulihkan", "restore", "reset", "nonaktifkan",
          "hentikan", "buang", "keluar", "simpan", "posting", "bayar",
          "transfer", "impor sekarang", "jalankan", "selesaikan", "tutup buku",
          # Tombol yang membuka aplikasi lain. Mengkliknya membuka program
          # di luar aplikasi: "kirim lewat email" membuka aplikasi email
          # bawaan, dan di sebagian komputer hal itu membuka OneNote atau
          # peramban. Tombol seperti ini tidak diuji dengan klik, tetapi
          # lewat pemeriksaan terpisah pada tautan yang dihasilkannya.
          "kirim", "email", "buka folder", "buka lokasi", "unduh",
          "buka tautan", "situs", "panduan daring",
          # Membuka dialog penyimpanan berkas milik Windows.
          "ekspor", "cetak", "simpan berkas")

ERROR: list = []


def tutup_dialog_muncul():
    """Tutup setiap dialog yang sedang tampil agar pengujian tidak macet.

    Dialog modal dapat menghentikan pengujian tanpa batas, sehingga setiap
    dialog yang muncul langsung ditutup dengan hasil 'batal'.
    """
    app = QApplication.instance()
    for w in list(app.topLevelWidgets()):
        if isinstance(w, QDialog) and w.isVisible():
            w.reject()
            w.close()
        elif isinstance(w, QMessageBox) and w.isVisible():
            w.close()


def uji_tombol(halaman, kode: str) -> int:
    """Klik setiap tombol yang aman dan tangkap error yang muncul.

    Dialog yang terbuka dijalankan sebentar di thread utama lalu ditutup,
    sehingga konstruktor dialog ikut teruji.
    """
    gagal = 0
    tombol = [b for b in halaman.findChildren(QPushButton) if b.isVisible()]
    for b in tombol:
        teks = b.text().strip().lower()
        if not teks or any(k in teks for k in LEWATI):
            continue

        # jadwalkan penutupan dialog sebelum tombol diklik
        pengatur = QTimer()
        pengatur.setInterval(120)
        pengatur.timeout.connect(tutup_dialog_muncul)
        pengatur.start()

        try:
            b.click()
            for _ in range(8):
                QApplication.instance().processEvents()
        except Exception as e:
            gagal += 1
            ERROR.append(f"{kode} tombol '{b.text()}': {type(e).__name__}: {e}")
            traceback.print_exc()
        finally:
            pengatur.stop()
            tutup_dialog_muncul()
    return gagal


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

    # cegah dialog pesan menghambat pengujian
    QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.Ok)
    QMessageBox.warning = staticmethod(lambda *a, **k: QMessageBox.Ok)
    QMessageBox.critical = staticmethod(lambda *a, **k: QMessageBox.Ok)
    QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.No)

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
        jendela._navigasi(kode)
        halaman = jendela.halaman.get(kode)
        if halaman is None:
            continue
        if hasattr(halaman, "muat"):
            halaman.muat()
        for _ in range(8):
            app.processEvents()

        jumlah_tombol = len([b for b in halaman.findChildren(QPushButton)
                             if b.isVisible()])
        gagal = uji_tombol(halaman, kode)

        # buka tiap tab lalu uji tombol di dalamnya
        for tab in halaman.findChildren(QTabWidget):
            for i in range(tab.count()):
                tab.setCurrentIndex(i)
                for _ in range(6):
                    app.processEvents()
                gagal += uji_tombol(halaman, f"{kode}/tab{i}")

        total += gagal
        status = "OK" if gagal == 0 else f"GAGAL {gagal}"
        print(f"{status:9s} {kode:14s} ({jumlah_tombol} tombol terlihat)")

    print()
    print("=" * 70)
    if ERROR:
        print(f"Error yang tertangkap: {len(ERROR)}")
        for e in ERROR[:40]:
            print(f"   {e}")
    if total:
        print(f"HASIL: {total} tombol menimbulkan error")
    else:
        print("HASIL: seluruh tombol aman diklik tanpa error")
    print("=" * 70)
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
