"""
AkunTuntas - Bagan Akun Standar (Chart of Accounts)
====================================================
Template COA untuk tiga profil entitas:
  1. UMKM Orang Pribadi   sederhana, fokus kas
  2. Perseroan Perorangan struktur PT ringkas
  3. PT / CV / Koperasi   - struktur lengkap sesuai PSAK

Penomoran mengikuti konvensi umum akuntansi Indonesia:
  1xxx Aset | 2xxx Liabilitas | 3xxx Ekuitas
  4xxx Pendapatan | 5xxx HPP | 6xxx Beban Operasional
  7xxx Pendapatan Lain | 8xxx Beban Lain

Setiap akun memiliki:
  - grup_lr        : posisi di Laba Rugi (kosong untuk akun neraca)
  - baris_neraca   : posisi di Neraca (kosong untuk akun L/R)
  - perlakuan_fiskal: memengaruhi Rekonsiliasi Fiskal otomatis
  - deskripsi      : penjelasan ramah-pemula (ditampilkan di UI)
"""
from __future__ import annotations

from . import db


# Perlakuan fiskal yang dikenali mesin rekonsiliasi:
#   "Deductible/Taxable"  -> netral
#   "Non-Deductible (+)"  -> koreksi positif otomatis
#   "Final Income (-)"    -> koreksi negatif otomatis
#   "Review Fiskal"       -> perlu tinjauan manual pengguna
#   "Timing/Depreciation" -> selisih waktu, dihitung dari modul aset

# Format: (kode, nama, tipe, grup_lr, baris_neraca, normal, perlakuan, deskripsi, is_kas_bank)
Row = tuple[str, str, str, str, str, str, str, str, int]


def _a(kode, nama, tipe, grup_lr, baris, normal, perlakuan, deskripsi, kas=0) -> Row:
    return (kode, nama, tipe, grup_lr, baris, normal, perlakuan, deskripsi, kas)


# ==========================================================================
# COA UMKM ORANG PRIBADI — sesederhana mungkin agar pemula tidak tersesat
# ==========================================================================
COA_UMKM_OP: list[Row] = [
    # ---- ASET
    _a("1001", "Kas", "Aset", "", "Kas & Bank", "Debit", "Deductible/Taxable",
       "Uang tunai di tangan (dompet usaha, laci kasir). Bertambah saat menerima uang, berkurang saat membayar tunai.", 1),
    _a("1002", "Bank", "Aset", "", "Kas & Bank", "Debit", "Deductible/Taxable",
       "Saldo rekening bank usaha. Gunakan akun terpisah dari rekening pribadi agar pembukuan rapi.", 1),
    _a("1003", "Dompet Digital / QRIS", "Aset", "", "Kas & Bank", "Debit", "Deductible/Taxable",
       "Saldo e-wallet atau QRIS (GoPay, OVO, Dana, ShopeePay). Catat saldo setelah potongan biaya admin.", 1),
    _a("1101", "Piutang Usaha", "Aset", "", "Piutang Usaha", "Debit", "Deductible/Taxable",
       "Tagihan ke pelanggan yang belum dibayar. Muncul saat penjualan kredit."),
    _a("1102", "Persediaan Barang Dagang", "Aset", "", "Persediaan", "Debit", "Deductible/Taxable",
       "Nilai barang yang belum terjual, dihitung dari harga beli. Lakukan stock opname minimal setahun sekali."),
    _a("1103", "Biaya Dibayar Dimuka", "Aset", "", "Aset Lancar Lain", "Debit", "Deductible/Taxable",
       "Beban yang sudah dibayar tapi manfaatnya untuk periode mendatang, contoh sewa setahun dibayar di muka."),
    _a("1201", "Peralatan Usaha", "Aset", "", "Aset Tetap", "Debit", "Deductible/Taxable",
       "Aset tetap berumur lebih dari 1 tahun: laptop, mesin, peralatan kerja."),
    _a("1202", "Akumulasi Penyusutan Peralatan", "Aset", "", "Akumulasi Penyusutan", "Kredit", "Deductible/Taxable",
       "Akumulasi penurunan nilai peralatan. Akun kontra - saldo kredit mengurangi nilai aset."),
    # ---- LIABILITAS
    _a("2001", "Utang Usaha", "Liabilitas", "", "Utang Usaha", "Kredit", "Deductible/Taxable",
       "Kewajiban bayar ke pemasok atas barang/jasa yang sudah diterima."),
    _a("2101", "Utang PPN", "Liabilitas", "", "Utang Pajak", "Kredit", "Deductible/Taxable",
       "PPN keluaran yang belum disetor ke negara. Hanya untuk pengusaha berstatus PKP."),
    _a("2102", "Utang PPh Potong/Pungut", "Liabilitas", "", "Utang Pajak", "Kredit", "Deductible/Taxable",
       "PPh yang sudah dipotong dari pihak lain tetapi belum disetor ke kas negara."),
    _a("2201", "Utang Bank / Pinjaman", "Liabilitas", "", "Pinjaman Jangka Pendek", "Kredit", "Deductible/Taxable",
       "Pinjaman dari bank, koperasi, atau pihak lain yang harus dikembalikan."),
    # ---- EKUITAS
    _a("3001", "Modal Pemilik", "Ekuitas", "", "Modal", "Kredit", "Deductible/Taxable",
       "Setoran modal pemilik ke usaha. Bertambah saat menyetor, berkurang saat menarik modal."),
    _a("3002", "Prive (Penarikan Pemilik)", "Ekuitas", "", "Prive", "Debit", "Deductible/Taxable",
       "Uang usaha yang dipakai untuk keperluan pribadi pemilik. BUKAN beban usaha - jangan dicatat sebagai biaya!"),
    _a("3101", "Saldo Laba", "Ekuitas", "", "Saldo Laba", "Kredit", "Deductible/Taxable",
       "Akumulasi laba tahun-tahun sebelumnya yang belum dibagikan."),
    # ---- PENDAPATAN
    _a("4001", "Penjualan / Pendapatan Usaha", "Pendapatan", "Pendapatan Usaha", "", "Kredit", "Deductible/Taxable",
       "Pendapatan utama dari kegiatan usaha. Catat sebesar nilai sebelum PPN."),
    _a("4002", "Pendapatan Usaha Lain", "Pendapatan", "Pendapatan Usaha", "", "Kredit", "Deductible/Taxable",
       "Pendapatan tambahan yang masih terkait usaha utama, misal ongkos kirim yang ditagihkan."),
    # ---- HPP
    _a("5001", "Harga Pokok Penjualan", "Beban", "HPP", "", "Debit", "Deductible/Taxable",
       "Harga beli barang yang sudah terjual atau biaya bahan langsung. Dikurangkan dari pendapatan untuk menghitung laba kotor."),
    # ---- BEBAN OPERASIONAL
    _a("6001", "Gaji & Tunjangan", "Beban", "Beban Operasional", "", "Debit", "Deductible/Taxable",
       "Gaji, upah, tunjangan, dan bonus karyawan. Biaya ini deductible bagi pemberi kerja."),
    _a("6002", "Sewa", "Beban", "Beban Operasional", "", "Debit", "Deductible/Taxable",
       "Sewa tempat usaha, gudang, atau kendaraan. Untuk sewa tanah/bangunan, ingat PPh Final 4(2) 10%."),
    _a("6003", "Listrik, Air & Internet", "Beban", "Beban Operasional", "", "Debit", "Deductible/Taxable",
       "Tagihan utilitas operasional usaha."),
    _a("6004", "Marketing & Promosi", "Beban", "Beban Operasional", "", "Debit", "Deductible/Taxable",
       "Biaya iklan, promosi, endorse, cetak brosur, dan pemasaran lainnya."),
    _a("6005", "Transportasi & Perjalanan", "Beban", "Beban Operasional", "", "Debit", "Deductible/Taxable",
       "Biaya transportasi, bensin, tol, perjalanan dinas. Simpan bukti agar dapat dibiayakan."),
    _a("6006", "Jasa Profesional", "Beban", "Beban Operasional", "", "Debit", "Deductible/Taxable",
       "Biaya jasa pihak ketiga: konsultan, akuntan, notaris, desainer. Ingat PPh 23 (2%) bila pembayarannya ke badan."),
    _a("6007", "Penyusutan", "Beban", "Beban Operasional", "", "Debit", "Timing/Depreciation",
       "Alokasi biaya perolehan aset tetap selama masa manfaatnya. Selisih komersial-fiskal muncul di sini."),
    _a("6008", "Perlengkapan & ATK", "Beban", "Beban Operasional", "", "Debit", "Deductible/Taxable",
       "Alat tulis, tinta printer, perlengkapan habis pakai."),
    _a("6009", "Biaya Bank & Administrasi", "Beban", "Beban Operasional", "", "Debit", "Deductible/Taxable",
       "Biaya admin bank, transfer, payment gateway (misal 2% dari transaksi marketplace)."),
    _a("6010", "Perbaikan & Pemeliharaan", "Beban", "Beban Operasional", "", "Debit", "Deductible/Taxable",
       "Servis, perbaikan ringan. Perbaikan besar yang menambah nilai aset harus dikapitalisasi."),
    _a("6011", "Beban Lain-lain", "Beban", "Beban Operasional", "", "Debit", "Review Fiskal",
       "Beban operasional yang tidak masuk kategori lain. Perlu ditinjau saat rekonsiliasi fiskal."),
    # ---- PENDAPATAN LAIN
    _a("7001", "Pendapatan Bunga Bank", "Pendapatan", "Pendapatan Lain", "", "Kredit", "Final Income (-)",
       "Bunga deposito/jasa giro. Sudah dipotong PPh Final 20% di bank, sehingga dikeluarkan dari PKP umum."),
    _a("7002", "Pendapatan Lain-lain", "Pendapatan", "Pendapatan Lain", "", "Kredit", "Deductible/Taxable",
       "Pendapatan di luar usaha utama yang tetap kena pajak, misal keuntungan penjualan aset."),
    # ---- BEBAN LAIN
    _a("8001", "Beban Bunga Pinjaman", "Beban", "Beban Lain", "", "Debit", "Deductible/Taxable",
       "Bunga atas pinjaman usaha. Bunga ke bank deductible; ke pemegang saham ada batasannya (DER)."),
    _a("8002", "Denda & Sanksi Pajak", "Beban", "Beban Lain", "", "Debit", "Non-Deductible (+)",
       "Sanksi administrasi pajak. TIDAK dapat dikurangkan secara fiskal (Pasal 9 UU PPh) - koreksi positif."),
]


