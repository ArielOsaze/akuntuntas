"""
Buka overlay live di peramban, siap dipakai untuk siaran TikTok.

Overlay dirancang pada ukuran 1080x1920 (9:16). Jendela peramban tidak
dapat lebih tinggi daripada layar, jadi Windows akan memangkasnya bila
ukurannya dipaksa. Peluncur ini menyetel isi jendela supaya tepat
1080x1920 dengan penanda khusus Windows, sehingga aplikasi siaran
menerima sumber berukuran penuh: tidak ada pita kosong di kanan kiri dan
gambar tidak perlu diperbesar.

Peramban dipilih karena aplikasi siaran dapat menangkap isi jendelanya
lewat Window capture.

Cara pakai:
    python tools/jalankan_overlay.py            (peramban bawaan)
    python tools/jalankan_overlay.py --chrome   (Chrome, tanpa bilah)
    python tools/jalankan_overlay.py --brave
    python tools/jalankan_overlay.py --info     (panduan siaran)
    python tools/jalankan_overlay.py --ukur     (hanya tampilkan ukuran)
"""
from __future__ import annotations

import ctypes
import shutil
import subprocess
import sys
import webbrowser
from ctypes import wintypes
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
OVERLAY = AKAR / "live_overlay" / "overlay.html"

# Perbandingan rancangan overlay.
LEBAR_RANCANGAN = 1080
TINGGI_RANCANGAN = 1920

# Peramban yang didukung, beserta lokasi pemasangan yang umum.
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
    ada = shutil.which(f"{nama}.exe")
    return ada or None


def ukuran_layar() -> tuple[int, int]:
    """Ukuran layar utama dalam piksel."""
    try:
        user32 = ctypes.windll.user32
        return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
    except Exception:
        return 1920, 1080


def ukuran_jendela() -> tuple[int, int, int]:
    """
    Hitung ukuran jendela awal yang pas untuk layar ini.

    Mengembalikan (lebar, tinggi, tinggi_isi).

    Ukuran ini dipakai saat jendela peramban pertama dibuka. Tingginya
    dibatasi oleh ruang layar yang tersedia sesudah dikurangi taskbar dan
    bilah judul, supaya peramban mau membuka jendela pada ukuran itu.
    Lebarnya lalu dihitung agar perbandingannya tetap 9:16.

    Jendela yang lebih tinggi daripada layar akan dipangkas Windows, dan
    akibatnya overlay terpotong. Karena itu tingginya dihitung dari ruang
    yang benar-benar tersedia, bukan dipaksa 1920.

    Sesudah jendela terbuka, setel_ukuran_penuh() memperbesar isinya
    sampai tepat 1080x1920 dengan penanda SWP_NOSENDCHANGING, sehingga
    batas layar tidak lagi berlaku.
    """
    lebar_layar, tinggi_layar = ukuran_layar()

    # Ruang yang dipakai taskbar dan bilah judul jendela.
    RENTANG_TASKBAR = 56
    RENTANG_JUDUL = 44

    tinggi_isi = tinggi_layar - RENTANG_TASKBAR - RENTANG_JUDUL
    if tinggi_isi < 320:
        tinggi_isi = 320

    lebar_isi = round(tinggi_isi * LEBAR_RANCANGAN / TINGGI_RANCANGAN)

    # Bila layar lebih sempit daripada hasil hitungan, batasi oleh lebar.
    if lebar_isi > lebar_layar - 40:
        lebar_isi = lebar_layar - 40
        tinggi_isi = round(lebar_isi * TINGGI_RANCANGAN / LEBAR_RANCANGAN)

    tinggi_jendela = tinggi_isi + RENTANG_JUDUL
    return lebar_isi, tinggi_jendela, tinggi_isi


