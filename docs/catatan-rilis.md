# Catatan Rilis AkunTuntas

Berkas ini **aman dipublikasikan**. Isinya boleh disalin ke kolom
**What's new** di Microsoft Partner Center, dan tayang untuk umum di
https://akuntuntas.xinet.id/rilis (berkas `web/rilis.html`).

Catatan yang memuat hal teknis atau sensitif dipisahkan ke
`docs/catatan-rilis-internal.md`. Jangan mencampur keduanya.

Bila mengubah berkas ini, perbarui juga `web/rilis.html` supaya isinya
sama.

---

## Versi 1.4.6 - 13 November 2026

Versi terbaru.

### Penyempurnaan

- **Tampilan baru yang lebih tenang.** Seluruh halaman memakai latar putih
  bersih dengan garis tipis dan aksen cokelat dari logo. Warna-warna yang
  mengganggu pandangan dihilangkan, sehingga isi pembukuan menjadi fokus
  utama.
- **Huruf lebih mudah dibaca.** Teks dan angka memakai Public Sans, huruf
  yang dibuat untuk formulir dan data. Judul memakai Source Serif 4 agar
  hierarki halaman jelas. Angka rupiah memakai lebar tetap, sehingga digit
  pada tabel nominal selalu sejajar.
- **Tabel dan kartu lebih lega.** Tinggi baris, jarak antarkolom, dan
  perataan tombol diseragamkan di semua halaman. Nominal rata kanan dan
  label status tidak lagi berdesakan.
- **Menu dan dialog ikut dirapikan.** Menu samping, baris tab, kotak pesan,
  pratinjau cetak, halaman masuk, dan pengaturan memakai ukuran serta jarak
  yang sama dengan halaman utama.

### Catatan

- Pembaruan ini hanya menyentuh tampilan. Cara hitung, format berkas, dan
  seluruh data pembukuan tidak berubah, sehingga versi 1.4.5 dapat
  diperbarui langsung tanpa memindahkan data.

---

## Versi 1.4.5 - 27 Oktober 2026

Versi terbaru.

### Fitur baru

- **Bekerja dengan dua halaman sekaligus.** Halaman kedua dapat dibuka di
  samping halaman yang sedang dikerjakan, misalnya Penjualan di kiri dan
  Biaya di kanan. Setiap sisi memiliki pemilih halaman, tombol muat ulang,
  dan tombol tutup sendiri, sehingga Anda dapat membandingkan atau mencatat
  dua bagian pembukuan tanpa berpindah menu. Panel dibuka lewat tombol
  **Dua halaman** di baris status, menu **Tampilan**, atau pintasan
  **Ctrl+Shift+D**. Setelah data disimpan, kedua sisi ikut diperbarui agar
  angkanya tidak saling bertentangan.

### Penyempurnaan

- **Seluruh kotak pesan seragam.** Pemberitahuan, pertanyaan, peringatan,
  dan pesan kesalahan kini memakai satu gaya jendela yang sama dengan
  aplikasi: judul yang jelas, teks yang terbaca, dan tombol yang rapi.
  Kotak pesan bawaan yang tampil berbeda gaya tidak dipakai lagi.
- **Pratinjau cetak lebih jelas.** Jendela pratinjau A4 memakai tampilan
  aplikasi dengan tombol ikon untuk memperbesar, memperkecil, dan
  berpindah halaman. Bidang kertas tampil di atas latar hangat, dan kolom
  zoom tidak lagi terpotong. Menekan **Cetak** langsung memberi tanggapan.

### Perbaikan

- **Garis tab aktif kembali sejajar.** Garis bawah tab yang dipilih
  menempel tepat pada baris tab, tidak lagi menggantung di bawahnya.
- **Nilai zoom tampil utuh.** Angka perbesaran pada pratinjau cetak tidak
  terpotong lagi.

---

## Versi 1.4.4 - 27 Oktober 2026

### Perbaikan

- **Keluar akun berjalan normal.** Tombol Keluar Akun sebelumnya dapat
  membuat aplikasi berhenti merespons, sehingga halaman tidak termuat lagi
  dan pembukuan tampak kosong. Jendela utama sekarang dilepas dan dibongkar
  dengan urutan yang benar, lalu halaman masuk dibuat ulang dari awal.
