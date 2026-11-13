# Catatan Rilis Internal AkunTuntas

> **BERKAS INI TIDAK UNTUK DIPUBLIKASIKAN.**
> Jangan menyalin isinya ke Partner Center, halaman web, atau balasan
> ke pengguna. Berkas ini hanya untuk keperluan pengembangan, penelusuran
> masalah, dan pengujian.
>
> Catatan rilis yang aman dipublikasikan ada di `docs/catatan-rilis.md`.

---

## Versi 1.4.6 - 13 November 2026

### Sistem visual putih

`ui/theme.py`: token BG/SURFACE menjadi `#FFFFFF`, SURFACE_ALT `#F7F7F7`,
BORDER `#E5E5E5`, BORDER_STRONG `#CFCFCF`, aksen `#A0622D`/`#7C4A1E`,
menu samping `#1B2426`. QSS seluruh komponen (kartu, tabel, tab, tombol,
dialog, login, pratinjau cetak) diselaraskan ke token tersebut; tidak ada
lagi warna krem atau biru sisa template di halaman aplikasi.

### Tipografi

`fonts.py` memuat Public Sans sebagai keluarga antarmuka (Regular, Medium,
SemiBold, Bold) dan Source Serif 4 Display untuk judul. Ukuran body 14 px,
teks kecil 13 px, keterangan 12 px. Nominal memakai fitur OpenType `tnum`
agar digit rata kolom. Baris tabel 40 px dengan minimum 32 px supaya data
padat tetap terbaca.

### Tangkapan dan verifikasi

`tools/tangkapan_review.py` mengambil delapan halaman dari salinan data
`_contoh` dengan lisensi uji, lalu menyalinnya ke Desktop. Menu samping
digulirkan ke atas sebelum setiap tangkapan agar posisinya konsisten.
Tangkapan ini juga dipakai untuk aset `web/tangkapan`.

---

## Versi 1.4.5 - 27 Oktober 2026

### Dua halaman berdampingan

`ui/main_window.py`: area isi kini berada di dalam `QSplitter` bersama
`PanelKedua`, panel halaman kedua yang tersembunyi sampai diminta. Panel
memiliki pemilih halaman (`QComboBox`) yang diisi dari `Sidebar.MENU` dan
disaring `batas_paket.boleh_buka`, tombol muat ulang, dan tombol tutup.
Kendali pembuka ada di tiga tempat dan dijaga tetap sinkron lewat
`blockSignals`: tombol centang **Dua halaman** pada baris status
(`QPushButton#SplitToggle`), aksi menu **Tampilan** yang dapat dicentang,
dan pintasan **Ctrl+Shift+D**.

Halaman panel kanan adalah salinan tersendiri dari `_pabrik`, bukan widget
yang dipindahkan dari panel kiri. Dengan begitu halaman yang sama dapat
tampil di kedua sisi, dan menutup panel kanan tidak mengganggu halaman
utama. `_pasang_halaman_kedua` membuang widget lama lewat `deleteLater()`
sehingga tumpukan tidak menumpuk. Tautan `pindah_halaman` dari halaman
kanan diarahkan ke `_pindah_dari_kanan`: mengganti isi panel kanan bila
tujuannya tersedia di sana, atau membuka di halaman utama sebagai cadangan.

Penyegaran data memakai penanda revisi yang sudah ada. `_navigasi`
menyegarkan panel kanan bila `db.revisi_data()` berubah, `_dua_halaman`
menyegarkannya saat dibuka kembali, dan `_pilih_perusahaan` serta
`_ubah_ukuran_teks` ikut memuat ulang panel kanan. Kedua sisi dibungkus
`QScrollArea` mendatar tanpa bingkai: saat jendela dipersempit di bawah
lebar minimum halaman (sekitar 600-650 px), halaman tetap pada lebar
nyamannya dan digeser mendatar, bukan dihimpit sampai judul dan tombol
saling bertumpuk. Uji regresi: `tests/test_dua_halaman.py` (22 pemeriksaan)
mencakup buka-tutup, ganti halaman tanpa menumpuk, tautan panel kanan,
penyegaran setelah revisi berubah, ingatan halaman terakhir, pintasan, dan
gulir mendatar pada lebar 1180.

### Kotak pesan seragam