def panduan():
    lebar, tinggi, tinggi_isi = ukuran_jendela()
    print("=" * 74)
    print("  PANDUAN SIARAN LIVE TIKTOK - AkunTuntas")
    print("=" * 74)
    print(f"""
  Berkas overlay:
    {OVERLAY}

  Ukuran jendela saat dibuka: {lebar}x{tinggi}
  Isi jendela disetel otomatis ke {LEBAR_RANCANGAN}x{TINGGI_RANCANGAN}

  ----------------------------------------------------------------------
  LANGKAH 1 - Buka overlay
  ----------------------------------------------------------------------
  Jalankan:
      MULAI-OVERLAY.bat

  Atau lewat perintah:
      python tools/jalankan_overlay.py --chrome

  Jendela terbuka tanpa bilah alamat, dan isinya langsung disetel ke
  1080x1920 penuh. Jangan tutup jendela ini selama siaran berlangsung.

  ----------------------------------------------------------------------
  LANGKAH 2 - Siapkan kamera
  ----------------------------------------------------------------------
  Kotak face cam ada di kanan atas, berbentuk 4:3 (400x300), sama seperti
  bentuk gambar yang dikirim kamera USB.

  Cara A (paling pasti, latar langsung berganti):
    Jalankan MULAI-KAMERA.bat. Jendela kamera terbuka dengan latar
    AkunTuntas sudah terpasang. Di TikTok LIVE Studio, tambahkan Window
    capture dan pilih jendela "AkunTuntas - Kamera".

  Cara B (pakai fitur TikTok LIVE Studio):
    Tambahkan sumber Camera, pilih USB Camera, lalu pasang efek
    "Virtual Background (Static/Dynamic)" dan aktifkan Cutout.

  ----------------------------------------------------------------------
  LANGKAH 3 - Tangkap overlay di TikTok LIVE Studio
  ----------------------------------------------------------------------
  1. Buka TikTok LIVE Studio
  2. Pilih scene Portrait (tegak)
  3. Klik Add source, pilih Window capture
  4. Pilih jendela "AkunTuntas - Overlay Live"
  5. Pilih Fit to screen supaya mengisi seluruh kanvas

  PANDUAN TIKTOK LIVE STUDIO LENGKAP:
    live_overlay/PANDUAN-TIKTOK-STUDIO.md

  ----------------------------------------------------------------------
  PINTASAN
  ----------------------------------------------------------------------
    Spasi        mempercepat ke slide berikutnya
    F11          layar penuh di peramban

  ----------------------------------------------------------------------
  MEMERIKSA HASIL
  ----------------------------------------------------------------------
    python tools/setel_jendela_overlay.py --periksa
    python tools/ukur_overlay.py
    python tools/periksa_tutup_kamera.py

  ----------------------------------------------------------------------
  PENGATURAN
  ----------------------------------------------------------------------
  Buka live_overlay/overlay.html untuk mengubah:

    DURASI      lama tiap slide tampil (bawaan 7 detik)
    SLIDE       isi dan urutan slide
    KAKI        teks keunggulan yang bergilir di bawah
    --cam-*     ukuran dan letak kotak face cam
""")





def jalankan_pemantau() -> bool:
    """
    Jalankan pemantau ukuran di latar belakang.

    Windows mengembalikan ukuran jendela ke ukuran layar setiap kali
    jendela dipulihkan dari keadaan diminimalkan. Akibatnya isi jendela
    tidak lagi 9:16, dan aplikasi siaran menyisakan pita kosong di kanan
    kiri sambil memperbesar gambar sehingga tampak pecah.

    Pemantau ini memeriksa ukuran tiap dua detik dan menyetelnya kembali
    bila menyimpang, sehingga masalah itu tidak muncul lagi meski jendela
    di-minimize berkali-kali.
    """
    import subprocess as _sub

    pemantau = AKAR / "tools" / "pantau_overlay.py"
    if not pemantau.exists():
        return False

    # Hentikan SEMUA pemantau lama lebih dahulu. Pencarian dilakukan lewat
    # daftar proses, karena proses pemantau tidak punya jendela sehingga
    # tidak bisa dicari dari judulnya.
    perintah = (
        "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
        "Where-Object { $_.CommandLine -like '*pantau_overlay*' } | "
        "ForEach-Object { Stop-Process -Id $_.ProcessId -Force "
        "-ErrorAction SilentlyContinue }"
    )
    _sub.run(["powershell", "-NoProfile", "-Command", perintah],
             capture_output=True, timeout=60)

    # Beri waktu proses lama benar-benar berhenti dan melepas mutex
    # sebelum yang baru mencoba memegangnya.
    import time as _waktu
    _waktu.sleep(1.5)

    _sub.Popen(
        [sys.executable, str(pemantau), "--jeda", "2"],
        cwd=str(AKAR),
        stdout=_sub.DEVNULL,
        stderr=_sub.DEVNULL,
        creationflags=0x00000008,  # DETACHED_PROCESS
    )
    return True


