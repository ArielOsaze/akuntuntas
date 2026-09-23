# Menerbitkan AkunTuntas di Microsoft Store

Panduan ini menempuh jalur gratis untuk menghilangkan peringatan Windows.
Microsoft Store menandatangani paket dengan sertifikatnya sendiri, sehingga
pembeli tidak melihat peringatan apa pun saat memasang.

## Kenapa jalur ini dipilih

Windows memunculkan peringatan "penerbit tidak dikenal" untuk setiap berkas
yang belum ditandatangani. Sertifikat code signing berbayar sekitar $211 per
tahun. Microsoft Store menyediakan penandatanganan **gratis** dan sekaligus
menghilangkan peringatan sepenuhnya, termasuk peringatan SmartScreen.

Bandingkan dengan sertifikat berbayar yang **masih** memunculkan peringatan
SmartScreen sampai reputasi berkas terbentuk dari jumlah unduhan.

## Yang sudah disiapkan di repositori

| Berkas | Kegunaan |
|---|---|
| `tools/bungkus_msix.py` | Menyusun dan membungkus paket MSIX |
| `src/akuntansi_id/core/uji_coba.py` | Mode uji coba untuk peninjau Store |
| `msix/identitas.json` | Identitas penerbit dari Partner Center |
| `msix/AppxManifest.xml` | Manifest paket, dibuat otomatis |
| `msix/Assets/` | Ikon MSIX lima ukuran, dibuat otomatis |

## Langkah yang perlu Anda kerjakan

### 1. Daftar akun pengembang Microsoft Store

Buka https://storedeveloper.microsoft.com/ lalu daftar sebagai
**individu**. Biayanya **gratis** sejak September 2025 dan akun berlaku
selamanya.

Siapkan:
- Akun Microsoft (bisa akun Outlook yang sudah ada)
- Kartu identitas untuk verifikasi umur
- Nomor telepon aktif

Pendaftaran biasanya selesai dalam beberapa menit sampai dua hari.

### 2. Buat nama produk di Partner Center

Setelah akun aktif, buka https://partner.microsoft.com/dashboard lalu:

1. Pilih **Apps and games** lalu **New product**
2. Pilih **MSIX or PWA app**
3. Isi nama produk: **AkunTuntas**
4. Pesan nama itu supaya tidak diambil pengembang lain

### 3. Ambil identitas produk

Masuk ke **Product management** lalu **Product identity**. Di situ ada tiga
nilai yang wajib disalin persis:

| Kolom di Partner Center | Isi ke `msix/identitas.json` |
|---|---|
| Package/Identity/Name | `nama_paket` |
| Package/Identity/Publisher | `penerbit` |
| Package/Properties/PublisherDisplayName | `nama_penerbit_tampil` |

Buat berkas `msix/identitas.json` dengan bentuk seperti ini:

```json
{
  "nama_paket": "12345XinetGroup.AkunTuntas",
  "penerbit": "CN=ABC12345-6789-ABCD-EF01-234567890ABC",
  "nama_penerbit_tampil": "Xinet Group",
  "nama_tampil": "AkunTuntas",
  "versi": "1.0.0.0",
  "deskripsi": "Pembukuan dan pajak perusahaan Indonesia"
}
```

Nilai `nama_paket` dan `penerbit` **harus sama persis** dengan yang tertulis
di Partner Center. Bila berbeda satu huruf, paket akan ditolak.

### 4. Bungkus paketnya

```bash
python -m PyInstaller build.spec --noconfirm
python tools/bungkus_msix.py --siapkan
python tools/bungkus_msix.py --bungkus
python tools/bungkus_msix.py --periksa
```

Hasilnya ada di `msix_output/AkunTuntas.msix`.

### 5. Isi halaman Store

Saat mengirim produk, Partner Center meminta:

**Halaman utama**
- Nama produk: AkunTuntas
- Deskripsi singkat (maksimal 200 huruf)
- Deskripsi lengkap
- Kategori: **Business** lalu **Accounting & Finance**

**Gambar yang diwajibkan**
- Tangkapan layar minimal 1, disarankan 4 (ukuran 1366x768 atau lebih besar)
- Logo Store 300x300 piksel
- Ubin persegi 300x300

Ambil tangkapan layar aplikasi dengan membuka jendela AkunTuntas lalu tekan
`Windows + Shift + S`, atau pakai tombol Print Screen.

**Catatan untuk sertifikasi** (penting)

Ini kolom yang menentukan lolos atau tidak. Isi dengan keterangan bahwa
aplikasi sudah dapat langsung dipakai tanpa kunci lisensi:

> Aplikasi ini tidak memerlukan akun demo. Saat pertama dibuka, aplikasi
> langsung menampilkan halaman masuk. Gunakan nama pengguna dan kata sandi
> berikut untuk masuk:
>
> Nama pengguna: admin
> Kata sandi: admin
>
> Seluruh fitur paket Enterprise terbuka untuk pengujian, termasuk dimensi
> biaya, konsolidasi grup, dan pajak lanjutan. Data disimpan di komputer
> setempat dan tidak dikirim ke mana pun.
>
> Aplikasi memerlukan sambungan internet hanya saat aktivasi lisensi
> berbayar. Pada paket uji coba ini, aktivasi dilewati sehingga aplikasi
> dapat diuji sepenuhnya tanpa internet.

