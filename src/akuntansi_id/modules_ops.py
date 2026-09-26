"""
Modul biaya, bank & rekonsiliasi, dimensi, tata kelola, otomasi,
tutup buku, dan akses jaringan lokal.
"""
from __future__ import annotations

import csv
import io
import json
import logging
import os
import shutil
import socket
import zipfile
from datetime import date, datetime, timedelta
from typing import Optional

from . import config, db, services
from .core import accounting as acc
from .core import tax_engine as tx
from .modules import (hari_ini, tambah_hari, nomor_berikut, catat_riwayat,
                      ke_recycle_bin, ringkas_angka, buat_mitra, buat_produk)


# ==========================================================================
# BIAYA (EXPENSE MANAGEMENT)
# ==========================================================================
def buat_kategori_biaya(company_id: int, nama: str, **kw) -> int:
    cur = db.ex("""INSERT INTO expense_categories(company_id, nama, akun_beban,
                  batas_nilai, perlu_persetujuan, catatan)
                  VALUES(?,?,?,?,?,?)""",
                (company_id, nama.strip(), kw.get("akun_beban", "6023"),
                 ringkas_angka(kw.get("batas_nilai")),
                 1 if kw.get("perlu_persetujuan") else 0, kw.get("catatan", "")))
    return cur.lastrowid


def daftar_kategori_biaya(company_id: int) -> list:
    return db.q("SELECT * FROM expense_categories WHERE company_id=? ORDER BY nama",
                (company_id,))


