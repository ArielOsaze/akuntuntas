"""
AkunTuntas - Analisis Kesehatan Keuangan & Deteksi Dini Masalah
================================================================
Mesin ini membaca data pembukuan dan menghasilkan DIAGNOSIS otomatis
tentang kondisi keuangan usaha, lengkap dengan rekomendasi tindakan.

Filosofi: pemilik usaha sering tidak tahu bahwa pembukuannya bermasalah
sampai terlambat (kena sanksi pajak, atau tidak sadar usahanya merugi).
Modul ini bertindak sebagai "akuntan virtual" yang memperingatkan lebih awal.

Setiap temuan memiliki:
  - tingkat   : kritis | peringatan | saran | baik
  - judul     : ringkas
  - penjelasan: apa artinya bagi pemilik usaha (bahasa awam)
  - tindakan  : langkah konkret yang harus dilakukan
  - dampak    : konsekuensi bila dibiarkan (termasuk sanksi pajak)
  - dasar_hukum: bila temuan terkait kewajiban hukum/pajak
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional

from .. import config, db
from . import accounting as acc
from . import tax_engine as tx


# ==========================================================================
# MODEL TEMUAN
# ==========================================================================
@dataclass
class Temuan:
    tingkat: str = "saran"          # kritis | peringatan | saran | baik
    kategori: str = "Umum"          # Pembukuan | Pajak | Kas | Profitabilitas | ...
    judul: str = ""
    penjelasan: str = ""
    tindakan: str = ""
    dampak: str = ""
    dasar_hukum: str = ""
    angka: str = ""
    # Kode halaman yang paling relevan untuk menindaklanjuti temuan ini,
    # dipakai tombol aksi cepat pada kartu temuan. Kosong berarti tidak ada
    # halaman yang cocok.
    halaman: str = ""

    @property
    def ikon(self) -> str:
        return {"kritis": "", "peringatan": "", "saran": "", "baik": ""}.get(
            self.tingkat, "")

    @property
    def label(self) -> str:
        return {"kritis": "KRITIS", "peringatan": "PERHATIAN",
                "saran": "SARAN", "baik": "BAIK"}.get(self.tingkat, "-")


def _persen(v: float, desimal: int = 1) -> str:
    """Persen dengan koma desimal, sesuai penulisan angka Indonesia."""
    try:
        teks = f"{float(v) * 100:.{desimal}f}"
    except (TypeError, ValueError):
        return "0%"
    return teks.replace(".", ",") + "%"


def _rasio(v, desimal: int = 2) -> str:
    """Angka rasio dengan koma desimal, sesuai penulisan angka Indonesia."""
    try:
        angka = float(v)
    except (TypeError, ValueError):
        return "-"
    if angka == float("inf"):
        return "tidak terhingga"
    teks = f"{angka:.{desimal}f}"
    return teks.replace(".", ",") + "x"


@dataclass
class HasilAnalisis:
    skor: int = 100
    grade: str = "A"
    grade_label: str = "Sangat Sehat"
    temuan: list = field(default_factory=list)
    ringkasan: str = ""
    statistik: dict = field(default_factory=dict)
    rasio: dict = field(default_factory=dict)

    @property
    def jumlah_kritis(self) -> int:
        return sum(1 for t in self.temuan if t.tingkat == "kritis")

    @property
    def jumlah_peringatan(self) -> int:
        return sum(1 for t in self.temuan if t.tingkat == "peringatan")

    @property
    def jumlah_saran(self) -> int:
        return sum(1 for t in self.temuan if t.tingkat == "saran")

    @property
    def jumlah_baik(self) -> int:
        return sum(1 for t in self.temuan if t.tingkat == "baik")


# ==========================================================================
# RASIO KEUANGAN
# ==========================================================================
def hitung_rasio(nr: acc.Neraca, lr: acc.LabaRugi, kas: int) -> dict:
    """
    Rasio keuangan standar untuk UMKM.
    Rumus mengikuti praktik analisis laporan keuangan umum.
    """
    r: dict = {}
    aset_lancar = nr.total_aset_lancar
    liab_pendek = nr.total_liabilitas_pendek

    r["rasio_lancar"] = (aset_lancar / liab_pendek) if liab_pendek > 0 else (
        float("inf") if aset_lancar > 0 else 0.0)
    r["rasio_kas"] = (kas / liab_pendek) if liab_pendek > 0 else (
        float("inf") if kas > 0 else 0.0)
    r["rasio_utang_ekuitas"] = (nr.total_liabilitas / nr.total_ekuitas
                                if nr.total_ekuitas > 0 else float("inf"))
    r["rasio_utang_aset"] = (nr.total_liabilitas / nr.total_aset
                             if nr.total_aset > 0 else 0.0)
    r["margin_kotor"] = lr.margin_kotor
    r["margin_operasional"] = lr.margin_operasional
    r["margin_bersih"] = lr.margin_bersih
    r["roa"] = (lr.laba_bersih / nr.total_aset) if nr.total_aset > 0 else 0.0
    r["roe"] = (lr.laba_bersih / nr.total_ekuitas) if nr.total_ekuitas > 0 else 0.0
    r["beban_terhadap_pendapatan"] = (
        (lr.beban_operasional + lr.hpp) / lr.pendapatan_usaha
        if lr.pendapatan_usaha > 0 else 0.0)
    r["kas"] = kas
    r["aset_lancar"] = aset_lancar
    r["liabilitas_pendek"] = liab_pendek
    r["ekuitas"] = nr.total_ekuitas
    r["laba_bersih"] = lr.laba_bersih
    return r


# ==========================================================================
# ANALISIS UTAMA
# ==========================================================================
def analisis_kesehatan(company_id: int, tahun: int,
                       bulan: Optional[int] = None) -> HasilAnalisis:
    """
    Jalankan seluruh pemeriksaan dan kembalikan diagnosis lengkap.
    """
    hasil = HasilAnalisis()
    comp = db.q1("SELECT * FROM companies WHERE id=?", (company_id,))
    if comp is None:
        hasil.skor = 0
        hasil.grade = "?"
        hasil.ringkasan = "Data perusahaan tidak ditemukan."
        return hasil

    nr = acc.neraca(company_id, tahun, bulan)
    lr = acc.laba_rugi(company_id, tahun, bulan)
    kas = _saldo_kas(company_id, tahun, bulan)
    omzet = acc.omzet_setahun(company_id, tahun, bulan)
    rasio = hitung_rasio(nr, lr, kas)
    hasil.rasio = rasio

    # ---- statistik pendukung
    jml_jurnal = int(db.scalar(
        "SELECT COUNT(*) FROM journal_entries WHERE company_id=? AND substr(tanggal,1,4)=?",
        (company_id, str(tahun))))
    jml_jurnal_total = int(db.scalar(
        "SELECT COUNT(*) FROM journal_entries WHERE company_id=?", (company_id,)))
    cek = acc.total_neraca_saldo(company_id, tahun, bulan)
    tdk_seimbang = acc.cek_jurnal_tidak_seimbang(company_id)
    jml_akun = int(db.scalar(
        "SELECT COUNT(*) FROM accounts WHERE company_id=? AND is_active=1", (company_id,)))

    hasil.statistik = {
        "omzet": omzet,
        "laba_bersih": lr.laba_bersih,
        "kas": kas,
        "total_aset": nr.total_aset,
        "total_liabilitas": nr.total_liabilitas,
        "total_ekuitas": nr.total_ekuitas,
        "jumlah_jurnal": jml_jurnal,
        "jumlah_jurnal_total": jml_jurnal_total,
        "jumlah_akun": jml_akun,
        "selisih_jurnal": cek["selisih"],
        "jurnal_tidak_seimbang": len(tdk_seimbang),
        "selisih_neraca": nr.selisih,
    }

    # ---------------------------------------------------------------- kosong
    # Belum ada satu pun jurnal berarti belum ada yang dapat dinilai. Tanpa
    # pemeriksaan ini, seluruh pemeriksaan lolos karena tidak menemukan
    # kesalahan, dan aplikasi memberi nilai tinggi kepada pembukuan yang
    # sebenarnya masih kosong. Pengguna mengira pembukuannya sehat padahal
    # belum ada isinya sama sekali.
    if jml_jurnal_total == 0:
        hasil.skor = 0
        hasil.grade = "N/A"
        hasil.grade_label = "Belum Dinilai"
        hasil.ringkasan = (
            "Belum ada transaksi yang tercatat, sehingga kondisi keuangan "
            "belum dapat dinilai. Nilai akan muncul setelah Anda mencatat "
            "transaksi pertama.")
        hasil.temuan = []
        return hasil

    T: list[Temuan] = []

    # ======================================================================
    # 1. INTEGRITAS PEMBUKUAN (paling dasar — bila salah, semua laporan salah)
    # ======================================================================
    if tdk_seimbang:
        contoh = ", ".join(r["no_bukti"] for r in tdk_seimbang[:5])
        T.append(Temuan(
            tingkat="kritis", kategori="Pembukuan",
            judul=f"{len(tdk_seimbang)} bukti jurnal tidak seimbang",
            penjelasan=(
                f"Ada {len(tdk_seimbang)} nomor bukti yang total debit dan kreditnya "
                f"tidak sama (contoh: {contoh}). Ini melanggar kaidah dasar pembukuan "
                "berpasangan sehingga seluruh laporan keuangan menjadi tidak akurat."
            ),
            tindakan=(
                "Buka menu Jurnal Umum, periksa bukti yang ditandai, lalu tambahkan atau "
                "perbaiki baris yang kurang agar total debit = total kredit."
            ),
            dampak=(
                "Laporan laba rugi, neraca, dan perhitungan pajak akan salah. Dalam "
                "pemeriksaan pajak, pembukuan yang tidak benar dapat dianggap tidak "
                "dipercaya dan penghasilan dihitung secara jabatan (Pasal 13 UU KUP)."
            ),
            dasar_hukum="Pasal 28 UU KUP - kewajiban menyelenggarakan pembukuan yang benar.",
        ))

    if abs(nr.selisih) >= 1:
        T.append(Temuan(
            tingkat="kritis", kategori="Pembukuan",
            judul="Neraca tidak seimbang",
            penjelasan=(
                f"Total Aset ({tx.rupiah(nr.total_aset)}) tidak sama dengan total "
                f"Liabilitas + Ekuitas ({tx.rupiah(nr.total_liabilitas_ekuitas)}). "
                f"Selisihnya {tx.rupiah(abs(nr.selisih))}. Persamaan dasar akuntansi "
                "harus selalu seimbang."
            ),
            tindakan=(
                "Periksa apakah ada saldo awal akun yang belum lengkap, akun dengan "
                "baris neraca kosong, atau jurnal dengan akun yang tidak terdaftar di "
                "Bagan Akun. Cek juga apakah laba tahun berjalan sudah dihitung."
            ),
            dampak="Neraca tidak dapat dipakai untuk pengambilan keputusan atau pelaporan.",
            dasar_hukum="Persamaan dasar akuntansi: ASET = LIABILITAS + EKUITAS.",
        ))

    if jml_jurnal == 0:
        T.append(Temuan(
            tingkat="peringatan", kategori="Pembukuan",
                halaman="jurnal",
            judul=f"Belum ada transaksi tercatat pada tahun {tahun}",
            penjelasan=(
                "Aplikasi tidak menemukan satu pun jurnal untuk tahun ini. Laporan "
                "keuangan akan menampilkan angka nol sehingga tidak bermakna."
            ),
            tindakan=(
                "Mulai catat transaksi: setoran modal awal, penjualan, pembelian, dan "
                "beban operasional. Gunakan menu Jurnal Umum atau catat lewat menu "
                "Penjualan/Pembelian agar pajak ikut terhitung otomatis."
            ),
            dampak=(
                "Pembukuan yang tidak dijalankan dapat dikenai sanksi pidana: penjara "
                "6 bulan sampai 6 tahun dan denda 2x sampai 4x pajak yang tidak dibayar."
            ),
            dasar_hukum="Pasal 28 & Pasal 39 UU KUP.",
        ))

    # Akun tanpa saldo awal padahal neraca butuh
    akun_tanpa_saldo = int(db.scalar(
        """SELECT COUNT(*) FROM accounts a
           WHERE a.company_id=? AND a.is_active=1 AND a.saldo_awal=0
             AND a.tipe IN ('Aset','Liabilitas','Ekuitas')
             AND NOT EXISTS (SELECT 1 FROM journal_lines jl
                             WHERE jl.company_id=a.company_id AND jl.kode_akun=a.kode)""",
        (company_id,)))
    if akun_tanpa_saldo > 0 and jml_jurnal > 0:
        T.append(Temuan(
            tingkat="saran", kategori="Pembukuan",
                halaman="jurnal",
            judul=f"{akun_tanpa_saldo} akun neraca belum memiliki saldo awal",
            penjelasan=(
                "Beberapa akun aset/liabilitas/ekuitas belum diisi saldo awal dan belum "
                "pernah dipakai dalam jurnal. Bila usaha Anda sudah berjalan sebelum "
                "memakai aplikasi ini, saldo awalnya perlu dimasukkan agar neraca benar."
            ),
            tindakan=(
                "Buka menu Bagan Akun, isi saldo awal untuk kas, bank, persediaan, "
                "utang, dan modal sesuai kondisi nyata pada tanggal mulai pembukuan."
            ),
            dampak="Neraca akan tampak lebih kecil dari kenyataan; modal tidak tercermin.",
        ))

    # ======================================================================
    # 2. LIKUIDITAS & KAS
    # ======================================================================
    liab_pendek = nr.total_liabilitas_pendek
    if liab_pendek > 0:
        if kas < liab_pendek:
            T.append(Temuan(
                tingkat="kritis" if kas < liab_pendek * 0.5 else "peringatan",
                kategori="Kas",
                judul="Kas tidak cukup menutup kewajiban jangka pendek",
                penjelasan=(
                    f"Saldo kas & bank {tx.rupiah(kas)}, sedangkan kewajiban jangka "
                    f"pendek {tx.rupiah(liab_pendek)}. Anda berpotensi kesulitan "
                    f"membayar utang yang jatuh tempo, kekurangan "
                    f"{tx.rupiah(liab_pendek - kas)}."
                ),
                tindakan=(
                    "Segera tagih piutang yang jatuh tempo, tunda pembelian yang belum "
                    "mendesak, dan negosiasi ulang jadwal bayar dengan pemasok. "
                    "Pertimbangkan menambah modal atau fasilitas kredit modal kerja."
                ),
                dampak=(
                    "Risiko gagal bayar, denda keterlambatan, dan kehilangan kepercayaan "
                    "pemasok. Bila yang tertunggak adalah pajak, akan dikenai sanksi "
                    "bunga 2%/bulan."
                ),
                angka=f"Kas {tx.rupiah(kas)} vs kewajiban {tx.rupiah(liab_pendek)}",
            ))
        elif kas < liab_pendek * 1.5:
            T.append(Temuan(
                tingkat="saran", kategori="Kas",
                judul="Bantalan kas relatif tipis",
                penjelasan=(
                    f"Kas {tx.rupiah(kas)} hanya sekitar "
                    f"{_rasio(kas / liab_pendek, 1)} kewajiban jangka pendek "
                    f"({tx.rupiah(liab_pendek)}). Idealnya minimal 1,5x untuk keamanan."
                ),
                tindakan="Perkuat cadangan kas dan percepat penagihan piutang.",
                dampak="Rentan terhadap keterlambatan pembayaran pelanggan.",
                angka=f"Rasio kas {_rasio(kas / liab_pendek, 2)}",
            ))
        else:
            T.append(Temuan(
                tingkat="baik", kategori="Kas",
                judul="Posisi kas sehat",
                penjelasan=(
                    f"Kas {tx.rupiah(kas)} mencukupi untuk menutup kewajiban jangka "
                    f"pendek {tx.rupiah(liab_pendek)} (rasio {_rasio(kas / liab_pendek, 2)})."
                ),
                tindakan="Pertahankan. Pertimbangkan menempatkan kelebihan kas pada deposito.",
                dasar_hukum="Bunga deposito dikenai PPh Final 20% (PP 19/2009).",
            ))

    rl = rasio["rasio_lancar"]
    if liab_pendek > 0 and rl != float("inf"):
        if rl < 1.0:
            T.append(Temuan(
                tingkat="kritis", kategori="Likuiditas",
                judul="Aset lancar lebih kecil dari kewajiban jangka pendek",
                penjelasan=(
                    f"Rasio lancar {_rasio(rl, 2)} (aset lancar {tx.rupiah(nr.total_aset_lancar)} "
                    f"dibanding kewajiban jangka pendek {tx.rupiah(liab_pendek)}). "
                    "Usaha berisiko tidak mampu membayar utang jangka pendek."
                ),
                tindakan=(
                    "Kurangi utang jangka pendek, konversi sebagian ke pinjaman jangka "
                    "panjang, atau tambah modal kerja."
                ),
                dampak="Risiko kebangkrutan teknis (tidak mampu bayar saat jatuh tempo).",
                angka=f"Rasio lancar {_rasio(rl, 2)}",
            ))
        elif rl >= 2.0:
            T.append(Temuan(
                tingkat="baik", kategori="Likuiditas",
                halaman="kas_bank",
                judul="Likuiditas kuat",
                penjelasan=(
                    f"Rasio lancar {_rasio(rl, 2)} - aset lancar jauh melebihi kewajiban "
                    "jangka pendek."
                ),
                tindakan="Sehat. Pastikan kelebihan dana tidak menganggur tanpa hasil.",
                angka=f"Rasio lancar {_rasio(rl, 2)}",
            ))
        elif rl < 1.5:
            T.append(Temuan(
                tingkat="saran", kategori="Likuiditas",
                halaman="kas_bank",
                judul="Likuiditas perlu diperhatikan",
                penjelasan=(
                    f"Rasio lancar {_rasio(rl, 2)}. Masih di atas 1 tetapi di bawah angka "
                    "nyaman 1,5x."
                ),
                tindakan="Tingkatkan penagihan piutang dan kelola persediaan lebih efisien.",
                angka=f"Rasio lancar {_rasio(rl, 2)}",
            ))

    # Kas negatif — indikasi kesalahan pencatatan
    akun_kas_negatif = db.q(
        """SELECT a.kode, a.nama,
                  a.saldo_awal + COALESCE(SUM(jl.debit - jl.kredit),0) AS saldo
           FROM accounts a
           LEFT JOIN journal_lines jl ON jl.company_id=a.company_id AND jl.kode_akun=a.kode
           WHERE a.company_id=? AND a.is_kas_bank=1
           GROUP BY a.kode HAVING saldo < 0""", (company_id,))
    if akun_kas_negatif:
        daftar = ", ".join(f"{r['nama']} ({tx.rupiah(r['saldo'])})" for r in akun_kas_negatif)
        T.append(Temuan(
            tingkat="kritis", kategori="Kas",
            judul="Saldo kas/bank bernilai negatif",
            penjelasan=(
                f"Akun berikut bersaldo negatif: {daftar}. Kas fisik tidak mungkin "
                "negatif - hampir pasti ada transaksi yang belum tercatat atau salah "
                "dicatat (mis. pengeluaran dicatat dua kali, atau penerimaan belum "
                "dicatat)."
            ),
            tindakan=(
                "Rekonsiliasi dengan mutasi rekening bank dan uang fisik. Cari "
                "pengeluaran yang tercatat ganda atau penerimaan yang belum dijurnal."
            ),
            dampak=(
                "Neraca dan laporan arus kas menjadi tidak benar. Sering menjadi temuan "
                "pertama dalam pemeriksaan pajak."
            ),
            dasar_hukum="Pasal 28 UU KUP - pembukuan harus dapat dipercaya.",
        ))

    # ======================================================================
    # 3. PROFITABILITAS
    # ======================================================================
    if lr.pendapatan_usaha > 0:
        if lr.laba_bersih < 0:
            T.append(Temuan(
                tingkat="kritis", kategori="Profitabilitas",
                judul="Usaha mengalami kerugian",
                penjelasan=(
                    f"Pendapatan {tx.rupiah(lr.pendapatan_usaha)} tetapi beban total "
                    f"{tx.rupiah(lr.hpp + lr.beban_operasional + lr.beban_lain)} sehingga "
                    f"rugi {tx.rupiah(abs(lr.laba_bersih))}."
                ),
                tindakan=(
                    "Telusuri beban terbesar pada rincian di bawah, lalu evaluasi: "
                    "(1) apakah harga jual terlalu rendah, (2) apakah ada beban yang bisa "
                    "dipangkas, (3) apakah ada beban pribadi yang keliru dicatat sebagai "
                    "beban usaha."
                ),
                dampak=(
                    "Usaha menggerus modal. Namun rugi fiskal dapat dikompensasikan ke "
                    "tahun berikutnya maksimal 5 tahun (Pasal 6 ayat 2 UU PPh) "
                    "pastikan rugi ini didukung bukti yang rapi."
                ),
                angka=f"Rugi {tx.rupiah(abs(lr.laba_bersih))}",
            ))
        elif lr.margin_bersih < 0.03:
            T.append(Temuan(
                tingkat="peringatan", kategori="Profitabilitas",
                judul="Margin laba bersih sangat tipis",
                penjelasan=(
                    f"Margin laba bersih hanya {_persen(lr.margin_bersih, 1)}. Artinya dari "
                    f"setiap Rp100 penjualan, laba bersih hanya {tx.rupiah(lr.margin_bersih * 100)}. "
                    "Usaha rentan terganggu bila biaya naik sedikit saja."
                ),
                tindakan=(
                    "Naikkan harga jual secara bertahap, cari pemasok dengan harga lebih "
                    "baik, dan tekan beban operasional yang tidak memberi nilai tambah."
                ),
                dampak="Sedikit kenaikan biaya bisa membuat usaha merugi.",
                angka=f"Margin bersih {_persen(lr.margin_bersih, 2)}",
            ))
        elif lr.margin_bersih >= 0.15:
            T.append(Temuan(
                tingkat="baik", kategori="Profitabilitas",
                halaman="laporan",
                judul="Margin laba bersih sehat",
                penjelasan=(
                    f"Margin laba bersih {_persen(lr.margin_bersih, 1)} - di atas 15%, "
                    "tergolong sehat untuk usaha kecil."
                ),
                tindakan="Pertahankan efisiensi. Pertimbangkan ekspansi bertahap.",
                angka=f"Margin bersih {_persen(lr.margin_bersih, 2)}",
            ))

        if lr.margin_kotor < 0.20:
            T.append(Temuan(
                tingkat="peringatan", kategori="Profitabilitas",
                judul="Margin kotor rendah",
                penjelasan=(
                    f"Margin kotor {_persen(lr.margin_kotor, 1)}. Laba kotor "
                    f"{tx.rupiah(lr.laba_kotor)} dari pendapatan "
                    f"{tx.rupiah(lr.pendapatan_usaha)}. Margin di bawah 20% menyulitkan "
                    "penutupan beban operasional."
                ),
                tindakan=(
                    "Tinjau harga pokok: negosiasi harga beli, cari pemasok alternatif, "
                    "kurangi pemborosan bahan, atau naikkan harga jual."
                ),
                dampak="Sulit menghasilkan laba operasional yang cukup.",
                angka=f"Margin kotor {_persen(lr.margin_kotor, 2)}",
            ))

        if rasio["beban_terhadap_pendapatan"] > 0.95:
            T.append(Temuan(
                tingkat="peringatan", kategori="Profitabilitas",
                halaman="laporan",
                judul="Beban menyerap hampir seluruh pendapatan",
                penjelasan=(
                    f"Total HPP + beban operasional = "
                    f"{_persen(rasio['beban_terhadap_pendapatan'], 1)} dari pendapatan. "
                    "Hampir tidak ada sisa untuk laba."
                ),
                tindakan="Lakukan audit beban: urutkan dari terbesar dan potong yang tidak esensial.",
                dampak="Usaha hanya bertahan tanpa bertumbuh.",
            ))

    # ======================================================================
    # 4. SOLVABILITAS
    # ======================================================================
    if nr.total_ekuitas > 0:
        der = nr.total_liabilitas / nr.total_ekuitas
        if der > 3.0:
            T.append(Temuan(
                tingkat="kritis", kategori="Solvabilitas",
                judul="Beban utang sangat berat dibanding modal",
                penjelasan=(
                    f"Rasio utang terhadap ekuitas {_rasio(der, 2)} - utang "
                    f"{tx.rupiah(nr.total_liabilitas)} vs ekuitas "
                    f"{tx.rupiah(nr.total_ekuitas)}. Usaha sangat bergantung pada utang."
                ),
                tindakan=(
                    "Kurangi ketergantungan utang, tingkatkan laba ditahan, atau tambah "
                    "modal pemilik. Hindari utang baru untuk kebutuhan konsumtif."
                ),
                dampak=(
                    "Bunga pinjaman menggerus laba. Untuk pinjaman dari pemegang saham, "
                    "bunga di atas rasio 4:1 tidak dapat dibiayakan (PMK 169/2017)."
                ),
                angka=f"DER {_rasio(der, 2)}",
            ))
        elif der > 1.5:
            T.append(Temuan(
                tingkat="saran", kategori="Solvabilitas",
                halaman="laporan",
                judul="Struktur modal cukup berutang",
                penjelasan=(
                    f"Rasio utang/ekuitas {_rasio(der, 2)}. Masih terkendali, tetapi perlu "
                    "pemantauan agar tidak meningkat."
                ),
                tindakan="Jaga pertumbuhan laba ditahan agar ekuitas menguat.",
                angka=f"DER {_rasio(der, 2)}",
            ))
    elif nr.total_liabilitas > 0:
        T.append(Temuan(
            tingkat="kritis", kategori="Solvabilitas",
            judul="Ekuitas nol atau negatif padahal ada utang",
            penjelasan=(
                f"Ekuitas {tx.rupiah(nr.total_ekuitas)} dengan utang "
                f"{tx.rupiah(nr.total_liabilitas)}. Usaha praktis dimodali oleh utang."
            ),
            tindakan="Segera tambah modal atau restrukturisasi utang.",
            dampak="Risiko insolvensi. Pemilik berpotensi menanggung kewajiban pribadi "
                   "bila tidak ada pemisahan aset yang jelas.",
        ))

    # ======================================================================
    # 5. KEPATUHAN PAJAK
    # ======================================================================
    sudah_pkp = bool(comp["status_pkp"])
    pkp_info = tx.status_pkp(omzet, sudah_pkp)
    if pkp_info["level"] == "danger":
        T.append(Temuan(
            tingkat="kritis", kategori="Pajak",
            judul="Omzet melampaui batas wajib PKP",
            penjelasan=(
                f"Peredaran bruto {tx.rupiah(omzet)} telah melewati Rp4,8 miliar, "
                "tetapi status perusahaan masih belum PKP."
            ),
            tindakan=(
                "Segera laporkan diri ke KPP untuk dikukuhkan sebagai PKP, lalu mulai "
                "memungut PPN dan menerbitkan faktur pajak."
            ),
            dampak=(
                "PPN yang seharusnya dipungut tetap menjadi kewajiban Anda meski tidak "
                "ditagih ke pelanggan. Ditambah sanksi administrasi."
            ),
            dasar_hukum=(
                "PMK 197/PMK.03/2013 - wajib PKP bila peredaran bruto melebihi "
                "Rp4,8 miliar."
            ),
        ))
    elif pkp_info["level"] == "warning":
        T.append(Temuan(
            tingkat="peringatan", kategori="Pajak",
            judul="Omzet mendekati batas wajib PKP",
            penjelasan=(
                f"Peredaran bruto {tx.rupiah(omzet)} sudah {pkp_info['pesan'].split('mencapai ')[-1].split(' dari')[0] if 'mencapai' in pkp_info['pesan'] else ''}"
                " dari batas Rp4,8 miliar."
            ),
            tindakan=(
                "Siapkan administrasi PKP: pemahaman faktur pajak, penomoran, dan "
                "pelaporan SPT Masa PPN. Pertimbangkan menambah harga jual 11% untuk "
                "mengakomodasi PPN."
            ),
            dampak="Bila terlambat mendaftar, PPN tetap terutang dan Anda yang menanggungnya.",
            dasar_hukum="PMK 197/PMK.03/2013; Pasal 9 UU PPN.",
        ))

    # Kelengkapan potput
    potput_tanpa_bupot = int(db.scalar(
        "SELECT COUNT(*) FROM tax_records WHERE company_id=? AND status='Terutang' "
        "AND substr(tanggal,1,4)=?", (company_id, str(tahun))))
    if potput_tanpa_bupot > 0:
        total_potput = int(db.scalar(
            "SELECT COALESCE(SUM(pajak),0) FROM tax_records WHERE company_id=? "
            "AND status='Terutang' AND substr(tanggal,1,4)=?", (company_id, str(tahun))))
        T.append(Temuan(
            tingkat="peringatan", kategori="Pajak",
            judul=f"{potput_tanpa_bupot} pemotongan pajak belum disetor",
            penjelasan=(
                f"Terdapat pemotongan pajak senilai {tx.rupiah(total_potput)} berstatus "
                "'Terutang' - belum disetor ke kas negara."
            ),
            tindakan=(
                "Segera buat kode billing dan setor melalui bank/payment channel, lalu "
                "catat NTPN pada menu Pajak. Simpan bukti potong untuk penerima penghasilan."
            ),
            dampak=(
                "Bunga keterlambatan dihitung dari tanggal jatuh tempo: suku bunga acuan "
                "+ 10% dibagi 12, per bulan keterlambatan."
            ),
            dasar_hukum="Pasal 9 UU KUP jo. UU HPP; PMK 81/2024.",
        ))

    # Deadline terdekat
    tenggat = cek_deadline(company_id, sudah_pkp)
    for d in tenggat:
        if d["hari_tersisa"] < 0:
            T.append(Temuan(
                tingkat="kritis", kategori="Pajak",
                judul=f"Terlewat: {d['nama']}",
                penjelasan=(
                    f"Tenggat {d['nama']} untuk {d['masa']} sudah lewat "
                    f"{abs(d['hari_tersisa'])} hari ({d['tenggat']})."
                ),
                tindakan="Setor dan laporkan segera. Hitung sanksi dengan kalkulator sanksi.",
                dampak=f"{d['sanksi']}",
                dasar_hukum=d["dasar_hukum"],
            ))
        elif d["hari_tersisa"] <= 7:
            T.append(Temuan(
                tingkat="peringatan", kategori="Pajak",
                judul=f"Tenggat dekat: {d['nama']}",
                penjelasan=(
                    f"{d['nama']} untuk {d['masa']} jatuh tempo {d['tenggat']} "
                    f"({d['hari_tersisa']} hari lagi)."
                ),
                tindakan="Siapkan pembayaran dan pelaporan sekarang agar tidak terlambat.",
                dampak=f"{d['sanksi']}",
                dasar_hukum=d["dasar_hukum"],
            ))

    # Skema PPh final tanpa konfirmasi
    if comp["skema_pph"] == "final_umkm" and not comp["final_eligible"]:
        T.append(Temuan(
            tingkat="kritis", kategori="Pajak",
                halaman="pajak",
            judul="Skema PPh Final 0,5% dipilih tetapi kelayakan belum dikonfirmasi",
            penjelasan=(
                "Perusahaan memakai skema PPh Final 0,5% padahal kelayakannya belum "
                "dikonfirmasi. Sejak PP 20/2026, tidak semua bentuk badan masih boleh "
                "memakai skema ini."
            ),
            tindakan=(
                "Buka Data Perusahaan, periksa kelayakan sesuai bentuk badan dan riwayat "
                "penggunaan, lalu konfirmasi atau ubah ke skema Pasal 31E."
            ),
            dampak="Salah skema berarti pajak terutang salah dan berpotensi kurang bayar.",
            dasar_hukum="PP 55/2022 jo. PP 20/2026.",
        ))

    # ======================================================================
    # 6. KUALITAS DATA
    # ======================================================================
    tanpa_keterangan = int(db.scalar(
        """SELECT COUNT(*) FROM journal_entries
           WHERE company_id=? AND substr(tanggal,1,4)=?
             AND (keterangan IS NULL OR TRIM(keterangan)='')""",
        (company_id, str(tahun))))
    if tanpa_keterangan > 0:
        T.append(Temuan(
            tingkat="saran", kategori="Kualitas Data",
                halaman="jurnal",
            judul=f"{tanpa_keterangan} jurnal tanpa keterangan",
            penjelasan=(
                "Beberapa jurnal tidak memiliki keterangan transaksi. Ini menyulitkan "
                "penelusuran saat pemeriksaan pajak atau audit."
            ),
            tindakan="Lengkapi keterangan jurnal dengan deskripsi transaksi yang jelas.",
            dampak=(
                "Dalam pemeriksaan, transaksi tanpa keterangan sulit dibuktikan "
                "kewajarannya dan berisiko dikoreksi."
            ),
            dasar_hukum="Pasal 28 ayat (8) UU KUP - dokumen harus tersimpan dan jelas.",
        ))

    tanpa_lawan = int(db.scalar(
        """SELECT COUNT(*) FROM journal_lines
           WHERE company_id=? AND (lawan_transaksi IS NULL OR TRIM(lawan_transaksi)='')
             AND entry_id IN (SELECT id FROM journal_entries
                              WHERE substr(tanggal,1,4)=?)""",
        (company_id, str(tahun))))
    if tanpa_lawan > 0 and jml_jurnal > 0:
        T.append(Temuan(
            tingkat="saran", kategori="Kualitas Data",
            judul=f"{tanpa_lawan} baris jurnal tanpa nama lawan transaksi",
            penjelasan=(
                "Kolom lawan transaksi (nama pelanggan/pemasok) masih kosong. Data ini "
                "penting untuk mencocokkan bukti potong dan faktur pajak."
            ),
            tindakan="Isi nama pelanggan/pemasok beserta NPWP/NIK pada setiap transaksi.",
            dampak="Menyulitkan rekonsiliasi dengan pihak ketiga saat pemeriksaan.",
        ))

    # Aset tetap
    jml_aset = int(db.scalar(
        "SELECT COUNT(*) FROM fixed_assets WHERE company_id=?", (company_id,)))
    if jml_aset == 0:
        T.append(Temuan(
            tingkat="saran", kategori="Aset Tetap",
                halaman="aset",
            judul="Belum ada aset tetap yang didaftarkan",
            penjelasan=(
                "Tidak ada aset tetap tercatat. Bila usaha memiliki peralatan, "
                "kendaraan, atau bangunan, nilainya tidak tercermin di neraca dan "
                "penyusutannya tidak terhitung."
            ),
            tindakan=(
                "Buka menu Aset Tetap dan daftarkan aset beserta tanggal perolehan, "
                "harga, dan kelompok fiskalnya."
            ),
            dampak=(
                "Beban penyusutan tidak terhitung - pajak terutang bisa menjadi lebih "
                "besar dari seharusnya."
            ),
            dasar_hukum="Pasal 11 UU PPh; PMK 72/PMK.03/2023.",
        ))
    else:
        kom = int(db.scalar(
            "SELECT COALESCE(SUM(penyusutan_komersial),0) FROM depreciation_entries "
            "WHERE company_id=? AND tahun=?", (company_id, tahun)))
        fis = int(db.scalar(
            "SELECT COALESCE(SUM(penyusutan_fiskal),0) FROM depreciation_entries "
            "WHERE company_id=? AND tahun=?", (company_id, tahun)))
        if kom == 0 and fis == 0:
            T.append(Temuan(
                tingkat="peringatan", kategori="Aset Tetap",
                halaman="aset",
                judul=f"Penyusutan aset tahun {tahun} belum dihitung",
                penjelasan=(
                    f"Ada {jml_aset} aset tetap terdaftar tetapi belum ada perhitungan "
                    "penyusutan untuk tahun ini."
                ),
                tindakan="Buka menu Aset Tetap dan jalankan proses penyusutan tahunan.",
                dampak=(
                    "Laba menjadi lebih besar dari seharusnya sehingga pajak terutang "
                    "lebih tinggi; neraca juga melebihkan nilai aset."
                ),
                dasar_hukum="Pasal 11 UU PPh; PSAK 16.",
            ))
        else:
            T.append(Temuan(
                tingkat="baik", kategori="Aset Tetap",
                judul="Penyusutan aset tetap sudah dihitung",
                penjelasan=(
                    f"Penyusutan komersial {tx.rupiah(kom)} dan fiskal "
                    f"{tx.rupiah(fis)} telah dihitung untuk tahun {tahun}."
                ),
                tindakan="Periksa konsistensi metode setiap tahun.",
                dasar_hukum="PMK 72/PMK.03/2023.",
            ))

    # Piutang menua
    piutang = sum(v for k, (_, v) in nr.aset_lancar.items()
                  if k in ("1101", "1102"))
    if piutang > 0 and lr.pendapatan_usaha > 0:
        rasio_piutang = piutang / lr.pendapatan_usaha
        if rasio_piutang > 0.5:
            T.append(Temuan(
                tingkat="peringatan", kategori="Kas",
                judul="Piutang menumpuk",
                penjelasan=(
                    f"Piutang {tx.rupiah(piutang)} setara {_persen(rasio_piutang, 0)} dari "
                    "pendapatan setahun. Uang Anda banyak tertahan di pelanggan."
                ),
                tindakan=(
                    "Buat jadwal umur piutang, kirim pengingat bertahap, berikan diskon "
                    "untuk pembayaran cepat, dan tetapkan batas kredit per pelanggan."
                ),
                dampak=(
                    "Risiko piutang tak tertagih. Untuk dapat dibiayakan secara fiskal, "
                    "penghapusan piutang harus memenuhi syarat Pasal 6 UU PPh dan "
                    "dokumen pendukung yang lengkap."
                ),
                angka=f"Piutang {tx.rupiah(piutang)}",
            ))

    # Persediaan besar
    persediaan = sum(v for k, (_, v) in nr.aset_lancar.items() if k.startswith("1104")
                     or k in ("1105", "1106", "1107"))
    if persediaan > 0 and lr.hpp > 0 and persediaan > lr.hpp * 0.6:
        T.append(Temuan(
            tingkat="peringatan", kategori="Kas",
            judul="Persediaan menumpuk",
            penjelasan=(
                f"Persediaan {tx.rupiah(persediaan)} dibanding HPP setahun "
                f"{tx.rupiah(lr.hpp)} - perputaran lambat, modal kerja tertahan."
            ),
            tindakan=(
                "Lakukan stock opname, hitung barang lambat laku, dan pertimbangkan "
                "diskon untuk membersihkan stok lama."
            ),
            dampak="Modal kerja tertahan dan risiko penurunan nilai persediaan.",
            dasar_hukum="PSAK 14 - persediaan diukur pada nilai terendah antara biaya "
                        "perolehan dan nilai realisasi neto.",
        ))

    # Beban pribadi tercampur
    prive = db.scalar(
        """SELECT COALESCE(SUM(jl.debit),0) FROM journal_lines jl
           JOIN journal_entries je ON je.id=jl.entry_id
           JOIN accounts a ON a.company_id=jl.company_id AND a.kode=jl.kode_akun
           WHERE jl.company_id=? AND a.baris_neraca='Prive'
             AND substr(je.tanggal,1,4)=?""", (company_id, str(tahun)))
    if prive > 0 and comp["bentuk"] in ("pt", "pt_perorangan", "koperasi"):
        T.append(Temuan(
            tingkat="peringatan", kategori="Kepatuhan",
            judul="Ada pencatatan prive pada entitas berbentuk badan hukum",
            penjelasan=(
                f"Tercatat penarikan pemilik (prive) {tx.rupiah(prive)}. Pada PT/PT "
                "Perorangan, pengambilan dana oleh pemilik seharusnya diperlakukan "
                "sebagai dividen atau piutang pemegang saham, bukan prive."
            ),
            tindakan=(
                "Revaluasi transaksi ini: bila untuk keperluan pribadi pemilik, "
                "perlakukan sebagai dividen (objek PPh dividen) atau piutang pemegang "
                "saham."
            ),
            dampak=(
                "Salah klasifikasi dapat menyebabkan koreksi fiskal dan sengketa "
                "mengenai sifat pembayaran."
            ),
            dasar_hukum="Pasal 4 ayat (1) UU PPh - dividen sebagai objek pajak.",
        ))

    # Kas/bank bercampur pribadi
    if comp["bentuk"] == "umkm_op":
        T.append(Temuan(
            tingkat="saran", kategori="Kepatuhan",
            judul="Pisahkan rekening usaha dan pribadi",
            penjelasan=(
                "Sebagai usaha perseorangan, Anda satu kesatuan dengan pemiliknya. "
                "Namun untuk pembukuan yang bersih, sebaiknya gunakan rekening "
                "terpisah dan catat setiap penarikan sebagai Prive."
            ),
            tindakan=(
                "Buka rekening khusus usaha, dan setiap pengambilan untuk keperluan "
                "pribadi dicatat ke akun Prive - jangan dicatat sebagai beban usaha."
            ),
            dampak=(
                "Beban pribadi yang dicatat sebagai biaya usaha akan dikoreksi dalam "
                "pemeriksaan pajak (koreksi positif)."
            ),
            dasar_hukum="Pasal 9 ayat (1) huruf a UU PPh - biaya untuk keperluan pribadi "
                        "tidak dapat dikurangkan.",
        ))

    # PPh 21 kelengkapan
    jml_karyawan = int(db.scalar(
        "SELECT COUNT(*) FROM employees WHERE company_id=? AND is_active=1", (company_id,)))
    jml_payroll = int(db.scalar(
        "SELECT COUNT(*) FROM payroll_runs WHERE company_id=? AND substr(masa,1,4)=?",
        (company_id, str(tahun))))
    if jml_karyawan > 0 and jml_payroll == 0:
        T.append(Temuan(
            tingkat="peringatan", kategori="Pajak",
            judul="Ada karyawan tetapi payroll belum dijalankan",
            penjelasan=(
                f"Terdapat {jml_karyawan} karyawan aktif, tetapi belum ada proses "
                f"payroll pada tahun {tahun}."
            ),
            tindakan=(
                "Jalankan payroll setiap bulan. PPh 21 wajib dipotong, disetor "
                "(tanggal 10), dan dilaporkan (tanggal 20) bulan berikutnya."
            ),
            dampak=(
                "Keterlambatan setor dikenai bunga; terlambat lapor dikenai denda "
                "Rp100.000 per SPT Masa."
            ),
            dasar_hukum="Pasal 21 UU PPh; PMK 168/PMK.03/2023; Pasal 7 & 9 UU KUP.",
        ))
    if jml_karyawan == 0:
        T.append(Temuan(
            tingkat="saran", kategori="Pajak",
            judul="Belum ada data karyawan",
            penjelasan=(
                "Tidak ada karyawan terdaftar. Bila Anda mempekerjakan orang lain "
                "(termasuk paruh waktu), PPh 21 tetap harus dihitung dan dilaporkan."
            ),
            tindakan="Daftarkan karyawan pada menu Payroll agar PPh 21 dihitung otomatis.",
            dampak="Kewajiban pemotongan PPh 21 yang tidak dijalankan menimbulkan sanksi.",
            dasar_hukum="Pasal 21 UU PPh.",
        ))

    # ======================================================================
    # 7. REKONSILIASI SUBLEDGER vs JURNAL
    # ======================================================================
    penjualan_sub = int(db.scalar(
        "SELECT COALESCE(SUM(nilai_penjualan),0) FROM sales WHERE company_id=? "
        "AND substr(tanggal,1,4)=?", (company_id, str(tahun))))
    if penjualan_sub > 0 and lr.pendapatan_usaha > 0:
        beda = abs(penjualan_sub - lr.pendapatan_usaha)
        if beda > max(1000, lr.pendapatan_usaha * 0.02):
            T.append(Temuan(
                tingkat="peringatan", kategori="Rekonsiliasi",
                judul="Subledger penjualan tidak cocok dengan jurnal",
                penjelasan=(
                    f"Total penjualan pada subledger {tx.rupiah(penjualan_sub)} berbeda "
                    f"{tx.rupiah(beda)} dari pendapatan usaha pada jurnal "
                    f"{tx.rupiah(lr.pendapatan_usaha)}."
                ),
                tindakan=(
                    "Rekonsiliasi: pastikan semua penjualan pada subledger sudah "
                    "dijurnal, dan tidak ada penjualan yang dijurnal dua kali."
                ),
                dampak=(
                    "PPN keluaran dan perhitungan omzet pajak dapat berbeda dari "
                    "laporan keuangan - berisiko koreksi saat pemeriksaan."
                ),
                dasar_hukum="Pasal 28 UU KUP - pembukuan harus konsisten dan dapat "
                            "diperiksa.",
            ))

    # ======================================================================
    # HITUNG SKOR
    # ======================================================================
    bobot = {"kritis": 15, "peringatan": 6, "saran": 2, "baik": 0}
    penalti = sum(bobot[t.tingkat] for t in T)
    hasil.skor = max(0, min(100, 100 - penalti))

    # Halaman tindak lanjut diisi dari kategorinya bila belum diisi saat
    # temuan dibuat. Dengan begitu setiap temuan pasti menunjuk ke halaman
    # yang tepat, dan tombol aksi cepat pada kartu temuan selalu berguna.
    peta_halaman = {
        "Kas": "kas_bank",
        "Likuiditas": "kas_bank",
        "Rekonsiliasi": "kas_bank",
        "Profitabilitas": "laporan",
        "Solvabilitas": "laporan",
        "Pajak": "pajak",
        "Kepatuhan": "pajak",
        "Aset Tetap": "aset",
        "Pembukuan": "jurnal",
        "Kualitas Data": "jurnal",
    }
    for t in T:
        if not t.halaman:
            t.halaman = peta_halaman.get(t.kategori, "jurnal")

    hasil.temuan = sorted(T, key=lambda t: {"kritis": 0, "peringatan": 1,
                                            "saran": 2, "baik": 3}[t.tingkat])

    s = hasil.skor
    if s >= 85:
        hasil.grade, hasil.grade_label = "A", "Sangat Sehat"
    elif s >= 70:
        hasil.grade, hasil.grade_label = "B", "Sehat"
    elif s >= 55:
        hasil.grade, hasil.grade_label = "C", "Perlu Perbaikan"
    elif s >= 40:
        hasil.grade, hasil.grade_label = "D", "Bermasalah"
    else:
        hasil.grade, hasil.grade_label = "E", "Kritis"

    hasil.ringkasan = _buat_ringkasan(hasil, comp, lr, nr, omzet)
    return hasil


def _saldo_kas(company_id: int, tahun: int, bulan: Optional[int] = None) -> int:
    awal, akhir = acc.periode(tahun, bulan)
    return int(db.scalar(
        """SELECT COALESCE(SUM(a.saldo_awal),0) +
                  COALESCE((SELECT SUM(jl.debit - jl.kredit) FROM journal_lines jl
                            JOIN journal_entries je ON je.id=jl.entry_id
                            WHERE jl.company_id=? AND je.tanggal <= ?
                              AND jl.kode_akun IN (SELECT kode FROM accounts
                                   WHERE company_id=? AND is_kas_bank=1)),0)
           FROM accounts a WHERE a.company_id=? AND a.is_kas_bank=1""",
        (company_id, akhir, company_id, company_id)))


def _buat_ringkasan(hasil: HasilAnalisis, comp, lr, nr, omzet: int) -> str:
    """Narasi ringkas kondisi keuangan dalam bahasa yang mudah dipahami."""
    bagian: list[str] = []

    bagian.append(
        f"Kondisi keuangan {comp['nama']} per periode yang dipilih mendapat skor "
        f"{hasil.skor}/100 ({hasil.grade} - {hasil.grade_label})."
    )

    if omzet > 0:
        bagian.append(
            f"Peredaran bruto tercatat {tx.rupiah(omzet)} "
            f"({_persen(omzet / config.THRESHOLD_PKP, 1)} dari batas wajib PKP "
            f"Rp4,8 miliar)."
        )
    if lr.pendapatan_usaha > 0:
        status = "laba" if lr.laba_bersih >= 0 else "rugi"
        bagian.append(
            f"Dari pendapatan {tx.rupiah(lr.pendapatan_usaha)}, usaha mencatat "
            f"{status} bersih {tx.rupiah(abs(lr.laba_bersih))} "
            f"(margin {_persen(lr.margin_bersih, 1)})."
        )
    bagian.append(
        f"Total aset {tx.rupiah(nr.total_aset)} dengan liabilitas "
        f"{tx.rupiah(nr.total_liabilitas)} dan ekuitas {tx.rupiah(nr.total_ekuitas)}."
    )

    kritis, peringatan = hasil.jumlah_kritis, hasil.jumlah_peringatan
    if kritis:
        bagian.append(
            f"Ada {kritis} temuan KRITIS yang perlu segera ditindaklanjuti"
            + (f" dan {peringatan} peringatan." if peringatan else ".")
        )
    elif peringatan:
        bagian.append(
            f"Ada {peringatan} hal yang perlu diperhatikan, tetapi tidak ada temuan kritis."
        )
    else:
        bagian.append("Tidak ditemukan masalah kritis maupun peringatan. Pembukuan Anda rapi.")

    if hasil.skor < 70:
        bagian.append(
            "Prioritaskan perbaikan pada temuan berlabel KRITIS terlebih dahulu "
            "biasanya masalah pembukuan harus dibenahi sebelum analisis lainnya bermakna."
        )
    return " ".join(bagian)


# ==========================================================================
# DEADLINE PAJAK
# ==========================================================================
def cek_deadline(company_id: int, sudah_pkp: bool = False,
                 referensi: Optional[date] = None) -> list[dict]:
    """
    Hitung tenggat setor/lapor terdekat.
    Tenggat mengikuti aturan umum UU KUP (belum memperhitungkan pergeseran
    hari libur - periksa kalender resmi DJP untuk kepastian).
    """
    hari_ini = referensi or date.today()
    hasil: list[dict] = []

    def tambah(kode, nama, tenggat: date, masa: str, sanksi: str, dasar: str):
        hasil.append({
            "kode": kode, "nama": nama, "tenggat": tenggat.isoformat(),
            "masa": masa, "hari_tersisa": (tenggat - hari_ini).days,
            "sanksi": sanksi, "dasar_hukum": dasar,
        })

    # Masa pajak bulan lalu
    if hari_ini.month == 1:
        bulan_lalu, tahun_lalu = 12, hari_ini.year - 1
    else:
        bulan_lalu, tahun_lalu = hari_ini.month - 1, hari_ini.year
    masa_label = f"{config.MONTH_NAMES_ID[bulan_lalu - 1]} {tahun_lalu}"

    bulan_depan = hari_ini.month % 12 + 1
    tahun_depan = hari_ini.year + (1 if hari_ini.month == 12 else 0)

    # Akhir bulan berikutnya setelah masa pajak berakhir = akhir bulan ini
    if hari_ini.month == 12:
        akhir_bulan = date(hari_ini.year, 12, 31)
    else:
        nxt = date(hari_ini.year, hari_ini.month + 1, 1)
        akhir_bulan = date.fromordinal(nxt.toordinal() - 1)

    if sudah_pkp:
        tambah("ppn_lapor", "Lapor & Setor SPT Masa PPN", akhir_bulan, masa_label,
               "Denda Rp100.000 + bunga keterlambatan setor.",
               "Pasal 3 ayat (3) huruf b & Pasal 9 UU KUP; PMK 81/2024")

    tgl10 = date(tahun_depan, bulan_depan, 10)
    tgl15 = date(tahun_depan, bulan_depan, 15)
    tgl20 = date(tahun_depan, bulan_depan, 20)

    tambah("pph21_setor", "Setor PPh 21", tgl10, masa_label,
           "Bunga keterlambatan: suku bunga acuan + 10% dibagi 12 per bulan.",
           "Pasal 9 UU KUP jo. UU HPP; PMK 81/2024")
    tambah("pph21_lapor", "Lapor SPT Masa PPh 21", tgl20, masa_label,
           "Denda Rp100.000 per SPT Masa.", "Pasal 7 UU KUP")
    tambah("pph23_setor", "Setor PPh 23/26", tgl10, masa_label,
           "Bunga keterlambatan per bulan.", "Pasal 9 UU KUP")
    tambah("pph23_lapor", "Lapor SPT Masa PPh 23/26", tgl20, masa_label,
           "Denda Rp100.000 per SPT Masa.", "Pasal 7 UU KUP")
    tambah("pph4_setor", "Setor PPh 4(2) & PPh Final", tgl10, masa_label,
           "Bunga keterlambatan per bulan.", "Pasal 9 UU KUP")
    tambah("pph25_setor", "Setor Angsuran PPh 25", tgl15, masa_label,
           "Bunga keterlambatan per bulan.", "Pasal 25 UU PPh; Pasal 9 UU KUP")

    # SPT Tahunan
    spt_badan = date(hari_ini.year + 1, 4, 30)
    tambah("spt_badan", "Lapor SPT Tahunan PPh Badan", spt_badan, str(hari_ini.year),
           "Denda Rp1.000.000.", "Pasal 3 ayat (3) huruf a & Pasal 7 UU KUP")

    hasil.sort(key=lambda x: x["hari_tersisa"])
    return hasil


# ==========================================================================
# PROYEKSI & SIMULASI
# ==========================================================================
def proyeksi_sederhana(company_id: int, tahun: int) -> dict:
    """
    Proyeksi sederhana berdasarkan rata-rata bulanan tahun berjalan.
    Membantu pemilik usaha melihat arah ke depan.
    """
    rb = acc.ringkasan_bulanan(company_id, tahun)
    bulan_berjalan = datetime.now().month if datetime.now().year == tahun else 12
    aktif = [b for b in rb[:bulan_berjalan] if b["pendapatan"] > 0 or b["beban"] > 0]
    n = len(aktif) or 1

    rata_pendapatan = sum(b["pendapatan"] for b in aktif) // n
    rata_beban = sum(b["beban"] + b["hpp"] for b in aktif) // n
    rata_laba = rata_pendapatan - rata_beban

    proyeksi_pendapatan = rata_pendapatan * 12
    proyeksi_laba = rata_laba * 12
    omzet_berjalan = acc.omzet_setahun(company_id, tahun)

    # Perkiraan kapan melewati batas PKP
    bulan_ke_batas = None
    if rata_pendapatan > 0 and omzet_berjalan < config.THRESHOLD_PKP:
        sisa = config.THRESHOLD_PKP - omzet_berjalan
        bulan_ke_batas = int(sisa / rata_pendapatan) + 1

    return {
        "bulan_data": n,
        "rata_pendapatan_bulanan": rata_pendapatan,
        "rata_beban_bulanan": rata_beban,
        "rata_laba_bulanan": rata_laba,
        "proyeksi_pendapatan_tahun": proyeksi_pendapatan,
        "proyeksi_laba_tahun": proyeksi_laba,
        "omzet_saat_ini": omzet_berjalan,
        "bulan_ke_batas_pkp": bulan_ke_batas,
        "catatan": (
            "Proyeksi dihitung dari rata-rata bulan yang sudah ada datanya. "
            "Semakin banyak bulan tercatat, semakin akurat proyeksinya."
        ),
    }


def simulasi_skenario(company_id: int, tahun: int,
                      perubahan_pendapatan_pct: float = 0.0,
                      perubahan_beban_pct: float = 0.0) -> dict:
    """
    Simulasi 'bagaimana jika': dampak perubahan pendapatan/beban terhadap laba
    dan pajak. Berguna untuk perencanaan sebelum mengambil keputusan.
    """
    comp = db.q1("SELECT * FROM companies WHERE id=?", (company_id,))
    lr = acc.laba_rugi(company_id, tahun, beban_pajak=0)

    pendapatan_baru = int(lr.pendapatan_usaha * (1 + perubahan_pendapatan_pct / 100))
    beban_baru = int((lr.hpp + lr.beban_operasional) * (1 + perubahan_beban_pct / 100))
    laba_baru = pendapatan_baru - beban_baru + lr.pendapatan_lain - lr.beban_lain

    skema_final = bool(comp and comp["skema_pph"] == "final_umkm" and comp["final_eligible"])
    if skema_final:
        pajak = int(round(min(pendapatan_baru, config.THRESHOLD_PKP) * config.RATE_FINAL_UMKM))
        skema = "PPh Final 0,5%"
    else:
        r = tx.hitung_pph_badan(omzet=pendapatan_baru, pkp=max(0, laba_baru))
        pajak = r.pph_terutang
        skema = r.skema

    return {
        "pendapatan_sekarang": lr.pendapatan_usaha,
        "pendapatan_baru": pendapatan_baru,
        "beban_sekarang": lr.hpp + lr.beban_operasional,
        "beban_baru": beban_baru,
        "laba_sekarang": lr.laba_sebelum_pajak,
        "laba_baru": laba_baru,
        "selisih_laba": laba_baru - lr.laba_sebelum_pajak,
        "pajak_sekarang": acc.estimasi_beban_pajak(company_id, tahun, lr.laba_sebelum_pajak),
        "pajak_baru": pajak,
        "skema": skema,
        "laba_setelah_pajak": laba_baru - pajak,
    }
