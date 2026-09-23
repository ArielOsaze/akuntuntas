"""
Bersihkan import yang tidak terpakai pada berkas sumber.

Cara pakai:
    python tools/bersihkan_import.py            # periksa saja
    python tools/bersihkan_import.py --tulis    # tulis perubahan
"""
from __future__ import annotations

import ast
import pathlib
import sys

AKAR = pathlib.Path(__file__).resolve().parent.parent / "src"


def nama_dipakai(pohon: ast.AST) -> set:
    dipakai: set = set()
    for n in ast.walk(pohon):
        if isinstance(n, ast.Name):
            dipakai.add(n.id)
        elif isinstance(n, ast.Attribute):
            dipakai.add(n.attr)
    for n in ast.walk(pohon):
        if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name):
            dipakai.add(n.value.id)
    return dipakai


def bersihkan(path: pathlib.Path, tulis: bool) -> list:
    sumber = path.read_text(encoding="utf-8")
    baris = sumber.splitlines(keepends=True)
    try:
        pohon = ast.parse(sumber)
    except SyntaxError:
        return []

    dipakai = nama_dipakai(pohon)
    # anotasi tipe dalam bentuk string ikut dihitung
    for n in ast.walk(pohon):
        if isinstance(n, ast.Constant) and isinstance(n.value, str):
            for kata in n.value.replace("|", " ").replace("[", " ").replace(
                    "]", " ").replace(",", " ").split():
                dipakai.add(kata)

    hapus: set = set()
    for n in pohon.body:
        if isinstance(n, ast.ImportFrom):
            for a in n.names:
                if a.name == "*":
                    continue
                if (a.asname or a.name) not in dipakai:
                    hapus.add(id(a))
        elif isinstance(n, ast.Import):
            for a in n.names:
                if (a.asname or a.name.split(".")[0]) not in dipakai:
                    hapus.add(id(a))

    if not hapus:
        return []

    baru = []
    dihapus = []
    for n in pohon.body:
        if isinstance(n, (ast.Import, ast.ImportFrom)):
            sisa = [a for a in n.names if id(a) not in hapus]
            for a in n.names:
                if id(a) in hapus:
                    dihapus.append(a.asname or a.name)
            if not sisa:
                continue
            n.names = sisa
        baru.append(n)

    if tulis:
        teks_baru = _tulis_ulang(sumber, baris, pohon, baru)
        path.write_text(teks_baru, encoding="utf-8")
    return dihapus


def _tulis_ulang(sumber, baris, pohon, simpul_baru) -> str:
    """Susun ulang berkas dengan mengganti baris import saja."""
    ganti: dict = {}
    baru_map = {}
    for n in simpul_baru:
        if isinstance(n, (ast.Import, ast.ImportFrom)):
            baru_map[n.lineno] = n

    for n in pohon.body:
        if not isinstance(n, (ast.Import, ast.ImportFrom)):
            continue
        awal, akhir = n.lineno - 1, n.end_lineno
        baru_n = baru_map.get(n.lineno)
        if baru_n is None:
            ganti[awal] = ""
            for i in range(awal + 1, akhir):
                ganti[i] = None
            continue
        if len(baru_n.names) == len(n.names):
            continue
        teks = _teks_import(baru_n, baris[awal:akhir])
        ganti[awal] = teks
        for i in range(awal + 1, akhir):
            ganti[i] = None

    keluaran = []
    for i, b in enumerate(baris):
        if i in ganti:
            if ganti[i] is None:
                continue
            if ganti[i] == "":
                continue
            keluaran.append(ganti[i])
        else:
            keluaran.append(b)
    return "".join(keluaran)


def _teks_import(n, potongan_baris) -> str:
    if isinstance(n, ast.Import):
        return "import " + ", ".join(
            (a.asname and f"{a.name} as {a.asname}") or a.name
            for a in n.names) + "\n"

    asal = "." * n.level + (n.module or "")
    nama = [(a.asname and f"{a.name} as {a.asname}") or a.name for a in n.names]
    if len(nama) == 1:
        return f"from {asal} import {nama[0]}\n"

    # pertahankan bentuk berbaris bila aslinya memang berbaris
    asli = "".join(potongan_baris)
    if "(\n" in asli or asli.count("\n") > 1:
        isi = "".join(f"    {x},\n" for x in nama)
        return f"from {asal} import (\n{isi})\n"
    return f"from {asal} import {', '.join(nama)}\n"


def main() -> int:
    tulis = "--tulis" in sys.argv
    total = 0
    for p in sorted(AKAR.rglob("*.py")):
        dihapus = bersihkan(p, tulis)
        if dihapus:
            total += len(dihapus)
            print(f"{'DIBERSIHKAN' if tulis else 'PERLU'} {p.relative_to(AKAR)}: "
                  f"{', '.join(sorted(dihapus))}")
    print(f"\n{'Total dibersihkan' if tulis else 'Total perlu dibersihkan'}: "
          f"{total} import")
    return 0


if __name__ == "__main__":
    sys.exit(main())
