# Overlay Live TikTok - AkunTuntas

Overlay siaran langsung berukuran 9:16 untuk mempromosikan AkunTuntas.
Tata letaknya bergerak sendiri: slide berganti tiap 7 detik, keunggulan
bergilir di bawah, dan ada kilau yang menyapu di bagian ajakan.

---

## Mulai cepat

Dua berkas ini menjalankan semuanya. Klik dua kali, tidak perlu perintah.

| Berkas | Kegunaan |
|---|---|
| `MULAI-OVERLAY.bat` | Membuka overlay layar promosi |
| `MULAI-KAMERA.bat` | Kamera dengan latar AkunTuntas (Window capture) |
| `MULAI-KAMERA-VIRTUAL.bat` | Kamera virtual, dipakai lewat sumber Camera |

Langkahnya:

1. Klik dua kali `MULAI-OVERLAY.bat`
2. Klik dua kali `MULAI-KAMERA.bat`
3. Di TikTok LIVE Studio, tambahkan dua sumber:
   - Window capture, pilih "AkunTuntas - Overlay Live"
   - Window capture, pilih "AkunTuntas - Kamera"
4. Letakkan overlay menutupi seluruh kanvas, kamera di kanan atas

Panduan langkah demi langkah untuk TikTok LIVE Studio ada di
`PANDUAN-TIKTOK-STUDIO.md`.

Catatan penting tentang kamera ada di `CATATAN-KAMERA.md`.

---

## Tampilan

```
┌──────────────────────────────────────────┐
│  [LOGO] AkunTuntas                       │
│  Pembukuan & Pajak Indonesia             │
├──────────────────────────────────────────┤
│                                          │
│  PEMBUKUAN                               │
│  Pembukuan rapi, pajak akurat            │
│  Satu aplikasi untuk mencatat...         │
│  ┌────────────────────────────────┐      │
│  │  [gambar aplikasi / situs]     │      │
│  │                        ┌──────┐│      │
│  │                        │  96  ││      │
│  │                        └──────┘│      │
│  └────────────────────────────────┘      │
│  ✓ Jurnal umum   ✓ Neraca saldo          │
├──────────────────────────────────────────┤
│  ● KUNJUNGI SEKARANG                     │
│  akuntuntas.xinet.id|                    │
│  [Unduh gratis] [Standar] [Enterprise]   │
│              ┌──────────────────┐        │
│              │  Buka di         │        │
│              │  peramban Anda   │        │
│              └──────────────────┘        │
├──────────────────────────────────────────┤
│  ✓ Bekerja offline, data di komputer Anda│
└──────────────────────────────────────────┘
```

Kotak face cam berada di kanan atas dengan bentuk **4:3**
(400x300 piksel), sama seperti kamera pada umumnya, sehingga wajah tidak
terpotong saat ditampilkan. Isi slide sengaja diberi ruang kosong di kanan
atas supaya tidak ada teks yang tertutup wajah penyiar.

Tidak ada lencana merah bertulisan LIVE di kotak ini, supaya tidak ada
elemen merah yang menutupi tampilan.

---

## Cara menjalankan

```
python tools/jalankan_overlay.py --chrome
```

Jendela terbuka dengan ukuran 9:16 tanpa bilah alamat, supaya yang
tertangkap siaran hanya overlaynya.

Peramban yang didukung: `--chrome`, `--brave`. Tanpa pilihan, overlay
dibuka di peramban bawaan.

Panduan lengkap: `python tools/jalankan_overlay.py --info`

---

## Mengisi kotak face cam

**Cara A, paling mudah.** Biarkan kotak itu sebagai penanda. Di aplikasi
siaran (TikTok LIVE Studio atau OBS), tambahkan sumber kamera dan letakkan
tepat menutupi kotak tersebut. Atur sekali, lalu simpan.

**Cara B.** Buka overlay di Chrome atau Brave, lalu izinkan akses kamera
saat diminta. Kamera tampil sendiri di dalam kotak.

---

## Menangkap overlay di aplikasi siaran

Di TikTok LIVE Studio, OBS, atau Streamlabs, tambahkan sumber:

- **Window Capture**, lalu pilih jendela peramban overlay, atau
- **Display Capture** bila ingin menangkap seluruh layar.

Lalu tambahkan sumber kamera dan letakkan menutupi kotak face cam.

### Panduan per aplikasi

