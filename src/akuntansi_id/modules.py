"""
AkunTuntas - Modul Lanjutan: Mitra, Produk, Stok, Penjualan, Pembelian,
              Biaya, Bank, Dimensi, Tata Kelola, Otomasi
=============================================================
Seluruh operasi bersifat atomik dan otomatis menghasilkan jurnal.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from typing import Any, Optional

from . import db, schema_ext


# ==========================================================================
# UTILITAS UMUM
# ==========================================================================
def hari_ini() -> str:
    return date.today().isoformat()


def tambah_hari(iso: str, hari: int) -> str:
    try:
        d = datetime.fromisoformat(str(iso)[:10]).date()
    except ValueError:
        d = date.today()
    return (d + timedelta(days=hari)).isoformat()


def catat_riwayat(company_id: Optional[int], tabel: str, record_id: int,
                  aksi: str, user_id=None, username: str = "",
                  field: str = "", lama: Any = "", baru: Any = "") -> None:
    try:
        db.ex(
            """INSERT INTO change_history(company_id, user_id, username, tabel,
               record_id, aksi, field, nilai_lama, nilai_baru)
               VALUES(?,?,?,?,?,?,?,?,?)""",
            (company_id, user_id, username, tabel, record_id, aksi, field,
             str(lama)[:500], str(baru)[:500]))
    except Exception:
        pass


def ke_recycle_bin(company_id: int, tabel: str, record_id: int, judul: str,
                   data: dict, oleh: str = "") -> None:
    try:
        db.ex(
            """INSERT INTO recycle_bin(company_id, tabel, record_id, judul,
               data_json, dihapus_oleh) VALUES(?,?,?,?,?,?)""",
            (company_id, tabel, record_id, judul,
             json.dumps(data, ensure_ascii=False, default=str), oleh))
    except Exception:
        pass


def ringkas_angka(nilai) -> int:
    try:
        return int(round(float(nilai)))
    except (TypeError, ValueError):
        return 0


# ==========================================================================
# PENOMORAN OTOMATIS
# ==========================================================================
POLA_NOMOR_DEFAULT = {
    "SO":   ("SO",   "{prefix}/{tahun}/{urut:04d}"),
    "INV":  ("INV",  "{prefix}/{tahun}/{urut:04d}"),
    "RCV":  ("RCV",  "{prefix}/{tahun}/{urut:04d}"),
    "CN":   ("CN",   "{prefix}/{tahun}/{urut:04d}"),
    "PO":   ("PO",   "{prefix}/{tahun}/{urut:04d}"),
    "BILL": ("BILL", "{prefix}/{tahun}/{urut:04d}"),
    "PAY":  ("PAY",  "{prefix}/{tahun}/{urut:04d}"),
    "EXP":  ("EXP",  "{prefix}/{tahun}/{urut:04d}"),
    "JU":   ("JU",   "{prefix}/{tahun}/{urut:04d}"),
    "AT":   ("AT",   "{prefix}-{urut:04d}"),
    "KRY":  ("KRY",  "{prefix}-{urut:03d}"),
    "CUST": ("C",    "{prefix}{urut:04d}"),
    "VEND": ("V",    "{prefix}{urut:04d}"),
    "PRD":  ("P",    "{prefix}{urut:04d}"),
    "GDG":  ("GDG",  "{prefix}{urut:03d}"),
    "BANK": ("BNK",  "{prefix}{urut:03d}"),
    "KAS":  ("KAS",  "{prefix}{urut:03d}"),
    "CC":   ("CC",   "{prefix}{urut:03d}"),
    "PRJ":  ("PRJ",  "{prefix}{urut:03d}"),
    "CAB":  ("CAB",  "{prefix}{urut:03d}"),
}

_TABEL_NOMOR = {
    "SO": ("sales_orders", "nomor"), "INV": ("invoices", "nomor"),
    "RCV": ("receipts", "nomor"), "CN": ("credit_notes", "nomor"),
    "PO": ("purchase_orders", "nomor"), "BILL": ("bills", "nomor"),
    "PAY": ("vendor_payments", "nomor"), "EXP": ("expenses", "nomor"),
}


def _nomor_dipakai(company_id: int, kode: str, nomor: str) -> bool:
    if kode not in _TABEL_NOMOR:
        return False
    tabel, kolom = _TABEL_NOMOR[kode]
    return bool(db.q1(f"SELECT 1 FROM {tabel} WHERE company_id=? AND {kolom}=?",
                      (company_id, nomor)))


def nomor_berikut(company_id: int, kode: str, tahun: Optional[int] = None) -> str:
    """Hasilkan nomor dokumen berurutan (direset setiap tahun bila dikonfigurasi)."""
    tahun = tahun or date.today().year
    prefix_default, pola_default = POLA_NOMOR_DEFAULT.get(
        kode, (kode, "{prefix}/{tahun}/{urut:04d}"))

    row = db.q1("SELECT * FROM number_sequences WHERE company_id=? AND kode=?",
                (company_id, kode))
    if row is None:
        db.ex("""INSERT INTO number_sequences(company_id, kode, prefix, pola,
                 urut_akhir, reset_tiap_tahun, tahun_aktif) VALUES(?,?,?,?,0,1,?)""",
              (company_id, kode, prefix_default, pola_default, tahun))
        row = db.q1("SELECT * FROM number_sequences WHERE company_id=? AND kode=?",
                    (company_id, kode))

    urut = int(row["urut_akhir"])
    if row["reset_tiap_tahun"] and int(row["tahun_aktif"]) != tahun:
        urut = 0
        db.ex("UPDATE number_sequences SET tahun_aktif=? WHERE id=?", (tahun, row["id"]))

    pola = row["pola"] or pola_default
    prefix = row["prefix"] or prefix_default

    for _ in range(500):
        urut += 1
        hasil = pola.format(prefix=prefix, tahun=tahun, urut=urut)
        if not _nomor_dipakai(company_id, kode, hasil):
            db.ex("UPDATE number_sequences SET urut_akhir=? WHERE id=?", (urut, row["id"]))
            return hasil

    raise RuntimeError(f"Tidak dapat menghasilkan nomor unik untuk kode {kode}.")


def set_pola_nomor(company_id: int, kode: str, prefix: str, pola: str,
                   reset_tahunan: bool = True) -> None:
    row = db.q1("SELECT id FROM number_sequences WHERE company_id=? AND kode=?",
                (company_id, kode))
    if row:
        db.ex("UPDATE number_sequences SET prefix=?, pola=?, reset_tiap_tahun=? WHERE id=?",
              (prefix, pola, 1 if reset_tahunan else 0, row["id"]))
    else:
        db.ex("""INSERT INTO number_sequences(company_id, kode, prefix, pola,
                 urut_akhir, reset_tiap_tahun, tahun_aktif) VALUES(?,?,?,?,0,?,?)""",
              (company_id, kode, prefix, pola, 1 if reset_tahunan else 0,
               date.today().year))


def pratinjau_nomor(company_id: int, kode: str) -> str:
    """Tampilkan nomor berikutnya TANPA memakai urutannya."""
    row = db.q1("SELECT * FROM number_sequences WHERE company_id=? AND kode=?",
                (company_id, kode))
    tahun = date.today().year
    if row is None:
        prefix, pola = POLA_NOMOR_DEFAULT.get(kode, (kode, "{prefix}/{tahun}/{urut:04d}"))
        urut = 1
    else:
        prefix, pola = row["prefix"], row["pola"]
        urut = int(row["urut_akhir"])
        if row["reset_tiap_tahun"] and int(row["tahun_aktif"]) != tahun:
            urut = 0
        urut += 1
    return pola.format(prefix=prefix, tahun=tahun, urut=urut)


def daftar_pola_nomor(company_id: int) -> list:
    hasil = []
    for kode, (prefix, pola) in POLA_NOMOR_DEFAULT.items():
        row = db.q1("SELECT * FROM number_sequences WHERE company_id=? AND kode=?",
                    (company_id, kode))
        hasil.append({
            "kode": kode,
            "prefix": row["prefix"] if row else prefix,
            "pola": row["pola"] if row else pola,
            "urut_akhir": row["urut_akhir"] if row else 0,
            "berikutnya": pratinjau_nomor(company_id, kode),
        })
    return hasil


# ==========================================================================
# IZIN & PERAN (RBAC)
# ==========================================================================
def inisialisasi_izin() -> None:
    for kode, modul, nama, deskripsi in schema_ext.PERMISSIONS:
        db.ex("""INSERT INTO permissions(kode, modul, nama, deskripsi)
                 VALUES(?,?,?,?)
                 ON CONFLICT(kode) DO UPDATE SET modul=excluded.modul,
                   nama=excluded.nama, deskripsi=excluded.deskripsi""",
              (kode, modul, nama, deskripsi))
    for role, izin in schema_ext.ROLE_DEFAULT_PERMISSIONS.items():
        for k in izin:
            if k == "*":
                continue
            db.ex("""INSERT INTO role_permissions(role, permission_kode)
                     VALUES(?,?) ON CONFLICT(role, permission_kode) DO NOTHING""",
                  (role, k))


def izin_peran(role: str) -> set:
    if role == "owner":
        return {p[0] for p in schema_ext.PERMISSIONS}
    return {r["permission_kode"] for r in db.q(
        "SELECT permission_kode FROM role_permissions WHERE role=?", (role,))}


def izin_pengguna(user_id: int, role: str) -> set:
    dasar = izin_peran(role)
    for r in db.q("SELECT permission_kode, diizinkan FROM user_permissions "
                  "WHERE user_id=?", (user_id,)):
        if r["diizinkan"]:
            dasar.add(r["permission_kode"])
        else:
            dasar.discard(r["permission_kode"])
    return dasar


def set_izin_pengguna(user_id: int, permission_kode: str, diizinkan: bool) -> None:
    db.ex("""INSERT INTO user_permissions(user_id, permission_kode, diizinkan)
             VALUES(?,?,?)
             ON CONFLICT(user_id, permission_kode) DO UPDATE SET
               diizinkan=excluded.diizinkan""",
          (user_id, permission_kode, 1 if diizinkan else 0))


def set_izin_peran(role: str, permission_kode: str, diizinkan: bool) -> None:
    if diizinkan:
        db.ex("""INSERT INTO role_permissions(role, permission_kode) VALUES(?,?)
                 ON CONFLICT(role, permission_kode) DO NOTHING""",
              (role, permission_kode))
    else:
        db.ex("DELETE FROM role_permissions WHERE role=? AND permission_kode=?",
              (role, permission_kode))


def daftar_izin(modul: str = "") -> list:
    if modul:
        return db.q("SELECT * FROM permissions WHERE modul=? ORDER BY kode", (modul,))
    return db.q("SELECT * FROM permissions ORDER BY modul, kode")


def modul_izin() -> list:
    return [r["modul"] for r in db.q(
        "SELECT DISTINCT modul FROM permissions ORDER BY modul")]


# ==========================================================================
# MITRA USAHA (CUSTOMER & VENDOR)
# ==========================================================================
def buat_mitra(company_id: int, nama: str, tipe: str = "customer", **kw) -> int:
    if not nama.strip():
        raise ValueError("Nama mitra wajib diisi.")
    if tipe not in ("customer", "vendor", "keduanya"):
        raise ValueError("Tipe mitra harus customer, vendor, atau keduanya.")

    kode = kw.get("kode") or nomor_berikut(
        company_id, "CUST" if tipe == "customer" else "VEND")

    with db.tx() as conn:
        cur = conn.execute(
            """INSERT INTO partners(company_id, tipe, kode, nama, npwp, nik, email,
               telepon, kontak_person, alamat, kota, kode_pos, negara,
               rekening_bank, nama_bank, termin_hari, batas_kredit, status_pajak,
               catatan) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (company_id, tipe, kode, nama.strip(), kw.get("npwp", ""),
             kw.get("nik", ""), kw.get("email", ""), kw.get("telepon", ""),
             kw.get("kontak_person", ""), kw.get("alamat", ""), kw.get("kota", ""),
             kw.get("kode_pos", ""), kw.get("negara", "Indonesia"),
             kw.get("rekening_bank", ""), kw.get("nama_bank", ""),
             int(kw.get("termin_hari", 30) or 30), ringkas_angka(kw.get("batas_kredit")),
             kw.get("status_pajak", "umum"), kw.get("catatan", "")))
        pid = cur.lastrowid
    catat_riwayat(company_id, "partners", pid, "create", kw.get("user_id"),
                  kw.get("username", ""), "", "", nama)
    return pid


