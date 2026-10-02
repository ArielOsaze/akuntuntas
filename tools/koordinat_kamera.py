"""
Hitung koordinat kotak kamera untuk dipakai di aplikasi siaran.

Aplikasi siaran seperti Streamlabs dan OBS meminta angka pasti: posisi X,
posisi Y, lebar, dan tinggi. Alat ini mengukur langsung dari overlay supaya
angkanya benar, bukan perkiraan.

Cara pakai:
    python tools/koordinat_kamera.py
"""
from __future__ import annotations

from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
BERKAS = AKAR / "live_overlay" / "overlay.html"

from PySide6.QtCore import QEventLoop, QTimer, QUrl  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402
from PySide6.QtWebEngineWidgets import QWebEngineView  # noqa: E402

app = QApplication.instance() or QApplication([])


def tunggu(detik: float):
    loop = QEventLoop()
    QTimer.singleShot(int(detik * 1000), loop.quit)
    loop.exec()


def ukur(view, skrip: str):
    import json
    hasil = {"nilai": None, "sudah": False}
    selesai = QEventLoop()

    def terima(nilai):
        hasil["nilai"] = nilai
        hasil["sudah"] = True
        selesai.quit()

    view.page().runJavaScript(f"JSON.stringify({skrip})", terima)
    batas = QTimer()
    batas.setSingleShot(True)
    batas.timeout.connect(selesai.quit)
    batas.start(8000)
    selesai.exec()

    if not hasil["sudah"] or hasil["nilai"] is None:
        return None
    try:
        return json.loads(hasil["nilai"])
    except (ValueError, TypeError):
        return None


view = QWebEngineView()
view.setMinimumSize(1080, 1920)
view.resize(1080, 1920)
view.show()
tunggu(0.6)
view.resize(1080, 1920)

selesai = QEventLoop()
view.loadFinished.connect(selesai.quit)
view.load(QUrl.fromLocalFile(str(BERKAS)))
QTimer.singleShot(15000, selesai.quit)
selesai.exec()
tunggu(2.5)

data = ukur(view, """
    (function(){
        var cam = document.querySelector('.cam');
        var dalam = document.querySelector('.cam-dalam');
        var k = cam.getBoundingClientRect();
        var d = dalam.getBoundingClientRect();
        return {
            luarX: Math.round(k.left),
            luarY: Math.round(k.top),
            luarL: Math.round(k.width),
            luarT: Math.round(k.height),
            dalamX: Math.round(d.left),
            dalamY: Math.round(d.top),
            dalamL: Math.round(d.width),
            dalamT: Math.round(d.height),
            layarL: window.innerWidth,
            layarT: window.innerHeight
        };
    })()
""")

print("=" * 74)
print("  KOORDINAT KOTAK KAMERA UNTUK APLIKASI SIARAN")
print("=" * 74)

if not data:
    print("\n  GAGAL mengukur. Pastikan overlay.html tidak rusak.")
    raise SystemExit(1)

print(f"\n  Kanvas siaran: {data['layarL']} x {data['layarT']} piksel")
print()
print("  --- KOTAK KAMERA (seluruhnya, termasuk bingkai) ---")
print(f"      Posisi X : {data['luarX']}")
print(f"      Posisi Y : {data['luarY']}")
print(f"      Lebar    : {data['luarL']}")
print(f"      Tinggi   : {data['luarT']}")
print()
print("  --- AREA GAMBAR KAMERA (di dalam bingkai) ---")
print(f"      Posisi X : {data['dalamX']}")
print(f"      Posisi Y : {data['dalamY']}")
print(f"      Lebar    : {data['dalamL']}")
print(f"      Tinggi   : {data['dalamT']}")
print()
print("  --- ANGKA SIAP SALIN UNTUK STREAMLABS ---")
print(f"      X = {data['dalamX']}, Y = {data['dalamY']}, "
      f"Lebar = {data['dalamL']}, Tinggi = {data['dalamT']}")
print()
print("  Catatan: pakai angka AREA GAMBAR bila ingin bingkai berputar tetap")
print("  terlihat. Pakai angka KOTAK KAMERA bila ingin kamera menutupi")
print("  seluruhnya termasuk bingkai.")
print("=" * 74)
