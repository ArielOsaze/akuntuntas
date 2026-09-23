"""Audit menyeluruh: pastikan tidak ada teks tampil yang memakai garis bawah.

Cara pakai:
    python tools/audit_garis_bawah.py

Alat ini memeriksa SETIAP elemen teks yang terlihat di SETIAP halaman:
label, tombol, kotak centang, tombol pilih, judul kelompok, tab, dan
menu bar. Teks yang mengandung "_" dicurigai sebagai nilai teknis atau
akibat tanda "&" yang dibaca Qt sebagai penanda pintasan.

Berbeda dari periksa_garis_bawah.py yang memeriksa halaman utama saja,
alat ini menelusuri seluruh halaman dan menu bar sekaligus.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
os.environ["AKUNTANSIID_DATA"] = str(AKAR / "_contoh")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(AKAR / "src"))

from PySide6.QtWidgets import (  # noqa: E402
    QApplication, QLabel, QPushButton, QCheckBox, QRadioButton, QTabBar,
    QGroupBox, QComboBox,
)

from akuntansi_id import config, services  # noqa: E402
from akuntansi_id.core import security as sec  # noqa: E402
from akuntansi_id.ui import theme  # noqa: E402
from akuntansi_id.ui.main_window import MainWindow, Sidebar  # noqa: E402

# Lisensi uji dipakai agar seluruh halaman ikut diperiksa, termasuk
# halaman yang hanya tersedia pada paket Enterprise.
from akuntansi_id.core.license import Lisensi as _LisensiUji
_LISENSI_UJI = _LisensiUji(kunci='ATNTUJI', paket='enterprise', fitur={})


# Nilai yang memang boleh mengandung garis bawah karena bukan kalimat,
# melainkan nama berkas, kode akun, atau nilai yang dijelaskan di layar.
DIKECUALIKAN = (
    ".py", ".txt", ".md", ".db", ".log", ".exe", ".csv", ".json",
    "akuntuntas.log", "reset_admin.txt", "akuntuntas.db",
)


def teks_terlihat(akar) -> list:
    """Kumpulkan semua teks yang tampil dari widget di dalam `akar`."""
    hasil = []
    for kelas in (QLabel, QPushButton, QCheckBox, QRadioButton, QGroupBox):
        for w in akar.findChildren(kelas):
            if not w.isVisible():
                continue
            t = w.text()
            if t and t.strip():
                hasil.append((kelas.__name__, t, w))
    for w in akar.findChildren(QTabBar):
        if not w.isVisible():
            continue
        for i in range(w.count()):
            hasil.append(("QTabBar", w.tabText(i), w))
    for w in akar.findChildren(QComboBox):
        if not w.isVisible():
            continue
        for i in range(w.count()):
            hasil.append(("QComboBox", w.itemText(i), w))
    return hasil


def bermasalah(teks: str) -> bool:
    """Teks dianggap bermasalah bila ada "_" yang bukan bagian nama berkas."""
    if "_" not in teks:
        return False
    rendah = teks.lower()
    if any(k in rendah for k in DIKECUALIKAN):
        return False
    return True


def main() -> int:
    app = QApplication.instance() or QApplication([])
    app.setStyleSheet(theme.stylesheet())

    perusahaan = services.list_companies()
    if not perusahaan:
        print("Tidak ada perusahaan. Jalankan tools/buat_data_contoh.py dulu.")
        return 1
    cid = perusahaan[0]["id"]

    hasil_login = sec.login("admin", config.DEFAULT_ADMIN_PASSWORD)
    if not hasil_login.ok:
        print("Login gagal.")
        return 1

    jendela = MainWindow(hasil_login, lisensi=_LISENSI_UJI)
    jendela.ctx.company_id = cid
    jendela.ctx.company = services.get_company(cid)
    jendela.resize(1440, 940)
    jendela.show()
    for _ in range(10):
        app.processEvents()

    temuan = []
    jumlah_diperiksa = 0

    # seluruh halaman
    for kode in jendela.halaman:
        jendela._navigasi(kode)
        for _ in range(6):
            app.processEvents()
        halaman = jendela.halaman.get(kode)
        if halaman is None:
            continue
        for kelas, teks, _ in teks_terlihat(halaman):
            jumlah_diperiksa += 1
            if bermasalah(teks):
                temuan.append((kode, kelas, teks))

    # judul kelompok sidebar
    sidebar = jendela.findChild(Sidebar)
    if sidebar is not None:
        for nama, (judul, _) in sidebar._grup.items():
            jumlah_diperiksa += 1
            # judul memakai "&&" agar Qt menampilkan satu "&"; itu benar
            tampil = judul.text().replace("&&", "&")
            if bermasalah(tampil):
                temuan.append(("sidebar", "judul kelompok", tampil))

    # menu bar dan seluruh isinya
    for aksi in jendela.menuBar().actions():
        jumlah_diperiksa += 1
        if bermasalah(aksi.text().replace("&&", "&")):
            temuan.append(("menubar", "menu", aksi.text()))
        menu = aksi.menu()
        if menu is None:
            continue
        for sub in menu.actions():
            jumlah_diperiksa += 1
            if bermasalah(sub.text().replace("&&", "&")):
                temuan.append(("menubar", "submenu", sub.text()))

    print(f"elemen teks diperiksa: {jumlah_diperiksa}")
    if temuan:
        print(f"HASIL: {len(temuan)} teks memakai garis bawah")
        for kode, kelas, teks in temuan[:20]:
            print(f"   [{kode}] {kelas}: {teks[:60]!r}")
        return 1

    print("HASIL: tidak ada teks tampil yang memakai garis bawah")
    return 0


if __name__ == "__main__":
    sys.exit(main())
