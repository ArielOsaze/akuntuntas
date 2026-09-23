"""
Cari sisa emoji dan nama ikon yang tampil sebagai teks di antarmuka.

Cara pakai:
    python tools/cari_teks_ikon.py

Berguna untuk memastikan tidak ada nama ikon (mis. "laporan", "bank")
yang keliru ditampilkan sebagai teks kepada pengguna.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
UI = AKAR / "src" / "akuntansi_id" / "ui"

# nama ikon yang tersedia pada modul icons
NAMA_IKON = {
    "dashboard", "analisis", "pencarian", "jurnal", "penjualan", "pembelian",
    "biaya", "bank", "mitra", "produk", "aset", "payroll", "dimensi", "periode",
    "konsolidasi", "laporan", "pajak", "checklist", "pengguna", "audit",
    "recycle", "impor", "ekspor", "coa", "perusahaan", "lan", "pengaturan",
    "bantuan", "keluar", "tambah", "simpan", "hapus", "cetak", "segarkan",
    "mata", "kalender", "transfer", "peringatan", "info", "uang", "kunci",
    "buka", "dokumen", "waktu", "laporan_kecil",
}

EMOJI = re.compile(
    r"[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F000-\U0001F2FF"
    r"\u2705\u274C\u2713\u2717\u2714\u2718\u26A0\u2699\u23FB\u23F9"
    r"\u25B6\u2192\u2190\u21BB\u21BA\uFE0F]")

# QLabel("nama_ikon") atau QLabel(f"nama_ikon")
POLA_LABEL = re.compile(r"""QLabel\(\s*f?["']([a-z_]+)["']\s*\)""")

# setText("nama_ikon")
POLA_SETTEXT = re.compile(r"""\.setText\(\s*["']([a-z_]+)["']\s*\)""")

# pemetaan tingkat -> nama ikon (mis. ikon_map = {"info": "info", ...})
POLA_MAP = re.compile(r"""["']([a-z_]+)["']\s*:\s*["']([a-z_]+)["']""")


def periksa(path: Path) -> list:
    """Periksa satu berkas; komentar dilewati karena tidak tampil ke pengguna."""
    temuan = []
    baris = path.read_text(encoding="utf-8").splitlines()
    for i, b in enumerate(baris, 1):
        kode = b.split("#", 1)[0] if "#" in b else b
        if not kode.strip():
            continue
        if EMOJI.search(kode):
            temuan.append((i, "emoji", kode.strip()[:88]))
        for m in POLA_LABEL.finditer(kode):
            if m.group(1) in NAMA_IKON:
                temuan.append((i, "label-ikon", kode.strip()[:88]))
        for m in POLA_SETTEXT.finditer(kode):
            if m.group(1) in NAMA_IKON:
                temuan.append((i, "settext-ikon", kode.strip()[:88]))
    return temuan


def main() -> int:
    total = 0
    for p in sorted(UI.rglob("*.py")):
        if p.name == "icons.py":
            continue
        temuan = periksa(p)
        if temuan:
            total += len(temuan)
            print(f"\n{p.relative_to(AKAR)}")
            for baris, jenis, teks in temuan:
                print(f"   baris {baris:4d} [{jenis}] {teks}")
    print()
    print("=" * 70)
    if total:
        print(f"HASIL: {total} sisa teks ikon/emoji ditemukan")
    else:
        print("HASIL: tidak ada nama ikon atau emoji yang tampil sebagai teks")
    print("=" * 70)
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