- **Pembukuan tetap utuh.** Setelah laporan data tampak hilang, seluruh
  catatan diperiksa dan ternyata tetap tersimpan lengkap. Yang gagal adalah
  pemuatan halaman setelah keluar akun, bukan datanya. Pemeriksaan otomatis
  baru memastikan perusahaan aktif dan bagan akun tetap termuat walau
  pengguna keluar dan masuk akun berkali-kali dalam satu sesi.

### Penyempurnaan

- **Halaman masuk yang formal.** Halaman masuk ditata seperti formulir
  resmi: keterangan di atas kertas hangat, kolom isian di atas permukaan
  terang, dan satu garis pemisah tipis. Strip warna, nomor hias, dan
  label kapital bersusun dihilangkan.
- **Dokumen cetak lebih resmi.** Kop surat memakai satu garis tipis
  sepanjang lebar kertas, judul bagian ditulis dengan huruf biasa, dan
  seluruh teks memakai tinta hitam hangat atau abu redup. Warna hanya
  dipakai pada segel verifikasi. Invoice PDF mengikuti aturan yang sama.
- **Panel keterangan tanpa strip warna.** Kotak informasi, peringatan,
  dan kesalahan memakai bingkai tipis dengan latar yang sesuai maknanya,
  sehingga pesannya tetap jelas tanpa hiasan.

---

## Versi 1.4.3 - 27 Oktober 2026

### Penyempurnaan

- **Tampilan baru yang tenang dan mudah dibaca.** Seluruh halaman memakai
  tata letak editorial: palet kertas hangat, garis tipis, sudut halus,
  dan jarak yang lega. Huruf Source Sans 3 dipakai untuk isi, sedangkan
  Source Serif 4 untuk judul dan angka penting. Keduanya dipilih karena
  bentuk hurufnya tetap jelas pada ukuran kecil maupun besar.
- **Dasbor lebih jernih.** Ringkasan keuangan, grafik kinerja, dan panel
  kesehatan usaha ditata ulang agar angka utama langsung terlihat,
  grafik menyatu dengan kartunya, dan warna tetap nyaman dipandang.
- **Cetak A4 dan PDF dengan pengaman dokumen.** Setiap dokumen cetak
  dapat diberi tanda air yang Anda atur sendiri (5%, 8%, atau 12%),
  blok tanda tangan elektronik dengan nama, jabatan, dan gambar tanda
  tangan, segel verifikasi, serta kode dokumen di kaki halaman. Kop
  perusahaan, nomor halaman, dan baris judul berulang tetap ada, dan
  tabel lebar otomatis dicetak mendatar.
- **Invoice seragam dengan dokumen resmi.** Invoice kini memakai desain,
  tanda air, tanda tangan, segel, dan kode verifikasi yang sama. Halaman
  lanjutan memuat kepala invoice dan nomor halaman, sedangkan blok
  pengesahan hanya muncul sekali di akhir dokumen.
- **Halaman masuk dan formulir lebih rapi.** Kartu masuk menyesuaikan
  ukuran jendela, langkah lupa kata sandi ditulis jelas, tinggi seluruh
  kotak isian seragam, tanggal tampil lengkap, dan tabel tetap terbaca
  pada jendela sempit.
- **Daftar pilihan lebih bersih dan nyaman.** Saat dibuka, daftar tidak
  lagi menampilkan bingkai abu-abu; baris terpilih disorot beige lembut
  dengan teks gelap dan tinggi baris yang lega. Daftar yang panjang
  dibatasi sepuluh baris dan dapat digulir, sehingga tidak memenuhi
  layar.

### Perbaikan

- **Dialog kontrak lebih mudah diisi.** Tanggal memakai format
  dd/mm/yyyy dan pilihan "Tanpa batas waktu" berupa kotak centang yang
  jelas. Label yang memuat tanda & tampil benar.
- **Dialog lapor bug tidak terpotong.** Kotak langkah dan catatan kini
  berukuran tetap, sehingga seluruh isi dialog muat di layar.
- **Panduan lupa kata sandi tampil sebagai kalimat biasa.** Karakter
  panah yang sempat terbaca sebagai teks aneh sudah diganti.
