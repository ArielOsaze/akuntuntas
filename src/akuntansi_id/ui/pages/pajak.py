"""
AkunTuntas - Halaman Perpajakan
================================
  • PPh Badan (Pasal 31E / Final UMKM)
  • PPN (rekap bulanan & SPT Masa)
  • Pajak Potong/Pungut
  • Rekonsiliasi Fiskal
  • Kalender & Tenggat Pajak
  • Kalkulator Sanksi
"""
from __future__ import annotations

from datetime import date, datetime

from PySide6.QtCore import Qt, Signal, QDate
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QTabWidget,
    QDialog, QMessageBox, QFrame, QGridLayout, QDateEdit, QLineEdit,
    QSpinBox,
)

from ... import config, coa, services
from ...core import accounting as acc
from ...core import tax_engine as tx
from .. import theme
from .. import kalender
from ..theme import C
from .. import widgets as w


# ==========================================================================
# HALAMAN PAJAK UTAMA
# ==========================================================================
class PajakPage(QWidget):
    pindah_halaman = Signal(str)

    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx

        luar = QVBoxLayout(self)
        luar.setContentsMargins(0, 0, 0, 0)
        luar.setSpacing(0)

        self.header = w.PageHeader(
            "Perpajakan",
            "Perhitungan PPh Badan, PPN, potong/pungut, dan rekonsiliasi fiskal.")

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
        wl.setContentsMargins(22, 16, 22, 22)
        wl.addWidget(self.tabs)
        luar.addWidget(wadah, 1)

        self.tab_pph_badan = QWidget()
        self.tab_ppn = QWidget()
        self.tab_potput = QWidget()
        self.tab_rekon = QWidget()
        self.tab_kalender = QWidget()
        self.tab_sanksi = QWidget()

        self.tabs.addTab(self.tab_pph_badan, "PPh Badan")
        self.tabs.addTab(self.tab_ppn, "PPN")
        self.tabs.addTab(self.tab_potput, "Potong/Pungut")
        self.tabs.addTab(self.tab_rekon, "Rekonsiliasi Fiskal")
        self.tabs.addTab(self.tab_kalender, "Kalender Pajak")
        self.tabs.addTab(self.tab_sanksi, "Kalkulator Sanksi")
        self.tabs.currentChanged.connect(self.muat)

        for t in (self.tab_pph_badan, self.tab_ppn, self.tab_potput,
                  self.tab_rekon, self.tab_kalender, self.tab_sanksi):
            l = QVBoxLayout(t)
            l.setContentsMargins(0, 12, 0, 0)
            l.setSpacing(13)

    def _ganti_tahun(self):
        self.ctx.tahun = self.cmb_tahun.currentData()
        self.muat()

    def muat(self):
        if not self.ctx.company_id:
            idx = self.tabs.currentIndex()
            tabs = [self.tab_pph_badan, self.tab_ppn, self.tab_potput,
                    self.tab_rekon, self.tab_kalender, self.tab_sanksi]
            lay = self._bersihkan(tabs[idx])
            lay.addWidget(w.InfoBanner(
                "Belum ada perusahaan. Buat profil perusahaan terlebih dahulu.",
                "warning", "Data belum tersedia"))
            return
        idx = self.tabs.currentIndex()
        if idx == 0:
            self._isi_pph_badan()
        elif idx == 1:
            self._isi_ppn()
        elif idx == 2:
            self._isi_potput()
        elif idx == 3:
            self._isi_rekon()
        elif idx == 4:
            self._isi_kalender()
        else:
            self._isi_sanksi()

    def _bersihkan(self, widget):
        """
        Kosongkan isi tab dan kembalikan tata letak tempat mengisi ulang.

        Area gulir dibuat sekali lalu dipakai terus; hanya isinya yang
        diganti. Isi panjang (penjelasan pajak, tabel besar) tetap dapat
        dijangkau pada jendela pendek tanpa ada label yang terpotong.
        """
        if not hasattr(widget, "_area_gulir"):
            wadah = QWidget()
            isi = QVBoxLayout(wadah)
            isi.setContentsMargins(0, 0, 0, 0)
            isi.setSpacing(13)
            lama = widget.layout()
            lama.addWidget(w.scroll(wadah))
            widget._area_gulir = wadah
            widget._isi_gulir = isi
            return isi

        isi = widget._isi_gulir
        while isi.count():
            it = isi.takeAt(0)
            wdg = it.widget()
            if wdg is not None:
                wdg.setParent(None)
                wdg.deleteLater()
            elif it.layout() is not None:
                self._bersihkan_layout(it.layout())
        return isi

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
    # PPH BADAN
    # ==================================================================
    def _isi_pph_badan(self):
        lay = self._bersihkan(self.tab_pph_badan)
        cid, tahun = self.ctx.company_id, self.ctx.tahun

        try:
            hasil = services.hitung_pph_badan_tahunan(cid, tahun)
        except Exception as e:
            lay.addWidget(w.InfoBanner(f"Gagal menghitung: {e}", "danger", "Kesalahan"))
            return

        # banner skema
        if hasil["pakai_final"]:
            lay.addWidget(w.InfoBanner(
                "Perusahaan memakai skema PPh Final UMKM 0,5%. Skema ini hanya berlaku "
                "bila memenuhi syarat bentuk badan, batas peredaran bruto, dan periode "
                "pemanfaatan sesuai PP 20/2026.",
                "info", "Skema: PPh Final UMKM 0,5%"))
        else:
            lay.addWidget(w.InfoBanner(
                "Perusahaan memakai ketentuan umum PPh Badan. Tarif 22% dengan fasilitas "
                "Pasal 31E: pengurangan 50% tarif atas PKP dari bagian peredaran bruto "
                "sampai Rp4,8 miliar, untuk badan dengan peredaran bruto sampai Rp50 miliar.",
                "info", "Skema: Ketentuan Umum / Pasal 31E"))

        # KPI
        kartu = w.Card()
        baris = QHBoxLayout()
        baris.setSpacing(28)
        baris.addWidget(w.MiniStat("Peredaran Bruto", theme.money(hasil["omzet"])))
        rekon = hasil["rekon"]
        baris.addWidget(w.MiniStat("PKP (Fiskal)", theme.money(rekon.pkp)))
        baris.addWidget(w.MiniStat("PPh Terutang", theme.money(hasil["pph_terutang"]),
                                   C.PRIMARY))
        baris.addWidget(w.MiniStat("Kredit Pajak", theme.money(hasil["kredit"]),
                                   C.SUCCESS))
        kb = hasil["kurang_lebih"]
        baris.addWidget(w.MiniStat("Kurang/(Lebih) Bayar", theme.money(kb),
                                   C.NEGATIF if kb > 0 else C.SUCCESS))
        baris.addStretch()
        kartu.body().addLayout(baris)
        lay.addWidget(kartu)

        # rincian perhitungan
        t = w.Tabel([("Uraian", -1), ("Jumlah (Rp)", 200), ("Keterangan", 380)])
        # Keterangan ini tampil saat tabel masih kosong, supaya
        # pengguna tahu langkah berikutnya.
        t.set_pesan_kosong(
            "Belum ada data perpajakan."
            "\n\n"
            "Catat dulu transaksi pada menu Jurnal Umum atau Penjualan. "
            "Perhitungan pajak akan muncul di sini.")

        baris_t, warna = [], {}

        def tambah(u, n, ket="", tebal=False, uang=True):
            idx = len(baris_t)
            baris_t.append([u, theme.money(n) if uang else str(n), ket])
            if tebal:
                warna[idx] = C.PRIMARY

        tambah("Peredaran Bruto (omzet)", hasil["omzet"],
               "Total pendapatan usaha dari jurnal", True)
        tambah("Batas wajib PKP", config.THRESHOLD_PKP,
               "PMK 197/2013 - Rp4,8 miliar")
        tambah("Batas fasilitas Pasal 31E", config.THRESHOLD_31E,
               "UU PPh Pasal 31E - Rp50 miliar")
        tambah("", "", "")
        tambah("Laba Komersial sebelum Pajak", rekon.laba_komersial,
               "Dari Laporan Laba Rugi", True)
        tambah("Koreksi Positif - Non-Deductible", rekon.koreksi_positif_otomatis,
               "Pasal 9 UU PPh: biaya yang tidak boleh dikurangkan")
        tambah("Koreksi Positif - Penyusutan", rekon.koreksi_positif_penyusutan,
               "Penyusutan komersial > fiskal (PMK 72/2023)")
        tambah("Koreksi Positif Manual", rekon.koreksi_positif_manual, "Input pengguna")
        tambah("Koreksi Negatif - Penghasilan Final", -rekon.koreksi_negatif_otomatis,
               "Penghasilan yang sudah dikenai PPh Final")
        tambah("Koreksi Negatif - Penyusutan", -rekon.koreksi_negatif_penyusutan,
               "Penyusutan fiskal > komersial")
        tambah("Koreksi Negatif Manual", -rekon.koreksi_negatif_manual, "Input pengguna")
        tambah("Penghasilan Neto Fiskal", rekon.neto_fiskal, "", True)
        tambah("Kompensasi Kerugian Fiskal", -rekon.kompensasi_rugi,
               "Pasal 6 ayat (2) UU PPh - maksimal 5 tahun")
        tambah("PENGHASILAN KENA PAJAK", rekon.pkp,
               "Dibulatkan ke ribuan penuh ke bawah - Pasal 17 ayat (4) UU PPh", True)

        if not hasil["pakai_final"]:
            h = hasil["hasil"]
            tambah("", "", "")
            tambah("PKP mendapat fasilitas (tarif 11%)", h.pkp_fasilitas, h.skema)
            tambah("PKP tanpa fasilitas (tarif 22%)", h.pkp_non_fasilitas, "")
            tambah("PPh dari bagian fasilitas", h.pph_fasilitas, "11% × PKP fasilitas")
            tambah("PPh dari bagian non-fasilitas", h.pph_non_fasilitas,
                   "22% × PKP non-fasilitas")
            tambah("PPh Badan Terutang", h.pph_terutang, h.skema, True)
            tambah("Tarif efektif", h.tarif_efektif * 100,
                   "Persentase PPh terutang terhadap PKP", False)
            tambah("Kredit PPh 22/23 (dipotong pihak lain)", -hasil.get("kredit_23", 0),
                   "Dari register potong/pungut")
            tambah("Kredit PPh 25 (angsuran disetor)", -hasil.get("kredit_25", 0),
                   "Dari catatan pembayaran pajak")
            tambah("PPh Kurang/(Lebih) Bayar", h.kurang_lebih_bayar,
                   "Pasal 29 UU PPh - dibayar sebelum SPT disampaikan", True)
            tambah("Angsuran PPh 25 tahun berikutnya", h.pph25_bulanan,
                   "Per bulan, disetor paling lambat tanggal 15", True)
        else:
            f = hasil["final"]
            tambah("", "", "")
            tambah("Dasar Pengenaan PPh Final", f.dasar_pengenaan,
                   "Bagian peredaran bruto yang dikenai pajak")
            tambah("Tarif PPh Final", 0.5, "PP 20/2026", False)
            tambah("PPh Final Terutang", hasil["pph_terutang"],
                   "Setor paling lambat tanggal 15 bulan berikutnya", True)
            tambah("Sudah disetor", -hasil["kredit"], "Dari catatan pembayaran pajak")
            tambah("Kurang/(Lebih) Bayar", hasil["kurang_lebih"], "", True)

        t.isi(baris_t, warna_baris=warna, align_kanan={1})
        t.setMinimumHeight(420)
        lay.addWidget(t)

        # peringatan
        for p in hasil.get("peringatan", []):
            lay.addWidget(w.InfoBanner(p, "warning", "Perhatian"))

        if self.ctx.beginner:
            lay.addWidget(w.HelpPanel(
                coa.HELP_TOPICS["pph_badan"]["judul"],
                coa.HELP_TOPICS["pph_badan"]["isi"],
                coa.HELP_TOPICS["pph_badan"]["dasar_hukum"]))

        lay.addStretch()

    # ==================================================================
    # PPN
    # ==================================================================
    def _isi_ppn(self):
        lay = self._bersihkan(self.tab_ppn)
        cid, tahun = self.ctx.company_id, self.ctx.tahun
        comp = services.get_company(cid)

        omzet = acc.omzet_setahun(cid, tahun)
        st = tx.status_pkp(omzet, bool(comp["status_pkp"]))
        lay.addWidget(w.InfoBanner(st["pesan"], st["level"],
                                   f"Status PKP: {st['status']}"))

        data = acc.rekap_ppn_bulanan(cid, tahun)

        t = w.Tabel([
            ("Masa", 105), ("PPN Keluaran", 155), ("PPN Masukan Kredit", 165),
            ("Kurang Bayar", 150), ("Lebih Bayar", 140), ("Disetor", 140),
            ("Sisa", 140), ("Status", 130),
        ])
        # Keterangan ini tampil saat tabel masih kosong, supaya
        # pengguna tahu langkah berikutnya.
        t.set_pesan_kosong(
            "Belum ada data perpajakan."
            "\n\n"
            "Catat dulu transaksi pada menu Jurnal Umum atau Penjualan. "
            "Perhitungan pajak akan muncul di sini.")

        baris, warna = [], {}
        for i, d in enumerate(data):
            idx = len(baris)
            baris.append([
                d["nama"], theme.money(d["ppn_keluaran"]),
                theme.money(d["ppn_masukan_kredit"]),
                theme.money(d["kurang_bayar"]) if d["kurang_bayar"] else "",
                theme.money(d["lebih_bayar"]) if d["lebih_bayar"] else "",
                theme.money(d["dibayar"]),
                theme.money(d["sisa"]) if d["sisa"] else "",
                d["status"],
            ])
            if d["kurang_bayar"] > d["dibayar"]:
                warna[idx] = C.WARNING
            elif d["lebih_bayar"] > 0:
                warna[idx] = C.SUCCESS

        tk = sum(d["ppn_keluaran"] for d in data)
        tm = sum(d["ppn_masukan_kredit"] for d in data)
        tkb = sum(d["kurang_bayar"] for d in data)
        tlb = sum(d["lebih_bayar"] for d in data)
        idx_total = len(baris)
        baris.append(["TOTAL", theme.money(tk), theme.money(tm), theme.money(tkb),
                      theme.money(tlb), "", "", ""])
        warna[idx_total] = C.PRIMARY

        t.isi(baris, warna_baris=warna, align_kanan={1, 2, 3, 4, 5, 6})
        t.setMinimumHeight(400)
        lay.addWidget(t)

        kartu = w.Card()
        b = QHBoxLayout()
        b.setSpacing(30)
        b.addWidget(w.MiniStat("PPN Keluaran Setahun", theme.money(tk)))
        b.addWidget(w.MiniStat("PPN Masukan Dikreditkan", theme.money(tm)))
        b.addWidget(w.MiniStat("Total Kurang Bayar", theme.money(tkb), C.NEGATIF))
        b.addWidget(w.MiniStat("Total Lebih Bayar", theme.money(tlb), C.SUCCESS))
        b.addStretch()
        kartu.body().addLayout(b)
        lay.addWidget(kartu)

        if self.ctx.beginner:
            lay.addWidget(w.HelpPanel(
                coa.HELP_TOPICS["ppn"]["judul"],
                coa.HELP_TOPICS["ppn"]["isi"],
                coa.HELP_TOPICS["ppn"]["dasar_hukum"]))
        lay.addStretch()

    # ==================================================================
    # POTONG/PUNGUT
    # ==================================================================
    def _isi_potput(self):
        lay = self._bersihkan(self.tab_potput)
        cid, tahun = self.ctx.company_id, self.ctx.tahun

        baris_aksi = QHBoxLayout()
        baris_aksi.setSpacing(9)
        b_tambah = w.tombol("Catat Pemotongan Pajak", gaya="primary", ikon="tambah")
        b_tambah.clicked.connect(self._tambah_potput)
        baris_aksi.addWidget(b_tambah)
        b_bayar = w.tombol("Catat Setoran Pajak", gaya="success", ikon="simpan")
        b_bayar.clicked.connect(self._catat_setoran)
        baris_aksi.addWidget(b_bayar)
        b_hapus = w.tombol("Hapus", gaya="danger", ikon="hapus")
        b_hapus.clicked.connect(self._hapus_potput)
        baris_aksi.addWidget(b_hapus)
        baris_aksi.addStretch()
        lay.addLayout(baris_aksi)

        h = None
        if self.ctx.beginner:
            h = w.HelpPanel(coa.HELP_TOPICS["pajak"]["judul"],
                            coa.HELP_TOPICS["pajak"]["isi"],
                            coa.HELP_TOPICS["pajak"]["dasar_hukum"])
            lay.addWidget(h)

        # register pemotongan
        lay.addWidget(w.label("Register Pemotongan / Pemungutan", objek="SectionTitle"))
        data = services.list_pajak(cid, tahun)
        t = w.Tabel([
            ("Tanggal", 100), ("Masa", 90), ("Kode", 130), ("Jenis", -1),
            ("DPP", 140), ("Tarif", 75), ("Pajak", 135), ("Status", 105),
        ])
        # Keterangan ini tampil saat tabel masih kosong, supaya
        # pengguna tahu langkah berikutnya.
        t.set_pesan_kosong(
            "Belum ada data perpajakan."
            "\n\n"
            "Catat dulu transaksi pada menu Jurnal Umum atau Penjualan. "
            "Perhitungan pajak akan muncul di sini.")

        baris, warna = [], {}
        for i, r in enumerate(data):
            idx = len(baris)
            baris.append([
                theme.tanggal_id(r["tanggal"]), r["masa"], r["kode_pajak"],
                r["jenis"], theme.money(r["dpp"]),
                f"{r['tarif_dipakai'] * 100:.2f}%", theme.money(r["pajak"]),
                r["status"],
            ])
            if r["status"] == "Terutang":
                warna[idx] = C.WARNING
        t.isi(baris, warna_baris=warna, align_kanan={4, 5, 6})
        t.setMinimumHeight(230)
        lay.addWidget(t)

        # pembayaran
        lay.addWidget(w.label("Riwayat Setoran Pajak", objek="SectionTitle"))
        bayar = services.list_pembayaran_pajak(cid, tahun)
        t2 = w.Tabel([
            ("Tanggal Bayar", 120), ("Jenis Pajak", 130), ("Masa", 95),
            ("Jumlah", 150), ("NTPN", 190), ("Cara Bayar", 130), ("Catatan", -1),
        ])
        # Keterangan ini tampil saat tabel masih kosong, supaya
        # pengguna tahu langkah berikutnya.
        t2.set_pesan_kosong(
            "Belum ada data perpajakan."
            "\n\n"
            "Catat dulu transaksi pada menu Jurnal Umum atau Penjualan. "
            "Perhitungan pajak akan muncul di sini.")

        baris2 = [[
            theme.tanggal_id(b["tanggal_bayar"]), b["jenis_pajak"], b["masa"],
            theme.money(b["jumlah"]), b["ntpn"], b["cara_bayar"], b["catatan"],
        ] for b in bayar]
        t2.isi(baris2, align_kanan={3})
        t2.setMinimumHeight(210)
        lay.addWidget(t2)

        # ringkasan
        total_potong = sum(r["pajak"] for r in data)
        total_setor = sum(b["jumlah"] for b in bayar)
        terutang = sum(r["pajak"] for r in data if r["status"] == "Terutang")

        kartu = w.Card()
        b = QHBoxLayout()
        b.setSpacing(30)
        b.addWidget(w.MiniStat("Total Dipotong/Dipungut", theme.money(total_potong)))
        b.addWidget(w.MiniStat("Total Disetor", theme.money(total_setor), C.SUCCESS))
        b.addWidget(w.MiniStat("Masih Terutang", theme.money(terutang),
                               C.DANGER if terutang else C.SUCCESS))
        b.addStretch()
        kartu.body().addLayout(b)
        lay.addWidget(kartu)
        lay.addStretch()

    def _tambah_potput(self):
        cid = self.ctx.company_id
        if not cid:
            return
        d = DialogPotPut(self.ctx, self)
        if d.exec():
            self.muat()

    def _catat_setoran(self):
        cid = self.ctx.company_id
        if not cid:
            return
        d = DialogSetoranPajak(self.ctx, self)
        if d.exec():
            self.muat()

    def _hapus_potput(self):
        QMessageBox.information(self, "Pilih data",
                                "Pilih baris pada tabel register, lalu gunakan tombol Hapus "
                                "pada baris tersebut.")

    # ==================================================================
    # REKONSILIASI FISKAL
    # ==================================================================
    def _isi_rekon(self):
        lay = self._bersihkan(self.tab_rekon)
        cid, tahun = self.ctx.company_id, self.ctx.tahun

        try:
            rekon = services.hitung_rekonsiliasi(cid, tahun)
        except Exception as e:
            lay.addWidget(w.InfoBanner(f"Gagal menghitung: {e}", "danger", "Kesalahan"))
            return

        lay.addWidget(w.InfoBanner(
            "Rekonsiliasi fiskal menjembatani laba komersial (menurut SAK) dengan "
            "laba fiskal (menurut pajak). Perbedaan muncul karena aturan pajak tidak "
            "selalu sama dengan standar akuntansi.",
            "info", "Tentang Rekonsiliasi Fiskal"))

        t = w.Tabel([("Uraian", -1), ("Jumlah (Rp)", 200), ("Keterangan", 420)])
        # Keterangan ini tampil saat tabel masih kosong, supaya
        # pengguna tahu langkah berikutnya.
        t.set_pesan_kosong(
            "Belum ada data perpajakan."
            "\n\n"
            "Catat dulu transaksi pada menu Jurnal Umum atau Penjualan. "
            "Perhitungan pajak akan muncul di sini.")

        baris, warna = [], {}
        for uraian, nilai, ket in rekon.rincian:
            idx = len(baris)
            tebal = uraian.isupper() or "PENGHASILAN KENA PAJAK" in uraian
            baris.append([uraian, theme.money(nilai), ket])
            if tebal:
                warna[idx] = C.PRIMARY
        t.isi(baris, warna_baris=warna, align_kanan={1})
        t.setMinimumHeight(400)
        lay.addWidget(t)

        for catatan in rekon.catatan:
            lay.addWidget(w.InfoBanner(catatan, "warning", "Perhatian"))

        # koreksi manual
        lay.addWidget(w.label("Koreksi Manual", objek="SectionTitle"))
        b = QHBoxLayout()
        b.setSpacing(9)
        b_tambah = w.tombol("Tambah Koreksi Manual", ikon="tambah")
        b_tambah.clicked.connect(self._tambah_koreksi)
        b.addWidget(b_tambah)
        b.addStretch()
        lay.addLayout(b)

        manual = services.list_koreksi_manual(cid, tahun)
        t2 = w.Tabel([("Uraian", -1), ("Jenis", 110), ("Nilai", 150),
                      ("Dokumen", 200), ("", 90)])
        # Keterangan ini tampil saat tabel masih kosong, supaya
        # pengguna tahu langkah berikutnya.
        t2.set_pesan_kosong(
            "Belum ada data perpajakan."
            "\n\n"
            "Catat dulu transaksi pada menu Jurnal Umum atau Penjualan. "
            "Perhitungan pajak akan muncul di sini.")

        baris2, warna2 = [], {}
        for i, m in enumerate(manual):
            idx = len(baris2)
            baris2.append([m["uraian"], m["jenis"], theme.money(m["nilai"]),
                           m["dokumen"], "Hapus"])
            warna2[idx] = C.POSITIF if m["jenis"] == "Positif" else C.NEGATIF
        t2.isi(baris2, warna_baris=warna2, align_kanan={2})
        t2.setMinimumHeight(160)
        t2.cellClicked.connect(lambda r, c: self._hapus_koreksi(r) if c == 4 else None)
        lay.addWidget(t2)

        # akun review fiskal
        ns = services.laporan_neraca_saldo(cid, tahun)
        review = [d for d in ns if d.perlakuan_fiskal == "Review Fiskal"
                  and d.saldo_akhir_normal != 0]
        if review:
            lay.addWidget(w.InfoBanner(
                f"Terdapat {len(review)} akun berstatus 'Review Fiskal' yang perlu "
                "ditinjau manual. Akun-akun ini mungkin deductible atau tidak, "
                "tergantung dokumen pendukung dan kondisi transaksi.",
                "warning", "Akun perlu tinjauan manual"))
            t3 = w.Tabel([("Kode", 90), ("Nama Akun", -1), ("Saldo", 160),
                          ("Catatan", 400)])
            # Keterangan ini tampil saat tabel masih kosong, supaya
            # pengguna tahu langkah berikutnya.
            t3.set_pesan_kosong(
                "Belum ada data perpajakan."
                "\n\n"
                "Catat dulu transaksi pada menu Jurnal Umum atau Penjualan. "
                "Perhitungan pajak akan muncul di sini.")

            baris3 = [[d.kode, d.nama, theme.money(d.saldo_akhir_normal),
                       "Perlu ditinjau: pastikan ada dokumen pendukung"] for d in review]
            t3.isi(baris3, align_kanan={2})
            t3.setMinimumHeight(150)
            lay.addWidget(t3)

        if self.ctx.beginner:
            lay.addWidget(w.HelpPanel(
                coa.HELP_TOPICS["rekonsiliasi"]["judul"],
                coa.HELP_TOPICS["rekonsiliasi"]["isi"],
                coa.HELP_TOPICS["rekonsiliasi"]["dasar_hukum"]))
        lay.addStretch()

    def _tambah_koreksi(self):
        d = DialogKoreksiManual(self.ctx, self)
        if d.exec():
            self.muat()

    def _hapus_koreksi(self, baris: int):
        manual = services.list_koreksi_manual(self.ctx.company_id, self.ctx.tahun)
        if baris < len(manual):
            m = manual[baris]
            if QMessageBox.question(
                    self, "Konfirmasi",
                    f"Hapus koreksi manual '{m['uraian']}'?",
                    QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
                services.hapus_koreksi_manual(m["id"])
                self.muat()

    # ==================================================================
    # KALENDER PAJAK
    # ==================================================================
    def _isi_kalender(self):
        lay = self._bersihkan(self.tab_kalender)
        cid = self.ctx.company_id

        lay.addWidget(w.InfoBanner(
            "Kalender ini menampilkan tenggat setor dan lapor berdasarkan aturan umum "
            "UU KUP. Tenggat yang jatuh pada hari libur umumnya bergeser ke hari kerja "
            "berikutnya - selalu periksa kalender resmi DJP.",
            "info", "Cara membaca kalender"))

        data = services.deadline_pajak(cid)
        t = w.Tabel([("Tenggat", 130), ("Hari", 105), ("Kewajiban", -1),
                     ("Masa", 130), ("Sanksi Bila Terlambat", 380),
                     ("Dasar Hukum", 320)])
        # Keterangan ini tampil saat tabel masih kosong, supaya
        # pengguna tahu langkah berikutnya.
        t.set_pesan_kosong(
            "Belum ada data perpajakan."
            "\n\n"
            "Catat dulu transaksi pada menu Jurnal Umum atau Penjualan. "
            "Perhitungan pajak akan muncul di sini.")

        baris, warna = [], {}
        for i, d in enumerate(data):
            idx = len(baris)
            hari = d["hari_tersisa"]
            if hari < 0:
                teks_hari, warna[idx] = f"Lewat {abs(hari)} hari", C.DANGER
            elif hari <= 7:
                teks_hari, warna[idx] = f"{hari} hari", C.WARNING
            else:
                teks_hari = f"{hari} hari"
            baris.append([
                theme.tanggal_id(d["tenggat"]), teks_hari, d["nama"], d["masa"],
                d["sanksi"], d["dasar_hukum"],
            ])
        t.isi(baris, warna_baris=warna, align_kanan=set())
        t.setMinimumHeight(400)
        lay.addWidget(t)

        # referensi aturan
        lay.addWidget(w.label("Referensi Aturan", objek="SectionTitle"))
        ref = w.Card()
        for topik, isi, hukum in [
            ("Tarif PPh Badan", "22% untuk tahun pajak 2022 dan seterusnya.",
             "UU No. 7/2021 (UU HPP) Pasal 17 ayat (1) huruf b"),
            ("Fasilitas Pasal 31E", "Pengurangan 50% tarif atas PKP dari bagian "
             "peredaran bruto sampai Rp4,8 miliar, untuk badan dengan peredaran "
             "bruto sampai Rp50 miliar.", "UU PPh Pasal 31E; SE-02/PJ/2015"),
            ("PPh Final UMKM 0,5%", "Untuk WP dengan peredaran bruto sampai Rp4,8 "
             "miliar, dengan syarat bentuk badan dan periode tertentu.",
             "PP 55/2022 jo. PP 20/2026"),
            ("PPN", "12% × DPP Nilai Lain (11/12) = efektif 11% untuk non-mewah; "
             "12% DPP penuh untuk objek mewah tertentu.",
             "UU HPP Pasal 7; PMK 131/2024"),
            ("Batas Wajib PKP", "Peredaran bruto melebihi Rp4,8 miliar setahun.",
             "PMK 197/PMK.03/2013; PP 44/2022"),
            ("Penyusutan Fiskal", "Kelompok 1 (4 thn) 25%/50%; Kelompok 2 (8 thn) "
             "12,5%/25%; Kelompok 3 (16 thn) 6,25%/12,5%; Kelompok 4 (20 thn) "
             "5%/10%; bangunan permanen 5%, non-permanen 10%.",
             "PMK 72/PMK.03/2023"),
            ("Denda Telat Lapor", "SPT Masa PPN Rp100.000; SPT Masa lainnya "
             "Rp100.000; SPT Tahunan Badan Rp1.000.000; SPT Tahunan OP Rp100.000.",
             "Pasal 7 UU KUP"),
            ("Bunga Telat Setor", "Suku bunga acuan + 10%, dibagi 12, dikalikan "
             "jumlah bulan keterlambatan.", "UU HPP Pasal 9 ayat (2a)/(2b); PMK 81/2024"),
            ("Sanksi Kurang Bayar", "Bunga 2% per bulan, maksimal 24 bulan.",
             "Pasal 13 ayat (2) UU KUP"),
            ("Kewajiban Pembukuan", "WP Badan wajib menyelenggarakan pembukuan. "
             "Dokumen wajib disimpan 10 tahun.", "Pasal 28 UU KUP; UU No. 8/1997"),
            ("Sanksi Tidak Membukukan", "Pidana penjara 6 bulan - 6 tahun dan denda "
             "2x - 4x pajak yang tidak/kurang dibayar.", "Pasal 39 UU KUP"),
            ("PPh 21 - TER", "Tarif Efektif Rata-rata bulanan kategori A/B/C "
             "berdasarkan status PTKP; penghitungan setahun pada masa Desember.",
             "PMK 168/PMK.03/2023; PP 58/2023"),
        ]:
            r = QWidget()
            rl = QVBoxLayout(r)
            rl.setContentsMargins(0, 6, 0, 6)
            rl.setSpacing(2)
            a = QLabel(topik)
            a.setStyleSheet(f"font-weight: 700; font-size: {theme.FS_BODY}px; "
                            "background: transparent;")
            rl.addWidget(a)
            b = QLabel(isi)
            b.setWordWrap(True)
            b.setStyleSheet(f"font-size: {theme.FS_SMALL}px; color: {C.TEXT}; "
                            "background: transparent;")
            rl.addWidget(b)
            c = QLabel(f" {hukum}")
            c.setWordWrap(True)
            c.setStyleSheet(f"font-size: {theme.FS_TINY}px; color: {C.PRIMARY_DARK}; "
                            "font-style: italic; background: transparent;")
            rl.addWidget(c)
            ref.body().addWidget(r)
            ref.body().addWidget(w.divider())
        lay.addWidget(ref)
        lay.addStretch()

    # ==================================================================
    # KALKULATOR SANKSI
    # ==================================================================
    def _isi_sanksi(self):
        lay = self._bersihkan(self.tab_sanksi)

        lay.addWidget(w.InfoBanner(
            "Kalkulator ini membantu memperkirakan sanksi administrasi bila terjadi "
            "keterlambatan atau kekurangan pembayaran pajak. Gunakan untuk perencanaan, "
            "bukan sebagai dasar resmi - nilai final ditetapkan dalam surat ketetapan.",
            "info", "Tentang kalkulator"))

        # --- bunga keterlambatan
        k1 = w.Card()
        k1.body().addWidget(w.label("Bunga Keterlambatan Pembayaran",
                                    objek="SectionTitle"))
        g1 = QGridLayout()
        g1.setSpacing(12)
        g1.addWidget(w.label("Jumlah pajak yang terlambat dibayar (Rp)",
                             objek="FormLabel"), 0, 0, 1, 2)
        self.inp_pajak = w.InputRupiah()
        self.inp_pajak.valueChanged.connect(self._hitung_sanksi)
        g1.addWidget(self.inp_pajak, 1, 0, 1, 2)

        g1.addWidget(w.label("Jumlah bulan keterlambatan", objek="FormLabel"), 0, 2)
        self.spin_bulan = QSpinBox()
        self.spin_bulan.setRange(1, 60)
        self.spin_bulan.setValue(3)
        self.spin_bulan.valueChanged.connect(self._hitung_sanksi)
        g1.addWidget(self.spin_bulan, 1, 2)

        g1.addWidget(w.label("Suku bunga acuan BI (%)", objek="FormLabel"), 0, 3)
        self.inp_suku = QLineEdit(f"{config.BI_REFERENCE_RATE * 100:g}")
        self.inp_suku.textChanged.connect(self._hitung_sanksi)
        g1.addWidget(self.inp_suku, 1, 3)
        k1.body().addLayout(g1)

        self.lbl_bunga = QLabel("")
        self.lbl_bunga.setWordWrap(True)
        self.lbl_bunga.setStyleSheet(f"font-size: {theme.FS_BODY}px; "
                                     "background: transparent;")
        k1.body().addWidget(self.lbl_bunga)
        lay.addWidget(k1)

        # --- denda telat lapor
        k2 = w.Card()
        k2.body().addWidget(w.label("Denda Terlambat Melaporkan SPT",
                                    objek="SectionTitle"))
        g2 = QGridLayout()
        g2.setSpacing(12)
        g2.addWidget(w.label("Jenis SPT", objek="FormLabel"), 0, 0)
        self.cmb_spt = QComboBox()
        for kode, nama in [("ppn", "SPT Masa PPN"), ("pph21", "SPT Masa PPh 21"),
                           ("pph23", "SPT Masa PPh 23/26"),
                           ("pph4", "SPT Masa PPh 4(2)"),
                           ("pph25", "SPT Masa PPh 25"),
                           ("badan", "SPT Tahunan PPh Badan"),
                           ("op", "SPT Tahunan PPh Orang Pribadi")]:
            self.cmb_spt.addItem(nama, kode)
        self.cmb_spt.currentIndexChanged.connect(self._hitung_sanksi)
        g2.addWidget(self.cmb_spt, 1, 0)

        g2.addWidget(w.label("Jumlah SPT terlambat", objek="FormLabel"), 0, 1)
        self.spin_jumlah_spt = QSpinBox()
        self.spin_jumlah_spt.setRange(1, 36)
        self.spin_jumlah_spt.setValue(1)
        self.spin_jumlah_spt.valueChanged.connect(self._hitung_sanksi)
        g2.addWidget(self.spin_jumlah_spt, 1, 1)
        k2.body().addLayout(g2)

        self.lbl_denda = QLabel("")
        self.lbl_denda.setWordWrap(True)
        self.lbl_denda.setStyleSheet(f"font-size: {theme.FS_BODY}px; "
                                     "background: transparent;")
        k2.body().addWidget(self.lbl_denda)
        lay.addWidget(k2)

        # --- sanksi SKPKB
        k3 = w.Card()
        k3.body().addWidget(w.label("Sanksi atas Kurang Bayar (SKPKB)",
                                    objek="SectionTitle"))
        g3 = QGridLayout()
        g3.setSpacing(12)
        g3.addWidget(w.label("Pajak kurang bayar (Rp)", objek="FormLabel"), 0, 0)
        self.inp_kb = w.InputRupiah()
        self.inp_kb.valueChanged.connect(self._hitung_sanksi)
        g3.addWidget(self.inp_kb, 1, 0)
        g3.addWidget(w.label("Jumlah bulan (maksimal 24)", objek="FormLabel"), 0, 1)
        self.spin_bulan_kb = QSpinBox()
        self.spin_bulan_kb.setRange(1, 24)
        self.spin_bulan_kb.setValue(12)
        self.spin_bulan_kb.valueChanged.connect(self._hitung_sanksi)
        g3.addWidget(self.spin_bulan_kb, 1, 1)
        k3.body().addLayout(g3)

        self.lbl_kb = QLabel("")
        self.lbl_kb.setWordWrap(True)
        self.lbl_kb.setStyleSheet(f"font-size: {theme.FS_BODY}px; "
                                  "background: transparent;")
        k3.body().addWidget(self.lbl_kb)
        lay.addWidget(k3)

        lay.addWidget(w.HelpPanel(
            "Mengapa sanksi ini penting dipahami",
            "Sanksi administrasi dapat dengan cepat melampaui pajak pokoknya sendiri. "
            "Contoh: pajak Rp10 juta yang terlambat 24 bulan dapat dikenai bunga "
            "2% × 24 = 48%, yaitu Rp4,8 juta tambahan.\n\n"
            "Karena itu, lebih baik setor lebih awal meskipun SPT belum selesai "
            "dilaporkan. Pembayaran lebih awal menghentikan perhitungan bunga.",
            "Pasal 9, 13, dan 7 UU KUP jo. UU HPP."))
        lay.addStretch()
        self._hitung_sanksi()

    def _hitung_sanksi(self):
        try:
            pajak = self.inp_pajak.nilai()
            if pajak > 0:
                try:
                    suku = float(self.inp_suku.text().replace(",", ".")) / 100
                except ValueError:
                    suku = config.BI_REFERENCE_RATE
                r = tx.hitung_bunga_keterlambatan(pajak, self.spin_bulan.value(), suku)
                self.lbl_bunga.setText(
                    f"<b>Bunga keterlambatan: {theme.money(r['bunga'])}</b><br>"
                    f"Total yang harus dibayar: <b>{theme.money(r['total_bayar'])}</b> "
                    f"(pajak {theme.money(pajak)} + bunga {theme.money(r['bunga'])})<br>"
                    f"<span style='color:{C.TEXT_MUTED}'>{r['keterangan']}</span>")
                self.lbl_bunga.setTextFormat(Qt.RichText)
            else:
                self.lbl_bunga.setText("Masukkan jumlah pajak untuk menghitung.")
        except Exception:
            pass

        try:
            kode = self.cmb_spt.currentData()
            r = tx.hitung_sanksi_telat_lapor(kode)
            total = r["denda"] * self.spin_jumlah_spt.value()
            self.lbl_denda.setText(
                f"<b>Total denda: {theme.money(total)}</b> "
                f"({self.spin_jumlah_spt.value()} × {theme.money(r['denda'])})<br>"
                f"<span style='color:{C.TEXT_MUTED}'>{r['keterangan']}</span>")
            self.lbl_denda.setTextFormat(Qt.RichText)
        except Exception:
            pass

        try:
            kb = self.inp_kb.nilai()
            if kb > 0:
                r = tx.hitung_sanksi_kurang_bayar(kb, self.spin_bulan_kb.value())
                self.lbl_kb.setText(
                    f"<b>Sanksi bunga: {theme.money(r['bunga'])}</b><br>"
                    f"Total yang harus dibayar: <b>{theme.money(r['total'])}</b><br>"
                    f"<span style='color:{C.TEXT_MUTED}'>{r['keterangan']}</span>")
                self.lbl_kb.setTextFormat(Qt.RichText)
            else:
                self.lbl_kb.setText("Masukkan jumlah kurang bayar untuk menghitung.")
        except Exception:
            pass


# ==========================================================================
# DIALOG POTPUT
# ==========================================================================
class DialogPotPut(QDialog):
    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.setWindowTitle("Catat Pemotongan/Pemungutan Pajak")
        self.setMinimumWidth(640)

        l = QVBoxLayout(self)
        l.setContentsMargins(24, 22, 24, 22)
        l.setSpacing(13)

        j = QLabel("Register Pajak Potong/Pungut")
        j.setObjectName("SectionTitle")
        l.addWidget(j)

        if ctx.beginner:
            l.addWidget(w.HelpPanel(
                "Panduan memilih kode pajak",
                "Pilih kode sesuai jenis pembayaran Anda:\n\n"
                "• PPh 23 JASA (2%) - bayar jasa konsultan, desainer, perbaikan "
                "ke WP Badan; sewa alat selain tanah/bangunan.\n"
                "• PPh 23 15% - bayar bunga pinjaman, royalti, hadiah ke badan.\n"
                "• PPh 4(2) SEWA (10%) - sewa tanah/bangunan, bersifat final.\n"
                "• PPh 4(2) KONSTRUKSI - bayar jasa konstruksi.\n"
                "• PPh 22 - impor barang atau pembelian barang tertentu.\n"
                "• PPh 26 (20%) - bayar ke pihak luar negeri.\n\n"
                "Pajak yang Anda potong wajib disetor (tgl 10) dan dilaporkan "
                "(tgl 20) bulan berikutnya.",
                "Pasal 21, 22, 23, 26, 4(2) UU PPh."))

        g = QGridLayout()
        g.setSpacing(12)

        g.addWidget(w.label("Tanggal Transaksi", objek="FormLabel"), 0, 0)
        self.inp_tanggal = kalender.pasang(QDateEdit())
        self.inp_tanggal.setDisplayFormat("dd/MM/yyyy")
        self.inp_tanggal.setDate(QDate.currentDate())
        g.addWidget(self.inp_tanggal, 1, 0)

        g.addWidget(w.label("Masa Pajak (YYYY-MM)", objek="FormLabel"), 0, 1)
        self.inp_masa = QLineEdit(date.today().strftime("%Y-%m"))
        g.addWidget(self.inp_masa, 1, 1)

        g.addWidget(w.label("Kode Pajak", objek="FormLabel"), 2, 0, 1, 2)
        self.cmb_kode = QComboBox()
        for kode, jenis, tarif, kredit, ket in services.KODE_PAJAK_LIST:
            label = f"{kode} - {jenis}"
            if tarif:
                label += f" ({tarif * 100:g}%)"
            self.cmb_kode.addItem(label, kode)
        self.cmb_kode.currentIndexChanged.connect(self._update_ket)
        g.addWidget(self.cmb_kode, 3, 0, 1, 2)

        g.addWidget(w.label("DPP / Jumlah Bruto (Rp)", objek="FormLabel"), 4, 0, 1, 2)
        self.inp_dpp = w.InputRupiah()
        self.inp_dpp.valueChanged.connect(self._hitung)
        g.addWidget(self.inp_dpp, 5, 0, 1, 2)

        g.addWidget(w.label("Tarif Override (%) - opsional", objek="FormLabel"), 4, 2)
        self.inp_tarif = QLineEdit()
        self.inp_tarif.setPlaceholderText("kosongkan untuk tarif default")
        self.inp_tarif.textChanged.connect(self._hitung)
        g.addWidget(self.inp_tarif, 5, 2)

        g.addWidget(w.label("No. Bukti Potong / Billing", objek="FormLabel"), 6, 0)
        self.inp_bupot = QLineEdit()
        g.addWidget(self.inp_bupot, 7, 0)

        g.addWidget(w.label("Catatan", objek="FormLabel"), 6, 1, 1, 2)
        self.inp_catatan = QLineEdit()
        g.addWidget(self.inp_catatan, 7, 1, 1, 2)
        l.addLayout(g)

        self.lbl_ket = QLabel("")
        self.lbl_ket.setWordWrap(True)
        self.lbl_ket.setStyleSheet(f"font-size: {theme.FS_SMALL}px; "
                                   f"color: {C.TEXT_MUTED}; background: transparent;")
        l.addWidget(self.lbl_ket)

        self.panel = QFrame()
        theme.latar(self.panel, f"background: {C.PRIMARY_SOFT}; border: 1px solid "
                                 "#CFE0F0; border-radius: 8px;")
        pl = QVBoxLayout(self.panel)
        pl.setContentsMargins(16, 13, 16, 13)
        self.lbl_pajak = QLabel("Pajak: Rp0")
        self.lbl_pajak.setStyleSheet(
            f"font-family: {theme.FONT_ANGKA}; font-size: 17px; font-weight: 700; "
            f"color: {C.PRIMARY}; background: transparent;")
        pl.addWidget(self.lbl_pajak)
        self.lbl_info = QLabel("")
        self.lbl_info.setWordWrap(True)
        self.lbl_info.setStyleSheet(f"font-size: {theme.FS_TINY}px; "
                                    f"color: {C.TEXT_MUTED}; background: transparent;")
        pl.addWidget(self.lbl_info)
        l.addWidget(self.panel)

        aksi = QHBoxLayout()
        aksi.addStretch()
        b = w.tombol("Batal")
        b.clicked.connect(self.reject)
        aksi.addWidget(b)
        bs = w.tombol("Simpan", gaya="primary")
        bs.clicked.connect(self._simpan)
        aksi.addWidget(bs)
        l.addLayout(aksi)

        self._update_ket()
        self._hitung()

    def _update_ket(self):
        kode = self.cmb_kode.currentData()
        info = next((k for k in services.KODE_PAJAK_LIST if k[0] == kode), None)
        if info:
            self.lbl_ket.setText(info[4])
        self._hitung()

    def _hitung(self):
        kode = self.cmb_kode.currentData()
        info = next((k for k in services.KODE_PAJAK_LIST if k[0] == kode), None)
        tarif = info[2] if info else 0
        try:
            ov = self.inp_tarif.text().replace(",", ".").strip()
            if ov:
                tarif = float(ov) / 100
        except ValueError:
            pass
        dpp = self.inp_dpp.nilai()
        pajak = int(round(dpp * (tarif or 0)))
        self.lbl_pajak.setText(f"Pajak: {theme.money(pajak)}")
        if info and info[3]:
            self.lbl_info.setText(
                "Kode pajak ini dapat menjadi KREDIT PPh Badan bagi pihak yang "
                "dipotong - pastikan bukti potong tersimpan.")
        else:
            self.lbl_info.setText(
                "Pajak ini bersifat final atau dipotong dari pihak lain, sehingga "
                "tidak menjadi kredit PPh Badan Anda.")

    def _simpan(self):
        try:
            if self.inp_dpp.nilai() <= 0:
                QMessageBox.warning(self, "DPP kosong", "Isi DPP terlebih dahulu.")
                return
            kode = self.cmb_kode.currentData()
            info = next((k for k in services.KODE_PAJAK_LIST if k[0] == kode), None)
            if info and info[2] is None:
                ov = self.inp_tarif.text().replace(",", ".").strip()
                if not ov:
                    QMessageBox.warning(self, "Tarif diperlukan",
                                        "Kode pajak ini tidak memiliki tarif default. "
                                        "Isi tarif override.")
                    return
            ov = None
            teks = self.inp_tarif.text().replace(",", ".").strip()
            if teks:
                ov = float(teks) / 100

            services.simpan_pajak(
                self.ctx.company_id,
                self.inp_tanggal.date().toString("yyyy-MM-dd"),
                kode, self.inp_dpp.nilai(), ov,
                self.inp_masa.text().strip(),
                no_bupot=self.inp_bupot.text().strip(),
                catatan=self.inp_catatan.text().strip(),
                user_id=self.ctx.user_id)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Gagal menyimpan", str(e))


# ==========================================================================
# DIALOG SETORAN PAJAK
# ==========================================================================
class DialogSetoranPajak(QDialog):
    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.setWindowTitle("Catat Setoran Pajak")
        self.setMinimumWidth(560)

        l = QVBoxLayout(self)
        l.setContentsMargins(24, 22, 24, 22)
        l.setSpacing(13)

        j = QLabel("Setoran Pajak ke Kas Negara")
        j.setObjectName("SectionTitle")
        l.addWidget(j)

        if ctx.beginner:
            l.addWidget(w.HelpPanel(
                "Cara mencatat setoran pajak",
                "Setelah membayar pajak melalui bank atau kanal pembayaran, catat "
                "di sini agar utang pajak berkurang dan tercatat sebagai pengurang kas.\n\n"
                "Simpan NTPN (Nomor Transaksi Penerimaan Negara) - nomor ini menjadi "
                "bukti pembayaran yang sah.",
                "Pasal 9 UU KUP; PMK 81/2024."))

        g = QGridLayout()
        g.setSpacing(12)

        g.addWidget(w.label("Jenis Pajak", objek="FormLabel"), 0, 0)
        self.cmb_jenis = QComboBox()
        for k in ["PPN", "PPh21", "PPh23", "PPh4", "PPh25", "PPhBadan", "PPhFinal"]:
            self.cmb_jenis.addItem(k, k)
        g.addWidget(self.cmb_jenis, 1, 0)

        g.addWidget(w.label("Masa Pajak (YYYY-MM atau YYYY)", objek="FormLabel"), 0, 1)
        self.inp_masa = QLineEdit(date.today().strftime("%Y-%m"))
        g.addWidget(self.inp_masa, 1, 1)

        g.addWidget(w.label("Tanggal Bayar", objek="FormLabel"), 2, 0)
        self.inp_tanggal = kalender.pasang(QDateEdit())
        self.inp_tanggal.setDisplayFormat("dd/MM/yyyy")
        self.inp_tanggal.setDate(QDate.currentDate())
        g.addWidget(self.inp_tanggal, 3, 0)

        g.addWidget(w.label("Jumlah (Rp)", objek="FormLabel"), 2, 1)
        self.inp_jumlah = w.InputRupiah()
        g.addWidget(self.inp_jumlah, 3, 1)

        g.addWidget(w.label("NTPN", objek="FormLabel"), 4, 0)
        self.inp_ntpn = QLineEdit()
        self.inp_ntpn.setPlaceholderText("Nomor Transaksi Penerimaan Negara")
        g.addWidget(self.inp_ntpn, 5, 0)

        g.addWidget(w.label("Cara Bayar", objek="FormLabel"), 4, 1)
        self.cmb_cara = QComboBox()
        for c in ["e-Billing", "Bank Persepsi", "Kantor Pos", "Marketplace",
                  "Pungutan Pihak Lain"]:
            self.cmb_cara.addItem(c, c)
        g.addWidget(self.cmb_cara, 5, 1)

        g.addWidget(w.label("Catatan", objek="FormLabel"), 6, 0, 1, 2)
        self.inp_catatan = QLineEdit()
        g.addWidget(self.inp_catatan, 7, 0, 1, 2)
        l.addLayout(g)

        aksi = QHBoxLayout()
        aksi.addStretch()
        b = w.tombol("Batal")
        b.clicked.connect(self.reject)
        aksi.addWidget(b)
        bs = w.tombol("Simpan Setoran", gaya="primary")
        bs.clicked.connect(self._simpan)
        aksi.addWidget(bs)
        l.addLayout(aksi)

    def _simpan(self):
        try:
            if self.inp_jumlah.nilai() <= 0:
                QMessageBox.warning(self, "Jumlah kosong", "Isi jumlah setoran.")
                return
            services.catat_pembayaran_pajak(
                self.ctx.company_id, self.cmb_jenis.currentData(),
                self.inp_masa.text().strip(),
                self.inp_tanggal.date().toString("yyyy-MM-dd"),
                self.inp_jumlah.nilai(), self.inp_ntpn.text().strip(),
                self.cmb_cara.currentData(), self.inp_catatan.text().strip(),
                self.ctx.user_id)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Gagal menyimpan", str(e))


# ==========================================================================
# DIALOG KOREKSI MANUAL
# ==========================================================================
class DialogKoreksiManual(QDialog):
    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.setWindowTitle("Tambah Koreksi Fiskal Manual")
        self.setMinimumWidth(560)

        l = QVBoxLayout(self)
        l.setContentsMargins(24, 22, 24, 22)
        l.setSpacing(13)

        j = QLabel("Koreksi Fiskal Manual")
        j.setObjectName("SectionTitle")
        l.addWidget(j)

        l.addWidget(w.HelpPanel(
            "Kapan memakai koreksi manual",
            "Gunakan bila ada perbedaan yang tidak terdeteksi otomatis, misalnya:\n\n"
            "• Biaya entertainment tanpa daftar nominatif -> koreksi positif\n"
            "• Sumbangan yang tidak memenuhi syarat -> koreksi positif\n"
            "• Penghasilan dividen yang dikecualikan -> koreksi negatif\n"
            "• Pendapatan sewa tanah yang sudah dikenai PPh Final -> koreksi negatif\n\n"
            "Sertakan dokumen pendukung pada kolom yang tersedia.",
            "Pasal 4, 6, dan 9 UU PPh."))

        g = QGridLayout()
        g.setSpacing(12)
        g.addWidget(w.label("Uraian Koreksi", objek="FormLabel"), 0, 0, 1, 2)
        self.inp_uraian = QLineEdit()
        self.inp_uraian.setPlaceholderText("mis. Entertainment tanpa daftar nominatif")
        g.addWidget(self.inp_uraian, 1, 0, 1, 2)

        g.addWidget(w.label("Jenis Koreksi", objek="FormLabel"), 2, 0)
        self.cmb_jenis = QComboBox()
        self.cmb_jenis.addItem("Positif (menambah laba fiskal)", "Positif")
        self.cmb_jenis.addItem("Negatif (mengurangi laba fiskal)", "Negatif")
        g.addWidget(self.cmb_jenis, 3, 0)

        g.addWidget(w.label("Nilai (Rp)", objek="FormLabel"), 2, 1)
        self.inp_nilai = w.InputRupiah()
        g.addWidget(self.inp_nilai, 3, 1)

        g.addWidget(w.label("Dokumen Pendukung", objek="FormLabel"), 4, 0, 1, 2)
        self.inp_dokumen = QLineEdit()
        self.inp_dokumen.setPlaceholderText(
            "mis. Daftar nominatif No. 012/2026, kuitansi, berita acara")
        g.addWidget(self.inp_dokumen, 5, 0, 1, 2)

        g.addWidget(w.label("Catatan", objek="FormLabel"), 6, 0, 1, 2)
        self.inp_catatan = QLineEdit()
        g.addWidget(self.inp_catatan, 7, 0, 1, 2)
        l.addLayout(g)

        aksi = QHBoxLayout()
        aksi.addStretch()
        b = w.tombol("Batal")
        b.clicked.connect(self.reject)
        aksi.addWidget(b)
        bs = w.tombol("Simpan Koreksi", gaya="primary")
        bs.clicked.connect(self._simpan)
        aksi.addWidget(bs)
        l.addLayout(aksi)

    def _simpan(self):
        try:
            if not self.inp_uraian.text().strip():
                QMessageBox.warning(self, "Uraian kosong", "Isi uraian koreksi.")
                return
            if self.inp_nilai.nilai() <= 0:
                QMessageBox.warning(self, "Nilai kosong", "Isi nilai koreksi.")
                return
            services.simpan_koreksi_manual(
                self.ctx.company_id, self.ctx.tahun,
                self.inp_uraian.text().strip(), self.inp_nilai.nilai(),
                self.cmb_jenis.currentData(), self.inp_dokumen.text().strip(),
                self.inp_catatan.text().strip())
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Gagal menyimpan", str(e))
