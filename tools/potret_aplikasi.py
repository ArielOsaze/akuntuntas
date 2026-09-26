"""
Potret halaman aplikasi AkunTuntas untuk diperiksa tampilannya.

Menjalankan jendela aplikasi sungguhan (bukan peramban), membuka halaman
tertentu, lalu menyimpan potretnya. Dipakai untuk menilai tampilan dengan
mata sekaligus mengukur tata letaknya.

Cara pakai:
    python tools/potret_aplikasi.py                    (semua halaman)
    python tools/potret_aplikasi.py dashboard
    python tools/potret_aplikasi.py dashboard --lebar 1400
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "src"))

from akuntansi_id import db  # noqa: E402

# Data uji dipakai supaya halaman berisi angka, bukan keadaan kosong.
os.environ.setdefault("AKUNTUNTAS_DATA", str(AKAR / "_data_potret"))

# Jendela digambar memakai platform asli, bukan offscreen: render
# offscreen tidak memakai huruf sistem sehingga seluruh teks tampil
# sebagai kotak kosong dan potretnya tidak dapat dinilai.

KELUARAN = AKAR / "_potret_app"

# Halaman yang dapat dipotret, memakai kode yang sama dengan menu aplikasi.
HALAMAN = [
    "dashboard",
    "analisis",
    "penjualan",
    "pembelian",
    "jurnal",
    "kas_bank",
    "pajak",
    "laporan",
    "aset",
    "mitra",
    "produk",
    "pengaturan",
]


def siapkan_data():
    """Siapkan basis data berisi contoh data supaya halaman tidak kosong."""
    from akuntansi_id import coa

    db.init_db()
    perusahaan = db.q("SELECT id FROM companies ORDER BY id LIMIT 1")
    if not perusahaan:
        cid = db.ex(
            "INSERT INTO companies (nama, bentuk, alamat, npwp) "
            "VALUES (?, ?, ?, ?)",
            "PT Contoh Potret", "pt", "Semarang", "01.234.567.8-901.000")
        coa.siapkan_coa(cid)
        return cid
    return perusahaan[0]["id"]


def main() -> int:
    nama = sys.argv[1] if len(sys.argv) > 1 else ""
    lebar = 1440
    tinggi = 900
    if "--lebar" in sys.argv:
        lebar = int(sys.argv[sys.argv.index("--lebar") + 1])
    if "--tinggi" in sys.argv:
        tinggi = int(sys.argv[sys.argv.index("--tinggi") + 1])

    KELUARAN.mkdir(exist_ok=True)

    siapkan_data()

    from PySide6.QtCore import QEventLoop, QTimer
    from PySide6.QtWidgets import QApplication
    from akuntansi_id.ui.main_window import MainWindow
    from akuntansi_id.core import security as sec

    # QApplication harus tetap ada selama jendela hidup. Seluruh
    # pengaturan tampilan disamakan dengan aplikasi sungguhan, supaya
    # potretnya benar benar menggambarkan yang dilihat pengguna.
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QFont
    from akuntansi_id.ui import theme as tema

    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    app.setStyle("Fusion")
    tema.palet_terang(app)
    app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet(tema.stylesheet())

    # Buat hasil login dari akun yang ada, sama seperti setelah pengguna
    # masuk. Bila belum ada akun, buat satu supaya halaman dapat dibuka.
    akun = db.q("SELECT id, username, full_name, role, app_mode "
                "FROM users ORDER BY id LIMIT 1")
    if akun:
        a = akun[0]
        hasil_login = sec.LoginResult(
            ok=True, user_id=a["id"], username=a["username"],
            full_name=a["full_name"], role=a["role"],
            app_mode=a["app_mode"] or "beginner", mode_dipilih=True)
    else:
        hasil_login = sec.LoginResult(
            ok=True, user_id=0, username="potret", full_name="Contoh Potret",
            role="admin", app_mode="expert", mode_dipilih=True)

    # Lisensi dibaca dengan cara yang sama seperti aplikasi sungguhan,
    # supaya seluruh menu terbuka saat dipotret.
    from akuntansi_id import config
    from akuntansi_id.core import license as LIS
    sah, _alasan, data_lisensi = LIS.lisensi_sah(config.DATA_DIR)
    if not sah:
        data_lisensi = None

    jendela = MainWindow(hasil_login, lisensi=data_lisensi)
    jendela.resize(lebar, tinggi)
    jendela.show()

    # Beri waktu halaman pertama selesai dimuat.
    jeda = QEventLoop()
    QTimer.singleShot(2500, jeda.quit)
    jeda.exec()

    daftar = [nama] if nama in HALAMAN else list(HALAMAN)

    # "--gulir" menggulir ke bawah sebanyak beberapa layar sebelum
    # memotret, supaya bagian bawah halaman yang panjang ikut terlihat.
    gulir = 0
    if "--gulir" in sys.argv:
        gulir = int(sys.argv[sys.argv.index("--gulir") + 1])

    berhasil = 0
    for nama_h in daftar:
        try:
            jendela._navigasi(nama_h)
            tunggu = QEventLoop()
            QTimer.singleShot(2000, tunggu.quit)
            tunggu.exec()

            if gulir:
                from PySide6.QtWidgets import QScrollArea
                halaman = dict.get(jendela.halaman, nama_h)
                if halaman is not None:
                    # Seluruh area gulir yang benar benar terlihat digulir.
                    # Halaman bertab punya satu area gulir per tab, dan
                    # menggulir tab yang tidak terlihat tidak berpengaruh.
                    digulir = 0
                    for area in halaman.findChildren(QScrollArea):
                        if not area.isVisible():
                            continue
                        bilah = area.verticalScrollBar()
                        if bilah.maximum() <= bilah.value():
                            continue
                        bilah.setValue(min(bilah.maximum(),
                                           bilah.value() + gulir))
                        digulir += 1
                    if digulir:
                        print(f"  (menggulir {digulir} area)")
                    tunggu2 = QEventLoop()
                    QTimer.singleShot(1200, tunggu2.quit)
                    tunggu2.exec()

            tujuan = KELUARAN / f"{nama_h}.png"
            jendela.grab().save(str(tujuan))
            if tujuan.exists():
                kb = tujuan.stat().st_size // 1024
                print(f"  [OK] {nama_h:12s} -> {tujuan.name}  ({kb} KB)")
                berhasil += 1
            else:
                print(f"  [GAGAL] {nama_h}: gambar tidak tersimpan")
        except Exception as e:
            print(f"  [GAGAL] {nama_h}: {type(e).__name__}: {e}")

    jendela.close()
    print()
    print(f"  berhasil dipotret: {berhasil} dari {len(daftar)}")
    print(f"  folder gambar: {KELUARAN}")
    return 0 if berhasil else 1


if __name__ == "__main__":
    sys.exit(main())
