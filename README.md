# AkunTuntas

## Pembukuan dan Pajak Perusahaan Indonesia

Versi 1.0.0, Edisi Regulasi 2026

Aplikasi desktop Windows untuk pembukuan dan perpajakan, dirancang untuk
usaha mikro, kecil, dan menengah (UMKM), Perseroan Perorangan, hingga
Perseroan Terbatas (PT). Seluruh data tersimpan lokal di komputer Anda.
Tidak ada koneksi internet, tidak ada server, dan tidak ada data yang
dikirim ke mana pun.

## Lisensi

Aplikasi ini dijual dengan lisensi sekali bayar yang berlaku selamanya.

| Paket | Harga | Perangkat | Fitur |
|---|---|---|---|
| Standar | Rp3.499.000 | 1 | Pembukuan, pajak dasar, laporan SAK EMKM |
| Enterprise | Rp5.499.000 | 5 | Seluruh fitur, termasuk konsolidasi dan pajak lanjutan |

Aktivasi dilakukan sekali di awal. Setelah aktif, aplikasi berjalan penuh
tanpa internet. Keterangan lisensi diperiksa berkala ke server supaya
lisensi yang dicabut karena pelanggaran dapat berhenti berlaku.

Situs resmi: https://akuntuntas.xinet.id

Pembelian dan pertanyaan lisensi: akuntuntas@gmail.com

## Daftar Isi

1. Memulai Cepat
2. Fitur Utama
3. Alur Kerja yang Disarankan
4. Dasar Hukum yang Diimplementasikan
5. Keamanan dan Privasi
6. Pertanyaan Umum
7. Pemecahan Masalah

## Memulai Cepat

### Login Pertama Kali

| Keterangan | Nilai |
|---|---|
| Nama pengguna | admin |
| Password | admin123 |

Penting: saat pertama kali masuk, aplikasi akan meminta Anda mengganti
password. Ini wajib dilakukan demi keamanan data pembukuan.

### Pilihan Mode

Setelah login, Anda akan diminta memilih mode penggunaan:

- **Mode Pemula.** Setiap halaman menampilkan panel penjelasan konsep
  akuntansi dan pajak dalam bahasa sehari-hari, lengkap dengan contoh dan
  dasar hukumnya. Cocok bila Anda baru memulai pembukuan.
- **Mode Ahli.** Antarmuka ringkas tanpa panel penjelasan. Seluruh fitur
  tetap lengkap. Cocok bila Anda sudah memahami dasar akuntansi.

Pilihan ini hanya muncul sekali. Setelah itu mode dapat diubah kapan saja
di menu Pengaturan, Preferensi.

### Langkah Pertama (5 Menit)

1. **Buat profil perusahaan** pada menu Data Perusahaan. Pilih bentuk badan
   usaha dengan tepat; aplikasi otomatis menyiapkan bagan akun yang sesuai.
2. **Isi saldo awal** pada menu Bagan Akun, Kelola Saldo Awal. Bila usaha
   Anda sudah berjalan sebelumnya, masukkan posisi kas, persediaan, utang,
   dan modal pada tanggal mulai pembukuan. Pastikan total debit sama dengan
   total kredit.
3. **Lengkapi pengaturan pajak** pada menu Data Perusahaan, Ubah Pengaturan
   Pajak: status PKP, skema PPh, dan omzet tahun sebelumnya.
4. **Mulai catat transaksi** melalui menu Penjualan, Pembelian, atau
   Jurnal Umum.

## Fitur Utama

### Pembukuan dan Laporan

- Jurnal umum berpasangan (double-entry) dengan validasi otomatis.
  Aplikasi menolak jurnal yang tidak seimbang.
- Buku besar per akun dengan saldo berjalan.
- Neraca saldo dengan kontrol keseimbangan debit dan kredit.
- Laporan Laba Rugi bertahap: laba kotor, laba operasional, laba bersih.
- Neraca dengan persamaan Aset sama dengan Liabilitas ditambah Ekuitas yang
  selalu diverifikasi.
