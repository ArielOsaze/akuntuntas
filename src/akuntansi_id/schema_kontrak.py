"""
Skema database: Kontrak & Kerja Sama
====================================

Menyimpan perjanjian dengan mitra, baik yang bernilai uang maupun kerja sama
non-tunai (barter barang, tukar jasa, bagi hasil, dan sejenisnya).

Dasar hukum yang dirujuk pada tiap kontrak:
- KUHPerdata Pasal 1313 (pengertian perjanjian), Pasal 1320 (syarat sah),
  Pasal 1338 (asas kebebasan berkontrak dan pacta sunt servanda).
- KUHPerdata Pasal 1457-1540 (jual beli), Pasal 1548-1600 (sewa menyewa),
  Pasal 1601-1617 (perjanjian kerja).
- UU 7/2014 tentang Perdagangan Pasal 33-51 (perjanjian dagang, waralaba,
  keagenan, dan distributor).
- PP 36/2021 tentang Pengupahan (untuk kontrak kerja dengan pekerja).
- UU 13/2003 Pasal 50-66 (perjanjian kerja, PKWT, alih daya) sebagaimana
  telah diubah oleh UU 6/2023 (Cipta Kerja).
- PMK 131/2024 dan PMK 81/2024 (PPh Pasal 23 atas jasa dan sewa selain tanah).
- UU 42/2009 Pasal 1 angka 23 (PPN atas penyerahan barang/jasa).
- PMK 68/2022 (PPh Pasal 4(2) atas sewa tanah/bangunan dan pengalihan hak).
"""

SKEMA_KONTRAK = """
CREATE TABLE IF NOT EXISTS kontrak (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id        INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    nomor             TEXT NOT NULL,
    judul             TEXT NOT NULL,
    jenis             TEXT NOT NULL DEFAULT 'kerja_sama',
    bentuk_imbalan    TEXT NOT NULL DEFAULT 'uang',
    partner_id        INTEGER REFERENCES partners(id) ON DELETE SET NULL,
    pihak_kedua       TEXT DEFAULT '',
    peran_kita        TEXT NOT NULL DEFAULT 'pemberi',
    tanggal_mulai     TEXT NOT NULL,
    tanggal_akhir     TEXT,
    tanggal_tanda_tangan TEXT,
    opsi_perpanjangan INTEGER NOT NULL DEFAULT 0,
    pemberitahuan_berakhir_hari INTEGER NOT NULL DEFAULT 30,
    nilai             INTEGER NOT NULL DEFAULT 0,
    nilai_barang      INTEGER NOT NULL DEFAULT 0,
    nilai_jasa        INTEGER NOT NULL DEFAULT 0,
    mata_uang         TEXT NOT NULL DEFAULT 'IDR',
    skema_bayar       TEXT NOT NULL DEFAULT 'lump_sum',
    jumlah_termin     INTEGER NOT NULL DEFAULT 1,
    termin_hari       INTEGER NOT NULL DEFAULT 0,
    persentase_bagi_hasil REAL,
    pph_pasal         TEXT DEFAULT '',
    tarif_pph         REAL,
    kena_ppn          INTEGER NOT NULL DEFAULT 0,
    status            TEXT NOT NULL DEFAULT 'aktif',
    alasan_berakhir   TEXT DEFAULT '',
    dokumen_path      TEXT DEFAULT '',
    dokumen_nama      TEXT DEFAULT '',
    catatan           TEXT DEFAULT '',
    dasar_hukum       TEXT DEFAULT '',
    dibuat_oleh       TEXT DEFAULT '',
    deleted_at        TEXT,
    created_at        TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    updated_at        TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS idx_kontrak_company ON kontrak(company_id, status);
CREATE INDEX IF NOT EXISTS idx_kontrak_nomor ON kontrak(company_id, nomor);
CREATE INDEX IF NOT EXISTS idx_kontrak_akhir ON kontrak(company_id, tanggal_akhir);
CREATE INDEX IF NOT EXISTS idx_kontrak_partner ON kontrak(partner_id);

CREATE TABLE IF NOT EXISTS kontrak_item (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    kontrak_id   INTEGER NOT NULL REFERENCES kontrak(id) ON DELETE CASCADE,
    arah         TEXT NOT NULL DEFAULT 'kita_beri',
    nama         TEXT NOT NULL,
    jumlah       REAL NOT NULL DEFAULT 1,
    satuan       TEXT DEFAULT 'unit',
    nilai_satuan INTEGER NOT NULL DEFAULT 0,
    total        INTEGER NOT NULL DEFAULT 0,
    catatan      TEXT DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_kontrak_item ON kontrak_item(kontrak_id);

CREATE TABLE IF NOT EXISTS kontrak_termin (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    kontrak_id   INTEGER NOT NULL REFERENCES kontrak(id) ON DELETE CASCADE,
    urutan       INTEGER NOT NULL DEFAULT 1,
    nama         TEXT NOT NULL,
    persen       REAL NOT NULL DEFAULT 0,
    nilai        INTEGER NOT NULL DEFAULT 0,
    jatuh_tempo  TEXT,
    dibayar      INTEGER NOT NULL DEFAULT 0,
    tanggal_bayar TEXT,
    catatan      TEXT DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_kontrak_termin ON kontrak_termin(kontrak_id, urutan);

CREATE TABLE IF NOT EXISTS kontrak_berkas (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    kontrak_id   INTEGER NOT NULL REFERENCES kontrak(id) ON DELETE CASCADE,
    nama         TEXT NOT NULL,
    path_berkas  TEXT NOT NULL,
    jenis        TEXT DEFAULT 'kontrak',
    isi_terstruktur TEXT DEFAULT '',
    ukuran       INTEGER NOT NULL DEFAULT 0,
    diunggah_oleh TEXT DEFAULT '',
    created_at   TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS idx_kontrak_berkas ON kontrak_berkas(kontrak_id);

DROP VIEW IF EXISTS v_kontrak_aktif;
CREATE VIEW v_kontrak_aktif AS
SELECT
    k.company_id,
    k.id,
    k.nomor,
    k.judul,
    k.jenis,
    k.bentuk_imbalan,
    k.status,
    k.tanggal_mulai,
    k.tanggal_akhir,
    k.nilai,
    k.nilai_barang,
    k.nilai_jasa,
    -- Nilai perjanjian: perjanjian uang memakai kolom nilai, kerja sama
    -- non-tunai memakai nilai barang/jasa yang ditukar. Tanpa penggabungan
    -- ini, kerja sama barter dan tukar jasa tampil bernilai nol.
    (k.nilai + k.nilai_barang + k.nilai_jasa) AS nilai_total,
    COALESCE(p.nama, k.pihak_kedua, '') AS mitra,
    CASE
        WHEN k.tanggal_akhir IS NULL THEN NULL
        ELSE CAST(julianday(k.tanggal_akhir) - julianday('now') AS INTEGER)
    END AS sisa_hari,
    CASE
        WHEN k.status <> 'aktif' THEN 'Tidak Aktif'
        WHEN k.tanggal_akhir IS NULL THEN 'Tanpa Batas Waktu'
        WHEN julianday(k.tanggal_akhir) < julianday('now') THEN 'Sudah Berakhir'
        WHEN julianday(k.tanggal_akhir) - julianday('now') <= 30 THEN 'Segera Berakhir'
        WHEN julianday(k.tanggal_akhir) - julianday('now') <= 90 THEN 'Perlu Perhatian'
        ELSE 'Berjalan'
    END AS kondisi
FROM kontrak k
LEFT JOIN partners p ON p.id = k.partner_id
WHERE k.deleted_at IS NULL;
"""
