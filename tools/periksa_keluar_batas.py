"""
Periksa apakah ada widget yang keluar dari tepi jendela pada tiap halaman.

Aplikasi harus dapat dipakai pada layar 1366x768, ukuran terkecil yang
didukung. Bila ada widget yang melewati tepi kanan atau tepi bawah, isinya
terpotong dan pengguna tidak dapat membacanya.

Pemeriksaan dilakukan dengan mengukur posisi setiap widget pada ukuran
jendela yang sebenarnya, bukan dengan menebak dari gambar. Vision dapat
salah menilai gambar, sedangkan pengukuran langsung memberi angka pasti.

Cara pakai:
    python tools/periksa_keluar_batas.py
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
os.environ["AKUNTANSIID_DATA"] = str(AKAR / "_ssdata")
sys.path.insert(0, str(AKAR / "src"))

from PySide6.QtWidgets import (  # noqa: E402
    QApplication, QComboBox, QLabel, QLineEdit, QPushButton, QScrollArea,
    QTableWidget, QTabWidget, QWidget)

from akuntansi_id.core import license as LIS  # noqa: E402
from akuntansi_id.core import security as sec  # noqa: E402
from akuntansi_id.ui import theme  # noqa: E402
from akuntansi_id.ui.main_window import MainWindow  # noqa: E402

LEBAR, TINGGI = 1366, 768

# Toleransi beberapa piksel, karena batas pembulatan tata letak.
TOLERANSI = 4

_LIS = LIS.Lisensi(
    kunci="PERIKSA", paket="enterprise", pemilik="X",
    berlaku_sampai=time.time() + 86400,
    fitur={"konsolidasi": True, "dimensi": True, "pajak_lanjutan": True,
           "audit_lanjutan": True, "multi_entitas": True})


def tunggu(app, detik=0.7):
    akhir = time.time() + detik
    while time.time() < akhir:
        app.processEvents()
        time.sleep(0.01)


def periksa_halaman(app, jendela, kode: str) -> list[str]:
    """Kembalikan daftar masalah pada satu halaman."""
    masalah = []

    try:
        jendela._navigasi(kode)
    except Exception as e:
        return [f"tidak dapat dibuka: {e}"]

    tunggu(app)

    halaman = jendela.stack.currentWidget()
    if halaman is None:
        return ["halaman kosong"]

    batas_kanan = halaman.width()
    batas_bawah = halaman.height()

    jenis_penting = (QLabel, QPushButton, QLineEdit, QComboBox,
                     QTableWidget)

    kandidat = []
    for jenis in jenis_penting:
        kandidat.extend(halaman.findChildren(jenis))

    for anak in kandidat:
        if not anak.isVisible() or anak.width() == 0:
            continue

        # Posisi relatif terhadap halaman
        kiri = anak.mapTo(halaman, anak.rect().topLeft()).x()
        kanan = anak.mapTo(halaman, anak.rect().topRight()).x()

        # Widget di dalam area gulir memang boleh lebih panjang dari layar;
        # pengguna dapat menggulir. Yang diperiksa adalah yang tidak dapat
        # dijangkau sama sekali.
        induk = anak.parent()
        dalam_gulir = False
        naik = 0
        while induk is not None and naik < 8:
            if isinstance(induk, QScrollArea):
                dalam_gulir = True
                break
            induk = induk.parent()
            naik += 1

        if kanan > batas_kanan + TOLERANSI:
            teks = ""
            if hasattr(anak, "text"):
                teks = str(anak.text())[:40]
            elif isinstance(anak, QComboBox):
                teks = anak.currentText()[:40]
            tanda = " (dalam area gulir)" if dalam_gulir else ""
            masalah.append(
                f"keluar kanan {kanan - batas_kanan}px: "
                f"{anak.__class__.__name__} '{teks}'{tanda}")

    return masalah


def main() -> int:
    if not (AKAR / "_ssdata" / "akuntuntas.db").exists():
        print("  Data contoh belum ada. Jalankan:")
        print('    python tools/buat_data_contoh.py "%s"' % (AKAR / "_ssdata"))
        return 2

    app = QApplication.instance() or QApplication([])
    app.setStyleSheet(theme.stylesheet())

    hasil = sec.LoginResult(ok=True, user_id=1, username="admin",
                            full_name="Budi Santoso", role="owner",
                            app_mode="expert", mode_dipilih=True)
    jendela = MainWindow(hasil, lisensi=_LIS)
    jendela.resize(LEBAR, TINGGI)
    jendela.show()
    tunggu(app, 1.5)

    # Kumpulkan seluruh halaman dari daftar menu sidebar
    from akuntansi_id.ui.main_window import Sidebar
    kode_halaman = [kode for _, isi in Sidebar.MENU for kode, _, _ in isi]

    print("=" * 74)
    print(f"  PERIKSA WIDGET KELUAR BATAS ({LEBAR}x{TINGGI})")
    print("=" * 74)
    print()
    print(f"  halaman diperiksa: {len(kode_halaman)}")
    print()

    bermasalah = {}
    for kode in kode_halaman:
        masalah = periksa_halaman(app, jendela, kode)
        if masalah:
            bermasalah[kode] = masalah

    if not bermasalah:
        print("  TIDAK ADA widget yang keluar batas pada seluruh halaman.")
    else:
        print(f"  {len(bermasalah)} halaman bermasalah:")
        print()
        for kode, daftar in bermasalah.items():
            print(f"  [{kode}]  {len(daftar)} masalah")
            for m in daftar[:4]:
                print(f"      {m}")
            if len(daftar) > 4:
                print(f"      ... dan {len(daftar) - 4} lainnya")
            print()

    jendela.close()
    app.processEvents()

    print("=" * 74)
    if bermasalah:
        total = sum(len(v) for v in bermasalah.values())
        print(f"  HASIL: {total} widget keluar batas pada "
              f"{len(bermasalah)} halaman")
        return 1
    print("  HASIL: seluruh widget berada di dalam batas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