- **Pesan tabel kosong sesuai konteks.** Setiap tab pada Pembelian,
  Biaya & Bank, Produk & Stok, Penjualan, dan Payroll kini menampilkan
  langkah berikutnya yang tepat, sehingga tidak lagi muncul panduan dari
  halaman lain.
- **Teks sekunder lebih nyaman dibaca.** Warna teks samar diperkuat agar
  kontrasnya memenuhi standar aksesibilitas AA, baik di halaman maupun
  dialog.

### Teks untuk kolom What's new di Partner Center

Batas 1500 huruf. Salin yang berikut.

```
Tampilan AkunTuntas dirombak dengan tata letak editorial yang tenang:
palet kertas hangat, garis tipis, dan huruf Source Sans 3 untuk isi
serta Source Serif 4 untuk judul dan angka. Seluruh halaman, dasbor,
dan halaman masuk ditata ulang agar mudah dibaca dan nyaman dipandang.

Dokumen cetak dan invoice kini punya pengaman: tanda air yang dapat
diatur sendiri, blok tanda tangan elektronik, segel verifikasi, dan
kode dokumen di kaki halaman. Kop perusahaan, nomor halaman, dan
judul kolom berulang tetap ada, dan tabel lebar otomatis dicetak
mendatar.

Dialog kontrak memakai tanggal dd/mm/yyyy dengan pilihan tanpa batas
waktu yang jelas; dialog lapor bug tidak lagi terpotong. Pesan pada
tabel kosong kini sesuai tabnya, dan warna teks sekunder diperkuat
agar tetap nyaman dibaca. Daftar pilihan juga lebih bersih: tanpa
bingkai abu-abu, dengan sorotan lembut dan daftar panjang yang
dibatasi sepuluh baris agar tidak memenuhi layar.
```

---

## Versi 1.4.2 - 26 Oktober 2026

### Penyempurnaan

- **Cetak A4 dan simpan PDF dari halaman data.** Tombol Ekspor dan Cetak
  kini tersedia pada halaman data utama (produk, mitra, pembelian, jurnal,
  biaya, aset tetap, bagan akun, laporan, analisis, dan dasbor). Hasil
  cetak memakai kertas A4, kop perusahaan, baris judul yang diulang di
  setiap halaman, dan nomor halaman. Tabel lebar otomatis dicetak
  mendatar, dan pratinjau tampil sebelum kertas terpakai.
- **Berkas Excel siap dibagikan.** Angka tetap tersimpan sebagai angka
  sehingga dapat dijumlahkan, lebar kolom mengikuti isi, baris judul
  dibekukan, saringan otomatis terpasang, dan halaman disiapkan untuk A4
  dengan judul kolom berulang.
- **Invoice rapi pada semua keadaan.** Deskripsi panjang terbungkus tanpa
  menimpa kolom lain, kolom Diskon hanya muncul bila ada diskon, nomor
  halaman tampil pada invoice lebih dari satu halaman, dan karakter khusus
  seperti & atau < tampil benar.
- **Huruf dan ikon konsisten.** Dokumen cetak dan invoice memakai huruf
  Inter yang sama dengan aplikasi, sedangkan ikon tampil seragam di semua
  halaman.

### Perbaikan

- **Kartu dasbor tampil bersih.** Latar kartu, kotak ringkasan, dan panel
  grafik kini putih penuh. Grafik batang menyatu dengan kartunya, tidak
  lagi tampak sebagai kotak putih terpisah di atas latar halaman.
- **Grafik kinerja lebih tenang.** Batang pendapatan dan beban memakai
  warna merek, garis laba mudah diikuti, dan label sumbu tetap terbaca
  pada jendela lebar maupun sempit.
- **Halaman masuk rapi di semua ukuran.** Kartu formulir menyesuaikan
  ruang yang tersedia, sehingga kolom isian dan tombol Masuk utuh bahkan
  pada jendela kecil. Panel merek tampil polos tanpa garis pengganggu,
  dengan jarak teks yang seimbang.
- **Isian tanggal dan angka lebih nyaman.** Tinggi seluruh kotak isian
  seragam, tanggal tampil lengkap, dan sorotan pilihan mengikuti warna
  aplikasi, bukan warna bawaan Windows.

### Teks untuk kolom What's new di Partner Center