| Aplikasi | Panduan |
|---|---|
| **TikTok LIVE Studio** | `live_overlay/PANDUAN-TIKTOK-STUDIO.md` |
| **Streamlabs Desktop** | `live_overlay/PANDUAN-STREAMLABS.md` |
| OBS Studio | Sama seperti Streamlabs, nama menunya hampir sama |

### Mengganti latar kamera

TikTok LIVE Studio sudah punya fitur pengganti latar bawaan, jadi latar
kamera bisa langsung diganti tanpa aplikasi tambahan. Buat gambar
latarnya lebih dahulu:

```
python tools/buat_latar_kamera.py
```

Lalu pasang "Virtual Background (Static/Dynamic)" pada sumber kamera.
Langkah lengkapnya ada di `PANDUAN-TIKTOK-STUDIO.md` bagian 6.

### Catatan penting tentang kamera

Masalah bentuk gambar, kamera yang dipakai aplikasi lain, dan
pengganti latar dibahas di `live_overlay/CATATAN-KAMERA.md`.

### Koordinat kamera

Bila aplikasi siaran meminta angka posisi dan ukuran, jalankan:

```
python tools/koordinat_kamera.py
```

Alat itu mengukur posisi kotak kamera langsung dari overlay dan
menampilkan angka yang siap disalin. Bawaannya:

| Bagian | X | Y | Lebar | Tinggi |
|---|---|---|---|---|
| Overlay penuh | 0 | 0 | 1080 | 1920 |
| Kamera (dalam bingkai) | 650 | 44 | 392 | 217 |
| Kamera (seluruh kotak) | 646 | 40 | 400 | 225 |

---

## Mengubah isi

Buka `live_overlay/overlay.html`. Bagian yang biasa diubah ada di dalam
blok `<script>`, yaitu:

| Bagian | Kegunaan |
|---|---|
| `DURASI` | Lama tiap slide tampil, bawaan 7000 milidetik |
| `SLIDE` | Isi dan urutan slide: label, judul, keterangan, gambar, daftar |
| `KAKI` | Teks keunggulan yang bergilir di bagian bawah |

Ukuran dan letak kotak face cam diatur di blok `:root` pada bagian atas
berkas: `--cam-lebar`, `--cam-tinggi`, `--cam-atas`, `--cam-kanan`, dan
`--cam-cadangan`.

Bawaannya `--cam-lebar: 400px` dan `--cam-tinggi: 225px`, yaitu 16:9.
Bila diubah, jaga perbandingannya tetap 16:9 dengan mengalikan lebar
dengan 0,5625. Contoh: lebar 512 berarti tinggi 288.

---

## Isi slide

| Slide | Tema | Gambar |
|---|---|---|
| 1 | Pembukuan | Tangkapan layar Dashboard |
| 2 | Perpajakan | Tangkapan layar Pajak & SPT |
| 3 | Penjualan | Tangkapan layar Penjualan |
| 4 | Laporan | Tangkapan layar Laporan Keuangan |
| 5 | Payroll | Tangkapan layar Payroll |
| 6 | Persediaan | Tangkapan layar Produk & Persediaan |
| 7 | Situs resmi | Halaman beranda situs |
| 8 | Harga | Halaman harga situs |

---

## Pintasan

| Tombol | Kegunaan |
|---|---|
| Spasi | Percepat ke slide berikutnya |
| F11 | Layar penuh di peramban |

---

## Memeriksa tampilan

```
python tools/potret_overlay.py
python tools/ukur_overlay.py
```

Yang pertama menghasilkan potret 1080x1920 untuk tiap jenis slide di
`_potret_overlay/`. Yang kedua mengukur tata letak langsung dari mesin
peramban: ukuran kotak kamera, apakah isinya muat, dan apakah gambar situs
mengisi penuh wadahnya.

Ukuran diukur langsung, bukan dinilai dari potret, karena proporsi pada
potret dapat terlihat berbeda dari ukuran sebenarnya.

---

## Catatan

- **Tidak ada kode QR.** TikTok membatasi tampilan kode QR di siaran, jadi
  ajakan memakai tautan yang ditulis besar.
- Gambar bersumber dari `store_gambar/` (tangkapan aplikasi) dan
  `_potret_web/` (tangkapan situs). Bila tampilan aplikasi atau situs
  berubah, potret ulang dengan:

```
python tools/tangkapan_store.py
python tools/potret_situs.py
```

Lalu salin ulang ke `live_overlay/gambar/`.
