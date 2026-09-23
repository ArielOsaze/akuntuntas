"""
Ukur waktu pindah halaman seperti yang dialami pengguna.

Pengukuran sebelumnya mencampur tiga hal: mengganti halaman, memproses
peristiwa, dan menggambar. Berkas ini memisahkannya dengan jelas dan
mengulang tiap pengukuran supaya hasilnya stabil.

Angka yang penting bagi pengguna adalah waktu sampai halaman siap dilihat,
yaitu setelah peristiwa dan penggambaran selesai diproses.
"""

import os
import sys
import time
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "src"))
os.environ.setdefault("AKUNTANSIID_DATA", str(AKAR / "_contoh"))

from PySide6.QtWidgets import QApplication      # noqa: E402


def main() -> int:
    app = QApplication([])
    app.setStyle("Fusion")

    from akuntansi_id.ui import theme
    theme.palet_terang(app)
    app.setStyleSheet(theme.stylesheet())

    from akuntansi_id.core import security as sec
    from akuntansi_id.ui.main_window import MainWindow


    def _lisensi_uji():
        """Lisensi uji paket Enterprise agar seluruh halaman ikut diperiksa."""
        from akuntansi_id.core.license import Lisensi
        return Lisensi(kunci='ATNTUJI', paket='enterprise', fitur={})

    hasil = sec.login("admin", "admin123")
    jendela = MainWindow(hasil, lisensi=_lisensi_uji())
    jendela.resize(1400, 900)
    jendela.show()
    for _ in range(20):
        app.processEvents()

    # buka semua halaman sekali supaya semuanya sudah dimuat
    for kode in jendela.halaman:
        jendela._navigasi(kode)
        for _ in range(3):
            app.processEvents()

    print("=" * 76)
    print("WAKTU PINDAH HALAMAN SEPERTI DIALAMI PENGGUNA")
    print("=" * 76)
    print()
    print(f"  {'halaman':18s} {'rata-rata':>10s} {'terlama':>9s}")
    print(f"  {'-' * 18} {'-' * 10} {'-' * 9}")

    hasil_ukur = []
    for kode in jendela.halaman:
        waktu = []
        for _ in range(5):
            # mulai dari halaman lain supaya benar-benar berpindah
            jendela.stack.setCurrentWidget(jendela.halaman["dashboard"])
            app.processEvents()

            t0 = time.perf_counter()
            jendela._navigasi(kode)
            # tuntaskan penggambaran, seperti yang terjadi saat dipakai
            for _ in range(6):
                app.processEvents()
            waktu.append((time.perf_counter() - t0) * 1000)

        rata = sum(waktu) / len(waktu)
        hasil_ukur.append((kode, rata, max(waktu)))

    hasil_ukur.sort(key=lambda x: -x[1])
    for kode, rata, maks in hasil_ukur:
        tanda = "  <-- LAMBAT" if rata > 150 else ""
        print(f"  {kode:18s} {rata:9.1f}ms {maks:8.1f}ms{tanda}")

    print()
    semua = [r for _, r, _ in hasil_ukur]
    print(f"  Rata-rata seluruh halaman: {sum(semua) / len(semua):.1f} ms")
    print(f"  Terlambat                : {max(semua):.1f} ms")

    lambat = [k for k, r, _ in hasil_ukur if r > 150]
    print()
    print("=" * 76)
    if lambat:
        print(f"HASIL: {len(lambat)} halaman melewati 150 ms")
        for k in lambat[:10]:
            print(f"   {k}")
    else:
        print("HASIL: seluruh halaman di bawah 150 ms")
    print("=" * 76)
    return 1 if lambat else 0


if __name__ == "__main__":
    sys.exit(main())
