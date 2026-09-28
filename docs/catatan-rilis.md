# Catatan Rilis AkunTuntas

Berkas ini memuat daftar perubahan setiap versi. Dipakai untuk mengisi
kolom **What's new** di Microsoft Partner Center, dan untuk memberi tahu
pengguna apa yang berubah setelah pemasangan.

---

## Versi 1.2.6 - 28 September 2026

### Perbaikan tampilan halaman masuk

**Halaman masuk ditata ulang mengikuti gaya yang bersih.**
Kotak berlatar abu di bawah tombol masuk dihapus. Keterangan akun bawaan
kini tampil sebagai teks biasa, bukan kotak, sehingga halaman masuk
terlihat rapi seperti halaman dialog aplikasi lainnya.

**Formulir memakai lebar penuh yang direncanakan.**
Sebelumnya kolom isian hanya selebar 259 piksel, sedangkan keterangan di
bawahnya meluber sampai 640 piksel sehingga tampak tidak sejajar. Kini
seluruh elemen formulir sama lebar 400 piksel dan rata pada satu garis,
di semua ukuran jendela.

**Teks kecil dibuat lebih jelas terbaca.**
Warna teks keterangan dinaikkan kontrasnya. Keterangan kata sandi bawaan
kini memakai ukuran dan warna yang lebih tegas supaya pengguna baru tidak
melewatkannya. Seluruh teks memenuhi standar kontras WCAG AA.

### Alur lisensi

**Pengguna yang belum punya lisensi diarahkan ke situs resmi.**
Pada layar aktivasi dan layar batas paket, pengguna diarahkan ke halaman
pembelian di akuntuntas.xinet.id, bukan ke alamat surel.

---

## Versi 1.2.5 - 28 September 2026

### Perbaikan tampilan

**Judul jendela tidak lagi menampilkan nama aplikasi dua kali.**
Sebelumnya judul jendela berbunyi "AkunTuntas - Pembukuan & Pajak
Perusahaan Indonesia - AkunTuntas". Nama aplikasi ditambahkan Qt di
belakang judul yang sudah memuat nama itu. Kini judulnya bersih.

**Halaman masuk ditata ulang.**
Kolom isian, tombol masuk, dan kotak keterangan akun bawaan kini sama
lebar dan sejajar. Sebelumnya kolom isian hanya selebar 259 piksel
sementara kotak keterangan meluber sampai 640 piksel, sehingga halaman
tampak tidak rapi. Lebar formulir kini tetap 400 piksel pada semua
ukuran jendela, dan seluruh elemennya rata pada satu garis.

**Laporan keuangan lebih mudah dipahami.**
Bila laba besar tetapi kas negatif, muncul keterangan yang menjelaskan
sebabnya, supaya angkanya tidak membingungkan.

**Penilaian rasio keuangan diperbaiki.**
Sebelumnya rasio kas negatif dinilai "Sangat Baik" dan rasio lancar yang
sehat dinilai "Berisiko Tinggi". Arah penilaian kini benar.

**Penulisan angka diseragamkan.**
Seluruh angka memakai koma sebagai tanda desimal dan titik sebagai
pemisah ribuan, sesuai kebiasaan Indonesia. Uang negatif ditulis
"-Rp168.837.000", bukan "Rp-168.837.000".

### Fitur baru

**Setiap temuan analisis kini punya tombol tindak lanjut.**
Setelah analisis keuangan menampilkan temuan, tersedia tombol yang
langsung membuka halaman terkait untuk menindaklanjuti temuan itu,
misalnya "Buka Kas & Bank" atau "Buka Jurnal Umum".

**Ekspor ke Excel dan cetak A4.**
Seluruh daftar dan laporan dapat diekspor ke berkas Excel yang angkanya
tetap dapat dijumlahkan, serta dicetak pada ukuran kertas A4.

### Alur lisensi

