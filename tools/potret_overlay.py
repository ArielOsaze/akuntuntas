"""
Potret overlay live supaya tampilannya dapat diperiksa dengan mata.

Memakai mesin peramban bawaan Qt, jadi hasilnya mendekati tampilan di
peramban sungguhan: tata letak, warna, dan ukuran teks benar-benar
dihitung seperti yang dilihat penonton.

Cara pakai:
    python tools/potret_overlay.py
"""
from __future__ import annotations

from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
BERKAS = AKAR / "live_overlay" / "overlay.html"
KELUARAN = AKAR / "_potret_overlay"

from PySide6.QtCore import QEventLoop, QTimer, QUrl  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402
from PySide6.QtWebEngineWidgets import QWebEngineView  # noqa: E402

app = QApplication.instance() or QApplication([])


def tunggu(detik: float):
    loop = QEventLoop()
    QTimer.singleShot(int(detik * 1000), loop.quit)
    loop.exec()


def potret(view: QWebEngineView, nama: str) -> Path:
    """Simpan tampilan halaman sebagai gambar."""
    KELUARAN.mkdir(exist_ok=True)
    berkas = KELUARAN / f"{nama}.png"

    # Diperbarui berkali-kali supaya permukaan widget benar-benar selesai
    # digambar sebelum ditangkap. Tanpa ini hasilnya gambar kosong.
    for _ in range(6):
        app.processEvents()
        tunggu(0.35)

    gambar = view.grab()
    if gambar.isNull():
        print(f"  [GAGAL] {nama}: gambar kosong")
        return berkas

    gambar.save(str(berkas))

    ukuran_benar = (gambar.width() == 1080 and gambar.height() == 1920)
    tanda = "" if ukuran_benar else "  <- BUKAN 9:16 PENUH"
    print(f"  [OK] {nama:20} {berkas.stat().st_size // 1024} KB "
          f"({gambar.width()}x{gambar.height()}){tanda}")
    return berkas


print("=" * 70)
print("  POTRET OVERLAY LIVE")
print("=" * 70)

view = QWebEngineView()
view.setMinimumSize(1080, 1920)
view.resize(1080, 1920)
view.show()

# Ukuran disetel ulang setelah jendela tampil. Tanpa ini, jendela kadang
# memakai ukuran bawaan yang lebih pendek sehingga hasil potretnya bukan
# 9:16 penuh.
tunggu(0.6)
view.resize(1080, 1920)
app.processEvents()

selesai_muat = QEventLoop()
view.loadFinished.connect(selesai_muat.quit)
view.load(QUrl.fromLocalFile(str(BERKAS)))
QTimer.singleShot(20000, selesai_muat.quit)
selesai_muat.exec()

# Beri waktu animasi masuk selesai dan slide pertama tampil.
tunggu(3.5)


def ke_slide(nomor: int):
    """
    Tampilkan satu slide tertentu dan hentikan pergantian otomatis.

    Pergantian otomatis dimatikan lebih dahulu karena kalau tidak, slide
    berganti sendiri di tengah pemotretan dan yang tertangkap adalah slide
    yang salah.
    """
    view.page().runJavaScript(f"""
        (function(){{
            clearInterval(window.jamSlide);
            var s = document.querySelectorAll('.slide');
            var b = document.querySelectorAll('.bilah');
            s.forEach(function(e,i){{
                e.classList.remove('aktif','keluar');
                if(i === {nomor}) e.classList.add('aktif');
                else if(i < {nomor}) e.classList.add('keluar');
            }});
            b.forEach(function(e,i){{
                e.classList.remove('jalan','selesai');
                if(i < {nomor}) e.classList.add('selesai');
            }});
        }})();
    """)
    tunggu(1.0)


ke_slide(0)
potret(view, "slide-1-aplikasi")

ke_slide(3)
potret(view, "slide-4-laporan")

ke_slide(6)
potret(view, "slide-7-situs")

ke_slide(7)
potret(view, "slide-8-harga")

print(f"\n  tersimpan di: {KELUARAN}")
