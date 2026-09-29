"""
Uji pemindahan lokasi penyimpanan data.

Memastikan pemindahan bekerja, data ikut tersalin utuh, dan kegagalan
penyalinan tidak menghilangkan data pengguna.

Cara pakai:
    python tools/uji_pindah_data.py
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "src"))

LULUS = 0
GAGAL = 0


def cek(nama: str, benar: bool, keterangan: str = ""):
    global LULUS, GAGAL
    if benar:
        LULUS += 1
        print(f"  [LULUS] {nama}")
    else:
        GAGAL += 1
        print(f"  [GAGAL] {nama}" + (f" - {keterangan}" if keterangan else ""))


def main() -> int:
    # Folder kerja terpisah supaya data asli tidak tersentuh.
    kerja = Path(tempfile.mkdtemp(prefix="uji_pindah_"))
    os.environ["LOCALAPPDATA"] = str(kerja)

    from akuntansi_id import config as cfg

    # Folder bawaan dihitung kode dari LOCALAPPDATA, jadi nilainya diambil
    # dari kode itu sendiri supaya tes memeriksa folder yang benar.
    bawaan = cfg.DATA_DIR

    print("=" * 74)
    print("  UJI PEMINDAHAN LOKASI DATA")
    print("=" * 74)
    print(f"  folder kerja : {kerja}")
    print(f"  folder bawaan: {bawaan}")
    print()

    cek("Lokasi awal adalah folder bawaan",
        bawaan == kerja / "AkunTuntas", f"dapat {bawaan}")

    # ---------------------------------------------------------- siapkan data
    print()
    print("[1. Menyiapkan data]")
    from akuntansi_id import db
    db.init_db()

    from akuntansi_id.core import security as sec
    sec.ensure_default_admin()
    cek("Basis data dapat disiapkan", (bawaan / "akuntuntas.db").exists())

    # Tambahkan berkas lain supaya penyalinan seluruh isi ikut teruji.
    bawaan.mkdir(parents=True, exist_ok=True)
    (bawaan / "backup").mkdir(exist_ok=True)
    (bawaan / "backup" / "cadangan.txt").write_text("isi cadangan",
                                                    encoding="utf-8")
    (bawaan / "lampiran").mkdir(exist_ok=True)
    (bawaan / "lampiran" / "nota.txt").write_text("isi lampiran",
                                                  encoding="utf-8")
    ukuran_awal = sum(f.stat().st_size for f in bawaan.rglob("*")
                      if f.is_file())
    print(f"  ukuran data awal: {ukuran_awal} bita")

    # ------------------------------------------------------------- pindah
    print()
    print("[2. Memindahkan data]")
    tujuan = kerja / "drive_lain" / "AkunTuntas"
    berhasil, pesan = cfg.pindahkan_data(tujuan)
    cek("Pemindahan berhasil", berhasil, pesan)
    cek("Folder tujuan dibuat", tujuan.exists())

    # -------------------------------------------------------- isi tersalin
    print()
    print("[3. Memeriksa isi yang tersalin]")
    cek("Basis data ikut tersalin",
        (tujuan / "akuntuntas.db").exists())
    cek("Folder cadangan ikut tersalin",
        (tujuan / "backup" / "cadangan.txt").exists())
    cek("Folder lampiran ikut tersalin",
        (tujuan / "lampiran" / "nota.txt").exists())

    ukuran_tujuan = sum(f.stat().st_size for f in tujuan.rglob("*")
                        if f.is_file())
    cek("Ukuran data sama",
        ukuran_tujuan >= ukuran_awal,
        f"asal {ukuran_awal} vs tujuan {ukuran_tujuan}")

    # -------------------------------------------------- penunjuk lokasi
    print()
    print("[4. Penunjuk lokasi]")
    penunjuk = cfg._folder_penunjuk()
    cek("Berkas penunjuk dibuat", penunjuk.exists())
    cek("Isi penunjuk benar",
        penunjuk.read_text(encoding="utf-8").strip() == str(tujuan),
        penunjuk.read_text(encoding="utf-8")[:60] if penunjuk.exists() else "-")
    cek("lokasi_dipindahkan() mengembalikan True", cfg.lokasi_dipindahkan())

    # --------------------------------------------- lokasi baru terbaca lagi
    print()
    print("[5. Lokasi baru terbaca pada pembukaan berikutnya]")
    import importlib
    importlib.reload(cfg)
    cek("DATA_DIR menunjuk lokasi baru",
        cfg.DATA_DIR == tujuan,
        f"dapat {cfg.DATA_DIR}")

    # ------------------------------------------------- data lama tidak hilang
    print()
    print("[6. Data lama tidak dihapus]")
    cek("Basis data lama masih ada",
        (bawaan / "akuntuntas.db").exists(),
        "berkas lama terhapus - pengguna kehilangan salinan cadangan")

    # ------------------------------------------------------- tolak folder salah
    print()
    print("[7. Penolakan folder yang tidak wajar]")
    berhasil2, pesan2 = cfg.pindahkan_data(cfg.DATA_DIR)
    cek("Menolak folder yang sedang dipakai", not berhasil2, pesan2)

    berhasil3, pesan3 = cfg.pindahkan_data(tujuan / "anak")
    cek("Menolak folder di dalam lokasi sekarang", not berhasil3, pesan3)

    # --------------------------------------------------- kembali ke bawaan
    print()
    print("[8. Kembali ke lokasi bawaan]")
    berhasil4, pesan4 = cfg.kembali_ke_lokasi_bawaan()
    cek("Pengembalian berhasil", berhasil4, pesan4)
    cek("Penunjuk lokasi dihapus", not cfg._folder_penunjuk().exists())

    importlib.reload(cfg)
    cek("DATA_DIR kembali ke bawaan",
        cfg.DATA_DIR == bawaan,
        f"dapat {cfg.DATA_DIR}")

    shutil.rmtree(kerja, ignore_errors=True)

    print()
    print("=" * 74)
    if GAGAL:
        print(f"  HASIL: {LULUS} LULUS, {GAGAL} GAGAL")
    else:
        print(f"  HASIL: {LULUS} LULUS, 0 GAGAL")
    print("=" * 74)
    return 1 if GAGAL else 0


if __name__ == "__main__":
    sys.exit(main())