def ubah_mitra(partner_id: int, **kw) -> None:
    row = db.q1("SELECT * FROM partners WHERE id=?", (partner_id,))
    if row is None:
        raise ValueError("Mitra tidak ditemukan.")
    bidang = ["nama", "tipe", "npwp", "nik", "email", "telepon", "kontak_person",
              "alamat", "kota", "kode_pos", "negara", "rekening_bank", "nama_bank",
              "termin_hari", "batas_kredit", "status_pajak", "catatan", "is_active"]
    sets, params = [], []
    for f in bidang:
        if f in kw:
            sets.append(f"{f}=?")
            params.append(kw[f])
            catat_riwayat(row["company_id"], "partners", partner_id, "update",
                          kw.get("user_id"), kw.get("username", ""), f,
                          row[f] if f in row.keys() else "", kw[f])
    if not sets:
        return
    params.append(partner_id)
    db.ex(f"UPDATE partners SET {', '.join(sets)} WHERE id=?", params)


def daftar_mitra(company_id: int, tipe: str = "", cari: str = "",
                 hanya_aktif: bool = True) -> list:
    sql = "SELECT * FROM partners WHERE company_id=? AND deleted_at IS NULL"
    params: list = [company_id]
    if tipe:
        sql += " AND (tipe=? OR tipe='keduanya')"
        params.append(tipe)
    if hanya_aktif:
        sql += " AND is_active=1"
    if cari:
        sql += (" AND (nama LIKE ? OR kode LIKE ? OR npwp LIKE ? OR email LIKE ? "
                "OR telepon LIKE ?)")
        params += [f"%{cari}%"] * 5
    sql += " ORDER BY nama"
    return db.q(sql, params)


