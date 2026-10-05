"""
Jendela kamera dengan latar AkunTuntas, siap ditangkap aplikasi siaran.

Cara ini menyelesaikan dua hal sekaligus:

  1. Bentuk gambar tetap benar. Kamera USB sering mengirim gambar 4:3
     sedangkan kotak face cam berbentuk 16:9. Bila gambar 4:3 dipaksa
     mengisi kotak 16:9, sisi atas dan bawahnya terpotong sehingga wajah
     terlihat diperbesar. Di sini gambar dipotong dengan takaran yang
     benar, dan hasilnya sudah berukuran 16:9 sejak awal.

  2. Latar belakang pasti berganti. Orang dipisahkan dari latar memakai
     model yang berjalan di komputer, jadi tidak bergantung pada fitur
     atau unduhan dari layanan lain.

Jendela ini lalu ditangkap dengan Window capture di aplikasi siaran dan
diletakkan tepat di kotak face cam overlay.

Cara pakai:
    python tools/jendela_kamera.py
    python tools/jendela_kamera.py --virtual   (kirim ke kamera virtual)
    python tools/jendela_kamera.py --virtual --index 0  (pilih kamera sumber)
    python tools/jendela_kamera.py --latar live_overlay/gambar/latar-akuntuntas.png
    python tools/jendela_kamera.py --ukuran 640x360
    python tools/jendela_kamera.py --tanpa-latar
    python tools/jendela_kamera.py --cek
    python tools/jendela_kamera.py --potret    (simpan 3 gambar lalu berhenti)

Mode --virtual:
    Gambar tidak ditampilkan di jendela, melainkan dikirim ke kamera
    virtual. Aplikasi siaran lalu memakai sumber Camera seperti biasa dan
    memilih kamera virtual itu. Hasilnya: sumber kamera asli dari aplikasi
    siaran, tetapi gambarnya sudah berlatar AkunTuntas, tanpa perlu
    Window capture.
"""
from __future__ import annotations

import ctypes
import sys
import time
from ctypes import wintypes
from pathlib import Path

import cv2
import numpy as np

AKAR = Path(__file__).resolve().parent.parent
LATAR_BAWAAN = AKAR / "live_overlay" / "gambar" / "latar-akuntuntas.png"

JUDUL = "AkunTuntas - Kamera"
# Bentuk 4:3, sama seperti kotak face cam di overlay dan sama seperti
# gambar yang dikirim kamera USB. Dengan begitu gambar tidak dipotong
# dan wajah tidak terlihat diperbesar.
LEBAR_BAWAAN = 480
TINGGI_BAWAAN = 360
FPS = 30

user32 = ctypes.WinDLL("user32", use_last_error=True)
user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND,
                                ctypes.c_int, ctypes.c_int,
                                ctypes.c_int, ctypes.c_int, wintypes.UINT]
user32.SetWindowPos.restype = wintypes.BOOL
user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
user32.GetWindowLongW.restype = wintypes.LONG
user32.SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int,
                                  wintypes.LONG]
user32.SetWindowLongW.restype = wintypes.LONG

GWL_STYLE = -16
WS_CAPTION = 0x00C00000
WS_THICKFRAME = 0x00040000
WS_MINIMIZEBOX = 0x00020000
WS_MAXIMIZEBOX = 0x00010000
SWP_FRAMECHANGED = 0x0020
SWP_NOMOVE = 0x0002
SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010


def cari_jendela(judul: str) -> int:
    hasil: list[int] = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def kunjungi(handle, _):
        if not user32.IsWindowVisible(handle):
            return True
        panjang = user32.GetWindowTextLengthW(handle)
        if panjang == 0:
            return True
        buf = ctypes.create_unicode_buffer(panjang + 1)
        user32.GetWindowTextW(handle, buf, panjang + 1)
        if judul.lower() in buf.value.lower():
            hasil.append(handle)
        return True

    user32.EnumWindows(kunjungi, 0)
    return hasil[0] if hasil else 0