def ajukan_biaya(company_id: int, tanggal: str, uraian: str, jumlah: int,
                 akun_beban: str = "6023", kategori_id: Optional[int] = None,
                 vendor: str = "", partner_id: Optional[int] = None,
                 cost_center_id: Optional[int] = None, project_id: Optional[int] = None,
                 branch_id: Optional[int] = None, tipe: str = "langsung",
                 diajukan_oleh: str = "", akun_kas: str = "",
                 catatan: str = "", user_id=None, username: str = "") -> int:
    jumlah = ringkas_angka(jumlah)
    if jumlah <= 0:
        raise ValueError("Jumlah biaya harus lebih besar dari nol.")
    if not uraian.strip():
        raise ValueError("Uraian biaya wajib diisi.")
    if tipe not in ("langsung", "reimbursement", "berkala"):
        raise ValueError("Tipe biaya harus langsung, reimbursement, atau berkala.")

    if not akun_kas:
        row = db.q1("SELECT kode FROM accounts WHERE company_id=? AND is_kas_bank=1 "
                    "ORDER BY kode LIMIT 1", (company_id,))
        akun_kas = row["kode"] if row else "1001"

    # tentukan perlu persetujuan
    perlu_setuju = False
    if kategori_id:
        kat = db.q1("SELECT * FROM expense_categories WHERE id=?", (kategori_id,))
        if kat:
            if kat["perlu_persetujuan"]:
                perlu_setuju = True
            if kat["batas_nilai"] and jumlah >= kat["batas_nilai"]:
                perlu_setuju = True

    status = "diajukan" if (perlu_setuju or tipe == "reimbursement") else "disetujui"
    nomor = nomor_berikut(company_id, "EXP", int(tanggal[:4]))

    cur = db.ex(
        """INSERT INTO expenses(company_id, nomor, tanggal, kategori_id, uraian,
           jumlah, akun_beban, akun_kas, partner_id, vendor, cost_center_id,
           project_id, branch_id, tipe, diajukan_oleh, status, catatan)
           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (company_id, nomor, tanggal, kategori_id, uraian.strip(), jumlah,
         akun_beban, akun_kas, partner_id, vendor, cost_center_id, project_id,
         branch_id, tipe, diajukan_oleh or username, status, catatan))
    exp_id = cur.lastrowid
    catat_riwayat(company_id, "expenses", exp_id, "create", user_id, username,
                  "", "", nomor)
    return exp_id


def setujui_biaya(expense_id: int, disetujui: bool, oleh: str = "",
                  catatan: str = "") -> None:
    row = db.q1("SELECT * FROM expenses WHERE id=?", (expense_id,))
    if row is None:
        raise ValueError("Biaya tidak ditemukan.")
    if row["status"] not in ("diajukan", "draft"):
        raise ValueError(f"Biaya dengan status '{row['status']}' tidak dapat disetujui lagi.")

    status = "disetujui" if disetujui else "ditolak"
    db.ex("""UPDATE expenses SET status=?, disetujui_oleh=?, tanggal_setuju=?,
             catatan_persetujuan=? WHERE id=?""",
          (status, oleh, hari_ini(), catatan, expense_id))
    catat_riwayat(row["company_id"], "expenses", expense_id,
                  "approve" if disetujui else "reject", None, oleh)


def bayar_biaya(expense_id: int, tanggal: Optional[str] = None, user_id=None,
                username: str = "") -> int:
    """Bayar biaya yang sudah disetujui dan buat jurnalnya."""
    row = db.q1("SELECT * FROM expenses WHERE id=?", (expense_id,))
    if row is None:
        raise ValueError("Biaya tidak ditemukan.")
    if row["dibayar"]:
        raise ValueError("Biaya ini sudah dibayar.")
    if row["status"] not in ("disetujui", "reimbursement"):
        raise ValueError(
            f"Biaya berstatus '{row['status']}' belum dapat dibayar. "
            "Setujui terlebih dahulu.")

    tanggal = tanggal or hari_ini()
    cid = row["company_id"]

    baris = [{
        "kode_akun": row["akun_beban"], "debit": int(row["jumlah"]), "kredit": 0,
        "lawan_transaksi": row["vendor"] or row["uraian"],
        "catatan": f"Biaya {row['nomor']}: {row['uraian']}",
    }, {
        "kode_akun": row["akun_kas"], "debit": 0, "kredit": int(row["jumlah"]),
        "lawan_transaksi": row["vendor"] or "",
        "catatan": f"Pembayaran biaya {row['nomor']}",
    }]
    entry_id = acc.simpan_jurnal(cid, tanggal, f"EXP-{row['nomor']}",
                                 f"Beban {row['uraian']}", baris,
                                 sumber="pajak", ref_id=expense_id,
                                 user_id=user_id)

    status_baru = "reimbursed" if row["tipe"] == "reimbursement" else "dibayar"
    db.ex("""UPDATE expenses SET dibayar=1, tanggal_bayar=?, status=?,
             journal_entry_id=? WHERE id=?""",
          (tanggal, status_baru, entry_id, expense_id))
    catat_riwayat(cid, "expenses", expense_id, "pay", user_id, username)
    return entry_id


def daftar_biaya(company_id: int, tahun: Optional[int] = None, status: str = "",
                 kategori_id: Optional[int] = None, cari: str = "") -> list:
    sql = """SELECT e.*, c.nama AS kategori_nama
             FROM expenses e
             LEFT JOIN expense_categories c ON c.id = e.kategori_id
             WHERE e.company_id=? AND e.deleted_at IS NULL"""
    params: list = [company_id]
    if tahun:
        sql += " AND substr(e.tanggal,1,4)=?"
        params.append(str(tahun))
    if status:
        sql += " AND e.status=?"
        params.append(status)
    if kategori_id:
        sql += " AND e.kategori_id=?"
        params.append(kategori_id)
    if cari:
        sql += " AND (e.uraian LIKE ? OR e.nomor LIKE ? OR e.vendor LIKE ?)"
        params += [f"%{cari}%"] * 3
    sql += " ORDER BY e.tanggal DESC, e.id DESC"
    return db.q(sql, params)


def hapus_biaya(expense_id: int, oleh: str = "") -> None:
    row = db.q1("SELECT * FROM expenses WHERE id=?", (expense_id,))
    if row is None:
        return
    if row["dibayar"]:
        raise ValueError("Biaya yang sudah dibayar tidak dapat dihapus. "
                         "Batalkan jurnalnya terlebih dahulu bila perlu.")
    ke_recycle_bin(row["company_id"], "expenses", expense_id, row["nomor"],
                   dict(row), oleh)
    db.ex("UPDATE expenses SET deleted_at=datetime('now','localtime') WHERE id=?",
          (expense_id,))


def ringkasan_biaya(company_id: int, tahun: int) -> list:
    return db.q("""SELECT COALESCE(c.nama,'Tanpa Kategori') AS kategori,
                          COUNT(*) AS jumlah_transaksi,
                          SUM(e.jumlah) AS total
                   FROM expenses e
                   LEFT JOIN expense_categories c ON c.id = e.kategori_id
                   WHERE e.company_id=? AND substr(e.tanggal,1,4)=?
                     AND e.deleted_at IS NULL AND e.status != 'ditolak'
                   GROUP BY COALESCE(c.nama,'Tanpa Kategori')
                   ORDER BY total DESC""", (company_id, str(tahun)))


# ==========================================================================
# REKENING KAS/BANK
# ==========================================================================
def buat_kas_bank(company_id: int, nama: str, tipe: str = "bank", **kw) -> int:
    """Tambah rekening kas/bank baru.

    Saldo awal dicatat lewat jurnal agar neraca tetap seimbang. Bila pengguna
    tidak menyebut sumber dananya, selisihnya masuk ke akun ekuitas "Saldo
    Awal" - cara yang sama dipakai pembukuan standar saat memindahkan saldo
    dari pembukuan lama.
    """
    if tipe not in ("kas", "bank", "ewallet"):
        raise ValueError("Tipe harus kas, bank, atau ewallet.")
    kode = kw.get("kode") or nomor_berikut(
        company_id, "BANK" if tipe == "bank" else "KAS")

    saldo_awal = ringkas_angka(kw.get("saldo_awal"))
    akun_lawan = kw.get("akun_lawan") or ""
    if saldo_awal and not akun_lawan:
        akun_lawan = _akun_saldo_awal(company_id)

    akun_buku = kw.get("akun_buku") or _buat_akun_kas_bank(company_id, nama, tipe)

    with db.tx() as conn:
        bank_id = None
        if tipe in ("bank", "ewallet"):
            cur = conn.execute(
                """INSERT INTO bank_accounts(company_id, kode, nama, nama_bank,
                   nomor_rekening, pemilik, akun_buku, saldo_awal)
                   VALUES(?,?,?,?,?,?,?,?)""",
                (company_id, kode, nama.strip(), kw.get("nama_bank", ""),
                 kw.get("nomor_rekening", ""), kw.get("pemilik", ""), akun_buku,
                 saldo_awal))
            bank_id = cur.lastrowid

        cur = conn.execute(
            """INSERT INTO cash_accounts(company_id, kode, nama, tipe, akun_buku,
               bank_account_id, saldo_awal, penanggung_jawab)
               VALUES(?,?,?,?,?,?,?,?)""",
            (company_id, kode, nama.strip(), tipe, akun_buku, bank_id,
             saldo_awal, kw.get("penanggung_jawab", "")))
        cash_id = cur.lastrowid

    if saldo_awal:
        baris = [
            {"kode_akun": akun_buku, "debit": saldo_awal, "kredit": 0,
             "catatan": f"Saldo awal rekening {nama}"},
            {"kode_akun": akun_lawan, "debit": 0, "kredit": saldo_awal,
             "catatan": f"Saldo awal rekening {nama}"},
        ]
        acc.simpan_jurnal(company_id, hari_ini(), f"SA-{kode}",
                          f"Saldo awal rekening {nama}", baris,
                          sumber="penyesuaian", user_id=kw.get("user_id"))

    catat_riwayat(company_id, "cash_accounts", cash_id, "create", kw.get("user_id"),
                  kw.get("username", ""), "", "", nama)
    return cash_id


def _akun_saldo_awal(company_id: int) -> str:
    """Akun ekuitas penyeimbang untuk saldo awal yang sumbernya belum jelas."""
    kode = "3900"
    akun = db.q1("SELECT kode FROM accounts WHERE company_id=? AND kode=?",
                 (company_id, kode))
    if not akun:
        services.create_account(
            company_id, kode, "Saldo Awal (Penyeimbang)", "Ekuitas", "", "Modal",
            "Kredit", "Deductible/Taxable",
            "Penyeimbang saldo awal rekening kas/bank. Boleh dipindahkan ke "
            "akun modal yang tepat lewat jurnal penyesuaian.", 0, True)
    return kode


def _buat_akun_kas_bank(company_id: int, nama: str, tipe: str,
                        saldo_awal: int = 0) -> str:
    """Pilih akun kas/bank untuk rekening baru.

    Template COA sudah menyediakan akun kas, bank, dan dompet digital.
    Akun tersebut dipakai lebih dulu bila belum terhubung ke rekening lain,
    sehingga tidak muncul akun tambahan yang menduplikasi fungsinya.
    """
    kandidat = {"kas": ["1001", "1004"], "bank": ["1003", "1004"],
                "ewallet": ["1005"]}.get(tipe, ["1001"])
    dipakai = {r["akun_buku"] for r in db.q(
        "SELECT akun_buku FROM cash_accounts WHERE company_id=? AND "
        "deleted_at IS NULL", (company_id,))}

    for kode in kandidat:
        if kode in dipakai:
            continue
        akun = db.q1("SELECT kode FROM accounts WHERE company_id=? AND kode=?",
                     (company_id, kode))
        if akun:
            return kode

    # semua akun template sudah terpakai: buat akun baru dengan nomor lanjut
    prefix = {"kas": "1001", "bank": "1003", "ewallet": "1005"}.get(tipe, "1001")
    baris = db.q("SELECT kode FROM accounts WHERE company_id=? AND kode LIKE ? "
                 "ORDER BY kode", (company_id, f"{prefix}%"))
    nomor = 1
    for r in baris:
        sisa = r["kode"][len(prefix):]
        if sisa.isdigit():
            nomor = max(nomor, int(sisa) + 1)
    kode = f"{prefix}{nomor:02d}"
    while db.q1("SELECT 1 FROM accounts WHERE company_id=? AND kode=?",
                (company_id, kode)):
        nomor += 1
        kode = f"{prefix}{nomor:02d}"

    services.create_account(
        company_id, kode, nama, "Aset", "", "Kas & Bank", "Debit",
        "Deductible/Taxable",
        f"Akun {'kas' if tipe == 'kas' else 'bank'} untuk {nama}.",
        int(saldo_awal or 0), True)
    return kode


def daftar_kas_bank(company_id: int, hanya_aktif: bool = True) -> list:
    sql = """SELECT ca.*, ba.nama_bank, ba.nomor_rekening,
                    COALESCE(a.saldo_awal,0) +
                      COALESCE((SELECT SUM(jl.debit - jl.kredit) FROM journal_lines jl
                                WHERE jl.company_id=ca.company_id
                                  AND jl.kode_akun=ca.akun_buku),0) AS saldo_buku
             FROM cash_accounts ca
             LEFT JOIN bank_accounts ba ON ba.id = ca.bank_account_id
             LEFT JOIN accounts a ON a.company_id=ca.company_id AND a.kode=ca.akun_buku
             WHERE ca.company_id=? AND ca.deleted_at IS NULL"""
    if hanya_aktif:
        sql += " AND ca.is_active=1"
    sql += " ORDER BY ca.tipe, ca.kode"
    return db.q(sql, (company_id,))


def saldo_kas_bank(company_id: int) -> dict:
    total_kas = total_bank = total_ewallet = 0
    for r in daftar_kas_bank(company_id):
        nilai = int(r["saldo_buku"] or 0)
        if r["tipe"] == "kas":
            total_kas += nilai
        elif r["tipe"] == "bank":
            total_bank += nilai
        else:
            total_ewallet += nilai
    return {
        "kas": total_kas, "bank": total_bank, "ewallet": total_ewallet,
        "total": total_kas + total_bank + total_ewallet,
    }


def transfer_kas_bank(company_id: int, tanggal: str, dari_kode: str, ke_kode: str,
                      jumlah: int, keterangan: str = "", biaya_admin: int = 0,
                      user_id=None) -> int:
    """Pindahkan dana antar rekening kas/bank (termasuk biaya admin)."""
    jumlah = ringkas_angka(jumlah)
    if jumlah <= 0:
        raise ValueError("Jumlah transfer harus lebih besar dari nol.")
    if dari_kode == ke_kode:
        raise ValueError("Rekening asal dan tujuan tidak boleh sama.")

    dari = db.q1("SELECT * FROM cash_accounts WHERE company_id=? AND akun_buku=?",
                 (company_id, dari_kode))
    ke = db.q1("SELECT * FROM cash_accounts WHERE company_id=? AND akun_buku=?",
               (company_id, ke_kode))
    if dari is None or ke is None:
        raise ValueError("Rekening asal atau tujuan tidak ditemukan.")

    nomor = f"TRF-{date.today():%Y%m%d}-{int(datetime.now().timestamp()) % 10000:04d}"
    baris = [
        {"kode_akun": ke_kode, "debit": jumlah, "kredit": 0,
         "catatan": f"Transfer masuk dari {dari['nama']}"},
        {"kode_akun": dari_kode, "debit": 0, "kredit": jumlah,
         "catatan": f"Transfer keluar ke {ke['nama']}"},
    ]
    if biaya_admin > 0:
        akun_admin = "6009" if db.q1(
            "SELECT 1 FROM accounts WHERE company_id=? AND kode='6009'",
            (company_id,)) else "8002"
        baris.append({"kode_akun": akun_admin, "debit": ringkas_angka(biaya_admin),
                      "kredit": 0, "catatan": "Biaya transfer"})
        baris.append({"kode_akun": dari_kode, "debit": 0,
                      "kredit": ringkas_angka(biaya_admin),
                      "catatan": "Biaya transfer"})

    entry_id = acc.simpan_jurnal(company_id, tanggal, nomor,
                                 f"Transfer {dari['nama']}  {ke['nama']}"
                                 + (f" ({keterangan})" if keterangan else ""),
                                 baris, sumber="manual", user_id=user_id)
    return entry_id


# ==========================================================================
# BANK: IMPOR MUTASI & REKONSILIASI
# ==========================================================================
def impor_mutasi_bank(company_id: int, bank_account_id: int, baris: list[dict],
                      user_id=None) -> dict:
    """
    Impor mutasi rekening koran.
    Setiap baris: {tanggal, uraian, referensi, debit, kredit, saldo}
    Deteksi duplikat berdasarkan tanggal + referensi + nilai.
    """
    bank = db.q1("SELECT * FROM bank_accounts WHERE id=?", (bank_account_id,))
    if bank is None:
        raise ValueError("Rekening bank tidak ditemukan.")

    masuk = duplikat = 0
    with db.tx() as conn:
        for b in baris:
            tanggal = str(b.get("tanggal", ""))[:10]
            if not tanggal:
                continue
            debit = ringkas_angka(b.get("debit"))
            kredit = ringkas_angka(b.get("kredit"))
            ref = str(b.get("referensi", "") or "")

            ada = conn.execute(
                """SELECT 1 FROM bank_transactions WHERE bank_account_id=?
                   AND tanggal=? AND debit=? AND kredit=?
                   AND COALESCE(referensi,'')=?""",
                (bank_account_id, tanggal, debit, kredit, ref)).fetchone()
            if ada:
                duplikat += 1
                continue

            conn.execute(
                """INSERT INTO bank_transactions(company_id, bank_account_id,
                   tanggal, uraian, referensi, debit, kredit, saldo, status)
                   VALUES(?,?,?,?,?,?,?,?,'belum')""",
                (company_id, bank_account_id, tanggal,
                 str(b.get("uraian", "") or ""), ref, debit, kredit,
                 ringkas_angka(b.get("saldo"))))
            masuk += 1

    return {"berhasil": masuk, "duplikat": duplikat, "total": len(baris)}


def impor_mutasi_dari_csv(company_id: int, bank_account_id: int, isi_csv: str,
                          user_id=None) -> dict:
    """
    Impor mutasi dari teks CSV. Format kolom yang dikenali (header fleksibel):
    tanggal, uraian/keterangan, referensi, debit/masuk, kredit/keluar, saldo
    """
    teks = isi_csv.lstrip("\ufeff")
    sniffer = csv.Sniffer()
    try:
        dialek = sniffer.sniff(teks[:2000], delimiters=",;\t|")
        pemisah = dialek.delimiter
    except csv.Error:
        pemisah = ";" if ";" in teks[:500] else ","

    reader = csv.reader(io.StringIO(teks), delimiter=pemisah)
    semua = [r for r in reader if any(c.strip() for c in r)]
    if not semua:
        raise ValueError("Berkas CSV kosong.")

    def cari_kolom(header: list[str], kandidat: list[str]) -> int:
        for i, h in enumerate(header):
            hl = h.strip().lower()
            if any(k in hl for k in kandidat):
                return i
        return -1

    header = [h.strip().lower() for h in semua[0]]
    i_tgl = cari_kolom(header, ["tanggal", "date", "tgl"])
    i_ura = cari_kolom(header, ["uraian", "keterangan", "description", "desc"])
    i_ref = cari_kolom(header, ["referensi", "ref", "no"])
    i_masuk = cari_kolom(header, ["debit", "masuk", "kredit_masuk", "in"])
    i_keluar = cari_kolom(header, ["kredit", "keluar", "out"])
    i_saldo = cari_kolom(header, ["saldo", "balance"])

    if i_tgl < 0:
        raise ValueError("Kolom tanggal tidak ditemukan pada berkas CSV.")

    def angka(teks: str) -> int:
        if not teks:
            return 0
        bersih = str(teks).replace("Rp", "").replace(" ", "")
        if "," in bersih and "." in bersih:
            if bersih.rfind(",") > bersih.rfind("."):
                bersih = bersih.replace(".", "").replace(",", ".")
            else:
                bersih = bersih.replace(",", "")
        elif "," in bersih:
            bersih = bersih.replace(".", "").replace(",", ".")
        elif bersih.count(".") > 1:
            bersih = bersih.replace(".", "")
        try:
            return int(round(float(bersih)))
        except ValueError:
            return 0

    def tanggal_iso(teks: str) -> str:
        teks = str(teks).strip()
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y",
                    "%Y/%m/%d", "%m/%d/%Y", "%d %b %Y", "%d %B %Y"):
            try:
                return datetime.strptime(teks[:11].strip(), fmt).date().isoformat()
            except ValueError:
                continue
        return teks[:10]

    baris = []
    for r in semua[1:]:
        if i_tgl >= len(r):
            continue
        d = {"tanggal": tanggal_iso(r[i_tgl])}
        if i_ura >= 0 and i_ura < len(r):
            d["uraian"] = r[i_ura]
        if i_ref >= 0 and i_ref < len(r):
            d["referensi"] = r[i_ref]
        if i_masuk >= 0 and i_masuk < len(r):
            d["debit"] = angka(r[i_masuk])
        if i_keluar >= 0 and i_keluar < len(r):
            d["kredit"] = angka(r[i_keluar])
        if i_saldo >= 0 and i_saldo < len(r):
            d["saldo"] = angka(r[i_saldo])
        if d.get("debit") or d.get("kredit"):
            baris.append(d)

    return impor_mutasi_bank(company_id, bank_account_id, baris, user_id)


def daftar_mutasi_bank(company_id: int, bank_account_id: Optional[int] = None,
                       status: str = "", periode: str = "") -> list:
    sql = """SELECT bt.*, ba.nama AS nama_rekening, ba.nomor_rekening
             FROM bank_transactions bt
             JOIN bank_accounts ba ON ba.id = bt.bank_account_id
             WHERE bt.company_id=?"""
    params: list = [company_id]
    if bank_account_id:
        sql += " AND bt.bank_account_id=?"
        params.append(bank_account_id)
    if status:
        sql += " AND bt.status=?"
        params.append(status)
    if periode:
        sql += " AND substr(bt.tanggal,1,7)=?"
        params.append(periode)
    sql += " ORDER BY bt.tanggal DESC, bt.id DESC"
    return db.q(sql, params)


def cocokkan_mutasi(transaction_id: int, entry_id: Optional[int],
                    user_id=None) -> None:
    """Tandai mutasi bank sudah dicocokkan dengan jurnal."""
    row = db.q1("SELECT * FROM bank_transactions WHERE id=?", (transaction_id,))
    if row is None:
        raise ValueError("Mutasi tidak ditemukan.")
    if entry_id:
        db.ex("""UPDATE bank_transactions SET status='tercocok',
                 journal_entry_id=? WHERE id=?""", (entry_id, transaction_id))
    else:
        db.ex("UPDATE bank_transactions SET status='dikecualikan' WHERE id=?",
              (transaction_id,))
    catat_riwayat(row["company_id"], "bank_transactions", transaction_id,
                  "match", user_id)


def jurnal_dari_mutasi(company_id: int, transaction_id: int, akun_lawan: str,
                       user_id=None) -> int:
    """
    Buat jurnal dari mutasi bank yang belum tercatat.
    Debit/kredit mengikuti arah uang pada rekening koran.
    """
    trx = db.q1("SELECT * FROM bank_transactions WHERE id=?", (transaction_id,))
    if trx is None:
        raise ValueError("Mutasi tidak ditemukan.")
    if trx["status"] == "tercocok":
        raise ValueError("Mutasi ini sudah dicocokkan.")

    bank = db.q1("SELECT * FROM bank_accounts WHERE id=?", (trx["bank_account_id"],))
    akun_bank = bank["akun_buku"] if bank else "1002"
    masuk = int(trx["debit"] or 0)
    keluar = int(trx["kredit"] or 0)
    if masuk <= 0 and keluar <= 0:
        raise ValueError("Mutasi tidak memiliki nilai.")

    if masuk > 0:
        baris = [{"kode_akun": akun_bank, "debit": masuk, "kredit": 0,
                  "catatan": trx["uraian"] or "Mutasi bank"},
                 {"kode_akun": akun_lawan, "debit": 0, "kredit": masuk,
                  "catatan": trx["uraian"] or "Mutasi bank"}]
        nilai = masuk
    else:
        baris = [{"kode_akun": akun_lawan, "debit": keluar, "kredit": 0,
                  "catatan": trx["uraian"] or "Mutasi bank"},
                 {"kode_akun": akun_bank, "debit": 0, "kredit": keluar,
                  "catatan": trx["uraian"] or "Mutasi bank"}]
        nilai = keluar

    nomor = f"BANK-{trx['tanggal'].replace('-', '')}-{transaction_id}"
    entry_id = acc.simpan_jurnal(company_id, trx["tanggal"], nomor,
                                 trx["uraian"] or f"Mutasi bank {tx.rupiah(nilai)}",
                                 baris, sumber="manual", user_id=user_id)
    db.ex("""UPDATE bank_transactions SET status='tercocok', journal_entry_id=?
             WHERE id=?""", (entry_id, transaction_id))
    return entry_id


def buat_rekonsiliasi(company_id: int, bank_account_id: int, periode: str,
                      saldo_bank: int, dibuat_oleh: str = "") -> int:
    """Hitung selisih antara saldo menurut bank dan saldo menurut buku."""
    bank = db.q1("SELECT * FROM bank_accounts WHERE id=?", (bank_account_id,))
    if bank is None:
        raise ValueError("Rekening bank tidak ditemukan.")

    akhir = f"{periode}-31" if periode.endswith("-12") else \
        (datetime.fromisoformat(f"{periode}-01").date() +
         timedelta(days=32)).replace(day=1) - timedelta(days=1)
    akhir = akhir.isoformat() if hasattr(akhir, "isoformat") else str(akhir)

    akun = db.q1("SELECT saldo_awal FROM accounts WHERE company_id=? AND kode=?",
                 (company_id, bank["akun_buku"]))
    saldo_awal = int(akun["saldo_awal"]) if akun else 0
    mutasi = int(db.scalar(
        """SELECT COALESCE(SUM(jl.debit - jl.kredit),0) FROM journal_lines jl
           JOIN journal_entries je ON je.id = jl.entry_id
           WHERE jl.company_id=? AND jl.kode_akun=? AND je.tanggal <= ?""",
        (company_id, bank["akun_buku"], akhir)))
    saldo_buku = saldo_awal + mutasi
    selisih = ringkas_angka(saldo_bank) - saldo_buku

    with db.tx() as conn:
        ada = conn.execute("SELECT id FROM bank_reconciliations WHERE bank_account_id=? "
                           "AND periode=?", (bank_account_id, periode)).fetchone()
        if ada:
            conn.execute("""UPDATE bank_reconciliations SET saldo_bank=?, saldo_buku=?,
                            selisih=?, catatan=?, dibuat_oleh=? WHERE id=?""",
                         (ringkas_angka(saldo_bank), saldo_buku, selisih,
                          "", dibuat_oleh, ada["id"]))
            rec_id = ada["id"]
        else:
            cur = conn.execute(
                """INSERT INTO bank_reconciliations(company_id, bank_account_id,
                   periode, saldo_bank, saldo_buku, selisih, status, dibuat_oleh)
                   VALUES(?,?,?,?,?,?,'proses',?)""",
                (company_id, bank_account_id, periode, ringkas_angka(saldo_bank),
                 saldo_buku, selisih, dibuat_oleh))
            rec_id = cur.lastrowid
    return rec_id


def daftar_rekonsiliasi(company_id: int, bank_account_id: Optional[int] = None) -> list:
    sql = """SELECT br.*, ba.nama AS nama_rekening, ba.nomor_rekening
             FROM bank_reconciliations br
             JOIN bank_accounts ba ON ba.id = br.bank_account_id
             WHERE br.company_id=?"""
    params: list = [company_id]
    if bank_account_id:
        sql += " AND br.bank_account_id=?"
        params.append(bank_account_id)
    sql += " ORDER BY br.periode DESC"
    return db.q(sql, params)


def selesaikan_rekonsiliasi(rec_id: int, catatan: str = "", user_id=None) -> None:
    db.ex("UPDATE bank_reconciliations SET status='selesai', catatan=? WHERE id=?",
          (catatan, rec_id))
    row = db.q1("SELECT company_id FROM bank_reconciliations WHERE id=?", (rec_id,))
    if row:
        catat_riwayat(row["company_id"], "bank_reconciliations", rec_id,
                      "selesai", user_id)


def mutasi_belum_cocok(company_id: int, bank_account_id: Optional[int] = None) -> list:
    return daftar_mutasi_bank(company_id, bank_account_id, status="belum")


# ==========================================================================
# DIMENSI: COST CENTER, PROYEK, CABANG
# ==========================================================================
def buat_cost_center(company_id: int, nama: str, **kw) -> int:
    kode = kw.get("kode") or nomor_berikut(company_id, "CC")
    cur = db.ex("""INSERT INTO cost_centers(company_id, kode, nama, penanggung_jawab,
                  anggaran) VALUES(?,?,?,?,?)""",
                (company_id, kode, nama.strip(), kw.get("penanggung_jawab", ""),
                 ringkas_angka(kw.get("anggaran"))))
    return cur.lastrowid


def daftar_cost_center(company_id: int) -> list:
    return db.q("SELECT * FROM cost_centers WHERE company_id=? AND is_active=1 "
                "ORDER BY kode", (company_id,))


def buat_proyek(company_id: int, nama: str, **kw) -> int:
    kode = kw.get("kode") or nomor_berikut(company_id, "PRJ")
    cur = db.ex("""INSERT INTO projects(company_id, kode, nama, partner_id,
                  tanggal_mulai, tanggal_selesai, nilai_kontrak, anggaran, status,
                  catatan) VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (company_id, kode, nama.strip(), kw.get("partner_id"),
                 kw.get("tanggal_mulai"), kw.get("tanggal_selesai"),
                 ringkas_angka(kw.get("nilai_kontrak")),
                 ringkas_angka(kw.get("anggaran")),
                 kw.get("status", "berjalan"), kw.get("catatan", "")))
    return cur.lastrowid


