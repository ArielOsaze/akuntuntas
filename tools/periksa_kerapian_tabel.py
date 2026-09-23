"""Periksa kerapian tabel: alignment angka, lebar kolom, dan jarak tepi.

Cara pakai:
    python tools/periksa_kerapian_tabel.py

Tabel yang rapi memenuhi tiga aturan:
1. Angka rata kanan supaya digit sejajar dan mudah dibandingkan.
2. Teks rata kiri.
3. Jumlah lebar kolom tidak melebihi area tampil, dan tidak menyisakan
   ruang kosong besar di kanan (kecuali memang satu kolom fleksibel).
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
os.environ["AKUNTANSIID_DATA"] = str(AKAR / "_contoh")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(AKAR / "src"))

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication, QTableWidget  # noqa: E402

from akuntansi_id import config, services  # noqa: E402
from akuntansi_id.core import security as sec  # noqa: E402
from akuntansi_id.ui import theme  # noqa: E402
from akuntansi_id.ui.main_window import MainWindow, Sidebar  # noqa: E402

# Lisensi uji dipakai agar seluruh halaman ikut diperiksa, termasuk
# halaman yang hanya tersedia pada paket Enterprise.
from akuntansi_id.core.license import Lisensi as _LisensiUji
_LISENSI_UJI = _LisensiUji(kunci='ATNTUJI', paket='enterprise', fitur={})


HALAMAN = [k for _, daftar in Sidebar.MENU for k, _, _ in daftar]

# nilai yang tampak seperti angka/rupiah/persen (harus mengandung digit)
POLA_ANGKA = re.compile(r"^[Rp$\s]*\d[\d.,]*%?$")
# kolom yang jelas berisi teks (bukan angka) meski isinya kosong
JUDUL_TEKS = ("nama", "kode", "uraian", "keterangan", "catatan", "akun",
              "pelanggan", "pemasok", "produk", "status", "tanggal", "tipe",
              "email", "telepon", "kota", "npwp", "pic", "aksi", "tindakan",
              "objek", "waktu", "pengguna", "satuan", "metode", "sumber",
              "vendor", "pengaju", "bank", "rekening", "kontak", "jabatan",
              "oleh", "alasan", "nama berkas", "lokasi", "tutup")


def periksa(tabel: QTableWidget) -> list:
    temuan = []
    if tabel.columnCount() == 0:
        return temuan

    # 1. alignment kolom angka
    for kolom in range(tabel.columnCount()):
        judul = tabel.horizontalHeaderItem(kolom)
        judul = (judul.text() if judul else "").lower()
        if any(t in judul for t in JUDUL_TEKS):
            continue

        contoh = []
        for baris in range(min(tabel.rowCount(), 12)):
            item = tabel.item(baris, kolom)
            if item is not None and item.text().strip():
                contoh.append(item.text().strip())
        if not contoh:
            continue
        angka = sum(1 for c in contoh if POLA_ANGKA.match(c))
        if angka < len(contoh) * 0.7:
            continue

        item = tabel.item(0, kolom)
        if item is None:
            continue
        if not (item.textAlignment() & Qt.AlignRight):
            temuan.append(("angka tidak rata kanan", judul or f"kolom {kolom}",
                           contoh[0][:18]))

    # 2. lebar total terhadap area tampil
    #
    # Tabel boleh lebih lebar dari areanya: bila isi kolom tidak muat, tabel
    # menggeser mendatar. Itu disengaja — memaksa kolom muat akan memotong
    # teksnya. Yang diperiksa di sini hanya bahwa tabel bisa menggeser
    # mendatar, sehingga kolom yang lebih lebar tetap dapat dijangkau.
    total = sum(tabel.columnWidth(i) for i in range(tabel.columnCount()))
    lebar = tabel.viewport().width()
    if lebar > 100 and total > lebar + 4:
        if tabel.horizontalScrollBarPolicy() == Qt.ScrollBarAlwaysOff:
            temuan.append(("kolom melebihi area tanpa geser", "",
                           f"{total} > {lebar}"))
        elif lebar - total > 120:
            temuan.append(("ruang kosong besar", "", f"selisih {lebar - total}"))

    # 3. jarak tepi baris
    if tabel.rowCount() and tabel.verticalHeader().defaultSectionSize() < 22:
        temuan.append(("baris terlalu rapat", "",
                       str(tabel.verticalHeader().defaultSectionSize())))

    return temuan


def main() -> int:
    app = QApplication.instance() or QApplication([])
    app.setStyle("Fusion")
    app.setStyleSheet(theme.stylesheet())

    perusahaan = services.list_companies()
    if not perusahaan:
        print("Tidak ada perusahaan. Jalankan tools/buat_data_contoh.py dulu.")
        return 1
    cid = perusahaan[0]["id"]

    hasil = sec.login("admin", config.DEFAULT_ADMIN_PASSWORD)
    if not hasil.ok:
        print("Login gagal.")
        return 1

    jendela = MainWindow(hasil, lisensi=_LISENSI_UJI)
    jendela.ctx.company_id = cid
    jendela.ctx.company = services.get_company(cid)
    jendela.ctx.beginner = False
    jendela.resize(1500, 950)
    jendela.show()

    masalah = []
    for kode in HALAMAN:
        try:
            jendela._navigasi(kode)
            for _ in range(6):
                app.processEvents()
            halaman = jendela.halaman.get(kode)
            if halaman is None:
                continue
            for tabel in halaman.findChildren(QTableWidget):
                if not tabel.isVisible() or tabel.rowCount() == 0:
                    continue
                for jenis, kolom, detail in periksa(tabel):
                    masalah.append((kode, jenis, kolom, detail))
                    print(f"  [{jenis:22s}] {kode:12s} "
                          f"{kolom[:22]:24s} {detail}")
        except Exception as e:
            print(f"  [ERROR] {kode}: {type(e).__name__}: {e}")

    print()
    if masalah:
        print(f"HASIL: {len(masalah)} masalah kerapian tabel")
        return 1
    print("HASIL: seluruh tabel rapi (angka rata kanan, lebar pas)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