**Pengguna yang belum punya lisensi diarahkan ke situs resmi.**
Pada layar aktivasi dan layar batas paket, pengguna kini diarahkan ke
halaman pembelian di akuntuntas.xinet.id, bukan ke alamat surel. Di situs
tersedia keterangan paket, harga, dan cara pembayaran yang lengkap.

### Perbaikan lain

- Tanda "&" pada tombol tidak lagi tampil sebagai garis bawah.
- Nama bentuk badan usaha tidak lagi muncul dua kali pada keterangan
  perusahaan, misalnya "PT Xinet persada - PT".
- Kata "peringatan" tidak lagi menyelip di awal kalimat ringkasan.
- Keterangan pada halaman analisis tidak lagi mewarisi warna ke anak
  elemennya.
- Pemasang aplikasi diperkecil dari 107 MB menjadi 92 MB dengan membuang
  pustaka multimedia yang tidak dipakai, sehingga dapat diunggah ke
  GitHub dan diunduh lebih cepat.

---

## Versi 1.2.4 - 27 September 2026

- Ekspor seluruh daftar ke Excel dengan angka bertipe angka.
- Cetak dokumen pada kertas A4 dengan pratinjau.
- Penjaga keseimbangan jurnal di lapisan basis data: jurnal yang tidak
  seimbang ditolak walau ditulis langsung ke tabel.
- Pemisahan data antar perusahaan diperketat pada 53 tabel.
- Halaman kontak di situs dengan formulir dan tombol WhatsApp.
- Perbaikan impor CSV: tanggal gaya Indonesia (15/03/2026) diterima.

---

## Versi 1.2.3 - 26 September 2026

- Perbaikan tampilan tabel perbandingan paket di situs.
- Penanda baris perbandingan dua jenis: fitur khusus Enterprise dan fitur
  yang batasannya berbeda.
- Perbaikan halaman pengaturan: ukuran berkas memakai koma desimal.

---

## Versi 1.2.2 - 26 September 2026

- Redesign Dashboard dan Analisis Keuangan.
- Penjelasan istilah rasio keuangan pada mode Pemula.
- Perbaikan logika penilaian rasio.
- Pemasang aplikasi diperkecil agar dapat diunggah.

---

## Versi 1.2.1 - 25 September 2026

- Perbaikan gaya lencana nomor pada panduan langkah awal.
- Panduan langkah awal muncul saat pembukuan masih kosong.
- Keadaan kosong diperjelas dan penilaian yang menyesatkan diperbaiki.

---

## Versi 1.2.0 - 25 September 2026

- Pemisahan data antar perusahaan.
- Pemeriksaan keseimbangan jurnal.
- Perbaikan 4 celah keamanan lisensi.
- Perbaikan buku besar yang menampilkan pendapatan sebagai negatif.
- Perbaikan kartu stok yang menyesatkan.
- Impor CSV menerima tanggal gaya Indonesia.

---

## Versi 1.1.0 - 24 September 2026

- Kwitansi dan bukti transaksi.
- Dashboard admin untuk pengelolaan lisensi.
- Pembayaran melalui iPaymu, termasuk QRIS.
- Perbaikan deteksi versi Windows (Windows 11 tidak lagi terbaca
  Windows 10).

---

## Versi 1.0.0 - 24 September 2026

Versi pertama.

- Pembukuan berpasangan dengan pemeriksaan debit dan kredit.
- Bagan akun siap pakai untuk lima bentuk badan usaha.
- Penjualan, pembelian, kas dan bank, biaya, persediaan FIFO dan
  rata-rata bergerak, aset tetap beserta penyusutan, kontrak, payroll.
- Perhitungan PPh 21 TER, PPh Badan, PPh Final UMKM, PPN, dan PPh 23.
- Checklist kepatuhan pajak.
- Laporan keuangan sesuai SAK EMKM, SAK EP, dan SAK Umum.
- Jejak audit yang mencatat setiap perubahan data.
- Dua mode pemakaian: Pemula dan Ahli.
- Cadangan otomatis dan pemulihan data.
- Keranjang sampah dengan pemulihan.