`ui/popup.py` (`KotakPesan`) dipakai di seluruh aplikasi. 383 pemanggilan
`QMessageBox` di 20 berkas dialihkan dengan penyapu AST berbasis offset
byte UTF-8 (`_sapu_popup.py`, hanya alat kerja, tidak ikut rilis), lalu
tujuh dialog khusus dikonversi tangan. `_rapikan()` mengubah baris baru
menjadi `<br>` karena `QLabel` rich text tidak menampilkan `\n`; teks yang
sudah memuat HTML dibiarkan. Lebar dikunci `setFixedWidth`, tinggi dihitung
`layout().heightForWidth()` pada `showEvent`, sehingga tidak ada pita kosong
di badan dialog. Tes dan alat yang dahulu menambal `QMessageBox.warning`
kini menambal `popup.peringatkan` agar tidak menggantung.

### Pratinjau cetak

`ui/pratinjau_cetak.py`: `QPrintPreviewDialog` diganti `DialogPratinjau`
berbasis `QPrintPreviewWidget` dengan bilah alat sendiri. Tingkat perbesaran
tetap (`TINGKAT`) dan ditampilkan pada label 56 px, bukan `QComboBox` yang
mewarisi gaya kolom isian. Tombol perbesaran dan pindah halaman memakai
ikon (`kurang`, `tambah`, `panah_kiri`, `panah_kanan`) karena lambang teks
minus dan panah nyaris tidak terlihat pada 34 px. Latar `QGraphicsView`
di dalam pratinjau diubah ke `C.BG` agar kertas putih menonjol. Jendela
tampil lebih dulu dengan label "Menyiapkan halaman cetak...", lalu lukisan
pertama menggantikannya, sehingga penekanan Cetak langsung terasa.

### Penanda tab

`widgets.Tab.paintEvent` menggambar sendiri garis dasar pada baris piksel
yang sama dengan penanda tab aktif (`bar.geometry().bottom()`), melewati
bagian di bawah tab terpilih. `setDrawBase(False)` mematikan garis bawaan
Qt yang berwarna palet sistem dan tidak sebaris.

---

## Versi 1.4.4 - 27 Oktober 2026

### Data tampak hilang: penelusuran dan hasilnya

Laporan "data hilang semua" ditelusuri lewat salinan basis data yang
dibuka hanya-baca. Seluruh tabel masih berisi: 1 perusahaan, 98 akun,
334 baris jurnal, 40 invoice, 18 bill. Tidak ada baris yang hilang dan
tidak ada jejak penghapusan pada `recycle_bin` maupun `audit_log`.

Gejalanya berasal dari jalur keluar akun di bawah: setelah jendela utama
dibongkar secara salah, aplikasi berhenti merespons dan halaman berikutnya
tidak pernah termuat, sehingga tampak seolah pembukuan kosong. Tidak ada
perubahan kode pada lapisan data. `tests/test_logout_alur.py` sekarang
menjaga dua hal setelah tiap siklus keluar-masuk: `ctx.company_id` sama
dengan perusahaan yang dibuat, dan jumlah baris `accounts` tetap > 0.

### Keluar akun membekukan aplikasi

`JendelaAplikasi._kembali_ke_login` dan `_buka_utama` menghapus widget
pusat lewat `setCentralWidget()`, yang membuang widget lama lewat
`deleteLater()` sementara `self.stack` masih menunjuk objek C++ di
dalamnya. Pada siklus keluar berikutnya referensi itu sudah mati.
Keduanya kini memakai `takeCentralWidget()` untuk melepas jendela utama
lebih dulu, memutus `kembali_ke_login.disconnect(...)`, membuang jendela
lama dan `self.stack` lewat `deleteLater()`, lalu membangun
`QStackedWidget` dan `LoginPage` yang baru. `self.stack` tidak pernah
dipakai ulang. Regresi dijaga oleh `tests/test_logout_alur.py`
(tiga siklus keluar-masuk berurutan).

### Halaman masuk dan panel keterangan tanpa strip dekoratif

