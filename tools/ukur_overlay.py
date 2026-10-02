"""
Ukur tata letak overlay live langsung dari halaman.

Vision dapat keliru menilai ukuran dan proporsi dari potret. Alat ini
mengukur langsung dari mesin peramban: ukuran kotak kamera, ukuran wadah
gambar, dan apakah gambarnya mengisi penuh.

Cara pakai:
    python tools/ukur_overlay.py
"""
from __future__ import annotations

from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
BERKAS = AKAR / "live_overlay" / "overlay.html"

from PySide6.QtCore import QEventLoop, QTimer, QUrl  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402
from PySide6.QtWebEngineWidgets import QWebEngineView  # noqa: E402

app = QApplication.instance() or QApplication([])

LULUS = 0
GAGAL = 0


def cek(nama: str, benar: bool, keterangan: str = ""):
    global LULUS, GAGAL
    if benar:
        LULUS += 1
        print(f"  [LULUS] {nama}")
    else:
        GAGAL += 1
        print(f"  [GAGAL] {nama}" + (f" - {keterangan}" if keterangan else ""))


def tunggu(detik: float):
    loop = QEventLoop()
    QTimer.singleShot(int(detik * 1000), loop.quit)
    loop.exec()


def ukur(view, skrip: str):
    """
    Jalankan skrip di halaman dan kembalikan hasilnya sebagai objek Python.

    Hasilnya diubah menjadi teks JSON lebih dahulu, karena objek bawaan
    halaman tidak dapat dibaca langsung dari sisi Python.
    """
    hasil = {"nilai": None, "sudah": False}
    selesai = QEventLoop()

    def terima(nilai):
        hasil["nilai"] = nilai
        hasil["sudah"] = True
        selesai.quit()

    view.page().runJavaScript(f"JSON.stringify({skrip})", terima)

    # Tunggu sampai hasilnya benar-benar diterima, bukan sekadar lewat waktu.
    batas = QTimer()
    batas.setSingleShot(True)
    batas.timeout.connect(selesai.quit)
    batas.start(8000)
    selesai.exec()

    if not hasil["sudah"] or hasil["nilai"] is None:
        return None

    import json
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

print("=" * 74)
print("  UKUR TATA LETAK OVERLAY")
print("=" * 74)

# ---------------------------------------------------------- kotak kamera
data = ukur(view, """
    (function(){
        var cam = document.querySelector('.cam');
        var k = cam.getBoundingClientRect();
        var gaya = getComputedStyle(cam);
        return {
            lebar: Math.round(k.width),
            tinggi: Math.round(k.height),
            rasio: (k.width / k.height).toFixed(4),
            radius: gaya.borderRadius,
            atas: Math.round(k.top),
            kanan: Math.round(window.innerWidth - k.right)
        };
    })()
""")

if data:
    print("\n  --- Kotak kamera ---")
    print(f"      ukuran     : {data['lebar']}x{data['tinggi']} piksel")
    print(f"      rasio      : {data['rasio']}")
    print(f"      sudut      : {data['radius']}")
    print(f"      dari atas  : {data['atas']} px")
    print(f"      dari kanan : {data['kanan']} px")

    rasio = float(data["rasio"])
    cek("kotak kamera berbentuk 16:9 mendatar",
        abs(rasio - 16 / 9) < 0.02,
        f"rasio {rasio}, seharusnya {16/9:.4f}")
    cek("kotak kamera berada di dalam layar",
        data["lebar"] <= 1080 and data["atas"] >= 0 and data["kanan"] >= 0,
        f"lebar {data['lebar']}, atas {data['atas']}, kanan {data['kanan']}")
else:
    cek("kotak kamera terukur", False, "skrip tidak mengembalikan hasil")

