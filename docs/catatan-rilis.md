# Catatan Rilis AkunTuntas

Berkas ini memuat riwayat perubahan setiap versi. Dipakai untuk mengisi
kolom **What's new** di Microsoft Partner Center, dan untuk memberi tahu
pengguna apa yang berubah setelah pemasangan.

Versi yang sama tampil untuk umum di https://akuntuntas.xinet.id/rilis
(berkas `web/rilis.html`). Bila mengubah berkas ini, perbarui juga halaman
webnya supaya isinya tidak berbeda.

---

## Versi 1.2.7 - 28 September 2026

Versi terbaru.

### Masa uji coba 1 hari untuk pemasangan dari Microsoft Store

Aplikasi yang dipasang dari Microsoft Store kini mendapat masa uji coba
**1 hari** sejak pertama kali dibuka. Seluruh fitur paket Enterprise
terbuka selama masa itu, sehingga calon pembeli dapat menilai aplikasi
sepenuhnya sebelum memutuskan.

Setelah masa uji coba berakhir, aplikasi menampilkan layar aktivasi
dengan keterangan yang jelas dan tautan ke halaman pembelian lisensi.

### Perbaikan penting pada paket Microsoft Store

Versi sebelumnya menyertakan berkas penanda uji coba di dalam paket.
Karena paket yang diuji peninjau Microsoft adalah paket yang SAMA dengan
yang diunduh semua orang, berkas itu membuat setiap orang yang memasang
dari Store mendapat lisensi Enterprise gratis tanpa membayar. Berkas
tersebut sekarang tidak lagi disertakan.

Masa uji coba yang baru tidak memakai berkas apa pun di dalam paket.
Waktu mulai dicatat di tiga tempat di komputer pengguna, dan yang dipakai
adalah catatan paling awal, sehingga menghapus salah satu catatan tidak
mengembalikan masa uji coba. Memundurkan jam komputer juga tidak
memperpanjangnya.

### Teks untuk kolom What's new di Partner Center

```
Masa uji coba 1 hari untuk pemasangan dari Microsoft Store. Seluruh
fitur paket Enterprise terbuka selama masa itu, sehingga Anda dapat
menilai aplikasi sepenuhnya sebelum membeli lisensi.

Setelah masa uji coba berakhir, aplikasi meminta kunci lisensi. Lisensi
dibeli sekali dan berlaku selamanya, tanpa biaya bulanan.

Perbaikan pada paket: berkas penanda uji coba tidak lagi disertakan.
```

---

## Versi 1.2.6 - 28 September 2026

### Halaman masuk lebih rapi

- Kotak berlatar abu di bawah tombol masuk dihapus. Keterangan akun
  bawaan kini tampil sebagai teks biasa, sehingga halaman masuk terlihat
  bersih seperti halaman lain di aplikasi.
- Kolom isian, tombol masuk, dan keterangan di bawahnya kini **sama
  lebar dan sejajar**. Sebelumnya kolom isian hanya selebar 259 piksel,
  sedangkan keterangan di bawahnya meluber sampai 640 piksel.
- Seluruh elemen formulir rata pada satu garis di semua ukuran jendela,
  dari layar 1024 piksel sampai 1920 piksel.

### Teks lebih mudah dibaca

- Warna teks keterangan dinaikkan kontrasnya, baik di panel gelap maupun
  panel terang.
- Keterangan kata sandi bawaan kini memakai ukuran dan warna yang lebih
  tegas, supaya pengguna baru tidak melewatkannya.
- Seluruh teks aplikasi memenuhi standar kontras **WCAG AA**.

### Alur lisensi diarahkan ke situs

- Pengguna yang belum punya lisensi kini diarahkan ke halaman pembelian
  di akuntuntas.xinet.id, bukan ke alamat surel. Di situs tersedia
  keterangan paket, harga, dan cara pembayaran yang lengkap.
- Pesan ketika lisensi dicabut juga menunjuk ke situs, supaya pengguna
  tahu langkah yang dapat ditempuh.

### Teks untuk kolom What's new di Partner Center

Batas 1500 huruf. Salin yang berikut.

```
Halaman masuk ditata ulang: kotak abu di bawah tombol masuk dihapus,
keterangan akun bawaan kini tampil sebagai teks biasa.

Formulir masuk kini sama lebar dan sejajar di semua ukuran jendela.
Sebelumnya kolom isian lebih sempit daripada keterangan di bawahnya.

Teks keterangan dibuat lebih jelas terbaca, termasuk keterangan kata
sandi bawaan supaya pengguna baru tidak melewatkannya.

Pengguna yang belum punya lisensi kini diarahkan ke halaman pembelian di
situs resmi, bukan ke alamat surel.

Seluruh teks aplikasi memenuhi standar kontras WCAG AA.
```

---

## Versi 1.2.5 - 28 September 2026

### Perbaikan tampilan

- Judul jendela tidak lagi menampilkan nama aplikasi dua kali.
  Sebelumnya berbunyi "AkunTuntas - Pembukuan & Pajak Perusahaan
  Indonesia - AkunTuntas".
- Bila laba besar tetapi kas negatif, muncul keterangan yang menjelaskan
  sebabnya, supaya angkanya tidak membingungkan.
- Penilaian rasio keuangan diperbaiki. Sebelumnya rasio kas negatif
  dinilai "Sangat Baik" dan rasio lancar yang sehat dinilai "Berisiko
  Tinggi".
- Penulisan angka diseragamkan: koma sebagai tanda desimal dan titik
  sebagai pemisah ribuan, sesuai kebiasaan Indonesia. Uang negatif
  ditulis "-Rp168.837.000", bukan "Rp-168.837.000".

### Fitur baru

- **Tombol tindak lanjut pada setiap temuan analisis.** Setelah analisis
  keuangan menampilkan temuan, tersedia tombol yang langsung membuka
  halaman terkait, misalnya "Buka Kas & Bank" atau "Buka Jurnal Umum".
- **Ekspor ke Excel dan cetak A4.** Seluruh daftar dan laporan dapat
  diekspor ke berkas Excel yang angkanya tetap dapat dijumlahkan, serta
  dicetak pada ukuran kertas A4.

### Perbaikan lain

- Tanda "&" pada tombol tidak lagi tampil sebagai garis bawah.
- Nama bentuk badan usaha tidak lagi muncul dua kali pada keterangan
  perusahaan, misalnya "PT Xinet persada - PT".
- Kata "peringatan" tidak lagi menyelip di awal kalimat ringkasan.
- Keterangan pada halaman analisis tidak lagi mewarisi warna ke anak
  elemennya.
- Pemasang aplikasi diperkecil dari 107 MB menjadi 92 MB dengan membuang
  pustaka multimedia yang tidak dipakai, sehingga diunduh lebih cepat.

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
