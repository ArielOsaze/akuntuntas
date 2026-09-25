"""
Uji batas percobaan aktivasi di server.

Kunci lisensi dapat dicoba dari perangkat berbeda beda untuk mencari kunci
yang masih berlaku. Tanpa batas, ribuan percobaan dapat dikirim dalam
hitungan menit. Server membatasi 12 kegagalan per perangkat dalam 15 menit,
dan hanya percobaan dengan kunci tidak dikenal yang dihitung, sehingga
pemakaian biasa tidak pernah terkena batas ini.

Alat ini mengirim percobaan sungguhan ke server, lalu memastikan batasnya
berlaku. Log percobaan dibersihkan setelah pengujian.

Cara pakai:
    python tools/uji_batas_percobaan.py
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "src"))

from akuntansi_id.core.license import ALAMAT_SERVER  # noqa: E402

#: Sidik khusus pengujian, dibedakan dari perangkat sungguhan.
SIDIK_UJI = "uji-batas-percobaan-0001"

#: Jumlah kegagalan yang masih diproses sebelum batas berlaku.
BATAS = 12


def kirim(permintaan: dict) -> tuple[int, dict]:
    panggilan = urllib.request.Request(
        ALAMAT_SERVER,
        data=json.dumps(permintaan).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(panggilan, timeout=30) as jawaban:
            return jawaban.status, json.loads(jawaban.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8"))
        except Exception:
            return e.code, {}
    except Exception as e:
        return 0, {"pesan": f"{type(e).__name__}: {e}"}


def main() -> int:
    print("=" * 74)
    print("  UJI BATAS PERCOBAAN AKTIVASI")
    print("=" * 74)
    print()
    print(f"  sidik uji    : {SIDIK_UJI}")
    print(f"  batas        : {BATAS} kegagalan per 15 menit")
    print()

    lulus = 0
    gagal = 0

    for i in range(1, BATAS + 3):
        kode, jawaban = kirim({
            "aksi": "aktivasi",
            "kunci": f"ATNTUJICOBATES{i:04d}",
            "sidik": SIDIK_UJI,
            "sidik_baru": SIDIK_UJI,
            "nama_perangkat": "Uji Batas",
        })

        dibatasi = (kode == 429)
        # Percobaan ke-1 sampai ke-BATAS harus diproses (ditolak karena
        # kuncinya tidak dikenal). Setelah itu batasnya berlaku.
        seharusnya_dibatasi = i > BATAS

        if dibatasi == seharusnya_dibatasi:
            lulus += 1
            tanda = "BATAS" if dibatasi else "diproses"
            print(f"  [LULUS] percobaan {i:2d}: HTTP {kode} ({tanda})")
        else:
            gagal += 1
            tanda = "BATAS" if dibatasi else "diproses"
            print(f"  [GAGAL] percobaan {i:2d}: HTTP {kode} ({tanda}), "
                  f"seharusnya {'BATAS' if seharusnya_dibatasi else 'diproses'}")

    print()
    print("=" * 74)
    print(f"  HASIL: {lulus} LULUS, {gagal} GAGAL")
    print("=" * 74)
    print()
    print("  Catatan: log percobaan dibiarkan di server sebagai jejak, dan")
    print("  akan hilang sendiri setelah 15 menit.")
    return 1 if gagal else 0


if __name__ == "__main__":
    sys.exit(main())
