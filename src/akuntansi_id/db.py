"""
AkunTuntas - Skema Database & Lapisan Akses Data
==================================================
Database: SQLite tunggal, tersimpan lokal di %LOCALAPPDATA%\\AkunTuntas\\
Tidak ada koneksi jaringan. Semua data milik pengguna sepenuhnya offline.

Prinsip desain:
- Setiap tabel transaksi memiliki `company_id` (multi-company dalam satu file DB).
- Jurnal mengikuti double-entry; constraint memastikan debit = kredit per bukti.
- Seluruh angka uang disimpan sebagai INTEGER rupiah (tidak ada floating point
  error pada akumulasi). Persentase disimpan sebagai REAL.
"""
from __future__ import annotations

import sqlite3
import threading
import logging
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Optional

from . import config

_local = threading.local()

SCHEMA_VERSION = 1


# ==========================================================================
# KONEKSI
# ==========================================================================
def _connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path), timeout=30, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA busy_timeout = 30000")
    return conn


def get_conn() -> sqlite3.Connection:
    """Koneksi per-thread (SQLite tidak aman dibagi antar-thread)."""
    key = f"conn_{config.DB_PATH}"
    conn = getattr(_local, key, None)
    if conn is None:
        config.ensure_dirs()
        conn = _connect(config.DB_PATH)
        setattr(_local, key, conn)
    return conn


# --------------------------------------------------------------------------
# PENJAGA KESEIMBANGAN JURNAL
# --------------------------------------------------------------------------
# Pemeriksaan di kode aplikasi sudah menolak jurnal yang tidak seimbang.
# Namun pemeriksaan itu hanya berlaku untuk jalur yang melewatinya. Bila ada
# jalur lain yang lupa memvalidasi, perbaikan data manual, atau impor dari
# alat lain yang menulis langsung ke tabel, jurnal tidak seimbang dapat masuk
# dan membuat neraca tidak seimbang tanpa ada yang menyadari.
#
# Karena itu pemeriksaan diulang di lapisan basis data, tepat sebelum sebuah
# transaksi disimpan. Di titik itu seluruh baris jurnal sudah selesai
# ditulis, sehingga jurnal yang sah tidak akan tertolak hanya karena
# barisnya belum lengkap.
#
# SQLite tidak mengenal pemeriksaan yang ditunda sampai transaksi selesai
# seperti pada basis data lain, jadi pemeriksaan ini dijalankan sendiri
# oleh fungsi tx() sebelum COMMIT.
#
# Penandanya memakai trigger sementara pada tabel jurnal. Trigger ini
# mencatat bahwa jurnal sudah berubah, tanpa memandang jalur mana yang
# menulisnya. Dengan begitu pemeriksaan menyeluruh hanya dijalankan pada
# transaksi yang benar benar menyentuh jurnal, dan tidak diulang pada
# transaksi lain.
DDL_PENANDA_JURNAL = """
CREATE TEMP TABLE IF NOT EXISTS _jurnal_berubah (
    id INTEGER PRIMARY KEY CHECK (id = 1)
);
CREATE TEMP TRIGGER IF NOT EXISTS _trg_jurnal_is
AFTER INSERT ON journal_lines BEGIN
    INSERT OR REPLACE INTO _jurnal_berubah(id) VALUES(1);
END;
CREATE TEMP TRIGGER IF NOT EXISTS _trg_jurnal_us
AFTER UPDATE ON journal_lines BEGIN
    INSERT OR REPLACE INTO _jurnal_berubah(id) VALUES(1);
END;
CREATE TEMP TRIGGER IF NOT EXISTS _trg_jurnal_ds
AFTER DELETE ON journal_lines BEGIN
    INSERT OR REPLACE INTO _jurnal_berubah(id) VALUES(1);
END;
CREATE TEMP TRIGGER IF NOT EXISTS _trg_jurnal_ie
AFTER INSERT ON journal_entries BEGIN
    INSERT OR REPLACE INTO _jurnal_berubah(id) VALUES(1);
END;
CREATE TEMP TRIGGER IF NOT EXISTS _trg_jurnal_ue
AFTER UPDATE ON journal_entries BEGIN
    INSERT OR REPLACE INTO _jurnal_berubah(id) VALUES(1);
END;
CREATE TEMP TRIGGER IF NOT EXISTS _trg_jurnal_de
AFTER DELETE ON journal_entries BEGIN
    INSERT OR REPLACE INTO _jurnal_berubah(id) VALUES(1);
END;
"""


def pasang_penanda_jurnal(conn) -> None:
    """Pasang trigger penanda perubahan jurnal pada satu koneksi."""
    try:
        conn.executescript(DDL_PENANDA_JURNAL)
    except Exception as e:
        logging.getLogger("akuntansiid").warning(
            "Penanda perubahan jurnal gagal dipasang: %s", e)


