"""
Naikkan nomor versi aplikasi dan sebarkan ke seluruh berkas.

Masalah yang diselesaikan: nomor versi tertulis di sebelas tempat berbeda.
Menaikkannya secara manual pasti ada yang terlewat, sehingga aplikasi,
installer, dan situs dapat menampilkan versi yang berbeda-beda. Akibatnya
sulit diketahui versi mana yang masih bermasalah.

Seluruh nilai diambil dari versi.json sebagai satu-satunya sumber, lalu
dituliskan ulang ke setiap berkas yang memerlukannya.

Cara pakai:
    python tools/naik_versi.py                 # tampilkan versi sekarang
    python tools/naik_versi.py 1.0.1           # naikkan ke 1.0.1
    python tools/naik_versi.py 1.0.1 --catatan "Perbaikan ikon tombol"
    python tools/naik_versi.py --periksa       # pastikan seluruh berkas seragam
"""
from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
VERSI_JSON = AKAR / "versi.json"


def baca_versi() -> dict:
    if not VERSI_JSON.exists():
        raise SystemExit(
            f"  berkas versi tidak ditemukan: {VERSI_JSON}\n"
            "  jalankan tools/naik_versi.py setelah berkas itu dibuat.")
    return json.loads(VERSI_JSON.read_text(encoding="utf-8"))


def tulis_versi(data: dict) -> None:
    VERSI_JSON.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8")


def versi_msix(versi: str) -> str:
    """MSIX memakai empat angka, misalnya 1.0.1 menjadi 1.0.1.0."""
    bagian = versi.split(".")
    while len(bagian) < 4:
        bagian.append("0")
    return ".".join(bagian[:4])


def ganti_teks(berkas: Path, pola: str, ganti: str,
               wajib: bool = True) -> bool:
    """Ganti teks memakai pola, kembalikan True bila ada yang berubah."""
    if not berkas.exists():
        if wajib:
            print(f"    {berkas.name}: TIDAK DITEMUKAN")
        return False

    teks = berkas.read_text(encoding="utf-8")
    baru, jumlah = re.subn(pola, ganti, teks, flags=re.MULTILINE)

    if jumlah:
        berkas.write_text(baru, encoding="utf-8")
        print(f"    {berkas.name}: {jumlah} tempat")
        return True

    return False


def sebarkan(versi: str, build: str, tanggal: str) -> int:
    """Tuliskan versi ke seluruh berkas yang memerlukannya."""
    print("  menyebarkan versi ke seluruh berkas:")
    print()
    jumlah = 0

    # 1. Konfigurasi aplikasi
    if ganti_teks(AKAR / "src/akuntansi_id/config.py",
                  r'^APP_VERSION = "[^"]*"',
                  f'APP_VERSION = "{versi}"'):
        jumlah += 1
    if ganti_teks(AKAR / "src/akuntansi_id/config.py",
                  r'^APP_BUILD = "[^"]*"',
                  f'APP_BUILD = "{build}"'):
        jumlah += 1

    # 2. Informasi versi berkas EXE
    angka = versi.split(".")
    while len(angka) < 4:
        angka.append("0")
    tuple_versi = ", ".join(angka[:4])
    versi_empat = ".".join(angka[:4])

    if ganti_teks(AKAR / "version_info.txt",
                  r"filevers=\([^)]*\)",
                  f"filevers=({tuple_versi})"):
        jumlah += 1
    if ganti_teks(AKAR / "version_info.txt",
                  r"prodvers=\([^)]*\)",
                  f"prodvers=({tuple_versi})"):
        jumlah += 1
    # StringStruct juga wajib diperbarui. Sebelumnya bagian ini terlewat,
    # sehingga berkas EXE tetap mencantumkan versi lama meskipun angka
    # filevers sudah berubah.
    if ganti_teks(AKAR / "version_info.txt",
                  r"StringStruct\('FileVersion', '[^']*'\)",
                  f"StringStruct('FileVersion', '{versi_empat}')"):
        jumlah += 1
    if ganti_teks(AKAR / "version_info.txt",
                  r"StringStruct\('ProductVersion', '[^']*'\)",
                  f"StringStruct('ProductVersion', "
                  f"'{versi} Edisi Regulasi 2026')"):
        jumlah += 1

    # 3. Installer Inno Setup
    if ganti_teks(AKAR / "installer.iss",
                  r'#define VersiAplikasi "[^"]*"',
                  f'#define VersiAplikasi "{versi}"'):
        jumlah += 1

    # 4. Identitas paket MSIX
    if ganti_teks(AKAR / "msix/identitas.json",
                  r'"versi": "[^"]*"',
                  f'"versi": "{versi_msix(versi)}"',
                  wajib=False):
        jumlah += 1

    # 5. Situs: data terstruktur dan halaman privasi
    if ganti_teks(AKAR / "web/index.html",
                  r'"softwareVersion": "[^"]*"',
                  f'"softwareVersion": "{versi}"'):
        jumlah += 1
    if ganti_teks(AKAR / "web/privasi.html",
                  r"Berlaku untuk aplikasi AkunTuntas versi [\d.]+",
                  f"Berlaku untuk aplikasi AkunTuntas versi {versi}"):
        jumlah += 1
    if ganti_teks(AKAR / "web/privasi.html",
                  r"Terakhir diperbarui [^<]*",
                  f"Terakhir diperbarui {tanggal}"):
        jumlah += 1

    # 6. Alat yang menyebut versi baku
    for nama in ("tools/bungkus_msix.py", "tools/tandatangani.py",
                 "tools/periksa_kompatibilitas.py", "tools/pasang_ulang.py",
                 "tools/uji_pasang_ulang.py"):
        berkas = AKAR / nama
        if not berkas.exists():
            continue
        teks = berkas.read_text(encoding="utf-8")
        baru, n = re.subn(r'\b1\.\d+\.\d+\b', versi, teks)
        if n:
            berkas.write_text(baru, encoding="utf-8")
            print(f"    {nama}: {n} tempat")
            jumlah += 1

    return jumlah


