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

import math
from datetime import datetime

from PySide6.QtCore import Qt, Signal, QRectF
from PySide6.QtGui import QPainter, QColor, QPen, QFont
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

        # Ruang atas tidak lagi dipakai label angka di atas batang, sehingga
        # grafik terasa lebih lapang dan batangnya menjadi fokus utama.
        margin_kiri, margin_kanan = 78, 20
        margin_atas, margin_bawah = 22, 42
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
        laba_min = min((d["laba_sebelum_pajak"] for d in self.data), default=0)
        nilai_bawah, nilai_atas, garis = self._sumbu(maks, laba_min)
        rentang_nilai = nilai_atas - nilai_bawah
        dasar_nol = margin_atas + (nilai_atas / rentang_nilai) * tinggi_grafik

        def posisi_y(nilai: float) -> float:
            return margin_atas + ((nilai_atas - nilai) / rentang_nilai) * tinggi_grafik

        # Garis bantu tipis dan rata, bukan garis putus-putus. Garis putus
        # membuat bidang grafik tampak ramai dan bersaing dengan batang.
        p.setFont(QFont(theme.FONT_UI, 8))
        for nilai in garis:
            y = posisi_y(nilai)
            p.setPen(QPen(QColor(C.BORDER), 1))
            p.drawLine(int(margin_kiri), int(y), int(w - margin_kanan), int(y))
            p.setPen(QColor(C.TEXT_FAINT))
            p.drawText(QRectF(0, y - 8, margin_kiri - 14, 16),
                       Qt.AlignRight | Qt.AlignVCenter,
                       self._singkat(nilai))

        n = len(self.data)
        lebar_grup = lebar_grafik / n
        lebar_batang = max(4.0, min(12.0, lebar_grup * 0.24))
        celah = 3.0
        self._geometri = {
            "kiri": margin_kiri, "kanan": margin_kanan, "atas": margin_atas,
            "dasar": dasar, "tinggi": tinggi_grafik, "lebar_grup": lebar_grup,
        }

        # Sorotan bulan yang ditunjuk digambar sekali di belakang seluruh
        # batang. Sebelumnya sorotan digambar per bulan dengan margin berbeda
        # dari batangnya, sehingga kolom yang tersorot bergeser dari batang.
        if 0 <= self._bulan_sorot < n:
            kiri_sorot = margin_kiri + self._bulan_sorot * lebar_grup
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(C.SURFACE_ALT))
            p.drawRoundedRect(
                QRectF(kiri_sorot + 2, margin_atas - 4,
                       lebar_grup - 4, tinggi_grafik + 8), 4, 4)

        # Garis laba digambar lebih dulu agar berada di belakang batang.
        titik_tren = []
        for i, d in enumerate(self.data):
            pusat = margin_kiri + i * lebar_grup + lebar_grup / 2
            titik_tren.append((pusat, posisi_y(d["laba_sebelum_pajak"])))

        if len(titik_tren) > 1:
            pena = QPen(QColor(C.POSITIF), 1.8)
            pena.setCapStyle(Qt.RoundCap)
            pena.setJoinStyle(Qt.RoundJoin)
            p.setPen(pena)
            p.setBrush(Qt.NoBrush)
            for (x1, y1), (x2, y2) in zip(titik_tren, titik_tren[1:]):
                p.drawLine(int(x1), int(y1), int(x2), int(y2))

        for i, d in enumerate(self.data):
            pusat = margin_kiri + i * lebar_grup + lebar_grup / 2
            x0 = pusat - lebar_batang - celah / 2
            sorot = i == self._bulan_sorot

            h1 = (d["pendapatan"] / rentang_nilai) * tinggi_grafik
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(C.PRIMARY))
            p.drawRoundedRect(QRectF(x0, dasar_nol - h1, lebar_batang, h1),
                              2, 2)

            beban = d["beban"] + d["hpp"]
            h2 = (beban / rentang_nilai) * tinggi_grafik
            p.setBrush(QColor(C.ACCENT))
            p.drawRoundedRect(QRectF(x0 + lebar_batang + celah,
                                     dasar_nol - h2, lebar_batang, h2), 2, 2)

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
        p.drawLine(int(margin_kiri), int(dasar_nol),
                   int(w - margin_kanan), int(dasar_nol))

        if 0 <= self._bulan_sorot < n:
            self._gambar_penunjuk(p, posisi_y)
        p.end()

    def _gambar_penunjuk(self, p, posisi_y):
        """
        Penanda bulan terpilih: garis tegak tipis dan titik pada garis laba.

        Angka rincian bulan ditampilkan di panel bawah grafik lewat
        bulan_terpilih(); menuliskannya di dalam bidang grafik hanya akan
        menutupi batang dan membuat tampilan ramai.
        """
        g = self._geometri
        x = (g["kiri"] + self._bulan_sorot * g["lebar_grup"]
             + g["lebar_grup"] / 2)
        p.setPen(QPen(QColor(C.BORDER_STRONG), 1))
        p.drawLine(int(x), int(g["atas"] - 2), int(x), int(g["dasar"]))

        y = posisi_y(self.data[self._bulan_sorot]["laba_sebelum_pajak"])
        p.setPen(QPen(QColor(C.SURFACE), 2))
        p.setBrush(QColor(C.POSITIF))
        p.drawEllipse(QRectF(x - 3.5, y - 3.5, 7, 7))

    def bulan_terpilih(self) -> dict | None:
        """Data bulan yang sedang ditunjuk, atau None bila tidak ada."""
        if 0 <= self._bulan_sorot < len(self.data):
            return self.data[self._bulan_sorot]
        return None

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
    def _sumbu(maks: float, laba_min: float) -> tuple[float, float, list[float]]:
        """
        Batas sumbu Y beserta nilai garis bantunya.

        Saat ada bulan merugi, garis nol tidak lagi berada di dasar grafik:
        sumbu turun sampai kerugian terdalam agar garis laba tetap terlihat.
        Kedua ujung dibulatkan ke kelipatan langkah yang sama sehingga garis
        nol selalu mendapat label dan angkanya mudah dibaca.
        """
        atas = BarChart._batas_atas(max(maks, 0.0))
        if laba_min >= 0:
            return 0.0, atas, [atas * i / 4 for i in range(5)]

        bawah_awal = -BarChart._batas_atas(-laba_min)
        langkah = BarChart._batas_atas((atas - bawah_awal) / 4)
        atas = math.ceil(atas / langkah) * langkah
        bawah = -math.ceil(-bawah_awal / langkah) * langkah
        jumlah = int(round((atas - bawah) / langkah))
        return bawah, atas, [bawah + i * langkah for i in range(jumlah + 1)]

    @staticmethod
    def _singkat(v: float) -> str:
        v = float(v)
        if v < 0:
            return "-" + BarChart._singkat(-v)
        if v >= 1_000_000_000:
            return f"{v / 1_000_000_000:.1f} M".replace(".", ",")
        if v >= 1_000_000:
            return f"{v / 1_000_000:.0f} jt"
        if v >= 1_000:
            return f"{v / 1_000:.0f} rb"
        return f"{v:.0f}"


