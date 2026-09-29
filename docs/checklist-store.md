# Checklist Pengiriman ke Microsoft Store

Diperiksa: 29 September 2026 (malam)
Versi aplikasi: 1.2.9

---

## 1. Berkas yang diunggah

| Berkas | Ukuran | Keterangan |
|---|---|---|
| `msix_output/AkunTuntas.msixupload` | 129.4 MB | **Ini yang diunggah ke Partner Center** |
| `msix_output/AkunTuntas.msix` | 131.6 MB | Untuk diperiksa sendiri |

Sidik jari:

```
.msixupload  sha256 372e6c29ef3ae424004ef327efc506bc76021e0619c9099f793a610b3b45970d
.msix        sha256 a2761ce73c5d33884f4744d6c5051fa5b2ff864191b014b450eafcdcd8354324
```

---

## 2. Identitas paket

Nilai ini **harus sama persis** dengan yang tertulis di Partner Center
(menu Product management > Product identity). Bila berbeda satu huruf,
paket ditolak.

| Kolom | Nilai |
|---|---|
| Nama paket | `XinetGroup.AkunTuntas` |
| Penerbit | `CN=82AE483E-A9EB-487B-BDE6-4D690C249608` |
| Nama penerbit | `Xinet Group` |
| Nama tampil | `AkunTuntas` |
| Versi | `1.2.9.0` |

Bila Partner Center memberi nilai yang berbeda, perbarui
`msix/identitas.json` lalu bungkus ulang:

```bash
python tools/bungkus_msix.py --siapkan
python tools/bungkus_msix.py --bungkus
python tools/bungkus_msix.py --periksa
```

---

## 3. Tangkapan layar

Enam berkas di `store_gambar/`, seluruhnya 1366x768 piksel (ukuran
terkecil yang diterima). Salinan juga ada di Desktop pada folder
`AkunTuntas-Gambar-Store`.

| Berkas | Halaman |
|---|---|
| 01-dashboard.png | Dashboard |
| 02-penjualan.png | Penjualan |
| 03-pajak.png | Pajak dan SPT |
| 04-laporan.png | Laporan Keuangan |
| 05-payroll.png | Payroll |
| 06-produk.png | Produk dan Persediaan |

---

## 4. Teks untuk halaman Store

Salin dari `docs/materi-store.md`:

| Kolom Partner Center | Sumber |
|---|---|
| Nama produk | AkunTuntas |
| Deskripsi singkat (200 huruf) | Bagian "Deskripsi singkat" |
| Deskripsi lengkap | Bagian "Deskripsi lengkap" |
| Kategori | Business > Accounting & Finance |
| Harga | Gratis (lisensi dijual di situs) |
| Bahasa utama | Indonesia (id-ID) |

---

## 5. Catatan untuk sertifikasi (PALING PENTING)

Kolom ini menentukan lolos atau tidaknya pengujian. Salin dari
`docs/teks-siap-tempel.md` bagian catatan sertifikasi.

Ringkasnya:

```
Aplikasi ini tidak memerlukan akun demo khusus dan tidak memerlukan
sambungan internet.

LANGKAH PENGGUNAAN
1. Setelah aplikasi dibuka, halaman masuk akan langsung ditampilkan.
2. Masukkan nama pengguna: admin
3. Masukkan kata sandi: admin123
4. Aplikasi akan meminta Anda mengganti kata sandi. Masukkan kata sandi
   baru, misalnya UjiCoba2026, lalu lanjutkan.
5. Pilih mode pemakaian: Pemula atau Ahli. Keduanya dapat dipilih.
6. Aplikasi siap dipakai. Seluruh fitur terbuka, termasuk Dimensi dan
   Biaya, Konsolidasi Grup, serta Pajak Lanjutan.

CATATAN PENTING
- Aplikasi ini tidak memerlukan kunci lisensi pada versi ini. Layar
  aktivasi lisensi sengaja dilewati agar dapat diuji sepenuhnya.
- Seluruh data disimpan di komputer setempat dan tidak dikirim ke mana pun.
- Aplikasi tidak memerlukan sambungan internet untuk diuji.
- Untuk mencoba fitur pajak, buka menu Data Perusahaan lalu isi data
  perusahaan, lalu buka menu Pajak dan SPT.
- Untuk mencoba laporan keuangan, buka menu Penjualan lalu masukkan satu
  transaksi, lalu buka menu Laporan Keuangan.

Bila ada kendala saat menguji, hubungi akuntuntas@gmail.com.
```