- Laporan Arus Kas metode langsung, diklasifikasikan ke aktivitas operasi,
  investasi, dan pendanaan.
- Laporan Perubahan Ekuitas.
- Ringkasan bulanan dan ekspor Excel serta PDF.

### Perpajakan

- PPh Badan tarif 22% dengan fasilitas Pasal 31E, perhitungan proporsional
  otomatis untuk omzet Rp4,8 miliar sampai Rp50 miliar.
- PPh Final UMKM 0,5% dengan gerbang verifikasi kelayakan agar tidak salah
  terapkan.
- PPN dengan mekanisme DPP Nilai Lain 11/12 (efektif 11%) dan DPP penuh 12%.
- PPh 21 skema Tarif Efektif Rata-rata (TER) bulanan kategori A, B, dan C
  sesuai PMK 168/2023, perhitungan setahun pada masa Desember, plus TER
  Harian.
- PPh 22, 23, 26, dan 4(2) lengkap dengan tarif terkini.
- Penyusutan fiskal sesuai PMK 72/2023 untuk Kelompok 1 sampai 4 dan
  bangunan.
- Rekonsiliasi fiskal otomatis: koreksi positif dan negatif dari akun
  non-deductible, penghasilan final, dan selisih penyusutan.
- Kalender pajak dengan tenggat setor dan lapor.
- Kalkulator sanksi: bunga keterlambatan, denda telat lapor, sanksi SKPKB.
- Nomor Seri Faktur Pajak (NSFP) serta faktur pajak keluaran dan masukan.
- Uang muka (panjar) dari pelanggan dan ke pemasok.
- Bea meterai untuk dokumen bernilai di atas Rp5 juta.
- Pajak daerah (PBJT) untuk makanan dan minuman, hiburan, perhotelan, serta
  parkir.
- Kurs mata uang asing dan perhitungan selisih kurs.
- PPh Pasal 15 untuk pelayaran dan penerbangan.
- Jurnal balik untuk akrual akhir periode.

### Analisis Kesehatan Keuangan

Mesin analisis memeriksa lebih dari 30 aspek dan memberi diagnosis otomatis:

- **Integritas pembukuan.** Jurnal tidak seimbang, neraca pincang, saldo kas
  negatif, akun tanpa saldo awal.
- **Likuiditas.** Rasio lancar, rasio kas, kecukupan kas terhadap kewajiban.
- **Profitabilitas.** Margin kotor, operasional, dan bersih; ROA; ROE; beban
  terhadap pendapatan.
- **Solvabilitas.** Rasio utang terhadap ekuitas dan terhadap aset.
- **Kepatuhan pajak.** Progres batas PKP, pemotongan belum disetor, tenggat
  terdekat, kelengkapan payroll.
- **Kualitas data.** Jurnal tanpa keterangan dan tanpa lawan transaksi.

Setiap temuan dilengkapi penjelasan artinya, tindakan yang perlu diambil,
dampak bila dibiarkan, dan dasar hukumnya. Skor 0 sampai 100 dengan grade
A sampai E.

### Transaksi Otomatis Berjurnal

Setiap transaksi pada menu Penjualan, Pembelian, Payroll, Aset Tetap, dan
Pajak otomatis menghasilkan jurnal. Anda tidak perlu menjurnal manual,
namun tetap bisa bila ingin.

### Penjualan Lengkap

- Alur Sales Order, Invoice, Penerimaan, dan Pelunasan dalam satu rangkaian.
- Invoice dengan nomor otomatis, dapat dicetak sebagai PDF lengkap dengan
  logo perusahaan, NPWP, dan tanda tangan.
- Diskon per baris (persen) maupun tingkat invoice (nilai atau persen).
- PPN otomatis sesuai status PKP dan jenis barang.
- Nota kredit untuk retur penjualan dengan jurnal balik otomatis.
- Penerimaan pembayaran sebagian dengan alokasi ke beberapa invoice.
- Pembatalan transaksi dengan pemulihan stok dan jurnal balik.
- Aging piutang (belum jatuh tempo, 1 sampai 30, 31 sampai 60, 61 sampai 90,
  dan lebih dari 90 hari) per pelanggan, lengkap dengan tombol pembuatan
  pengingat penagihan.

