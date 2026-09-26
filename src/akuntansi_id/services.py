"""
AkunTuntas - Lapisan Layanan (Business Services)
=================================================
Menghubungkan antarmuka pengguna dengan mesin akuntansi/pajak.

Setiap operasi di sini ATOMIK: bila gagal di tengah, tidak ada data setengah jadi.
Setiap transaksi bisnis otomatis menghasilkan JURNAL, sehingga pengguna tidak
perlu menjurnal manual (tetapi tetap bisa bila ingin).
"""
from __future__ import annotations

from typing import Optional

from . import coa, config, db
from .core import accounting as acc
from .core import analyzer as an
from .core import tax_engine as tx


# ==========================================================================
# PERUSAHAAN
# ==========================================================================
def _persen(v: float, desimal: int = 1) -> str:
    """Persen dengan koma desimal, sesuai penulisan angka Indonesia."""
    try:
        teks = f"{float(v) * 100:.{desimal}f}"
    except (TypeError, ValueError):
        return "0%"
    return teks.replace(".", ",") + "%"



def list_companies(aktif_saja: bool = True) -> list:
    sql = "SELECT * FROM companies"
    if aktif_saja:
        sql += " WHERE is_active=1"
    sql += " ORDER BY nama"
    return db.q(sql)


def get_company(company_id: int):
    return db.q1("SELECT * FROM companies WHERE id=?", (company_id,))


def create_company(nama: str, bentuk: str = "umkm_op", **kwargs) -> int:
    """
    Buat perusahaan baru beserta bagan akun sesuai bentuk badan.
    Ini langkah pertama yang harus dilakukan pengguna.

    Badan usaha kedua dan seterusnya hanya tersedia pada paket Enterprise.
    Pemeriksaan dilakukan di sini, bukan hanya di tombol, supaya tidak bisa
    dilewati lewat jalan lain.
    """
    if not nama.strip():
        raise ValueError("Nama perusahaan wajib diisi.")
    if bentuk not in config.ENTITY_TYPES:
        raise ValueError(f"Bentuk badan '{bentuk}' tidak dikenal.")

    # Perusahaan pertama selalu boleh dibuat; yang dibatasi adalah
    # penambahan badan usaha berikutnya.
    jumlah = db.q1("SELECT COUNT(*) AS n FROM companies")
    if jumlah and jumlah["n"] > 0:
        from .ui import batas_paket
        if not batas_paket.boleh_pakai(kwargs.get("lisensi"), "multi_entitas"):
            raise ValueError(
                "Menambah badan usaha lain tersedia pada paket Enterprise. "
                "Paket Standar memakai satu badan usaha.")

    tahun = kwargs.get("tahun_buku_awal") or f"{config.DEFAULT_TAX_YEAR}-01-01"

    with db.tx() as conn:
        cur = conn.execute(
            """INSERT INTO companies(
                nama, bentuk, npwp, nik, alamat, kota, kode_pos, telepon, email,
                nama_pemilik, tanggal_pendirian, tanggal_npwp, tahun_buku_awal,
                status_pkp, nomor_pkp, skema_pph, final_eligible, omzet_prev_year
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                nama.strip(), bentuk,
                kwargs.get("npwp", ""), kwargs.get("nik", ""),
                kwargs.get("alamat", ""), kwargs.get("kota", ""),
                kwargs.get("kode_pos", ""), kwargs.get("telepon", ""),
                kwargs.get("email", ""), kwargs.get("nama_pemilik", ""),
                kwargs.get("tanggal_pendirian"), kwargs.get("tanggal_npwp"),
                tahun,
                1 if kwargs.get("status_pkp") else 0,
                kwargs.get("nomor_pkp", ""),
                kwargs.get("skema_pph", "pasal31e"),
                1 if kwargs.get("final_eligible") else 0,
                int(kwargs.get("omzet_prev_year", 0) or 0),
            ),
        )
        cid = cur.lastrowid

        for kode, nama_akun, tipe, grup, baris, normal, perl, desk, kas in \
                coa.get_coa_template(bentuk):
            conn.execute(
                """INSERT INTO accounts(company_id, kode, nama, tipe, grup_lr,
                   baris_neraca, normal, perlakuan_fiskal, deskripsi, is_kas_bank)
                   VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (cid, kode, nama_akun, tipe, grup, baris, normal, perl, desk, kas),
            )

        # Checklist kepatuhan awal
        for i, (frek, area, item) in enumerate(CHECKLIST_DEFAULT):
            conn.execute(
                """INSERT INTO checklist_items(company_id, frekuensi, area, checklist, urutan)
                   VALUES(?,?,?,?,?)""",
                (cid, frek, area, item, i),
            )

        # Gudang utama — dipakai modul persediaan
        conn.execute("INSERT INTO warehouses(company_id, kode, nama, lokasi) "
                     "VALUES(?,?,?,?)", (cid, "GDG001", "Gudang Utama", ""))

        # Rekening kas & bank default agar pengguna dapat langsung bertransaksi.
        # Setiap rekening terhubung ke akun COA yang sesuai.
        akun_kas = conn.execute(
            "SELECT kode FROM accounts WHERE company_id=? AND is_kas_bank=1 "
            "ORDER BY kode", (cid,)).fetchall()
        for a in akun_kas:
            kode_akun = a["kode"]
            nama_akun = conn.execute(
                "SELECT nama FROM accounts WHERE company_id=? AND kode=?",
                (cid, kode_akun)).fetchone()["nama"]
            if "Kas Kecil" in nama_akun or "Petty" in nama_akun:
                tipe = "kas"
            elif "Dompet" in nama_akun or "QRIS" in nama_akun or "Wallet" in nama_akun:
                tipe = "ewallet"
            elif kode_akun.startswith("1001"):
                tipe = "kas"
            else:
                tipe = "bank"

            bank_id = None
            if tipe in ("bank", "ewallet"):
                bank_cur = conn.execute(
                    """INSERT INTO bank_accounts(company_id, kode, nama, akun_buku)
                       VALUES(?,?,?,?)""",
                    (cid, f"BNK{kode_akun}", nama_akun, kode_akun))
                bank_id = bank_cur.lastrowid

            conn.execute(
                """INSERT INTO cash_accounts(company_id, kode, nama, tipe,
                   akun_buku, bank_account_id)
                   VALUES(?,?,?,?,?,?)""",
                (cid, f"KB{kode_akun}", nama_akun, tipe, kode_akun, bank_id))

        # Kategori biaya dasar
        for nama_kat, akun in [("Operasional", "6003"), ("Gaji & SDM", "6001"),
                               ("Marketing", "6009"), ("Transportasi", "6005"),
                               ("Perlengkapan", "6008"), ("Lain-lain", "6023")]:
            conn.execute(
                """INSERT INTO expense_categories(company_id, nama, akun_beban)
                   VALUES(?,?,?)""", (cid, nama_kat, akun))

        # Pajak & dimensi contoh tidak dibuat agar data tetap bersih.

    db.log_action(None, "", cid, "company.create", "companies", cid, nama)
    return cid


def update_company(company_id: int, **kwargs) -> None:
    fields = ["nama", "bentuk", "npwp", "nik", "alamat", "kota", "kode_pos",
              "telepon", "email", "nama_pemilik", "tanggal_pendirian",
              "tanggal_npwp", "tahun_buku_awal", "nomor_pkp", "skema_pph",
              "omzet_prev_year", "mata_uang"]
    sets, params = [], []
    for f in fields:
        if f in kwargs:
            sets.append(f"{f}=?")
            params.append(kwargs[f])
    for f in ("status_pkp", "final_eligible"):
        if f in kwargs:
            sets.append(f"{f}=?")
            params.append(1 if kwargs[f] else 0)
    if not sets:
        return
    sets.append("updated_at=datetime('now','localtime')")
    params.append(company_id)
    db.ex(f"UPDATE companies SET {', '.join(sets)} WHERE id=?", params)
    db.log_action(None, "", company_id, "company.update", "companies", company_id,
                  ", ".join(sets))


def delete_company(company_id: int) -> None:
    db.ex("DELETE FROM companies WHERE id=?", (company_id,))
    db.log_action(None, "", company_id, "company.delete", "companies", company_id)


# ==========================================================================
# BAGAN AKUN
# ==========================================================================
def list_accounts(company_id: int, aktif_saja: bool = True) -> list:
    sql = "SELECT * FROM accounts WHERE company_id=?"
    if aktif_saja:
        sql += " AND is_active=1"
    sql += " ORDER BY kode"
    return db.q(sql, (company_id,))


def get_account(company_id: int, kode: str):
    return db.q1("SELECT * FROM accounts WHERE company_id=? AND kode=?", (company_id, kode))


