"""
Modul penjualan, pembelian, biaya, bank, dimensi, tata kelola, dan otomasi.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from . import config, db
from .core import accounting as acc
from .core import tax_engine as tx
from .modules import (hari_ini, tambah_hari, nomor_berikut, catat_riwayat,
                      ke_recycle_bin, ringkas_angka, stok_masuk, stok_keluar,
                      get_produk)


# ==========================================================================
# PENJUALAN
# ==========================================================================
def _hitung_baris(items: list[dict], diskon_persen: float = 0,
                  jenis_ppn: str = "Non-PKP/Tidak Dipungut") -> dict:
    subtotal = 0
    for it in items:
        qty = float(it.get("qty", 1) or 1)
        harga = ringkas_angka(it.get("harga_satuan"))
        dp = float(it.get("diskon_persen", 0) or 0)
        dn = ringkas_angka(it.get("diskon_nilai"))
        baris = int(round(qty * harga))
        potongan = int(round(baris * dp / 100)) + dn
        it["subtotal"] = max(0, baris - potongan)
        it["diskon_nilai"] = potongan
        subtotal += it["subtotal"]

    diskon_total = int(round(subtotal * float(diskon_persen or 0) / 100))
    dpp = max(0, subtotal - diskon_total)
    ppn_res = tx.hitung_ppn(dpp, jenis_ppn)
    return {
        "subtotal": subtotal,
        "diskon_persen": float(diskon_persen or 0),
        "diskon_nilai": diskon_total,
        "dpp": dpp,
        "ppn": ppn_res.ppn,
        "dpp_faktur": ppn_res.dpp_faktur,
        "total": dpp + ppn_res.ppn,
        "keterangan_ppn": ppn_res.keterangan,
    }


def buat_sales_order(company_id: int, tanggal: str, items: list[dict],
                     partner_id: Optional[int] = None, pelanggan: str = "",
                     diskon_persen: float = 0, jenis_ppn: str = "Non-PKP/Tidak Dipungut",
                     alamat_kirim: str = "", tanggal_kirim: str = "",
                     catatan: str = "", user_id=None, username: str = "") -> int:
    if not items:
        raise ValueError("Sales order harus memiliki minimal satu baris barang.")

    mitra = None
    if partner_id:
        mitra = db.q1("SELECT * FROM partners WHERE id=?", (partner_id,))
    nama_pelanggan = pelanggan or (mitra["nama"] if mitra else "Pelanggan Umum")

    h = _hitung_baris(items, diskon_persen, jenis_ppn)
    nomor = nomor_berikut(company_id, "SO", int(tanggal[:4]))

    with db.tx() as conn:
        cur = conn.execute(
            """INSERT INTO sales_orders(company_id, nomor, tanggal, partner_id,
               pelanggan, alamat_kirim, tanggal_kirim, status, subtotal, diskon,
               dpp, ppn, total, catatan)
               VALUES(?,?,?,?,?,?,?,'draft',?,?,?,?,?,?)""",
            (company_id, nomor, tanggal, partner_id, nama_pelanggan, alamat_kirim,
             tanggal_kirim or None, h["subtotal"], h["diskon_nilai"], h["dpp"],
             h["ppn"], h["total"], catatan))
        so_id = cur.lastrowid
        for it in items:
            conn.execute(
                """INSERT INTO sales_order_items(so_id, product_id, deskripsi, qty,
                   satuan, harga_satuan, diskon_persen, diskon_nilai, subtotal)
                   VALUES(?,?,?,?,?,?,?,?,?)""",
                (so_id, it.get("product_id"), it.get("deskripsi", ""),
                 float(it.get("qty", 1) or 1), it.get("satuan", "pcs"),
                 ringkas_angka(it.get("harga_satuan")),
                 float(it.get("diskon_persen", 0) or 0),
                 ringkas_angka(it.get("diskon_nilai")), it["subtotal"]))
    catat_riwayat(company_id, "sales_orders", so_id, "create", user_id, username,
                  "", "", nomor)
    return so_id


def ubah_status_so(so_id: int, status: str) -> None:
    if status not in ("draft", "dikonfirmasi", "sebagian", "selesai", "batal"):
        raise ValueError("Status sales order tidak valid.")
    db.ex("UPDATE sales_orders SET status=? WHERE id=?", (status, so_id))


def daftar_sales_order(company_id: int, tahun: Optional[int] = None,
                       status: str = "", cari: str = "") -> list:
    sql = "SELECT * FROM sales_orders WHERE company_id=? AND deleted_at IS NULL"
    params: list = [company_id]
    if tahun:
        sql += " AND substr(tanggal,1,4)=?"
        params.append(str(tahun))
    if status:
        sql += " AND status=?"
        params.append(status)
    if cari:
        sql += " AND (nomor LIKE ? OR pelanggan LIKE ?)"
        params += [f"%{cari}%"] * 2
    sql += " ORDER BY tanggal DESC, id DESC"
    return db.q(sql, params)


def detail_so(so_id: int) -> list:
    return db.q("""SELECT soi.*, p.kode AS produk_kode, p.nama AS produk_nama
                   FROM sales_order_items soi
                   LEFT JOIN products p ON p.id = soi.product_id
                   WHERE soi.so_id=? ORDER BY soi.id""", (so_id,))


def hapus_sales_order(so_id: int, oleh: str = "") -> None:
    row = db.q1("SELECT * FROM sales_orders WHERE id=?", (so_id,))
    if row is None:
        return
    ke_recycle_bin(row["company_id"], "sales_orders", so_id, row["nomor"],
                   dict(row), oleh)
    db.ex("UPDATE sales_orders SET deleted_at=datetime('now','localtime'), "
          "status='batal' WHERE id=?", (so_id,))


def buat_invoice(company_id: int, tanggal: str, items: list[dict],
                 partner_id: Optional[int] = None, pelanggan: str = "",
                 jatuh_tempo: str = "", diskon_persen: float = 0,
                 jenis_ppn: str = "Non-PKP/Tidak Dipungut", so_id: Optional[int] = None,
                 catatan: str = "", user_id=None, username: str = "",
                 kurangi_stok: bool = True) -> int:
    if not items:
        raise ValueError("Invoice harus memiliki minimal satu baris.")

    mitra = db.q1("SELECT * FROM partners WHERE id=?", (partner_id,)) if partner_id else None
    nama = pelanggan or (mitra["nama"] if mitra else "Pelanggan Umum")
    npwp = mitra["npwp"] if mitra else ""
    alamat = mitra["alamat"] if mitra else ""

    if not jatuh_tempo:
        termin = mitra["termin_hari"] if mitra else 30
        jatuh_tempo = tambah_hari(tanggal, int(termin or 30))

    h = _hitung_baris(items, diskon_persen, jenis_ppn)
    nomor = nomor_berikut(company_id, "INV", int(tanggal[:4]))

    with db.tx() as conn:
        cur = conn.execute(
            """INSERT INTO invoices(company_id, nomor, so_id, tanggal, jatuh_tempo,
               partner_id, pelanggan, npwp_nik, alamat, subtotal, diskon_persen,
               diskon_nilai, dpp, jenis_ppn, ppn, total, dibayar, sisa, status, catatan)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,0,?,'terkirim',?)""",
            (company_id, nomor, so_id, tanggal, jatuh_tempo, partner_id, nama,
             npwp, alamat, h["subtotal"], h["diskon_persen"], h["diskon_nilai"],
             h["dpp"], jenis_ppn, h["ppn"], h["total"], h["total"], catatan))
        inv_id = cur.lastrowid

        total_hpp = 0
        for it in items:
            hpp_baris = 0
            qty = float(it.get("qty", 1) or 1)
            pid = it.get("product_id")
            produk = get_produk(pid) if pid else None

            if produk and produk["tipe"] == "barang" and kurangi_stok:
                r = stok_keluar(company_id, pid, qty, tanggal, None, "penjualan",
                                inv_id, nomor, f"Penjualan {nomor}")
                hpp_baris = r["hpp"]

            conn.execute(
                """INSERT INTO invoice_items(invoice_id, product_id, deskripsi, qty,
                   satuan, harga_satuan, diskon_persen, diskon_nilai, subtotal, hpp)
                   VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (inv_id, pid, it.get("deskripsi") or (produk["nama"] if produk else ""),
                 qty, it.get("satuan") or (produk["satuan"] if produk else "pcs"),
                 ringkas_angka(it.get("harga_satuan")),
                 float(it.get("diskon_persen", 0) or 0),
                 ringkas_angka(it.get("diskon_nilai")), it["subtotal"], hpp_baris))
            total_hpp += hpp_baris

        akun_piutang = "1101" if db.q1("SELECT 1 FROM accounts WHERE company_id=? AND kode='1101'",
                                       (company_id,)) else "1101"
        akun_pendapatan = "4001"
        if items and items[0].get("product_id"):
            p = get_produk(items[0]["product_id"])
            if p and p["akun_pendapatan"]:
                akun_pendapatan = p["akun_pendapatan"]

        baris_jurnal = [{
            "kode_akun": akun_piutang, "debit": h["total"], "kredit": 0,
            "lawan_transaksi": nama, "npwp_nik": npwp,
            "catatan": f"Invoice {nomor}",
        }, {
            "kode_akun": akun_pendapatan, "debit": 0, "kredit": h["dpp"],
            "lawan_transaksi": nama, "catatan": f"Pendapatan {nomor}",
        }]
        if h["ppn"] > 0:
            akun_ppn = "2101" if db.q1("SELECT 1 FROM accounts WHERE company_id=? AND kode='2101'",
                                       (company_id,)) else "2003"
            baris_jurnal.append({
                "kode_akun": akun_ppn, "debit": 0, "kredit": h["ppn"],
                "lawan_transaksi": nama, "ref_pajak": "PPN Keluaran",
                "catatan": "PPN keluaran",
            })
        if total_hpp > 0:
            akun_hpp = "5001"
            akun_persediaan = "1104"
            if items and items[0].get("product_id"):
                p = get_produk(items[0]["product_id"])
                if p:
                    akun_hpp = p["akun_hpp"] or akun_hpp
                    akun_persediaan = p["akun_persediaan"] or akun_persediaan
            baris_jurnal.append({
                "kode_akun": akun_hpp, "debit": total_hpp, "kredit": 0,
                "catatan": f"HPP {nomor}",
            })
            baris_jurnal.append({
                "kode_akun": akun_persediaan, "debit": 0, "kredit": total_hpp,
                "catatan": f"Pengurangan persediaan {nomor}",
            })

        entry_id = acc.simpan_jurnal(company_id, tanggal, f"INV-{nomor}",
                                     f"Penjualan {nomor} - {nama}", baris_jurnal,
                                     sumber="penjualan", ref_id=inv_id, user_id=user_id)
        conn.execute("UPDATE invoices SET journal_entry_id=? WHERE id=?",
                     (entry_id, inv_id))

        if so_id:
            conn.execute("UPDATE sales_orders SET status='selesai' WHERE id=?", (so_id,))

    catat_riwayat(company_id, "invoices", inv_id, "create", user_id, username,
                  "", "", nomor)
    return inv_id


