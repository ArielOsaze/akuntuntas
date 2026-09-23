"""
Reset data usaha.

Dipakai saat aplikasi hendak dipakai untuk perusahaan baru, atau saat data
percobaan ingin dibersihkan sebelum dipakai sungguhan. Data yang dihapus
adalah seluruh transaksi dan data usaha; pengguna, profil perusahaan, dan
bagan akun tetap dipertahankan supaya aplikasi langsung siap dipakai.

Cadangan otomatis dibuat lebih dulu, sehingga reset selalu dapat dibatalkan
dengan memulihkan cadangan itu.
"""

from __future__ import annotations

import logging
import sqlite3
from typing import Optional

from .. import db

# Tabel yang dibersihkan saat reset data usaha.
#
# Urutan tidak menjadi masalah karena pemeriksaan kunci asing dimatikan
# selama penghapusan, lalu dinyalakan kembali. Penghapusan dijalankan dalam
# satu transaksi sehingga bila ada yang gagal, tidak ada yang terhapus
# setengah jalan.
TABEL_USAHA = (
    # buku besar
    "journal_lines",
    "journal_entries",
    "jurnal_balik",
    "change_history",
    # penjualan
    "invoice_items",
    "invoices",
    "receipt_allocations",
    "receipts",
    "credit_notes",
    "sales_order_items",
    "sales_orders",
    "sales",
    # pembelian
    "purchase_order_items",
    "purchase_orders",
    "bill_items",
    "bills",
    "vendor_payment_allocations",
    "vendor_payments",
    "purchases",
    # persediaan
    "stock_movements",
    "stock_balances",
    "products",
    "product_categories",
    "warehouses",
    # kas dan bank
    "bank_transactions",
    "bank_reconciliations",
    "bank_accounts",
    "cash_accounts",
    "expenses",
    "expense_categories",
    # aset tetap
    "depreciation_entries",
    "fixed_assets",
    # pegawai dan payroll
    "payroll_items",
    "payroll_runs",
    "employees",
    # pajak
    "tax_records",
    "tax_payments",
    "fiscal_adjustments",
    "checklist_items",
    "faktur_pajak",
    "nsfp",
    "uang_muka_pakai",
    "uang_muka",
    "pajak_daerah",
    "bea_meterai",
    "pph15",
    # kontrak
    "kontrak_berkas",
    "kontrak_termin",
    "kontrak_item",
    "kontrak",
    # lain-lain
    "partners",
    "documents",
    "recurring_templates",
    "reminders",
    "recycle_bin",
    "cost_centers",
    "projects",
    "branches",
    "fiscal_periods",
    "number_sequences",
    "kurs",
)


def ringkasan(company_id: int) -> dict:
    """
    Hitung berapa banyak data yang akan terhapus.

    Angka ini ditampilkan sebelum pengguna menekan tombol reset supaya ia
    tahu apa yang akan hilang.
    """
    hitung = {
        "mitra": ("partners", "company_id"),
        "produk": ("products", "company_id"),
        "penjualan": ("invoices", "company_id"),
        "pembelian": ("bills", "company_id"),
        "jurnal": ("journal_entries", "company_id"),
        "kontrak": ("kontrak", "company_id"),
        "aset tetap": ("fixed_assets", "company_id"),
        "pegawai": ("employees", "company_id"),
    }
    hasil = {}
    for label, (tabel, kolom) in hitung.items():
        try:
            hasil[label] = db.scalar(
                f"SELECT COUNT(*) FROM {tabel} WHERE {kolom}=?", (company_id,))
        except Exception:
            hasil[label] = 0
    return hasil


def reset_data(company_id: int, catat_ke_log: bool = True,
               user_id: Optional[int] = None,
               username: str = "") -> dict:
    """
    Hapus seluruh data usaha, sisakan pengguna, profil, dan bagan akun.

    Cadangan dibuat lebih dulu. Bila penghapusan gagal di tengah jalan,
    seluruh perubahan dibatalkan sehingga data tetap utuh.

    Mengembalikan keterangan berisi jumlah baris yang terhapus dan lokasi
    berkas cadangan.
    """
    from ..core import security as sec

    sebelum = ringkasan(company_id)

    # Cadangan sebelum menghapus. Tanpa ini, kesalahan memilih perusahaan
    # berarti kehilangan seluruh pembukuan.
    berkas = db.create_backup("Sebelum reset data")

    terhapus = {}
    gagal_dihapus = []
    conn = db.get_conn()
    kunci_asing = conn.execute("PRAGMA foreign_keys").fetchone()[0]

    try:
        conn.execute("PRAGMA foreign_keys=OFF")
        conn.execute("BEGIN")
        for tabel in TABEL_USAHA:
            try:
                # Tabel tanpa kolom company_id dihapus seluruhnya karena
                # isinya hanya milik perusahaan aktif pada aplikasi ini.
                kolom = [d[1] for d in conn.execute(
                    f"PRAGMA table_info({tabel})").fetchall()]
                if not kolom:
                    # Tabel belum ada pada basis data lama: wajar dilewati.
                    continue
                if "company_id" in kolom:
                    cur = conn.execute(
                        f"DELETE FROM {tabel} WHERE company_id=?", (company_id,))
                else:
                    cur = conn.execute(f"DELETE FROM {tabel}")
                if cur.rowcount > 0:
                    terhapus[tabel] = cur.rowcount
            except sqlite3.OperationalError as e:
                # Tabel ada tetapi tidak dapat dihapus. Ini bukan keadaan
                # yang boleh diabaikan: sisa datanya akan terbawa ke
                # pembukuan baru, jadi dicatat agar dapat ditelusuri.
                gagal_dihapus.append(f"{tabel} ({e})")
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.execute(f"PRAGMA foreign_keys={'ON' if kunci_asing else 'OFF'}")

    if gagal_dihapus:
        logging.getLogger("akuntansiid").warning(
            "Sebagian tabel tidak dapat dibersihkan saat reset: %s",
            ", ".join(gagal_dihapus))

    # Nomor dokumen dimulai ulang dari satu supaya perusahaan baru tidak
    # mewarisi nomor urut perusahaan sebelumnya.
    try:
        db.ex("DELETE FROM number_sequences WHERE company_id=?", (company_id,))
    except Exception as e:
        gagal_dihapus.append(f"number_sequences ({e})")

    if catat_ke_log:
        try:
            sec.log_action(user_id, username, "data.reset",
                           f"Reset data usaha. Terhapus: "
                           f"{sum(terhapus.values())} baris. "
                           f"Cadangan: {berkas.name}")
        except Exception as e:
            logging.getLogger("akuntansiid").warning(
                "Riwayat reset gagal dicatat: %s", e)

    return {
        "sebelum": sebelum,
        "terhapus": terhapus,
        "jumlah_baris": sum(terhapus.values()),
        "berkas_cadangan": berkas,
        "gagal_dihapus": gagal_dihapus,
    }
