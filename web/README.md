# AkunTuntas — Situs Promosi

Situs promosi dan penjualan AkunTuntas. Dibuat sebagai situs statis tanpa
proses build, sehingga dapat langsung dipasang di Vercel, Netlify, atau
GitHub Pages.

## Isi

| Berkas | Keterangan |
|---|---|
| `index.html` | Halaman utama: fitur, harga, dan ketentuan lisensi |
| `styles.css` | Tampilan situs |
| `logo.svg` | Logo AkunTuntas, sama dengan yang dipakai di aplikasi |
| `vercel.json` | Pengaturan pemasangan di Vercel |

## Warna

Warna diambil dari aplikasi supaya situs dan aplikasi terlihat satu kesatuan.

| Nama | Kode | Dipakai untuk |
|---|---|---|
| Biru utama | `#1B4F8A` | Tombol, judul, aksen |
| Biru tua | `#143C6B` | Keadaan hover |
| Navy | `#0F2942` | Latar bagian gelap, kaki halaman |
| Teks | `#1A2733` | Tulisan utama |
| Abu teks | `#556577` | Tulisan penjelas |

## Pemasangan di Vercel

```bash
cd web
vercel --prod
```

Atau lewat dasbor Vercel: hubungkan repositori, lalu pilih folder `web`
sebagai akar proyek.

## Menyesuaikan

- **Harga** ada di bagian `#harga` pada `index.html`.
- **Nomor WhatsApp** dan **email** ada di bagian `#kontak` dan di kaki
  halaman.
- **Fitur per paket** ada di daftar `paket-fitur` pada tiap kartu harga.
