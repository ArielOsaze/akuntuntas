"""
Uji dua kelemahan yang tersisa pada pengikatan perangkat.

Kelemahan pertama: sidik perangkat memakai nama komputer dan alamat MAC,
padahal keduanya mudah diubah pengguna. Bila keduanya diubah agar sama
dengan komputer asal, sidik perangkat menjadi sama dan lisensi dapat
dipakai di komputer kedua.

Kelemahan kedua: pemakaian berulang tanpa internet. Setelah aktivasi,
pemeriksaan berjalan tanpa jaringan. Selama komputer kedua belum pernah
menyambung ke server, server tidak tahu perangkat itu dipakai.

Cara pakai:
    python tools/uji_kelemahan_lisensi.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "src"))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from akuntansi_id.core import license as LIS  # noqa: E402


def main() -> int:
    print("=" * 76)
    print("  UJI KELEMAHAN PENGIKATAN PERANGKAT")
    print("=" * 76)
    print()

    # ---------------------------------------------------------------- 1
    print("[Kelemahan 1: ciri perangkat yang mudah diubah]")
    print()
    print(f"  Nama komputer : {LIS._nama_komputer()}")
    print(f"  Nomor volume  : {LIS._nomor_volume()}")
    print(f"  Nomor prosesor: {LIS._nomor_prosesor()}")
    print(f"  Alamat MAC    : {LIS._alamat_mac()}")
    print()

    # Periksa mana yang berasal dari sumber yang dapat diubah pengguna.
    bahaya = []
    if LIS._nama_komputer():
        bahaya.append("nama komputer (dapat diganti siapa saja)")
    if LIS._alamat_mac():
        bahaya.append("alamat MAC (dapat dipalsukan perangkat lunak)")
    if not LIS._nomor_volume():
        bahaya.append("nomor volume KOSONG (tidak terbaca)")
    if not LIS._nomor_prosesor():
        bahaya.append("nomor prosesor KOSONG (tidak terbaca)")

    if bahaya:
        print("  CIRI YANG BERMASALAH:")
        for b in bahaya:
            print(f"    - {b}")
    else:
        print("  Seluruh ciri berasal dari sumber yang tidak mudah diubah.")

    print()
    print("  Uji: apakah sidik berubah bila nama komputer berubah?")
    sidik_sekarang = LIS.sidik_perangkat()

    # Tiru penggantian nama komputer dengan menimpa fungsi pembacanya.
    asli = LIS._nama_komputer
    try:
        LIS._nama_komputer = lambda: "NAMA-BUATAN-PENYERANG"
        sidik_buatan = LIS.sidik_perangkat()
    finally:
        LIS._nama_komputer = asli

    print(f"    sidik asli   : {sidik_sekarang[:32]}...")
    print(f"    sidik buatan : {sidik_buatan[:32]}...")
    if sidik_sekarang != sidik_buatan:
        print("    -> Sidik BERUBAH. Mengganti nama saja tidak cukup untuk")
        print("       meniru komputer asal, karena masih ada ciri lain.")
    else:
        print("    -> Sidik TIDAK berubah. Nama komputer tidak berpengaruh.")

    # ---------------------------------------------------------------- 2
    print()
    print("[Kelemahan 2: ciri mana yang paling menentukan]")
    print()
    # Uji satu per satu, ciri mana yang benar-benar membedakan perangkat.
    penting = []
    for nama, pengganti in (
        ("nama komputer", lambda: "XXX"),
        ("nomor volume", lambda: "0000-0000"),
        ("nomor prosesor", lambda: "0000000000000000"),
        ("alamat MAC", lambda: "0x0"),
    ):
        fungsi = {
            "nama komputer": "_nama_komputer",
            "nomor volume": "_nomor_volume",
            "nomor prosesor": "_nomor_prosesor",
            "alamat MAC": "_alamat_mac",
        }[nama]
        asli_f = getattr(LIS, fungsi)
        try:
            setattr(LIS, fungsi, pengganti)
            sidik_baru = LIS.sidik_perangkat()
        finally:
            setattr(LIS, fungsi, asli_f)

        beda = sidik_baru != sidik_sekarang
        tanda = "berpengaruh" if beda else "TIDAK berpengaruh"
        print(f"    {nama:16s}: {tanda}")
        if beda:
            penting.append(nama)

    print()
    print("  Ciri yang benar-benar membedakan perangkat:")
    for c in penting:
        print(f"    - {c}")

    # ---------------------------------------------------------------- 3
    print()
    print("[Kelemahan 3: berapa ciri yang harus ditiru penyerang]")
    print()
    mudah = [c for c in penting if c in ("nama komputer", "alamat MAC")]
    sulit = [c for c in penting if c not in ("nama komputer", "alamat MAC")]
    print(f"  Ciri mudah ditiru : {len(mudah)} ({', '.join(mudah) or 'tidak ada'})")
    print(f"  Ciri sulit ditiru : {len(sulit)} ({', '.join(sulit) or 'tidak ada'})")
    print()

    if len(sulit) >= 1:
        print("  KESIMPULAN: penyerang harus meniru ciri yang sulit diubah")
        print("  (nomor volume atau nomor prosesor), sehingga menyalin lisensi")
        print("  ke komputer lain tidak cukup hanya dengan mengganti nama.")
    else:
        print("  KESIMPULAN: SELURUH ciri dapat ditiru dengan mudah.")
        print("  Pengikatan perangkat perlu diperkuat.")

    # ---------------------------------------------------------------- 4
    print()
    print("[Kelemahan 4: pemakaian tanpa internet]")
    print()
    print("  Setelah aktivasi, aplikasi berjalan tanpa jaringan.")
    print("  Server baru mengetahui perangkat kedua saat perangkat itu")
    print("  menyambung untuk aktivasi atau pemeriksaan berkala.")
    print()
    print("  Yang membatasi: server menolak aktivasi ke-2 pada paket Standar")
    print("  (max_device = 1), sehingga penyerang harus melepas perangkat")
    print("  pertama lebih dulu, dan tindakan itu tercatat di jejak server.")

    print()
    print("=" * 76)
    return 0


if __name__ == "__main__":
    sys.exit(main())