def create_account(company_id: int, kode: str, nama: str, tipe: str,
                   grup_lr: str = "", baris_neraca: str = "", normal: str = "Debit",
                   perlakuan: str = "Deductible/Taxable", deskripsi: str = "",
                   saldo_awal: int = 0, is_kas_bank: bool = False) -> int:
    if not kode.strip() or not nama.strip():
        raise ValueError("Kode dan nama akun wajib diisi.")
    if get_account(company_id, kode):
        raise ValueError(f"Kode akun '{kode}' sudah dipakai.")
    if tipe not in ("Aset", "Liabilitas", "Ekuitas", "Pendapatan", "Beban"):
        raise ValueError("Tipe akun tidak valid.")
    if tipe in ("Aset", "Beban") and normal != "Debit":
        raise ValueError(f"Akun {tipe} harus bersaldo normal Debit.")
    if tipe in ("Liabilitas", "Ekuitas", "Pendapatan") and normal != "Kredit":
        raise ValueError(f"Akun {tipe} harus bersaldo normal Kredit.")

    with db.tx() as conn:
        cur = conn.execute(
            """INSERT INTO accounts(company_id, kode, nama, tipe, grup_lr, baris_neraca,
               normal, perlakuan_fiskal, deskripsi, saldo_awal, is_kas_bank)
               VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            (company_id, kode.strip(), nama.strip(), tipe, grup_lr, baris_neraca,
             normal, perlakuan, deskripsi, int(saldo_awal), 1 if is_kas_bank else 0),
        )
        aid = cur.lastrowid
    db.log_action(None, "", company_id, "account.create", "accounts", aid, f"{kode} {nama}")
    return aid


def update_account(company_id: int, kode: str, **kwargs) -> None:
    fields = ["nama", "tipe", "grup_lr", "baris_neraca", "normal",
              "perlakuan_fiskal", "deskripsi", "saldo_awal"]
    sets, params = [], []
    for f in fields:
        if f in kwargs:
            sets.append(f"{f}=?")
            params.append(kwargs[f])
    if "is_kas_bank" in kwargs:
        sets.append("is_kas_bank=?")
        params.append(1 if kwargs["is_kas_bank"] else 0)
    if "is_active" in kwargs:
        sets.append("is_active=?")
        params.append(1 if kwargs["is_active"] else 0)
    if not sets:
        return
    params.extend([company_id, kode])
    db.ex(f"UPDATE accounts SET {', '.join(sets)} WHERE company_id=? AND kode=?", params)


def hapus_account(company_id: int, kode: str) -> None:
    """Hapus akun hanya bila belum pernah dipakai di jurnal."""
    dipakai = int(db.scalar(
        "SELECT COUNT(*) FROM journal_lines WHERE company_id=? AND kode_akun=?",
        (company_id, kode)))
    if dipakai:
        raise ValueError(
            f"Akun tidak dapat dihapus karena sudah dipakai pada {dipakai} baris jurnal. "
            "Nonaktifkan saja agar tidak muncul di pilihan."
        )
    db.ex("DELETE FROM accounts WHERE company_id=? AND kode=?", (company_id, kode))


def set_saldo_awal(company_id: int, saldo: dict[str, int]) -> None:
    """
    Isi saldo awal beberapa akun sekaligus.
    Menyimpan nilai pada sisi normal akun (selalu positif).
    """
    with db.tx() as conn:
        for kode, nilai in saldo.items():
            conn.execute("UPDATE accounts SET saldo_awal=? WHERE company_id=? AND kode=?",
                         (int(nilai), company_id, kode))
    db.log_action(None, "", company_id, "account.set_saldo_awal", "accounts", "",
                  f"{len(saldo)} akun")


def cek_keseimbangan_saldo_awal(company_id: int) -> dict:
    """
    Saldo awal harus seimbang: total debit = total kredit.
    Bila tidak, neraca akan pincang sejak awal.
    """
    rows = db.q("SELECT kode, nama, tipe, normal, saldo_awal FROM accounts "
                "WHERE company_id=? AND saldo_awal != 0", (company_id,))
    total_debit = sum(r["saldo_awal"] for r in rows if r["normal"] == "Debit")
    total_kredit = sum(r["saldo_awal"] for r in rows if r["normal"] == "Kredit")
    return {
        "total_debit": total_debit,
        "total_kredit": total_kredit,
        "selisih": total_debit - total_kredit,
        "seimbang": total_debit == total_kredit,
        "jumlah_akun": len(rows),
        "rincian": [dict(r) for r in rows],
    }


# ==========================================================================
# JURNAL
# ==========================================================================
def list_jurnal(company_id: int, tahun: Optional[int] = None,
                bulan: Optional[int] = None, cari: str = "",
                limit: int = 500) -> list:
    sql = """SELECT je.*, 
                    (SELECT COALESCE(SUM(debit),0) FROM journal_lines WHERE entry_id=je.id) AS total_debit,
                    (SELECT COALESCE(SUM(kredit),0) FROM journal_lines WHERE entry_id=je.id) AS total_kredit
             FROM journal_entries je WHERE je.company_id=?"""
    params: list = [company_id]
    if tahun:
        if bulan:
            awal, akhir = acc.periode(tahun, bulan)
            sql += " AND je.tanggal BETWEEN ? AND ?"
            params += [awal, akhir]
        else:
            sql += " AND substr(je.tanggal,1,4)=?"
            params.append(str(tahun))
    if cari:
        sql += " AND (je.keterangan LIKE ? OR je.no_bukti LIKE ?)"
        params += [f"%{cari}%", f"%{cari}%"]
    sql += " ORDER BY je.tanggal DESC, je.id DESC LIMIT ?"
    params.append(limit)
    return db.q(sql, params)


def detail_jurnal(entry_id: int) -> list:
    return db.q("SELECT * FROM journal_lines WHERE entry_id=? ORDER BY id", (entry_id,))


def simpan_jurnal_manual(company_id: int, tanggal: str, no_bukti: str, keterangan: str,
                         baris: list[dict], user_id: Optional[int] = None) -> int:
    if not tanggal:
        raise ValueError("Tanggal jurnal wajib diisi.")
    if not no_bukti.strip():
        no_bukti = acc.nomor_bukti_berikut(company_id)
    return acc.simpan_jurnal(company_id, tanggal, no_bukti.strip(), keterangan,
                             baris, sumber="manual", user_id=user_id)


def hapus_jurnal(entry_id: int, user_id: Optional[int] = None) -> None:
    row = db.q1("SELECT company_id, sumber, ref_id FROM journal_entries WHERE id=?",
                (entry_id,))
    if row and row["sumber"] in ("penjualan", "pembelian"):
        # hapus jurnal yang terhubung ke subledger juga menghapus subledgernya
        tabel = "sales" if row["sumber"] == "penjualan" else "purchases"
        db.ex(f"DELETE FROM {tabel} WHERE id=?", (row["ref_id"],))
    acc.hapus_jurnal(entry_id, user_id)


def buku_besar(company_id: int, kode: str, tahun: int, bulan: Optional[int] = None) -> list:
    return acc.buku_besar(company_id, kode, tahun, bulan)


def buat_jurnal_penutup(company_id: int, tahun: int, user_id=None) -> Optional[int]:
    return acc.buat_jurnal_penutup(company_id, tahun, user_id)


# ==========================================================================
# PENJUALAN
# ==========================================================================
def list_penjualan(company_id: int, tahun: Optional[int] = None,
                   bulan: Optional[int] = None, cari: str = "") -> list:
    sql = "SELECT * FROM sales WHERE company_id=?"
    params: list = [company_id]
    if tahun:
        awal, akhir = acc.periode(tahun, bulan)
        sql += " AND tanggal BETWEEN ? AND ?"
        params += [awal, akhir]
    if cari:
        sql += " AND (no_invoice LIKE ? OR pelanggan LIKE ?)"
        params += [f"%{cari}%", f"%{cari}%"]
    sql += " ORDER BY tanggal DESC, id DESC"
    return db.q(sql, params)


def simpan_penjualan(company_id: int, tanggal: str, no_invoice: str, pelanggan: str,
                     nilai_penjualan: int, jenis_ppn: str = "Non-PKP/Tidak Dipungut",
                     npwp_nik: str = "", keterangan: str = "",
                     akun_piutang: str = "1101", akun_pendapatan: str = "4001",
                     lunas: bool = False, tanggal_bayar: Optional[str] = None,
                     catatan: str = "", user_id: Optional[int] = None,
                     buat_jurnal: bool = True) -> int:
    """
    Simpan penjualan dan (opsional) langsung buat jurnalnya.
    Bila lunas  debit Kas/Bank; bila belum  debit Piutang Usaha.
    """
    if nilai_penjualan <= 0:
        raise ValueError("Nilai penjualan harus lebih besar dari nol.")
    if not no_invoice.strip():
        raise ValueError("Nomor invoice wajib diisi.")

    ppn = tx.hitung_ppn(nilai_penjualan, jenis_ppn)
    total = nilai_penjualan + ppn.ppn
    tgl_bayar = tanggal_bayar or (tanggal if lunas else None)

    # Akun kas/bank default
    akun_kas = db.q1("SELECT kode FROM accounts WHERE company_id=? AND is_kas_bank=1 "
                     "ORDER BY kode LIMIT 1", (company_id,))
    kode_kas = akun_kas["kode"] if akun_kas else "1001"

    with db.tx() as conn:
        cur = conn.execute(
            """INSERT INTO sales(company_id, tanggal, no_invoice, pelanggan, npwp_nik,
               keterangan, nilai_penjualan, jenis_ppn, dpp_faktur, tarif_efektif,
               ppn_keluaran, total_tagihan, akun_piutang, akun_pendapatan, lunas,
               tanggal_bayar, catatan)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (company_id, tanggal, no_invoice.strip(), pelanggan, npwp_nik, keterangan,
             int(nilai_penjualan), jenis_ppn, ppn.dpp_faktur, ppn.tarif,
             ppn.ppn, total, akun_piutang, akun_pendapatan,
             1 if lunas else 0, tgl_bayar, catatan),
        )
        sid = cur.lastrowid

        if buat_jurnal:
            akun_debit = kode_kas if lunas else akun_piutang
            baris = [{
                "kode_akun": akun_debit, "debit": total, "kredit": 0,
                "lawan_transaksi": pelanggan, "npwp_nik": npwp_nik,
                "catatan": f"Penjualan {no_invoice}",
            }, {
                "kode_akun": akun_pendapatan, "debit": 0, "kredit": int(nilai_penjualan),
                "lawan_transaksi": pelanggan, "catatan": keterangan or no_invoice,
            }]
            if ppn.ppn > 0:
                akun_ppn = "2101" if db.q1("SELECT 1 FROM accounts WHERE company_id=? "
                                           "AND kode='2101'", (company_id,)) else "2003"
                baris.append({
                    "kode_akun": akun_ppn, "debit": 0, "kredit": ppn.ppn,
                    "lawan_transaksi": pelanggan, "ref_pajak": "PPN Keluaran",
                    "catatan": "PPN keluaran",
                })
            entry_id = acc.simpan_jurnal(
                company_id, tanggal, f"INV-{no_invoice}", 
                f"Penjualan {no_invoice} - {pelanggan}", baris,
                sumber="penjualan", ref_id=sid, user_id=user_id)
            conn.execute("UPDATE sales SET journal_entry_id=? WHERE id=?", (entry_id, sid))

    db.log_action(user_id, "", company_id, "sale.create", "sales", sid,
                  f"{no_invoice} {tx.rupiah(total)}")
    return sid


