"""
AkunTuntas - Skema Database Lanjutan (Modul ERP Lengkap)
========================================================
Berisi seluruh tabel tambahan untuk fitur tingkat lanjut:

  • Mitra usaha     : customer, vendor/supplier
  • Produk & stok   : produk, kategori, gudang, mutasi stok (FIFO/Average)
  • Penjualan       : sales order, invoice, receipt, credit note, refund
  • Pembelian       : purchase order, bill, purchase return, payment
  • Biaya           : kategori, pengajuan, persetujuan, reimbursement, berkala
  • Bank            : rekening bank, transaksi bank, rekonsiliasi
  • Piutang/Utang   : aging, reminder, pembayaran sebagian
  • Dimensi         : cost center, proyek, cabang (multi-entitas & konsolidasi)
  • Tata kelola     : peran & izin granular, riwayat perubahan, soft delete,
                      recycle bin, lampiran dokumen, versi dokumen
  • Otomasi         : template transaksi berulang, penomoran otomatis
"""
from __future__ import annotations

SCHEMA_EXT_VERSION = 2

DDL_EXT = """
-- ======================================================================
-- PENOMORAN OTOMATIS
-- ======================================================================
CREATE TABLE IF NOT EXISTS number_sequences (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id  INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    kode        TEXT NOT NULL,              -- INV, PO, BILL, RCV, PAY, CN, dll.
    prefix      TEXT NOT NULL DEFAULT '',
    pola        TEXT NOT NULL DEFAULT '{prefix}/{tahun}/{urut:04d}',
    urut_akhir  INTEGER NOT NULL DEFAULT 0,
    reset_tiap_tahun INTEGER NOT NULL DEFAULT 1,
    tahun_aktif INTEGER NOT NULL DEFAULT 0,
    UNIQUE(company_id, kode)
);

-- ======================================================================
-- MITRA USAHA: CUSTOMER & VENDOR
-- ======================================================================
CREATE TABLE IF NOT EXISTS partners (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id      INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    tipe            TEXT NOT NULL DEFAULT 'customer',  -- customer|vendor|keduanya
    kode            TEXT NOT NULL,
    nama            TEXT NOT NULL,
    npwp            TEXT DEFAULT '',
    nik             TEXT DEFAULT '',
    email           TEXT DEFAULT '',
    telepon         TEXT DEFAULT '',
    kontak_person   TEXT DEFAULT '',
    alamat          TEXT DEFAULT '',
    kota            TEXT DEFAULT '',
    kode_pos        TEXT DEFAULT '',
    negara          TEXT DEFAULT 'Indonesia',
    rekening_bank   TEXT DEFAULT '',
    nama_bank       TEXT DEFAULT '',
    termin_hari     INTEGER NOT NULL DEFAULT 30,
    batas_kredit    INTEGER NOT NULL DEFAULT 0,
    status_pajak    TEXT DEFAULT 'umum',   -- umum|pkp|non_pkp
    catatan         TEXT DEFAULT '',
    is_active       INTEGER NOT NULL DEFAULT 1,
    deleted_at      TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS idx_partner_tipe ON partners(company_id, tipe, is_active);
CREATE INDEX IF NOT EXISTS idx_partner_nama ON partners(company_id, nama);

-- ======================================================================
-- PRODUK & PERSEDIAAN
-- ======================================================================
CREATE TABLE IF NOT EXISTS product_categories (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id  INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    nama        TEXT NOT NULL,
    akun_persediaan TEXT DEFAULT '1104',
    akun_pendapatan TEXT DEFAULT '4001',
    akun_hpp        TEXT DEFAULT '5001',
    catatan     TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS products (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id      INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    kategori_id     INTEGER REFERENCES product_categories(id) ON DELETE SET NULL,
    kode            TEXT NOT NULL,
    barcode         TEXT DEFAULT '',
    nama            TEXT NOT NULL,
    deskripsi       TEXT DEFAULT '',
    satuan          TEXT DEFAULT 'pcs',
    tipe            TEXT NOT NULL DEFAULT 'barang',  -- barang|jasa
    harga_beli      INTEGER NOT NULL DEFAULT 0,
    harga_jual      INTEGER NOT NULL DEFAULT 0,
    metode_hpp      TEXT NOT NULL DEFAULT 'average', -- fifo|average
    stok_minimum    INTEGER NOT NULL DEFAULT 0,
    akun_persediaan TEXT DEFAULT '1104',
    akun_pendapatan TEXT DEFAULT '4001',
    akun_hpp        TEXT DEFAULT '5001',
    is_active       INTEGER NOT NULL DEFAULT 1,
    deleted_at      TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    UNIQUE(company_id, kode)
);
CREATE INDEX IF NOT EXISTS idx_produk_nama ON products(company_id, nama);

CREATE TABLE IF NOT EXISTS warehouses (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id  INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    kode        TEXT NOT NULL,
    nama        TEXT NOT NULL,
    lokasi      TEXT DEFAULT '',
    pic         TEXT DEFAULT '',
    is_active   INTEGER NOT NULL DEFAULT 1,
    UNIQUE(company_id, kode)
);

-- Saldo stok per produk per gudang
CREATE TABLE IF NOT EXISTS stock_balances (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id      INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    product_id      INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    warehouse_id    INTEGER NOT NULL REFERENCES warehouses(id) ON DELETE CASCADE,
    qty             REAL NOT NULL DEFAULT 0,
    nilai_total     INTEGER NOT NULL DEFAULT 0,   -- untuk metode average
    qty_minimum     REAL NOT NULL DEFAULT 0,
    UNIQUE(product_id, warehouse_id)
);

-- Mutasi stok (kartu stok) - juga menyimpan lapisan FIFO
CREATE TABLE IF NOT EXISTS stock_movements (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id      INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    product_id      INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    warehouse_id    INTEGER NOT NULL REFERENCES warehouses(id) ON DELETE CASCADE,
    tanggal         TEXT NOT NULL,
    tipe            TEXT NOT NULL,          -- masuk|keluar|penyesuaian|transfer|retur
    ref_tipe        TEXT DEFAULT '',        -- penjualan|pembelian|penyesuaian|awal
    ref_id          INTEGER,
    no_ref          TEXT DEFAULT '',
    qty             REAL NOT NULL DEFAULT 0,      -- positif masuk, negatif keluar
    harga_satuan    INTEGER NOT NULL DEFAULT 0,
    nilai           INTEGER NOT NULL DEFAULT 0,
    qty_sisa_fifo   REAL NOT NULL DEFAULT 0,      -- sisa lapisan (untuk FIFO)
    keterangan      TEXT DEFAULT '',
    created_at      TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS idx_mutasi_produk ON stock_movements(product_id, tanggal);
CREATE INDEX IF NOT EXISTS idx_mutasi_ref ON stock_movements(ref_tipe, ref_id);

-- ======================================================================
-- PENJUALAN: SALES ORDER  INVOICE  RECEIPT (PEMBAYARAN)
-- ======================================================================
CREATE TABLE IF NOT EXISTS sales_orders (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id      INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    nomor           TEXT NOT NULL,
    tanggal         TEXT NOT NULL,
    partner_id      INTEGER REFERENCES partners(id) ON DELETE SET NULL,
    pelanggan       TEXT DEFAULT '',
    alamat_kirim    TEXT DEFAULT '',
    tanggal_kirim   TEXT,
    status          TEXT NOT NULL DEFAULT 'draft', -- draft|dikonfirmasi|sebagian|selesai|batal
    subtotal        INTEGER NOT NULL DEFAULT 0,
    diskon          INTEGER NOT NULL DEFAULT 0,
    dpp             INTEGER NOT NULL DEFAULT 0,
    ppn             INTEGER NOT NULL DEFAULT 0,
    total           INTEGER NOT NULL DEFAULT 0,
    catatan         TEXT DEFAULT '',
    deleted_at      TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS idx_so_company ON sales_orders(company_id, tanggal);

CREATE TABLE IF NOT EXISTS sales_order_items (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    so_id           INTEGER NOT NULL REFERENCES sales_orders(id) ON DELETE CASCADE,
    product_id      INTEGER REFERENCES products(id) ON DELETE SET NULL,
    deskripsi       TEXT DEFAULT '',
    qty             REAL NOT NULL DEFAULT 1,
    satuan          TEXT DEFAULT 'pcs',
    harga_satuan    INTEGER NOT NULL DEFAULT 0,
    diskon_persen   REAL NOT NULL DEFAULT 0,
    diskon_nilai    INTEGER NOT NULL DEFAULT 0,
    subtotal        INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS invoices (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id      INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    nomor           TEXT NOT NULL,
    so_id           INTEGER REFERENCES sales_orders(id) ON DELETE SET NULL,
    tanggal         TEXT NOT NULL,
    jatuh_tempo     TEXT,
    partner_id      INTEGER REFERENCES partners(id) ON DELETE SET NULL,
    pelanggan       TEXT DEFAULT '',
    npwp_nik        TEXT DEFAULT '',
    alamat          TEXT DEFAULT '',
    subtotal        INTEGER NOT NULL DEFAULT 0,
    diskon_persen   REAL NOT NULL DEFAULT 0,
    diskon_nilai    INTEGER NOT NULL DEFAULT 0,
    dpp             INTEGER NOT NULL DEFAULT 0,
    jenis_ppn       TEXT DEFAULT 'Non-PKP/Tidak Dipungut',
    ppn             INTEGER NOT NULL DEFAULT 0,
    total           INTEGER NOT NULL DEFAULT 0,
    dibayar         INTEGER NOT NULL DEFAULT 0,
    sisa            INTEGER NOT NULL DEFAULT 0,
    status          TEXT NOT NULL DEFAULT 'terkirim', -- draft|terkirim|sebagian|lunas|batal
    catatan         TEXT DEFAULT '',
    journal_entry_id INTEGER REFERENCES journal_entries(id) ON DELETE SET NULL,
    deleted_at      TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS idx_inv_company ON invoices(company_id, tanggal);
CREATE INDEX IF NOT EXISTS idx_inv_status ON invoices(company_id, status);

CREATE TABLE IF NOT EXISTS invoice_items (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id      INTEGER NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    product_id      INTEGER REFERENCES products(id) ON DELETE SET NULL,
    deskripsi       TEXT DEFAULT '',
    qty             REAL NOT NULL DEFAULT 1,
    satuan          TEXT DEFAULT 'pcs',
    harga_satuan    INTEGER NOT NULL DEFAULT 0,
    diskon_persen   REAL NOT NULL DEFAULT 0,
    diskon_nilai    INTEGER NOT NULL DEFAULT 0,
    subtotal        INTEGER NOT NULL DEFAULT 0,
    hpp             INTEGER NOT NULL DEFAULT 0
);

-- Penerimaan pembayaran (dari pelanggan)
CREATE TABLE IF NOT EXISTS receipts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id      INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    nomor           TEXT NOT NULL,
    tanggal         TEXT NOT NULL,
    partner_id      INTEGER REFERENCES partners(id) ON DELETE SET NULL,
    pelanggan       TEXT DEFAULT '',
    akun_kas        TEXT DEFAULT '1002',
    jumlah          INTEGER NOT NULL DEFAULT 0,
    metode          TEXT DEFAULT 'Transfer',   -- Tunai|Transfer|QRIS|Kartu|Cek
    referensi       TEXT DEFAULT '',
    catatan         TEXT DEFAULT '',
    status          TEXT NOT NULL DEFAULT 'aktif',  -- aktif|void
    journal_entry_id INTEGER REFERENCES journal_entries(id) ON DELETE SET NULL,
    deleted_at      TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

-- Alokasi pembayaran ke invoice (mendukung pembayaran sebagian)
CREATE TABLE IF NOT EXISTS receipt_allocations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    receipt_id      INTEGER NOT NULL REFERENCES receipts(id) ON DELETE CASCADE,
    invoice_id      INTEGER NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    jumlah          INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

-- Nota kredit (pengurang tagihan) & refund
CREATE TABLE IF NOT EXISTS credit_notes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id      INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    nomor           TEXT NOT NULL,
    tanggal         TEXT NOT NULL,
    invoice_id      INTEGER REFERENCES invoices(id) ON DELETE SET NULL,
    partner_id      INTEGER REFERENCES partners(id) ON DELETE SET NULL,
    pelanggan       TEXT DEFAULT '',
    tipe            TEXT NOT NULL DEFAULT 'retur',  -- retur|diskon|refund
    jumlah          INTEGER NOT NULL DEFAULT 0,
    alasan          TEXT DEFAULT '',
    status          TEXT NOT NULL DEFAULT 'aktif',  -- aktif|void
    journal_entry_id INTEGER REFERENCES journal_entries(id) ON DELETE SET NULL,
    deleted_at      TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

-- ======================================================================
-- PEMBELIAN: PURCHASE ORDER  BILL  PAYMENT
-- ======================================================================
CREATE TABLE IF NOT EXISTS purchase_orders (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id      INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    nomor           TEXT NOT NULL,
    tanggal         TEXT NOT NULL,
    partner_id      INTEGER REFERENCES partners(id) ON DELETE SET NULL,
    vendor          TEXT DEFAULT '',
    tanggal_terima  TEXT,
    status          TEXT NOT NULL DEFAULT 'draft', -- draft|dikonfirmasi|sebagian|selesai|batal
    subtotal        INTEGER NOT NULL DEFAULT 0,
    diskon          INTEGER NOT NULL DEFAULT 0,
    dpp             INTEGER NOT NULL DEFAULT 0,
    ppn             INTEGER NOT NULL DEFAULT 0,
    total           INTEGER NOT NULL DEFAULT 0,
    catatan         TEXT DEFAULT '',
    deleted_at      TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS purchase_order_items (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    po_id           INTEGER NOT NULL REFERENCES purchase_orders(id) ON DELETE CASCADE,
    product_id      INTEGER REFERENCES products(id) ON DELETE SET NULL,
    deskripsi       TEXT DEFAULT '',
    qty             REAL NOT NULL DEFAULT 1,
    satuan          TEXT DEFAULT 'pcs',
    harga_satuan    INTEGER NOT NULL DEFAULT 0,
    diskon_persen   REAL NOT NULL DEFAULT 0,
    subtotal        INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS bills (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id      INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    nomor           TEXT NOT NULL,             -- nomor internal
    nomor_vendor    TEXT DEFAULT '',           -- nomor invoice dari supplier
    po_id           INTEGER REFERENCES purchase_orders(id) ON DELETE SET NULL,
    tanggal         TEXT NOT NULL,
    jatuh_tempo     TEXT,
    partner_id      INTEGER REFERENCES partners(id) ON DELETE SET NULL,
    vendor          TEXT DEFAULT '',
    npwp_nik        TEXT DEFAULT '',
    jenis           TEXT NOT NULL DEFAULT 'Beban', -- Beban|Persediaan|Aset Tetap
    subtotal        INTEGER NOT NULL DEFAULT 0,
    diskon          INTEGER NOT NULL DEFAULT 0,
    dpp             INTEGER NOT NULL DEFAULT 0,
    jenis_ppn       TEXT DEFAULT 'Non-PKP/Tidak Dipungut',
    ppn             INTEGER NOT NULL DEFAULT 0,
    dapat_dikreditkan INTEGER NOT NULL DEFAULT 1,
    total           INTEGER NOT NULL DEFAULT 0,
    dibayar         INTEGER NOT NULL DEFAULT 0,
    sisa            INTEGER NOT NULL DEFAULT 0,
    status          TEXT NOT NULL DEFAULT 'terbuka', -- terbuka|sebagian|lunas|batal
    akun_beban      TEXT DEFAULT '6008',
    catatan         TEXT DEFAULT '',
    journal_entry_id INTEGER REFERENCES journal_entries(id) ON DELETE SET NULL,
    deleted_at      TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS idx_bill_company ON bills(company_id, tanggal);

CREATE TABLE IF NOT EXISTS bill_items (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    bill_id         INTEGER NOT NULL REFERENCES bills(id) ON DELETE CASCADE,
    product_id      INTEGER REFERENCES products(id) ON DELETE SET NULL,
    deskripsi       TEXT DEFAULT '',
    qty             REAL NOT NULL DEFAULT 1,
    satuan          TEXT DEFAULT 'pcs',
    harga_satuan    INTEGER NOT NULL DEFAULT 0,
    diskon_persen   REAL NOT NULL DEFAULT 0,
    subtotal        INTEGER NOT NULL DEFAULT 0
);

-- Pembayaran ke vendor
CREATE TABLE IF NOT EXISTS vendor_payments (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id      INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    nomor           TEXT NOT NULL,
    tanggal         TEXT NOT NULL,
    partner_id      INTEGER REFERENCES partners(id) ON DELETE SET NULL,
    vendor          TEXT DEFAULT '',
    akun_kas        TEXT DEFAULT '1002',
    jumlah          INTEGER NOT NULL DEFAULT 0,
    metode          TEXT DEFAULT 'Transfer',
    referensi       TEXT DEFAULT '',
    catatan         TEXT DEFAULT '',
    status          TEXT NOT NULL DEFAULT 'aktif',
    journal_entry_id INTEGER REFERENCES journal_entries(id) ON DELETE SET NULL,
    deleted_at      TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS vendor_payment_allocations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    payment_id      INTEGER NOT NULL REFERENCES vendor_payments(id) ON DELETE CASCADE,
    bill_id         INTEGER NOT NULL REFERENCES bills(id) ON DELETE CASCADE,
    jumlah          INTEGER NOT NULL DEFAULT 0
);

-- ======================================================================
-- BIAYA (EXPENSE MANAGEMENT)
-- ======================================================================
CREATE TABLE IF NOT EXISTS expense_categories (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id  INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    nama        TEXT NOT NULL,
    akun_beban  TEXT DEFAULT '6023',
    batas_nilai INTEGER NOT NULL DEFAULT 0,     -- di atas ini perlu persetujuan
    perlu_persetujuan INTEGER NOT NULL DEFAULT 0,
    catatan     TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS expenses (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id      INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    nomor           TEXT NOT NULL,
    tanggal         TEXT NOT NULL,
    kategori_id     INTEGER REFERENCES expense_categories(id) ON DELETE SET NULL,
    uraian          TEXT NOT NULL,
    jumlah          INTEGER NOT NULL DEFAULT 0,
    akun_beban      TEXT DEFAULT '6023',
    akun_kas        TEXT DEFAULT '1002',
    partner_id      INTEGER REFERENCES partners(id) ON DELETE SET NULL,
    vendor          TEXT DEFAULT '',
    cost_center_id  INTEGER,
    project_id      INTEGER,
    branch_id       INTEGER,
    tipe            TEXT NOT NULL DEFAULT 'langsung', -- langsung|reimbursement|berkala
    diajukan_oleh   TEXT DEFAULT '',
    status          TEXT NOT NULL DEFAULT 'disetujui',
    -- draft|diajukan|disetujui|ditolak|dibayar|reimbursed
    disetujui_oleh  TEXT DEFAULT '',
    tanggal_setuju  TEXT,
    catatan_persetujuan TEXT DEFAULT '',
    catatan         TEXT DEFAULT '',
    tanggal_bayar   TEXT,
    dibayar         INTEGER NOT NULL DEFAULT 0,
    journal_entry_id INTEGER REFERENCES journal_entries(id) ON DELETE SET NULL,
    deleted_at      TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS idx_expense_company ON expenses(company_id, tanggal);
CREATE INDEX IF NOT EXISTS idx_expense_status ON expenses(company_id, status);

-- ======================================================================
-- BANK & REKONSILIASI
-- ======================================================================
CREATE TABLE IF NOT EXISTS bank_accounts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id      INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    kode            TEXT NOT NULL,
    nama            TEXT NOT NULL,             -- mis. "BCA Operasional"
    nama_bank       TEXT DEFAULT '',
    nomor_rekening  TEXT DEFAULT '',
    pemilik         TEXT DEFAULT '',
    akun_buku       TEXT NOT NULL DEFAULT '1002',  -- akun COA terkait
    saldo_awal      INTEGER NOT NULL DEFAULT 0,
    mata_uang       TEXT DEFAULT 'IDR',
    is_active       INTEGER NOT NULL DEFAULT 1,
    deleted_at      TEXT,
    UNIQUE(company_id, kode)
);

-- Transaksi menurut rekening koran / mutasi bank
CREATE TABLE IF NOT EXISTS bank_transactions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id      INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    bank_account_id INTEGER NOT NULL REFERENCES bank_accounts(id) ON DELETE CASCADE,
    tanggal         TEXT NOT NULL,
    uraian          TEXT DEFAULT '',
    referensi       TEXT DEFAULT '',
    debit           INTEGER NOT NULL DEFAULT 0,    -- uang masuk ke bank
    kredit          INTEGER NOT NULL DEFAULT 0,    -- uang keluar dari bank
    saldo           INTEGER NOT NULL DEFAULT 0,
    status          TEXT NOT NULL DEFAULT 'belum', -- belum|tercocok|dikecualikan
    journal_line_id INTEGER,
    journal_entry_id INTEGER REFERENCES journal_entries(id) ON DELETE SET NULL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS idx_banktrx ON bank_transactions(bank_account_id, tanggal);
CREATE INDEX IF NOT EXISTS idx_banktrx_status ON bank_transactions(company_id, status);

CREATE TABLE IF NOT EXISTS bank_reconciliations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id      INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    bank_account_id INTEGER NOT NULL REFERENCES bank_accounts(id) ON DELETE CASCADE,
    periode         TEXT NOT NULL,             -- YYYY-MM
    saldo_bank      INTEGER NOT NULL DEFAULT 0,
    saldo_buku      INTEGER NOT NULL DEFAULT 0,
    selisih         INTEGER NOT NULL DEFAULT 0,
    status          TEXT NOT NULL DEFAULT 'proses', -- proses|selesai
    catatan         TEXT DEFAULT '',
    dibuat_oleh     TEXT DEFAULT '',
    created_at      TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    UNIQUE(bank_account_id, periode)
);

-- ======================================================================
-- DIMENSI: COST CENTER, PROYEK, CABANG
-- ======================================================================
CREATE TABLE IF NOT EXISTS cost_centers (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id  INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    kode        TEXT NOT NULL,
    nama        TEXT NOT NULL,
    penanggung_jawab TEXT DEFAULT '',
    anggaran    INTEGER NOT NULL DEFAULT 0,
    is_active   INTEGER NOT NULL DEFAULT 1,
    UNIQUE(company_id, kode)
);

CREATE TABLE IF NOT EXISTS projects (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id  INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    kode        TEXT NOT NULL,
    nama        TEXT NOT NULL,
    partner_id  INTEGER REFERENCES partners(id) ON DELETE SET NULL,
    tanggal_mulai TEXT,
    tanggal_selesai TEXT,
    nilai_kontrak INTEGER NOT NULL DEFAULT 0,
    anggaran    INTEGER NOT NULL DEFAULT 0,
    status      TEXT NOT NULL DEFAULT 'berjalan', -- berjalan|selesai|batal
    catatan     TEXT DEFAULT '',
    UNIQUE(company_id, kode)
);

CREATE TABLE IF NOT EXISTS branches (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id  INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    kode        TEXT NOT NULL,
    nama        TEXT NOT NULL,
    alamat      TEXT DEFAULT '',
    kota        TEXT DEFAULT '',
    penanggung_jawab TEXT DEFAULT '',
    npwp        TEXT DEFAULT '',
    is_active   INTEGER NOT NULL DEFAULT 1,
    UNIQUE(company_id, kode)
);

-- ======================================================================
-- TATA KELOLA: IZIN, RIWAYAT PERUBAHAN, RECYCLE BIN, DOKUMEN
-- ======================================================================
CREATE TABLE IF NOT EXISTS permissions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    kode        TEXT NOT NULL UNIQUE,
    modul       TEXT NOT NULL,
    nama        TEXT NOT NULL,
    deskripsi   TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS role_permissions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    role        TEXT NOT NULL,
    permission_kode TEXT NOT NULL,
    UNIQUE(role, permission_kode)
);

CREATE TABLE IF NOT EXISTS user_permissions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    permission_kode TEXT NOT NULL,
    diizinkan   INTEGER NOT NULL DEFAULT 1,
    UNIQUE(user_id, permission_kode)
);

CREATE TABLE IF NOT EXISTS change_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    company_id  INTEGER,
    user_id     INTEGER,
    username    TEXT,
    tabel       TEXT NOT NULL,
    record_id   INTEGER NOT NULL,
    aksi        TEXT NOT NULL,        -- create|update|delete|restore|void
    field       TEXT DEFAULT '',
    nilai_lama  TEXT DEFAULT '',
    nilai_baru  TEXT DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_history ON change_history(tabel, record_id, ts DESC);

CREATE TABLE IF NOT EXISTS recycle_bin (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id  INTEGER NOT NULL,
    tabel       TEXT NOT NULL,
    record_id   INTEGER NOT NULL,
    judul       TEXT DEFAULT '',
    data_json   TEXT NOT NULL,
    dihapus_oleh TEXT DEFAULT '',
    ts          TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    dipulihkan  INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_recycle ON recycle_bin(company_id, tabel, dipulihkan);

CREATE TABLE IF NOT EXISTS documents (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id  INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    tabel       TEXT NOT NULL,
    record_id   INTEGER NOT NULL,
    nama_berkas TEXT NOT NULL,
    path_berkas TEXT NOT NULL,
    tipe        TEXT DEFAULT '',      -- invoice|faktur|kwitansi|kontrak|lainnya
    ukuran      INTEGER NOT NULL DEFAULT 0,
    versi       INTEGER NOT NULL DEFAULT 1,
    diunggah_oleh TEXT DEFAULT '',
    catatan     TEXT DEFAULT '',
    created_at  TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS idx_doc_ref ON documents(tabel, record_id);

-- ======================================================================
-- TRANSAKSI BERULANG (RECURRING)
-- ======================================================================
CREATE TABLE IF NOT EXISTS recurring_templates (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id      INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    nama            TEXT NOT NULL,
    tipe            TEXT NOT NULL,     -- jurnal|expense|invoice
    frekuensi       TEXT NOT NULL DEFAULT 'bulanan', -- harian|mingguan|bulanan|triwulanan|tahunan
    interval_hari   INTEGER NOT NULL DEFAULT 30,
    tanggal_mulai   TEXT NOT NULL,
    tanggal_berikut TEXT,
    tanggal_akhir   TEXT,
    jumlah_terbuat  INTEGER NOT NULL DEFAULT 0,
    maks_kali       INTEGER NOT NULL DEFAULT 0,   -- 0 = tak terbatas
    payload_json    TEXT NOT NULL DEFAULT '{}',
    aktif           INTEGER NOT NULL DEFAULT 1,
    terakhir_jalan  TEXT,
    deleted_at      TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

-- ======================================================================
-- TUTUP BUKU / PERIODE
-- ======================================================================
CREATE TABLE IF NOT EXISTS fiscal_periods (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id      INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    periode         TEXT NOT NULL,           -- YYYY-MM
    status          TEXT NOT NULL DEFAULT 'terbuka', -- terbuka|tertutup
    ditutup_oleh    TEXT DEFAULT '',
    tanggal_tutup   TEXT,
    laba_bersih     INTEGER NOT NULL DEFAULT 0,
    journal_entry_id INTEGER REFERENCES journal_entries(id) ON DELETE SET NULL,
    catatan         TEXT DEFAULT '',
    UNIQUE(company_id, periode)
);

-- ======================================================================
-- REMINDER (PENGINGAT JATUH TEMPO)
-- ======================================================================
CREATE TABLE IF NOT EXISTS reminders (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id      INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    tipe            TEXT NOT NULL,        -- piutang|utang|pajak|umum
    ref_tabel       TEXT DEFAULT '',
    ref_id          INTEGER,
    judul           TEXT NOT NULL,
    keterangan      TEXT DEFAULT '',
    tanggal_jatuh   TEXT NOT NULL,
    jumlah          INTEGER NOT NULL DEFAULT 0,
    status          TEXT NOT NULL DEFAULT 'aktif', -- aktif|selesai|diabaikan
    hari_ingat      INTEGER NOT NULL DEFAULT 7,
    created_at      TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS idx_reminder ON reminders(company_id, status, tanggal_jatuh);

-- ======================================================================
-- KONSOLIDASI (relasi entitas dalam satu grup)
-- ======================================================================
CREATE TABLE IF NOT EXISTS entity_groups (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nama        TEXT NOT NULL,
    catatan     TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS entity_group_members (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id    INTEGER NOT NULL REFERENCES entity_groups(id) ON DELETE CASCADE,
    company_id  INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    persentase_kepemilikan REAL NOT NULL DEFAULT 100.0,
    UNIQUE(group_id, company_id)
);

-- ======================================================================
-- AKUN KAS/BANK TAMBAHAN (multiple cash accounts)
-- ======================================================================
CREATE TABLE IF NOT EXISTS cash_accounts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id  INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    kode        TEXT NOT NULL,
    nama        TEXT NOT NULL,
    tipe        TEXT NOT NULL DEFAULT 'kas',  -- kas|bank|ewallet
    akun_buku   TEXT NOT NULL,
    bank_account_id INTEGER REFERENCES bank_accounts(id) ON DELETE SET NULL,
    saldo_awal  INTEGER NOT NULL DEFAULT 0,
    penanggung_jawab TEXT DEFAULT '',
    is_active   INTEGER NOT NULL DEFAULT 1,
    deleted_at  TEXT,
    UNIQUE(company_id, kode)
);

-- ======================================================================
-- KONFIGURASI JARINGAN LOKAL (LAN)
-- ======================================================================
CREATE TABLE IF NOT EXISTS lan_config (
    id          INTEGER PRIMARY KEY CHECK (id = 1),
    aktif       INTEGER NOT NULL DEFAULT 0,
    port        INTEGER NOT NULL DEFAULT 8787,
    host        TEXT DEFAULT '0.0.0.0',
    token       TEXT DEFAULT '',
    mode        TEXT NOT NULL DEFAULT 'server',  -- server|client
    server_host TEXT DEFAULT '',
    server_port INTEGER DEFAULT 8787,
    server_token TEXT DEFAULT '',
    last_sync   TEXT,
    catatan     TEXT DEFAULT ''
);

-- ======================================================================
-- VIEW BANTU: SALDO PIUTANG & UTANG
-- ======================================================================
CREATE VIEW IF NOT EXISTS v_ar_aging AS
SELECT
    i.company_id,
    i.id                AS invoice_id,
    i.nomor,
    i.tanggal,
    i.jatuh_tempo,
    COALESCE(i.pelanggan, p.nama, 'Tanpa Nama') AS pelanggan,
    p.id                AS partner_id,
    i.total,
    i.dibayar,
    i.sisa,
    i.status,
    CASE
        WHEN i.status IN ('lunas','batal') THEN 0
        ELSE CAST(julianday('now') - julianday(COALESCE(i.jatuh_tempo, i.tanggal)) AS INTEGER)
    END AS umur_hari,
    CASE
        WHEN i.status IN ('lunas','batal') THEN 'Lunas'
        WHEN julianday('now') - julianday(COALESCE(i.jatuh_tempo, i.tanggal)) <= 0 THEN 'Belum Jatuh Tempo'
        WHEN julianday('now') - julianday(COALESCE(i.jatuh_tempo, i.tanggal)) <= 30 THEN '1-30 hari'
        WHEN julianday('now') - julianday(COALESCE(i.jatuh_tempo, i.tanggal)) <= 60 THEN '31-60 hari'
        WHEN julianday('now') - julianday(COALESCE(i.jatuh_tempo, i.tanggal)) <= 90 THEN '61-90 hari'
        ELSE 'Di atas 90 hari'
    END AS kelompok_umur
FROM invoices i
LEFT JOIN partners p ON p.id = i.partner_id
WHERE i.deleted_at IS NULL;

CREATE VIEW IF NOT EXISTS v_ap_aging AS
SELECT
    b.company_id,
    b.id                AS bill_id,
    b.nomor,
    b.nomor_vendor,
    b.tanggal,
    b.jatuh_tempo,
    COALESCE(b.vendor, p.nama, 'Tanpa Nama') AS vendor,
    p.id                AS partner_id,
    b.total,
    b.dibayar,
    b.sisa,
    b.status,
    CASE
        WHEN b.status IN ('lunas','batal') THEN 0
        ELSE CAST(julianday('now') - julianday(COALESCE(b.jatuh_tempo, b.tanggal)) AS INTEGER)
    END AS umur_hari,
    CASE
        WHEN b.status IN ('lunas','batal') THEN 'Lunas'
        WHEN julianday('now') - julianday(COALESCE(b.jatuh_tempo, b.tanggal)) <= 0 THEN 'Belum Jatuh Tempo'
        WHEN julianday('now') - julianday(COALESCE(b.jatuh_tempo, b.tanggal)) <= 30 THEN '1-30 hari'
        WHEN julianday('now') - julianday(COALESCE(b.jatuh_tempo, b.tanggal)) <= 60 THEN '31-60 hari'
        WHEN julianday('now') - julianday(COALESCE(b.jatuh_tempo, b.tanggal)) <= 90 THEN '61-90 hari'
        ELSE 'Di atas 90 hari'
    END AS kelompok_umur
FROM bills b
LEFT JOIN partners p ON p.id = b.partner_id
WHERE b.deleted_at IS NULL;

CREATE VIEW IF NOT EXISTS v_stock_summary AS
SELECT
    sb.company_id,
    sb.product_id,
    pr.kode,
    pr.nama,
    pr.satuan,
    pr.metode_hpp,
    pr.stok_minimum,
    sb.warehouse_id,
    w.nama AS gudang,
    sb.qty,
        sb.nilai_total,
    CASE WHEN sb.qty <> 0 THEN CAST(sb.nilai_total / sb.qty AS INTEGER) ELSE 0 END AS hpp_satuan
FROM stock_balances sb
JOIN products pr ON pr.id = sb.product_id
JOIN warehouses w ON w.id = sb.warehouse_id
WHERE pr.deleted_at IS NULL;
"""


