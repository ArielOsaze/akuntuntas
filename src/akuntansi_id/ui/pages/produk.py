"""
Halaman produk, gudang, persediaan, kartu stok, dan stock opname.
"""
from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt, Signal, QDate
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit, QDateEdit,
    QDialog, QMessageBox, QGridLayout, QCheckBox, QTabWidget, QFileDialog, QMenu,
)

from ... import config, modules as M, modules_ops as O
from ...core import tax_engine as tx
from ... import istilah
from .. import theme, widgets as w
from .. import icons, kalender
from ..theme import C


class DialogProduk(QDialog):
    def __init__(self, ctx, parent=None, produk=None):
        super().__init__(parent)
        self.ctx = ctx
        self.produk = produk
        self.setWindowTitle("Ubah Produk" if produk else "Tambah Produk")
        self.setMinimumWidth(680)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 22, 24, 22)
        lay.setSpacing(13)

        j = QLabel("Data Produk / Jasa")
        j.setObjectName("SectionTitle")
        lay.addWidget(j)

        if ctx.beginner and not produk:
            lay.addWidget(w.HelpPanel(
                "Tentang metode HPP",
                "Metode HPP menentukan cara menghitung harga pokok saat barang "
                "terjual:\n\n"
                "• FIFO (First In First Out) - barang yang dibeli lebih dulu "
                "dianggap terjual lebih dulu. Cocok untuk barang yang mudah rusak "
                "atau harga belinya berubah-ubah.\n\n"
                "• Average (Rata-rata) - harga pokok dihitung dari rata-rata "
                "tertimbang seluruh pembelian. Cocok untuk barang homogen.\n\n"
                "Pilihan metode harus konsisten dan tidak diubah tanpa alasan kuat.",
                "PSAK 14 - persediaan. Metode FIFO dan rata-rata tertimbang "
                "keduanya diizinkan secara fiskal."))

        g = QGridLayout()
        g.setSpacing(12)

        g.addWidget(w.label("Kode Produk", objek="FormLabel"), 0, 0)
        self.inp_kode = QLineEdit()
        self.inp_kode.setPlaceholderText("otomatis bila kosong")
        g.addWidget(self.inp_kode, 1, 0)

        g.addWidget(w.label("Nama Produk", objek="FormLabel"), 0, 1, 1, 2)
        self.inp_nama = QLineEdit()
        self.inp_nama.setPlaceholderText("mis. Kopi Arabika 250g")
        g.addWidget(self.inp_nama, 1, 1, 1, 2)

        g.addWidget(w.label("Tipe", objek="FormLabel"), 2, 0)
        self.cmb_tipe = QComboBox()
        self.cmb_tipe.addItem("Barang (ada stok)", "barang")
        self.cmb_tipe.addItem("Jasa (tanpa stok)", "jasa")
        self.cmb_tipe.currentIndexChanged.connect(self._update_hint)
        g.addWidget(self.cmb_tipe, 3, 0)

        g.addWidget(w.label("Satuan", objek="FormLabel"), 2, 1)
        self.inp_satuan = QLineEdit("pcs")
        g.addWidget(self.inp_satuan, 3, 1)

        g.addWidget(w.label("Barcode", objek="FormLabel"), 2, 2)
        self.inp_barcode = QLineEdit()
        g.addWidget(self.inp_barcode, 3, 2)

        g.addWidget(w.label("Kategori", objek="FormLabel"), 4, 0)
        self.cmb_kategori = QComboBox()
        self.cmb_kategori.addItem("Tanpa Kategori", None)
        for k in M.daftar_kategori_produk(ctx.company_id):
            self.cmb_kategori.addItem(k["nama"], k["id"])
        g.addWidget(self.cmb_kategori, 5, 0)

        g.addWidget(w.label("Metode HPP", objek="FormLabel"), 4, 1)
        self.cmb_metode = QComboBox()
        self.cmb_metode.addItem("Average (rata-rata)", "average")
        self.cmb_metode.addItem("FIFO (First In First Out)", "fifo")
        g.addWidget(self.cmb_metode, 5, 1)

        g.addWidget(w.label("Stok Minimum", objek="FormLabel"), 4, 2)
        self.inp_stok_min = w.InputRupiah()
        g.addWidget(self.inp_stok_min, 5, 2)

        g.addWidget(w.label("Harga Beli (Rp)", objek="FormLabel"), 6, 0)
        self.inp_beli = w.InputRupiah()
        self.inp_beli.valueChanged.connect(self._update_hint)
        g.addWidget(self.inp_beli, 7, 0)

        g.addWidget(w.label("Harga Jual (Rp)", objek="FormLabel"), 6, 1)
        self.inp_jual = w.InputRupiah()
        self.inp_jual.valueChanged.connect(self._update_hint)
        g.addWidget(self.inp_jual, 7, 1)

        g.addWidget(w.label("Stok Awal (bila ada)", objek="FormLabel"), 6, 2)
        self.inp_stok_awal = w.InputRupiah()
        self.inp_stok_awal.setToolTip(
            "Isi hanya bila Anda memiliki stok saat mulai memakai aplikasi.")
        g.addWidget(self.inp_stok_awal, 7, 2)

        g.addWidget(w.label("Deskripsi", objek="FormLabel"), 8, 0, 1, 3)
        self.inp_deskripsi = QLineEdit()
        g.addWidget(self.inp_deskripsi, 9, 0, 1, 3)

        g.addWidget(w.label("Akun Persediaan", objek="FormLabel"), 10, 0)
        self.cmb_akun_persediaan = w.combo_akun(ctx.company_id)
        w.set_combo_by_data(self.cmb_akun_persediaan, "1104")
        g.addWidget(self.cmb_akun_persediaan, 11, 0)

        g.addWidget(w.label("Akun Pendapatan", objek="FormLabel"), 10, 1)
        self.cmb_akun_pendapatan = w.combo_akun(ctx.company_id)
        w.set_combo_by_data(self.cmb_akun_pendapatan, "4001")
        g.addWidget(self.cmb_akun_pendapatan, 11, 1)

        g.addWidget(w.label("Akun HPP", objek="FormLabel"), 10, 2)
        self.cmb_akun_hpp = w.combo_akun(ctx.company_id)
        w.set_combo_by_data(self.cmb_akun_hpp, "5001")
        g.addWidget(self.cmb_akun_hpp, 11, 2)
        lay.addLayout(g)

        self.lbl_hint = QLabel("")
        self.lbl_hint.setWordWrap(True)
        self.lbl_hint.setTextFormat(Qt.RichText)
        theme.latar(self.lbl_hint, f"background: {C.PRIMARY_SOFT}; border: 1px solid #CFE0F0; "
            f"border-radius: 8px; padding: 12px 14px; font-size: {theme.FS_SMALL}px;")
        lay.addWidget(self.lbl_hint)

        aksi = QHBoxLayout()
        aksi.addStretch()
        b = w.tombol("Batal")
        b.clicked.connect(self.reject)
        aksi.addWidget(b)
        bs = w.tombol("Simpan", gaya="primary")
        bs.clicked.connect(self._simpan)
        aksi.addWidget(bs)
        lay.addLayout(aksi)

        if produk:
            self._muat()
        self._update_hint()

    def _update_hint(self):
        """
        Sesuaikan kolom isian dengan tipe produk yang dipilih.

        Barang dilacak stoknya sehingga memerlukan stok minimum, metode HPP,
        dan akun HPP. Jasa tidak punya persediaan, jadi kolom itu dinonaktifkan
        supaya tidak ada isian yang tidak terpakai - kolom yang tetap aktif
        tetapi diabaikan membuat pengguna ragu apakah isiannya tersimpan.
        """
        beli = self.inp_beli.nilai()
        jual = self.inp_jual.nilai()
        is_barang = self.cmb_tipe.currentData() == "barang"

        # Kolom khusus persediaan: hanya berguna untuk barang.
        self.inp_stok_min.setEnabled(is_barang)
        self.inp_stok_awal.setEnabled(is_barang and self.produk is None)
        self.cmb_metode.setEnabled(is_barang)
        self.cmb_akun_persediaan.setEnabled(is_barang)
        self.cmb_akun_hpp.setEnabled(is_barang)
        self.inp_satuan.setEnabled(is_barang)

        pesan = []
        if beli and jual:
            margin = jual - beli
            persen = (margin / beli * 100) if beli else 0
            pesan.append(f"Margin per unit: <b>{tx.rupiah(margin)}</b> "
                         f"({persen:.1f}% dari harga beli)")
            if margin <= 0:
                pesan.append(f"<span style='color:{C.DANGER}'>peringatan Harga jual di bawah "
                             "atau sama dengan harga beli - usaha akan merugi.</span>")
            elif persen < 10:
                pesan.append(f"<span style='color:{C.WARNING}'>Margin di bawah 10% "
                             "periksa apakah cukup menutup beban operasional.</span>")
        if is_barang:
            pesan.append("Barang akan dilacak stoknya. Setiap penjualan mengurangi "
                         "stok dan mencatat HPP otomatis.")
        else:
            pesan.append("Jasa tidak dilacak stoknya - tidak ada HPP persediaan.")
        if self.cmb_metode.currentData() == "fifo" and is_barang:
            pesan.append("Metode FIFO: lapisan pembelian tertua dipakai lebih dulu.")
        self.lbl_hint.setText("<br>".join(pesan))

    def _muat(self):
        p = self.produk
        self.inp_kode.setText(p["kode"])
        self.inp_kode.setReadOnly(True)
        self.inp_nama.setText(p["nama"])
        i = self.cmb_tipe.findData(p["tipe"])
        if i >= 0:
            self.cmb_tipe.setCurrentIndex(i)
        self.inp_satuan.setText(p["satuan"] or "pcs")
        self.inp_barcode.setText(p["barcode"] or "")
        i = self.cmb_kategori.findData(p["kategori_id"])
        if i >= 0:
            self.cmb_kategori.setCurrentIndex(i)
        i = self.cmb_metode.findData(p["metode_hpp"])
        if i >= 0:
            self.cmb_metode.setCurrentIndex(i)
        self.inp_stok_min.set_nilai(p["stok_minimum"])
        self.inp_beli.set_nilai(p["harga_beli"])
        self.inp_jual.set_nilai(p["harga_jual"])
        self.inp_deskripsi.setText(p["deskripsi"] or "")
        w.set_combo_by_data(self.cmb_akun_persediaan, p["akun_persediaan"])
        w.set_combo_by_data(self.cmb_akun_pendapatan, p["akun_pendapatan"])
        w.set_combo_by_data(self.cmb_akun_hpp, p["akun_hpp"])
        self.inp_stok_awal.setEnabled(False)

    def _simpan(self):
        try:
            if not self.inp_nama.text().strip():
                QMessageBox.warning(self, "Nama kosong", "Isi nama produk.")
                return
            data = dict(
                kategori_id=self.cmb_kategori.currentData(),
                barcode=self.inp_barcode.text().strip(),
                deskripsi=self.inp_deskripsi.text().strip(),
                satuan=self.inp_satuan.text().strip() or "pcs",
                tipe=self.cmb_tipe.currentData(),
                harga_beli=self.inp_beli.nilai(),
                harga_jual=self.inp_jual.nilai(),
                metode_hpp=self.cmb_metode.currentData(),
                stok_minimum=self.inp_stok_min.nilai(),
                akun_persediaan=self.cmb_akun_persediaan.currentData() or "1104",
                akun_pendapatan=self.cmb_akun_pendapatan.currentData() or "4001",
                akun_hpp=self.cmb_akun_hpp.currentData() or "5001",
            )
            if self.produk:
                M.ubah_produk(self.produk["id"], user_id=self.ctx.user_id,
                              username=self.ctx.username, **data)
            else:
                M.buat_produk(self.ctx.company_id, self.inp_nama.text().strip(),
                              kode=self.inp_kode.text().strip() or None,
                              qty_awal=self.inp_stok_awal.nilai(),
                              user_id=self.ctx.user_id,
                              username=self.ctx.username, **data)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Gagal menyimpan", str(e))


