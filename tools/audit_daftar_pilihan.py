"""
Periksa seluruh daftar pilihan di aplikasi.

Baris terpilih pada daftar pilihan pernah tertutup biru tua penuh sehingga
tulisannya tidak terbaca dan tampak seperti tajuk gelap. Penyebabnya warna
sorotan yang dipasang pada QComboBox ikut merambat ke daftar pilihannya.

Pemeriksaan ini membuka setiap daftar pilihan yang ada di seluruh halaman,
lalu memastikan baris terpilihnya memakai warna sorotan muda, bukan warna
tua yang menutupi tulisan.

Jalankan:  python tools/audit_daftar_pilihan.py
"""

import os
import sys
import time
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "src"))
os.environ.setdefault("AKUNTANSIID_DATA", str(AKAR / "_contoh"))

from PySide6.QtWidgets import QApplication, QComboBox      # noqa: E402

# Warna yang tidak boleh muncul pada baris terpilih: biru tua penuh.
TERLARANG = ((27, 79, 138), (22, 63, 110), (20, 60, 105))


def mirip(warna, acuan, toleransi: int = 14) -> bool:
    return (abs(warna.red() - acuan[0]) <= toleransi
            and abs(warna.green() - acuan[1]) <= toleransi
            and abs(warna.blue() - acuan[2]) <= toleransi)


def periksa_kotak(cb: QComboBox) -> str:
    """
    Buka satu daftar pilihan dan periksa warna baris terpilihnya.

    Mengembalikan keterangan masalah, atau teks kosong bila tidak ada.
    """
    if cb.count() == 0 or not cb.isEnabled():
        return ""

    try:
        cb.showPopup()
    except Exception:
        return ""
    for _ in range(20):
        QApplication.processEvents()
        time.sleep(0.01)

    tampilan = cb.view()
    if tampilan is None or not tampilan.isVisible():
        try:
            cb.hidePopup()
        except Exception:
            pass
        return ""

    gambar = tampilan.grab().toImage()
    lebar, tinggi = gambar.width(), gambar.height()

    # Baris terpilih ada di baris pertama bila belum ada pilihan lain, atau
    # di baris yang sedang disorot. Periksa beberapa baris pertama sekaligus.
    tinggi_baris = max(1, tampilan.sizeHintForRow(0))
    jumlah_diperiksa = min(3, max(1, tinggi // tinggi_baris))

    temuan = ""
    for i in range(jumlah_diperiksa):
        y = i * tinggi_baris + tinggi_baris // 2
        if y >= tinggi:
            continue
        warna = gambar.pixelColor(lebar - 6, y)
        for terlarang in TERLARANG:
            if mirip(warna, terlarang):
                temuan = (f"baris {i} disorot biru tua {warna.name()} "
                          f"sehingga tulisannya tertutup")
                break
        if temuan:
            break

    try:
        cb.hidePopup()
    except Exception:
        pass
    for _ in range(10):
        QApplication.processEvents()
        time.sleep(0.01)
    return temuan


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

    try:
        hasil = sec.login("admin", "admin123")
    except Exception as e:
        print(f"Tidak dapat masuk: {e}")
        print("Jalankan tools/buat_data_contoh.py dulu.")
        return 1

    jendela = MainWindow(hasil, lisensi=_lisensi_uji())
    jendela.resize(1400, 900)
    jendela.show()
    for _ in range(30):
        app.processEvents()
        time.sleep(0.02)

    masalah = []
    diperiksa = 0
    halaman_dikunjungi = 0

    halaman = getattr(jendela, "halaman", {})
    for kode in list(halaman.keys()):
        wdg = halaman[kode]
        try:
            jendela._navigasi(kode)
        except Exception:
            continue
        for _ in range(20):
            app.processEvents()
            time.sleep(0.01)
        halaman_dikunjungi += 1

        for cb in wdg.findChildren(QComboBox):
            if not cb.isVisible():
                continue
            diperiksa += 1
            temuan = periksa_kotak(cb)
            if temuan:
                masalah.append((kode, cb.currentText()[:30] or "(kosong)", temuan))

    print(f"{diperiksa} daftar pilihan diperiksa pada "
          f"{halaman_dikunjungi} halaman")
    print()

    if masalah:
        print(f"HASIL: {len(masalah)} daftar pilihan bermasalah")
        for kode, teks, alasan in masalah[:15]:
            print(f"   [{kode}] {teks!r} — {alasan}")
        return 1

    print("HASIL: tidak ada baris terpilih yang tertutup warna tua")
    return 0


if __name__ == "__main__":
    sys.exit(main())