def daftar_proyek(company_id: int, status: str = "") -> list:
    sql = """SELECT p.*, m.nama AS partner_nama
             FROM projects p
             LEFT JOIN partners m ON m.id = p.partner_id
             WHERE p.company_id=?"""
    params: list = [company_id]
    if status:
        sql += " AND p.status=?"
        params.append(status)
    sql += " ORDER BY p.kode"
    return db.q(sql, params)


def buat_cabang(company_id: int, nama: str, **kw) -> int:
    kode = kw.get("kode") or nomor_berikut(company_id, "CAB")
    cur = db.ex("""INSERT INTO branches(company_id, kode, nama, alamat, kota,
                  penanggung_jawab, npwp) VALUES(?,?,?,?,?,?,?)""",
                (company_id, kode, nama.strip(), kw.get("alamat", ""),
                 kw.get("kota", ""), kw.get("penanggung_jawab", ""),
                 kw.get("npwp", "")))
    return cur.lastrowid


def daftar_cabang(company_id: int) -> list:
    return db.q("SELECT * FROM branches WHERE company_id=? AND is_active=1 "
                "ORDER BY kode", (company_id,))


def laba_rugi_dimensi(company_id: int, tahun: int, dimensi: str = "cost_center") -> list:
    """
    Laba rugi per dimensi (cost center / proyek / cabang).
    Dihitung dari jurnal yang memiliki referensi dimensi.
    """
    kolom = {"cost_center": "cost_center_id", "proyek": "project_id",
             "cabang": "branch_id"}.get(dimensi)
    if kolom is None:
        raise ValueError("Dimensi harus cost_center, proyek, atau cabang.")

    tabel = {"cost_center": "cost_centers", "proyek": "projects",
             "cabang": "branches"}[dimensi]
    daftar = db.q(f"SELECT id, kode, nama FROM {tabel} WHERE company_id=?",
                  (company_id,))

    hasil = []
    for d in daftar:
        pendapatan = int(db.scalar(
            f"""SELECT COALESCE(SUM(e.jumlah),0) FROM expenses e
                WHERE e.company_id=? AND e.{kolom}=?
                  AND substr(e.tanggal,1,4)=? AND e.status != 'ditolak'""",
            (company_id, d["id"], str(tahun))))
        hasil.append({"kode": d["kode"], "nama": d["nama"], "beban": pendapatan,
                      "pendapatan": 0, "laba": -pendapatan})
    return hasil