Batas 1500 huruf. Salin yang berikut.

```
Setiap halaman data utama kini punya tombol Ekspor dan Cetak. Laporan
dapat dicetak ke kertas A4 atau disimpan sebagai PDF dengan kop
perusahaan, judul kolom yang berulang, dan nomor halaman. Tabel lebar
otomatis dicetak mendatar, dan pratinjau tampil sebelum kertas terpakai.

Berkas Excel siap dibagikan: angka tetap dapat dijumlahkan, lebar kolom
mengikuti isi, baris judul dibekukan, dan halaman disiapkan untuk A4.

Invoice lebih rapi: deskripsi panjang terbungkus, kolom diskon muncul
saat diperlukan, nomor halaman tampil pada invoice panjang, dan karakter
khusus tampil benar. Dokumen memakai huruf Inter yang sama dengan
aplikasi.

Dasbor, grafik, halaman masuk, serta isian tanggal dan angka juga
disempurnakan agar lebih tenang dan mudah dibaca.
```

---

## Versi 1.4.1 - 25 Oktober 2026

### Perbaikan

- **Jurnal otomatis memakai akun yang tepat pada setiap bentuk usaha.**
  Sebelumnya sebagian jurnal dapat menunjuk akun yang tidak ada atau akun
  dengan arti berbeda. Kini PPN penjualan, pajak daerah, pembelian,
  persediaan, aset tetap, penyusutan, sewa, biaya bank, dan pemotongan
  pajak mengikuti bagan akun perusahaan.
- **Formulir langsung memilih akun yang tersedia.** Dialog aset tetap,
  pembelian, produk, biaya, dan template berulang tidak lagi memilih akun
  bawaan dari bentuk usaha lain.
- **Rincian beban pada Laba Rugi konsisten.** Nilai beban operasional
  kini bertanda negatif seperti baris totalnya, sehingga laporan lebih
  mudah dibaca dan dijumlahkan.
- **Dasbor menyesuaikan ukuran jendela.** Pada jendela sempit, panel
  kesehatan keuangan dan grafik kinerja ditumpuk agar teksnya tidak
  berdesakan.
- **Nominal pada tabel tetap terbaca utuh.** Kolom saldo yang dicetak
  tebal kini diukur dengan huruf tebal, sehingga angka besar tidak
  terpotong pada jendela sempit.

### Teks untuk kolom What's new di Partner Center

Batas 1500 huruf. Salin yang berikut.

```
Jurnal otomatis kini memakai akun yang sesuai bagan akun setiap bentuk
usaha. PPN penjualan, pajak daerah, pembelian, persediaan, aset tetap,
penyusutan, sewa, biaya bank, dan pemotongan pajak tidak lagi menunjuk
akun yang tidak ada atau akun dengan arti berbeda.

Dialog aset tetap, pembelian, produk, biaya, dan template berulang
langsung memilih akun yang tersedia pada perusahaan Anda.

Rincian beban pada laporan Laba Rugi kini bertanda negatif seperti baris
totalnya, sehingga laporan lebih mudah dibaca.

Dasbor menyesuaikan ukuran jendela, dan nominal pada tabel tetap terbaca
utuh meski jendela dipersempit.
```

---

## Versi 1.4.0 - 25 Oktober 2026

### Penyempurnaan

- **Tampilan baru selaras logo.** Warna arang dan tembaga dipadukan
  dengan latar kertas hangat. Tombol, judul, dan sorotan menu aktif
  memakai satu bahasa warna yang tenang dan konsisten.
- **Halaman masuk ditata ulang.** Panel merek menampilkan contoh jurnal
  yang seimbang, sedangkan formulir dibuat lebih lapang dengan kolom
  isian yang jelas, pilihan mengingat nama pengguna, dan tombol lihat
  kata sandi.
- **Tabel dan laporan lebih mudah dibaca.** Angka rata kanan, baris
  berselang warna, status berwarna, dan baris total ditebalkan. Laporan
  panjang dapat digulir sampai totalnya terlihat tanpa terpotong.
- **Menu samping lebih mudah ditelusuri.** Kelompok menu dapat dilipat,
  tersedia pencarian menu, dan menu yang sedang dibuka otomatis
  terlihat.