### 6. Kirim dan tunggu

Setelah diunggah, Microsoft akan menguji aplikasi. Prosesnya **2 sampai 7
hari kerja**. Bila ada yang kurang, mereka mengirim keterangan lewat email
dan Anda dapat memperbaikinya lalu mengirim ulang tanpa biaya tambahan.

## Cara kerja mode uji coba

Paket MSIX memuat berkas `uji_coba.txt`. Keberadaan berkas itu membuat
aplikasi terbuka tanpa meminta kunci lisensi.

Tiga pengaman yang mencegahnya bocor ke versi yang dijual:

1. **Berkas penanda tidak ikut pada build installer.** Berkas itu hanya
   disalin saat `--bungkus` dijalankan, tidak pernah lewat `build.spec` atau
   `installer.iss`.

2. **Berlaku 60 hari** sejak aplikasi pertama dibuka. Setelah itu mode uji
   coba mati sendiri dan aplikasi meminta lisensi sungguhan. Peninjau
   Microsoft selalu menguji dalam hitungan hari.

3. **Tidak menyentuh server lisensi.** Mode uji coba tidak mengaktifkan
   apa pun di Supabase dan tidak menulis berkas lisensi, sehingga lisensi
   asli milik pembeli tidak terpengaruh.

## Hal yang perlu diperhatikan

**Perbarui berkas penanda bila mengirim versi baru.** Setiap kali mengirim
pembaruan ke Store, paket baru juga memuat mode uji coba dengan hitungan 60
hari yang baru. Ini memang disengaja, karena peninjau perlu dapat menguji
setiap versi.

**Jangan sertakan `uji_coba.txt` pada build yang dijual.** Bila berkas itu
ada di folder aplikasi versi installer, pembeli dapat memakai aplikasi tanpa
membeli lisensi.

**Versi MSIX wajib empat angka.** Tulis `1.0.0.0`, bukan `1.0.0`. Store
menolak format yang kurang dari empat angka.

**Paket belum ditandatangani.** Microsoft Store yang menandatanganinya saat
paket diterima. Untuk mencoba memasangnya sendiri di komputer sebelum
diunggah, paket perlu ditandatangani dengan sertifikat uji terlebih dahulu.

## Cara menguji paket sebelum diunggah

Paket MSIX yang belum ditandatangani tidak dapat dipasang. Untuk mencobanya
di komputer sendiri, buat sertifikat uji lalu pasang sebagai sertifikat
terpercaya.

```powershell
# Buat sertifikat uji
$cert = New-SelfSignedCertificate -Type Custom `
  -Subject "CN=Uji AkunTuntas" `
  -KeyUsage DigitalSignature `
  -FriendlyName "Uji MSIX AkunTuntas" `
  -CertStoreLocation "Cert:\CurrentUser\My" `
  -TextExtension @("2.5.29.37={text}1.3.6.1.5.5.7.3.3", `
                   "2.5.29.19={text}")

# Ekspor ke berkas
$sandi = ConvertTo-SecureString -String "uji" -Force -AsPlainText
Export-PfxCertificate -Cert $cert -FilePath uji.pfx -Password $sandi

# Pasang sebagai sertifikat terpercaya
Export-Certificate -Cert $cert -FilePath uji.cer
Import-Certificate -FilePath uji.cer `
  -CertStoreLocation Cert:\LocalMachine\Root
```

Lalu tandatangani paketnya:

```powershell
signtool sign /fd SHA256 /a /f uji.pfx /p uji `
  msix_output\AkunTuntas.msix
```

Setelah itu paket dapat dipasang dengan klik dua kali. **Hapus sertifikat
uji** dari penyimpanan setelah selesai mencoba:

```powershell
Get-ChildItem Cert:\LocalMachine\Root | Where-Object {
  $_.Subject -like "*Uji AkunTuntas*"
} | Remove-Item
```

## Berkas yang tidak boleh ikut terkirim

Berkas berikut sudah masuk `.gitignore`:

- `msix_output/` — hasil bungkus, besar dan dapat dibuat ulang
- `*.pfx`, `*.p12` — kunci sertifikat
- `sertifikat.json` — kata sandi sertifikat

## Bila paket ditolak

Penyebab yang paling sering:

| Pesan | Penyebab | Perbaikan |
|---|---|---|
| Identity mismatch | `nama_paket` atau `penerbit` tidak sama dengan Partner Center | Salin ulang dari Product identity |
| Version format invalid | Versi kurang dari empat angka | Tulis `1.0.0.0` |
| App does not launch | Aplikasi gagal dibuka di komputer penguji | Uji paketnya lebih dahulu dengan sertifikat uji |
| Missing screenshots | Gambar belum lengkap | Tambahkan minimal satu tangkapan layar |
| Testable: cannot sign in | Penguji tidak dapat masuk | Isi kolom Catatan untuk sertifikasi |