# ==========================================================================
# COA PERSEROAN PERORANGAN — struktur PT ringkas
# ==========================================================================
# Dibangun dari COA UMKM (agar semua akun dasar tersedia: HPP, beban, dll.)
# ditambah akun-akun khusus badan hukum.
COA_PT_PERORANGAN: list[Row] = list(COA_UMKM_OP) + [
    _a("1004", "Kas Kecil (Petty Cash)", "Aset", "", "Kas & Bank", "Debit", "Deductible/Taxable",
       "Kas khusus pengeluaran kecil sehari-hari. Dilakukan replenishment periodik.", 1),
    _a("1104", "Pajak Dibayar Dimuka", "Aset", "", "Aset Lancar Lain", "Debit", "Deductible/Taxable",
       "PPh 25 dibayar di muka, PPh 23 dipotong pihak lain, atau PPN masukan yang dapat dikreditkan."),
    _a("1203", "Kendaraan", "Aset", "", "Aset Tetap", "Debit", "Deductible/Taxable",
       "Kendaraan operasional perusahaan. Umumnya Kelompok Fiskal 2."),
    _a("1204", "Bangunan", "Aset", "", "Aset Tetap", "Debit", "Deductible/Taxable",
       "Bangunan milik perusahaan. Disusutkan garis lurus 5% (permanen) atau 10% (tidak permanen)."),
    _a("1205", "Akumulasi Penyusutan Bangunan", "Aset", "", "Akumulasi Penyusutan", "Kredit", "Deductible/Taxable",
       "Akumulasi penyusutan bangunan."),
    _a("2301", "Utang PPh Badan", "Liabilitas", "", "Utang Pajak", "Kredit", "Deductible/Taxable",
       "PPh Badan tahun berjalan yang masih harus dibayar."),
    _a("2401", "Pinjaman Jangka Panjang", "Liabilitas", "", "Pinjaman Jangka Panjang", "Kredit", "Deductible/Taxable",
       "Pinjaman dengan jatuh tempo lebih dari satu tahun."),
    _a("3003", "Tambahan Modal Disetor", "Ekuitas", "", "Modal", "Kredit", "Deductible/Taxable",
       "Agio saham atau setoran modal di atas nilai nominal."),
    _a("3004", "Dividen Dibagikan", "Ekuitas", "", "Dividen", "Debit", "Deductible/Taxable",
       "Dividen yang dibagikan ke pemegang saham. Bukan beban; mengurangi ekuitas."),
    _a("6012", "BPJS Kesehatan (Perusahaan)", "Beban", "Beban Operasional", "", "Debit", "Deductible/Taxable",
       "Iuran BPJS Kesehatan porsi pemberi kerja sebesar 4% dari upah."),
    _a("6013", "BPJS Ketenagakerjaan (Perusahaan)", "Beban", "Beban Operasional", "", "Debit", "Deductible/Taxable",
       "JHT 3,7% + JKK + JKM + JP 2% porsi pemberi kerja."),
    _a("6014", "PPh 21 Ditanggung Perusahaan", "Beban", "Beban Operasional", "", "Debit", "Deductible/Taxable",
       "PPh 21 yang ditanggung perusahaan (tunjangan pajak). Merupakan deductible bagi perusahaan."),
    _a("6015", "Entertainment & Representasi", "Beban", "Beban Operasional", "", "Debit", "Review Fiskal",
       "Biaya jamuan/representasi. Deductible hanya bila disertai daftar nominatif (PMK 02/2022)."),
    _a("6016", "Sumbangan & Donasi", "Beban", "Beban Operasional", "", "Debit", "Review Fiskal",
       "Sumbangan. Hanya deductible bila memenuhi syarat Pasal 6 UU PPh (misal ke lembaga resmi)."),
    _a("8003", "Beban Pajak Final", "Beban", "Beban Lain", "", "Debit", "Non-Deductible (+)",
       "PPh Final yang dibayar sendiri (misal PPh Final 0,5%). Tidak deductible."),
]