- **Ikon baru yang konsisten.** Seluruh ikon garis digambar ulang agar
  ukuran dan ketebalannya seragam di semua halaman.

### Perbaikan

- **Kontras teks memenuhi WCAG AA.** Teks bantuan dan keterangan kecil
  dipergelap secukupnya agar tetap terbaca di latar kertas hangat.
- **Kolom tabel tidak lagi menyisakan ruang kosong.** Kolom yang tidak
  terpakai disembunyikan, sehingga kolom lain mendapat ruang lebih lega.
- **Bagian laporan yang kosong tidak lagi mengganggu.** Neraca hanya
  menampilkan kelompok yang berisi angka, dengan judul bagian yang lebih
  ringkas.

### Teks untuk kolom What's new di Partner Center

Batas 1500 huruf. Salin yang berikut.

```
Tampilan AkunTuntas dibangun ulang mengikuti warna logo: arang dan
tembaga di atas latar kertas hangat. Halaman masuk kini lebih lapang,
tabel dan laporan lebih mudah dibaca, serta menu samping dapat dilipat
dan dicari. Ikon garis digambar ulang agar seragam, dan kontras teks
dinaikkan agar memenuhi WCAG AA. Laporan panjang dapat digulir sampai
totalnya terlihat tanpa terpotong.
```

---

## Versi 1.2.9 - 29 September 2026

### Penyempurnaan

- **Menu samping kini memakai jalur sempit.** Sebelumnya tombol pengembali
  menu diletakkan mengapung di atas area isi, sehingga menutupi sebagian
  menu **Berkas** di bagian atas jendela. Kini tombol itu punya jalurnya
  sendiri di sisi kiri, jadi tidak menutupi apa pun. Area isi tetap
  bertambah lebar 276 piksel saat menu disembunyikan.
- **Popup pesan memakai huruf lebih besar.** Judul, isi pesan, dan tombol
  diperbesar, serta tombolnya dibuat lebih tinggi. Popup kini nyaman
  dibaca tanpa perlu dizoom.
- **Salinan Regulasi Resmi ditata ulang.** Judul peraturan yang panjang
  sebelumnya terpotong dengan titik-titik, sehingga dua peraturan yang
  mirip sulit dibedakan. Kini judul tampil utuh. Ditambah keterangan
  peraturan yang sedang dibaca beserta jumlah barisnya, serta tombol
  Salin Isi.

### Teks untuk kolom What's new di Partner Center

Batas 1500 huruf. Salin yang berikut.

```
Menu samping dapat disembunyikan sehingga tabel dan laporan memakai
seluruh lebar layar. Pilihannya diingat.

Lokasi penyimpanan data dapat dipindahkan ke folder atau drive lain,
dengan pengaman agar data tidak pernah hilang bila penyalinan gagal.

Seluruh popup pesan ditata ulang supaya menyatu dengan tampilan aplikasi,
dengan huruf yang lebih besar dan mudah dibaca.

Salinan Regulasi Resmi kini dapat dibaca seluruhnya. Judul peraturan
tampil utuh, disertai keterangan jumlah baris dan tombol Salin Isi.
```

---

## Versi 1.2.8 - 28 September 2026

### Fitur baru

- **Menu samping dapat disembunyikan.** Pada layar sempit, menu samping
  memakan ruang sehingga sebagian kolom tabel terpotong. Kini menu dapat
  disembunyikan lewat tombol di sudut kanan atas, menu Tampilan, atau
  pintasan **Ctrl+Shift+B**. Pilihannya diingat, sehingga tidak perlu
  diulang setiap membuka aplikasi.
- **Lokasi penyimpanan data dapat dipindahkan.** Tersedia di
  **Pengaturan > Penyimpanan Data**. Pindahkan folder data ke drive lain
  atau folder yang ikut dicadangkan, buka folder lewat tombol, atau
  kembalikan ke lokasi bawaan. Pemindahan menyalin seluruh isi lebih
  dahulu, memeriksa hasilnya, baru berpindah, sehingga data tidak pernah
  hilang bila penyalinan gagal.
- **Aktifkan lisensi lain tanpa menutup aplikasi.** Tersedia tombol
  Aktifkan Lisensi Lain di menu Lisensi & Keamanan.

### Penyempurnaan

