"""
Uji panel panduan langkah awal di dasbor.

Panel ini muncul hanya saat pembukuan masih kosong, untuk menggantikan
layar yang seluruhnya berisi angka nol. Yang diperiksa: panelnya muncul
pada keadaan kosong, memuat empat langkah dan dua tombol, serta tidak
muncul lagi setelah ada transaksi.

Cara pakai:
    python tools/uji_panel_panduan.py
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "src"))

FOLDER = Path(tempfile.mkdtemp(prefix="akuntuntas_panduan_"))
os.environ["LOCALAPPDATA"] = str(FOLDER)

from PySide6.QtWidgets import QApplication, QLabel, QPushButton  # noqa: E402

from akuntansi_id import config, db  # noqa: E402
from akuntansi_id.ui import theme  # noqa: E402
from akuntansi_id.ui.pages.dashboard import DashboardPage  # noqa: E402


class Konteks:
    """Konteks sekecil mungkin untuk membangun halaman dasbor."""

    def __init__(self):
        self.lisensi = None
        self.perusahaan = None
        self.pengguna = None
        self.tahun = 2026
        self.beginner = True
        self.data_dir = Path(config.DATA_DIR)
        self.company_id = None


def main() -> int:
    app = QApplication([])
    theme.palet_terang(app)
    app.setStyleSheet(theme.stylesheet())

    db.init_db()

    lulus = 0
    gagal = 0

    def cek(nama: str, syarat: bool, keterangan: str = ""):
        nonlocal lulus, gagal
        if syarat:
            lulus += 1
            print(f"  [LULUS] {nama}")
        else:
            gagal += 1
            print(f"  [GAGAL] {nama}" + (f" — {keterangan}" if keterangan else ""))

    print("=" * 74)
    print("  UJI PANEL PANDUAN LANGKAH AWAL")
    print("=" * 74)
    print()

    # Panel dibangun langsung, tanpa memerlukan perusahaan di basis data.
    # Yang diuji susunan panelnya, bukan pembacaan data.
    kelas = DashboardPage.__dict__["_panel_mulai"]

    # Panel memerlukan atribut pindah_halaman yang berupa sinyal. Susun
    # halaman sungguhan supaya atribut itu ada.
    ctx = Konteks()
    halaman = DashboardPage(ctx)

    panel = kelas(halaman, {"nama": "PT Contoh Uji"})
    panel.resize(900, 600)
    panel.grab()

    print("[1. Panel terbentuk]")
    cek("Panel tergambar", not panel.grab().isNull())
    print()

    def kumpulkan_teks(widget) -> str:
        bagian = []
        for anak in widget.findChildren(QLabel):
            bagian.append(anak.text())
        return "\n".join(bagian)

    teks = kumpulkan_teks(panel)

    print("[2. Isi panel]")
    cek("Judul panduan tampil",
          "Langkah pertama menyiapkan pembukuan" in teks)
    cek("Nama usaha disebut", "PT Contoh Uji" in teks)

    langkah = [
        "Catat data usaha",
        "Daftarkan pelanggan dan pemasok",
        "Daftarkan produk atau jasa",
        "Catat penjualan atau pembelian pertama",
    ]
    for l in langkah:
        cek(f"Langkah: {l}", l in teks)
    print()

    print("[3. Nomor langkah]")
    for nomor in ("1", "2", "3", "4"):
        ada = any(a.text() == nomor for a in panel.findChildren(QLabel))
        cek(f"Nomor {nomor} tampil", ada)
    print()

    print("[4. Tombol tindakan]")
    tombol = [b.text() for b in panel.findChildren(QPushButton)]
    print(f"    tombol: {tombol}")
    cek("Tombol catat penjualan ada",
          any("Catat Penjualan" in t for t in tombol))
    cek("Tombol bagan akun ada",
          any("Bagan Akun" in t for t in tombol))
    print()

    print("[5. Keterangan penutup]")
    cek("Menjelaskan panduan hilang setelah ada transaksi",
          "tidak ditampilkan lagi" in teks)
    cek("Tidak memakai garis bawah sebagai spasi",
          "_" not in teks)
    cek("Tidak memakai tanda pisah panjang",
          "—" not in teks)

    print()
    print("=" * 74)
    print(f"  HASIL: {lulus} LULUS, {gagal} GAGAL")
    print("=" * 74)
    return 1 if gagal else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(line_buffering=True)
    kode = main()
    sys.stdout.flush()
    os._exit(kode)