# ==========================================================================
# COA PT / CV / KOPERASI — lengkap, siap audit
# ==========================================================================
COA_FULL: list[Row] = [
    # ---------------- ASET LANCAR
    _a("1001", "Kas", "Aset", "", "Kas & Bank", "Debit", "Deductible/Taxable",
       "Uang tunai di tangan perusahaan.", 1),
    _a("1002", "Kas Kecil (Petty Cash)", "Aset", "", "Kas & Bank", "Debit", "Deductible/Taxable",
       "Dana kas kecil untuk pengeluaran rutin bernilai kecil (imprest fund).", 1),
    _a("1003", "Bank", "Aset", "", "Kas & Bank", "Debit", "Deductible/Taxable",
       "Rekening giro/tabungan perusahaan. Lakukan rekonsiliasi bank bulanan.", 1),
    _a("1004", "Bank - Rekening Khusus", "Aset", "", "Kas & Bank", "Debit", "Deductible/Taxable",
       "Rekening terpisah untuk keperluan khusus (payroll, escrow, proyek).", 1),
    _a("1005", "Dompet Digital / QRIS", "Aset", "", "Kas & Bank", "Debit", "Deductible/Taxable",
       "Saldo e-wallet dan QRIS. Biaya MDR (merchant discount rate) dicatat sebagai biaya bank.", 1),
    _a("1101", "Piutang Usaha", "Aset", "", "Piutang Usaha", "Debit", "Deductible/Taxable",
       "Tagihan kepada pelanggan atas penjualan kredit. Umur piutang perlu dipantau (aging schedule)."),
    _a("1102", "Piutang Lain-lain", "Aset", "", "Piutang Usaha", "Debit", "Deductible/Taxable",
       "Piutang ke pihak lain: karyawan, pemasok (retur), pinjaman jangka pendek."),
    _a("1103", "Cadangan Kerugian Piutang", "Aset", "", "Piutang Usaha", "Kredit", "Review Fiskal",
       "Penyisihan penurunan nilai piutang (PSAK 71). Bagi fiskal, hanya dapat dibebankan bila memenuhi syarat tertentu."),
    _a("1104", "Persediaan Barang Dagang", "Aset", "", "Persediaan", "Debit", "Deductible/Taxable",
       "Persediaan dinilai pada nilai terendah antara biaya perolehan dan nilai realisasi neto (PSAK 14)."),
    _a("1105", "Persediaan Bahan Baku", "Aset", "", "Persediaan", "Debit", "Deductible/Taxable",
       "Bahan baku produksi yang belum dipakai."),
    _a("1106", "Persediaan Barang Dalam Proses", "Aset", "", "Persediaan", "Debit", "Deductible/Taxable",
       "Barang setengah jadi pada tanggal laporan."),
    _a("1107", "Persediaan Barang Jadi", "Aset", "", "Persediaan", "Debit", "Deductible/Taxable",
       "Produk selesai yang belum terjual."),
    _a("1108", "PPN Masukan", "Aset", "", "Aset Lancar Lain", "Debit", "Deductible/Taxable",
       "PPN yang dibayar saat pembelian, dapat dikreditkan terhadap PPN keluaran (hanya PKP)."),
    _a("1109", "PPh 22/23/25 Dibayar Dimuka", "Aset", "", "Aset Lancar Lain", "Debit", "Deductible/Taxable",
       "Kredit pajak: PPh dipotong pihak lain, PPh 22 impor, dan angsuran PPh 25. Mengurangi PPh Badan terutang."),
    _a("1110", "Biaya Dibayar Dimuka", "Aset", "", "Aset Lancar Lain", "Debit", "Deductible/Taxable",
       "Sewa, asuransi, atau lisensi yang dibayar di muka; diamortisasi sesuai masa manfaat."),
    _a("1111", "Uang Muka Pembelian", "Aset", "", "Aset Lancar Lain", "Debit", "Deductible/Taxable",
       "DP ke pemasok yang belum menghasilkan barang/jasa."),
    # ---------------- ASET TETAP
    _a("1201", "Tanah", "Aset", "", "Aset Tetap", "Debit", "Deductible/Taxable",
       "Tanah tidak disusutkan. Biaya perolehan termasuk BPHTB dan biaya notaris."),
    _a("1202", "Bangunan", "Aset", "", "Aset Tetap", "Debit", "Deductible/Taxable",
       "Bangunan permanen: susut garis lurus 5%/tahun (20 tahun)."),
    _a("1203", "Akumulasi Penyusutan Bangunan", "Aset", "", "Akumulasi Penyusutan", "Kredit", "Deductible/Taxable",
       "Akun kontra atas bangunan."),
    _a("1204", "Mesin & Peralatan Pabrik", "Aset", "", "Aset Tetap", "Debit", "Deductible/Taxable",
       "Mesin produksi. Umumnya Kelompok Fiskal 2 atau 3 sesuai PMK 72/2023."),
    _a("1205", "Akumulasi Penyusutan Mesin", "Aset", "", "Akumulasi Penyusutan", "Kredit", "Deductible/Taxable",
       "Akumulasi penyusutan mesin."),
    _a("1206", "Kendaraan", "Aset", "", "Aset Tetap", "Debit", "Deductible/Taxable",
       "Kendaraan operasional. Kelompok 1 (roda dua) atau Kelompok 2 (roda empat)."),
    _a("1207", "Akumulasi Penyusutan Kendaraan", "Aset", "", "Akumulasi Penyusutan", "Kredit", "Deductible/Taxable",
       "Akumulasi penyusutan kendaraan."),
    _a("1208", "Peralatan Kantor & Komputer", "Aset", "", "Aset Tetap", "Debit", "Deductible/Taxable",
       "Komputer, printer, AC, furniture. Umumnya Kelompok 1 (4 tahun) atau Kelompok 2 (8 tahun)."),
    _a("1209", "Akumulasi Penyusutan Peralatan", "Aset", "", "Akumulasi Penyusutan", "Kredit", "Deductible/Taxable",
       "Akumulasi penyusutan peralatan kantor."),
    _a("1210", "Aset Takberwujud", "Aset", "", "Aset Tetap", "Debit", "Deductible/Taxable",
       "Software, lisensi, hak paten. Diamortisasi; untuk fiskal umumnya 4 tahun (Kelompok 1)."),
    # ---------------- ASET LAIN
    _a("1301", "Aset Pajak Tangguhan", "Aset", "", "Aset Lain", "Debit", "Deductible/Taxable",
       "Dampak pajak atas perbedaan temporer (PSAK 46). Contoh: beda penyusutan komersial vs fiskal."),
    _a("1302", "Investasi Jangka Panjang", "Aset", "", "Aset Lain", "Debit", "Deductible/Taxable",
       "Penyertaan saham, obligasi, atau properti investasi."),
    _a("1303", "Sewa Dibayar Dimuka Jangka Panjang", "Aset", "", "Aset Lain", "Debit", "Deductible/Taxable",
       "Sewa dengan masa lebih dari satu tahun."),
    # ---------------- LIABILITAS
    _a("2001", "Utang Usaha", "Liabilitas", "", "Utang Usaha", "Kredit", "Deductible/Taxable",
       "Kewajiban kepada pemasok atas pembelian kredit."),
    _a("2002", "Utang Gaji", "Liabilitas", "", "Utang Usaha", "Kredit", "Deductible/Taxable",
       "Gaji karyawan yang sudah menjadi haknya tetapi belum dibayar."),
    _a("2003", "Utang PPN Keluaran", "Liabilitas", "", "Utang Pajak", "Kredit", "Deductible/Taxable",
       "PPN keluaran yang dipungut dari pelanggan dan belum disetor."),
    _a("2004", "Utang PPh 21", "Liabilitas", "", "Utang Pajak", "Kredit", "Deductible/Taxable",
       "PPh 21 yang sudah dipotong dari karyawan tetapi belum disetor."),
    _a("2005", "Utang PPh 23", "Liabilitas", "", "Utang Pajak", "Kredit", "Deductible/Taxable",
       "PPh 23 yang dipotong atas jasa/sewa ke pihak lain."),
    _a("2006", "Utang PPh 4(2)", "Liabilitas", "", "Utang Pajak", "Kredit", "Deductible/Taxable",
       "PPh Final 4(2) yang dipotong (sewa tanah/bangunan, konstruksi)."),
    _a("2007", "Utang PPh Badan", "Liabilitas", "", "Utang Pajak", "Kredit", "Deductible/Taxable",
       "PPh Badan terutang yang belum dibayar."),
    _a("2008", "Utang PPh Final UMKM", "Liabilitas", "", "Utang Pajak", "Kredit", "Deductible/Taxable",
       "PPh Final 0,5% terutang (bila skema final dipakai)."),
    _a("2009", "Utang BPJS Kesehatan", "Liabilitas", "", "Utang Usaha", "Kredit", "Deductible/Taxable",
       "Iuran BPJS Kesehatan yang belum disetor."),
    _a("2010", "Utang BPJS Ketenagakerjaan", "Liabilitas", "", "Utang Usaha", "Kredit", "Deductible/Taxable",
       "Iuran JHT/JKK/JKM/JP yang belum disetor."),
    _a("2011", "Uang Muka Pelanggan", "Liabilitas", "", "Utang Usaha", "Kredit", "Deductible/Taxable",
       "DP yang diterima dari pelanggan atas barang/jasa yang belum diserahkan."),
    _a("2012", "Utang Dividen", "Liabilitas", "", "Utang Usaha", "Kredit", "Deductible/Taxable",
       "Dividen yang telah diumumkan tetapi belum dibayar."),
    _a("2013", "Utang Akrual", "Liabilitas", "", "Utang Usaha", "Kredit", "Deductible/Taxable",
       "Beban yang sudah terjadi tetapi belum ditagih pemasoknya, misalnya "
       "tagihan listrik akhir bulan. Dipakai bersama fitur jurnal balik pada "
       "halaman Pajak Lanjutan, agar beban tidak dihitung dua kali pada "
       "periode berikutnya."),
    _a("2101", "Utang Bank Jangka Pendek", "Liabilitas", "", "Pinjaman Jangka Pendek", "Kredit", "Deductible/Taxable",
       "Kredit modal kerja dengan jatuh tempo ≤ 1 tahun."),
    _a("2102", "Utang Leasing Jangka Pendek", "Liabilitas", "", "Pinjaman Jangka Pendek", "Kredit", "Deductible/Taxable",
       "Bagian lancar dari utang sewa pembiayaan."),
    _a("2201", "Utang Bank Jangka Panjang", "Liabilitas", "", "Pinjaman Jangka Panjang", "Kredit", "Deductible/Taxable",
       "Kredit investasi dengan jatuh tempo > 1 tahun."),
    _a("2202", "Utang Leasing Jangka Panjang", "Liabilitas", "", "Pinjaman Jangka Panjang", "Kredit", "Deductible/Taxable",
       "Bagian jangka panjang utang sewa pembiayaan."),
    _a("2203", "Liabilitas Imbalan Kerja", "Liabilitas", "", "Pinjaman Jangka Panjang", "Kredit", "Review Fiskal",
       "Cadangan imbalan pascakerja (PSAK 24). Deductible fiskal saat dibayarkan, bukan saat dicadangkan."),
    # ---------------- EKUITAS
    _a("3001", "Modal Saham", "Ekuitas", "", "Modal", "Kredit", "Deductible/Taxable",
       "Nilai nominal saham yang disetor pemegang saham."),
    _a("3002", "Tambahan Modal Disetor (Agio)", "Ekuitas", "", "Modal", "Kredit", "Deductible/Taxable",
       "Selisih setoran di atas nilai nominal saham."),
    _a("3003", "Modal Disetor Belum Lunas", "Ekuitas", "", "Modal", "Debit", "Deductible/Taxable",
       "Bagian modal yang masih menjadi kewajiban pemegang saham."),
    _a("3004", "Saldo Laba", "Ekuitas", "", "Saldo Laba", "Kredit", "Deductible/Taxable",
       "Akumulasi laba yang belum dibagikan sebagai dividen."),
    _a("3005", "Dividen Dibagikan", "Ekuitas", "", "Dividen", "Debit", "Deductible/Taxable",
       "Dividen yang diumumkan/dibayar. Bukan beban pajak - mengurangi ekuitas."),
    _a("3006", "Prive (Penarikan Pemilik)", "Ekuitas", "", "Prive", "Debit", "Deductible/Taxable",
       "Khusus bentuk usaha perorangan/CV: penarikan pemilik. Bukan beban."),
    _a("3007", "Laba Tahun Berjalan", "Ekuitas", "", "Laba Tahun Berjalan", "Kredit", "Deductible/Taxable",
       "Hasil periode berjalan sebelum dipindahkan ke Saldo Laba pada saat penutupan."),
    # ---------------- PENDAPATAN
    _a("4001", "Penjualan / Pendapatan Usaha", "Pendapatan", "Pendapatan Usaha", "", "Kredit", "Deductible/Taxable",
       "Pendapatan utama. Dicatat neto setelah retur dan potongan penjualan."),
    _a("4002", "Pendapatan Usaha Lain", "Pendapatan", "Pendapatan Usaha", "", "Kredit", "Deductible/Taxable",
       "Pendapatan terkait usaha utama di luar penjualan pokok."),
    _a("4003", "Retur & Potongan Penjualan", "Pendapatan", "Pendapatan Usaha", "", "Debit", "Deductible/Taxable",
       "Akun kontra pendapatan: barang dikembalikan pelanggan atau diskon penjualan."),
    # ---------------- HPP
    _a("5001", "Harga Pokok Penjualan", "Beban", "HPP", "", "Debit", "Deductible/Taxable",
       "HPP barang dagang: persediaan awal + pembelian − persediaan akhir."),
    _a("5002", "Biaya Bahan Baku", "Beban", "HPP", "", "Debit", "Deductible/Taxable",
       "Pemakaian bahan baku produksi."),
    _a("5003", "Biaya Tenaga Kerja Langsung", "Beban", "HPP", "", "Debit", "Deductible/Taxable",
       "Upah pekerja langsung yang terkait produksi."),
    _a("5004", "Biaya Overhead Pabrik", "Beban", "HPP", "", "Debit", "Deductible/Taxable",
       "Biaya pabrik tidak langsung: listrik pabrik, penyusutan mesin, bahan penolong."),
    # ---------------- BEBAN OPERASIONAL
    _a("6001", "Gaji & Tunjangan", "Beban", "Beban Operasional", "", "Debit", "Deductible/Taxable",
       "Beban gaji seluruh karyawan (non-produksi langsung)."),
    _a("6002", "Tunjangan Hari Raya (THR) & Bonus", "Beban", "Beban Operasional", "", "Debit", "Deductible/Taxable",
       "THR dan bonus tahunan. Dapat dibiayakan pada tahun terjadinya."),
    _a("6003", "BPJS Kesehatan (Perusahaan)", "Beban", "Beban Operasional", "", "Debit", "Deductible/Taxable",
       "Iuran BPJS Kesehatan porsi pemberi kerja (4%)."),
    _a("6004", "BPJS Ketenagakerjaan (Perusahaan)", "Beban", "Beban Operasional", "", "Debit", "Deductible/Taxable",
       "JHT 3,7% + JKK + JKM + JP 2% porsi pemberi kerja."),
    _a("6005", "PPh 21 Ditanggung Perusahaan", "Beban", "Beban Operasional", "", "Debit", "Deductible/Taxable",
       "Tunjangan pajak PPh 21. Deductible bagi perusahaan dan menambah bruto karyawan."),
    _a("6006", "Sewa", "Beban", "Beban Operasional", "", "Debit", "Deductible/Taxable",
       "Sewa kantor, gudang, kendaraan. Untuk tanah/bangunan dikenakan PPh Final 10%."),
    _a("6007", "Listrik, Air & Gas", "Beban", "Beban Operasional", "", "Debit", "Deductible/Taxable",
       "Biaya utilitas operasional."),
    _a("6008", "Telekomunikasi & Internet", "Beban", "Beban Operasional", "", "Debit", "Deductible/Taxable",
       "Internet, telepon, langganan software komunikasi."),
    _a("6009", "Marketing & Promosi", "Beban", "Beban Operasional", "", "Debit", "Deductible/Taxable",
       "Iklan digital, cetak, event, endorse."),
    _a("6010", "Entertainment & Representasi", "Beban", "Beban Operasional", "", "Debit", "Review Fiskal",
       "Jamuan klien. Deductible bila ada daftar nominatif (PMK 02/PMK.03/2022)."),
    _a("6011", "Transportasi & Perjalanan Dinas", "Beban", "Beban Operasional", "", "Debit", "Deductible/Taxable",
       "Tiket, hotel, uang harian perjalanan dinas."),
    _a("6012", "Jasa Profesional", "Beban", "Beban Operasional", "", "Debit", "Deductible/Taxable",
       "Konsultan, akuntan, notaris, advokat. Wajib dipotong PPh 23 2% bila penerima WP Badan."),
    _a("6013", "Biaya Bank & Payment Gateway", "Beban", "Beban Operasional", "", "Debit", "Deductible/Taxable",
       "Biaya administrasi bank, transfer, MDR QRIS, komisi marketplace."),
    _a("6014", "Perlengkapan & ATK", "Beban", "Beban Operasional", "", "Debit", "Deductible/Taxable",
       "Perlengkapan habis pakai."),
    _a("6015", "Perbaikan & Pemeliharaan", "Beban", "Beban Operasional", "", "Debit", "Deductible/Taxable",
       "Pemeliharaan rutin. Perbaikan yang memperpanjang umur aset harus dikapitalisasi."),
    _a("6016", "Asuransi", "Beban", "Beban Operasional", "", "Debit", "Deductible/Taxable",
       "Premi asuransi aset dan operasional usaha."),
    _a("6017", "Perizinan & Legalitas", "Beban", "Beban Operasional", "", "Debit", "Deductible/Taxable",
       "Biaya pendirian, perizinan, sertifikasi, pembaruan dokumen."),
    _a("6018", "Pelatihan & Pengembangan SDM", "Beban", "Beban Operasional", "", "Debit", "Deductible/Taxable",
       "Training, seminar, sertifikasi karyawan."),
    _a("6019", "Penyusutan Aset Tetap", "Beban", "Beban Operasional", "", "Debit", "Timing/Depreciation",
       "Penyusutan bangunan, mesin, kendaraan, peralatan (komersial)."),
    _a("6020", "Amortisasi Aset Takberwujud", "Beban", "Beban Operasional", "", "Debit", "Timing/Depreciation",
       "Amortisasi software, lisensi, hak."),
    _a("6021", "Beban Piutang Tak Tertagih", "Beban", "Beban Operasional", "", "Debit", "Review Fiskal",
       "Penghapusan piutang. Fiskal hanya mengakui bila memenuhi syarat Pasal 6 UU PPh & PMK terkait."),
    _a("6022", "Sumbangan & Donasi", "Beban", "Beban Operasional", "", "Debit", "Review Fiskal",
       "Deductible terbatas: zakat/sumbangan ke lembaga resmi maksimal 5% dari laba fiskal (Pasal 6 UU PPh)."),
    _a("6023", "Beban Umum Lainnya", "Beban", "Beban Operasional", "", "Debit", "Review Fiskal",
       "Beban operasional lain yang tidak terkategori. Tinjau saat rekonsiliasi fiskal."),
    # ---------------- PENDAPATAN LAIN
    _a("7001", "Pendapatan Bunga Deposito/Jasa Giro", "Pendapatan", "Pendapatan Lain", "", "Kredit", "Final Income (-)",
       "Kena PPh Final 20% yang sudah dipotong bank - dikeluarkan dari PKP tarif umum."),
    _a("7002", "Keuntungan Penjualan Aset Tetap", "Pendapatan", "Pendapatan Lain", "", "Kredit", "Deductible/Taxable",
       "Selisih nilai jual di atas nilai buku. Kena tarif umum (bukan final)."),
    _a("7003", "Pendapatan Dividen", "Pendapatan", "Pendapatan Lain", "", "Kredit", "Review Fiskal",
       "Dividen dari penyertaan ≥25% dapat dikecualikan (Pasal 4 ayat 3 UU PPh) bila memenuhi syarat."),
    _a("7004", "Pendapatan Sewa", "Pendapatan", "Pendapatan Lain", "", "Kredit", "Deductible/Taxable",
       "Sewa harta selain tanah/bangunan: objek PPh 23 bila ke WP Badan."),
    _a("7005", "Laba Selisih Kurs", "Pendapatan", "Pendapatan Lain", "", "Kredit", "Deductible/Taxable",
       "Keuntungan selisih kurs. Untuk fiskal: kena pajak saat realisasi, kecuali memilih kebijakan tertentu."),
    _a("7006", "Pendapatan Lain-lain", "Pendapatan", "Pendapatan Lain", "", "Kredit", "Deductible/Taxable",
       "Pendapatan lain yang bersifat insidental."),
    # ---------------- BEBAN LAIN
    _a("8001", "Beban Bunga Pinjaman", "Beban", "Beban Lain", "", "Debit", "Deductible/Taxable",
       "Bunga pinjaman bank/leasing. Bunga ke pemegang saham dibatasi rasio utang-modal 4:1 (PMK 169/2017)."),
    _a("8002", "Beban Administrasi Bank", "Beban", "Beban Lain", "", "Debit", "Deductible/Taxable",
       "Biaya provisi, administrasi, denda bank."),
    _a("8003", "Rugi Selisih Kurs", "Beban", "Beban Lain", "", "Debit", "Deductible/Taxable",
       "Kerugian selisih kurs yang telah direalisasi."),
    _a("8004", "Beban Pajak Final", "Beban", "Beban Lain", "", "Debit", "Non-Deductible (+)",
       "PPh Final yang dibayar sendiri (misal PPh Final 0,5%, PPh Final sewa). Tidak deductible."),
    _a("8005", "Beban PPh Badan", "Beban", "Beban Lain", "", "Debit", "Non-Deductible (+)",
       "Beban PPh Badan tahun berjalan. Bukan biaya yang dapat dikurangkan (Pasal 9 UU PPh)."),
    _a("8006", "Denda & Sanksi Pajak", "Beban", "Beban Lain", "", "Debit", "Non-Deductible (+)",
       "Sanksi administrasi/pidana pajak. Tidak deductible (Pasal 9 ayat 1 huruf k UU PPh)."),
    _a("8007", "Beban Lain-lain", "Beban", "Beban Lain", "", "Debit", "Review Fiskal",
       "Beban non-operasional lain. Tinjau saat rekonsiliasi fiskal."),
]


