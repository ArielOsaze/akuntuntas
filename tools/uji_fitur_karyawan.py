"""
Uji menyeluruh fitur karyawan, dari menambah sampai menghapus.

Yang diuji bukan hanya fungsinya berjalan, tetapi juga datanya benar-benar
tersimpan dan muncul kembali, serta jejak auditnya tercatat. Fitur yang
hanya "tidak error" belum tentu benar.

Cara pakai:
    python tools/uji_fitur_karyawan.py
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent

# Data uji dibuat di folder sementara supaya data pengguna tidak tersentuh.
FOLDER = Path(tempfile.mkdtemp(prefix="akuntuntas_uji_"))
os.environ["AKUNTANSIID_DATA"] = str(FOLDER)

sys.path.insert(0, str(AKAR / "src"))

from akuntansi_id import db, services  # noqa: E402
from akuntansi_id.core import security as sec  # noqa: E402


class Pemeriksa:
    def __init__(self):
        self.lulus = 0
        self.gagal = 0
        self.catatan: list[str] = []

    def cek(self, nama: str, syarat: bool, keterangan: str = ""):
        if syarat:
            self.lulus += 1
            print(f"  [LULUS] {nama}")
        else:
            self.gagal += 1
            print(f"  [GAGAL] {nama}" + (f" — {keterangan}" if keterangan else ""))
            self.catatan.append(nama)

    def ringkas(self) -> int:
        print()
        print("=" * 74)
        print(f"  HASIL: {self.lulus} LULUS, {self.gagal} GAGAL")
        if self.catatan:
            print()
            print("  Yang gagal:")
            for c in self.catatan:
                print(f"    - {c}")
        print("=" * 74)
        return 1 if self.gagal else 0


def main() -> int:
    p = Pemeriksa()

    print("=" * 74)
    print("  UJI FITUR KARYAWAN")
    print("=" * 74)
    print()
    print(f"  data uji: {FOLDER}")
    print()

    # ---------------------------------------------------------------- siap
    print("[Persiapan]")
    # Skema basis data harus disiapkan lebih dulu. Tanpa ini, tabel users
    # belum ada dan seluruh pengujian berikutnya gagal.
    db.init_db()
    sec.ensure_default_admin()
    lis = type("L", (), {
        "enterprise": True, "paket": "enterprise",
        "punya": lambda self, x: True,
    })()
    cid = services.create_company("PT Uji Karyawan", "pt", lisensi=lis)
    p.cek("Perusahaan dibuat", cid > 0, f"id={cid}")

    # ------------------------------------------------------- tanpa perusahaan
    print()
    print("[Penjagaan: belum ada perusahaan]")
    try:
        services.simpan_karyawan(0, "Uji", 1000000)
        p.cek("Karyawan ditolak bila perusahaan tidak ada", False,
              "justru tersimpan")
    except Exception:
        p.cek("Karyawan ditolak bila perusahaan tidak ada", True)

    # ------------------------------------------------------------ tambah
    print()
    print("[Tambah karyawan]")
    try:
        eid = services.simpan_karyawan(
            cid, "Budi Santoso", 7500000, "Staf Akuntansi",
            status_ptkp="TK/0", tunjangan_tetap=500000,
            nik_npwp="3273010101900001", tanggal_masuk="2026-01-15")
        p.cek("Karyawan tersimpan", eid > 0, f"id={eid}")
    except Exception as e:
        p.cek("Karyawan tersimpan", False, str(e))
        return p.ringkas()

    # ------------------------------------------------------- data muncul
    print()
    print("[Data karyawan benar-benar muncul]")
    daftar = services.list_karyawan(cid)
    p.cek("Daftar karyawan tidak kosong", len(daftar) == 1,
          f"jumlah={len(daftar)}")

    if daftar:
        k = daftar[0]
        p.cek("Nama tersimpan benar", k["nama"] == "Budi Santoso",
              f"dapat '{k['nama']}'")
        p.cek("Gaji pokok tersimpan benar", k["gaji_pokok"] == 7500000,
              f"dapat {k['gaji_pokok']}")
        p.cek("Jabatan tersimpan benar", k["jabatan"] == "Staf Akuntansi",
              f"dapat '{k['jabatan']}'")
        p.cek("Status PTKP tersimpan benar", k["status_ptkp"] == "TK/0",
              f"dapat '{k['status_ptkp']}'")
        p.cek("Tunjangan tersimpan benar", k["tunjangan_tetap"] == 500000,
              f"dapat {k['tunjangan_tetap']}")
        p.cek("NPWP tersimpan benar",
              k["nik_npwp"] == "3273010101900001",
              f"dapat '{k['nik_npwp']}'")
        p.cek("Tanggal masuk tersimpan benar",
              k["tanggal_masuk"] == "2026-01-15",
              f"dapat '{k['tanggal_masuk']}'")
        p.cek("Karyawan berstatus aktif", bool(k["is_active"]))

    # ------------------------------------------------------------- ubah
    print()
    print("[Ubah karyawan]")
    services.update_karyawan(eid, gaji_pokok=8200000, jabatan="Kepala Akuntansi")
    k2 = services.list_karyawan(cid)[0]
    p.cek("Gaji berubah setelah diubah", k2["gaji_pokok"] == 8200000,
          f"dapat {k2['gaji_pokok']}")
    p.cek("Jabatan berubah setelah diubah",
          k2["jabatan"] == "Kepala Akuntansi", f"dapat '{k2['jabatan']}'")
    p.cek("Nama tidak ikut berubah", k2["nama"] == "Budi Santoso",
          f"dapat '{k2['nama']}'")

    # ----------------------------------------------------------- validasi
    print()
    print("[Penjagaan data]")
    try:
        services.simpan_karyawan(cid, "", 5000000)
        p.cek("Nama kosong ditolak", False, "justru tersimpan")
    except Exception:
        p.cek("Nama kosong ditolak", True)

    try:
        services.simpan_karyawan(cid, "Uji", -100)
        p.cek("Gaji negatif ditolak", False, "justru tersimpan")
    except Exception:
        p.cek("Gaji negatif ditolak", True)

    try:
        services.simpan_karyawan(cid, "Uji", 5000000, status_ptkp="XX/9")
        p.cek("Status PTKP asing ditolak", False, "justru tersimpan")
    except Exception:
        p.cek("Status PTKP asing ditolak", True)

    # ------------------------------------------------------------- hapus
    print()
    print("[Hapus karyawan]")
    services.hapus_karyawan(eid)
    daftar_aktif = services.list_karyawan(cid)
    p.cek("Karyawan keluar dari daftar aktif", len(daftar_aktif) == 0,
          f"masih ada {len(daftar_aktif)}")

    semua = services.list_karyawan(cid, aktif_saja=False)
    p.cek("Data karyawan tetap tersimpan sebagai riwayat",
          len(semua) == 1, f"jumlah={len(semua)}")

    # ------------------------------------------------------- jejak audit
    print()
    print("[Jejak audit]")
    jejak = db.q(
        "SELECT action FROM audit_log WHERE action LIKE 'employee%' "
        "ORDER BY id")
    aksi = [j["action"] for j in jejak]
    p.cek("Penambahan karyawan tercatat", "employee.create" in aksi,
          f"aksi tercatat: {aksi}")

    # ----------------------------------------------------------- bersihkan
    shutil.rmtree(FOLDER, ignore_errors=True)

    return p.ringkas()


if __name__ == "__main__":
    sys.exit(main())
