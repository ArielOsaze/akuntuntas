"""
Buat tangkapan perbandingan menu untuk setiap bentuk badan usaha.

Cara pakai:
    python tools/tangkapan_bentuk.py

Skrip ini menjalankan satu proses terpisah untuk setiap bentuk badan usaha.
Pemisahan proses diperlukan karena folder data aplikasi dibaca sekali saat
modul dimuat; menjalankannya dalam satu proses membuat bentuk kedua dan
seterusnya tetap memakai basis data yang pertama.

Hasil disimpan di folder _review_bentuk/ dan disalin ke Desktop.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import sqlite3
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
KELUAR = AKAR / "_review_bentuk"
DESKTOP = Path.home() / "Desktop" / "Hasil-Redesign-AkunTuntas"

# bentuk badan, nama perusahaan contoh, dan nama berkas tangkapan
BENTUK = [
    ("umkm_op", "Toko Sinar Jaya", "7-Mode-UMKM-Orang-Pribadi"),
    ("pt_perorangan", "PT Berkah Mandiri", "8-Mode-PT-Perorangan"),
    ("pt", "PT Maju Bersama Sejahtera", "9-Mode-PT"),
]

# Program yang dijalankan pada proses terpisah untuk satu bentuk badan.
PROGRAM = r'''
import os, sys, time
from pathlib import Path

folder = Path(sys.argv[1])
keluar = Path(sys.argv[2])
os.environ["AKUNTANSIID_DATA"] = str(folder)

sys.path.insert(0, str(Path(sys.argv[3]) / "src"))

from PySide6.QtWidgets import QApplication
from akuntansi_id.core import security as sec
from akuntansi_id.ui import theme
from akuntansi_id.ui.main_window import MainWindow

# Lisensi uji dipakai agar seluruh halaman ikut diperiksa, termasuk
# halaman yang hanya tersedia pada paket Enterprise.
from akuntansi_id.core.license import Lisensi as _LisensiUji
_LISENSI_UJI = _LisensiUji(kunci='ATNTUJI', paket='enterprise', fitur={})


app = QApplication.instance() or QApplication([])
app.setStyleSheet(theme.stylesheet())

hasil = sec.LoginResult(ok=True, user_id=1, username="ariel",
                        full_name="Ariel Pratama", role="owner",
                        app_mode="expert", mode_dipilih=True)
jendela = MainWindow(hasil, lisensi=_LISENSI_UJI)
jendela.resize(1440, 900)
jendela.show()

akhir = time.time() + 1.3
while time.time() < akhir:
    app.processEvents()
    time.sleep(0.01)

jendela._navigasi("dashboard")
akhir = time.time() + 1.0
while time.time() < akhir:
    app.processEvents()
    time.sleep(0.01)

jendela.grab().save(str(keluar))
print("DISEMBUNYIKAN:" + ",".join(sorted(jendela.sidebar.sembunyikan)))
jendela.close()
'''


def siapkan_basis(bentuk: str, nama: str) -> Path:
    """Salin data contoh lalu ganti nama dan bentuk perusahaannya."""
    sumber = AKAR / "_contoh"
    tujuan = AKAR / f"_bentuk_{bentuk}"

    if tujuan.exists():
        shutil.rmtree(tujuan, ignore_errors=True)
    shutil.copytree(sumber, tujuan)

    conn = sqlite3.connect(str(tujuan / "akuntuntas.db"))
    try:
        conn.execute("UPDATE companies SET nama=?, bentuk=?", (nama, bentuk))
        conn.commit()
    finally:
        conn.close()
    return tujuan


def main() -> int:
    if not (AKAR / "_contoh").exists():
        print("data contoh belum ada; jalankan tools/buat_data_contoh.py dulu")
        return 1

    KELUAR.mkdir(exist_ok=True)
    skrip = AKAR / "_tangkapan_bentuk_proses.py"
    skrip.write_text(PROGRAM, encoding="utf-8")

    print("Membuat tangkapan per bentuk badan usaha:")
    try:
        for bentuk, nama, nama_berkas in BENTUK:
            folder = siapkan_basis(bentuk, nama)
            keluaran = KELUAR / f"{nama_berkas}.png"

            hasil = subprocess.run(
                [sys.executable, str(skrip), str(folder), str(keluaran),
                 str(AKAR)],
                capture_output=True, text=True, cwd=str(AKAR))

            if hasil.returncode != 0:
                print(f"  {nama_berkas}: GAGAL")
                print(f"    {hasil.stderr.strip()[-200:]}")
            else:
                baris = [b for b in hasil.stdout.splitlines()
                         if b.startswith("DISEMBUNYIKAN:")]
                sembunyi = baris[0].split(":", 1)[1] if baris else ""
                print(f"  {nama_berkas}.png  (menu disembunyikan: "
                      f"{sembunyi if sembunyi else 'tidak ada'})")

            shutil.rmtree(folder, ignore_errors=True)
    finally:
        skrip.unlink(missing_ok=True)

    if DESKTOP.parent.exists():
        DESKTOP.mkdir(parents=True, exist_ok=True)
        for berkas in sorted(KELUAR.glob("*.png")):
            shutil.copy2(berkas, DESKTOP / berkas.name)
        print()
        print(f"disalin ke: {DESKTOP}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
