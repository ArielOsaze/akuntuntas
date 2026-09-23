"""
Pemburu bug pada penanganan kesalahan.

Kesalahan yang ditelan diam-diam adalah sumber bug tersembunyi: aplikasi
terlihat berjalan, tetapi ada langkah yang gagal tanpa pemberitahuan dan
datanya tidak tersimpan. Pemeriksaan ini mencari blok pengecualian yang
tidak melakukan apa pun, dan pemanggilan yang gagalnya tidak dilaporkan.

Yang dicari BUKAN semua blok kosong: sebagian memang disengaja, misalnya
saat membaca setelan yang boleh tidak ada. Yang dicari adalah blok kosong
pada jalur yang menyimpan atau mengubah data.

Jalankan:  python tools/buruh_bug_kesalahan.py
"""

import ast
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
SUMBER = AKAR / "src" / "akuntansi_id"

# Nama fungsi yang menandakan penyimpanan data. Blok pengecualian kosong di
# sekitarnya berarti kegagalan menyimpan tidak pernah dilaporkan.
KATA_SIMPAN = ("simpan", "buat", "tambah", "ubah", "hapus", "insert",
               "update", "delete", "create", "reset", "restore", "pulihkan",
               "posting", "tutup", "bayar", "terima", "kirim")

# Berkas yang boleh memiliki blok kosong: pembacaan setelan dan tampilan.
DIPERBOLEHKAN = {
    "config.py", "theme.py", "istilah.py", "coa.py",
}

# Nama fungsi yang kegagalannya memang tidak perlu dilaporkan, karena
# kegagalan itu tidak mengubah data pembukuan. Misalnya menyimpan preferensi
# tampilan, atau membersihkan koneksi yang akan dibuka ulang.
WAJAR_DITELAN = (
    "_simpan_preferensi", "simpan_lipatan", "_tutup_koneksi",
    "simpan_laporan", "simpan_metadata", "buat_pdf", "konfirmasi_pulihkan",
    "_muat", "ekspor", "logo",
)


def blok_kosong(handler: ast.ExceptHandler) -> bool:
    """Apakah blok pengecualian tidak melakukan apa pun yang berarti."""
    badan = handler.body
    if not badan:
        return True
    # pass saja
    if len(badan) == 1 and isinstance(badan[0], ast.Pass):
        return True
    # hanya berisi 'continue' atau 'return' tanpa keterangan
    if len(badan) == 1 and isinstance(badan[0], (ast.Continue, ast.Return)):
        return True
    # hanya berisi docstring
    if all(isinstance(b, ast.Expr) and isinstance(b.value, ast.Constant)
           for b in badan):
        return True
    return False


def nama_induk(pohon: ast.AST) -> dict:
    """Petakan setiap simpul ke nama fungsi induknya."""
    peta = {}

    def telusuri(simpul, nama=""):
        for anak in ast.iter_child_nodes(simpul):
            baru = nama
            if isinstance(anak, (ast.FunctionDef, ast.AsyncFunctionDef)):
                baru = anak.name
            peta[anak] = baru
            telusuri(anak, baru)

    peta[pohon] = ""
    telusuri(pohon, "")
    return peta


def main() -> int:
    print("=" * 72)
    print("PEMBURU BUG — PENANGANAN KESALAHAN")
    print("=" * 72)
    print()

    berbahaya = []
    wajar = 0
    berkas_diperiksa = 0

    for berkas in sorted(SUMBER.rglob("*.py")):
        if berkas.name in DIPERBOLEHKAN:
            continue
        berkas_diperiksa += 1
        try:
            pohon = ast.parse(berkas.read_text(encoding="utf-8"))
        except SyntaxError as e:
            berbahaya.append((berkas, 0, f"syntax error: {e}", ""))
            continue

        peta = nama_induk(pohon)
        for simpul in ast.walk(pohon):
            if not isinstance(simpul, ast.Try):
                continue
            for handler in simpul.handlers:
                if not blok_kosong(handler):
                    continue
                induk = peta.get(simpul, "")
                kunci = induk.lower()
                if any(w in kunci for w in WAJAR_DITELAN):
                    wajar += 1
                elif any(k in kunci for k in KATA_SIMPAN):
                    berbahaya.append((
                        berkas, simpul.lineno,
                        f"kegagalan di {induk}() ditelan tanpa laporan",
                        f"baris {simpul.lineno}"))
                else:
                    wajar += 1

    print(f"{berkas_diperiksa} berkas diperiksa")
    print(f"{wajar} blok pengecualian kosong pada jalur baca (wajar)")
    print()

    if berbahaya:
        print(f"HASIL: {len(berbahaya)} penanganan kesalahan berbahaya")
        for berkas, baris, pesan, _ in berbahaya[:15]:
            relatif = berkas.relative_to(AKAR)
            print(f"   {relatif}:{baris} — {pesan}")
        return 1

    print("HASIL: tidak ada kegagalan penyimpanan yang ditelan diam-diam")
    return 0


if __name__ == "__main__":
    sys.exit(main())
