"""
Uji celah keamanan lisensi: apakah mode uji coba dapat dinyalakan sendiri.

Mode uji coba disediakan untuk peninjau Microsoft Store dan memberi seluruh
fitur Enterprise. Bila penandanya cukup berupa berkas kosong di sebelah
aplikasi, siapa pun dapat membuatnya sendiri dan memakai aplikasi penuh
tanpa membeli lisensi. Alat ini membuktikan apakah celah itu ada.

Cara pakai:
    python tools/uji_celah_uji_coba.py
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "src"))


class Pemeriksa:
    def __init__(self):
        self.lulus = 0
        self.gagal = 0
        self.temuan: list[str] = []

    def cek(self, nama: str, aman: bool, keterangan: str = ""):
        if aman:
            self.lulus += 1
            print(f"  [AMAN]  {nama}")
        else:
            self.gagal += 1
            self.temuan.append(nama)
            print(f"  [BOCOR] {nama}" + (f" — {keterangan}" if keterangan else ""))

    def ringkas(self) -> int:
        print()
        print("=" * 76)
        if self.gagal:
            print(f"  HASIL: {self.lulus} AMAN, {self.gagal} BOCOR")
            print()
            print("  Celah yang perlu ditutup:")
            for t in self.temuan:
                print(f"    - {t}")
        else:
            print(f"  HASIL: {self.lulus} AMAN, 0 BOCOR")
        print("=" * 76)
        return 1 if self.gagal else 0


def main() -> int:
    from akuntansi_id.core import uji_coba

    p = Pemeriksa()

    print("=" * 76)
    print("  UJI CELAH MODE UJI COBA")
    print("=" * 76)
    print()
    print(f"  nama berkas penanda : {uji_coba.PENANDA}")
    print(f"  nama paket sah      : {uji_coba.NAMA_PAKET}")
    print(f"  lama berlaku        : {uji_coba.HARI_UJI_COBA} hari")
    print()

    sementara = Path(tempfile.mkdtemp(prefix="uji_coba_"))
    asli_tempat = uji_coba._tempat_penanda
    asli_paksa = uji_coba._paksa_dalam_paket

    try:
        # -------------------------------------------- 1. berkas kosong
        print("[1. Berkas kosong buatan sendiri]")
        (sementara / uji_coba.PENANDA).write_text("", encoding="utf-8")
        uji_coba._tempat_penanda = lambda: [sementara]
        uji_coba._paksa_dalam_paket = True

        sah, alasan = uji_coba.penanda_sah()
        p.cek("Berkas kosong ditolak", not sah, alasan)
        p.cek("Berkas kosong tidak menyalakan mode uji coba",
              not uji_coba.aktif(), "aktif=True")
        print()

        # ---------------------------------------- 2. berkas tanpa tanda
        print("[2. Berkas dengan isi buatan sendiri]")
        (sementara / uji_coba.PENANDA).write_text(json.dumps({
            "muatan": json.dumps({"uji_coba": True, "berlaku_sampai": "2099-01-01"}),
            "tanda": "00" * 64,
        }), encoding="utf-8")
        sah, alasan = uji_coba.penanda_sah()
        p.cek("Tanda tangan palsu ditolak", not sah, alasan)
        p.cek("Tanda tangan palsu tidak menyalakan mode uji coba",
              not uji_coba.aktif(), "aktif=True")
        print()

        # ------------------------------------ 3. di luar paket MSIX
        print("[3. Aplikasi dijalankan di luar paket MSIX]")
        # Penanda sah tapi aplikasi tidak berjalan di dalam paket MSIX.
        # Tiru dengan mematikan paksaan dan memakai berkas nyata.
        penanda_nyata = AKAR / "msix" / uji_coba.PENANDA
        if penanda_nyata.exists():
            uji_coba._tempat_penanda = lambda: [AKAR / "msix"]
            uji_coba._paksa_dalam_paket = False
            p.cek("Penanda sah tidak berlaku di luar paket MSIX",
                  not uji_coba.aktif(),
                  "aktif=True padahal bukan paket MSIX")
        else:
            # Belum ada penanda sah; tiru keadaan itu dengan berkas bertanda
            # tangan yang dibuat khusus untuk pemeriksaan ini.
            uji_coba._paksa_dalam_paket = False
            p.cek("Aplikasi dari installer biasa tidak dianggap paket MSIX",
                  not uji_coba.dalam_paket_msix(),
                  "dalam_paket_msix=True")
        print()

        # ------------------------------- 4. masa berlaku dari penanda
        print("[4. Masa berlaku dibaca dari penanda, bukan catatan lokal]")
        ada_catatan = hasattr(uji_coba, "_mulai_dihitung")
        p.cek("Catatan waktu mulai di komputer tidak lagi dipakai",
              not ada_catatan,
              "masih memakai _mulai_dihitung yang dapat dihapus pengguna")
        p.cek("Sisa hari dibaca dari penanda bertanda tangan",
              "sisa_hari" in dir(uji_coba))
        print()

        # ------------------------------------- 5. penanda sah dari server
        print("[5. Penanda sah dari server (bila sudah diterbitkan)]")
        if penanda_nyata.exists():
            uji_coba._tempat_penanda = lambda: [AKAR / "msix"]
            uji_coba._paksa_dalam_paket = True
            sah, alasan = uji_coba.penanda_sah()
            p.cek("Penanda terbitan server diterima", sah, alasan)
            if sah:
                print(f"    sisa hari: {uji_coba.sisa_hari()}")
            # Di luar paket MSIX, penanda sah pun tidak boleh berlaku.
            uji_coba._paksa_dalam_paket = False
            p.cek("Penanda sah tetap tidak berlaku di luar paket MSIX",
                  not uji_coba.aktif(), "aktif=True")
        else:
            print("    belum ada penanda; lewati")
            print("    terbitkan dengan: python tools/terbitkan_uji_coba.py")

    finally:
        uji_coba._tempat_penanda = asli_tempat
        uji_coba._paksa_dalam_paket = asli_paksa
        shutil.rmtree(sementara, ignore_errors=True)

    return p.ringkas()


if __name__ == "__main__":
    sys.exit(main())
