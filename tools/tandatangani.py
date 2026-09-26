"""
Menandatangani installer AkunTuntas secara digital.

Windows menampilkan peringatan "penerbit tidak dikenal" untuk berkas yang
belum ditandatangani. Peringatan itu hilang setelah berkas ditandatangani
memakai sertifikat code signing atas nama Xinet Group.

Skrip ini membaca lokasi sertifikat dari berkas `sertifikat.json` di folder
yang sama. Berkas itu tidak ikut disimpan di repositori karena memuat
kata sandi.

Bentuk sertifikat.json:

    {
      "berkas": "C:/kunci/xinet.pfx",
      "sandi": "kata-sandi-pfx",
      "cap_waktu": "http://timestamp.digicert.com"
    }

Untuk sertifikat yang tersimpan di penyimpanan Windows (bukan berkas .pfx),
kosongkan "berkas" dan isi "sidik_jari" dengan sidik jari sertifikat:

    {
      "berkas": "",
      "sidik_jari": "A1B2C3...",
      "cap_waktu": "http://timestamp.digicert.com"
    }

Pemakaian:

    python tools/tandatangani.py                      # tandatangani installer
    python tools/tandatangani.py --periksa            # periksa tanda tangan saja
    python tools/tandatangani.py --berkas <path>      # berkas tertentu
"""
from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import subprocess
import sys

AKAR = pathlib.Path(__file__).resolve().parent.parent
SETELAN = AKAR / "sertifikat.json"
INSTALLER = AKAR / "installer_output" / "AkunTuntas-1.1.5-Setup.exe"
APLIKASI = AKAR / "dist" / "AkunTuntas" / "AkunTuntas.exe"


def cari_signtool() -> str | None:
    """Cari signtool.exe dari Windows SDK."""
    # jalur yang dipakai Windows SDK versi terbaru lebih dahulu
    kandidat = sorted(
        pathlib.Path("C:/Program Files (x86)/Windows Kits/10/bin").glob(
            "*/x64/signtool.exe"),
        reverse=True,
    )
    for jalur in kandidat:
        if jalur.exists():
            return str(jalur)
    bawaan = shutil.which("signtool")
    return bawaan


def periksa_tanda_tangan(berkas: pathlib.Path) -> dict:
    """Baca keadaan tanda tangan sebuah berkas lewat PowerShell."""
    if not berkas.exists():
        return {"ada": False, "pesan": f"berkas tidak ditemukan: {berkas}"}

    perintah = (
        "$s = Get-AuthenticodeSignature -LiteralPath "
        f"'{berkas}'; "
        "Write-Output $s.Status; "
        "Write-Output $s.SignerCertificate.Subject; "
        "Write-Output $s.SignerCertificate.Issuer; "
        "Write-Output $s.TimeStamperCertificate.Subject"
    )
    hasil = subprocess.run(
        ["powershell", "-NoProfile", "-Command", perintah],
        capture_output=True, text=True,
    )
    baris = [b.strip() for b in hasil.stdout.splitlines() if b.strip()]
    return {
        "ada": True,
        "status": baris[0] if len(baris) > 0 else "-",
        "penanda": baris[1] if len(baris) > 1 else "-",
        "penerbit": baris[2] if len(baris) > 2 else "-",
        "cap_waktu": baris[3] if len(baris) > 3 else "-",
    }


def tanda_tangani(berkas: pathlib.Path, setelan: dict, signtool: str) -> bool:
    """Jalankan signtool untuk satu berkas."""
    perintah = [signtool, "sign", "/fd", "sha256", "/v"]

    if setelan.get("berkas"):
        perintah += ["/f", str(setelan["berkas"])]
        if setelan.get("sandi"):
            perintah += ["/p", str(setelan["sandi"])]
    elif setelan.get("sidik_jari"):
        perintah += ["/sha1", str(setelan["sidik_jari"]), "/sm"]
    else:
        print("  Setelan sertifikat tidak lengkap: isi 'berkas' atau "
              "'sidik_jari'.")
        return False

    cap = setelan.get("cap_waktu") or "http://timestamp.digicert.com"
    perintah += ["/tr", cap, "/td", "sha256", str(berkas)]

    hasil = subprocess.run(perintah, capture_output=True, text=True)
    if hasil.returncode != 0:
        print("  Penandatanganan gagal:")
        for baris in (hasil.stdout + hasil.stderr).splitlines()[-6:]:
            print(f"    {baris}")
        return False
    return True


def main() -> int:
    p = argparse.ArgumentParser(
        description="Tandatangani installer AkunTuntas secara digital.")
    p.add_argument("--periksa", action="store_true",
                   help="hanya periksa keadaan tanda tangan")
    p.add_argument("--berkas", type=pathlib.Path, default=None,
                   help="berkas yang ditandatangani (bawaan: installer)")
    arg = p.parse_args()

    berkas = arg.berkas or INSTALLER

    print("=" * 74)
    print("  TANDA TANGAN DIGITAL AKUNTUNTAS")
    print("=" * 74)
    print()

    if arg.periksa:
        for sasaran in (berkas, APLIKASI):
            print(f"  {sasaran.name}")
            hasil = periksa_tanda_tangan(sasaran)
            if not hasil["ada"]:
                print(f"    {hasil['pesan']}")
            else:
                print(f"    Status   : {hasil['status']}")
                print(f"    Penanda  : {hasil['penanda']}")
                print(f"    Penerbit : {hasil['penerbit']}")
                print(f"    Cap waktu: {hasil['cap_waktu']}")
            print()
        return 0

    if not SETELAN.exists():
        print("  Berkas setelan sertifikat belum ada:")
        print(f"    {SETELAN}")
        print()
        print("  Buat berkas itu dengan isi seperti contoh di bawah, lalu")
        print("  jalankan skrip ini kembali:")
        print()
        print("    {")
        print('      "berkas": "C:/kunci/xinet.pfx",')
        print('      "sandi": "kata-sandi-pfx",')
        print('      "cap_waktu": "http://timestamp.digicert.com"')
        print("    }")
        print()
        print("  Belum punya sertifikat? Lihat docs/penandatanganan.md")
        return 2

    setelan = json.loads(SETELAN.read_text(encoding="utf-8"))
    signtool = cari_signtool()
    if not signtool:
        print("  signtool.exe tidak ditemukan. Pasang Windows SDK terlebih")
        print("  dahulu (komponen Signing Tools for Desktop Apps).")
        return 3

    print(f"  signtool : {signtool}")
    print(f"  berkas   : {berkas}")
    print()

    if not berkas.exists():
        print(f"  Berkas tidak ditemukan: {berkas}")
        return 4

    print("  Menandatangani...")
    if not tanda_tangani(berkas, setelan, signtool):
        return 5

    print()
    print("  Hasil:")
    hasil = periksa_tanda_tangan(berkas)
    print(f"    Status   : {hasil.get('status')}")
    print(f"    Penanda  : {hasil.get('penanda')}")
    print(f"    Penerbit : {hasil.get('penerbit')}")
    print(f"    Cap waktu: {hasil.get('cap_waktu')}")
    print()

    if hasil.get("status") == "Valid":
        print("  BERHASIL: berkas sudah ditandatangani dan berlaku.")
        print("  Peringatan 'penerbit tidak dikenal' tidak akan muncul lagi,")
        print("  meski SmartScreen masih dapat menampilkan peringatan sampai")
        print("  reputasi berkas terbentuk.")
        return 0

    print("  Tanda tangan belum berstatus Valid. Periksa sertifikatnya.")
    return 6


if __name__ == "__main__":
    sys.exit(main())
