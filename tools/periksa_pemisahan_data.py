"""
Pencarian celah pemisahan data dengan membaca kode, bukan menjalankannya.

Cara ini berbeda dari semua pengujian sebelumnya. Pengujian sebelumnya
menjalankan aplikasi lalu memeriksa hasilnya, sehingga hanya menjangkau
jalur yang terpikirkan. Cara ini membaca seluruh kode dan mencari pola yang
berbahaya, sehingga dapat menemukan jalur yang belum pernah dijalankan
siapa pun.

Polanya: aplikasi ini menyimpan seluruh perusahaan dalam satu berkas basis
data. Setiap query yang membaca tabel ber-company_id WAJIB menyaring
company_id. Bila satu query lupa menyaringnya, angka perusahaan lain akan
ikut terbaca, dan angkanya tetap terlihat wajar sehingga sulit disadari.

Yang dicari:

  1. Query SELECT dari tabel ber-company_id tanpa syarat company_id.
  2. Query UPDATE dan DELETE dari tabel ber-company_id tanpa syarat
     company_id, yang lebih berbahaya karena dapat mengubah atau menghapus
     data perusahaan lain.
  3. Pemakaian f-string atau penggabungan teks untuk menyusun query, yang
     membuka celah penyisipan perintah.

Cara pakai:
    python tools/periksa_pemisahan_data.py
    python tools/periksa_pemisahan_data.py --rinci
"""
from __future__ import annotations

import os
import re
import sys
import tempfile
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
SUMBER = AKAR / "src" / "akuntansi_id"

# Berkas yang memang berisi query lintas perusahaan, jadi dikecualikan
# dengan alasan yang jelas.
DIKECUALIKAN = {
    # Skema dan migrasi tidak menyaring karena membangun seluruh tabel.
    "db.py",
    "schema_ext.py",
    "schema_kontrak.py",
    # Pencarian lintas data untuk keperluan pemeliharaan.
    "core/reset.py",
    "core/license.py",
    "core/uji_coba.py",
    "ui/periksa_lisensi.py",
    "laporan_bug.py",
}


def daftar_tabel_ber_company() -> set[str]:
    """Baca skema untuk mengetahui tabel mana yang punya kolom company_id."""
    sys.path.insert(0, str(AKAR / "src"))
    os.environ["LOCALAPPDATA"] = tempfile.mkdtemp(prefix="akuntuntas_periksa_")
    from akuntansi_id import db  # noqa: E402

    db.init_db()
    conn = db.get_conn()
    tabel = set()
    for (nama,) in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%'"):
        kolom = [r[1] for r in conn.execute(f"PRAGMA table_info({nama})")]
        if "company_id" in kolom:
            tabel.add(nama)
    return tabel


def ambil_query(berkas: Path) -> list[tuple[int, str]]:
    """
    Ambil seluruh teks query dari satu berkas.

    Query dikenali dari teks yang memuat kata SELECT, UPDATE, atau DELETE
    di dalam tanda kutip. Cara ini sengaja sederhana supaya mudah diperiksa
    ulang oleh manusia, dan supaya query yang disusun bertahap pun terbaca.
    """
    try:
        isi = berkas.read_text(encoding="utf-8")
    except Exception:
        return []

    hasil = []
    # Teks di dalam tanda kutip tiga atau satu.
    for pola in (r'"""(.*?)"""', r"'''(.*?)'''", r'"([^"\n]*)"', r"'([^'\n]*)'"):
        for cocok in re.finditer(pola, isi, re.DOTALL):
            teks = cocok.group(1)
            if re.search(r"\b(SELECT|UPDATE|DELETE)\b", teks, re.IGNORECASE):
                baris = isi[:cocok.start()].count("\n") + 1
                hasil.append((baris, teks))
    return hasil


def tabel_dibaca(teks: str) -> set[str]:
    """Nama tabel yang disebut pada bagian FROM, JOIN, UPDATE, atau DELETE."""
    nama = set()
    for pola in (
        r"\bFROM\s+([A-Za-z_][A-Za-z0-9_]*)",
        r"\bJOIN\s+([A-Za-z_][A-Za-z0-9_]*)",
        r"\bUPDATE\s+([A-Za-z_][A-Za-z0-9_]*)",
        r"\bDELETE\s+FROM\s+([A-Za-z_][A-Za-z0-9_]*)",
        r"\bINSERT\s+INTO\s+([A-Za-z_][A-Za-z0-9_]*)",
    ):
        for cocok in re.finditer(pola, teks, re.IGNORECASE):
            nama.add(cocok.group(1).lower())
    return nama