COA_TEMPLATES: dict[str, list[Row]] = {
    "umkm_op": COA_UMKM_OP,
    "pt_perorangan": COA_PT_PERORANGAN,
    "pt": COA_FULL,
    "cv": COA_FULL,
    "koperasi": COA_FULL,
}


def get_coa_template(entity_type: str) -> list[Row]:
    return COA_TEMPLATES.get(entity_type, COA_FULL)


def coa_template_label(entity_type: str) -> str:
    labels = {
        "umkm_op": "UMKM Orang Pribadi (sederhana)",
        "pt_perorangan": "Perseroan Perorangan (ringkas)",
        "pt": "PT / CV / Koperasi (lengkap)",
    }
    return labels.get(entity_type, "Lengkap")


def akun_belum_ada(company_id: int, bentuk: str = "pt") -> list:
    """
    Akun bawaan yang belum ada pada perusahaan tertentu.

    Bagan akun ditulis saat perusahaan dibuat. Bila aplikasi diperbarui dan
    bagan akunnya bertambah, perusahaan yang sudah ada tidak ikut mendapat
    akun baru itu. Akibatnya fitur yang memakai akun tersebut gagal pada
    komputer pengguna lama, meskipun pada perusahaan baru berjalan normal.

    Fungsi ini mencari selisihnya, supaya akun yang kurang dapat
    ditambahkan tanpa menyentuh akun yang sudah ada.
    """
    try:
        ada = {
            r["kode"] for r in db.q(
                "SELECT kode FROM accounts WHERE company_id = ?", (company_id,))
        }
    except Exception:
        return []

    return [baris for baris in get_coa_template(bentuk)
            if baris[0] not in ada]


