"""
Samakan penulisan angka desimal dan persen ke gaya Indonesia.

Penulisan angka Indonesia memakai koma sebagai pemisah desimal, bukan
titik. Selama ini sebagian teks masih memakai format bawaan Python
("{:.1f}%") sehingga muncul angka seperti "22.4%" di tengah kalimat
berbahasa Indonesia. Alat ini menggantinya menjadi "22,4%".

Yang diganti hanya format di dalam rangkaian teks (f-string) yang tampil
ke pengguna. Nilai yang dikirim ke Excel, cetak, atau berkas data tidak
disentuh karena di sana titik desimal memang diperlukan.

Pemakaian:
    python tools/samakan_angka.py            # periksa saja
    python tools/samakan_angka.py --tulis    # tulis perubahan
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
SUMBER = AKAR / "src" / "akuntansi_id"

# Pola "{ekspresi * 100:.Nf}%" dan "{ekspresi:.Nf}%" di dalam rangkaian teks.
POLA_PERSEN_KALI = re.compile(r"\{([^{}]+?)\s*\*\s*100:\.(\d)f\}%")
POLA_PERSEN = re.compile(r"\{([^{}]+?):\.(\d)f\}%")

# Berkas yang memang menyimpan angka untuk dibaca mesin, bukan dibaca orang.
KECUALI = (
    "ui/ekspor_cetak.py",
    "core/excel.py",
)


def _nama_bantu(berkas: Path) -> str:
    """
    Nama fungsi bantu penulisan persen untuk tiap lapisan.

    Lapisan core tidak boleh mengimpor lapisan ui, jadi tiap berkas core
    memakai fungsi bantunya sendiri. Berkas ui memakai theme.persen.
    """
    if "ui" in berkas.parts:
        return "theme.persen"
    return "_persen"


def sisir(berkas: Path) -> list[tuple[int, str, str]]:
    """Kembalikan daftar (nomor baris, baris lama, baris baru)."""
    teks = berkas.read_text(encoding="utf-8")
    bantu = _nama_bantu(berkas)
    hasil = []

    for i, baris in enumerate(teks.splitlines(), 1):
        if "f\"" not in baris and "f'" not in baris:
            continue
        baru = baris

        # "{x * 100:.1f}%" -> "{_persen(x, 1)}"
        baru = POLA_PERSEN_KALI.sub(
            lambda m: "{" + f"{bantu}({m.group(1).strip()}, {m.group(2)})" + "}",
            baru)

        # "{x:.1f}%" -> "{_persen(x, 1)}"
        baru = POLA_PERSEN.sub(
            lambda m: "{" + f"{bantu}({m.group(1).strip()}, {m.group(2)})" + "}",
            baru)

        # Penggantian titik menjadi koma yang lama menjadi mubazir karena
        # fungsi bantu sudah memakai koma.
        baru = re.sub(r'(\{[a-z_]+\.persen\([^{}]*\)\})(\.replace\("\."\s*,\s*","\))',
                      r"\1", baru)

        if baru != baris:
            hasil.append((i, baris, baru))

    return hasil


def main() -> int:
    tulis = "--tulis" in sys.argv
    jumlah = 0
    berkas_terdampak = 0

    for berkas in sorted(SUMBER.rglob("*.py")):
        rel = berkas.relative_to(SUMBER).as_posix()
        if any(rel.endswith(k) for k in KECUALI):
            continue

        perubahan = sisir(berkas)
        if not perubahan:
            continue

        berkas_terdampak += 1
        print(f"\n  {rel}  ({len(perubahan)} baris)")
        for baris_ke, lama, baru in perubahan:
            jumlah += 1
            print(f"    baris {baris_ke}")
            print(f"      - {lama.strip()[:96]}")
            print(f"      + {baru.strip()[:96]}")

        if tulis:
            teks = berkas.read_text(encoding="utf-8")
            for _, lama, baru in perubahan:
                teks = teks.replace(lama, baru, 1)
            berkas.write_text(teks, encoding="utf-8")

    print()
    print("=" * 74)
    if tulis:
        print(f"  {jumlah} baris disamakan di {berkas_terdampak} berkas")
    else:
        print(f"  {jumlah} baris perlu disamakan di {berkas_terdampak} berkas")
        print("  jalankan ulang dengan --tulis untuk menerapkan")
    print("=" * 74)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
