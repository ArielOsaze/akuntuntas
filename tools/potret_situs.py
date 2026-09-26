"""
Potret halaman situs, supaya tampilannya dapat diperiksa dengan mata.

Memakai mesin peramban bawaan Qt, jadi hasilnya mendekati tampilan di
peramban sungguhan: tata letak, warna, dan ukuran teks benar benar
dihitung seperti yang dilihat pengunjung.

Cara pakai:
    python tools/potret_situs.py
    python tools/potret_situs.py bagian_tombol
"""
from __future__ import annotations

import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
WEB = AKAR / "web"
KELUARAN = AKAR / "_potret_web"

from PySide6.QtCore import QEventLoop, QTimer, QUrl
from PySide6.QtWidgets import QApplication
from PySide6.QtWebEngineWidgets import QWebEngineView

app = QApplication.instance() or QApplication([])


def potret(nama: str, berkas: str, lebar: int = 1280,
           tinggi: int = 900, tunggu: int = 2200,
           gulir_ke: str = "", tekan: str = "") -> Path:
    """Potret satu halaman dan simpan sebagai gambar."""
    KELUARAN.mkdir(exist_ok=True)
    tujuan = KELUARAN / f"{nama}.png"

    tampilan = QWebEngineView()
    tampilan.resize(lebar, tinggi)
    tampilan.show()

    selesai = {"ya": False}

    def setelah_muat(ok):
        selesai["ya"] = True

    tampilan.loadFinished.connect(setelah_muat)
    tampilan.load(QUrl.fromLocalFile(str((WEB / berkas).resolve())))

    # Tunggu halaman selesai dimuat.
    tunggu_muat = QEventLoop()
    batas = QTimer()
    batas.setSingleShot(True)
    batas.timeout.connect(tunggu_muat.quit)
    batas.start(tunggu)
    tampilan.loadFinished.connect(lambda _: tunggu_muat.quit())
    tunggu_muat.exec()

    # Beri waktu tata letak dan huruf selesai dihitung.
    jeda = QEventLoop()
    QTimer.singleShot(900, jeda.quit)
    jeda.exec()

    # Tekan elemen tertentu lebih dulu, misalnya tombol yang membuka
    # formulir, supaya keadaan sesudah ditekan ikut terpotret.
    if tekan:
        hasil_tekan = {"nilai": ""}
        selesai_tekan = QEventLoop()

        def terima_tekan(nilai):
            hasil_tekan["nilai"] = nilai
            selesai_tekan.quit()

        skrip_tekan = (
            "(() => {"
            f"  const el = document.querySelector('{tekan}');"
            "  if (!el) return 'tidak ketemu';"
            "  el.click();"
            "  return 'ok';"
            "})()")
        tampilan.page().runJavaScript(skrip_tekan, terima_tekan)
        QTimer.singleShot(1200, selesai_tekan.quit)
        selesai_tekan.exec()
        if hasil_tekan["nilai"] != "ok":
            print(f"  ! tombol {tekan} tidak ketemu")
        # Beri waktu tata letak sesudah ditekan selesai dihitung.
        jeda_tekan = QEventLoop()
        QTimer.singleShot(800, jeda_tekan.quit)
        jeda_tekan.exec()

    if gulir_ke == "penuh":
        # Setel jendela setinggi isi halaman, lalu potret seluruhnya.
        tinggi_isi = {"px": 0}
        selesai_ukur = QEventLoop()

        def terima_tinggi(nilai):
            tinggi_isi["px"] = int(nilai or 0)
            selesai_ukur.quit()

        tampilan.page().runJavaScript(
            "Math.max(document.body.scrollHeight,"
            " document.documentElement.scrollHeight)",
            terima_tinggi)
        QTimer.singleShot(1500, selesai_ukur.quit)
        selesai_ukur.exec()

        if tinggi_isi["px"] > tinggi:
            tampilan.resize(lebar, min(tinggi_isi["px"] + 20, 6000))
            jeda_ukur = QEventLoop()
            QTimer.singleShot(900, jeda_ukur.quit)
            jeda_ukur.exec()
    elif gulir_ke:
        # Elemen digulir ke tengah layar supaya isi di atas dan di
        # bawahnya ikut terpotret, bukan hanya bagian bawahnya saja.
        skrip = (
            "(() => {"
            f"  const el = document.querySelector('{gulir_ke}');"
            "  if (!el) return 'tidak ketemu';"
            "  const r = el.getBoundingClientRect();"
            "  const t = window.pageYOffset + r.top"
            "            - (window.innerHeight - r.height) / 2;"
            "  window.scrollTo(0, Math.max(0, t));"
            "  return 'ok';"
            "})()")
        tampilan.page().runJavaScript(skrip)
        jeda2 = QEventLoop()
        QTimer.singleShot(900, jeda2.quit)
        jeda2.exec()

    # Ambil gambar halaman.
    selesai_gambar = {"ya": False}

    def simpan(gambar):
        gambar.save(str(tujuan))
        selesai_gambar["ya"] = True

    tampilan.grab().save(str(tujuan))
    tampilan.hide()

    if not tujuan.exists():
        raise RuntimeError(f"potret {nama} gagal disimpan")
    return tujuan