### Pembelian Lengkap

- Alur Purchase Order, Bill, dan Pembayaran Vendor dalam satu rangkaian.
- Bill otomatis menambah persediaan dan mengakui utang usaha.
- Pembayaran ke vendor dengan alokasi ke beberapa bill sekaligus, plus
  validasi kelebihan bayar.
- Retur pembelian dengan pengurangan utang dan pengeluaran stok.
- Aging utang per pemasok dengan pengingat jatuh tempo.

### Kas dan Bank

- Multi rekening: kas tunai, beberapa rekening bank, dan dompet digital
  (e-wallet), masing-masing terhubung ke akun buku.
- Transfer antar rekening termasuk biaya transfer otomatis.
- Impor mutasi rekening koran dari CSV dengan pengenalan kolom otomatis dan
  deteksi duplikat.
- Rekonsiliasi bank: bandingkan saldo bank dengan saldo buku, cocokkan mutasi
  ke jurnal, tandai dikecualikan, dan simpan riwayat rekonsiliasi.

### Biaya dan Pengeluaran

- Alur pengajuan, persetujuan, dan pembayaran dengan pemisahan tugas.
- Kategori biaya dengan batas nilai dan aturan wajib persetujuan.
- Lampiran bukti (foto atau scan kuitansi) tersimpan bersama catatan biaya.
- Dimensi: biaya dapat ditandai ke cost center, proyek, dan cabang.

### Pelanggan dan Pemasok

- Data lengkap: NPWP atau NIK, alamat, kontak, termin pembayaran, batas
  kredit.
- Riwayat transaksi dan ringkasan saldo per mitra (piutang atau utang).
- Pencarian dan filter cepat.

### Produk dan Persediaan

- Barang dan jasa dengan akun persediaan, pendapatan, dan HPP masing-masing.
- Dua metode HPP: Average (rata-rata bergerak) dan FIFO (first in first out).
- Multi gudang dengan transfer antar gudang.
- Kartu stok per produk dengan saldo berjalan.
- Stock opname dengan jurnal penyesuaian selisih otomatis.
- Peringatan stok menipis berdasarkan stok minimum.

### Dimensi dan Pusat Biaya

- Cost center, proyek, dan cabang untuk analisis per unit usaha.
- Laba rugi per dimensi untuk melihat unit mana yang paling efisien.
- Anggaran dibanding realisasi per cost center dan per proyek.

### Tutup Buku dan Otomasi

- Tutup buku per periode (bulanan) atau seluruh tahun sekaligus. Periode
  tertutup menolak jurnal baru, dan setiap pembukaan kembali wajib
  menyertakan alasan yang tercatat di log audit.
- Jurnal berulang: template untuk transaksi rutin (sewa, cicilan,
  penyusutan) dengan frekuensi harian, mingguan, bulanan, triwulanan, atau
  tahunan.
- Pengingat jatuh tempo untuk piutang dan utang.

### Konsolidasi dan Multi Entitas

- Grup entitas dengan persentase kepemilikan.
- Laporan konsolidasi yang menjumlahkan seluruh anggota sesuai porsi
  kepemilikan, lengkap dengan catatan eliminasi transaksi antar entitas.

### Akses Jaringan Lokal (LAN)

- Mode server dan klien untuk berbagi data antar komputer kantor tanpa
  internet, dilindungi token akses.
- Cadangan dan pemulihan basis data dengan satu klik, plus catatan riwayat
  cadangan.

### Tata Kelola dan Pengendalian Internal

- Pengguna dan peran (Pemilik, Administrator, Staf, Hanya Lihat) dengan hak
  akses per modul yang dapat disesuaikan per pengguna.
