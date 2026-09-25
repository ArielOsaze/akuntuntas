"""
Halaman mitra usaha: customer & vendor lengkap dengan riwayat transaksi.
"""
from __future__ import annotations


from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit, QDialog,
    QMessageBox, QGridLayout, QTabWidget, QFileDialog, QSpinBox,
)

from ... import config, modules as M, modules_ops as O
from ...core import tax_engine as tx
from ... import istilah
from .. import theme, widgets as w
from ..theme import C


class DialogMitra(QDialog):
    def __init__(self, ctx, parent=None, mitra=None, tipe_awal="customer"):
        super().__init__(parent)
        self.ctx = ctx
        self.mitra = mitra
        self.setWindowTitle("Ubah Mitra" if mitra else "Tambah Mitra")
        self.setMinimumWidth(680)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 22, 24, 22)
        lay.setSpacing(13)

        j = QLabel("Data Mitra Usaha")
        j.setObjectName("SectionTitle")
        lay.addWidget(j)

        if ctx.beginner and not mitra:
            lay.addWidget(w.HelpPanel(
                "Tentang data mitra",
                "Data mitra dipakai otomatis saat membuat invoice, bill, dan "
                "pembayaran - sehingga Anda tidak perlu mengetik ulang.\n\n"
                "• NPWP penting untuk penerbitan faktur pajak dan bukti potong.\n"
                "• Termin pembayaran menentukan tanggal jatuh tempo otomatis.\n"
                "• Batas kredit membantu mencegah piutang berlebihan.",
                "PMK 131/PMK.03/2024 - kelengkapan identitas lawan transaksi."))

        g = QGridLayout()
        g.setSpacing(12)

        g.addWidget(w.label("Tipe Mitra", objek="FormLabel"), 0, 0)
        self.cmb_tipe = QComboBox()
        self.cmb_tipe.addItem("Pelanggan (Customer)", "customer")
        self.cmb_tipe.addItem("Pemasok (Vendor)", "vendor")
        self.cmb_tipe.addItem("Keduanya", "keduanya")
        i = self.cmb_tipe.findData(tipe_awal)
        if i >= 0:
            self.cmb_tipe.setCurrentIndex(i)
        g.addWidget(self.cmb_tipe, 1, 0)

        g.addWidget(w.label("Nama Mitra", objek="FormLabel"), 0, 1, 1, 2)
        self.inp_nama = QLineEdit()
        self.inp_nama.setPlaceholderText("mis. PT Pelanggan Sejahtera")
        g.addWidget(self.inp_nama, 1, 1, 1, 2)

        g.addWidget(w.label("NPWP", objek="FormLabel"), 2, 0)
        self.inp_npwp = QLineEdit()
        self.inp_npwp.setPlaceholderText("00.000.000.0-000.000")
        g.addWidget(self.inp_npwp, 3, 0)

        g.addWidget(w.label("NIK (bila perorangan)", objek="FormLabel"), 2, 1)
        self.inp_nik = QLineEdit()
        g.addWidget(self.inp_nik, 3, 1)

        g.addWidget(w.label("Status Pajak", objek="FormLabel"), 2, 2)
        self.cmb_pajak = QComboBox()
        self.cmb_pajak.addItem("Umum", "umum")
        self.cmb_pajak.addItem("PKP", "pkp")
        self.cmb_pajak.addItem("Non-PKP", "non_pkp")
        g.addWidget(self.cmb_pajak, 3, 2)

        g.addWidget(w.label("Email", objek="FormLabel"), 4, 0)
        self.inp_email = QLineEdit()
        g.addWidget(self.inp_email, 5, 0)

        g.addWidget(w.label("Telepon / HP", objek="FormLabel"), 4, 1)
        self.inp_telepon = QLineEdit()
        g.addWidget(self.inp_telepon, 5, 1)

        g.addWidget(w.label("Kontak Person", objek="FormLabel"), 4, 2)
        self.inp_kontak = QLineEdit()
        g.addWidget(self.inp_kontak, 5, 2)

        g.addWidget(w.label("Alamat", objek="FormLabel"), 6, 0, 1, 3)
        self.inp_alamat = QLineEdit()
        g.addWidget(self.inp_alamat, 7, 0, 1, 3)

        g.addWidget(w.label("Kota", objek="FormLabel"), 8, 0)
        self.inp_kota = QLineEdit()
        g.addWidget(self.inp_kota, 9, 0)

        g.addWidget(w.label("Termin Pembayaran (hari)", objek="FormLabel"), 8, 1)
        self.spin_termin = QSpinBox()
        self.spin_termin.setRange(0, 365)
        self.spin_termin.setValue(30)
        g.addWidget(self.spin_termin, 9, 1)

        g.addWidget(w.label("Batas Kredit (Rp)", objek="FormLabel"), 8, 2)
        self.inp_batas = w.InputRupiah()
        g.addWidget(self.inp_batas, 9, 2)

        g.addWidget(w.label("Nama Bank", objek="FormLabel"), 10, 0)
        self.inp_bank = QLineEdit()
        g.addWidget(self.inp_bank, 11, 0)

        g.addWidget(w.label("Nomor Rekening", objek="FormLabel"), 10, 1)
        self.inp_rek = QLineEdit()
        g.addWidget(self.inp_rek, 11, 1)

        g.addWidget(w.label("Catatan", objek="FormLabel"), 10, 2)
        self.inp_catatan = QLineEdit()
        g.addWidget(self.inp_catatan, 11, 2)
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

        if mitra:
            self._muat()

    def _muat(self):
        m = self.mitra
        i = self.cmb_tipe.findData(m["tipe"])
        if i >= 0:
            self.cmb_tipe.setCurrentIndex(i)
        self.inp_nama.setText(m["nama"])
        self.inp_npwp.setText(m["npwp"] or "")
        self.inp_nik.setText(m["nik"] or "")
        i = self.cmb_pajak.findData(m["status_pajak"])
        if i >= 0:
            self.cmb_pajak.setCurrentIndex(i)
        self.inp_email.setText(m["email"] or "")
        self.inp_telepon.setText(m["telepon"] or "")
        self.inp_kontak.setText(m["kontak_person"] or "")
        self.inp_alamat.setText(m["alamat"] or "")
        self.inp_kota.setText(m["kota"] or "")
        self.spin_termin.setValue(int(m["termin_hari"] or 30))
        self.inp_batas.set_nilai(m["batas_kredit"])
        self.inp_bank.setText(m["nama_bank"] or "")
        self.inp_rek.setText(m["rekening_bank"] or "")
        self.inp_catatan.setText(m["catatan"] or "")

    def _simpan(self):
        try:
            if not self.inp_nama.text().strip():
                QMessageBox.warning(self, "Nama kosong", "Isi nama mitra.")
                return
            data = dict(
                tipe=self.cmb_tipe.currentData(),
                nama=self.inp_nama.text().strip(),
                npwp=self.inp_npwp.text().strip(),
                nik=self.inp_nik.text().strip(),
                status_pajak=self.cmb_pajak.currentData(),
                email=self.inp_email.text().strip(),
                telepon=self.inp_telepon.text().strip(),
                kontak_person=self.inp_kontak.text().strip(),
                alamat=self.inp_alamat.text().strip(),
                kota=self.inp_kota.text().strip(),
                termin_hari=self.spin_termin.value(),
                batas_kredit=self.inp_batas.nilai(),
                nama_bank=self.inp_bank.text().strip(),
                rekening_bank=self.inp_rek.text().strip(),
                catatan=self.inp_catatan.text().strip(),
            )
            if self.mitra:
                M.ubah_mitra(self.mitra["id"], user_id=self.ctx.user_id,
                             username=self.ctx.username, **data)
            else:
                M.buat_mitra(self.ctx.company_id, data.pop("nama"),
                             user_id=self.ctx.user_id,
                             username=self.ctx.username, **data)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Gagal menyimpan", str(e))