def _periksa_keseimbangan(conn) -> None:
    """
    Batalkan transaksi bila ada bukti jurnal yang tidak seimbang.

    Pemeriksaan ini menutup celah yang tidak tertangkap pemeriksaan di kode
    aplikasi: jalur tulis langsung ke tabel, perbaikan data manual, dan
    impor dari alat lain. Dijalankan tepat sebelum transaksi disimpan, saat
    seluruh baris jurnal sudah selesai ditulis.

    Pesannya menyebut nomor bukti yang bermasalah supaya pengguna tahu
    bagian mana yang harus diperbaiki, bukan hanya bahwa ada yang salah.
    """
    # Hanya diperiksa bila transaksi ini benar benar menyentuh jurnal.
    try:
        berubah = conn.execute(
            "SELECT COUNT(*) FROM _jurnal_berubah").fetchone()[0]
    except Exception:
        # Penanda belum terpasang, jadi pemeriksaan dilewati.
        return
    if not berubah:
        return

    temuan = conn.execute(
        """SELECT je.id, je.no_bukti,
                  COALESCE(SUM(jl.debit), 0) AS total_debit,
                  COALESCE(SUM(jl.kredit), 0) AS total_kredit,
                  COUNT(jl.id) AS jumlah_baris
           FROM journal_entries je
           LEFT JOIN journal_lines jl ON jl.entry_id = je.id
           GROUP BY je.id
           HAVING total_debit <> total_kredit OR jumlah_baris < 2""").fetchall()

    # Penanda dibersihkan supaya transaksi berikutnya mulai dari keadaan
    # bersih. Bila pemeriksaan gagal, rollback akan mengembalikannya.
    conn.execute("DELETE FROM _jurnal_berubah")

    if not temuan:
        return

    rincian = []
    for t in temuan[:3]:
        selisih = int(t["total_debit"]) - int(t["total_kredit"])
        rincian.append(
            f"{t['no_bukti']} (debit {int(t['total_debit']):,} "
            f"vs kredit {int(t['total_kredit']):,}, selisih {selisih:,})")
    sisa = len(temuan) - len(rincian)
    pesan = ("Jurnal tidak seimbang sehingga tidak dapat disimpan: "
             + "; ".join(rincian))
    if sisa > 0:
        pesan += f"; dan {sisa} bukti lain"
    raise ValueError(pesan)


@contextmanager
def tx():
    """
    Transaksi atomik. Rollback otomatis bila ada exception.

    Mendukung PEMANGGILAN BERSARANG (nested): bila sudah berada di dalam
    transaksi, blok dalam hanya ikut transaksi luar (savepoint tidak
    diperlukan karena SQLite menangani ini secara implisit di level
    koneksi). Ini memungkinkan fungsi tingkat tinggi seperti
    services.simpan_penjualan() memanggil acc.simpan_jurnal() yang juga
    membuka transaksi.
    """
    conn = get_conn()
    if getattr(_local, "tx_depth", 0) > 0:
        # sudah di dalam transaksi — cukup teruskan koneksi yang sama
        _local.tx_depth += 1
        try:
            yield conn
        finally:
            _local.tx_depth -= 1
        return

    conn.execute("BEGIN IMMEDIATE")
    _local.tx_depth = 1
    try:
        yield conn
        _periksa_keseimbangan(conn)
        conn.execute("COMMIT")
    except Exception:
        try:
            conn.execute("ROLLBACK")
        except Exception:
            pass
        raise
    finally:
        _local.tx_depth = 0


def q(sql: str, params: Iterable = ()) -> list[sqlite3.Row]:
    return get_conn().execute(sql, tuple(params)).fetchall()


def q1(sql: str, params: Iterable = ()) -> Optional[sqlite3.Row]:
    return get_conn().execute(sql, tuple(params)).fetchone()


def scalar(sql: str, params: Iterable = (), default: Any = 0) -> Any:
    row = q1(sql, params)
    if row is None or row[0] is None:
        return default
    return row[0]


def ex(sql: str, params: Iterable = ()) -> sqlite3.Cursor:
    """
    Jalankan satu perintah SQL.

    Setiap perintah yang mengubah isi basis data menaikkan penanda revisi.
    Halaman yang sedang terbuka memakai penanda itu untuk mengetahui bahwa
    datanya sudah berubah dan perlu dimuat ulang, tanpa perlu memuat ulang
    setiap kali menu dibuka.
    """
    _periksa_tanggal(sql, params)
    kursor = get_conn().execute(sql, tuple(params))

    # Perintah yang mengubah data dikenali dari katanya. Pembacaan tidak
    # menghitung, supaya penanda hanya berubah saat isinya benar-benar
    # berbeda.
    awal = sql.lstrip()[:6].upper()
    if awal.startswith(("INSERT", "UPDATE", "DELETE", "REPLAC")):
        _naikkan_revisi()

    return kursor


# Nama kolom yang memuat tanggal. Nilai pada kolom ini harus berupa tanggal
# yang benar benar ada pada kalender.
KOLOM_TANGGAL = (
    "tanggal", "tanggal_bayar", "tanggal_balik", "tanggal_jatuh",
    "tanggal_perolehan", "tanggal_pendirian", "tanggal_npwp",
    "tanggal_mulai", "tanggal_akhir", "tanggal_selesai", "tanggal_kontrak",
    "tanggal_faktur", "tanggal_bayar_pajak", "masa_awal", "masa_akhir",
    "jatuh_tempo", "berlaku_sampai",
)


def _periksa_tanggal(sql: str, params: Iterable) -> None:
    """
    Tolak penulisan tanggal yang tidak ada pada kalender.

    Pemeriksaan ini diletakkan di lapisan basis data, bukan di tiap fungsi
    penyimpanan, karena fungsi penyimpanan jumlahnya puluhan dan mudah ada
    yang terlewat. Semua penulisan melewati fungsi ini.

    Hanya nilai yang berbentuk mirip tanggal yang diperiksa, yaitu teks
    sepuluh huruf dengan tanda hubung pada posisi yang benar. Nilai lain
    dibiarkan, karena kolom tanggal kadang diisi teks kosong untuk data
    yang belum lengkap.
    """
    if not params:
        return

    teks_sql = sql.lower()
    nama_kolom = [k for k in KOLOM_TANGGAL if k in teks_sql]
    if not nama_kolom:
        return

    for nilai in params:
        if not isinstance(nilai, str):
            continue
        bersih = nilai.strip()
        # Hanya bentuk tanggal yang diperiksa.
        if len(bersih) != 10 or bersih[4] != "-" or bersih[7] != "-":
            continue
        bagian = bersih.split("-")
        if not all(b.isdigit() and len(b) == n
                   for b, n in zip(bagian, (4, 2, 2))):
            continue
        try:
            from datetime import date
            date(int(bagian[0]), int(bagian[1]), int(bagian[2]))
        except ValueError:
            raise ValueError(
                f"Tanggal {bersih} tidak ada pada kalender. "
                "Periksa kembali bulan dan harinya.") from None