- Log audit merekam siapa melakukan apa dan kapan.
- Riwayat perubahan data per tabel dan per catatan.
- Keranjang sampah: data yang dihapus dapat dipulihkan; pembersihan permanen
  hanya untuk data lama.
- Lampiran dokumen pada catatan transaksi.

### Impor Data Massal

- Impor pelanggan, pemasok, produk, dan jurnal dari CSV.
- Template CSV siap unduh untuk tiap jenis data.
- Deteksi duplikat otomatis: baris ganda dilewati, bukan digandakan.
- Pratinjau dan laporan hasil impor.

### Pencarian Global

Cari satu kata kunci di seluruh data: invoice, bill, pelanggan, produk,
jurnal, aset, biaya, dan proyek. Hasilnya langsung menuju catatannya.

### Payroll

- Perhitungan gaji, tunjangan, bonus, dan THR.
- BPJS Kesehatan (4% dan 1%) serta Ketenagakerjaan (JHT 3,7% dan 2%,
  JP 2% dan 1%, JKM 0,3%, JKK 0,24% sampai 1,74%).
- PPh 21 otomatis dengan skema TER.
- Jurnal payroll otomatis.

### Aset Tetap

- Penyusutan komersial (garis lurus, PSAK 16) dan fiskal (PMK 72/2023)
  dihitung terpisah.
- Prorata bulan pada tahun perolehan.
- Selisih otomatis menjadi koreksi rekonsiliasi fiskal.
- Jurnal penyusutan otomatis.

### Checklist Kepatuhan

Daftar periksa bulanan dan tahunan: rekonsiliasi kas, PPh 21, PPh 23,
PPh 4(2), PPN, aset tetap, stock opname, review fiskal, SPT Tahunan, dan
pengarsipan dokumen.

## Alur Kerja yang Disarankan

```
TAHAP 1: PENYIAPAN (sekali saja)
  Buat profil perusahaan (Data Perusahaan)
  Isi saldo awal (Bagan Akun, Kelola Saldo Awal)
  Lengkapi pengaturan pajak (status PKP, skema PPh)

TAHAP 2: INPUT RUTIN (harian atau mingguan)
  Catat penjualan, PPN keluaran dan jurnal otomatis
  Catat pembelian, PPN masukan dan jurnal otomatis
  Transaksi lain lewat Jurnal Umum (12 contoh jurnal tersedia)

TAHAP 3: BULANAN
  Jalankan Payroll (PPh 21 otomatis)
  Catat pemotongan PPh 23 dan PPh 4(2) bila ada
  Catat setoran pajak setelah membayar via bank
  Rekonsiliasi bank (impor mutasi rekening koran)
  Review Aging Piutang dan Utang, kirim pengingat
  Jalankan Checklist Kepatuhan
  Periksa Dashboard, tangani temuan kritis
  Tutup buku periode setelah semua beres

TAHAP 4: TAHUNAN
  Hitung penyusutan aset (Aset Tetap)
  Review Rekonsiliasi Fiskal dan akun Review Fiskal
  Cek PPh Badan terutang dan angsuran PPh 25
  Cetak laporan (Excel atau PDF)
  Stock opname persediaan
  Susun laporan konsolidasi bila punya beberapa entitas
  Buat cadangan data
```

### Jurnal Umum

Setiap transaksi dicatat pada minimal dua akun: satu debit, satu kredit,
dengan jumlah sama.

| Bertambah di | Akun |
|---|---|
| Debit | Aset, Beban, Prive |
| Kredit | Liabilitas, Ekuitas, Pendapatan |

Aplikasi menampilkan indikator keseimbangan secara langsung. Tersedia
12 contoh jurnal standar yang dapat diisi otomatis sebagai pembelajaran.

### Alur Penjualan (Order sampai Pelunasan)

```
Sales Order (opsional) menjadi Invoice, lalu Penerimaan, lalu Pelunasan
                        jurnal          jurnal        aging bersih
```

1. **Sales Order** (opsional). Pesanan pelanggan; belum menjadi transaksi
   akuntansi.
