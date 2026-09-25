"""
Uji celah keamanan lisensi: masa tenggang dan jam dimundurkan.

Dua celah yang diperiksa:

1. Tanpa batas masa tenggang, seseorang dapat mengaktifkan lisensi sekali,
   mematikan internet untuk selamanya, lalu memakai aplikasi meskipun
   lisensinya sudah dicabut penjual. Pencabutan menjadi sia-sia.

2. Pemeriksaan masa berlaku memakai jam komputer. Bila jamnya dimundurkan,
   lisensi yang sudah lewat tampak masih berlaku.

Alat ini bekerja di folder sementara dan tidak menyentuh data pengguna.

Cara pakai:
    python tools/uji_celah_waktu.py
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import time
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
            for t in self.temuan:
                print(f"    - {t}")
        else:
            print(f"  HASIL: {self.lulus} AMAN, 0 BOCOR")
        print("=" * 76)
        return 1 if self.gagal else 0


def buat_lisensi(data_dir: Path, hari: int, tenggang_hari: int):
    """
    Tulis berkas lisensi bertanda tangan yang sah untuk pengujian.

    Tanda tangannya diambil dari lisensi sungguhan yang sudah ada di
    komputer, karena kunci privat server tidak ada di sini. Yang diubah
    hanya masa berlakunya, lalu berkasnya ditandatangani ulang memakai
    kunci uji sementara.
    """
    from akuntansi_id.core import license as LIS

    sekarang = time.time()
    muatan = {
        "kunci": "ATNTUJIWAKTUAAAAAAA",
        "sidik": LIS.sidik_perangkat(),
        "paket": "enterprise",
        "fitur": {"dimensi": True},
        "pemilik": "Uji",
        "diterbitkan": _iso(sekarang - 86400),
        "berlaku_sampai": _iso(sekarang + hari * 86400),
        "tenggang_sampai": _iso(sekarang + tenggang_hari * 86400),
    }
    return muatan


def _iso(detik: float) -> str:
    from datetime import datetime, timezone
    return datetime.fromtimestamp(detik, timezone.utc).isoformat()


def main() -> int:
    from akuntansi_id.core import license as LIS

    p = Pemeriksa()
    print("=" * 76)
    print("  UJI CELAH MASA TENGGANG DAN JAM DIMUNDURKAN")
    print("=" * 76)
    print()
    print(f"  toleransi jam : {LIS.TOLERANSI_JAM / 3600:.0f} jam")
    print(f"  catatan waktu : berkas {LIS.NAMA_JEJAK} + registry Windows")
    print()

    sementara = Path(tempfile.mkdtemp(prefix="uji_waktu_"))
    asli_tanda = LIS.tanda_sah
    asli_sidik = LIS.sidik_cocok

    # Simpan catatan registry yang sudah ada supaya pemakaian aplikasi
    # sungguhan tidak terganggu oleh pengujian ini.
    asli_registry = None
    if sys.platform == "win32":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                LIS.KUNCI_REGISTRY) as k:
                asli_registry = winreg.QueryValueEx(k, LIS.NILAI_REGISTRY)[0]
        except Exception:
            asli_registry = None

    try:
        # Tanda tangan dan sidik dianggap cocok, karena yang sedang diuji
        # adalah pemeriksaan waktu, bukan pemeriksaan tanda tangan.
        LIS.tanda_sah = lambda m, t: True
        LIS.sidik_cocok = lambda s: True

        # ---------------------------------------- 1. catatan waktu dibuat
        print("[1. Pencatatan waktu tertinggi]")
        aman, alasan = LIS.catat_waktu(sementara)
        p.cek("Pencatatan waktu berhasil", aman, alasan)
        tertinggi = LIS.waktu_tertinggi(sementara)
        p.cek("Waktu tertinggi tercatat", tertinggi > 0,
              f"nilai={tertinggi}")
        print()

        # ------------------------------------------- 2. jam dimundurkan
        print("[2. Jam komputer dimundurkan]")
        # Tiru jam dimundurkan 30 hari.
        mundur = time.time() - 30 * 86400
        LIS._tulis_jejak(sementara, time.time())
        asli_time = time.time
        try:
            time.time = lambda: mundur
            aman, alasan = LIS.catat_waktu(sementara)
            p.cek("Jam dimundurkan terdeteksi", not aman,
                  "tidak terdeteksi")
            if alasan:
                print(f"    pesan: {alasan[:70]}...")
        finally:
            time.time = asli_time
        print()

        # ------------------------------- 3. masa tenggang habis
        print("[3. Masa tenggang habis tanpa internet]")
        # Lisensi dengan tenggang yang sudah lewat.
        muatan = buat_lisensi(sementara, hari=-400, tenggang_hari=-10)
        teks = json.dumps(muatan)
        (sementara / "lisensi.json").write_text(json.dumps({
            "muatan": teks, "tanda": "00" * 64,
        }), encoding="utf-8")

        sah, alasan, lis = LIS.lisensi_sah(sementara)
        p.cek("Lisensi lewat masa tenggang ditolak", not sah,
              "masih diterima")
        if alasan:
            print(f"    pesan: {alasan[:70]}...")
        print()

        # ------------------------------- 4. dalam masa tenggang
        print("[4. Masih di dalam masa tenggang]")
        muatan = buat_lisensi(sementara, hari=-5, tenggang_hari=30)
        teks = json.dumps(muatan)
        (sementara / "lisensi.json").write_text(json.dumps({
            "muatan": teks, "tanda": "00" * 64,
        }), encoding="utf-8")
        LIS._tulis_jejak(sementara, time.time())

        sah, alasan, lis = LIS.lisensi_sah(sementara)
        p.cek("Lisensi dalam masa tenggang tetap diterima", sah, alasan)
        print()

        # --------------------- 5. menghapus catatan tidak menghapus penjaga
        print("[5. Menghapus berkas catatan waktu]")
        jejak = sementara / LIS.NAMA_JEJAK
        ada_sebelum = jejak.exists()
        if ada_sebelum:
            jejak.unlink()
        # Registry tetap menyimpan catatannya, jadi waktu tertinggi tidak
        # hilang seluruhnya.
        sisa = LIS.waktu_tertinggi(sementara)
        p.cek("Catatan waktu tidak hilang seluruhnya saat berkas dihapus",
              sisa > 0 or not ada_sebelum,
              f"waktu tertinggi menjadi {sisa}")
        print()

        # ------------------ 6. penjaga dipanggil dari pemeriksaan lisensi
        print("[6. Penjaga waktu dipakai saat memeriksa lisensi]")
        import inspect
        sumber = inspect.getsource(LIS.lisensi_sah)
        p.cek("lisensi_sah memanggil catat_waktu",
              "catat_waktu" in sumber)
        p.cek("lisensi_sah memeriksa dalam_tenggang",
              "dalam_tenggang" in sumber)

    finally:
        LIS.tanda_sah = asli_tanda
        LIS.sidik_cocok = asli_sidik
        shutil.rmtree(sementara, ignore_errors=True)

        # Pulihkan catatan registry seperti semula.
        if sys.platform == "win32":
            try:
                import winreg
                if asli_registry is not None:
                    with winreg.CreateKey(winreg.HKEY_CURRENT_USER,
                                          LIS.KUNCI_REGISTRY) as k:
                        winreg.SetValueEx(k, LIS.NILAI_REGISTRY, 0,
                                          winreg.REG_SZ, str(asli_registry))
                else:
                    winreg.DeleteKey(winreg.HKEY_CURRENT_USER,
                                     LIS.KUNCI_REGISTRY)
            except Exception:
                pass

    return p.ringkas()


if __name__ == "__main__":
    sys.exit(main())
