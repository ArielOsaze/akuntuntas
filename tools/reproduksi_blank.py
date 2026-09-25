"""
Reproduksi bug: halaman Data Perusahaan kosong putih saat belum ada data.

Keadaan yang ditiru: aplikasi baru dipasang, belum ada perusahaan sama
sekali, lalu pengguna menekan tombol Buat Profil Perusahaan di dashboard.
Halaman yang muncul dilaporkan kosong putih tanpa isi apa pun.

Alat ini membangun halaman itu dengan basis data kosong, lalu memeriksa
berapa banyak isi yang benar-benar tergambar. Bila halaman kosong, jumlah
widget yang terlihat akan nol.

Cara pakai:
    python tools/reproduksi_blank.py
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "src"))

os.environ["QT_QPA_PLATFORM"] = "offscreen"

# Basis data kosong dipakai lebih dulu sebelum modul aplikasi dimuat.
# Lokasi data ditentukan oleh LOCALAPPDATA, jadi variabel itu yang diarahkan
# ke folder sementara supaya data asli tidak tersentuh.
FOLDER = Path(tempfile.mkdtemp(prefix="akuntuntas_kosong_"))
os.environ["LOCALAPPDATA"] = str(FOLDER)

from PySide6.QtWidgets import QApplication, QLabel, QLineEdit, QPushButton  # noqa: E402

app = QApplication.instance() or QApplication([])

from akuntansi_id import config  # noqa: E402
from akuntansi_id import db  # noqa: E402


def siapkan_kosong():
    """Siapkan basis data kosong tanpa perusahaan."""
    db.init_db()
    print(f"  basis data: {config.DB_PATH}")
    print(f"  perusahaan: {db.scalar('SELECT COUNT(*) FROM companies')}")


def hitung_isi(widget, jeluk=0):
    """Hitung widget yang benar-benar terlihat."""
    from PySide6.QtWidgets import QWidget

    jumlah = 0
    rincian = []
    for anak in widget.findChildren(QWidget):
        if anak.isVisible() and anak.width() > 0 and anak.height() > 0:
            jumlah += 1
            if isinstance(anak, (QLabel, QLineEdit, QPushButton)):
                teks = ""
                if isinstance(anak, QLabel):
                    teks = anak.text()[:40]
                elif isinstance(anak, QLineEdit):
                    teks = anak.placeholderText()[:40]
                else:
                    teks = anak.text()[:40]
                if teks:
                    rincian.append(f"{type(anak).__name__}: {teks}")
    return jumlah, rincian


def main() -> int:
    print("=" * 76)
    print("  REPRODUKSI HALAMAN DATA PERUSAHAAN KOSONG")
    print("=" * 76)
    print()

    siapkan_kosong()

    from akuntansi_id.ui.pages.coa_page import PerusahaanPage

    class Konteks:
        company_id = None
        company = None
        tahun = 2026
        lisensi = None

        def muat_perusahaan(self):
            pass

    print()
    print("[1. Membangun halaman tanpa perusahaan]")
    try:
        halaman = PerusahaanPage(Konteks())
        halaman.resize(1200, 760)
        halaman.muat()
        halaman.show()
        app.processEvents()
    except Exception as e:
        print(f"  GAGAL MEMBANGUN: {type(e).__name__}: {e}")
        import traceback
        for b in traceback.format_exc().splitlines()[-6:]:
            print(f"    {b}")
        return 1

    jumlah, rincian = hitung_isi(halaman)
    print(f"  widget terlihat: {jumlah}")
    if rincian:
        print("  isi yang terbaca:")
        for r in rincian[:12]:
            print(f"    - {r}")
    print()

    if jumlah == 0:
        print("  HASIL: HALAMAN KOSONG (bug terulang)")
        return 1

    # Apakah formulirnya benar-benar dapat dipakai.
    from PySide6.QtWidgets import QLineEdit as LE

    ada_nama = any(
        isinstance(x, LE) and x.isVisible()
        for x in halaman.findChildren(LE))
    print(f"  kolom isian ada: {'ya' if ada_nama else 'TIDAK'}")
    print()
    print("  HASIL: halaman terisi" if ada_nama
          else "  HASIL: HALAMAN KOSONG (bug terulang)")
    return 0 if ada_nama else 1


if __name__ == "__main__":
    sys.exit(main())
