# Persyaratan Sistem AkunTuntas

Seluruh angka di bawah ini diukur langsung dari aplikasi yang berjalan,
bukan perkiraan. Cara mengukurnya tercatat di bagian akhir dokumen.

## Untuk halaman Microsoft Store

Kolom persyaratan di Partner Center menerima teks bebas. Isi seperti ini.

### Minimum

```
Sistem operasi   : Windows 10 versi 2004 (build 19041) atau lebih baru
Arsitektur       : x64 (64 bit)
Prosesor         : Prosesor x64 1 GHz, 2 inti
Memori           : 2 GB RAM
Penyimpanan      : 700 MB ruang kosong
Layar            : 1366 x 768 piksel
Koneksi internet : diperlukan sekali untuk aktivasi lisensi
```

### Direkomendasikan

```
Sistem operasi   : Windows 11
Arsitektur       : x64 (64 bit)
Prosesor         : Prosesor x64 2 GHz, 4 inti atau lebih
Memori           : 4 GB RAM atau lebih
Penyimpanan      : 1 GB ruang kosong
Layar            : 1920 x 1080 piksel
Koneksi internet : hanya untuk aktivasi lisensi
```

## Dasar setiap angka

### Memori 2 GB minimum, 4 GB direkomendasikan

Aplikasi memakai 142 MB saat berjalan dengan data satu tahun penuh.
Windows 10 sendiri memerlukan 2 GB, jadi angka itu yang menjadi batas
bawah. Pada 4 GB, aplikasi dan Windows berjalan nyaman bersamaan dengan
peramban dan Excel yang biasanya dibuka bersamaan oleh staf akuntansi.

Diukur: 141,9 MB memori kerja pada data contoh dua belas bulan.

### Penyimpanan 700 MB minimum, 1 GB direkomendasikan

| Bagian | Ukuran |
|---|---|
| Terpasang di disk | 398 MB (3.874 berkas) |
| Berkas installer | 107 MB |
| Ruang data tahun pertama | sekitar 5 MB |
| Ruang cadangan otomatis | sekitar 5 MB |

Cadangan otomatis disimpan bergilir, jadi ruangnya tidak tumbuh tanpa
batas. Angka 700 MB memberi sisa cukup untuk pembaruan aplikasi.

### Prosesor 2 inti minimum

Aplikasi berjalan pada satu proses dengan 13 thread. Beban saat diam
0,02 persen dari satu inti. Saat membuka aplikasi, beban puncaknya
singkat. Dua inti sudah memadai; empat inti membuat perpindahan halaman
terasa lebih mulus ketika aplikasi lain juga berjalan.

Diukur: 13 thread, 1.099 handle, 0,02 persen CPU saat diam.

### Layar 1366 x 768 minimum

Jendela utama meminta ukuran minimum 1180 x 720 piksel. Pada layar
1366 x 768, seluruh halaman diuji satu per satu dan tidak ada teks yang
terpotong atau widget yang keluar batas.

Diukur: 29 halaman diperiksa pada 1366 x 768, nol temuan.

### Windows 10 versi 2004 minimum

Paket MSIX mencantumkan `MinVersion="10.0.19041.0"`, yaitu Windows 10
versi 2004. Ini batas yang ditetapkan oleh alat pembungkus Microsoft
untuk aplikasi desktop berbasis MSIX.

### Koneksi internet hanya untuk aktivasi

Data pembukuan tidak pernah meninggalkan komputer. Satu-satunya
panggilan jaringan adalah verifikasi lisensi saat pengaktifan, ke
layanan milik Xinet Group. Setelah aktif, aplikasi berjalan penuh
tanpa internet.

### Arsitektur x64 saja

Paket dibangun untuk `ProcessorArchitecture="x64"`. Versi 32 bit tidak
dibuat, karena Windows 10 dan 11 yang masih didukung semuanya 64 bit.

## Yang tidak diperlukan

| Hal | Keterangan |
|---|---|
| Microsoft Visual C++ Redistributable | Tidak perlu dipasang terpisah, seluruh pustaka dibawa aplikasi |
| .NET Framework | Tidak dipakai |
| Java | Tidak dipakai |
| Peramban web | Tidak dipakai, antarmuka dibangun dengan Qt |
| Hak administrator | Tidak diminta, pemasangan per pengguna |
| Kartu grafis khusus | Tidak perlu, tampilan digambar oleh Qt tanpa akselerasi GPU |
| Printer | Tidak perlu, ekspor berbentuk berkas PDF dan Excel |

## Pemakaian ruang data menurut besar usaha

Angka dari pengukuran: 4,8 KB per baris jurnal, sudah termasuk indeks.

| Besar usaha | Transaksi per tahun | Data | Dengan cadangan |
|---|---|---|---|
| Kecil | 500 | 2,3 MB | 4,7 MB |
| Menengah | 2.000 | 9,4 MB | 18,8 MB |
| Ramai | 5.000 | 23,5 MB | 46,9 MB |

Bahkan usaha paling ramai tidak menghabiskan 50 MB setahun, jadi ruang
700 MB cukup untuk bertahun-tahun pemakaian.

## Cara mengukur ulang

Semua angka dapat diperiksa sendiri dengan alat yang ada di repositori.

| Angka | Alat |
|---|---|
| Memori dan CPU saat berjalan | `tools/periksa_terpasang.py` lalu Task Manager |
| Waktu buka aplikasi | jalankan aplikasi tiga kali, catat waktu jendela muncul |
| Ukuran terpasang | klik kanan folder pemasangan, Properties |
| Tampilan pada 1366 x 768 | `tools/periksa_label_terpotong.py` |
| Widget keluar batas | `tools/periksa_keluar_batas.py` |
| Ukuran data | `tools/buat_data_contoh.py` lalu periksa berkas basis data |
| Batas Windows | `grep MinVersion msix_output/.../AppxManifest.xml` |
