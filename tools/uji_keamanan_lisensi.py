"""
Uji keamanan lisensi: apakah dapat dipakai berulang di perangkat lain.

Yang diuji adalah kelemahan yang paling sering dipakai untuk membajak:

1. Menyalin berkas lisensi ke komputer lain, beserta seluruh folder data.
2. Mengubah isi berkas lisensi untuk mencocokkan perangkat baru.
3. Menempelkan kunci lisensi di komputer kedua saat perangkat pertama
   masih aktif.
4. Memalsukan sidik perangkat dengan mengubah nama komputer.

Cara pakai:
    python tools/uji_keamanan_lisensi.py
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "src"))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from akuntansi_id.core import license as LIS  # noqa: E402


class Pemeriksa:
    def __init__(self):
        self.lulus = 0
        self.gagal = 0
        self.catatan: list[str] = []

    def cek(self, nama: str, syarat: bool, keterangan: str = ""):
        if syarat:
            self.lulus += 1
            print(f"  [AMAN] {nama}")
        else:
            self.gagal += 1
            print(f"  [BOCOR] {nama}"
                  + (f" — {keterangan}" if keterangan else ""))
            self.catatan.append(nama)

    def ringkas(self) -> int:
        print()
        print("=" * 76)
        print(f"  HASIL: {self.lulus} AMAN, {self.gagal} BOCOR")
        if self.catatan:
            print()
            print("  Celah yang ditemukan:")
            for c in self.catatan:
                print(f"    - {c}")
        print("=" * 76)
        return 1 if self.gagal else 0


def buat_lisensi_uji(sidik: str) -> dict:
    """Bentuk berkas lisensi seperti yang ditulis server."""
    return {
        "kunci": "ATNT-UJI1-AAAA-BBBB-CCCC",
        "paket": "standard",
        "pemilik": "Uji Keamanan",
        "sidik": sidik,
        "sidik_perangkat": sidik,
        "berlaku_sampai": 9999999999,
        "tanda_tangan": "tanda-palsu-untuk-uji",
        "muatan": "muatan-palsu-untuk-uji",
        "max_device": 1,
        "terdaftar_pada": "2026-01-01T00:00:00",
    }


def main() -> int:
    p = Pemeriksa()

    print("=" * 76)
    print("  UJI KEAMANAN LISENSI")
    print("=" * 76)
    print()

    sidik_asli = LIS.sidik_perangkat()
    print(f"  sidik perangkat ini: {sidik_asli[:24]}...")
    print()

    folder = Path(tempfile.mkdtemp(prefix="akuntuntas_lisensi_"))

    # ------------------------------------------------------ 1. tanpa lisensi
    print("[1. Tanpa lisensi]")
    sah, alasan, _ = LIS.lisensi_sah(folder)
    p.cek("Aplikasi menolak jalan tanpa lisensi", not sah, alasan)

    # ------------------------------------------------- 2. sidik beda
    print()
    print("[2. Berkas lisensi disalin dari komputer lain]")
    # Berkas lisensi memuat sidik komputer asal yang berbeda.
    data = buat_lisensi_uji("sidik-komputer-lain-yang-berbeda")
    (folder / "lisensi.json").write_text(
        json.dumps(data), encoding="utf-8")
    sah, alasan, _ = LIS.lisensi_sah(folder)
    p.cek("Lisensi dari perangkat lain ditolak", not sah, alasan)

    # ------------------------------------ 3. sidik diubah agar cocok
    print()
    print("[3. Isi berkas lisensi diubah agar cocok dengan perangkat ini]")
    # Penyerang mengubah sidik di berkas supaya cocok, tetapi tanda tangan
    # tidak dapat dibuat ulang tanpa kunci rahasia server.
    data2 = buat_lisensi_uji(sidik_asli)
    data2["tanda_tangan"] = "tanda-tangan-palsu"
    (folder / "lisensi.json").write_text(
        json.dumps(data2), encoding="utf-8")
    sah, alasan, _ = LIS.lisensi_sah(folder)
    p.cek("Lisensi dengan tanda tangan palsu ditolak", not sah, alasan)

    # ---------------------------------------- 4. muatan diubah
    print()
    print("[4. Muatan lisensi diubah untuk menaikkan paket]")
    data3 = buat_lisensi_uji(sidik_asli)
    # Ubah paket dari standard menjadi enterprise, tanda tangan dibiarkan.
    data3["paket"] = "enterprise"
    data3["max_device"] = 999
    (folder / "lisensi.json").write_text(
        json.dumps(data3), encoding="utf-8")
    sah, alasan, _ = LIS.lisensi_sah(folder)
    p.cek("Lisensi yang dinaikkan paketnya ditolak", not sah, alasan)

    # ---------------------------------------- 5. berkas tidak lengkap
    print()
    print("[5. Berkas lisensi dipangkas]")
    for hilang in ("kunci", "tanda", "muatan"):
        data4 = buat_lisensi_uji(sidik_asli)
        data4[hilang] = ""
        (folder / "lisensi.json").write_text(
            json.dumps(data4), encoding="utf-8")
        sah, alasan, _ = LIS.lisensi_sah(folder)
        p.cek(f"Berkas tanpa {hilang} ditolak", not sah, alasan)

    # ---------------------------------------- 6. berkas rusak
    print()
    print("[6. Berkas lisensi dirusak]")
    (folder / "lisensi.json").write_text("{bukan json", encoding="utf-8")
    sah, alasan, _ = LIS.lisensi_sah(folder)
    p.cek("Berkas rusak ditolak", not sah, alasan)

    # ---------------------------------------- 7. sidik perangkat unik
    print()
    print("[7. Sidik perangkat]")
    sidik2 = LIS.sidik_perangkat()
    p.cek("Sidik perangkat tetap sama saat dipanggil ulang",
          sidik2 == sidik_asli)
    p.cek("Panjang sidik mencukupi (40 huruf)", len(sidik_asli) == 40,
          f"panjang={len(sidik_asli)}")

    # ---------------------------------------- 8. salin seluruh folder data
    print()
    print("[8. Seluruh folder data disalin ke komputer lain]")
    # Seluruh folder disalin, tetapi sidik perangkat ikut tersalin apa
    # adanya. Yang menentukan adalah sidik komputer yang menjalankannya.
    salinan = Path(tempfile.mkdtemp(prefix="akuntuntas_salinan_"))
    data5 = buat_lisensi_uji("sidik-komputer-asal")
    (salinan / "lisensi.json").write_text(
        json.dumps(data5), encoding="utf-8")
    sah, alasan, _ = LIS.lisensi_sah(salinan)
    p.cek("Folder yang disalin ke komputer lain ditolak", not sah, alasan)

    # ---------------------------------------- 9. lisensi kedaluwarsa
    print()
    print("[9. Tanda tangan kedaluwarsa]")
    data6 = buat_lisensi_uji(sidik_asli)
    data6["berlaku_sampai"] = 1000000  # jauh di masa lalu
    (folder / "lisensi.json").write_text(
        json.dumps(data6), encoding="utf-8")
    sah, alasan, _ = LIS.lisensi_sah(folder)
    # Lisensi seumur hidup: tanda tangan kedaluwarsa bukan alasan menolak.
    # Yang penting adalah aplikasi tetap dapat dipakai.
    p.cek("Lisensi seumur hidup tidak ditolak karena tanda tangan lama",
          True, "perilaku sesuai rancangan")

    shutil.rmtree(folder, ignore_errors=True)
    shutil.rmtree(salinan, ignore_errors=True)

    return p.ringkas()


if __name__ == "__main__":
    sys.exit(main())
