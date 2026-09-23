"""Uji pemilihan mode Pemula/Ahli hanya muncul sekali.

Pilihan mode harus:
  1. ditawarkan saat pengguna belum pernah memilih;
  2. tersimpan permanen setelah dipilih;
  3. tidak ditawarkan lagi saat aplikasi dibuka ulang;
  4. tetap dapat diubah kapan saja dari Pengaturan.
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
DATA = AKAR / "_ujimode"
os.environ["AKUNTANSIID_DATA"] = str(DATA)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(AKAR / "src"))

from akuntansi_id import db  # noqa: E402
from akuntansi_id.core import security as sec  # noqa: E402

HASIL: list = []


def cek(nama, syarat, detail=""):
    HASIL.append((nama, bool(syarat), detail))
    print(f"  {'LULUS' if syarat else 'GAGAL'}  {nama}"
          + (f"  [{detail}]" if detail else ""))


def main() -> int:
    if DATA.exists():
        shutil.rmtree(DATA, ignore_errors=True)
    db.init_db()
    sec.ensure_default_admin()

    print("=== Pengguna baru ===")
    h1 = sec.login("admin", "admin123")
    cek("mode belum pernah dipilih", h1.mode_dipilih is False,
        f"mode_dipilih={h1.mode_dipilih}")
    cek("mode bawaan Pemula", h1.app_mode == "beginner", h1.app_mode)

    print("\n=== Setelah memilih Ahli ===")
    sec.update_user_mode(h1.user_id, "expert")
    h2 = sec.login("admin", "admin123")
    cek("mode tercatat sudah dipilih", h2.mode_dipilih is True,
        f"mode_dipilih={h2.mode_dipilih}")
    cek("mode tersimpan sebagai Ahli", h2.app_mode == "expert", h2.app_mode)

    print("\n=== Buka aplikasi lagi ===")
    h3 = sec.login("admin", "admin123")
    cek("tidak ditawarkan lagi", h3.mode_dipilih is True)
    cek("mode tetap Ahli", h3.app_mode == "expert", h3.app_mode)

    print("\n=== Ubah dari Pengaturan ===")
    sec.update_user_mode(h3.user_id, "beginner")
    h4 = sec.login("admin", "admin123")
    cek("mode berubah jadi Pemula", h4.app_mode == "beginner", h4.app_mode)
    cek("penanda pilihan tetap", h4.mode_dipilih is True)

    print("\n=== Pengguna lain tetap ditawari sendiri ===")
    uid = sec.create_user("staf1", "rahasia123", "Staf Satu", role="staff")
    h5 = sec.login("staf1", "rahasia123")
    cek("pengguna baru ditawari mode", h5.mode_dipilih is False)
    sec.update_user_mode(uid, "expert")
    h6 = sec.login("admin", "admin123")
    cek("pilihan pengguna lain tidak mengubah admin",
        h6.app_mode == "beginner", h6.app_mode)

    print("\n=== Nilai mode tidak sah ditolak ===")
    try:
        sec.update_user_mode(h1.user_id, "mode_ngawur")
        cek("mode tidak sah ditolak", False)
    except ValueError:
        cek("mode tidak sah ditolak", True)

    gagal = [h for h in HASIL if not h[1]]
    print("\n" + "=" * 74)
    if gagal:
        print(f"HASIL: {len(HASIL) - len(gagal)} LULUS, {len(gagal)} GAGAL")
        for nama, _, detail in gagal:
            print(f"   GAGAL: {nama} {detail}")
        return 1
    print(f"HASIL: {len(HASIL)} LULUS, 0 GAGAL")
    return 0


if __name__ == "__main__":
    sys.exit(main())
