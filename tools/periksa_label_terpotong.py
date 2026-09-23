"""
Periksa apakah ada label kecil (badge, chip, pil) yang teksnya terpotong.

Label dengan kebijakan ukuran Maximum akan menyusut mengikuti ruang yang
tersisa. Bila ruangnya sempit, label menyusut sampai di bawah lebar
teksnya dan tulisannya terpotong. Akibatnya badge "GRADE D - BERMASALAH"
hanya menampilkan beberapa huruf pertama.

Skrip ini membuka setiap halaman pada ukuran layar terkecil yang didukung,
lalu membandingkan lebar setiap label dengan lebar teks yang dibutuhkan.

Cara pakai:
    python tools/periksa_label_terpotong.py
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
from akuntansi_id.ui.main_window import MainWindow, Sidebar  # noqa: E402

LEBAR, TINGGI = 1366, 768

# Selisih yang masih wajar akibat pembulatan.
TOLERANSI = 3

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


def periksa(jendela) -> list[tuple[str, str, int, int]]:
    """Kembalikan daftar label terpotong: (teks, kelas, butuh, dapat)."""
    halaman = jendela.stack.currentWidget()
    if halaman is None:
        return []

    hasil = []
    for lbl in halaman.findChildren(QLabel):
        if not lbl.isVisible():
            continue

        teks = lbl.text()
        if not teks or not teks.strip():
            continue

        # Label dengan pembungkusan baris memang dapat lebih tinggi, dan
        # lebarnya boleh mengikuti wadah. Yang diperiksa adalah label yang
        # tidak membungkus baris, karena label seperti itu wajib cukup lebar.
        if lbl.wordWrap():
            continue

        if "<" in teks:
            # Label berisi HTML: ukur memakai ukuran saran
            butuh = lbl.sizeHint().width()
        else:
            butuh = lbl.fontMetrics().horizontalAdvance(teks)

        dapat = lbl.width()
        # Label yang dimatikan (setVisible(False)) memang tidak ditampilkan,
        # jadi tidak dihitung sebagai terpotong.
        if not lbl.isVisibleTo(halaman):
            continue

        if dapat + TOLERANSI < butuh:
            bersih = teks.replace("\n", " ")[:44]
            hasil.append((bersih, lbl.__class__.__name__, butuh, dapat))

    return hasil


def main() -> int:
    if not (AKAR / "_ssdata" / "akuntuntas.db").exists():
        print("  Data contoh belum ada:")
        print(f'    python tools/buat_data_contoh.py "{AKAR / "_ssdata"}"')
        return 2

    app = QApplication.instance() or QApplication([])
    app.setStyleSheet(theme.stylesheet())

    hasil_login = sec.LoginResult(
        ok=True, user_id=1, username="admin", full_name="Budi Santoso",
        role="owner", app_mode="expert", mode_dipilih=True)
    j = MainWindow(hasil_login, lisensi=_LIS)
    j.resize(LEBAR, TINGGI)
    j.show()
    tunggu(app, 1.5)

    kode_halaman = [kode for _, isi in Sidebar.MENU for kode, _, _ in isi]

    print("=" * 74)
    print(f"  PERIKSA LABEL TERPOTONG ({LEBAR}x{TINGGI})")
    print("=" * 74)
    print()
    print(f"  halaman diperiksa: {len(kode_halaman)}")
    print()

    bermasalah = {}
    for kode in kode_halaman:
        try:
            j._navigasi(kode)
        except Exception:
            continue
        tunggu(app)

        temuan = periksa(j)
        if temuan:
            bermasalah[kode] = temuan

    if not bermasalah:
        print("  TIDAK ADA label terpotong.")
    else:
        total = sum(len(v) for v in bermasalah.values())
        print(f"  {total} label terpotong pada {len(bermasalah)} halaman:")
        print()
        for kode, daftar in bermasalah.items():
            print(f"  [{kode}]")
            for teks, kelas, butuh, dapat in daftar:
                kurang = butuh - dapat
                print(f"      kurang {kurang:3d}px  '{teks}'"
                      f"  (butuh {butuh}, dapat {dapat})")
            print()

    j.close()
    app.processEvents()

    print("=" * 74)
    if bermasalah:
        print("  HASIL: ada label yang tulisannya terpotong")
        return 1
    print("  HASIL: seluruh label tampil utuh")
    return 0


if __name__ == "__main__":
    sys.exit(main())
