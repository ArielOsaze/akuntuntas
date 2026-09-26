"""
Periksa ukuran perbandingan paket pada layar sempit.

Menjawab pertanyaan: apakah pengunjung harus menggeser ke samping untuk
membaca keterangan paket Standar dan Enterprise, dan apakah nama paket
serta nilainya benar benar tampil.

Cara pakai:
    python tools/periksa_banding.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
WEB = AKAR / "web"

from PySide6.QtCore import QEventLoop, QTimer, QUrl
from PySide6.QtWidgets import QApplication
from PySide6.QtWebEngineWidgets import QWebEngineView

app = QApplication.instance() or QApplication([])

SKRIP = """
(() => {
  const de = document.documentElement;
  const ambil = (s) => document.querySelector(s);
  const ukur = (el) => el ? Math.round(el.getBoundingClientRect().width) : -1;
  const gaya = (el, s) => {
    if (!el) return 'x';
    const anak = el.querySelector(s);
    return anak ? getComputedStyle(anak).display : 'tidak ada';
  };
  const kisi = ambil('.banding-kisi');
  const kepala = ambil('.banding-kepala');
  const fitur = ambil('.banding-fitur');
  const nama = ambil('.banding-nama');
  const nilai = ambil('.banding-nilai');
  return JSON.stringify({
    lebar_jendela: window.innerWidth,
    lebar_dokumen: de.scrollWidth,
    perlu_geser: de.scrollWidth > window.innerWidth + 1,
    kisi: ukur(kisi),
    kepala: ukur(kepala),
    fitur: ukur(fitur),
    nama: ukur(nama),
    nilai: ukur(nilai),
    kepala_tampil: kepala ? getComputedStyle(kepala).display : 'x',
    nama_paket_tampil: gaya(nilai, '.nilai-paket'),
    nilai_teks_tampil: gaya(nilai, '.nilai-teks')
  });
})()
"""


def periksa(lebar: int) -> dict:
    tampilan = QWebEngineView()
    tampilan.resize(lebar, 900)
    tampilan.show()

    tampilan.load(QUrl.fromLocalFile(str((WEB / "index.html").resolve())))
    tunggu = QEventLoop()
    QTimer.singleShot(20000, tunggu.quit)
    tampilan.loadFinished.connect(lambda _: tunggu.quit())
    tunggu.exec()

    jeda = QEventLoop()
    QTimer.singleShot(1800, jeda.quit)
    jeda.exec()

    hasil = {"nilai": None}
    selesai = QEventLoop()

    def terima(nilai):
        hasil["nilai"] = nilai
        selesai.quit()

    tampilan.page().runJavaScript(SKRIP, terima)
    QTimer.singleShot(6000, selesai.quit)
    selesai.exec()
    tampilan.hide()

    if not hasil["nilai"]:
        return {"lebar_jendela": lebar, "gagal": True}
    d = json.loads(hasil["nilai"])
    d["gagal"] = False
    return d


def main() -> int:
    print("=" * 74)
    print("  PERIKSA PERBANDINGAN PAKET PADA BERBAGAI LEBAR LAYAR")
    print("=" * 74)
    print()

    gagal = 0
    for lebar in (209, 320, 375, 414, 600, 768, 1280):
        d = periksa(lebar)
        if d.get("gagal"):
            print(f"  [GAGAL] {lebar}px: pengukuran tidak menghasilkan apa pun")
            gagal += 1
            continue

        sempit = d["lebar_jendela"] <= 760
        masalah = []
        if d["perlu_geser"]:
            masalah.append("perlu digeser ke samping")
        # Pada layar sempit, nama paket harus tampil karena kepala disembunyikan.
        if sempit and d["nama_paket_tampil"] == "none":
            masalah.append("nama paket tidak tampil")
        if sempit and d["nilai_teks_tampil"] == "none":
            masalah.append("keterangan nilai tidak tampil")
        # "tidak ada" berarti baris itu berisi teks langsung, bukan tanda
        # centang, jadi memang tidak memerlukan keterangan tambahan.
        if not sempit and d["kepala_tampil"] == "none":
            masalah.append("kepala paket tersembunyi pada layar lebar")

        tanda = "AMAN " if not masalah else "MASALAH"
        print(f"  [{tanda}] {lebar:4d}px  isi={d['lebar_dokumen']:4d} "
              f"kisi={d['kisi']:3d} nama={d['nama']:3d} nilai={d['nilai']:3d}")
        if masalah:
            gagal += 1
            for m in masalah:
                print(f"            - {m}")

    print()
    print("=" * 74)
    if gagal:
        print(f"  HASIL: {gagal} lebar layar bermasalah")
    else:
        print("  HASIL: seluruh lebar layar AMAN")
    print("=" * 74)
    return 1 if gagal else 0


if __name__ == "__main__":
    sys.exit(main())