def hilangkan_bingkai(judul: str) -> bool:
    """
    Hilangkan bilah judul jendela kamera.

    Dengan begitu yang tertangkap aplikasi siaran hanya gambarnya saja,
    tanpa bilah judul yang ikut terlihat.
    """
    handle = cari_jendela(judul)
    if not handle:
        return False

    gaya = user32.GetWindowLongW(handle, GWL_STYLE)
    gaya &= ~(WS_CAPTION | WS_THICKFRAME | WS_MINIMIZEBOX | WS_MAXIMIZEBOX)
    user32.SetWindowLongW(handle, GWL_STYLE, gaya)
    user32.SetWindowPos(handle, 0, 0, 0, 0, 0,
                        SWP_FRAMECHANGED | SWP_NOMOVE
                        | SWP_NOZORDER | SWP_NOACTIVATE)
    return True


def potong_ke_bentuk(gambar: np.ndarray, lebar: int,
                     tinggi: int) -> np.ndarray:
    """
    Sesuaikan gambar ke bentuk kotak tanpa membuat wajah gepeng.

    Gambar dipotong di sisi yang berlebih, bukan diregangkan. Cara ini
    menjaga bentuk wajah tetap wajar.
    """
    h, w = gambar.shape[:2]
    rasio_sasaran = lebar / tinggi
    rasio_gambar = w / h

    if abs(rasio_gambar - rasio_sasaran) < 0.01:
        return cv2.resize(gambar, (lebar, tinggi))

    if rasio_gambar > rasio_sasaran:
        # Gambar lebih lebar: potong sisi kiri dan kanan.
        lebar_baru = int(h * rasio_sasaran)
        mulai = (w - lebar_baru) // 2
        potong = gambar[:, mulai:mulai + lebar_baru]
    else:
        # Gambar lebih tegak: potong sisi atas dan bawah.
        tinggi_baru = int(w / rasio_sasaran)
        mulai = (h - tinggi_baru) // 2
        potong = gambar[mulai:mulai + tinggi_baru, :]

    return cv2.resize(potong, (lebar, tinggi))


MODEL = AKAR / "model" / "selfie_segmenter.tflite"


def siapkan_pemisah():
    """
    Siapkan alat pemisah orang dari latar.

    Versi mediapipe terbaru memakai cara ini. Modelnya disimpan di folder
    model dan dibaca dari sana, jadi tidak perlu unduh ulang tiap kali.
    """
    import mediapipe as mp

    if not MODEL.exists():
        print(f"  GAGAL model tidak ada: {MODEL}")
        print("  Unduh dari:")
        print("    https://storage.googleapis.com/mediapipe-models/"
              "image_segmenter/selfie_segmenter/float16/1/"
              "selfie_segmenter.tflite")
        return None

    dasar = mp.tasks.BaseOptions(model_asset_path=str(MODEL))
    pilihan = mp.tasks.vision.ImageSegmenterOptions(
        base_options=dasar,
        running_mode=mp.tasks.vision.RunningMode.IMAGE,
        output_confidence_masks=True,
    )
    return mp.tasks.vision.ImageSegmenter.create_from_options(pilihan)


def pisahkan_orang(pemisah, gambar):
    """
    Hasilkan topeng yang menandai bagian gambar milik orang.

    Nilai 1 berarti orang, nilai 0 berarti latar belakang.
    """
    import mediapipe as mp

    rgb = cv2.cvtColor(gambar, cv2.COLOR_BGR2RGB)
    gambar_mp = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    hasil = pemisah.segment(gambar_mp)

    # Ambil topeng pertama, yaitu bagian orang.
    topeng = hasil.confidence_masks[0].numpy_view()

    # Sesuaikan ukuran topeng dengan gambar.
    if topeng.shape[:2] != gambar.shape[:2]:
        topeng = cv2.resize(topeng, (gambar.shape[1], gambar.shape[0]))

    return topeng


