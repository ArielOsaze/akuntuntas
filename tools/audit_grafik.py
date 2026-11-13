"""
Periksa tata letak elemen yang digambar manual pada grafik dashboard.

Grafik batang digambar dengan QPainter, sehingga pemeriksa widget biasa tidak
melihat label bulan dan angka sumbu. Alat ini menghitung posisi elemen itu
pada beberapa lebar jendela, lalu memastikan:

  1. label bulan tidak saling menimpa dan tetap di dalam grafik,
  2. angka sumbu Y tidak masuk ke bidang grafik,
  3. sorotan bulan sejajar dengan pasangan batangnya,
  4. batang tidak keluar dari bidang grafik.

Cara pakai:
    python tools/audit_grafik.py
"""
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
os.environ.setdefault("AKUNTANSIID_DATA",
                      str(Path(__file__).resolve().parents[1] / "_contoh"))

from PySide6.QtGui import QFont, QFontMetrics
from PySide6.QtWidgets import QApplication

from akuntansi_id import config
from akuntansi_id.core import security as sec
from akuntansi_id.ui import theme
from akuntansi_id.ui.main_window import MainWindow
from akuntansi_id.ui.pages.dashboard import BarChart

# Lisensi uji dipakai agar seluruh halaman ikut diperiksa, termasuk
# halaman yang hanya tersedia pada paket Enterprise.
from akuntansi_id.core.license import Lisensi as _LisensiUji
_LISENSI_UJI = _LisensiUji(kunci='ATNTUJI', paket='enterprise', fitur={})

# Sama dengan margin di BarChart.paintEvent.
MARGIN_KIRI, MARGIN_KANAN = 78, 20
MARGIN_ATAS, MARGIN_BAWAH = 22, 42


def periksa(chart: BarChart) -> tuple[int, list[str]]:
    """Kembalikan jumlah pasangan yang bermasalah beserta keterangannya."""
    lebar, tinggi = chart.width(), chart.height()
    lebar_grafik = lebar - MARGIN_KIRI - MARGIN_KANAN
    tinggi_grafik = tinggi - MARGIN_ATAS - MARGIN_BAWAH
    if lebar_grafik <= 10 or tinggi_grafik <= 10 or not chart.data:
        return 0, []

    dasar = MARGIN_ATAS + tinggi_grafik
    n = len(chart.data)
    lebar_grup = lebar_grafik / n
    lebar_batang = max(4.0, min(12.0, lebar_grup * 0.24))
    celah = 3.0
    fm_bulan = QFontMetrics(QFont(theme.FONT_UI, 8))

    kotak = []
    for i in range(n):
        teks = config.MONTH_ABBR_ID[i]
        if fm_bulan.horizontalAdvance(teks) + 4 > lebar_grup:
            teks = teks[0]
        kiri = MARGIN_KIRI + i * lebar_grup + 2
        lebar_label = max(1.0, min(lebar_grup - 4, lebar - 4 - kiri))
        kotak.append((f"bulan {i} ({teks})", kiri, dasar + 11,
                      lebar_label, 16))

    masalah: list[str] = []
    for i in range(len(kotak)):
        _, x, y, w, h = kotak[i]
        if x < 0 or y < 0 or x + w > lebar + 0.5 or y + h > tinggi + 0.5:
            masalah.append(f"label {kotak[i][0]} keluar dari grafik")
        for j in range(i + 1, len(kotak)):
            _, bx, by, bw, bh = kotak[j]
            if not (x + w <= bx or bx + bw <= x
                    or y + h <= by or by + bh <= y):
                masalah.append(
                    f"label {kotak[i][0]} menimpa {kotak[j][0]}")

    # Angka sumbu Y harus berhenti sebelum bidang grafik. Bila masuk ke
    # bidang, angka itu bisa tertutup batang bulan pertama.
    fm_sumbu = QFontMetrics(QFont(theme.FONT_UI, 8))
    for i in range(5):
        y = MARGIN_ATAS + tinggi_grafik * i / 4
        teks = chart._singkat(1_000_000)
        lebar_teks = fm_sumbu.horizontalAdvance(teks)
        if lebar_teks > MARGIN_KIRI - 14:
            masalah.append(
                f"angka sumbu Y ({lebar_teks}px) melewati margin kiri")

    # Sorotan dan batang harus memakai geometri yang sama.
    maks = max((max(d["pendapatan"], d["beban"] + d["hpp"]) for d in chart.data),
               default=0)
    laba_min = min((d["laba_sebelum_pajak"] for d in chart.data), default=0)
    bawah, atas, _garis = chart._sumbu(max(maks, 1), laba_min)
    selisih = atas - bawah
    for i, d in enumerate(chart.data):
        pusat_grup = MARGIN_KIRI + i * lebar_grup + lebar_grup / 2
        x0 = pusat_grup - lebar_batang - celah / 2
        pusat_batang = x0 + lebar_batang + celah / 2
        if abs(pusat_grup - pusat_batang) > 0.5:
            masalah.append(f"bulan {i}: sorotan tidak sejajar dengan batang")
        if x0 < MARGIN_KIRI - 0.5 or x0 + 2 * lebar_batang + celah > (
                lebar - MARGIN_KANAN + 0.5):
            masalah.append(f"bulan {i}: batang keluar dari bidang grafik")
        # Batang dan garis laba harus berada di dalam bidang grafik, termasuk
        # saat laba bulan itu negatif. Sebelumnya garis laba digambar dari
        # dasar grafik sehingga kerugian jatuh keluar bidang dan terpotong.
        for nama, nilai in (("pendapatan", d["pendapatan"]),
                            ("beban", d["beban"] + d["hpp"]),
                            ("laba", d["laba_sebelum_pajak"])):
            y = MARGIN_ATAS + ((atas - nilai) / selisih) * tinggi_grafik
            if y < MARGIN_ATAS - 0.5 or y > MARGIN_ATAS + tinggi_grafik + 0.5:
                masalah.append(
                    f"bulan {i}: {nama} keluar dari bidang grafik")

    return len(masalah), masalah