def hapus_penjualan(sale_id: int, user_id=None) -> None:
    row = db.q1("SELECT company_id, journal_entry_id FROM sales WHERE id=?", (sale_id,))
    with db.tx() as conn:
        if row and row["journal_entry_id"]:
            conn.execute("DELETE FROM journal_lines WHERE entry_id=?", (row["journal_entry_id"],))
            conn.execute("DELETE FROM journal_entries WHERE id=?", (row["journal_entry_id"],))
        conn.execute("DELETE FROM sales WHERE id=?", (sale_id,))
    if row:
        db.log_action(user_id, "", row["company_id"], "sale.delete", "sales", sale_id)


def tandai_penjualan_lunas(sale_id: int, tanggal_bayar: str, user_id=None) -> None:
    """Tandai invoice lunas dan buat jurnal penerimaan kas."""
    s = db.q1("SELECT * FROM sales WHERE id=?", (sale_id,))
    if s is None:
        raise ValueError("Data penjualan tidak ditemukan.")
    if s["lunas"]:
        raise ValueError("Invoice ini sudah ditandai lunas.")

    akun_kas = db.q1("SELECT kode FROM accounts WHERE company_id=? AND is_kas_bank=1 "
                     "ORDER BY kode LIMIT 1", (s["company_id"],))
    kode_kas = akun_kas["kode"] if akun_kas else "1001"

    baris = [{
        "kode_akun": kode_kas, "debit": s["total_tagihan"], "kredit": 0,
        "lawan_transaksi": s["pelanggan"], "catatan": f"Penerimaan {s['no_invoice']}",
    }, {
        "kode_akun": s["akun_piutang"], "debit": 0, "kredit": s["total_tagihan"],
        "lawan_transaksi": s["pelanggan"], "catatan": f"Pelunasan {s['no_invoice']}",
    }]
    with db.tx() as conn:
        acc.simpan_jurnal(
            s["company_id"], tanggal_bayar, f"BKM-{s['no_invoice']}",
            f"Pelunasan {s['no_invoice']} - {s['pelanggan']}", baris,
            sumber="penjualan", ref_id=sale_id, user_id=user_id)
        conn.execute("UPDATE sales SET lunas=1, tanggal_bayar=? WHERE id=?",
                     (tanggal_bayar, sale_id))


# ==========================================================================
# PEMBELIAN
# ==========================================================================
def list_pembelian(company_id: int, tahun: Optional[int] = None,
                   bulan: Optional[int] = None, cari: str = "") -> list:
    sql = "SELECT * FROM purchases WHERE company_id=?"
    params: list = [company_id]
    if tahun:
        awal, akhir = acc.periode(tahun, bulan)
        sql += " AND tanggal BETWEEN ? AND ?"
        params += [awal, akhir]
    if cari:
        sql += " AND (no_invoice LIKE ? OR vendor LIKE ?)"
        params += [f"%{cari}%", f"%{cari}%"]
    sql += " ORDER BY tanggal DESC, id DESC"
    return db.q(sql, params)


def simpan_pembelian(company_id: int, tanggal: str, no_invoice: str, vendor: str,
                     nilai_sebelum_ppn: int, jenis_ppn: str = "Non-PKP/Tidak Dipungut",
                     jenis: str = "Beban", akun_beban: str = "6008",
                     npwp_nik: str = "", keterangan: str = "",
                     dapat_dikreditkan: bool = True, dibayar: bool = True,
                     tanggal_bayar: Optional[str] = None, catatan: str = "",
                     user_id=None, buat_jurnal: bool = True) -> int:
    """
    Simpan pembelian. Bila PKP dan PPN masukan dapat dikreditkan, PPN dicatat
    sebagai aset (PPN Masukan) - bukan sebagai beban.
    """
    if nilai_sebelum_ppn <= 0:
        raise ValueError("Nilai pembelian harus lebih besar dari nol.")
    if not no_invoice.strip():
        raise ValueError("Nomor invoice wajib diisi.")

    ppn = tx.hitung_ppn(nilai_sebelum_ppn, jenis_ppn)
    ppn_dikreditkan = ppn.ppn if dapat_dikreditkan else 0
    total = nilai_sebelum_ppn + ppn.ppn

    akun_kas = db.q1("SELECT kode FROM accounts WHERE company_id=? AND is_kas_bank=1 "
                     "ORDER BY kode LIMIT 1", (company_id,))
    kode_kas = akun_kas["kode"] if akun_kas else "1001"
    kode_utang = "2001" if db.q1("SELECT 1 FROM accounts WHERE company_id=? AND kode='2001'",
                                 (company_id,)) else "2001"

    with db.tx() as conn:
        cur = conn.execute(
            """INSERT INTO purchases(company_id, tanggal, no_invoice, vendor, npwp_nik,
               keterangan, jenis, nilai_sebelum_ppn, jenis_ppn, dpp_faktur, tarif_efektif,
               ppn_masukan, dapat_dikreditkan, ppn_dikreditkan, total_bayar, akun_beban,
               akun_utang, dibayar, tanggal_bayar, catatan)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (company_id, tanggal, no_invoice.strip(), vendor, npwp_nik, keterangan,
             jenis, int(nilai_sebelum_ppn), jenis_ppn, ppn.dpp_faktur, ppn.tarif,
             ppn.ppn, 1 if dapat_dikreditkan else 0, ppn_dikreditkan, total,
             akun_beban, kode_utang, 1 if dibayar else 0,
             tanggal_bayar or (tanggal if dibayar else None), catatan),
        )
        pid = cur.lastrowid

        if buat_jurnal:
            baris = [{
                "kode_akun": akun_beban, "debit": int(nilai_sebelum_ppn), "kredit": 0,
                "lawan_transaksi": vendor, "npwp_nik": npwp_nik,
                "catatan": keterangan or no_invoice,
            }]
            if ppn.ppn > 0:
                akun_ppn_masukan = "1108" if db.q1(
                    "SELECT 1 FROM accounts WHERE company_id=? AND kode='1108'",
                    (company_id,)) else "1104"
                if dapat_dikreditkan:
                    baris.append({
                        "kode_akun": akun_ppn_masukan, "debit": ppn.ppn, "kredit": 0,
                        "lawan_transaksi": vendor, "ref_pajak": "PPN Masukan",
                        "catatan": "PPN masukan dapat dikreditkan",
                    })
                else:
                    baris[0]["debit"] = int(nilai_sebelum_ppn) + ppn.ppn
                    baris[0]["catatan"] = (keterangan or no_invoice) + \
                        " (PPN tidak dapat dikreditkan - dibebankan)"

            akun_kredit = kode_kas if dibayar else kode_utang
            baris.append({
                "kode_akun": akun_kredit, "debit": 0, "kredit": total,
                "lawan_transaksi": vendor,
                "catatan": f"Pembayaran {no_invoice}" if dibayar else f"Utang {no_invoice}",
            })
            entry_id = acc.simpan_jurnal(
                company_id, tanggal, f"PB-{no_invoice}",
                f"Pembelian {no_invoice} - {vendor}", baris,
                sumber="pembelian", ref_id=pid, user_id=user_id)
            conn.execute("UPDATE purchases SET journal_entry_id=? WHERE id=?",
                         (entry_id, pid))

    db.log_action(user_id, "", company_id, "purchase.create", "purchases", pid,
                  f"{no_invoice} {tx.rupiah(total)}")
    return pid


def hapus_pembelian(purchase_id: int, user_id=None) -> None:
    row = db.q1("SELECT company_id, journal_entry_id FROM purchases WHERE id=?",
                (purchase_id,))
    with db.tx() as conn:
        if row and row["journal_entry_id"]:
            conn.execute("DELETE FROM journal_lines WHERE entry_id=?",
                         (row["journal_entry_id"],))
            conn.execute("DELETE FROM journal_entries WHERE id=?",
                         (row["journal_entry_id"],))
        conn.execute("DELETE FROM purchases WHERE id=?", (purchase_id,))
    if row:
        db.log_action(user_id, "", row["company_id"], "purchase.delete", "purchases",
                      purchase_id)


# ==========================================================================
# ASET TETAP
# ==========================================================================
def list_aset(company_id: int, aktif_saja: bool = True) -> list:
    sql = "SELECT * FROM fixed_assets WHERE company_id=?"
    if aktif_saja:
        sql += " AND tanggal_pelepasan IS NULL"
    sql += " ORDER BY kode_aset"
    return db.q(sql, (company_id,))


def simpan_aset(company_id: int, kode_aset: str, nama_aset: str, tanggal_perolehan: str,
                harga_perolehan: int, kelompok_fiskal: str = "Kelompok 1",
                metode_fiskal: str = "Garis Lurus", umur_komersial: int = 4,
                residu_komersial: int = 0, nbv_fiskal_awal: int = 0,
                akun_aset: str = "1201", akun_akum: str = "1202",
                akun_beban: str = "6007", catatan: str = "",
                akun_kas: str = "", user_id=None, buat_jurnal: bool = True) -> int:
    if harga_perolehan <= 0:
        raise ValueError("Harga perolehan harus lebih besar dari nol.")
    if not nama_aset.strip():
        raise ValueError("Nama aset wajib diisi.")
    if kelompok_fiskal not in config.FISCAL_ASSET_GROUPS:
        raise ValueError(f"Kelompok fiskal '{kelompok_fiskal}' tidak dikenal.")

    if not kode_aset.strip():
        n = int(db.scalar("SELECT COUNT(*) FROM fixed_assets WHERE company_id=?",
                          (company_id,)))
        kode_aset = f"AT-{n + 1:04d}"

    with db.tx() as conn:
        cur = conn.execute(
            """INSERT INTO fixed_assets(company_id, kode_aset, nama_aset, tanggal_perolehan,
               harga_perolehan, residu_komersial, umur_komersial, kelompok_fiskal,
               metode_fiskal, nbv_fiskal_awal, akun_aset, akun_akum, akun_beban, catatan)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (company_id, kode_aset.strip(), nama_aset.strip(), tanggal_perolehan,
             int(harga_perolehan), int(residu_komersial), int(umur_komersial),
             kelompok_fiskal, metode_fiskal, int(nbv_fiskal_awal),
             akun_aset, akun_akum, akun_beban, catatan),
        )
        aid = cur.lastrowid

        if buat_jurnal:
            # Pilih akun kas/bank: pakai yang diminta pengguna, atau akun
            # dengan saldo terbesar agar saldo kas tidak menjadi negatif.
            kode_kas = akun_kas
            if not kode_kas:
                kandidat = db.q(
                    """SELECT a.kode,
                              COALESCE(a.saldo_awal,0) +
                                COALESCE((SELECT SUM(jl.debit - jl.kredit)
                                          FROM journal_lines jl
                                          WHERE jl.company_id=a.company_id
                                            AND jl.kode_akun=a.kode),0) AS saldo
                       FROM accounts a
                       WHERE a.company_id=? AND a.is_kas_bank=1""",
                    (company_id,))
                if kandidat:
                    # utamakan akun yang saldonya cukup menutup perolehan
                    cukup = [r for r in kandidat
                             if int(r["saldo"] or 0) >= int(harga_perolehan)]
                    pilihan = cukup if cukup else kandidat
                    kode_kas = max(pilihan,
                                   key=lambda r: int(r["saldo"] or 0))["kode"]
                else:
                    kode_kas = "1001"
            baris = [{
                "kode_akun": akun_aset, "debit": int(harga_perolehan), "kredit": 0,
                "lawan_transaksi": "Perolehan aset", "catatan": nama_aset,
            }, {
                "kode_akun": kode_kas, "debit": 0, "kredit": int(harga_perolehan),
                "catatan": f"Perolehan {nama_aset}",
            }]
            acc.simpan_jurnal(
                company_id, tanggal_perolehan, f"AT-{kode_aset}",
                f"Perolehan aset tetap - {nama_aset}", baris,
                sumber="aset", ref_id=aid, user_id=user_id)

    db.log_action(user_id, "", company_id, "asset.create", "fixed_assets", aid, nama_aset)
    return aid


