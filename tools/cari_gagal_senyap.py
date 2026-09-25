"""
Cari tempat di antarmuka yang gagal tanpa memberi pesan kepada pengguna.

Masalah yang dicari: fungsi yang langsung berhenti (return) ketika ada
syarat yang belum terpenuhi, tanpa menampilkan pesan apa pun. Pengguna
yang menekan tombol lalu tidak terjadi apa-apa akan mengira aplikasinya
rusak, padahal ada syarat yang belum dipenuhi.

Pola yang ditandai:
    if <syarat>:
        return
    ...
    if <syarat>:
        return

yang tidak diikuti QMessageBox, QDialog, atau pemanggilan lain yang
menampilkan pesan.

Cara pakai:
    python tools/cari_gagal_senyap.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
SUMBER = AKAR / "src" / "akuntansi_id" / "ui"

# Pemanggilan yang menampilkan pesan kepada pengguna.
TAMPILKAN = (
    "QMessageBox", "info(", "peringatan(", "warning(", "critical(",
    "question(", "dialog(", "notif", "toast", "self.status",
)

# Baris yang boleh berhenti tanpa pesan.
DIKECUALIKAN = (
    "super()", "pass", "continue", "break", "raise", "self.accept",
    "self.reject", "return True", "return False", "return None",
    "return []", "return {}", "return 0",
)


def main() -> int:
    if not SUMBER.exists():
        print(f"  folder sumber tidak ditemukan: {SUMBER}")
        return 2

    temuan = []
    berkas_diperiksa = 0

    for f in sorted(SUMBER.rglob("*.py")):
        if "__pycache__" in str(f):
            continue
        berkas_diperiksa += 1
        baris = f.read_text(encoding="utf-8", errors="replace").splitlines()

        for i, teks in enumerate(baris):
            # Cari "return" yang berdiri sendiri.
            if teks.strip() != "return":
                continue

            # Lihat 8 baris sebelum dan 2 baris sesudah, untuk menilai
            # apakah ada pesan yang ditampilkan.
            awal = max(0, i - 8)
            sekitar = "\n".join(baris[awal:i + 2])

            if any(k in sekitar for k in TAMPILKAN):
                continue

            # Baris "return" di dalam fungsi yang mengembalikan nilai
            # memang wajar; yang dicari adalah berhenti tanpa pesan.
            # Tandai hanya bila sebelumnya ada pemeriksaan syarat.
            ada_syarat = bool(re.search(r"\bif\b.*:\s*$", "\n".join(
                baris[awal:i])))

            if ada_syarat:
                temuan.append((f.relative_to(AKAR), i + 1,
                               baris[max(0, i - 3)].strip(),
                               baris[i - 1].strip()))

    print("=" * 78)
    print("  CARI KEGAGALAN TANPA PESAN KEPADA PENGGUNA")
    print("=" * 78)
    print()
    print(f"  berkas diperiksa: {berkas_diperiksa}")
    print()

    if not temuan:
        print("  TIDAK ADA kegagalan senyap yang ditemukan.")
        print("=" * 78)
        return 0

    print(f"  DITEMUKAN {len(temuan)} tempat yang berhenti tanpa pesan:")
    print()
    for f, n, sebelum, terakhir in temuan:
        print(f"    {f}:{n}")
        print(f"      {sebelum}")
        print(f"      {terakhir}")
        print()

    print("=" * 78)
    print("  HASIL: tambahkan pesan kepada pengguna pada tempat tersebut")
    print("=" * 78)
    return 1


if __name__ == "__main__":
    sys.exit(main())