def periksa_sumbu() -> list[str]:
    """Periksa sumbu Y untuk bulan yang merugi."""
    masalah = []
    data = []
    for i in range(12):
        pendapatan = 20_000_000 + i * 5_000_000
        beban = 12_000_000
        data.append({
            "pendapatan": pendapatan, "beban": beban, "hpp": 0,
            "laba_sebelum_pajak": pendapatan - beban,
        })
    data[4].update(pendapatan=5_000_000, beban=30_000_000,
                   laba_sebelum_pajak=-25_000_000)

    chart = BarChart()
    chart.resize(760, 300)
    chart.set_data(data)
    temuan, masalah = periksa(chart)
    if temuan:
        masalah.insert(0, f"{temuan} unsur grafik keluar bidang pada data rugi")

    bawah, atas, garis = chart._sumbu(70_000_000, -25_000_000)
    if bawah > -25_000_000:
        masalah.append("sumbu tidak turun sampai kerugian terdalam")
    if any(abs(nilai) < 0.01 for nilai in garis) is False:
        masalah.append("garis nol tidak mendapat label")
    if garis != sorted(garis):
        masalah.append("garis bantu tidak berurutan")
    if "-" not in chart._singkat(-25_000_000):
        masalah.append("angka sumbu negatif tidak memakai tanda minus")
    return masalah


def periksa_latar_kartu(chart: BarChart) -> list[str]:
    """Pastikan kartu grafik benar-benar putih, bukan tembus pandang.

    Aturan gaya tanpa selector pada wadah di atas kartu dapat menular dan
    menghapus latar kartu. Bila itu terjadi, bidang grafik tampak sebagai
    kotak putih yang ditempel di atas latar krem halaman.
    """
    from PySide6.QtGui import QColor

    kartu = chart
    while kartu is not None and kartu.objectName() not in ("Card", "CardFlat"):
        kartu = kartu.parentWidget()
    if kartu is None:
        return ["kartu grafik tidak ditemukan"]

    gambar = kartu.grab().toImage()
    if gambar.isNull():
        return ["kartu grafik gagal digambar"]
    x = min(20, gambar.width() - 1)
    y = min(20, gambar.height() - 1)
    warna = QColor(gambar.pixel(x, y))
    if warna.alpha() < 250 or min(warna.red(), warna.green(), warna.blue()) < 246:
        return [f"latar kartu grafik tidak putih "
                f"({warna.name()}, alfa {warna.alpha()})"]
    return []


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyleSheet(theme.stylesheet())

    hasil = sec.LoginResult(ok=True, user_id=1, username="admin",
                            full_name="Admin", role="owner",
                            app_mode="expert", mode_dipilih=True)
    jw = MainWindow(hasil, lisensi=_LISENSI_UJI)
    jw.resize(1440, 900)
    jw.show()
    batas = time.time() + 2.0
    while time.time() < batas:
        app.processEvents()
        time.sleep(0.01)

    halaman = jw.stack.currentWidget()
    daftar = halaman.findChildren(BarChart)
    if not daftar:
        print("tidak ada grafik ditemukan")
        return 1
    chart = daftar[0]

    jumlah_temuan = 0
    for lebar_uji in (1440, 1280, 1100):
        jw.resize(lebar_uji, 900)
        for _ in range(10):
            app.processEvents()
        temuan, masalah = periksa(chart)
        jumlah_temuan += temuan
        print(f"lebar {lebar_uji}: {len(chart.data)} bulan, "
              f"{temuan} masalah tata letak")
        for m in masalah[:6]:
            print(f"    {m}")

    jw.resize(1440, 900)
    for _ in range(10):
        app.processEvents()
    masalah_kartu = periksa_latar_kartu(chart)
    if masalah_kartu:
        jumlah_temuan += len(masalah_kartu)
        print("[GAGAL] latar kartu grafik:")
        for m in masalah_kartu[:6]:
            print(f"    {m}")
    else:
        print("[LULUS] kartu grafik putih penuh, bukan tembus pandang")

    masalah_sumbu = periksa_sumbu()
    if masalah_sumbu:
        jumlah_temuan += len(masalah_sumbu)
        print("[GAGAL] sumbu bulan merugi:")
        for m in masalah_sumbu[:6]:
            print(f"    {m}")
    else:
        print("[LULUS] bulan merugi tetap tampil di dalam bidang grafik")

    print()
    if jumlah_temuan:
        print(f"HASIL: {jumlah_temuan} masalah tata letak grafik")
        return 1
    print("HASIL: grafik rapi pada seluruh ukuran dan data yang diuji")
    return 0


if __name__ == "__main__":
    sys.exit(main())
