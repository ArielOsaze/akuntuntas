"""
Uji tombol hero pada banyak lebar layar, cari yang teksnya hilang.

Gambar dari pengguna menunjukkan tombol kedua tampak kosong pada layar
sempit. Alat ini memotret bagian tombol pada setiap lebar yang dicurigai
dan memeriksa pikselnya, supaya lebar mana yang bermasalah dapat
diketahui dengan pasti.

Pemakaian:
    python tools/uji_lebar_tombol.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
KELUARAN = AKAR / "_potret_live"

from PySide6.QtCore import QEventLoop, QTimer, QUrl
from PySide6.QtWidgets import QApplication
from PySide6.QtWebEngineWidgets import QWebEngineView

app = QApplication.instance() or QApplication([])
ALAMAT = "https://akuntuntas.xinet.id"

LEBAR_UJI = [360, 380, 400, 420, 423, 440, 480, 520, 600, 760, 900, 1280]


def uji(lebar: int) -> dict:
    """Ukur tombol hero pada satu lebar layar."""
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
    QTimer.singleShot(1800, jeda.quit)
    jeda.exec()

    hasil = {"nilai": ""}
    selesai = QEventLoop()

    def terima(nilai):
        hasil["nilai"] = nilai
        selesai.quit()

    # Ukur setiap tombol hero: warna teks dan latar efektifnya.
    skrip = """(() => {
      function latarEfektif(el) {
        let n = el;
        while (n && n !== document.documentElement) {
          const g = getComputedStyle(n).backgroundColor;
          const m = g.match(/rgba?\\((\\d+),\\s*(\\d+),\\s*(\\d+)(?:,\\s*([\\d.]+))?\\)/);
          if (m) {
            const a = m[4] === undefined ? 1 : parseFloat(m[4]);
            if (a > 0.5) return [parseInt(m[1]), parseInt(m[2]), parseInt(m[3])];
          }
          n = n.parentElement;
        }
        return [255, 255, 255];
      }
      function terang(c) {
        const s = c.map(v => { v /= 255; return v <= 0.03928 ? v/12.92 : Math.pow((v+0.055)/1.055, 2.4); });
        return 0.2126*s[0] + 0.7152*s[1] + 0.0722*s[2];
      }
      function rasio(a, b) {
        const l1 = terang(a), l2 = terang(b);
        const hi = Math.max(l1, l2), lo = Math.min(l1, l2);
        return Math.round(((hi + 0.05) / (lo + 0.05)) * 100) / 100;
      }
      const wadah = document.querySelector('.hero-tombol');
      if (!wadah) return JSON.stringify({galat: 'wadah tidak ada'});
      const keluar = [];
      wadah.querySelectorAll('a').forEach(t => {
        const g = getComputedStyle(t);
        const r = t.getBoundingClientRect();
        const m = g.color.match(/rgba?\\((\\d+),\\s*(\\d+),\\s*(\\d+)/);
        const teks = m ? [parseInt(m[1]), parseInt(m[2]), parseInt(m[3])] : [0,0,0];
        const latar = latarEfektif(t);
        keluar.push({
          teks: t.textContent.trim().slice(0, 30),
          warnaTeks: teks.join(','),
          latar: latar.join(','),
          rasio: rasio(teks, latar),
          lebar: Math.round(r.width),
          x: Math.round(r.left),
          y: Math.round(r.top),
          display: g.display,
          fontSize: g.fontSize,
        });
      });
      return JSON.stringify(keluar);
    })()"""

    tampilan.page().runJavaScript(skrip, terima)
    QTimer.singleShot(2000, selesai.quit)
    selesai.exec()

    KELUARAN.mkdir(exist_ok=True)
    tampilan.grab().save(str(KELUARAN / f"hero_{lebar}.png"))
    tampilan.deleteLater()

    try:
        return json.loads(hasil["nilai"])
    except Exception:
        return {"galat": hasil["nilai"][:60]}


def main() -> int:
    print("=" * 78)
    print("  UJI TOMBOL HERO PADA BANYAK LEBAR LAYAR")
    print("=" * 78)

    bermasalah = []
    for lebar in LEBAR_UJI:
        data = uji(lebar)
        if isinstance(data, dict) and "galat" in data:
            print(f"\n  {lebar}px : GAGAL ukur ({data['galat']})")
            continue

        print(f"\n  {lebar}px")
        for t in data:
            tanda = ""
            if t["rasio"] < 3.0:
                tanda = "   <<< TEKS TIDAK TERBACA"
                bermasalah.append((lebar, t))
            print(f"    {t['teks']!r:24} rasio={t['rasio']:5.2f}  "
                  f"ukuran={t['lebar']}x{t['y']}  x={t['x']}{tanda}")
            if tanda:
                print(f"      warna teks={t['warnaTeks']}  latar={t['latar']}  "
                      f"font={t['fontSize']}")

    print()
    print("=" * 78)
    if bermasalah:
        print(f"  TEMUAN: {len(bermasalah)} keadaan dengan teks tidak terbaca")
        for lebar, t in bermasalah:
            print(f"    {lebar}px: {t['teks']!r} rasio={t['rasio']} "
                  f"warna={t['warnaTeks']} latar={t['latar']}")
    else:
        print("  HASIL: seluruh tombol hero terbaca pada semua lebar uji")
    print("=" * 78)
    return 1 if bermasalah else 0


if __name__ == "__main__":
    sys.exit(main())