2. **Invoice.** Di sinilah pendapatan diakui. Stok berkurang, HPP dihitung
   dengan metode produk (Average atau FIFO), PPN dihitung sesuai status PKP.
   Invoice dapat dicetak sebagai PDF.
3. **Penerimaan.** Catat uang masuk. Satu penerimaan dapat dialokasikan ke
   beberapa invoice sekaligus.
4. **Nota Kredit.** Bila ada retur, stok masuk kembali dan pendapatan
   dikurangi lewat jurnal balik.

### Alur Pembelian (Order sampai Pembayaran)

```
Purchase Order (opsional) menjadi Bill, lalu Pembayaran Vendor
                            jurnal        jurnal
```

Bill menambah persediaan, mengakui utang usaha, dan mencatat PPN masukan.
Pembayaran dapat dialokasikan ke beberapa bill dengan validasi agar tidak
melebihi jumlah utang.

### Rekonsiliasi Bank

Unduh mutasi dari internet banking (CSV), impor di menu Kas dan Bank, lalu
cocokkan setiap mutasi ke akun lawan yang tepat. Aplikasi menampilkan
selisih antara saldo bank dan saldo buku secara langsung, sehingga kesalahan
pencatatan cepat terdeteksi.

### Penjualan

Masukkan nilai sebelum PPN. Aplikasi menghitung PPN dan membuat jurnal:

```
DEBIT   Kas atau Bank (atau Piutang Usaha)   Rp11.100.000
KREDIT  Pendapatan Usaha                                  Rp10.000.000
KREDIT  Utang PPN                                          Rp1.100.000
```

### Pembelian

PPN masukan yang dapat dikreditkan dicatat sebagai aset, bukan beban. Bila
tidak dapat dikreditkan, nilainya dibebankan.

### Rekonsiliasi Fiskal

Aplikasi otomatis menghitung:

| Koreksi | Sumber |
|---|---|
| Positif | Akun bertanda Non-Deductible, misalnya denda pajak |
| Positif | Penyusutan komersial lebih besar daripada fiskal |
| Negatif | Akun bertanda Final Income, misalnya bunga deposito |
| Negatif | Penyusutan fiskal lebih besar daripada komersial |
| Manual | Input pengguna dengan dokumen pendukung |

Hasil akhir: Penghasilan Kena Pajak, dibulatkan ke ribuan ke bawah.

## Dasar Hukum yang Diimplementasikan

