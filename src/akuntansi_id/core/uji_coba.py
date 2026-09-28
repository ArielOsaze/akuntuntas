"""
AkunTuntas - Masa Uji Coba
==========================
Microsoft Store mewajibkan setiap aplikasi dapat diuji oleh peninjau. Karena
AkunTuntas bekerja dengan kunci lisensi berbayar, peninjau tidak akan bisa
melewati layar aktivasi dan aplikasi akan ditolak. Masa uji coba menjawab
kebutuhan itu tanpa membuka jalan memakai aplikasi secara gratis.

RANCANGAN LAMA DAN KENAPA DITINGGALKAN
======================================
Sebelumnya masa uji coba ditentukan oleh berkas penanda bertanda tangan
yang ikut dibungkus ke dalam paket MSIX, berlaku 60 hari. Rancangan itu
salah besar: paket yang diuji peninjau adalah paket yang SAMA dengan yang
diunduh semua orang dari Microsoft Store. Akibatnya setiap orang yang
memasang dari Store langsung mendapat lisensi Enterprise penuh tanpa
membayar, sampai masa berlakunya habis. Berkas penanda tidak lagi
disertakan ke dalam paket.

RANCANGAN SEKARANG
==================
Masa uji coba dihitung sejak aplikasi PERTAMA KALI DIBUKA di komputer
pengguna, selama HARI_UJI_COBA hari. Waktu mulai dicatat di tiga tempat
sekaligus, dan yang dipakai adalah catatan PALING AWAL:

1. Tabel `settings` di basis data aplikasi.
2. Berkas `trial.dat` di folder data aplikasi.
3. Kunci registry milik aplikasi di HKCU.

Menghapus satu tempat tidak mengembalikan masa uji coba, karena waktunya
dipulihkan dari tempat lain. Menghapus ketiganya sama dengan memasang ulang
aplikasi, dan itu pun tetap hanya memberi satu masa uji coba.

JAM YANG DIMUNDURKAN
====================
Selain waktu mulai, dicatat juga waktu terjauh yang pernah terlihat. Bila
jam komputer dimundurkan, patokan yang dipakai adalah catatan terjauh itu,
bukan jam sekarang, sehingga masa uji coba tidak bertambah. Bila jam
dimajukan, masa uji coba justru langsung habis, dan itu tetap aman karena
hanya merugikan orang yang mencoba mengakalinya.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

# Nama paket yang berhak memakai masa uji coba. Harus sama dengan nama paket
# pada msix/identitas.json. Di luar paket ini, masa uji coba tidak berlaku:
# pemasangan lewat installer dari situs memang sudah memerlukan kunci
# lisensi untuk mengunduh, jadi tidak perlu masa uji coba.
NAMA_PAKET = "XinetGroup.AkunTuntas"

# Lama masa uji coba dalam hari.
HARI_UJI_COBA = 1

# Berkas dan kunci tempat waktu mulai dicatat.
NAMA_BERKAS = "trial.dat"
KUNCI_DB_MULAI = "trial_mulai"
KUNCI_DB_PUNCAK = "trial_puncak"
JALUR_REGISTRY = r"Software\XinetGroup\AkunTuntas"

# Dipakai alat uji untuk meniru keadaan di dalam paket MSIX tanpa benar-benar
# membungkus paket. Nilai None berarti keadaan sebenarnya yang ditanyakan
# kepada Windows.
_paksa_dalam_paket: bool | None = None

# Dipakai alat uji untuk memakai folder data sementara.
_paksa_data_dir: Path | None = None

# Dipakai alat uji untuk memakai kunci registry lain, supaya menjalankan
# alat uji tidak mengubah catatan masa uji coba di komputer yang dipakai
# menguji. Nilai None berarti kunci registry yang sebenarnya.
_paksa_jalur_registry: str | None = None


# ==========================================================================
# APAKAH APLIKASI BERJALAN DI DALAM PAKET MSIX
# ==========================================================================
def nama_keluarga_paket() -> str:
    """
    Nama keluarga paket bila proses ini berjalan di dalam paket MSIX.

    Windows menyediakan keterangan ini lewat GetCurrentPackageFullName.
    Pertanyaan itu hanya terjawab bila prosesnya benar-benar dijalankan
    Windows sebagai aplikasi terpaket, sehingga jawabannya tidak dapat ditiru
    dengan menaruh berkas di folder tertentu.

    Mengembalikan teks kosong bila aplikasi dijalankan dari luar paket,
    misalnya dari hasil pemasangan installer biasa.
    """
    if sys.platform != "win32":
        return ""

    try:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        fungsi = kernel32.GetCurrentPackageFullName
        fungsi.argtypes = [ctypes.POINTER(wintypes.UINT), wintypes.LPWSTR]
        fungsi.restype = wintypes.LONG

        panjang = wintypes.UINT(0)
        # Panggilan pertama hanya untuk mengetahui panjang namanya.
        fungsi(ctypes.byref(panjang), None)
        if panjang.value == 0 or panjang.value > 8192:
            return ""

        penyangga = ctypes.create_unicode_buffer(panjang.value)
        if fungsi(ctypes.byref(panjang), penyangga) != 0:
            return ""
        return penyangga.value
    except Exception:
        return ""


def dalam_paket_msix() -> bool:
    """Apakah aplikasi berjalan dari paket MSIX yang benar."""
    if _paksa_dalam_paket is not None:
        return _paksa_dalam_paket

    nama = nama_keluarga_paket()
    if not nama:
        return False
    return nama.startswith(NAMA_PAKET)


# ==========================================================================
# TEMPAT PENCATATAN
# ==========================================================================
def _folder_data() -> Path:
    """Folder data aplikasi tempat berkas catatan disimpan."""
    if _paksa_data_dir is not None:
        return Path(_paksa_data_dir)

    from .. import config
    return Path(config.DATA_DIR)


def _baca_berkas() -> tuple[float, float] | None:
    """Waktu mulai dan puncak dari berkas catatan."""
    try:
        berkas = _folder_data() / NAMA_BERKAS
        if not berkas.exists():
            return None
        isi = json.loads(berkas.read_text(encoding="utf-8"))
        mulai = float(isi["mulai"])
        puncak = float(isi.get("puncak", mulai))
        return mulai, puncak
    except Exception:
        return None


def _tulis_berkas(mulai: float, puncak: float) -> None:
    """Simpan waktu mulai dan puncak ke berkas catatan."""
    try:
        folder = _folder_data()
        folder.mkdir(parents=True, exist_ok=True)
        berkas = folder / NAMA_BERKAS
        berkas.write_text(json.dumps({
            "mulai": mulai,
            "puncak": puncak,
        }), encoding="utf-8")
    except Exception:
        # Pencatatan gagal bukan alasan menghentikan aplikasi. Dua tempat
        # lain masih mencatat hal yang sama.
        pass


def _baca_db() -> tuple[float, float] | None:
    """Waktu mulai dan puncak dari tabel settings."""
    try:
        from .. import db

        baris_mulai = db.q1("SELECT value FROM settings WHERE key=?",
                            (KUNCI_DB_MULAI,))
        if baris_mulai is None:
            return None
        mulai = float(baris_mulai["value"])

        baris_puncak = db.q1("SELECT value FROM settings WHERE key=?",
                             (KUNCI_DB_PUNCAK,))
        puncak = float(baris_puncak["value"]) if baris_puncak else mulai
        return mulai, puncak
    except Exception:
        return None


def _tulis_db(mulai: float, puncak: float) -> None:
    """Simpan waktu mulai dan puncak ke tabel settings."""
    try:
        from .. import db

        for kunci, nilai in ((KUNCI_DB_MULAI, mulai), (KUNCI_DB_PUNCAK, puncak)):
            db.ex("INSERT INTO settings(key, value) VALUES(?, ?) "
                  "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                  (kunci, repr(nilai)))
    except Exception:
        pass


def _baca_registry() -> tuple[float, float] | None:
    """Waktu mulai dan puncak dari registry Windows."""
    if sys.platform != "win32":
        return None
    try:
        import winreg

        jalur = _paksa_jalur_registry or JALUR_REGISTRY
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, jalur) as kunci:
            mulai = float(winreg.QueryValueEx(kunci, "TrialMulai")[0])
            try:
                puncak = float(winreg.QueryValueEx(kunci, "TrialPuncak")[0])
            except FileNotFoundError:
                puncak = mulai
        return mulai, puncak
    except Exception:
        return None


def _tulis_registry(mulai: float, puncak: float) -> None:
    """Simpan waktu mulai dan puncak ke registry Windows."""
    if sys.platform != "win32":
        return
    try:
        import winreg

        jalur = _paksa_jalur_registry or JALUR_REGISTRY
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, jalur) as kunci:
            winreg.SetValueEx(kunci, "TrialMulai", 0, winreg.REG_SZ,
                              repr(mulai))
            winreg.SetValueEx(kunci, "TrialPuncak", 0, winreg.REG_SZ,
                              repr(puncak))
    except Exception:
        pass


def _baca_semua() -> tuple[float, float] | None:
    """
    Gabungkan catatan dari ketiga tempat.

    Waktu mulai diambil dari catatan PALING AWAL, supaya menghapus salah satu
    tempat tidak memundurkan awal masa uji coba. Waktu puncak diambil dari
    catatan PALING AKHIR, supaya memundurkan jam tidak memperpanjangnya.
    """
    catatan = [c for c in (_baca_berkas(), _baca_db(), _baca_registry())
               if c is not None]
    if not catatan:
        return None

    mulai = min(c[0] for c in catatan)
    puncak = max(c[1] for c in catatan)
    return mulai, puncak


def _simpan_semua(mulai: float, puncak: float) -> None:
    """Simpan waktu mulai dan puncak ke ketiga tempat sekaligus."""
    _tulis_berkas(mulai, puncak)
    _tulis_db(mulai, puncak)
    _tulis_registry(mulai, puncak)


# ==========================================================================
# PERHITUNGAN MASA UJI COBA
# ==========================================================================
def mulai_uji_coba() -> float:
    """
    Waktu mulai masa uji coba, dicatat pada pemakaian pertama.

    Bila catatan sudah ada, nilainya dipulihkan ke tempat yang belum memuat
    catatan, sehingga menghapus salah satu tempat tidak berpengaruh.
    """
    sekarang = time.time()
    catatan = _baca_semua()

    if catatan is None:
        _simpan_semua(sekarang, sekarang)
        return sekarang

    mulai, puncak = catatan
    # Jam mundur tidak boleh membuat puncak ikut mundur.
    puncak_baru = max(puncak, sekarang)
    if puncak_baru != puncak:
        _simpan_semua(mulai, puncak_baru)
    else:
        # Pastikan ketiga tempat memuat catatan yang sama.
        _simpan_semua(mulai, puncak)
    return mulai


def sisa_detik() -> float:
    """
    Sisa masa uji coba dalam detik.

    Angka nol atau negatif berarti masa uji coba sudah habis. Patokan waktu
    yang dipakai adalah yang paling jauh antara jam sekarang dan catatan
    terjauh, sehingga memundurkan jam komputer tidak memperpanjangnya.
    """
    mulai = mulai_uji_coba()
    catatan = _baca_semua()
    puncak = catatan[1] if catatan else mulai

    patokan = max(time.time(), puncak)
    batas = mulai + HARI_UJI_COBA * 86400
    return batas - patokan


def sisa_jam() -> int:
    """Sisa masa uji coba dalam jam, dibulatkan ke atas."""
    sisa = sisa_detik()
    if sisa <= 0:
        return 0
    return int((sisa + 3599) // 3600)


def aktif() -> bool:
    """
    Apakah masa uji coba sedang berlaku.

    Masa uji coba hanya berlaku di dalam paket MSIX yang benar. Pemasangan
    lewat installer dari situs tidak mendapat masa uji coba, karena unduhan
    itu sendiri sudah memerlukan kunci lisensi.
    """
    if not dalam_paket_msix():
        return False
    return sisa_detik() > 0


def kadaluarsa() -> bool:
    """Apakah masa uji coba sudah habis di dalam paket MSIX."""
    if not dalam_paket_msix():
        return False
    return sisa_detik() <= 0


def sudah_mulai() -> bool:
    """Apakah masa uji coba pernah dimulai di komputer ini."""
    return _baca_semua() is not None


def lisensi_uji_coba():
    """
    Bentuk objek lisensi sementara selama masa uji coba.

    Objek ini tidak disimpan ke berkas dan tidak menghubungi server. Seluruh
    fitur paket Enterprise dibuka supaya pengguna dapat menilai aplikasi
    sepenuhnya selama masa uji coba.
    """
    from . import license as LIS

    mulai = mulai_uji_coba()
    batas = mulai + HARI_UJI_COBA * 86400

    return LIS.Lisensi(
        kunci="UJI-COBA",
        paket="enterprise",
        pemilik="Masa uji coba",
        berlaku_sampai=batas,
        tenggang_sampai=batas,
        fitur={
            "konsolidasi": True,
            "dimensi": True,
            "pajak_lanjutan": True,
            "audit_lanjutan": True,
            "multi_entitas": True,
            "multi_cabang": True,
            "payroll_lanjutan": True,
        },
    )


def keterangan() -> str:
    """Kalimat singkat tentang sisa masa uji coba, untuk ditampilkan."""
    jam = sisa_jam()
    if jam <= 0:
        return "Masa uji coba sudah berakhir."
    if jam <= 1:
        return "Masa uji coba tersisa kurang dari 1 jam."
    return f"Masa uji coba tersisa {jam} jam."


def pesan_kadaluarsa() -> str:
    """Keterangan yang ditampilkan setelah masa uji coba berakhir."""
    return (
        "Masa uji coba 1 hari sudah berakhir.\n\n"
        "Untuk terus memakai AkunTuntas, aktifkan lisensi Anda. "
        "Lisensi dibeli sekali dan berlaku selamanya, tanpa biaya bulanan.\n\n"
        "Beli lisensi di akuntuntas.xinet.id/beli, lalu masukkan kunci "
        "lisensi yang Anda terima di layar ini."
    )


def bersihkan_catatan() -> None:
    """
    Hapus seluruh catatan masa uji coba.

    Dipakai alat uji saja. Tidak dipanggil oleh aplikasi, karena menghapus
    catatan di tengah pemakaian sama dengan memberi masa uji coba baru.
    """
    try:
        berkas = _folder_data() / NAMA_BERKAS
        if berkas.exists():
            berkas.unlink()
    except Exception:
        pass

    try:
        from .. import db

        for kunci in (KUNCI_DB_MULAI, KUNCI_DB_PUNCAK):
            db.ex("DELETE FROM settings WHERE key=?", (kunci,))
    except Exception:
        pass

    if sys.platform == "win32":
        try:
            import winreg

            jalur = _paksa_jalur_registry or JALUR_REGISTRY
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, jalur, 0,
                                winreg.KEY_SET_VALUE) as kunci:
                for nama in ("TrialMulai", "TrialPuncak"):
                    try:
                        winreg.DeleteValue(kunci, nama)
                    except FileNotFoundError:
                        pass
        except Exception:
            pass