`ui/login.py` dibersihkan: strip aksen, label kapital bersusun
(`Eyebrow`), nomor urut hias `01/02/03`, dan slogan dihapus. Kolom isian
memakai kotak bergaris tipis (`QFrame#LoginField`), label memakai
`QLabel#LoginLabel` dalam huruf biasa. Pada `ui/theme.py`,
`QFrame#HelpPanel`, `WarningPanel`, `DangerPanel`, dan `SuccessPanel`
kehilangan `border-left: 3px` dan memakai bingkai 1 px dengan latar
sesuai maknanya (`WARNING_BG`, `DANGER_BG`, `SUCCESS_BG`). `QLabel#HelpTitle`
dan `QLabel#HelpLegal` memakai tinta dan abu redup, bukan tembaga.
Enam belas baris `border-left: ... {C.ACCENT}` pada `ui/pages/*.py` juga
dihapus. Garis aksen pada `QPushButton#NavButton:checked` dan cincin
fokus `QLineEdit:focus` tetap ada karena keduanya penanda keadaan, bukan
hiasan.

### Dokumen cetak dan invoice diformalkan

`ui/ekspor_cetak.py`: kop memakai satu garis `WARNA_TINTA` 0,6 px
sepanjang lebar kertas tanpa potongan berwarna; kode dokumen pada kaki
dan keterangan tanda tangan memakai tinta atau abu redup. Judul bagian
tabel (`thead tr.bagian th`) memakai latar bening, huruf biasa, dan
`letter-spacing: 0`. `ui/pages/penjualan.py`: palet invoice dipangkas ke
`TINTA`, `MUTED`, `GARIS`, `KEPALA`, `TOTAL_BG`, `BELANG`; label berubah
menjadi "Ditagihkan kepada", "Catatan", dan "Instruksi pembayaran".
Tanda air, blok pengesahan, segel verifikasi, dan kode dokumen tetap
utuh. Segel adalah satu-satunya unsur berwarna.

### Ikon banner sukses

`ui/widgets.py` memakai ikon `centang` untuk banner sukses, sebelumnya
ikon `simpan` yang maknanya tidak sesuai. Ikon panel bantuan memakai
`icons.WARNA_MUTED`.

---

## Versi 1.4.3 - 27 Oktober 2026

### Sistem desain editorial dan tipografi baru

`ui/theme.py` ditulis ulang: token warna kertas hangat (aksen tembaga
`#A0622D`, latar `#F9F5ED`, garis `#E3DCCF`), sudut kartu 3 px dan
kontrol 4 px, serta tangga huruf Source Sans 3 untuk isi dan Source Serif 4
untuk judul/angka. Kedua berkas huruf disertakan agar tampilan sama pada
setiap komputer. Seluruh QSS global dan gaya per halaman dirapikan;
`theme.latar(widget, aturan)` mengunci selector ke
`<Kelas>#<ObjectName>` supaya latar transparan tidak menular ke turunan.
Dashboard, halaman masuk, sidebar, tabel, dialog, dan lembar cetak
memakai token yang sama.

### Cetak A4: tanda air, pengesahan, segel, dan kode dokumen

`ui/ekspor_cetak.py` kini membangun identitas dokumen lewat
`_identitas_cetak`: kode HMAC-SHA256 pendek dari judul, subjudul, isi
tabel, dan perusahaan. Halaman cetak memuat kop, kaki bernomor, tanda
air diagonal dengan kepekatan pilihan pengguna (5/8/12%), segel
verifikasi melingkar, dan blok pengesahan yang dipaku ke dasar halaman
(nama, jabatan, gambar tanda tangan, keterangan tanda tangan elektronik,
kode verifikasi). Baris dibagi rata antarhalaman lewat
`_bagi_bagian_panjang`; orientasi mendatar dipilih otomatis bila lebar
kolom melebihi area A4 tegak. Setelan baru disimpan melalui
`simpan_setelan_cetak`: air aktif/teks/kepekatan, ttd aktif, nama,
jabatan, kota, dan gambar tanda tangan.

Helper publik `identitas_dokumen()`, `gambar_segel()`, dan `segel_png()`
dipakai modul lain agar kode dan segel sama dengan lembar laporan.

### Invoice mengikuti identitas dokumen

`pages/penjualan.py:buat_pdf_invoice` dirombak: kop serif, judul
INVOICE, tabel tanpa garis vertikal dengan kepala beige, ringkasan
bergaris tipis, dan kaki bernomor. `NumberedCanvas` menggambar tanda air
di badan halaman, kepala berjalan pada halaman kedua dan seterusnya
("Invoice {nomor} · lanjutan"), serta kode dokumen di tengah kaki.
`BlokPengesahan` (Flowable) menggambar blok tanda tangan pada koordinat
dasar halaman 30 mm sehingga selalu di dasar halaman terakhir dan hanya
sekali; segel 28 mm ditempatkan di kiri garis tanda tangan. Blok ini
hanya ditambahkan bila `ttd_aktif`. Mode polos tetap mencetak kode
dokumen di kaki.

