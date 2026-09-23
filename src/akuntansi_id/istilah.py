"""Terjemahan nilai teknis basis data menjadi teks yang enak dibaca.

Cara pakai:
    from .. import istilah
    istilah.label("action", "login.success")   -> "Masuk aplikasi"
    istilah.label("status", "lunas")           -> "Lunas"

Nilai di basis data memakai huruf kecil dan garis bawah (mis. `login.success`,
`non_deductible`) karena itu bentuk yang aman untuk kode. Pengguna tidak
perlu melihat bentuk mentah tersebut, jadi setiap nilai diterjemahkan ke
istilah Indonesia yang wajar sebelum ditampilkan.
"""

from __future__ import annotations

KAMUS = {
    # --- aksi pada jejak audit
    "login.success": "Masuk aplikasi",
    "login.fail": "Gagal masuk",
    "login.failed": "Gagal masuk",
    "login.blocked": "Masuk diblokir",
    "logout": "Keluar aplikasi",
    "company.create": "Perusahaan dibuat",
    "company.update": "Perusahaan diubah",
    "company.delete": "Perusahaan dihapus",
    "account.create": "Akun dibuat",
    "account.update": "Akun diubah",
    "account.delete": "Akun dihapus",
    "account.set_saldo_awal": "Saldo awal diisi",
    "user.create": "Pengguna dibuat",
    "user.update": "Pengguna diubah",
    "user.delete": "Pengguna dihapus",
    "user.password_change": "Password diubah",
    "user.role_change": "Hak akses diubah",
    "journal.create": "Jurnal dibuat",
    "journal.update": "Jurnal diubah",
    "journal.delete": "Jurnal dihapus",
    "sale.create": "Penjualan dibuat",
    "sale.update": "Penjualan diubah",
    "sale.delete": "Penjualan dihapus",
    "purchase.create": "Pembelian dibuat",
    "purchase.update": "Pembelian diubah",
    "purchase.delete": "Pembelian dihapus",
    "asset.create": "Aset dibuat",
    "asset.update": "Aset diubah",
    "asset.delete": "Aset dihapus",
    "asset.depreciate": "Penyusutan aset dihitung",
    "employee.create": "Karyawan dibuat",
    "employee.update": "Karyawan diubah",
    "employee.delete": "Karyawan dihapus",
    "payroll.calculate": "Payroll dihitung",
    "payroll.post": "Payroll dijurnal",
    "tax.create": "Pajak dicatat",
    "tax.update": "Pajak diubah",
    "tax.payment": "Pembayaran pajak dicatat",
    "user.reset_password": "Password direset",
    "user.change_password": "Password diubah",
    "user.activate": "Pengguna diaktifkan",
    "user.deactivate": "Pengguna dinonaktifkan",
    "backup.create": "Cadangan dibuat",
    "restore": "Data dipulihkan",
    "import": "Data diimpor",
    "export": "Data diekspor",

    # --- status dokumen
    "draft": "Draf",
    "terkirim": "Terkirim",
    "sebagian": "Sebagian",
    "lunas": "Lunas",
    "batal": "Dibatalkan",
    "jatuh_tempo": "Jatuh tempo",
    "belum_bayar": "Belum dibayar",
    "selesai": "Selesai",
    "aktif": "Aktif",
    "nonaktif": "Nonaktif",
    "menunggu": "Menunggu",
    "disetujui": "Disetujui",
    "ditolak": "Ditolak",
    "dikecualikan": "Dikecualikan",
    "diabaikan": "Diabaikan",
    "cocok": "Cocok",
    "belum_cocok": "Belum dicocokkan",

    # --- jenis & tipe
    "kas": "Kas",
    "bank": "Bank",
    "ewallet": "Dompet digital",
    "barang": "Barang",
    "jasa": "Jasa",
    "paket": "Paket",
    "customer": "Pelanggan",
    "supplier": "Pemasok",
    "pemasok": "Pemasok",
    "pelanggan": "Pelanggan",
    "masuk": "Masuk",
    "keluar": "Keluar",
    "umum": "Umum",
    "invoice": "Faktur",
    "pajak": "Pajak",
    "fifo": "FIFO",
    "average": "Rata-rata",
    "manual": "Manual",
    "otomatis": "Otomatis",

    # --- perlakuan fiskal
    "deductible/taxable": "Dapat dikurangkan",
    "non-deductible (+)": "Tidak dapat dikurangkan",
    "final income (-)": "Penghasilan final",
    "review fiskal": "Perlu telaah",

    # --- sumber jurnal
    "penjualan": "Penjualan",
    "pembelian": "Pembelian",
    "biaya": "Biaya",
    "penyesuaian": "Penyesuaian",
    "saldo_awal": "Saldo awal",
    "tutup_buku": "Tutup buku",
    "payroll": "Payroll",
    "transfer": "Transfer",

    # --- nama tabel basis data (dipakai kolom "Objek" pada jejak audit)
    "users": "Pengguna",
    "companies": "Perusahaan",
    "accounts": "Bagan akun",
    "journal_entries": "Jurnal",
    "journal_lines": "Baris jurnal",
    "invoices": "Faktur penjualan",
    "invoice_items": "Rincian faktur",
    "bills": "Tagihan pembelian",
    "bill_items": "Rincian tagihan",
    "payments": "Pembayaran",
    "expenses": "Biaya",
    "products": "Produk",
    "partners": "Mitra usaha",
    "warehouses": "Gudang",
    "stock_moves": "Mutasi stok",
    "fixed_assets": "Aset tetap",
    "employees": "Karyawan",
    "payroll_runs": "Penggajian",
    "cash_accounts": "Rekening kas & bank",
    "bank_accounts": "Rekening bank",
    "bank_transactions": "Transaksi bank",
    "reconciliations": "Rekonsiliasi",
    "projects": "Proyek",
    "cost_centers": "Pusat biaya",
    "dimensions": "Dimensi",
    "reminders": "Pengingat",
    "compliance_checklist": "Checklist kepatuhan",
    "tax_periods": "Masa pajak",
    "fiscal_periods": "Periode buku",
    "settings": "Pengaturan",
    "audit_log": "Jejak audit",
    "change_history": "Riwayat perubahan",
    "attachments": "Lampiran",
    "recycle_bin": "Keranjang sampah",
}

# Nilai yang hanya berupa satu kata teknis tetapi sudah punya bentuk baku
HURUF_BESAR = {"fifo", "ppn", "pph", "npwp", "pkp", "spt", "csv", "pdf", "id"}


def label(kunci: str, nilai) -> str:
    """Terjemahkan satu nilai; kembalikan apa adanya bila tidak dikenal."""
    if nilai is None:
        return ""
    teks = str(nilai).strip()
    if not teks:
        return ""

    kunci_lower = teks.lower()
    if kunci_lower in KAMUS:
        return KAMUS[kunci_lower]

    # bentuk teknis seperti "login.success" atau "belum_bayar"
    if "." in teks:
        akhir = teks.split(".")[-1].lower()
        if akhir in KAMUS:
            return KAMUS[akhir]

    if "_" in teks:
        bagian = [b for b in teks.split("_") if b]
        if bagian:
            hasil = []
            for i, b in enumerate(bagian):
                if b.lower() in HURUF_BESAR:
                    hasil.append(b.upper())
                elif b.lower() in KAMUS:
                    hasil.append(KAMUS[b.lower()])
                elif i == 0:
                    hasil.append(b.capitalize())
                else:
                    hasil.append(b.lower())
            return " ".join(hasil)

    return teks[:1].upper() + teks[1:] if teks.islower() else teks