def get_mitra(partner_id: int):
    return db.q1("SELECT * FROM partners WHERE id=?", (partner_id,))


def hapus_mitra(partner_id: int, oleh: str = "") -> None:
    row = db.q1("SELECT * FROM partners WHERE id=?", (partner_id,))
    if row is None:
        return
    ke_recycle_bin(row["company_id"], "partners", partner_id, row["nama"],
                   dict(row), oleh)
    db.ex("UPDATE partners SET deleted_at=datetime('now','localtime'), is_active=0 "
          "WHERE id=?", (partner_id,))
    catat_riwayat(row["company_id"], "partners", partner_id, "delete", None, oleh)


def ringkasan_mitra(partner_id: int) -> dict:
    """Riwayat transaksi & saldo piutang/utang satu mitra."""
    m = get_mitra(partner_id)
    if m is None:
        return {}
    hasil = {
        "mitra": dict(m),
        "total_invoice": 0, "jumlah_invoice": 0, "piutang": 0,
        "total_dibayar": 0, "total_bill": 0, "jumlah_bill": 0, "utang": 0,
        "batas_kredit": m["batas_kredit"] or 0,
    }
    if m["tipe"] in ("customer", "keduanya"):
        hasil["total_invoice"] = int(db.scalar(
            "SELECT COALESCE(SUM(total),0) FROM invoices WHERE partner_id=? "
            "AND deleted_at IS NULL AND status != 'batal'", (partner_id,)))
        hasil["piutang"] = int(db.scalar(
            "SELECT COALESCE(SUM(sisa),0) FROM invoices WHERE partner_id=? "
            "AND deleted_at IS NULL AND status NOT IN ('lunas','batal')",
            (partner_id,)))
        hasil["jumlah_invoice"] = int(db.scalar(
            "SELECT COUNT(*) FROM invoices WHERE partner_id=? AND deleted_at IS NULL",
            (partner_id,)))
        hasil["total_dibayar"] = int(db.scalar(
            "SELECT COALESCE(SUM(jumlah),0) FROM receipts WHERE partner_id=? "
            "AND deleted_at IS NULL AND status='aktif'", (partner_id,)))
    if m["tipe"] in ("vendor", "keduanya"):
        hasil["total_bill"] = int(db.scalar(
            "SELECT COALESCE(SUM(total),0) FROM bills WHERE partner_id=? "
            "AND deleted_at IS NULL AND status != 'batal'", (partner_id,)))
        hasil["utang"] = int(db.scalar(
            "SELECT COALESCE(SUM(sisa),0) FROM bills WHERE partner_id=? "
            "AND deleted_at IS NULL AND status NOT IN ('lunas','batal')",
            (partner_id,)))
        hasil["jumlah_bill"] = int(db.scalar(
            "SELECT COUNT(*) FROM bills WHERE partner_id=? AND deleted_at IS NULL",
            (partner_id,)))
    hasil["kredit_tersisa"] = max(0, hasil["batas_kredit"] - hasil["piutang"])
    return hasil


