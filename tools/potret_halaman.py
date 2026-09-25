"""
Potret setiap halaman aplikasi untuk pemeriksaan desain.

Satu jendela dipakai untuk seluruh halaman, bukan satu jendela per
halaman. Membuka dan menutup jendela berkali-kali dalam satu proses
membuat Qt tidak stabil dan prosesnya berhenti tanpa pesan.

Jendela sungguhan dipakai, bukan render di luar layar, karena render di
luar layar tidak memakai font sistem sehingga teksnya tampil sebagai kotak
dan gambarnya tidak dapat dipakai untuk menilai tampilan.

Cara pakai:
    python tools/potret_halaman.py [folder]
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "src"))

# Folder data sementara supaya data asli tidak tersentuh.
FOLDER = Path(tempfile.mkdtemp(prefix="akuntuntas_potret_"))
os.environ["LOCALAPPDATA"] = str(FOLDER)

from PySide6.QtCore import QEventLoop, QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication.instance() or QApplication([])

from akuntansi_id import db  # noqa: E402
from akuntansi_id.core import security as sec  # noqa: E402
from akuntansi_id.ui import theme  # noqa: E402

# Mode terang wajib dipaksa lebih dulu. Tanpa ini, Qt mengikuti mode gelap
# Windows dan seluruh area yang tidak diatur stylesheet tampil gelap,
# sehingga gambarnya tidak menggambarkan tampilan aplikasi sebenarnya.
theme.palet_terang(app)
app.setStyleSheet(theme.stylesheet())

# Halaman yang dipotret, memakai nama yang benar sesuai daftar halaman
# di main_window. Nama yang salah membuat halaman tidak berpindah dan
# gambarnya menjadi sama dengan halaman sebelumnya.
HALAMAN = [
    "dashboard", "jurnal", "penjualan", "pembelian", "biaya", "bank",
    "mitra", "produk", "aset", "payroll", "coa", "laporan", "pajak",
    "pajak_lanjutan", "dimensi", "periode", "konsolidasi", "analisis",
    "pencarian", "checklist", "pengguna", "audit", "recycle", "impor",
    "kontrak", "perusahaan", "lan", "pengaturan", "bantuan",
]


def tunggu(ms: int):
    """Jalankan putaran peristiwa sungguhan selama beberapa milidetik."""
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def siapkan_data():
    """Siapkan perusahaan beserta bagan akunnya."""
    db.init_db()
    sec.ensure_default_admin()

    from akuntansi_id import services

    lisensi = type("L", (), {
        "paket": "enterprise", "enterprise": True,
        "punya": lambda self, x: True,
    })()
    return services.create_company(
        "PT Maju Bersama Sejahtera", "pt",
        npwp="01.234.567.8-901.000",
        nama_pemilik="Ariel Budi",
        alamat="Jalan Sudirman 45",
        kota="Jakarta",
        lisensi=lisensi,
    )


def main() -> int:
    tujuan_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else AKAR / "_potret"
    tujuan_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 76)
    print("  POTRET HALAMAN APLIKASI")
    print("=" * 76)
    print()

    print("[Persiapan data]")
    cid = siapkan_data()
    print(f"  perusahaan dibuat: id={cid}")
    print()

    from akuntansi_id.ui.main_window import MainWindow

    lisensi = type("L", (), {
        "paket": "enterprise", "enterprise": True, "pemilik": "Uji",
        "kunci": "ATNT-UJI", "fitur": {},
        "punya": lambda self, x: True,
    })()

    masuk = sec.LoginResult(
        ok=True, user_id=1, username="admin", full_name="Administrator",
        role="owner", app_mode="beginner", mode_dipilih=True,
    )

    # Satu jendela untuk seluruh halaman.
    jendela = MainWindow(masuk, lisensi=lisensi)
    jendela.resize(1440, 900)
    jendela.show()
    tunggu(1500)

    berhasil = []
    for nama in HALAMAN:
        try:
            jendela._navigasi(nama)
        except Exception as e:
            print(f"  [LEWAT] {nama}: {type(e).__name__}: {e}")
            continue

        tunggu(900)
        jendela.repaint()
        tunggu(250)

        berkas = tujuan_dir / f"{nama}.png"
        if jendela.grab().save(str(berkas)):
            berhasil.append(nama)
            print(f"  [OK]    {nama}")
        else:
            print(f"  [GAGAL] {nama}")

    jendela.close()

    print()
    print(f"  berhasil dipotret: {len(berhasil)} dari {len(HALAMAN)}")
    print(f"  folder gambar: {tujuan_dir}")
    return 0


if __name__ == "__main__":
    kode = main()
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(kode)