def cek() -> int:
    print("=== KESIAPAN ===")

    kurang = []
    for modul, keterangan in (("cv2", "membaca kamera"),
                              ("mediapipe", "memisahkan orang dari latar"),
                              ("numpy", "mengolah gambar")):
        try:
            __import__(modul)
            print(f"  {modul:12}: ADA  ({keterangan})")
        except ImportError:
            print(f"  {modul:12}: belum ada  ({keterangan})")
            kurang.append(modul)

    if kurang:
        print()
        print(f"  Pasang dengan: python -m pip install {' '.join(kurang)}")
        return 1

    print()
    print("=== GAMBAR LATAR ===")
    if LATAR_BAWAAN.exists():
        from PIL import Image
        im = Image.open(LATAR_BAWAAN)
        print(f"  {LATAR_BAWAAN.name}: {im.width}x{im.height}")
    else:
        print(f"  BELUM ADA: {LATAR_BAWAAN}")
        print("  Buat dengan: python tools/buat_latar_kamera.py")
        return 1

    print()
    print("=== KAMERA ===")
    kamera = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not kamera.isOpened():
        kamera = cv2.VideoCapture(0)
    if not kamera.isOpened():
        print("  kamera tidak bisa dibuka")
        return 1

    berhasil, gambar = kamera.read()
    if berhasil:
        h, w = gambar.shape[:2]
        print(f"  gambar asli: {w}x{h}  (rasio {w / h:.4f})")
    kamera.release()

    print()
    print("  Semua siap. Jalankan tanpa --cek untuk memulai.")
    return 0



def jalankan_virtual(lebar: int, tinggi: int, latar, pemisah,
                     nama_kamera: int = 0) -> int:
    """
    Kirim gambar ke kamera virtual.

    Aplikasi siaran memakai sumber Camera seperti biasa dan memilih
    kamera virtual ini. Dengan begitu tidak perlu Window capture, dan
    sumbernya tetap kamera asli dari sisi aplikasi siaran.
    """
    try:
        import pyvirtualcam
    except ImportError:
        print("  GAGAL pyvirtualcam belum terpasang")
        print("  Pasang dengan:")
        print("    python -m pip install pyvirtualcam")
        return 1

    # ---- Buka kamera asli ----
    kamera = cv2.VideoCapture(nama_kamera, cv2.CAP_DSHOW)
    if not kamera.isOpened():
        kamera = cv2.VideoCapture(nama_kamera)
    if not kamera.isOpened():
        print(f"  GAGAL kamera {nama_kamera} tidak bisa dibuka")
        return 1

    kamera.set(cv2.CAP_PROP_FRAME_WIDTH, 1024)
    kamera.set(cv2.CAP_PROP_FRAME_HEIGHT, 768)
    kamera.set(cv2.CAP_PROP_FPS, FPS)

    lebar_kamera = int(kamera.get(cv2.CAP_PROP_FRAME_WIDTH))
    tinggi_kamera = int(kamera.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"  kamera asli   : index {nama_kamera}  "
          f"{lebar_kamera}x{tinggi_kamera}")

    print(f"  latar         : {'dipakai' if latar is not None else 'tidak'}")

    # ---- Buka kamera virtual ----
    print("  membuka kamera virtual...")
    try:
        kamera_virtual = pyvirtualcam.Camera(
            width=lebar, height=tinggi, fps=FPS, print_fps=False)
    except Exception as e:
        print(f"  GAGAL membuka kamera virtual: {e}")
        print()
        print("  Pastikan kamera virtual sudah terdaftar:")
        print("    python tools/cek_semua_kamera.py")
        kamera.release()
        return 1

    print(f"  kamera virtual: {kamera_virtual.device}")
    print(f"  ukuran kirim  : {lebar}x{tinggi}")

    print()
    print("=" * 68)
    print("  KAMERA VIRTUAL AKTIF")
    print("=" * 68)
    print()
    print("  DI TIKTOK LIVE STUDIO:")
    print("    1. Add source, pilih Camera")
    print("    2. Pada daftar perangkat, pilih:")
    print(f"         {kamera_virtual.device}")
    print("    3. Letakkan tepat menutupi kotak face cam:")
    print("       X=646  Y=40  lebar=400  tinggi=300")
    print()
    print("  Tidak perlu Window capture. Sumbernya kamera asli.")
    print()
    print("  Catatan: pilih kameranya BERDASARKAN NAMA, bukan nomor.")
    print("  Kamera virtual ini terdaftar di Windows dengan nama itu.")
    print()
    print("  Tekan Ctrl+C untuk berhenti.")
    print("=" * 68)
    print()

    jumlah = 0
    mulai = time.time()

    try:
        while True:
            berhasil, gambar = kamera.read()
            if not berhasil:
                print("  gambar tidak terbaca, berhenti")
                break

            gambar = cv2.flip(gambar, 1)
            gambar = potong_ke_bentuk(gambar, lebar, tinggi)

            if pemisah is not None:
                topeng = pisahkan_orang(pemisah, gambar)
                topeng = cv2.GaussianBlur(topeng, (9, 9), 0)
                topeng = np.clip((topeng - 0.35) / 0.3, 0, 1)
                topeng = cv2.merge([topeng, topeng, topeng])
                tampil = (gambar * topeng
                          + latar * (1 - topeng)).astype(np.uint8)
            else:
                tampil = gambar

            # Kirim ke kamera virtual. pyvirtualcam memakai RGB.
            kamera_virtual.send(cv2.cvtColor(tampil, cv2.COLOR_BGR2RGB))
            kamera_virtual.sleep_until_next_frame()

            jumlah += 1
            if jumlah % 150 == 0:
                detik = time.time() - mulai
                print(f"  {jumlah} gambar terkirim "
                      f"({jumlah / detik:.1f} per detik)")

    except KeyboardInterrupt:
        print()
        print("  dihentikan")
    finally:
        kamera.release()
        kamera_virtual.close()
        if pemisah is not None:
            pemisah.close()

    return 0