def hapus_aset(asset_id: int, user_id=None) -> None:
    db.ex("DELETE FROM depreciation_entries WHERE asset_id=?", (asset_id,))
    db.ex("DELETE FROM fixed_assets WHERE id=?", (asset_id,))


def hitung_penyusutan_tahun(company_id: int, tahun: int, user_id=None,
                            buat_jurnal: bool = True) -> list[dict]:
    """
    Hitung penyusutan seluruh aset untuk satu tahun dan (opsional) buat jurnalnya.
    Perhitungan komersial & fiskal dihitung terpisah sesuai dasar hukum masing-masing.
    """
    aset_list = list_aset(company_id)
    hasil = []

    for a in aset_list:
        tgl_perolehan = a["tanggal_perolehan"]
        tahun_perolehan = int(tgl_perolehan[:4])

        if tahun < tahun_perolehan:
            continue  # belum dimiliki
        if a["tanggal_pelepasan"] and int(a["tanggal_pelepasan"][:4]) < tahun:
            continue  # sudah dilepas

        # Bulan disusutkan pada tahun perolehan (prorata)
        if tahun == tahun_perolehan:
            bulan = 12 - int(tgl_perolehan[5:7]) + 1
        else:
            bulan = 12

        # Nilai buku fiskal awal tahun (untuk tahun setelah perolehan)
        nbv_awal = a["nbv_fiskal_awal"]
        if tahun > tahun_perolehan:
            nbv_awal = int(db.scalar(
                "SELECT nbv_fiskal_akhir FROM depreciation_entries WHERE asset_id=? "
                "AND tahun=?", (a["id"], tahun - 1), default=0))
            if nbv_awal == 0:
                # hitung mundur bila belum pernah dihitung
                nbv_awal = a["harga_perolehan"]

        r = tx.hitung_penyusutan(
            harga_perolehan=a["harga_perolehan"],
            residu=a["residu_komersial"],
            umur_komersial=a["umur_komersial"],
            kelompok_fiskal=a["kelompok_fiskal"],
            metode_fiskal=a["metode_fiskal"],
            bulan=bulan,
            nbv_fiskal_awal=nbv_awal if tahun > tahun_perolehan else 0,
        )

        with db.tx() as conn:
            conn.execute(
                """INSERT INTO depreciation_entries(company_id, asset_id, tahun, bulan,
                   penyusutan_komersial, penyusutan_fiskal, nbv_fiskal_akhir)
                   VALUES(?,?,?,?,?,?,?)
                   ON CONFLICT(asset_id, tahun) DO UPDATE SET
                     bulan=excluded.bulan,
                     penyusutan_komersial=excluded.penyusutan_komersial,
                     penyusutan_fiskal=excluded.penyusutan_fiskal,
                     nbv_fiskal_akhir=excluded.nbv_fiskal_akhir""",
                (company_id, a["id"], tahun, bulan, r.penyusutan_komersial,
                 r.penyusutan_fiskal, r.nbv_fiskal),
            )

        if buat_jurnal and r.penyusutan_komersial > 0:
            no_bukti = f"SUSUT-{a['kode_aset']}-{tahun}"
            ada = db.q1("SELECT id FROM journal_entries WHERE company_id=? AND no_bukti=?",
                        (company_id, no_bukti))
            if ada:
                db.ex("DELETE FROM journal_lines WHERE entry_id=?", (ada["id"],))
                db.ex("DELETE FROM journal_entries WHERE id=?", (ada["id"],))
            baris = [{
                "kode_akun": a["akun_beban"], "debit": r.penyusutan_komersial, "kredit": 0,
                "catatan": f"Penyusutan {a['nama_aset']} tahun {tahun}",
            }, {
                "kode_akun": a["akun_akum"], "debit": 0, "kredit": r.penyusutan_komersial,
                "catatan": f"Akumulasi penyusutan {a['nama_aset']}",
            }]
            acc.simpan_jurnal(company_id, f"{tahun}-12-31", no_bukti,
                              f"Penyusutan {a['nama_aset']} tahun {tahun}", baris,
                              sumber="aset", ref_id=a["id"], user_id=user_id)

        hasil.append({
            "kode_aset": a["kode_aset"], "nama": a["nama_aset"],
            "kelompok": a["kelompok_fiskal"], "bulan": bulan,
            "komersial": r.penyusutan_komersial,
            "fiskal": r.penyusutan_fiskal,
            "selisih": r.selisih,
            "nbv_fiskal": r.nbv_fiskal,
            "keterangan": r.keterangan,
        })

    db.log_action(user_id, "", company_id, "asset.depreciate", "fixed_assets", "",
                  f"tahun {tahun}, {len(hasil)} aset")
    return hasil