### Perbaikan dialog dan formulir

- `dialog_bug.py`: kotak langkah dan catatan dipatok 118/72 px;
  `theme.latar(... min-height/max-height ...)` diperlukan karena QSS
  global memasang `min-height: 20px` pada QPlainTextEdit dan melonggarkan
  tinggi tetap. Ringkasan teknis dipadatkan menjadi satu baris.
- `pages/kontrak_page.py`: tanggal `dd/MM/yyyy`, pilihan tanpa batas
  waktu menjadi QCheckBox (bukan QComboBox), dan label tab/tombol yang
  memuat `&` di-escape (`&&`) agar tidak dibaca sebagai mnemonic Qt.
- `login.py`: panah `→` pada langkah lupa kata sandi diganti kalimat
  biasa; pemeriksa teks ikon kembali bersih.
- `version_info.txt`: kunci StringTable `040904B0` dan filevers/prodvers
  1.4.3.0 disamakan dengan teks versi.

### Sapuan pesan kosong dan kontras

Seluruh `set_pesan_kosong` pada `pages/aset.py`, `pages/penjualan.py`,
`pages/pembelian.py`, `pages/biaya_bank.py`, dan `pages/produk.py`
disisir ulang. Banyak tabel masih memakai teks generik hasil salin-tempel,
misalnya tabel Payroll menampilkan "Belum ada aset tetap ... Tambah Aset".
Kini setiap tab menyebut objek dan tombol yang benar (bill, purchase order,
pembayaran pemasok, aging utang, baris bill, biaya, lampiran, kategori,
rekening, mutasi, riwayat rekonsiliasi, karyawan, payroll, invoice, sales
order, penerimaan, nota kredit, aging piutang, alokasi, lampiran invoice,
stok barang, dan kartu stok).

`theme.TEXT_FAINT` dinaikkan dari `#6A7572` menjadi `#626D6A` agar rasio
kontras teks samar memenuhi 4.5:1 pada permukaan `#F9F5ED` dan `#F3EFE7`.
Label gambar di `pages/pengaturan.py` memakai selector `QLabel` ter-scope
supaya gayanya tidak menular; em dash pada teks UI diganti `·` atau `–`;
padding horizontal tombol Ghost dilonggarkan agar lebar minimum tombol
lolos audit.

### Daftar pilihan yang bersih dan terbaca

Kotak pilihan di seluruh aplikasi dirapikan. Bingkai fokus bawaan Fusion
yang dulu menggambar kotak abu-abu di sekitar baris terpilih dihilangkan
lewat delegate yang membuang `QStyle.State_HasFocus` sebelum melukis;
seleksi kini memakai beige lembut `ACCENT_SOFT` dengan teks gelap, hover
tipis `SURFACE_ALT`, dan sudut baris 3 px. Tinggi baris dipatok 33 px
(`metrik.height() + 16`, minimum 32) supaya tidak lagi terasa sempit,
dan `doItemsLayout()` dipakai menggantikan `reset()` agar pilihan aktif
tetap tersorot setelah halaman dirapikan.

Pop-up daftar panjang dibatasi maksimal 10 baris dengan penempatan
otomatis ke bawah atau ke atas sesuai ruang layar; sisa daftar dapat
digulir. Panah gulir bawaan yang sempat muncul meski seluruh isi muat
disembunyikan setelah tata letak selesai. `QComboBox` mendapat
`padding-right: 30px` (termasuk saat fokus) agar teks panjang tidak
menimpa panah, dan delegate dua baris pada pilihan bentuk badan usaha
ditandai `delegasi_pilihan` supaya tidak tertimpa delegate tinggi baris
global — ikon dan baris "Standar: SAK ..." tetap tampil.

### Verifikasi 1.4.3

`tests/jalankan_semua_tes.py` lulus penuh: **1882 LULUS, 0 GAGAL**
(tidak ada rangkaian yang gagal), termasuk pemuatan seluruh halaman, tab,
dan dialog, audit tumpang tindih widget, pemeriksaan teks terpotong, serta
pemeriksaan pilihan (baris 33 px, seleksi tetap tersorot, daftar panjang
dibatasi 10 baris, delegate dua baris utuh).

