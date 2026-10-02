# Panduan Lengkap TikTok LIVE Studio

Panduan ini menjelaskan cara memasang overlay AkunTuntas di TikTok LIVE
Studio, langkah demi langkah, dari nol sampai siap siaran.

Isinya:

1. Ringkasan tata letak
2. Menyiapkan overlay
3. Menyiapkan kamera
4. Memasang sumber di TikTok LIVE Studio
5. Mengatur posisi dan ukuran
6. Mengganti latar kamera (greenscreen)
7. Memeriksa hasil sebelum siaran
8. Mengatasi masalah
9. Padanan pengaturan dengan OBS dan Streamlabs


## 1. Ringkasan tata letak

Hasil siaran berukuran 1080x1920 (tegak, 9:16). Susunannya:

```
+--------------------------------------+
|  AkunTuntas              +---------+ |
|  lencana Store           | KAMERA  | |
|                          | 4:3     | |
|                          +---------+ |
|                                      |
|      +------------------------+      |
|      |                        |      |
|      |   layar promosi        |      |
|      |   (berganti slide)     |      |
|      |                        |      |
|      +------------------------+      |
|                                      |
|      akuntuntas.xinet.id             |
|      keunggulan bergilir             |
+--------------------------------------+
```

Keterangan:

- Kotak kamera di kanan atas, ukuran 400x300 (4:3)
- Layar promosi di tengah, berganti slide tiap 7 detik
- Tautan situs di bawah, menonjol dan mudah dibaca
- Tiga keunggulan bergilir di kaki layar


## 2. Menyiapkan overlay

Jalankan dari folder proyek:

```
python tools/jalankan_overlay.py --chrome
```

Yang terjadi:

- Jendela Chrome terbuka tanpa bilah alamat
- Isi jendela disetel otomatis ke 1080x1920
- Overlay langsung berjalan dan berganti slide

Penting: jendela ini jangan ditutup selama siaran. Biarkan terbuka,
boleh tertutup jendela lain.

Bila ingin memeriksa ukurannya:

```
python tools/jalankan_overlay.py --ukur
```

Ukuran isi jendela harus 1080x1920 dengan rasio 0.5625.

### Mengapa ukuran ini penting

Windows membatasi ukuran jendela ke ukuran layar. Pada layar 1080p,
jendela setinggi 1920 akan dipangkas menjadi sekitar 1090. Akibatnya:

- Isi jendela tidak lagi 9:16
- Aplikasi siaran menyisakan pita kosong di kanan dan kiri
- Gambar diperbesar untuk menutupi kanvas, sehingga tampak pecah

Perkakas peluncur mengatasi ini dengan penanda khusus Windows
(SWP_NOSENDCHANGING), sehingga isi jendela tetap 1080x1920 penuh. Dengan
begitu tidak ada pita kosong dan gambar tidak perlu diperbesar.

Bila jendela pernah dibuat dengan cara lama, tutup lalu jalankan ulang
perkakas peluncur.


## 3. Menyiapkan kamera

Kamera yang dipakai adalah kamera USB biasa. Tidak perlu perangkat lain.

Tempatkan kamera sehingga wajah berada di tengah bidang, dengan jarak
sekitar satu lengan. Cahaya sebaiknya dari depan, bukan dari belakang.

Untuk memeriksa kamera terdeteksi:

```
python tools/cek_bentuk_kamera.py
```

Kamera USB akan muncul dengan namanya, misalnya "USB Camera".


## 4. Memasang sumber di TikTok LIVE Studio

Urutan lengkapnya:

1. Buka TikTok LIVE Studio
2. Masuk ke halaman Studio, bukan halaman beranda
3. Pastikan kanvas berbentuk tegak. Ikon pemilih bentuk ada di kiri
   atas, pilih ikon persegi tegak (portrait)
4. Klik tombol "Add source"
5. Pada daftar yang muncul, pilih "Window capture"
6. Klik "Add"
7. Pada daftar jendela, pilih "AkunTuntas - Overlay Live"
8. Klik "Add" sekali lagi

Overlay sekarang tampil di kanvas.

Ulangi langkah 4 sampai 8 untuk kamera:

1. Klik "Add source"
2. Pilih "Camera"
3. Klik "Add"
4. Pada daftar perangkat, pilih "USB Camera"
5. Klik "Add"

Sekarang ada dua sumber: overlay dan kamera.