# Penanda revisi data. Dipakai antarmuka untuk mengetahui bahwa isi basis
# data sudah berubah sejak halaman terakhir dimuat.
_revisi = 0


def revisi_data() -> int:
    """Angka yang berubah setiap kali isi basis data berubah."""
    return _revisi


def _naikkan_revisi() -> None:
    global _revisi
    _revisi += 1


# ==========================================================================
# SKEMA
# ==========================================================================
DDL = """
-- ------------------------------------------------------------------ users
CREATE TABLE IF NOT EXISTS users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    username        TEXT NOT NULL UNIQUE COLLATE NOCASE,
    full_name       TEXT NOT NULL DEFAULT '',
    email           TEXT NOT NULL DEFAULT '',
    jabatan         TEXT NOT NULL DEFAULT '',
    password_hash   TEXT NOT NULL,
    salt            TEXT NOT NULL,
    role            TEXT NOT NULL DEFAULT 'owner',   -- owner | admin | staff | viewer
    app_mode        TEXT NOT NULL DEFAULT 'beginner', -- beginner | expert
    mode_dipilih    INTEGER NOT NULL DEFAULT 0,      -- 1 = sudah pernah memilih
    is_active       INTEGER NOT NULL DEFAULT 1,
    must_change_pw  INTEGER NOT NULL DEFAULT 1,
    failed_attempts INTEGER NOT NULL DEFAULT 0,
    locked_until    TEXT,
    last_login      TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    updated_at      TEXT
);

CREATE TABLE IF NOT EXISTS audit_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    user_id     INTEGER,
    username    TEXT,
    company_id  INTEGER,
    action      TEXT NOT NULL,
    entity      TEXT,
    entity_id   TEXT,
    detail      TEXT,
    ip_or_host  TEXT,
    kategori    TEXT NOT NULL DEFAULT 'data'
);
CREATE INDEX IF NOT EXISTS idx_audit_ts ON audit_log(ts DESC);

-- --------------------------------------------------------------- companies
CREATE TABLE IF NOT EXISTS companies (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    nama                TEXT NOT NULL,
    bentuk              TEXT NOT NULL DEFAULT 'umkm_op',
    npwp                TEXT DEFAULT '',
    nik                 TEXT DEFAULT '',
    alamat              TEXT DEFAULT '',
    kota                TEXT DEFAULT '',
    kode_pos            TEXT DEFAULT '',
    telepon             TEXT DEFAULT '',
    email               TEXT DEFAULT '',
    nama_pemilik        TEXT DEFAULT '',
    tanggal_pendirian   TEXT,
    tanggal_npwp        TEXT,
    tahun_buku_awal     TEXT,
    tahun_buku_akhir    TEXT,
    status_pkp          INTEGER NOT NULL DEFAULT 0,
    nomor_pkp           TEXT DEFAULT '',
    tarif_ppn           REAL NOT NULL DEFAULT 0.11,
    skema_pph           TEXT NOT NULL DEFAULT 'pasal31e',
    final_eligible      INTEGER NOT NULL DEFAULT 0,
    pkp_terdaftar_tgl   TEXT,
    omzet_prev_year     INTEGER NOT NULL DEFAULT 0,
    logo_path           TEXT DEFAULT '',
    mata_uang           TEXT NOT NULL DEFAULT 'IDR',
    is_active           INTEGER NOT NULL DEFAULT 1,
    created_at          TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    updated_at          TEXT
);

-- -------------------------------------------------------- chart of accounts
CREATE TABLE IF NOT EXISTS accounts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id      INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    kode            TEXT NOT NULL,
    nama            TEXT NOT NULL,
    tipe            TEXT NOT NULL,        -- Aset|Liabilitas|Ekuitas|Pendapatan|Beban
    grup_lr         TEXT DEFAULT '',      -- Pendapatan Usaha|HPP|Beban Operasional|...
    baris_neraca    TEXT DEFAULT '',      -- Kas & Bank|Piutang Usaha|...
    normal          TEXT NOT NULL,        -- Debit | Kredit
    perlakuan_fiskal TEXT NOT NULL DEFAULT 'Deductible/Taxable',
    saldo_awal      INTEGER NOT NULL DEFAULT 0,
    saldo_awal_debit  INTEGER NOT NULL DEFAULT 0,
    saldo_awal_kredit INTEGER NOT NULL DEFAULT 0,
    deskripsi       TEXT DEFAULT '',      -- penjelasan untuk pengguna baru
    is_kas_bank     INTEGER NOT NULL DEFAULT 0,
    is_active       INTEGER NOT NULL DEFAULT 1,
    UNIQUE(company_id, kode)
);

-- ------------------------------------------------------------------- journal
CREATE TABLE IF NOT EXISTS journal_entries (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id      INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    tanggal         TEXT NOT NULL,
    no_bukti        TEXT NOT NULL,
    keterangan      TEXT NOT NULL DEFAULT '',
    sumber          TEXT NOT NULL DEFAULT 'manual', -- manual|penjualan|pembelian|payroll|aset|penyesuaian|penutup
    ref_id          INTEGER,
    created_by      INTEGER,
    posted          INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS idx_je_company_date ON journal_entries(company_id, tanggal);
CREATE INDEX IF NOT EXISTS idx_je_bukti ON journal_entries(company_id, no_bukti);

CREATE TABLE IF NOT EXISTS journal_lines (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_id        INTEGER NOT NULL REFERENCES journal_entries(id) ON DELETE CASCADE,
    company_id      INTEGER NOT NULL,
    kode_akun       TEXT NOT NULL,
    nama_akun       TEXT NOT NULL DEFAULT '',
    debit           INTEGER NOT NULL DEFAULT 0,
    kredit          INTEGER NOT NULL DEFAULT 0,
    lawan_transaksi TEXT DEFAULT '',
    npwp_nik        TEXT DEFAULT '',
    ref_pajak       TEXT DEFAULT '',
    catatan         TEXT DEFAULT '',
    CHECK (debit >= 0 AND kredit >= 0),
    CHECK (NOT (debit > 0 AND kredit > 0))
);
CREATE INDEX IF NOT EXISTS idx_jl_entry ON journal_lines(entry_id);
CREATE INDEX IF NOT EXISTS idx_jl_akun ON journal_lines(company_id, kode_akun);

-- -------------------------------------------------------------- subledgers
CREATE TABLE IF NOT EXISTS sales (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id          INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    tanggal             TEXT NOT NULL,
    no_invoice          TEXT NOT NULL,
    pelanggan           TEXT DEFAULT '',
    npwp_nik            TEXT DEFAULT '',
    keterangan          TEXT DEFAULT '',
    nilai_penjualan     INTEGER NOT NULL DEFAULT 0,   -- DPP komersial (sebelum PPN)
    jenis_ppn           TEXT NOT NULL DEFAULT 'Non-PKP/Tidak Dipungut',
    dpp_faktur          INTEGER NOT NULL DEFAULT 0,
    tarif_efektif       REAL NOT NULL DEFAULT 0,
    ppn_keluaran        INTEGER NOT NULL DEFAULT 0,
    total_tagihan       INTEGER NOT NULL DEFAULT 0,
    akun_piutang        TEXT DEFAULT '1101',
    akun_pendapatan     TEXT DEFAULT '4001',
    lunas               INTEGER NOT NULL DEFAULT 0,
    tanggal_bayar       TEXT,
    journal_entry_id    INTEGER REFERENCES journal_entries(id) ON DELETE SET NULL,
    catatan             TEXT DEFAULT '',
    created_at          TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS idx_sales_company ON sales(company_id, tanggal);

CREATE TABLE IF NOT EXISTS purchases (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id          INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    tanggal             TEXT NOT NULL,
    no_invoice          TEXT NOT NULL,
    vendor              TEXT DEFAULT '',
    npwp_nik            TEXT DEFAULT '',
    keterangan          TEXT DEFAULT '',
    jenis               TEXT NOT NULL DEFAULT 'Beban',   -- Beban|Persediaan|Aset Tetap
    nilai_sebelum_ppn   INTEGER NOT NULL DEFAULT 0,
    jenis_ppn           TEXT NOT NULL DEFAULT 'Non-PKP/Tidak Dipungut',
    dpp_faktur          INTEGER NOT NULL DEFAULT 0,
    tarif_efektif       REAL NOT NULL DEFAULT 0,
    ppn_masukan         INTEGER NOT NULL DEFAULT 0,
    dapat_dikreditkan   INTEGER NOT NULL DEFAULT 0,
    ppn_dikreditkan     INTEGER NOT NULL DEFAULT 0,
    total_bayar         INTEGER NOT NULL DEFAULT 0,
    akun_beban          TEXT DEFAULT '6008',
    akun_utang          TEXT DEFAULT '2001',
    dibayar             INTEGER NOT NULL DEFAULT 0,
    tanggal_bayar       TEXT,
    journal_entry_id    INTEGER REFERENCES journal_entries(id) ON DELETE SET NULL,
    catatan             TEXT DEFAULT '',
    created_at          TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS idx_purch_company ON purchases(company_id, tanggal);

CREATE TABLE IF NOT EXISTS fixed_assets (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id          INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    kode_aset           TEXT NOT NULL,
    nama_aset           TEXT NOT NULL,
    tanggal_perolehan   TEXT NOT NULL,
    harga_perolehan     INTEGER NOT NULL DEFAULT 0,
    residu_komersial    INTEGER NOT NULL DEFAULT 0,
    umur_komersial      INTEGER NOT NULL DEFAULT 5,
    kelompok_fiskal     TEXT NOT NULL DEFAULT 'Kelompok 1',
    metode_fiskal       TEXT NOT NULL DEFAULT 'Garis Lurus',
    nbv_fiskal_awal     INTEGER NOT NULL DEFAULT 0,
    akun_aset           TEXT DEFAULT '1201',
    akun_akum           TEXT DEFAULT '1202',
    akun_beban          TEXT DEFAULT '6007',
    tanggal_pelepasan   TEXT,
    nilai_pelepasan     INTEGER DEFAULT 0,
    catatan             TEXT DEFAULT '',
    created_at          TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS depreciation_entries (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id      INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    asset_id        INTEGER NOT NULL REFERENCES fixed_assets(id) ON DELETE CASCADE,
    tahun           INTEGER NOT NULL,
    bulan           INTEGER NOT NULL DEFAULT 12,
    penyusutan_komersial INTEGER NOT NULL DEFAULT 0,
    penyusutan_fiskal    INTEGER NOT NULL DEFAULT 0,
    nbv_fiskal_akhir     INTEGER NOT NULL DEFAULT 0,
    journal_entry_id     INTEGER REFERENCES journal_entries(id) ON DELETE SET NULL,
    UNIQUE(asset_id, tahun)
);

CREATE TABLE IF NOT EXISTS employees (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id      INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    nik_npwp        TEXT DEFAULT '',
    nama            TEXT NOT NULL,
    jabatan         TEXT DEFAULT '',
    status_ptkp     TEXT NOT NULL DEFAULT 'TK/0',
    gaji_pokok      INTEGER NOT NULL DEFAULT 0,
    tunjangan_tetap INTEGER NOT NULL DEFAULT 0,
    bpjs_kes        INTEGER NOT NULL DEFAULT 1,
    bpjs_jht        INTEGER NOT NULL DEFAULT 1,
    bpjs_jp         INTEGER NOT NULL DEFAULT 1,
    bpjs_jkk_rate   REAL NOT NULL DEFAULT 0.0024,
    tanggal_masuk   TEXT,
    tanggal_keluar  TEXT,
    is_active       INTEGER NOT NULL DEFAULT 1,
    catatan         TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS payroll_runs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id      INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    masa            TEXT NOT NULL,             -- YYYY-MM
    status          TEXT NOT NULL DEFAULT 'draft',  -- draft|posted
    total_bruto     INTEGER NOT NULL DEFAULT 0,
    total_potongan  INTEGER NOT NULL DEFAULT 0,
    total_thp       INTEGER NOT NULL DEFAULT 0,
    total_beban     INTEGER NOT NULL DEFAULT 0,
    journal_entry_id INTEGER REFERENCES journal_entries(id) ON DELETE SET NULL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    UNIQUE(company_id, masa)
);

CREATE TABLE IF NOT EXISTS payroll_items (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id          INTEGER NOT NULL REFERENCES payroll_runs(id) ON DELETE CASCADE,
    employee_id     INTEGER REFERENCES employees(id) ON DELETE SET NULL,
    nama            TEXT NOT NULL,
    nik_npwp        TEXT DEFAULT '',
    status_ptkp     TEXT DEFAULT 'TK/0',
    gaji_pokok      INTEGER NOT NULL DEFAULT 0,
    tunjangan       INTEGER NOT NULL DEFAULT 0,
    bonus           INTEGER NOT NULL DEFAULT 0,
    bruto           INTEGER NOT NULL DEFAULT 0,
    bpjs_karyawan   INTEGER NOT NULL DEFAULT 0,
    bpjs_perusahaan INTEGER NOT NULL DEFAULT 0,
    pph21           INTEGER NOT NULL DEFAULT 0,
    potongan_lain   INTEGER NOT NULL DEFAULT 0,
    take_home_pay   INTEGER NOT NULL DEFAULT 0,
    beban_perusahaan INTEGER NOT NULL DEFAULT 0,
    metode_pph21    TEXT DEFAULT 'TER'
);

CREATE TABLE IF NOT EXISTS tax_records (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id      INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    tanggal         TEXT NOT NULL,
    masa            TEXT DEFAULT '',
    kode_pajak      TEXT NOT NULL,
    jenis           TEXT NOT NULL DEFAULT '',
    arah            TEXT NOT NULL DEFAULT 'Potong',   -- Potong|Pungut|Setor|Kredit
    dpp             INTEGER NOT NULL DEFAULT 0,
    tarif_default   REAL NOT NULL DEFAULT 0,
    tarif_override  REAL,
    tarif_dipakai   REAL NOT NULL DEFAULT 0,
    pajak           INTEGER NOT NULL DEFAULT 0,
    kredit_pph_badan INTEGER NOT NULL DEFAULT 0,
    tanggal_bayar   TEXT,
    no_bupot        TEXT DEFAULT '',
    status          TEXT NOT NULL DEFAULT 'Terutang',  -- Terutang|Disetor|Dilaporkan
    journal_entry_id INTEGER REFERENCES journal_entries(id) ON DELETE SET NULL,
    catatan         TEXT DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_tax_company ON tax_records(company_id, tanggal);

CREATE TABLE IF NOT EXISTS tax_payments (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id      INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    jenis_pajak     TEXT NOT NULL,        -- PPN|PPh21|PPh23|PPh4|PPh25|PPhBadan|PPhFinal
    masa            TEXT NOT NULL,        -- YYYY-MM atau YYYY
    tanggal_bayar   TEXT NOT NULL,
    jumlah          INTEGER NOT NULL DEFAULT 0,
    ntpn            TEXT DEFAULT '',
    cara_bayar      TEXT DEFAULT 'e-Billing',
    catatan         TEXT DEFAULT '',
    journal_entry_id INTEGER REFERENCES journal_entries(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS fiscal_adjustments (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id      INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    tahun           INTEGER NOT NULL,
    uraian          TEXT NOT NULL,
    nilai           INTEGER NOT NULL DEFAULT 0,
    jenis           TEXT NOT NULL DEFAULT 'Positif',   -- Positif|Negatif
    dokumen         TEXT DEFAULT '',
    catatan         TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS checklist_items (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id      INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    frekuensi       TEXT NOT NULL DEFAULT 'Bulanan',
    area            TEXT NOT NULL DEFAULT '',
    checklist       TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'Belum',    -- Belum|Proses|Selesai|N/A
    pic             TEXT DEFAULT '',
    masa            TEXT DEFAULT '',
    catatan         TEXT DEFAULT '',
    urutan          INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS settings (
    key     TEXT PRIMARY KEY,
    value   TEXT
);

CREATE TABLE IF NOT EXISTS backups (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    path        TEXT NOT NULL,
    size_bytes  INTEGER NOT NULL DEFAULT 0,
    keterangan  TEXT DEFAULT ''
);

-- View bantu: saldo per akun per perusahaan
CREATE VIEW IF NOT EXISTS v_account_balances AS
SELECT
    a.company_id,
    a.kode,
    a.nama,
    a.tipe,
    a.grup_lr,
    a.baris_neraca,
    a.normal,
    a.perlakuan_fiskal,
    a.saldo_awal,
    COALESCE(SUM(CASE WHEN jl.debit  > 0 THEN jl.debit  ELSE 0 END), 0) AS total_debit,
    COALESCE(SUM(CASE WHEN jl.kredit > 0 THEN jl.kredit ELSE 0 END), 0) AS total_kredit,
    a.saldo_awal
      + COALESCE(SUM(jl.debit), 0)
      - COALESCE(SUM(jl.kredit), 0) AS saldo_debit_minus_kredit
FROM accounts a
LEFT JOIN journal_lines jl ON jl.company_id = a.company_id AND jl.kode_akun = a.kode
GROUP BY a.company_id, a.kode;
"""