def rekap_penyusutan(company_id: int, tahun: int) -> dict:
    rows = db.q(
        """SELECT d.*, a.nama_aset, a.kode_aset, a.kelompok_fiskal
           FROM depreciation_entries d JOIN fixed_assets a ON a.id=d.asset_id
           WHERE d.company_id=? AND d.tahun=? ORDER BY a.kode_aset""",
        (company_id, tahun))
    kom = sum(r["penyusutan_komersial"] for r in rows)
    fis = sum(r["penyusutan_fiskal"] for r in rows)
    return {
        "rincian": [dict(r) for r in rows],
        "total_komersial": kom,
        "total_fiskal": fis,
        "selisih": kom - fis,
    }


# ==========================================================================
# KARYAWAN & PAYROLL
# ==========================================================================
def list_karyawan(company_id: int, aktif_saja: bool = True) -> list:
    sql = "SELECT * FROM employees WHERE company_id=?"
    if aktif_saja:
        sql += " AND is_active=1"
    sql += " ORDER BY nama"
    return db.q(sql, (company_id,))


def simpan_karyawan(company_id: int, nama: str, gaji_pokok: int, jabatan: str = "",
                    status_ptkp: str = "TK/0", tunjangan_tetap: int = 0,
                    nik_npwp: str = "", bpjs_kes: bool = True, bpjs_jht: bool = True,
                    bpjs_jp: bool = True, bpjs_jkk_rate: float = 0.0024,
                    tanggal_masuk: Optional[str] = None, catatan: str = "") -> int:
    if not nama.strip():
        raise ValueError("Nama karyawan wajib diisi.")
    if gaji_pokok < 0:
        raise ValueError("Gaji pokok tidak boleh negatif.")
    if status_ptkp not in config.PTKP_ANNUAL:
        raise ValueError(f"Status PTKP '{status_ptkp}' tidak dikenal.")
    with db.tx() as conn:
        cur = conn.execute(
            """INSERT INTO employees(company_id, nik_npwp, nama, jabatan, status_ptkp,
               gaji_pokok, tunjangan_tetap, bpjs_kes, bpjs_jht, bpjs_jp, bpjs_jkk_rate,
               tanggal_masuk, catatan)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (company_id, nik_npwp, nama.strip(), jabatan, status_ptkp, int(gaji_pokok),
             int(tunjangan_tetap), 1 if bpjs_kes else 0, 1 if bpjs_jht else 0,
             1 if bpjs_jp else 0, float(bpjs_jkk_rate), tanggal_masuk, catatan),
        )
        eid = cur.lastrowid
    db.log_action(None, "", company_id, "employee.create", "employees", eid, nama)
    return eid


def update_karyawan(employee_id: int, **kwargs) -> None:
    fields = ["nama", "jabatan", "status_ptkp", "gaji_pokok", "tunjangan_tetap",
              "nik_npwp", "tanggal_masuk", "tanggal_keluar", "catatan"]
    sets, params = [], []
    for f in fields:
        if f in kwargs:
            sets.append(f"{f}=?")
            params.append(kwargs[f])
    for f in ("bpjs_kes", "bpjs_jht", "bpjs_jp", "is_active"):
        if f in kwargs:
            sets.append(f"{f}=?")
            params.append(1 if kwargs[f] else 0)
    if not sets:
        return
    params.append(employee_id)
    db.ex(f"UPDATE employees SET {', '.join(sets)} WHERE id=?", params)


def hapus_karyawan(employee_id: int) -> None:
    db.ex("UPDATE employees SET is_active=0 WHERE id=?", (employee_id,))


def list_payroll(company_id: int, tahun: Optional[int] = None) -> list:
    sql = """SELECT pr.*, 
                    (SELECT COUNT(*) FROM payroll_items WHERE run_id=pr.id) AS jumlah_karyawan
             FROM payroll_runs pr WHERE pr.company_id=?"""
    params: list = [company_id]
    if tahun:
        sql += " AND substr(pr.masa,1,4)=?"
        params.append(str(tahun))
    sql += " ORDER BY pr.masa DESC"
    return db.q(sql, params)


def hitung_payroll_bulanan(company_id: int, masa: str, bonus: dict[int, int] = None,
                           user_id=None, posting: bool = True) -> dict:
    """
    Hitung payroll satu masa pajak (format masa: YYYY-MM).

    Rumus:
      Bruto = gaji pokok + tunjangan tetap + bonus
      Potongan karyawan = BPJS (kes 1%, JHT 2%, JP 1%) + PPh 21 (TER)
      Take Home Pay = Bruto − potongan karyawan
      Beban perusahaan = Bruto + BPJS pemberi kerja
    """
    bonus = bonus or {}
    karyawan = list_karyawan(company_id)
    if not karyawan:
        raise ValueError("Belum ada karyawan aktif. Daftarkan karyawan terlebih dahulu.")

    bulan = int(masa[5:7])
    tahun = int(masa[:4])
    # Pada Desember, PPh 21 dihitung dengan skema setahun penuh (PMK 168/2023)
    pakai_setahun = (bulan == 12)

    items: list[dict] = []
    total_bruto = total_potongan = total_thp = total_beban = 0
    total_pph21 = 0

    for k in karyawan:
        gaji = k["gaji_pokok"]
        tunjangan = k["tunjangan_tetap"]
        bns = int(bonus.get(k["id"], 0) or 0)
        bruto = gaji + tunjangan + bns

        bpjs = tx.hitung_bpjs(
            upah=gaji + tunjangan,
            jkk_rate=k["bpjs_jkk_rate"],
            ikut_kes=bool(k["bpjs_kes"]),
            ikut_jht=bool(k["bpjs_jht"]),
            ikut_jp=bool(k["bpjs_jp"]),
        )

        if pakai_setahun:
            # Rekap setahun: bruto Jan-Des + perhitungan Pasal 17
            bruto_setahun = int(db.scalar(
                """SELECT COALESCE(SUM(bruto),0) FROM payroll_items pi
                   JOIN payroll_runs pr ON pr.id=pi.run_id
                   WHERE pr.company_id=? AND pi.employee_id=? AND substr(pr.masa,1,4)=?
                     AND substr(pr.masa,6,2) != '12'""",
                (company_id, k["id"], str(tahun))))
            bruto_setahun += bruto
            pph_sudah = int(db.scalar(
                """SELECT COALESCE(SUM(pph21),0) FROM payroll_items pi
                   JOIN payroll_runs pr ON pr.id=pi.run_id
                   WHERE pr.company_id=? AND pi.employee_id=? AND substr(pr.masa,1,4)=?
                     AND substr(pr.masa,6,2) != '12'""",
                (company_id, k["id"], str(tahun))))
            iuran_pensiun = int(db.scalar(
                """SELECT COALESCE(SUM(bpjs_karyawan),0) FROM payroll_items pi
                   JOIN payroll_runs pr ON pr.id=pi.run_id
                   WHERE pr.company_id=? AND pi.employee_id=? AND substr(pr.masa,1,4)=?
                     AND substr(pr.masa,6,2) != '12'""",
                (company_id, k["id"], str(tahun))))
            iuran_pensiun += bpjs.total_karyawan
            hasil = tx.pph21_setahun(bruto_setahun, k["status_ptkp"], iuran_pensiun,
                                     pph_sudah)
            pph21 = max(0, hasil.pph21_desember)
            metode = "Setahun (Pasal 17)"
        else:
            r = tx.pph21_bulanan_ter(bruto, k["status_ptkp"])
            pph21 = r.pph21_ter
            metode = f"TER {r.kategori_ter} ({_persen(r.tarif_ter, 2)})"

        potongan = bpjs.total_karyawan + pph21
        thp = bruto - potongan
        beban = bruto + bpjs.total_perusahaan

        items.append({
            "employee_id": k["id"], "nama": k["nama"], "nik_npwp": k["nik_npwp"],
            "status_ptkp": k["status_ptkp"], "gaji_pokok": gaji, "tunjangan": tunjangan,
            "bonus": bns, "bruto": bruto, "bpjs_karyawan": bpjs.total_karyawan,
            "bpjs_perusahaan": bpjs.total_perusahaan, "pph21": pph21,
            "potongan_lain": 0, "take_home_pay": thp, "beban_perusahaan": beban,
            "metode_pph21": metode,
        })
        total_bruto += bruto
        total_potongan += potongan
        total_thp += thp
        total_beban += beban
        total_pph21 += pph21

    with db.tx() as conn:
        existing = conn.execute(
            "SELECT id FROM payroll_runs WHERE company_id=? AND masa=?",
            (company_id, masa)).fetchone()
        if existing:
            conn.execute("DELETE FROM payroll_items WHERE run_id=?", (existing["id"],))
            conn.execute("""UPDATE payroll_runs SET status='draft', total_bruto=?,
                total_potongan=?, total_thp=?, total_beban=? WHERE id=?""",
                (total_bruto, total_potongan, total_thp, total_beban, existing["id"]))
            run_id = existing["id"]
        else:
            cur = conn.execute(
                """INSERT INTO payroll_runs(company_id, masa, status, total_bruto,
                   total_potongan, total_thp, total_beban) VALUES(?,?,'draft',?,?,?,?)""",
                (company_id, masa, total_bruto, total_potongan, total_thp, total_beban))
            run_id = cur.lastrowid

        for it in items:
            conn.execute(
                """INSERT INTO payroll_items(run_id, employee_id, nama, nik_npwp,
                   status_ptkp, gaji_pokok, tunjangan, bonus, bruto, bpjs_karyawan,
                   bpjs_perusahaan, pph21, potongan_lain, take_home_pay, beban_perusahaan,
                   metode_pph21) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (run_id, it["employee_id"], it["nama"], it["nik_npwp"], it["status_ptkp"],
                 it["gaji_pokok"], it["tunjangan"], it["bonus"], it["bruto"],
                 it["bpjs_karyawan"], it["bpjs_perusahaan"], it["pph21"],
                 it["potongan_lain"], it["take_home_pay"], it["beban_perusahaan"],
                 it["metode_pph21"]),
            )

    if posting:
        posting_payroll(run_id, user_id)

    db.log_action(user_id, "", company_id, "payroll.calculate", "payroll_runs", run_id, masa)
    return {
        "run_id": run_id, "masa": masa, "items": items,
        "total_bruto": total_bruto, "total_potongan": total_potongan,
        "total_thp": total_thp, "total_beban": total_beban, "total_pph21": total_pph21,
    }