# ==========================================================================
# DDL FITUR PAJAK LANJUTAN
# ==========================================================================
DDL_PAJAK_LANJUT = """
-- Nomor Seri Faktur Pajak (NSFP) yang diberikan DJP kepada PKP.
CREATE TABLE IF NOT EXISTS nsfp (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id      INTEGER NOT NULL,
    tahun           INTEGER NOT NULL,
    nomor_awal      TEXT NOT NULL,
    nomor_akhir     TEXT NOT NULL,
    terpakai        INTEGER NOT NULL DEFAULT 0,
    catatan         TEXT NOT NULL DEFAULT '',
    created_at      TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

-- Faktur pajak keluaran dan masukan, terpisah dari invoice/bill.
CREATE TABLE IF NOT EXISTS faktur_pajak (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id      INTEGER NOT NULL,
    jenis           TEXT NOT NULL,        -- keluaran | masukan
    nomor_seri      TEXT NOT NULL DEFAULT '',
    tanggal         TEXT NOT NULL,
    lawan_nama      TEXT NOT NULL DEFAULT '',
    lawan_npwp      TEXT NOT NULL DEFAULT '',
    dpp             INTEGER NOT NULL DEFAULT 0,
    ppn             INTEGER NOT NULL DEFAULT 0,
    ppnbm           INTEGER NOT NULL DEFAULT 0,
    status          TEXT NOT NULL DEFAULT 'normal',  -- normal | pengganti | batal
    faktur_diganti  TEXT NOT NULL DEFAULT '',
    invoice_id      INTEGER,
    bill_id         INTEGER,
    keterangan      TEXT NOT NULL DEFAULT '',
    deleted_at      TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

-- Uang muka / panjar (DP) dari pelanggan dan ke pemasok.
CREATE TABLE IF NOT EXISTS uang_muka (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id      INTEGER NOT NULL,
    jenis           TEXT NOT NULL,        -- diterima | dibayar
    nomor           TEXT NOT NULL DEFAULT '',
    tanggal         TEXT NOT NULL,
    partner_id      INTEGER,
    nama_lawan      TEXT NOT NULL DEFAULT '',
    jumlah          INTEGER NOT NULL DEFAULT 0,
    terpakai        INTEGER NOT NULL DEFAULT 0,
    akun_kas        TEXT NOT NULL DEFAULT '1001',
    akun_uang_muka  TEXT NOT NULL DEFAULT '1105',
    keterangan      TEXT NOT NULL DEFAULT '',
    deleted_at      TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

-- Pemakaian uang muka pada invoice atau bill.
CREATE TABLE IF NOT EXISTS uang_muka_pakai (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    uang_muka_id    INTEGER NOT NULL,
    invoice_id      INTEGER,
    bill_id         INTEGER,
    jumlah          INTEGER NOT NULL DEFAULT 0,
    tanggal         TEXT NOT NULL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

-- Pajak daerah (PBJT/PB1) yang dipungut atas penjualan.
CREATE TABLE IF NOT EXISTS pajak_daerah (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id      INTEGER NOT NULL,
    jenis           TEXT NOT NULL,        -- makanan_minuman | hiburan | ...
    tanggal         TEXT NOT NULL,
    dpp             INTEGER NOT NULL DEFAULT 0,
    tarif           REAL NOT NULL DEFAULT 0.10,
    pajak           INTEGER NOT NULL DEFAULT 0,
    invoice_id      INTEGER,
    keterangan      TEXT NOT NULL DEFAULT '',
    deleted_at      TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

-- Bea meterai yang dipakai pada dokumen.
CREATE TABLE IF NOT EXISTS bea_meterai (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id      INTEGER NOT NULL,
    tanggal         TEXT NOT NULL,
    dokumen         TEXT NOT NULL DEFAULT '',
    nilai_dokumen   INTEGER NOT NULL DEFAULT 0,
    jumlah_berkas   INTEGER NOT NULL DEFAULT 1,
    tarif           INTEGER NOT NULL DEFAULT 10000,
    total           INTEGER NOT NULL DEFAULT 0,
    akun_beban      TEXT NOT NULL DEFAULT '6016',
    keterangan      TEXT NOT NULL DEFAULT '',
    deleted_at      TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

-- Kurs mata uang asing per tanggal.
CREATE TABLE IF NOT EXISTS kurs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id      INTEGER NOT NULL,
    mata_uang       TEXT NOT NULL,
    tanggal         TEXT NOT NULL,
    kurs            REAL NOT NULL DEFAULT 1,
    keterangan      TEXT NOT NULL DEFAULT '',
    UNIQUE(company_id, mata_uang, tanggal)
);

-- PPh Pasal 15 norma khusus.
CREATE TABLE IF NOT EXISTS pph15 (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id      INTEGER NOT NULL,
    jenis           TEXT NOT NULL,
    tanggal         TEXT NOT NULL,
    peredaran_bruto INTEGER NOT NULL DEFAULT 0,
    tarif           REAL NOT NULL DEFAULT 0,
    pph             INTEGER NOT NULL DEFAULT 0,
    keterangan      TEXT NOT NULL DEFAULT '',
    deleted_at      TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

-- Jurnal balik (reversing entry) untuk akrual akhir periode.
CREATE TABLE IF NOT EXISTS jurnal_balik (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id      INTEGER NOT NULL,
    entry_id        INTEGER NOT NULL,
    tanggal_balik   TEXT NOT NULL,
    entry_balik_id  INTEGER,
    sudah_dibuat    INTEGER NOT NULL DEFAULT 0,
    keterangan      TEXT NOT NULL DEFAULT '',
    created_at      TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
"""


    # ==========================================================================