- **Popup pesan ditata ulang.** Seluruh kotak pesan, pertanyaan, dan
  pemberitahuan kini menyatu dengan tampilan aplikasi, dengan ikon dan
  tombol yang sesuai maksud pesannya.
- **Popup masa uji coba lebih jelas.** Memuat pilihan langsung untuk
  mengaktifkan lisensi yang sudah dimiliki, membeli lisensi, atau
  menundanya.
- **Menu Lisensi & Keamanan dirapikan.** Keterangan lisensi disusun dua
  kolom dengan lencana paket, kunci lisensi disamarkan sebagian demi
  keamanan, dan butir keterangan diberi nomor supaya mudah dipindai.

### Perbaikan

- **Salinan Regulasi Resmi kini dapat dibaca.** Sebelumnya seluruh berkas
  peraturan di halaman Panduan dan Aturan gagal dibuka. Kini seluruh 15
  berkas peraturan terbaca lengkap.

---

## Versi 1.2.7 - 28 September 2026

### Fitur baru

- **Masa uji coba 1 hari.** Aplikasi yang dipasang dari Microsoft Store
  dapat dicoba selama 1 hari sejak pertama kali dibuka, dengan seluruh
  fitur paket Enterprise terbuka. Setelah masa itu berakhir, aplikasi
  meminta kunci lisensi.

### Penyempurnaan

- **Pemberitahuan masa uji coba.** Setelah masuk, Anda diberi tahu berapa
  sisa waktunya dan bahwa lisensi dibeli sekali lalu berlaku selamanya.
- **Pesan setelah masa uji coba berakhir.** Aplikasi menjelaskan apa yang
  terjadi dan mengarahkan Anda ke halaman pembelian lisensi.

### Teks untuk kolom What's new di Partner Center

```
Masa uji coba 1 hari untuk pemasangan dari Microsoft Store. Seluruh fitur
paket Enterprise terbuka selama masa itu, sehingga Anda dapat menilai
aplikasi sepenuhnya sebelum membeli lisensi.

Setelah masa uji coba berakhir, aplikasi meminta kunci lisensi. Lisensi
dibeli sekali dan berlaku selamanya, tanpa biaya bulanan.
```

---

## Versi 1.2.6 - 28 September 2026

### Penyempurnaan

- **Halaman masuk lebih rapi.** Kotak berlatar abu di bawah tombol masuk
  dihapus, dan keterangan akun bawaan kini tampil sebagai teks biasa.
- **Formulir masuk sejajar.** Kolom isian, tombol masuk, dan keterangan di
  bawahnya kini sama lebar dan rata pada satu garis di semua ukuran
  jendela.
- **Teks lebih mudah dibaca.** Warna teks keterangan dinaikkan kontrasnya,
  termasuk keterangan kata sandi bawaan supaya pengguna baru tidak
  melewatkannya.
- **Alur lisensi diarahkan ke situs.** Pengguna yang belum punya lisensi
  diarahkan ke halaman pembelian, bukan ke alamat surel.

### Teks untuk kolom What's new di Partner Center

```
Halaman masuk ditata ulang: kotak abu di bawah tombol masuk dihapus,
keterangan akun bawaan kini tampil sebagai teks biasa.

Formulir masuk kini sama lebar dan sejajar di semua ukuran jendela.

Teks keterangan dibuat lebih jelas terbaca, termasuk keterangan kata
sandi bawaan supaya pengguna baru tidak melewatkannya.

Pengguna yang belum punya lisensi kini diarahkan ke halaman pembelian di
situs resmi, bukan ke alamat surel.

Seluruh teks aplikasi memenuhi standar kontras WCAG AA.
```

---

## Versi 1.2.5 - 28 September 2026

### Fitur baru

- **Tombol tindak lanjut pada setiap temuan analisis.** Setelah analisis
  keuangan menampilkan temuan, tersedia tombol yang langsung membuka
  halaman terkait, misalnya Buka Kas & Bank atau Buka Jurnal Umum.
- **Ekspor ke Excel dan cetak A4.** Seluruh daftar dan laporan dapat
  diekspor ke berkas Excel yang angkanya tetap dapat dijumlahkan, serta
  dicetak pada ukuran kertas A4.

### Perbaikan

