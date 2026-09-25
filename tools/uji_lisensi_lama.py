"""
Uji bahwa lisensi yang sudah aktif tetap diterima setelah pembaruan.

Yang diperiksa:

1. Aplikasi mengirim sidik yang sudah terdaftar ke server, bukan sidik
   baru. Tanpa ini, server menganggap perangkat ini perangkat baru.
2. Server sungguhan menerima sidik itu dan mengenali perangkatnya.
3. Sidik baru tetap ikut dikirim sebagai calon pengganti, supaya server
   yang sudah diperbarui dapat menaikkan pengikatan perangkat.

Alat ini memakai berkas lisensi yang benar-benar terpasang di komputer,
jadi hasilnya menggambarkan keadaan pelanggan sungguhan.

Cara pakai:
    python tools/uji_lisensi_lama.py
"""
from __future__ import annotations

import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "src"))

from akuntansi_id import config  # noqa: E402
from akuntansi_id.core import license as LIS  # noqa: E402


def main() -> int:
    print("=" * 76)
    print("  UJI LISENSI LAMA TETAP DITERIMA SETELAH PEMBARUAN")
    print("=" * 76)
    print()

    data_dir = config.DATA_DIR
    print(f"  folder data: {data_dir}")

    lisensi = LIS.muat(data_dir)
    if lisensi is None:
        print("  Lisensi belum terpasang di komputer ini.")
        print("  Uji ini memerlukan lisensi yang sudah aktif.")
        return 1

    print(f"  kunci      : {lisensi.kunci[:9]}...{lisensi.kunci[-4:]}")
    print(f"  paket      : {lisensi.paket}")
    print()

    # ------------------------------------------------- sidik yang dikirim
    print("[1. Sidik yang akan dikirim ke server]")
    sidik_kirim, sidik_baru = LIS._sidik_untuk_server(data_dir)
    terdaftar = lisensi.sidik
    baru = LIS.sidik_perangkat()
    lama = LIS.sidik_perangkat_versi_lama()

    print(f"  sidik terdaftar di berkas : {terdaftar}")
    print(f"  sidik yang dikirim        : {sidik_kirim}")
    print(f"  sidik terbaru             : {sidik_baru}")
    print()

    lulus = True
    if sidik_kirim != terdaftar:
        print("  GAGAL: yang dikirim bukan sidik terdaftar.")
        lulus = False
    else:
        print("  BENAR: yang dikirim adalah sidik terdaftar.")

    # Apakah sidik terdaftar termasuk yang dikenali aplikasi.
    if not LIS.sidik_cocok(terdaftar):
        print("  GAGAL: sidik terdaftar tidak dikenali aplikasi.")
        lulus = False
    else:
        print("  BENAR: sidik terdaftar dikenali aplikasi.")

    print()
    print("[2. Perbandingan sidik]")
    print(f"  sidik terbaru sama dengan versi lama? "
          f"{'ya' if baru == lama else 'tidak'}")
    print(f"  sidik terbaru sama dengan terdaftar? "
          f"{'ya' if baru == terdaftar else 'tidak'}")
    if baru != terdaftar:
        print("  Artinya: pengikatan perangkat dapat dinaikkan ke ciri yang")
        print("  lebih sukar ditiru tanpa mengubah pengenalan perangkat.")

    # ----------------------------------------------------- uji ke server
    print()
    print("[3. Uji ke server sungguhan (aksi verifikasi)]")
    from akuntansi_id.core.license import _kirim  # noqa: PLC0415

    terhubung, jawaban = _kirim({
        "aksi": "verifikasi",
        "kunci": lisensi.kunci,
        "sidik": sidik_kirim,
        "sidik_baru": sidik_baru,
        "nama_perangkat": LIS.nama_perangkat(),
        "os_info": LIS.info_sistem(),
        "versi_app": "1.0.3",
    })

    if not terhubung:
        print(f"  Server tidak dapat dihubungi: {jawaban.get('pesan')}")
        print("  (Uji ini memerlukan sambungan internet.)")
    else:
        ok = bool(jawaban.get("ok"))
        print(f"  jawaban server: ok={ok} "
              f"pesan={jawaban.get('pesan', '(diterima)')}")
        if ok:
            print("  BENAR: server mengenali perangkat ini.")
        else:
            print("  GAGAL: server menolak perangkat ini.")
            lulus = False

    print()
    print("=" * 76)
    print(f"  HASIL: {'LULUS' if lulus else 'GAGAL'}")
    print("=" * 76)
    return 0 if lulus else 1


if __name__ == "__main__":
    sys.exit(main())