class DialogDetailMitra(QDialog):
    def __init__(self, partner_id: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Detail Mitra")
        self.setMinimumSize(920, 620)

        ringkas = M.ringkasan_mitra(partner_id)
        m = ringkas.get("mitra", {})

        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 20, 22, 20)
        lay.setSpacing(12)

        j = QLabel(m.get("nama", "Mitra"))
        j.setObjectName("SectionTitle")
        lay.addWidget(j)

        info = QGridLayout()
        info.setSpacing(14)
        data = [
            ("Kode", m.get("kode", "")),
            ("Tipe", {"customer": "Pelanggan", "vendor": "Pemasok",
                      "keduanya": "Keduanya"}.get(m.get("tipe"), "")),
            ("NPWP", m.get("npwp") or ""),
            ("Email", m.get("email") or ""),
            ("Telepon", m.get("telepon") or ""),
            ("Kota", m.get("kota") or ""),
            ("Termin", f"{m.get('termin_hari', 0)} hari"),
            ("Batas Kredit", tx.rupiah(m.get("batas_kredit", 0))),
        ]
        for i, (label, nilai) in enumerate(data):
            kotak = QWidget()
            kl = QVBoxLayout(kotak)
            kl.setContentsMargins(0, 0, 0, 0)
            kl.setSpacing(2)
            lb = QLabel(label.upper())
            lb.setObjectName("KpiLabel")
            kl.addWidget(lb)
            vl = QLabel(str(nilai))
            vl.setWordWrap(True)
            vl.setStyleSheet(f"font-size: {theme.FS_BODY}px; background: transparent;")
            kl.addWidget(vl)
            info.addWidget(kotak, i // 4, i % 4)
        lay.addLayout(info)

        kartu = w.Card()
        kl = kartu.body()
        b = QHBoxLayout()
        b.setSpacing(28)
        if m.get("tipe") in ("customer", "keduanya"):
            b.addWidget(w.MiniStat("Total Invoice",
                                   tx.rupiah(ringkas["total_invoice"])))
            b.addWidget(w.MiniStat("Jumlah Invoice", str(ringkas["jumlah_invoice"])))
            b.addWidget(w.MiniStat("Piutang", tx.rupiah(ringkas["piutang"]),
                                   C.WARNING if ringkas["piutang"] else C.TEXT))
            b.addWidget(w.MiniStat("Kredit Tersisa",
                                   tx.rupiah(ringkas["kredit_tersisa"])))
        if m.get("tipe") in ("vendor", "keduanya"):
            b.addWidget(w.MiniStat("Total Bill", tx.rupiah(ringkas["total_bill"])))
            b.addWidget(w.MiniStat("Utang", tx.rupiah(ringkas["utang"]),
                                   C.WARNING if ringkas["utang"] else C.TEXT))
        b.addStretch()
        kl.addLayout(b)
        lay.addWidget(kartu)

        lay.addWidget(w.label("Riwayat Transaksi", objek="SectionTitle"))
        t = w.Tabel([("Tanggal", 115), ("Jenis", 130), ("Nomor", 175),
                     ("Jumlah", 165), ("Status", 130)])
        riwayat = M.riwayat_mitra(partner_id)
        t.isi([[theme.tanggal_id(r["tanggal"]), istilah.label("tipe", r["jenis"]), r["nomor"],
                tx.rupiah(r["jumlah"]), istilah.label("status", r["status"])] for r in riwayat],
              align_kanan={3})
        t.setMinimumHeight(240)
        lay.addWidget(t)

        bt = w.tombol("Tutup", gaya="primary")
        bt.clicked.connect(self.accept)
        bl = QHBoxLayout()
        bl.addStretch()
        bl.addWidget(bt)
        lay.addLayout(bl)


class MitraPage(QWidget):
    pindah_halaman = Signal(str)

    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.tipe_aktif = "customer"

        luar = QVBoxLayout(self)
        luar.setContentsMargins(0, 0, 0, 0)
        luar.setSpacing(0)

        self.header = w.PageHeader(
            "Mitra Usaha",
            "Data pelanggan dan pemasok beserta riwayat transaksi, piutang, "
            "dan utangnya.")

        b_tambah = w.tombol("Tambah Mitra", gaya="primary", ikon="tambah")
        b_tambah.clicked.connect(self._tambah)
        self.header.tambah_aksi(b_tambah)

        b_impor = w.tombol("Impor dari CSV", ikon="impor")
        b_impor.clicked.connect(self._impor)
        self.header.tambah_aksi(b_impor)

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

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tab_pelanggan = QWidget()
        self.tab_pemasok = QWidget()
        self.tabs.addTab(self.tab_pelanggan, "Pelanggan")
        self.tabs.addTab(self.tab_pemasok, "Pemasok")
        self.tabs.currentChanged.connect(self._ganti_tab)
        self.lay.addWidget(self.tabs, 1)

        self.tabel_cust = self._buat_tabel(self.tab_pelanggan)
        self.tabel_vend = self._buat_tabel(self.tab_pemasok)

    def _buat_tabel(self, induk: QWidget) -> w.Tabel:
        lay = QVBoxLayout(induk)
        lay.setContentsMargins(0, 12, 0, 0)
        lay.setSpacing(12)

        filter_baris = QHBoxLayout()
        filter_baris.setSpacing(10)
        inp = QLineEdit()
        inp.setPlaceholderText("Cari nama, kode, NPWP, email, atau telepon…")
        inp.setMinimumWidth(320)
        inp.textChanged.connect(self.muat)
        filter_baris.addWidget(inp)
        filter_baris.addStretch()
        lbl = QLabel("")
        lbl.setObjectName("Muted")
        filter_baris.addWidget(lbl)
        lay.addLayout(filter_baris)

        kolom = [("Kode", 95), ("Nama", -1), ("NPWP", 165),
                 ("Kontak", 210), ("Kota", 110),
                 ("Termin", 80), ("Total Transaksi", 150), ("Saldo", 140)]
        t = w.Tabel(kolom)
        t.doubleClicked.connect(self._detail)
        lay.addWidget(t, 1)

        baris = QHBoxLayout()
        baris.setSpacing(9)
        b1 = w.tombol("Lihat Detail", ikon="")
        b1.clicked.connect(self._detail)
        baris.addWidget(b1)
        b2 = w.tombol("Ubah", ikon="pengaturan")
        b2.clicked.connect(self._ubah)
        baris.addWidget(b2)
        b3 = w.tombol("Hapus", gaya="danger", ikon="hapus")
        b3.clicked.connect(self._hapus)
        baris.addWidget(b3)
        baris.addStretch()
        lay.addLayout(baris)

        t._inp_cari = inp
        t._lbl_info = lbl
        return t

    def _ganti_tab(self, idx: int):
        self.tipe_aktif = "customer" if idx == 0 else "vendor"
        self.muat()

    def muat(self):
        cid = self.ctx.company_id
        if not cid:
            return

        for tipe, tabel in (("customer", self.tabel_cust), ("vendor", self.tabel_vend)):
            cari = tabel._inp_cari.text().strip()
            data = M.daftar_mitra(cid, tipe, cari)
            baris, warna = [], {}
            total_saldo = 0
            for i, m in enumerate(data):
                ringkas = M.ringkasan_mitra(m["id"])
                if tipe == "customer":
                    total_trans = ringkas["total_invoice"]
                    saldo = ringkas["piutang"]
                else:
                    total_trans = ringkas["total_bill"]
                    saldo = ringkas["utang"]
                total_saldo += saldo
                idx = len(baris)
                baris.append([
                    m["kode"], m["nama"], m["npwp"] or "",
                    m["telepon"] or m["email"] or "", m["kota"] or "",
                    f"{m['termin_hari']} hari", tx.rupiah(total_trans),
                    tx.rupiah(saldo) if saldo else "",
                ])
                if saldo > 0:
                    warna[idx] = C.WARNING
                if m["batas_kredit"] and ringkas["piutang"] > m["batas_kredit"]:
                    warna[idx] = C.DANGER
            tabel.isi(baris, warna_baris=warna, align_kanan={6, 7})
            label = "pelanggan" if tipe == "customer" else "pemasok"
            tabel._lbl_info.setText(
                f"{len(data)} {label} · total saldo {tx.rupiah(total_saldo)}")

    def _tabel_aktif(self) -> w.Tabel:
        return self.tabel_cust if self.tipe_aktif == "customer" else self.tabel_vend

    def _mitra_terpilih(self):
        t = self._tabel_aktif()
        r = t.baris_terpilih()
        if r is None:
            return None
        data = M.daftar_mitra(self.ctx.company_id, self.tipe_aktif,
                              t._inp_cari.text().strip())
        return data[r] if r < len(data) else None

    def _tambah(self):
        if not self.ctx.company_id:
            QMessageBox.information(self, "Belum ada perusahaan",
                                    "Buat profil perusahaan terlebih dahulu.")
            return
        d = DialogMitra(self.ctx, self, tipe_awal=self.tipe_aktif)
        if d.exec():
            self.muat()

    def _ubah(self):
        m = self._mitra_terpilih()
        if m is None:
            QMessageBox.information(self, "Belum dipilih", "Pilih satu mitra.")
            return
        d = DialogMitra(self.ctx, self, m)
        if d.exec():
            self.muat()

    def _detail(self):
        m = self._mitra_terpilih()
        if m is None:
            return
        DialogDetailMitra(m["id"], self).exec()

    def _hapus(self):
        m = self._mitra_terpilih()
        if m is None:
            QMessageBox.information(self, "Belum dipilih", "Pilih satu mitra.")
            return
        if QMessageBox.question(
                self, "Konfirmasi Hapus",
                f"Hapus mitra '{m['nama']}'?\n\n"
                "Data akan dipindahkan ke keranjang sampah dan dapat dipulihkan.",
                QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            M.hapus_mitra(m["id"], self.ctx.username)
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
            hasil = O.impor_mitra_massal(self.ctx.company_id, isi,
                                         self.tipe_aktif, self.ctx.user_id)
            pesan = (f"Impor selesai.\n\n"
                     f"Berhasil: {hasil['berhasil']}\n"
                     f"Duplikat dilewati: {hasil['duplikat']}\n"
                     f"Gagal: {hasil['gagal']}")
            if hasil["pesan"]:
                pesan += "\n\nCatatan:\n" + "\n".join(hasil["pesan"][:5])
            QMessageBox.information(self, "Hasil Impor", pesan)
            self.muat()
        except Exception as e:
            QMessageBox.critical(self, "Gagal mengimpor", str(e))