def main() -> int:
    rinci = "--rinci" in sys.argv
    print("=" * 76)
    print("  PEMERIKSAAN PEMISAHAN DATA DENGAN MEMBACA KODE")
    print("=" * 76)
    print()

    tabel_company = daftar_tabel_ber_company()
    print(f"  tabel ber-company_id: {len(tabel_company)}")
    print()

    # ------------------------------------------------------------------
    # 1. Query tanpa saringan company_id
    # ------------------------------------------------------------------
    print("[1. Query dari tabel ber-company_id tanpa saringan company_id]")
    tanpa_saring: list[tuple[str, int, str, str]] = []
    diperiksa = 0

    for berkas in sorted(SUMBER.rglob("*.py")):
        relatif = str(berkas.relative_to(SUMBER)).replace("\\", "/")
        if relatif in DIKECUALIKAN:
            continue

        for baris, teks in ambil_query(berkas):
            dipakai = tabel_dibaca(teks) & tabel_company
            if not dipakai:
                continue
            diperiksa += 1

            # Saringan dianggap ada bila kata company_id muncul, atau bila
            # query memakai subquery yang menyaring lewat tabel lain.
            if re.search(r"\bcompany_id\b", teks, re.IGNORECASE):
                continue
            # Query yang hanya menghitung jumlah baris milik satu entry
            # (mis. WHERE entry_id=?) tidak memerlukan saringan, karena
            # entry_id sudah unik untuk satu perusahaan.
            if re.search(r"\bentry_id\s*=", teks, re.IGNORECASE):
                continue
            # Query yang menyaring lewat id unik juga aman.
            if re.search(r"\bWHERE\s+id\s*=", teks, re.IGNORECASE):
                continue
            # Perintah INSERT tidak membaca data perusahaan lain.
            if re.match(r"\s*INSERT", teks, re.IGNORECASE):
                continue

            tanpa_saring.append((relatif, baris, sorted(dipakai)[0],
                                 teks.strip().replace("\n", " ")[:90]))

    print(f"  query diperiksa: {diperiksa}")
    if tanpa_saring:
        print(f"  PERLU DIPERIKSA: {len(tanpa_saring)}")
        for relatif, baris, tabel, cuplikan in tanpa_saring[:25]:
            print(f"    {relatif}:{baris}  [{tabel}]")
            if rinci:
                print(f"      {cuplikan}")
    else:
        print("  tidak ada query yang lupa menyaring company_id")
    print()

    # ------------------------------------------------------------------
    # 2. Query yang disusun dengan penggabungan teks
    # ------------------------------------------------------------------
    print("[2. Query yang disusun dengan f-string atau penggabungan teks]")
    disusun: list[tuple[str, int, str]] = []
    for berkas in sorted(SUMBER.rglob("*.py")):
        relatif = str(berkas.relative_to(SUMBER)).replace("\\", "/")
        if relatif in DIKECUALIKAN:
            continue
        try:
            isi = berkas.read_text(encoding="utf-8")
        except Exception:
            continue
        for i, baris_teks in enumerate(isi.splitlines(), start=1):
            # f-string yang memuat kata kunci SQL.
            if re.search(r'f["\'].*\b(SELECT|UPDATE|DELETE|INSERT)\b',
                         baris_teks, re.IGNORECASE):
                # Nilai yang disisipkan dari variabel bernama aman bila
                # hanya nama tabel atau kolom dari daftar tetap.
                disusun.append((relatif, i, baris_teks.strip()[:95]))
    if disusun:
        print(f"  ditemukan: {len(disusun)}")
        for relatif, baris, cuplikan in disusun[:25]:
            print(f"    {relatif}:{baris}  {cuplikan}")
    else:
        print("  tidak ada query yang disusun dengan f-string")
    print()

    # ------------------------------------------------------------------
    # 3. Nilai yang digabungkan langsung ke query (celah penyisipan)
    # ------------------------------------------------------------------
    print("[3. Nilai yang digabungkan langsung ke dalam query]")
    gabung: list[tuple[str, int, str]] = []
    for berkas in sorted(SUMBER.rglob("*.py")):
        relatif = str(berkas.relative_to(SUMBER)).replace("\\", "/")
        if relatif in DIKECUALIKAN:
            continue
        try:
            isi = berkas.read_text(encoding="utf-8")
        except Exception:
            continue
        for i, baris_teks in enumerate(isi.splitlines(), start=1):
            # Query yang memakai tanda kutip lalu ditambah variabel, bukan
            # parameter ?. Pola seperti "... WHERE kode='" + kode + "'"
            if re.search(r'["\']\s*\+\s*[A-Za-z_]', baris_teks) and \
               re.search(r"(WHERE|AND|OR|VALUES|SET)", baris_teks, re.IGNORECASE):
                gabung.append((relatif, i, baris_teks.strip()[:95]))
            # Query dengan .format() atau % untuk nilai.
            if re.search(r'["\'].*%s.*["\']\s*%', baris_teks):
                gabung.append((relatif, i, baris_teks.strip()[:95]))
    if gabung:
        print(f"  ditemukan: {len(gabung)}")
        for relatif, baris, cuplikan in gabung[:25]:
            print(f"    {relatif}:{baris}  {cuplikan}")
    else:
        print("  tidak ada nilai yang digabungkan langsung ke query")
    print()

    # ------------------------------------------------------------------
    # 4. Kesimpulan
    # ------------------------------------------------------------------
    print("=" * 76)
    masalah = len(tanpa_saring)
    print(f"  query diperiksa              : {diperiksa}")
    print(f"  tanpa saringan company_id    : {len(tanpa_saring)}")
    print(f"  disusun dengan f-string      : {len(disusun)}")
    print(f"  nilai digabung langsung      : {len(gabung)}")
    print("=" * 76)

    if masalah:
        print()
        print("  Query tanpa saringan company_id perlu diperiksa satu per satu:")
        print("  sebagian memang aman (misalnya menyaring lewat id unik), tetapi")
        print("  setiap yang tidak aman dapat mencampur data antar perusahaan.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