def tutup_overlay_lama() -> int:
    """
    Tutup jendela overlay yang sudah terbuka.

    Menjalankan peluncur berulang kali akan menumpuk banyak jendela
    overlay. Aplikasi siaran lalu bisa salah memilih jendela yang lama,
    yang ukurannya belum disetel. Karena itu jendela lama ditutup lebih
    dahulu.
    """
    import time

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT,
                                    wintypes.WPARAM, wintypes.LPARAM]
    WM_CLOSE = 0x0010
    JUDUL = "AkunTuntas - Overlay Live"

    ditemukan = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def kunjungi(handle, _):
        if not user32.IsWindowVisible(handle):
            return True
        panjang = user32.GetWindowTextLengthW(handle)
        if panjang == 0:
            return True
        buf = ctypes.create_unicode_buffer(panjang + 1)
        user32.GetWindowTextW(handle, buf, panjang + 1)
        if buf.value.strip() == JUDUL:
            ditemukan.append(handle)
        return True

    user32.EnumWindows(kunjungi, 0)

    if not ditemukan:
        return 0

    print(f"  menutup {len(ditemukan)} jendela overlay yang sudah terbuka")
    for handle in ditemukan:
        user32.PostMessageW(handle, WM_CLOSE, 0, 0)

    time.sleep(2.5)
    return len(ditemukan)


def setel_ukuran_penuh(jeda: float = 4.0) -> bool:
    """
    Setel jendela overlay supaya isinya tepat 1080x1920.

    Windows membatasi ukuran jendela ke ukuran layar, sehingga jendela
    setinggi 1920 dipangkas bila layarnya 1080. Akibatnya isi jendela
    tidak 9:16, dan aplikasi siaran menyisakan pita kosong di kanan kiri
    sambil memperbesar gambar sehingga tampak pecah.

    Batas itu bisa dilewati dengan penanda SWP_NOSENDCHANGING. Sesudah
    disetel, isi jendela tepat 1080x1920 sehingga tidak ada pita kosong
    dan gambar tidak perlu diperbesar.
    """
    import time as _waktu

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.GetWindowRect.argtypes = [wintypes.HWND,
                                     ctypes.POINTER(wintypes.RECT)]
    user32.GetClientRect.argtypes = [wintypes.HWND,
                                     ctypes.POINTER(wintypes.RECT)]
    user32.SetWindowPos.argtypes = [wintypes.HWND,
                                    wintypes.HWND,
                                    ctypes.c_int, ctypes.c_int,
                                    ctypes.c_int, ctypes.c_int,
                                    wintypes.UINT]

    SWP_NOZORDER = 0x0004
    SWP_NOACTIVATE = 0x0010
    SWP_NOSENDCHANGING = 0x0400
    JUDUL = "AkunTuntas - Overlay Live"

    def cari() -> int:
        hasil = []

        @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND,
                            wintypes.LPARAM)
        def kunjungi(handle, _):
            if not user32.IsWindowVisible(handle):
                return True
            panjang = user32.GetWindowTextLengthW(handle)
            if panjang == 0:
                return True
            buf = ctypes.create_unicode_buffer(panjang + 1)
            user32.GetWindowTextW(handle, buf, panjang + 1)
            if JUDUL.lower() in buf.value.lower():
                hasil.append(handle)
            return True

        user32.EnumWindows(kunjungi, 0)
        return hasil[0] if hasil else 0

    # Tunggu jendela muncul.
    handle = 0
    for _ in range(int(jeda * 4)):
        _waktu.sleep(0.25)
        handle = cari()
        if handle:
            break

    if not handle:
        print("  catatan: jendela overlay belum terdeteksi")
        return False

    luar = wintypes.RECT()
    isi = wintypes.RECT()
    user32.GetWindowRect(handle, ctypes.byref(luar))
    user32.GetClientRect(handle, ctypes.byref(isi))

    bingkai_x = (luar.right - luar.left) - isi.right
    bingkai_y = (luar.bottom - luar.top) - isi.bottom

    user32.SetWindowPos(handle, 0, 0, 0,
                        LEBAR_RANCANGAN + bingkai_x,
                        TINGGI_RANCANGAN + bingkai_y,
                        SWP_NOZORDER | SWP_NOACTIVATE
                        | SWP_NOSENDCHANGING)
    _waktu.sleep(1.0)

    user32.GetWindowRect(handle, ctypes.byref(luar))
    user32.GetClientRect(handle, ctypes.byref(isi))
    print(f"  isi jendela: {isi.right}x{isi.bottom}  "
          f"(rasio {isi.right / isi.bottom:.4f}, 9:16 = {9 / 16:.4f})")

    return abs(isi.right / isi.bottom - 9 / 16) < 0.004