def daftar_invoice(company_id: int, tahun: Optional[int] = None, status: str = "",
                   partner_id: Optional[int] = None, cari: str = "",
                   jatuh_tempo_sampai: str = "") -> list:
    sql = "SELECT * FROM invoices WHERE company_id=? AND deleted_at IS NULL"
    params: list = [company_id]
    if tahun:
        sql += " AND substr(tanggal,1,4)=?"
        params.append(str(tahun))
    if status:
        if status == "belum_lunas":
            sql += " AND status NOT IN ('lunas','batal')"
        else:
            sql += " AND status=?"
            params.append(status)
    if partner_id:
        sql += " AND partner_id=?"
        params.append(partner_id)
    if cari:
        sql += " AND (nomor LIKE ? OR pelanggan LIKE ?)"
        params += [f"%{cari}%"] * 2
    if jatuh_tempo_sampai:
        sql += " AND jatuh_tempo <= ?"
        params.append(jatuh_tempo_sampai)
    sql += " ORDER BY tanggal DESC, id DESC"
    return db.q(sql, params)


def get_invoice(invoice_id: int):
    return db.q1("SELECT * FROM invoices WHERE id=?", (invoice_id,))


def detail_invoice(invoice_id: int) -> list:
    return db.q("""SELECT ii.*, p.kode AS produk_kode, p.nama AS produk_nama
                   FROM invoice_items ii
                   LEFT JOIN products p ON p.id = ii.product_id
                   WHERE ii.invoice_id=? ORDER BY ii.id""", (invoice_id,))