class DialogGudang(QDialog):
    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.setWindowTitle("Tambah Gudang")
        self.setMinimumWidth(480)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 22, 24, 22)
        lay.setSpacing(13)

        j = QLabel("Data Gudang")
        j.setObjectName("SectionTitle")
        lay.addWidget(j)

        g = QGridLayout()
        g.setSpacing(12)
        g.addWidget(w.label("Nama Gudang", objek="FormLabel"), 0, 0, 1, 2)
        self.inp_nama = QLineEdit()
        self.inp_nama.setPlaceholderText("mis. Gudang Bandung")
        g.addWidget(self.inp_nama, 1, 0, 1, 2)

        g.addWidget(w.label("Lokasi", objek="FormLabel"), 2, 0)
        self.inp_lokasi = QLineEdit()
        g.addWidget(self.inp_lokasi, 3, 0)

        g.addWidget(w.label("Penanggung Jawab", objek="FormLabel"), 2, 1)
        self.inp_pic = QLineEdit()
        g.addWidget(self.inp_pic, 3, 1)
        lay.addLayout(g)

        aksi = QHBoxLayout()
        aksi.addStretch()
        b = w.tombol("Batal")
        b.clicked.connect(self.reject)
        aksi.addWidget(b)
        bs = w.tombol("Simpan", gaya="primary")
        bs.clicked.connect(self._simpan)
        aksi.addWidget(bs)
        lay.addLayout(aksi)

    def _simpan(self):
        try:
            if not self.inp_nama.text().strip():
                QMessageBox.warning(self, "Nama kosong", "Isi nama gudang.")
                return
            M.buat_gudang(self.ctx.company_id, self.inp_nama.text().strip(),
                          lokasi=self.inp_lokasi.text().strip(),
                          pic=self.inp_pic.text().strip())
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Gagal menyimpan", str(e))


