# Latar kamera dari fitur bawaan TikTok

Cara ini paling sederhana dan paling bersih. TikTok LIVE Studio sudah
punya fitur latar kamera sendiri yang bisa memakai gambar Anda. Jadi
sumbernya tetap Camera biasa, tidak perlu Window capture, tidak perlu
kamera virtual, dan tidak perlu alat tambahan apa pun.

Ini juga cara yang paling aman karena semua pemrosesan gambar dilakukan
oleh TikTok sendiri.

## Ringkas

| | |
|---|---|
| Sumber di TikTok | **Camera** (USB Camera langsung) |
| Latar dari | **Fitur Background bawaan TikTok** |
| Perlu Window capture | Tidak |
| Perlu kamera virtual | Tidak |
| Perlu alat tambahan | Tidak |

## Dua cara memasang gambar

**Cara pertama: daftarkan langsung (paling cepat)**

```
python tools/latar_ke_tiktok.py --pasang --tunggu
```

Perintah ini menaruh gambar di folder TikTok dan mendaftarkannya
sekaligus, jadi gambar langsung muncul di tab Background tanpa perlu
menambah manual. Perlu TikTok tertutup lebih dahulu, dan perintahnya
menunggu sendiri sampai Anda menutupnya.

**Cara kedua: tambah manual dari dalam TikTok**

Kalau lebih suka menambah sendiri lewat menu TikTok:

```
python tools/siapkan_latar_tiktok.py
```

Perintah itu membuat tiga berkas di folder
`live_overlay/gambar/siap-pakai-tiktok` dan menyalinnya juga ke
**Desktop/Latar Kamera AkunTuntas**:

| Berkas | Ukuran | Dipakai untuk |
|---|---|---|
| `latar-akuntuntas-4x3.jpg` | 1280x960 | **Pakai ini** kalau kamera Anda 4:3 |
| `latar-akuntuntas-16x9.jpg` | 1920x1080 | Kalau kamera Anda 16:9 |
| `latar-akuntuntas-9x16.jpg` | 1215x2160 | Kalau kanvas siaran tegak |

Kamera USB umumnya mengirim gambar 4:3, jadi pakai yang **4x3**. Bentuk
gambarnya sama dengan kamera, jadi tidak ada bagian yang terpotong.

## Langkah di TikTok LIVE Studio

1. Buka TikTok LIVE Studio, pilih kanvas Portrait kalau siaran tegak
2. Pada daftar sumber, klik sumber **Camera**
3. Buka pengaturan sumber itu. Tab yang tersedia:

   | Tab | Isi |
   |---|---|
   | **Background** | **Latar kamera, di sinilah tempatnya** |
   | Light | Pencahayaan |
   | Appearance | Tampilan |
   | Filter | Saringan warna |

4. Di tab **Background**, pilih **Custom**. Ini bagian untuk gambar
   Anda sendiri, di samping pilihan latar bawaan TikTok
5. Tambahkan gambar, arahkan ke folder
   **Desktop/Latar Kamera AkunTuntas**, pilih `latar-akuntuntas-4x3.jpg`
6. Nyalakan **Cutout**. Ini yang memisahkan orang dari latar, jadi
   hanya orangnya yang tampak di depan gambar AkunTuntas
7. Kalau ruangan Anda punya kain hijau, pilih **Green screen** dan
   pilih warna kainnya
8. Atur **Background opacity** kalau gambarnya terlalu pekat
9. Tekan **Save**

## Mengatur bentuk dan posisi

| Tombol | Gunanya |
|---|---|
| Crop | Memotong gambar supaya pas |
| Adjust | Menggeser dan mengatur ukuran |
| Original | Kembali ke bentuk asli |

TikTok menulis di layarnya: "Aspect ratio aligns with your camera" yang
artinya bentuk gambar mengikuti bentuk kamera. Itu sebabnya gambar 4:3
paling cocok untuk kamera USB.

## Batas dan persyaratan

Angka ini dibaca langsung dari pengaturan TikTok:

| | Batas TikTok | Gambar kita |
|---|---|---|
| Jumlah latar sendiri | 20 gambar | 1 gambar |
| Resolusi paling kecil | 500 x 500 piksel | 1600 x 1200 |
| Ukuran berkas | 30 MB | 77 KB |
| Bentuk berkas | JPG atau PNG | JPG |