def posting_payroll(run_id: int, user_id=None) -> int:
    """
    Buat jurnal payroll:
      Debit  Beban Gaji (bruto)
      Debit  Beban BPJS Perusahaan
      Kredit Utang PPh 21
      Kredit Utang BPJS
      Kredit Kas/Bank (take home pay)
    """
    run = db.q1("SELECT * FROM payroll_runs WHERE id=?", (run_id,))
    if run is None:
        raise ValueError("Data payroll tidak ditemukan.")
    cid = run["company_id"]
    masa = run["masa"]
    tanggal = f"{masa}-28"

    items = db.q(
        """SELECT pi.*, e.status_ptkp FROM payroll_items pi
           LEFT JOIN employees e ON e.id = pi.employee_id WHERE pi.run_id=?""", (run_id,))

    total_bruto = sum(i["bruto"] for i in items)
    total_bpjs_perusahaan = sum(i["bpjs_perusahaan"] for i in items)
    total_pph21 = sum(i["pph21"] for i in items)
    total_bpjs_karyawan = sum(i["bpjs_karyawan"] for i in items)
    total_thp = sum(i["take_home_pay"] for i in items)

    def akun(kode_preferensi: str, kandidat: list[str], default: str) -> str:
        if db.q1("SELECT 1 FROM accounts WHERE company_id=? AND kode=?",
                 (cid, kode_preferensi)):
            return kode_preferensi
        for k in kandidat:
            if db.q1("SELECT 1 FROM accounts WHERE company_id=? AND kode=?", (cid, k)):
                return k
        return default

    akun_beban_gaji = akun("6001", ["6001"], "6001")
    akun_beban_bpjs = akun("6004", ["6004", "6013", "6003"], "6004")
    akun_utang_pph21 = akun("2004", ["2004", "2102"], "2004")
    akun_utang_bpjs = akun("2010", ["2010", "2009", "2102"], "2010")
    akun_kas = db.q1("SELECT kode FROM accounts WHERE company_id=? AND is_kas_bank=1 "
                     "ORDER BY kode LIMIT 1", (cid,))
    kode_kas = akun_kas["kode"] if akun_kas else "1001"

    baris = [
        {"kode_akun": akun_beban_gaji, "debit": total_bruto, "kredit": 0,
         "catatan": f"Beban gaji {masa}"},
        {"kode_akun": akun_beban_bpjs, "debit": total_bpjs_perusahaan, "kredit": 0,
         "catatan": f"BPJS pemberi kerja {masa}"},
        {"kode_akun": akun_utang_pph21, "debit": 0, "kredit": total_pph21,
         "ref_pajak": "PPh 21", "catatan": f"PPh 21 dipotong {masa}"},
        {"kode_akun": akun_utang_bpjs, "debit": 0,
         "kredit": total_bpjs_perusahaan + total_bpjs_karyawan,
         "catatan": f"BPJS terutang {masa}"},
        {"kode_akun": kode_kas, "debit": 0, "kredit": total_thp,
         "catatan": f"Pembayaran gaji {masa}"},
    ]
    baris = [b for b in baris if b["debit"] or b["kredit"]]

    with db.tx() as conn:
        if run["journal_entry_id"]:
            conn.execute("DELETE FROM journal_lines WHERE entry_id=?",
                         (run["journal_entry_id"],))
            conn.execute("DELETE FROM journal_entries WHERE id=?",
                         (run["journal_entry_id"],))
        entry_id = acc.simpan_jurnal(
            cid, tanggal, f"PAY-{masa}", f"Payroll {masa}", baris,
            sumber="payroll", ref_id=run_id, user_id=user_id)
        conn.execute("UPDATE payroll_runs SET status='posted', journal_entry_id=? "
                     "WHERE id=?", (entry_id, run_id))

    # Catat PPh 21 sebagai utang pajak
    if total_pph21 > 0:
        db.ex(
            """INSERT INTO tax_records(company_id, tanggal, masa, kode_pajak, jenis,
               arah, dpp, tarif_dipakai, pajak, status, catatan)
               VALUES(?,?,?,'PPh21','PPh Pasal 21 - payroll','Potong',?,0,?, 'Terutang', ?)""",
            (cid, tanggal, masa, total_bruto, total_pph21,
             f"Payroll {masa}, {len(items)} karyawan"))
    return entry_id


def detail_payroll(run_id: int) -> list:
    return db.q("SELECT * FROM payroll_items WHERE run_id=? ORDER BY nama", (run_id,))


def hapus_payroll(run_id: int, user_id=None) -> None:
    run = db.q1("SELECT journal_entry_id FROM payroll_runs WHERE id=?", (run_id,))
    with db.tx() as conn:
        if run and run["journal_entry_id"]:
            conn.execute("DELETE FROM journal_lines WHERE entry_id=?",
                         (run["journal_entry_id"],))
            conn.execute("DELETE FROM journal_entries WHERE id=?",
                         (run["journal_entry_id"],))
        conn.execute("DELETE FROM payroll_items WHERE run_id=?", (run_id,))
        conn.execute("DELETE FROM payroll_runs WHERE id=?", (run_id,))


# ==========================================================================
# PAJAK POTONG/PUNGUT
# ==========================================================================
KODE_PAJAK_LIST = [
    ("PPh21", "PPh Pasal 21 - penghasilan karyawan", None, False,
     "Tarif efektif rata-rata (TER) per PMK 168/2023. Dihitung otomatis pada menu Payroll."),
    ("PPh22-IMPOR", "PPh 22 - impor (dengan API)", config.RATE_PPH22_IMPORT, True,
     "2,5% dari nilai impor. Bagi importir menjadi kredit pajak (PMK 34/2017)."),
    ("PPh22-UMKM", "PPh 22 - pembelian dari UMKM", config.RATE_PPH22_UMKM, True,
     "0,25% dari pembelian oleh badan tertentu dari pelaku UMKM (PP 55/2022)."),
    ("PPh22-BARANG", "PPh 22 - penjualan barang tertentu", config.RATE_PPH22_GOODS, True,
     "1,5% untuk kertas, semen, baja, otomotif, dll."),
    ("PPh23-JASA", "PPh 23 - jasa & sewa harta", config.RATE_PPH23_SERVICES_RENT, False,
     "2% dari jumlah bruto. Wajib dipotong bila pembayaran ke WP Badan (PMK 141/2015)."),
    ("PPh23-15", "PPh 23 - bunga/royalti/hadiah", config.RATE_PPH23_DIVIDEND_INTEREST_ROYALTY, True,
     "15% dari jumlah bruto. Bagi penerima menjadi kredit pajak."),
    ("PPh4-SEWA", "PPh Final 4(2) - sewa tanah/bangunan", config.RATE_PPH4_SEWA_TANAH_BANGUNAN, False,
     "10% dari nilai bruto persewaan (PP 34/2017). Bersifat final."),
    ("PPh4-KONSTRUKSI", "PPh Final 4(2) - jasa konstruksi", config.RATE_PPH4_KONSTRUKSI_MENENGAH, False,
     "1,75%-2,65% tergantung kualifikasi (PP 9/2022). Bersifat final."),
    ("PPh4-PENGALIHAN", "PPh Final 4(2) - pengalihan tanah/bangunan", config.RATE_PPH4_PENGALIHAN_TANAH, False,
     "2,5% dari nilai pengalihan (PP 34/2016)."),
    ("PPh4-DEPOSITO", "PPh Final 4(2) - bunga deposito", config.RATE_PPH4_BUNGA_DEPOSITO, False,
     "20% dari bunga deposito/tabungan (PP 19/2009)."),
    ("PPh26", "PPh 26 - Wajib Pajak Luar Negeri", config.RATE_PPH26, False,
     "20% dari jumlah bruto, atau tarif P3B bila ada SKD (Pasal 26 UU PPh)."),
    ("PPh-FINAL05", "PPh Final UMKM 0,5%", config.RATE_FINAL_UMKM, False,
     "Hanya bila memenuhi syarat PP 20/2026. Setor tanggal 15 bulan berikutnya."),
]


