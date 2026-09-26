"""
Periksa tampilan penanda perbandingan paket.

Memastikan tiap baris yang berbeda memiliki penanda yang benar:
  - garis tepi berwarna sesuai jenis perbedaannya,
  - label keterangan tampil pada barisnya sendiri di bawah nama fitur,
  - label tidak menempel pada nama fitur.

Cara pakai:
    python tools/periksa_penanda_banding.py
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
  const hasil = [];
  for (const baris of document.querySelectorAll('.banding-fitur')) {
    const nama = baris.querySelector('.banding-nama');
    if (!nama) continue;
    const label = baris.querySelector('.banding-label');
    const s = getComputedStyle(nama);
    const rn = nama.getBoundingClientRect();
    let info = {
      nama: (nama.textContent || '').trim().slice(0, 44),
      kelas: baris.className,
      garis_kiri: s.boxShadow.includes('inset') ? s.boxShadow : 'tidak ada',
      garis_tepi: s.borderLeftWidth + ' ' + s.borderLeftColor,
      ada_label: !!label,
      label_teks: label ? (label.textContent || '').trim() : '',
      label_display: label ? getComputedStyle(label).display : 'x',
      label_lebar: label ? Math.round(label.getBoundingClientRect().width) : 0,
      nama_lebar: Math.round(rn.width)
    };
    // Periksa apakah label berada pada barisnya sendiri di bawah nama.
    if (label) {
      const rl = label.getBoundingClientRect();
      info.label_baris_sendiri = rl.top >= rn.top + 8;
    }
    hasil.push(info);
  }
  return JSON.stringify(hasil);
})()
"""


def main() -> int:
    print("=" * 76)
    print("  PERIKSA PENANDA PERBANDINGAN PAKET")
    print("=" * 76)
    print()

    tampilan = QWebEngineView()
    tampilan.resize(1280, 1000)
    tampilan.show()
    tampilan.load(QUrl.fromLocalFile(str((WEB / "index.html").resolve())))

    tunggu = QEventLoop()
    QTimer.singleShot(20000, tunggu.quit)
    tampilan.loadFinished.connect(lambda _: tunggu.quit())
    tunggu.exec()

    jeda = QEventLoop()
    QTimer.singleShot(1500, jeda.quit)
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
        print("  ! pengukuran tidak menghasilkan apa pun")
        return 1

    daftar = json.loads(hasil["nilai"])

    masalah = []
    eksklusif = beda_nilai = 0
    for d in daftar:
        jenis = "biasa"
        if "banding-fitur-eksklusif" in d["kelas"]:
            jenis = "eksklusif"
            eksklusif += 1
        elif "banding-fitur-beda-nilai" in d["kelas"]:
            jenis = "beda nilai"
            beda_nilai += 1

        tanda = " "
        if jenis == "eksklusif":
            # Harus bergaris biru dan berlabel "Hanya Enterprise".
            if "27, 79, 138" not in d["garis_kiri"]:
                masalah.append(f"{d['nama']}: garis bukan biru")
                tanda = "!"
            if not d["ada_label"] or "Hanya" not in d["label_teks"]:
                masalah.append(f"{d['nama']}: label 'Hanya Enterprise' tidak ada")
                tanda = "!"
            if d["ada_label"] and d["label_display"] != "block":
                masalah.append(f"{d['nama']}: label tidak pada barisnya sendiri")
                tanda = "!"
            if d["ada_label"] and not d.get("label_baris_sendiri"):
                masalah.append(
                    f"{d['nama']}: label menempel pada nama fitur, "
                    f"tidak pada barisnya sendiri")
                tanda = "!"
        elif jenis == "beda nilai":
            # Harus bergaris cokelat dan berlabel "Batasannya berbeda".
            if "192, 138, 62" not in d["garis_kiri"]:
                masalah.append(f"{d['nama']}: garis bukan cokelat")
                tanda = "!"
            if not d["ada_label"] or "Batasannya" not in d["label_teks"]:
                masalah.append(f"{d['nama']}: label 'Batasannya berbeda' tidak ada")
                tanda = "!"
            if d["ada_label"] and d["label_display"] != "block":
                masalah.append(f"{d['nama']}: label tidak pada barisnya sendiri")
                tanda = "!"
            if d["ada_label"] and not d.get("label_baris_sendiri"):
                masalah.append(
                    f"{d['nama']}: label menempel pada nama fitur, "
                    f"tidak pada barisnya sendiri")
                tanda = "!"
        else:
            # Baris biasa tidak boleh punya garis maupun label.
            if d["garis_kiri"] != "tidak ada":
                masalah.append(f"{d['nama']}: baris biasa tapi bergaris")
                tanda = "!"
            if d["ada_label"]:
                masalah.append(f"{d['nama']}: baris biasa tapi berlabel")
                tanda = "!"

        label_info = f" [{d['label_teks']}]" if d["ada_label"] else ""
        print(f"  [{tanda}] {jenis:11s} {d['nama'][:42]:44s}{label_info}")

    print()
    print(f"  eksklusif   : {eksklusif} baris (harus 6)")
    print(f"  beda nilai  : {beda_nilai} baris (harus 4)")
    print(f"  biasa       : {len(daftar) - eksklusif - beda_nilai} baris")
    print()
    print("=" * 76)
    if masalah:
        print(f"  HASIL: {len(masalah)} masalah")
        for m in masalah:
            print(f"    - {m}")
    else:
        print("  HASIL: seluruh penanda BENAR")
    print("=" * 76)
    return 1 if masalah else 0


if __name__ == "__main__":
    sys.exit(main())
