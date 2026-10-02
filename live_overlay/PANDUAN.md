# Overlay Live TikTok - AkunTuntas

Overlay siaran langsung berukuran 9:16 untuk mempromosikan AkunTuntas.
Tata letaknya bergerak sendiri: slide berganti tiap 7 detik, keunggulan
bergilir di bawah, dan ada kilau yang menyapu di bagian ajakan.

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

Kotak face cam berada di kanan atas, menumpuk di atas kepala dan bagian
atas slide. Isi slide sengaja diberi ruang kosong di kanan atas supaya
tidak ada teks yang tertutup wajah penyiar.

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

Di TikTok LIVE Studio atau OBS, tambahkan sumber:

- **Window Capture**, lalu pilih jendela peramban overlay, atau
- **Display Capture** bila ingin menangkap seluruh layar.

Lalu tambahkan sumber kamera dan letakkan menutupi kotak face cam.

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
```

Menghasilkan potret 1080x1920 untuk tiap jenis slide di `_potret_overlay/`,
supaya tampilannya dapat diperiksa tanpa harus membuka peramban.

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