def _perbarui_status_invoice(conn, invoice_id: int) -> None:
    row = conn.execute("SELECT total, dibayar, status FROM invoices WHERE id=?",
                       (invoice_id,)).fetchone()
    if row is None or row["status"] == "batal":
        return
    sisa = int(row["total"]) - int(row["dibayar"])
    if sisa <= 0:
        status = "lunas"
        sisa = 0
    elif row["dibayar"] > 0:
        status = "sebagian"
    else:
        status = "terkirim"
    conn.execute("UPDATE invoices SET sisa=?, status=? WHERE id=?",
                 (sisa, status, invoice_id))


def hapus_invoice(invoice_id: int, oleh: str = "", user_id=None) -> None:
    """Void invoice: batalkan jurnal, kembalikan stok, tandai terhapus."""
    inv = get_invoice(invoice_id)
    if inv is None:
        return
    if inv["dibayar"] > 0:
        raise ValueError(
            "Invoice sudah memiliki pembayaran. Batalkan pembayarannya terlebih "
            "dahulu sebelum menghapus invoice.")

    with db.tx() as conn:
        if inv["journal_entry_id"]:
            conn.execute("DELETE FROM journal_lines WHERE entry_id=?",
                         (inv["journal_entry_id"],))
            conn.execute("DELETE FROM journal_entries WHERE id=?",
                         (inv["journal_entry_id"],))

        for it in conn.execute("SELECT * FROM invoice_items WHERE invoice_id=?",
                               (invoice_id,)).fetchall():
            if it["product_id"]:
                p = get_produk(it["product_id"])
                if p and p["tipe"] == "barang":
                    harga = int(it["hpp"] / it["qty"]) if it["qty"] else int(p["harga_beli"] or 0)
                    stok_masuk(inv["company_id"], it["product_id"], float(it["qty"]),
                               harga, inv["tanggal"], None, "void_penjualan",
                               invoice_id, inv["nomor"], f"Void {inv['nomor']}")

        conn.execute("UPDATE invoices SET status='batal', "
                     "deleted_at=datetime('now','localtime') WHERE id=?", (invoice_id,))

    ke_recycle_bin(inv["company_id"], "invoices", invoice_id, inv["nomor"],
                   dict(inv), oleh)
    catat_riwayat(inv["company_id"], "invoices", invoice_id, "void", user_id, oleh)


def terima_pembayaran(company_id: int, tanggal: str, jumlah: int,
                      alokasi: list[dict], partner_id: Optional[int] = None,
                      pelanggan: str = "", akun_kas: str = "", metode: str = "Transfer",
                      referensi: str = "", catatan: str = "", user_id=None,
                      username: str = "") -> int:
    """
    Catat penerimaan pembayaran dan alokasikan ke satu atau beberapa invoice.
    Mendukung pembayaran sebagian: alokasi boleh lebih kecil dari nilai invoice.
    """
    jumlah = ringkas_angka(jumlah)
    if jumlah <= 0:
        raise ValueError("Jumlah pembayaran harus lebih besar dari nol.")

    total_alokasi = sum(ringkas_angka(a.get("jumlah")) for a in alokasi)
    if total_alokasi > jumlah:
        raise ValueError(
            f"Total alokasi ({tx.rupiah(total_alokasi)}) melebihi jumlah "
            f"pembayaran ({tx.rupiah(jumlah)}).")
    if not alokasi:
        raise ValueError("Pilih minimal satu invoice untuk dialokasikan.")

    mitra = db.q1("SELECT * FROM partners WHERE id=?", (partner_id,)) if partner_id else None
    nama = pelanggan or (mitra["nama"] if mitra else "Pelanggan Umum")

    if not akun_kas:
        row = db.q1("SELECT kode FROM accounts WHERE company_id=? AND is_kas_bank=1 "
                    "ORDER BY kode LIMIT 1", (company_id,))
        akun_kas = row["kode"] if row else "1001"

    nomor = nomor_berikut(company_id, "RCV", int(tanggal[:4]))

    with db.tx() as conn:
        cur = conn.execute(
            """INSERT INTO receipts(company_id, nomor, tanggal, partner_id, pelanggan,
               akun_kas, jumlah, metode, referensi, catatan, status)
               VALUES(?,?,?,?,?,?,?,?,?,?,'aktif')""",
            (company_id, nomor, tanggal, partner_id, nama, akun_kas, jumlah,
             metode, referensi, catatan))
        rcv_id = cur.lastrowid

        for a in alokasi:
            inv_id = a.get("invoice_id")
            nilai = ringkas_angka(a.get("jumlah"))
            if nilai <= 0 or not inv_id:
                continue
            inv = conn.execute("SELECT * FROM invoices WHERE id=?", (inv_id,)).fetchone()
            if inv is None:
                continue
            if nilai > int(inv["sisa"]) + 1:
                raise ValueError(
                    f"Alokasi {tx.rupiah(nilai)} melebihi sisa tagihan "
                    f"{inv['nomor']} sebesar {tx.rupiah(inv['sisa'])}. "
                    "Periksa kembali jumlah pembayaran.")
            conn.execute("""INSERT INTO receipt_allocations(receipt_id, invoice_id, jumlah)
                            VALUES(?,?,?)""", (rcv_id, inv_id, nilai))
            conn.execute("UPDATE invoices SET dibayar=dibayar+? WHERE id=?",
                         (nilai, inv_id))
            _perbarui_status_invoice(conn, inv_id)

        akun_piutang = "1101"
        baris = [{
            "kode_akun": akun_kas, "debit": jumlah, "kredit": 0,
            "lawan_transaksi": nama, "catatan": f"Penerimaan {nomor}",
        }, {
            "kode_akun": akun_piutang, "debit": 0, "kredit": jumlah,
            "lawan_transaksi": nama, "catatan": f"Pelunasan piutang {nomor}",
        }]
        entry_id = acc.simpan_jurnal(company_id, tanggal, f"RCV-{nomor}",
                                     f"Penerimaan pembayaran {nomor} - {nama}",
                                     baris, sumber="penjualan", ref_id=rcv_id,
                                     user_id=user_id)
        conn.execute("UPDATE receipts SET journal_entry_id=? WHERE id=?",
                     (entry_id, rcv_id))

    catat_riwayat(company_id, "receipts", rcv_id, "create", user_id, username,
                  "", "", nomor)
    return rcv_id