`tools/uji_ekspor_cetak.py` diperluas dari 74 menjadi 88 pemeriksaan:
invoice satu halaman, invoice 45 baris (3 halaman), dan invoice polos.
Yang diperiksa antara lain judul, nama penanda tangan, kalimat tanda
tangan elektronik, kode verifikasi, kode di kaki setiap halaman, tanda
air diagonal, kepala halaman lanjutan, dan pengesahan yang hanya muncul
sekali. Hasil: 88 BENAR, 0 SALAH.

Pemasang dibangun dari `dist/AkunTuntas` (PyInstaller 6.22.3, FileVersion
1.4.3.0) lalu `installer_output/AkunTuntas-1.4.3-Setup.exe`
(60.538.395 bita, SHA256
`150f7c7098f4b07edbef6c7b8b18794ea2098c53851c2c78a404f0d105703212`).
`web/AkunTuntas-Setup.exe` disalin dari berkas yang sama dan hash di
`web/unduh.html` diperbarui.

`tools/uji_pasang_ulang.py` dipasang senyap menimpa 1.4.2:
pemasangan berhasil (kode keluar 0), aplikasi terpasang melaporkan
FileVersion 1.4.3.0, dan aplikasi berjalan 30 detik pada salinan data
tanpa berhenti. Folder data tetap 9 berkas / 8.409,8 KB; hash
`akuntuntas.db` dan `lisensi.json` sama persis dengan sebelum
pemasangan, dan lisensi Enterprise tidak disentuh.

---

## Versi 1.4.2 - 26 Oktober 2026

### Cetak A4 dan ekspor Excel memakai satu jalur

`ui/ekspor_cetak.py` dirombak agar seluruh halaman memakai jalur yang sama.
Cetak memakai QTextDocument berukuran 96 dpi, dipotong sendiri per baris
dengan tinggi baris contoh, sehingga baris tidak terbelah di antara dua
halaman. Judul kolom diulang, kop dan kaki digambar di setiap halaman,
dan orientasi mendatar dipilih otomatis bila kebutuhan lebar kolom
melebihi area A4 tegak. Excel memakai pengaturan halaman A4, skala muat
lebar, baris judul berulang, dan saringan otomatis.

Diuji dengan menghasilkan PDF A4 dari keenam tab Laporan. Neraca Saldo
menjadi mendatar karena tujuh kolom, tab lain tegak; kop, nomor halaman,
dan baris total benar. Berkas Excel diperiksa ulang dengan openpyxl:
`Uraian` di A5, angka 10000000 di B6 tetap numerik, orientasi potret dan
fit-to-width aktif.

### Invoice panjang: deskripsi tidak membungkus

Sel tabel reportlab berupa string biasa tidak pernah membungkus, sehingga
deskripsi panjang menimpa kolom Qty dan Harga. Sel kini dibuat sebagai
`Paragraph`, dengan teks dinamis di-escape (`xml.sax.saxutils.escape`)
dan baris baru diubah menjadi `<br/>`. Kolom Diskon hanya ditambahkan bila
ada item yang berdiskon, dan lebar kolom dihitung ulang untuk dua bentuk
tabel. Kaki halaman “Halaman X dari Y” tetap digambar NumberedCanvas
setelah jumlah halaman diketahui. Huruf Inter disematkan lewat
`fonts.pasang_reportlab()`.

Bukti: invoice 45 baris menjadi 3 halaman A4 tanpa tumpang tindih; invoice
berdiskon menampilkan Diskon 10% dan Jumlah 675.000; nama pelanggan serta
deskripsi yang memuat `&` dan `<` tampil sebagai teks biasa.

### Audit ikon dan kolom tabel: hilangkan positif palsu

`tools/periksa_teks_ikon.py` menandai label sah “Pajak” karena kebetulan
sama dengan nama ikon. Nama ikon selalu huruf kecil, jadi pencocokan kini
peka huruf besar-kecil. `tools/audit_kolom_tabel.py` menuntut kolom
fleksibel (`-1`) memuat seluruh isi terpanjang; padahal kolom itu memang
dipotong dengan elipsis dan tooltip. Audit kini hanya mewajibkan judul
kolom untuk kolom fleksibel. Keduanya lulus tanpa temuan.

### Uji UI berhenti bersih di Windows

