# Catatan Rilis Internal AkunTuntas

> **BERKAS INI TIDAK UNTUK DIPUBLIKASIKAN.**
> Jangan menyalin isinya ke Partner Center, halaman web, atau balasan
> ke pengguna. Berkas ini hanya untuk keperluan pengembangan, penelusuran
> masalah, dan pengujian.
>
> Catatan rilis yang aman dipublikasikan ada di `docs/catatan-rilis.md`.

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