def init_db() -> None:
    config.ensure_dirs()
    conn = get_conn()

    # Skema dasar lebih dulu, lalu migrasi kolom, BARU skema lanjutan.
    #
    # Urutan ini penting. Skema lanjutan memuat view yang membaca kolom hasil
    # migrasi (mis. v_kontrak_aktif membaca nilai_jasa). Bila skema lanjutan
    # dijalankan lebih dulu, view itu gagal dibuat pada basis data lama dan
    # kegagalannya menular ke seluruh pemuatan skema — tabel lain ikut tidak
    # terbuat. Kolomnya harus ada lebih dulu.
    conn.executescript(DDL)
    _jalankan_migrasi(conn)

    # Import ditulis statis, bukan lewat importlib: PyInstaller hanya mengenali
    # import statis saat membundel, sehingga modul yang diimpor secara dinamis
    # tidak ikut terbawa ke dalam EXE.
    from .schema_ext import DDL_EXT, DDL_PAJAK_LANJUT
    from .schema_kontrak import SKEMA_KONTRAK

    for nama, isi in (("DDL_EXT", DDL_EXT),
                      ("DDL_PAJAK_LANJUT", DDL_PAJAK_LANJUT),
                      ("SKEMA_KONTRAK", SKEMA_KONTRAK)):
        try:
            conn.executescript(isi)
        except Exception as e:
            import logging
            logging.getLogger("akuntansiid").warning(
                "Skema %s gagal dimuat: %s", nama, e)

    # Index yang bergantung pada kolom migrasi dibuat setelah skema lanjutan,
    # supaya view dan index sama-sama melihat kolom yang sudah lengkap.
    for nama, tabel, kolom in INDEX_TAMBAHAN:
        try:
            conn.execute(f"CREATE INDEX IF NOT EXISTS {nama} "
                         f"ON {tabel}({kolom})")
        except Exception:
            continue

    # Daftar izin diisi setelah tabelnya dibuat oleh skema lanjutan.
    _isi_izin(conn)

    conn.execute(
        "INSERT INTO settings(key,value) VALUES('schema_version',?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (str(SCHEMA_VERSION),),
    )
    conn.execute(
        "INSERT INTO settings(key,value) VALUES('app_version',?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (config.APP_VERSION,),
    )

    # Penanda perubahan jurnal dipasang paling akhir, setelah tabel jurnal
    # benar benar ada. Bila dipasang lebih awal, pembuatannya gagal karena
    # tabel yang dirujuknya belum terbentuk.
    pasang_penanda_jurnal(conn)