# DAFTAR IZIN (PERMISSIONS) — granular per modul
# ==========================================================================
PERMISSIONS = [
    # (kode, modul, nama, deskripsi)
    ("dashboard.lihat", "Dashboard", "Lihat dashboard", "Melihat ringkasan dan KPI"),
    ("analisis.lihat", "Analisis", "Lihat analisis", "Menjalankan analisis kesehatan keuangan"),

    ("jurnal.lihat", "Jurnal", "Lihat jurnal", "Melihat daftar jurnal"),
    ("jurnal.buat", "Jurnal", "Buat jurnal", "Menambah entri jurnal"),
    ("jurnal.ubah", "Jurnal", "Ubah jurnal", "Mengubah entri jurnal"),
    ("jurnal.hapus", "Jurnal", "Hapus jurnal", "Menghapus entri jurnal"),

    ("penjualan.lihat", "Penjualan", "Lihat penjualan", "Melihat data penjualan"),
    ("penjualan.buat", "Penjualan", "Buat penjualan", "Membuat sales order & invoice"),
    ("penjualan.ubah", "Penjualan", "Ubah penjualan", "Mengubah invoice"),
    ("penjualan.hapus", "Penjualan", "Hapus penjualan", "Menghapus/void invoice"),
    ("penjualan.bayar", "Penjualan", "Terima pembayaran", "Mencatat penerimaan pembayaran"),

    ("pembelian.lihat", "Pembelian", "Lihat pembelian", "Melihat data pembelian"),
    ("pembelian.buat", "Pembelian", "Buat pembelian", "Membuat purchase order & bill"),
    ("pembelian.ubah", "Pembelian", "Ubah pembelian", "Mengubah bill"),
    ("pembelian.hapus", "Pembelian", "Hapus pembelian", "Menghapus bill"),
    ("pembelian.bayar", "Pembelian", "Bayar vendor", "Mencatat pembayaran ke vendor"),

    ("mitra.lihat", "Mitra", "Lihat mitra", "Melihat data customer/vendor"),
    ("mitra.kelola", "Mitra", "Kelola mitra", "Menambah/mengubah customer/vendor"),

    ("produk.lihat", "Produk", "Lihat produk", "Melihat data produk & stok"),
    ("produk.kelola", "Produk", "Kelola produk", "Menambah/mengubah produk"),
    ("stok.opname", "Produk", "Stock opname", "Melakukan penyesuaian stok"),

    ("biaya.lihat", "Biaya", "Lihat biaya", "Melihat data biaya"),
    ("biaya.ajukan", "Biaya", "Ajukan biaya", "Membuat pengajuan biaya"),
    ("biaya.setujui", "Biaya", "Setujui biaya", "Menyetujui pengajuan biaya"),
    ("biaya.bayar", "Biaya", "Bayar biaya", "Mencatat pembayaran biaya"),

    ("bank.lihat", "Bank", "Lihat bank", "Melihat rekening & mutasi bank"),
    ("bank.kelola", "Bank", "Kelola bank", "Menambah rekening & impor mutasi"),
    ("bank.rekonsiliasi", "Bank", "Rekonsiliasi bank", "Melakukan rekonsiliasi bank"),

    ("aset.lihat", "Aset", "Lihat aset", "Melihat data aset tetap"),
    ("aset.kelola", "Aset", "Kelola aset", "Menambah/mengubah aset"),
    ("aset.susut", "Aset", "Hitung penyusutan", "Menjalankan penyusutan"),

    ("payroll.lihat", "Payroll", "Lihat payroll", "Melihat data karyawan & payroll"),
    ("payroll.kelola", "Payroll", "Kelola payroll", "Menjalankan payroll"),
    ("karyawan.kelola", "Payroll", "Kelola karyawan", "Menambah/mengubah karyawan"),

    ("pajak.lihat", "Pajak", "Lihat pajak", "Melihat perhitungan pajak"),
    ("pajak.kelola", "Pajak", "Kelola pajak", "Mencatat pemotongan & setoran pajak"),

    ("laporan.lihat", "Laporan", "Lihat laporan", "Membuka laporan keuangan"),
    ("laporan.ekspor", "Laporan", "Ekspor laporan", "Mengekspor laporan ke Excel/PDF"),

    ("periode.tutup", "Periode", "Tutup buku", "Menutup periode akuntansi"),
    ("periode.buka", "Periode", "Buka buku", "Membuka kembali periode tertutup"),

    ("dimensi.kelola", "Dimensi", "Kelola dimensi", "Mengelola cost center, proyek, cabang"),

    ("pengguna.lihat", "Pengguna", "Lihat pengguna", "Melihat daftar pengguna"),
    ("pengguna.kelola", "Pengguna", "Kelola pengguna", "Menambah/mengubah pengguna & izin"),

    ("perusahaan.kelola", "Perusahaan", "Kelola perusahaan", "Mengubah profil perusahaan"),
    ("perusahaan.hapus", "Perusahaan", "Hapus perusahaan", "Menghapus data perusahaan"),

    ("backup.kelola", "Sistem", "Kelola cadangan", "Membuat & memulihkan cadangan"),
    ("audit.lihat", "Sistem", "Lihat audit", "Melihat jejak audit & riwayat perubahan"),
    ("recycle.kelola", "Sistem", "Kelola recycle bin", "Memulihkan data terhapus"),
    ("lan.kelola", "Sistem", "Kelola jaringan LAN", "Mengatur akses jaringan lokal"),
    ("impor.bulk", "Sistem", "Impor massal", "Mengimpor data secara massal"),
]

