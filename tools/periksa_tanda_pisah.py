"""
Pisahkan tanda pisah panjang yang terlihat pengguna dari yang tidak.

Tanda pisah panjang (em dash) pada teks yang ditampilkan membuat aplikasi
terasa ditulis mesin. Tanda itu juga tidak lazim pada tulisan Indonesia:
orang menulis dengan tanda hubung biasa, koma, atau titik dua.

Pemeriksaan ini membaca setiap berkas Python, mengambil hanya bagian yang
berupa teks tampilan, lalu melaporkan berapa banyak yang perlu diganti.
Komentar dan penjelasan kode tidak dihitung karena tidak pernah terlihat
pengguna.
"""

import ast
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
SUMBER = AKAR / "src" / "akuntansi_id"

TANDA = "\u2014"


def teks_tampilan(berkas: Path) -> list:
    """
    Ambil semua teks yang berpotensi tampil ke pengguna.

    Yang diambil adalah seluruh nilai teks (string literal) pada berkas.
    Komentar tidak diambil karena tidak pernah ditampilkan.
    """
    isi = berkas.read_text(encoding="utf-8")
    hasil = []
    try:
        pohon = ast.parse(isi)
    except SyntaxError:
        return hasil

    for simpul in ast.walk(pohon):
        if isinstance(simpul, ast.Constant) and isinstance(simpul.value, str):
            if TANDA in simpul.value:
                hasil.append((simpul.lineno, simpul.value))
    return hasil


def main() -> int:
    if not SUMBER.exists():
        print("Folder sumber tidak ditemukan.")
        return 1

    total = 0
    per_berkas = []

    for berkas in sorted(SUMBER.rglob("*.py")):
        temuan = teks_tampilan(berkas)
        if temuan:
            per_berkas.append((berkas, temuan))
            total += len(temuan)

    print("=" * 74)
    print(f"TANDA PISAH PANJANG PADA TEKS TAMPILAN: {total} kemunculan")
    print("=" * 74)
    print()

    for berkas, temuan in sorted(per_berkas,
                                 key=lambda x: -len(x[1])):
        relatif = berkas.relative_to(AKAR)
        print(f"  {relatif}  ({len(temuan)} kemunculan)")
        for baris, teks in temuan[:3]:
            ringkas = teks.replace("\n", " ")[:66]
            print(f"     baris {baris:4d}: {ringkas}")
        if len(temuan) > 3:
            print(f"     ... dan {len(temuan) - 3} lagi")
        print()

    print("=" * 74)
    if total == 0:
        print("HASIL: tidak ada tanda pisah panjang pada teks tampilan")
        return 0
    print(f"HASIL: {total} tanda pisah panjang perlu diganti")
    return 1


if __name__ == "__main__":
    sys.exit(main())
