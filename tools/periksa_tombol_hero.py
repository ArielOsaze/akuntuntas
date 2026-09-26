"""
Potret beranda pada beberapa lebar layar, khusus bagian tombol.

Gambar dari pengguna menunjukkan tombol kedua tampak kosong pada layar
sempit. Alat ini memotret bagian hero pada lebar lebar yang dicurigai
supaya penyebabnya dapat dipastikan.
"""
from __future__ import annotations

import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
WEB = AKAR / "web"
KELUARAN = AKAR / "_potret_web"

sys.path.insert(0, str(AKAR / "tools"))

from PySide6.QtCore import QEventLoop, QTimer, QUrl
from PySide6.QtWidgets import QApplication
from PySide6.QtWebEngineWidgets import QWebEngineView

app = QApplication.instance() or QApplication([])


def periksa(lebar: int) -> None:
    """Ukur tombol hero pada lebar layar tertentu."""
    tampilan = QWebEngineView()
    tampilan.resize(lebar, 900)
    tampilan.show()

    tampilan.load(QUrl.fromLocalFile(str((WEB / "index.html").resolve())))

    tunggu = QEventLoop()
    tampilan.loadFinished.connect(lambda _: tunggu.quit())
    batas = QTimer()
    batas.setSingleShot(True)
    batas.timeout.connect(tunggu.quit)
    batas.start(4000)
    tunggu.exec()

    jeda = QEventLoop()
    QTimer.singleShot(1200, jeda.quit)
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
    QTimer.singleShot(1500, selesai.quit)
    selesai.exec()

    import json
    try:
        data = json.loads(hasil["nilai"])
    except Exception:
        print(f"  lebar {lebar}: gagal ukur -> {hasil['nilai'][:60]}")
        tampilan.deleteLater()
        return

    print(f"\n  LEBAR {lebar}px")
    for t in data:
        print(f"    teks={t['teks']!r}")
        print(f"      warna={t['warna']}  latar={t['latar']}")
        print(f"      ukuran={t['lebar']}x{t['tinggi']}  kelas={t['kelas']}")

    # Simpan gambar bagian hero
    KELUARAN.mkdir(exist_ok=True)
    tujuan = KELUARAN / f"tombol_{lebar}.png"

    potret = QEventLoop()

    def simpan(data_gambar):
        with open(tujuan, "wb") as f:
            f.write(data_gambar)
        potret.quit()

    tampilan.grab().save(str(tujuan))
    print(f"    gambar: {tujuan.name}")
    tampilan.deleteLater()


if __name__ == "__main__":
    print("=" * 72)
    print("  PERIKSA TOMBOL HERO PADA BERBAGAI LEBAR")
    print("=" * 72)
    for lebar in (423, 600, 760, 900, 1280):
        periksa(lebar)
    print()
