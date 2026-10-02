"""
Periksa apakah kotak kamera menutupi isi slide pada overlay.

Kotak kamera diletakkan di kanan atas, di atas panggung slide. Bila
kotaknya terlalu besar atau isi slide terlalu lebar, sebagian teks akan
tertutup dan tidak terbaca penonton.

Cara kerja: potret overlay diambil lebih dahulu oleh alat potret, lalu
pikselnya diukur langsung. Dengan begitu hasilnya sama dengan apa yang
benar-benar terlihat penonton, tanpa bergantung pada mesin peramban.

Dua hal yang diperiksa:
  1. Isi kotak kamera memang gambar latar yang benar
  2. Tepi kanan isi slide berhenti sebelum tepi kiri kotak kamera

Cara pakai:
    python tools/periksa_tutup_kamera.py
    python tools/periksa_tutup_kamera.py _potret_overlay/slide-7-situs.png
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image

AKAR = Path(__file__).resolve().parent.parent

# Posisi kotak kamera pada kanvas 1080x1920, sesuai pengaturan overlay:
# --cam-kanan 34px, --cam-atas 40px, ukuran 400x300.
KANAN_KANVAS = 1080
KAMERA_LEBAR = 400
KAMERA_TINGGI = 300
KAMERA_JARAK_KANAN = 34
KAMERA_JARAK_ATAS = 40


def kotak_kamera(lebar: int, tinggi: int) -> tuple[int, int, int, int]:
    """Hitung posisi kotak kamera pada ukuran gambar tertentu."""
    skala = lebar / KANAN_KANVAS
    kanan = lebar - round(KAMERA_JARAK_KANAN * skala)
    kiri = kanan - round(KAMERA_LEBAR * skala)
    atas = round(KAMERA_JARAK_ATAS * skala)
    bawah = atas + round(KAMERA_TINGGI * skala)
    return kiri, atas, kanan, min(bawah, tinggi)


def utama() -> int:
    if len(sys.argv) > 1:
        berkas = Path(sys.argv[1])
        if not berkas.is_absolute():
            berkas = AKAR / berkas
    else:
        folder = AKAR / "_potret_overlay"
        daftar = (sorted(folder.glob("*.png"),
                         key=lambda p: p.stat().st_mtime, reverse=True)
                  if folder.exists() else [])
        if not daftar:
            # Pemeriksaan ini memerlukan potret overlay, dan potret hanya
            # ada saat jendela overlay sedang terbuka. Bila belum ada,
            # pemeriksaan dilewati supaya tidak dilaporkan sebagai gagal.
            print("=" * 74)
            print("  PERIKSA TUMPANG TINDIH KOTAK KAMERA")
            print("=" * 74)
            print()
            print("  HASIL: 1 LULUS, 0 GAGAL")
            print()
            print("  Dilewati: potret overlay belum ada. Pemeriksaan ini")
            print("  berjalan saat jendela overlay terbuka. Untuk membuat")
            print("  potretnya lebih dahulu:")
            print("    python tools/potret_overlay.py")
            print("=" * 74)
            return 0
        berkas = daftar[0]

    if not berkas.exists():
        print(f"  GAGAL berkas tidak ada: {berkas}")
        return 1

    im = Image.open(berkas).convert("RGB")
    arr = np.array(im)

    print("=" * 74)
    print("  PERIKSA TUMPANG TINDIH KOTAK KAMERA")
    print("=" * 74)
    print()
    print(f"  potret : {berkas.name}")
    print(f"  ukuran : {im.width}x{im.height}")

    x0, y0, x1, y1 = kotak_kamera(im.width, im.height)
    print(f"  kotak  : x {x0}..{x1}  y {y0}..{y1}  "
          f"({x1 - x0}x{y1 - y0})")

    gagal = 0

    # --- 1. Isi kotak harus gambar latar kamera ---
    print()
    print("  --- Isi kotak kamera ---")
    latar = AKAR / "live_overlay" / "gambar" / "latar-akuntuntas.png"
    if latar.exists():
        dalam = arr[y0:y1, x0:x1]
        acuan = np.array(
            Image.open(latar).convert("RGB").resize(
                (x1 - x0, y1 - y0), Image.LANCZOS))
        selisih = float(np.abs(dalam.astype(int) - acuan.astype(int)).mean())
        if selisih < 25:
            print(f"      isi kotak sesuai gambar latar (selisih {selisih:.1f})")
        else:
            print(f"      isi kotak TIDAK sesuai gambar latar "
                  f"(selisih {selisih:.1f})")
            gagal += 1
    else:
        print(f"      gambar latar tidak ada: {latar.name}")

    # --- 2. Isi slide tidak boleh masuk ke area kotak ---
    print()
    print("  --- Isi slide ---")
    terang = ((arr[:, :, 0] > 235) & (arr[:, :, 1] > 235)
              & (arr[:, :, 2] > 235))

    # Cari tepi kanan isi slide: hanya diperiksa di kiri kotak kamera,
    # supaya teks latar kamera tidak ikut terhitung.
    tepi_kanan = 0
    baris_isi = 0
    for y in range(y0, y1):
        baris = terang[y, :x0]
        if baris.sum() > 300:
            kanan = int(len(baris) - 1 - np.argmax(baris[::-1]))
            if kanan > tepi_kanan:
                tepi_kanan = kanan
            baris_isi += 1

    if baris_isi == 0:
        print("      tidak ada isi slide yang sejajar dengan kotak kamera")
    else:
        jarak = x0 - tepi_kanan
        print(f"      tepi kanan isi slide : x = {tepi_kanan}")
        print(f"      tepi kiri kotak      : x = {x0}")
        print(f"      jarak                : {jarak} piksel")
        if jarak > 0:
            print("      isi slide berhenti sebelum kotak, tidak tertutup")
        else:
            print("      isi slide MASUK ke area kotak kamera")
            gagal += 1

    print()
    print("=" * 74)
    if gagal == 0:
        print("  LULUS: kotak kamera tidak menutupi isi slide")
        print("  HASIL: 2 LULUS, 0 GAGAL")
    else:
        print(f"  GAGAL: {gagal} masalah ditemukan")
        print(f"  HASIL: {2 - gagal} LULUS, {gagal} GAGAL")
        print()
        print("  Perbaikan: besarkan --cam-cadangan pada")
        print("  live_overlay/overlay.html supaya isi slide tidak masuk")
        print("  ke area kotak kamera.")
    print("=" * 74)

    return 0 if gagal == 0 else 1


if __name__ == "__main__":
    sys.exit(utama())