Semuanya jauh di dalam batas, jadi tidak ada masalah.

## Memeriksa dan menghapus

```
python tools/latar_ke_tiktok.py --daftar
python tools/latar_ke_tiktok.py --lepas
```

Perintah pertama menampilkan berapa latar yang terdaftar. Perintah
kedua menghapus latar AkunTuntas beserta berkasnya.

## Kalau daftar tidak mau berubah

TikTok menyimpan daftarnya sendiri setiap beberapa detik. Kalau TikTok
sedang berjalan, perubahan akan tertimpa dalam sepuluh detik. Karena itu
TikTok wajib ditutup lebih dahulu. Pakai `--tunggu` supaya tidak perlu
mencoba berulang kali.

## Catatan penting

TikTok memproses gambarnya sendiri, jadi Anda tidak perlu menjalankan
alat apa pun saat siaran. Cukup pilih latarnya sekali, lalu tekan Save.
Setelah itu tinggal siaran seperti biasa.

## Bukti bahwa ini bekerja

Sudah diperiksa sampai ke berkas catatan TikTok. Saat TikTok dibuka,
layanannya memuat gambar kita ke daftar gambarnya:

```
[ImageManagerService] _getImages: localImages: [
  {"id":"akuntuntas-48f9d8dd-0ed0-4649-b8c0-b838c7f46eed",
   "path":"...\origin.jpg",
   "deletable":true,
   "cropped":[{"ratio":0.562,"width":1215,"height":2160}],
   "isAiImage":false}
]
```

Tiga hal yang sudah dipastikan:

1. TikTok membaca daftar yang kita tulis
2. TikTok menyimpan ulang daftarnya dengan bentuknya sendiri, dan
   entri kita tetap dipertahankan
3. Layanan gambar TikTok memuat gambar kita saat aplikasi dibuka

## Mengatur supaya orang terlihat di depan latar

Bagian ini yang membuat latar berguna. Tanpa ini, gambar hanya akan
menutupi seluruh kamera.

| Pilihan | Gunanya | Kapan dipakai |
|---|---|---|
| **Cutout** | Memisahkan orang dari latar asli | Paling sering, tanpa alat tambahan |
| **Green screen** | Menghapus warna tertentu | Kalau ada kain hijau di belakang |
| **Chroma key** | Sama seperti green screen, lebih halus | Kalau warna latar tidak rata |
| **Background opacity** | Mengatur kepekatan gambar | Kalau gambar terlalu mencolok |

Nyalakan **Cutout** lebih dahulu. Kalau hasilnya bergerigi di tepi,
baru coba green screen dengan kain hijau di belakang Anda.

## Kalau gambar tidak muncul di TikTok

1. Pastikan TikTok ditutup saat memasang, lalu buka lagi
2. Periksa daftarnya: `python tools/latar_ke_tiktok.py --daftar`
3. Kalau tertulis "berkasnya hilang", pasang ulang:
   `python tools/latar_ke_tiktok.py --pasang`
4. Kalau masih tidak muncul, pasang manual:
   `python tools/siapkan_latar_tiktok.py`, lalu tambahkan sendiri dari
   dalam TikTok memakai tombol tambah gambar

## Kalau gambar tersendat

TikTok sendiri yang memberi peringatan ini di layarnya:

- "Using the virtual background might cause frame drops in your current
  setup. Consider hardware upgrades."
- "Frame drops detected. Turn off the virtual background for smoother
  video."

Kalau itu muncul:

1. Matikan dulu efek kamera lain seperti makeup dan filter
2. Turunkan mutu siaran
3. Kalau masih tersendat, pakai Jalan A atau Jalan C sebagai gantinya

## Kelebihan cara ini

- Paling sedikit langkahnya
- Tidak ada alat tambahan yang perlu dijalankan
- Tidak ada jendela yang perlu dibuka
- Gambar diproses oleh TikTok sendiri
- Sumbernya Camera asli, jadi kualitasnya paling baik
- Aman dari perubahan versi, karena ini fitur resmi TikTok

## Kekurangan cara ini

- Bentuk gambar mengikuti kamera, jadi tidak bisa bebas
- Ada peringatan performa kalau komputer kurang kuat
- Tidak bisa mengatur posisi orang seperti di kamera virtual