# ==========================================================================
# TUTUP BUKU & BUKA BUKU
# ==========================================================================
def status_periode(company_id: int, periode: str) -> str:
    row = db.q1("SELECT status FROM fiscal_periods WHERE company_id=? AND periode=?",
                (company_id, periode))
    return row["status"] if row else "terbuka"


def daftar_periode(company_id: int, tahun: int) -> list:
    hasil = []
    for b in range(1, 13):
        p = f"{tahun}-{b:02d}"
        row = db.q1("SELECT * FROM fiscal_periods WHERE company_id=? AND periode=?",
                    (company_id, p))
        lr = acc.laba_rugi(company_id, tahun, b, beban_pajak=0)
        hasil.append({
            "periode": p,
            "nama": config.MONTH_NAMES_ID[b - 1],
            "status": row["status"] if row else "terbuka",
            "ditutup_oleh": row["ditutup_oleh"] if row else "",
            "tanggal_tutup": row["tanggal_tutup"] if row else "",
            "catatan": (row["catatan"] if row else "") or "",
            "pendapatan": lr.pendapatan_usaha,
            "beban": lr.beban_operasional + lr.hpp + lr.beban_lain,
            "laba": lr.laba_sebelum_pajak,
        })
    return hasil


def cek_periode_terbuka(company_id: int, tanggal: str) -> bool:
    periode = str(tanggal)[:7]
    return status_periode(company_id, periode) == "terbuka"


def tutup_buku(company_id: int, periode: str, oleh: str = "",
               user_id=None, buat_jurnal_penutup: bool = False) -> dict:
    """
    Tutup periode akuntansi.
    Periode tertutup tidak dapat menerima jurnal baru (dicek di layanan jurnal).
    """
    if status_periode(company_id, periode) == "tertutup":
        raise ValueError(f"Periode {periode} sudah tertutup.")

    tahun = int(periode[:4])
    bulan = int(periode[5:7])
    lr = acc.laba_rugi(company_id, tahun, bulan, beban_pajak=0)

    entry_id = None
    if buat_jurnal_penutup:
        # tutup pendapatan & beban periode ini ke saldo laba
        ns = acc.neraca_saldo(company_id, tahun, bulan)
        baris = []
        for b in ns:
            if b.tipe == "Pendapatan" and b.saldo_akhir_normal != 0:
                baris.append({"kode_akun": b.kode, "debit": b.saldo_akhir_normal,
                              "kredit": 0, "catatan": f"Tutup {b.nama}"})
            elif b.tipe == "Beban" and b.saldo_akhir_normal != 0:
                baris.append({"kode_akun": b.kode, "debit": 0,
                              "kredit": b.saldo_akhir_normal,
                              "catatan": f"Tutup {b.nama}"})
        if baris:
            akun_laba = db.q1("SELECT kode FROM accounts WHERE company_id=? "
                              "AND baris_neraca='Saldo Laba' LIMIT 1", (company_id,))
            # Cadangannya memakai akun Laba Tahun Berjalan yang selalu ada
            # pada bagan akun bawaan. Kode 3101 yang dulu tertulis di sini
            # tidak ada pada bagan akun, sehingga penutupan gagal.
            kode_laba = akun_laba["kode"] if akun_laba else "3007"
            laba = lr.laba_sebelum_pajak
            if laba >= 0:
                baris.append({"kode_akun": kode_laba, "debit": 0, "kredit": laba,
                              "catatan": "Laba periode ditutup ke Saldo Laba"})
            else:
                baris.append({"kode_akun": kode_laba, "debit": -laba, "kredit": 0,
                              "catatan": "Rugi periode ditutup ke Saldo Laba"})
            akhir = acc.periode(tahun, bulan)[1]
            entry_id = acc.simpan_jurnal(
                company_id, akhir, f"CLOSE-{periode}",
                f"Jurnal penutup periode {periode}", baris,
                sumber="penutup", user_id=user_id)

    with db.tx() as conn:
        ada = conn.execute("SELECT id FROM fiscal_periods WHERE company_id=? "
                           "AND periode=?", (company_id, periode)).fetchone()
        if ada:
            conn.execute("""UPDATE fiscal_periods SET status='tertutup',
                            ditutup_oleh=?, tanggal_tutup=?, laba_bersih=?,
                            journal_entry_id=? WHERE id=?""",
                         (oleh, hari_ini(), lr.laba_sebelum_pajak, entry_id,
                          ada["id"]))
        else:
            conn.execute("""INSERT INTO fiscal_periods(company_id, periode, status,
                            ditutup_oleh, tanggal_tutup, laba_bersih, journal_entry_id)
                            VALUES(?,?,'tertutup',?,?,?,?)""",
                         (company_id, periode, oleh, hari_ini(),
                          lr.laba_sebelum_pajak, entry_id))

    catat_riwayat(company_id, "fiscal_periods", 0, "tutup", user_id, oleh, "",
                  "", periode)
    return {"periode": periode, "laba": lr.laba_sebelum_pajak,
            "journal_entry_id": entry_id}


def buka_buku(company_id: int, periode: str, oleh: str = "", user_id=None,
              hapus_jurnal_penutup: bool = False) -> None:
    row = db.q1("SELECT * FROM fiscal_periods WHERE company_id=? AND periode=?",
                (company_id, periode))
    if row is None or row["status"] == "terbuka":
        raise ValueError(f"Periode {periode} tidak dalam status tertutup.")

    with db.tx() as conn:
        if hapus_jurnal_penutup and row["journal_entry_id"]:
            conn.execute("DELETE FROM journal_lines WHERE entry_id=?",
                         (row["journal_entry_id"],))
            conn.execute("DELETE FROM journal_entries WHERE id=?",
                         (row["journal_entry_id"],))
        conn.execute("""UPDATE fiscal_periods SET status='terbuka',
                        ditutup_oleh='', tanggal_tutup=NULL, journal_entry_id=NULL
                        WHERE id=?""", (row["id"],))

    catat_riwayat(company_id, "fiscal_periods", row["id"], "buka", user_id, oleh,
                  "", "", periode)


def periode_tertutup_sampai(company_id: int) -> str:
    row = db.q1("""SELECT MAX(periode) AS p FROM fiscal_periods
                   WHERE company_id=? AND status='tertutup'""", (company_id,))
    return row["p"] if row and row["p"] else ""


# ==========================================================================
# TRANSAKSI BERULANG
# ==========================================================================
def buat_template_berulang(company_id: int, nama: str, tipe: str,
                           tanggal_mulai: str, payload: dict, **kw) -> int:
    if tipe not in ("jurnal", "expense", "invoice"):
        raise ValueError("Tipe template harus jurnal, expense, atau invoice.")
    frekuensi = kw.get("frekuensi", "bulanan")
    if frekuensi not in ("harian", "mingguan", "bulanan", "triwulanan", "tahunan"):
        raise ValueError("Frekuensi tidak valid.")

    interval = {"harian": 1, "mingguan": 7, "bulanan": 30,
                "triwulanan": 91, "tahunan": 365}[frekuensi]
    if kw.get("interval_hari"):
        interval = int(kw["interval_hari"])

    cur = db.ex(
        """INSERT INTO recurring_templates(company_id, nama, tipe, frekuensi,
           interval_hari, tanggal_mulai, tanggal_berikut, tanggal_akhir,
           maks_kali, payload_json, aktif)
           VALUES(?,?,?,?,?,?,?,?,?,?,1)""",
        (company_id, nama.strip(), tipe, frekuensi, interval, tanggal_mulai,
         tanggal_mulai, kw.get("tanggal_akhir"), int(kw.get("maks_kali", 0) or 0),
         json.dumps(payload, ensure_ascii=False, default=str)))
    return cur.lastrowid