def daftar_penerimaan(company_id: int, tahun: Optional[int] = None,
                      partner_id: Optional[int] = None) -> list:
    sql = "SELECT * FROM receipts WHERE company_id=? AND deleted_at IS NULL"
    params: list = [company_id]
    if tahun:
        sql += " AND substr(tanggal,1,4)=?"
        params.append(str(tahun))
    if partner_id:
        sql += " AND partner_id=?"
        params.append(partner_id)
    sql += " ORDER BY tanggal DESC, id DESC"
    return db.q(sql, params)


def alokasi_penerimaan(receipt_id: int) -> list:
    return db.q("""SELECT ra.*, i.nomor AS invoice_nomor, i.total, i.jatuh_tempo
                   FROM receipt_allocations ra
                   JOIN invoices i ON i.id = ra.invoice_id
                   WHERE ra.receipt_id=?""", (receipt_id,))


def void_penerimaan(receipt_id: int, oleh: str = "", user_id=None) -> None:
    rcv = db.q1("SELECT * FROM receipts WHERE id=?", (receipt_id,))
    if rcv is None:
        return
    if rcv["status"] == "void":
        raise ValueError("Penerimaan ini sudah dibatalkan.")

    with db.tx() as conn:
        for a in conn.execute("SELECT * FROM receipt_allocations WHERE receipt_id=?",
                              (receipt_id,)).fetchall():
            conn.execute("UPDATE invoices SET dibayar=dibayar-? WHERE id=?",
                         (a["jumlah"], a["invoice_id"]))
            _perbarui_status_invoice(conn, a["invoice_id"])
        conn.execute("DELETE FROM receipt_allocations WHERE receipt_id=?", (receipt_id,))
        if rcv["journal_entry_id"]:
            conn.execute("DELETE FROM journal_lines WHERE entry_id=?",
                         (rcv["journal_entry_id"],))
            conn.execute("DELETE FROM journal_entries WHERE id=?",
                         (rcv["journal_entry_id"],))
        conn.execute("UPDATE receipts SET status='void', journal_entry_id=NULL "
                     "WHERE id=?", (receipt_id,))

    catat_riwayat(rcv["company_id"], "receipts", receipt_id, "void", user_id, oleh)


def buat_nota_kredit(company_id: int, tanggal: str, jumlah: int,
                     invoice_id: Optional[int] = None, partner_id: Optional[int] = None,
                     tipe: str = "retur", alasan: str = "", user_id=None,
                     username: str = "") -> int:
    """
    Nota kredit: retur penjualan, diskon setelah invoice, atau refund.
    Mengurangi piutang pelanggan dan pendapatan.
    """
    jumlah = ringkas_angka(jumlah)
    if jumlah <= 0:
        raise ValueError("Jumlah nota kredit harus lebih besar dari nol.")
    if tipe not in ("retur", "diskon", "refund"):
        raise ValueError("Tipe nota kredit harus retur, diskon, atau refund.")

    inv = db.q1("SELECT * FROM invoices WHERE id=?", (invoice_id,)) if invoice_id else None
    nama = inv["pelanggan"] if inv else "Pelanggan"
    if inv and not partner_id:
        partner_id = inv["partner_id"]

    nomor = nomor_berikut(company_id, "CN", int(tanggal[:4]))

    with db.tx() as conn:
        cur = conn.execute(
            """INSERT INTO credit_notes(company_id, nomor, tanggal, invoice_id,
               partner_id, pelanggan, tipe, jumlah, alasan, status)
               VALUES(?,?,?,?,?,?,?,?,?,'aktif')""",
            (company_id, nomor, tanggal, invoice_id, partner_id, nama, tipe,
             jumlah, alasan))
        cn_id = cur.lastrowid

        if invoice_id:
            conn.execute("UPDATE invoices SET total=total-?, sisa=sisa-? WHERE id=?",
                         (jumlah, jumlah, invoice_id))
            _perbarui_status_invoice(conn, invoice_id)

        akun_piutang = "1101"
        akun_lawan = "4003" if db.q1("SELECT 1 FROM accounts WHERE company_id=? AND kode='4003'",
                                     (company_id,)) else "4001"
        if tipe == "refund":
            akun_kas = db.q1("SELECT kode FROM accounts WHERE company_id=? AND is_kas_bank=1 "
                             "ORDER BY kode LIMIT 1", (company_id,))
            akun_lawan = akun_kas["kode"] if akun_kas else "1001"

        baris = [{
            "kode_akun": akun_lawan, "debit": jumlah, "kredit": 0,
            "lawan_transaksi": nama, "catatan": f"Nota kredit {nomor}",
        }, {
            "kode_akun": akun_piutang, "debit": 0, "kredit": jumlah,
            "lawan_transaksi": nama, "catatan": f"Pengurangan piutang {nomor}",
        }]
        entry_id = acc.simpan_jurnal(company_id, tanggal, f"CN-{nomor}",
                                     f"Nota kredit {nomor} - {nama}", baris,
                                     sumber="penjualan", ref_id=cn_id, user_id=user_id)
        conn.execute("UPDATE credit_notes SET journal_entry_id=? WHERE id=?",
                     (entry_id, cn_id))

    catat_riwayat(company_id, "credit_notes", cn_id, "create", user_id, username,
                  "", "", nomor)
    return cn_id


def daftar_nota_kredit(company_id: int, tahun: Optional[int] = None) -> list:
    sql = "SELECT * FROM credit_notes WHERE company_id=? AND deleted_at IS NULL"
    params: list = [company_id]
    if tahun:
        sql += " AND substr(tanggal,1,4)=?"
        params.append(str(tahun))
    sql += " ORDER BY tanggal DESC"
    return db.q(sql, params)


