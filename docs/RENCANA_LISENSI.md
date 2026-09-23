# Rencana Sistem Lisensi AkunTuntas

## Arsitektur

```
[Software Desktop]          [Supabase]                [Web Promosi]
  AkunTuntas.exe     <-->   akuntuntas-license   <-->  Vercel
  (Python/PySide6)          (Postgres + Edge Fn)       (Next.js/HTML)
   |                              |
   | kunci lisensi                | tabel: licenses
   | sidik perangkat              |        activations
   | tanda tangan digital         |        products
```

## Alur Aktivasi (Satu Lisensi = Satu Perangkat)

1. Pembeli bayar -> dapat **kunci lisensi** (format: `ATNT-XXXX-XXXX-XXXX-XXXX`)
2. Buka aplikasi -> layar **Aktivasi Lisensi** muncul SEBELUM login
3. Aplikasi hitung **sidik perangkat** (hash dari: nama komputer + volume disk + CPU + MAC)
4. Kirim ke Edge Function `activate-license` -> server catat perangkat pertama
5. Server balas **tanda tangan digital** (HMAC) berisi: kunci, perangkat, paket, masa berlaku
6. Aplikasi simpan tanda tangan itu secara lokal
7. Setiap kali buka, aplikasi **verifikasi tanda tangan** (offline, tanpa internet)
8. Bila perangkat berbeda -> DITOLAK: "lisensi sudah dipakai di perangkat lain"

## Kenapa Tidak Bisa Dibypass

| Serangan | Pertahanan |
|---|---|
| Ganti tanggal sistem | Tanda tangan berisi tanggal kedaluwarsa, diverifikasi ke server berkala |
| Copy folder aplikasi ke PC lain | Sidik perangkat berbeda -> tanda tangan tidak cocok |
| Edit file lisensi lokal | Tanda tangan HMAC rusak -> ditolak |
| Blokir internet | Masa tenggang 7 hari, lalu wajib verifikasi ulang |
| Bongkar EXE | Kunci HMAC tidak ada di EXE (disimpan di server) |

## Paket

| | Standar | Enterprise |
|---|---|---|
| Harga | Rp3.499.000 | Rp5.499.000 |
| Perangkat | 1 | Multi (5) |
| Fitur | Dasar | Semua |

## Batasan Fitur Standar

Fitur yang dikunci di Standar:
- Konsolidasi multi-entitas
- Multi-cabang
- Payroll lanjutan
- Dimensi (cost center, proyek)
- Pajak lanjutan (faktur pajak, uang muka, kurs)
- Audit lanjutan

## Tabel Database (Supabase)

```sql
products       -- paket & harga
licenses       -- kunci lisensi, paket, status, masa berlaku
activations    -- perangkat yang terdaftar per lisensi
pembelian      -- catatan pembelian
developer_keys -- kunci untuk dev xinet
```

## Edge Functions

- `activate-license`  -- aktivasi perangkat pertama
- `verify-license`    -- verifikasi berkala
- `deactivate-license` -- lepas perangkat (pindah PC)
- `check-version`     -- info versi terbaru
