"""
Uji tampilan widget: pastikan perubahan desain tidak merusak apa pun.

Memeriksa tiga widget yang paling banyak dipakai di seluruh halaman:
lingkaran skor dalam dua keadaan (belum dinilai dan sudah dinilai),
kartu ringkas KPI, dan tabel kosong.

Cara pakai:
    python tools/uji_tampilan_widget.py
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "src"))

os.environ["LOCALAPPDATA"] = tempfile.mkdtemp(prefix="akuntuntas_widget_")

from PySide6.QtWidgets import QApplication  # noqa: E402

from akuntansi_id.ui import theme, widgets  # noqa: E402


def main() -> int:
    app = QApplication([])
    theme.palet_terang(app)
    app.setStyleSheet(theme.stylesheet())

    lulus = 0
    gagal = 0

    def cek(nama: str, syarat: bool, keterangan: str = ""):
        nonlocal lulus, gagal
        if syarat:
            lulus += 1
            print(f"  [LULUS] {nama}")
        else:
            gagal += 1
            print(f"  [GAGAL] {nama}" + (f" — {keterangan}" if keterangan else ""))

    print("=" * 74)
    print("  UJI TAMPILAN WIDGET")
    print("=" * 74)
    print()

    # ---------------------------------------------------------- gauge
    print("[1. Lingkaran skor]")
    g = widgets.SkorGauge(ukuran=150)
    g.set_skor(0, "Belum Dinilai", belum_dinilai=True)
    g.resize(150, 150)
    kosong = g.grab()
    cek("Keadaan belum dinilai tergambar", not kosong.isNull())
    cek("Keadaan belum dinilai bertanda",
          g.belum_dinilai is True)

    g2 = widgets.SkorGauge(ukuran=150)
    g2.set_skor(85, "Sangat Sehat")
    g2.resize(150, 150)
    bernilai = g2.grab()
    cek("Keadaan bernilai tergambar", not bernilai.isNull())
    cek("Skor tersimpan benar", g2.skor == 85)
    cek("Gambar kedua keadaan berbeda",
          kosong.toImage() != bernilai.toImage())
    print()

    # ------------------------------------------------------ kartu KPI
    print("[2. Kartu ringkas KPI]")
    k = widgets.KpiTile("Omzet", "Rp1.234.567", "Margin 12%",
                        warna=theme.C.SUCCESS, ikon="omzet")
    k.resize(300, 112)
    kartu = k.grab()
    cek("Kartu tergambar", not kartu.isNull())
    cek("Label tersimpan", k.lbl_label.text() == "OMZET")
    cek("Angka tersimpan", k.lbl_value.text() == "Rp1.234.567")
    cek("Keterangan tersimpan", k.lbl_hint.text() == "Margin 12%")

    # Tanpa ikon, kartu harus tetap tergambar.
    k2 = widgets.KpiTile("Laba", "Rp0", "Belum ada")
    k2.resize(300, 112)
    cek("Kartu tanpa ikon tergambar", not k2.grab().isNull())
    print()

    # ---------------------------------------------------------- tabel
    print("[3. Tabel kosong]")
    t = widgets.Tabel([("Tanggal", 110), ("Keterangan", 260), ("Jumlah", 130)])
    t.resize(700, 300)
    t.grab()
    cek("Tabel kosong tergambar", True)
    cek("Tabel menampilkan pesan saat kosong",
          t.rowCount() == 0)
    print()

    # ---------------------------------------------------------- warna
    print("[4. Warna teks memenuhi kontras]")
    # Rasio kontras WCAG AA untuk teks biasa adalah 4,5:1.
    def terang(hex_warna: str) -> float:
        h = hex_warna.lstrip("#")
        r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
        def lin(c):
            return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
        return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)

    def rasio(a: str, b: str) -> float:
        la, lb = terang(a), terang(b)
        gelap, muda = min(la, lb), max(la, lb)
        return (muda + 0.05) / (gelap + 0.05)

    latar = theme.C.SURFACE
    for nama, warna in (
        ("Teks utama", theme.C.TEXT),
        ("Teks sekunder", theme.C.TEXT_MUTED),
        ("Teks samar", theme.C.TEXT_FAINT),
        ("Sukses", theme.C.SUCCESS),
        ("Peringatan", theme.C.WARNING),
        ("Bahaya", theme.C.DANGER),
    ):
        r = rasio(warna, latar)
        cek(f"{nama} kontras di latar putih ({r:.1f}:1)", r >= 4.5,
            f"hanya {r:.1f}:1, minimal 4,5:1")

    # Teks sidebar di atas latar gelap.
    r_sidebar = rasio(theme.C.SIDEBAR_TEXT, theme.C.SIDEBAR_BG)
    cek(f"Teks sidebar kontras ({r_sidebar:.1f}:1)", r_sidebar >= 4.5,
        f"hanya {r_sidebar:.1f}:1")
    r_seksi = rasio(theme.C.SIDEBAR_SECTION, theme.C.SIDEBAR_BG)
    cek(f"Judul kelompok sidebar kontras ({r_seksi:.1f}:1)", r_seksi >= 4.5,
        f"hanya {r_seksi:.1f}:1")

    print()
    print("=" * 74)
    print(f"  HASIL: {lulus} LULUS, {gagal} GAGAL")
    print("=" * 74)
    return 1 if gagal else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(line_buffering=True)
    kode = main()
    sys.stdout.flush()
    os._exit(kode)
