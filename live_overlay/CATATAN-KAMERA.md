# Catatan Kamera USB

Catatan ini berisi hal penting tentang kamera USB untuk siaran, supaya
masalah yang pernah muncul tidak terulang.

## Ringkasan cepat

Dua masalah yang paling sering muncul, dan penyebabnya:

| Gejala | Penyebab | Perbaikan |
|---|---|---|
| Wajah terlihat diperbesar (ngezoom) | Bentuk gambar kamera 4:3, kotak face cam 16:9, sehingga sisi atas dan bawah gambar terpotong | Kotak face cam sudah dibuat 4:3 (400x300) supaya cocok |
| Pengganti latar tidak bekerja | Fitur butuh pengaturan Cutout aktif, atau tidak ada orang terang di depan kamera | Aktifkan Cutout, perbaiki pencahayaan, atau pakai jendela kamera sendiri |

Bila ingin langsung berhasil tanpa mengatur fitur aplikasi:

```
MULAI-KAMERA.bat
```

Jendela itu menampilkan kamera dengan latar sudah diganti. Di aplikasi
siaran, tambahkan Window capture dan pilih jendela "AkunTuntas - Kamera".

## Bentuk gambar kamera

Kamera USB umumnya mengirim gambar **4:3** (640x480 atau 1024x768), bukan
16:9. Ini yang paling sering menimbulkan dua masalah sekaligus:

1. **Wajah terlihat diperbesar (ngezoom)**
   Bila gambar 4:3 dipaksa mengisi kotak 16:9, sisi atas dan bawah gambar
   terpotong. Yang tersisa hanya bagian tengah, sehingga wajah tampak
   diperbesar.

2. **Gambar terlihat pecah**
   Bila kotak face cam 16:9 tetapi sumber gambarnya kecil, aplikasi
   siaran memperbesar gambar untuk menutupi kotak. Pembesaran inilah yang
   membuat gambar pecah.

Karena itu kotak face cam di overlay dibuat **4:3 (400x300)**, sama
seperti bentuk gambar yang dikirim kamera.

Untuk memeriksa bentuk kamera Anda:

```
python tools/cek_bentuk_kamera.py
```

Bila kamera Anda justru mengirim 16:9, ubah kotak face cam dengan
menyunting `live_overlay/overlay.html`, pada bagian `--cam-lebar` dan
`--cam-tinggi`. Jaga perbandingannya tetap sesuai bentuk kamera.

## Kamera hanya dapat dipakai satu aplikasi

Kamera USB tidak dapat dipakai dua aplikasi sekaligus. Bila aplikasi lain
sedang memakainya, aplikasi berikutnya akan menerima **gambar hitam**
tanpa pesan galat sama sekali. Gejala ini mudah tertukar dengan kamera
rusak.

Aplikasi yang biasanya memakai kamera:

- TikTok LIVE Studio
- OBS Studio dan Streamlabs
- Peramban (Chrome, Edge) bila ada tab yang memakai kamera
- Discord, Zoom, Teams
- Aplikasi Camera bawaan Windows

Untuk memeriksa:

```
python tools/cari_pemakai_kamera.py
```

## Cara memastikan kamera bekerja

Sebelum menyalahkan fitur siaran, pastikan kameranya memang mengirim
gambar:

```
python tools/uji_kamera_hidup.py
```

Skrip ini mengambil beberapa gambar dan melaporkan kecerahan tiap
gambar. Bila semuanya hitam, masalahnya ada pada kamera atau aplikasi
lain yang memakainya, bukan pada fitur siaran.

## Pengganti latar kamera

Ada dua jalan, pilih yang paling nyaman:

### Jalan 1: fitur bawaan TikTok LIVE Studio

1. Klik sumber kamera
2. Buka panel efek, pilih kategori background
3. Pilih "Virtual Background (Static/Dynamic)"
4. Aktifkan pengaturan Cutout
5. Pilih gambar latar yang diinginkan

Gambar latar dibuat dengan:

```
python tools/buat_latar_kamera.py
```

Hasilnya ada di `live_overlay/gambar/`. Berkas yang dipakai adalah
`latar-akuntuntas.png` (1600x1200, bentuk 4:3).

Pengaturan yang perlu diperhatikan:

| Pengaturan  | Arti                      | Saran        |
|-------------|---------------------------|--------------|
| Cutout      | Memotong orang dari latar | aktifkan    |
| Similarity  | Kemiripan warna latar     | 30 sampai 45 |
| Smoothness  | Kehalusan tepi orang      | 6 sampai 12  |
| Spill       | Mengurangi pantulan warna | 8 sampai 15  |

### Jalan 2: jendela kamera sendiri

Jalan ini tidak bergantung pada fitur aplikasi, jadi hasilnya lebih
pasti:

```
python tools/jendela_kamera.py
```

