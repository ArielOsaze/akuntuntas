"""
Jalankan seluruh rangkaian pengujian AkunTuntas.

Cara pakai:
    python tests/jalankan_semua_tes.py

Keluaran: ringkasan setiap rangkaian beserta total keseluruhan.
Berkas hasil lengkap disimpan di tests/hasil_<nama>.txt
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent

RANGKAIAN = [
    ("backend", "test_semua_fitur.py",
     "Mesin pajak, akuntansi, persediaan, penjualan, pembelian, tata kelola"),
    ("ui", "test_ui.py",
     "Pemuatan seluruh halaman antarmuka (mode pemula & ahli)"),
    ("ui_mendalam", "test_ui_mendalam.py",
     "Dialog, formulir, dan penyimpanan data lewat antarmuka"),
    ("pajak", "test_kepatuhan_pajak.py",
     "Kesesuaian angka pajak dengan salinan regulasi resmi"),
    ("pajak_baru", "test_pajak_baru.py",
     "PPh 15, bea meterai, pajak daerah, dan kurs"),
    ("pajak_lanjut", "test_pajak_lanjut.py",
     "Faktur pajak, uang muka, jurnal balik, dan keseimbangan neraca"),
    ("halaman_pajak_lanjutan", "test_halaman_pajak_lanjutan.py",
     "Halaman Pajak Lanjutan: seluruh tab dan dialognya"),
    ("mode_sekali", "test_mode_sekali.py",
     "Pilihan mode Pemula/Ahli hanya muncul sekali"),
    ("sidebar_kelompok", "test_sidebar_kelompok.py",
     "Sub-kategori sidebar: pengelompokan dan buka-tutup"),
    ("bentuk_usaha", "test_bentuk_usaha.py",
     "Antarmuka menyesuaikan bentuk badan usaha"),
    ("subkategori", "test_subkategori.py",
     "Sub-kategori sidebar: pengelompokan dan buka-tutup"),
    ("sidebar_cari", "test_sidebar_cari.py",
     "Sidebar tetap lengkap setelah pencarian menu; laporan masalah"),
    ("log_terpisah", "test_log_terpisah.py",
     "Jejak audit terpisah dari log keamanan"),
    ("login_fitur", "test_login_fitur.py",
     "Halaman login: lihat password, ingat pengguna, caps lock"),
    ("migrasi_lama", "test_migrasi_lama.py",
     "Basis data versi lama dapat dibuka dan dimigrasi"),
    ("exe_modul", "test_exe_modul.py",
     "EXE terpasang memuat seluruh modul skema"),
    ("backup_restore", "test_backup_restore.py",
     "Cadangan dan pemulihan data tanpa perlu pasang ulang"),
    ("reset", "test_reset.py",
     "Reset data usaha: transaksi bersih, profil & bagan akun tetap"),
    ("lisensi", "test_lisensi.py",
     "Lisensi: aktivasi, pemalsuan ditolak, pembatasan paket"),
    ("kontrak", "test_kontrak.py",
     "Kontrak, MoU, barter, termin, pajak, dan pembacaan dokumen"),
]

# pemeriksaan tambahan (dijalankan dari folder tools)
PEMERIKSAAN = [
    ("verifikasi_ter.py", "Tabel TER PPh 21 vs PMK 168/2023"),
    ("cari_teks_ikon.py", "Tidak ada nama ikon tampil sebagai teks"),
    ("uji_semua_halaman.py", "Seluruh halaman & tab termuat tanpa error"),
    ("uji_klik_tombol.py", "Seluruh tombol aman diklik"),
    ("uji_dialog_simpan.py", "Seluruh dialog menyimpan data dengan benar"),
    ("periksa_tumpang_tindih.py", "Tidak ada widget bertumpuk"),
    ("periksa_tata_letak.py", "Seluruh teks tampil utuh"),
    ("periksa_himpit.py", "Tidak ada isi halaman yang terhimpit"),
    ("periksa_kontras.py", "Seluruh teks memenuhi kontras WCAG AA"),
    ("periksa_kontras_dialog.py", "Kontras jendela login & dialog"),
    ("periksa_teks_ikon.py", "Nama ikon tidak tampil sebagai teks"),
    ("periksa_sidebar.py", "Seluruh label sidebar terbaca utuh"),
    ("periksa_navbar.py", "Seluruh nama menu sidebar tampil utuh"),
    ("periksa_istilah.py", "Tidak ada nilai teknis yang tampil mentah"),
    ("periksa_latar.py", "Tidak ada aturan gaya yang menular"),
    ("periksa_ampersand.py", "Tidak ada '&' tunggal yang mengubah teks"),
    ("periksa_garis_bawah.py", "Tidak ada teks teknis bergaris bawah"),
    ("periksa_garis_bawah_dialog.py", "Dialog bebas garis bawah"),
    ("periksa_tombol_aman.py", "Tombol pembuka aplikasi lain tidak diklik saat uji"),
    ("periksa_tanda_pisah.py", "Tidak ada tanda pisah panjang pada teks tampilan"),
    ("uji_pasang_ulang.py", "Pemasangan ulang mengganti versi lama, data tetap utuh"),
    ("periksa_kerapian_tabel.py", "Seluruh tabel rapi"),
    ("periksa_integrasi.py", "Seluruh modul terintegrasi"),
    ("periksa_jejak_ai.py", "Teks bebas jejak gaya AI"),
    ("audit_tampilan.py", "Seluruh teks tampil utuh dan tidak keluar batas"),
    ("verifikasi_visual.py", "Kotak isian menampilkan isinya, tidak bertumpuk"),
    ("audit_garis_bawah.py", "Audit menyeluruh garis bawah"),
    ("audit_tinggi_label.py", "Tinggi label cukup untuk seluruh teksnya"),
    ("audit_rich_text.py", "Teks berformat tidak terpotong"),
    ("audit_grafik.py", "Elemen grafik tidak saling menimpa"),
    ("audit_kolom_tabel.py", "Lebar kolom tabel cukup untuk judulnya"),
    ("audit_elipsis_sel.py", "Tidak ada teks sel tabel yang terpotong"),
    ("audit_bingkai_gelap.py", "Bingkai popup terang walau Windows bermode gelap"),
    ("audit_daftar_pilihan.py", "Tidak ada baris pilihan tertutup warna tua"),
    ("audit_tinggi_baris_pilihan.py", "Baris daftar pilihan cukup tinggi untuk hurufnya"),
    ("buruh_bug_ui.py", "Seluruh halaman, tab, dan dialog terbentuk tanpa error"),
    ("buruh_bug_pajak.py", "Mesin pajak tahan nilai tepi dan ekstrem"),
    ("buruh_bug_data.py", "Integritas data: jurnal, stok, saldo, rujukan"),
    ("buruh_bug_akuntansi.py", "Perhitungan akuntansi, HPP, FIFO, dan rata-rata"),
    ("buruh_bug_kesalahan.py", "Tidak ada kegagalan penyimpanan yang ditelan"),
]


def baris_hasil(teks: str) -> str:
    """
    Ambil baris ringkasan hasil dari keluaran sebuah rangkaian uji.

    Sebagian rangkaian menuliskan ringkasannya dengan kata "HASIL",
    sebagian lagi memakai "RINGKASAN". Keduanya harus dikenali, karena
    kalau tidak, rangkaian yang sebenarnya lulus akan dilaporkan sebagai
    tidak menghasilkan ringkasan.
    """
    for baris in reversed(teks.splitlines()):
        naik = baris.upper()
        if "HASIL" in naik or "RINGKASAN" in naik:
            return baris.strip()
    return "(ringkasan tidak ditemukan)"


def main() -> int:
    print("=" * 74)
    print("AKUNTANSIID — RANGKAIAN PENGUJIAN LENGKAP")
    print("=" * 74)

    ringkasan = []
    semua_lulus = True

    for nama, berkas, keterangan in RANGKAIAN:
        print(f"\n[{nama}] {keterangan}")
        print("-" * 74)
        hasil = subprocess.run(
            [sys.executable, str(AKAR / "tests" / berkas)],
            cwd=str(AKAR), capture_output=True, text=True, timeout=1800)
        keluaran = hasil.stdout + hasil.stderr

        berkas_hasil = AKAR / "tests" / f"hasil_{nama}.txt"
        berkas_hasil.write_text(keluaran, encoding="utf-8")

        ringkas = baris_hasil(keluaran)
        print(f"  {ringkas}")
        print(f"  berkas hasil: {berkas_hasil.name}")
        ringkasan.append((nama, ringkas, hasil.returncode == 0))
        if hasil.returncode != 0:
            semua_lulus = False

    print("\n" + "=" * 74)
    print("RINGKASAN")
    print("=" * 74)
    for nama, ringkas, lulus in ringkasan:
        tanda = "LULUS" if lulus else "GAGAL"
        print(f"  [{tanda:5s}] {nama:14s} {ringkas}")

    # verifikasi tabel TER
    print("\n[verifikasi] Tabel TER vs PMK 168/2023")
    print("-" * 74)
    hasil = subprocess.run([sys.executable, str(AKAR / "tools" / "verifikasi_ter.py")],
                           cwd=str(AKAR), capture_output=True, text=True, timeout=600)
    keluaran = hasil.stdout + hasil.stderr
    for baris in keluaran.splitlines():
        if "HASIL" in baris.upper() or "COCOK" in baris.upper():
            print(f"  {baris.strip()}")
    if hasil.returncode != 0:
        semua_lulus = False

    # pemeriksaan antarmuka tambahan
    print("\n[antarmuka] Pemeriksaan tambahan")
    print("-" * 74)
    for berkas, keterangan in PEMERIKSAAN:
        if berkas == "verifikasi_ter.py":
            continue
        path = AKAR / "tools" / berkas
        if not path.exists():
            print(f"  [LEWAT] {keterangan} (berkas tidak ada)")
            continue
        hasil = subprocess.run(
            [sys.executable, str(path)], cwd=str(AKAR),
            capture_output=True, text=True, timeout=1800)
        keluaran = hasil.stdout + hasil.stderr
        ringkas = baris_hasil(keluaran)
        tanda = "LULUS" if hasil.returncode == 0 else "GAGAL"
        print(f"  [{tanda:5s}] {keterangan}")
        print(f"           {ringkas}")
        if hasil.returncode != 0:
            semua_lulus = False
            for b in keluaran.splitlines():
                if "GAGAL" in b or "TUMPANG" in b or "terpotong" in b:
                    print(f"           {b.strip()[:110]}")

    print("\n" + "=" * 74)
    print("SEMUA RANGKAIAN LULUS" if semua_lulus else "ADA RANGKAIAN YANG GAGAL")
    print("=" * 74)
    return 0 if semua_lulus else 1


if __name__ == "__main__":
    sys.exit(main())