# Kolom yang ditambahkan setelah versi awal. Basis data lama akan
# dilengkapi otomatis saat aplikasi dibuka.
KOLOM_TAMBAHAN = [
    ("users", "jabatan", "TEXT NOT NULL DEFAULT ''"),
    ("expenses", "catatan", "TEXT DEFAULT ''"),
    ("fixed_assets", "catatan", "TEXT DEFAULT ''"),
    ("partners", "catatan", "TEXT DEFAULT ''"),
    ("products", "catatan", "TEXT DEFAULT ''"),
    ("users", "mode_dipilih", "INTEGER NOT NULL DEFAULT 0"),
    ("kontrak", "nilai_jasa", "INTEGER NOT NULL DEFAULT 0"),
    ("audit_log", "kategori", "TEXT NOT NULL DEFAULT 'data'"),
]

# Index yang bergantung pada kolom hasil migrasi di atas. Dibuat setelah
# kolomnya ada, bukan bersama tabel, supaya basis data lama tidak gagal.
INDEX_TAMBAHAN = [
    ("idx_audit_kategori", "audit_log", "kategori, ts DESC"),
]


def _jalankan_migrasi(conn) -> None:
    for tabel, kolom, definisi in KOLOM_TAMBAHAN:
        try:
            ada = conn.execute(
                f"SELECT COUNT(*) FROM pragma_table_info('{tabel}') "
                f"WHERE name=?", (kolom,)).fetchone()[0]
            if not ada:
                conn.execute(f"ALTER TABLE {tabel} ADD COLUMN {kolom} {definisi}")
        except Exception:
            continue