def periksa(versi: str) -> int:
    """Pastikan seluruh berkas memakai versi yang sama."""
    print("=" * 74)
    print("  PERIKSA KESERAGAMAN VERSI")
    print("=" * 74)
    print()
    print(f"  versi baku (versi.json): {versi}")
    print()

    salah = []

    pemeriksaan = [
        ("src/akuntansi_id/config.py", r'APP_VERSION = "([^"]*)"', versi),
        ("installer.iss", r'#define VersiAplikasi "([^"]*)"', versi),
        ("web/index.html", r'"softwareVersion": "([^"]*)"', versi),
        ("msix/identitas.json", r'"versi": "([^"]*)"', versi_msix(versi)),
    ]

    for nama, pola, harus in pemeriksaan:
        berkas = AKAR / nama
        if not berkas.exists():
            print(f"    {nama:34s}: berkas tidak ada")
            continue
        m = re.search(pola, berkas.read_text(encoding="utf-8"))
        dapat = m.group(1) if m else "(tidak terbaca)"
        tanda = "OK" if dapat == harus else "BEDA"
        print(f"    {nama:34s}: {dapat:12s} [{tanda}]")
        if dapat != harus:
            salah.append(nama)

    print()
    if salah:
        print(f"  {len(salah)} berkas belum seragam.")
        print("  Jalankan: python tools/naik_versi.py " + versi)
    else:
        print("  SELURUH berkas memakai versi yang sama.")
    print("=" * 74)

    return 1 if salah else 0


def main() -> int:
    argumen = [a for a in sys.argv[1:] if not a.startswith("--")]

    data = baca_versi()

    if "--periksa" in sys.argv:
        return periksa(data["versi"])

    if not argumen:
        print("=" * 74)
        print("  VERSI APLIKASI")
        print("=" * 74)
        print()
        print(f"  versi sekarang : {data['versi']}")
        print(f"  build          : {data['build']}")
        print(f"  tanggal        : {data['tanggal']}")
        print()
        print("  Menaikkan versi:")
        print("    python tools/naik_versi.py 1.0.1")
        print()
        print("  Memeriksa keseragaman:")
        print("    python tools/naik_versi.py --periksa")
        print("=" * 74)
        return 0

    versi_baru = argumen[0]
    if not re.fullmatch(r"\d+\.\d+\.\d+", versi_baru):
        print(f"  format versi tidak dikenal: {versi_baru}")
        print("  contoh yang benar: 1.0.1")
        return 2

    versi_lama = data["versi"]

    # Build memakai penomoran tahun.bulan, mengikuti tanggal hari ini.
    hari_ini = date.today()
    build_baru = f"{hari_ini.year}.{hari_ini.month:02d}"

    catatan = ""
    if "--catatan" in sys.argv:
        pos = sys.argv.index("--catatan")
        if pos + 1 < len(sys.argv):
            catatan = sys.argv[pos + 1]

    data["versi"] = versi_baru
    data["build"] = build_baru
    data["tanggal"] = hari_ini.isoformat()
    if catatan:
        data["catatan"] = catatan

    print("=" * 74)
    print("  NAIKKAN VERSI APLIKASI")
    print("=" * 74)
    print()
    print(f"  versi lama: {versi_lama}")
    print(f"  versi baru: {versi_baru}")
    print(f"  build     : {build_baru}")
    print(f"  tanggal   : {hari_ini.isoformat()}")
    if catatan:
        print(f"  catatan   : {catatan}")
    print()

    tulis_versi(data)
    jumlah = sebarkan(versi_baru, build_baru, hari_ini.isoformat())

    print()
    print(f"  berkas diperbarui: {jumlah}")
    print("=" * 74)

    # Periksa hasilnya langsung, supaya kesalahan penyebaran ketahuan.
    print()
    return periksa(versi_baru)


if __name__ == "__main__":
    sys.exit(main())