## 5. Mengatur posisi dan ukuran

### Overlay

Overlay harus menutupi seluruh kanvas.

1. Klik sumber "AkunTuntas - Overlay Live" di daftar kiri
2. Pada kanvas, tarik sudut overlay sampai menutupi seluruh bidang
3. Bila ada pilihan "Fit to screen" atau "Stretch", pilih itu

Hasilnya: overlay mengisi penuh 1080x1920, tanpa pita kosong di kanan
kiri.

### Kamera

Kamera diletakkan tepat menutupi kotak kamera di overlay.

Koordinat yang sudah diukur (kanvas 1080x1920):

| Bagian                 | X   | Y  | Lebar | Tinggi |
|------------------------|-----|----|-------|--------|
| Seluruh kotak kamera   | 646 | 40 | 400   | 300    |
| Bagian dalam (tanpa bingkai) | 650 | 44 | 392 | 292  |

Cara memasangnya:

1. Klik sumber "Camera" di daftar kiri
2. Pada kanvas, atur posisinya sehingga tepat menutupi kotak
3. Bila ada kolom isian posisi dan ukuran, isi sesuai tabel di atas

Perhatikan urutan lapisan: kamera harus DI ATAS overlay. Bila kamera
tertutup overlay, geser sumber kamera ke urutan teratas di daftar.

### Menyesuaikan bentuk kamera

Kamera USB umumnya menghasilkan gambar 4:3, sama seperti kotak di
overlay, jadi seharusnya pas. Bila gambarnya terpotong atau gepeng:

- Pilih "Fit" bila gambar terpotong
- Pilih "Fill" bila ada bagian kosong
- Jangan pilih "Stretch", karena membuat gambar gepeng


## 6. Mengganti latar kamera (greenscreen)

Ada dua jalan. Pilih yang paling nyaman.

### Jalan A: jendela kamera sendiri (paling pasti)

Jalan ini tidak bergantung pada fitur aplikasi, jadi hasilnya paling
pasti berhasil. Latar sudah diganti sebelum masuk ke aplikasi siaran.

1. Jalankan:

```
MULAI-KAMERA.bat
```

Atau lewat perintah:

```
python tools/jendela_kamera.py
```

2. Jendela "AkunTuntas - Kamera" terbuka, menampilkan kamera Anda dengan
   latar sudah bernuansa AkunTuntas.

3. Di TikTok LIVE Studio, klik "Add source", pilih "Window capture",
   lalu pilih jendela "AkunTuntas - Kamera".

4. Letakkan tepat menutupi kotak face cam:

| Bagian | X | Y | Lebar | Tinggi |
|---|---|---|---|---|
| Seluruh kotak kamera | 646 | 40 | 400 | 300 |
| Bagian dalam (tanpa bingkai) | 650 | 44 | 392 | 292 |

5. Jangan tambahkan sumber Camera lagi, karena jendela ini sudah
   menampilkan kameranya.

Kelebihan jalan ini:

- Bentuk gambar sudah 4:3, sama seperti kotak, jadi tidak terpotong
- Latar pasti berganti
- Tidak perlu mengatur apa pun di aplikasi siaran

### Jalan B: fitur bawaan TikTok LIVE Studio

Jalan ini memakai fitur pengganti latar milik TikTok LIVE Studio. Hasilnya
bergantung pada pencahayaan dan pengaturan.

Nama fiturnya pada daftar efek:

- "Virtual Background (Static/Dynamic)"
- Dalam bahasa Indonesia: "Latar belakang virtual (statis/dinamis)"

Langkahnya:

1. Klik sumber kamera di daftar kiri
2. Buka panel efek. Biasanya berupa ikon wajah atau ikon bintang di bilah
   bawah kanvas
3. Pilih kategori "background" atau "latar"
4. Pilih "Virtual Background (Static/Dynamic)"
5. Aktifkan pengaturan "Cutout". Tanpa ini, orangnya tidak dipisahkan
   dari latar, sehingga latar tidak akan berganti
6. Pilih gambar latar yang ingin dipakai

Gambar latar dibuat dengan:

```
python tools/buat_latar_kamera.py
```

Hasilnya ada di `live_overlay/gambar/`:

| Berkas | Kegunaan |
|---|---|
| `latar-akuntuntas.png` | Latar bernuansa AkunTuntas, 1600x1200 |
| `latar-hijau.png` | Hijau rata untuk chroma key |
| `latar-pratinjau-400x300.png` | Pratinjau ukuran sebenarnya |