# Izin default per peran
ROLE_DEFAULT_PERMISSIONS = {
    "owner": ["*"],   # seluruh izin
    "admin": [
        "dashboard.lihat", "analisis.lihat",
        "jurnal.lihat", "jurnal.buat", "jurnal.ubah", "jurnal.hapus",
        "penjualan.lihat", "penjualan.buat", "penjualan.ubah", "penjualan.hapus",
        "penjualan.bayar",
        "pembelian.lihat", "pembelian.buat", "pembelian.ubah", "pembelian.hapus",
        "pembelian.bayar",
        "mitra.lihat", "mitra.kelola",
        "produk.lihat", "produk.kelola", "stok.opname",
        "biaya.lihat", "biaya.ajukan", "biaya.setujui", "biaya.bayar",
        "bank.lihat", "bank.kelola", "bank.rekonsiliasi",
        "aset.lihat", "aset.kelola", "aset.susut",
        "payroll.lihat", "payroll.kelola", "karyawan.kelola",
        "pajak.lihat", "pajak.kelola",
        "laporan.lihat", "laporan.ekspor",
        "periode.tutup", "periode.buka",
        "dimensi.kelola",
        "pengguna.lihat", "pengguna.kelola",
        "perusahaan.kelola",
        "backup.kelola", "audit.lihat", "recycle.kelola", "impor.bulk",
    ],
    "staff": [
        "dashboard.lihat",
        "jurnal.lihat", "jurnal.buat",
        "penjualan.lihat", "penjualan.buat", "penjualan.bayar",
        "pembelian.lihat", "pembelian.buat",
        "mitra.lihat", "mitra.kelola",
        "produk.lihat",
        "biaya.lihat", "biaya.ajukan",
        "bank.lihat",
        "aset.lihat",
        "payroll.lihat",
        "pajak.lihat",
        "laporan.lihat",
    ],
    "viewer": [
        "dashboard.lihat", "analisis.lihat",
        "jurnal.lihat", "penjualan.lihat", "pembelian.lihat",
        "mitra.lihat", "produk.lihat", "biaya.lihat", "bank.lihat",
        "aset.lihat", "payroll.lihat", "pajak.lihat", "laporan.lihat",
    ],
}
