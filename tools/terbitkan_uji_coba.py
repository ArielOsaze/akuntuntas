"""
AkunTuntas - Menerbitkan Penanda Uji Coba untuk Microsoft Store
================================================================
Penanda mode uji coba harus memuat keterangan bertanda tangan kunci privat
server. Kunci itu tidak ada di komputer pengembang, jadi penanda diminta
lewat layanan lisensi yang sudah ada.

Hasilnya disimpan di `msix/uji_coba.txt`, lalu ikut dibungkus ke dalam
paket MSIX. Berkas kosong tidak lagi berguna, karena aplikasi memeriksa
tanda tangannya.

Cara pakai:
    python tools/terbitkan_uji_coba.py
    python tools/terbitkan_uji_coba.py --hari 90
"""
from __future__ import annotations

import argparse
import getpass
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
TUJUAN = AKAR / "msix" / "uji_coba.txt"

sys.path.insert(0, str(AKAR / "src"))

from akuntansi_id.core.license import ALAMAT_SERVER  # noqa: E402


def kirim(permintaan: dict) -> tuple[bool, dict]:
    """Kirim permintaan ke layanan lisensi."""
    panggilan = urllib.request.Request(
        ALAMAT_SERVER,
        data=json.dumps(permintaan).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(panggilan, timeout=30) as jawaban:
            return True, json.loads(jawaban.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            return True, json.loads(e.read().decode("utf-8"))
        except Exception:
            return False, {"pesan": f"HTTP {e.code}"}
    except Exception as e:
        return False, {"pesan": f"{type(e).__name__}: {e}"}


def main() -> int:
    p = argparse.ArgumentParser(
        description="Terbitkan penanda mode uji coba untuk paket MSIX.")
    p.add_argument("--hari", type=int, default=60,
                   help="masa berlaku penanda dalam hari (baku 60)")
    p.add_argument("--sandi", default="",
                   help="sandi dashboard admin (bila tidak ingin ditanyakan)")
    p.add_argument("--email", default="",
                   help="email admin (bila tidak ingin ditanyakan)")
    arg = p.parse_args()

    print("=" * 74)
    print("  MENERBITKAN PENANDA UJI COBA")
    print("=" * 74)
    print()
    print(f"  masa berlaku : {arg.hari} hari")
    print(f"  tujuan       : {TUJUAN}")
    print()

    # Penanda hanya boleh diterbitkan oleh pemilik dashboard admin, karena
    # penanda memberi seluruh fitur Enterprise selama masa berlakunya.
    email = arg.email or input("  Email admin    : ").strip()
    sandi = arg.sandi or getpass.getpass("  Sandi admin    : ")
    if not email or not sandi:
        print()
        print("  Email dan sandi admin wajib diisi.")
        return 2

    print()
    print("  Meminta izin masuk...")
    terhubung, jawaban = kirim({
        "aksi": "admin-masuk",
        "email": email,
        "sandi": sandi,
    })
    if not terhubung:
        print(f"  GAGAL: {jawaban.get('pesan')}")
        return 3
    if not jawaban.get("ok"):
        print(f"  DITOLAK: {jawaban.get('pesan', 'tidak dijelaskan')}")
        return 4

    token = jawaban.get("token", "")
    if not token:
        print("  GAGAL: server tidak mengirim token sesi.")
        return 5
    print("  Izin masuk diterima.")

    print()
    print("  Meminta penanda...")
    terhubung, jawaban = kirim({
        "aksi": "terbitkan-uji-coba",
        "token": token,
        "hari": arg.hari,
    })
    if not terhubung:
        print(f"  GAGAL: {jawaban.get('pesan')}")
        return 6
    if not jawaban.get("ok"):
        print(f"  DITOLAK: {jawaban.get('pesan', 'tidak dijelaskan')}")
        return 7

    muatan = jawaban.get("muatan", "")
    tanda = jawaban.get("tanda", "")
    if not muatan or not tanda:
        print("  GAGAL: penanda yang diterima tidak lengkap.")
        return 8

    # Periksa tanda tangannya sebelum disimpan, supaya paket tidak dibungkus
    # dengan penanda yang akan ditolak aplikasi.
    from akuntansi_id.core.license import tanda_sah
    if not tanda_sah(muatan, tanda):
        print("  GAGAL: tanda tangan penanda tidak dapat diperiksa.")
        return 9

    TUJUAN.parent.mkdir(parents=True, exist_ok=True)
    TUJUAN.write_text(json.dumps({
        "muatan": muatan,
        "tanda": tanda,
    }, indent=2), encoding="utf-8")

    isi = json.loads(muatan)
    print()
    print("  BERHASIL. Penanda bertanda tangan sudah disimpan.")
    print(f"    berlaku sampai : {isi.get('berlaku_sampai')}")
    print(f"    paket          : {isi.get('paket')}")
    print()
    print("  Langkah berikutnya:")
    print("    python tools/bungkus_msix.py --siapkan")
    print("    python tools/bungkus_msix.py --bungkus")
    return 0


if __name__ == "__main__":
    sys.exit(main())