Rangkaian uji UI mencetak hasil LULUS tetapi proses keluar dengan
`0xC0000005` saat Qt membongkar DLL. Pembersihan jendela dan pelepasan
event filter tidak cukup. Proses kini diakhiri dengan
`OpenProcess(PROCESS_TERMINATE)` + `TerminateProcess` sebelum `os._exit`,
sehingga kode keluar sesuai hasil uji tanpa menjalankan pembongkaran DLL.

---

### Kartu dasbor tembus pandang

Penyebab kotak putih grafik yang tampak ditempel di dasbor bukan pelukis
grafik, melainkan gaya tanpa selector pada wadah di atas kartu:
`setStyleSheet("background: transparent;")`. Aturan itu menular ke seluruh
turunan, termasuk kartu dan kotak ringkasan, sehingga latar putihnya hilang.
Diperbaiki dengan `theme.latar(widget, aturan)` yang mengunci selector ke
`<Kelas>#<ObjectName>`. Penjaga regresi ada di
`tools/audit_grafik.py:periksa_latar_kartu`.

### Halaman masuk terpotong pada jendela sempit

Kartu formulir memakai lebar tetap 440 px, sedangkan panel merek menahan
520 px. Pada lebar 920 px sisi kanan formulir terpotong. Kartu kini memakai
`setMaximumWidth(440)` agar boleh menyusut. Diuji pada 1366, 1120, 980, dan
920 px.

### Sorotan isian tanggal berwarna biru bawaan

Aturan `selection-background-color` hanya mencakup QLineEdit dan QTextEdit.
QDateEdit, QSpinBox, QDoubleSpinBox, dan QTimeEdit belum tercakup sehingga
memakai biru Windows. Keempat kelas itu ditambahkan ke selector di
`theme.stylesheet()`.

### Audit dialog yang selalu melaporkan nol

`tools/periksa_garis_bawah_dialog.py` tidak pernah menaikkan penghitung
`dicek`, jadi selalu mencetak "dialog diperiksa: 0" dan lulus tanpa bukti.
Penghitung diperbaiki; kini 63 dialog benar-benar diperiksa.

---

## Versi 1.2.9 - 29 September 2026

Versi ini memuat tiga perbaikan yang semula ditempelkan ke 1.2.8 pada hari
yang sama. Karena installer 1.2.8 sudah telanjur dibangun dan disebarkan
sebelum perbaikan itu, versinya dinaikkan supaya pengguna yang sudah
memasang 1.2.8 dapat menerima perbaikan tanpa kebingungan versi.

### Tombol pengembali menu menimpa menu Berkas

Tombol diletakkan mengapung di koordinat tetap sebagai anak jendela, yaitu
pada y 14..49, sedangkan menu bar berada di y 0..33. Jadi tombol menimpa
menu bar sebanyak 19 piksel.

Diperbaiki dengan mengganti pendekatan: bukan lagi tombol mengapung, tetapi
rel sempit 44 piksel di samping area isi (`MainWindow.REL_LEBAR`). Tombol
punya ruangnya sendiri sehingga tidak mungkin menimpa apa pun. Area isi
bertambah 276 piksel saat menu disembunyikan (320 dikurangi 44).

Uji: `tools/ukur_tombol_mengapung.py` (36 LULUS) dan
`tools/uji_sidebar.py` (24 LULUS).

Catatan saat mengukur: `widget.geometry()` relatif terhadap induknya.
Tombol dan menu bar berbeda induk, jadi keduanya harus dipetakan dahulu
dengan `mapTo(jendela, ...)` sebelum dibandingkan. Tanpa itu, tombol yang
sudah benar akan terlihat menimpa menu bar.

### Judul peraturan terpotong titik-titik

Akar masalahnya `QListWidget` memakai `ElideRight` secara bawaan: teks
dipotong dengan titik-titik begitu tidak muat satu baris, walau barisnya
masih dapat dibungkus. `setWordWrap(True)` saja tidak menolong.

Diperbaiki dengan menampilkan setiap judul sebagai dua baris terpisah di
dalam `QLabel`: kode peraturan di atas (tebal), uraian di bawahnya (kecil,
membungkus). Dipilih setelah membandingkan empat cara penataan.

Catatan: menghitung tinggi baris sendiri lalu memasangnya lewat `setSizeHint`
TIDAK menyelesaikan masalah ini, karena penyebabnya pemotongan teks, bukan
tinggi baris. Pengukuran yang membaca kembali `sizeHint` buatan sendiri juga
tidak membuktikan apa pun.

