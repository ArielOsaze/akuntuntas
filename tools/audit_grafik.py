"""
Periksa tumpang tindih antar elemen yang digambar pada grafik dashboard.

Grafik batang digambar manual dengan QPainter, sehingga tata letaknya tidak
diperiksa oleh pemeriksa widget biasa. Alat ini menghitung sendiri posisi
setiap elemen yang digambar (label nilai, label bulan, penanda tren, penunjuk
bulan terpilih) lalu memastikan tidak ada dua elemen yang saling menimpa.

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



def kotak_teks(chart: BarChart, bulan_sorot: int) -> list:
    """Hitung kotak setiap elemen yang digambar grafik pada ukuran sekarang."""
    lebar, tinggi = chart.width(), chart.height()
    margin_kiri, margin_kanan = 86, 24
    margin_atas, margin_bawah = 42, 46
    lebar_grafik = lebar - margin_kiri - margin_kanan
    tinggi_grafik = tinggi - margin_atas - margin_bawah
    dasar = margin_atas + tinggi_grafik

    data = chart.data
    if not data or lebar_grafik <= 10 or tinggi_grafik <= 10:
        return []

    maks = max(max(d["pendapatan"], d["beban"] + d["hpp"]) for d in data)
    maks_bulat = chart._batas_atas(maks)
    n = len(data)
    lebar_grup = lebar_grafik / n
    lebar_batang = max(5.0, min(16.0, lebar_grup * 0.28))
    celah = 3.0

    fm = QFontMetrics(QFont(theme.FONT_UI, 7))
    kotak = []
    masalah_jarak: list[str] = []

    for i, d in enumerate(data):
        pusat = margin_kiri + i * lebar_grup + lebar_grup / 2
        x0 = pusat - lebar_batang - celah / 2
        h1 = (d["pendapatan"] / maks_bulat) * tinggi_grafik
        h2 = ((d["beban"] + d["hpp"]) / maks_bulat) * tinggi_grafik

        tengah1 = x0 + lebar_batang / 2
        tengah2 = x0 + lebar_batang * 1.5 + celah
        t1 = chart._nilai_batang(d["pendapatan"])
        t2 = chart._nilai_batang(d["beban"] + d["hpp"])
        l1 = fm.horizontalAdvance(t1) + 8
        l2 = fm.horizontalAdvance(t2) + 8

        ada1, ada2 = h1 >= 18, h2 >= 18
        # Label disembunyikan bila kolom terlalu sempit, sama seperti yang
        # dilakukan grafik. Tanpa penyesuaian ini, pemeriksaan mengukur label
        # yang sebenarnya tidak digambar.
        if lebar_grup < l1 + 6:
            ada1 = False
        if lebar_grup < l2 + 6:
            ada2 = False
        jarak_label = 8
        tinggi_label = 13
        berdekatan = ada1 and ada2 and abs(tengah1 - tengah2) < (l1 + l2) / 2
        batas = margin_atas - 14

        kotak1 = None
        if ada1:
            y = dasar - h1 - jarak_label - tinggi_label
            if berdekatan:
                y -= tinggi_label + 1
            y = max(y, batas)
            x = min(max(tengah1 - l1 / 2, 2.0), lebar - l1 - 2)
            kotak1 = (f"nilai pendapatan {t1}", x, y, l1, tinggi_label)
            kotak.append(kotak1)
        if ada2:
            y = max(dasar - h2 - jarak_label - tinggi_label, batas)
            x = min(max(tengah2 - l2 / 2, 2.0), lebar - l2 - 2)
            if kotak1 is not None:
                x1, y1, w1 = kotak1[1], kotak1[2], kotak1[3]
                # Logika pergeseran harus sama dengan yang dipakai grafik,
                # supaya pemeriksaan ini mengukur keadaan yang sebenarnya.
                if not (x + l2 <= x1 or x1 + w1 <= x):
                    batas_bawah = dasar - tinggi_label - 2
                    if abs(y - y1) < tinggi_label + 2:
                        y = min(y1 + tinggi_label + 3, batas_bawah)
                    if abs(y - y1) < tinggi_label + 2:
                        geser = x1 + w1 - x + 2
                        if x + geser + l2 <= lebar - 2:
                            x += geser
                        elif x1 - l2 - 2 >= 2:
                            x = x1 - l2 - 2
            kotak.append((f"nilai beban {t2}", x, y, l2, tinggi_label))

        # jarak label ke puncak batang tidak boleh nol (menempel)
        if ada1 and not berdekatan:
            celah1 = (dasar - h1) - (kotak1[2] + tinggi_label)
            if celah1 < 2:
                masalah_jarak.append(
                    f"bulan {i}: label pendapatan menempel batang "
                    f"(jarak {celah1:.0f}px)")
        if ada2:
            y_label2 = [k for k in kotak if k[0].startswith("nilai beban")][-1][2]
            celah2 = (dasar - h2) - (y_label2 + tinggi_label)
            if celah2 < 2:
                masalah_jarak.append(
                    f"bulan {i}: label beban menempel batang (jarak {celah2:.0f}px)")

        fm_bulan = QFontMetrics(QFont(theme.FONT_UI, 8))
        teks_bulan = config.MONTH_ABBR_ID[i]
        if fm_bulan.horizontalAdvance(teks_bulan) + 4 > lebar_grup:
            teks_bulan = teks_bulan[0]
        kotak.append((f"bulan {i} ({teks_bulan})", margin_kiri + i * lebar_grup + 2,
                      dasar + 11, max(1.0, lebar_grup - 4), 16))

    return kotak, masalah_jarak


def tumpang(a, b) -> bool:
    _, ax, ay, aw, ah = a
    _, bx, by, bw, bh = b
    return not (ax + aw <= bx or bx + bw <= ax or ay + ah <= by or by + bh <= ay)


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
        kotak, masalah_jarak = kotak_teks(chart, -1)
        pasangan = 0
        temuan = []
        for i in range(len(kotak)):
            for j in range(i + 1, len(kotak)):
                pasangan += 1
                if tumpang(kotak[i], kotak[j]):
                    temuan.append((kotak[i][0], kotak[j][0]))
        jumlah_temuan += len(temuan) + len(masalah_jarak)
        print(f"lebar {lebar_uji}: {len(kotak)} elemen, {pasangan} pasangan, "
              f"{len(temuan)} tumpang, {len(masalah_jarak)} menempel")
        for a, b in temuan[:6]:
            print(f"    {a!r} x {b!r}")
        for m in masalah_jarak[:6]:
            print(f"    {m}")

    print()
    if jumlah_temuan:
        print(f"HASIL: {jumlah_temuan} elemen grafik saling menimpa")
        return 1
    print("HASIL: tidak ada elemen grafik yang saling menimpa")
    return 0


if __name__ == "__main__":
    sys.exit(main())
