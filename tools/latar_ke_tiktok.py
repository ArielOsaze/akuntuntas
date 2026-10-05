"""
Tambah atau hapus latar kamera AkunTuntas di daftar TikTok LIVE Studio.

TikTok menyimpan daftar latar kamera sendiri di dua tempat:

    userImage/camera_background/<id>/     berkas gambarnya
    TTStore/services.json                 daftar yang dibaca TikTok

Skrip ini menyiapkan gambar, menaruhnya di folder TikTok, lalu
mendaftarkannya supaya muncul di bagian Background pada pengaturan
sumber Camera. Tidak perlu menambah gambar secara manual.

TikTok perlu dibuka ulang supaya daftar baru terbaca.

Cara pakai:

    python tools/latar_ke_tiktok.py --pasang
    python tools/latar_ke_tiktok.py --daftar
    python tools/latar_ke_tiktok.py --lepas
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import time
import uuid
from pathlib import Path

from PIL import Image

AKAR = Path(__file__).resolve().parent.parent
SUMBER = AKAR / "live_overlay/gambar/latar-akuntuntas.png"

DATA_TIKTOK = Path.home() / "AppData/Roaming/TikTok LIVE Studio"
FOLDER_GAMBAR = DATA_TIKTOK / "userImage/camera_background"
BERKAS_DAFTAR = DATA_TIKTOK / "TTStore/services.json"

# Penanda supaya gambar kita mudah dikenali dan tidak tertukar dengan
# latar bawaan TikTok
PENANDA = "akuntuntas"

# Diisi dari argumen --tunggu
TUNGGU = False

# Bentuk potongan yang dipakai TikTok untuk kanvas tegak
LEBAR_TEGAK = 1215
TINGGI_TEGAK = 2160
RASIO_TEGAK = 0.562


def tiktok_berjalan() -> bool:
    """Periksa apakah TikTok LIVE Studio sedang berjalan.

    TikTok menyimpan daftarnya sendiri setiap beberapa detik, jadi
    perubahan yang kita tulis akan tertimpa kalau TikTok sedang jalan.
    """
    import subprocess

    try:
        h = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq TikTok LIVE Studio.exe", "/NH"],
            capture_output=True, text=True, timeout=60,
        )
        return "TikTok LIVE Studio" in (h.stdout or "")
    except Exception:
        return False


def minta_tutup() -> None:
    """Beri tahu bahwa TikTok perlu ditutup lebih dahulu."""
    print("  TikTok LIVE Studio sedang berjalan.")
    print()
    print("  TikTok menyimpan daftarnya sendiri setiap beberapa detik,")
    print("  jadi perubahan akan tertimpa kalau TikTok masih terbuka.")
    print()
    print("  Tutup dulu TikTok LIVE Studio, lalu jalankan perintah ini lagi.")
    print("  Cara menutup: klik kanan ikon TikTok di bilah tugas, pilih Close.")
    print("  Kalau tidak bisa, buka Task Manager, cari TikTok LIVE Studio,")
    print("  lalu pilih End task.")
    print()
    print("  Atau jalankan dengan --tunggu, nanti menunggu sendiri sampai")
    print("  TikTok tertutup lalu langsung memasangnya.")


def tunggu_tutup(menit: int = 10) -> bool:
    """Tunggu sampai TikTok tertutup, lalu kembalikan benar."""
    print("  Menunggu TikTok LIVE Studio ditutup...")
    print("  Silakan tutup TikTok sekarang. Cara menutup:")
    print("     1. Tutup jendelanya seperti biasa, atau")
    print("     2. Buka Task Manager, cari TikTok LIVE Studio, End task")
    print()

    batas = time.time() + menit * 60
    tanda = 0
    while time.time() < batas:
        if not tiktok_berjalan():
            print("  TikTok sudah tertutup.")
            return True
        time.sleep(2)
        tanda += 2
        if tanda % 30 == 0:
            sisa = int((batas - time.time()) / 60)
            print(f"      masih menunggu... (sisa sekitar {sisa} menit)")

    print("  Waktu tunggu habis. Jalankan lagi kalau sudah siap.")
    return False


def baca_daftar() -> tuple[dict, str, int, int]:
    """Baca services.json dan temukan letak daftar gambar sendiri."""
    teks = BERKAS_DAFTAR.read_text(encoding="utf-8", errors="ignore")
    pola = re.search(r'"userImageInfos"\s*:\s*\[\s*', teks)
    if not pola:
        raise RuntimeError("daftar userImageInfos tidak ditemukan")
    return json.loads(teks), teks, pola.start(), pola.end()


def ambil_daftar(data: dict) -> list[dict]:
    """Ambil daftar gambar sendiri dari data TikTok."""
    try:
        return data["ImageManagerService"]["state"]["userImageInfos"]
    except (KeyError, TypeError):
        return []


def entri_kita(data: dict) -> list[dict]:
    """Ambil entri yang kita buat sebelumnya."""
    return [e for e in ambil_daftar(data) if PENANDA in str(e.get("basePath", ""))]


def siapkan_gambar() -> tuple[Image.Image, Image.Image]:
    """Siapkan gambar bentuk kamera dan potongan tegak."""
    if not SUMBER.exists():
        raise FileNotFoundError(
            f"gambar sumber tidak ada: {SUMBER}\n"
            "Jalankan lebih dahulu: python tools/buat_latar_kamera.py"
        )

    asli = Image.open(SUMBER).convert("RGB")

    # Bentuk kamera: dipakai apa adanya
    origin = asli

    # Potongan tegak: penuhi bidang lalu potong tengahnya
    rasio = LEBAR_TEGAK / TINGGI_TEGAK
    if asli.width / asli.height > rasio:
        skala = TINGGI_TEGAK / asli.height
        baru = asli.resize(
            (max(1, round(asli.width * skala)), TINGGI_TEGAK), Image.LANCZOS
        )
    else:
        skala = LEBAR_TEGAK / asli.width
        baru = asli.resize(
            (LEBAR_TEGAK, max(1, round(asli.height * skala))), Image.LANCZOS
        )

    kiri = max(0, (baru.width - LEBAR_TEGAK) // 2)
    atas = max(0, (baru.height - TINGGI_TEGAK) // 2)
    potong = baru.crop(
        (kiri, atas, kiri + LEBAR_TEGAK, atas + TINGGI_TEGAK)
    )
    return origin, potong


def pasang() -> int:
    if not BERKAS_DAFTAR.exists():
        print(f"  TikTok LIVE Studio tidak ditemukan di {DATA_TIKTOK}")
        return 1

    if tiktok_berjalan():
        if not TUNGGU:
            minta_tutup()
            return 1
        if not tunggu_tutup():
            return 1

    print("  TikTok tidak berjalan, aman untuk mengubah daftar.")
    print("  Menyiapkan gambar...")
    origin, potong = siapkan_gambar()
    print(f"      bentuk kamera : {origin.width}x{origin.height}")
    print(f"      potongan tegak: {potong.width}x{potong.height}")

    # Simpan berkas
    id_baru = f"{PENANDA}-{uuid.uuid4()}"
    folder = FOLDER_GAMBAR / id_baru
    folder.mkdir(parents=True, exist_ok=True)

    cap = int(time.time() * 1000)
    jalur_origin = folder / "origin.jpg"
    jalur_potong = folder / f"{RASIO_TEGAK}-{cap}.jpg"

    origin.save(jalur_origin, "JPEG", quality=92, optimize=True)
    potong.save(jalur_potong, "JPEG", quality=92, optimize=True)
    print(f"  Gambar disimpan di {folder.name}")

    # Daftarkan
    data, teks, _, akhir = baca_daftar()

    # Lepas dulu entri lama supaya tidak menumpuk
    lama = entri_kita(data)
    if lama:
        print(f"  Menghapus {len(lama)} entri lama...")
        lepas(sunyi=True)
        data, teks, _, akhir = baca_daftar()

    entri = {
        "id": id_baru,
        "basePath": str(folder),
        "path": str(jalur_origin),
        "deletable": True,
        "cropped": [
            {
                "ratio": RASIO_TEGAK,
                "path": str(jalur_potong),
                "cropInfo": {
                    "top": 0,
                    "left": max(0, (potong.width - LEBAR_TEGAK) / 2),
                    "width": float(LEBAR_TEGAK),
                    "height": float(TINGGI_TEGAK),
                },
            }
        ],
        "_maxWidth": 1920,
        "isAiImage": False,
        "originResourceId": "",
        "backgroundResourceId": "",
        "isAIGE": False,
        "aigeSessionId": "",
        "aigeTitle": "",
        "aigeCreateTime": 0,
    }

    teks_baru = teks[:akhir] + json.dumps(entri, ensure_ascii=False) + ", " + teks[akhir:]

    # Tulis hanya kalau bentuknya tetap sah
    simpan_aman(teks_baru, folder)

    print()
    print("  Selesai. Langkah di TikTok:")
    print("     1. Buka TikTok LIVE Studio")
    print("     2. Klik sumber Camera, buka tab Background")
    print("     3. Gambar AkunTuntas muncul di bagian Custom")
    print("     4. Nyalakan Cutout, lalu Save")
    return 0


def simpan_aman(teks_baru: str, folder: Path) -> None:
    """Tulis daftar, dan kembalikan keadaan semula kalau bentuknya rusak."""
    cadangan = BERKAS_DAFTAR.with_suffix(".json.cadangan")
    shutil.copy2(BERKAS_DAFTAR, cadangan)
    try:
        BERKAS_DAFTAR.write_text(teks_baru, encoding="utf-8")
        json.loads(BERKAS_DAFTAR.read_text(encoding="utf-8"))
    except Exception:
        shutil.copy2(cadangan, BERKAS_DAFTAR)
        shutil.rmtree(folder, ignore_errors=True)
        raise
    finally:
        cadangan.unlink(missing_ok=True)


def daftar() -> int:
    if not BERKAS_DAFTAR.exists():
        print("  TikTok LIVE Studio tidak ditemukan")
        return 1

    data, _, _, _ = baca_daftar()
    semua = ambil_daftar(data)
    kita = entri_kita(data)

    # Batas yang dipakai TikTok
    try:
        keadaan = data["ImageManagerService"]["state"]
        batas = keadaan.get("maxUpload", "-")
        kecil = keadaan.get("minResolution", {})
        ukuran = keadaan.get("maxSize", "-")
        print(f"  Batas TikTok: paling banyak {batas} gambar, "
              f"paling kecil {kecil.get('width','?')}x{kecil.get('height','?')} piksel, "
              f"paling besar {ukuran/1024:.0f} MB")
    except (KeyError, TypeError):
        pass

    print(f"  {len(semua)} latar terdaftar, {len(kita)} di antaranya dari AkunTuntas")
    for e in kita:
        folder = Path(e.get("basePath", ""))
        ada = "ada" if folder.exists() else "berkasnya hilang"
        gambar = folder / "origin.jpg"
        ukuran = f"{gambar.stat().st_size / 1024:.0f} KB" if gambar.exists() else "-"
        print(f"      {e.get('id', '?')[:44]}  {ada}  {ukuran}")
    return 0


def lepas(sunyi: bool = False) -> int:
    if not BERKAS_DAFTAR.exists():
        return 1

    if not sunyi and tiktok_berjalan():
        if not TUNGGU:
            minta_tutup()
            return 1
        if not tunggu_tutup():
            return 1

    data, teks, _, _ = baca_daftar()
    kita = entri_kita(data)
    if not kita:
        if not sunyi:
            print("  Tidak ada latar AkunTuntas yang terdaftar")
        return 0

    # Hapus entri dari teks mentah, satu per satu
    for e in kita:
        id_entri = str(e.get("id", ""))
        if not id_entri:
            continue
        pola = re.compile(
            r"\{\s*\"id\"\s*:\s*\"" + re.escape(id_entri) + r"\".*?\}\s*,?\s*",
            re.DOTALL,
        )
        teks = pola.sub("", teks, count=1)

        # Hapus berkasnya juga
        folder = Path(e.get("basePath", ""))
        if folder.exists() and PENANDA in folder.name:
            shutil.rmtree(folder, ignore_errors=True)

    # Rapikan koma yang tertinggal
    teks = re.sub(r",\s*\]", "]", teks)
    teks = re.sub(r"\[\s*,", "[", teks)

    cadangan = BERKAS_DAFTAR.with_suffix(".json.cadangan")
    shutil.copy2(BERKAS_DAFTAR, cadangan)
    try:
        BERKAS_DAFTAR.write_text(teks, encoding="utf-8")
        json.loads(BERKAS_DAFTAR.read_text(encoding="utf-8"))
    except Exception:
        shutil.copy2(cadangan, BERKAS_DAFTAR)
        print("  GAGAL: bentuk daftar jadi rusak, keadaan semula dikembalikan")
        return 1
    finally:
        cadangan.unlink(missing_ok=True)

    if not sunyi:
        print(f"  {len(kita)} latar AkunTuntas dilepas")
        print("  Tutup dan buka ulang TikTok supaya perubahannya terbaca")
    return 0


def utama() -> int:
    p = argparse.ArgumentParser(
        description="Atur latar kamera AkunTuntas di TikTok LIVE Studio"
    )
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--pasang", action="store_true", help="tambah latar AkunTuntas")
    g.add_argument("--daftar", action="store_true", help="lihat yang terdaftar")
    g.add_argument("--lepas", action="store_true", help="hapus latar AkunTuntas")
    p.add_argument("--tunggu", action="store_true",
                   help="tunggu TikTok ditutup, lalu langsung pasang")
    a = p.parse_args()

    global TUNGGU
    TUNGGU = a.tunggu

    if a.pasang:
        return pasang()
    if a.daftar:
        return daftar()
    return lepas()


if __name__ == "__main__":
    sys.exit(utama())