def lengkapi_akun_bawaan(company_id: int, bentuk: str = "pt") -> int:
    """
    Tambahkan akun bawaan yang belum ada pada perusahaan tertentu.

    Mengembalikan jumlah akun yang ditambahkan. Akun yang sudah ada tidak
    disentuh, sehingga saldo dan jurnal pengguna tidak terpengaruh.
    """
    kurang = akun_belum_ada(company_id, bentuk)
    if not kurang:
        return 0

    jumlah = 0
    with db.tx() as conn:
        for kode, nama_akun, tipe, grup, baris, normal, perl, desk, kas in kurang:
            conn.execute(
                """INSERT INTO accounts(company_id, kode, nama, tipe, grup_lr,
                   baris_neraca, normal, perlakuan_fiskal, deskripsi, is_kas_bank)
                   VALUES(?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(company_id, kode) DO NOTHING""",
                (company_id, kode, nama_akun, tipe, grup, baris, normal,
                 perl, desk, kas),
            )
            jumlah += 1
    return jumlah


def lengkapi_semua_perusahaan() -> int:
    """
    Tambahkan akun bawaan yang kurang pada seluruh perusahaan.

    Dipanggil sekali saat aplikasi dibuka, supaya pengguna yang sudah
    memakai versi lama tetap mendapat akun baru tanpa perlu membuat ulang
    perusahaannya.
    """
    try:
        perusahaan = db.q("SELECT id, bentuk FROM companies")
    except Exception:
        return 0

    jumlah = 0
    for p in perusahaan:
        jumlah += lengkapi_akun_bawaan(p["id"], p["bentuk"] or "pt")
    return jumlah