Pengaturan yang perlu diperhatikan:

| Pengaturan | Arti | Saran nilai |
|---|---|---|
| Cutout | Memotong orang dari latar | aktifkan |
| Similarity | Kemiripan warna yang dianggap latar | 30 sampai 45 |
| Smoothness | Kehalusan tepi orang | 6 sampai 12 |
| Spill | Mengurangi pantulan warna | 8 sampai 15 |

Mulai dari nilai bawaan. Bila tepi badan masih bergerigi, naikkan
Smoothness. Bila ada bagian latar yang tersisa, naikkan Similarity.

### Bila latar tetap tidak mau berganti

Beberapa hal yang membantu:

- Pastikan pencahayaan merata, tidak ada bayangan tajam di dinding
- Pastikan wajah dan badan cukup terang
- Pastikan latar belakang tidak sama warnanya dengan pakaian
- Periksa kamera benar-benar mengirim gambar:

```
python tools/uji_kamera_hidup.py
```

- Pastikan kamera tidak sedang dipakai aplikasi lain. Kamera USB hanya
  dapat dipakai satu aplikasi dalam satu waktu:

```
python tools/cari_pemakai_kamera.py
```

Bila semuanya sudah dicoba dan tetap tidak berhasil, pakai Jalan A.
Jalan A tidak bergantung pada fitur aplikasi.

## 7. Memeriksa hasil sebelum siaran

Sebelum menekan Go LIVE, periksa lima hal ini pada pratinjau kanvas:

1. Tidak ada pita gelap di kanan dan kiri
2. Tulisan pada overlay terbaca, tidak pecah
3. Kamera menutupi kotak kamera dengan pas
4. Wajah terlihat jelas, tidak terlalu gelap
5. Tautan situs terbaca, termasuk pada layar ponsel

Untuk memeriksa dari sisi overlay saja:

```
python tools/potret_overlay.py
python tools/ukur_overlay.py
```

Hasil potret tersimpan di `_potret_overlay/`. Periksa berkas
`slide-7-situs.png`, di situ kotak kamera terlihat paling jelas.

Untuk memeriksa ukuran jendela overlay:

```
python tools/setel_jendela_overlay.py --periksa
```

Rasio isi jendela harus 0.5625, sama dengan 9 dibagi 16.


## 8. Mengatasi masalah

### Kamera terlihat diperbesar (ngezoom)

Penyebab: bentuk gambar kamera tidak sama dengan bentuk kotak face cam.
Kamera USB umumnya mengirim gambar 640x480 (4:3). Bila kotaknya berbentuk
16:9, sisi atas dan bawah gambar terpotong, sehingga wajah terlihat
diperbesar.

Perbaikan: kotak face cam sudah dibuat 4:3 (400x300) supaya cocok.
Bila masih terlihat diperbesar, periksa bentuk gambar kamera:

```
python tools/cek_bentuk_kamera.py
```

Bila kamera Anda mengirim 16:9, ubah kotaknya kembali ke 16:9 dengan
menyunting `live_overlay/overlay.html`, pada bagian `--cam-lebar` dan
`--cam-tinggi`.

### Pengganti latar tidak bekerja

Beberapa hal yang perlu diperiksa:

1. Pastikan efeknya benar-benar aktif. Buka panel efek, pilih kategori
   background, pilih "Virtual Background (Static/Dynamic)". Setelah
   aktif, akan muncul pengaturan Cutout, Similarity, dan Smoothness.

2. Aktifkan pengaturan Cutout. Tanpa itu, orangnya tidak dipisahkan dari
   latar.

3. Periksa pencahayaan. Fitur ini bekerja paling baik bila wajah dan
   badan cukup terang, dan latar belakang tidak sama warnanya dengan
   pakaian.

4. Periksa kamera benar-benar mengirim gambar. Bila gambar dari kamera
   gelap atau hitam, pemisahan latar tidak akan bekerja:

```
python tools/uji_kamera_hidup.py
```

5. Pastikan kamera tidak sedang dipakai aplikasi lain. Kamera USB hanya
   dapat dipakai satu aplikasi dalam satu waktu:

```
python tools/cari_pemakai_kamera.py
```

### Bila pengganti latar tetap tidak mau bekerja

