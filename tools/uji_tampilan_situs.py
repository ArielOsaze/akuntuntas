"""
Uji tampilan situs: tombol terlihat, tabel perbandingan rapi, kontras aman.

Cara ini memeriksa berkas HTML dan CSS langsung, sehingga tidak bergantung
pada browser. Yang diperiksa:

  1. Setiap tombol punya teks yang benar benar tampil.
  2. Warna teks tombol kontras dengan latarnya.
  3. Tabel perbandingan memuat seluruh bagian yang seharusnya.
  4. Berkas CSS dimuat dengan versi yang benar, supaya perubahan tidak
     tertahan di simpanan sementara peramban.
  5. Tidak ada tanda pisah panjang maupun garis bawah sebagai spasi.

Cara pakai:
    python tools/uji_tampilan_situs.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
WEB = AKAR / "web"

# Warna yang dipakai situs.
WARNA = {
    "--biru": "#1B4F8A",
    "--biru-tua": "#143C6B",
    "--navy": "#0F2942",
    "--teks": "#1A2733",
    "--teks-abu": "#556577",
    "--putih": "#FFFFFF",
}


class Pemeriksa:
    def __init__(self):
        self.lulus = 0
        self.gagal = 0
        self.temuan: list[str] = []

    def cek(self, nama: str, syarat: bool, catatan: str = ""):
        if syarat:
            self.lulus += 1
            print(f"  [BENAR] {nama}")
        else:
            self.gagal += 1
            self.temuan.append(nama)
            print(f"  [SALAH] {nama}")
            if catatan:
                print(f"          {catatan}")

    def ringkas(self) -> int:
        print()
        print("=" * 76)
        if self.gagal:
            print(f"  HASIL: {self.lulus} BENAR, {self.gagal} SALAH")
            print()
            for t in self.temuan:
                print(f"    - {t}")
        else:
            print(f"  HASIL: {self.lulus} BENAR, 0 SALAH")
        print("=" * 76)
        return 1 if self.gagal else 0


def hitung_kontras(warna1: str, warna2: str) -> float:
    """Rasio kontras dua warna menurut rumus WCAG."""
    def terang(w: str) -> float:
        w = w.lstrip("#")
        r, g, b = (int(w[i:i + 2], 16) / 255 for i in (0, 2, 4))
        def lin(c):
            return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
        return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)

    a, b = terang(warna1), terang(warna2)
    muda, tua = max(a, b), min(a, b)
    return (muda + 0.05) / (tua + 0.05)


def main() -> int:
    p = Pemeriksa()
    print("=" * 76)
    print("  UJI TAMPILAN SITUS: TOMBOL, TABEL PERBANDINGAN, KONTRAS")
    print("=" * 76)
    print()

    html = (WEB / "index.html").read_text(encoding="utf-8")
    css = (WEB / "styles.css").read_text(encoding="utf-8")

    # ------------------------------------------------------------------
    print("[1. Setiap tombol punya teks yang tampil]")
    # Tombol pada situs berupa <a class="tombol"> atau <button class="tombol">.
    tombol = re.findall(
        r'<(a|button)[^>]*class="[^"]*\btombol\b[^"]*"[^>]*>(.*?)</\1>',
        html, re.DOTALL)

    kosong = []
    for tag, isi in tombol:
        # Buang seluruh tanda kurung sudut, lalu rapikan spasinya.
        teks = re.sub(r"<[^>]+>", " ", isi)
        teks = " ".join(teks.split())
        if not teks:
            kosong.append(isi.strip()[:60])

    p.cek(f"seluruh {len(tombol)} tombol di beranda punya teks",
          not kosong,
          f"tombol tanpa teks: {kosong[:3]}")

    # Tombol di halaman lain juga diperiksa.
    for berkas in sorted(WEB.glob("*.html")):
        if berkas.name == "index.html":
            continue
        isi_h = berkas.read_text(encoding="utf-8")
        t2 = re.findall(
            r'<(a|button)[^>]*class="[^"]*\btombol\b[^"]*"[^>]*>(.*?)</\1>',
            isi_h, re.DOTALL)
        kosong2 = []
        for tag, isi in t2:
            teks = " ".join(re.sub(r"<[^>]+>", " ", isi).split())
            if not teks:
                kosong2.append(isi.strip()[:50])
        p.cek(f"tombol di {berkas.name} punya teks", not kosong2,
              f"tanpa teks: {kosong2[:2]}")
    print()

    # ------------------------------------------------------------------
    print("[2. Warna teks tombol kontras dengan latarnya]")
    # Tombol utama: teks putih di atas biru.
    rasio = hitung_kontras(WARNA["--putih"], WARNA["--biru"])
    p.cek(f"teks putih di atas biru (rasio {rasio:.2f}:1) memenuhi AA",
          rasio >= 4.5, f"rasio {rasio:.2f}, minimal 4.5")

    rasio2 = hitung_kontras(WARNA["--biru"], WARNA["--putih"])
    p.cek(f"teks biru di atas putih (rasio {rasio2:.2f}:1) memenuhi AA",
          rasio2 >= 4.5, f"rasio {rasio2:.2f}, minimal 4.5")

    # Tombol garis: teks biru di atas putih.
    p.cek("tombol garis memakai teks biru di atas latar terang",
          ".tombol-garis" in css and "color: var(--biru)" in css)
    print()

    # ------------------------------------------------------------------
    print("[3. Tabel perbandingan fitur lengkap]")
    # Seluruh bagian yang seharusnya ada.
    for bagian in ("Jumlah pemakaian", "Pembukuan dasar", "Perpajakan",
                   "Laporan keuangan", "Akuntansi lanjutan",
                   "Tata kelola dan pengawasan", "Dukungan"):
        p.cek(f"bagian '{bagian}' ada di tabel", bagian in html)

    # Harga kedua paket tampil di kepala tabel.
    p.cek("harga paket Standar tampil di tabel", "Rp3.499.000" in html)
    p.cek("harga paket Enterprise tampil di tabel", "Rp5.499.000" in html)

    # Pita penanda paket unggulan.
    p.cek("penanda paket paling lengkap ada", "paket-pita" in html)
    p.cek("CSS pita paket ada", ".paket-pita" in css)

    # Keterangan lambang centang dan silang.
    p.cek("keterangan lambang tersedia", "banding-legenda" in html)
    p.cek("lambang centang dan silang ada di tabel",
          "&#10003;" in html and "&#10005;" in html)

    # Baris pembeda paket.
    jumlah_beda = html.count('class="baris-beda"')
    p.cek(f"baris pembeda paket ditandai ({jumlah_beda} baris)",
          jumlah_beda >= 8, f"jumlah: {jumlah_beda}")
    p.cek("CSS baris pembeda ada", "baris-beda" in css)

    # Kepala tabel melekat saat digulir.
    p.cek("kepala tabel melekat saat digulir",
          "position: sticky" in css and "banding-tabel thead th" in css)
    print()

    # ------------------------------------------------------------------
    print("[4. Versi berkas CSS memaksa peramban memuat ulang]")
    for berkas in sorted(WEB.glob("*.html")):
        isi_h = berkas.read_text(encoding="utf-8")
        # Sebagian halaman berdiri sendiri dan memuat gayanya sendiri di
        # dalam berkas, jadi tidak memakai styles.css.
        if "styles.css" not in isi_h:
            p.cek(f"{berkas.name} memuat gaya sendiri", "<style>" in isi_h,
                  "tidak memuat styles.css maupun gaya sendiri")
            continue
        versi = re.findall(r'styles\.css\?v=(\d+)', isi_h)
        p.cek(f"{berkas.name} memuat CSS dengan versi",
              bool(versi) and int(versi[0]) >= 3,
              f"versi: {versi}")
    print()

    # ------------------------------------------------------------------
    print("[5. Teks bersih dari jejak gaya penulisan mesin]")
    semua_html = "\n".join(f.read_text(encoding="utf-8")
                           for f in WEB.glob("*.html"))
    # Tanda pisah panjang.
    pisah = re.findall(r"[\u2014\u2013]", semua_html)
    p.cek("tidak ada tanda pisah panjang pada teks tampilan",
          not pisah, f"jumlah: {len(pisah)}")

    # Garis bawah dipakai sebagai pengganti spasi. Yang diperiksa hanya
    # teks yang tampil, jadi seluruh blok skrip dan gaya dibuang lebih
    # dulu: di dalamnya garis bawah memang dipakai untuk nama variabel.
    teks_tampil = re.sub(r"<script[^>]*>.*?</script>", " ",
                         semua_html, flags=re.DOTALL | re.IGNORECASE)
    teks_tampil = re.sub(r"<style[^>]*>.*?</style>", " ",
                         teks_tampil, flags=re.DOTALL | re.IGNORECASE)
    garis_bawah = re.findall(r">[^<>]*[A-Za-z]_[A-Za-z][^<>]*<", teks_tampil)
    p.cek("tidak ada garis bawah sebagai pengganti spasi pada teks tampilan",
          not garis_bawah, f"contoh: {[g[:50] for g in garis_bawah[:3]]}")
    print()

    # ------------------------------------------------------------------
    print("[6. Tidak ada aturan CSS yang saling menimpa warna teks]")
    # Aturan dengan pemilih yang sama dan muncul dua kali akan saling
    # menimpa. Bila aturan kedua memberi warna teks yang sama dengan
    # latarnya, teksnya menjadi tidak terlihat dan tombolnya tampak kosong.
    # Kejadian ini pernah terjadi pada .tombol-garis.
    aturan: dict = {}
    for m in re.finditer(r"([^{}]+)\{([^}]*)\}", css):
        selektor = " ".join(m.group(1).split())
        # Buang komentar yang mungkin ikut terbaca.
        selektor = re.sub(r"/\*.*?\*/", "", selektor).strip()
        if not selektor or selektor.startswith("@"):
            continue
        isi_aturan = m.group(2)
        warna = re.search(r"(?:^|;)\s*color:\s*([^;]+)", isi_aturan)
        latar = re.search(r"(?:^|;)\s*background(?:-color)?:\s*([^;]+)",
                          isi_aturan)
        if selektor not in aturan:
            aturan[selektor] = []
        aturan[selektor].append({
            "warna": warna.group(1).strip() if warna else None,
            "latar": latar.group(1).strip() if latar else None,
            "baris": css[:m.start()].count("\n") + 1,
        })

    bertabrakan = []
    for selektor, daftar in aturan.items():
        if len(daftar) < 2:
            continue
        # Hanya periksa pemilih sederhana tanpa induk, karena pemilih
        # berinduk memang sengaja dibatasi pada bagian tertentu.
        if " " in selektor or "," in selektor:
            continue
        warna_akhir = None
        latar_akhir = None
        for d in daftar:
            if d["warna"]:
                warna_akhir = d["warna"]
            if d["latar"]:
                latar_akhir = d["latar"]
        # Bila warna teks dan latar sama, teksnya tidak terlihat.
        if warna_akhir and latar_akhir and warna_akhir == latar_akhir:
            bertabrakan.append(
                f"{selektor}: teks dan latar sama ({warna_akhir})")

    p.cek("tidak ada aturan yang membuat teks dan latar sewarna",
          not bertabrakan, f"temuan: {bertabrakan[:3]}")

    # Periksa juga: pemilih tanpa induk yang muncul dua kali dengan warna
    # berbeda, karena itulah bentuk kesalahan yang pernah terjadi.
    ganda = {s: len(d) for s, d in aturan.items()
             if len(d) > 1 and " " not in s and "," not in s
             and not s.startswith("@")}
    mencurigakan = []
    for selektor, jumlah in ganda.items():
        warna = {d["warna"] for d in aturan[selektor] if d["warna"]}
        if len(warna) > 1:
            mencurigakan.append(f"{selektor}: warna teks berbeda ({warna})")
    p.cek("tidak ada pemilih yang didefinisikan ulang dengan warna berbeda",
          not mencurigakan, f"temuan: {mencurigakan[:3]}")
    print()

    # ------------------------------------------------------------------
    print("[7. Tidak ada tautan surel yang tidak merespons]")
    # Tautan surel tidak berfungsi pada komputer yang tidak memiliki
    # aplikasi surel. Pengunjung yang menekannya tidak melihat apa pun
    # terjadi, sehingga tombolnya terasa mati. Seluruh tautan kontak
    # diganti WhatsApp atau formulir pada situs.
    surel = []
    for berkas in sorted(WEB.glob("*.html")):
        isi_h = berkas.read_text(encoding="utf-8")
        # Hanya periksa tautan yang benar benar diklik pengunjung.
        if 'href="mailto:' in isi_h:
            jumlah = isi_h.count('href="mailto:')
            surel.append(f"{berkas.name}: {jumlah}")
    p.cek("tidak ada tautan surel yang tidak merespons",
          not surel, f"temuan: {surel}")

    # WhatsApp harus tersedia sebagai gantinya.
    ada_wa = sum(1 for f in WEB.glob("*.html")
                 if "wa.me/" in f.read_text(encoding="utf-8"))
    p.cek(f"tautan WhatsApp tersedia di {ada_wa} halaman", ada_wa >= 5)
    print()

    # ------------------------------------------------------------------
    print("[8. Tabel dapat digulir pada layar sempit]")
    p.cek("tabel dibungkus wadah yang dapat digulir",
          "banding-tabel-wadah" in html and "overflow-x: auto" in css)
    p.cek("tabel punya lebar minimum supaya kolom tidak terhimpit",
          "min-width" in css)
    print()

    return p.ringkas()


if __name__ == "__main__":
    sys.exit(main())
