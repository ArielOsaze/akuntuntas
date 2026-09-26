"""
AkunTuntas - Titik Masuk Aplikasi
==================================
Menjalankan aplikasi desktop: inisialisasi basis data, pemeriksaan awal,
lalu menampilkan jendela login.

Pemakaian:
    python -m akuntansi_id
    python -m akuntansi_id --data "D:\\DataAkuntansi"
"""
from __future__ import annotations

import argparse
import os
import sys
import traceback
from datetime import datetime


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="AkunTuntas",
        description="Pembukuan & Pajak Perusahaan Indonesia")
    p.add_argument("--data", help="Folder penyimpanan data (opsional)")
    p.add_argument("--version", action="store_true", help="Tampilkan versi")
    return p.parse_args()


def main() -> int:
    args = _parse_args()

    if args.data:
        os.environ["AKUNTANSIID_DATA"] = args.data

    # impor setelah env disiapkan agar path data mengikuti
    from akuntansi_id import config

    if args.version:
        print(f"{config.APP_LONG_NAME} versi {config.APP_VERSION} "
              f"({config.APP_BUILD})")
        return 0

    # ---------------------------------------------------------------- log
    config.ensure_dirs()
    log_file = config.LOG_PATH

    def catat(pesan: str):
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {pesan}\n")
        except Exception:
            pass

    # ---------------------------------------------------------------- Qt
    from PySide6.QtWidgets import QApplication, QMessageBox
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtGui import QFont

    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    app = QApplication(sys.argv)
    app.setApplicationName(config.APP_NAME)
    app.setApplicationDisplayName(config.APP_NAME)
    app.setApplicationVersion(config.APP_VERSION)
    app.setOrganizationName(config.APP_PUBLISHER)
    app.setStyle("Fusion")

    from akuntansi_id.ui import theme
    theme.palet_terang(app)

    from akuntansi_id.ui import widgets as w
    app.setWindowIcon(w.ikon_aplikasi())

    font = QFont("Segoe UI", 10)
    app.setFont(font)

    # ---------------------------------------------------------------- DB
    try:
        from akuntansi_id import coa, db
        from akuntansi_id.core import security as sec
        db.init_db()
        sec.ensure_default_admin()

        # Lengkapi akun bawaan yang belum ada pada perusahaan yang sudah
        # dibuat. Tanpa langkah ini, pengguna versi lama tidak mendapat akun
        # baru yang ditambahkan pada pembaruan, sehingga fitur yang memakai
        # akun tersebut gagal di komputer mereka.
        try:
            n_akun = coa.lengkapi_semua_perusahaan()
            if n_akun:
                catat(f"Melengkapi bagan akun: {n_akun} akun ditambahkan.")
        except Exception as galat:
            catat(f"Bagan akun tidak dapat dilengkapi: {galat}")

        catat(f"Aplikasi dimulai. Basis data: {config.DB_PATH}")

        # Cadangan otomatis dijalankan di latar belakang supaya pembukaan
        # aplikasi tidak tertunda. Kegagalan tidak menghentikan aplikasi.
        def cadangkan():
            try:
                berkas = db.backup_otomatis()
                if berkas:
                    catat(f"Cadangan otomatis dibuat: {berkas.name}")
            except Exception as e:
                catat(f"Cadangan otomatis gagal: {e}")

        QTimer.singleShot(4000, cadangkan)
    except Exception as e:
        detail = traceback.format_exc()
        catat(f"GAGAL INISIALISASI BASIS DATA: {e}\n{detail}")
        QMessageBox.critical(
            None, "Gagal memulai aplikasi",
            f"Basis data tidak dapat dibuka.\n\n"
            f"Lokasi: {config.DB_PATH}\n\n"
            f"Kesalahan: {e}\n\n"
            "Kemungkinan penyebab:\n"
            "• Berkas sedang dipakai proses lain - tutup aplikasi lain lalu coba lagi.\n"
            "• Folder tidak dapat ditulis - periksa izin akses folder.\n"
            "• Berkas rusak - pulihkan dari cadangan.")
        return 1

    # ---------------------------------------------------------------- tema
    from akuntansi_id.ui import theme
    app.setStyleSheet(theme.stylesheet())
    # Rapikan isi setiap dialog saat ditampilkan, termasuk daftar pilihannya.
    theme.pasang_penyesuai_dialog(app)

    # ---------------------------------------------------------------- UI
    try:
        from akuntansi_id.ui.main_window import JendelaAplikasi
        jendela = JendelaAplikasi()
        jendela.show()
        catat("Antarmuka ditampilkan.")
    except Exception as e:
        detail = traceback.format_exc()
        catat(f"GAGAL MEMBUKA ANTARMUKA: {e}\n{detail}")
        QMessageBox.critical(
            None, "Gagal membuka antarmuka",
            f"Antarmuka tidak dapat dimuat.\n\n{e}\n\n"
            f"Detail lengkap tersimpan di:\n{log_file}")
        return 1

    # ---------------------------------------------------------------- pengecualian tak tertangani
    def tangkap_pengecualian(tipe, nilai, tb):
        teks = "".join(traceback.format_exception(tipe, nilai, tb))
        catat(f"PENGECUALIAN TAK TERTANGANI:\n{teks}")
        # Simpan laporan lebih dulu supaya keterangannya tetap ada meski
        # pengguna memilih menutup jendela tanpa mengirim email.
        try:
            from akuntansi_id import laporan_bug as bug
            berkas = bug.simpan_laporan(bug.laporan_dari_pengecualian(tipe, nilai, tb))
            bug.simpan_metadata(f"{tipe.__name__}: {nilai}", berkas)
        except Exception:
            berkas = None

        try:
            from akuntansi_id.ui.dialog_bug import DialogLaporBug
            dlg = DialogLaporBug(
                jendela, kesalahan=f"{tipe.__name__}: {nilai}",
                jejak=teks[-1400:],
                judul_awal="Aplikasi mengalami kesalahan")
            dlg.exec()
        except Exception:
            try:
                QMessageBox.critical(
                    None, "Terjadi kesalahan",
                    f"Aplikasi mengalami kesalahan teknis:\n\n"
                    f"{tipe.__name__}: {nilai}\n\n"
                    f"Data Anda tetap aman. Detail tersimpan di:\n{log_file}\n\n"
                    "Anda dapat melanjutkan bekerja, namun sebaiknya simpan "
                    "pekerjaan dan mulai ulang aplikasi.")
            except Exception:
                pass

    sys.excepthook = tangkap_pengecualian

    kode = app.exec()
    catat(f"Aplikasi ditutup (kode {kode}).")
    return kode


if __name__ == "__main__":
    sys.exit(main())