# ==========================================================================
# DASHBOARD
# ==========================================================================
def _angka_dari(teks: str):
    """
    Ubah teks angka gaya Indonesia menjadi angka.

    Dipakai untuk data ekspor: "Rp1.074.469.000" menjadi 1074469000 dan
    "44,9%" menjadi 0.449, sehingga Excel dapat menjumlahkannya. Teks
    yang bukan angka dikembalikan apa adanya.
    """
    if not teks:
        return teks
    bersih = str(teks).strip()
    persen = bersih.endswith("%")
    bersih = (bersih.replace("Rp", "").replace("%", "")
              .replace(" ", "").replace(".", "").replace(",", "."))
    try:
        angka = float(bersih)
    except ValueError:
        return teks
    if persen:
        return angka / 100
    return int(angka) if angka == int(angka) else angka


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

        # Ekspor dan cetak memakai jalur yang sama dengan halaman lain,
        # sehingga ringkasan dashboard dapat disimpan atau dilampirkan ke
        # laporan tanpa harus difoto layar. Isi dashboard berupa kartu
        # angka, bukan tabel, jadi datanya dikumpulkan lewat fungsi.
        self._ringkasan_ekspor: list = []
        self.header.pasang_ekspor_cetak(
            self, "Dashboard", kumpulkan=lambda: self._ringkasan_ekspor)

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
        self._grid_panel = None
        self._panel_kesehatan_w = None
        self._panel_grafik_w = None
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
        # 1. PITA KINERJA — satu lembar ringkasan, bukan deretan kartu
        # ============================================================
        try:
            kpi = services.kpi_dashboard(cid, tahun)
        except Exception:
            kpi = None

        if kpi:
            self.isi_lay.addWidget(self._panel_kinerja(kpi, comp, tahun))

        # ============================================================
        # 2. PENILAIAN + GRAFIK — berdampingan pada jendela lapang
        # ============================================================
        try:
            analisis = services.analisis(cid, tahun)
        except Exception as e:
            analisis = None
            self.isi_lay.addWidget(w.InfoBanner(
                f"Analisis tidak dapat dijalankan: {e}", "danger",
                "Terjadi kesalahan"))

        # Panduan langkah awal hanya berguna saat belum ada jurnal sama
        # sekali. Jumlah jurnal ada di statistik analisis, bukan di KPI.
        if kpi and (analisis is None
                    or analisis.statistik.get("jumlah_jurnal_total", 0) == 0):
            self.isi_lay.addWidget(self._panel_mulai(comp))

        # Dua panel diletakkan berdampingan pada jendela lebar, dan bertumpuk
        # pada jendela sempit. Susunan diatur ulang setiap kali ukuran
        # jendela berubah; tanpa itu panel kiri menyempit sampai teksnya
        # hanya tersisa beberapa kata per baris.
        from PySide6.QtWidgets import QGridLayout
        baris = QWidget()
        # Latar transparan dikunci ke wadah ini saja. Tanpa kunci, aturan itu
        # menular ke kartu di dalamnya dan menghapus latar putih kartu.
        theme.latar(baris, "background: transparent;")
        grid = QGridLayout(baris)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(14)

        if analisis is not None:
            panel_kesehatan = self._panel_kesehatan(analisis, comp)
            panel_kesehatan.setMinimumWidth(0)
            grid.addWidget(panel_kesehatan, 0, 0)
            self._panel_kesehatan_w = panel_kesehatan

        try:
            panel_grafik = self._panel_grafik(cid, tahun)
            panel_grafik.setMinimumWidth(0)
            if analisis is not None:
                grid.addWidget(panel_grafik, 0, 1)
            else:
                grid.addWidget(panel_grafik, 0, 0, 1, 2)
            self._panel_grafik_w = panel_grafik
        except Exception:
            pass

        grid.setColumnStretch(0, 6)
        grid.setColumnStretch(1, 5)
        # Tanpa lebar minimum kolom: kartu menyusut mengikuti jendela dan
        # teksnya membungkus. Lebar minimum di sini dulu mendorong kolom
        # kanan keluar tepi pada jendela 1180 piksel.
        self._grid_panel = grid

        if grid.count():
            self.isi_lay.addWidget(baris)
            self._susun_panel()

        # ============================================================
        # 3. TENGGAT PAJAK & KONTRAK — satu agenda, dua kolom
        # ============================================================
        try:
            agenda = self._panel_agenda(cid)
            if agenda is not None:
                self.isi_lay.addWidget(agenda)
        except Exception:
            pass

        # ============================================================
        # 4. TEMUAN ANALISIS
        # ============================================================
        if analisis is not None and analisis.temuan:
            self.isi_lay.addWidget(self._panel_temuan(analisis))

        # ============================================================
        # 5. PROYEKSI
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

    def _susun_panel(self):
        """Tumpuk grafik di bawah kesehatan saat lebar halaman terbatas."""
        grid = getattr(self, "_grid_panel", None)
        grafik = getattr(self, "_panel_grafik_w", None)
        kesehatan = getattr(self, "_panel_kesehatan_w", None)
        if grid is None or grafik is None or kesehatan is None:
            return

        def posisi(widget):
            indeks = grid.indexOf(widget)
            return grid.getItemPosition(indeks) if indeks >= 0 else None

        pos_k = posisi(kesehatan)
        pos_g = posisi(grafik)
        # Ambang memakai lebar halaman, termasuk tepi 26 piksel di kedua
        # sisi. Di bawah 1000 piksel, dua kolom hanya menyisakan sekitar
        # 400 piksel per panel: teks penilaian menjadi terlalu sempit dan
        # grafiknya kehilangan ruang untuk dua belas bulan. Pada keadaan
        # itu grafik ditumpuk di bawah penilaian.
        sempit = self.width() < 1000
        if sempit:
            if pos_k and pos_k[3] == 2 and pos_g and pos_g[0] == 1:
                return
            if pos_g:
                grid.removeWidget(grafik)
            if pos_k:
                grid.removeWidget(kesehatan)
                grid.addWidget(kesehatan, 0, 0, 1, 2)
            grid.addWidget(grafik, 1, 0, 1, 2)
            grid.setColumnStretch(1, 0)
        else:
            if (pos_k and pos_k[3] == 1 and pos_g
                    and pos_g[0] == 0 and pos_g[1] == 1):
                return
            if pos_g:
                grid.removeWidget(grafik)
            if pos_k:
                grid.removeWidget(kesehatan)
                grid.addWidget(kesehatan, 0, 0)
            grid.addWidget(grafik, 0, 1)
            grid.setColumnStretch(1, 5)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._susun_panel()

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
        theme.latar(atas, "background: transparent;")
        al = QHBoxLayout(atas)
        al.setContentsMargins(24, 22, 26, 20)
        al.setSpacing(26)

        gauge = w.SkorGauge(ukuran=150)
        # Bila pembukuan masih kosong, skor tidak ditampilkan sebagai angka.
        belum_dinilai = analisis.grade == "N/A"
        gauge.set_skor(analisis.skor, analisis.grade_label,
                       belum_dinilai=belum_dinilai, grade=analisis.grade)
        al.addWidget(gauge, 0, Qt.AlignTop)

        kanan = QVBoxLayout()
        kanan.setSpacing(5)

        kicker = QLabel("PENILAIAN")
        kicker.setObjectName("Kicker")
        kanan.addWidget(kicker)

        j = QLabel("Kesehatan Keuangan")
        j.setObjectName("SectionTitle")
        # Judul boleh membungkus menjadi dua baris. Dengan penskalaan tampilan
        # Windows, lebar teks dapat membesar sementara ruang panel tetap, dan
        # tanpa pembungkusan tulisannya terpotong.
        j.setWordWrap(True)
        j.setMinimumWidth(0)
        kanan.addWidget(j)
        kanan.addSpacing(3)

        ringkasan = w.LabelTinggiOtomatis(w.rata_kanan_kiri(analisis.ringkasan))
        ringkasan.setTextFormat(Qt.RichText)
        ringkasan.setWordWrap(True)
        ringkasan.setStyleSheet(
            f"font-size: {theme.FS_SMALL}px; color: {C.TEXT_MUTED}; "
            "background: transparent; line-height: 168%;")
        ringkasan.setTextInteractionFlags(Qt.TextSelectableByMouse)
        kanan.addWidget(ringkasan)
        kanan.addSpacing(9)

        # Penghitung temuan ditulis sebagai satu kalimat berwarna, bukan
        # deretan keping pastel. Keping warna membuat penilaian terbaca
        # seperti lencana permainan; titik warna dan angka tebal sudah cukup
        # membedakan tingkat tanpa mengalihkan perhatian dari skor.
        bagian = []
        for jumlah, label, tingkat in (
                (analisis.jumlah_kritis, "kritis", "kritis"),
                (analisis.jumlah_peringatan, "perhatian", "peringatan"),
                (analisis.jumlah_saran, "saran", "saran"),
                (analisis.jumlah_baik, "baik", "baik")):
            if jumlah:
                warna, _bg = theme.STATUS_COLORS[tingkat]
                bagian.append(
                    f"<span style='color:{warna};'>●</span>&nbsp;"
                    f"<b>{jumlah}</b>&nbsp;{label}")
        if bagian:
            teks_hitung = "&nbsp;&nbsp;&nbsp;&nbsp;".join(bagian)
            warna_hitung = C.TEXT_MUTED
        else:
            teks_hitung = (
                f"<span style='color:{C.SUCCESS};'>●</span>&nbsp;"
                "Tidak ada temuan · semua pemeriksaan terlewati")
            warna_hitung = C.SUCCESS
        hitung = QLabel(teks_hitung)
        hitung.setTextFormat(Qt.RichText)
        hitung.setWordWrap(True)
        hitung.setStyleSheet(
            f"font-size: {theme.FS_TINY}px; color: {warna_hitung}; "
            "background: transparent;")
        kanan.addWidget(hitung)
        al.addLayout(kanan, 1)
        lay.addWidget(atas)

        # --- bagian bawah: tombol tindakan
        bawah = QWidget()
        theme.latar(bawah, f"background: {C.SURFACE_ALT}; "
                          f"border-top: 1px solid {C.BORDER}; "
                          "border-bottom-left-radius: 2px; "
                          "border-bottom-right-radius: 2px;")
        bl = QHBoxLayout(bawah)
        bl.setContentsMargins(24, 12, 26, 12)
        bl.setSpacing(12)

        pesan = QLabel(
            "Rincian lengkap: keseimbangan jurnal, likuiditas, profitabilitas, "
            "solvabilitas, dan kepatuhan pajak.")
        pesan.setStyleSheet(f"font-size: {theme.FS_TINY}px; color: {C.TEXT_FAINT}; "
                            "background: transparent;")
        pesan.setWordWrap(True)
        bl.addWidget(pesan, 1)

        btn = w.tombol("Buka Rincian", gaya="primary")
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
        theme.latar(wadah, "background: transparent;")
        lay = QVBoxLayout(wadah)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        kartu = w.Card()
        isi = kartu.body()
        isi.setSpacing(14)

        kicker = QLabel("LANGKAH AWAL")
        kicker.setObjectName("Kicker")
        isi.addWidget(kicker)

        judul = QLabel("Menyiapkan pembukuan pertama")
        judul.setObjectName("SectionTitle")
        judul.setWordWrap(True)
        isi.addWidget(judul)

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
            b.setSpacing(13)

            lencana = QLabel(nomor)
            lencana.setFixedWidth(26)
            lencana.setAlignment(Qt.AlignLeft | Qt.AlignTop)
            # Nomor ditulis sebagai angka serif tembaga, bukan keping
            # lingkaran. Bentuk ini menyatu dengan tipografi laporan dan
            # tidak menambah bentuk dekoratif baru pada halaman.
            lencana.setStyleSheet(
                f"font-family: '{theme.FONT_SERIF}', Georgia, serif; "
                f"font-size: 17px; font-weight: 600; color: {C.ACCENT_DARK}; "
                "background: transparent; padding-top: 1px;")

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

        for i, (teks_tombol, kode_halaman, keterangan_tombol, gaya) in enumerate((
            ("Catat Penjualan", "penjualan",
             "Buka halaman penjualan untuk mencatat transaksi pertama",
             "primary"),
            ("Lihat Bagan Akun", "coa",
             "Periksa akun yang sudah disiapkan otomatis", "ghost"),
        )):
            t = w.tombol(teks_tombol, gaya=gaya,
                         ikon="tambah" if i == 0 else "")
            t.setToolTip(keterangan_tombol)
            t.clicked.connect(
                lambda _=False, k=kode_halaman: self.pindah_halaman.emit(k))
            tombol_baris.addWidget(t)

        tombol_baris.addStretch()
        isi.addLayout(tombol_baris)

        lay.addWidget(kartu)
        return wadah

    # ==================================================================
    # PANEL: PITA KINERJA
    # ==================================================================
    def _panel_kinerja(self, kpi, comp, tahun) -> QWidget:
        """
        Satu lembar ringkasan kinerja: omzet sebagai angka pokok, laba dan
        kas sebagai angka pendamping, lalu kewajiban pokok pada kaki pita.

        Seluruh angka berada dalam satu bidang putih dengan garis rambut
        pemisah, bukan enam kartu sejajar. Bidang tunggal membuat mata
        membaca urutan yang sama seperti laporan keuangan: pendapatan lebih
        dulu, laba dan kas berikutnya, lalu posisi neraca.
        """
        wadah = QWidget()
        theme.latar(wadah, "background: transparent;")
        luar = QVBoxLayout(wadah)
        luar.setContentsMargins(0, 0, 0, 0)
        luar.setSpacing(12)

        kartu = w.Card()
        lay = kartu.ganti_isi(QVBoxLayout())
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        omzet = kpi["omzet"]
        pct_pkp = (omzet / config.THRESHOLD_PKP * 100
                   if config.THRESHOLD_PKP else 0.0)
        if pct_pkp >= 100:
            warna_omzet = C.DANGER
            ket_omzet = (
                f"Telah melewati batas wajib PKP Rp4,8 M. Pengusaha wajib "
                "dikukuhkan sebagai PKP dan memungut PPN.")
        elif pct_pkp >= 80:
            warna_omzet = C.WARNING
            ket_omzet = (
                f"{theme.persen(pct_pkp / 100, 1)} dari batas wajib PKP "
                "Rp4,8 M. Mendekati batas; siapkan administrasi PKP.")
        else:
            warna_omzet = C.TEXT
            ket_omzet = (
                f"{theme.persen(pct_pkp / 100, 1)} dari batas wajib PKP "
                "Rp4,8 M")

        # ------------------------------------------------------ angka utama
        atas = QWidget()
        theme.latar(atas, "background: transparent;")
        al = QHBoxLayout(atas)
        al.setContentsMargins(24, 22, 24, 20)
        al.setSpacing(26)

        kiri = QVBoxLayout()
        kiri.setSpacing(8)
        kiri.addWidget(w.AngkaBuku(
            "Omzet / Peredaran Bruto", theme.money(omzet),
            ukuran=38, warna=warna_omzet))

        meter = w.MeterBatas()
        meter.set_nilai(min(pct_pkp, 100.0),
                        warna_omzet if pct_pkp >= 80 else C.ACCENT)
        kiri.addWidget(meter)

        ket = QLabel(ket_omzet)
        ket.setWordWrap(True)
        ket.setStyleSheet(
            f"font-size: {theme.FS_TINY}px; color: {warna_omzet}; "
            "background: transparent;")
        kiri.addWidget(ket)

        status_pkp = kpi.get("status_pkp") or {}
        if status_pkp.get("status"):
            warna_status = {"danger": C.DANGER,
                            "warning": C.WARNING}.get(status_pkp.get("level"),
                                                      C.TEXT_FAINT)
            lbl_status = QLabel(f"Status PKP · {status_pkp['status']}")
            lbl_status.setStyleSheet(
                f"font-size: {theme.FS_TINY}px; color: {warna_status}; "
                "background: transparent;")
            kiri.addWidget(lbl_status)
        kiri.addStretch()
        al.addLayout(kiri, 7)

        garis_tegak = QFrame()
        garis_tegak.setFixedWidth(1)
        garis_tegak.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        theme.latar(garis_tegak, f"background: {C.BORDER}; border: none;")
        al.addWidget(garis_tegak)

        kanan = QVBoxLayout()
        kanan.setSpacing(9)
        kanan.addWidget(w.AngkaBuku(
            "Laba Bersih", theme.money(kpi["laba_bersih"]),
            f"Margin {theme.persen(kpi['margin_bersih'])}",
            warna=C.POSITIF if kpi["laba_bersih"] >= 0 else C.NEGATIF,
            ukuran=25))

        garis_mendatar = QFrame()
        garis_mendatar.setFixedHeight(1)
        theme.latar(garis_mendatar, f"background: {C.BORDER}; border: none;")
        kanan.addWidget(garis_mendatar)

        kanan.addWidget(w.AngkaBuku(
            "Kas & Bank", theme.money(kpi["kas"]),
            "Saldo defisit · periksa arus kas"
            if kpi["kas"] < 0 else "Saldo likuid saat ini",
            warna=C.NEGATIF if kpi["kas"] < 0 else C.TEXT,
            ukuran=25))
        kanan.addStretch()
        al.addLayout(kanan, 4)
        lay.addWidget(atas)

        # ------------------------------------------------------ kaki pita
        kaki = QWidget()
        theme.latar(kaki, f"background: {C.SURFACE_ALT}; "
                         f"border-top: 1px solid {C.BORDER}; "
                         "border-bottom-left-radius: 2px; "
                         "border-bottom-right-radius: 2px;")
        kl = QHBoxLayout(kaki)
        kl.setContentsMargins(24, 15, 24, 16)
        kl.setSpacing(20)

        posisi = [
            ("Total Aset", theme.money(kpi["total_aset"]), "", C.TEXT),
            ("Total Liabilitas", theme.money(kpi["total_liabilitas"]), "", C.TEXT),
            ("Total Ekuitas", theme.money(kpi["total_ekuitas"]), "", C.TEXT),
            ("PPh Terutang (estimasi)", theme.money(kpi["pph_terutang"]),
             kpi["pph_skema"].split(" - ")[0], C.TEXT),
        ]
        for i, (label, nilai, hint, warna) in enumerate(posisi):
            if i:
                pemisah = QFrame()
                pemisah.setFixedWidth(1)
                theme.latar(pemisah, f"background: {C.BORDER}; border: none;")
                kl.addWidget(pemisah)
            kl.addWidget(w.AngkaBuku(label, nilai, hint, warna, ukuran=20), 1)
        lay.addWidget(kaki)
        luar.addWidget(kartu)

        # ------------------------------------------------------ integritas
        if abs(kpi["selisih_jurnal"]) > 0.5 or abs(kpi["selisih_neraca"]) >= 1:
            pesan = []
            if abs(kpi["selisih_jurnal"]) > 0.5:
                pesan.append(
                    f"jurnal tidak seimbang {theme.money(kpi['selisih_jurnal'])}")
            if abs(kpi["selisih_neraca"]) >= 1:
                pesan.append(
                    f"neraca berselisih {theme.money(kpi['selisih_neraca'])}")
            luar.addWidget(w.InfoBanner(
                "Terdapat ketidakseimbangan: " + " dan ".join(pesan) +
                ". Perbaiki sebelum mempercayai angka di atas.",
                "danger", "Integritas data bermasalah"))

        # Data untuk tombol Ekspor dan Cetak.
        baris_ekspor = [
            ["Ringkasan", "Nilai", "Keterangan"],
            ["Perusahaan", comp["nama"], f"Tahun pajak {tahun}"],
            ["Omzet / Peredaran Bruto", _angka_dari(theme.money(omzet)),
             ket_omzet],
            ["Laba Bersih", _angka_dari(theme.money(kpi["laba_bersih"])),
             f"Margin {theme.persen(kpi['margin_bersih'])}"],
            ["Kas & Bank", _angka_dari(theme.money(kpi["kas"])),
             "Saldo defisit" if kpi["kas"] < 0 else "Saldo likuid"],
            ["Total Aset", _angka_dari(theme.money(kpi["total_aset"])), ""],
            ["Total Liabilitas",
             _angka_dari(theme.money(kpi["total_liabilitas"])), ""],
            ["Total Ekuitas",
             _angka_dari(theme.money(kpi["total_ekuitas"])), ""],
            ["PPh Terutang (estimasi)",
             _angka_dari(theme.money(kpi["pph_terutang"])), kpi["pph_skema"]],
        ]
        self._ringkasan_ekspor = [("Dashboard", baris_ekspor)]
        return wadah

    # ==================================================================
    # PANEL: AGENDA (TENGGAT PAJAK & KONTRAK)
    # ==================================================================
    def _panel_agenda(self, cid: int) -> QWidget:
        """
        Tenggat pajak dan kontrak yang perlu perhatian dalam satu agenda.

        Keduanya dulu berupa dua kartu terpisah dengan keping warna yang
        sama, sehingga tampak seperti dua daftar yang saling bersaing.
        Digabung, keduanya menjadi satu daftar tindakan yang dibaca dari
        atas ke bawah: apa yang harus dikerjakan, kapan, dan seberapa dekat.
        """
        try:
            daftar_pajak = services.deadline_pajak(cid) or []
        except Exception:
            daftar_pajak = []
        try:
            from ... import kontrak as kt
            daftar_kontrak = kt.yang_perlu_perhatian(cid) or []
        except Exception:
            daftar_kontrak = []

        if not daftar_pajak and not daftar_kontrak:
            return None

        kartu = w.Card()
        lay = kartu.body()
        lay.setSpacing(14)

        kepala = QHBoxLayout()
        kepala.setSpacing(12)
        kolom_judul = QVBoxLayout()
        kolom_judul.setSpacing(3)
        j = QLabel("Agenda Terdekat")
        j.setObjectName("SectionTitle")
        kolom_judul.addWidget(j)
        sub = QLabel("Tenggat pajak dan kontrak yang perlu ditindaklanjuti.")
        sub.setStyleSheet(
            f"font-size: {theme.FS_SMALL}px; color: {C.TEXT_MUTED}; "
            "background: transparent;")
        sub.setWordWrap(True)
        kolom_judul.addWidget(sub)
        kepala.addLayout(kolom_judul, 1)
        lay.addLayout(kepala)

        kolom = QHBoxLayout()
        kolom.setSpacing(26)

        def buat_kolom(judul, baris_list, kode_halaman, teks_tombol):
            wadah_kolom = QWidget()
            theme.latar(wadah_kolom, "background: transparent;")
            kl = QVBoxLayout(wadah_kolom)
            kl.setContentsMargins(0, 0, 0, 0)
            kl.setSpacing(0)

            judul_kolom = QLabel(judul.upper())
            judul_kolom.setStyleSheet(
                f"font-size: 10px; font-weight: 700; color: {C.TEXT_FAINT}; "
                "letter-spacing: 1.1px; background: transparent;")
            kl.addWidget(judul_kolom)
            kl.addSpacing(4)

            for baris in baris_list:
                nama, rincian, hitung, warna = baris
                blok = QWidget()
                theme.latar(blok, "background: transparent;")
                bl = QVBoxLayout(blok)
                bl.setContentsMargins(0, 8, 0, 8)
                bl.setSpacing(2)

                atas = QHBoxLayout()
                atas.setSpacing(10)
                n = QLabel(nama)
                n.setStyleSheet(
                    f"font-size: {theme.FS_BODY}px; font-weight: 600; "
                    f"color: {C.TEXT}; background: transparent;")
                n.setWordWrap(True)
                n.setMinimumWidth(0)
                atas.addWidget(n, 1)
                h = QLabel(hitung)
                h.setStyleSheet(
                    f"font-size: {theme.FS_TINY}px; font-weight: 700; "
                    f"color: {warna}; background: transparent;")
                h.setAlignment(Qt.AlignRight | Qt.AlignTop)
                atas.addWidget(h, 0)
                bl.addLayout(atas)

                r = QLabel(rincian)
                r.setStyleSheet(
                    f"font-size: {theme.FS_TINY}px; color: {C.TEXT_MUTED}; "
                    "background: transparent;")
                r.setWordWrap(True)
                bl.addWidget(r)

                garis = QFrame()
                garis.setFixedHeight(1)
                theme.latar(garis, f"background: {C.BORDER}; border: none;")
                bl.addSpacing(3)
                bl.addWidget(garis)
                kl.addWidget(blok)

            kl.addSpacing(9)
            b = w.tombol(teks_tombol, gaya="ghost")
            b.clicked.connect(
                lambda _=False, k=kode_halaman: self.pindah_halaman.emit(k))
            kl.addWidget(b, 0, Qt.AlignLeft)
            kl.addStretch()
            return wadah_kolom

        if daftar_pajak:
            baris_pajak = []
            for d in daftar_pajak[:3]:
                hari = d["hari_tersisa"]
                if hari < 0:
                    warna, hitung = C.DANGER, f"Lewat {abs(hari)} hari"
                elif hari <= 7:
                    warna, hitung = C.WARNING, f"{hari} hari lagi"
                else:
                    warna, hitung = C.SUCCESS, f"{hari} hari lagi"
                rincian = (f"Masa {d['masa']} · jatuh tempo "
                           f"{theme.tanggal_id(d['tenggat'])}")
                baris_pajak.append((d["nama"], rincian, hitung, warna))
            kolom.addWidget(buat_kolom(
                "Tenggat pajak", baris_pajak, "checklist",
                "Checklist Kepatuhan"), 1)

        if daftar_pajak and daftar_kontrak:
            pemisah = QFrame()
            pemisah.setFixedWidth(1)
            theme.latar(pemisah, f"background: {C.BORDER}; border: none;")
            kolom.addWidget(pemisah)

        if daftar_kontrak:
            baris_kontrak = []
            for k in daftar_kontrak[:3]:
                sisa = k.get("sisa_hari")
                if sisa is None:
                    warna, hitung = C.TEXT_MUTED, "Tanpa batas"
                elif sisa < 0:
                    warna, hitung = C.DANGER, f"Lewat {abs(sisa)} hari"
                elif sisa <= 30:
                    warna, hitung = C.WARNING, f"{sisa} hari lagi"
                else:
                    warna, hitung = C.SUCCESS, f"{sisa} hari lagi"
                rincian = (
                    f"{k['mitra'] or 'Tanpa mitra'} · berakhir "
                    f"{theme.tanggal_id(k['tanggal_akhir']) if k['tanggal_akhir'] else '-'}")
                baris_kontrak.append((k["judul"], rincian, hitung, warna))
            kolom.addWidget(buat_kolom(
                "Kontrak", baris_kontrak, "kontrak", "Daftar Kontrak"), 1)

        lay.addLayout(kolom)

        sisa_pajak = len(daftar_pajak) - 3
        sisa_kontrak = len(daftar_kontrak) - 3
        catatan = []
        if sisa_pajak > 0:
            catatan.append(f"{sisa_pajak} tenggat pajak lain")
        if sisa_kontrak > 0:
            catatan.append(f"{sisa_kontrak} kontrak lain")
        if catatan:
            lay.addWidget(w.label("Belum ditampilkan: " + " dan ".join(catatan) +
                                  ".", objek="Faint"))
        return kartu

    # ==================================================================
    # PANEL: GRAFIK
    # ==================================================================
    def _panel_grafik(self, cid: int, tahun: int) -> QWidget:
        kartu = w.Card()
        lay = kartu.ganti_isi(QVBoxLayout())
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        kepala = QWidget()
        theme.latar(kepala, "background: transparent;")
        kl = QVBoxLayout(kepala)
        kl.setContentsMargins(22, 18, 22, 8)
        kl.setSpacing(4)

        kicker = QLabel("PENDAPATAN · BEBAN · LABA")
        kicker.setObjectName("Kicker")
        kl.addWidget(kicker)

        j = QLabel(f"Kinerja Bulanan {tahun}")
        j.setObjectName("SectionTitle")
        j.setWordWrap(True)
        j.setMinimumWidth(0)
        kl.addWidget(j)

        # Legenda diletakkan pada barisnya sendiri di bawah judul. Bila
        # ditempatkan sebaris dengan judul, ruang yang tersisa tidak cukup
        # pada layar 1366 piksel dan label terakhir terpotong.
        legenda = QHBoxLayout()
        legenda.setSpacing(14)
        for bentuk, warna, teks in [
                ("kotak", C.PRIMARY, "Pendapatan"),
                ("kotak", C.ACCENT, "HPP + Beban"),
                ("garis", C.POSITIF, "Laba sebelum pajak")]:
            item = QHBoxLayout()
            item.setSpacing(6)
            titik = QLabel()
            if bentuk == "kotak":
                titik.setFixedSize(11, 11)
                theme.latar(titik, f"background: {warna}; border-radius: 2px;")
            else:
                # penanda garis tren: batang tipis di tengah label
                titik.setFixedSize(15, 11)
                theme.latar(titik, f"background: {warna}; border-radius: 1px;")
                titik.setFixedHeight(3)
            item.addWidget(titik, 0, Qt.AlignVCenter)
            t = QLabel(teks)
            t.setStyleSheet(f"font-size: {theme.FS_TINY}px; color: {C.TEXT_MUTED}; "
                            "background: transparent;")
            t.setMinimumWidth(t.fontMetrics().horizontalAdvance(teks) + 2)
            item.addWidget(t)
            legenda.addLayout(item)
        legenda.addStretch()
        kl.addSpacing(5)
        kl.addLayout(legenda)
        lay.addWidget(kepala)

        data = acc.ringkasan_bulanan(cid, tahun)
        chart = BarChart()
        chart.set_data(data)
        bungkus_grafik = QWidget()
        theme.latar(bungkus_grafik, "background: transparent;")
        bl = QVBoxLayout(bungkus_grafik)
        bl.setContentsMargins(12, 2, 12, 4)
        bl.addWidget(chart)
        lay.addWidget(bungkus_grafik)

        # Baris keterangan: menampilkan angka bulan yang sedang ditunjuk,
        # dan kembali ke total setahun saat kursor keluar dari grafik.
        kaki = QWidget()
        theme.latar(kaki, f"background: {C.SURFACE_ALT}; "
                         f"border-top: 1px solid {C.BORDER}; "
                         "border-bottom-left-radius: 2px; "
                         "border-bottom-right-radius: 2px;")
        fl = QHBoxLayout(kaki)
        fl.setContentsMargins(22, 12, 22, 13)
        fl.setSpacing(26)

        stat_pendapatan = w.MiniStat("Total Pendapatan", theme.money(0))
        stat_beban = w.MiniStat("Total Beban", theme.money(0))
        stat_laba = w.MiniStat("Laba Sebelum Pajak", theme.money(0))
        for s in (stat_pendapatan, stat_beban, stat_laba):
            fl.addWidget(s, 1)
        lay.addWidget(kaki)

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
        lay.setSpacing(10)

        kicker = QLabel("TEMUAN")
        kicker.setObjectName("Kicker")
        lay.addWidget(kicker)

        kepala = QHBoxLayout()
        kepala.setSpacing(12)
        j = QLabel("Yang Perlu Ditindaklanjuti")
        j.setObjectName("SectionTitle")
        j.setWordWrap(True)
        j.setMinimumWidth(0)
        kepala.addWidget(j, 1)
        b = w.tombol("Semua Temuan", gaya="ghost")
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
            # Tanpa kotak dan bayangan: kartu temuan dibaca sebagai bagian
            # dari satu daftar, bukan dua kotak terpisah di dalam kotak.
            lay.addWidget(w.TemuanCard(t, ringkas=True, datar=True))

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

        kicker = QLabel("PROYEKSI")
        kicker.setObjectName("Kicker")
        lay.addWidget(kicker)

        j = QLabel("Perkiraan Berdasarkan Kinerja Saat Ini")
        j.setObjectName("SectionTitle")
        j.setWordWrap(True)
        lay.addWidget(j)

        if p["bulan_data"] == 0 or p["rata_pendapatan_bulanan"] == 0:
            lay.addWidget(w.label(
                "Belum cukup data untuk membuat proyeksi. Catat transaksi beberapa "
                "bulan agar proyeksi bermakna.", objek="Muted", wrap=True))
            return kartu

        grid = QGridLayout()
        grid.setHorizontalSpacing(26)
        grid.setVerticalSpacing(16)
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
            grid.addWidget(w.AngkaBuku(label, nilai, warna=warna, ukuran=22),
                           i // 2, i % 2)
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
        wadah = QWidget()
        theme.latar(wadah, "background: transparent;")
        luar = QHBoxLayout(wadah)
        luar.setContentsMargins(0, 10, 0, 10)
        luar.addStretch(1)

        kartu = w.Card(padding=38)
        kartu.setMaximumWidth(620)
        lay = kartu.body()
        lay.setSpacing(10)
        lay.setAlignment(Qt.AlignCenter)

        ikon = QLabel()
        ikon.setPixmap(icons.pixmap("perusahaan", C.ACCENT, 26))
        ikon.setAlignment(Qt.AlignCenter)
        ikon.setStyleSheet("background: transparent;")
        lay.addWidget(ikon)
        lay.addSpacing(4)

        kicker = QLabel("MULAI DARI SINI")
        kicker.setObjectName("Kicker")
        kicker.setAlignment(Qt.AlignCenter)
        lay.addWidget(kicker)

        j = QLabel("Belum ada perusahaan")
        j.setAlignment(Qt.AlignCenter)
        j.setStyleSheet(
            f"font-family: '{theme.FONT_SERIF}', Georgia, serif; "
            "font-size: 28px; font-weight: 600; background: transparent;")
        lay.addWidget(j)

        ket = QLabel(
            "Langkah pertama adalah membuat profil perusahaan. Setelah itu "
            "aplikasi menyiapkan bagan akun (chart of accounts) sesuai bentuk "
            "badan usaha yang Anda pilih, lalu Anda dapat langsung mencatat "
            "transaksi pertama."
        )
        ket.setAlignment(Qt.AlignCenter)
        ket.setWordWrap(True)
        ket.setStyleSheet(f"font-size: {theme.FS_SMALL}px; color: {C.TEXT_MUTED}; "
                          "background: transparent; line-height: 160%;")
        lay.addWidget(ket)
        lay.addSpacing(8)

        b = w.tombol("Buat Profil Perusahaan", gaya="primary", ikon="tambah")
        b.setMinimumHeight(38)
        b.clicked.connect(lambda: self.pindah_halaman.emit("perusahaan"))
        lay.addWidget(b, 0, Qt.AlignCenter)

        luar.addWidget(kartu)
        luar.addStretch(1)
        self.isi_lay.addWidget(wadah)