# ==========================================================================
# PIUTANG & AGING
# ==========================================================================
def aging_piutang(company_id: int, sampai: str = "") -> dict:
    """
    Analisis umur piutang per pelanggan.
    Kelompok: belum jatuh tempo, 1-30, 31-60, 61-90, di atas 90 hari.
    """
    sampai = sampai or hari_ini()
    rows = db.q("""SELECT i.*, COALESCE(i.pelanggan,'Tanpa Nama') AS nama_pelanggan
                   FROM invoices i
                   WHERE i.company_id=? AND i.deleted_at IS NULL
                     AND i.status NOT IN ('lunas','batal') AND i.sisa > 0
                   ORDER BY i.jatuh_tempo""", (company_id,))

    kelompok = {"Belum Jatuh Tempo": 0, "1-30 hari": 0, "31-60 hari": 0,
                "61-90 hari": 0, "Di atas 90 hari": 0}
    per_pelanggan: dict[str, dict] = {}
    total = 0
    rincian = []

    for r in rows:
        jt = r["jatuh_tempo"] or r["tanggal"]
        try:
            d_jt = datetime.fromisoformat(jt[:10]).date()
            d_acuan = datetime.fromisoformat(sampai[:10]).date()
            umur = (d_acuan - d_jt).days
        except ValueError:
            umur = 0

        if umur <= 0:
            kat = "Belum Jatuh Tempo"
        elif umur <= 30:
            kat = "1-30 hari"
        elif umur <= 60:
            kat = "31-60 hari"
        elif umur <= 90:
            kat = "61-90 hari"
        else:
            kat = "Di atas 90 hari"

        sisa = int(r["sisa"])
        kelompok[kat] += sisa
        total += sisa

        nama = r["nama_pelanggan"]
        if nama not in per_pelanggan:
            per_pelanggan[nama] = {
                "pelanggan": nama, "partner_id": r["partner_id"],
                "Belum Jatuh Tempo": 0, "1-30 hari": 0, "31-60 hari": 0,
                "61-90 hari": 0, "Di atas 90 hari": 0, "total": 0,
                "jumlah_invoice": 0, "terlama": 0,
            }
        per_pelanggan[nama][kat] += sisa
        per_pelanggan[nama]["total"] += sisa
        per_pelanggan[nama]["jumlah_invoice"] += 1
        per_pelanggan[nama]["terlama"] = max(per_pelanggan[nama]["terlama"], umur)

        rincian.append({
            "invoice_id": r["id"], "nomor": r["nomor"], "pelanggan": nama,
            "tanggal": r["tanggal"], "jatuh_tempo": jt, "total": r["total"],
            "dibayar": r["dibayar"], "sisa": sisa, "umur_hari": umur,
            "kelompok": kat,
        })

    daftar_pelanggan = sorted(per_pelanggan.values(),
                              key=lambda x: x["total"], reverse=True)
    return {
        "kelompok": kelompok,
        "total": total,
        "per_pelanggan": daftar_pelanggan,
        "rincian": rincian,
        "bermasalah": [r for r in rincian if r["umur_hari"] > 90],
        "sampai": sampai,
    }


def piutang_per_pelanggan(company_id: int) -> list:
    return db.q("""SELECT COALESCE(p.nama, i.pelanggan) AS pelanggan,
                          i.partner_id,
                          COUNT(*) AS jumlah_invoice,
                          SUM(i.total) AS total_invoice,
                          SUM(i.dibayar) AS total_dibayar,
                          SUM(i.sisa) AS sisa
                   FROM invoices i
                   LEFT JOIN partners p ON p.id = i.partner_id
                   WHERE i.company_id=? AND i.deleted_at IS NULL
                     AND i.status NOT IN ('lunas','batal')
                   GROUP BY COALESCE(p.nama, i.pelanggan)
                   HAVING sisa > 0
                   ORDER BY sisa DESC""", (company_id,))


def aging_utang(company_id: int, sampai: str = "") -> dict:
    sampai = sampai or hari_ini()
    rows = db.q("""SELECT b.*, COALESCE(b.vendor,'Tanpa Nama') AS nama_vendor
                   FROM bills b
                   WHERE b.company_id=? AND b.deleted_at IS NULL
                     AND b.status NOT IN ('lunas','batal') AND b.sisa > 0
                   ORDER BY b.jatuh_tempo""", (company_id,))

    kelompok = {"Belum Jatuh Tempo": 0, "1-30 hari": 0, "31-60 hari": 0,
                "61-90 hari": 0, "Di atas 90 hari": 0}
    per_vendor: dict[str, dict] = {}
    total = 0
    rincian = []

    for r in rows:
        jt = r["jatuh_tempo"] or r["tanggal"]
        try:
            umur = (datetime.fromisoformat(sampai[:10]).date()
                    - datetime.fromisoformat(jt[:10]).date()).days
        except ValueError:
            umur = 0

        if umur <= 0:
            kat = "Belum Jatuh Tempo"
        elif umur <= 30:
            kat = "1-30 hari"
        elif umur <= 60:
            kat = "31-60 hari"
        elif umur <= 90:
            kat = "61-90 hari"
        else:
            kat = "Di atas 90 hari"

        sisa = int(r["sisa"])
        kelompok[kat] += sisa
        total += sisa

        nama = r["nama_vendor"]
        if nama not in per_vendor:
            per_vendor[nama] = {
                "vendor": nama, "partner_id": r["partner_id"],
                "Belum Jatuh Tempo": 0, "1-30 hari": 0, "31-60 hari": 0,
                "61-90 hari": 0, "Di atas 90 hari": 0, "total": 0,
                "jumlah_bill": 0, "terlama": 0,
            }
        per_vendor[nama][kat] += sisa
        per_vendor[nama]["total"] += sisa
        per_vendor[nama]["jumlah_bill"] += 1
        per_vendor[nama]["terlama"] = max(per_vendor[nama]["terlama"], umur)

        rincian.append({
            "bill_id": r["id"], "nomor": r["nomor"], "vendor": nama,
            "tanggal": r["tanggal"], "jatuh_tempo": jt, "total": r["total"],
            "dibayar": r["dibayar"], "sisa": sisa, "umur_hari": umur,
            "kelompok": kat,
        })

    return {
        "kelompok": kelompok,
        "total": total,
        "per_vendor": sorted(per_vendor.values(), key=lambda x: x["total"], reverse=True),
        "rincian": rincian,
        "bermasalah": [r for r in rincian if r["umur_hari"] > 90],
        "sampai": sampai,
    }


def piutang_jatuh_tempo(company_id: int, hari_ke_depan: int = 7) -> list:
    batas = tambah_hari(hari_ini(), hari_ke_depan)
    return db.q("""SELECT * FROM invoices
                   WHERE company_id=? AND deleted_at IS NULL
                     AND status NOT IN ('lunas','batal') AND sisa > 0
                     AND jatuh_tempo IS NOT NULL AND jatuh_tempo <= ?
                   ORDER BY jatuh_tempo""", (company_id, batas))


