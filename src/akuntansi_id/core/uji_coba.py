"""
AkunTuntas - Mode Uji Coba untuk Peninjau Microsoft Store
=========================================================
Microsoft Store mewajibkan setiap aplikasi dapat diuji oleh peninjau. Karena
AkunTuntas bekerja dengan kunci lisensi berbayar, peninjau tidak akan bisa
melewati layar aktivasi dan aplikasi akan ditolak.

Modul ini menyediakan lisensi sementara yang hanya berlaku di dalam paket
MSIX. Tiga hal yang menjaganya agar tidak bocor ke versi yang dijual:

1. Penanda di berkas `uji_coba.txt` harus ada di dalam folder aplikasi.
   Berkas itu hanya disertakan saat membungkus paket MSIX, tidak pernah
   ikut pada build installer biasa.

2. Masa berlaku dihitung sejak aplikasi pertama kali dijalankan dan
   disimpan di folder data. Setelah 60 hari, mode uji coba berhenti dengan
   sendirinya. Peninjau Microsoft selalu menguji dalam hitungan hari,
   sehingga batas ini cukup longgar untuk mereka tetapi tidak untuk
   pemakaian jangka panjang.

3. Lisensi yang dihasilkan diberi paket Enterprise supaya seluruh halaman
   dapat diperiksa peninjau. Isinya tidak menyentuh server lisensi dan tidak
   pernah ditulis ke berkas lisensi pengguna, jadi aktivasi sungguhan tidak
   terpengaruh.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

# Nama berkas penanda. Keberadaannya menentukan mode uji coba boleh dipakai.
PENANDA = "uji_coba.txt"

# Berapa lama mode uji coba berlaku sejak pertama kali dijalankan.
HARI_UJI_COBA = 60

# Nama berkas catatan waktu mulai, disimpan di folder data pengguna.
CATATAN = "uji_coba_mulai.json"


def _folder_penanda() -> list[Path]:
    """
    Kumpulkan tempat yang mungkin memuat berkas penanda.

    Aplikasi dibundel PyInstaller dalam mode satu folder, sehingga berkas
    data berada di dalam `_internal`. Berkas penanda sengaja diletakkan di
    akar paket MSIX, bukan di `_internal`, karena isi `_internal` dibangun
    ulang setiap kali aplikasi dibungkus sedangkan penanda harus ditambahkan
    setelahnya. Karena itu kedua tempat diperiksa.

    Saat dijalankan dari kode sumber, akar proyek juga diperiksa supaya mode
    uji coba dapat dicoba tanpa membungkus paket.
    """
    import sys

    tempat = []

    dasar = getattr(sys, "_MEIPASS", None)
    if dasar:
        dasar_path = Path(dasar)
        # _internal tempat PyInstaller meletakkan berkas data
        tempat.append(dasar_path)
        # akar paket MSIX, satu tingkat di atas _internal
        tempat.append(dasar_path.parent)

    # folder berkas modul ini: .../akuntansi_id/core/
    tempat.append(Path(__file__).resolve().parent.parent.parent.parent)
    tempat.append(Path(__file__).resolve().parent)
    return tempat


def penanda_ada() -> bool:
    """Apakah paket ini memang paket uji coba untuk peninjau Store."""
    for folder in _folder_penanda():
        try:
            if (folder / PENANDA).exists():
                return True
        except Exception:
            continue
    return False


def _catatan_path(data_dir: Path) -> Path:
    return Path(data_dir) / CATATAN


def _mulai_dihitung(data_dir: Path) -> dt.date | None:
    """
    Baca tanggal mulai uji coba, atau catat hari ini bila belum ada.

    Tanggal dicatat pada pemakaian pertama, bukan pada saat pembungkusan,
    supaya masa berlaku tidak terbuang selama paket menunggu diunggah.
    """
    jalur = _catatan_path(data_dir)
    hari_ini = dt.date.today()

    try:
        if jalur.exists():
            isi = json.loads(jalur.read_text(encoding="utf-8"))
            teks = isi.get("mulai")
            if teks:
                return dt.date.fromisoformat(teks)
    except Exception:
        pass

    try:
        jalur.parent.mkdir(parents=True, exist_ok=True)
        jalur.write_text(
            json.dumps({"mulai": hari_ini.isoformat()}, indent=2),
            encoding="utf-8")
    except Exception:
        # Bila folder data tidak dapat ditulis, uji coba tetap dianggap
        # mulai hari ini supaya peninjau tidak terhalang.
        pass
    return hari_ini


def sisa_hari(data_dir: Path) -> int:
    """Sisa hari masa uji coba. Angka negatif berarti sudah lewat."""
    mulai = _mulai_dihitung(data_dir)
    if mulai is None:
        return HARI_UJI_COBA
    lewat = (dt.date.today() - mulai).days
    return HARI_UJI_COBA - lewat


def aktif(data_dir: Path) -> bool:
    """Apakah mode uji coba sedang berlaku."""
    if not penanda_ada():
        return False
    return sisa_hari(data_dir) > 0


def lisensi_uji_coba(data_dir: Path):
    """
    Bentuk objek lisensi sementara untuk peninjau.

    Dipakai oleh alur pembuka aplikasi supaya halaman masuk langsung
    ditampilkan tanpa melewati layar aktivasi. Objek ini tidak disimpan ke
    berkas dan tidak menghubungi server.
    """
    from . import license as LIS

    sisa = max(sisa_hari(data_dir), 1)
    batas = dt.datetime.now() + dt.timedelta(days=sisa)
    return LIS.Lisensi(
        kunci="UJI-COBA-STORE",
        paket="enterprise",
        pemilik="Peninjau Microsoft Store",
        berlaku_sampai=batas.timestamp(),
        fitur={
            "konsolidasi": True,
            "dimensi": True,
            "pajak_lanjutan": True,
            "audit_lanjutan": True,
            "multi_entitas": True,
        },
    )


def keterangan() -> str:
    """Kalimat singkat untuk ditampilkan di dalam aplikasi."""
    return (f"Mode uji coba untuk peninjau Microsoft Store. "
            f"Berlaku {HARI_UJI_COBA} hari sejak aplikasi pertama dibuka.")