def _isi_izin(conn) -> None:
    """
    Isi daftar izin dan izin bawaan tiap peran.

    Dijalankan setelah skema lanjutan karena tabel permissions dan
    role_permissions dibuat di sana. Bila dijalankan lebih dulu, tabelnya
    belum ada sehingga daftar izin tetap kosong dan dialog hak akses
    pengguna tidak menampilkan apa pun.
    """
    try:
        jumlah = conn.execute("SELECT COUNT(*) FROM permissions").fetchone()[0]
        if jumlah == 0:
            from .schema_ext import PERMISSIONS, ROLE_DEFAULT_PERMISSIONS
            for kode, modul, nama, deskripsi in PERMISSIONS:
                conn.execute(
                    """INSERT INTO permissions(kode, modul, nama, deskripsi)
                       VALUES(?,?,?,?) ON CONFLICT(kode) DO NOTHING""",
                    (kode, modul, nama, deskripsi))
            for role, izin in ROLE_DEFAULT_PERMISSIONS.items():
                for k in izin:
                    if k == "*":
                        continue
                    conn.execute(
                        """INSERT INTO role_permissions(role, permission_kode)
                           VALUES(?,?) ON CONFLICT(role, permission_kode)
                           DO NOTHING""", (role, k))
    except Exception:
        pass


