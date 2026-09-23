"""
AkunTuntas - Laporan Bug
========================

Mengumpulkan keterangan teknis saat terjadi kesalahan, lalu menyiapkannya
untuk dikirim ke pengembang.

Cara kirimnya memakai aplikasi email bawaan pengguna (lewat tautan mailto).
Cara ini dipilih karena aplikasi ini tidak menyimpan password email siapa
pun: menyimpan password di berkas program berarti membuka jalan bagi orang
lain untuk memakainya. Dengan mailto, email dikirim dari akun pengguna
sendiri dan isi laporannya sudah terisi otomatis.

Berkas laporan juga disimpan di folder data aplikasi supaya pengguna dapat
melampirkannya secara manual bila aplikasi emailnya tidak terbuka.
"""
from __future__ import annotations

import json
import platform
import sys
import traceback
import urllib.parse
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Optional

from . import config

EMAIL_PENGEMBANG = "akuntuntas@gmail.com"

# Batas panjang isi email: sebagian aplikasi email memotong tautan yang
# terlalu panjang, jadi jejak teknis dipangkas lebih dulu.
BATAS_JEJAK = 1400


def folder_laporan() -> Path:
    """Folder tempat berkas laporan disimpan."""
    p = config.DATA_DIR / "laporan_bug"
    try:
        p.mkdir(parents=True, exist_ok=True)
    except OSError:
        p = config.DATA_DIR
    return p


def ringkas_sistem() -> dict:
    """Keterangan singkat tentang komputer dan aplikasi yang dipakai."""
    return {
        "aplikasi": config.APP_NAME,
        "versi": config.APP_VERSION,
        "sistem": f"{platform.system()} {platform.release()}",
        "arsitektur": platform.machine(),
        "python": platform.python_version(),
    }


def jejak_terakhir(baris: int = 60) -> str:
    """Potongan akhir berkas log aplikasi, untuk melihat kejadian sebelumnya."""
    try:
        berkas = config.DATA_DIR / "akuntuntas.log"
        if not berkas.exists():
            return ""
        isi = berkas.read_text(encoding="utf-8", errors="replace").splitlines()
        return "\n".join(isi[-baris:])
    except Exception:
        return ""


def susun_laporan(kesalahan: str = "", jejak: str = "",
                  catatan_pengguna: str = "", langkah: str = "") -> dict:
    """
    Susun isi laporan dari keterangan yang tersedia.

    Mengembalikan dict berisi keterangan sistem, jejak teknis, dan teks
    lengkap laporan yang siap dikirim.
    """
    sistem = ringkas_sistem()
    jejak = (jejak or "")[:BATAS_JEJAK]

    bagian = [
        "LAPORAN MASALAH AKUNTUNTAS",
        "=" * 40,
        "",
        "Keterangan sistem:",
    ]
    for k, v in sistem.items():
        bagian.append(f"  {k:12s}: {v}")
    bagian.append(f"  waktu       : {datetime.now():%Y-%m-%d %H:%M:%S}")
    bagian.append("")

    if langkah.strip():
        bagian += ["Yang saya lakukan sebelum masalah muncul:",
                   langkah.strip(), ""]
    if catatan_pengguna.strip():
        bagian += ["Keterangan tambahan:", catatan_pengguna.strip(), ""]
    if kesalahan.strip():
        bagian += ["Pesan kesalahan:", kesalahan.strip(), ""]
    if jejak.strip():
        bagian += ["Jejak teknis (potongan log terakhir):", jejak.strip(), ""]

    bagian += [
        "-" * 40,
        "Laporan ini dibuat otomatis oleh AkunTuntas.",
        "Mohon jelaskan langkah yang Anda lakukan agar masalah dapat ditelusuri.",
    ]

    teks = "\n".join(bagian)
    return {
        "sistem": sistem,
        "kesalahan": kesalahan.strip(),
        "jejak": jejak,
        "teks": teks,
    }


def simpan_laporan(teks: str, label: str = "") -> Optional[Path]:
    """Simpan laporan ke berkas agar bisa dilampirkan secara manual."""
    try:
        cap = datetime.now().strftime("%Y%m%d_%H%M%S")
        nama = f"laporan_{label + '_' if label else ''}{cap}.txt"
        berkas = folder_laporan() / nama
        berkas.write_text(teks, encoding="utf-8")
        return berkas
    except Exception:
        return None


def tautan_email(teks: str, judul: str = "") -> str:
    """Tautan mailto berisi laporan yang sudah terisi."""
    if not judul:
        judul = f"Laporan masalah AkunTuntas {config.APP_VERSION}"
    return ("mailto:" + EMAIL_PENGEMBANG
            + "?subject=" + urllib.parse.quote(judul)
            + "&body=" + urllib.parse.quote(teks))


def buka_email(teks: str, judul: str = "") -> bool:
    """
    Buka aplikasi email pengguna dengan laporan yang sudah terisi.

    Mengembalikan True bila perintah pembukaan berhasil dijalankan. Berhasil
    di sini berarti aplikasi email mencoba dibuka; pengiriman emailnya tetap
    dilakukan pengguna sendiri.
    """
    try:
        return webbrowser.open(tautan_email(teks, judul))
    except Exception:
        return False


def laporan_dari_pengecualian(tipe, nilai, tb) -> str:
    """Susun laporan dari kesalahan yang tidak tertangani."""
    jejak_penuh = "".join(traceback.format_exception(tipe, nilai, tb))
    return susun_laporan(
        kesalahan=f"{tipe.__name__}: {nilai}",
        jejak=jejak_penuh[-BATAS_JEJAK:])["teks"]


def kumpulkan_berkas() -> list:
    """Daftar berkas laporan yang pernah disimpan."""
    try:
        return sorted(folder_laporan().glob("laporan_*.txt"),
                      key=lambda p: p.stat().st_mtime, reverse=True)
    except Exception:
        return []


def simpan_metadata(kesalahan: str, berkas: Optional[Path]) -> None:
    """
    Catat ringkasan kesalahan ke berkas JSON.

    Berguna untuk memeriksa kesalahan yang paling sering muncul tanpa harus
    membaca seluruh berkas laporan.
    """
    try:
        p = folder_laporan() / "riwayat_kesalahan.json"
        riwayat = []
        if p.exists():
            try:
                riwayat = json.loads(p.read_text(encoding="utf-8"))
            except (ValueError, OSError):
                riwayat = []
        riwayat.append({
            "waktu": datetime.now().isoformat(timespec="seconds"),
            "kesalahan": kesalahan[:300],
            "berkas": str(berkas) if berkas else "",
            "versi": config.APP_VERSION,
        })
        p.write_text(json.dumps(riwayat[-200:], indent=2, ensure_ascii=False),
                     encoding="utf-8")
    except Exception:
        pass


if __name__ == "__main__":
    contoh = susun_laporan(
        kesalahan="AttributeError: contoh kesalahan",
        jejak="baris log terakhir",
        catatan_pengguna="Halaman kontrak tidak terbuka.",
        langkah="Membuka menu Kontrak lalu menekan tombol Kontrak Baru.")
    print(contoh["teks"])
    print()
    print("tautan email:", tautan_email(contoh["teks"])[:120] + "...")
    sys.exit(0)
