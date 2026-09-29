"""
Potret popup dan dialog untuk pemeriksaan tampilan.

Cara pakai:
    python tools/potret_popup.py
"""
from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "src"))

os.environ["LOCALAPPDATA"] = tempfile.mkdtemp(prefix="potret_popup_")

from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication.instance() or QApplication([])

from akuntansi_id import db  # noqa: E402
from akuntansi_id.ui import theme  # noqa: E402

app.setStyle("Fusion")
theme.palet_terang(app)
app.setStyleSheet(theme.stylesheet())
db.init_db()

from akuntansi_id.ui import popup  # noqa: E402

HASIL = AKAR / "_potret_popup"
HASIL.mkdir(exist_ok=True)


def tunggu(detik=0.5):
    akhir = time.time() + detik
    while time.time() < akhir:
        app.processEvents()
        time.sleep(0.01)


def potret(kotak, nama: str):
    kotak.show()
    tunggu(0.6)
    berkas = HASIL / f"{nama}.png"
    kotak.grab().save(str(berkas))
    print(f"  [OK] {nama:22} {kotak.width()}x{kotak.height()}  {berkas.name}")
    kotak.close()
    tunggu(0.15)


# 1. Popup uji coba (yang paling penting)
k = popup.KotakPesan(
    None,
    "Masa uji coba tersisa 23 jam",
    "Seluruh fitur paket <b>Enterprise</b> terbuka selama masa uji coba. "
    "Setelah masa itu berakhir, aplikasi memerlukan kunci lisensi.",
    "tanya",
    rincian="Lisensi dibeli sekali dan berlaku selamanya, tanpa biaya bulanan.")
k.tambah_tombol("aktifkan", "Sudah punya lisensi? Aktifkan di sini",
                "primary", utama=True)
k.tambah_tombol("beli", "Beli lisensi", "biasa")
k.tambah_tombol("nanti", "Nanti", "biasa")
potret(k, "uji_coba")

# 2. Popup galat
k2 = popup.KotakPesan(
    None, "Data tidak dapat disimpan",
    "Kode akun <b>1101</b> sudah dipakai akun lain.",
    "galat",
    rincian="Ubah kode akun atau pilih akun yang sudah ada.")
k2.tambah_tombol("ok", "Tutup", "primary", utama=True)
potret(k2, "galat")

# 3. Popup sukses
k3 = popup.KotakPesan(
    None, "Data tersimpan",
    "Transaksi penjualan senilai <b>Rp11.100.000</b> berhasil dicatat.",
    "sukses",
    rincian="Jurnal otomatis dibuat dan saldo sudah diperbarui.")
k3.tambah_tombol("ok", "Selesai", "primary", utama=True)
potret(k3, "sukses")

# 4. Popup pertanyaan
k4 = popup.KotakPesan(
    None, "Hapus transaksi ini?",
    "Transaksi <b>INV-2026-0042</b> akan dipindahkan ke keranjang sampah.",
    "tanya",
    rincian="Data masih dapat dipulihkan dari keranjang sampah.")
k4.tambah_tombol("tidak", "Batal", "biasa")
k4.tambah_tombol("ya", "Hapus", "primary", utama=True)
potret(k4, "tanya")

# 5. Popup peringatan
k5 = popup.KotakPesan(
    None, "Jurnal belum seimbang",
    "Total debit <b>Rp5.000.000</b> tidak sama dengan total kredit "
    "<b>Rp4.500.000</b>.",
    "peringatan",
    rincian="Periksa kembali baris jurnal sebelum menyimpan.")
k5.tambah_tombol("ok", "Mengerti", "primary", utama=True)
potret(k5, "peringatan")

# 6. Dialog aktivasi
from akuntansi_id.ui.aktivasi import AktivasiDialog  # noqa: E402
d = AktivasiDialog(None)
d.show()
tunggu(0.7)
berkas = HASIL / "aktivasi.png"
d.grab().save(str(berkas))
print(f"  [OK] {'aktivasi':22} {d.width()}x{d.height()}  {berkas.name}")
d.close()

print(f"\n  tersimpan di: {HASIL}")