# ==========================================================================
# AUDIT LOG
# ==========================================================================
# Jejak aktivitas dibagi dua jenis yang berbeda keperluannya:
#
#   keamanan      : percobaan masuk dan keluar aplikasi. Dipakai untuk
#                   memeriksa siapa yang mengakses data dan kapan — termasuk
#                   percobaan yang gagal, yang menandakan upaya menerobos.
#   data          : pembuatan, perubahan, dan penghapusan data pembukuan.
#                   Dipakai menelusuri asal sebuah angka bila ada selisih.
#   administrasi  : pengelolaan pengguna, perusahaan, dan pengaturan.
#
# Pemisahan ini penting karena pertanyaannya berbeda: "siapa masuk tadi
# malam?" dijawab log keamanan, sedangkan "siapa mengubah jurnal ini?"
# dijawab log data. Mencampur keduanya membuat keduanya sulit dibaca.
KATEGORI_KEAMANAN = "keamanan"
KATEGORI_DATA = "data"
KATEGORI_ADMIN = "administrasi"

KATEGORI_AUDIT = (KATEGORI_KEAMANAN, KATEGORI_DATA, KATEGORI_ADMIN)

# Aksi yang tergolong keamanan: seluruh percobaan masuk dan keluar.
AKSI_KEAMANAN = ("login.success", "login.fail", "login.locked", "logout")

# Aksi yang tergolong administrasi: pengelolaan akun dan perusahaan.
AWALAN_ADMIN = ("user.", "company.", "permission.", "role.")


def kategori_aksi(aksi: str) -> str:
    """
    Tentukan kategori sebuah aksi.

    Kategori disimpulkan dari nama aksinya supaya aksi baru otomatis
    tergolong benar tanpa perlu didaftarkan satu per satu.
    """
    aksi = (aksi or "").strip()
    if aksi in AKSI_KEAMANAN:
        return KATEGORI_KEAMANAN
    if aksi.startswith(AWALAN_ADMIN):
        return KATEGORI_ADMIN
    return KATEGORI_DATA


def log_action(user_id: Optional[int], username: str, company_id: Optional[int],
               action: str, entity: str = "", entity_id: str = "",
               detail: str = "", kategori: str = None) -> None:
    """
    Catat satu aktivitas ke jejak audit.

    Kategori ditentukan otomatis dari nama aksi bila tidak diberikan, dan
    sumber (nama komputer) ikut dicatat untuk aksi keamanan agar percobaan
    masuk dapat ditelusuri asalnya.
    """
    if kategori is None:
        kategori = kategori_aksi(action)
    sumber = nama_komputer() if kategori == KATEGORI_KEAMANAN else None
    try:
        ex(
            "INSERT INTO audit_log(user_id,username,company_id,action,entity,"
            "entity_id,detail,kategori,ip_or_host) VALUES(?,?,?,?,?,?,?,?,?)",
            (user_id, username, company_id, action, entity, str(entity_id),
             detail[:2000], kategori, sumber),
        )
    except Exception:
        pass  # audit tidak boleh menggagalkan operasi utama


def log_login(username: str, berhasil: bool, user_id: Optional[int] = None,
              keterangan: str = "") -> None:
    """
    Catat satu percobaan masuk aplikasi.

    Dipisahkan dari log_action supaya seluruh percobaan masuk berhasil
    maupun gagal tercatat seragam beserta sumbernya.
    """
    if berhasil:
        aksi, pesan = "login.success", keterangan or "Berhasil masuk aplikasi."
    else:
        aksi, pesan = "login.fail", keterangan or "Password salah."
    log_action(user_id, username, None, aksi, "users", user_id or "",
               pesan, KATEGORI_KEAMANAN)


def nama_komputer() -> str:
    """Nama komputer yang sedang dipakai, untuk menandai asal akses."""
    try:
        import socket
        return socket.gethostname()[:64]
    except Exception:
        return ""


# ==========================================================================
# BACKUP
# ==========================================================================
def create_backup(keterangan: str = "") -> Path:
    config.ensure_dirs()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = config.BACKUP_DIR / f"akuntansiid_{stamp}.db"
    # Nama berkas memakai detik, sehingga dua cadangan dalam detik yang sama
    # akan saling menimpa. Bila itu terjadi, urutannya ditambahkan.
    urut = 1
    while target.exists():
        target = config.BACKUP_DIR / f"akuntansiid_{stamp}_{urut}.db"
        urut += 1
    src = get_conn()
    dst = sqlite3.connect(str(target))
    with dst:
        src.backup(dst)
    dst.close()
    try:
        ex("INSERT INTO backups(path,size_bytes,keterangan) VALUES(?,?,?)",
           (str(target), target.stat().st_size, keterangan))
    except Exception as e:
        # Cadangan tetap dianggap berhasil karena berkasnya sudah jadi.
        # Kegagalan di sini hanya membuat riwayat tidak tercatat, jadi
        # dicatat ke log aplikasi agar masih dapat ditelusuri.
        logging.getLogger("akuntansiid").warning(
            "Riwayat cadangan gagal disimpan: %s", e)
    return target


def restore_backup(path: Path) -> None:
    """
    Pulihkan basis data dari berkas cadangan.

    Koneksi yang sedang terbuka ditutup lebih dulu, lalu dibuka kembali
    setelah berkas diganti. Dengan begitu data hasil pemulihan langsung
    terpakai tanpa perlu menutup dan membuka ulang aplikasi.

    Berkas pendamping WAL dan SHM dibuang setelah penggantian. Bila berkas
    itu tertinggal, isinya dapat menimpa data hasil pemulihan sehingga
    pemulihan tampak berhasil padahal datanya sebagian masih lama.
    """
    _tutup_koneksi()
    import shutil
    shutil.copy2(path, config.DB_PATH)

    for akhiran in ("-wal", "-shm"):
        sisa = Path(str(config.DB_PATH) + akhiran)
        if not sisa.exists():
            continue
        try:
            sisa.unlink()
        except OSError as e:
            # Berkas pendamping tidak dapat dibuang. Ini perlu dilaporkan
            # karena hasil pemulihan bisa tidak utuh, dan pengguna harus tahu
            # sebelum melanjutkan pembukuan di atas data yang meragukan.
            raise OSError(
                f"Berkas pendamping basis data tidak dapat dibuang: "
                f"{sisa.name}. Tutup aplikasi lebih dulu, lalu ulangi "
                f"pemulihan. ({e})") from e

    # buka kembali supaya pemanggil langsung memakai data hasil pemulihan
    get_conn()