Jendela ini menampilkan kamera dengan latar sudah diganti. Di aplikasi
siaran, tambahkan Window capture dan pilih jendela
"AkunTuntas - Kamera".

Kelebihannya:

- Bentuk gambar sudah 4:3, sama seperti kotak, jadi tidak terpotong
- Latar pasti berganti
- Ukuran jendelanya dapat diatur

## Ukuran jendela overlay

Jendela peramban tidak dapat lebih tinggi daripada layar. Pada layar
1080p, jendela setinggi 1920 dipangkas Windows menjadi sekitar 1090.
Akibatnya isi jendela tidak lagi 9:16, dan aplikasi siaran menyisakan
pita kosong di kanan kiri sambil memperbesar gambar sehingga pecah.

Peluncur overlay mengatasi ini dengan penanda khusus Windows, sehingga
isi jendela tetap 1080x1920 penuh. Karena itu overlay sebaiknya selalu
dibuka lewat peluncur, bukan dengan membuka berkas HTML langsung:

```
MULAI-OVERLAY.bat
```

Untuk memeriksa ukurannya:

```
python tools/setel_jendela_overlay.py --periksa
```

Rasio isi jendela harus 0.5625, sama dengan 9 dibagi 16.

## Bentuk gambar yang benar untuk kotak kamera

Kamera USB Anda mendukung beberapa resolusi:

| Resolusi | Bentuk |
|---|---|
| 1920x1080 | 16:9 |
| 1280x720 | 16:9 |
| 1024x768 | 4:3 |
| 640x480 | 4:3 |

Resolusi yang benar-benar dipakai ditentukan aplikasi yang membukanya.
Kamera terbuka pada 640x480 (4:3) secara bawaan, dan itulah yang dipakai
TikTok LIVE Studio. Karena kotak face cam dibuat 4:3, gambarnya kini pas
tanpa terpotong.

Bila ingin gambar lebih tajam, minta resolusi lebih tinggi pada aplikasi
siaran. Pilih 1024x768, bukan 1280x720, karena 1024x768 tetap 4:3
sehingga cocok dengan kotaknya.

## Ukuran huruf agar terbaca di ponsel

Penonton TikTok sebagian besar menonton dari ponsel, dan ponsel
menampilkan siaran pada lebar sekitar 360 sampai 400 piksel. Overlay
dirancang pada lebar 1080, jadi semuanya tampil sekitar sepertiga
ukurannya.

Artinya ukuran huruf di rancangan harus cukup besar. Sebagai patokan,
huruf di rancangan perlu minimal 30px supaya tampil minimal 10px di
ponsel, dan 10px adalah batas bawah yang masih nyaman dibaca.

Tabel berikut menunjukkan ukuran yang dipakai sekarang:

| Unsur | Di rancangan | Di ponsel |
|---|---|---|
| Judul slide | 46px | 15.3px |
| Nama merek | 40px | 13.3px |
| Keterangan slide | 32px | 10.7px |
| Butir dan label | 30px | 10.0px |
| Alamat situs | 68px | 22.7px |

Untuk memeriksa apakah ada unsur yang bertabrakan atau keluar dari layar
setelah ukuran huruf diubah:

```
python tools/periksa_luber_teks.py
python tools/bandingkan_ukuran_font.py
```

Alat pertama memeriksa tabrakan antar unsur dan batas layar. Alat kedua
membandingkan tata letak sebelum dan sesudah ukuran huruf diubah,
sehingga terlihat unsur mana yang bergeser.

Keduanya mengukur dengan Chrome, karena Chrome itulah yang dipakai
menampilkan overlay. Hasilnya sama dengan yang benar-benar terlihat
penonton.

## Ukuran jendela overlay dijaga otomatis

Windows mengembalikan ukuran jendela ke ukuran yang muat layar setiap
kali jendela dipulihkan dari keadaan diminimalkan. Pada layar 1080p,
jendela overlay yang tadinya 1080x1920 akan kembali menjadi 1080x1092.

Akibatnya isi jendela tidak lagi 9:16, dan aplikasi siaran menyisakan
pita kosong di kanan kiri sambil memperbesar gambar sehingga tampak
pecah. Masalah ini muncul setiap kali jendela di-minimize lalu dibuka
lagi.

Karena itu peluncur overlay menjalankan pemantau ukuran di latar
belakang. Pemantau memeriksa ukuran tiap dua detik dan menyetelnya
kembali bila menyimpang. Dengan begitu masalah itu tidak muncul lagi.

Pemantau hanya berjalan satu, dijaga oleh sistem Windows sendiri
(named mutex), jadi menjalankan peluncur berulang kali tidak menumpuk
pemantau.

Untuk memeriksa ukuran tanpa menunggu:

```
python tools/pantau_overlay.py --sekali
python tools/setel_jendela_overlay.py --periksa
```

Rasio isi jendela harus 0.5625, sama dengan 9 dibagi 16.
