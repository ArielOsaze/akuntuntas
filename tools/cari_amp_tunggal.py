"""
Cari teks Qt yang memakai satu tanda & tunggal pada tempat yang salah.

Qt memperlakukan tanda & sebagai penanda pintasan papan tikus pada QAction
dan QMenu: satu tanda & akan dihapus dari tampilan. Pada QLabel, QPushButton,
QCheckBox, QRadioButton, QGroupBox, dan tab, tanda & tampil apa adanya.
Perilaku ini sudah diuji dengan piksel oleh tools/uji_perilaku_amp.py.

Karena itu aturannya berbeda menurut jenis widget:

1. Teks yang dikirim lewat pembantu aksi() di main_window.py tidak perlu
   diubah: pembantu itu sendiri sudah menggandakan setiap tanda &.
   Menulis && di sana justru membuat tampilan memunculkan && ganda.

2. Teks yang langsung masuk ke QAction() atau QMenu() wajib memakai &&
   bila memang ingin menampilkan satu tanda &.

3. Teks pada QLabel, tombol, kotak centang, dan tab dibiarkan apa adanya.

Cara pakai:
    python tools/cari_amp_tunggal.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
SUMBER = AKAR / "src" / "akuntansi_id"

# Pembantu yang sudah menggandakan tanda & sendiri.
SUDAH_DI_ESCAPE = ("aksi(",)

# Pemanggilan yang teksnya langsung dipakai Qt tanpa penggandaan.
LANGSUNG = ("QAction(", "addMenu(", "QMenu(")

# Jenis widget yang tanda & nya tampil apa adanya, tidak perlu diperiksa.
AMAN = ("QLabel(", "QPushButton(", "QCheckBox(", "QRadioButton(",
        "QGroupBox(", "addTab(", "setTabText(", "setText(", "setToolTip(")

POLA_TEKS = re.compile(r'"([^"\\]*(?:\\.[^"\\]*)*)"')

# Tanda & yang sah: "&&" (tanda & harfiah) atau "&X" (penanda pintasan).
POLA_SAH = re.compile(r"&&|&[A-Za-z0-9]")


def ada_amp_tunggal(teks: str) -> bool:
    """Benar bila teks memuat tanda & yang akan hilang saat ditampilkan."""
    return "&" in POLA_SAH.sub("", teks)


def main() -> int:
    if not SUMBER.exists():
        print(f"  folder sumber tidak ditemukan: {SUMBER}")
        return 2

    salah = []          # teks langsung ke QAction/QMenu tanpa &&
    ganda_salah = []    # teks lewat aksi() tetapi sudah memakai &&
    berkas_diperiksa = 0

    for f in sorted(SUMBER.rglob("*.py")):
        if "__pycache__" in str(f):
            continue
        berkas_diperiksa += 1
        relatif = f.relative_to(AKAR)

        for i, baris in enumerate(
                f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            lewat_aksi = any(k in baris for k in SUDAH_DI_ESCAPE)
            lewat_langsung = any(k in baris for k in LANGSUNG)

            if not (lewat_aksi or lewat_langsung):
                continue

            for m in POLA_TEKS.finditer(baris):
                teks = m.group(1)
                if not teks.strip():
                    continue

                # Baris berisi penggantian tanda & itu sendiri, bukan teks
                # yang ditampilkan: itu kode pengaman, bukan temuan.
                if ".replace(" in baris and teks in ("&", "&&"):
                    continue

                if lewat_aksi and "&&" in teks:
                    # aksi() menggandakan lagi, sehingga && tampil sebagai &&
                    ganda_salah.append((relatif, i, teks))
                elif lewat_langsung and not lewat_aksi and ada_amp_tunggal(teks):
                    salah.append((relatif, i, teks))

    print("=" * 74)
    print("  CARI TANDA & YANG SALAH PADA TEKS Qt")
    print("=" * 74)
    print()
    print(f"  berkas diperiksa: {berkas_diperiksa}")
    print()

    jumlah = len(salah) + len(ganda_salah)

    if not jumlah:
        print("  TIDAK ADA teks dengan tanda & yang salah.")
        print("=" * 74)
        return 0

    if salah:
        print(f"  {len(salah)} teks langsung ke QAction/QMenu perlu memakai &&:")
        print()
        for f, i, teks in salah:
            print(f"    {f}:{i}")
            print(f"      \"{teks}\"")
        print()

    if ganda_salah:
        print(f"  {len(ganda_salah)} teks lewat aksi() tidak boleh memakai &&:")
        print()
        for f, i, teks in ganda_salah:
            print(f"    {f}:{i}")
            print(f"      \"{teks}\"")
        print()

    print("=" * 74)
    return 1


if __name__ == "__main__":
    sys.exit(main())
