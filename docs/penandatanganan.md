# Penandatanganan digital AkunTuntas

## Kenapa peringatan itu muncul

Windows memeriksa asal setiap berkas yang dijalankan. Selama berkas belum
ditandatangani secara digital, Windows tidak dapat memastikan siapa yang
membuatnya, lalu menampilkan peringatan bahwa penerbitnya tidak dikenal.

Peringatan itu **tidak dapat dihilangkan lewat setelan di dalam installer**.
Windows menolak menerima keterangan penerbit dari berkas yang tidak
ditandatangani, karena keterangan seperti itu dapat ditulis siapa saja.
Satu-satunya jalan adalah menandatangani berkas memakai sertifikat yang
dikeluarkan oleh badan sertifikasi yang diakui Windows.

## Dua peringatan yang berbeda

Penting untuk dibedakan, karena penanganannya tidak sama.

**1. Penerbit tidak dikenal / Unknown Publisher**

Muncul di jendela "User Account Control" saat installer dijalankan, dan pada
tab Digital Signatures di properti berkas. Penyebabnya berkas belum
ditandatangani. **Hilang sepenuhnya setelah ditandatangani.**

**2. Peringatan SmartScreen / "Windows melindungi PC Anda"**

Muncul saat berkas diunduh dari internet. Penyebabnya berkas belum memiliki
reputasi di Microsoft. Sertifikat yang baru dibeli **tetap** menampilkan
peringatan ini pada unduhan pertama, karena reputasi terbentuk dari jumlah
unduhan dan waktu, bukan dari sertifikat. Yang berubah: nama penerbit
tertulis jelas di peringatan, sehingga pembeli dapat memastikan berkas itu
memang dari Xinet Group.

Reputasi biasanya terbentuk setelah beberapa ratus unduhan yang tidak
dilaporkan sebagai berbahaya. Sertifikat jenis EV dahulu melewati tahap ini
seketika, tetapi aturan itu sudah tidak berlaku lagi sejak 2024.

## Pilihan sertifikat

| Pilihan | Biaya | Penerbit yang tampil | SmartScreen |
|---|---|---|---|
| Azure Artifact Signing | sekitar $9,99 per bulan | Xinet Group | Peringatan berkurang seiring reputasi |
| Sertifikat OV dari CA | $150 sampai $300 per tahun | Xinet Group | Peringatan berkurang seiring reputasi |
| Sertifikat EV dari CA | $300 sampai $600 per tahun | Xinet Group | Peringatan berkurang seiring reputasi |
| Belum ditandatangani | Rp0 | tidak ada, tertulis "tidak dikenal" | Peringatan penuh |

Keterangan penting soal Azure Artifact Signing: layanan itu hanya menerima
badan usaha yang terdaftar di Amerika Serikat, Kanada, Uni Eropa, atau
Inggris. Badan usaha Indonesia **belum termasuk**, sehingga untuk Xinet Group
pilihannya adalah sertifikat dari CA yang melayani seluruh dunia.

### CA yang melayani Indonesia

- **Sectigo** lewat reseller, sekitar $150 sampai $250 per tahun
- **DigiCert**, sekitar $300 sampai $500 per tahun
- **GlobalSign**, sekitar $250 sampai $400 per tahun
- **SSL.com**, sekitar $150 sampai $300 per tahun

Untuk badan usaha, CA umumnya meminta dokumen berikut:

1. Akta pendirian atau surat keterangan usaha
2. Nomor Pokok Wajib Pajak badan usaha
3. Bukti alamat usaha
4. Surat kuasa bila pendaftar bukan pemilik
5. Verifikasi lewat telepon atau surel resmi badan usaha

Proses penerbitan biasanya tiga sampai sepuluh hari kerja.

## Cara menandatangani setelah sertifikat diterima

Sertifikat akan diterima dalam bentuk berkas `.pfx` beserta kata sandinya,
atau tersimpan di token USB.

**Bila berbentuk berkas .pfx:**

Buat berkas `sertifikat.json` di akar proyek. Berkas ini sudah masuk daftar
`.gitignore`, jadi kata sandinya tidak akan ikut terkirim ke repositori.

```json
{
  "berkas": "C:/kunci/xinet.pfx",
  "sandi": "kata-sandi-dari-CA",
  "cap_waktu": "http://timestamp.digicert.com"
}
```

Lalu jalankan:

```bash
python tools/tandatangani.py
```

**Bila berbentuk token USB:**

Pasang token lebih dahulu. Cari sidik jari sertifikatnya:

```powershell
Get-ChildItem Cert:\CurrentUser\My | Where-Object {
    $_.EnhancedKeyUsageList -match 'Code Signing'
} | Select-Object Subject, Thumbprint
```

Isi `sertifikat.json` dengan sidik jari tersebut, dan kosongkan `berkas`:

```json
{
  "berkas": "",
  "sidik_jari": "A1B2C3D4E5F6...",
  "cap_waktu": "http://timestamp.digicert.com"
}
```

## Urutan penandatanganan yang benar

Ini penting: **penandatanganan harus dilakukan setelah build terakhir**.

1. Build aplikasi: `python -m PyInstaller build.spec --noconfirm`
2. Build installer: `iscc installer.iss`
3. Tandatangani installer: `python tools/tandatangani.py`
4. Periksa hasilnya: `python tools/tandatangani.py --periksa`
5. Unggah ke GitHub Releases

Bila installer dibangun ulang setelah ditandatangani, tanda tangannya hilang
dan harus dipasang kembali. Sebabnya, menulis ulang berkas akan mengubah
isinya sehingga tanda tangan lama menjadi tidak sah.

## Cap waktu

Skrip penandatanganan memakai cap waktu dari DigiCert secara bawaan. Cap
waktu membuat tanda tangan tetap sah walaupun sertifikatnya sudah
kedaluwarsa di kemudian hari. Tanpa cap waktu, aplikasi yang ditandatangani
hari ini akan ditolak Windows setelah sertifikat habis masa berlakunya.

## Keterangan penerbit di dalam aplikasi

Selain sertifikat, keterangan penerbit juga ditulis di dalam berkas installer
lewat `installer.iss`:

```
AppPublisher=Xinet Group
VersionInfoCompany=Xinet Group
VersionInfoCopyright=Hak cipta 2026 Xinet Group
```

Keterangan ini muncul di Control Panel, di properti berkas, dan di jendela
installer. Ini bukan pengganti sertifikat, tetapi membuat asal aplikasi jelas
dan memperkuat kepercayaan pembeli.

## Yang perlu disiapkan sekarang

Sementara sertifikat belum ada, yang dapat dilakukan:

1. Keterangan penerbit di installer sudah diubah menjadi Xinet Group
2. Skrip penandatanganan sudah siap dipakai
3. Halaman unduhan sebaiknya memuat keterangan bahwa aplikasi belum
   ditandatangani, disertai nilai sidik jari berkas (checksum) agar pembeli
   dapat memastikan berkas yang diunduh tidak berubah

Setelah sertifikat diterima, penandatanganan hanya perlu satu perintah.