### Dua kesalahan penamaan variabel saat mengerjakan penataan itu

1. Memakai `baris` untuk jumlah baris, padahal `baris` adalah layout utama
   halaman. Akibatnya halaman gagal dibuka dengan
   `'int' object has no attribute 'addLayout'`.
2. Memakai `wadah` di dalam perulangan, padahal `wadah` adalah widget
   halaman. Widget lama dibuang Python, dan layout-nya ikut terhapus dengan
   `libshiboken: Internal C++ object already deleted`.

Keduanya diperbaiki dengan mengganti nama variabel perulangan menjadi
`jumlah_baris` dan `baris_wadah`.

### Popup diperbesar

Judul 14 -> 16, isi 13 -> 15, tombol 13 -> 15 dan tinggi 38 -> 42, lebar
460 -> 540. Ukuran baru ditambahkan sebagai `theme.FS_PESAN`.

### Sidik jari dan ukuran berkas di halaman unduh

Installer dibangun ulang, sehingga sidik jarinya berubah. Halaman unduh
masih memuat sidik lama, yang akan membuat pengguna melihat peringatan
"berkas tidak cocok" walau berkasnya benar. Keterangan ukuran berkas juga
masih tertulis 107 MB padahal installer sudah 92 MB. Keduanya diperbarui.

### Catatan rilis dipisah per versi

Butir yang benar-benar baru ada di 1.2.9 dikeluarkan dari bagian 1.2.8,
supaya catatan rilis 1.2.8 menggambarkan apa yang benar-benar terkirim pada
versi itu.

### Alat baru

| Alat | Kegunaan |
|---|---|
| `tools/cek_versi_exe.py` | Membaca versi tertanam di EXE, membandingkan dengan versi.json |
| `tools/ukur_tombol_mengapung.py` | Rel sempit tidak menimpa menu bar atau judul |
| `tools/ukur_daftar_regulasi.py` | Judul peraturan utuh, teks nyaman dibaca |
| `tools/potret_regulasi.py` | Potret halaman Salinan Regulasi Resmi |

---

## Versi 1.2.8 - 28 September 2026

### Perbaikan Salinan Regulasi Resmi

Seluruh berkas peraturan di halaman Panduan dan Aturan gagal dibuka dengan
keterangan:

```
Berkas tidak dapat dibaca: 'PySide6.QtGui.QTextCursor' object has no
attribute 'Start'
```

Sebabnya konstanta `MoveOperation.Start` diakses pada objek kursor, bukan
pada kelas `QTextCursor`. Diperbaiki dengan `movePosition()`. Terverifikasi
15 berkas peraturan terbaca lengkap (PMK 105/2025 = 152.544 huruf, PMK
114/2025 = 84.138, PMK 168/2023 = 83.380).

### Menu samping

Tombol, menu Tampilan, dan pintasan **Ctrl+Shift+B**. Ctrl+B tidak dipakai
karena sudah menjadi pintasan Buat Cadangan Data. Menyembunyikan menu
menambah lebar area isi 320 piksel penuh. Pilihan disimpan ke pengaturan
dan dipulihkan saat aplikasi dibuka.

Uji: `tools/uji_sidebar.py` (20 LULUS, 0 GAGAL).

### Pemindahan lokasi penyimpanan

Tab Pengaturan indeks 3. Urutan: salin seluruh isi, periksa hasil, baru
pindah. Bila gagal, lokasi lama tetap dipakai. Berkas di lokasi lama tidak
dihapus. Uji: `tools/uji_pindah_data.py` (18 LULUS, 0 GAGAL).

### Popup

Modul baru `src/akuntansi_id/ui/popup.py`. Selain itu aturan `QMessageBox`
ditambahkan di `theme.py` supaya seluruh popup lama ikut naik kelas tanpa
harus menyentuh ratusan pemanggil.

### Penanganan kegagalan yang ditelan

`_simpan_pilihan_sidebar()` semula memakai `except Exception: pass`
sehingga kegagalan penyimpanan tidak terlihat. Diperbaiki agar sebabnya
dicatat. Ditemukan oleh `tools/buruh_bug_kesalahan.py`.

---

## Versi 1.2.7 - 28 September 2026

### Uji coba 1 hari

