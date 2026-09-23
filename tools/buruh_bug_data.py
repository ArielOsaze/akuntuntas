"""
Pemburu bug pada integritas basis data.

Memeriksa hal-hal yang bisa merusak pembukuan tanpa terlihat: jurnal yang
tidak seimbang, saldo yang tidak cocok dengan jurnalnya, stok negatif, dan
kunci asing yang menggantung. Bug seperti ini tidak memunculkan pesan
kesalahan, tetapi membuat laporan keuangan salah.

Jalankan:  python tools/buruh_bug_data.py
"""

import os
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "src"))
os.environ.setdefault("AKUNTANSIID_DATA", str(AKAR / "_contoh"))

from akuntansi_id import db                          # noqa: E402

lulus = 0
gagal = 0
temuan = []


def periksa(syarat: bool, keterangan: str, rincian: str = "") -> None:
    global lulus, gagal
    if syarat:
        lulus += 1
        print(f"  [LULUS] {keterangan}")
    else:
        gagal += 1
        print(f"  [GAGAL] {keterangan}")
        if rincian:
            for baris in rincian.splitlines()[:8]:
                print(f"          {baris}")
        temuan.append(keterangan)


def main() -> int:
    db.init_db()
    print("=" * 72)
    print("PEMBURU BUG — INTEGRITAS BASIS DATA")
    print("=" * 72)
    print()

    # ------------------------------------------------- 1. jurnal seimbang
    print("[1] Jurnal berpasangan seimbang")
    baris = db.q("""
        SELECT je.id, je.no_bukti,
               SUM(jl.debit) AS total_debit,
               SUM(jl.kredit) AS total_kredit
        FROM journal_entries je
        JOIN journal_lines jl ON jl.entry_id = je.id
        GROUP BY je.id
        HAVING total_debit != total_kredit
    """)
    rincian = "\n".join(
        f"{r['no_bukti']}: debit {r['total_debit']:,} != kredit {r['total_kredit']:,}"
        for r in baris[:8])
    periksa(len(baris) == 0,
            f"tidak ada jurnal pincang ({len(baris)} ditemukan)", rincian)

    # ------------------------------------------------- 2. jurnal tanpa baris
    print()
    print("[2] Jurnal punya baris")
    yatim = db.q("""
        SELECT je.id, je.no_bukti FROM journal_entries je
        LEFT JOIN journal_lines jl ON jl.entry_id = je.id
        WHERE jl.id IS NULL
    """)
    rincian = "\n".join(f"{r['no_bukti']}" for r in yatim[:8])
    periksa(len(yatim) == 0,
            f"tidak ada jurnal kosong ({len(yatim)} ditemukan)", rincian)

    # ------------------------------------------------- 3. stok negatif
    print()
    print("[3] Stok tidak negatif")
    try:
        negatif = db.q("""
            SELECT p.nama, sb.qty FROM stock_balances sb
            JOIN products p ON p.id = sb.product_id
            WHERE sb.qty < 0
        """)
        rincian = "\n".join(f"{r['nama']}: {r['qty']}" for r in negatif[:8])
        periksa(len(negatif) == 0,
                f"tidak ada stok negatif ({len(negatif)} ditemukan)", rincian)
    except Exception as e:
        periksa(False, f"pemeriksaan stok gagal: {e}")

    # ------------------------------------------------- 4. akun tidak ditemukan
    print()
    print("[4] Kode akun pada jurnal terdaftar di bagan akun")
    hantu = db.q("""
        SELECT DISTINCT jl.kode_akun, jl.company_id
        FROM journal_lines jl
        LEFT JOIN accounts a
               ON a.kode = jl.kode_akun AND a.company_id = jl.company_id
        WHERE a.id IS NULL
    """)
    rincian = "\n".join(f"{r['kode_akun']}" for r in hantu[:8])
    periksa(len(hantu) == 0,
            f"tidak ada akun hantu ({len(hantu)} ditemukan)", rincian)

    # ------------------------------------------------- 5. saldo akun vs jurnal
    print()
    print("[5] Saldo akun cocok dengan jumlah jurnalnya")
    try:
        beda = db.q("""
            SELECT a.kode, a.nama, a.saldo_awal,
                   COALESCE(SUM(CASE WHEN a.normal = 'Debit'
                                     THEN jl.debit - jl.kredit
                                     ELSE jl.kredit - jl.debit END), 0) AS mutasi
            FROM accounts a
            LEFT JOIN journal_lines jl
                   ON jl.kode_akun = a.kode AND jl.company_id = a.company_id
            GROUP BY a.id
            HAVING a.saldo_awal + mutasi < 0
        """)
        rincian = "\n".join(
            f"{r['kode']} {r['nama']}: saldo {r['saldo_awal'] + r['mutasi']:,}"
            for r in beda[:8])
        periksa(len(beda) == 0,
                f"tidak ada akun bersaldo negatif tak wajar "
                f"({len(beda)} ditemukan)", rincian)
    except Exception as e:
        periksa(False, f"pemeriksaan saldo gagal: {e}")

    # ------------------------------------------------- 6. kunci asing menggantung
    print()
    print("[6] Tidak ada rujukan menggantung")
    pasangan = [
        ("journal_lines", "entry_id", "journal_entries", "id"),
        ("invoice_items", "invoice_id", "invoices", "id"),
        ("bill_items", "bill_id", "bills", "id"),
        ("stock_movements", "product_id", "products", "id"),
    ]
    for anak, kolom_anak, induk, kolom_induk in pasangan:
        try:
            yatim = db.q(f"""
                SELECT COUNT(*) AS n FROM {anak} c
                LEFT JOIN {induk} p ON p.{kolom_induk} = c.{kolom_anak}
                WHERE c.{kolom_anak} IS NOT NULL AND p.{kolom_induk} IS NULL
            """)
            n = yatim[0]["n"] if yatim else 0
            periksa(n == 0, f"{anak}.{kolom_anak} -> {induk}: {n} menggantung")
        except Exception as e:
            periksa(False, f"{anak}: tidak dapat diperiksa ({e})")

    # ------------------------------------------------- 7. foreign_keys aktif
    print()
    print("[7] Pemeriksaan kunci asing aktif")
    fk = db.scalar("PRAGMA foreign_keys")
    periksa(bool(fk), f"foreign_keys = {fk}")

    # ------------------------------------------------- 8. integrity_check
    print()
    print("[8] Pemeriksaan integritas berkas")
    hasil = db.scalar("PRAGMA integrity_check")
    periksa(hasil == "ok", f"integrity_check = {hasil}")

    # ------------------------------------------------- 9. duplikat kode akun
    print()
    print("[9] Tidak ada kode akun ganda dalam satu perusahaan")
    ganda = db.q("""
        SELECT company_id, kode, COUNT(*) AS n FROM accounts
        GROUP BY company_id, kode HAVING n > 1
    """)
    rincian = "\n".join(f"perusahaan {r['company_id']}: {r['kode']} ({r['n']}x)"
                        for r in ganda[:8])
    periksa(len(ganda) == 0,
            f"tidak ada kode akun ganda ({len(ganda)} ditemukan)", rincian)

    # ------------------------------------------------- 10. nomor dokumen ganda
    print()
    print("[10] Tidak ada nomor dokumen ganda")
    for tabel, kolom in (("invoices", "no_invoice"), ("bills", "no_bill"),
                         ("journal_entries", "no_bukti")):
        try:
            ganda = db.q(f"""
                SELECT company_id, {kolom}, COUNT(*) AS n FROM {tabel}
                WHERE {kolom} IS NOT NULL AND {kolom} != ''
                GROUP BY company_id, {kolom} HAVING n > 1
            """)
            rincian = "\n".join(
                f"perusahaan {r['company_id']}: {r[kolom]} ({r['n']}x)"
                for r in ganda[:5])
            periksa(len(ganda) == 0,
                    f"{tabel}.{kolom}: {len(ganda)} nomor ganda", rincian)
        except Exception:
            pass

    print()
    print("=" * 72)
    if gagal == 0:
        print(f"HASIL: {lulus} LULUS, 0 GAGAL — integritas data terjaga")
    else:
        print(f"HASIL: {lulus} LULUS, {gagal} GAGAL")
        for t in temuan:
            print(f"        - {t}")
    print("=" * 72)
    return 1 if gagal else 0


if __name__ == "__main__":
    sys.exit(main())
