"""
Buka overlay live di peramban, siap dipakai untuk siaran TikTok.

Overlay dibuka di peramban dengan ukuran jendela 9:16. Peramban dipilih
karena dapat langsung ditangkap oleh aplikasi siaran (TikTok LIVE Studio,
OBS) lewat jendela atau tangkapan layar.

Cara pakai:
    python tools/jalankan_overlay.py            (peramban bawaan)
    python tools/jalankan_overlay.py --chrome   (Chrome, tanpa bilah)
    python tools/jalankan_overlay.py --info     (hanya tampilkan panduan)
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
OVERLAY = AKAR / "live_overlay" / "overlay.html"

# Peramban yang didukung, beserta cara membuka jendela tanpa bilah alamat.
# Jendela tanpa bilah diperlukan supaya yang tertangkap siaran hanya
# overlaynya, bukan perkakas peramban.
PERAMBAN = {
    "chrome": [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ],
    "edge": [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ],
    "brave": [
        r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
    ],
}


def cari_peramban(nama: str) -> str | None:
    """Cari berkas peramban pada lokasi pemasangan yang umum."""
    for jalur in PERAMBAN.get(nama, []):
        if Path(jalur).exists():
            return jalur
    # Coba lewat PATH sistem.
    for nama_exe in (f"{nama}.exe",):
        ada = shutil.which(nama_exe)
        if ada:
            return ada
    return None


def panduan():
    print("=" * 74)
    print("  PANDUAN SIARAN LIVE TIKTOK - AkunTuntas")
    print("=" * 74)
    print(f"""
  Berkas overlay:
    {OVERLAY}

  ----------------------------------------------------------------------
  LANGKAH 1 - Buka overlay
  ----------------------------------------------------------------------
  Jalankan:
      python tools/jalankan_overlay.py --chrome

  Jendela akan terbuka dengan ukuran 9:16 (1080x1920) tanpa bilah alamat.
  Bila layar Anda lebih pendek dari 1920, jendela akan menyesuaikan diri.

  ----------------------------------------------------------------------
  LANGKAH 2 - Siapkan kamera
  ----------------------------------------------------------------------
  Kotak face cam ada di kanan atas. Isinya dapat diisi dua cara:

  Cara A (paling mudah):
    Biarkan kotak itu sebagai penanda, lalu di aplikasi siaran
    (TikTok LIVE Studio / OBS), letakkan sumber kamera Anda tepat
    menutupi kotak tersebut. Atur posisi dan ukurannya sekali, lalu simpan.

  Cara B:
    Buka overlay di peramban Chrome atau Edge, lalu izinkan akses kamera
    saat diminta. Kamera akan tampil sendiri di dalam kotak.

  ----------------------------------------------------------------------
  LANGKAH 3 - Tangkap overlay di aplikasi siaran
  ----------------------------------------------------------------------
  Di TikTok LIVE Studio atau OBS, tambahkan sumber:

    - "Window Capture" lalu pilih jendela peramban overlay, atau
    - "Display Capture" bila ingin menangkap seluruh layar.

  Lalu tambahkan sumber kamera dan letakkan menutupi kotak face cam.

  ----------------------------------------------------------------------
  PINTASAN
  ----------------------------------------------------------------------
    Spasi        mempercepat ke slide berikutnya
    F11          layar penuh di peramban

  ----------------------------------------------------------------------
  PENGATURAN
  ----------------------------------------------------------------------
  Buka live_overlay/overlay.html untuk mengubah:

    DURASI      lama tiap slide tampil (bawaan 7 detik)
    SLIDE       isi dan urutan slide
    KAKI        teks keunggulan yang bergilir di bawah
    --cam-*     ukuran dan letak kotak face cam
""")


def utama() -> int:
    if not OVERLAY.exists():
        print(f"  GAGAL overlay tidak ada: {OVERLAY}")
        return 1

    if "--info" in sys.argv:
        panduan()
        return 0

    nama = "chrome" if "--chrome" in sys.argv else ""
    if "--edge" in sys.argv:
        nama = "edge"
    if "--brave" in sys.argv:
        nama = "brave"

    url = OVERLAY.as_uri()

    if nama:
        exe = cari_peramban(nama)
        if exe:
            # Jendela aplikasi: tanpa bilah alamat dan tanpa bilah perkakas,
            # supaya yang tertangkap siaran hanya isi overlaynya.
            print(f"  Membuka {nama}: {exe}")
            subprocess.Popen([
                exe,
                "--app=" + url,
                "--window-size=1080,1900",
                "--window-position=0,0",
                "--autoplay-policy=no-user-gesture-required",
            ])
            print("  Jendela overlay dibuka.")
            print("  Tekan F11 bila ingin layar penuh.")
            return 0
        print(f"  {nama} tidak ditemukan, memakai peramban bawaan.")

    webbrowser.open(url)
    print("  Overlay dibuka di peramban bawaan.")
    print("  Jalankan dengan --info untuk panduan siaran lengkap.")
    return 0


if __name__ == "__main__":
    sys.exit(utama())