Sejak pemakaian pertama. Waktu mulai dicatat di tiga tempat di komputer
pengguna, dan yang dipakai adalah catatan paling awal, sehingga menghapus
salah satu catatan tidak mengembalikan masa uji coba. Memundurkan jam
komputer juga tidak memperpanjangnya.

Uji: `tools/uji_celah_uji_coba.py`.

### Penanda uji coba yang bocor di paket Microsoft Store

**Kejadian:** paket MSIX yang dikirim ke Store memuat `msix/uji_coba.txt`,
yaitu penanda bertanda tangan sah berlaku sampai 24 November 2026. Karena
paket yang diuji peninjau Microsoft adalah paket yang sama dengan yang
diunduh semua orang, siapa pun yang memasang dari Store mendapat lisensi
Enterprise penuh tanpa membayar. Installer web tidak terpengaruh.

**Perbaikan:**

- `msix/uji_coba.txt` dihapus.
- `tools/bungkus_msix.py` menolak membuat paket bila penanda masih ada
  (`--siapkan`), tidak menyalin penanda (`--bungkus`), dan menolak paket
  berpenanda (`--periksa`).
- Masa uji coba baru tidak memakai berkas apa pun di dalam paket.

**Pelajaran:** apa pun yang ada di dalam paket akan sampai ke tangan
publik. Bukti lisensi tidak boleh ikut dibungkus.

---

## Versi 1.2.6 - 28 September 2026

### Ketidakrataan formulir masuk

Kolom isian 229 piksel sedangkan tombol masuk 245 piksel, beda 8 piksel di
tiap sisi. Ditemukan lewat pengukuran piksel, bukan pemeriksaan mata.
Alat: `tools/ukur_login.py`.

Catatan: mode offscreen membuat laporan "teks terpotong" pada alat ini
menjadi palsu, karena angka yang dihasilkan sama di semua ukuran jendela
akibat font sistem tidak dimuat.

### Kontras

Warna teks panel gelap dan keterangan kecil dinaikkan. Diperiksa dengan
`tools/periksa_kontras.py` terhadap WCAG AA.

---

## Versi 1.2.5 - 28 September 2026

- Penilaian rasio keuangan terbalik: rasio kas negatif dinilai sangat baik
  dan rasio lancar sehat dinilai berisiko tinggi.
- Judul jendela menampilkan nama aplikasi dua kali.
- Pemasang diperkecil dari 107 MB menjadi 92 MB dengan membuang pustaka
  multimedia yang tidak dipakai, supaya dapat diunggah ke GitHub.

---

## Versi 1.2.4 - 27 September 2026

- Penjaga keseimbangan jurnal di lapisan basis data.
- Pemisahan data antar perusahaan pada 53 tabel.
- Perbaikan impor CSV untuk tanggal gaya Indonesia.

---

## Versi 1.2.0 - 25 September 2026

- Perbaikan celah keamanan lisensi.
- Perbaikan buku besar dan kartu stok.

---

## Catatan umum

### Alat pengujian yang dipakai

| Alat | Kegunaan |
|---|---|
| `tests/jalankan_semua_tes.py` | Seluruh rangkaian tes |
| `tools/uji_sidebar.py` | Sembunyikan/tampilkan menu samping |
| `tools/uji_pindah_data.py` | Pemindahan lokasi penyimpanan |
| `tools/uji_celah_uji_coba.py` | Masa uji coba tidak dapat dilewati |
| `tools/buruh_bug_kesalahan.py` | Kegagalan yang ditelan tanpa laporan |
| `tools/periksa_kontras.py` | Kontras WCAG AA |
| `tools/periksa_latar.py` | Gaya yang menular ke anak elemen |
| `tools/audit_tampilan.py` | Tampilan seluruh halaman |
| `tools/periksa_seo.py` | SEO halaman web |

### Aturan saat menulis catatan rilis publik

1. Sebutkan **apa yang berubah bagi pengguna**, bukan **bagaimana
   perlindungannya bekerja**.
2. Jangan menyebut nama berkas di dalam paket.
3. Jangan mengakui sistem pernah dapat ditembus.
4. Jangan mengajari cara mengakali, walau untuk menyatakan bahwa cara itu
   gagal.
5. Jangan menyebut angka perbaikan keamanan, misalnya "perbaikan 4 celah".
6. Perbaikan yang tidak terlihat pengguna tidak perlu disebut sama sekali.