# ------------------------------------------------- isi kotak kamera muat
data2 = ukur(view, """
    (function(){
        var cam = document.querySelector('.cam-dalam');
        var k = cam.getBoundingClientRect();
        var isi = document.querySelector('.cam-isi');
        var nama = document.querySelector('.cam-nama');
        var ikon = document.querySelector('.cam-isi svg');
        var paragraf = document.querySelector('.cam-isi p');
        return {
            camTinggi: Math.round(k.height),
            isiTinggi: Math.round(isi.scrollHeight),
            namaTinggi: Math.round(nama.getBoundingClientRect().height),
            ikonTinggi: Math.round(ikon.getBoundingClientRect().height),
            teksTinggi: Math.round(paragraf.getBoundingClientRect().height)
        };
    })()
""")

if data2:
    print("\n  --- Isi kotak kamera ---")
    print(f"      tinggi dalam kotak : {data2['camTinggi']} px")
    print(f"      tinggi isi         : {data2['isiTinggi']} px")
    print(f"      tinggi nama        : {data2['namaTinggi']} px")
    print(f"      ikon               : {data2['ikonTinggi']} px")
    print(f"      teks               : {data2['teksTinggi']} px")

    cek("isi kotak kamera muat tanpa terpotong",
        data2["isiTinggi"] <= data2["camTinggi"],
        f"isi {data2['isiTinggi']}px melebihi kotak {data2['camTinggi']}px")

# --------------------------------------------- wadah gambar halaman situs
data3 = ukur(view, """
    (function(){
        var wadah = document.querySelectorAll('.slide-gambar')[6];
        var k = wadah.getBoundingClientRect();
        var img = wadah.querySelector('img');
        var ki = img.getBoundingClientRect();
        var gaya = getComputedStyle(img);
        return {
            wadahLebar: Math.round(k.width),
            wadahTinggi: Math.round(k.height),
            imgLebar: Math.round(ki.width),
            imgTinggi: Math.round(ki.height),
            fit: gaya.objectFit,
            alami: img.naturalWidth + 'x' + img.naturalHeight,
            sisaBawah: Math.round(k.bottom - ki.bottom),
            sisaKanan: Math.round(k.right - ki.right)
        };
    })()
""")

if data3:
    print("\n  --- Gambar halaman situs (slide 7) ---")
    print(f"      wadah      : {data3['wadahLebar']}x{data3['wadahTinggi']} px")
    print(f"      gambar     : {data3['imgLebar']}x{data3['imgTinggi']} px")
    print(f"      ukuran asli: {data3['alami']}")
    print(f"      mode       : {data3['fit']}")
    print(f"      sisa bawah : {data3['sisaBawah']} px")
    print(f"      sisa kanan : {data3['sisaKanan']} px")

    cek("gambar situs mengisi penuh wadah (tanpa sisa kosong)",
        data3["sisaBawah"] <= 2 and data3["sisaKanan"] <= 2,
        f"sisa bawah {data3['sisaBawah']}px, kanan {data3['sisaKanan']}px")

# --------------------------------------- kotak angka tidak keluar gambar
data4 = ukur(view, """
    (function(){
        var wadah = document.querySelectorAll('.slide-gambar')[0];
        var angka = wadah.querySelector('.slide-angka');
        var k = wadah.getBoundingClientRect();
        var a = angka.getBoundingClientRect();
        return {
            diLuar: (a.right > k.right + 1) || (a.bottom > k.bottom + 1)
                    || (a.left < k.left - 1) || (a.top < k.top - 1),
            wadah: Math.round(k.width) + 'x' + Math.round(k.height),
            angka: Math.round(a.width) + 'x' + Math.round(a.height)
        };
    })()
""")

if data4:
    print("\n  --- Kotak angka pada gambar ---")
    print(f"      wadah gambar : {data4['wadah']}")
    print(f"      kotak angka  : {data4['angka']}")
    cek("kotak angka berada di dalam gambar",
        not data4["diLuar"], "kotak angka keluar dari batas gambar")

print()
print("=" * 74)
print(f"  HASIL: {LULUS} LULUS, {GAGAL} GAGAL")
print("=" * 74)