- Penilaian rasio keuangan diperbaiki. Sebelumnya rasio kas negatif dinilai
  sangat baik dan rasio lancar yang sehat dinilai berisiko tinggi.
- Bila laba besar tetapi kas negatif, muncul keterangan yang menjelaskan
  sebabnya.
- Penulisan angka diseragamkan: koma sebagai tanda desimal dan titik
  sebagai pemisah ribuan, sesuai kebiasaan Indonesia.
- Judul jendela tidak lagi menampilkan nama aplikasi dua kali.
- Ukuran pemasang diperkecil dari 107 MB menjadi 92 MB sehingga diunduh
  lebih cepat.

---

## Versi 1.2.4 - 27 September 2026

- **Ekspor Excel dan cetak A4.** Seluruh daftar dan laporan dapat diekspor
  ke berkas Excel dengan angka bertipe angka, serta dicetak pada kertas A4
  dengan pratinjau.
- **Halaman kontak di situs.** Tersedia formulir dan tombol WhatsApp untuk
  menghubungi kami.
- **Data antar perusahaan lebih terjaga.** Pemisahan data diperketat pada
  53 tabel, sehingga catatan satu perusahaan tidak tercampur dengan
  perusahaan lain.
- **Pemeriksaan jurnal lebih ketat.** Jurnal yang tidak seimbang ditolak
  sebelum tersimpan, sehingga laporan terhindar dari kesalahan yang sulit
  dilacak.
- **Impor CSV menerima tanggal Indonesia.** Bentuk 15/03/2026 kini
  diterima, bukan hanya 2026-03-15.

---

## Versi 1.2.3 - 26 September 2026

- **Tabel perbandingan paket di situs** ditata ulang supaya lebih mudah
  dibaca, dengan penanda untuk fitur khusus Enterprise dan fitur yang
  batasannya berbeda.
- Perbaikan tampilan halaman pengaturan: ukuran berkas memakai koma
  desimal.

---

## Versi 1.2.2 - 26 September 2026

- **Dashboard dan Analisis Keuangan** ditata ulang supaya lebih mudah
  dipahami.
- **Penjelasan istilah rasio keuangan** pada mode Pemula.
- **Panduan langkah awal** muncul saat pembukuan masih kosong, supaya
  pengguna baru tahu harus mulai dari mana.

---

## Versi 1.2.1 - 25 September 2026

- Panduan langkah awal muncul saat pembukuan masih kosong.
- Keadaan kosong diperjelas supaya tidak menyesatkan.

---

## Versi 1.2.0 - 25 September 2026

- **Pemisahan data antar perusahaan** supaya catatan tiap perusahaan
  berdiri sendiri.
- **Pemeriksaan keseimbangan jurnal** sebelum data disimpan.
- **Buku besar** tidak lagi menampilkan pendapatan sebagai angka negatif.
- **Kartu stok** tidak lagi menampilkan saldo yang menyesatkan.
- **Impor CSV** menerima tanggal gaya Indonesia.

---

## Versi 1.1.0 - 24 September 2026

- **Kwitansi dan bukti transaksi.**
- **Dashboard admin** untuk pengelolaan lisensi.
- **Pembayaran melalui iPaymu**, termasuk QRIS.
- **Deteksi versi Windows diperbaiki.** Windows 11 tidak lagi terbaca
  sebagai Windows 10.

---

## Versi 1.0.0 - 24 September 2026

Versi pertama.

- Pembukuan berpasangan dengan pemeriksaan debit dan kredit.
- Bagan akun siap pakai untuk lima bentuk badan usaha.
- Penjualan, pembelian, kas dan bank, biaya, persediaan dengan metode FIFO
  dan rata-rata bergerak, aset tetap beserta penyusutan, kontrak, dan
  payroll.
- Perhitungan PPh 21 TER, PPh Badan, PPh Final UMKM, PPN, dan PPh 23.
- Checklist kepatuhan pajak.
- Laporan keuangan sesuai SAK EMKM, SAK EP, dan SAK Umum.
- Jejak audit yang mencatat setiap perubahan data.
- Dua mode pemakaian: Pemula dan Ahli.
- Cadangan otomatis dan pemulihan data.
- Keranjang sampah dengan pemulihan data.