def utang_jatuh_tempo(company_id: int, hari_ke_depan: int = 7) -> list:
    batas = tambah_hari(hari_ini(), hari_ke_depan)
    return db.q("""SELECT * FROM bills
                   WHERE company_id=? AND deleted_at IS NULL
                     AND status NOT IN ('lunas','batal') AND sisa > 0
                     AND jatuh_tempo IS NOT NULL AND jatuh_tempo <= ?
                   ORDER BY jatuh_tempo""", (company_id, batas))


# ==========================================================================
# PEMBELIAN
# ==========================================================================
def buat_purchase_order(company_id: int, tanggal: str, items: list[dict],
                        partner_id: Optional[int] = None, vendor: str = "",
                        diskon: int = 0, catatan: str = "", user_id=None,
                        username: str = "") -> int:
    if not items:
        raise ValueError("Purchase order harus memiliki minimal satu baris.")

    mitra = db.q1("SELECT * FROM partners WHERE id=?", (partner_id,)) if partner_id else None
    nama = vendor or (mitra["nama"] if mitra else "Pemasok")

    subtotal = 0
    for it in items:
        qty = float(it.get("qty", 1) or 1)
        harga = ringkas_angka(it.get("harga_satuan"))
        dp = float(it.get("diskon_persen", 0) or 0)
        bruto = int(round(qty * harga))
        it["subtotal"] = max(0, bruto - int(round(bruto * dp / 100)))
        subtotal += it["subtotal"]

    diskon_nilai = min(ringkas_angka(diskon), subtotal)
    dpp = subtotal - diskon_nilai
    ppn = int(round(dpp * config.RATE_VAT_EFFECTIVE_NORMAL))
    total = dpp + ppn
    nomor = nomor_berikut(company_id, "PO", int(tanggal[:4]))

    with db.tx() as conn:
        cur = conn.execute(
            """INSERT INTO purchase_orders(company_id, nomor, tanggal, partner_id,
               vendor, status, subtotal, diskon, dpp, ppn, total, catatan)
               VALUES(?,?,?,?,?,'draft',?,?,?,?,?,?)""",
            (company_id, nomor, tanggal, partner_id, nama, subtotal, diskon_nilai,
             dpp, ppn, total, catatan))
        po_id = cur.lastrowid
        for it in items:
            conn.execute(
                """INSERT INTO purchase_order_items(po_id, product_id, deskripsi, qty,
                   satuan, harga_satuan, diskon_persen, subtotal)
                   VALUES(?,?,?,?,?,?,?,?)""",
                (po_id, it.get("product_id"), it.get("deskripsi", ""),
                 float(it.get("qty", 1) or 1), it.get("satuan", "pcs"),
                 ringkas_angka(it.get("harga_satuan")),
                 float(it.get("diskon_persen", 0) or 0), it["subtotal"]))
    catat_riwayat(company_id, "purchase_orders", po_id, "create", user_id, username,
                  "", "", nomor)
    return po_id


def daftar_purchase_order(company_id: int, tahun: Optional[int] = None,
                          status: str = "") -> list:
    sql = "SELECT * FROM purchase_orders WHERE company_id=? AND deleted_at IS NULL"
    params: list = [company_id]
    if tahun:
        sql += " AND substr(tanggal,1,4)=?"
        params.append(str(tahun))
    if status:
        sql += " AND status=?"
        params.append(status)
    sql += " ORDER BY tanggal DESC, id DESC"
    return db.q(sql, params)


def detail_po(po_id: int) -> list:
    return db.q("""SELECT poi.*, p.kode AS produk_kode, p.nama AS produk_nama
                   FROM purchase_order_items poi
                   LEFT JOIN products p ON p.id = poi.product_id
                   WHERE poi.po_id=? ORDER BY poi.id""", (po_id,))


def ubah_status_po(po_id: int, status: str) -> None:
    if status not in ("draft", "dikonfirmasi", "sebagian", "selesai", "batal"):
        raise ValueError("Status purchase order tidak valid.")
    db.ex("UPDATE purchase_orders SET status=? WHERE id=?", (status, po_id))