def main() -> int:
    print("=" * 72)
    print("  POTRET HALAMAN SITUS")
    print("=" * 72)
    print()

    daftar = [
        ("beranda", "index.html", 1280, 900, ""),
        ("beranda_hero", "index.html", 1280, 900, ""),
        ("harga", "index.html", 1280, 1100, "#harga"),
        ("banding_kepala", "index.html", 1280, 1000, ".banding-kepala"),
        ("banding_lebar", "index.html", 1280, 1000, ".banding"),
        ("banding_sempit", "index.html", 209, 1000, ".banding"),
        ("banding_370", "index.html", 370, 1000, ".banding"),
        ("banding_600", "index.html", 600, 1000, ".banding"),
        ("banding_bawah", "index.html", 1280, 1000, ".banding-pilih"),
        ("fitur", "index.html", 1280, 1100, "#fitur"),
        ("fitur_penuh", "index.html", 1280, 1400, "penuh"),
        ("ajakan", "index.html", 1280, 800, ".ajakan"),
        ("kontak", "kontak.html", 1280, 1000, ""),
        ("kontak_sempit", "kontak.html", 420, 1100, ""),
        ("kontak_bawah", "kontak.html", 1280, 1000, "#formulir"),
        ("kontak_sempit_bawah", "kontak.html", 420, 1100, ".kontak-aksi"),
        ("beli", "beli.html", 1280, 1000, ""),
        ("unduh", "unduh.html", 1280, 900, ""),
        ("privasi", "privasi.html", 1280, 900, ""),
    ]

    if len(sys.argv) > 1:
        pilih = sys.argv[1]
        daftar = [d for d in daftar if pilih in d[0]]

    berhasil = 0
    for d in daftar:
        nama, berkas, lebar, tinggi, gulir = d[0], d[1], d[2], d[3], d[4]
        try:
            tekan = ""
            if len(d) > 5:
                tekan = d[5]
            hasil = potret(nama, berkas, lebar, tinggi,
                           gulir_ke=gulir, tekan=tekan)
            ukuran = hasil.stat().st_size // 1024
            print(f"  [OK] {nama:16s} -> {hasil.name}  ({ukuran} KB)")
            berhasil += 1
        except Exception as e:
            print(f"  [GAGAL] {nama}: {type(e).__name__}: {e}")

    print()
    print(f"  berhasil dipotret: {berhasil} dari {len(daftar)}")
    print(f"  folder gambar: {KELUARAN}")
    return 0 if berhasil else 1


if __name__ == "__main__":
    sys.exit(main())