Ada jalan lain yang tidak bergantung pada fitur aplikasi: jendela kamera
yang dibuat sendiri, sudah berlatar AkunTuntas.

```
python tools/jendela_kamera.py
```

Jendela ini menampilkan kamera dengan latar sudah diganti. Di aplikasi
siaran, tambahkan Window capture dan pilih jendela "AkunTuntas - Kamera",
lalu letakkan tepat menutupi kotak face cam.

Kelebihannya:

- Bentuk gambar sudah 4:3, sama seperti kotak, jadi tidak terpotong
- Latar pasti berganti, tanpa bergantung pada fitur aplikasi
- Ukuran jendelanya dapat diatur


### Pita gelap di kanan dan kiri kanvas

Penyebab: isi jendela overlay tidak tepat 9:16.

Perbaikan:

```
python tools/jalankan_overlay.py --chrome
```

Tutup jendela overlay yang lama lebih dahulu. Perkakas peluncur akan
menyetel ukuran penuh secara otomatis.

### Gambar terlihat pecah atau buram

Penyebab: jendela overlay lebih kecil daripada 1080x1920, sehingga
aplikasi siaran memperbesarnya.

Perbaikan: sama seperti di atas, jalankan ulang perkakas peluncur.
Setelah itu, pada TikTok LIVE Studio, setel ulang ukuran sumber overlay
ke penuh.

### Kotak kamera tampak kosong

Penyebab: kamera belum dipilih atau tertutup sumber lain.

Perbaikan:

1. Klik sumber kamera di daftar kiri
2. Periksa perangkat yang dipilih, harus "USB Camera"
3. Periksa urutan lapisan, kamera harus di atas overlay

### Kamera tidak muncul di daftar perangkat

Perbaikan:

1. Cabut dan pasang ulang kabel kamera
2. Tutup aplikasi lain yang sedang memakai kamera
3. Periksa kamera terdeteksi Windows:

```
python tools/cek_bentuk_kamera.py
```

### Overlay tidak berganti slide

Penyebab: jendela overlay tertutup, atau peramban menghentikan animasi
untuk jendela yang tidak aktif.

Perbaikan:

1. Periksa jendela "AkunTuntas - Overlay Live" masih terbuka
2. Bila tertutup, jalankan ulang perkakas peluncur

### Tulisan pada overlay tidak terbaca di ponsel

Perbaikan: perbesar ukuran tulisan pada berkas
`live_overlay/overlay.html`. Bagian yang perlu disesuaikan ada di dalam
blok `:root` di bagian atas berkas.


## 9. Padanan pengaturan dengan OBS dan Streamlabs

Bila nanti memakai OBS Studio atau Streamlabs, padanannya:

| TikTok LIVE Studio    | OBS Studio / Streamlabs          |
|-----------------------|----------------------------------|
| Window capture        | Window Capture                   |
| Camera                | Video Capture Device             |
| Virtual Background    | Filter Chroma Key + gambar latar |
| Similarity            | Similarity                       |
| Smoothness            | Smoothness                       |
| Spill                 | Spill Reduction                  |
| Kanvas tegak          | Settings, Video, 1080x1920       |

Untuk OBS dan Streamlabs, urutan lapisan sama: kamera di atas overlay.

Panduan khusus Streamlabs ada di `PANDUAN-STREAMLABS.md`.


## Pintasan berguna

| Tombol   | Fungsi                                |
|----------|---------------------------------------|
| Spasi    | Mempercepat ke slide berikutnya       |
| F11      | Layar penuh pada jendela peramban     |

Bila jendela overlay dalam keadaan layar penuh, tekan F11 lagi untuk
kembali. Ukuran jendela akan disetel ulang otomatis.


## Berkas terkait

| Berkas                            | Isi                              |
|-----------------------------------|----------------------------------|
| `live_overlay/overlay.html`       | Tampilan overlay                 |
| `live_overlay/gambar/`            | Gambar dan latar kamera          |
| `tools/jalankan_overlay.py`       | Membuka overlay                  |
| `tools/setel_jendela_overlay.py`  | Memeriksa dan menyetel ukuran    |
| `tools/buat_latar_kamera.py`      | Membuat gambar latar kamera      |
| `tools/cek_bentuk_kamera.py`      | Periksa bentuk gambar kamera      |
| `tools/ukur_overlay.py`           | Mengukur tata letak              |
| `tools/potret_overlay.py`         | Memotret tampilan overlay        |