def utama() -> int:
    if "--cek" in sys.argv:
        return cek()

    mode_virtual = "--virtual" in sys.argv

    # ---- Ukuran jendela ----
    lebar, tinggi = LEBAR_BAWAAN, TINGGI_BAWAAN
    if "--ukuran" in sys.argv:
        nilai = sys.argv[sys.argv.index("--ukuran") + 1]
        try:
            lebar, tinggi = (int(x) for x in nilai.lower().split("x"))
        except ValueError:
            print(f"  ukuran tidak sah: {nilai}. Contoh: 640x360")
            return 1

    # ---- Gambar latar ----
    berkas_latar = LATAR_BAWAAN
    if "--latar" in sys.argv:
        berkas_latar = Path(sys.argv[sys.argv.index("--latar") + 1])
        if not berkas_latar.is_absolute():
            berkas_latar = AKAR / berkas_latar

    pakai_latar = "--tanpa-latar" not in sys.argv

    if pakai_latar:
        if not berkas_latar.exists():
            print(f"  GAGAL gambar latar tidak ada: {berkas_latar}")
            print("  Buat dengan: python tools/buat_latar_kamera.py")
            return 1
        latar = cv2.imread(str(berkas_latar))
        if latar is None:
            print(f"  GAGAL gambar latar tidak bisa dibaca: {berkas_latar}")
            return 1
        latar = cv2.resize(latar, (lebar, tinggi))
        print(f"  latar: {berkas_latar.name}")

    # ---- Buka kamera ----
    kamera = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not kamera.isOpened():
        kamera = cv2.VideoCapture(0)
    if not kamera.isOpened():
        print("  GAGAL kamera tidak bisa dibuka")
        return 1

    # Minta resolusi 4:3 yang paling besar supaya gambar tajam dan
    # bentuknya sama dengan kotak face cam.
    kamera.set(cv2.CAP_PROP_FRAME_WIDTH, 1024)
    kamera.set(cv2.CAP_PROP_FRAME_HEIGHT, 768)
    kamera.set(cv2.CAP_PROP_FPS, FPS)

    lebar_kamera = int(kamera.get(cv2.CAP_PROP_FRAME_WIDTH))
    tinggi_kamera = int(kamera.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"  kamera: {lebar_kamera}x{tinggi_kamera}")

    # ---- Siapkan pemisah orang dari latar ----
    pemisah = None
    if pakai_latar:
        pemisah = siapkan_pemisah()

    # ---- Nomor kamera sumber ----
    index_kamera = 0
    if "--index" in sys.argv:
        try:
            index_kamera = int(sys.argv[sys.argv.index("--index") + 1])
        except (ValueError, IndexError):
            print("  nomor index tidak sah, memakai 0")

    # ---- Mode kamera virtual ----
    if mode_virtual:
        # Ukuran kirim dibuat 4:3 supaya cocok dengan kotak face cam.
        lebar_kirim, tinggi_kirim = lebar, tinggi
        if (lebar, tinggi) == (LEBAR_BAWAAN, TINGGI_BAWAAN):
            lebar_kirim, tinggi_kirim = 1024, 768

        if pakai_latar:
            latar = cv2.resize(latar, (lebar_kirim, tinggi_kirim))
        else:
            latar = None

        return jalankan_virtual(lebar_kirim, tinggi_kirim, latar,
                                pemisah, index_kamera)

    # ---- Jendela ----
    cv2.namedWindow(JUDUL, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(JUDUL, lebar, tinggi)
    cv2.moveWindow(JUDUL, 40, 40)
    time.sleep(1.2)
    hilangkan_bingkai(JUDUL)

    print()
    print("=" * 66)
    print("  JENDELA KAMERA AKUNTUNTAS")
    print("=" * 66)
    print()
    print(f"  Ukuran jendela : {lebar}x{tinggi}")
    print("  Tekan Q atau Esc pada jendela untuk berhenti.")
    print()
    print("  DI TIKTOK LIVE STUDIO:")
    print("    1. Add source, pilih Window capture")
    print(f"    2. Pilih jendela \"{JUDUL}\"")
    print("    3. Letakkan tepat menutupi kotak face cam:")
    print("       X=646  Y=40  lebar=400  tinggi=300")
    print()
    print("  Panduan lengkap: live_overlay/PANDUAN-TIKTOK-STUDIO.md")
    print("=" * 66)
    print()

    # Mode potret: simpan beberapa gambar lalu berhenti sendiri. Berguna
    # untuk memeriksa hasil tanpa harus melihat jendelanya.
    mode_potret = "--potret" in sys.argv
    batas_potret = 3 if mode_potret else 0
    jumlah_potret = 0

    jumlah = 0
    mulai = time.time()

    try:
        while True:
            berhasil, gambar = kamera.read()
            if not berhasil:
                print("  gambar tidak terbaca")
                break

            # Cermin, seperti cermin biasa.
            gambar = cv2.flip(gambar, 1)

            # Potong ke bentuk jendela tanpa membuat wajah gepeng.
            gambar = potong_ke_bentuk(gambar, lebar, tinggi)

            if pemisah is not None:
                topeng = pisahkan_orang(pemisah, gambar)

                # Perhalus tepi topeng supaya tidak bergerigi.
                topeng = cv2.GaussianBlur(topeng, (9, 9), 0)
                topeng = np.clip((topeng - 0.35) / 0.3, 0, 1)
                topeng = cv2.merge([topeng, topeng, topeng])

                tampil = (gambar * topeng
                          + latar * (1 - topeng)).astype(np.uint8)
            else:
                tampil = gambar

            cv2.imshow(JUDUL, tampil)

            if mode_potret and jumlah > 20:
                jumlah_potret += 1
                berkas = AKAR / f"_kamera_hasil_{jumlah_potret}.png"
                cv2.imwrite(str(berkas), tampil)
                print(f"  potret {jumlah_potret}: {berkas.name}")
                if jumlah_potret >= batas_potret:
                    break

            jumlah += 1
            if jumlah % 150 == 0:
                detik = time.time() - mulai
                print(f"  {jumlah} gambar, {jumlah / detik:.1f} per detik")

            tombol = cv2.waitKey(1) & 0xFF
            if tombol in (ord("q"), 27):
                break

    except KeyboardInterrupt:
        print()
        print("  dihentikan")
    finally:
        kamera.release()
        cv2.destroyAllWindows()
        if pemisah is not None:
            pemisah.close()

    return 0


if __name__ == "__main__":
    sys.exit(utama())