def _tutup_koneksi() -> None:
    """
    Tutup koneksi basis data milik thread ini.

    Kegagalan penutupan diabaikan dengan sengaja: koneksi tetap dibuang dari
    penyimpanan thread, dan pemanggil berikutnya akan membuka koneksi baru.
    Menutup koneksi tidak mengubah data, jadi kegagalannya tidak berakibat
    pada isi pembukuan.
    """
    key = f"conn_{config.DB_PATH}"
    conn = getattr(_local, key, None)
    if conn is not None:
        try:
            conn.commit()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass
        try:
            delattr(_local, key)
        except AttributeError:
            pass


def pulihkan_dari_cadangan(path: Path, simpan_dulu: bool = True) -> dict:
    """
    Pulihkan basis data dari cadangan dan laporkan isinya.

    Bila simpan_dulu benar, keadaan sekarang dicadangkan lebih dulu sehingga
    pemulihan yang salah pilih masih bisa dibatalkan.

    Mengembalikan ringkasan isi basis data setelah pemulihan supaya pengguna
    dapat memastikan datanya benar-benar kembali.
    """
    cadangan_pengaman = None
    if simpan_dulu:
        try:
            cadangan_pengaman = create_backup(
                "Cadangan otomatis sebelum pemulihan")
        except Exception:
            cadangan_pengaman = None

    restore_backup(Path(path))
    return {
        "cadangan_pengaman": cadangan_pengaman,
        "perusahaan": scalar("SELECT COUNT(*) FROM companies") or 0,
        "pengguna": scalar("SELECT COUNT(*) FROM users") or 0,
        "jurnal": scalar("SELECT COUNT(*) FROM journal_entries") or 0,
    }


# ==========================================================================
# CADANGAN OTOMATIS
# ==========================================================================
def _setelan_angka(kunci: str, bawaan: int) -> int:
    try:
        r = q1("SELECT value FROM settings WHERE key=?", (kunci,))
        return int(r["value"]) if r and r["value"] else bawaan
    except Exception:
        return bawaan


def _setelan_teks(kunci: str, bawaan: str = "") -> str:
    try:
        r = q1("SELECT value FROM settings WHERE key=?", (kunci,))
        return (r["value"] or bawaan) if r else bawaan
    except Exception:
        return bawaan


def _set_setelan(kunci: str, nilai) -> None:
    ex("INSERT INTO settings(key,value) VALUES(?,?) "
       "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
       (kunci, str(nilai)))


def setelan_backup_otomatis() -> dict:
    """Baca pengaturan cadangan otomatis."""
    return {
        "aktif": _setelan_teks("backup_auto", "1") == "1",
        "interval_jam": max(1, _setelan_angka("backup_interval_jam", 24)),
        "simpan_maks": max(2, _setelan_angka("backup_simpan_maks", 14)),
        "terakhir": _setelan_teks("backup_terakhir", ""),
    }


def simpan_setelan_backup(aktif: bool = None, interval_jam: int = None,
                          simpan_maks: int = None) -> dict:
    if aktif is not None:
        _set_setelan("backup_auto", "1" if aktif else "0")
    if interval_jam is not None:
        _set_setelan("backup_interval_jam", max(1, int(interval_jam)))
    if simpan_maks is not None:
        _set_setelan("backup_simpan_maks", max(2, int(simpan_maks)))
    return setelan_backup_otomatis()


def cadangan_terakhir() -> Optional[dict]:
    try:
        r = q1("SELECT * FROM backups ORDER BY id DESC LIMIT 1")
        return dict(r) if r else None
    except Exception:
        return None


def _sudah_waktunya() -> bool:
    """Tentukan apakah cadangan otomatis perlu dijalankan sekarang."""
    st = setelan_backup_otomatis()
    if not st["aktif"]:
        return False
    terakhir = st["terakhir"]
    if not terakhir:
        r = cadangan_terakhir()
        terakhir = (r or {}).get("ts", "")
    if not terakhir:
        return True
    try:
        kapan = datetime.strptime(terakhir[:19], "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return True
    selang = datetime.now() - kapan
    return selang.total_seconds() >= st["interval_jam"] * 3600


def bersihkan_cadangan_lama(simpan_maks: int = None) -> int:
    """Hapus berkas cadangan terlama agar jumlahnya tidak menumpuk."""
    batas = simpan_maks or setelan_backup_otomatis()["simpan_maks"]
    baris = q("SELECT id, path FROM backups ORDER BY id DESC")
    dihapus = 0
    for r in baris[batas:]:
        try:
            p = Path(r["path"])
            if p.exists():
                p.unlink()
            ex("DELETE FROM backups WHERE id=?", (r["id"],))
            dihapus += 1
        except Exception:
            continue
    return dihapus


def backup_otomatis(paksa: bool = False) -> Optional[Path]:
    """
    Jalankan cadangan otomatis bila sudah waktunya.

    Dipanggil saat aplikasi dimulai. Bila ``paksa`` benar, cadangan dibuat
    tanpa memeriksa selang waktu.
    """
    try:
        if not paksa and not _sudah_waktunya():
            return None
        berkas = create_backup("otomatis")
        _set_setelan("backup_terakhir",
                     datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        bersihkan_cadangan_lama()
        return berkas
    except Exception as e:
        import logging
        logging.getLogger("akuntansiid").warning("Cadangan otomatis gagal: %s", e)
        return None
