"""Pastikan seluruh nama menu sidebar tampil utuh di berbagai ukuran jendela.

Cara pakai:
    python tools/periksa_navbar.py

Nama menu yang lebih panjang dari lebar tombol akan terpotong sehingga
sebagian kalimatnya hilang. Pemeriksaan ini mengukur kebutuhan lebar teks
sebenarnya (ikon + jarak + padding) pada beberapa ukuran jendela.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
os.environ["AKUNTANSIID_DATA"] = str(AKAR / "_contoh")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(AKAR / "src"))

from PySide6.QtGui import QFontMetrics  # noqa: E402
from PySide6.QtWidgets import QApplication, QPushButton  # noqa: E402

from akuntansi_id.core import security as sec  # noqa: E402
from akuntansi_id.ui.main_window import MainWindow, Sidebar  # noqa: E402

# Lisensi uji dipakai agar seluruh halaman ikut diperiksa, termasuk
# halaman yang hanya tersedia pada paket Enterprise.
from akuntansi_id.core.license import Lisensi as _LisensiUji
_LISENSI_UJI = _LisensiUji(kunci='ATNTUJI', paket='enterprise', fitur={})


UKURAN = [(1600, 950), (1440, 900), (1280, 800), (1100, 720), (1024, 680)]

# Ruang tetap di dalam tombol menu: ikon 16 + jarak 9 + padding kiri 8
# + padding kanan 10, ditambah sedikit kelonggaran.
RUANG_TETAP = 16 + 9 + 8 + 10 + 4


def main() -> int:
    app = QApplication.instance() or QApplication([])

    # Siapkan keadaan seperti pemakaian sehari-hari: sebagian kelompok sudah
    # dibuka pengguna dan pilihannya tersimpan. Tanpa persiapan ini, semua
    # kelompok tertutup sehingga pemeriksaan isi kelompok tidak menguji apa
    # pun. Kelompok yang dibuka sengaja lebih dari satu karena masalahnya
    # hanya muncul pada kelompok yang isinya banyak.
    try:
        from akuntansi_id import db
        db.ex("INSERT INTO settings(key,value) VALUES('sidebar_lipat',?) "
              "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
              ("DATA USAHA,PERPAJAKAN,AKUNTANSI LANJUTAN,TATA KELOLA,PENGATURAN",))
    except Exception as e:
        print(f"Tidak dapat menyiapkan pilihan kelompok: {e}")
        print("Jalankan tools/buat_data_contoh.py dulu.")
        return 1

    try:
        hasil = sec.login("admin", "admin123")
    except Exception as e:
        print(f"Tidak dapat masuk: {e}")
        print("Jalankan tools/buat_data_contoh.py dulu.")
        return 1

    jendela = MainWindow(hasil, lisensi=_LISENSI_UJI)
    jendela.show()

    semua_masalah = []
    for lebar, tinggi in UKURAN:
        jendela.resize(lebar, tinggi)
        # beri waktu tata letak selesai sebelum mengukur: lebar tombol baru
        # benar setelah Qt menyelesaikan perhitungan ukuran
        for _ in range(6):
            app.processEvents()

        tombol = [b for b in jendela.sidebar.findChildren(QPushButton)
                  if b.objectName() == "NavButton"]
        for b in tombol:
            tampil = b.text().replace("&&", "&")
            if "_" in tampil:
                semua_masalah.append(
                    (lebar, tampil, "memakai garis bawah sebagai spasi"))
                continue
            butuh = QFontMetrics(b.font()).horizontalAdvance(tampil) + RUANG_TETAP
            if b.width() < butuh:
                semua_masalah.append(
                    (lebar, tampil, f"butuh {butuh}px, tersedia {b.width()}px"))

    if semua_masalah:
        print(f"HASIL: {len(semua_masalah)} nama menu bermasalah")
        for lebar, nama, alasan in semua_masalah[:15]:
            print(f"   [{lebar}px] {nama!r} — {alasan}")
        return 1

    tombol = [b for b in jendela.findChildren(QPushButton)
              if b.objectName() == "NavButton"]
    sidebar = jendela.findChild(Sidebar)
    grup = getattr(sidebar, "_grup", {})

    masalah_isi = periksa_isi_terbuka(jendela)
    if masalah_isi:
        print(f"HASIL: {len(masalah_isi)} kelompok bermasalah saat aplikasi dibuka")
        for nama, kode, alasan in masalah_isi[:10]:
            print(f"   [{nama}] {alasan}")
        return 1

    masalah_grup = periksa_kelompok(jendela)
    if masalah_grup:
        print(f"HASIL: {len(masalah_grup)} masalah pada kelompok menu")
        for nama, kode, alasan in masalah_grup[:10]:
            print(f"   [{nama}] {kode} — {alasan}")
        return 1

    print(f"HASIL: seluruh {len(tombol)} nama menu sidebar tampil utuh "
          f"pada {len(UKURAN)} ukuran jendela")
    if grup:
        print(f"        {len(grup)} kelompok menu dapat dibuka dan ditutup")
    return 0


def periksa_isi_terbuka(jendela) -> list:
    """
    Periksa kelompok yang bertanda terbuka benar-benar menampilkan isinya.

    Keadaan yang diperiksa adalah keadaan setelah aplikasi dibuka: kelompok
    yang sebelumnya dibuka pengguna harus tetap menampilkan menunya. Dahulu
    isi kelompok disembunyikan saat pemuatan bentuk badan usaha, sehingga
    panahnya menunjuk ke bawah tetapi tidak ada menu di bawahnya.

    Bentuk badan usaha TIDAK diterapkan lagi di sini. Penerapan ulang setelah
    jendela tampil justru menutupi masalahnya, karena saat itu seluruh widget
    sudah terbaca terlihat. Yang diperiksa adalah hasil pemuatan yang
    sesungguhnya, yaitu yang dilakukan saat jendela belum tampil.

    Diperiksa dengan isHidden(), bukan isVisible(), karena isVisible() ikut
    keadaan jendela induk.
    """
    masalah = []
    sidebar = jendela.findChild(Sidebar)
    if sidebar is None or not sidebar._grup:
        return masalah

    for nama, (judul, wadah) in sidebar._grup.items():
        if judul.isHidden():
            continue
        # Keadaan wadah yang menentukan, bukan keadaan tiap tombol di
        # dalamnya. Setelah jendela ditampilkan, tombol anak yang induknya
        # tersembunyi tetap terbaca tidak disembunyikan karena tombol itu
        # sendiri tidak pernah disembunyikan langsung.
        if judul.isChecked() and wadah.isHidden():
            masalah.append(
                (nama, "", "bertanda terbuka tetapi isinya tidak tampil"))
        elif not judul.isChecked() and not wadah.isHidden():
            masalah.append(
                (nama, "", "bertanda tertutup tetapi isinya tampil"))
    return masalah


def periksa_kelompok(jendela) -> list:
    """
    Periksa sub-kategori: setiap menu harus berada di kelompok yang tepat,
    dan membuka kelompok harus menampilkan menunya.
    """
    masalah = []
    sidebar = jendela.findChild(Sidebar)
    if sidebar is None or not sidebar._grup:
        return masalah

    # Setiap menu wajib berada di tepat satu kelompok.
    semua_menu = set(sidebar.tombol)
    ada_di_grup = set()
    for nama, (judul, wadah) in sidebar._grup.items():
        for i in range(wadah.layout().count()):
            it = wadah.layout().itemAt(i)
            wdg = it.widget() if it else None
            if wdg is None:
                continue
            for kode, b in sidebar.tombol.items():
                if b is wdg:
                    ada_di_grup.add(kode)
                    if not b.text().strip():
                        masalah.append((nama, kode, "nama menu kosong"))

    # Menu di luar kelompok (judul bagian biasa) tetap harus ada.
    luar = semua_menu - ada_di_grup
    if not luar and not ada_di_grup:
        masalah.append(("", "", "tidak ada menu sama sekali"))

    # Membuka kelompok harus benar-benar menampilkan menunya.
    #
    # Pemeriksaan memakai klik sungguhan dan isHidden(), bukan isVisible().
    # isVisible() ikut keadaan jendela induk, sehingga saat pemeriksaan
    # dijalankan di luar jendela yang tampil hasilnya selalu "tidak terlihat"
    # dan kelompok yang sehat pun dilaporkan bermasalah.
    for nama, (judul, wadah) in sidebar._grup.items():
        if judul.isChecked():
            judul.click()          # pastikan mulai dari keadaan tertutup
            if hasattr(jendela, "app"):
                jendela.app.processEvents()
        judul.click()              # buka seperti yang dilakukan pengguna
        if hasattr(jendela, "app"):
            for _ in range(3):
                jendela.app.processEvents()
        isi_kelompok = [b for b in sidebar.tombol.values()
                        if wadah.isAncestorOf(b)]
        if wadah.isHidden() or not any(not b.isHidden() for b in isi_kelompok):
            masalah.append((nama, "", "isi tidak muncul saat dibuka"))
        judul.click()              # tutup kembali
        if hasattr(jendela, "app"):
            jendela.app.processEvents()
    return masalah


if __name__ == "__main__":
    sys.exit(main())
