"""
Bukti bergambar: halaman Data Perusahaan pada keadaan tanpa data.

Alat ini membangun halaman Data Perusahaan dengan basis data kosong persis
seperti yang dialami pengguna saat aplikasi baru dipasang, lalu menyimpan
gambarnya supaya dapat diperiksa dengan mata.

Cara pakai:
    python tools/bukti_halaman_perusahaan.py
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "src"))

os.environ["QT_QPA_PLATFORM"] = "offscreen"

FOLDER = Path(tempfile.mkdtemp(prefix="akuntuntas_bukti_"))
os.environ["LOCALAPPDATA"] = str(FOLDER)

from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication.instance() or QApplication([])

from akuntansi_id import db  # noqa: E402


def main() -> int:
    print("=" * 76)
    print("  BUKTI HALAMAN DATA PERUSAHAAN TANPA DATA")
    print("=" * 76)
    print()

    db.init_db()
    jumlah = db.scalar("SELECT COUNT(*) FROM companies")
    print(f"  perusahaan di basis data: {jumlah}")
    print()

    from akuntansi_id.ui.pages.coa_page import PerusahaanPage

    class Konteks:
        company_id = None
        company = None
        tahun = 2026
        lisensi = None

        def muat_perusahaan(self):
            pass

    halaman = PerusahaanPage(Konteks())
    halaman.resize(1280, 820)
    halaman.muat()
    halaman.show()
    app.processEvents()

    # Periksa isi yang benar-benar tergambar.
    from PySide6.QtWidgets import QLabel, QLineEdit, QPushButton

    terlihat = []
    for anak in halaman.findChildren(QLabel):
        if anak.isVisible() and anak.text().strip():
            terlihat.append(("label", anak.text().strip()[:60]))
    for anak in halaman.findChildren(QLineEdit):
        if anak.isVisible():
            terlihat.append(("isian", anak.placeholderText() or "(tanpa petunjuk)"))
    for anak in halaman.findChildren(QPushButton):
        if anak.isVisible() and anak.text().strip():
            terlihat.append(("tombol", anak.text().strip()[:40]))

    print(f"  elemen terlihat: {len(terlihat)}")
    for jenis, teks in terlihat[:16]:
        print(f"    [{jenis}] {teks}")

    # Simpan gambar untuk diperiksa.
    gambar = AKAR / "_halaman_perusahaan.png"
    halaman.grab().save(str(gambar))
    print()
    print(f"  gambar disimpan: {gambar}")

    # Cari tombol Buat Perusahaan.
    tombol_buat = [
        b for b in halaman.findChildren(QPushButton)
        if "Buat Perusahaan" in b.text() and b.isVisible()
    ]
    print()
    if tombol_buat:
        print("  HASIL: halaman TERISI dan tombol Buat Perusahaan TERSEDIA")
        hasil = 0
    else:
        print("  HASIL: halaman KOSONG atau tombol tidak ada")
        hasil = 1

    return hasil


if __name__ == "__main__":
    kode = main()
    sys.stdout.flush()
    os._exit(kode)