| Topik | Dasar Hukum |
|---|---|
| Kewajiban pembukuan | Pasal 28 UU KUP |
| Penyimpanan dokumen 10 tahun | Pasal 28 ayat (8) UU KUP; UU No. 8/1997 |
| Sanksi tidak membukukan | Pasal 39 UU KUP |
| Tarif PPh Badan 22% | UU No. 7/2021 (UU HPP) Pasal 17 ayat (1) huruf b |
| Fasilitas Pasal 31E | UU PPh Pasal 31E; SE-02/PJ/2015 |
| Pembulatan PKP | UU PPh Pasal 17 ayat (4) |
| Kompensasi rugi 5 tahun | UU PPh Pasal 6 ayat (2) |
| PPh Final UMKM 0,5% | PP 55/2022 jo. PP 20/2026 |
| PPN 12% | UU No. 7/2021 (UU HPP) Pasal 7 |
| PPN DPP Nilai Lain 11/12 | PMK 131/PMK.03/2024 |
| Batas wajib PKP Rp4,8 miliar | PMK 197/PMK.03/2013; PP 44/2022 |
| PPh 21 skema TER | PMK 168/PMK.03/2023; PP 58/2023 |
| Biaya jabatan | PMK 250/PMK.03/2008 |
| PTKP | PMK 101/PMK.010/2016 |
| PPh 23 jasa dan sewa | UU PPh Pasal 23; PMK 141/PMK.03/2015 |
| PPh 22 | UU PPh Pasal 22; PMK 34/2017 |
| PPh 26 | UU PPh Pasal 26 |
| PPh Final 4(2) sewa tanah | PP 34/2017 |
| PPh Final 4(2) konstruksi | PP 9/2022 |
| PPh Final pengalihan tanah | PP 34/2016 |
| Penyusutan fiskal | PMK 72/PMK.03/2023; UU PPh Pasal 11 |
| Denda telat lapor | Pasal 7 UU KUP |
| Bunga telat setor | UU HPP Pasal 9 ayat (2a) dan (2b); PMK 81/2024 |
| Sanksi kurang bayar 2% per bulan | Pasal 13 ayat (2) UU KUP |
| PPh 15 pelayaran dan penerbangan | KMK 416, 417, dan 475/KMK.04/1996 |
| Bea meterai | UU No. 10/2020; PP 86/2021 |
| Pajak daerah (PBJT) | UU No. 1/2022 (HKPD) Pasal 55 |
| Kurs untuk keperluan pajak | PMK 196/PMK.03/2007; PSAK 52 |
| BPJS Kesehatan | Perpres 64/2020 |
| BPJS Ketenagakerjaan | PP 44/2015; PP 46/2015 |
| SAK EMKM | Keputusan Ketua DSAK IAI |
| SAK Entitas Privat | DSAK IAI (efektif 1 Januari 2025) |
| PSAK umum | PSAK 1, 2, 14, 16, 46, 71, 73 |
| Perseroan Terbatas | UU No. 40/2007 jo. UU No. 6/2023 |
| Perseroan Perorangan | UU No. 11/2020 jo. UU No. 6/2023; PP 8/2021 |
| Kriteria UMKM | PP No. 7/2021 |
| Akuntansi proyek dan konstruksi | PSAK 34; PSAK 72 |
| Laporan konsolidasian | PSAK 65; PSAK 4 |
| Provisi dan liabilitas kontinjensi | PSAK 57 |
| Zakat, bantuan, dan hibahan | PMK 114/2025 |

Catatan: selalu periksa pembaruan regulasi. Aplikasi memuat ketentuan sampai
edisi yang tertera pada halaman Bantuan, Tentang Aplikasi.

### Bukti Keselarasan Regulasi

Salinan resmi regulasi tersimpan di `docs/pajak2026/`, diunduh dari
pajak.go.id dan peraturan.bpk.go.id. Aplikasi menyertakan alat dan tes yang
membandingkan angka di kode dengan isi dokumen resmi:

| Pemeriksaan | Cara menjalankan |
|---|---|
| Tabel TER PPh 21 vs PMK 168/2023 (lapisan dan tarif) | `python tools/verifikasi_ter.py` |
| Angka pajak vs regulasi (70 pemeriksaan) | `python tests/test_kepatuhan_pajak.py` |

Hasil terakhir: ketiga tabel TER (A, B, C) cocok 100% dengan dokumen resmi,
dan seluruh 70 pemeriksaan kepatuhan lulus.

## Keamanan dan Privasi

| Aspek | Implementasi |
|---|---|
| Penyimpanan data | SQLite lokal di `%LOCALAPPDATA%\AkunTuntas\` |
| Koneksi internet | Tidak ada; aplikasi bekerja sepenuhnya offline |
| Password | PBKDF2-HMAC-SHA256, 480.000 iterasi, salt acak 16 byte |
| Percobaan login | Dibatasi 5 kali, lalu akun terkunci 5 menit |
| Multi-pengguna | Peran: Pemilik, Administrator, Staf, Hanya Lihat |
| Jejak audit | Seluruh aktivitas penting tercatat (waktu, pengguna, aksi) |
| Cadangan | Manual dan cadangan otomatis sebelum pemulihan |

### Lokasi Data

```
%LOCALAPPDATA%\AkunTuntas\
  akuntuntas.db      basis data utama
  backup\            cadangan otomatis dan manual
  export\            hasil ekspor laporan
  lampiran\          folder lampiran
  akuntuntas.log     catatan teknis aplikasi