def daftar_template_berulang(company_id: int, aktif_saja: bool = True) -> list:
    sql = "SELECT * FROM recurring_templates WHERE company_id=? AND deleted_at IS NULL"
    if aktif_saja:
        sql += " AND aktif=1"
    sql += " ORDER BY nama"
    return db.q(sql, (company_id,))


def hapus_template_berulang(template_id: int) -> None:
    db.ex("UPDATE recurring_templates SET deleted_at=datetime('now','localtime'), "
          "aktif=0 WHERE id=?", (template_id,))


def jalankan_template_berulang(company_id: int, sampai: Optional[str] = None,
                               user_id=None) -> dict:
    """
    Jalankan semua template yang sudah jatuh tempo.
    Mengembalikan ringkasan apa yang dibuat.
    """
    sampai = sampai or hari_ini()
    dibuat: list[dict] = []
    gagal: list[dict] = []

    for t in daftar_template_berulang(company_id):
        if t["tanggal_akhir"] and t["tanggal_berikut"] and \
                t["tanggal_berikut"] > t["tanggal_akhir"]:
            continue
        if t["maks_kali"] and t["jumlah_terbuat"] >= t["maks_kali"]:
            continue

        tanggal = t["tanggal_berikut"] or t["tanggal_mulai"]
        while tanggal and tanggal <= sampai:
            if t["maks_kali"] and t["jumlah_terbuat"] >= t["maks_kali"]:
                break
            try:
                payload = json.loads(t["payload_json"] or "{}")
                ref = _jalankan_satu_template(company_id, t, payload, tanggal,
                                              user_id)
                dibuat.append({"template": t["nama"], "tanggal": tanggal,
                               "tipe": t["tipe"], "ref_id": ref})
                db.ex("""UPDATE recurring_templates SET jumlah_terbuat=jumlah_terbuat+1,
                         terakhir_jalan=? WHERE id=?""", (tanggal, t["id"]))
            except Exception as e:
                gagal.append({"template": t["nama"], "tanggal": tanggal,
                              "error": str(e)})
                break

            tanggal = tambah_hari(tanggal, int(t["interval_hari"] or 30))
            if t["tanggal_akhir"] and tanggal > t["tanggal_akhir"]:
                break

        db.ex("UPDATE recurring_templates SET tanggal_berikut=? WHERE id=?",
              (tanggal, t["id"]))

    return {"dibuat": dibuat, "gagal": gagal,
            "jumlah_dibuat": len(dibuat), "jumlah_gagal": len(gagal)}


def _jalankan_satu_template(company_id: int, template, payload: dict,
                            tanggal: str, user_id) -> int:
    tipe = template["tipe"]
    if tipe == "jurnal":
        baris = payload.get("baris", [])
        if not baris:
            raise ValueError("Template jurnal tidak memiliki baris.")
        nomor = nomor_berikut(company_id, "JU", int(tanggal[:4]))
        return acc.simpan_jurnal(company_id, tanggal, nomor,
                                 payload.get("keterangan", template["nama"]),
                                 baris, sumber="manual", user_id=user_id)
    if tipe == "expense":
        return ajukan_biaya(
            company_id, tanggal, payload.get("uraian", template["nama"]),
            ringkas_angka(payload.get("jumlah")),
            payload.get("akun_beban", "6023"),
            payload.get("kategori_id"), payload.get("vendor", ""),
            user_id=user_id)
    # invoice
    from .modules_sales import buat_invoice
    return buat_invoice(company_id, tanggal, payload.get("items", []),
                        payload.get("partner_id"), payload.get("pelanggan", ""),
                        jenis_ppn=payload.get("jenis_ppn", "Non-PKP/Tidak Dipungut"),
                        catatan=f"Dibuat otomatis oleh template: {template['nama']}",
                        user_id=user_id)


# ==========================================================================
# PENGINGAT (REMINDER)
# ==========================================================================
def buat_reminder(company_id: int, judul: str, tanggal_jatuh: str, **kw) -> int:
    cur = db.ex(
        """INSERT INTO reminders(company_id, tipe, ref_tabel, ref_id, judul,
           keterangan, tanggal_jatuh, jumlah, hari_ingat)
           VALUES(?,?,?,?,?,?,?,?,?)""",
        (company_id, kw.get("tipe", "umum"), kw.get("ref_tabel", ""),
         kw.get("ref_id"), judul.strip(), kw.get("keterangan", ""),
         tanggal_jatuh, ringkas_angka(kw.get("jumlah")),
         int(kw.get("hari_ingat", 7) or 7)))
    return cur.lastrowid


def daftar_reminder(company_id: int, status: str = "aktif") -> list:
    sql = "SELECT * FROM reminders WHERE company_id=?"
    params: list = [company_id]
    if status:
        sql += " AND status=?"
        params.append(status)
    sql += " ORDER BY tanggal_jatuh"
    return db.q(sql, params)


def reminder_jatuh_tempo(company_id: int, hari_ke_depan: int = 7) -> list:
    batas = tambah_hari(hari_ini(), hari_ke_depan)
    return db.q("""SELECT * FROM reminders WHERE company_id=? AND status='aktif'
                   AND tanggal_jatuh <= ? ORDER BY tanggal_jatuh""",
                (company_id, batas))


def selesaikan_reminder(reminder_id: int) -> None:
    db.ex("UPDATE reminders SET status='selesai' WHERE id=?", (reminder_id,))


def buat_reminder_dari_piutang(company_id: int, hari_ke_depan: int = 7) -> int:
    """Buat pengingat otomatis dari invoice yang akan jatuh tempo."""
    dibuat = 0
    for inv in db.q("""SELECT * FROM invoices WHERE company_id=?
                       AND deleted_at IS NULL AND status NOT IN ('lunas','batal')
                       AND sisa > 0 AND jatuh_tempo IS NOT NULL
                       AND jatuh_tempo <= ?""",
                    (company_id, tambah_hari(hari_ini(), hari_ke_depan))):
        ada = db.q1("""SELECT 1 FROM reminders WHERE company_id=? AND tipe='piutang'
                       AND ref_tabel='invoices' AND ref_id=? AND status='aktif'""",
                    (company_id, inv["id"]))
        if ada:
            continue
        buat_reminder(company_id, f"Tagih {inv['pelanggan']} - {inv['nomor']}",
                      inv["jatuh_tempo"], tipe="piutang", ref_tabel="invoices",
                      ref_id=inv["id"], jumlah=inv["sisa"],
                      keterangan=f"Sisa piutang {tx.rupiah(inv['sisa'])}")
        dibuat += 1
    return dibuat


def buat_reminder_dari_utang(company_id: int, hari_ke_depan: int = 7) -> int:
    dibuat = 0
    for b in db.q("""SELECT * FROM bills WHERE company_id=?
                     AND deleted_at IS NULL AND status NOT IN ('lunas','batal')
                     AND sisa > 0 AND jatuh_tempo IS NOT NULL
                     AND jatuh_tempo <= ?""",
                  (company_id, tambah_hari(hari_ini(), hari_ke_depan))):
        ada = db.q1("""SELECT 1 FROM reminders WHERE company_id=? AND tipe='utang'
                       AND ref_tabel='bills' AND ref_id=? AND status='aktif'""",
                    (company_id, b["id"]))
        if ada:
            continue
        buat_reminder(company_id, f"Bayar {b['vendor']} - {b['nomor']}",
                      b["jatuh_tempo"], tipe="utang", ref_tabel="bills",
                      ref_id=b["id"], jumlah=b["sisa"],
                      keterangan=f"Sisa utang {tx.rupiah(b['sisa'])}")
        dibuat += 1
    return dibuat


# ==========================================================================
# DOKUMEN & LAMPIRAN
# ==========================================================================
def lampirkan_dokumen(company_id: int, tabel: str, record_id: int,
                      path_sumber: str, tipe: str = "", catatan: str = "",
                      oleh: str = "") -> int:
    """Salin berkas ke folder lampiran aplikasi dan catat di database."""
    if not os.path.isfile(path_sumber):
        raise ValueError(f"Berkas tidak ditemukan: {path_sumber}")

    config.ensure_dirs()
    sub = os.path.join(config.ATTACH_DIR, f"{tabel}_{record_id}")
    os.makedirs(sub, exist_ok=True)

    nama = os.path.basename(path_sumber)
    dasar, ext = os.path.splitext(nama)
    tujuan = os.path.join(sub, nama)
    versi = 1
    while os.path.exists(tujuan):
        versi += 1
        tujuan = os.path.join(sub, f"{dasar}_v{versi}{ext}")

    shutil.copy2(path_sumber, tujuan)
    ukuran = os.path.getsize(tujuan)

    cur = db.ex(
        """INSERT INTO documents(company_id, tabel, record_id, nama_berkas,
           path_berkas, tipe, ukuran, versi, diunggah_oleh, catatan)
           VALUES(?,?,?,?,?,?,?,?,?,?)""",
        (company_id, tabel, record_id, nama, tujuan, tipe, ukuran, versi,
         oleh, catatan))
    catat_riwayat(company_id, "documents", cur.lastrowid, "create", None, oleh,
                  "", "", nama)
    return cur.lastrowid


def daftar_dokumen(company_id: int, tabel: str = "", record_id: Optional[int] = None) -> list:
    sql = "SELECT * FROM documents WHERE company_id=?"
    params: list = [company_id]
    if tabel:
        sql += " AND tabel=?"
        params.append(tabel)
    if record_id is not None:
        sql += " AND record_id=?"
        params.append(record_id)
    sql += " ORDER BY created_at DESC"
    return db.q(sql, params)


