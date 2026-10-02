# Cara Pakai di Streamlabs - Overlay Live AkunTuntas

Panduan menyiapkan overlay di **Streamlabs Desktop** (dahulu Streamlabs OBS)
untuk siaran TikTok.

---

## Ringkasan

```
┌─────────────────────────────────────────────────────┐
│                                                     │
│  Lapisan 1 : Overlay AkunTuntas   (paling bawah)    │
│  Lapisan 2 : Kamera Anda          (paling atas)     │
│                                                     │
└─────────────────────────────────────────────────────┘
```

Kamera diletakkan **di atas** overlay, tepat menutupi kotak kamera yang
sudah disediakan. Urutannya tidak boleh terbalik, karena kalau overlay
berada di atas kamera, wajah Anda akan tertutup.

---

## Langkah 1 - Siapkan kanvas 9:16

Streamlabs bawaannya memakai kanvas mendatar 1920x1080. Siaran TikTok
butuh tegak 9:16, jadi kanvasnya harus diubah lebih dahulu.

1. Buka Streamlabs Desktop
2. Klik **Settings** (roda gigi di kiri bawah)
3. Pilih **Video**
4. Ubah:

| Kolom | Nilai |
|---|---|
| Base (Canvas) Resolution | **1080x1920** |
| Output (Scaled) Resolution | **1080x1920** |
| FPS | 30 |

5. Klik **Done**

> Bila pilihan 1080x1920 tidak ada di daftar, ketik angkanya langsung.

---

## Langkah 2 - Buka overlay di peramban

Buka Command Prompt di folder proyek, lalu jalankan:

```
python tools/jalankan_overlay.py --chrome
```

Jendela Chrome terbuka berisi overlay, tanpa bilah alamat.

> **Penting:** jangan tutup jendela ini selama siaran. Jendela boleh
> ditutup hanya setelah siaran selesai.

---

## Langkah 3 - Tambahkan overlay ke Streamlabs

1. Di panel **Sources** (kiri bawah), klik **+**
2. Pilih **Window Capture**
3. Beri nama, misalnya `Overlay AkunTuntas`, klik **Add Source**
4. Pada daftar jendela, pilih jendela **AkunTuntas - Overlay Live**
5. Klik **Done**

### Atur ukurannya

Klik kanan sumber itu, pilih **Transform**, lalu **Fit to Screen**.

Bila masih belum pas, klik kanan lagi, pilih **Transform**, **Edit
Transform**, lalu isi:

| Kolom | Nilai |
|---|---|
| Position X | 0 |
| Position Y | 0 |
| Width | 1080 |
| Height | 1920 |

---

## Langkah 4 - Tambahkan kamera

1. Di panel **Sources**, klik **+** lagi
2. Pilih **Video Capture Device**
3. Beri nama `Kamera`, klik **Add Source**
4. Pilih kamera Anda dari daftar, klik **Done**

### Letakkan tepat di atas kotak kamera

Klik kanan sumber kamera, pilih **Transform**, lalu **Edit Transform**.
Isi angkanya persis seperti ini:

| Kolom | Nilai |
|---|---|
| Position X | **650** |
| Position Y | **44** |
| Width | **392** |
| Height | **217** |

Angka ini hasil pengukuran langsung dari overlay, jadi kamera akan pas
menutupi kotak yang disediakan.

**Ingin menutupi seluruh kotak termasuk bingkai berputarnya?**

| Kolom | Nilai |
|---|---|
| Position X | **646** |
| Position Y | **40** |
| Width | **400** |
| Height | **225** |

### Urutan lapisan

Pastikan **Kamera berada di atas Overlay** pada daftar Sources. Seret
namanya bila perlu. Yang paling atas adalah yang paling depan.

---

## Langkah 5 - Atur suara

1. Klik **+** di panel Sources, pilih **Audio Input Capture**
2. Pilih mikrofon Anda
3. Uji dengan bicara, lihat apakah bilah suara bergerak di panel **Mixer**

---

## Langkah 6 - Atur siaran TikTok

1. Buka **TikTok LIVE Studio** atau situs TikTok, mulai siaran
2. Salin **Server URL** dan **Stream Key** dari TikTok
3. Di Streamlabs: **Settings**, lalu **Stream**
4. Pilih **Custom Streaming Server**
5. Tempel Server URL dan Stream Key
6. Klik **Go Live**

> **Catatan:** TikTok hanya memberi kunci siaran kepada akun yang sudah
> memenuhi syarat siaran langsung. Bila belum bisa, gunakan TikTok LIVE
> Studio dan tangkap layarnya dengan Display Capture.

---

## Ringkasan angka

Simpan angka ini supaya tidak perlu mengukur lagi.

| Bagian | X | Y | Lebar | Tinggi |
|---|---|---|---|---|
| Overlay penuh | 0 | 0 | 1080 | 1920 |
| Kamera (dalam bingkai) | 650 | 44 | 392 | 217 |
| Kamera (seluruh kotak) | 646 | 40 | 400 | 225 |

---

## Susunan lapisan akhir

```
Sources (dari atas ke bawah)
├── Kamera              <- 650, 44, 392x292
├── Overlay AkunTuntas  <- 0, 0, 1080x1920
└── Audio Input         <- suara mikrofon
```

---

## Bila ada masalah

**Overlay tidak muncul di daftar Window Capture**
Pastikan jendela Chrome masih terbuka. Tutup Streamlabs, buka overlay
lebih dahulu, lalu buka Streamlabs lagi.

**Kamera terlihat terbalik**
Klik kanan sumber kamera, pilih **Transform**, lalu **Flip Horizontal**.

**Wajah terpotong di kotak kamera**
Pastikan lebar dan tinggi kamera 392x292, bukan angka lain. Bila kamera
Anda merek 16:9, rasio ini sudah pas.

**Overlay menutupi kamera**
Di daftar Sources, seret `Kamera` ke atas `Overlay AkunTuntas`.

**Gambar bergerak tersendat**
Kurangi beban: di **Settings**, **Video**, turunkan FPS ke 30. Bila masih
tersendat, matikan pratinjau di Streamlabs saat siaran.

**Streamlabs tidak mendukung 1080x1920**
Perbarui Streamlabs ke versi terbaru. Bila tetap tidak bisa, pakai OBS
Studio, caranya hampir sama.

---

## Kalau pakai OBS Studio

Langkahnya sama, hanya nama menunya berbeda:

| Streamlabs | OBS Studio |
|---|---|
| Sources | Sources |
| Window Capture | Window Capture |
| Video Capture Device | Video Capture Device |
| Settings > Video | Settings > Video |
| Edit Transform | Transform > Edit Transform |

Angka koordinatnya sama persis.

---

## Memeriksa ulang koordinat

Bila overlay diubah, ukur ulang koordinatnya dengan:

```
python tools/koordinat_kamera.py
```

Alat itu membaca posisi kotak kamera langsung dari overlay, jadi angkanya
selalu sesuai keadaan terbaru.