**Catatan:** kata sandi demo adalah `admin123`, BUKAN `admin`. Aplikasi
meminta penggantian kata sandi setelah masuk pertama kali, dan itu memang
perilaku yang diinginkan.

---

## 6. Hasil verifikasi sebelum kirim

| Pemeriksaan | Hasil |
|---|---|
| Tes lengkap aplikasi | 1642 LULUS, 0 GAGAL |
| Audit tampilan (27 halaman + 2 dialog) | Bersih |
| Kontras WCAG AA | Seluruh teks lulus |
| Gaya menular | Tidak ada |
| Keseragaman versi | Seluruh berkas 1.2.9 |
| Pemasangan ulang | Data pembukuan tetap utuh |
| Kompatibilitas | Windows 10 (1809+) dan 11, 64-bit |
| Uji alur peninjau Store (mode paket) | 20 LULUS, 0 GAGAL |
| Uji celah masa uji coba | 19 AMAN, 0 BOCOR |
| Uji jalan dari susunan folder paket | LULUS, judul jendela bersih |
| Isi paket MSIX | Manifest, exe, penanda, ikon lengkap |
| Versi tertanam di EXE | 1.2.9.0 (dibaca lewat Windows API) |
| Sidik EXE di paket vs hasil build | Cocok |

---

## 7. Langkah mengirim

1. Buka https://partner.microsoft.com/dashboard
2. Pilih **Apps and games** > produk **AkunTuntas**
3. Menu **Packages** > unggah `AkunTuntas.msixupload`
4. Menu **Store listing** > salin teks dari `docs/materi-store.md`
5. Unggah 6 tangkapan layar dari `store_gambar/`
6. Menu **Properties** > kategori Business > Accounting & Finance
7. Menu **Age ratings** > isi kuesioner
8. Kolom **Notes for certification** > salin dari `docs/teks-siap-tempel.md`
9. Menu **Pricing and availability** > pilih negara
10. Tekan **Submit for certification**

Pengujian Microsoft memakan waktu **2 sampai 7 hari kerja**. Bila ada yang
kurang, mereka mengirim keterangan lewat email dan Anda dapat memperbaiki
lalu mengirim ulang tanpa biaya tambahan.

---

## 8. Hal yang perlu diperhatikan

**Paket TIDAK boleh memuat `uji_coba.txt`.** Masa uji coba sekarang
dihitung dari catatan di komputer pengguna selama 1 hari, bukan dari berkas
di dalam paket. Paket yang diuji peninjau Microsoft adalah paket yang SAMA
dengan yang diunduh semua orang dari Store, sehingga berkas penanda apa pun
di dalamnya akan menjadi lisensi gratis untuk seluruh dunia.

Periksa dengan `python tools/bungkus_msix.py --periksa`. Keluarannya harus
menyebut `uji_coba.txt tidak ada (benar)`. Bila menyebut BAHAYA, bungkus
ulang paketnya sebelum dikirim.

**Paket MSIX belum ditandatangani.** Microsoft Store yang menandatanganinya
saat paket diterima. Ini justru yang menghilangkan peringatan SmartScreen
pada pengguna.

**Versi MSIX wajib empat angka.** Tulis `1.2.9.0`, bukan `1.2.9`.

**Untuk setiap pembaruan ke Store**, naikkan versi dan pastikan paket tidak memuat
berkas penanda. Masa uji coba 1 hari otomatis berlaku di setiap komputer yang
baru memasang, sehingga peninjau selalu dapat menguji versi terbaru.
