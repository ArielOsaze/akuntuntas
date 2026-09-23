"""
Ukur tata letak dashboard pada ukuran jendela yang dipakai Store.

Vision dapat keliru menilai gambar. Skrip ini mengukur langsung lebar dan
posisi setiap widget, sehingga masalah terpotong dapat dipastikan dengan
angka, bukan dugaan.

Cara pakai:
    python tools/ukur_dashboard.py
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
os.environ["AKUNTANSIID_DATA"] = str(AKAR / "_ssdata")
sys.path.insert(0, str(AKAR / "src"))

from PySide6.QtWidgets import QApplication, QLabel  # noqa: E402

from akuntansi_id.core import license as LIS  # noqa: E402
from akuntansi_id.core import security as sec  # noqa: E402
from akuntansi_id.ui import theme  # noqa: E402
from akuntansi_id.ui.main_window import MainWindow  # noqa: E402

LEBAR, TINGGI = 1366, 768

_LISENSI = LIS.Lisensi(
    kunci="UKUR", paket="enterprise", pemilik="X",
    berlaku_sampai=time.time() + 86400,
    fitur={"konsolidasi": True, "dimensi": True, "pajak_lanjutan": True,
           "audit_lanjutan": True, "multi_entitas": True})


def tunggu(app, detik=0.8):
    akhir = time.time() + detik
    while time.time() < akhir:
        app.processEvents()
        time.sleep(0.01)


def main() -> int:
    app = QApplication.instance() or QApplication([])
    app.setStyleSheet(theme.stylesheet())

    hasil = sec.LoginResult(ok=True, user_id=1, username="admin",
                            full_name="Budi Santoso", role="owner",
                            app_mode="expert", mode_dipilih=True)
    jendela = MainWindow(hasil, lisensi=_LISENSI)
    jendela.resize(LEBAR, TINGGI)
    jendela.show()
    tunggu(app, 1.5)
    jendela._navigasi("dashboard")
    tunggu(app, 1.5)

    halaman = jendela.stack.currentWidget()

    print("=" * 72)
    print(f"  UKUR TATA LETAK DASHBOARD ({LEBAR}x{TINGGI})")
    print("=" * 72)
    print()

    # ------------------------------------------------ label legenda grafik
    print("1. LABEL LEGENDA GRAFIK")
    teks_legenda = ["Pendapatan", "HPP + Beban", "Laba sebelum pajak"]
    ditemukan = 0
    for lbl in halaman.findChildren(QLabel):
        teks = lbl.text().strip()
        if teks in teks_legenda:
            ditemukan += 1
            butuh = lbl.fontMetrics().horizontalAdvance(teks)
            dapat = lbl.width()
            cukup = dapat >= butuh
            tanda = "CUKUP" if cukup else "TERPOTONG"
            print(f"  [{tanda}] '{teks}'")
            print(f"           butuh {butuh}px, dapat {dapat}px")
    if ditemukan == 0:
        print("  label legenda tidak ditemukan")

    # ----------------------------------------------------- widget keluar tepi
    print()
    print("2. WIDGET YANG KELUAR BATAS JENDELA")
    lebar_jendela = jendela.width()
    keluar = []
    for lbl in halaman.findChildren(QLabel):
        if not lbl.isVisible() or not lbl.text().strip():
            continue
        kanan = lbl.mapTo(jendela, lbl.rect().topRight()).x()
        if kanan > lebar_jendela:
            keluar.append((lbl.text().strip()[:50], kanan))
    if keluar:
        for teks, kanan in keluar[:10]:
            print(f"  KELUAR ({kanan}px > {lebar_jendela}px): {teks}")
    else:
        print("  tidak ada widget keluar batas")

    # ------------------------------------------------ data grafik 12 bulan
    print()
    print("3. DATA GRAFIK KINERJA BULANAN")
    from akuntansi_id import modules as M
    from akuntansi_id import config as C

    cid = M.daftar_perusahaan()[0]["id"] if hasattr(M, "daftar_perusahaan") else 1
    try:
        from akuntansi_id import services as SV
        data = SV.ringkasan_bulanan(cid, C.DEFAULT_TAX_YEAR)
        print(f"  jumlah bulan pada data: {len(data)}")
        for b in data:
            nama = b.get("bulan") or b.get("label") or "?"
            print(f"    {nama}: pendapatan {b.get('pendapatan', 0):>15,}")
    except Exception as e:
        print(f"  gagal membaca data: {e}")

    jendela.close()
    app.processEvents()
    return 0


if __name__ == "__main__":
    sys.exit(main())
