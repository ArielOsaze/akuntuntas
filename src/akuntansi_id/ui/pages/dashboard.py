"""
AkunTuntas - Dashboard & Analisis Kesehatan Keuangan
=====================================================
Halaman pertama setelah login. Menampilkan:
  1. Skor kesehatan keuangan + diagnosis otomatis
  2. KPI utama (omzet, laba, kas, aset, pajak)
  3. Temuan analisis (kritis  saran) dengan tindakan konkret
  4. Tenggat pajak terdekat
  5. Peringatan batas PKP
  6. Grafik kinerja bulanan
"""
from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt, Signal, QRectF
from PySide6.QtGui import QPainter, QColor, QPen, QFont, QBrush, QLinearGradient
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QFrame,
    QComboBox, QSizePolicy, QPushButton,
)

from ... import config, services
from ...core import accounting as acc
from .. import icons
from .. import theme
from ..theme import C
from .. import widgets as w


# ==========================================================================
# GRAFIK BATANG SEDERHANA (tanpa dependensi tambahan)
# ==========================================================================
class BarChart(QWidget):
    """
    Grafik batang pendapatan vs beban per bulan.

    Dilengkapi label nilai di atas batang tertinggi, garis tren laba, sorotan
    bulan yang sedang ditunjuk, dan keterangan angka saat kursor diarahkan ke
    sebuah bulan.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.data: list[dict] = []
        self.setMinimumHeight(240)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.setMouseTracking(True)
        self.setCursor(Qt.CrossCursor)
        self._bulan_sorot = -1
        self._kotak: list[tuple] = []
        # dipanggil setiap kali bulan yang ditunjuk berubah
        self.sorotan_berubah = None

    def set_data(self, data: list[dict]):
        self.data = data
        self._bulan_sorot = -1
        self.update()

    def leaveEvent(self, peristiwa):
        if self._bulan_sorot != -1:
            self._bulan_sorot = -1
            self._beri_tahu()
            self.update()
        super().leaveEvent(peristiwa)

    def mouseMoveEvent(self, peristiwa):
        pos = peristiwa.position()
        bulan = -1
        for i, x0, x1, _y0, _y1 in self._kotak:
            if x0 <= pos.x() <= x1:
                bulan = i
                break
        if bulan != self._bulan_sorot:
            self._bulan_sorot = bulan
            self._beri_tahu()
            self.update()
        super().mouseMoveEvent(peristiwa)

    def _beri_tahu(self):
        if callable(self.sorotan_berubah):
            self.sorotan_berubah()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        w, h = self.width(), self.height()
        p.fillRect(self.rect(), QColor(C.SURFACE))
        self._kotak = []

        # Dua keadaan dianggap belum ada data: daftarnya kosong, dan
        # daftarnya terisi tetapi seluruh nilainya nol. Keadaan kedua
        # muncul saat perusahaan baru dibuat, karena kedua belas bulan
        # sudah ada tetapi belum satu pun berisi angka. Tanpa pemeriksaan
        # ini, grafiknya tergambar sebagai garis rata nol yang terbaca
        # seperti grafik rusak.
        ada_angka = any(
            d["pendapatan"] or d["beban"] or d["hpp"] for d in (self.data or []))
        if not self.data or not ada_angka:
            p.setPen(QColor(C.TEXT_MUTED))
            f = QFont(theme.FONT_UI)
            f.setPixelSize(theme.FS_BODY)
            p.setFont(f)
            p.drawText(self.rect(), Qt.AlignCenter,
                       "Belum ada transaksi pada tahun ini.\n"
                       "Grafik akan terisi setelah Anda mencatat transaksi.")
            p.end()
            return

        # Margin diberi ruang lebih supaya label sumbu dan label nilai tidak
        # berdesakan dengan bidang grafiknya.
        margin_kiri, margin_kanan = 86, 24
        margin_atas, margin_bawah = 42, 46
        lebar_grafik = w - margin_kiri - margin_kanan
        tinggi_grafik = h - margin_atas - margin_bawah
        if lebar_grafik <= 10 or tinggi_grafik <= 10:
            p.end()
            return

        dasar = margin_atas + tinggi_grafik
        maks = max((max(d["pendapatan"], d["beban"] + d["hpp"]) for d in self.data),
                   default=0)
        if maks <= 0:
            maks = 1
        maks_bulat = self._batas_atas(maks)

        # grid horizontal bergaris putus agar tidak bersaing dengan batang
        p.setFont(QFont(theme.FONT_UI, 8))
        for i in range(5):
            y = margin_atas + tinggi_grafik * i / 4
            pena = QPen(QColor(C.BORDER), 1, Qt.DashLine)
            pena.setDashPattern([3, 4])
            p.setPen(pena)
            p.drawLine(int(margin_kiri), int(y), int(w - margin_kanan), int(y))
            p.setPen(QColor(C.TEXT_FAINT))
            p.drawText(QRectF(0, y - 8, margin_kiri - 16, 16),
                       Qt.AlignRight | Qt.AlignVCenter,
                       self._singkat(maks_bulat * (4 - i) / 4))

        n = len(self.data)
        lebar_grup = lebar_grafik / n
        lebar_batang = max(5.0, min(16.0, lebar_grup * 0.28))
        celah = 3.0

        # garis tren laba sebelum pajak
        titik_tren = []
        for i, d in enumerate(self.data):
            pusat = margin_kiri + i * lebar_grup + lebar_grup / 2
            laba = d["laba_sebelum_pajak"]
            y = dasar - (laba / maks_bulat) * tinggi_grafik
            titik_tren.append((pusat, y))

        # garis tren laba digambar lebih dulu agar berada di belakang batang
        # dan tidak menyentuh label nilainya
        if len(titik_tren) > 1:
            pena = QPen(QColor(C.POSITIF), 2)
            pena.setCapStyle(Qt.RoundCap)
            p.setPen(pena)
            p.setBrush(Qt.NoBrush)
            for (x1, y1), (x2, y2) in zip(titik_tren, titik_tren[1:]):
                p.drawLine(int(x1), int(y1), int(x2), int(y2))
            p.setBrush(QColor(C.POSITIF))
            p.setPen(Qt.NoPen)
            for x, y in titik_tren:
                p.drawEllipse(QRectF(x - 2.5, y - 2.5, 5, 5))

            # Laba negatif ditandai angkanya supaya besar kerugian terbaca,
            # bukan hanya terlihat dari garis yang turun di bawah nol.
            p.setFont(QFont(theme.FONT_UI, 7))
            fm_tren = p.fontMetrics()
            for i, (x, y) in enumerate(titik_tren):
                laba = self.data[i]["laba_sebelum_pajak"]
                if laba >= 0:
                    continue
                teks = self._nilai_batang(abs(laba))
                lebar_teks = fm_tren.horizontalAdvance(teks) + 6
                p.setPen(QColor(C.NEGATIF))
                p.drawText(QRectF(x - lebar_teks / 2, y + 6, lebar_teks, 12),
                           Qt.AlignCenter, teks)

        for i, d in enumerate(self.data):
            pusat = margin_kiri + i * lebar_grup + lebar_grup / 2
            x0 = pusat - lebar_batang - celah / 2
            sorot = i == self._bulan_sorot

            if sorot:
                p.setPen(Qt.NoPen)
                p.setBrush(QColor(C.SURFACE_ALT))
                p.drawRoundedRect(
                    QRectF(margin_kiri + i * lebar_grup + 2, margin_atas - 6,
                           lebar_grup - 4, tinggi_grafik + 10), 6, 6)

            h1 = (d["pendapatan"] / maks_bulat) * tinggi_grafik
            grad1 = QLinearGradient(0, dasar - h1, 0, dasar)
            grad1.setColorAt(0, QColor(C.PRIMARY))
            grad1.setColorAt(1, QColor(C.PRIMARY_LIGHT))
            p.setBrush(QBrush(grad1))
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(QRectF(x0, dasar - h1, lebar_batang, h1), 3, 3)

            beban = d["beban"] + d["hpp"]
            h2 = (beban / maks_bulat) * tinggi_grafik
            grad2 = QLinearGradient(0, dasar - h2, 0, dasar)
            grad2.setColorAt(0, QColor(C.WARNING))
            grad2.setColorAt(1, QColor("#E8C9A0"))
            p.setBrush(QBrush(grad2))
            p.drawRoundedRect(QRectF(x0 + lebar_batang + celah, dasar - h2,
                                     lebar_batang, h2), 3, 3)

            # Nilai di atas tiap batang dengan jarak tetap dari puncaknya,
            # sehingga tidak menempel pada batang. Bila kedua label akan
            # beririsan karena batangnya berdekatan, salah satunya dinaikkan.
            p.setFont(QFont(theme.FONT_UI, 7))
            fm = p.fontMetrics()
            tengah1 = x0 + lebar_batang / 2
            tengah2 = x0 + lebar_batang * 1.5 + celah
            t1 = self._nilai_batang(d["pendapatan"])
            t2 = self._nilai_batang(beban)
            l1 = fm.horizontalAdvance(t1) + 8
            l2 = fm.horizontalAdvance(t2) + 8

            ada1 = h1 >= 18
            ada2 = h2 >= 18
            # Label nilai disembunyikan bila kolomnya terlalu sempit untuk
            # memuatnya. Pada layar sempit, label nilai antar bulan akan
            # bertumpuk dan angkanya justru tidak terbaca. Angka yang sama
            # tetap dapat dibaca dari keterangan di atas grafik.
            if lebar_grup < l1 + 6:
                ada1 = False
            if lebar_grup < l2 + 6:
                ada2 = False

            jarak_label = 8          # jarak label ke puncak batang
            tinggi_label = 13
            berdekatan = (ada1 and ada2
                          and abs(tengah1 - tengah2) < (l1 + l2) / 2)

            batas_atas_teks = margin_atas - 14

            if ada1:
                y1 = dasar - h1 - jarak_label - tinggi_label
                if berdekatan:
                    y1 -= tinggi_label + 1
                y1 = max(y1, batas_atas_teks)
                x1 = min(max(tengah1 - l1 / 2, 2.0), w - l1 - 2)
                p.setPen(QColor(C.PRIMARY))
                p.drawText(QRectF(x1, y1, l1, tinggi_label), Qt.AlignCenter, t1)

            if ada2:
                y2 = dasar - h2 - jarak_label - tinggi_label
                y2 = max(y2, batas_atas_teks)
                x2 = min(max(tengah2 - l2 / 2, 2.0), w - l2 - 2)
                # Bila label beban beririsan mendatar dengan label pendapatan,
                # geser ke bawah sampai benar-benar tidak bertumpuk. Pergeseran
                # sebelumnya hanya sebesar tinggi label, sehingga masih
                # menyisakan tumpang tindih beberapa piksel.
                if ada1 and not (x2 + l2 <= x1 or x1 + l1 <= x2):
                    batas_bawah = dasar - tinggi_label - 2
                    if abs(y2 - y1) < tinggi_label + 2:
                        y2 = min(y1 + tinggi_label + 3, batas_bawah)
                    # Bila masih bertumpuk karena ruang bawah tidak cukup,
                    # geser mendatar ke sisi yang masih lapang.
                    if abs(y2 - y1) < tinggi_label + 2:
                        geser = x1 + l1 - x2 + 2
                        if x2 + geser + l2 <= w - 2:
                            x2 += geser
                        elif x1 - l2 - 2 >= 2:
                            x2 = x1 - l2 - 2
                p.setPen(QColor(C.WARNING))
                p.drawText(QRectF(x2, y2, l2, tinggi_label), Qt.AlignCenter, t2)

            p.setPen(QColor(C.TEXT) if sorot else (
                QColor(C.TEXT_FAINT) if (d["pendapatan"] == 0 and beban == 0)
                else QColor(C.TEXT_MUTED)))
            p.setFont(QFont(theme.FONT_UI, 8, QFont.Bold if sorot else QFont.Normal))
            # Nama bulan dipendekkan bila kolomnya lebih sempit dari teksnya,
            # supaya label bulan yang berdekatan tidak saling menimpa.
            fm_bulan = p.fontMetrics()
            teks_bulan = config.MONTH_ABBR_ID[i]
            lebar_perlu = fm_bulan.horizontalAdvance(teks_bulan) + 4
            if lebar_perlu > lebar_grup:
                teks_bulan = teks_bulan[0]
            # Bulan terakhir dibatasi agar tidak melewati tepi kanan grafik.
            kiri_label = margin_kiri + i * lebar_grup + 2
            lebar_label = max(1.0, lebar_grup - 4)
            if kiri_label + lebar_label > w - 4:
                lebar_label = max(1.0, w - 4 - kiri_label)
            p.drawText(QRectF(kiri_label, dasar + 11, lebar_label, 16),
                       Qt.AlignCenter, teks_bulan)

            self._kotak.append((i, margin_kiri + i * lebar_grup + 2,
                                margin_kiri + (i + 1) * lebar_grup - 2,
                                margin_atas, dasar))

        p.setPen(QPen(QColor(C.BORDER_STRONG), 1))
        p.drawLine(int(margin_kiri), int(dasar), int(w - margin_kanan), int(dasar))

        if 0 <= self._bulan_sorot < n:
            self._gambar_penunjuk(p, w, margin_atas, dasar, tinggi_grafik)
        p.end()

    def _gambar_penunjuk(self, p, lebar, atas, dasar, tinggi_grafik):
        """
        Penunjuk bulan terpilih: sorotan kolom dan label nama bulan.

        Angka rinciannya tidak digambar di dalam bidang grafik supaya tidak
        menutupi batang; pemanggil menampilkannya di panel bawah grafik lewat
        bulan_terpilih().
        """
        d = self.data[self._bulan_sorot]
        n = max(1, len(self.data))
        lebar_grafik = lebar - 70 - 18
        lebar_grup = lebar_grafik / n
        kiri = 70 + self._bulan_sorot * lebar_grup

        p.setPen(Qt.NoPen)
        p.setBrush(QColor(C.SURFACE_ALT))
        p.drawRoundedRect(QRectF(kiri + 2, atas - 8, lebar_grup - 4,
                                 tinggi_grafik + 12), 6, 6)

        beban = d["beban"] + d["hpp"]
        puncak = max(d["pendapatan"], beban)
        maks_bulat = self._batas_atas(
            max(max(q["pendapatan"], q["beban"] + q["hpp"]) for q in self.data))
        p.setPen(QPen(QColor(C.PRIMARY), 1, Qt.DotLine))
        p.drawLine(int(kiri), int(atas - 8), int(kiri + lebar_grup),
                   int(atas - 8))

        # penanda nilai di puncak batang bulan terpilih
        if puncak > 0:
            y = dasar - (puncak / maks_bulat) * tinggi_grafik
            teks = self._singkat(puncak)
            p.setFont(QFont(theme.FONT_UI, 8, QFont.Bold))
            fm = p.fontMetrics()
            lebar_teks = fm.horizontalAdvance(teks) + 14
            x = max(6.0, min(kiri + lebar_grup / 2 - lebar_teks / 2,
                             lebar - lebar_teks - 6))
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(C.PRIMARY))
            p.drawRoundedRect(QRectF(x, y - 20, lebar_teks, 17), 8, 8)
            p.setPen(QColor("#FFFFFF"))
            p.drawText(QRectF(x, y - 20, lebar_teks, 17),
                       Qt.AlignCenter, teks)

    def bulan_terpilih(self) -> dict | None:
        """Data bulan yang sedang ditunjuk, atau None bila tidak ada."""
        if 0 <= self._bulan_sorot < len(self.data):
            return self.data[self._bulan_sorot]
        return None

    @staticmethod
    def _nilai_batang(v: float) -> str:
        """
        Angka ringkas untuk label di atas batang.

        Satuannya sudah tercantum pada sumbu Y, jadi label cukup memuat
        angkanya saja. Label yang pendek tidak menutupi batang di sebelahnya
        dan tidak berdesakan saat batangnya berdekatan.
        """
        v = float(v)
        if v >= 1_000_000_000:
            return f"{v / 1_000_000_000:.1f}M"
        if v >= 1_000_000:
            angka = v / 1_000_000
            return f"{angka:.0f}" if angka >= 10 else f"{angka:.1f}"
        if v >= 1_000:
            return f"{v / 1_000:.0f}rb"
        return f"{v:.0f}"

    @staticmethod
    def _batas_atas(maks: float) -> float:
        """
        Batas atas sumbu berupa angka bulat yang mudah dibaca.

        Nilai puncak dibulatkan ke kelipatan 1, 2, 2,5, atau 5 dikali pangkat
        sepuluh terdekat, sehingga garis gridnya jatuh pada angka seperti 25,
        50, 75, 100 juta, bukan 22 atau 68 juta.
        """
        if maks <= 0:
            return 1.0
        pangkat = 10 ** int(len(str(int(maks))) - 1)
        for faktor in (1.0, 1.2, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0):
            kandidat = faktor * pangkat
            if kandidat >= maks:
                return kandidat
        return 10.0 * pangkat

    @staticmethod
    def _singkat(v: float) -> str:
        v = float(v)
        if v >= 1_000_000_000:
            return f"{v / 1_000_000_000:.1f} M"
        if v >= 1_000_000:
            return f"{v / 1_000_000:.0f} jt"
        if v >= 1_000:
            return f"{v / 1_000:.0f} rb"
        return f"{v:.0f}"


# ==========================================================================
# DASHBOARD
# ==========================================================================
class DashboardPage(QWidget):
    pindah_halaman = Signal(str)

    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx

        luar = QVBoxLayout(self)
        luar.setContentsMargins(0, 0, 0, 0)
        luar.setSpacing(0)

        # header
        self.header = w.PageHeader(
            "Dashboard",
            "Ringkasan kondisi keuangan dan kepatuhan pajak perusahaan Anda.")
        self.btn_refresh = w.tombol("Muat Ulang", gaya="biasa", ikon="segarkan")
        self.btn_refresh.clicked.connect(self.muat)
        self.header.tambah_aksi(self.btn_refresh)

        self.cmb_tahun = QComboBox()
        tahun_kini = datetime.now().year
        for t in range(tahun_kini - 3, tahun_kini + 2):
            self.cmb_tahun.addItem(str(t), t)
        idx = self.cmb_tahun.findData(ctx.tahun)
        if idx >= 0:
            self.cmb_tahun.setCurrentIndex(idx)
        self.cmb_tahun.currentIndexChanged.connect(self._ganti_tahun)
        self.cmb_tahun.setMinimumWidth(105)
        self.header.tambah_aksi(self.cmb_tahun)

        kepala = QWidget()
        theme.latar(kepala, f"background: {C.SURFACE}; "
                             f"border-bottom: 1px solid {C.BORDER};")
        kl = QVBoxLayout(kepala)
        kl.setContentsMargins(26, 20, 26, 18)
        kl.addWidget(self.header)
        luar.addWidget(kepala)

        # isi yang bisa digulir
        self.isi = QWidget()
        self.isi_lay = QVBoxLayout(self.isi)
        self.isi_lay.setContentsMargins(26, 22, 26, 26)
        self.isi_lay.setSpacing(18)
        luar.addWidget(w.scroll(self.isi), 1)

    # ------------------------------------------------------------------
    def _ganti_tahun(self):
        self.ctx.tahun = self.cmb_tahun.currentData()
        self.muat()

    # ------------------------------------------------------------------
    def muat(self):
        """Bangun ulang seluruh isi dashboard."""
        self._bersihkan()
        cid = self.ctx.company_id
        tahun = self.ctx.tahun

        if not cid:
            self._tampilkan_tanpa_perusahaan()
            return

        comp = services.get_company(cid)
        if comp is None:
            self._tampilkan_tanpa_perusahaan()
            return

        self.header.set_subjudul(
            f"{comp['nama']} · {config.ENTITY_TYPES.get(comp['bentuk'], {}).get('nama', comp['bentuk'])} "
            f"· Tahun pajak {tahun}")

        # ============================================================
        # 1. KPI UTAMA — paling atas, angka yang dicari pertama
        # ============================================================
        try:
            kpi = services.kpi_dashboard(cid, tahun)
        except Exception:
            kpi = None

        if kpi:
            self.isi_lay.addWidget(self._panel_kpi(kpi, comp, tahun))

        # ============================================================
        # 1b. PANDUAN LANGKAH AWAL
        #     Saat pembukuan masih kosong, seluruh kartu menampilkan nol.
        #     Angka nol tidak memberi tahu apa yang harus dilakukan, jadi
        #     panduan ini ditampilkan hanya pada keadaan itu.
        # ============================================================
        if kpi and kpi.get("jumlah_jurnal_total", 0) == 0:
            self.isi_lay.addWidget(self._panel_mulai(comp))

        # ============================================================
        # 2. SKOR KESEHATAN + GRAFIK — berdampingan agar keduanya
        #    terlihat tanpa menggulir.
        # ============================================================
        try:
            analisis = services.analisis(cid, tahun)
        except Exception as e:
            analisis = None
            self.isi_lay.addWidget(w.InfoBanner(
                f"Analisis tidak dapat dijalankan: {e}", "danger",
                "Terjadi kesalahan"))

        # Dua panel diletakkan berdampingan pada jendela lebar, dan bertumpuk
        # pada jendela sempit. Pemilihan susunan dilakukan otomatis memakai
        # grid: bila lebar kurang dari 1100 piksel, kedua panel ditumpuk
        # supaya tidak ada yang terpotong. Ini menghindari pembagian ruang
        # yang dipaksakan, yang membuat salah satu panel terlalu sempit.
        from PySide6.QtWidgets import QGridLayout
        baris = QWidget()
        baris.setStyleSheet("background: transparent;")
        grid = QGridLayout(baris)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(14)

        if analisis is not None:
            panel_kesehatan = self._panel_kesehatan(analisis, comp)
            panel_kesehatan.setMinimumWidth(380)
            grid.addWidget(panel_kesehatan, 0, 0)

        try:
            panel_grafik = self._panel_grafik(cid, tahun)
            panel_grafik.setMinimumWidth(360)
            grid.addWidget(panel_grafik, 0, 1)
        except Exception:
            pass

        grid.setColumnStretch(0, 6)
        grid.setColumnStretch(1, 5)
        # Kolom kedua turun ke baris berikutnya saat jendela menyempit.
        grid.setColumnMinimumWidth(0, 380)
        grid.setColumnMinimumWidth(1, 360)
        self._grid_panel = grid

        if grid.count():
            self.isi_lay.addWidget(baris)

        # ============================================================
        # 3. TENGGAT PAJAK
        # ============================================================
        try:
            self.isi_lay.addWidget(self._panel_deadline(cid))
        except Exception:
            pass

        # ============================================================
        # 4. KONTRAK PERLU PERHATIAN
        # ============================================================
        try:
            panel_kontrak = self._panel_kontrak(cid)
            if panel_kontrak is not None:
                self.isi_lay.addWidget(panel_kontrak)
        except Exception:
            pass

        # ============================================================
        # 5. TEMUAN ANALISIS LENGKAP
        # ============================================================
        if analisis is not None and analisis.temuan:
            self.isi_lay.addWidget(self._panel_temuan(analisis))

        # ============================================================
        # 6. PROYEKSI
        # ============================================================
        try:
            self.isi_lay.addWidget(self._panel_proyeksi(cid, tahun))
        except Exception:
            pass

        self.isi_lay.addStretch()

    def _bersihkan(self):
        """Buang seluruh isi panel lama sebelum menyusun ulang.

        Widget dibuang langsung dari tata letak dan dilepas dari induknya,
        sehingga tidak ada sisa tampilan yang menumpuk saat halaman dimuat ulang.
        """
        while self.isi_lay.count():
            item = self.isi_lay.takeAt(0)
            wdg = item.widget()
            if wdg is not None:
                wdg.setParent(None)
                wdg.deleteLater()

    # ==================================================================
    # PANEL: KESEHATAN KEUANGAN
    # ==================================================================
    def _panel_kesehatan(self, analisis, comp) -> QWidget:
        kartu = w.Card()
        lay = kartu.ganti_isi(QVBoxLayout())
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # --- bagian atas: skor + ringkasan
        atas = QWidget()
        atas.setStyleSheet("background: transparent;")
        al = QHBoxLayout(atas)
        al.setContentsMargins(24, 22, 28, 20)
        al.setSpacing(28)

        gauge = w.SkorGauge(ukuran=158)
        # Bila pembukuan masih kosong, lingkaran tidak menampilkan angka.
        belum_dinilai = analisis.grade == "N/A"
        gauge.set_skor(analisis.skor, analisis.grade_label,
                       belum_dinilai=belum_dinilai)
        al.addWidget(gauge, 0, Qt.AlignVCenter)

        kanan = QVBoxLayout()
        kanan.setSpacing(11)

        judul_baris = QHBoxLayout()
        judul_baris.setSpacing(12)
        j = QLabel("Kesehatan Keuangan")
        j.setStyleSheet("font-size: 19px; font-weight: 700; background: transparent;")
        # Judul boleh membungkus menjadi dua baris. Dengan penskalaan tampilan
        # Windows, lebar teks dapat membesar sementara ruang panel tetap, dan
        # tanpa pembungkusan tulisannya terpotong. Membungkus dua baris tetap
        # terbaca utuh dan tidak mengubah susunan panel.
        j.setWordWrap(True)
        j.setMinimumWidth(0)
        judul_baris.addWidget(j)
        judul_baris.addStretch()
        kanan.addLayout(judul_baris)

        # Badge hanya ditampilkan bila panel cukup lebar untuk memuatnya
        # bersama judul. Pada jendela sempit, badge disembunyikan supaya
        # judulnya tetap terbaca utuh. Keterangan grade sudah tercantum pada
        # kalimat ringkasan di bawahnya, sehingga tidak ada informasi hilang.
        #
        # Saat pembukuan masih kosong, badge diberi warna netral. Warna
        # peringatan akan terbaca sebagai penilaian buruk, padahal yang
        # terjadi adalah belum ada yang dapat dinilai.
        if belum_dinilai:
            badge_warna, badge_bg = C.TEXT_MUTED, C.NEUTRAL_BG
        else:
            badge_warna, badge_bg = theme.STATUS_COLORS.get(
                "baik" if analisis.skor >= 70 else
                ("peringatan" if analisis.skor >= 55 else "kritis"),
                (C.TEXT_MUTED, C.NEUTRAL_BG))
        teks_badge = f"GRADE {analisis.grade} · {analisis.grade_label.upper()}"
        bdg = QLabel(teks_badge)
        theme.latar(bdg, f"background: {badge_bg}; color: {badge_warna}; border-radius: 9px; "
            f"padding: 4px 12px; font-size: {theme.FS_TINY}px; font-weight: 800;")
        bdg.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        bdg.setMinimumWidth(
            bdg.fontMetrics().horizontalAdvance(teks_badge) + 26)
        bdg.setVisible(self.width() >= 520)

        baris_badge = QHBoxLayout()
        baris_badge.addWidget(bdg)
        baris_badge.addStretch()
        kanan.addLayout(baris_badge)
        kanan.addSpacing(6)

        ringkasan = w.LabelTinggiOtomatis(w.rata_kanan_kiri(analisis.ringkasan))
        ringkasan.setTextFormat(Qt.RichText)
        ringkasan.setWordWrap(True)
        ringkasan.setStyleSheet(
            f"font-size: {theme.FS_BODY}px; color: {C.TEXT}; background: transparent; "
            "line-height: 168%;")
        ringkasan.setTextInteractionFlags(Qt.TextSelectableByMouse)
        kanan.addWidget(ringkasan)
        kanan.addSpacing(4)

        # penghitung temuan
        hitung = QHBoxLayout()
        hitung.setSpacing(9)
        for jumlah, label, tingkat in [
            (analisis.jumlah_kritis, "Kritis", "kritis"),
            (analisis.jumlah_peringatan, "Perhatian", "peringatan"),
            (analisis.jumlah_saran, "Saran", "saran"),
            (analisis.jumlah_baik, "Baik", "baik"),
        ]:
            warna, bg = theme.STATUS_COLORS[tingkat]
            chip = QLabel(f"<b style='font-size:15px'>{jumlah}</b>"
                          f"<span style='font-size:9px'> {label}</span>")
            chip.setTextFormat(Qt.RichText)
            chip.setAlignment(Qt.AlignCenter)
            theme.latar(chip, f"background: {bg}; color: {warna}; border-radius: 8px; "
                "padding: 5px 9px;")
            # Chip dibiarkan menyusut mengikuti ruang yang tersedia, tetapi
            # tidak lebih kecil dari ukuran isinya. Ukuran minimum dipakai
            # sebagai batas bawah, dan lebarnya dibatasi pada ukuran saran
            # supaya keempat chip tidak saling menimpa saat ruang sempit.
            chip.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
            chip.setMinimumWidth(0)
            hitung.addWidget(chip, 1)
        kanan.addLayout(hitung)
        al.addLayout(kanan, 1)
        lay.addWidget(atas)

        # --- bagian bawah: tombol tindakan
        bawah = QWidget()
        theme.latar(bawah, f"background: {C.SURFACE_ALT}; border-top: 1px solid {C.BORDER}; "
            "border-bottom-left-radius: 10px; border-bottom-right-radius: 10px;")
        bl = QHBoxLayout(bawah)
        bl.setContentsMargins(24, 13, 28, 13)
        bl.setSpacing(12)

        pesan = QLabel(
            "Analisis ini memeriksa 30+ aspek: keseimbangan jurnal, likuiditas, "
            "profitabilitas, solvabilitas, kepatuhan pajak, dan kualitas data."
        )
        pesan.setStyleSheet(f"font-size: {theme.FS_TINY}px; color: {C.TEXT_MUTED}; "
                            "background: transparent;")
        pesan.setWordWrap(True)
        bl.addWidget(pesan, 1)

        btn = w.tombol("Lihat Rincian Analisis", gaya="primary")
        btn.clicked.connect(lambda: self.pindah_halaman.emit("analisis"))
        bl.addWidget(btn)
        lay.addWidget(bawah)
        return kartu

    # ==================================================================
    # PANEL: PANDUAN LANGKAH AWAL
    # ==================================================================
    def _panel_mulai(self, comp) -> QWidget:
        """
        Panduan singkat saat pembukuan masih kosong.

        Seluruh kartu di dasbor menampilkan nol saat belum ada transaksi.
        Angka nol tidak memberi tahu apa yang harus dilakukan, sehingga
        pengguna baru berhenti di layar kosong. Panel ini hanya muncul pada
        keadaan itu, dan hilang sendiri begitu ada transaksi pertama.
        """
        wadah = QWidget()
        wadah.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(wadah)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        kartu = w.Card()
        isi = kartu.body()
        isi.setSpacing(14)

        kepala = QHBoxLayout()
        kepala.setSpacing(10)
        ikon = QLabel()
        ikon.setPixmap(icons.pixmap("bantuan", C.PRIMARY, 20))
        ikon.setFixedSize(20, 20)
        ikon.setStyleSheet("background: transparent;")
        kepala.addWidget(ikon)

        judul = QLabel("Langkah pertama menyiapkan pembukuan")
        judul.setObjectName("SectionTitle")
        judul.setWordWrap(True)
        kepala.addWidget(judul, 1)
        isi.addLayout(kepala)

        nama = comp.get("nama") if isinstance(comp, dict) else None
        keterangan = QLabel(
            f"Bagan akun untuk {nama or 'usaha Anda'} sudah disiapkan otomatis. "
            "Dasbor masih menampilkan nol karena belum ada transaksi yang "
            "dicatat. Ikuti langkah berikut supaya laporan keuangan Anda "
            "mulai terisi." if nama else
            "Bagan akun sudah disiapkan otomatis. Dasbor masih menampilkan "
            "nol karena belum ada transaksi yang dicatat. Ikuti langkah "
            "berikut supaya laporan keuangan Anda mulai terisi.")
        keterangan.setWordWrap(True)
        keterangan.setStyleSheet(
            f"color: {C.TEXT_MUTED}; font-size: {theme.FS_BODY}px; "
            f"background: transparent;")
        isi.addWidget(keterangan)

        langkah = [
            ("1", "Catat data usaha",
             "Nama, NPWP, dan bentuk badan usaha dipakai untuk menghitung "
             "pajak dan menyusun laporan."),
            ("2", "Daftarkan pelanggan dan pemasok",
             "Daftar ini mengisi pilihan pada formulir penjualan dan "
             "pembelian, sehingga pencatatan berikutnya lebih cepat."),
            ("3", "Daftarkan produk atau jasa",
             "Produk memuat harga jual, harga beli, dan persediaan. Bagian "
             "ini dapat dilewati bila usaha Anda berupa jasa."),
            ("4", "Catat penjualan atau pembelian pertama",
             "Satu transaksi sudah cukup untuk mengisi dasbor, laporan, dan "
             "penilaian kesehatan keuangan."),
        ]

        for nomor, judul_langkah, penjelasan in langkah:
            b = QHBoxLayout()
            b.setSpacing(11)

            lencana = QLabel(nomor)
            lencana.setFixedSize(24, 24)
            lencana.setAlignment(Qt.AlignCenter)
            # Gaya ditulis lewat theme.latar() supaya hanya berlaku pada
            # label ini, tidak menular ke widget di dalamnya.
            theme.latar(
                lencana,
                f"background: {C.PRIMARY_SOFT}; color: {C.PRIMARY_DARK}; "
                f"border-radius: 12px; font-size: {theme.FS_SMALL}px; "
                f"font-weight: 700;")

            teks = QVBoxLayout()
            teks.setSpacing(2)
            jl = QLabel(judul_langkah)
            jl.setStyleSheet(
                f"color: {C.TEXT}; font-size: {theme.FS_BODY}px; "
                f"font-weight: 600; background: transparent;")
            jl.setWordWrap(True)
            pl = QLabel(penjelasan)
            pl.setStyleSheet(
                f"color: {C.TEXT_MUTED}; font-size: {theme.FS_SMALL}px; "
                f"background: transparent;")
            pl.setWordWrap(True)
            teks.addWidget(jl)
            teks.addWidget(pl)

            b.addWidget(lencana, 0, Qt.AlignTop)
            b.addLayout(teks, 1)
            isi.addLayout(b)

        isi.addWidget(w.label(
            "Tombol di bawah membuka halaman yang bersangkutan. Setelah "
            "transaksi pertama tercatat, panduan ini tidak ditampilkan lagi.",
            objek="Muted"))

        tombol_baris = QHBoxLayout()
        tombol_baris.setSpacing(10)

        for teks_tombol, kode_halaman, keterangan_tombol in (
            ("Catat Penjualan", "penjualan",
             "Buka halaman penjualan untuk mencatat transaksi pertama"),
            ("Lihat Bagan Akun", "coa",
             "Periksa akun yang sudah disiapkan otomatis"),
        ):
            t = QPushButton(teks_tombol)
            t.setCursor(Qt.PointingHandCursor)
            t.setToolTip(keterangan_tombol)
            t.clicked.connect(
                lambda _=False, k=kode_halaman: self.pindah_halaman.emit(k))
            tombol_baris.addWidget(t)

        tombol_baris.addStretch()
        isi.addLayout(tombol_baris)

        lay.addWidget(kartu)
        return wadah

    # ==================================================================
    # PANEL: KPI
    # ==================================================================
    def _panel_kpi(self, kpi, comp, tahun) -> QWidget:
        wadah = QWidget()
        wadah.setStyleSheet("background: transparent;")
        grid = QGridLayout(wadah)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(14)
        # Tiga kartu dalam satu baris. Setiap kolom diberi bobot sama dan
        # boleh menyusut, sehingga isinya tidak pernah melebihi lebar jendela.
        # Tanpa ini, ukuran minimum kartu membuat baris melebar keluar tepi
        # dan kartu ketiga terpotong pada layar 1366 piksel.
        for kolom in range(3):
            grid.setColumnStretch(kolom, 1)
            grid.setColumnMinimumWidth(kolom, 0)

        omzet = kpi["omzet"]
        pct_pkp = omzet / config.THRESHOLD_PKP * 100
        warna_omzet = C.DANGER if pct_pkp >= 100 else (
            C.WARNING if pct_pkp >= 80 else C.TEXT)

        tiles = [
            ("Omzet / Peredaran Bruto", theme.money(omzet),
             f"{pct_pkp:.1f}% dari batas wajib PKP Rp4,8 M", warna_omzet, "laporan"),
            ("Laba Bersih", theme.money(kpi["laba_bersih"]),
             f"Margin {theme.persen(kpi['margin_bersih'])}",
             C.POSITIF if kpi["laba_bersih"] >= 0 else C.NEGATIF, "uang"),
            ("Kas & Bank", theme.money(kpi["kas"]),
             "Saldo likuid saat ini", C.TEXT, "bank"),
            ("Total Aset", theme.money(kpi["total_aset"]),
             f"Liabilitas {theme.money(kpi['total_liabilitas'])}", C.TEXT, "perusahaan"),
            ("PPh Terutang (estimasi)", theme.money(kpi["pph_terutang"]),
             kpi["pph_skema"], C.PRIMARY, "pajak"),
            ("Ekuitas", theme.money(kpi["total_ekuitas"]),
             f"ROE {theme.persen(kpi['laba_bersih'] / kpi['total_ekuitas'] if kpi['total_ekuitas'] else 0)}",
             C.TEXT, "penjualan"),
        ]
        for i, (label, nilai, hint, warna, ikon) in enumerate(tiles):
            grid.addWidget(w.KpiTile(label, nilai, hint, warna, ikon),
                           i // 3, i % 3)

        # peringatan integritas data
        if abs(kpi["selisih_jurnal"]) > 0.5 or abs(kpi["selisih_neraca"]) >= 1:
            pesan = []
            if abs(kpi["selisih_jurnal"]) > 0.5:
                pesan.append(f"jurnal tidak seimbang {theme.money(kpi['selisih_jurnal'])}")
            if abs(kpi["selisih_neraca"]) >= 1:
                pesan.append(f"neraca berselisih {theme.money(kpi['selisih_neraca'])}")
            grid.addWidget(w.InfoBanner(
                "Terdapat ketidakseimbangan: " + " dan ".join(pesan) +
                ". Perbaiki sebelum mempercayai angka di atas.",
                "danger", "Integritas data bermasalah"), 2, 0, 1, 3)

        return wadah

    # ==================================================================
    # PANEL: TENGGAT PAJAK
    # ==================================================================
    def _panel_kontrak(self, cid: int) -> QWidget:
        """Kontrak yang segera berakhir atau sudah melewati tenggatnya."""
        from ... import kontrak as kt
        perhatian = kt.yang_perlu_perhatian(cid)
        if not perhatian:
            return None

        kartu = w.Card()
        lay = kartu.body()
        lay.setSpacing(12)

        kepala = QHBoxLayout()
        j = QLabel("Kontrak Perlu Perhatian")
        j.setObjectName("SectionTitle")
        kepala.addWidget(j)
        kepala.addStretch()
        b = w.tombol("Buka Kontrak", gaya="ghost")
        b.clicked.connect(lambda: self.pindah_halaman.emit("kontrak"))
        kepala.addWidget(b)
        lay.addLayout(kepala)

        for k in perhatian[:3]:
            baris = QFrame()
            warna = C.DANGER if k["kondisi"] == "Sudah Berakhir" else C.WARNING
            bg = C.DANGER_BG if k["kondisi"] == "Sudah Berakhir" else C.WARNING_BG
            theme.latar(baris, f"background: {C.SURFACE_ALT}; "
                f"border: 1px solid {C.BORDER}; border-radius: 7px;")
            bl = QHBoxLayout(baris)
            bl.setContentsMargins(14, 9, 14, 9)
            bl.setSpacing(13)

            sisa = k.get("sisa_hari")
            if sisa is None:
                teks_hari = "Tanpa batas"
            elif sisa < 0:
                teks_hari = f"Lewat {abs(sisa)} hari"
            else:
                teks_hari = f"{sisa} hari lagi"
            kotak = QLabel(teks_hari)
            theme.latar(kotak, f"background: {bg}; color: {warna}; "
                f"border-radius: 6px; padding: 5px 11px; "
                f"font-size: {theme.FS_TINY}px; font-weight: 700;")
            kotak.setMinimumWidth(118)
            kotak.setAlignment(Qt.AlignCenter)
            bl.addWidget(kotak)

            kolom = QVBoxLayout()
            kolom.setSpacing(2)
            n = QLabel(f"{k['nomor']} · {k['judul']}")
            n.setStyleSheet(f"font-weight: 600; font-size: {theme.FS_BODY}px; "
                            "background: transparent;")
            n.setWordWrap(True)
            kolom.addWidget(n)
            ket = QLabel(
                f"{k['mitra'] or 'Tanpa mitra'} · berakhir "
                f"{theme.tanggal_id(k['tanggal_akhir']) if k['tanggal_akhir'] else '-'}")
            ket.setStyleSheet(f"font-size: {theme.FS_TINY}px; "
                              f"color: {C.TEXT_MUTED}; background: transparent;")
            ket.setWordWrap(True)
            kolom.addWidget(ket)
            bl.addLayout(kolom, 1)
            lay.addWidget(baris)

        sisa = len(perhatian) - 3
        if sisa > 0:
            b2 = w.tombol(f"Lihat {sisa} kontrak lainnya", gaya="ghost")
            b2.clicked.connect(lambda: self.pindah_halaman.emit("kontrak"))
            lay.addWidget(b2, 0, Qt.AlignLeft)
        return kartu

    # ==================================================================
    # PANEL: TENGGAT PAJAK
    # ==================================================================
    def _panel_deadline(self, cid: int) -> QWidget:
        kartu = w.Card()
        lay = kartu.body()
        lay.setSpacing(13)

        kepala = QHBoxLayout()
        j = QLabel("Tenggat Pajak Terdekat")
        j.setObjectName("SectionTitle")
        kepala.addWidget(j)
        kepala.addStretch()
        b = w.tombol("Lihat Checklist Kepatuhan", gaya="ghost")
        b.clicked.connect(lambda: self.pindah_halaman.emit("checklist"))
        kepala.addWidget(b)
        lay.addLayout(kepala)

        daftar = services.deadline_pajak(cid)
        if not daftar:
            lay.addWidget(w.label("Tidak ada tenggat terdekat.", objek="Muted"))
            return kartu

        for d in daftar[:3]:
            baris = QFrame()
            theme.latar(baris, f"background: {C.SURFACE_ALT}; border: 1px solid {C.BORDER}; "
                "border-radius: 7px;")
            bl = QHBoxLayout(baris)
            bl.setContentsMargins(14, 9, 14, 9)
            bl.setSpacing(13)

            hari = d["hari_tersisa"]
            if hari < 0:
                warna, bg, teks_hari = C.DANGER, C.DANGER_BG, f"Lewat {abs(hari)} hari"
            elif hari <= 7:
                warna, bg, teks_hari = C.WARNING, C.WARNING_BG, f"{hari} hari lagi"
            else:
                warna, bg, teks_hari = C.SUCCESS, C.SUCCESS_BG, f"{hari} hari lagi"

            kotak = QLabel(teks_hari)
            theme.latar(kotak, f"background: {bg}; color: {warna}; border-radius: 6px; "
                f"padding: 5px 11px; font-size: {theme.FS_TINY}px; font-weight: 700;")
            kotak.setMinimumWidth(118)
            kotak.setAlignment(Qt.AlignCenter)
            bl.addWidget(kotak)

            kolom = QVBoxLayout()
            kolom.setSpacing(2)
            n = QLabel(d["nama"])
            n.setStyleSheet(f"font-weight: 600; font-size: {theme.FS_BODY}px; "
                            "background: transparent;")
            kolom.addWidget(n)
            ket = QLabel(f"Masa {d['masa']} · jatuh tempo {theme.tanggal_id(d['tenggat'])} "
                         f"· {d['sanksi'][:70]}")
            ket.setStyleSheet(f"font-size: {theme.FS_TINY}px; color: {C.TEXT_MUTED}; "
                              "background: transparent;")
            ket.setWordWrap(True)
            kolom.addWidget(ket)
            bl.addLayout(kolom, 1)
            lay.addWidget(baris)

        sisa = len(daftar) - 3
        if sisa > 0:
            b2 = w.tombol(f"Lihat {sisa} tenggat lainnya", gaya="ghost")
            b2.clicked.connect(lambda: self.pindah_halaman.emit("checklist"))
            lay.addWidget(b2, 0, Qt.AlignLeft)

        return kartu

    # ==================================================================
    # PANEL: GRAFIK
    # ==================================================================
    def _panel_grafik(self, cid: int, tahun: int) -> QWidget:
        kartu = w.Card()
        lay = kartu.body()

        kepala = QHBoxLayout()
        kepala.setSpacing(14)
        j = QLabel(f"Kinerja Bulanan {tahun}")
        j.setObjectName("SectionTitle")
        j.setMinimumWidth(0)
        kepala.addWidget(j)
        kepala.addStretch()

        # Legenda diletakkan pada barisnya sendiri di bawah judul. Bila
        # ditempatkan sebaris dengan judul, ruang yang tersisa tidak cukup
        # pada layar 1366 piksel dan label terakhir terpotong. Menaruhnya
        # terpisah membuat seluruh label selalu terbaca utuh.
        legenda = QHBoxLayout()
        legenda.setSpacing(14)
        for bentuk, warna, teks in [
                ("kotak", C.PRIMARY, "Pendapatan"),
                ("kotak", C.WARNING, "HPP + Beban"),
                ("garis", C.POSITIF, "Laba sebelum pajak")]:
            item = QHBoxLayout()
            item.setSpacing(6)
            titik = QLabel()
            if bentuk == "kotak":
                titik.setFixedSize(11, 11)
                theme.latar(titik, f"background: {warna}; border-radius: 2px;")
            else:
                # penanda garis tren: batang tipis ditengah label
                titik.setFixedSize(15, 11)
                theme.latar(titik, f"background: {warna}; border-radius: 1px;")
                titik.setFixedHeight(3)
            item.addWidget(titik)
            t = QLabel(teks)
            t.setStyleSheet(f"font-size: {theme.FS_TINY}px; color: {C.TEXT_MUTED}; "
                            "background: transparent;")
            t.setMinimumWidth(t.fontMetrics().horizontalAdvance(teks) + 2)
            item.addWidget(t)
            legenda.addLayout(item)
        legenda.addStretch()

        lay.addLayout(kepala)
        lay.addSpacing(6)
        lay.addLayout(legenda)

        data = acc.ringkasan_bulanan(cid, tahun)
        chart = BarChart()
        chart.set_data(data)
        lay.addWidget(chart)

        # Baris keterangan: menampilkan angka bulan yang sedang ditunjuk,
        # dan kembali ke total setahun saat kursor keluar dari grafik.
        keterangan = QHBoxLayout()
        keterangan.setSpacing(26)

        stat_pendapatan = w.MiniStat("Total Pendapatan", theme.money(0))
        stat_beban = w.MiniStat("Total Beban", theme.money(0))
        stat_laba = w.MiniStat("Laba Sebelum Pajak", theme.money(0))
        for s in (stat_pendapatan, stat_beban, stat_laba):
            keterangan.addWidget(s)
        keterangan.addStretch()
        lay.addLayout(keterangan)

        total = {
            "pendapatan": sum(d["pendapatan"] for d in data),
            "beban": sum(d["beban"] + d["hpp"] for d in data),
            "laba": sum(d["laba_sebelum_pajak"] for d in data),
        }

        def tampilkan(nilai, judul):
            for stat, label, angka in (
                    (stat_pendapatan, judul[0], nilai["pendapatan"]),
                    (stat_beban, judul[1], nilai["beban"]),
                    (stat_laba, judul[2], nilai["laba"])):
                stat.set_teks_label(label)
                stat.set_nilai(
                    theme.money(angka),
                    None if stat is not stat_laba else
                    (C.POSITIF if nilai["laba"] >= 0 else C.NEGATIF))

        def perbarui():
            bulan = chart.bulan_terpilih()
            if bulan is None:
                tampilkan(total, ("Total Pendapatan", "Total Beban",
                                  "Laba Sebelum Pajak"))
                return
            kosong = bulan["pendapatan"] == 0 and (bulan["beban"] + bulan["hpp"]) == 0
            if kosong:
                tampilkan({"pendapatan": 0, "beban": 0, "laba": 0},
                          (f"{bulan['nama']} · belum ada transaksi",
                           "Beban", "Laba"))
                return
            tampilkan(
                {"pendapatan": bulan["pendapatan"],
                 "beban": bulan["beban"] + bulan["hpp"],
                 "laba": bulan["laba_sebelum_pajak"]},
                (f"Pendapatan {bulan['nama']}", "HPP + Beban",
                 "Laba Sebelum Pajak"))

        chart.sorotan_berubah = perbarui
        perbarui()
        return kartu

    # ==================================================================
    # PANEL: TEMUAN
    # ==================================================================
    def _panel_temuan(self, analisis) -> QWidget:
        kartu = w.Card()
        lay = kartu.body()
        lay.setSpacing(12)

        kepala = QHBoxLayout()
        j = QLabel("Temuan & Rekomendasi")
        j.setObjectName("SectionTitle")
        kepala.addWidget(j)
        kepala.addStretch()
        b = w.tombol("Buka Halaman Analisis", gaya="ghost")
        b.clicked.connect(lambda: self.pindah_halaman.emit("analisis"))
        kepala.addWidget(b)
        lay.addLayout(kepala)

        # Dashboard hanya menampilkan temuan terpenting agar ringkas;
        # daftar lengkapnya ada di halaman Analisis Keuangan.
        penting = [t for t in analisis.temuan if t.tingkat in ("kritis", "peringatan")]
        if not penting:
            penting = analisis.temuan[:2]

        tampil = penting[:2]
        for t in tampil:
            lay.addWidget(w.TemuanCard(t, ringkas=True))

        sisa = len(analisis.temuan) - len(tampil)
        if sisa > 0:
            b2 = w.tombol(f"Lihat {sisa} temuan lainnya", gaya="ghost")
            b2.clicked.connect(lambda: self.pindah_halaman.emit("analisis"))
            lay.addWidget(b2, 0, Qt.AlignLeft)
        return kartu

    # ==================================================================
    # PANEL: PROYEKSI
    # ==================================================================
    def _panel_proyeksi(self, cid: int, tahun: int) -> QWidget:
        p = services.proyeksi(cid, tahun)
        kartu = w.Card()
        lay = kartu.body()

        j = QLabel("Proyeksi Berdasarkan Kinerja Saat Ini")
        j.setObjectName("SectionTitle")
        lay.addWidget(j)

        if p["bulan_data"] == 0 or p["rata_pendapatan_bulanan"] == 0:
            lay.addWidget(w.label(
                "Belum cukup data untuk membuat proyeksi. Catat transaksi beberapa "
                "bulan agar proyeksi bermakna.", objek="Muted", wrap=True))
            return kartu

        # grid 2x2 agar setiap label dan angka punya ruang cukup
        grid = QGridLayout()
        grid.setHorizontalSpacing(30)
        grid.setVerticalSpacing(14)
        stat = [
            ("Rata-rata Pendapatan per Bulan",
             theme.money(p["rata_pendapatan_bulanan"]), None),
            ("Rata-rata Laba per Bulan",
             theme.money(p["rata_laba_bulanan"]),
             C.POSITIF if p["rata_laba_bulanan"] >= 0 else C.NEGATIF),
            ("Proyeksi Pendapatan Setahun",
             theme.money(p["proyeksi_pendapatan_tahun"]), None),
            ("Proyeksi Laba Setahun",
             theme.money(p["proyeksi_laba_tahun"]),
             C.POSITIF if p["proyeksi_laba_tahun"] >= 0 else C.NEGATIF),
        ]
        for i, (label, nilai, warna) in enumerate(stat):
            kotak = w.MiniStat(label, nilai, warna)
            kotak.setMinimumWidth(230)
            grid.addWidget(kotak, i // 2, i % 2)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        lay.addLayout(grid)

        if p["bulan_ke_batas_pkp"]:
            lay.addWidget(w.InfoBanner(
                f"Dengan laju pendapatan saat ini, batas wajib PKP Rp4,8 miliar "
                f"diperkirakan tercapai dalam {p['bulan_ke_batas_pkp']} bulan ke depan. "
                "Siapkan administrasi PKP: penomoran faktur pajak, pelaporan SPT Masa PPN, "
                "dan penyesuaian harga jual.",
                "warning", "Perkiraan waktu mencapai batas PKP"))

        catatan = w.label(p["catatan"], objek="Faint", wrap=True)
        catatan.setContentsMargins(0, 2, 0, 0)
        lay.addWidget(catatan)
        return kartu

    # ==================================================================
    def _tampilkan_tanpa_perusahaan(self):
        kartu = w.Card(padding=40)
        lay = kartu.body()
        lay.setSpacing(14)
        lay.setAlignment(Qt.AlignCenter)

        ikon = QLabel()
        ikon.setPixmap(icons.pixmap("perusahaan", icons.WARNA_MUTED, 56))
        ikon.setAlignment(Qt.AlignCenter)
        ikon.setStyleSheet("background: transparent;")
        lay.addWidget(ikon)

        j = QLabel("Belum ada data perusahaan")
        j.setAlignment(Qt.AlignCenter)
        j.setStyleSheet("font-size: 20px; font-weight: 700; background: transparent;")
        lay.addWidget(j)

        ket = QLabel(
            "Langkah pertama adalah membuat profil perusahaan. Setelah itu aplikasi "
            "otomatis menyiapkan bagan akun (chart of accounts) sesuai bentuk badan "
            "usaha yang Anda pilih."
        )
        ket.setAlignment(Qt.AlignCenter)
        ket.setWordWrap(True)
        ket.setStyleSheet(f"font-size: {theme.FS_BODY}px; color: {C.TEXT_MUTED}; "
                          "background: transparent;")
        lay.addWidget(ket)

        b = w.tombol("Buat Profil Perusahaan", gaya="primary")
        b.setMinimumHeight(42)
        b.clicked.connect(lambda: self.pindah_halaman.emit("perusahaan"))
        lay.addWidget(b, 0, Qt.AlignCenter)
        self.isi_lay.addWidget(kartu)