def hapus_dokumen(doc_id: int, oleh: str = "") -> None:
    row = db.q1("SELECT * FROM documents WHERE id=?", (doc_id,))
    if row is None:
        return
    try:
        if os.path.isfile(row["path_berkas"]):
            os.remove(row["path_berkas"])
    except OSError as e:
        # Berkas tidak dapat dihapus: pemakaian berkas itu masih terkunci
        # proses lain. Barisnya tetap dihapus supaya daftar dokumen bersih,
        # tetapi kegagalannya dicatat agar berkas sisa dapat ditelusuri.
        logging.getLogger("akuntansiid").warning(
            "Berkas dokumen gagal dihapus: %s (%s)", row["path_berkas"], e)
    db.ex("DELETE FROM documents WHERE id=?", (doc_id,))
    catat_riwayat(row["company_id"], "documents", doc_id, "delete", None, oleh)


# ==========================================================================
# RECYCLE BIN
# ==========================================================================
def daftar_recycle_bin(company_id: int, tabel: str = "") -> list:
    sql = "SELECT * FROM recycle_bin WHERE company_id=? AND dipulihkan=0"
    params: list = [company_id]
    if tabel:
        sql += " AND tabel=?"
        params.append(tabel)
    sql += " ORDER BY ts DESC"
    return db.q(sql, params)


def pulihkan_dari_recycle(recycle_id: int, oleh: str = "") -> dict:
    row = db.q1("SELECT * FROM recycle_bin WHERE id=?", (recycle_id,))
    if row is None:
        raise ValueError("Catatan recycle bin tidak ditemukan.")
    if row["dipulihkan"]:
        raise ValueError("Catatan ini sudah dipulihkan.")

    tabel = row["tabel"]
    data = json.loads(row["data_json"])
    record_id = row["record_id"]

    kolom_soft_delete = {"partners", "products", "invoices", "bills",
                         "sales_orders", "purchase_orders", "expenses",
                         "receipts", "vendor_payments", "credit_notes"}
    if tabel in kolom_soft_delete:
        with db.tx() as conn:
            conn.execute(f"UPDATE {tabel} SET deleted_at=NULL WHERE id=?", (record_id,))
            if tabel in ("partners", "products"):
                conn.execute(f"UPDATE {tabel} SET is_active=1 WHERE id=?", (record_id,))
            if tabel in ("invoices", "bills", "sales_orders", "purchase_orders",
                         "receipts", "vendor_payments", "credit_notes"):
                conn.execute(f"UPDATE {tabel} SET status=? WHERE id=?",
                             ("terkirim" if tabel == "invoices" else "terbuka",
                              record_id))
        db.ex("UPDATE recycle_bin SET dipulihkan=1 WHERE id=?", (recycle_id,))
        catat_riwayat(row["company_id"], tabel, record_id, "restore", None, oleh)
        return {"dipulihkan": True, "tabel": tabel, "record_id": record_id,
                "pesan": f"Data pada tabel {tabel} berhasil dipulihkan."}

    # tabel tanpa soft delete: sisipkan ulang barisnya
    try:
        kolom = [k for k in data.keys() if k != "id"]
        placeholders = ",".join("?" * len(kolom))
        db.ex(f"INSERT OR REPLACE INTO {tabel}(id,{','.join(kolom)}) "
              f"VALUES(?,{placeholders})",
              [record_id] + [data[k] for k in kolom])
        db.ex("UPDATE recycle_bin SET dipulihkan=1 WHERE id=?", (recycle_id,))
        catat_riwayat(row["company_id"], tabel, record_id, "restore", None, oleh)
        return {"dipulihkan": True, "tabel": tabel, "record_id": record_id,
                "pesan": "Data berhasil dipulihkan."}
    except Exception as e:
        raise ValueError(f"Gagal memulihkan data: {e}")


def bersihkan_recycle_bin(company_id: int, lebih_lama_dari_hari: int = 90) -> int:
    batas = tambah_hari(hari_ini(), -abs(lebih_lama_dari_hari))
    cur = db.ex("DELETE FROM recycle_bin WHERE company_id=? AND dipulihkan=0 "
                "AND ts < ?", (company_id, batas))
    return cur.rowcount if cur.rowcount else 0


# ==========================================================================
# RIWAYAT PERUBAHAN
# ==========================================================================
def riwayat_perubahan(company_id: int, tabel: str = "", record_id: Optional[int] = None,
                      limit: int = 300) -> list:
    """Riwayat perubahan data, lengkap dengan keterangan yang mudah dibaca."""
    sql = """SELECT id, ts, tabel, record_id, aksi, field,
                    nilai_lama, nilai_baru, username,
                    CASE
                      WHEN field IS NULL OR field = '' THEN aksi
                      WHEN nilai_lama IS NULL OR nilai_lama = ''
                        THEN field || '  ' || COALESCE(nilai_baru, '')
                      WHEN nilai_baru IS NULL OR nilai_baru = ''
                        THEN field || ': ' || COALESCE(nilai_lama, '') || ' dihapus'
                      ELSE field || ': ' || nilai_lama || '  ' || nilai_baru
                    END AS perubahan,
                    username AS oleh
             FROM change_history WHERE company_id=?"""
    params: list = [company_id]
    if tabel:
        sql += " AND tabel=?"
        params.append(tabel)
    if record_id is not None:
        sql += " AND record_id=?"
        params.append(record_id)
    sql += " ORDER BY ts DESC, id DESC LIMIT ?"
    params.append(limit)
    return db.q(sql, params)


# ==========================================================================
# IMPOR MASSAL
# ==========================================================================
def impor_mitra_massal(company_id: int, isi_csv: str, tipe: str = "customer",
                       user_id=None) -> dict:
    """Impor daftar customer/vendor dari CSV. Deteksi duplikat nama/NPWP."""
    teks = isi_csv.lstrip("\ufeff")
    try:
        pemisah = csv.Sniffer().sniff(teks[:2000], delimiters=",;\t").delimiter
    except csv.Error:
        pemisah = ";" if ";" in teks[:500] else ","

    baris = [r for r in csv.reader(io.StringIO(teks), delimiter=pemisah)
             if any(c.strip() for c in r)]
    if len(baris) < 2:
        raise ValueError("Berkas CSV harus memiliki baris header dan minimal satu data.")

    header = [h.strip().lower() for h in baris[0]]

    def kolom(*nama) -> int:
        for i, h in enumerate(header):
            if any(n in h for n in nama):
                return i
        return -1

    i_nama = kolom("nama", "name")
    i_npwp = kolom("npwp")
    i_email = kolom("email")
    i_telp = kolom("telepon", "phone", "hp")
    i_alamat = kolom("alamat", "address")
    i_kota = kolom("kota", "city")

    if i_nama < 0:
        raise ValueError("Kolom nama tidak ditemukan pada berkas CSV.")

    berhasil = duplikat = gagal = 0
    pesan: list[str] = []

    for r in baris[1:]:
        try:
            nama = r[i_nama].strip() if i_nama < len(r) else ""
            if not nama:
                continue
            npwp = r[i_npwp].strip() if 0 <= i_npwp < len(r) else ""

            ada = None
            if npwp:
                ada = db.q1("SELECT id FROM partners WHERE company_id=? AND npwp=?",
                            (company_id, npwp))
            if ada is None:
                ada = db.q1("SELECT id FROM partners WHERE company_id=? "
                            "AND nama=? COLLATE NOCASE", (company_id, nama))
            if ada:
                duplikat += 1
                continue

            buat_mitra(company_id, nama, tipe,
                       npwp=npwp,
                       email=r[i_email].strip() if 0 <= i_email < len(r) else "",
                       telepon=r[i_telp].strip() if 0 <= i_telp < len(r) else "",
                       alamat=r[i_alamat].strip() if 0 <= i_alamat < len(r) else "",
                       kota=r[i_kota].strip() if 0 <= i_kota < len(r) else "",
                       user_id=user_id)
            berhasil += 1
        except Exception as e:
            gagal += 1
            pesan.append(f"Baris {baris.index(r) + 1}: {e}")

    return {"berhasil": berhasil, "duplikat": duplikat, "gagal": gagal,
            "pesan": pesan[:20], "total": len(baris) - 1}


def impor_produk_massal(company_id: int, isi_csv: str, user_id=None) -> dict:
    """Impor daftar produk dari CSV."""
    teks = isi_csv.lstrip("\ufeff")
    try:
        pemisah = csv.Sniffer().sniff(teks[:2000], delimiters=",;\t").delimiter
    except csv.Error:
        pemisah = ";" if ";" in teks[:500] else ","

    baris = [r for r in csv.reader(io.StringIO(teks), delimiter=pemisah)
             if any(c.strip() for c in r)]
    if len(baris) < 2:
        raise ValueError("Berkas CSV harus memiliki header dan minimal satu data.")

    header = [h.strip().lower() for h in baris[0]]

    def kolom(*nama) -> int:
        for i, h in enumerate(header):
            if any(n in h for n in nama):
                return i
        return -1

    i_nama = kolom("nama", "name")
    i_kode = kolom("kode", "code", "sku")
    i_satuan = kolom("satuan", "unit")
    i_beli = kolom("beli", "cost", "harga_beli")
    i_jual = kolom("jual", "price", "harga_jual")
    i_stok = kolom("stok", "qty", "quantity")
    i_tipe = kolom("tipe", "type")

    if i_nama < 0:
        raise ValueError("Kolom nama produk tidak ditemukan.")

    def angka(teks: str) -> int:
        if not teks:
            return 0
        bersih = str(teks).replace("Rp", "").replace(" ", "").replace(".", "")
        bersih = bersih.replace(",", ".")
        try:
            return int(round(float(bersih)))
        except ValueError:
            return 0

    berhasil = duplikat = gagal = 0
    pesan: list[str] = []

    for n, r in enumerate(baris[1:], start=2):
        try:
            nama = r[i_nama].strip() if i_nama < len(r) else ""
            if not nama:
                continue
            kode = r[i_kode].strip() if 0 <= i_kode < len(r) else ""
            ada = None
            if kode:
                ada = db.q1("SELECT id FROM products WHERE company_id=? AND kode=?",
                            (company_id, kode))
            if ada is None:
                ada = db.q1("SELECT id FROM products WHERE company_id=? "
                            "AND nama=? COLLATE NOCASE", (company_id, nama))
            if ada:
                duplikat += 1
                continue

            buat_produk(company_id, nama,
                        kode=kode or None,
                        satuan=r[i_satuan].strip() if 0 <= i_satuan < len(r) else "pcs",
                        tipe=(r[i_tipe].strip().lower()
                              if 0 <= i_tipe < len(r) and r[i_tipe].strip()
                              else "barang"),
                        harga_beli=angka(r[i_beli]) if 0 <= i_beli < len(r) else 0,
                        harga_jual=angka(r[i_jual]) if 0 <= i_jual < len(r) else 0,
                        qty_awal=angka(r[i_stok]) if 0 <= i_stok < len(r) else 0,
                        user_id=user_id)
            berhasil += 1
        except Exception as e:
            gagal += 1
            pesan.append(f"Baris {n}: {e}")

    return {"berhasil": berhasil, "duplikat": duplikat, "gagal": gagal,
            "pesan": pesan[:20], "total": len(baris) - 1}


