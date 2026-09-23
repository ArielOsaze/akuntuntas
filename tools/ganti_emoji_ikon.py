"""
Ganti emoji pada pemanggilan w.tombol(...) dan KpiTile(...) dengan nama
ikon garis dari modul icons.

Cara pakai:
    python tools/ganti_emoji_ikon.py           # periksa saja
    python tools/ganti_emoji_ikon.py --tulis   # tulis perubahan
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent

# Emoji -> nama ikon garis
PETA = {
    "📊": "laporan", "📈": "penjualan", "📉": "laporan_kecil",
    "🔍": "analisis", "🔎": "pencarian",
    "🛒": "pembelian", "📦": "produk", "💸": "biaya", "💳": "bank",
    "🏦": "bank", "👥": "mitra", "🏭": "aset", "👔": "payroll",
    "🎯": "dimensi", "🔒": "periode", "🔓": "buka", "🏢": "perusahaan",
    "🧾": "pajak", "✅": "checklist", "🔑": "pengguna", "📋": "audit",
    "🗑": "hapus", "📥": "impor", "⬇": "ekspor", "⬆": "ekspor",
    "📚": "coa", "🌐": "lan", "⚙": "pengaturan", "❓": "bantuan",
    "💾": "simpan", "🔔": "peringatan", "📅": "kalender", "📝": "jurnal",
    "✎": "pengaturan", "↻": "segarkan", "⏻": "keluar", "🔌": "lan",
    "▶": "simpan", "⏹": "hapus", "⇄": "transfer", "📂": "dokumen",
    "📎": "dokumen", "🔗": "lan", "💡": "info", "⚠": "peringatan",
    "✓": "simpan", "✗": "hapus", "💰": "uang", "🎉": "checklist",
    "🔐": "kunci", "🖨": "cetak", "🖊": "pengaturan", "➡": "penjualan",
    "⊘": "hapus", "↺": "segarkan", "📤": "ekspor", "🕐": "waktu",
    "🗂": "dokumen", "📄": "dokumen", "🖼": "dokumen", "📁": "dokumen",
}

# Pola emoji apa pun di dalam berkas Python (di luar komentar)
POLA = re.compile(
    r"[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F000-\U0001F2FF"
    r"\U00002190-\U000021FF\U00002B00-\U00002BFF\u2705\u274C\u2713\u2717"
    r"\u2714\u2718\u26A0\u2699\u23FB\u23F9\u25B6\u2192\u2190\u21BB\u21BA"
    r"\uFE0F]")


def bersihkan(path: Path, tulis: bool) -> int:
    sumber = path.read_text(encoding="utf-8")
    asli = sumber

    def ganti(m) -> str:
        e = m.group(0)
        return PETA.get(e, "")

    # hanya proses baris yang memanggil tombol()/KpiTile()/ikon=
    baris_baru = []
    jumlah = 0
    for baris in sumber.splitlines(keepends=True):
        if ("w.tombol(" in baris or "KpiTile(" in baris or "ikon=" in baris
                or "tambah_aksi(" in baris):
            baru = POLA.sub(ganti, baris)
            if baru != baris:
                jumlah += 1
                baris = baru
        baris_baru.append(baris)

    hasil = "".join(baris_baru)
    if tulis and hasil != asli:
        path.write_text(hasil, encoding="utf-8")
    return jumlah


def main() -> int:
    tulis = "--tulis" in sys.argv
    total = 0
    for p in sorted((AKAR / "src").rglob("*.py")):
        n = bersihkan(p, tulis)
        if n:
            total += n
            print(f"{'DIPERBARUI' if tulis else 'PERLU'} "
                  f"{p.relative_to(AKAR)}: {n} baris")
    print(f"\nTotal: {total} baris")
    return 0


if __name__ == "__main__":
    sys.exit(main())
