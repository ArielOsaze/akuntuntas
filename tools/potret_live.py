"""
Potret situs live langsung dari alamatnya, bukan dari berkas lokal.

Alat potret lain membuka berkas di komputer, sehingga hasilnya tidak
menangkap keadaan yang benar benar dikirim server. Alat ini membuka
alamat sungguhan supaya perbedaan antara berkas lokal dan situs live
dapat diketahui.

Pemakaian:
    python tools/potret_live.py
    python tools/potret_live.py unduh
"""
from __future__ import annotations

import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
KELUARAN = AKAR / "_potret_live"

from PySide6.QtCore import QEventLoop, QTimer, QUrl
from PySide6.QtWidgets import QApplication
from PySide6.QtWebEngineWidgets import QWebEngineView

app = QApplication.instance() or QApplication([])

ALAMAT = "https://akuntuntas.xinet.id"


def potret(nama: str, jalur: str, lebar: int = 1280, tinggi: int = 900) -> Path:
    """Potret satu halaman situs live."""
    KELUARAN.mkdir(exist_ok=True)
    tujuan = KELUARAN / f"{nama}.png"

    tampilan = QWebEngineView()
    tampilan.resize(lebar, tinggi)
    tampilan.show()

    tampilan.load(QUrl(f"{ALAMAT}/{jalur}"))

    tunggu = QEventLoop()
    tampilan.loadFinished.connect(lambda _: tunggu.quit())
    batas = QTimer()
    batas.setSingleShot(True)
    batas.timeout.connect(tunggu.quit)
    batas.start(20000)
    tunggu.exec()

    # Beri waktu tata letak dan huruf selesai dihitung.
    jeda = QEventLoop()
    QTimer.singleShot(2500, jeda.quit)
    jeda.exec()

    tampilan.grab().save(str(tujuan))
    return tujuan


def ukur_tombol(nama: str, lebar: int) -> None:
    """Ukur tombol hero pada situs live."""
    tampilan = QWebEngineView()
    tampilan.resize(lebar, 900)
    tampilan.show()
    tampilan.load(QUrl(f"{ALAMAT}/"))

    tunggu = QEventLoop()
    tampilan.loadFinished.connect(lambda _: tunggu.quit())
    batas = QTimer()
    batas.setSingleShot(True)
    batas.timeout.connect(tunggu.quit)
    batas.start(20000)
    tunggu.exec()

    jeda = QEventLoop()
    QTimer.singleShot(2500, jeda.quit)
    jeda.exec()

    hasil = {"nilai": ""}
    selesai = QEventLoop()

    def terima(nilai):
        hasil["nilai"] = nilai
        selesai.quit()

    skrip = """(() => {
      const wadah = document.querySelector('.hero-tombol');
      if (!wadah) return JSON.stringify({galat: 'wadah tidak ada'});
      const keluar = [];
      wadah.querySelectorAll('a').forEach(t => {
        const g = getComputedStyle(t);
        const r = t.getBoundingClientRect();
        keluar.push({
          teks: t.textContent.trim(),
          kelas: t.className,
          warna: g.color,
          latar: g.backgroundColor,
          lebar: Math.round(r.width),
          tinggi: Math.round(r.height),
        });
      });
      return JSON.stringify(keluar);
    })()"""

    tampilan.page().runJavaScript(skrip, terima)
    QTimer.singleShot(2000, selesai.quit)
    selesai.exec()

    import json
    print(f"\n  LEBAR {lebar}px (situs live)")
    try:
        data = json.loads(hasil["nilai"])
        for t in data:
            print(f"    teks={t['teks']!r}")
            print(f"      warna={t['warna']}  latar={t['latar']}")
            print(f"      ukuran={t['lebar']}x{t['tinggi']}")
    except Exception:
        print(f"    gagal ukur: {hasil['nilai'][:80]}")

    KELUARAN.mkdir(exist_ok=True)
    tampilan.grab().save(str(KELUARAN / f"hero_live_{lebar}.png"))
    tampilan.deleteLater()


if __name__ == "__main__":
    print("=" * 72)
    print("  POTRET SITUS LIVE")
    print("=" * 72)

    daftar = [
        ("beranda", "", 1280, 900),
        ("beranda_sempit", "", 423, 900),
        ("unduh", "unduh", 1280, 900),
        ("kontak", "kontak", 1280, 900),
    ]

    if len(sys.argv) > 1:
        pilih = sys.argv[1]
        daftar = [d for d in daftar if pilih in d[0]]

    for nama, jalur, lebar, tinggi in daftar:
        try:
            hasil = potret(nama, jalur, lebar, tinggi)
            ukuran = hasil.stat().st_size // 1024
            print(f"  [OK] {nama:16s} -> {hasil.name}  ({ukuran} KB)")
        except Exception as e:
            print(f"  [GAGAL] {nama}: {type(e).__name__}: {e}")

    print()
    print("  Ukur tombol pada situs live:")
    for lebar in (423, 1280):
        ukur_tombol("hero", lebar)