def impor_jurnal_massal(company_id: int, isi_csv: str, user_id=None) -> dict:
    """
    Impor jurnal dari CSV. Kolom: tanggal, no_bukti, keterangan, kode_akun,
    debit, kredit. Baris dengan no_bukti sama digabung menjadi satu entri.
    """
    teks = isi_csv.lstrip("\ufeff")
    try:
        pemisah = csv.Sniffer().sniff(teks[:2000], delimiters=",;\t").delimiter
    except csv.Error:
        pemisah = ";" if ";" in teks[:500] else ","

    baris = [r for r in csv.reader(io.StringIO(teks), delimiter=pemisah)
             if any(c.strip() for c in r)]
    if len(baris) < 2:
        raise ValueError("Berkas CSV harus memiliki header dan minimal satu data.")

    header = [h.strip().lower() for h in baris[0]]

    def kolom(*nama) -> int:
        for i, h in enumerate(header):
            if any(n in h for n in nama):
                return i
        return -1

    i_tgl = kolom("tanggal", "date")
    i_bukti = kolom("bukti", "no_bukti", "ref")
    i_ket = kolom("keterangan", "description", "uraian")
    i_akun = kolom("akun", "account", "kode")
    i_debit = kolom("debit")
    i_kredit = kolom("kredit", "credit")

    if i_tgl < 0 or i_akun < 0:
        raise ValueError("Kolom tanggal dan akun wajib ada pada berkas CSV.")

    def angka(teks: str) -> int:
        if not teks:
            return 0
        bersih = str(teks).replace("Rp", "").replace(" ", "").replace(".", "")
        bersih = bersih.replace(",", ".")
        try:
            return int(round(float(bersih)))
        except ValueError:
            return 0

    entri: dict[str, dict] = {}
    for n, r in enumerate(baris[1:], start=2):
        try:
            bukti = (r[i_bukti].strip() if 0 <= i_bukti < len(r) and r[i_bukti].strip()
                     else f"IMP-{n:04d}")
            if bukti not in entri:
                entri[bukti] = {
                    "tanggal": r[i_tgl].strip()[:10],
                    "keterangan": (r[i_ket].strip()
                                   if 0 <= i_ket < len(r) else "Impor jurnal"),
                    "baris": [],
                }
            entri[bukti]["baris"].append({
                "kode_akun": r[i_akun].strip(),
                "debit": angka(r[i_debit]) if 0 <= i_debit < len(r) else 0,
                "kredit": angka(r[i_kredit]) if 0 <= i_kredit < len(r) else 0,
            })
        except Exception:
            continue

    berhasil = gagal = 0
    pesan: list[str] = []
    for bukti, e in entri.items():
        try:
            v = acc.validasi_jurnal(e["baris"], company_id)
            if not v.valid:
                gagal += 1
                pesan.append(f"Bukti {bukti}: {'; '.join(v.errors[:2])}")
                continue
            acc.simpan_jurnal(company_id, e["tanggal"], bukti, e["keterangan"],
                              e["baris"], sumber="manual", user_id=user_id)
            berhasil += 1
        except Exception as ex:
            gagal += 1
            pesan.append(f"Bukti {bukti}: {ex}")

    return {"berhasil": berhasil, "gagal": gagal, "pesan": pesan[:20],
            "total": len(entri)}


def template_csv(untuk: str) -> str:
    """Hasilkan contoh berkas CSV untuk panduan impor."""
    contoh = {
        "customer": "nama;npwp;email;telepon;alamat;kota\n"
                    "PT Contoh Sejahtera;01.234.567.8-901.000;info@contoh.co.id;"
                    "021-1234567;Jl. Merdeka 10;Jakarta\n",
        "vendor": "nama;npwp;email;telepon;alamat;kota\n"
                  "CV Pemasok Jaya;02.345.678.9-012.000;pemasok@contoh.co.id;"
                  "021-7654321;Jl. Sudirman 5;Bandung\n",
        "produk": "kode;nama;satuan;tipe;harga_beli;harga_jual;stok\n"
                  "P0001;Kopi Arabika 250g;pcs;barang;45000;75000;100\n"
                  "P0002;Jasa Konsultasi;jam;jasa;0;350000;0\n",
        "jurnal": "tanggal;no_bukti;keterangan;kode_akun;debit;kredit\n"
                  "2026-01-15;BKM-001;Penerimaan jasa;1001;5000000;0\n"
                  "2026-01-15;BKM-001;Pendapatan jasa;4001;0;5000000\n",
    }
    return contoh.get(untuk, "")


# ==========================================================================
# PENCARIAN GLOBAL
# ==========================================================================
def cari_global(company_id: int, kata: str, batas_per_tabel: int = 8) -> list:
    """Cari kata kunci di seluruh entitas utama.

    Pencarian dijalankan pada kolom teks yang benar-benar dibaca pengguna:
    nomor dokumen, nama mitra, nama produk, kode akun, keterangan jurnal, dan
    sejenisnya. Nama tabel yang tidak punya kolom teks tidak disertakan.
    """
    if not kata or len(kata.strip()) < 2:
        return []
    k = f"%{kata.strip()}%"
    hasil: list[dict] = []

    def tambah(jenis, halaman, tabel, id_kolom, judul, sub, tanggal=""):
        for r in db.q(f"""SELECT {id_kolom} AS id, {judul} AS judul,
                                 {sub} AS keterangan
                          FROM {tabel}
                          WHERE company_id=? AND ({judul} LIKE ? OR {sub} LIKE ?)
                          LIMIT ?""", (company_id, k, k, batas_per_tabel)):
            hasil.append({
                "jenis": jenis, "halaman": halaman, "id": r["id"],
                "judul": str(r["judul"] or ""), "keterangan": str(r["keterangan"] or ""),
                "tanggal": tanggal,
            })

    # dokumen transaksi
    tambah("Invoice", "penjualan", "invoices", "id", "nomor", "pelanggan")
    tambah("Sales Order", "sales_order", "sales_orders", "id", "nomor", "pelanggan")
    tambah("Penerimaan", "penerimaan", "receipts", "id", "nomor", "pelanggan")
    tambah("Bill", "pembelian", "bills", "id", "nomor", "vendor")
    tambah("Purchase Order", "purchase_order", "purchase_orders", "id", "nomor", "vendor")

    # data induk
    tambah("Pelanggan/Pemasok", "mitra", "partners", "id", "nama", "kode")
    tambah("Produk", "produk", "products", "id", "nama", "kode")
    tambah("Karyawan", "payroll", "employees", "id", "nama", "jabatan")
    tambah("Aset", "aset", "fixed_assets", "id", "nama_aset", "kode_aset")
    tambah("Biaya", "biaya", "expenses", "id", "uraian", "nomor")
    tambah("Proyek", "dimensi", "projects", "id", "nama", "kode")

    # akun dan gudang: sering dicari saat menelusuri saldo atau stok
    tambah("Akun", "coa", "accounts", "id", "nama", "kode")
    tambah("Gudang", "produk", "warehouses", "id", "nama", "kode")

    # transaksi bank dan kas
    tambah("Transaksi Bank", "bank", "bank_transactions", "id",
           "uraian", "referensi")

    # pajak
    tambah("Faktur Pajak", "pajak_lanjutan", "faktur_pajak", "id",
           "nomor_seri", "lawan_nama")

    for r in db.q("""SELECT id, no_bukti AS judul, keterangan FROM journal_entries
                     WHERE company_id=? AND (no_bukti LIKE ? OR keterangan LIKE ?)
                     LIMIT ?""", (company_id, k, k, batas_per_tabel)):
        hasil.append({"jenis": "Jurnal", "halaman": "jurnal", "id": r["id"],
                      "judul": r["judul"], "keterangan": r["keterangan"] or "",
                      "tanggal": ""})

    return hasil


# ==========================================================================
# FILTER LANJUTAN
# ==========================================================================
def filter_invoice_lanjutan(company_id: int, **f) -> list:
    """Filter invoice dengan banyak kriteria sekaligus."""
    sql = "SELECT * FROM invoices WHERE company_id=? AND deleted_at IS NULL"
    params: list = [company_id]

    if f.get("tanggal_dari"):
        sql += " AND tanggal >= ?"
        params.append(f["tanggal_dari"])
    if f.get("tanggal_sampai"):
        sql += " AND tanggal <= ?"
        params.append(f["tanggal_sampai"])
    if f.get("jumlah_min"):
        sql += " AND total >= ?"
        params.append(ringkas_angka(f["jumlah_min"]))
    if f.get("jumlah_max"):
        sql += " AND total <= ?"
        params.append(ringkas_angka(f["jumlah_max"]))
    if f.get("partner_id"):
        sql += " AND partner_id=?"
        params.append(f["partner_id"])
    if f.get("status"):
        if f["status"] == "belum_lunas":
            sql += " AND status NOT IN ('lunas','batal')"
        else:
            sql += " AND status=?"
            params.append(f["status"])
    if f.get("terlambat"):
        sql += " AND status NOT IN ('lunas','batal') AND jatuh_tempo < ?"
        params.append(hari_ini())
    if f.get("jatuh_tempo_dari"):
        sql += " AND jatuh_tempo >= ?"
        params.append(f["jatuh_tempo_dari"])
    if f.get("jatuh_tempo_sampai"):
        sql += " AND jatuh_tempo <= ?"
        params.append(f["jatuh_tempo_sampai"])
    if f.get("cari"):
        sql += " AND (nomor LIKE ? OR pelanggan LIKE ?)"
        params += [f"%{f['cari']}%"] * 2

    urut = f.get("urut", "tanggal_desc")
    peta_urut = {
        "tanggal_desc": "tanggal DESC, id DESC",
        "tanggal_asc": "tanggal ASC, id ASC",
        "jumlah_desc": "total DESC",
        "jumlah_asc": "total ASC",
        "jatuh_tempo": "jatuh_tempo ASC",
        "sisa_desc": "sisa DESC",
    }
    sql += " ORDER BY " + peta_urut.get(urut, "tanggal DESC, id DESC")
    if f.get("limit"):
        sql += " LIMIT ?"
        params.append(int(f["limit"]))
    return db.q(sql, params)


