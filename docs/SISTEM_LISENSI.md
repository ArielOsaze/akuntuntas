# Sistem Lisensi AkunTuntas — Ringkasan Teknis

## Arsitektur

```
[Aplikasi Desktop]        [Supabase]              [Web Promosi]
  AkunTuntas.exe   <-->   akuntuntas-license  <-->  Vercel
  (Python/PySide6)        (Postgres + Edge Fn)      (halaman jualan)
```

- **Vercel tidak bisa jadi database.** Vercel hanya hosting web. Database lisensi
  wajib di Supabase (Postgres) karena butuh: kunci unik, batas perangkat, dan
  tanda tangan digital yang tidak bisa dipalsukan.
- **Supabase = sumber kebenaran lisensi.** Aplikasi desktop hanya memegang kunci
  publik untuk memeriksa tanda tangan. Kunci privat tidak pernah ada di aplikasi.

## Alur Aktivasi

1. Pembeli membayar, dapat kunci: `ATNT-XXXX-XXXX-XXXX-XXXX`
2. Buka aplikasi, layar **Aktivasi Lisensi** muncul SEBELUM login
3. Aplikasi hitung sidik perangkat (hash: nama komputer + volume disk + CPU + MAC)
4. Kirim ke Edge Function `license` -> server catat perangkat
5. Server balas tanda tangan Ed25519 (kunci privat hanya di server)
6. Aplikasi simpan tanda tangan lokal, verifikasi setiap kali dibuka (offline)
7. Perangkat berbeda -> DITOLAK

## Kenapa Tidak Bisa Dibypass

| Serangan | Pertahanan |
|---|---|
| Copy folder ke PC lain | Sidik perangkat beda -> tanda tangan tidak cocok |
| Edit berkas lisensi lokal | Tanda tangan Ed25519 rusak -> ditolak |
| Ganti tanggal sistem | Tanda tangan berisi masa berlaku, diverifikasi ke server |
| Blokir internet | Masa tenggang 7 hari, lalu wajib verifikasi ulang |
| Bongkar EXE | Kunci privat tidak ada di EXE (hanya di server) |

## Paket

| | Standar | Enterprise |
|---|---|---|
| Harga | Rp3.499.000 | Rp5.499.000 |
| Perangkat | 1 | 5 |
| Fitur | Dasar | Semua |

Fitur yang dikunci di Standar (tidak muncul):
- Konsolidasi multi-entitas
- Multi-cabang
- Payroll lanjutan
- Dimensi (cost center, proyek)
- Pajak lanjutan
- Audit lanjutan

## Tabel Database

| Tabel | Isi |
|---|---|
| `products` | paket, harga, batas perangkat, fitur |
| `licenses` | kunci lisensi, pemilik, status, masa berlaku |
| `activations` | perangkat terdaftar per lisensi |
| `activation_log` | riwayat semua percobaan aktivasi |
| `orders` | pesanan pembelian |
| `developer_accounts` | akun developer (Xinet Group) |
| `server_secrets` | kunci privat penanda tangan (hanya server) |

## Cara Menerbitkan Lisensi

Di Supabase SQL Editor:

```sql
-- Lisensi standar
select terbitkan_lisensi('standar', 'Nama Pembeli', 'email@contoh.com', '0812xxx');

-- Lisensi enterprise
select terbitkan_lisensi('enterprise', 'PT Contoh', 'email@contoh.com', '0812xxx');
```

Hasilnya kunci siap kirim ke pembeli: `ATNT-XXXX-XXXX-XXXX-XXXX`

## Cara Mencabut Lisensi (mis. dibajak)

```sql
update licenses set status = 'dicabut' where license_key = 'ATNTXXXXXXXXXXXX';
```

Lisensi langsung tidak bisa dipakai lagi saat verifikasi berikutnya.

## Melihat Perangkat Terdaftar

```sql
select * from v_ringkasan_lisensi;
```

## Memindahkan Lisensi ke PC Baru

```sql
-- lepas semua perangkat lisensi itu
update activations set aktif = false
where license_id = (select id from licenses where license_key = 'ATNTXXXXXXXXXXXX');
```

## Endpoint

```
POST https://<ref>.supabase.co/functions/v1/license
```

Aksi: `aktivasi` (bawaan), `lepas`, `kunci-publik`

## Pasal & Ketentuan (untuk halaman web)

1. Lisensi bersifat **tidak eksklusif** dan tidak dapat dipindahtangankan tanpa izin tertulis.
2. Dilarang **memperjualbelikan kembali**, menyewakan, atau mendistribusikan aplikasi.
3. Dilarang **membypass**, membongkar, memodifikasi, atau menghapus sistem lisensi.
4. **Hak cipta** melekat pada Xinet Group. Pelanggaran dapat dituntut secara hukum.
5. Lisensi Standar: 1 perangkat. Lisensi Enterprise: sesuai jumlah yang tertera.
6. Pelanggaran mengakibatkan **pencabutan lisensi tanpa pengembalian dana**.