def buat_bill(company_id: int, tanggal: str, items: list[dict],
              partner_id: Optional[int] = None, vendor: str = "",
              nomor_vendor: str = "", jatuh_tempo: str = "", jenis: str = "Persediaan",
              diskon: int = 0, jenis_ppn: str = "Non-PKP/Tidak Dipungut",
              dapat_dikreditkan: bool = True, po_id: Optional[int] = None,
              akun_beban: str = "6008", catatan: str = "", user_id=None,
              username: str = "", tambah_stok: bool = True) -> int:
    if not items:
        raise ValueError("Bill harus memiliki minimal satu baris.")

    mitra = db.q1("SELECT * FROM partners WHERE id=?", (partner_id,)) if partner_id else None
    nama = vendor or (mitra["nama"] if mitra else "Pemasok")
    npwp = mitra["npwp"] if mitra else ""
    if not jatuh_tempo:
        termin = mitra["termin_hari"] if mitra else 30
        jatuh_tempo = tambah_hari(tanggal, int(termin or 30))

    subtotal = 0
    for it in items:
        qty = float(it.get("qty", 1) or 1)
        harga = ringkas_angka(it.get("harga_satuan"))
        dp = float(it.get("diskon_persen", 0) or 0)
        bruto = int(round(qty * harga))
        it["subtotal"] = max(0, bruto - int(round(bruto * dp / 100)))
        subtotal += it["subtotal"]

    diskon_nilai = min(ringkas_angka(diskon), subtotal)
    dpp = subtotal - diskon_nilai
    ppn_res = tx.hitung_ppn(dpp, jenis_ppn)
    total = dpp + ppn_res.ppn
    nomor = nomor_berikut(company_id, "BILL", int(tanggal[:4]))

    with db.tx() as conn:
        cur = conn.execute(
            """INSERT INTO bills(company_id, nomor, nomor_vendor, po_id, tanggal,
               jatuh_tempo, partner_id, vendor, npwp_nik, jenis, subtotal, diskon,
               dpp, jenis_ppn, ppn, dapat_dikreditkan, total, dibayar, sisa,
               status, akun_beban, catatan)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,0,?,'terbuka',?,?)""",
            (company_id, nomor, nomor_vendor, po_id, tanggal, jatuh_tempo,
             partner_id, nama, npwp, jenis, subtotal, diskon_nilai, dpp,
             jenis_ppn, ppn_res.ppn, 1 if dapat_dikreditkan else 0, total,
             total, akun_beban, catatan))
        bill_id = cur.lastrowid

        for it in items:
            conn.execute(
                """INSERT INTO bill_items(bill_id, product_id, deskripsi, qty,
                   satuan, harga_satuan, diskon_persen, subtotal)
                   VALUES(?,?,?,?,?,?,?,?)""",
                (bill_id, it.get("product_id"), it.get("deskripsi", ""),
                 float(it.get("qty", 1) or 1), it.get("satuan", "pcs"),
                 ringkas_angka(it.get("harga_satuan")),
                 float(it.get("diskon_persen", 0) or 0), it["subtotal"]))

            pid = it.get("product_id")
            produk = get_produk(pid) if pid else None
            if produk and produk["tipe"] == "barang" and tambah_stok:
                stok_masuk(company_id, pid, float(it.get("qty", 1) or 1),
                           ringkas_angka(it.get("harga_satuan")), tanggal, None,
                           "pembelian", bill_id, nomor,
                           f"Pembelian {nomor} dari {nama}")

        akun_utang = "2001"
        akun_debit = akun_beban
        if jenis == "Persediaan":
            akun_debit = "1104"
            if items and items[0].get("product_id"):
                p = get_produk(items[0]["product_id"])
                if p and p["akun_persediaan"]:
                    akun_debit = p["akun_persediaan"]
        elif jenis == "Aset Tetap":
            akun_debit = "1201"

        baris = [{
            "kode_akun": akun_debit, "debit": dpp, "kredit": 0,
            "lawan_transaksi": nama, "npwp_nik": npwp,
            "catatan": f"Pembelian {nomor}",
        }]
        if ppn_res.ppn > 0:
            if dapat_dikreditkan:
                akun_ppn = "1108" if db.q1(
                    "SELECT 1 FROM accounts WHERE company_id=? AND kode='1108'",
                    (company_id,)) else "1104"
                baris.append({
                    "kode_akun": akun_ppn, "debit": ppn_res.ppn, "kredit": 0,
                    "lawan_transaksi": nama, "ref_pajak": "PPN Masukan",
                    "catatan": "PPN masukan dapat dikreditkan",
                })
            else:
                baris[0]["debit"] = dpp + ppn_res.ppn
                baris[0]["catatan"] += " (PPN dibebankan)"
        baris.append({
            "kode_akun": akun_utang, "debit": 0, "kredit": total,
            "lawan_transaksi": nama, "catatan": f"Utang {nomor}",
        })

        entry_id = acc.simpan_jurnal(company_id, tanggal, f"BILL-{nomor}",
                                     f"Pembelian {nomor} - {nama}", baris,
                                     sumber="pembelian", ref_id=bill_id,
                                     user_id=user_id)
        conn.execute("UPDATE bills SET journal_entry_id=? WHERE id=?",
                     (entry_id, bill_id))

        if po_id:
            conn.execute("UPDATE purchase_orders SET status='selesai' WHERE id=?",
                         (po_id,))

    catat_riwayat(company_id, "bills", bill_id, "create", user_id, username,
                  "", "", nomor)
    return bill_id


def daftar_bill(company_id: int, tahun: Optional[int] = None, status: str = "",
                partner_id: Optional[int] = None, cari: str = "") -> list:
    sql = "SELECT * FROM bills WHERE company_id=? AND deleted_at IS NULL"
    params: list = [company_id]
    if tahun:
        sql += " AND substr(tanggal,1,4)=?"
        params.append(str(tahun))
    if status:
        if status == "belum_lunas":
            sql += " AND status NOT IN ('lunas','batal')"
        else:
            sql += " AND status=?"
            params.append(status)
    if partner_id:
        sql += " AND partner_id=?"
        params.append(partner_id)
    if cari:
        sql += " AND (nomor LIKE ? OR vendor LIKE ? OR nomor_vendor LIKE ?)"
        params += [f"%{cari}%"] * 3
    sql += " ORDER BY tanggal DESC, id DESC"
    return db.q(sql, params)


def get_bill(bill_id: int):
    return db.q1("SELECT * FROM bills WHERE id=?", (bill_id,))


def detail_bill(bill_id: int) -> list:
    return db.q("""SELECT bi.*, p.kode AS produk_kode, p.nama AS produk_nama
                   FROM bill_items bi
                   LEFT JOIN products p ON p.id = bi.product_id
                   WHERE bi.bill_id=? ORDER BY bi.id""", (bill_id,))


def _perbarui_status_bill(conn, bill_id: int) -> None:
    row = conn.execute("SELECT total, dibayar, status FROM bills WHERE id=?",
                       (bill_id,)).fetchone()
    if row is None or row["status"] == "batal":
        return
    sisa = int(row["total"]) - int(row["dibayar"])
    if sisa <= 0:
        status, sisa = "lunas", 0
    elif row["dibayar"] > 0:
        status = "sebagian"
    else:
        status = "terbuka"
    conn.execute("UPDATE bills SET sisa=?, status=? WHERE id=?", (sisa, status, bill_id))