class DialogStockOpname(QDialog):
    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.setWindowTitle("Stock Opname")
        self.setMinimumSize(880, 600)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 20, 22, 20)
        lay.setSpacing(12)

        j = QLabel("Penyesuaian Stok Fisik")
        j.setObjectName("SectionTitle")
        lay.addWidget(j)

        lay.addWidget(w.HelpPanel(
            "Tentang stock opname",
            "Hitung fisik barang di gudang, lalu masukkan jumlah sebenarnya. "
            "Aplikasi akan menyesuaikan catatan dan menghitung selisihnya.\n\n"
            "Selisih positif (fisik lebih banyak) menambah persediaan.\n"
            "Selisih negatif (fisik lebih sedikit) mengurangi persediaan dan "
            "menjadi beban.",
            "Pasal 28 UU KUP - pembukuan harus menggambarkan keadaan sebenarnya. "
            "PSAK 14 - pengukuran persediaan."))

        baris = QHBoxLayout()
        baris.setSpacing(11)
        baris.addWidget(w.label("Gudang:", objek="FormLabel"))
        self.cmb_gudang = QComboBox()
        for g in M.daftar_gudang(ctx.company_id):
            self.cmb_gudang.addItem(f"{g['kode']} - {g['nama']}", g["id"])
        self.cmb_gudang.currentIndexChanged.connect(self._muat)
        baris.addWidget(self.cmb_gudang)

        baris.addWidget(w.label("Tanggal:", objek="FormLabel"))
        self.inp_tanggal = kalender.pasang(QDateEdit())
        self.inp_tanggal.setDisplayFormat("dd/MM/yyyy")
        self.inp_tanggal.setDate(QDate.currentDate())
        baris.addWidget(self.inp_tanggal)

        baris.addWidget(w.label("Alasan:", objek="FormLabel"))
        self.inp_alasan = QLineEdit()
        self.inp_alasan.setPlaceholderText("mis. Opname akhir bulan")
        baris.addWidget(self.inp_alasan, 1)
        lay.addLayout(baris)

        self.tabel = w.Tabel([("Produk", -1), ("Satuan", 90), ("Stok Tercatat", 145),
                              ("Stok Fisik", 165), ("Selisih", 145)])
        lay.addWidget(self.tabel, 1)

        self.inputs: dict[int, w.InputRupiah] = {}
        self.tabel.setMinimumHeight(340)

        aksi = QHBoxLayout()
        self.lbl_info = QLabel("")
        self.lbl_info.setObjectName("Muted")
        aksi.addWidget(self.lbl_info, 1)
        b = w.tombol("Batal")
        b.clicked.connect(self.reject)
        aksi.addWidget(b)
        bs = w.tombol("Simpan Penyesuaian", gaya="primary")
        bs.clicked.connect(self._simpan)
        aksi.addWidget(bs)
        lay.addLayout(aksi)

        self._muat()

    def _muat(self):
        gudang_id = self.cmb_gudang.currentData()
        produk = M.daftar_produk(self.ctx.company_id, tipe="barang")
        self.tabel.setRowCount(len(produk))
        self.inputs.clear()

        for i, p in enumerate(produk):
            saldo = M.saldo_stok(self.ctx.company_id, p["id"], gudang_id)
            self.tabel.setItem(i, 0, w.QTableWidgetItem(f"{p['kode']} - {p['nama']}"))
            self.tabel.setItem(i, 1, w.QTableWidgetItem(p["satuan"] or "pcs"))
            self.tabel.setItem(i, 2, w.QTableWidgetItem(f"{saldo['qty']:g}"))

            inp = w.InputRupiah()
            inp.set_nilai(int(saldo["qty"]))
            self.inputs[p["id"]] = (inp, saldo["qty"], p["nama"])
            self.tabel.setCellWidget(i, 3, inp)

            lbl = QLabel("0")
            lbl.setStyleSheet(f"font-family: {theme.FONT_ANGKA}; "
                              "background: transparent;")
            self.tabel.setCellWidget(i, 4, lbl)

        self.lbl_info.setText(f"{len(produk)} produk barang di gudang ini")

    def _simpan(self):
        try:
            gudang_id = self.cmb_gudang.currentData()
            tanggal = self.inp_tanggal.date().toString("yyyy-MM-dd")
            alasan = self.inp_alasan.text().strip() or "Stock opname"
            jumlah_disesuaikan = 0
            total_selisih = 0

            for pid, (inp, qty_lama, nama) in self.inputs.items():
                qty_baru = float(inp.nilai())
                if abs(qty_baru - qty_lama) < 0.01:
                    continue
                r = M.penyesuaian_stok(self.ctx.company_id, pid, qty_baru,
                                       tanggal, gudang_id, alasan,
                                       self.ctx.user_id)
                jumlah_disesuaikan += 1
                total_selisih += r["nilai"]

            if jumlah_disesuaikan == 0:
                QMessageBox.information(self, "Tidak ada perubahan",
                                        "Tidak ada selisih stok yang perlu disesuaikan.")
                return

            QMessageBox.information(
                self, "Penyesuaian selesai",
                f"{jumlah_disesuaikan} produk disesuaikan.\n"
                f"Nilai penyesuaian: {tx.rupiah(total_selisih)}")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Gagal menyimpan", str(e))