def filter_jurnal_lanjutan(company_id: int, **f) -> list:
    sql = """SELECT je.*,
                    (SELECT COALESCE(SUM(debit),0) FROM journal_lines
                     WHERE entry_id=je.id) AS total_debit,
                    (SELECT COALESCE(SUM(kredit),0) FROM journal_lines
                     WHERE entry_id=je.id) AS total_kredit
             FROM journal_entries je WHERE je.company_id=?"""
    params: list = [company_id]

    if f.get("tanggal_dari"):
        sql += " AND je.tanggal >= ?"
        params.append(f["tanggal_dari"])
    if f.get("tanggal_sampai"):
        sql += " AND je.tanggal <= ?"
        params.append(f["tanggal_sampai"])
    if f.get("sumber"):
        sql += " AND je.sumber=?"
        params.append(f["sumber"])
    if f.get("akun"):
        sql += (" AND EXISTS (SELECT 1 FROM journal_lines jl WHERE jl.entry_id=je.id "
                "AND jl.kode_akun=?)")
        params.append(f["akun"])
    if f.get("jumlah_min"):
        sql += (" AND (SELECT COALESCE(SUM(debit),0) FROM journal_lines "
                "WHERE entry_id=je.id) >= ?")
        params.append(ringkas_angka(f["jumlah_min"]))
    if f.get("cari"):
        sql += " AND (je.keterangan LIKE ? OR je.no_bukti LIKE ?)"
        params += [f"%{f['cari']}%"] * 2

    sql += " ORDER BY je.tanggal DESC, je.id DESC"
    if f.get("limit"):
        sql += " LIMIT ?"
        params.append(int(f["limit"]))
    return db.q(sql, params)


# ==========================================================================
# KONSOLIDASI MULTI-ENTITAS
# ==========================================================================
def buat_grup_entitas(nama: str, catatan: str = "") -> int:
    cur = db.ex("INSERT INTO entity_groups(nama, catatan) VALUES(?,?)",
                (nama.strip(), catatan))
    return cur.lastrowid


def daftar_grup_entitas() -> list:
    return db.q("SELECT * FROM entity_groups ORDER BY nama")


def tambah_anggota_grup(group_id: int, company_id: int,
                        persentase: float = 100.0) -> None:
    db.ex("""INSERT INTO entity_group_members(group_id, company_id,
             persentase_kepemilikan) VALUES(?,?,?)
             ON CONFLICT(group_id, company_id) DO UPDATE SET
               persentase_kepemilikan=excluded.persentase_kepemilikan""",
          (group_id, company_id, float(persentase)))


def anggota_grup(group_id: int) -> list:
    return db.q("""SELECT egm.*, c.nama, c.bentuk
                   FROM entity_group_members egm
                   JOIN companies c ON c.id = egm.company_id
                   WHERE egm.group_id=?""", (group_id,))


def laporan_konsolidasi(group_id: int, tahun: int) -> dict:
    """
    Gabungkan laporan keuangan beberapa entitas dalam satu grup.
    Eliminasi antar-entitas belum dilakukan otomatis (perlu penyesuaian manual).
    """
    anggota = anggota_grup(group_id)
    if not anggota:
        raise ValueError("Grup ini belum memiliki anggota.")

    total = {"aset": 0, "liabilitas": 0, "ekuitas": 0, "pendapatan": 0,
             "beban": 0, "laba": 0, "kas": 0, "piutang": 0, "utang": 0}
    per_entitas = []

    for a in anggota:
        cid = a["company_id"]
        nr = acc.neraca(cid, tahun)
        lr = acc.laba_rugi(cid, tahun)
        porsi = float(a["persentase_kepemilikan"] or 100) / 100

        per_entitas.append({
            "company_id": cid, "nama": a["nama"], "bentuk": a["bentuk"],
            "persentase": a["persentase_kepemilikan"],
            "aset": nr.total_aset, "liabilitas": nr.total_liabilitas,
            "ekuitas": nr.total_ekuitas, "pendapatan": lr.pendapatan_usaha,
            "beban": lr.beban_operasional + lr.hpp + lr.beban_lain,
            "laba": lr.laba_bersih, "selisih": nr.selisih,
        })

        total["aset"] += int(nr.total_aset * porsi)
        total["liabilitas"] += int(nr.total_liabilitas * porsi)
        total["ekuitas"] += int(nr.total_ekuitas * porsi)
        total["pendapatan"] += int(lr.pendapatan_usaha * porsi)
        total["beban"] += int((lr.beban_operasional + lr.hpp + lr.beban_lain) * porsi)
        total["laba"] += int(lr.laba_bersih * porsi)
        total["kas"] += int(sum(v for k, (_, v) in nr.aset_lancar.items()
                                if k.startswith("100")) * porsi)
        total["piutang"] += int(sum(v for k, (_, v) in nr.aset_lancar.items()
                                    if k in ("1101", "1102")) * porsi)
        total["utang"] += int(nr.total_liabilitas * porsi)

    return {
        "grup_id": group_id,
        "tahun": tahun,
        "jumlah_entitas": len(anggota),
        "per_entitas": per_entitas,
        "total": total,
        "catatan": ("Konsolidasi ini menjumlahkan laporan tiap entitas sesuai "
                    "persentase kepemilikan. Transaksi antar-entitas (piutang/utang "
                    "afiliasi, penjualan antar-perusahaan) perlu dieliminasi secara "
                    "manual agar tidak terjadi penghitungan ganda."),
    }


# ==========================================================================
# AKSES JARINGAN LOKAL (LAN)
# ==========================================================================
def info_lan() -> dict:
    row = db.q1("SELECT * FROM lan_config WHERE id=1")
    if row is None:
        db.ex("INSERT INTO lan_config(id, aktif, port, host, mode) "
              "VALUES(1,0,8787,'0.0.0.0','server')")
        row = db.q1("SELECT * FROM lan_config WHERE id=1")
    d = dict(row)
    d["ip_lokal"] = alamat_ip_lokal()
    return d


def set_lan(aktif: bool = None, port: int = None, mode: str = None,
            server_host: str = None, server_port: int = None,
            server_token: str = None) -> None:
    info_lan()
    sets, params = [], []
    if aktif is not None:
        sets.append("aktif=?")
        params.append(1 if aktif else 0)
    if port is not None:
        sets.append("port=?")
        params.append(int(port))
    if mode is not None:
        if mode not in ("server", "client"):
            raise ValueError("Mode harus server atau client.")
        sets.append("mode=?")
        params.append(mode)
    if server_host is not None:
        sets.append("server_host=?")
        params.append(server_host)
    if server_port is not None:
        sets.append("server_port=?")
        params.append(int(server_port))
    if server_token is not None:
        sets.append("server_token=?")
        params.append(server_token)
    if not sets:
        return
    params.append(1)
    db.ex(f"UPDATE lan_config SET {', '.join(sets)} WHERE id=?", params)


def alamat_ip_lokal() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        try:
            return socket.gethostbyname(socket.gethostname())
        except OSError:
            return "127.0.0.1"


def token_lan_baru() -> str:
    import secrets as _secrets
    token = _secrets.token_urlsafe(24)
    db.ex("UPDATE lan_config SET token=? WHERE id=1", (token,))
    return token


def uji_koneksi_lan(host: str, port: int, timeout: float = 2.0) -> dict:
    """Periksa apakah server AkunTuntas dapat dijangkau di jaringan."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((host, int(port)))
        s.close()
        return {"ok": True, "pesan": f"Server di {host}:{port} dapat dijangkau."}
    except socket.timeout:
        return {"ok": False, "pesan": f"Waktu koneksi habis ({host}:{port})."}
    except OSError as e:
        return {"ok": False, "pesan": f"Tidak dapat terhubung: {e}"}


def buat_paket_sinkronisasi(company_id: int, path_keluaran: str) -> str:
    """
    Buat berkas paket berisi data satu perusahaan untuk dibawa ke perangkat lain.
    Berisi basis data lengkap agar integritas terjaga.
    """
    config.ensure_dirs()
    if os.path.exists(path_keluaran):
        os.remove(path_keluaran)

    with zipfile.ZipFile(path_keluaran, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(config.DB_PATH, "akuntansi.db")
        meta = {
            "company_id": company_id,
            "dibuat": datetime.now().isoformat(timespec="seconds"),
            "versi_aplikasi": config.APP_VERSION,
        }
        z.writestr("meta.json", json.dumps(meta, ensure_ascii=False, indent=2))
    return path_keluaran


# ==========================================================================
# LOGO PERUSAHAAN
# ==========================================================================
def simpan_logo(company_id: int, path_sumber: str) -> str:
    if not os.path.isfile(path_sumber):
        raise ValueError("Berkas logo tidak ditemukan.")
    ext = os.path.splitext(path_sumber)[1].lower()
    if ext not in (".png", ".jpg", ".jpeg", ".bmp"):
        raise ValueError("Format logo harus PNG, JPG, JPEG, atau BMP.")

    config.ensure_dirs()
    tujuan = os.path.join(config.ATTACH_DIR, f"logo_{company_id}{ext}")
    shutil.copy2(path_sumber, tujuan)
    db.ex("UPDATE companies SET logo_path=? WHERE id=?", (tujuan, company_id))
    return tujuan


def hapus_logo(company_id: int) -> None:
    row = db.q1("SELECT logo_path FROM companies WHERE id=?", (company_id,))
    if row and row["logo_path"] and os.path.isfile(row["logo_path"]):
        try:
            os.remove(row["logo_path"])
        except OSError as e:
            # Logo tidak dapat dihapus: berkasnya masih dipakai proses lain.
            # Rujukannya tetap dibersihkan, tetapi kegagalannya dicatat agar
            # berkas sisa dapat ditelusuri.
            logging.getLogger("akuntansiid").warning(
                "Berkas logo gagal dihapus: %s (%s)", row["logo_path"], e)
    db.ex("UPDATE companies SET logo_path='' WHERE id=?", (company_id,))
