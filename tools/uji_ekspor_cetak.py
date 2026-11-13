"""
Uji ekspor Excel dan cetak A4.

Yang diperiksa bukan hanya apakah berkasnya terbentuk, tetapi apakah
isinya benar: angka tersimpan sebagai angka, lembar terpisah per tabel,
ukuran kertas benar benar A4, dan hasil cetak memuat seluruh baris.

Cara pakai:
    python tools/uji_ekspor_cetak.py
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "src"))

FOLDER = Path(tempfile.mkdtemp(prefix="akuntuntas_ekspor_"))
os.environ["LOCALAPPDATA"] = str(FOLDER)
# Qt tidak menampilkan jendela pada pengujian ini.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication.instance() or QApplication([])

from akuntansi_id.ui import ekspor_cetak as EC  # noqa: E402


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

    def cek_sama(self, nama: str, satu, lain, catatan: str = ""):
        self.cek(nama, satu == lain,
                 catatan or f"seharusnya {lain!r}, ternyata {satu!r}")

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


def main() -> int:
    p = Pemeriksa()
    print("=" * 76)
    print("  UJI EKSPOR EXCEL DAN CETAK A4")
    print("=" * 76)
    print()

    # Data uji menyerupai laporan sungguhan.
    data = [
        ("Neraca", [
            ["Akun", "Kode", "Jumlah"],
            ["Kas", "1001", 750_000_000],
            ["Piutang Usaha", "1101", 250_000_000],
            ["Persediaan", "1104", 180_000_000],
            ["Total Harta", "", 1_180_000_000],
        ]),
        ("Laba Rugi", [
            ["Keterangan", "Jumlah"],
            ["Pendapatan", 375_000_000],
            ["Harga Pokok Penjualan", 63_600_000],
            ["Laba Kotor", 311_400_000],
        ]),
    ]

    # ==================================================================
    print("[1. Ekspor Excel: berkas dan isinya]")
    berkas = FOLDER / "laporan.xlsx"
    try:
        EC.ekspor_excel("Laporan Keuangan", data, str(berkas),
                        subjudul="Tahun 2026",
                        nama_perusahaan="PT Sinar Nusantara")
        p.cek("berkas Excel terbentuk", berkas.exists(),
              f"ukuran: {berkas.stat().st_size if berkas.exists() else 0} byte")
    except Exception as e:
        p.cek("ekspor Excel berjalan tanpa galat", False,
              f"{type(e).__name__}: {e}")
        berkas = None

    if berkas and berkas.exists():
        import openpyxl
        wb = openpyxl.load_workbook(str(berkas))

        p.cek_sama("satu lembar per tabel", len(wb.sheetnames), 2,
                   f"lembar: {wb.sheetnames}")
        p.cek("nama lembar sama dengan nama tabel",
              wb.sheetnames[0] == "Neraca", f"lembar: {wb.sheetnames}")

        ws = wb["Neraca"]
        p.cek_sama("judul lembar ada di kop", ws.cell(row=1, column=1).value,
                   "Neraca")
        # Kop memuat perusahaan di baris 2 dan subjudul di baris 3.
        kop = str(ws.cell(row=2, column=1).value or "")
        p.cek("kop memuat nama perusahaan", "Sinar Nusantara" in kop,
              f"kop: {kop}")
        info = str(ws.cell(row=3, column=1).value or "")
        p.cek("kop memuat subjudul", "2026" in info, f"info: {info}")

        # Baris judul tabel di baris 5, data mulai baris 6.
        p.cek_sama("baris judul tabel benar",
                   ws.cell(row=5, column=1).value, "Akun")
        p.cek_sama("data pertama benar",
                   ws.cell(row=6, column=1).value, "Kas")

        # Angka harus tersimpan sebagai angka, bukan teks.
        sel_angka = ws.cell(row=6, column=3)
        p.cek("angka tersimpan sebagai angka, bukan teks",
              isinstance(sel_angka.value, (int, float)),
              f"tipe: {type(sel_angka.value).__name__}, "
              f"nilai: {sel_angka.value!r}")
        p.cek_sama("nilai angka benar", sel_angka.value, 750_000_000)
        p.cek("angka memakai format ribuan",
              '#,##0' in sel_angka.number_format,
              f"format: {sel_angka.number_format}")

        # Teks tetap teks.
        sel_teks = ws.cell(row=6, column=1)
        p.cek("teks tersimpan sebagai teks",
              isinstance(sel_teks.value, str))

        # Baris judul dibekukan.
        p.cek("baris judul dibekukan", ws.freeze_panes is not None,
              f"freeze_panes: {ws.freeze_panes}")

        # Halaman Excel sudah disiapkan untuk kertas A4.
        p.cek("lembar Excel memakai kertas A4",
              str(ws.page_setup.paperSize) == "9",
              f"paperSize: {ws.page_setup.paperSize}")
        p.cek("lebar Excel dimuat ke satu halaman",
              ws.page_setup.fitToWidth == 1
              and ws.sheet_properties.pageSetUpPr is not None
              and ws.sheet_properties.pageSetUpPr.fitToPage,
              f"fitToWidth: {ws.page_setup.fitToWidth}")
        p.cek("judul kolom diulang saat dicetak",
              str(ws.print_title_rows).replace("$", "") == "5:5",
              f"print_title_rows: {ws.print_title_rows}")

        # Lebar kolom sudah diatur.
        lebar = ws.column_dimensions["A"].width
        p.cek("lebar kolom sudah diatur", lebar and lebar >= 12,
              f"lebar kolom A: {lebar}")

        # Jumlah baris data benar.
        terisi = [r for r in range(6, 12) if ws.cell(row=r, column=1).value]
        p.cek_sama("seluruh baris data tertulis", len(terisi), 4,
                   f"baris terisi: {terisi}")

    # ==================================================================
    print()
    print("[2. Nama lembar yang bermasalah dibersihkan]")
    sulit = [
        ("Neraca 2026/2027", "karakter garis miring"),
        ("Laba: Rugi", "karakter titik dua"),
        ("Data [penting]", "karakter kurung siku"),
        ("A" * 50, "nama terlalu panjang"),
        ("", "nama kosong"),
        ("'Kutip'", "tanda kutip"),
    ]
    for nama, alasan in sulit:
        bersih = EC.nama_lembar_aman(nama)
        p.cek(f"nama lembar aman ({alasan})",
              len(bersih) <= 31
              and not any(c in bersih for c in ':\\/?*[]')
              and bool(bersih),
              f"{nama!r} -> {bersih!r}")

    # Nama yang sama dua kali tidak boleh bertabrakan.
    dipakai: set = set()
    n1 = EC.nama_lembar_aman("Neraca", dipakai)
    n2 = EC.nama_lembar_aman("Neraca", dipakai)
    p.cek("nama lembar kembar dibedakan", n1 != n2, f"{n1!r} vs {n2!r}")

    # ==================================================================
    print()
    print("[3. Cetak A4: ukuran kertas dan isinya]")
    pdf = FOLDER / "cetak.pdf"
    try:
        EC.simpan_pdf("Laporan Keuangan", "Tahun 2026", data, str(pdf),
                      perusahaan="PT Sinar Nusantara")
        p.cek("berkas PDF terbentuk", pdf.exists(),
              f"ukuran: {pdf.stat().st_size if pdf.exists() else 0} byte")
    except Exception as e:
        p.cek("penyimpanan PDF berjalan tanpa galat", False,
              f"{type(e).__name__}: {e}")
        pdf = None

    if pdf and pdf.exists():
        isi = pdf.read_bytes()
        p.cek("penanda berkas PDF sah", isi[:5] == b"%PDF-",
              f"awal: {isi[:8]!r}")

        # Ukuran halaman A4 dalam satuan titik PDF: 595 x 842.
        import re
        ukuran = re.search(rb"/MediaBox\s*\[\s*([\d.]+)\s+([\d.]+)\s+"
                           rb"([\d.]+)\s+([\d.]+)", isi)
        if ukuran:
            lebar = float(ukuran.group(3)) - float(ukuran.group(1))
            tinggi = float(ukuran.group(4)) - float(ukuran.group(2))
            # A4 = 595 x 842 titik. Toleransi 2 titik untuk pembulatan.
            p.cek("ukuran halaman A4 tegak (595 x 842 titik)",
                  abs(lebar - 595) <= 2 and abs(tinggi - 842) <= 2,
                  f"terukur: {lebar:.0f} x {tinggi:.0f} titik")
        else:
            p.cek("ukuran halaman dapat dibaca", False,
                  "penanda MediaBox tidak ditemukan")

        p.cek("PDF memuat sekurangnya satu halaman",
              isi.count(b"/Type /Page") >= 1)
        p.cek("PDF berukuran wajar", len(isi) > 1500,
              f"ukuran: {len(isi)} byte")

    # ==================================================================
    print()
    print("[4. Cetak A4 mendatar]")
    pdf_l = FOLDER / "cetak_mendatar.pdf"
    try:
        EC.simpan_pdf("Daftar Panjang", "", data, str(pdf_l),
                      mendatar=True,
                      perusahaan="PT Sinar Nusantara")
        isi = pdf_l.read_bytes()
        import re
        ukuran = re.search(rb"/MediaBox\s*\[\s*([\d.]+)\s+([\d.]+)\s+"
                           rb"([\d.]+)\s+([\d.]+)", isi)
        if ukuran:
            lebar = float(ukuran.group(3)) - float(ukuran.group(1))
            tinggi = float(ukuran.group(4)) - float(ukuran.group(2))
            p.cek("halaman mendatar (842 x 595 titik)",
                  abs(lebar - 842) <= 2 and abs(tinggi - 595) <= 2,
                  f"terukur: {lebar:.0f} x {tinggi:.0f} titik")
        else:
            p.cek("ukuran halaman mendatar dapat dibaca", False)
    except Exception as e:
        p.cek("penyimpanan PDF mendatar berjalan", False,
              f"{type(e).__name__}: {e}")

    # ==================================================================
    print()
    print("[5. Tabel panjang terpecah menjadi beberapa halaman]")
    # 120 baris data, jauh lebih panjang dari satu halaman A4.
    panjang = [("Daftar Panjang", [["No", "Nama", "Jumlah"]]
                + [[i, f"Baris {i}", i * 1_000_000] for i in range(1, 121)])]
    pdf_p = FOLDER / "panjang.pdf"
    try:
        EC.simpan_pdf("Uji Halaman", "", panjang, str(pdf_p))
        isi = pdf_p.read_bytes()
        halaman = isi.count(b"/Type /Page") - isi.count(b"/Type /Pages")
        p.cek("tabel panjang terpecah menjadi beberapa halaman",
              halaman >= 2, f"jumlah halaman: {halaman}")
        p.cek("berkas tidak kosong", len(isi) > 3000,
              f"ukuran: {len(isi)} byte")
    except Exception as e:
        p.cek("tabel panjang dapat dicetak", False,
              f"{type(e).__name__}: {e}")

    # ==================================================================
    print()
    print("[6. Pratinjau gambar terbentuk]")
    try:
        gambar = EC.pratinjau_gambar("Pratinjau", "Uji", data, lebar=800)
        p.cek("gambar pratinjau terbentuk", not gambar.isNull(),
              f"ukuran: {gambar.width()}x{gambar.height()}")
        p.cek("gambar pratinjau berukuran wajar", gambar.height() > 100,
              f"tinggi: {gambar.height()}")
        # Gambar harus berisi sesuatu, bukan putih kosong.
        berwarna = 0
        for y in range(0, gambar.height(), 20):
            for x in range(0, gambar.width(), 20):
                if gambar.pixel(x, y) != 0xFFFFFFFF:
                    berwarna += 1
        p.cek("gambar pratinjau memuat isi, bukan halaman kosong",
              berwarna > 10, f"titik berisi: {berwarna}")
        jalur_gambar = FOLDER / "pratinjau.png"
        gambar.save(str(jalur_gambar))
        p.cek("pratinjau dapat disimpan sebagai gambar",
              jalur_gambar.exists())
    except Exception as e:
        p.cek("pratinjau gambar berjalan tanpa galat", False,
              f"{type(e).__name__}: {e}")

    # ==================================================================
    print()
    print("[7. Nilai kosong dan teks panjang tetap aman]")
    aneh = [
        ("Data Kosong", [["A", "B"]]),
        ("Nilai Kosong", [["A", "B"], [None, ""], ["x", None]]),
        ("Teks Panjang", [["Keterangan"], ["A" * 500]]),
        ("Karakter Khusus", [["Nama"], ["<b>tebal</b> & 'kutip' \"ganda\""]]),
        ("Angka Nol", [["Jumlah"], [0], [0.0]]),
    ]
    berkas2 = FOLDER / "aneh.xlsx"
    try:
        EC.ekspor_excel("Uji Nilai Aneh", aneh, str(berkas2))
        p.cek("ekspor dengan nilai kosong dan karakter khusus berhasil",
              berkas2.exists())
        import openpyxl
        wb = openpyxl.load_workbook(str(berkas2))
        p.cek_sama("seluruh lembar terbentuk", len(wb.sheetnames), 5,
                   f"lembar: {wb.sheetnames}")
    except Exception as e:
        p.cek("ekspor nilai aneh berjalan tanpa galat", False,
              f"{type(e).__name__}: {e}")

    pdf_aneh = FOLDER / "aneh.pdf"
    try:
        EC.simpan_pdf("Uji Nilai Aneh", "", aneh, str(pdf_aneh))
        p.cek("cetak dengan nilai kosong dan karakter khusus berhasil",
              pdf_aneh.exists())
        # Karakter khusus tidak boleh merusak tata letak HTML.
        isi = pdf_aneh.read_bytes()
        p.cek("berkas hasil tetap sah", isi[:5] == b"%PDF-")
    except Exception as e:
        p.cek("cetak nilai aneh berjalan tanpa galat", False,
              f"{type(e).__name__}: {e}")

    # ==================================================================
    print()
    print("[8. Teks tabel diubah menjadi angka dengan benar]")
    # Angka harus dikenali supaya dapat dijumlahkan di Excel, sedangkan
    # teks biasa tetap tersimpan sebagai teks.
    contoh = [
        ("750.000.000", 750_000_000, "angka ribuan gaya Indonesia"),
        ("Rp1.500.000", 1_500_000, "angka dengan awalan Rp"),
        ("45.000,50", 45_000.5, "angka dengan desimal koma"),
        ("-2.500.000", -2_500_000, "angka negatif"),
        ("12,5%", None, "persentase tetap teks agar tanda % tidak hilang"),
        ("0", 0, "nol"),
        ("Kas", None, "teks biasa"),
        ("PT Maju Bersama", None, "nama perusahaan"),
        ("", None, "teks kosong"),
        ("2026-01-15", None, "tanggal"),
        ("INV/2026/0001", None, "nomor dokumen"),
    ]
    for teks, harap, alasan in contoh:
        hasil = EC._teks_ke_angka(teks)
        p.cek_sama(f"ubah teks ke angka ({alasan}): {teks!r}", hasil, harap)

    # ==================================================================
    print()
    print("[9. Mengambil isi tabel di layar]")
    from PySide6.QtWidgets import QTableWidget, QTableWidgetItem

    tabel = QTableWidget(2, 3)
    tabel.setHorizontalHeaderLabels(["Nama", "Jumlah", "Catatan"])
    isi_tabel = [
        ("Kas", "750.000.000", "saldo awal"),
        ("Piutang", "250.000.000", ""),
    ]
    for r, baris in enumerate(isi_tabel):
        for c, nilai in enumerate(baris):
            tabel.setItem(r, c, QTableWidgetItem(nilai))

    diambil = EC.tabel_dari_widget(tabel)
    p.cek_sama("jumlah baris termasuk judul", len(diambil), 3)
    p.cek_sama("baris judul diambil dari kepala tabel", diambil[0],
               ["Nama", "Jumlah", "Catatan"])
    p.cek_sama("teks tetap teks", diambil[1][0], "Kas")
    p.cek_sama("angka diubah menjadi angka", diambil[1][1], 750_000_000)
    p.cek("angka bertipe angka, bukan teks",
          isinstance(diambil[1][1], (int, float)),
          f"tipe: {type(diambil[1][1]).__name__}")

    # Tabel kosong tidak membuat galat.
    p.cek_sama("tabel kosong menghasilkan daftar kosong",
               EC.tabel_dari_widget(None), [])

    # ==================================================================
    print()
    print("[10. Tanda air, pengesahan, dan kode verifikasi dokumen]")
    from akuntansi_id import db
    import pdfplumber
    import re
    import string

    db.init_db()
    db.simpan_setelan_cetak(
        air_aktif=True, air_teks="{perusahaan} · SALINAN", air_pekat=8,
        ttd_aktif=True, ttd_nama="Ariel Pratama", ttd_jabatan="Direktur",
        ttd_kota="Jakarta", ttd_gambar="")

    setelan = db.setelan_cetak()
    p.cek_sama("nama penanda tangan tersimpan", setelan["ttd_nama"],
               "Ariel Pratama")
    p.cek_sama("teks tanda air tersimpan", setelan["air_teks"],
               "{perusahaan} · SALINAN")
    p.cek("kepekatan tanda air dibatasi", 
          db.simpan_setelan_cetak(air_pekat=99)["air_pekat"] == 18)
    db.simpan_setelan_cetak(air_pekat=8)

    ttd_data = [("Ringkasan", [
        ["Keterangan", "Nilai"],
        ["Pendapatan usaha", 128_500_000],
        ["Beban usaha", 74_300_000],
        ["Laba bersih", 54_200_000],
    ])]
    penanda = {"nama": "Ariel Pratama", "jabatan": "Direktur",
               "kota": "Jakarta"}
    kode = EC.kode_verifikasi_dokumen(
        "Laporan Laba Rugi", "Tahun 2026", ttd_data,
        "PT Sinar Nusantara", penanda)
    p.cek("kode verifikasi berformat 4-4-4-4",
          bool(re.fullmatch(r"[0-9A-F]{4}(-[0-9A-F]{4}){3}", kode)),
          f"kode: {kode}")
    p.cek("kode hanya memakai huruf besar dan angka",
          set(kode.replace("-", "")) <= set(string.hexdigits.upper()),
          f"kode: {kode}")

    kode_ulang = EC.kode_verifikasi_dokumen(
        "Laporan Laba Rugi", "Tahun 2026", ttd_data,
        "PT Sinar Nusantara", penanda)
    p.cek_sama("isi yang sama menghasilkan kode yang sama", kode_ulang, kode)

    ttd_lain = [("Ringkasan", [
        ["Keterangan", "Nilai"],
        ["Pendapatan usaha", 128_500_001],
        ["Beban usaha", 74_300_000],
        ["Laba bersih", 54_200_001],
    ])]
    kode_lain = EC.kode_verifikasi_dokumen(
        "Laporan Laba Rugi", "Tahun 2026", ttd_lain,
        "PT Sinar Nusantara", penanda)
    p.cek("satu angka berubah menghasilkan kode berbeda", kode_lain != kode,
          f"{kode} vs {kode_lain}")

    nama_bagian_lain = [("Rincian Lain", ttd_data[0][1])]
    kode_bagian = EC.kode_verifikasi_dokumen(
        "Laporan Laba Rugi", "Tahun 2026", nama_bagian_lain,
        "PT Sinar Nusantara", penanda)
    p.cek("nama bagian ikut terlindungi", kode_bagian != kode,
          f"{kode} vs {kode_bagian}")

    pdf_ttd = FOLDER / "pengesahan.pdf"
    EC.simpan_pdf("Laporan Laba Rugi", "Tahun 2026", ttd_data,
                  str(pdf_ttd), perusahaan="PT Sinar Nusantara",
                  penanda=penanda)
    try:
        with pdfplumber.open(str(pdf_ttd)) as dok:
            halaman_ttd = [h.extract_text() or "" for h in dok.pages]
        teks_ttd = "\n".join(halaman_ttd)
        p.cek("pengesahan memuat nama penanda tangan",
              "Ariel Pratama" in teks_ttd)
        p.cek("pengesahan memuat jabatan", "Direktur" in teks_ttd)
        p.cek("pengesahan memuat kota dan tanggal", "Jakarta" in teks_ttd)
        p.cek("pengesahan menyebut tanda tangan elektronik",
              "Ditandatangani secara elektronik" in teks_ttd)
        p.cek("kode verifikasi tercetak", kode in teks_ttd)
    except Exception as e:
        p.cek("pengesahan dapat dibaca dari PDF", False,
              f"{type(e).__name__}: {e}")

    # Tanda air diperiksa lewat piksel: area kosong harus berubah saat
    # tanda air dinyalakan. Teks diagonal tidak selalu terbaca oleh
    # pengekstrak PDF, jadi pemeriksaan teks tidak cukup.
    def non_putih(gambar, atas: int, bawah: int) -> int:
        jumlah = 0
        for y in range(atas, min(bawah, gambar.height()), 3):
            for x in range(0, gambar.width(), 3):
                if gambar.pixel(x, y) != 0xFFFFFFFF:
                    jumlah += 1
        return jumlah

    pendek = [("Ringkasan", [["Keterangan", "Nilai"],
                             ["Pendapatan", 128_500_000]])]
    db.simpan_setelan_cetak(air_aktif=False, ttd_aktif=False)
    bersih = EC.pratinjau_gambar("Uji Tanda Air", "", pendek, lebar=800,
                                 perusahaan="PT Sinar Nusantara")
    db.simpan_setelan_cetak(air_aktif=True, air_pekat=12)
    berair = EC.pratinjau_gambar("Uji Tanda Air", "", pendek, lebar=800,
                                 perusahaan="PT Sinar Nusantara")
    atas, bawah = int(bersih.height() * 0.42), int(bersih.height() * 0.88)
    titik_bersih = non_putih(bersih, atas, bawah)
    titik_air = non_putih(berair, atas, bawah)
    p.cek("tanda air terlihat pada area kosong",
          titik_air > titik_bersih + 200,
          f"titik berisi: {titik_bersih} -> {titik_air}")

    pdf_tanpa = FOLDER / "tanpa_pengesahan.pdf"
    EC.simpan_pdf("Laporan Laba Rugi", "Tahun 2026", ttd_data,
                  str(pdf_tanpa), perusahaan="PT Sinar Nusantara",
                  penanda=penanda)
    try:
        with pdfplumber.open(str(pdf_tanpa)) as dok:
            teks_tanpa = "\n".join(h.extract_text() or "" for h in dok.pages)
        p.cek("pengesahan mati tidak mencetak nama penanda tangan",
              "Ariel Pratama" not in teks_tanpa)
        p.cek("pengesahan mati tidak mencetak kalimat tanda tangan",
              "Ditandatangani secara elektronik" not in teks_tanpa)
    except Exception as e:
        p.cek("PDF tanpa pengesahan dapat dibaca", False,
              f"{type(e).__name__}: {e}")

    # ==================================================================
    print()
    print("[11. Invoice: desain dokumen, tanda air, dan pengesahan]")
    from akuntansi_id import services, modules_sales as S
    from akuntansi_id.ui.pages.penjualan import buat_pdf_invoice

    db.simpan_setelan_cetak(air_aktif=True, air_teks="{perusahaan}",
                            air_pekat=8, ttd_aktif=True,
                            ttd_nama="Ariel Pratama", ttd_jabatan="Direktur",
                            ttd_kota="Jakarta")
    cid = services.create_company("PT Uji Invoice", "pt")
    butir = [
        {"deskripsi": "Jasa konsultasi pajak", "qty": 1, "satuan": "paket",
         "harga_satuan": 2_500_000, "subtotal": 2_500_000},
        {"deskripsi": "Penyusunan laporan keuangan", "qty": 1,
         "satuan": "paket", "harga_satuan": 1_750_000, "subtotal": 1_750_000},
    ]
    inv_id = S.buat_invoice(cid, "2026-10-27", butir,
                            pelanggan="PT Pelanggan Uji",
                            catatan="Invoice untuk pengujian.",
                            username="uji")
    pdf_inv = FOLDER / "invoice.pdf"
    try:
        buat_pdf_invoice(cid, inv_id, str(pdf_inv))
        with pdfplumber.open(str(pdf_inv)) as dok:
            halaman_inv = [h.extract_text() or "" for h in dok.pages]
            besar_inv = [sum(1 for c in h.chars if c["size"] > 30)
                         for h in dok.pages]
        teks_inv = "\n".join(halaman_inv)
        p.cek("invoice terbentuk dan memuat judul INVOICE",
              pdf_inv.exists() and "INVOICE" in teks_inv)
        p.cek("invoice memuat nama penanda tangan",
              "Ariel Pratama" in teks_inv)
        p.cek("invoice memuat pengesahan elektronik",
              "Ditandatangani secara elektronik" in teks_inv)
        p.cek("invoice memuat kode verifikasi pengesahan",
              "Kode verifikasi" in teks_inv)
        p.cek("invoice memuat kode dokumen di kaki",
              "Kode dokumen" in teks_inv)
        p.cek("invoice memuat tanda air diagonal", besar_inv[0] >= 10,
              f"huruf besar: {besar_inv[0]}")
    except Exception as e:
        p.cek("invoice dapat dibuat dan dibaca", False,
              f"{type(e).__name__}: {e}")

    # Invoice panjang: kepala tabel dan tanda air berulang, pengesahan sekali.
    butir_panjang = [
        {"deskripsi": f"Jasa pendampingan bulan ke-{i}", "qty": 1,
         "satuan": "paket", "harga_satuan": 1_250_000,
         "subtotal": 1_250_000}
        for i in range(1, 41)
    ]
    inv_panjang = S.buat_invoice(
        cid, "2026-10-27", butir_panjang, pelanggan="PT Pelanggan Uji",
        username="uji")
    pdf_inv_panjang = FOLDER / "invoice_panjang.pdf"
    try:
        buat_pdf_invoice(cid, inv_panjang, str(pdf_inv_panjang))
        with pdfplumber.open(str(pdf_inv_panjang)) as dok:
            halaman_panjang = [h.extract_text() or "" for h in dok.pages]
            besar_panjang = [sum(1 for c in h.chars if c["size"] > 30)
                             for h in dok.pages]
        teks_panjang = "\n".join(halaman_panjang)
        p.cek("invoice panjang memakai lebih dari satu halaman",
              len(halaman_panjang) >= 2, f"{len(halaman_panjang)} halaman")
        p.cek("halaman lanjutan invoice diberi kepala",
              "lanjutan" in halaman_panjang[1])
        p.cek("pengesahan hanya tercetak sekali",
              teks_panjang.count("Ditandatangani secara elektronik") == 1)
        p.cek("kode dokumen tercetak di setiap halaman",
              all("Kode dokumen" in t for t in halaman_panjang))
        p.cek("tanda air tercetak di setiap halaman",
              all(n >= 10 for n in besar_panjang), f"{besar_panjang}")
    except Exception as e:
        p.cek("invoice panjang dapat dibuat dan dibaca", False,
              f"{type(e).__name__}: {e}")

    # Invoice polos: tanpa tanda air dan pengesahan, kode tetap melindungi isi.
    db.simpan_setelan_cetak(air_aktif=False, ttd_aktif=False)
    pdf_inv_polos = FOLDER / "invoice_polos.pdf"
    try:
        buat_pdf_invoice(cid, inv_id, str(pdf_inv_polos))
        with pdfplumber.open(str(pdf_inv_polos)) as dok:
            halaman_polos = [h.extract_text() or "" for h in dok.pages]
            besar_polos = [sum(1 for c in h.chars if c["size"] > 30)
                           for h in dok.pages]
        teks_polos = "\n".join(halaman_polos)
        p.cek("invoice polos tanpa pengesahan",
              "Ditandatangani secara elektronik" not in teks_polos)
        p.cek("invoice polos tanpa tanda air", besar_polos[0] == 0,
              f"huruf besar: {besar_polos[0]}")
        p.cek("invoice polos tetap memuat kode dokumen",
              "Kode dokumen" in teks_polos)
    except Exception as e:
        p.cek("invoice polos dapat dibuat dan dibaca", False,
              f"{type(e).__name__}: {e}")

    # Kembalikan ke keadaan netral untuk uji berikutnya.
    db.simpan_setelan_cetak(air_aktif=False, ttd_aktif=False,
                            ttd_nama="", ttd_jabatan="", ttd_kota="",
                            air_teks="{perusahaan}")

    return p.ringkas()


if __name__ == "__main__":
    try:
        kode = main()
    finally:
        shutil.rmtree(FOLDER, ignore_errors=True)
    sys.exit(kode)
