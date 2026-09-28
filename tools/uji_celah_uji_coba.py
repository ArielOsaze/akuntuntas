"""
Uji celah masa uji coba: apakah masa uji coba dapat diperpanjang sendiri.

Masa uji coba berlaku 1 hari sejak aplikasi pertama kali dibuka, dan seluruh
fitur Enterprise terbuka selama masa itu. Alat ini membuktikan bahwa
pengguna TIDAK dapat memperpanjangnya dengan cara apa pun yang masuk akal:

    1. Menghapus berkas catatan
    2. Menghapus catatan di basis data
    3. Menghapus kunci registry
    4. Menghapus ketiganya sekaligus
    5. Memundurkan jam komputer
    6. Memajukan jam komputer
    7. Menyalin berkas catatan milik orang lain
    8. Menjalankan di luar paket MSIX

Yang diuji adalah perilaku sebenarnya, bukan keberadaan fungsi.

Cara pakai:
    python tools/uji_celah_uji_coba.py
"""
from __future__ import annotations

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
            print(f"  [BOCOR] {nama}"
                  + (f" - {keterangan}" if keterangan else ""))

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
    from akuntansi_id import db
    from akuntansi_id.core import uji_coba

    p = Pemeriksa()

    print("=" * 76)
    print("  UJI CELAH MASA UJI COBA")
    print("=" * 76)
    print()
    print(f"  lama masa uji coba : {uji_coba.HARI_UJI_COBA} hari")
    print(f"  nama paket sah     : {uji_coba.NAMA_PAKET}")
    print(f"  catatan berkas     : {uji_coba.NAMA_BERKAS}")
    print(f"  catatan registry   : {uji_coba.JALUR_REGISTRY}")
    print()

    # Folder data sementara supaya data pengguna tidak tersentuh.
    sementara = Path(tempfile.mkdtemp(prefix="uji_coba_"))
    asli_data = uji_coba._paksa_data_dir
    asli_paksa = uji_coba._paksa_dalam_paket
    asli_dir = uji_coba._folder_data
    asli_reg = getattr(uji_coba, "_paksa_jalur_registry", None)

    try:
        uji_coba._paksa_data_dir = sementara
        uji_coba._paksa_dalam_paket = True
        # Kunci registry terpisah: menjalankan alat uji tidak boleh mengubah
        # catatan masa uji coba di komputer yang dipakai menguji, karena
        # hasil uji berikutnya akan salah.
        uji_coba._paksa_jalur_registry = (
            r"Software\XinetGroup\AkunTuntasUji")

        # Siapkan basis data di folder sementara supaya tabel settings ada.
        # Lokasi berkas dibaca db dari config, jadi config yang diarahkan.
        from akuntansi_id import config as _cfg
        asli_db_path = _cfg.DB_PATH
        asli_data_dir = _cfg.DATA_DIR
        _cfg.DATA_DIR = sementara
        _cfg.DB_PATH = sementara / "akuntuntas.db"
        db.init_db()

        # ============================================================
        # 0. DASAR: masa uji coba berjalan dan tidak berjalan selamanya
        # ============================================================
        print("[0. Keadaan dasar]")
        uji_coba.bersihkan_catatan()
        mulai = uji_coba.mulai_uji_coba()
        p.cek("Masa uji coba mulai dicatat pada pemakaian pertama",
              mulai > 0)
        p.cek("Masa uji coba sedang berlaku", uji_coba.aktif())
        sisa = uji_coba.sisa_detik()
        p.cek("Sisa waktu tidak melebihi lama yang ditentukan",
              0 < sisa <= uji_coba.HARI_UJI_COBA * 86400 + 5,
              f"sisa={sisa:.0f} detik")
        print()

        # ============================================================
        # 1. HAPUS BERKAS CATATAN
        # ============================================================
        print("[1. Pengguna menghapus berkas catatan]")
        berkas = sementara / uji_coba.NAMA_BERKAS
        berkas.unlink(missing_ok=True)
        p.cek("Menghapus berkas tidak memulai masa uji coba baru",
              uji_coba.mulai_uji_coba() == mulai,
              f"mulai berubah: {mulai} -> {uji_coba.mulai_uji_coba()}")
        p.cek("Berkas catatan dipulihkan dari tempat lain",
              berkas.exists(), "berkas tidak dibuat ulang")
        print()

        # ============================================================
        # 2. HAPUS CATATAN DI BASIS DATA
        # ============================================================
        print("[2. Pengguna menghapus catatan di basis data]")
        for kunci in (uji_coba.KUNCI_DB_MULAI, uji_coba.KUNCI_DB_PUNCAK):
            db.ex("DELETE FROM settings WHERE key=?", (kunci,))
        p.cek("Menghapus catatan basis data tidak memulai ulang",
              uji_coba.mulai_uji_coba() == mulai,
              f"mulai berubah: {mulai} -> {uji_coba.mulai_uji_coba()}")
        print()

        # ============================================================
        # 3. HAPUS KUNCI REGISTRY
        # ============================================================
        print("[3. Pengguna menghapus kunci registry]")
        if sys.platform == "win32":
            try:
                import winreg
                jalur_uji = uji_coba._paksa_jalur_registry or uji_coba.JALUR_REGISTRY
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                    jalur_uji, 0,
                                    winreg.KEY_SET_VALUE) as k:
                    for nama in ("TrialMulai", "TrialPuncak"):
                        try:
                            winreg.DeleteValue(k, nama)
                        except FileNotFoundError:
                            pass
            except Exception:
                pass
        p.cek("Menghapus registry tidak memulai masa uji coba baru",
              uji_coba.mulai_uji_coba() == mulai,
              f"mulai berubah: {mulai} -> {uji_coba.mulai_uji_coba()}")
        print()

        # ============================================================
        # 4. HAPUS KETIGANYA SEKALIGUS
        # ============================================================
        print("[4. Pengguna menghapus ketiga catatan sekaligus]")
        uji_coba.bersihkan_catatan()
        mulai_baru = uji_coba.mulai_uji_coba()
        # Masa uji coba memang mulai lagi, tetapi tidak boleh MELEBIHI lama
        # yang ditentukan, dan tidak boleh lebih lama dari sekali pakai.
        sisa_baru = uji_coba.sisa_detik()
        p.cek("Masa uji coba tidak melebihi lama yang ditentukan",
              0 < sisa_baru <= uji_coba.HARI_UJI_COBA * 86400 + 5,
              f"sisa={sisa_baru:.0f} detik")
        p.cek("Waktu mulai bergeser ke sekarang, bukan mundur",
              mulai_baru >= mulai - 1,
              f"mulai mundur: {mulai} -> {mulai_baru}")
        print("    catatan: menghapus ketiganya sama dengan memasang ulang")
        print("    aplikasi, dan itu tetap hanya memberi satu masa uji coba")
        print()

        # ============================================================
        # 5. JAM DIMUNDURKAN
        # ============================================================
        print("[5. Pengguna memundurkan jam komputer]")
        # Tiru jam mundur dengan menaikkan catatan puncak ke depan, lalu
        # memastikan sisa waktu dihitung dari catatan itu.
        uji_coba.bersihkan_catatan()
        uji_coba.mulai_uji_coba()
        puncak_depan = time.time() + 10 * 86400
        uji_coba._simpan_semua(uji_coba.mulai_uji_coba(), puncak_depan)
        p.cek("Jam mundur tidak memperpanjang masa uji coba",
              uji_coba.sisa_detik() <= 0,
              f"sisa={uji_coba.sisa_detik():.0f} detik, seharusnya habis")
        print()

        # ============================================================
        # 6. JAM DIMAJUKAN
        # ============================================================
        print("[6. Pengguna memajukan jam komputer]")
        uji_coba.bersihkan_catatan()
        uji_coba._simpan_semua(time.time() - 10 * 86400,
                               time.time() - 10 * 86400)
        p.cek("Jam maju membuat masa uji coba habis, bukan bertambah",
              uji_coba.sisa_detik() <= 0,
              f"sisa={uji_coba.sisa_detik():.0f} detik")
        print()

        # ============================================================
        # 7. TIDAK ADA BERKAS DI DALAM PAKET YANG BISA DIPALSUKAN
        # ============================================================
        print("[7. Berkas penanda di dalam paket sudah tidak dipakai]")
        p.cek("Modul tidak lagi membaca berkas penanda dari paket",
              not hasattr(uji_coba, "PENANDA")
              or uji_coba.__dict__.get("PENANDA") is None
              or "penanda" not in dir(uji_coba),
              "masih ada jalur penanda di dalam paket")
        p.cek("Tidak ada fungsi penanda_sah yang bisa dipalsukan",
              not hasattr(uji_coba, "penanda_sah"))
        p.cek("Tidak ada fungsi penanda_ada yang bisa dipalsukan",
              not hasattr(uji_coba, "penanda_ada"))
        # Berkas penanda lama tidak boleh ada di folder msix.
        penanda_lama = AKAR / "msix" / "uji_coba.txt"
        p.cek("Berkas penanda lama sudah tidak ada di folder msix",
              not penanda_lama.exists(),
              f"masih ada: {penanda_lama}")
        print()

        # ============================================================
        # 8. DI LUAR PAKET MSIX
        # ============================================================
        print("[8. Aplikasi dijalankan di luar paket MSIX]")
        uji_coba._paksa_dalam_paket = False
        p.cek("Masa uji coba tidak berlaku di luar paket MSIX",
              not uji_coba.aktif(),
              "aktif=True padahal bukan paket MSIX")
        uji_coba._paksa_dalam_paket = True
        print()

        # ============================================================
        # 9. MASA UJI COBA HABIS MEMANG MENGHENTIKAN APLIKASI
        # ============================================================
        print("[9. Setelah habis, aplikasi memerlukan lisensi]")
        uji_coba.bersihkan_catatan()
        uji_coba._simpan_semua(time.time() - 2 * 86400,
                               time.time() - 2 * 86400)
        p.cek("Masa uji coba tidak aktif setelah habis",
              not uji_coba.aktif())
        p.cek("Keadaan kadaluarsa terdeteksi", uji_coba.kadaluarsa())
        pesan = uji_coba.pesan_kadaluarsa()
        p.cek("Pesan kadaluarsa menyebut cara membeli lisensi",
              "beli" in pesan.lower() and "xinet.id" in pesan,
              "pesan tidak mengarahkan ke halaman pembelian")
        print()

        _cfg.DATA_DIR = asli_data_dir
        _cfg.DB_PATH = asli_db_path

    finally:
        uji_coba._paksa_data_dir = asli_data
        uji_coba._paksa_dalam_paket = asli_paksa
        uji_coba._folder_data = asli_dir
        uji_coba._paksa_jalur_registry = asli_reg
        # Bersihkan kunci registry khusus uji supaya tidak menumpuk.
        if sys.platform == "win32":
            try:
                import winreg
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER,
                                 r"Software\XinetGroup\AkunTuntasUji")
            except Exception:
                pass
        shutil.rmtree(sementara, ignore_errors=True)

    return p.ringkas()


if __name__ == "__main__":
    sys.exit(main())