```

Disarankan membuat cadangan berkala dan menyimpannya di lokasi lain,
misalnya flashdisk atau drive eksternal.

## Pertanyaan Umum

**Apakah data saya aman bila komputer rusak?**

Data tersimpan lokal, jadi Anda perlu membuat cadangan berkala dan
menyimpannya di lokasi terpisah. Menu Pengaturan, Cadangan dan Data.

**Bisakah memakai lebih dari satu perusahaan?**

Bisa. Buat beberapa profil perusahaan, lalu ganti perusahaan aktif di menu
Pengaturan, Preferensi.

**Bagaimana bila saya salah input?**

Hapus transaksi pada halaman terkait; jurnalnya ikut terhapus. Untuk jurnal
manual, gunakan Jurnal Umum, Hapus.

**Apakah saya wajib PKP?**

Wajib bila peredaran bruto melebihi Rp4,8 miliar setahun. Aplikasi memantau
progres Anda dan memberi peringatan pada Dashboard.

**Apakah bisa memakai PPh Final 0,5%?**

Bergantung bentuk badan, peredaran bruto, dan periode pemanfaatan. Aplikasi
tidak menerapkan tarif final sebelum Anda mengonfirmasi kelayakan di menu
Data Perusahaan, Ubah Pengaturan Pajak, untuk menghindari kekeliruan.

**Bagaimana bila lupa password?**

Minta pengguna berperan Pemilik mereset password Anda di menu Pengaturan,
Pengguna. Bila Anda satu-satunya pengguna, buat berkas `reset_admin.txt` di
folder data lalu jalankan ulang aplikasi.

**Apakah laporan bisa diberikan ke bank atau kantor pajak?**

Ya. Gunakan Laporan Keuangan, Ekspor Excel atau PDF. Untuk keperluan resmi,
verifikasi terlebih dahulu kebenaran datanya.

## Pemecahan Masalah

| Gejala | Penyebab dan Solusi |
|---|---|
| Aplikasi tidak terbuka | Cek `%LOCALAPPDATA%\AkunTuntas\akuntuntas.log`. Pastikan tidak ada proses lain yang memakai basis data. |
| Neraca tidak seimbang | Periksa saldo awal di Bagan Akun; total debit harus sama dengan total kredit. Periksa juga akun dengan baris neraca kosong. |
| Angka laporan tidak sesuai | Periksa apakah ada jurnal tidak seimbang di Jurnal Umum (ditandai merah). |
| PPN tidak terhitung | Periksa status PKP di Data Perusahaan, dan jenis PPN pada transaksi. |
| Penyusutan nol | Buka Aset Tetap, lalu jalankan Hitung Penyusutan Tahun Ini. |
| Data hilang | Pulihkan dari cadangan di menu Pengaturan, Cadangan dan Data. |

### Kontak Bantuan

Sebelum menghubungi bantuan, siapkan:

1. Isi berkas `akuntuntas.log`
2. Versi aplikasi (menu Bantuan, Tentang)
3. Langkah yang dilakukan sebelum masalah muncul

## Pernyataan Penggunaan

Aplikasi ini dirancang untuk membantu administrasi pembukuan dan estimasi
perpajakan bagi usaha mikro, kecil, dan menengah hingga perseroan terbatas
di Indonesia. Aplikasi membantu menyusun pembukuan berpasangan, menghasilkan
laporan keuangan sesuai standar akuntansi, menghitung pajak berdasarkan
ketentuan yang berlaku, serta menganalisis kesehatan keuangan usaha.

Namun perlu dipahami: aplikasi ini tidak menggantikan pertimbangan
profesional. Transaksi yang bersifat khusus, fasilitas perpajakan tertentu,
industri dengan perlakuan khusus, serta interpretasi atas regulasi tetap
perlu diverifikasi sesuai fakta dan ketentuan terbaru, sebaiknya dengan
bantuan konsultan pajak atau akuntan bersertifikat.

AkunTuntas v1.0.0, Edisi Regulasi 2026
