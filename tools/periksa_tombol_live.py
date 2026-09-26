"""
Periksa semua tombol di semua halaman situs live.

Mencari tombol yang teksnya tidak terlihat, yaitu tombol yang warnanya
sama dengan latar belakangnya. Keadaan ini sulit terlihat dari kode
karena warna datang dari beberapa aturan CSS yang saling menimpa.

Pemakaian:
    python tools/periksa_tombol_live.py
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

HALAMAN = [
    ("beranda", ""),
    ("unduh", "unduh"),
    ("beli", "beli"),
    ("kontak", "kontak"),
    ("privasi", "privasi"),
    ("selesai", "selesai"),
    ("batal", "batal"),
    ("kwitansi", "kwitansi"),
    ("admin", "admin"),
]


def periksa(nama: str, jalur: str) -> list[dict]:
    """Kembalikan daftar tombol beserta warna teks dan latarnya."""
    tampilan = QWebEngineView()
    tampilan.resize(1280, 1000)
    tampilan.show()
    tampilan.load(QUrl(f"{ALAMAT}/{jalur}"))

    tunggu = QEventLoop()
    tampilan.loadFinished.connect(lambda _: tunggu.quit())
    batas = QTimer()
    batas.setSingleShot(True)
    batas.timeout.connect(tunggu.quit)
    batas.start(20000)
    tunggu.exec()

    jeda = QEventLoop()
    QTimer.singleShot(2000, jeda.quit)
    jeda.exec()

    hasil = {"nilai": ""}
    selesai = QEventLoop()

    def terima(nilai):
        hasil["nilai"] = nilai
        selesai.quit()

    # Ukur setiap tombol: warna teks, latar efektif (telusuri ke atas bila
    # transparan), dan rasio kontras.
    skrip = """(() => {
      function dariGradasi(gambar) {
        // Gradasi tidak muncul di backgroundColor, jadi warnanya harus
        // dibaca dari backgroundImage. Tanpa ini, tombol bergradasi
        // dianggap berlatar transparan dan warnanya salah dinilai.
        if (!gambar || gambar === 'none') return null;
        const m = gambar.match(/rgba?\\((\\d+),\\s*(\\d+),\\s*(\\d+)/);
        return m ? [parseInt(m[1]), parseInt(m[2]), parseInt(m[3])] : null;
      }
      function latarEfektif(el) {
        let n = el;
        while (n && n !== document.documentElement) {
          const g = getComputedStyle(n);
          const m = g.backgroundColor.match(/rgba?\\((\\d+),\\s*(\\d+),\\s*(\\d+)(?:,\\s*([\\d.]+))?\\)/);
          if (m) {
            const a = m[4] === undefined ? 1 : parseFloat(m[4]);
            if (a > 0.5) return [parseInt(m[1]), parseInt(m[2]), parseInt(m[3])];
          }
          const dariGambar = dariGradasi(g.backgroundImage);
          if (dariGambar) return dariGambar;
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
        return (hi + 0.05) / (lo + 0.05);
      }
      const keluar = [];
      document.querySelectorAll('a.tombol, button, .tombol-pilih, a.tombol-garis').forEach(t => {
        const g = getComputedStyle(t);
        if (g.display === 'none' || g.visibility === 'hidden') return;
        const r = t.getBoundingClientRect();
        if (r.width < 10 || r.height < 10) return;
        const m = g.color.match(/rgba?\\((\\d+),\\s*(\\d+),\\s*(\\d+)/);
        const teks = m ? [parseInt(m[1]), parseInt(m[2]), parseInt(m[3])] : [0,0,0];
        const latar = latarEfektif(t);
        keluar.push({
          teksIsi: (t.textContent || '').trim().slice(0, 44),
          warnaTeks: teks.join(','),
          latar: latar.join(','),
          rasio: Math.round(rasio(teks, latar) * 100) / 100,
          lebar: Math.round(r.width),
          kelas: (t.className || '').toString().slice(0, 60),
        });
      });
      return JSON.stringify(keluar);
    })()"""

    tampilan.page().runJavaScript(skrip, terima)
    QTimer.singleShot(2500, selesai.quit)
    selesai.exec()
    tampilan.deleteLater()

    try:
        return json.loads(hasil["nilai"])
    except Exception:
        print(f"  [GAGAL UKUR] {nama}: {hasil['nilai'][:60]}")
        return []


def main() -> int:
    print("=" * 78)
    print("  PERIKSA KONTRAS SEMUA TOMBOL DI SITUS LIVE")
    print("=" * 78)

    bermasalah = []
    for nama, jalur in HALAMAN:
        tombol = periksa(nama, jalur)
        print(f"\n  --- {nama}  ({len(tombol)} tombol) ---")
        for t in tombol:
            tanda = ""
            if t["rasio"] < 3.0:
                tanda = "   <<< TEKS TIDAK TERBACA"
                bermasalah.append((nama, t))
            print(f"    rasio {t['rasio']:5.2f}  teks={t['teksIsi']!r:46}")
            if tanda:
                print(f"      warna teks={t['warnaTeks']}  latar={t['latar']}")
                print(f"      kelas={t['kelas']}{tanda}")

    print()
    print("=" * 78)
    if bermasalah:
        print(f"  TEMUAN: {len(bermasalah)} tombol dengan teks tidak terbaca")
        for nama, t in bermasalah:
            print(f"    {nama}: {t['teksIsi']!r} rasio={t['rasio']}")
    else:
        print("  HASIL: seluruh tombol memenuhi kontras minimum (rasio >= 3)")
    print("=" * 78)
    return 1 if bermasalah else 0


if __name__ == "__main__":
    sys.exit(main())