def riwayat_mitra(partner_id: int, limit: int = 200) -> list:
    hasil: list[dict] = []
    for tabel, jenis, kolom in [
            ("invoices", "invoice", "total"), ("receipts", "penerimaan", "jumlah"),
            ("bills", "bill", "total"), ("vendor_payments", "pembayaran", "jumlah"),
            ("credit_notes", "nota kredit", "jumlah")]:
        for r in db.q(f"SELECT tanggal, nomor, {kolom} AS jumlah, status "
                      f"FROM {tabel} WHERE partner_id=? AND deleted_at IS NULL",
                      (partner_id,)):
            d = dict(r)
            d["jenis"] = jenis
            hasil.append(d)
    hasil.sort(key=lambda x: x["tanggal"], reverse=True)
    return hasil[:limit]


# ==========================================================================
# PRODUK, GUDANG & PERSEDIAAN
# ==========================================================================
def buat_kategori_produk(company_id: int, nama: str, **kw) -> int:
    cur = db.ex("""INSERT INTO product_categories(company_id, nama, akun_persediaan,
                  akun_pendapatan, akun_hpp, catatan) VALUES(?,?,?,?,?,?)""",
                (company_id, nama.strip(), kw.get("akun_persediaan", "1104"),
                 kw.get("akun_pendapatan", "4001"), kw.get("akun_hpp", "5001"),
                 kw.get("catatan", "")))
    return cur.lastrowid


def daftar_kategori_produk(company_id: int) -> list:
    return db.q("SELECT * FROM product_categories WHERE company_id=? ORDER BY nama",
                (company_id,))


