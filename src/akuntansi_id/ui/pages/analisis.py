"""
AkunTuntas - Halaman Analisis Kesehatan Keuangan (Lengkap)
===========================================================
Menampilkan seluruh temuan analisis, rasio keuangan, simulasi skenario,
dan rekomendasi tindakan.
"""
from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QFrame,
    QGridLayout, QSizePolicy, QTabWidget, QTableWidgetItem, QPushButton,
)

from ... import services
from ...core.analyzer import _rasio
from .. import theme
from ..theme import C
from .. import widgets as w


class AnalisisPage(QWidget):
    pindah_halaman = Signal(str)

    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx

        luar = QVBoxLayout(self)
        luar.setContentsMargins(0, 0, 0, 0)
        luar.setSpacing(0)

        self.header = w.PageHeader(
            "Analisis Kesehatan Keuangan",
            "Diagnosis otomatis kondisi usaha beserta tindakan yang perlu dilakukan.")

        self.cmb_tahun = QComboBox()
        tk = datetime.now().year
        for t in range(tk - 3, tk + 2):
            self.cmb_tahun.addItem(str(t), t)
        idx = self.cmb_tahun.findData(ctx.tahun)
        if idx >= 0:
            self.cmb_tahun.setCurrentIndex(idx)
        self.cmb_tahun.currentIndexChanged.connect(self._ganti_tahun)
        self.cmb_tahun.setMinimumWidth(105)
        self.header.tambah_aksi(self.cmb_tahun)

        btn = w.tombol("Muat Ulang", ikon="segarkan")
        btn.clicked.connect(self.muat)
        self.header.tambah_aksi(btn)

        # Ekspor dan cetak memakai jalur yang sama dengan halaman lain,
        # sehingga hasil analisis dapat disimpan atau dilampirkan ke
        # laporan tanpa harus difoto layar.
        self.header.pasang_ekspor_cetak(self, "Analisis Kesehatan Keuangan")

        kepala = QWidget()
        theme.latar(kepala, f"background: {C.SURFACE}; "
                             f"border-bottom: 1px solid {C.BORDER};")
        kl = QVBoxLayout(kepala)
        kl.setContentsMargins(26, 20, 26, 18)
        kl.addWidget(self.header)
        luar.addWidget(kepala)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        wadah = QWidget()
        wl = QVBoxLayout(wadah)
        wl.setContentsMargins(22, 18, 22, 22)
        wl.addWidget(self.tabs)
        luar.addWidget(wadah, 1)

        # setiap tab dibungkus area gulir agar temuan panjang tetap terbaca
        self.tab_temuan = QWidget()
        self.tab_rasio = QWidget()
        self.tab_simulasi = QWidget()
        for isi, judul in ((self.tab_temuan, "Temuan && Rekomendasi"),
                           (self.tab_rasio, "Rasio Keuangan"),
                           (self.tab_simulasi, "Simulasi Skenario")):
            l = QVBoxLayout(isi)
            l.setContentsMargins(0, 14, 12, 14)
            l.setSpacing(12)
            self.tabs.addTab(w.scroll(isi), judul)

    def _ganti_tahun(self):
        self.ctx.tahun = self.cmb_tahun.currentData()
        self.muat()

    # ------------------------------------------------------------------
    def muat(self):
        self._bersihkan(self.tab_temuan)
        self._bersihkan(self.tab_rasio)
        self._bersihkan(self.tab_simulasi)

        cid, tahun = self.ctx.company_id, self.ctx.tahun
        if not cid:
            self.tab_temuan.layout().addWidget(w.InfoBanner(
                "Belum ada perusahaan. Buat profil perusahaan terlebih dahulu.",
                "warning", "Data belum tersedia"))
            return

        comp = services.get_company(cid)
        self.header.set_subjudul(
            f"{comp['nama']} · Analisis tahun {tahun}")

        try:
            a = services.analisis(cid, tahun)
        except Exception as e:
            self.tab_temuan.layout().addWidget(w.InfoBanner(
                f"Gagal menjalankan analisis: {e}", "danger", "Kesalahan"))
            return

        self._isi_temuan(a)
        self._isi_rasio(a, comp)
        self._isi_simulasi(cid, tahun)

    def _bersihkan(self, widget: QWidget):
        lay = widget.layout()
        while lay.count():
            item = lay.takeAt(0)
            wdg = item.widget()
            if wdg is not None:
                wdg.setParent(None)
                wdg.deleteLater()
            elif item.layout():
                self._bersihkan_layout(item.layout())

    def _bersihkan_layout(self, lay):
        while lay.count():
            item = lay.takeAt(0)
            wdg = item.widget()
            if wdg is not None:
                wdg.setParent(None)
                wdg.deleteLater()
            elif item.layout():
                self._bersihkan_layout(item.layout())

    # ==================================================================
    # TAB 1: TEMUAN
    # ==================================================================
    def _isi_temuan(self, a):
        lay = self.tab_temuan.layout()

        # ringkasan atas
        atas = w.Card()
        al = atas.ganti_isi(QHBoxLayout())
        al.setContentsMargins(22, 18, 22, 18)
        al.setSpacing(24)

        gauge = w.SkorGauge(ukuran=132)
        gauge.set_skor(a.skor, a.grade_label)
        al.addWidget(gauge)

        kanan = QVBoxLayout()
        kanan.setSpacing(7)
        j = QLabel("Ringkasan Diagnosis")
        j.setObjectName("SectionTitle")
        kanan.addWidget(j)
        r = QLabel(a.ringkasan)
        r.setWordWrap(True)
        r.setStyleSheet(f"font-size: {theme.FS_BODY}px; line-height: 155%; "
                        "background: transparent;")
        kanan.addWidget(r)

        # Laba besar dengan kas negatif sering tampak seperti salah hitung,
        # padahal wajar bila penjualan masih berupa piutang. Keterangan ini
        # hanya muncul saat keadaannya memang begitu.
        laba = a.rasio.get("laba_bersih", 0)
        kas = a.rasio.get("kas", 0)
        if laba > 0 and kas < 0:
            catatan = QLabel(
                "Laba dan kas berbeda karena penjualan yang belum dibayar "
                "tidak menambah uang di rekening. Laba dihitung saat "
                "transaksi terjadi, sedangkan kas bertambah saat uangnya "
                "benar benar masuk. Karena itu usaha bisa mencetak laba "
                "namun uang tunainya kurang. Tagih piutang yang jatuh tempo "
                "untuk menutup selisih ini.")
            catatan.setWordWrap(True)
            theme.latar(catatan,
                        f"color: {C.TEXT_MUTED}; font-size: {theme.FS_SMALL}px; "
                        f"background: {C.INFO_BG}; border-radius: 8px; "
                        "padding: 10px 12px;")
            kanan.addWidget(catatan)

        st = QHBoxLayout()
        st.setSpacing(9)
        for jumlah, label, tingkat in [
            (a.jumlah_kritis, "KRITIS", "kritis"),
            (a.jumlah_peringatan, "PERHATIAN", "peringatan"),
            (a.jumlah_saran, "SARAN", "saran"),
            (a.jumlah_baik, "BAIK", "baik"),
        ]:
            warna, bg = theme.STATUS_COLORS[tingkat]
            chip = QLabel(f"<b style='font-size:17px'>{jumlah}</b><br>"
                          f"<span style='font-size:9px'>{label}</span>")
            chip.setTextFormat(Qt.RichText)
            chip.setAlignment(Qt.AlignCenter)
            theme.latar(chip, f"background: {bg}; color: {warna}; "
                               "border-radius: 8px; padding: 7px 16px;")
            chip.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
            chip.setMinimumWidth(chip.sizeHint().width())
            st.addWidget(chip)
        st.addStretch()
        kanan.addLayout(st)
        al.addLayout(kanan, 1)
        lay.addWidget(atas)

        # temuan per tingkat
        urutan = [("kritis", " Temuan Kritis - Perlu Tindakan Segera"),
                  ("peringatan", " Perlu Perhatian"),
                  ("saran", " Saran Perbaikan"),
                  ("baik", " Kondisi Baik")]

        # Penyaring tingkat temuan. Bila temuan bertambah banyak, pengguna
        # dapat memusatkan perhatian pada satu tingkat saja tanpa harus
        # menggulir seluruh daftar.
        jumlah_per_tingkat = {
            "semua": len(a.temuan),
            "kritis": a.jumlah_kritis,
            "peringatan": a.jumlah_peringatan,
            "saran": a.jumlah_saran,
            "baik": a.jumlah_baik,
        }
        ada_pilihan = sum(1 for t, _ in urutan if jumlah_per_tingkat[t] > 0)
        self._saring = "semua"
        self._kotak_temuan: list = []

        if ada_pilihan > 1:
            baris_saring = QHBoxLayout()
            baris_saring.setSpacing(8)

            lbl_saring = QLabel("Tampilkan:")
            lbl_saring.setStyleSheet(
                f"color: {C.TEXT_MUTED}; font-size: {theme.FS_SMALL}px; "
                "background: transparent;")
            baris_saring.addWidget(lbl_saring)

            self._tombol_saring: dict = {}
            for kunci, teks in (("semua", "Semua"),
                                ("kritis", "Kritis"),
                                ("peringatan", "Perhatian"),
                                ("saran", "Saran"),
                                ("baik", "Baik")):
                jumlah = jumlah_per_tingkat.get(kunci, 0)
                if kunci != "semua" and jumlah == 0:
                    continue
                b = QPushButton(f"{teks} ({jumlah})")
                b.setCheckable(True)
                b.setChecked(kunci == "semua")
                b.setCursor(Qt.PointingHandCursor)
                b.clicked.connect(
                    lambda _=False, k=kunci: self._saring_temuan(k))
                # Tombol yang sedang dipakai diberi warna tegas, sedangkan
                # yang tidak dipakai dibuat netral. Seluruh keadaan ditulis
                # lengkap supaya gaya umum QPushButton pada theme.py tidak
                # menimpanya, dan warna hurufnya disebut ulang pada keadaan
                # :checked agar teksnya tetap terbaca di atas latar biru.
                b.setStyleSheet(f"""
                    QPushButton {{
                        padding: 7px 15px;
                        border-radius: 8px;
                        border: 1px solid {C.BORDER};
                        background: {C.SURFACE};
                        color: {C.TEXT_MUTED};
                        font-size: {theme.FS_SMALL}px;
                        font-weight: 600;
                    }}
                    QPushButton:hover {{
                        background: {C.SURFACE_ALT};
                        border-color: {C.PRIMARY};
                        color: {C.PRIMARY_DARK};
                    }}
                    QPushButton:pressed {{
                        background: {C.NEUTRAL_BG};
                        color: {C.TEXT};
                    }}
                    QPushButton:checked {{
                        background: {C.PRIMARY};
                        border-color: {C.PRIMARY};
                        color: {C.TEXT_INVERSE};
                    }}
                    QPushButton:checked:hover {{
                        background: {C.PRIMARY_DARK};
                        border-color: {C.PRIMARY_DARK};
                        color: {C.TEXT_INVERSE};
                    }}
                """)
                baris_saring.addWidget(b)
                self._tombol_saring[kunci] = b

            baris_saring.addStretch()
            lay.addLayout(baris_saring)

        for tingkat, judul in urutan:
            grup = [t for t in a.temuan if t.tingkat == tingkat]
            if not grup:
                continue
            kepala_seksi = self._judul_seksi(judul, len(grup))
            lay.addWidget(kepala_seksi)

            kartu_tingkat = []
            for t in grup:
                kartu = w.TemuanCard(
                    t, buka_halaman=self._buka_halaman_temuan)
                lay.addWidget(kartu)
                kartu_tingkat.append(kartu)
            self._kotak_temuan.append((tingkat, kepala_seksi, kartu_tingkat))

        if not a.temuan:
            lay.addWidget(w.InfoBanner(
                "Tidak ada temuan. Pembukuan Anda dalam kondisi baik.",
                "ok", "Semua pemeriksaan terlewati"))

        lay.addStretch()

    def _buka_halaman_temuan(self, kode: str):
        """Buka halaman yang berkaitan dengan temuan yang sedang dibaca."""
        if kode:
            self.pindah_halaman.emit(kode)

    def _saring_temuan(self, tingkat: str):
        """Tampilkan hanya temuan pada tingkat yang dipilih."""
        self._saring = tingkat

        for kunci, tombol in getattr(self, "_tombol_saring", {}).items():
            tombol.setChecked(kunci == tingkat)

        for tkt, kepala, kartu_list in getattr(self, "_kotak_temuan", []):
            tampil = tingkat == "semua" or tkt == tingkat
            kepala.setVisible(tampil)
            for kartu in kartu_list:
                kartu.setVisible(tampil)

    def _judul_seksi(self, judul: str, jumlah: int) -> QWidget:
        wdg = QWidget()
        l = QHBoxLayout(wdg)
        l.setContentsMargins(0, 14, 0, 2)
        l.setSpacing(9)
        t = QLabel(judul)
        t.setStyleSheet("font-size: 15px; font-weight: 700; background: transparent;")
        l.addWidget(t)
        b = QLabel(str(jumlah))
        theme.latar(b, f"background: {C.NEUTRAL_BG}; color: {C.TEXT_MUTED}; "
                        "border-radius: 9px; padding: 2px 9px; "
                        f"font-size: {theme.FS_TINY}px; font-weight: 700;")
        b.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        b.setMinimumWidth(b.sizeHint().width())
        l.addWidget(b)
        l.addStretch()
        return wdg

    # ==================================================================
    # TAB 2: RASIO
    # ==================================================================
    def _isi_rasio(self, a, comp):
        lay = self.tab_rasio.layout()
        r = a.rasio
        st = a.statistik

        lay.addWidget(w.InfoBanner(
            "Rasio keuangan membantu Anda menilai kondisi usaha secara cepat. "
            "Setiap rasio dibandingkan dengan acuan umum untuk usaha kecil di Indonesia. "
            "Rasio bukan penilaian mutlak - tetap perhatikan konteks industri Anda.",
            "info", "Cara membaca rasio"))

        # Pada mode Pemula, istilah rasio keuangan dijelaskan lebih dahulu
        # dengan bahasa sehari hari. Pengguna yang sudah terbiasa dapat
        # menutup keterangan ini.
        if getattr(self.ctx, "beginner", False):
            penjelasan = w.Card()
            pl = penjelasan.body()
            judul_p = QLabel("Arti istilah rasio dalam bahasa sehari hari")
            judul_p.setObjectName("SectionTitle")
            pl.addWidget(judul_p)

            for istilah, arti in (
                ("Rasio lancar",
                 "Berapa kali aset jangka pendek Anda menutup utang jangka "
                 "pendek. Di atas 1,5x berarti aman."),
                ("Rasio kas",
                 "Seberapa besar uang tunai Anda dibanding utang jangka "
                 "pendek. Bila negatif, artinya saldo kas Anda minus."),
                ("Margin",
                 "Sisa laba dari setiap penjualan setelah dikurangi biaya. "
                 "Margin 20% berarti dari Rp100 penjualan tersisa Rp20."),
                ("ROA dan ROE",
                 "Seberapa besar laba yang dihasilkan dari aset dan dari "
                 "modal sendiri. Semakin besar semakin baik."),
                ("Rasio utang",
                 "Seberapa besar usaha Anda bergantung pada utang. Semakin "
                 "kecil semakin aman."),
            ):
                baris_p = QHBoxLayout()
                baris_p.setSpacing(10)
                nama_p = QLabel(istilah)
                nama_p.setFixedWidth(110)
                nama_p.setStyleSheet(
                    f"color: {C.TEXT}; font-size: {theme.FS_SMALL}px; "
                    "font-weight: 600; background: transparent;")
                baris_p.addWidget(nama_p, 0)
                arti_p = QLabel(arti)
                arti_p.setWordWrap(True)
                arti_p.setStyleSheet(
                    f"color: {C.TEXT_MUTED}; font-size: {theme.FS_SMALL}px; "
                    "background: transparent;")
                baris_p.addWidget(arti_p, 1)
                pl.addLayout(baris_p)

            lay.addWidget(penjelasan)

        # --- Likuiditas
        lay.addWidget(self._judul_seksi("Likuiditas - kemampuan membayar utang jangka pendek", 0))
        kartu = w.Card()
        grid = QGridLayout()
        grid.setSpacing(16)

        rasio_lancar = r["rasio_lancar"]
        teks_rl = ("Tidak ada utang jangka pendek" if rasio_lancar == float("inf")
                   else f"{_rasio(rasio_lancar, 2)}")
        status_rl, warna_rl = self._nilai_rasio(
            rasio_lancar, baik=2.0, cukup=1.5, bahaya=1.0, teks=teks_rl,
            terbalik=True, maks=1.0)
        grid.addWidget(self._kotak_rasio(
            "Rasio Lancar", teks_rl, status_rl, warna_rl,
            "Aset lancar ÷ utang jangka pendek. Mengukur kemampuan membayar "
            "kewajiban dalam 12 bulan. Acuan sehat: di atas 1,5x."), 0, 0)

        rasio_kas = r["rasio_kas"]
        teks_rk = ("Tidak ada utang jangka pendek" if rasio_kas == float("inf")
                   else f"{_rasio(rasio_kas, 2)}")
        status_rk, warna_rk = self._nilai_rasio(
            rasio_kas, baik=1.0, cukup=0.5, bahaya=0.25, teks=teks_rk,
            terbalik=True, maks=0.0)
        grid.addWidget(self._kotak_rasio(
            "Rasio Kas", teks_rk, status_rk, warna_rk,
            "Kas ÷ utang jangka pendek. Mengukur kemampuan membayar utang "
            "segera dengan uang tunai yang tersedia. Acuan sehat: di atas "
            "0,50x. Nilai negatif berarti kas Anda minus."), 0, 1)
        kartu.body().addLayout(grid)
        lay.addWidget(kartu)

        # --- Profitabilitas
        lay.addWidget(self._judul_seksi("Profitabilitas - kemampuan menghasilkan laba", 0))
        kartu2 = w.Card()
        grid2 = QGridLayout()
        grid2.setSpacing(16)

        mk = r["margin_kotor"]
        s, wrn = self._nilai_rasio(mk, baik=0.30, cukup=0.20, bahaya=0.10,
                                   teks=theme.persen(mk), terbalik=True)
        grid2.addWidget(self._kotak_rasio(
            "Margin Kotor", theme.persen(mk), s, wrn,
            "(Pendapatan − HPP) ÷ Pendapatan. Menunjukkan efisiensi harga jual "
            "dan biaya produksi. Acuan sehat: di atas 30%."), 0, 0)

        mo = r["margin_operasional"]
        s, wrn = self._nilai_rasio(mo, baik=0.15, cukup=0.08, bahaya=0.02,
                                   teks=theme.persen(mo), terbalik=True)
        grid2.addWidget(self._kotak_rasio(
            "Margin Operasional", theme.persen(mo), s, wrn,
            "Laba operasional ÷ Pendapatan. Menunjukkan laba sebelum pajak dan "
            "pos non-operasional."), 0, 1)

        mb = r["margin_bersih"]
        s, wrn = self._nilai_rasio(mb, baik=0.10, cukup=0.04, bahaya=0.0,
                                   teks=theme.persen(mb), terbalik=True)
        grid2.addWidget(self._kotak_rasio(
            "Margin Bersih", theme.persen(mb), s, wrn,
            "Laba bersih ÷ Pendapatan. Dari setiap Rp100 penjualan, berapa yang "
            "menjadi laba bersih."), 1, 0)

        roa = r["roa"]
        s, wrn = self._nilai_rasio(roa, baik=0.10, cukup=0.04, bahaya=0.0,
                                   teks=theme.persen(roa), terbalik=True)
        grid2.addWidget(self._kotak_rasio(
            "ROA (Return on Assets)", theme.persen(roa), s, wrn,
            "Laba bersih ÷ Total aset. Seberapa efisien aset menghasilkan laba."), 1, 1)
        kartu2.body().addLayout(grid2)
        lay.addWidget(kartu2)

        # --- Solvabilitas
        lay.addWidget(self._judul_seksi("Solvabilitas - struktur pendanaan", 0))
        kartu3 = w.Card()
        grid3 = QGridLayout()
        grid3.setSpacing(16)

        der = r["rasio_utang_ekuitas"]
        teks_der = ("Tidak ada utang" if der == 0 else
                    ("Ekuitas negatif" if der == float("inf") else f"{_rasio(der, 2)}"))
        s, wrn = self._nilai_rasio(der, baik=0.5, cukup=1.5, bahaya=3.0,
                                   teks=teks_der)
        grid3.addWidget(self._kotak_rasio(
            "Rasio Utang terhadap Ekuitas", teks_der, s, wrn,
            "Total utang ÷ Ekuitas. Mengukur ketergantungan pada utang. "
            "Acuan sehat: di bawah 1,5x. Di atas 3x berisiko tinggi."), 0, 0)

        roe = r["roe"]
        s, wrn = self._nilai_rasio(roe, baik=0.15, cukup=0.08, bahaya=0.0,
                                   teks=theme.persen(roe), terbalik=True)
        grid3.addWidget(self._kotak_rasio(
            "ROE (Return on Equity)", theme.persen(roe), s, wrn,
            "Laba bersih ÷ Ekuitas. Imbal hasil bagi pemilik atas modal yang "
            "ditanamkan."), 0, 1)

        rua = r["rasio_utang_aset"]
        s, wrn = self._nilai_rasio(rua, baik=0.3, cukup=0.6, bahaya=0.8,
                                   teks=theme.persen(rua))
        grid3.addWidget(self._kotak_rasio(
            "Rasio Utang terhadap Aset", theme.persen(rua), s, wrn,
            "Total utang ÷ Total aset. Berapa bagian aset yang dibiayai utang."), 1, 0)

        beban_rasio = r["beban_terhadap_pendapatan"]
        s, wrn = self._nilai_rasio(beban_rasio, baik=0.75, cukup=0.9, bahaya=1.0,
                                   teks=theme.persen(beban_rasio))
        grid3.addWidget(self._kotak_rasio(
            "Beban terhadap Pendapatan", theme.persen(beban_rasio), s, wrn,
            "(HPP + Beban) ÷ Pendapatan. Semakin rendah semakin efisien. "
            "Di atas 95% hampir tidak ada sisa laba."), 1, 1)
        kartu3.body().addLayout(grid3)
        lay.addWidget(kartu3)

        # --- Data pendukung
        lay.addWidget(self._judul_seksi("Data Pendukung", 0))
        kartu4 = w.Card()
        baris = QHBoxLayout()
        baris.setSpacing(30)
        baris.addWidget(w.MiniStat("Omzet", theme.money(st["omzet"])))
        baris.addWidget(w.MiniStat("Laba Bersih", theme.money(st["laba_bersih"]),
                                   C.POSITIF if st["laba_bersih"] >= 0 else C.NEGATIF))
        baris.addWidget(w.MiniStat("Total Aset", theme.money(st["total_aset"])))
        baris.addWidget(w.MiniStat("Liabilitas", theme.money(st["total_liabilitas"])))
        baris.addWidget(w.MiniStat("Ekuitas", theme.money(st["total_ekuitas"])))
        baris.addStretch()
        kartu4.body().addLayout(baris)

        baris2 = QHBoxLayout()
        baris2.setSpacing(30)
        baris2.addWidget(w.MiniStat("Jumlah Jurnal", str(st["jumlah_jurnal_total"])))
        baris2.addWidget(w.MiniStat("Jumlah Akun", str(st["jumlah_akun"])))
        baris2.addWidget(w.MiniStat(
            "Selisih Jurnal", theme.money(st["selisih_jurnal"]),
            C.NEGATIF if abs(st["selisih_jurnal"]) > 0.5 else C.POSITIF))
        baris2.addWidget(w.MiniStat(
            "Selisih Neraca", theme.money(st["selisih_neraca"]),
            C.NEGATIF if abs(st["selisih_neraca"]) >= 1 else C.POSITIF))
        baris2.addStretch()
        kartu4.body().addLayout(baris2)
        lay.addWidget(kartu4)

        # ------------------------------------------------------------
        # Tabel ringkas seluruh rasio. Berguna untuk dua hal: pengunjung
        # dapat melihat seluruh rasio sekaligus dalam satu pandangan, dan
        # tombol Ekspor pada kepala halaman memakai tabel ini sebagai
        # sumber datanya.
        # ------------------------------------------------------------
        lay.addWidget(self._judul_seksi(
            "Ringkasan Seluruh Rasio", 0))
        lay.addWidget(self._tabel_rasio(r))

        lay.addStretch()

    def _tabel_rasio(self, r) -> QWidget:
        """Tabel seluruh rasio beserta nilainya, status, dan acuannya."""
        kartu = w.Card()

        def baris_rasio(nama, nilai, status, warna, acuan):
            return nama, nilai, status, warna, acuan

        daftar = []

        rl = r["rasio_lancar"]
        t = ("Tidak ada utang jangka pendek" if rl == float("inf")
             else f"{_rasio(rl, 2)}")
        s, wrn = self._nilai_rasio(rl, baik=2.0, cukup=1.5, bahaya=1.0, teks=t,
                                   terbalik=True, maks=1.0)
        daftar.append(baris_rasio("Rasio Lancar", t, s, wrn,
                                  "di atas 1,50x"))

        rk = r["rasio_kas"]
        t = ("Tidak ada utang jangka pendek" if rk == float("inf")
             else f"{_rasio(rk, 2)}")
        s, wrn = self._nilai_rasio(rk, baik=1.0, cukup=0.5, bahaya=0.25, teks=t,
                                   terbalik=True, maks=0.0)
        daftar.append(baris_rasio("Rasio Kas", t, s, wrn, "di atas 1,00x"))

        mk = r["margin_kotor"]
        s, wrn = self._nilai_rasio(mk, baik=0.30, cukup=0.20, bahaya=0.10,
                                   teks=theme.persen(mk), terbalik=True)
        daftar.append(baris_rasio("Margin Kotor", theme.persen(mk), s, wrn,
                                  "di atas 30%"))

        mo = r["margin_operasional"]
        s, wrn = self._nilai_rasio(mo, baik=0.15, cukup=0.08, bahaya=0.02,
                                   teks=theme.persen(mo), terbalik=True)
        daftar.append(baris_rasio("Margin Operasional", theme.persen(mo),
                                  s, wrn, "di atas 15%"))

        mb = r["margin_bersih"]
        s, wrn = self._nilai_rasio(mb, baik=0.10, cukup=0.04, bahaya=0.0,
                                   teks=theme.persen(mb), terbalik=True)
        daftar.append(baris_rasio("Margin Bersih", theme.persen(mb), s, wrn,
                                  "di atas 10%"))

        roa = r["roa"]
        s, wrn = self._nilai_rasio(roa, baik=0.10, cukup=0.04, bahaya=0.0,
                                   teks=theme.persen(roa), terbalik=True)
        daftar.append(baris_rasio("ROA", theme.persen(roa), s, wrn,
                                  "di atas 10%"))

        der = r["rasio_utang_ekuitas"]
        t = ("Tidak ada utang" if der == 0 else
             ("Ekuitas negatif" if der == float("inf") else f"{_rasio(der, 2)}"))
        s, wrn = self._nilai_rasio(der, baik=0.5, cukup=1.5, bahaya=3.0, teks=t)
        daftar.append(baris_rasio("Rasio Utang terhadap Ekuitas", t, s, wrn,
                                  "di bawah 1,50x"))

        roe = r["roe"]
        s, wrn = self._nilai_rasio(roe, baik=0.15, cukup=0.08, bahaya=0.0,
                                   teks=theme.persen(roe), terbalik=True)
        daftar.append(baris_rasio("ROE", theme.persen(roe), s, wrn,
                                  "di atas 15%"))

        rua = r["rasio_utang_aset"]
        s, wrn = self._nilai_rasio(rua, baik=0.3, cukup=0.6, bahaya=0.8,
                                   teks=theme.persen(rua))
        daftar.append(baris_rasio("Rasio Utang terhadap Aset",
                                  theme.persen(rua), s, wrn, "di bawah 60%"))

        bp = r["beban_terhadap_pendapatan"]
        s, wrn = self._nilai_rasio(bp, baik=0.75, cukup=0.9, bahaya=1.0,
                                   teks=theme.persen(bp))
        daftar.append(baris_rasio("Beban terhadap Pendapatan",
                                  theme.persen(bp), s, wrn, "di bawah 75%"))

        tabel = w.Tabel([("Rasio", -1), ("Nilai", 130),
                         ("Status", 170), ("Acuan Sehat", 150)])
        tabel.setObjectName("tabel_rasio")
        tabel.setRowCount(len(daftar))
        for i, (nama, nilai, status, warna, acuan) in enumerate(daftar):
            tabel.setItem(i, 0, QTableWidgetItem(nama))

            it_n = QTableWidgetItem(nilai)
            it_n.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            tabel.setItem(i, 1, it_n)

            it_s = QTableWidgetItem(status)
            it_s.setForeground(QBrush(QColor(warna)))
            tabel.setItem(i, 2, it_s)

            tabel.setItem(i, 3, QTableWidgetItem(acuan))
        tabel.setMinimumHeight(360)

        kartu.body().addWidget(tabel)
        return kartu

    def _nilai_rasio(self, nilai: float, baik: float, cukup: float, bahaya: float,
                     teks: str, terbalik: bool = False,
                     maks=None) -> tuple[str, str]:
        """
        Klasifikasikan rasio menjadi status beserta warnanya.

        terbalik=False dipakai untuk rasio yang nilainya KECIL itu baik,
        misalnya rasio utang. terbalik=True untuk yang nilainya BESAR itu
        baik, misalnya margin laba.

        maks dipakai untuk rasio yang nilainya kecil itu baik, tetapi
        terlalu kecil juga tidak sehat, misalnya rasio kas: kas negatif
        berarti utang, bukan kondisi baik. Bila nilai berada di bawah maks,
        hasilnya dinilai berbahaya.
        """
        if nilai == float("inf"):
            return ("Data tidak memadai", C.TEXT_MUTED)

        # Nilai di bawah batas bawah berarti kondisinya justru berbahaya,
        # bukan baik. Contohnya rasio kas -0,58x: kasnya negatif.
        if maks is not None and nilai < maks:
            return ("Berisiko Tinggi", C.DANGER)

        if terbalik:
            if nilai >= baik:
                return ("Sangat Baik", C.SUCCESS)
            if nilai >= cukup:
                return ("Cukup", C.WARNING)
            return ("Perlu Perbaikan", C.DANGER)
        else:
            if nilai <= baik:
                return ("Sangat Baik", C.SUCCESS)
            if nilai <= cukup:
                return ("Cukup", C.WARNING)
            return ("Berisiko Tinggi", C.DANGER)

    def _kotak_rasio(self, nama: str, nilai: str, status: str, warna: str,
                     penjelasan: str) -> QWidget:
        f = QFrame()
        theme.latar(f, f"background: {C.SURFACE_ALT}; border: 1px solid {C.BORDER}; "
                        "border-radius: 8px;")
        l = QVBoxLayout(f)
        l.setContentsMargins(16, 14, 16, 14)
        l.setSpacing(6)

        atas = QHBoxLayout()
        n = QLabel(nama)
        n.setStyleSheet(f"font-size: {theme.FS_SMALL}px; font-weight: 600; "
                        f"color: {C.TEXT_MUTED}; background: transparent;")
        atas.addWidget(n)
        atas.addStretch()
        s = QLabel(status)
        s.setStyleSheet(f"color: {warna}; font-size: {theme.FS_TINY}px; "
                        "font-weight: 700; background: transparent;")
        atas.addWidget(s)
        l.addLayout(atas)

        v = QLabel(nilai)
        v.setStyleSheet(f"font-family: {theme.FONT_ANGKA}; font-size: 22px; "
                        f"font-weight: 700; color: {warna}; background: transparent;")
        l.addWidget(v)

        p = QLabel(penjelasan)
        p.setWordWrap(True)
        p.setStyleSheet(f"font-size: {theme.FS_TINY}px; color: {C.TEXT_MUTED}; "
                        "background: transparent; line-height: 145%;")
        l.addWidget(p)
        return f

    # ==================================================================
    # TAB 3: SIMULASI
    # ==================================================================
    def _isi_simulasi(self, cid: int, tahun: int):
        lay = self.tab_simulasi.layout()

        lay.addWidget(w.InfoBanner(
            "Gunakan simulasi ini untuk menguji keputusan sebelum diambil: "
            "bagaimana bila pendapatan naik 20%? Bagaimana bila beban dipangkas 10%? "
            "Aplikasi menghitung dampaknya terhadap laba dan pajak.",
            "info", "Cara memakai simulasi"))

        kartu = w.Card()
        kl = kartu.body()

        j = QLabel("Atur Skenario")
        j.setObjectName("SectionTitle")
        kl.addWidget(j)

        baris = QHBoxLayout()
        baris.setSpacing(24)

        k1 = QVBoxLayout()
        k1.addWidget(w.label("Perubahan Pendapatan (%)", objek="FormLabel"))
        from PySide6.QtWidgets import QSlider
        self.slider_pendapatan = QSlider(Qt.Horizontal)
        self.slider_pendapatan.setRange(-50, 100)
        self.slider_pendapatan.setValue(0)
        self.slider_pendapatan.setTickPosition(QSlider.TicksBelow)
        self.slider_pendapatan.setTickInterval(25)
        self.lbl_pendapatan = QLabel("0%")
        self.lbl_pendapatan.setStyleSheet(
            f"font-family: {theme.FONT_ANGKA}; font-size: 17px; font-weight: 700; "
            f"color: {C.PRIMARY}; background: transparent;")
        self.slider_pendapatan.valueChanged.connect(self._ubah_slider)
        k1.addWidget(self.slider_pendapatan)
        k1.addWidget(self.lbl_pendapatan)
        baris.addLayout(k1, 1)

        k2 = QVBoxLayout()
        k2.addWidget(w.label("Perubahan Beban (%)", objek="FormLabel"))
        self.slider_beban = QSlider(Qt.Horizontal)
        self.slider_beban.setRange(-50, 100)
        self.slider_beban.setValue(0)
        self.slider_beban.setTickPosition(QSlider.TicksBelow)
        self.slider_beban.setTickInterval(25)
        self.lbl_beban = QLabel("0%")
        self.lbl_beban.setStyleSheet(
            f"font-family: {theme.FONT_ANGKA}; font-size: 17px; font-weight: 700; "
            f"color: {C.WARNING}; background: transparent;")
        self.slider_beban.valueChanged.connect(self._ubah_slider)
        k2.addWidget(self.slider_beban)
        k2.addWidget(self.lbl_beban)
        baris.addLayout(k2, 1)
        kl.addLayout(baris)

        self.area_hasil = QWidget()
        self.area_hasil_lay = QVBoxLayout(self.area_hasil)
        self.area_hasil_lay.setContentsMargins(0, 12, 0, 0)
        kl.addWidget(self.area_hasil)

        lay.addWidget(kartu)
        lay.addStretch()

        self._render_simulasi(cid, tahun)

    def _ubah_slider(self):
        self.lbl_pendapatan.setText(f"{self.slider_pendapatan.value():+d}%")
        self.lbl_beban.setText(f"{self.slider_beban.value():+d}%")
        self._render_simulasi(self.ctx.company_id, self.ctx.tahun)

    def _render_simulasi(self, cid: int, tahun: int):
        while self.area_hasil_lay.count():
            it = self.area_hasil_lay.takeAt(0)
            wdg = it.widget()
            if wdg is not None:
                wdg.setParent(None)
                wdg.deleteLater()

        if not cid:
            return
        try:
            s = services.simulasi(cid, tahun,
                                  self.slider_pendapatan.value(),
                                  self.slider_beban.value())
        except Exception as e:
            self.area_hasil_lay.addWidget(w.InfoBanner(str(e), "danger", "Gagal"))
            return

        grid = QGridLayout()
        grid.setSpacing(14)

        def kotak(label, sebelum, sesudah, satuan_uang=True):
            f = QFrame()
            theme.latar(f, f"background: {C.SURFACE_ALT}; border: 1px solid "
                            f"{C.BORDER}; border-radius: 8px;")
            l = QVBoxLayout(f)
            l.setContentsMargins(14, 12, 14, 12)
            l.setSpacing(5)
            t = QLabel(label.upper())
            t.setObjectName("KpiLabel")
            l.addWidget(t)
            fmt = theme.money if satuan_uang else str
            v = QLabel(fmt(sesudah))
            delta = sesudah - sebelum
            warna = C.POSITIF if delta > 0 else (C.NEGATIF if delta < 0 else C.TEXT)
            v.setStyleSheet(f"font-family: {theme.FONT_ANGKA}; font-size: 19px; "
                            f"font-weight: 700; color: {warna}; background: transparent;")
            l.addWidget(v)
            d = QLabel(f"Semula {fmt(sebelum)} "
                       f"({'+' if delta >= 0 else ''}{fmt(delta)})")
            d.setStyleSheet(f"font-size: {theme.FS_TINY}px; color: {C.TEXT_MUTED}; "
                            "background: transparent;")
            d.setWordWrap(True)
            l.addWidget(d)
            return f

        grid.addWidget(kotak("Pendapatan", s["pendapatan_sekarang"],
                             s["pendapatan_baru"]), 0, 0)
        grid.addWidget(kotak("Beban", s["beban_sekarang"], s["beban_baru"]), 0, 1)
        grid.addWidget(kotak("Laba Sebelum Pajak", s["laba_sekarang"],
                             s["laba_baru"]), 1, 0)
        grid.addWidget(kotak("Pajak Terutang", s["pajak_sekarang"],
                             s["pajak_baru"]), 1, 1)
        grid.addWidget(kotak("Laba Setelah Pajak",
                             s["laba_sekarang"] - s["pajak_sekarang"],
                             s["laba_setelah_pajak"]), 2, 0, 1, 2)

        self.area_hasil_lay.addLayout(grid)

        catatan = QLabel(
            f"Skema pajak yang dipakai: <b>{s['skema']}</b>. Simulasi ini "
            "mengasumsikan struktur biaya tetap dan tidak memperhitungkan "
            "perubahan aset atau pinjaman."
        )
        catatan.setWordWrap(True)
        catatan.setTextFormat(Qt.RichText)
        catatan.setStyleSheet(f"font-size: {theme.FS_TINY}px; color: {C.TEXT_MUTED}; "
                              "background: transparent;")
        self.area_hasil_lay.addWidget(catatan)