def utama() -> int:
    if not OVERLAY.exists():
        print(f"  GAGAL overlay tidak ada: {OVERLAY}")
        return 1

    lebar, tinggi, tinggi_isi = ukuran_jendela()

    if "--info" in sys.argv:
        panduan()
        return 0

    if "--ukur" in sys.argv:
        lebar_layar, tinggi_layar = ukuran_layar()
        print("=" * 74)
        print("  UKURAN JENDELA OVERLAY")
        print("=" * 74)
        print(f"\n  layar            : {lebar_layar}x{tinggi_layar}")
        print(f"  jendela awal     : {lebar}x{tinggi}")
        print(f"  isi jendela awal : {lebar}x{tinggi_isi}")
        print(f"  rasio isi awal   : {lebar / tinggi_isi:.4f} "
              f"(9:16 = {9 / 16:.4f})")
        print()
        print("  Angka di atas adalah ukuran jendela saat baru dibuka.")
        print("  Sesudah terbuka, isi jendela disetel otomatis ke "
              f"{LEBAR_RANCANGAN}x{TINGGI_RANCANGAN}.")
        print()
        print("  Untuk memeriksa ukuran jendela yang sedang terbuka:")
        print("    python tools/setel_jendela_overlay.py --periksa")
        return 0

    nama = ""
    if "--chrome" in sys.argv:
        nama = "chrome"
    elif "--edge" in sys.argv:
        nama = "edge"
    elif "--brave" in sys.argv:
        nama = "brave"

    url = OVERLAY.as_uri()

    if nama:
        exe = cari_peramban(nama)
        if exe:
            # Jendela aplikasi: tanpa bilah alamat dan tanpa bilah perkakas,
            # supaya yang tertangkap siaran hanya isi overlaynya.
            print("=" * 74)
            print("  OVERLAY LIVE AKUNTUNTAS")
            print("=" * 74)
            print(f"\n  peramban  : {nama}")
            print(f"  jendela   : {lebar}x{tinggi}")
            print("  isi jendela akan disetel ke 1080x1920,")
            print("  sehingga di siaran sumber ini pas tanpa diperbesar.")
            print()
            tutup_overlay_lama()
            subprocess.Popen([
                exe,
                "--app=" + url,
                f"--window-size={lebar},{tinggi}",
                "--window-position=0,0",
                "--autoplay-policy=no-user-gesture-required",
            ])
            print("  Jendela overlay dibuka.")
            print("  Menyetel ukuran penuh 1080x1920...")
            if setel_ukuran_penuh():
                print("  Ukuran penuh tercapai: tidak ada pita kosong.")
            if jalankan_pemantau():
                print("  Pemantau ukuran aktif: ukuran dijaga otomatis,")
                print("  termasuk bila jendela di-minimize lalu dibuka lagi.")
            print("  Jangan tutup jendela ini selama siaran.")
            print()
            print("  Panduan: python tools/jalankan_overlay.py --info")
            return 0
        print(f"  {nama} tidak ditemukan, memakai peramban bawaan.")

    webbrowser.open(url)
    print("  Overlay dibuka di peramban bawaan.")
    print("  Jalankan dengan --info untuk panduan siaran lengkap.")
    return 0


if __name__ == "__main__":
    sys.exit(utama())