def list_pajak(company_id: int, tahun: Optional[int] = None) -> list:
    sql = "SELECT * FROM tax_records WHERE company_id=?"
    params: list = [company_id]
    if tahun:
        sql += " AND substr(tanggal,1,4)=?"
        params.append(str(tahun))
    sql += " ORDER BY tanggal DESC, id DESC"
    return db.q(sql, params)


def simpan_pajak(company_id: int, tanggal: str, kode_pajak: str, dpp: int,
                 tarif_override: Optional[float] = None, masa: str = "",
                 tanggal_bayar: Optional[str] = None, no_bupot: str = "",
                 status: str = "Terutang", catatan: str = "",
                 user_id=None, buat_jurnal: bool = True) -> int:
    """Catat pemotongan/pemungutan pajak beserta jurnalnya."""
    info = next((k for k in KODE_PAJAK_LIST if k[0] == kode_pajak), None)
    if info is None:
        raise ValueError(f"Kode pajak '{kode_pajak}' tidak dikenal.")
    _, jenis, tarif_default, kredit, ket = info

    if tarif_override is not None:
        tarif = float(tarif_override)
    elif tarif_default is not None:
        tarif = float(tarif_default)
    else:
        raise ValueError(f"Kode pajak '{kode_pajak}' tidak memiliki tarif default. "
                         "Isi tarif secara manual.")

    if dpp <= 0:
        raise ValueError("DPP (dasar pengenaan pajak) harus lebih besar dari nol.")

    pajak = int(round(dpp * tarif))

    with db.tx() as conn:
        cur = conn.execute(
            """INSERT INTO tax_records(company_id, tanggal, masa, kode_pajak, jenis, arah,
               dpp, tarif_default, tarif_override, tarif_dipakai, pajak, kredit_pph_badan,
               tanggal_bayar, no_bupot, status, catatan)
               VALUES(?,?,?,?,?,'Potong',?,?,?,?,?,?,?,?,?,?)""",
            (company_id, tanggal, masa or tanggal[:7], kode_pajak, jenis, int(dpp),
             float(tarif_default or 0), tarif_override, tarif, pajak,
             1 if kredit else 0, tanggal_bayar, no_bupot, status, catatan),
        )
        tid = cur.lastrowid

        if buat_jurnal and pajak > 0:
            # Jurnal: Debit Beban/Utang Usaha, Kredit Utang Pajak
            akun_beban = "6006"  # jasa profesional
            akun_utang = "2005"
            if kode_pajak.startswith("PPh4"):
                akun_utang = "2006"
            elif kode_pajak == "PPh21":
                akun_utang = "2004"
            elif kode_pajak.startswith("PPh22"):
                akun_utang = "2007"
            for k in (akun_beban, akun_utang):
                if not db.q1("SELECT 1 FROM accounts WHERE company_id=? AND kode=?",
                             (company_id, k)):
                    akun_utang = "2102"
                    akun_beban = "6006"

            baris = [{
                "kode_akun": akun_beban, "debit": pajak, "kredit": 0,
                "ref_pajak": kode_pajak, "catatan": f"Pajak {jenis}",
            }, {
                "kode_akun": akun_utang, "debit": 0, "kredit": pajak,
                "ref_pajak": kode_pajak, "catatan": f"Utang {jenis}",
            }]
            entry_id = acc.simpan_jurnal(
                company_id, tanggal, f"PP-{kode_pajak}-{tid}",
                f"Pemotongan {jenis}", baris, sumber="pajak", ref_id=tid,
                user_id=user_id)
            conn.execute("UPDATE tax_records SET journal_entry_id=? WHERE id=?",
                         (entry_id, tid))

    db.log_action(user_id, "", company_id, "tax.create", "tax_records", tid,
                  f"{kode_pajak} {tx.rupiah(pajak)}")
    return tid


def hapus_pajak(tax_id: int, user_id=None) -> None:
    row = db.q1("SELECT company_id, journal_entry_id FROM tax_records WHERE id=?",
                (tax_id,))
    with db.tx() as conn:
        if row and row["journal_entry_id"]:
            conn.execute("DELETE FROM journal_lines WHERE entry_id=?",
                         (row["journal_entry_id"],))
            conn.execute("DELETE FROM journal_entries WHERE id=?",
                         (row["journal_entry_id"],))
        conn.execute("DELETE FROM tax_records WHERE id=?", (tax_id,))


def list_pembayaran_pajak(company_id: int, tahun: Optional[int] = None) -> list:
    sql = "SELECT * FROM tax_payments WHERE company_id=?"
    params: list = [company_id]
    if tahun:
        sql += " AND substr(tanggal_bayar,1,4)=?"
        params.append(str(tahun))
    sql += " ORDER BY tanggal_bayar DESC, id DESC"
    return db.q(sql, params)


def catat_pembayaran_pajak(company_id: int, jenis_pajak: str, masa: str,
                           tanggal_bayar: str, jumlah: int, ntpn: str = "",
                           cara_bayar: str = "e-Billing", catatan: str = "",
                           user_id=None, buat_jurnal: bool = True) -> int:
    """Catat setoran pajak dan lunasi utang pajak terkait."""
    if jumlah <= 0:
        raise ValueError("Jumlah setoran harus lebih besar dari nol.")

    with db.tx() as conn:
        cur = conn.execute(
            """INSERT INTO tax_payments(company_id, jenis_pajak, masa, tanggal_bayar,
               jumlah, ntpn, cara_bayar, catatan) VALUES(?,?,?,?,?,?,?,?)""",
            (company_id, jenis_pajak, masa, tanggal_bayar, int(jumlah), ntpn,
             cara_bayar, catatan))
        pid = cur.lastrowid

        if buat_jurnal:
            akun_utang_map = {
                "PPN": "2003", "PPh21": "2004", "PPh23": "2005", "PPh4": "2006",
                "PPh25": "2007", "PPhBadan": "2007", "PPhFinal": "2008",
            }
            akun_utang = akun_utang_map.get(jenis_pajak, "2007")
            if not db.q1("SELECT 1 FROM accounts WHERE company_id=? AND kode=?",
                         (company_id, akun_utang)):
                akun_utang = "2102" if db.q1(
                    "SELECT 1 FROM accounts WHERE company_id=? AND kode='2102'",
                    (company_id,)) else "2101"
            akun_kas = db.q1("SELECT kode FROM accounts WHERE company_id=? AND is_kas_bank=1 "
                             "ORDER BY kode LIMIT 1", (company_id,))
            kode_kas = akun_kas["kode"] if akun_kas else "1001"

            # PPh 25 bukan pelunasan utang, melainkan pembayaran di muka
            if jenis_pajak == "PPh25":
                akun_utang = "1109" if db.q1(
                    "SELECT 1 FROM accounts WHERE company_id=? AND kode='1109'",
                    (company_id,)) else "1104"

            baris = [{
                "kode_akun": akun_utang, "debit": int(jumlah), "kredit": 0,
                "ref_pajak": jenis_pajak, "catatan": f"Setoran {jenis_pajak} masa {masa}",
            }, {
                "kode_akun": kode_kas, "debit": 0, "kredit": int(jumlah),
                "catatan": f"Pembayaran {jenis_pajak} {masa}",
            }]
            entry_id = acc.simpan_jurnal(
                company_id, tanggal_bayar, f"ST-{jenis_pajak}-{masa}",
                f"Setoran {jenis_pajak} masa {masa}", baris, sumber="pajak",
                ref_id=pid, user_id=user_id)
            conn.execute("UPDATE tax_payments SET journal_entry_id=? WHERE id=?",
                         (entry_id, pid))

        # tandai tax_records terkait sebagai Disetor
        conn.execute(
            """UPDATE tax_records SET status='Disetor', tanggal_bayar=?
               WHERE company_id=? AND substr(masa,1,7)=? AND status='Terutang'
                 AND kode_pajak LIKE ?""",
            (tanggal_bayar, company_id, masa, f"%{jenis_pajak.replace('PPh', '')}%"
             if jenis_pajak.startswith("PPh") else "%"))

    db.log_action(user_id, "", company_id, "tax.payment", "tax_payments", pid,
                  f"{jenis_pajak} {masa} {tx.rupiah(jumlah)}")
    return pid


# ==========================================================================
# REKONSILIASI FISKAL & PPh BADAN
# ==========================================================================
def list_koreksi_manual(company_id: int, tahun: int) -> list:
    return db.q("SELECT * FROM fiscal_adjustments WHERE company_id=? AND tahun=? "
                "ORDER BY jenis DESC, id", (company_id, tahun))


def simpan_koreksi_manual(company_id: int, tahun: int, uraian: str, nilai: int,
                          jenis: str = "Positif", dokumen: str = "",
                          catatan: str = "") -> int:
    if not uraian.strip():
        raise ValueError("Uraian koreksi wajib diisi.")
    if nilai < 0:
        raise ValueError("Nilai koreksi harus positif; jenis menentukan arah koreksi.")
    cur = db.ex(
        """INSERT INTO fiscal_adjustments(company_id, tahun, uraian, nilai, jenis,
           dokumen, catatan) VALUES(?,?,?,?,?,?,?)""",
        (company_id, tahun, uraian.strip(), int(nilai), jenis, dokumen, catatan))
    return cur.lastrowid


def hapus_koreksi_manual(adj_id: int) -> None:
    db.ex("DELETE FROM fiscal_adjustments WHERE id=?", (adj_id,))


