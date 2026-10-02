"""
Periksa penanda baris pada tabel perbandingan paket di situs live.

Dua jenis perbedaan harus tampak berbeda: baris yang hanya ada di
Enterprise (penanda biru) dan baris yang batasannya berbeda (penanda
cokelat). Alat ini menghitung jumlah penanda tiap jenis dan memastikan
keduanya muncul pada baris yang benar.

Pemakaian:
    python tools/periksa_penanda_live.py
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


def main() -> int:
    print("=" * 78)
    print("  PERIKSA PENANDA BARIS TABEL PERBANDINGAN (SITUS LIVE)")
    print("=" * 78)

    tampilan = QWebEngineView()
    tampilan.resize(1280, 1000)
    tampilan.show()
    tampilan.load(QUrl(f"{ALAMAT}/"))

    tunggu = QEventLoop()
    tampilan.loadFinished.connect(lambda _: tunggu.quit())
    batas = QTimer()
    batas.setSingleShot(True)
    batas.timeout.connect(tunggu.quit)
    batas.start(25000)
    tunggu.exec()

    jeda = QEventLoop()
    QTimer.singleShot(2500, jeda.quit)
    jeda.exec()

    hasil = {"nilai": ""}
    selesai = QEventLoop()

    def terima(nilai):
        hasil["nilai"] = nilai
        selesai.quit()

    # Kumpulkan seluruh baris perbandingan beserta kelas penandanya.
    skrip = """(() => {
      const baris = [];
      document.querySelectorAll('.banding-fitur').forEach(b => {
        const nama = b.querySelector('.banding-nama');
        baris.push({
          nama: nama ? nama.textContent.trim().slice(0, 62) : '?',
          kelas: (b.className || '').toString(),
          label: Array.from(b.querySelectorAll('.banding-label, .penanda-label'))
                       .map(e => e.textContent.trim()).join('|'),
        });
      });
      return JSON.stringify(baris);
    })()"""

    tampilan.page().runJavaScript(skrip, terima)
    QTimer.singleShot(2500, selesai.quit)
    selesai.exec()

    try:
        baris = json.loads(hasil["nilai"])
    except Exception:
        print(f"  GAGAL ukur: {hasil['nilai'][:120]}")
        return 1

    print(f"\n  jumlah baris perbandingan: {len(baris)}")
    print()
    for b in baris:
        kelas = b["kelas"]
        tanda = ""
        if "beda" in kelas:
            tanda = "  [penanda cokelat: batasan berbeda]"
        elif "eksklusif" in kelas or "khusus" in kelas:
            tanda = "  [penanda biru: hanya Enterprise]"
        elif "penanda" in kelas or "tanda" in kelas:
            tanda = f"  [{kelas}]"
        print(f"    {b['nama'][:60]}{tanda}")
        if b["label"]:
            print(f"      label: {b['label']}")

    # Simpan potret tabel perbandingan
    KELUARAN.mkdir(exist_ok=True)
    tampilan.page().runJavaScript(
        "document.querySelector('.banding').scrollIntoView({block:'start'});")
    jeda2 = QEventLoop()
    QTimer.singleShot(900, jeda2.quit)
    jeda2.exec()
    tampilan.grab().save(str(KELUARAN / "banding_live.png"))
    print("\n  gambar: banding_live.png")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
