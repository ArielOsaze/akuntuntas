"""
AkunTuntas - Mode Uji Coba untuk Peninjau Microsoft Store
=========================================================
Microsoft Store mewajibkan setiap aplikasi dapat diuji oleh peninjau. Karena
AkunTuntas bekerja dengan kunci lisensi berbayar, peninjau tidak akan bisa
melewati layar aktivasi dan aplikasi akan ditolak.

Mode uji coba memberi lisensi sementara. Tiga hal menjaganya supaya tidak
dapat dipakai untuk memakai aplikasi secara gratis:

1. Aplikasi harus benar-benar berjalan di dalam paket MSIX yang dipasang
   Windows. Keadaan itu ditanyakan kepada Windows sendiri, bukan disimpulkan
   dari keberadaan berkas. Menaruh berkas penanda di folder aplikasi biasa,
   atau di folder mana pun yang dapat ditulis pengguna, tidak berpengaruh.

2. Penanda harus memuat keterangan bertanda tangan kunci privat server.
   Berkas kosong, atau berkas yang disunting untuk memperpanjang masa
   berlakunya, langsung ditolak karena tanda tangannya tidak lagi cocok.
   Kunci privatnya tidak ada di dalam aplikasi, sehingga penanda tidak dapat
   dibuat sendiri.

3. Masa berlaku ditentukan di dalam penanda bertanda tangan itu, bukan
   dihitung dari catatan di komputer pengguna. Menghapus atau menyunting
   berkas apa pun di komputer tidak memperpanjang masa uji coba.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Nama berkas penanda. Isinya keterangan bertanda tangan dari server.
PENANDA = "uji_coba.txt"

# Nama paket yang berhak memakai mode uji coba. Harus sama dengan nama paket
# pada msix/identitas.json.
NAMA_PAKET = "XinetGroup.AkunTuntas"

# Berapa lama masa uji coba bila penanda tidak menyebutkan batasnya sendiri.
# Dipakai hanya sebagai cadangan, karena penanda terbitan server selalu
# memuat batas waktunya.
HARI_UJI_COBA = 60

# Dipakai alat uji untuk meniru keadaan di dalam paket MSIX tanpa benar-benar
# membungkus paket. Nilai None berarti keadaan sebenarnya yang ditanyakan
# kepada Windows.
_paksa_dalam_paket: bool | None = None


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
# PENANDA BERTANDA TANGAN
# ==========================================================================
def _tempat_penanda() -> list[Path]:
    """
    Tempat yang mungkin memuat berkas penanda.

    Aplikasi dibundel PyInstaller dalam mode satu folder, sehingga berkas
    data berada di dalam `_internal`. Berkas penanda sengaja diletakkan di
    akar paket MSIX, bukan di dalam `_internal`, karena isi `_internal`
    dibangun ulang setiap kali aplikasi dibungkus sedangkan penanda
    ditambahkan setelahnya. Karena itu kedua tempat diperiksa.
    """
    tempat = []

    dasar = getattr(sys, "_MEIPASS", None)
    if dasar:
        tempat.append(Path(dasar))
        tempat.append(Path(dasar).parent)

    tempat.append(Path(__file__).resolve().parent.parent.parent.parent)
    tempat.append(Path(__file__).resolve().parent)
    return tempat


def _path_penanda() -> Path | None:
    """Berkas penanda yang ditemukan, atau None bila tidak ada."""
    for folder in _tempat_penanda():
        try:
            berkas = folder / PENANDA
            if berkas.exists():
                return berkas
        except Exception:
            continue
    return None


def baca_penanda() -> dict | None:
    """
    Baca keterangan bertanda tangan dari berkas penanda.

    Mengembalikan None bila berkasnya tidak ada, tidak dapat dibaca, atau
    isinya bukan keterangan yang lengkap.
    """
    berkas = _path_penanda()
    if berkas is None:
        return None

    try:
        isi = json.loads(berkas.read_text(encoding="utf-8"))
    except Exception:
        return None

    if not isinstance(isi, dict):
        return None
    if not isi.get("muatan") or not isi.get("tanda"):
        return None
    return isi


def penanda_sah() -> tuple[bool, str]:
    """
    Apakah penanda ada dan tanda tangannya sah.

    Mengembalikan (sah, alasan). Berkas kosong, berkas yang disunting, dan
    berkas yang dibuat sendiri tanpa kunci privat server semuanya ditolak.
    """
    isi = baca_penanda()
    if isi is None:
        return False, "Berkas penanda uji coba tidak ada atau tidak lengkap."

    from . import license as LIS

    if not LIS.tanda_sah(isi["muatan"], isi["tanda"]):
        return False, ("Berkas penanda uji coba tidak sah. Berkas ini mungkin "
                       "sudah diubah, atau bukan berasal dari Xinet Group.")

    try:
        muatan = json.loads(isi["muatan"])
    except Exception:
        return False, "Isi penanda uji coba tidak dapat dibaca."

    if not muatan.get("uji_coba"):
        return False, "Berkas penanda bukan untuk mode uji coba."

    return True, ""


def sisa_hari() -> int:
    """
    Sisa hari masa uji coba menurut penanda bertanda tangan.

    Angka negatif berarti masa uji coba sudah lewat. Batas waktu dibaca dari
    penanda, bukan dari catatan di komputer pengguna, sehingga menghapus
    berkas apa pun tidak memperpanjang masa uji coba.
    """
    isi = baca_penanda()
    if isi is None:
        return 0

    try:
        muatan = json.loads(isi["muatan"])
    except Exception:
        return 0

    from . import license as LIS

    batas = LIS.waktu_dari_iso(muatan.get("berlaku_sampai"))
    if not batas:
        return HARI_UJI_COBA

    import time
    return int((batas - time.time()) // 86400)


def penanda_ada() -> bool:
    """Apakah paket ini memuat penanda uji coba yang sah dan belum lewat."""
    sah, _ = penanda_sah()
    if not sah:
        return False
    return sisa_hari() > 0


def aktif() -> bool:
    """
    Apakah mode uji coba sedang berlaku.

    Dua syarat harus terpenuhi: aplikasi berjalan di dalam paket MSIX yang
    benar, dan penanda bertanda tangannya sah serta belum lewat masa
    berlakunya. Tanpa syarat pertama, menyalin berkas penanda ke hasil
    pemasangan installer biasa tidak membuka apa pun.
    """
    if not dalam_paket_msix():
        return False
    return penanda_ada()


def lisensi_uji_coba():
    """
    Bentuk objek lisensi sementara untuk peninjau.

    Dipakai oleh alur pembuka aplikasi supaya halaman masuk langsung
    ditampilkan tanpa melewati layar aktivasi. Objek ini tidak disimpan ke
    berkas dan tidak menghubungi server.
    """
    from . import license as LIS

    isi = baca_penanda()
    muatan = {}
    if isi is not None:
        try:
            muatan = json.loads(isi["muatan"])
        except Exception:
            muatan = {}

    batas = LIS.waktu_dari_iso(muatan.get("berlaku_sampai"))
    if not batas:
        import datetime as dt
        batas = (dt.datetime.now()
                 + dt.timedelta(days=HARI_UJI_COBA)).timestamp()

    return LIS.Lisensi(
        kunci="UJI-COBA-STORE",
        paket="enterprise",
        pemilik="Peninjau Microsoft Store",
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
    """Kalimat singkat untuk ditampilkan di dalam aplikasi."""
    return (f"Mode uji coba untuk peninjau Microsoft Store. "
            f"Sisa {max(sisa_hari(), 0)} hari.")