def buat_produk(company_id: int, nama: str, **kw) -> int:
    if not nama.strip():
        raise ValueError("Nama produk wajib diisi.")
    kode = kw.get("kode") or nomor_berikut(company_id, "PRD")
    tipe = kw.get("tipe", "barang")
    if tipe not in ("barang", "jasa"):
        raise ValueError("Tipe produk harus 'barang' atau 'jasa'.")
    metode = kw.get("metode_hpp", "average")
    if metode not in ("fifo", "average"):
        raise ValueError("Metode HPP harus 'fifo' atau 'average'.")

    with db.tx() as conn:
        cur = conn.execute(
            """INSERT INTO products(company_id, kategori_id, kode, barcode, nama,
               deskripsi, satuan, tipe, harga_beli, harga_jual, metode_hpp,
               stok_minimum, akun_persediaan, akun_pendapatan, akun_hpp)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (company_id, kw.get("kategori_id"), kode, kw.get("barcode", ""),
             nama.strip(), kw.get("deskripsi", ""), kw.get("satuan", "pcs"),
             tipe, ringkas_angka(kw.get("harga_beli")), ringkas_angka(kw.get("harga_jual")),
             metode, ringkas_angka(kw.get("stok_minimum")),
             kw.get("akun_persediaan", "1104"), kw.get("akun_pendapatan", "4001"),
             kw.get("akun_hpp", "5001")))
        pid = cur.lastrowid

        qty_awal = float(kw.get("qty_awal", 0) or 0)
        if qty_awal and tipe == "barang":
            wh_id = pastikan_gudang_utama(company_id)
            harga = ringkas_angka(kw.get("harga_beli"))
            nilai = int(round(qty_awal * harga))
            # Tanggal stok awal harus lebih awal dari transaksi mana pun agar
            # urutan FIFO benar. Default: awal tahun berjalan.
            tanggal_awal = kw.get("tanggal_stok_awal") or f"{date.today().year}-01-01"
            conn.execute("""INSERT INTO stock_balances(company_id, product_id,
                            warehouse_id, qty, nilai_total) VALUES(?,?,?,?,?)""",
                         (company_id, pid, wh_id, qty_awal, nilai))
            conn.execute("""INSERT INTO stock_movements(company_id, product_id,
                            warehouse_id, tanggal, tipe, ref_tipe, qty, harga_satuan,
                            nilai, qty_sisa_fifo, keterangan)
                            VALUES(?,?,?,?,'masuk','awal',?,?,?,?,'Stok awal')""",
                         (company_id, pid, wh_id, tanggal_awal, qty_awal, harga,
                          nilai, qty_awal))
    catat_riwayat(company_id, "products", pid, "create", kw.get("user_id"),
                  kw.get("username", ""), "", "", nama)
    return pid


def ubah_produk(product_id: int, **kw) -> None:
    row = db.q1("SELECT * FROM products WHERE id=?", (product_id,))
    if row is None:
        raise ValueError("Produk tidak ditemukan.")
    bidang = ["nama", "kategori_id", "barcode", "deskripsi", "satuan", "tipe",
              "harga_beli", "harga_jual", "metode_hpp", "stok_minimum",
              "akun_persediaan", "akun_pendapatan", "akun_hpp", "is_active"]
    sets, params = [], []
    for f in bidang:
        if f in kw:
            sets.append(f"{f}=?")
            params.append(kw[f])
            catat_riwayat(row["company_id"], "products", product_id, "update",
                          kw.get("user_id"), kw.get("username", ""), f,
                          row[f] if f in row.keys() else "", kw[f])
    if not sets:
        return
    params.append(product_id)
    db.ex(f"UPDATE products SET {', '.join(sets)} WHERE id=?", params)


def daftar_produk(company_id: int, cari: str = "", tipe: str = "",
                  hanya_aktif: bool = True) -> list:
    sql = """SELECT p.*, c.nama AS kategori_nama,
                    COALESCE((SELECT SUM(qty) FROM stock_balances WHERE product_id=p.id),0) AS stok,
                    COALESCE((SELECT SUM(nilai_total) FROM stock_balances WHERE product_id=p.id),0) AS nilai_stok
             FROM products p
             LEFT JOIN product_categories c ON c.id = p.kategori_id
             WHERE p.company_id=? AND p.deleted_at IS NULL"""
    params: list = [company_id]
    if hanya_aktif:
        sql += " AND p.is_active=1"
    if tipe:
        sql += " AND p.tipe=?"
        params.append(tipe)
    if cari:
        sql += " AND (p.nama LIKE ? OR p.kode LIKE ? OR p.barcode LIKE ?)"
        params += [f"%{cari}%"] * 3
    sql += " ORDER BY p.nama"
    return db.q(sql, params)


def get_produk(product_id: int):
    return db.q1("SELECT * FROM products WHERE id=?", (product_id,))


def hapus_produk(product_id: int, oleh: str = "") -> None:
    row = db.q1("SELECT * FROM products WHERE id=?", (product_id,))
    if row is None:
        return
    ke_recycle_bin(row["company_id"], "products", product_id, row["nama"],
                   dict(row), oleh)
    db.ex("UPDATE products SET deleted_at=datetime('now','localtime'), is_active=0 "
          "WHERE id=?", (product_id,))


def buat_gudang(company_id: int, nama: str, **kw) -> int:
    kode = kw.get("kode")
    if not kode:
        # Pastikan kode unik — gudang utama mungkin sudah memakai GDG001.
        n = int(db.scalar("SELECT COUNT(*) FROM warehouses WHERE company_id=?",
                          (company_id,))) + 1
        kode = f"GDG{n:03d}"
        while db.q1("SELECT 1 FROM warehouses WHERE company_id=? AND kode=?",
                    (company_id, kode)):
            n += 1
            kode = f"GDG{n:03d}"
    cur = db.ex("INSERT INTO warehouses(company_id, kode, nama, lokasi, pic) "
                "VALUES(?,?,?,?,?)",
                (company_id, kode, nama.strip(), kw.get("lokasi", ""), kw.get("pic", "")))
    return cur.lastrowid


def pastikan_gudang_utama(company_id: int) -> int:
    """
    Pastikan gudang utama ada. Dibuat langsung lewat SQL agar dapat dipanggil
    dari dalam transaksi yang sedang berjalan.
    """
    row = db.q1("SELECT id FROM warehouses WHERE company_id=? AND is_active=1 "
                "AND nama LIKE 'Gudang Utama%' ORDER BY id LIMIT 1", (company_id,))
    if row:
        return row["id"]

    kode = "GDG001"
    n = 1
    while db.q1("SELECT 1 FROM warehouses WHERE company_id=? AND kode=?",
                (company_id, kode)):
        n += 1
        kode = f"GDG{n:03d}"
    cur = db.ex("INSERT INTO warehouses(company_id, kode, nama) VALUES(?,?,?)",
                (company_id, kode, "Gudang Utama"))
    return cur.lastrowid


def daftar_gudang(company_id: int, hanya_aktif: bool = True) -> list:
    sql = "SELECT * FROM warehouses WHERE company_id=?"
    if hanya_aktif:
        sql += " AND is_active=1"
    sql += " ORDER BY kode"
    return db.q(sql, (company_id,))


def gudang_utama(company_id: int) -> int:
    """Kembalikan id gudang utama; dibuat otomatis bila belum ada."""
    return pastikan_gudang_utama(company_id)


# --------------------------------------------------------------------------
# STOK: FIFO & AVERAGE
# --------------------------------------------------------------------------
def saldo_stok(company_id: int, product_id: int,
               warehouse_id: Optional[int] = None) -> dict:
    if warehouse_id:
        row = db.q1("SELECT * FROM stock_balances WHERE product_id=? AND warehouse_id=?",
                    (product_id, warehouse_id))
    else:
        row = db.q1("""SELECT COALESCE(SUM(qty),0) AS qty,
                              COALESCE(SUM(nilai_total),0) AS nilai_total
                       FROM stock_balances WHERE company_id=? AND product_id=?""",
                    (company_id, product_id))
    if row is None:
        return {"qty": 0.0, "nilai_total": 0, "hpp_satuan": 0}
    qty = float(row["qty"] or 0)
    nilai = int(row["nilai_total"] or 0)
    return {"qty": qty, "nilai_total": nilai,
            "hpp_satuan": int(nilai / qty) if qty else 0}


def stok_masuk(company_id: int, product_id: int, qty: float, harga_satuan: int,
               tanggal: Optional[str] = None, warehouse_id: Optional[int] = None,
               ref_tipe: str = "", ref_id: Optional[int] = None, no_ref: str = "",
               keterangan: str = "") -> dict:
    if qty <= 0:
        raise ValueError("Jumlah barang masuk harus lebih besar dari nol.")
    tanggal = tanggal or hari_ini()
    wh = warehouse_id or gudang_utama(company_id)
    nilai = int(round(qty * int(harga_satuan)))

    with db.tx() as conn:
        sb = conn.execute("SELECT * FROM stock_balances WHERE product_id=? AND "
                          "warehouse_id=?", (product_id, wh)).fetchone()
        if sb is None:
            conn.execute("""INSERT INTO stock_balances(company_id, product_id,
                            warehouse_id, qty, nilai_total) VALUES(?,?,?,?,?)""",
                         (company_id, product_id, wh, qty, nilai))
        else:
            conn.execute("""UPDATE stock_balances SET qty=qty+?, nilai_total=nilai_total+?
                            WHERE product_id=? AND warehouse_id=?""",
                         (qty, nilai, product_id, wh))
        cur = conn.execute(
            """INSERT INTO stock_movements(company_id, product_id, warehouse_id,
               tanggal, tipe, ref_tipe, ref_id, no_ref, qty, harga_satuan, nilai,
               qty_sisa_fifo, keterangan) VALUES(?,?,?,?,'masuk',?,?,?,?,?,?,?,?)""",
            (company_id, product_id, wh, tanggal, ref_tipe, ref_id, no_ref,
             qty, int(harga_satuan), nilai, qty, keterangan))
        mov_id = cur.lastrowid
    return {"movement_id": mov_id, "nilai": nilai,
            "saldo": saldo_stok(company_id, product_id, wh)}


def stok_keluar(company_id: int, product_id: int, qty: float,
                tanggal: Optional[str] = None, warehouse_id: Optional[int] = None,
                ref_tipe: str = "", ref_id: Optional[int] = None, no_ref: str = "",
                keterangan: str = "", izinkan_negatif: bool = False) -> dict:
    """Keluarkan stok dan hitung HPP sesuai metode (FIFO / Average)."""
    if qty <= 0:
        raise ValueError("Jumlah barang keluar harus lebih besar dari nol.")
    tanggal = tanggal or hari_ini()
    wh = warehouse_id or gudang_utama(company_id)
    produk = get_produk(product_id)
    if produk is None:
        raise ValueError("Produk tidak ditemukan.")

    metode = (produk["metode_hpp"] or "average").lower()
    total_hpp = 0
    rincian: list[dict] = []
    sisa = float(qty)

    with db.tx() as conn:
        sb = conn.execute("SELECT * FROM stock_balances WHERE product_id=? AND "
                          "warehouse_id=?", (product_id, wh)).fetchone()
        tersedia = float(sb["qty"]) if sb else 0.0
        if qty > tersedia + 1e-9 and not izinkan_negatif:
            raise ValueError(
                f"Stok tidak cukup. Tersedia {tersedia:g} {produk['satuan']}, "
                f"diminta {qty:g}. Lakukan penyesuaian stok atau pembelian dahulu.")

        if metode == "fifo":
            for l in conn.execute(
                    """SELECT * FROM stock_movements WHERE product_id=? AND
                       warehouse_id=? AND qty_sisa_fifo > 0 ORDER BY tanggal, id""",
                    (product_id, wh)).fetchall():
                if sisa <= 1e-9:
                    break
                ambil = min(sisa, float(l["qty_sisa_fifo"]))
                nilai = int(round(ambil * int(l["harga_satuan"])))
                total_hpp += nilai
                sisa -= ambil
                conn.execute("UPDATE stock_movements SET qty_sisa_fifo=qty_sisa_fifo-? "
                             "WHERE id=?", (ambil, l["id"]))
                rincian.append({"lapisan_id": l["id"], "qty": ambil,
                                "harga": int(l["harga_satuan"]), "nilai": nilai})
            if sisa > 1e-9:   # stok negatif diizinkan
                harga = int(produk["harga_beli"] or 0)
                nilai = int(round(sisa * harga))
                total_hpp += nilai
                rincian.append({"lapisan_id": None, "qty": sisa, "harga": harga,
                                "nilai": nilai})
                sisa = 0
        else:  # average
            hpp_satuan = (int(sb["nilai_total"] / sb["qty"])
                          if sb and sb["qty"] else int(produk["harga_beli"] or 0))
            total_hpp = int(round(qty * hpp_satuan))
            rincian.append({"lapisan_id": None, "qty": qty, "harga": hpp_satuan,
                            "nilai": total_hpp})

        if sb is None:
            conn.execute("""INSERT INTO stock_balances(company_id, product_id,
                            warehouse_id, qty, nilai_total) VALUES(?,?,?,?,?)""",
                         (company_id, product_id, wh, -qty, -total_hpp))
        else:
            conn.execute("""UPDATE stock_balances SET qty=qty-?, nilai_total=nilai_total-?
                            WHERE product_id=? AND warehouse_id=?""",
                         (qty, total_hpp, product_id, wh))

        hpp_satuan_rata = int(round(total_hpp / qty)) if qty else 0
        cur = conn.execute(
            """INSERT INTO stock_movements(company_id, product_id, warehouse_id,
               tanggal, tipe, ref_tipe, ref_id, no_ref, qty, harga_satuan, nilai,
               qty_sisa_fifo, keterangan) VALUES(?,?,?,?,'keluar',?,?,?,?,?,?,0,?)""",
            (company_id, product_id, wh, tanggal, ref_tipe, ref_id, no_ref,
             -qty, hpp_satuan_rata, -total_hpp, keterangan))
        mov_id = cur.lastrowid

    return {"movement_id": mov_id, "hpp": total_hpp, "hpp_satuan": hpp_satuan_rata,
            "rincian": rincian, "saldo": saldo_stok(company_id, product_id, wh)}


def penyesuaian_stok(company_id: int, product_id: int, qty_baru: float,
                     tanggal: Optional[str] = None, warehouse_id: Optional[int] = None,
                     alasan: str = "", user_id=None) -> dict:
    wh = warehouse_id or gudang_utama(company_id)
    saldo = saldo_stok(company_id, product_id, wh)
    selisih = qty_baru - saldo["qty"]
    if abs(selisih) < 1e-9:
        return {"selisih": 0, "nilai": 0, "tipe": "tidak_ada_perubahan"}

    if selisih > 0:
        p = get_produk(product_id)
        harga = saldo["hpp_satuan"] or int(p["harga_beli"] if p else 0)
        r = stok_masuk(company_id, product_id, selisih, harga, tanggal, wh,
                       "penyesuaian", None, "", f"Stock opname: {alasan}")
        return {"selisih": selisih, "nilai": r["nilai"], "tipe": "tambah"}
    r = stok_keluar(company_id, product_id, -selisih, tanggal, wh, "penyesuaian",
                    None, "", f"Stock opname: {alasan}", izinkan_negatif=True)
    return {"selisih": selisih, "nilai": r["hpp"], "tipe": "kurang"}


def saldo_stok_sebelum(company_id: int, product_id: int, tanggal: str,
                       warehouse_id: Optional[int] = None) -> float:
    """
    Jumlah stok sebelum tanggal tertentu.

    Dipakai sebagai saldo awal pada kartu stok. Tanpa saldo awal ini, kartu
    stok yang disaring pada rentang tanggal tertentu hanya menampilkan
    perubahan di dalam rentang itu, sehingga saldo yang terlihat bukan saldo
    yang sebenarnya.
    """
    sql = ("SELECT COALESCE(SUM(qty),0) AS qty FROM stock_movements "
           "WHERE company_id=? AND product_id=? AND tanggal < ?")
    params: list = [company_id, product_id, tanggal]
    if warehouse_id:
        sql += " AND warehouse_id=?"
        params.append(warehouse_id)
    return float(db.scalar(sql, params) or 0)


def kartu_stok(company_id: int, product_id: int, tanggal_awal: str = "",
               tanggal_akhir: str = "", warehouse_id: Optional[int] = None) -> list:
    sql = "SELECT * FROM stock_movements WHERE company_id=? AND product_id=?"
    params: list = [company_id, product_id]
    if warehouse_id:
        sql += " AND warehouse_id=?"
        params.append(warehouse_id)
    if tanggal_awal:
        sql += " AND tanggal >= ?"
        params.append(tanggal_awal)
    if tanggal_akhir:
        sql += " AND tanggal <= ?"
        params.append(tanggal_akhir)
    sql += " ORDER BY tanggal, id"
    return db.q(sql, params)


def daftar_stok(company_id: int, cari: str = "", hanya_menipis: bool = False) -> list:
    sql = """SELECT p.id AS product_id, p.kode, p.nama, p.satuan, p.metode_hpp,
                    p.stok_minimum, p.harga_beli, p.harga_jual,
                    COALESCE(SUM(sb.qty),0) AS qty,
                    COALESCE(SUM(sb.nilai_total),0) AS nilai_total
             FROM products p
             LEFT JOIN stock_balances sb ON sb.product_id = p.id
             WHERE p.company_id=? AND p.deleted_at IS NULL AND p.tipe='barang'
               AND p.is_active=1"""
    params: list = [company_id]
    if cari:
        sql += " AND (p.nama LIKE ? OR p.kode LIKE ?)"
        params += [f"%{cari}%"] * 2
    sql += " GROUP BY p.id"
    if hanya_menipis:
        sql += " HAVING qty <= p.stok_minimum"
    sql += " ORDER BY p.nama"

    keluar = []
    for r in db.q(sql, params):
        d = dict(r)
        d["hpp_satuan"] = int(d["nilai_total"] / d["qty"]) if d["qty"] else 0
        d["nilai_jual"] = int(d["qty"] * (d["harga_jual"] or 0))
        keluar.append(d)
    return keluar


def transfer_stok(company_id: int, product_id: int, qty: float, dari_gudang: int,
                  ke_gudang: int, tanggal: Optional[str] = None,
                  keterangan: str = "") -> dict:
    if dari_gudang == ke_gudang:
        raise ValueError("Gudang asal dan tujuan tidak boleh sama.")
    tanggal = tanggal or hari_ini()
    keluar = stok_keluar(company_id, product_id, qty, tanggal, dari_gudang,
                         "transfer", None, "", f"Transfer keluar: {keterangan}")
    masuk = stok_masuk(company_id, product_id, qty, keluar["hpp_satuan"], tanggal,
                       ke_gudang, "transfer", None, "",
                       f"Transfer masuk: {keterangan}")
    return {"keluar": keluar, "masuk": masuk}


def nilai_persediaan_total(company_id: int) -> int:
    return int(db.scalar(
        "SELECT COALESCE(SUM(nilai_total),0) FROM stock_balances WHERE company_id=?",
        (company_id,)))


def produk_menipis(company_id: int) -> list:
    return daftar_stok(company_id, hanya_menipis=True)