def hitung_rekonsiliasi(company_id: int, tahun: int,
                        kompensasi_rugi: int = 0) -> tx.RekonsiliasiResult:
    """
    Rekonsiliasi fiskal otomatis dari data jurnal + penyusutan + koreksi manual.
    """
    ns = acc.neraca_saldo(company_id, tahun)
    lr = acc.laba_rugi(company_id, tahun, beban_pajak=0)

    # Akun dengan perlakuan Non-Deductible  koreksi positif otomatis
    non_deductible = sum(b.saldo_akhir_normal for b in ns
                         if b.perlakuan_fiskal == "Non-Deductible (+)"
                         and b.tipe == "Beban")
    # Pendapatan final  koreksi negatif
    final_income = sum(b.saldo_akhir_normal for b in ns
                       if b.perlakuan_fiskal == "Final Income (-)"
                       and b.tipe == "Pendapatan")

    # Penyusutan
    susut = rekap_penyusutan(company_id, tahun)

    # Koreksi manual
    adj = list_koreksi_manual(company_id, tahun)
    pos_manual = sum(a["nilai"] for a in adj if a["jenis"] == "Positif")
    neg_manual = sum(a["nilai"] for a in adj if a["jenis"] == "Negatif")

    return tx.hitung_rekonsiliasi_fiskal(
        laba_komersial=lr.laba_sebelum_pajak,
        non_deductible=non_deductible,
        penghasilan_final=final_income,
        penyusutan_komersial=susut["total_komersial"],
        penyusutan_fiskal=susut["total_fiskal"],
        koreksi_positif_manual=pos_manual,
        koreksi_negatif_manual=neg_manual,
        kompensasi_rugi=kompensasi_rugi,
    )


def hitung_pph_badan_tahunan(company_id: int, tahun: int,
                             kompensasi_rugi: int = 0) -> dict:
    """Perhitungan lengkap PPh Badan tahunan beserta kredit pajak."""
    comp = get_company(company_id)
    rekon = hitung_rekonsiliasi(company_id, tahun, kompensasi_rugi)
    omzet = acc.omzet_setahun(company_id, tahun)

    # Kredit pajak: PPh 22/23 yang dipotong pihak lain + PPh 25 disetor
    kredit_23 = int(db.scalar(
        "SELECT COALESCE(SUM(pajak),0) FROM tax_records WHERE company_id=? "
        "AND kredit_pph_badan=1 AND substr(tanggal,1,4)=?",
        (company_id, str(tahun))))
    pph25 = int(db.scalar(
        "SELECT COALESCE(SUM(jumlah),0) FROM tax_payments WHERE company_id=? "
        "AND jenis_pajak='PPh25' AND substr(masa,1,4)=?",
        (company_id, str(tahun))))
    kredit_total = kredit_23 + pph25

    # Skema final?
    pakai_final = bool(comp and comp["skema_pph"] == "final_umkm"
                       and comp["final_eligible"])
    final_res = None
    if pakai_final:
        final_res = tx.hitung_pph_final_umkm(
            omzet_setahun=omzet, bentuk_badan=comp["bentuk"],
            final_eligible_dikonfirmasi=True)
        bayar_final = int(db.scalar(
            "SELECT COALESCE(SUM(jumlah),0) FROM tax_payments WHERE company_id=? "
            "AND jenis_pajak='PPhFinal' AND substr(masa,1,4)=?",
            (company_id, str(tahun))))
        return {
            "skema": "PPh Final UMKM 0,5%",
            "omzet": omzet,
            "rekon": rekon,
            "final": final_res,
            "pph_terutang": final_res.pph_final if final_res.layak else 0,
            "kredit": bayar_final,
            "kurang_lebih": (final_res.pph_final if final_res.layak else 0) - bayar_final,
            "pph25_bulanan": 0,
            "pakai_final": True,
            "catatan": final_res.alasan,
        }

    hasil = tx.hitung_pph_badan(omzet=omzet, pkp=rekon.pkp,
                                kredit_pajak=kredit_total, sudah_dibayar=pph25)
    return {
        "skema": hasil.skema,
        "omzet": omzet,
        "rekon": rekon,
        "hasil": hasil,
        "pph_terutang": hasil.pph_terutang,
        "kredit": kredit_total,
        "kredit_23": kredit_23,
        "kredit_25": pph25,
        "kurang_lebih": hasil.kurang_lebih_bayar,
        "pph25_bulanan": hasil.pph25_bulanan,
        "pakai_final": False,
        "catatan": hasil.keterangan,
        "peringatan": hasil.peringatan,
    }


# ==========================================================================
# CHECKLIST
# ==========================================================================
CHECKLIST_DEFAULT = [
    ("Bulanan", "Pembukuan", "Rekonsiliasi kas/bank dengan catatan jurnal"),
    ("Bulanan", "Pembukuan", "Pastikan semua transaksi bulan ini sudah dicatat"),
    ("Bulanan", "Penjualan", "Cocokkan invoice & faktur pajak dengan pendapatan"),
    ("Bulanan", "Pembelian", "Cocokkan invoice & faktur masukan dengan beban/persediaan"),
    ("Bulanan", "PPh 21", "Hitung payroll, potong, setor, dan laporkan PPh 21"),
    ("Bulanan", "PPh 23/4(2)", "Review transaksi yang wajib dipotong & buat bukti potong"),
    ("Bulanan", "PPh 25", "Setor angsuran PPh 25 bila berlaku"),
    ("Bulanan", "PPN", "Rekonsiliasi PPN keluaran/masukan & lapor SPT Masa PPN (bila PKP)"),
    ("Bulanan", "Aset Tetap", "Perbarui perolehan/pelepasan aset dan penyusutannya"),
    ("Tahunan", "Stock Opname", "Hitung fisik persediaan dan cocokkan dengan buku"),
    ("Tahunan", "Fiskal", "Review akun 'Review Fiskal', koreksi positif/negatif, rugi fiskal"),
    ("Tahunan", "PPh Badan", "Review Pasal 31E / kelayakan Final 0,5% / kredit pajak"),
    ("Tahunan", "SPT Tahunan", "Siapkan laporan keuangan, rekonsiliasi, bukti bayar & potong"),
    ("Tahunan", "Dokumen", "Arsipkan dokumen pembukuan (wajib simpan 10 tahun)"),
]


def list_checklist(company_id: int, masa: str = "") -> list:
    sql = "SELECT * FROM checklist_items WHERE company_id=?"
    params: list = [company_id]
    if masa:
        sql += " AND (masa=? OR masa='')"
        params.append(masa)
    sql += " ORDER BY urutan, id"
    return db.q(sql, params)


def update_checklist(item_id: int, status: str = None, pic: str = None,
                     catatan: str = None, masa: str = None) -> None:
    sets, params = [], []
    if status is not None:
        sets.append("status=?")
        params.append(status)
    if pic is not None:
        sets.append("pic=?")
        params.append(pic)
    if catatan is not None:
        sets.append("catatan=?")
        params.append(catatan)
    if masa is not None:
        sets.append("masa=?")
        params.append(masa)
    if not sets:
        return
    params.append(item_id)
    db.ex(f"UPDATE checklist_items SET {', '.join(sets)} WHERE id=?", params)


def tambah_checklist(company_id: int, frekuensi: str, area: str, checklist: str) -> int:
    n = int(db.scalar("SELECT COALESCE(MAX(urutan),0) FROM checklist_items "
                      "WHERE company_id=?", (company_id,)))
    cur = db.ex("INSERT INTO checklist_items(company_id, frekuensi, area, checklist, "
                "urutan) VALUES(?,?,?,?,?)", (company_id, frekuensi, area, checklist, n + 1))
    return cur.lastrowid


def hapus_checklist(item_id: int) -> None:
    db.ex("DELETE FROM checklist_items WHERE id=?", (item_id,))


# ==========================================================================
# LAPORAN & EKSPOR
# ==========================================================================
def laporan_laba_rugi(company_id: int, tahun: int, bulan=None):
    return acc.laba_rugi(company_id, tahun, bulan)


def laporan_neraca(company_id: int, tahun: int, bulan=None):
    return acc.neraca(company_id, tahun, bulan)


def laporan_arus_kas(company_id: int, tahun: int, bulan=None):
    return acc.arus_kas(company_id, tahun, bulan)


def laporan_perubahan_ekuitas(company_id: int, tahun: int):
    return acc.perubahan_ekuitas(company_id, tahun)


def laporan_neraca_saldo(company_id: int, tahun: int, bulan=None):
    return acc.neraca_saldo(company_id, tahun, bulan)


def analisis(company_id: int, tahun: int, bulan=None):
    return an.analisis_kesehatan(company_id, tahun, bulan)


def deadline_pajak(company_id: int) -> list:
    comp = get_company(company_id)
    return an.cek_deadline(company_id, bool(comp and comp["status_pkp"]))


def proyeksi(company_id: int, tahun: int) -> dict:
    return an.proyeksi_sederhana(company_id, tahun)


def simulasi(company_id: int, tahun: int, delta_pendapatan: float,
             delta_beban: float) -> dict:
    return an.simulasi_skenario(company_id, tahun, delta_pendapatan, delta_beban)


def kpi_dashboard(company_id: int, tahun: int, bulan=None) -> dict:
    return acc.dashboard_kpi(company_id, tahun, bulan)