# ==========================================================================
# PANDUAN KONTEKSTUAL — ditampilkan di UI sebagai panel "Penjelasan"
# ==========================================================================
HELP_TOPICS: dict[str, dict[str, str]] = {
    "coa": {
        "judul": "Bagan Akun (Chart of Accounts)",
        "isi": (
            "Bagan akun adalah daftar seluruh 'wadah' pencatatan transaksi usaha Anda.\n\n"
            "Cara membaca kode akun:\n"
            "  1xxx = Aset (harta yang dimiliki)\n"
            "  2xxx = Liabilitas (utang/kewajiban)\n"
            "  3xxx = Ekuitas (modal & laba)\n"
            "  4xxx = Pendapatan (penghasilan usaha)\n"
            "  5xxx = HPP (harga pokok penjualan)\n"
            "  6xxx = Beban Operasional\n"
            "  7xxx = Pendapatan Lain\n"
            "  8xxx = Beban Lain\n\n"
            "Persamaan dasar akuntansi:\n"
            "  ASET = LIABILITAS + EKUITAS\n\n"
            "Setiap transaksi harus menjaga persamaan ini tetap seimbang."
        ),
        "dasar_hukum": "Pasal 28 UU KUP - wajib menyelenggarakan pembukuan bagi WP Badan dan OP yang menjalankan usaha.",
    },
    "jurnal": {
        "judul": "Jurnal Umum (Double-Entry)",
        "isi": (
            "Setiap transaksi dicatat minimal pada DUA akun: satu DEBIT, satu KREDIT,\n"
            "dengan jumlah yang SAMA. Inilah inti pembukuan berpasangan.\n\n"
            "Aturan praktis:\n"
            "  • Aset & Beban bertambah di DEBIT, berkurang di KREDIT\n"
            "  • Liabilitas, Ekuitas & Pendapatan bertambah di KREDIT, berkurang di DEBIT\n\n"
            "Contoh - menjual jasa Rp10.000.000 tunai:\n"
            "  DEBIT  Kas               10.000.000\n"
            "  KREDIT Pendapatan Usaha              10.000.000\n\n"
            "Nomor bukti (mis. BKM-001 untuk Bukti Kas Masuk) mengelompokkan baris-baris\n"
            "dari satu transaksi. Aplikasi otomatis menolak jurnal yang tidak seimbang."
        ),
        "dasar_hukum": (
            "Pasal 28 UU KUP jo. Pasal 2 UU No. 8/1997 tentang Dokumen Perusahaan.\n"
            "Dokumen pembukuan wajib disimpan 10 tahun."
        ),
    },
    "penjualan": {
        "judul": "Penjualan & PPN Keluaran",
        "isi": (
            "Subledger ini mencatat semua penjualan dan menghitung PPN keluaran otomatis.\n\n"
            "Jenis PPN yang tersedia:\n"
            "  • Non-PKP/Tidak Dipungut - Anda belum PKP atau penyerahan dibebaskan\n"
            "  • 12% DPP Nilai Lain (11/12) - mekanisme umum sejak 2025, efektif 11%\n"
            "  • 12% DPP Penuh - untuk objek mewah tertentu\n\n"
            "Batas wajib PKP: peredaran bruto melebihi Rp4,8 miliar dalam satu tahun buku.\n"
            "Jika penjualan lunas, aplikasi otomatis membuat jurnal penerimaan kas."
        ),
        "dasar_hukum": (
            "UU No. 7/2021 (UU HPP) Pasal 7 - tarif PPN 12%.\n"
            "PMK 131/PMK.03/2024 - DPP Nilai Lain 11/12 untuk non-mewah.\n"
            "PMK 197/PMK.03/2013 - batas pengusaha kecil Rp4,8 miliar."
        ),
    },
    "pembelian": {
        "judul": "Pembelian & PPN Masukan",
        "isi": (
            "Catat pembelian dengan nilai SEBELUM PPN.\n\n"
            "PPN Masukan hanya dapat dikreditkan (mengurangi PPN keluaran) bila:\n"
            "  • Anda berstatus PKP\n"
            "  • Ada faktur pajak masukan yang sah dan lengkap\n"
            "  • Berhubungan langsung dengan kegiatan usaha\n\n"
            "PPN masukan atas perolehan yang tidak berhubungan dengan usaha, atau\n"
            "kendaraan sedan/station wagon (kecuali untuk dijual/disewakan), TIDAK\n"
            "dapat dikreditkan - PMK 131/2024 & Pasal 9 ayat (8) UU PPN."
        ),
        "dasar_hukum": (
            "Pasal 9 UU PPN jo. UU HPP - mekanisme pengkreditan PPN Masukan.\n"
            "PMK 131/PMK.03/2024."
        ),
    },
    "aset": {
        "judul": "Aset Tetap & Penyusutan",
        "isi": (
            "Aset tetap = harta berumur > 1 tahun yang dipakai dalam usaha.\n\n"
            "Penyusutan KOMERSIAL ditentukan manajemen (bisa garis lurus atau saldo menurun).\n"
            "Penyusutan FISKAL mengikuti PMK 72/2023:\n"
            "  Kelompok 1 (4 thn)  : Garis lurus 25%  | Saldo menurun 50%\n"
            "  Kelompok 2 (8 thn)  : Garis lurus 12,5%| Saldo menurun 25%\n"
            "  Kelompok 3 (16 thn) : Garis lurus 6,25%| Saldo menurun 12,5%\n"
            "  Kelompok 4 (20 thn) : Garis lurus 5%   | Saldo menurun 10%\n"
            "  Bangunan permanen   : Garis lurus 5% (hanya garis lurus)\n"
            "  Bangunan non-permanen: Garis lurus 10%\n\n"
            "Selisih antara penyusutan komersial dan fiskal menjadi koreksi dalam\n"
            "Rekonsiliasi Fiskal (perbedaan temporer / timing difference)."
        ),
        "dasar_hukum": (
            "PMK 72/PMK.03/2023 - kelompok dan tarif penyusutan fiskal.\n"
            "Pasal 11 UU PPh - metode penyusutan.\n"
            "PSAK 16 - aset tetap (komersial)."
        ),
    },
    "pajak": {
        "judul": "Pajak Potong/Pungut (PotPut)",
        "isi": (
            "Sebagai pemotong pajak, Anda WAJIB memotong pajak saat membayar pihak lain.\n\n"
            "PPh 21 - dari penghasilan karyawan. Skema TER bulanan (PMK 168/2023),\n"
            "         perhitungan setahun pada masa Desember.\n"
            "PPh 23 - 2% atas jasa/sewa harta selain tanah & bangunan ke WP Badan;\n"
            "         15% atas bunga, royalti, hadiah.\n"
            "PPh 4(2) - final: sewa tanah/bangunan 10%, konstruksi 1,75%-2,65%,\n"
            "           pengalihan tanah/bangunan 2,5%, bunga deposito 20%.\n"
            "PPh 26 - 20% untuk penerima WPLN (atau tarif P3B).\n\n"
            "Sebagai pihak yang DIPOTONG, pajak itu menjadi KREDIT pajak Anda yang\n"
            "mengurangi PPh Badan terutang."
        ),
        "dasar_hukum": (
            "Pasal 21, 22, 23, 26, dan 4(2) UU PPh.\n"
            "PMK 168/PMK.03/2023 - TER PPh 21.\n"
            "PMK 141/PMK.03/2015 - jenis jasa objek PPh 23."
        ),
    },
    "pph_badan": {
        "judul": "PPh Badan & Pasal 31E",
        "isi": (
            "Tarif umum PPh Badan 22%.\n\n"
            "Fasilitas Pasal 31E: badan dengan peredaran bruto sampai Rp50 miliar\n"
            "mendapat pengurangan 50% dari tarif atas bagian PKP yang berasal dari\n"
            "peredaran bruto sampai Rp4,8 miliar.\n\n"
            "Cara menghitung bila omzet ≤ Rp4,8 miliar:\n"
            "  Seluruh PKP x 11% (tarif efektif)\n\n"
            "Bila omzet antara Rp4,8 M - Rp50 M:\n"
            "  PKP fasilitas  = (4,8M / omzet) x PKP total    tarif 11%\n"
            "  PKP non-fasilitas = PKP total - PKP fasilitas   tarif 22%\n\n"
            "PPh Final UMKM 0,5% (PP 20/2026): hanya untuk WP yang memenuhi syarat\n"
            "subjek dan periode. Aplikasi ini meminta konfirmasi manual sebelum\n"
            "menerapkan skema final agar tidak salah terapkan."
        ),
        "dasar_hukum": (
            "Pasal 17 & 31E UU PPh.\n"
            "PP 55/2022 jo. PP 20/2026 - PPh Final UMKM 0,5%.\n"
            "SE-02/PJ/2015 - contoh perhitungan Pasal 31E."
        ),
    },
    "ppn": {
        "judul": "PPN & SPT Masa",
        "isi": (
            "PPN = PPN Keluaran − PPN Masukan yang dapat dikreditkan.\n\n"
            "Tarif: 12% x DPP Nilai Lain (11/12) = efektif 11% untuk non-mewah.\n\n"
            "Jika hasilnya positif -> kurang bayar, setor dengan kode billing MP.\n"
            "Jika negatif -> lebih bayar, dapat dikompensasikan ke masa berikutnya\n"
            "atau direstitusi.\n\n"
            "Tenggat: setor & lapor paling lambat AKHIR BULAN BERIKUTNYA.\n"
            "Denda terlambat lapor SPT Masa PPN: Rp100.000."
        ),
        "dasar_hukum": (
            "UU No. 7/2021 (UU HPP) Pasal 7 & 9.\n"
            "PMK 131/PMK.03/2024.\n"
            "Pasal 3 & 7 UU KUP - tenggat & sanksi."
        ),
    },
    "rekonsiliasi": {
        "judul": "Rekonsiliasi Fiskal",
        "isi": (
            "Laba komersial (menurut SAK) berbeda dengan laba fiskal (menurut pajak).\n"
            "Rekonsiliasi fiskal menjembatani keduanya.\n\n"
            "KOREKSI POSITIF (menambah laba fiskal):\n"
            "  • Biaya yang tidak deductible: denda pajak, PPh Badan sebagai beban,\n"
            "    sumbangan non-syarat, entertainment tanpa daftar nominatif\n"
            "  • Penyusutan komersial > fiskal\n"
            "  • Cadangan yang tidak diakui fiskal (mis. imbalan kerja)\n\n"
            "KOREKSI NEGATIF (mengurangi laba fiskal):\n"
            "  • Penghasilan yang sudah dikenai PPh Final (bunga deposito, sewa tanah)\n"
            "  • Penghasilan bukan objek pajak (dividen dengan syarat, hibah tertentu)\n"
            "  • Penyusutan fiskal > komersial\n\n"
            "Hasil akhir = PENGHASILAN KENA PAJAK (PKP), dibulatkan ke ribuan ke bawah."
        ),
        "dasar_hukum": (
            "Pasal 4, 6, 9, dan 11 UU PPh.\n"
            "Pasal 1 & 2 UU No. 8/1997 tentang Dokumen Perusahaan."
        ),
    },
    "payroll": {
        "judul": "Payroll & PPh 21",
        "isi": (
            "Perhitungan payroll mencakup:\n\n"
            "GAJI BRUTO = gaji pokok + tunjangan + bonus\n\n"
            "POTONGAN KARYAWAN:\n"
            "  • BPJS Kesehatan 1% (batas upah Rp12 juta)\n"
            "  • JHT 2% | JP 1% (batas upah sesuai ketentuan)\n"
            "  • PPh 21 dengan skema TER bulanan\n\n"
            "TAKE HOME PAY = bruto − potongan karyawan\n\n"
            "BEBAN PERUSAHAAN = bruto + BPJS pemberi kerja\n"
            "  • BPJS Kesehatan 4%\n"
            "  • JHT 3,7% | JKM 0,3% | JKK 0,24% (tergantung risiko) | JP 2%\n\n"
            "PPh 21 skema TER: tarif efektif diterapkan atas penghasilan bruto bulanan.\n"
            "Pada masa Desember dilakukan penghitungan setahun penuh dengan tarif\n"
            "progresif Pasal 17 sebagai koreksi akhir."
        ),
        "dasar_hukum": (
            "PMK 168/PMK.03/2023 - tarif efektif rata-rata (TER).\n"
            "PP 58/2023 - pemotongan PPh 21.\n"
            "Perpres 64/2020 & PP 44/2015 - iuran BPJS.\n"
            "PMK 250/PMK.03/2008 - biaya jabatan."
        ),
    },
    "legal": {
        "judul": "Kewajiban Hukum Pembukuan",
        "isi": (
            "WAJIB PEMBUKUAN\n"
            "  • WP Badan (PT, CV, Koperasi, Yayasan) - wajib pembukuan lengkap\n"
            "  • Orang Pribadi yang menjalankan usaha/praktik bebas - wajib pembukuan\n"
            "    bila peredaran bruto > Rp4,8 M; bila ≤ Rp4,8 M boleh pencatatan\n\n"
            "PENYIMPANAN DOKUMEN\n"
            "  • Wajib menyimpan buku, catatan, dan dokumen dasar 10 tahun\n"
            "  • Dokumen perusahaan (UU No. 8/1997) juga 10 tahun\n\n"
            "SANKSI TIDAK MENYELENGGARAKAN PEMBUKUAN\n"
            "  • Pasal 39 UU KUP: pidana penjara 6 bulan - 6 tahun + denda\n"
            "    2x - 4x jumlah pajak yang tidak/kurang dibayar\n\n"
            "KEWAJIBAN PELAPORAN\n"
            "  • SPT Masa: tiap bulan (PPN, PPh 21/23/4(2), PPh 25)\n"
            "  • SPT Tahunan Badan: paling lambat 30 April (4 bulan)\n"
            "  • SPT Tahunan OP: paling lambat 31 Maret (3 bulan)"
        ),
        "dasar_hukum": (
            "Pasal 28 & 29 UU KUP.\n"
            "Pasal 39 UU KUP - sanksi pidana.\n"
            "UU No. 8/1997 tentang Dokumen Perusahaan.\n"
            "Pasal 3 UU KUP - tenggat pelaporan SPT."
        ),
    },
    "bentuk_badan": {
        "judul": "Memilih Bentuk Badan Usaha",
        "isi": (
            "UMKM ORANG PRIBADI\n"
            "  • Tanpa badan hukum, mendaftar NPWP pribadi + KLU usaha\n"
            "  • Pembukuan: SAK EMKM (3 laporan)\n"
            "  • Pajak: PPh Final 0,5% bila memenuhi syarat, atau tarif Pasal 17\n\n"
            "PERSEROAN PERORANGAN (PT Perorangan)\n"
            "  • Badan hukum, didirikan 1 orang WNI, kriteria UMK\n"
            "  • Dasar: UU 11/2020 jo. UU 6/2023, PP 8/2021\n"
            "  • Tanggung jawab terbatas, tidak perlu akta notaris\n"
            "  • Pajak: PPh Badan (22% / fasilitas 31E)\n\n"
            "PT (PERSEROAN TERBATAS)\n"
            "  • Badan hukum penuh, dasar UU 40/2007 jo. UU 6/2023\n"
            "  • Modal dasar minimal Rp50 juta (minimal 25% disetor)\n"
            "  • Wajib RUPS tahunan, pembukuan lengkap\n"
            "  • Pajak: PPh Badan 22%, fasilitas 31E bila omzet ≤ Rp50 M\n\n"
            "Pilih bentuk sesuai kebutuhan: tanggung jawab, modal, dan skala usaha."
        ),
        "dasar_hukum": (
            "UU No. 40/2007 tentang Perseroan Terbatas.\n"
            "UU No. 11/2020 jo. UU No. 6/2023 (Cipta Kerja).\n"
            "PP No. 8/2021 tentang Modal Dasar Perseroan serta Pendaftaran\n"
            "Pendirian, Perubahan, dan Pembubaran Perseroan yang Memenuhi\n"
            "Kriteria untuk Usaha Mikro dan Kecil.\n"
            "PP No. 7/2021 tentang Kemudahan, Perlindungan, dan Pemberdayaan\n"
            "UMK."
        ),
    },
}
