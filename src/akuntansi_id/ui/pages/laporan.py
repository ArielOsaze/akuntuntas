"""
AkunTuntas - Halaman Laporan Keuangan
======================================
  • Neraca Saldo
  • Laba Rugi
  • Neraca (Laporan Posisi Keuangan)
  • Arus Kas
  • Perubahan Ekuitas
  • Buku Besar
  • Cetak A4 dan ekspor Excel/PDF
"""
from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QFrame, QScrollArea,
)

from ... import config, services
from .. import icons, theme
from ..theme import C
from .. import widgets as w
from .. import popup

PETA_TAB = {
    0: "Laba Rugi",
    1: "Neraca",
    2: "Arus Kas",
    3: "Perubahan Ekuitas",
    4: "Neraca Saldo",
    5: "Buku Besar",
}


# ==========================================================================
# HALAMAN LAPORAN
# ==========================================================================
class LaporanPage(QWidget):
    pindah_halaman = Signal(str)

    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx

        luar = QVBoxLayout(self)
        luar.setContentsMargins(0, 0, 0, 0)
        luar.setSpacing(0)

        self.header = w.PageHeader(
            "Laporan Keuangan",
            "Seluruh laporan diturunkan dari jurnal yang sama, sehingga angkanya "
            "konsisten satu dengan yang lain.")

        self.cmb_tahun = QComboBox()
        tk = datetime.now().year
        for t in range(tk - 3, tk + 2):
            self.cmb_tahun.addItem(str(t), t)
        i = self.cmb_tahun.findData(ctx.tahun)
        if i >= 0:
            self.cmb_tahun.setCurrentIndex(i)
        self.cmb_tahun.setMinimumWidth(100)
        self.cmb_tahun.currentIndexChanged.connect(self._ganti_tahun)
        self.header.tambah_aksi(self.cmb_tahun)

        self.cmb_periode = QComboBox()
        self.cmb_periode.addItem("Setahun", 0)
        for i, n in enumerate(config.MONTH_NAMES_ID, start=1):
            self.cmb_periode.addItem(f"s.d. {n}", i)
        self.cmb_periode.setMinimumWidth(130)
        self.cmb_periode.currentIndexChanged.connect(self.muat)
        self.header.tambah_aksi(self.cmb_periode)

        b_ekspor = w.tombol("Ekspor", ikon="ekspor")
        b_ekspor.setToolTip(
            "Simpan laporan yang sedang dibuka ke Excel atau PDF.\n"
            "Pilih format pada dialog penyimpanan.")
        b_ekspor.clicked.connect(self._ekspor)
        self.header.tambah_aksi(b_ekspor)

        b_cetak = w.tombol("Cetak", ikon="dokumen")
        b_cetak.setToolTip(
            "Cetak laporan yang sedang dibuka ke kertas A4.\n"
            "Pratinjau ditampilkan lebih dulu sebelum kertas terpakai.")
        b_cetak.clicked.connect(self._cetak)
        self.header.tambah_aksi(b_cetak)

        kepala = QWidget()
        theme.latar(kepala, f"background: {C.SURFACE}; "
                             f"border-bottom: 1px solid {C.BORDER};")
        kl = QVBoxLayout(kepala)
        kl.setContentsMargins(26, 20, 26, 18)
        kl.addWidget(self.header)
        luar.addWidget(kepala)

        self.tabs = w.Tab()
        wadah = QWidget()
        wl = QVBoxLayout(wadah)
        wl.setContentsMargins(22, 16, 22, 22)
        wl.addWidget(self.tabs)
        luar.addWidget(wadah, 1)

        self.tab_laba_rugi = self._tab_gulir("Laba Rugi")
        self.tab_neraca = self._tab_gulir("Neraca")
        self.tab_arus_kas = self._tab_gulir("Arus Kas")
        self.tab_ekuitas = self._tab_gulir("Perubahan Ekuitas")
        self.tab_neraca_saldo = self._tab_gulir("Neraca Saldo")
        self.tab_buku_besar = self._tab_gulir("Buku Besar")
        self.tabs.currentChanged.connect(self.muat)

    def _tab_gulir(self, judul: str) -> QWidget:
        """
        Buat isi tab yang dapat digulir, lalu pasang sebagai tab.

        Laporan panjang seperti neraca dan buku besar tidak boleh dipotong
        oleh tinggi jendela. Dengan satu area gulir per tab, seluruh baris
        dan totalnya dapat dicapai tanpa gulir bertumpuk di dalam tabel.
        """
        isi = QWidget()
        lay = QVBoxLayout(isi)
        lay.setContentsMargins(0, 12, 0, 0)
        lay.setSpacing(12)
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setFrameShape(QFrame.NoFrame)
        area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        area.setWidget(isi)
        self.tabs.addTab(area, judul)
        return isi

    def _ganti_tahun(self):
        self.ctx.tahun = self.cmb_tahun.currentData()
        self.muat()

    def periode(self):
        return self.cmb_periode.currentData() or None

    # ------------------------------------------------------------------
    def muat(self):
        cid = self.ctx.company_id
        if not cid:
            self._bersihkan(self.tab_laba_rugi)
            self.tab_laba_rugi.layout().addWidget(w.InfoBanner(
                "Belum ada perusahaan. Buat profil perusahaan terlebih dahulu.",
                "warning", "Data belum tersedia"))
            return
        idx = self.tabs.currentIndex()
        if idx == 0:
            self._isi_laba_rugi(cid)
        elif idx == 1:
            self._isi_neraca(cid)
        elif idx == 2:
            self._isi_arus_kas(cid)
        elif idx == 3:
            self._isi_ekuitas(cid)
        elif idx == 4:
            self._isi_neraca_saldo(cid)
        elif idx == 5:
            self._isi_buku_besar(cid)

    def _bersihkan(self, widget):
        lay = widget.layout()
        while lay.count():
            it = lay.takeAt(0)
            wdg = it.widget()
            if wdg is not None:
                wdg.setParent(None)
                wdg.deleteLater()
            elif it.layout():
                self._bersihkan_layout(it.layout())

    def _bersihkan_layout(self, lay):
        while lay.count():
            it = lay.takeAt(0)
            wdg = it.widget()
            if wdg is not None:
                wdg.setParent(None)
                wdg.deleteLater()
            elif it.layout():
                self._bersihkan_layout(it.layout())

    # ==================================================================
    # LABA RUGI
    # ==================================================================
    def _isi_laba_rugi(self, cid):
        self._bersihkan(self.tab_laba_rugi)
        lay = self.tab_laba_rugi.layout()
        tahun, bulan = self.ctx.tahun, self.periode()

        lr = services.laporan_laba_rugi(cid, tahun, bulan)

        # KPI atas
        kartu = w.Card()
        kl = kartu.body()
        baris = QHBoxLayout()
        baris.setSpacing(30)
        baris.addWidget(w.MiniStat("Pendapatan Usaha", theme.money(lr.pendapatan_usaha)))
        baris.addWidget(w.MiniStat("Laba Kotor", theme.money(lr.laba_kotor),
                                   C.POSITIF if lr.laba_kotor >= 0 else C.NEGATIF))
        baris.addWidget(w.MiniStat("Laba Operasional", theme.money(lr.laba_operasional),
                                   C.POSITIF if lr.laba_operasional >= 0 else C.NEGATIF))
        baris.addWidget(w.MiniStat("Laba Bersih", theme.money(lr.laba_bersih),
                                   C.POSITIF if lr.laba_bersih >= 0 else C.NEGATIF))
        baris.addWidget(w.MiniStat("Margin Bersih", theme.persen(lr.margin_bersih)))
        baris.addStretch()
        kl.addLayout(baris)
        lay.addWidget(kartu)

        # tabel laba rugi
        t = w.Tabel([("Uraian", -1), ("Jumlah (Rp)", 200), ("% Pendapatan", 140)])
        # Keterangan ini tampil saat tabel masih kosong, supaya
        # pengguna tahu langkah berikutnya.
        t.set_pesan_kosong(
            "Belum ada data untuk dilaporkan."
            "\n\n"
            "Catat dulu transaksi pada menu Jurnal Umum, Penjualan, atau "
            "Pembelian. Laporan akan terisi sendiri.")

        baris_tabel = []
        warna = {}
        baris_tebal = set()

        def tambah(uraian, nilai, tebal=False, persen=None):
            idx = len(baris_tabel)
            p = persen if persen is not None else (
                nilai / lr.pendapatan_usaha if lr.pendapatan_usaha else 0)
            baris_tabel.append([uraian, theme.money(nilai),
                                f"{theme.persen(p, 1)}" if lr.pendapatan_usaha else ""])
            if tebal:
                warna[idx] = C.PRIMARY
                baris_tebal.add(idx)
            return idx

        tambah("PENDAPATAN USAHA", lr.pendapatan_usaha, True, 1.0)
        for kode, nama, nilai in lr.rincian_pendapatan:
            if "Pendapatan Usaha" in nama or kode.startswith("400"):
                baris_tabel.append([f"    {kode} {nama}", theme.money(nilai), ""])
        tambah("Harga Pokok Penjualan", -lr.hpp)
        tambah("LABA KOTOR", lr.laba_kotor, True)
        tambah("BEBAN OPERASIONAL", -lr.beban_operasional, True)
        for kode, nama, nilai in lr.rincian_beban:
            akun = services.get_account(cid, kode)
            if akun and akun["grup_lr"] == "Beban Operasional":
                baris_tabel.append(
                    [f"    {kode} {nama}", theme.money(-nilai), ""])
        tambah("LABA OPERASIONAL", lr.laba_operasional, True)
        tambah("Pendapatan Lain-lain", lr.pendapatan_lain)
        tambah("Beban Lain-lain", -lr.beban_lain)
        tambah("LABA SEBELUM PAJAK", lr.laba_sebelum_pajak, True)
        tambah("Beban Pajak Kini (estimasi)", -lr.beban_pajak)
        tambah("LABA BERSIH SETELAH PAJAK", lr.laba_bersih, True)

        t.isi(baris_tabel, warna_baris=warna, align_kanan={1, 2},
              tebal_baris=baris_tebal)
        t.sesuaikan_tinggi(minimum=200, maksimum=900)
        lay.addWidget(t, 1)

        if self.ctx.beginner:
            lay.addWidget(w.HelpPanel(
                "Cara membaca Laba Rugi",
                "Laporan ini menunjukkan apakah usaha Anda untung atau rugi.\n\n"
                "• LABA KOTOR = Pendapatan − HPP. Ini laba dari penjualan sebelum "
                "beban operasional.\n"
                "• LABA OPERASIONAL = Laba kotor − beban operasional. Ini laba dari "
                "kegiatan usaha utama.\n"
                "• LABA BERSIH = setelah pajak. Ini yang benar-benar menjadi milik Anda.\n\n"
                "Kolom '% Pendapatan' membantu Anda melihat proporsi tiap pos "
                "terhadap total penjualan.",
                "SAK EMKM - laporan laba rugi; PSAK 1 - penyajian laporan keuangan."))

        lay.addStretch()

    # ==================================================================
    # NERACA
    # ==================================================================
    def _isi_neraca(self, cid):
        self._bersihkan(self.tab_neraca)
        lay = self.tab_neraca.layout()
        tahun, bulan = self.ctx.tahun, self.periode()
        n = services.laporan_neraca(cid, tahun, bulan)

        if not n.seimbang:
            lay.addWidget(w.InfoBanner(
                f"Neraca belum seimbang. Selisih {theme.money(n.selisih)} antara "
                f"total aset {theme.money(n.total_aset)} dan total liabilitas+ekuitas "
                f"{theme.money(n.total_liabilitas_ekuitas)}. Periksa saldo awal akun "
                "dan kelengkapan baris neraca pada bagan akun.",
                "danger", "Neraca tidak seimbang"))

        dua = QHBoxLayout()
        dua.setSpacing(16)

        # ---- sisi aset
        ka = w.Card()
        ka.body().addWidget(self._judul_kolom("ASET"))
        t1 = w.Tabel([("Keterangan", -1), ("Jumlah (Rp)", 165)])
        # Keterangan ini tampil saat tabel masih kosong, supaya
        # pengguna tahu langkah berikutnya.
        t1.set_pesan_kosong(
            "Belum ada data untuk dilaporkan."
            "\n\n"
            "Catat dulu transaksi pada menu Jurnal Umum, Penjualan, atau "
            "Pembelian. Laporan akan terisi sendiri.")

        baris1, warna1, tebal1 = [], {}, set()

        def tambah1(label, nilai=None, tebal=False, indent=True):
            idx = len(baris1)
            nilai_teks = theme.money(nilai) if nilai is not None else ""
            baris1.append([("    " if indent else "") + label, nilai_teks])
            if tebal:
                warna1[idx] = C.PRIMARY
                tebal1.add(idx)
            return idx

        tambah1("ASET LANCAR", tebal=True, indent=False)
        for kode, (nama, nilai) in sorted(n.aset_lancar.items()):
            if nilai != 0:
                tambah1(f"{kode} {nama}", nilai)
        tambah1("Total Aset Lancar", n.total_aset_lancar, True, False)

        if any(nilai != 0 for _, (_, nilai) in n.aset_tetap.items()):
            tambah1("ASET TETAP", tebal=True, indent=False)
            for kode, (nama, nilai) in sorted(n.aset_tetap.items()):
                if nilai != 0:
                    tambah1(f"{kode} {nama}", nilai)
            tambah1("Total Aset Tetap", n.total_aset_tetap, True, False)

        if any(nilai != 0 for _, (_, nilai) in n.aset_lain.items()):
            tambah1("ASET LAIN", tebal=True, indent=False)
            for kode, (nama, nilai) in sorted(n.aset_lain.items()):
                if nilai != 0:
                    tambah1(f"{kode} {nama}", nilai)

        tambah1("TOTAL ASET", n.total_aset, True, False)
        t1.isi(baris1, warna_baris=warna1, align_kanan={1},
               tebal_baris=tebal1)
        ka.body().addWidget(t1, 1)
        dua.addWidget(ka, 1)

        # ---- sisi liabilitas & ekuitas
        ke = w.Card()
        ke.body().addWidget(self._judul_kolom("LIABILITAS & EKUITAS"))
        t2 = w.Tabel([("Keterangan", -1), ("Jumlah (Rp)", 165)])
        # Keterangan ini tampil saat tabel masih kosong, supaya
        # pengguna tahu langkah berikutnya.
        t2.set_pesan_kosong(
            "Belum ada data untuk dilaporkan."
            "\n\n"
            "Catat dulu transaksi pada menu Jurnal Umum, Penjualan, atau "
            "Pembelian. Laporan akan terisi sendiri.")

        baris2, warna2, tebal2 = [], {}, set()

        def tambah2(label, nilai=None, tebal=False, indent=True):
            idx = len(baris2)
            nilai_teks = theme.money(nilai) if nilai is not None else ""
            baris2.append([("    " if indent else "") + label, nilai_teks])
            if tebal:
                warna2[idx] = C.PRIMARY
                tebal2.add(idx)
            return idx

        tambah2("LIABILITAS JANGKA PENDEK", tebal=True, indent=False)
        for kode, (nama, nilai) in sorted(n.liabilitas_pendek.items()):
            if nilai != 0:
                tambah2(f"{kode} {nama}", nilai)
        tambah2("Total Liabilitas Jangka Pendek", n.total_liabilitas_pendek, True, False)

        if any(nilai != 0 for _, (_, nilai) in n.liabilitas_panjang.items()):
            tambah2("LIABILITAS JANGKA PANJANG", tebal=True, indent=False)
            for kode, (nama, nilai) in sorted(n.liabilitas_panjang.items()):
                if nilai != 0:
                    tambah2(f"{kode} {nama}", nilai)
            tambah2("Total Liabilitas Jangka Panjang", n.total_liabilitas_panjang, True, False)

        tambah2("TOTAL LIABILITAS", n.total_liabilitas, True, False)

        tambah2("EKUITAS", tebal=True, indent=False)
        tambah2("Modal Disetor", n.modal)
        tambah2("Saldo Laba", n.saldo_laba)
        tambah2("Laba Tahun Berjalan", n.laba_tahun_berjalan)
        if n.prive:
            tambah2("Prive (Penarikan Pemilik)", -n.prive)
        tambah2("Total Ekuitas", n.total_ekuitas, True, False)
        tambah2("TOTAL LIABILITAS & EKUITAS", n.total_liabilitas_ekuitas, True, False)

        t2.isi(baris2, warna_baris=warna2, align_kanan={1},
               tebal_baris=tebal2)
        # Kedua sisi neraca memakai tinggi yang sama agar tampak sejajar,
        # dan seluruh baris termasuk totalnya langsung terlihat.
        tinggi_neraca = max(t1.tinggi_konten(), t2.tinggi_konten())
        t1.setFixedHeight(tinggi_neraca)
        t2.setFixedHeight(tinggi_neraca)
        ke.body().addWidget(t2, 1)
        dua.addWidget(ke, 1)
        lay.addLayout(dua)

        # kontrol keseimbangan
        cek = QFrame()
        warna_bg = C.SUCCESS_BG if n.seimbang else C.DANGER_BG
        warna_txt = C.SUCCESS if n.seimbang else C.DANGER
        border = "#BFDCCB" if n.seimbang else "#EAC4BF"
        theme.latar(cek, f"background: {warna_bg}; border: 1px solid {border}; "
                          "border-radius: 8px;")
        cl = QHBoxLayout(cek)
        cl.setContentsMargins(16, 12, 16, 12)
        cl.setSpacing(30)
        ikon = "simpan" if n.seimbang else "hapus"
        pesan = (f"{ikon} Persamaan akuntansi seimbang: "
                 f"Aset {theme.money(n.total_aset)} = Liabilitas + Ekuitas "
                 f"{theme.money(n.total_liabilitas_ekuitas)}"
                 if n.seimbang else
                 f"{ikon} Selisih {theme.money(n.selisih)}")
        l = QLabel(pesan)
        l.setStyleSheet(f"color: {warna_txt}; font-weight: 700; background: transparent;")
        cl.addWidget(l)
        cl.addStretch()
        lay.addWidget(cek)

        if self.ctx.beginner:
            lay.addWidget(w.HelpPanel(
                "Cara membaca Neraca",
                "Neraca menunjukkan apa yang DIMILIKI (aset) dan dari mana "
                "PENDANAANNYA (liabilitas + ekuitas) pada satu tanggal tertentu.\n\n"
                "Persamaan dasar akuntansi:\n"
                "    ASET = LIABILITAS + EKUITAS\n\n"
                "Ini harus selalu seimbang. Bila tidak seimbang, ada pencatatan "
                "yang salah atau saldo awal belum lengkap.\n\n"
                "• Aset lancar: dapat dicairkan dalam 12 bulan (kas, piutang, persediaan)\n"
                "• Aset tetap: dipakai jangka panjang (peralatan, kendaraan, bangunan)\n"
                "• Ekuitas: modal pemilik + laba yang belum diambil",
                "SAK EMKM; PSAK 1 - penyajian laporan posisi keuangan."))

        lay.addStretch()

    def _judul_kolom(self, teks: str) -> QLabel:
        l = QLabel(teks)
        l.setStyleSheet(
            f"font-size: 14px; font-weight: 700; color: {C.PRIMARY}; "
            f"background: transparent; padding-bottom: 4px; "
            f"border-bottom: 2px solid {C.PRIMARY_SOFT};")
        return l

    # ==================================================================
    # ARUS KAS
    # ==================================================================
    def _isi_arus_kas(self, cid):
        self._bersihkan(self.tab_arus_kas)
        lay = self.tab_arus_kas.layout()
        tahun, bulan = self.ctx.tahun, self.periode()
        a = services.laporan_arus_kas(cid, tahun, bulan)

        kartu = w.Card()
        baris = QHBoxLayout()
        baris.setSpacing(30)
        baris.addWidget(w.MiniStat("Kas Awal", theme.money(a.kas_awal)))
        baris.addWidget(w.MiniStat("Arus Kas Operasi", theme.money(a.total_operasi),
                                   C.POSITIF if a.total_operasi >= 0 else C.NEGATIF))
        baris.addWidget(w.MiniStat("Arus Kas Investasi", theme.money(a.total_investasi),
                                   C.POSITIF if a.total_investasi >= 0 else C.NEGATIF))
        baris.addWidget(w.MiniStat("Arus Kas Pendanaan", theme.money(a.total_pendanaan),
                                   C.POSITIF if a.total_pendanaan >= 0 else C.NEGATIF))
        baris.addWidget(w.MiniStat("Kas Akhir", theme.money(a.kas_akhir), C.PRIMARY))
        baris.addStretch()
        kartu.body().addLayout(baris)
        lay.addWidget(kartu)

        t = w.Tabel([("Uraian", -1), ("Jumlah (Rp)", 190)])
        # Keterangan ini tampil saat tabel masih kosong, supaya
        # pengguna tahu langkah berikutnya.
        t.set_pesan_kosong(
            "Belum ada data untuk dilaporkan."
            "\n\n"
            "Catat dulu transaksi pada menu Jurnal Umum, Penjualan, atau "
            "Pembelian. Laporan akan terisi sendiri.")

        baris_t, warna, tebal_baris = [], {}, set()

        def tambah(label, nilai=None, tebal=False, indent=0):
            idx = len(baris_t)
            nilai_teks = theme.money(nilai) if nilai is not None else ""
            baris_t.append(["    " * indent + label, nilai_teks])
            if tebal:
                warna[idx] = C.PRIMARY
                tebal_baris.add(idx)

        tambah("AKTIVITAS OPERASI", tebal=True)
        for label, nilai in a.operasi_masuk:
            tambah(f"Penerimaan - {label}", nilai, indent=1)
        for label, nilai in a.operasi_keluar:
            tambah(f"Pengeluaran - {label}", -nilai, indent=1)
        tambah("Arus Kas Bersih dari Aktivitas Operasi", a.total_operasi, True)

        tambah("AKTIVITAS INVESTASI", tebal=True)
        for label, nilai in a.investasi_masuk:
            tambah(f"Penerimaan - {label}", nilai, indent=1)
        for label, nilai in a.investasi_keluar:
            tambah(f"Pengeluaran - {label}", -nilai, indent=1)
        tambah("Arus Kas Bersih dari Aktivitas Investasi", a.total_investasi, True)

        tambah("AKTIVITAS PENDANAAN", tebal=True)
        for label, nilai in a.pendanaan_masuk:
            tambah(f"Penerimaan - {label}", nilai, indent=1)
        for label, nilai in a.pendanaan_keluar:
            tambah(f"Pengeluaran - {label}", -nilai, indent=1)
        tambah("Arus Kas Bersih dari Aktivitas Pendanaan", a.total_pendanaan, True)

        tambah("KENAIKAN/(PENURUNAN) KAS", a.kenaikan_kas, True)
        tambah("Kas pada Awal Periode", a.kas_awal)
        tambah("KAS PADA AKHIR PERIODE", a.kas_akhir, True)

        t.isi(baris_t, warna_baris=warna, align_kanan={1},
              tebal_baris=tebal_baris)
        t.sesuaikan_tinggi()
        lay.addWidget(t, 1)

        if not a.seimbang:
            lay.addWidget(w.InfoBanner(
                f"Selisih {theme.money(a.selisih)} antara perhitungan arus kas dan "
                "saldo kas akhir. Kemungkinan ada transaksi kas yang lawan akunnya "
                "belum terpetakan, atau saldo awal akun kas belum diisi.",
                "warning", "Perlu penelusuran"))

        if self.ctx.beginner:
            lay.addWidget(w.HelpPanel(
                "Cara membaca Arus Kas",
                "Laporan ini menjawab pertanyaan: 'ke mana uang saya pergi?'\n\n"
                "Dibagi tiga aktivitas:\n"
                "• OPERASI - uang dari kegiatan usaha sehari-hari (jualan, bayar beban). "
                "Ini yang paling penting: harus positif.\n"
                "• INVESTASI - uang untuk membeli/jual aset tetap.\n"
                "• PENDANAAN - uang dari/ke pemilik dan bank (modal, pinjaman, dividen).\n\n"
                "Usaha sehat biasanya memiliki arus kas operasi yang positif dan "
                "cukup untuk membiayai investasi.",
                "PSAK 2 - laporan arus kas; SAK EMKM."))

        lay.addStretch()

    # ==================================================================
    # PERUBAHAN EKUITAS
    # ==================================================================
    def _isi_ekuitas(self, cid):
        self._bersihkan(self.tab_ekuitas)
        lay = self.tab_ekuitas.layout()
        tahun = self.ctx.tahun
        data = services.laporan_perubahan_ekuitas(cid, tahun)

        t = w.Tabel([("Uraian", -1), ("Jumlah (Rp)", 200)])
        # Keterangan ini tampil saat tabel masih kosong, supaya
        # pengguna tahu langkah berikutnya.
        t.set_pesan_kosong(
            "Belum ada data untuk dilaporkan."
            "\n\n"
            "Catat dulu transaksi pada menu Jurnal Umum, Penjualan, atau "
            "Pembelian. Laporan akan terisi sendiri.")

        baris, warna, tebal_baris = [], {}, set()
        for d in data:
            idx = len(baris)
            baris.append([d["uraian"], theme.money(d["nilai"])])
            if d.get("tebal"):
                warna[idx] = C.PRIMARY
                tebal_baris.add(idx)
        t.isi(baris, warna_baris=warna, align_kanan={1},
              tebal_baris=tebal_baris)
        t.sesuaikan_tinggi()
        lay.addWidget(t, 1)

        if self.ctx.beginner:
            lay.addWidget(w.HelpPanel(
                "Cara membaca Perubahan Ekuitas",
                "Laporan ini menjelaskan mengapa ekuitas (kekayaan bersih pemilik) "
                "berubah selama satu periode.\n\n"
                "Ekuitas bertambah dari: setoran modal dan laba bersih.\n"
                "Ekuitas berkurang dari: dividen yang dibagikan dan prive "
                "(penarikan pemilik).\n\n"
                "Laporan ini menjembatani laba pada Laba Rugi dengan perubahan "
                "ekuitas pada Neraca.",
                "PSAK 1 - laporan perubahan ekuitas."))
        lay.addStretch()

    # ==================================================================
    # NERACA SALDO
    # ==================================================================
    def _isi_neraca_saldo(self, cid):
        self._bersihkan(self.tab_neraca_saldo)
        lay = self.tab_neraca_saldo.layout()
        tahun, bulan = self.ctx.tahun, self.periode()
        data = services.laporan_neraca_saldo(cid, tahun, bulan)

        t = w.Tabel([
            ("Kode", 75), ("Nama Akun", -1), ("Tipe", 100), ("Normal", 75),
            ("Saldo Awal", 140), ("Debit", 140), ("Kredit", 140), ("Saldo Akhir", 150),
        ])
        # Keterangan ini tampil saat tabel masih kosong, supaya
        # pengguna tahu langkah berikutnya.
        t.set_pesan_kosong(
            "Belum ada data untuk dilaporkan."
            "\n\n"
            "Catat dulu transaksi pada menu Jurnal Umum, Penjualan, atau "
            "Pembelian. Laporan akan terisi sendiri.")

        baris, warna = [], {}
        for d in data:
            if (d.saldo_awal == 0 and d.debit == 0 and d.kredit == 0):
                continue
            idx = len(baris)
            baris.append([d.kode, d.nama, d.tipe, d.normal,
                          theme.money(d.saldo_awal), theme.money(d.debit),
                          theme.money(d.kredit), theme.money(d.saldo_akhir_normal)])
            if d.perlakuan_fiskal in ("Non-Deductible (+)", "Final Income (-)",
                                      "Review Fiskal"):
                warna[idx] = C.WARNING

        td = sum(d.debit for d in data)
        tk = sum(d.kredit for d in data)
        idx_total = len(baris)
        baris.append(["", "TOTAL MUTASI", "", "", "", theme.money(td),
                      theme.money(tk), ""])
        warna[idx_total] = C.PRIMARY

        t.isi(baris, warna_baris=warna, align_kanan={4, 5, 6, 7},
              tebal_baris={idx_total})
        t.sesuaikan_tinggi(minimum=200, maksimum=620)
        lay.addWidget(t, 1)

        status = QFrame()
        seimbang = abs(td - tk) < 0.5
        theme.latar(status, f"background: {C.SUCCESS_BG if seimbang else C.DANGER_BG}; "
            f"border: 1px solid {'#BFDCCB' if seimbang else '#EAC4BF'}; "
            "border-radius: 8px;")
        sl = QHBoxLayout(status)
        sl.setContentsMargins(16, 12, 16, 12)
        l = QLabel(f"{'simpan' if seimbang else 'hapus'} Total debit {theme.money(td)} "
                   f"{'=' if seimbang else '≠'} total kredit {theme.money(tk)}")
        l.setStyleSheet(f"color: {C.SUCCESS if seimbang else C.DANGER}; "
                        "font-weight: 700; background: transparent;")
        sl.addWidget(l)
        sl.addStretch()
        lay.addWidget(status)

        if self.ctx.beginner:
            lay.addWidget(w.HelpPanel(
                "Cara membaca Neraca Saldo",
                "Neraca saldo adalah daftar semua akun beserta saldonya. Fungsinya "
                "untuk MEMASTIKAN total debit sama dengan total kredit.\n\n"
                "• Saldo Awal - posisi akun pada awal periode\n"
                "• Debit / Kredit - mutasi selama periode\n"
                "• Saldo Akhir - posisi akhir (disajikan pada sisi normal akun)\n\n"
                "Baris berwarna kuning menandai akun yang memerlukan perhatian "
                "khusus saat rekonsiliasi fiskal.",
                "Pasal 28 UU KUP - pembukuan harus dapat diperiksa."))
        lay.addStretch()

    # ==================================================================
    # BUKU BESAR
    # ==================================================================
    def _isi_buku_besar(self, cid):
        self._bersihkan(self.tab_buku_besar)
        lay = self.tab_buku_besar.layout()

        baris_pilih = QHBoxLayout()
        baris_pilih.setSpacing(11)
        baris_pilih.addWidget(w.label("Pilih Akun:", objek="FormLabel"))
        self.cmb_akun = w.combo_akun(cid)
        self.cmb_akun.setMinimumWidth(320)
        self.cmb_akun.currentIndexChanged.connect(self._muat_buku_besar)
        baris_pilih.addWidget(self.cmb_akun)
        baris_pilih.addStretch()
        lay.addLayout(baris_pilih)

        self.area_bb = QWidget()
        self.area_bb_lay = QVBoxLayout(self.area_bb)
        self.area_bb_lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.area_bb)
        self._muat_buku_besar()

    def _muat_buku_besar(self):
        while self.area_bb_lay.count():
            it = self.area_bb_lay.takeAt(0)
            wdg = it.widget()
            if wdg is not None:
                wdg.setParent(None)
                wdg.deleteLater()

        cid = self.ctx.company_id
        kode = self.cmb_akun.currentData() if hasattr(self, "cmb_akun") else None
        if not cid or not kode:
            return

        data = services.buku_besar(cid, kode, self.ctx.tahun, self.periode())
        akun = services.get_account(cid, kode)

        if akun and akun["deskripsi"]:
            self.area_bb_lay.addWidget(w.HelpPanel(
                f"{akun['kode']} - {akun['nama']}", akun["deskripsi"],
                f"Perlakuan fiskal: {akun['perlakuan_fiskal']}"))

        t = w.Tabel([
            ("Tanggal", 105), ("No. Bukti", 130), ("Keterangan", -1),
            ("Debit", 140), ("Kredit", 140), ("Saldo", 150),
        ])
        # Keterangan ini tampil saat tabel masih kosong, supaya
        # pengguna tahu langkah berikutnya.
        t.set_pesan_kosong(
            "Belum ada data untuk dilaporkan."
            "\n\n"
            "Catat dulu transaksi pada menu Jurnal Umum, Penjualan, atau "
            "Pembelian. Laporan akan terisi sendiri.")

        baris, warna, tebal_baris = [], {}, set()
        for i, d in enumerate(data):
            idx = len(baris)
            baris.append([
                theme.tanggal_id(d["tanggal"]) if not d.get("awal") else "",
                d["no_bukti"], d["keterangan"],
                theme.money(d["debit"]) if d["debit"] else "",
                theme.money(d["kredit"]) if d["kredit"] else "",
                theme.money(d["saldo"]),
            ])
            if d.get("awal"):
                warna[idx] = C.PRIMARY
                tebal_baris.add(idx)
        t.isi(baris, warna_baris=warna, align_kanan={3, 4, 5},
              tebal_baris=tebal_baris)
        t.sesuaikan_tinggi(minimum=200, maksimum=620)
        self.area_bb_lay.addWidget(t)

        total_d = sum(d["debit"] for d in data)
        total_k = sum(d["kredit"] for d in data)
        saldo_akhir = data[-1]["saldo"] if data else 0

        kartu = w.Card()
        b = QHBoxLayout()
        b.setSpacing(30)
        b.addWidget(w.MiniStat("Total Debit", theme.money(total_d)))
        b.addWidget(w.MiniStat("Total Kredit", theme.money(total_k)))
        b.addWidget(w.MiniStat("Saldo Akhir", theme.money(saldo_akhir), C.PRIMARY))
        b.addStretch()
        kartu.body().addLayout(b)
        self.area_bb_lay.addWidget(kartu)
        self.area_bb_lay.addStretch()

    # ==================================================================
    # EKSPOR
    # ==================================================================
    def _kumpulkan_data_ekspor(self, bagian: str = None):
        """
        Siapkan tabel satu laporan, atau seluruh laporan bila bagian kosong.

        Data dibentuk dari layanan yang sama dengan yang tampil di layar,
        sehingga angka pada hasil cetak selalu sama dengan yang dilihat
        pengguna.
        """
        cid, tahun, bulan = self.ctx.company_id, self.ctx.tahun, self.periode()
        comp = services.get_company(cid)
        nama_periode = (config.MONTH_NAMES_ID[bulan - 1] + f" {tahun}"
                        if bulan else f"Tahun {tahun}")
        hasil = []

        def perlu(nama):
            return bagian is None or bagian == nama

        if bagian is None:
            hasil.append(("Identitas", [
                ["Keterangan", "Nilai"],
                ["Nama Entitas", comp["nama"]],
                ["Bentuk Badan", config.ENTITY_TYPES.get(
                    comp["bentuk"], {}).get("nama", comp["bentuk"])],
                ["NPWP", comp["npwp"] or "-"],
                ["Periode Laporan", nama_periode],
                ["Status PKP", "Ya" if comp["status_pkp"] else "Tidak"],
                ["Skema PPh", comp["skema_pph"]],
                ["SAK yang Dipakai", config.ENTITY_TYPES.get(
                    comp["bentuk"], {}).get("sak", "-")],
            ]))

        if perlu("Laba Rugi"):
            lr = services.laporan_laba_rugi(cid, tahun, bulan)
            baris = [["Uraian", "Jumlah (Rp)"]]
            baris += [
                ["Pendapatan Usaha", lr.pendapatan_usaha],
                ["Harga Pokok Penjualan", -lr.hpp],
                ["LABA KOTOR", lr.laba_kotor],
                ["Beban Operasional", -lr.beban_operasional],
                ["LABA OPERASIONAL", lr.laba_operasional],
                ["Pendapatan Lain-lain", lr.pendapatan_lain],
                ["Beban Lain-lain", -lr.beban_lain],
                ["LABA SEBELUM PAJAK", lr.laba_sebelum_pajak],
                ["Beban Pajak Kini (estimasi)", -lr.beban_pajak],
                ["LABA BERSIH SETELAH PAJAK", lr.laba_bersih],
            ]
            hasil.append(("Laba Rugi", baris))

        if perlu("Neraca"):
            n = services.laporan_neraca(cid, tahun, bulan)
            baris = [["Keterangan", "Jumlah (Rp)"], ["ASET", ""]]
            for kode, (nama, nilai) in sorted(n.aset_lancar.items()):
                if nilai:
                    baris.append([f"{kode} {nama}", nilai])
            for kode, (nama, nilai) in sorted(n.aset_tetap.items()):
                if nilai:
                    baris.append([f"{kode} {nama}", nilai])
            for kode, (nama, nilai) in sorted(n.aset_lain.items()):
                if nilai:
                    baris.append([f"{kode} {nama}", nilai])
            baris.append(["TOTAL ASET", n.total_aset])
            baris.append(["LIABILITAS", ""])
            for kode, (nama, nilai) in sorted(n.liabilitas_pendek.items()):
                if nilai:
                    baris.append([f"{kode} {nama}", nilai])
            for kode, (nama, nilai) in sorted(n.liabilitas_panjang.items()):
                if nilai:
                    baris.append([f"{kode} {nama}", nilai])
            baris.append(["TOTAL LIABILITAS", n.total_liabilitas])
            baris.append(["EKUITAS", ""])
            baris.append(["Modal Disetor", n.modal])
            baris.append(["Saldo Laba", n.saldo_laba])
            baris.append(["Laba Tahun Berjalan", n.laba_tahun_berjalan])
            if n.prive:
                baris.append(["Prive", -n.prive])
            baris.append(["TOTAL EKUITAS", n.total_ekuitas])
            baris.append(["TOTAL LIABILITAS & EKUITAS",
                          n.total_liabilitas_ekuitas])
            hasil.append(("Neraca", baris))

        if perlu("Arus Kas"):
            a = services.laporan_arus_kas(cid, tahun, bulan)
            baris = [["Uraian", "Jumlah (Rp)"]]
            for label, nilai in a.operasi_masuk:
                baris.append([f"Penerimaan operasi - {label}", nilai])
            for label, nilai in a.operasi_keluar:
                baris.append([f"Pengeluaran operasi - {label}", -nilai])
            baris.append(["Arus Kas Operasi", a.total_operasi])
            for label, nilai in a.investasi_masuk:
                baris.append([f"Penerimaan investasi - {label}", nilai])
            for label, nilai in a.investasi_keluar:
                baris.append([f"Pengeluaran investasi - {label}", -nilai])
            baris.append(["Arus Kas Investasi", a.total_investasi])
            for label, nilai in a.pendanaan_masuk:
                baris.append([f"Penerimaan pendanaan - {label}", nilai])
            for label, nilai in a.pendanaan_keluar:
                baris.append([f"Pengeluaran pendanaan - {label}", -nilai])
            baris.append(["Arus Kas Pendanaan", a.total_pendanaan])
            baris.append(["Kenaikan/(Penurunan) Kas", a.kenaikan_kas])
            baris.append(["Kas Awal", a.kas_awal])
            baris.append(["Kas Akhir", a.kas_akhir])
            hasil.append(("Arus Kas", baris))

        if perlu("Perubahan Ekuitas"):
            data = services.laporan_perubahan_ekuitas(cid, tahun)
            baris = [["Uraian", "Jumlah (Rp)"]]
            for d in data:
                baris.append([d["uraian"], d["nilai"]])
            hasil.append(("Perubahan Ekuitas", baris))

        if perlu("Neraca Saldo"):
            ns = services.laporan_neraca_saldo(cid, tahun, bulan)
            baris = [["Kode", "Nama Akun", "Tipe", "Saldo Awal", "Debit",
                      "Kredit", "Saldo Akhir"]]
            for d in ns:
                if d.saldo_awal == 0 and d.debit == 0 and d.kredit == 0:
                    continue
                baris.append([d.kode, d.nama, d.tipe, d.saldo_awal, d.debit,
                              d.kredit, d.saldo_akhir_normal])
            if len(baris) > 1:
                baris.append(["", "TOTAL MUTASI", "", "",
                              sum(d.debit for d in ns),
                              sum(d.kredit for d in ns), ""])
            hasil.append(("Neraca Saldo", baris))

        if perlu("Buku Besar"):
            kode = (self.cmb_akun.currentData()
                    if hasattr(self, "cmb_akun") else None)
            akun = services.get_account(cid, kode) if kode else None
            nama = (f"Buku Besar · {akun['kode']} {akun['nama']}"
                    if akun else "Buku Besar")
            baris = [["Tanggal", "No. Bukti", "Keterangan", "Debit", "Kredit",
                      "Saldo"]]
            data = (services.buku_besar(cid, kode, tahun, bulan)
                    if kode else [])
            for d in data:
                baris.append([
                    d["tanggal"] if not d.get("awal") else "",
                    d["no_bukti"], d["keterangan"], d["debit"], d["kredit"],
                    d["saldo"],
                ])
            if len(baris) > 1:
                baris.append(["", "", "TOTAL MUTASI",
                              sum(d["debit"] for d in data),
                              sum(d["kredit"] for d in data),
                              data[-1]["saldo"]])
            hasil.append((nama, baris))

        if bagian is None:
            jurnal = services.list_jurnal(cid, tahun, bulan, limit=5000)
            baris = [["Tanggal", "No. Bukti", "Keterangan", "Debit", "Kredit"]]
            for e in jurnal:
                baris.append([e["tanggal"], e["no_bukti"], e["keterangan"],
                              e["total_debit"], e["total_kredit"]])
            hasil.append(("Jurnal", baris))

        return hasil

    def _data_laporan_aktif(self):
        """Ambil laporan pada tab yang sedang dibuka, siap dicetak."""
        nama = PETA_TAB.get(self.tabs.currentIndex())
        if not nama:
            return []
        try:
            data = self._kumpulkan_data_ekspor(nama)
        except Exception as e:
            popup.galat(self, "Gagal menyiapkan data", str(e))
            return []
        if not data or len(data[0][1]) <= 1:
            popup.beri_tahu(self,
                            "Belum ada data",
                            f"Laporan {nama} belum memiliki data untuk dicetak.")
            return []
        return data

    def _judul_dan_subjudul(self):
        cid = self.ctx.company_id
        if not cid:
            return None
        comp = services.get_company(cid)
        tahun, bulan = self.ctx.tahun, self.periode()
        periode = (f"{config.MONTH_NAMES_ID[bulan - 1]} {tahun}"
                   if bulan else f"Tahun {tahun}")
        nama = PETA_TAB.get(self.tabs.currentIndex(), "Laporan")
        sub = f"Periode {periode} · NPWP {comp['npwp'] or '-'}"
        return comp, nama, sub, periode

    def _ekspor(self):
        info = self._judul_dan_subjudul()
        if not info:
            popup.beri_tahu(self,
                            "Belum ada perusahaan",
                            "Buat profil perusahaan terlebih dahulu.")
            return
        comp, nama, sub, periode = info
        data = self._data_laporan_aktif()
        if not data:
            return
        from ..ekspor_cetak import ekspor_halaman
        ekspor_halaman(
            self, nama, sub, data,
            nama_berkas=f"{nama}_{comp['nama']}_{periode}",
            perusahaan=comp["nama"],
            penanda={"nama": getattr(self.ctx, "full_name", "")
                             or getattr(self.ctx, "username", ""),
                     "kota": comp.get("kota", "")})

    def _cetak(self):
        info = self._judul_dan_subjudul()
        if not info:
            popup.beri_tahu(self,
                            "Belum ada perusahaan",
                            "Buat profil perusahaan terlebih dahulu.")
            return
        comp, nama, sub, _ = info
        data = self._data_laporan_aktif()
        if not data:
            return
        from ..ekspor_cetak import cetak_halaman
        cetak_halaman(self, nama, sub, data, perusahaan=comp["nama"],
                      penanda={"nama": getattr(self.ctx, "full_name", "")
                                       or getattr(self.ctx, "username", ""),
                               "kota": comp.get("kota", "")})
