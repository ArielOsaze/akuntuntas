"""
Uji bahwa EXE terpasang memuat seluruh modul skema.

Bug yang dijaga di sini pernah terjadi: modul skema diimpor secara dinamis
lewat importlib, sehingga PyInstaller tidak mengenalinya saat membundel dan
modul itu tidak ikut ke dalam EXE. Akibatnya aplikasi terpasang gagal memuat
skema kontrak, dan tabel serta view-nya tidak terbuat.

Uji ini menjalankan EXE terpasang pada basis data kosong, lalu memeriksa
bahwa seluruh tabel dan view dari semua modul skema benar-benar ada.

Cara pakai:
    python tests/test_exe_modul.py
"""
from __future__ import annotations

import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "src"))

EXE = Path.home() / "AkunTuntas" / "AkunTuntas.exe"

# Tabel yang dibuat modul skema lanjutan. Bila modulnya tidak terbundel,
# tabel-tabel ini tidak akan ada meski aplikasi tetap bisa dibuka.
TABEL_WAJIB = [
    "kontrak", "kontrak_item", "kontrak_termin", "kontrak_berkas",
    "permissions", "role_permissions", "user_permissions", "change_history",
]
VIEW_WAJIB = ["v_kontrak_aktif", "v_account_balances"]

LULUS = 0
GAGAL = 0


def cek(nama: str, syarat: bool, keterangan: str = ""):
    global LULUS, GAGAL
    if syarat:
        LULUS += 1
        print(f"  [LULUS] {nama}")
    else:
        GAGAL += 1
        print(f"  [GAGAL] {nama}" + (f" — {keterangan}" if keterangan else ""))


def main() -> int:
    print("=" * 66)
    print("EXE TERPASANG — KELENGKAPAN MODUL SKEMA")
    print("=" * 66)

    if not EXE.exists():
        print(f"\n  [LEWAT] EXE tidak ada di {EXE}")
        print("          Pasang dulu dengan: python tools/pasang_ulang.py")
        return 0

    folder = Path(tempfile.mkdtemp(prefix="akuntuntas_exe_"))
    try:
        print("\n[Menjalankan EXE pada basis data kosong]")
        env = dict(os.environ, AKUNTANSIID_DATA=str(folder))
        proc = subprocess.Popen([str(EXE)], env=env,
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL)
        # beri waktu membuat basis data dan memuat seluruh skema
        for _ in range(40):
            time.sleep(1)
            if (folder / "akuntuntas.db").exists():
                break
        time.sleep(6)
        proc.terminate()
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()

        basis = folder / "akuntuntas.db"
        cek("EXE membuat basis data", basis.exists(), f"di {basis}")
        if not basis.exists():
            return 1

        # Periksa log: peringatan "gagal dimuat" menandakan modul tidak ada.
        log = folder / "akuntuntas.log"
        isi_log = log.read_text(encoding="utf-8", errors="replace") if log.exists() else ""
        cek("Tidak ada skema yang gagal dimuat",
            "gagal dimuat" not in isi_log,
            [b for b in isi_log.splitlines() if "gagal dimuat" in b][:2])

        conn = sqlite3.connect(basis)
        conn.row_factory = sqlite3.Row

        print("\n[Tabel dari modul skema]")
        nama_tabel = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        for t in TABEL_WAJIB:
            cek(f"Tabel {t} ada", t in nama_tabel)

        print("\n[View dari modul skema]")
        nama_view = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='view'")}
        for v in VIEW_WAJIB:
            cek(f"View {v} ada", v in nama_view)

        print("\n[Isi data bawaan]")
        izin = conn.execute("SELECT COUNT(*) FROM permissions").fetchone()[0]
        cek("Daftar izin terisi", izin > 0, f"dapat {izin}")
        peran = conn.execute("SELECT COUNT(*) FROM role_permissions").fetchone()[0]
        cek("Izin bawaan peran terisi", peran > 0, f"dapat {peran}")

        total = len(nama_tabel)
        cek("Jumlah tabel sesuai harapan", total >= 70, f"dapat {total}")
        conn.close()
    finally:
        shutil.rmtree(folder, ignore_errors=True)

    print()
    print("=" * 66)
    print(f"HASIL: {LULUS} LULUS, {GAGAL} GAGAL")
    print("=" * 66)
    return 1 if GAGAL else 0


if __name__ == "__main__":
    sys.exit(main())
