"""
Periksa tata letak: deteksi label yang teksnya tidak muat pada tempatnya.

Cara pakai:
    python tools/periksa_tata_letak.py

Pemeriksaan ini membuka setiap halaman lalu mengukur lebar teks terhadap
lebar labelnya. Label yang membungkus (word wrap) atau memakai elipsis
tidak dilaporkan karena teksnya tetap dapat dibaca pengguna.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
os.environ["AKUNTANSIID_DATA"] = str(AKAR / "_contoh")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(AKAR / "src"))

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QFontMetrics
from PySide6.QtWidgets import QApplication, QLabel, QTabWidget

HALAMAN = ["dashboard", "analisis", "pencarian", "jurnal", "penjualan",
           "pembelian", "biaya", "bank", "mitra", "produk", "aset", "payroll",
           "dimensi", "periode", "konsolidasi", "laporan", "pajak", "checklist",
           "pengguna", "audit", "recycle", "impor", "coa", "perusahaan", "lan",
           "pengaturan", "bantuan"]


def lebar_teks(lbl, teks: str) -> int:
    """Lebar teks memakai font efektif label.

    fontMetrics() memakai font default widget, bukan ukuran dari stylesheet,
    sehingga hasilnya bisa jauh berbeda dari tampilan sebenarnya.
    """
    font = QFont(lbl.font())
    for bagian in lbl.styleSheet().split(";"):
        if ":" not in bagian:
            continue
        nama, nilai = bagian.split(":", 1)
        nama, nilai = nama.strip(), nilai.strip()
        if nama == "font-size":
            try:
                font.setPixelSize(int(float(nilai.replace("px", ""))))
            except ValueError:
                pass
        elif nama == "font-weight":
            try:
                font.setWeight(QFont.Weight(int(nilai)))
            except ValueError:
                pass
    return QFontMetrics(font).horizontalAdvance(teks)


def label_terpotong(halaman) -> list:
    """Label yang seluruh teksnya tidak muat dan tidak punya mekanisme elipsis."""
    masalah = []
    for lbl in halaman.findChildren(QLabel):
        if not lbl.isVisible() or not lbl.text().strip():
            continue
        # label berisi markup kaya (rich text) tidak diukur sebagai teks biasa
        if lbl.textFormat() == Qt.RichText:
            continue
        teks = lbl.text()
        # lewati label yang sudah dipotong sendiri oleh aplikasi
        if "…" in teks:
            continue
        # lewati label yang hanya berisi ikon (digambar sebagai pixmap)
        if lbl.pixmap() and not lbl.pixmap().isNull():
            continue
        # label murni angka/simbol pendek tidak perlu dilaporkan
        if len(teks) <= 4:
            continue

        # label terlihat tetapi tidak mendapat ruang sama sekali: terhimpit
        if lbl.width() <= 4 or lbl.height() <= 2:
            masalah.append((teks, -1, lbl.height()))
            continue

        if lbl.wordWrap():
            # teks yang membungkus tetap terpotong bila tinggi kotaknya
            # tidak cukup untuk seluruh baris
            tinggi_perlu = lbl.heightForWidth(lbl.width())
            if tinggi_perlu > lbl.height() + 2:
                masalah.append((teks, tinggi_perlu, lbl.height()))
            continue

        lebar = lebar_teks(lbl, teks)
        if lebar > lbl.width() + 2:
            masalah.append((teks, lebar, lbl.width()))
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
        print("Belum ada data contoh. Jalankan dulu:")
        print("    python tools/buat_data_contoh.py")
        return 2

    cid = perusahaan[0]["id"]
    hasil_login = sec.login("admin", config.DEFAULT_ADMIN_PASSWORD)
    jendela = MainWindow(hasil_login, lisensi=_lisensi_uji())
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
        for _ in range(6):
            app.processEvents()

        kumpulan = []
        for tab in [None] + halaman.findChildren(QTabWidget):
            if tab is not None:
                for i in range(tab.count()):
                    tab.setCurrentIndex(i)
                    for _ in range(4):
                        app.processEvents()
            kumpulan.extend(label_terpotong(halaman))

        unik = []
        for m in kumpulan:
            if m not in unik:
                unik.append(m)
        if unik:
            total += len(unik)
            print(f"\n[{kode}] {len(unik)} label terpotong")
            for teks, lebar, tersedia in unik[:12]:
                print(f"   - '{teks[:52]}' butuh {lebar}px, tersedia {tersedia}px")

    print()
    print("=" * 70)
    if total:
        print(f"HASIL: {total} label terpotong ditemukan")
    else:
        print("HASIL: seluruh teks tampil utuh")
    print("=" * 70)
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