class ProdukPage(QWidget):
    pindah_halaman = Signal(str)

    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx

        luar = QVBoxLayout(self)
        luar.setContentsMargins(0, 0, 0, 0)
        luar.setSpacing(0)

        self.header = w.PageHeader(
            "Produk & Persediaan",
            "Kelola produk, gudang, stok, dan perhitungan HPP dengan metode "
            "FIFO atau rata-rata.")

        # Satu aksi utama saja di header. Aksi lain dipindah ke menu agar
        # baris tombol tidak meluber keluar tepi halaman.
        b_tambah = w.tombol("Tambah Produk", gaya="primary", ikon="+")
        b_tambah.clicked.connect(self._tambah)
        self.header.tambah_aksi(b_tambah)

        b_lain = w.tombol("Aksi Lain", ikon="panah_bawah")
        menu = QMenu(b_lain)
        menu.addAction(icons.ikon("aset", C.TEXT, 16), "Kelola Gudang",
                       self._gudang)
        menu.addAction(icons.ikon("audit", C.TEXT, 16), "Stock Opname",
                       self._opname)
        menu.addAction(icons.ikon("impor", C.TEXT, 16), "Impor CSV",
                       self._impor)
        b_lain.setMenu(menu)
        self.header.tambah_aksi(b_lain)

        kepala = QWidget()
        theme.latar(kepala, f"background: {C.SURFACE}; "
                             f"border-bottom: 1px solid {C.BORDER};")
        kl = QVBoxLayout(kepala)
        kl.setContentsMargins(26, 20, 26, 18)
        kl.addWidget(self.header)
        luar.addWidget(kepala)

        isi = QWidget()
        self.lay = QVBoxLayout(isi)
        self.lay.setContentsMargins(24, 20, 24, 22)
        self.lay.setSpacing(13)
        luar.addWidget(isi, 1)

        self.banner = QWidget()
        self.banner_lay = QVBoxLayout(self.banner)
        self.banner_lay.setContentsMargins(0, 0, 0, 0)
        self.lay.addWidget(self.banner)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tab_produk = QWidget()
        self.tab_stok = QWidget()
        self.tab_kartu = QWidget()
        self.tabs.addTab(self.tab_produk, "Daftar Produk")
        self.tabs.addTab(self.tab_stok, "Posisi Stok")
        self.tabs.addTab(self.tab_kartu, "Kartu Stok")
        self.tabs.currentChanged.connect(self.muat)
        self.lay.addWidget(self.tabs, 1)

        self._bangun_produk()
        self._bangun_stok()
        self._bangun_kartu()

    def _bangun_produk(self):
        lay = QVBoxLayout(self.tab_produk)
        lay.setContentsMargins(0, 12, 0, 0)
        lay.setSpacing(12)

        baris = QHBoxLayout()
        baris.setSpacing(10)
        self.inp_cari = QLineEdit()
        self.inp_cari.setPlaceholderText("Cari nama, kode, atau barcode…")
        self.inp_cari.setMinimumWidth(300)
        self.inp_cari.textChanged.connect(self.muat)
        baris.addWidget(self.inp_cari)

        self.cmb_tipe_filter = QComboBox()
        self.cmb_tipe_filter.addItem("Semua Tipe", "")
        self.cmb_tipe_filter.addItem("Barang", "barang")
        self.cmb_tipe_filter.addItem("Jasa", "jasa")
        self.cmb_tipe_filter.currentIndexChanged.connect(self.muat)
        baris.addWidget(self.cmb_tipe_filter)
        baris.addStretch()
        self.lbl_produk = QLabel("")
        self.lbl_produk.setObjectName("Muted")
        baris.addWidget(self.lbl_produk)
        lay.addLayout(baris)

        self.tabel_produk = w.Tabel([
            ("Kode", 105), ("Nama", -1), ("Tipe", 90), ("Satuan", 85),
            ("Harga Beli", 140), ("Harga Jual", 140), ("Stok", 110),
            ("Metode HPP", 115), ("Nilai Stok", 155),
        ])
        self.tabel_produk.doubleClicked.connect(self._ubah)
        lay.addWidget(self.tabel_produk, 1)

        baris2 = QHBoxLayout()
        baris2.setSpacing(9)
        b1 = w.tombol("Ubah", ikon="pengaturan")
        b1.clicked.connect(self._ubah)
        baris2.addWidget(b1)
        b2 = w.tombol("Hapus", gaya="danger", ikon="hapus")
        b2.clicked.connect(self._hapus)
        baris2.addWidget(b2)
        baris2.addStretch()
        lay.addLayout(baris2)

    def _bangun_stok(self):
        lay = QVBoxLayout(self.tab_stok)
        lay.setContentsMargins(0, 12, 0, 0)
        lay.setSpacing(12)

        baris = QHBoxLayout()
        baris.setSpacing(10)
        self.inp_cari_stok = QLineEdit()
        self.inp_cari_stok.setPlaceholderText("Cari produk…")
        self.inp_cari_stok.setMinimumWidth(280)
        self.inp_cari_stok.textChanged.connect(self.muat)
        baris.addWidget(self.inp_cari_stok)

        self.chk_menipis = QCheckBox("Hanya tampilkan stok menipis")
        self.chk_menipis.stateChanged.connect(self.muat)
        baris.addWidget(self.chk_menipis)

        self.cmb_gudang_stok = QComboBox()
        self.cmb_gudang_stok.addItem("Semua Gudang", None)
        self.cmb_gudang_stok.currentIndexChanged.connect(self._refresh_gudang_combo)
        baris.addWidget(self.cmb_gudang_stok)
        baris.addStretch()
        self.lbl_stok = QLabel("")
        self.lbl_stok.setObjectName("Muted")
        baris.addWidget(self.lbl_stok)
        lay.addLayout(baris)

        self.tabel_stok = w.Tabel([
            ("Kode", 105), ("Produk", -1), ("Satuan", 85), ("Stok", 115),
            ("HPP Satuan", 145), ("Nilai Stok", 160), ("Stok Min", 105),
            ("Status", 135),
        ])
        lay.addWidget(self.tabel_stok, 1)

        baris2 = QHBoxLayout()
        b = w.tombol("Transfer Antar Gudang", ikon="transfer")
        b.clicked.connect(self._transfer)
        baris2.addWidget(b)
        b2 = w.tombol("Stock Opname", ikon="audit")
        b2.clicked.connect(self._opname)
        baris2.addWidget(b2)
        baris2.addStretch()
        lay.addLayout(baris2)

    def _bangun_kartu(self):
        lay = QVBoxLayout(self.tab_kartu)
        lay.setContentsMargins(0, 12, 0, 0)
        lay.setSpacing(12)

        baris = QHBoxLayout()
        baris.setSpacing(11)
        baris.addWidget(w.label("Produk:", objek="FormLabel"))
        self.cmb_produk_kartu = QComboBox()
        self.cmb_produk_kartu.setMinimumWidth(300)
        self.cmb_produk_kartu.currentIndexChanged.connect(self._muat_kartu)
        baris.addWidget(self.cmb_produk_kartu)

        baris.addWidget(w.label("Dari:", objek="FormLabel"))
        self.inp_dari = kalender.pasang(QDateEdit())
        self.inp_dari.setDisplayFormat("dd/MM/yyyy")
        self.inp_dari.setDate(QDate(datetime.now().year, 1, 1))
        self.inp_dari.dateChanged.connect(self._muat_kartu)
        baris.addWidget(self.inp_dari)

        baris.addWidget(w.label("Sampai:", objek="FormLabel"))
        self.inp_sampai = kalender.pasang(QDateEdit())
        self.inp_sampai.setDisplayFormat("dd/MM/yyyy")
        self.inp_sampai.setDate(QDate.currentDate())
        self.inp_sampai.dateChanged.connect(self._muat_kartu)
        baris.addWidget(self.inp_sampai)
        baris.addStretch()
        lay.addLayout(baris)

        self.tabel_kartu = w.Tabel([
            ("Tanggal", 110), ("Tipe", 110), ("Referensi", 165),
            ("Keterangan", -1), ("Masuk", 110), ("Keluar", 110),
            ("Harga Satuan", 140), ("Nilai", 150), ("Sisa FIFO", 110),
        ])
        lay.addWidget(self.tabel_kartu, 1)

        self.lbl_kartu = QLabel("")
        self.lbl_kartu.setObjectName("Muted")
        lay.addWidget(self.lbl_kartu)

    def _refresh_gudang_combo(self):
        combo = self.cmb_gudang_stok
        data_lama = combo.currentData()
        combo.blockSignals(True)
        combo.clear()
        combo.addItem("Semua Gudang", None)
        for g in M.daftar_gudang(self.ctx.company_id):
            combo.addItem(f"{g['kode']} - {g['nama']}", g["id"])
        i = combo.findData(data_lama)
        combo.setCurrentIndex(i if i >= 0 else 0)
        combo.blockSignals(False)
        self.muat()

    def muat(self):
        cid = self.ctx.company_id
        if not cid:
            return

        while self.banner_lay.count():
            it = self.banner_lay.takeAt(0)
            wdg = it.widget()
            if wdg is not None:
                wdg.setParent(None)
                wdg.deleteLater()

        menipis = M.produk_menipis(cid)
        if menipis:
            daftar = ", ".join(f"{p['nama']} ({p['qty']:g} {p['satuan']})"
                               for p in menipis[:5])
            self.banner_lay.addWidget(w.InfoBanner(
                f"{len(menipis)} produk mencapai atau di bawah stok minimum: {daftar}"
                + (" …" if len(menipis) > 5 else ""),
                "warning", "Stok menipis - segera lakukan pembelian"))

        self._refresh_gudang_combo_silent()
        idx = self.tabs.currentIndex()
        if idx == 0:
            self._muat_produk()
        elif idx == 1:
            self._muat_stok()
        else:
            self._muat_kartu()

    def _refresh_gudang_combo_silent(self):
        combo = self.cmb_gudang_stok
        if combo.count() <= 1:
            data_lama = combo.currentData()
            combo.blockSignals(True)
            combo.clear()
            combo.addItem("Semua Gudang", None)
            for g in M.daftar_gudang(self.ctx.company_id):
                combo.addItem(f"{g['kode']} - {g['nama']}", g["id"])
            i = combo.findData(data_lama)
            combo.setCurrentIndex(i if i >= 0 else 0)
            combo.blockSignals(False)

        combo2 = self.cmb_produk_kartu
        data_lama = combo2.currentData()
        combo2.blockSignals(True)
        combo2.clear()
        for p in M.daftar_produk(self.ctx.company_id):
            combo2.addItem(f"{p['kode']} - {p['nama']}", p["id"])
        i = combo2.findData(data_lama)
        combo2.setCurrentIndex(i if i >= 0 else 0)
        combo2.blockSignals(False)

    def _muat_produk(self):
        cid = self.ctx.company_id
        data = M.daftar_produk(cid, self.inp_cari.text().strip(),
                               self.cmb_tipe_filter.currentData())
        baris, warna = [], {}
        for i, p in enumerate(data):
            idx = len(baris)
            stok = p["stok"] or 0
            if p["tipe"] == "barang":
                metode = "Rata-rata" if p["metode_hpp"] == "average" else "FIFO"
            else:
                metode = ""
            baris.append([
                p["kode"], p["nama"], istilah.label("tipe", p["tipe"]), p["satuan"],
                tx.rupiah(p["harga_beli"]), tx.rupiah(p["harga_jual"]),
                f"{stok:g}" if p["tipe"] == "barang" else "",
                metode,
                tx.rupiah(p["nilai_stok"]) if p["nilai_stok"] else "",
            ])
            if p["tipe"] == "barang" and stok <= (p["stok_minimum"] or 0):
                warna[idx] = C.WARNING
        self.tabel_produk.isi(baris, warna_baris=warna, align_kanan={4, 5, 6, 8})
        self.lbl_produk.setText(f"{len(data)} produk")

    def _muat_stok(self):
        cid = self.ctx.company_id
        gudang_id = self.cmb_gudang_stok.currentData()
        data = M.daftar_stok(cid, self.inp_cari_stok.text().strip(),
                             self.chk_menipis.isChecked())

        baris, warna = [], {}
        total_nilai = 0
        for p in data:
            if gudang_id:
                saldo = M.saldo_stok(cid, p["product_id"], gudang_id)
                qty, nilai = saldo["qty"], saldo["nilai_total"]
                hpp = saldo["hpp_satuan"]
            else:
                qty = p["qty"]
                nilai = p["nilai_total"]
                hpp = p["hpp_satuan"]
            total_nilai += nilai
            idx = len(baris)
            status = ("Habis" if qty <= 0 else
                      ("Menipis" if qty <= (p["stok_minimum"] or 0) else "Aman"))
            baris.append([
                p["kode"], p["nama"], p["satuan"], f"{qty:g}",
                tx.rupiah(hpp), tx.rupiah(nilai), f"{p['stok_minimum'] or 0:g}",
                status,
            ])
            if qty <= 0:
                warna[idx] = C.DANGER
            elif qty <= (p["stok_minimum"] or 0):
                warna[idx] = C.WARNING
        self.tabel_stok.isi(baris, warna_baris=warna, align_kanan={3, 4, 5, 6})
        self.lbl_stok.setText(f"{len(data)} produk · total nilai persediaan "
                              f"{tx.rupiah(total_nilai)}")

    def _muat_kartu(self):
        cid = self.ctx.company_id
        pid = self.cmb_produk_kartu.currentData()
        if not pid:
            self.tabel_kartu.setRowCount(0)
            return

        data = M.kartu_stok(cid, pid,
                            self.inp_dari.date().toString("yyyy-MM-dd"),
                            self.inp_sampai.date().toString("yyyy-MM-dd"))
        baris, warna = [], {}
        saldo_qty = 0
        for i, r in enumerate(data):
            idx = len(baris)
            qty = float(r["qty"])
            saldo_qty += qty
            baris.append([
                theme.tanggal_id(r["tanggal"]),
                istilah.label("tipe", r["tipe"]),
                r["no_ref"] or r["ref_tipe"] or "",
                r["keterangan"] or "",
                f"{qty:g}" if qty > 0 else "",
                f"{-qty:g}" if qty < 0 else "",
                tx.rupiah(r["harga_satuan"]),
                tx.rupiah(abs(r["nilai"])),
                f"{r['qty_sisa_fifo']:g}" if r["qty_sisa_fifo"] else "",
            ])
            warna[idx] = C.POSITIF if qty > 0 else C.NEGATIF
        self.tabel_kartu.isi(baris, warna_baris=warna, align_kanan={4, 5, 6, 7, 8})
        produk = M.get_produk(pid)
        self.lbl_kartu.setText(
            f"{len(data)} mutasi · saldo akhir {saldo_qty:g} "
            f"{produk['satuan'] if produk else ''}")

    def _tambah(self):
        if not self.ctx.company_id:
            QMessageBox.information(self, "Belum ada perusahaan",
                                    "Buat profil perusahaan terlebih dahulu.")
            return
        d = DialogProduk(self.ctx, self)
        if d.exec():
            self.muat()

    def _ubah(self):
        r = self.tabel_produk.baris_terpilih()
        if r is None:
            QMessageBox.information(self, "Belum dipilih", "Pilih satu produk.")
            return
        data = M.daftar_produk(self.ctx.company_id, self.inp_cari.text().strip(),
                               self.cmb_tipe_filter.currentData())
        if r < len(data):
            d = DialogProduk(self.ctx, self, M.get_produk(data[r]["id"]))
            if d.exec():
                self.muat()

    def _hapus(self):
        r = self.tabel_produk.baris_terpilih()
        if r is None:
            QMessageBox.information(self, "Belum dipilih", "Pilih satu produk.")
            return
        data = M.daftar_produk(self.ctx.company_id, self.inp_cari.text().strip(),
                               self.cmb_tipe_filter.currentData())
        if r >= len(data):
            return
        p = data[r]
        if QMessageBox.question(
                self, "Konfirmasi Hapus",
                f"Hapus produk '{p['nama']}'?\n\n"
                "Data dipindahkan ke keranjang sampah dan dapat dipulihkan.",
                QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            M.hapus_produk(p["id"], self.ctx.username)
            self.muat()

    def _gudang(self):
        d = DialogGudang(self.ctx, self)
        if d.exec():
            self.muat()

    def _opname(self):
        if not self.ctx.company_id:
            return
        d = DialogStockOpname(self.ctx, self)
        if d.exec():
            self.muat()

    def _transfer(self):
        d = DialogTransferStok(self.ctx, self)
        if d.exec():
            self.muat()

    def _impor(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Pilih Berkas CSV", str(config.EXPORT_DIR),
            "Berkas CSV (*.csv);;Semua Berkas (*)")
        if not path:
            return
        try:
            with open(path, encoding="utf-8-sig") as f:
                isi = f.read()
            hasil = O.impor_produk_massal(self.ctx.company_id, isi, self.ctx.user_id)
            pesan = (f"Impor selesai.\n\nBerhasil: {hasil['berhasil']}\n"
                     f"Duplikat dilewati: {hasil['duplikat']}\n"
                     f"Gagal: {hasil['gagal']}")
            if hasil["pesan"]:
                pesan += "\n\nCatatan:\n" + "\n".join(hasil["pesan"][:5])
            QMessageBox.information(self, "Hasil Impor", pesan)
            self.muat()
        except Exception as e:
            QMessageBox.critical(self, "Gagal mengimpor", str(e))


class DialogTransferStok(QDialog):
    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.setWindowTitle("Transfer Stok Antar Gudang")
        self.setMinimumWidth(560)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 22, 24, 22)
        lay.setSpacing(13)

        j = QLabel("Transfer Stok")
        j.setObjectName("SectionTitle")
        lay.addWidget(j)

        g = QGridLayout()
        g.setSpacing(12)

        g.addWidget(w.label("Produk", objek="FormLabel"), 0, 0, 1, 2)
        self.cmb_produk = QComboBox()
        for p in M.daftar_produk(ctx.company_id, tipe="barang"):
            self.cmb_produk.addItem(f"{p['kode']} - {p['nama']}", p["id"])
        self.cmb_produk.currentIndexChanged.connect(self._update_saldo)
        g.addWidget(self.cmb_produk, 1, 0, 1, 2)

        g.addWidget(w.label("Gudang Asal", objek="FormLabel"), 2, 0)
        self.cmb_dari = QComboBox()
        for gd in M.daftar_gudang(ctx.company_id):
            self.cmb_dari.addItem(f"{gd['kode']} - {gd['nama']}", gd["id"])
        self.cmb_dari.currentIndexChanged.connect(self._update_saldo)
        g.addWidget(self.cmb_dari, 3, 0)

        g.addWidget(w.label("Gudang Tujuan", objek="FormLabel"), 2, 1)
        self.cmb_ke = QComboBox()
        for gd in M.daftar_gudang(ctx.company_id):
            self.cmb_ke.addItem(f"{gd['kode']} - {gd['nama']}", gd["id"])
        g.addWidget(self.cmb_ke, 3, 1)

        g.addWidget(w.label("Jumlah", objek="FormLabel"), 4, 0)
        self.inp_qty = w.InputRupiah()
        g.addWidget(self.inp_qty, 5, 0)

        g.addWidget(w.label("Tanggal", objek="FormLabel"), 4, 1)
        self.inp_tanggal = kalender.pasang(QDateEdit())
        self.inp_tanggal.setDisplayFormat("dd/MM/yyyy")
        self.inp_tanggal.setDate(QDate.currentDate())
        g.addWidget(self.inp_tanggal, 5, 1)

        g.addWidget(w.label("Keterangan", objek="FormLabel"), 6, 0, 1, 2)
        self.inp_ket = QLineEdit()
        g.addWidget(self.inp_ket, 7, 0, 1, 2)
        lay.addLayout(g)

        self.lbl_saldo = QLabel("")
        theme.latar(self.lbl_saldo, f"background: {C.PRIMARY_SOFT}; border: 1px solid #CFE0F0; "
            f"border-radius: 8px; padding: 11px 13px; font-size: {theme.FS_SMALL}px;")
        lay.addWidget(self.lbl_saldo)

        aksi = QHBoxLayout()
        aksi.addStretch()
        b = w.tombol("Batal")
        b.clicked.connect(self.reject)
        aksi.addWidget(b)
        bs = w.tombol("Transfer", gaya="primary")
        bs.clicked.connect(self._simpan)
        aksi.addWidget(bs)
        lay.addLayout(aksi)

        if self.cmb_ke.count() > 1:
            self.cmb_ke.setCurrentIndex(1)
        self._update_saldo()

    def _update_saldo(self):
        pid = self.cmb_produk.currentData()
        gid = self.cmb_dari.currentData()
        if not pid or not gid:
            return
        s = M.saldo_stok(self.ctx.company_id, pid, gid)
        p = M.get_produk(pid)
        self.lbl_saldo.setText(
            f"Stok tersedia di gudang asal: <b>{s['qty']:g} "
            f"{p['satuan'] if p else ''}</b> · nilai {tx.rupiah(s['nilai_total'])}")
        self.lbl_saldo.setTextFormat(Qt.RichText)

    def _simpan(self):
        try:
            pid = self.cmb_produk.currentData()
            dari = self.cmb_dari.currentData()
            ke = self.cmb_ke.currentData()
            qty = self.inp_qty.nilai()
            if not pid:
                QMessageBox.warning(self, "Produk kosong", "Pilih produk.")
                return
            if dari == ke:
                QMessageBox.warning(self, "Gudang sama",
                                    "Gudang asal dan tujuan harus berbeda.")
                return
            if qty <= 0:
                QMessageBox.warning(self, "Jumlah kosong", "Isi jumlah yang dipindah.")
                return
            M.transfer_stok(self.ctx.company_id, pid, qty, dari, ke,
                            self.inp_tanggal.date().toString("yyyy-MM-dd"),
                            self.inp_ket.text().strip())
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Gagal transfer", str(e))
