"""
Ukur geometri elemen halaman: tinggi, lebar, dan posisi.

Memakai mesin peramban bawaan Qt, jadi ukurannya sama dengan yang dihitung
peramban sungguhan. Hasilnya dipakai untuk memastikan kartu kartu pada satu
baris benar benar sama tinggi dan tidak ada elemen yang keluar batas.

Cara pakai:
    python tools/ukur_tata_letak.py index.html .fitur
    python tools/ukur_tata_letak.py kontak.html .kontak-jalan-kartu
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


def ukur(berkas: str, pemilih: str, lebar: int = 1280,
         tinggi: int = 1000) -> list:
    """Kembalikan daftar ukuran tiap elemen yang cocok dengan pemilih."""
    tampilan = QWebEngineView()
    tampilan.resize(lebar, tinggi)
    tampilan.show()

    tampilan.load(QUrl.fromLocalFile(str((WEB / berkas).resolve())))

    tunggu = QEventLoop()
    batas = QTimer()
    batas.setSingleShot(True)
    batas.timeout.connect(tunggu.quit)
    batas.start(20000)
    tampilan.loadFinished.connect(lambda _: tunggu.quit())
    tunggu.exec()

    # Beri waktu tata letak selesai dihitung.
    jeda = QEventLoop()
    QTimer.singleShot(1200, jeda.quit)
    jeda.exec()

    skrip = (
        "(() => {"
        f"  const els = [...document.querySelectorAll('{pemilih}')];"
        "  const hasil = els.map((el, i) => {"
        "    const r = el.getBoundingClientRect();"
        "    const s = getComputedStyle(el);"
        "    const j = el.querySelector('h3,h4,h2');"
        "    return {"
        "      i: i,"
        "      x: Math.round(r.x), y: Math.round(r.y),"
        "      w: Math.round(r.width), h: Math.round(r.height),"
        "      padB: s.paddingBottom,"
        "      teks: j ? j.textContent : ''"
        "    };"
        "  });"
        "  return JSON.stringify(hasil);"
        "})()")

    hasil = {"nilai": None}
    selesai = QEventLoop()

    def terima(nilai):
        hasil["nilai"] = nilai
        selesai.quit()

    tampilan.page().runJavaScript(skrip, terima)
    QTimer.singleShot(6000, selesai.quit)
    selesai.exec()

    tampilan.hide()

    teks = hasil["nilai"]
    if not teks:
        print("  ! halaman tidak mengembalikan hasil pengukuran")
        return []
    try:
        return json.loads(teks)
    except (TypeError, ValueError) as e:
        print(f"  ! hasil tidak dapat dibaca: {e}")
        return []


def main() -> int:
    if len(sys.argv) < 3:
        print("  pakai: python tools/ukur_tata_letak.py <berkas> <pemilih>")
        return 2

    berkas, pemilih = sys.argv[1], sys.argv[2]
    lebar = int(sys.argv[3]) if len(sys.argv) > 3 else 1280

    print("=" * 74)
    print(f"  UKUR TATA LETAK: {pemilih} di {berkas} (lebar {lebar})")
    print("=" * 74)
    print()

    daftar = ukur(berkas, pemilih, lebar)
    if not daftar:
        print("  ! tidak ada elemen yang cocok")
        return 1

    for d in daftar:
        nama = d["teks"][:38] if d["teks"] else ""
        print(f"  [{d['i']:2d}] x={d['x']:4d} y={d['y']:5d} "
              f"{d['w']:4d}x{d['h']:4d}  padB={d['padB']:>6s}  {nama}")

    print()
    # Kelompokkan per baris (y sama) lalu periksa tingginya.
    baris: dict = {}
    for d in daftar:
        baris.setdefault(d["y"], []).append(d)

    print("  Tinggi per baris:")
    ada_beda = False
    for y in sorted(baris):
        tinggi = [d["h"] for d in baris[y]]
        sama = len(set(tinggi)) == 1
        tanda = "sama" if sama else "BEDA"
        if not sama:
            ada_beda = True
        print(f"    y={y:5d}: {tinggi}  {tanda}")

    print()
    if ada_beda:
        print("  HASIL: ada kartu yang tingginya berbeda pada satu baris")
    else:
        print("  HASIL: seluruh kartu pada satu baris sama tinggi")
    return 0


if __name__ == "__main__":
    sys.exit(main())
