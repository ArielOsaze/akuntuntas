"""
Membungkus AkunTuntas menjadi paket MSIX untuk Microsoft Store.

Microsoft Store menandatangani paket MSIX dengan sertifikatnya sendiri,
sehingga aplikasi yang dipasang lewat Store tidak memunculkan peringatan
SmartScreen. Ini satu-satunya cara menghilangkan peringatan itu tanpa
membeli sertifikat code signing.

Alur pemakaian:

    python tools/bungkus_msix.py --siapkan     # siapkan berkas paket
    python tools/bungkus_msix.py --bungkus     # bungkus menjadi .msix
    python tools/bungkus_msix.py --periksa     # periksa hasilnya

Hasil akhir ada di folder `msix_output/` berupa berkas `.msixupload` yang
diunggah ke Partner Center.

Sebelum dipakai, isi dulu `msix/identitas.json` dengan nama penerbit yang
diberikan Partner Center. Nilai itu berbeda untuk setiap akun dan tidak
dapat dikira-kira.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import subprocess
import sys

AKAR = pathlib.Path(__file__).resolve().parent.parent
DIST = AKAR / "dist" / "AkunTuntas"
MSIX = AKAR / "msix"
KELUARAN = AKAR / "msix_output"
IDENTITAS = MSIX / "identitas.json"

NAMA_PAKET = "AkunTuntas"


def cari_makeappx() -> str | None:
    """Cari MakeAppx.exe dari Windows SDK."""
    dasar = pathlib.Path("C:/Program Files (x86)/Windows Kits/10/bin")
    if dasar.exists():
        for jalur in sorted(dasar.glob("*/x64/makeappx.exe"), reverse=True):
            return str(jalur)
    return shutil.which("makeappx")


def cari_signtool() -> str | None:
    """Cari SignTool.exe, dipakai untuk penandatanganan uji lokal."""
    dasar = pathlib.Path("C:/Program Files (x86)/Windows Kits/10/bin")
    if dasar.exists():
        for jalur in sorted(dasar.glob("*/x64/signtool.exe"), reverse=True):
            return str(jalur)
    return shutil.which("signtool")


def baca_identitas() -> dict:
    """
    Baca identitas penerbit dari Partner Center.

    Nilai-nilai ini wajib sama persis dengan yang terdaftar di Partner
    Center. Bila berbeda satu huruf, paket akan ditolak saat diunggah.
    """
    if not IDENTITAS.exists():
        return {}
    try:
        return json.loads(IDENTITAS.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"  identitas.json tidak terbaca: {e}")
        return {}


def tulis_manifest(identitas: dict) -> pathlib.Path:
    """
    Tulis AppxManifest.xml memakai identitas dari Partner Center.

    Manifest menentukan bagaimana Windows memasang aplikasi: nama yang
    tampil di Store, versi, ikon, dan cara aplikasi dijalankan.
    """
    nama_penerbit = identitas.get("penerbit",
                                  "CN=Isi-Dari-Partner-Center")
    nama_paket = identitas.get("nama_paket", "XinetGroup.AkunTuntas")
    nama_tampil = identitas.get("nama_tampil", NAMA_PAKET)
    versi = identitas.get("versi", "1.1.2.0")
    deskripsi = identitas.get(
        "deskripsi", "Pembukuan dan pajak perusahaan Indonesia")

    isi = f'''<?xml version="1.0" encoding="utf-8"?>
<Package
  xmlns="http://schemas.microsoft.com/appx/manifest/foundation/windows10"
  xmlns:uap="http://schemas.microsoft.com/appx/manifest/uap/windows10"
  xmlns:rescap="http://schemas.microsoft.com/appx/manifest/foundation/windows10/restrictedcapabilities"
  IgnorableNamespaces="uap rescap">

  <Identity
    Name="{nama_paket}"
    Publisher="{nama_penerbit}"
    Version="{versi}"
    ProcessorArchitecture="x64" />

  <Properties>
    <DisplayName>{nama_tampil}</DisplayName>
    <PublisherDisplayName>{identitas.get("nama_penerbit_tampil", "Xinet Group")}</PublisherDisplayName>
    <Description>{deskripsi}</Description>
    <Logo>Assets\\StoreLogo.png</Logo>
  </Properties>

  <Dependencies>
    <TargetDeviceFamily
      Name="Windows.Desktop"
      MinVersion="10.0.19041.0"
      MaxVersionTested="10.0.26100.0" />
  </Dependencies>

  <Resources>
    <Resource Language="id-ID" />
    <Resource Language="en-US" />
  </Resources>

  <Applications>
    <Application Id="AkunTuntas"
      Executable="AkunTuntas.exe"
      EntryPoint="Windows.FullTrustApplication">
      <uap:VisualElements
        DisplayName="{nama_tampil}"
        Description="{deskripsi}"
        BackgroundColor="transparent"
        Square150x150Logo="Assets\\Square150x150Logo.png"
        Square44x44Logo="Assets\\Square44x44Logo.png">
        <uap:DefaultTile
          Wide310x150Logo="Assets\\Wide310x150Logo.png"
          Square310x310Logo="Assets\\LargeTile.png"
          ShortName="{nama_tampil}" />
      </uap:VisualElements>
    </Application>
  </Applications>

  <Capabilities>
    <rescap:Capability Name="runFullTrust" />
    <Capability Name="internetClient" />
  </Capabilities>
</Package>
'''
    tujuan = MSIX / "AppxManifest.xml"
    tujuan.write_text(isi, encoding="utf-8")
    return tujuan


def buat_aset_ikon() -> bool:
    """
    Siapkan ikon ukuran yang diwajibkan MSIX.

    MSIX meminta lima ukuran ikon. Ikon asli AkunTuntas dipakai ulang dan
    diperkecil, sehingga tampilannya tetap sama seperti di installer.
    """
    try:
        from PIL import Image
    except ImportError:
        print("  Pillow belum terpasang. Jalankan: pip install pillow")
        return False

    sumber = AKAR / "assets" / "app_256.png"
    if not sumber.exists():
        print(f"  ikon sumber tidak ada: {sumber}")
        return False

    folder = MSIX / "Assets"
    folder.mkdir(parents=True, exist_ok=True)

    gambar = Image.open(sumber).convert("RGBA")

    # Ukuran yang diminta manifest. StoreLogo dipakai di halaman Store,
    # sisanya untuk ubin di menu Start dan daftar aplikasi.
    daftar = {
        "StoreLogo.png": (50, 50),
        "Square44x44Logo.png": (44, 44),
        "Square150x150Logo.png": (150, 150),
        "Wide310x150Logo.png": (310, 150),
        "LargeTile.png": (310, 310),
    }

    for nama, ukuran in daftar.items():
        kanvas = Image.new("RGBA", ukuran, (0, 0, 0, 0))
        salinan = gambar.copy()
        salinan.thumbnail(ukuran, Image.LANCZOS)
        kiri = (ukuran[0] - salinan.width) // 2
        atas = (ukuran[1] - salinan.height) // 2
        kanvas.paste(salinan, (kiri, atas), salinan)
        kanvas.save(folder / nama)
        print(f"    {nama:26s} {ukuran[0]}x{ukuran[1]}")

    return True


def siapkan() -> int:
    """Susun seluruh berkas yang dibutuhkan paket MSIX."""
    print("=" * 74)
    print("  MENYIAPKAN PAKET MSIX")
    print("=" * 74)
    print()

    if not DIST.exists():
        print(f"  Folder aplikasi belum ada: {DIST}")
        print("  Jalankan lebih dahulu:")
        print("    python -m PyInstaller build.spec --noconfirm")
        return 2

    identitas = baca_identitas()
    if not identitas:
        print(f"  Berkas identitas belum ada: {IDENTITAS}")
        print()
        print("  Salin contoh di bawah, lalu isi dengan nilai dari Partner")
        print("  Center (menu Product management > Product identity):")
        print()
        print("    {")
        print('      "nama_paket": "12345XinetGroup.AkunTuntas",')
        print('      "penerbit": "CN=ABC12345-6789-ABCD-EF01-234567890ABC",')
        print('      "nama_penerbit_tampil": "Xinet Group",')
        print('      "nama_tampil": "AkunTuntas",')
        print('      "versi": "1.1.2.0",')
        print('      "deskripsi": "Pembukuan dan pajak perusahaan Indonesia"')
        print("    }")
        print()
        print("  Catatan: 'versi' wajib empat angka (1.1.2.0), bukan 1.1.2.")
        return 3

    MSIX.mkdir(parents=True, exist_ok=True)

    print("  Ikon:")
    if not buat_aset_ikon():
        return 4

    print()
    print("  Manifest:")
    manifest = tulis_manifest(identitas)
    print(f"    {manifest.name}")

    # Berkas penanda mode uji coba tidak dibuat di sini. Penanda harus memuat
    # keterangan bertanda tangan kunci privat server, dan kunci itu tidak ada
    # di komputer pengembang. Penanda diterbitkan lewat:
    #     python tools/terbitkan_uji_coba.py
    # Berkas kosong tidak lagi cukup, karena aplikasi memeriksa tanda
    # tangannya dan memastikan dirinya benar benar berjalan di dalam paket
    # MSIX.
    penanda = MSIX / "uji_coba.txt"
    print()
    print("  Penanda uji coba:")
    if penanda.exists():
        try:
            isi = json.loads(penanda.read_text(encoding="utf-8"))
            lengkap = bool(isi.get("muatan") and isi.get("tanda"))
        except Exception:
            lengkap = False
        if lengkap:
            print(f"    {penanda.name} (bertanda tangan, siap dipakai)")
        else:
            print(f"    {penanda.name} ADA tetapi tidak bertanda tangan")
            print("    Mode uji coba akan DITOLAK. Terbitkan yang sah:")
            print("      python tools/terbitkan_uji_coba.py")
    else:
        print("    belum ada. Paket akan dibungkus tanpa mode uji coba.")
        print("    Untuk paket yang dikirim ke Microsoft Store, terbitkan dulu:")
        print("      python tools/terbitkan_uji_coba.py")

    print()
    print("  Selesai. Lanjutkan dengan:")
    print("    python tools/bungkus_msix.py --bungkus")
    return 0


def bungkus() -> int:
    """Bungkus folder aplikasi menjadi berkas .msix."""
    print("=" * 74)
    print("  MEMBUNGKUS PAKET MSIX")
    print("=" * 74)
    print()

    makeappx = cari_makeappx()
    if not makeappx:
        print("  MakeAppx.exe tidak ditemukan.")
        print("  Pasang Windows SDK: komponen 'MSIX Packaging Tools'.")
        return 2

    manifest = MSIX / "AppxManifest.xml"
    if not manifest.exists():
        print("  Manifest belum ada. Jalankan dulu:")
        print("    python tools/bungkus_msix.py --siapkan")
        return 3

    # Susun folder paket: isi aplikasi ditambah manifest dan ikon MSIX.
    KELUARAN.mkdir(parents=True, exist_ok=True)
    tahap = KELUARAN / "_tahap"
    if tahap.exists():
        shutil.rmtree(tahap)

    print(f"  Menyalin aplikasi dari {DIST.name}...")
    shutil.copytree(DIST, tahap)

    print("  Menambahkan manifest dan ikon...")
    shutil.copy2(manifest, tahap / "AppxManifest.xml")
    tujuan_aset = tahap / "Assets"
    if tujuan_aset.exists():
        shutil.rmtree(tujuan_aset)
    shutil.copytree(MSIX / "Assets", tujuan_aset)

    penanda = MSIX / "uji_coba.txt"
    if penanda.exists():
        # Penanda harus memuat keterangan bertanda tangan, bukan berkas
        # kosong. Tanpa tanda tangan, siapa pun dapat membuat berkas dengan
        # nama yang sama dan memakai aplikasi tanpa membeli lisensi.
        try:
            isi = json.loads(penanda.read_text(encoding="utf-8"))
            lengkap = bool(isi.get("muatan") and isi.get("tanda"))
        except Exception:
            lengkap = False

        if not lengkap:
            print()
            print("  Penanda uji coba tidak dapat dipakai.")
            print("  Berkas msix/uji_coba.txt tidak memuat keterangan")
            print("  bertanda tangan, sehingga mode uji coba akan ditolak.")
            print()
            print("  Terbitkan penanda yang sah lebih dulu:")
            print("    python tools/terbitkan_uji_coba.py")
            return 5

        shutil.copy2(penanda, tahap / "uji_coba.txt")
        print("  Menyertakan penanda mode uji coba (bertanda tangan).")

    keluaran = KELUARAN / f"{NAMA_PAKET}.msix"
    if keluaran.exists():
        keluaran.unlink()

    print()
    print("  Membungkus (bisa memakan beberapa menit)...")
    hasil = subprocess.run(
        [makeappx, "pack", "/d", str(tahap), "/p", str(keluaran),
         "/o"],
        capture_output=True, text=True,
    )
    if hasil.returncode != 0:
        print("  Gagal membungkus:")
        for baris in (hasil.stdout + hasil.stderr).splitlines()[-8:]:
            print(f"    {baris}")
        return 4

    print()
    ukuran = keluaran.stat().st_size / 1048576
    print(f"  BERHASIL: {keluaran.name} ({ukuran:.1f} MB)")
    print(f"  Lokasi  : {keluaran}")
    print()

    if tahap.exists():
        shutil.rmtree(tahap)

    print("  Langkah berikutnya:")
    print("    1. Periksa paket : python tools/bungkus_msix.py --periksa")
    print("    2. Unggah ke Partner Center:")
    print("       https://partner.microsoft.com/dashboard")
    return 0


def periksa() -> int:
    """Periksa paket MSIX yang sudah dibungkus."""
    print("=" * 74)
    print("  MEMERIKSA PAKET MSIX")
    print("=" * 74)
    print()

    keluaran = KELUARAN / f"{NAMA_PAKET}.msix"
    if not keluaran.exists():
        print(f"  Paket belum ada: {keluaran}")
        print("  Jalankan: python tools/bungkus_msix.py --bungkus")
        return 2

    ukuran = keluaran.stat().st_size / 1048576
    print(f"  Berkas  : {keluaran.name}")
    print(f"  Ukuran  : {ukuran:.1f} MB")

    batas = 25000
    if ukuran < batas:
        print(f"  Batas   : di bawah {batas} MB, aman untuk Store")
    else:
        print(f"  Batas   : MELEBIHI {batas} MB, paket akan ditolak")

    print()
    print("  Isi paket:")

    makeappx = cari_makeappx()
    if makeappx:
        hasil = subprocess.run(
            [makeappx, "unpack", "/p", str(keluaran), "/d",
             str(KELUARAN / "_periksa"), "/o"],
            capture_output=True, text=True,
        )
        if hasil.returncode == 0:
            folder = KELUARAN / "_periksa"
            penting = [
                "AppxManifest.xml",
                "AkunTuntas.exe",
                "uji_coba.txt",
                "Assets/Square150x150Logo.png",
                "Assets/StoreLogo.png",
            ]
            for nama in penting:
                jalur = folder / nama
                tanda = "ADA" if jalur.exists() else "HILANG"
                print(f"    {tanda:6s} {nama}")

            jumlah = sum(1 for _ in folder.rglob("*") if _.is_file())
            print(f"    total berkas: {jumlah}")

            # Baca identitas dari manifest
            man = folder / "AppxManifest.xml"
            if man.exists():
                isi = man.read_text(encoding="utf-8", errors="ignore")
                import re
                for pola, label in (
                        (r'Name="([^"]+)"\s+Publisher', "Nama paket"),
                        (r'Publisher="([^"]+)"', "Penerbit"),
                        (r'Version="([^"]+)"', "Versi"),
                ):
                    cocok = re.search(pola, isi)
                    if cocok:
                        print(f"    {label:12s}: {cocok.group(1)}")

            shutil.rmtree(folder, ignore_errors=True)
        else:
            print("    (paket tidak dapat dibuka untuk diperiksa)")
    else:
        print("    (MakeAppx tidak tersedia)")

    print()
    print("  Catatan penting:")
    print("    Paket ini BELUM ditandatangani. Microsoft Store akan")
    print("    menandatanganinya sendiri saat paket diterima. Untuk mencoba")
    print("    memasangnya di komputer sendiri sebelum diunggah, paket harus")
    print("    ditandatangani dengan sertifikat uji terlebih dahulu.")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(
        description="Bungkus AkunTuntas menjadi paket MSIX untuk "
                    "Microsoft Store.")
    grup = p.add_mutually_exclusive_group(required=True)
    grup.add_argument("--siapkan", action="store_true",
                      help="siapkan manifest dan ikon")
    grup.add_argument("--bungkus", action="store_true",
                      help="bungkus menjadi berkas .msix")
    grup.add_argument("--periksa", action="store_true",
                      help="periksa paket yang sudah dibungkus")
    arg = p.parse_args()

    if arg.siapkan:
        return siapkan()
    if arg.bungkus:
        return bungkus()
    return periksa()


if __name__ == "__main__":
    sys.exit(main())