def bayar_vendor(company_id: int, tanggal: str, jumlah: int, alokasi: list[dict],
                 partner_id: Optional[int] = None, vendor: str = "",
                 akun_kas: str = "", metode: str = "Transfer", referensi: str = "",
                 catatan: str = "", user_id=None, username: str = "") -> int:
    jumlah = ringkas_angka(jumlah)
    if jumlah <= 0:
        raise ValueError("Jumlah pembayaran harus lebih besar dari nol.")
    if not alokasi:
        raise ValueError("Pilih minimal satu bill untuk dialokasikan.")

    total_alokasi = sum(ringkas_angka(a.get("jumlah")) for a in alokasi)
    if total_alokasi > jumlah:
        raise ValueError("Total alokasi melebihi jumlah pembayaran.")

    mitra = db.q1("SELECT * FROM partners WHERE id=?", (partner_id,)) if partner_id else None
    nama = vendor or (mitra["nama"] if mitra else "Pemasok")

    if not akun_kas:
        row = db.q1("SELECT kode FROM accounts WHERE company_id=? AND is_kas_bank=1 "
                    "ORDER BY kode LIMIT 1", (company_id,))
        akun_kas = row["kode"] if row else "1001"

    nomor = nomor_berikut(company_id, "PAY", int(tanggal[:4]))

    with db.tx() as conn:
        cur = conn.execute(
            """INSERT INTO vendor_payments(company_id, nomor, tanggal, partner_id,
               vendor, akun_kas, jumlah, metode, referensi, catatan, status)
               VALUES(?,?,?,?,?,?,?,?,?,?,'aktif')""",
            (company_id, nomor, tanggal, partner_id, nama, akun_kas, jumlah,
             metode, referensi, catatan))
        pay_id = cur.lastrowid

        for a in alokasi:
            bill_id = a.get("bill_id")
            nilai = ringkas_angka(a.get("jumlah"))
            if not bill_id or nilai <= 0:
                continue
            bill = conn.execute("SELECT * FROM bills WHERE id=?", (bill_id,)).fetchone()
            if bill is None:
                continue
            if nilai > int(bill["sisa"]) + 1:
                raise ValueError(
                    f"Alokasi {tx.rupiah(nilai)} melebihi sisa utang "
                    f"{bill['nomor']} sebesar {tx.rupiah(bill['sisa'])}.")
            conn.execute("""INSERT INTO vendor_payment_allocations(payment_id, bill_id,
                            jumlah) VALUES(?,?,?)""", (pay_id, bill_id, nilai))
            conn.execute("UPDATE bills SET dibayar=dibayar+? WHERE id=?",
                         (nilai, bill_id))
            _perbarui_status_bill(conn, bill_id)

        akun_utang = "2001"
        baris = [{
            "kode_akun": akun_utang, "debit": jumlah, "kredit": 0,
            "lawan_transaksi": nama, "catatan": f"Pelunasan utang {nomor}",
        }, {
            "kode_akun": akun_kas, "debit": 0, "kredit": jumlah,
            "lawan_transaksi": nama, "catatan": f"Pembayaran {nomor}",
        }]
        entry_id = acc.simpan_jurnal(company_id, tanggal, f"PAY-{nomor}",
                                     f"Pembayaran ke {nama} ({nomor})", baris,
                                     sumber="pembelian", ref_id=pay_id,
                                     user_id=user_id)
        conn.execute("UPDATE vendor_payments SET journal_entry_id=? WHERE id=?",
                     (entry_id, pay_id))

    catat_riwayat(company_id, "vendor_payments", pay_id, "create", user_id,
                  username, "", "", nomor)
    return pay_id


def daftar_pembayaran_vendor(company_id: int, tahun: Optional[int] = None,
                             partner_id: Optional[int] = None) -> list:
    sql = "SELECT * FROM vendor_payments WHERE company_id=? AND deleted_at IS NULL"
    params: list = [company_id]
    if tahun:
        sql += " AND substr(tanggal,1,4)=?"
        params.append(str(tahun))
    if partner_id:
        sql += " AND partner_id=?"
        params.append(partner_id)
    sql += " ORDER BY tanggal DESC, id DESC"
    return db.q(sql, params)


def void_pembayaran_vendor(payment_id: int, oleh: str = "", user_id=None) -> None:
    pay = db.q1("SELECT * FROM vendor_payments WHERE id=?", (payment_id,))
    if pay is None:
        return
    if pay["status"] == "void":
        raise ValueError("Pembayaran ini sudah dibatalkan.")

    with db.tx() as conn:
        for a in conn.execute("SELECT * FROM vendor_payment_allocations WHERE payment_id=?",
                              (payment_id,)).fetchall():
            conn.execute("UPDATE bills SET dibayar=dibayar-? WHERE id=?",
                         (a["jumlah"], a["bill_id"]))
            _perbarui_status_bill(conn, a["bill_id"])
        conn.execute("DELETE FROM vendor_payment_allocations WHERE payment_id=?",
                     (payment_id,))
        if pay["journal_entry_id"]:
            conn.execute("DELETE FROM journal_lines WHERE entry_id=?",
                         (pay["journal_entry_id"],))
            conn.execute("DELETE FROM journal_entries WHERE id=?",
                         (pay["journal_entry_id"],))
        conn.execute("UPDATE vendor_payments SET status='void', journal_entry_id=NULL "
                     "WHERE id=?", (payment_id,))

    catat_riwayat(pay["company_id"], "vendor_payments", payment_id, "void",
                  user_id, oleh)


def retur_pembelian(company_id: int, tanggal: str, bill_id: int, items: list[dict],
                    alasan: str = "", user_id=None, username: str = "") -> int:
    """Retur pembelian: kurangi utang, keluarkan stok, catat jurnal balik."""
    bill = get_bill(bill_id)
    if bill is None:
        raise ValueError("Bill tidak ditemukan.")

    total = 0
    for it in items:
        total += int(round(float(it.get("qty", 0) or 0) * ringkas_angka(it.get("harga_satuan"))))
    if total <= 0:
        raise ValueError("Nilai retur harus lebih besar dari nol.")

    with db.tx() as conn:
        for it in items:
            pid = it.get("product_id")
            qty = float(it.get("qty", 0) or 0)
            if pid and qty > 0:
                produk = get_produk(pid)
                if produk and produk["tipe"] == "barang":
                    stok_keluar(company_id, pid, qty, tanggal, None, "retur_pembelian",
                                bill_id, bill["nomor"], f"Retur ke {bill['vendor']}",
                                izinkan_negatif=True)

        conn.execute("UPDATE bills SET total=total-?, sisa=sisa-? WHERE id=?",
                     (total, total, bill_id))
        _perbarui_status_bill(conn, bill_id)

        akun_utang = "2001"
        akun_lawan = "1104"
        if items and items[0].get("product_id"):
            p = get_produk(items[0]["product_id"])
            if p and p["akun_persediaan"]:
                akun_lawan = p["akun_persediaan"]

        baris = [{
            "kode_akun": akun_utang, "debit": total, "kredit": 0,
            "lawan_transaksi": bill["vendor"], "catatan": f"Retur pembelian {bill['nomor']}",
        }, {
            "kode_akun": akun_lawan, "debit": 0, "kredit": total,
            "lawan_transaksi": bill["vendor"], "catatan": alasan or "Retur pembelian",
        }]
        entry_id = acc.simpan_jurnal(company_id, tanggal,
                                     f"RET-{bill['nomor']}",
                                     f"Retur pembelian {bill['nomor']}", baris,
                                     sumber="pembelian", ref_id=bill_id,
                                     user_id=user_id)

    catat_riwayat(company_id, "bills", bill_id, "retur", user_id, username, "",
                  "", f"Retur {tx.rupiah(total)}")
    return entry_id
