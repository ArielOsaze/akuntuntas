"""
Periksa apakah halaman meluber ke samping pada berbagai lebar layar.

Halaman yang meluber memaksa pengunjung menggeser ke samping untuk
membaca isinya. Pemeriksaan ini memakai mesin peramban bawaan Qt, jadi
ukurannya sama dengan yang dihitung peramban sungguhan.

Yang diperiksa pada setiap lebar layar:
  1. Lebar isi halaman tidak melebihi lebar layar.
  2. Tidak ada elemen yang tepinya keluar dari layar.
  3. Elemen yang meluber disebutkan namanya supaya mudah diperbaiki.

Cara pakai:
    python tools/periksa_luber.py index.html
    python tools/periksa_luber.py index.html 209 320 375 768
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

# Lebar layar yang diperiksa. 209 adalah lebar gambar tangkapan pengguna.
LEBAR_BAKU = [209, 320, 375, 414, 600, 768, 1024, 1280]


def periksa(berkas: str, lebar: int) -> dict:
    """Kembalikan hasil pemeriksaan luber untuk satu lebar layar."""
    tampilan = QWebEngineView()
    tampilan.resize(lebar, 900)
    tampilan.show()

    tampilan.load(QUrl.fromLocalFile(str((WEB / berkas).resolve())))
    tunggu = QEventLoop()
    batas = QTimer()
    batas.setSingleShot(True)
    batas.timeout.connect(tunggu.quit)
    batas.start(20000)
    tampilan.loadFinished.connect(lambda _: tunggu.quit())
    tunggu.exec()

    jeda = QEventLoop()
    QTimer.singleShot(1100, jeda.quit)
    jeda.exec()

    # Cari elemen yang tepi kanannya melewati lebar layar.
    skrip = (
        "(() => {"
        "  const lw = document.documentElement.clientWidth;"
        "  const semua = [...document.querySelectorAll('body *')];"
        "  const didalamGulir = (el) => {"
        "    let p = el.parentElement;"
        "    while (p && p !== document.body) {"
        "      const s = getComputedStyle(p);"
        "      const ox = s.overflowX;"
        "      if (ox === 'auto' || ox === 'scroll' || ox === 'hidden')"
        "        return true;"
        "      p = p.parentElement;"
        "    }"
        "    return false;"
        "  };"
        "  const didalamWadahContoh = (el) => {"
        "    return el.closest('.contoh') !== null;"
        "  };"
        "  const luber = [];"
        "  for (const el of semua) {"
        "    const r = el.getBoundingClientRect();"
        "    if (r.width === 0 || r.height === 0) continue;"
        "    if (r.right <= lw + 1.5) continue;"
        "    const s = getComputedStyle(el);"
        "    if (s.position === 'fixed') continue;"
        "    if (didalamGulir(el)) continue;"
        "    if (didalamWadahContoh(el)) continue;"
        "    luber.push({"
        "      tag: el.tagName.toLowerCase(),"
        "      kelas: (el.className || '').toString().slice(0, 46),"
        "      kanan: Math.round(r.right),"
        "      lebar: Math.round(r.width)"
        "    });"
        "  }"
        "  return JSON.stringify({"
        "    lebar_layar: window.innerWidth,"
        "    lebar_isi: document.documentElement.scrollWidth,"
        "    luber: luber.slice(0, 12)"
        "  });"
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

    # Bila pengukuran gagal, hasilnya ditandai supaya TIDAK dilaporkan
    # aman. Kegagalan mengukur bukan berarti halaman sudah rapi.
    if not hasil["nilai"]:
        return {"lebar_layar": lebar, "lebar_isi": -1, "luber": [],
                "gagal_ukur": True}
    try:
        hasil_baca = json.loads(hasil["nilai"])
        hasil_baca["gagal_ukur"] = False
        return hasil_baca
    except (TypeError, ValueError):
        return {"lebar_layar": lebar, "lebar_isi": -1, "luber": [],
                "gagal_ukur": True}


def main() -> int:
    berkas = sys.argv[1] if len(sys.argv) > 1 else "index.html"
    lebar_list = ([int(x) for x in sys.argv[2:]] if len(sys.argv) > 2
                  else LEBAR_BAKU)

    print("=" * 74)
    print(f"  PERIKSA LUBER: {berkas}")
    print("=" * 74)
    print()

    gagal = 0
    for lebar in lebar_list:
        h = periksa(berkas, lebar)
        layar = h["lebar_layar"] or lebar
        isi = h["lebar_isi"]
        luber = h["luber"]

        if h.get("gagal_ukur"):
            gagal += 1
            print(f"  [GAGAL] {lebar:4d}px  pengukuran tidak menghasilkan apa pun")
            continue

        if isi <= layar + 1 and not luber:
            print(f"  [AMAN]  {lebar:4d}px  lebar isi {isi}px")
            continue

        gagal += 1
        selisih = isi - layar
        print(f"  [LUBER] {lebar:4d}px  lebar isi {isi}px "
              f"(kelebihan {selisih}px)")
        for e in luber[:5]:
            print(f"            {e['tag']}.{e['kelas']} "
                  f"kanan={e['kanan']} lebar={e['lebar']}")
        print()

    print("=" * 74)
    if gagal:
        print(f"  HASIL: {gagal} dari {len(lebar_list)} lebar layar LUBER")
    else:
        print(f"  HASIL: seluruh {len(lebar_list)} lebar layar AMAN")
    print("=" * 74)
    return 1 if gagal else 0


if __name__ == "__main__":
    sys.exit(main())
