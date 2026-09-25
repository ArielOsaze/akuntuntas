"""
Ikon garis AkunTuntas
======================
Seluruh ikon digambar langsung dengan QPainter pada grid acuan 24x24,
sehingga tampil tajam di semua skala layar tanpa bergantung pada berkas
gambar atau font ikon dari luar.

Pemakaian:
    from . import icons
    tombol.setIcon(icons.ikon("tambah", icons.WARNA_GELAP, 18))
"""
from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QColor, QIcon, QPainter, QPainterPath, QPen,
                           QPixmap, QPolygonF)

# Warna baku ikon; sesuaikan agar menyatu dengan tema.
WARNA_GELAP = "#3E4C59"
WARNA_TERANG = "#FFFFFF"
WARNA_MUTED = "#7B8794"
WARNA_PRIMER = "#1B4F8A"
WARNA_SUKSES = "#0F7B54"
WARNA_BAHAYA = "#B91C1C"

_UKURAN_BAKU = (14, 16, 18, 20, 22, 24, 28, 32)
_CACHE: dict = {}


def tersedia(nama: str) -> bool:
    return nama in _NAMA


def _p(x: float, y: float, u: float) -> QPointF:
    return QPointF(x * u, y * u)


def _r(x: float, y: float, w: float, h: float, u: float) -> QRectF:
    return QRectF(x * u, y * u, w * u, h * u)


def _poli(titik: list, u: float) -> QPolygonF:
    return QPolygonF([_p(x, y, u) for x, y in titik])


def _gambar(nama: str, p: QPainter, u: float) -> None:
    """Gambar satu ikon pada kanvas. u = ukuran satu satuan grid."""
    if nama == "dashboard":
        for x, y in ((3, 3), (13.5, 3), (3, 13.5), (13.5, 13.5)):
            p.drawRoundedRect(_r(x, y, 7.5, 7.5, u), 1.6 * u, 1.6 * u)

    elif nama == "analisis":
        p.drawEllipse(_r(3, 3, 13, 13, u))
        p.drawLine(_p(15.6, 15.6, u), _p(20.8, 20.8, u))
        p.drawPolyline(_poli([(6.6, 11.6), (9.2, 8.6), (11.4, 11.2), (13.4, 7.4)], u))

    elif nama == "pencarian":
        p.drawEllipse(_r(3.5, 3.5, 12, 12, u))
        p.drawLine(_p(15.4, 15.4, u), _p(20.5, 20.5, u))

    elif nama == "jurnal":
        p.drawPolyline(_poli([(6, 3.5), (15, 3.5), (19, 7.5), (19, 20.5),
                              (6, 20.5), (6, 3.5)], u))
        p.drawPolyline(_poli([(15, 3.5), (15, 7.5), (19, 7.5)], u))
        for y in (11.5, 15):
            p.drawLine(_p(9, y, u), _p(16, y, u))

    elif nama == "penjualan":
        p.drawPolyline(_poli([(3.5, 19.5), (20.5, 19.5)], u))
        p.drawPolyline(_poli([(5, 15.5), (10, 10), (13.5, 13.5), (19, 6)], u))
        p.drawPolyline(_poli([(14.5, 6), (19, 6), (19, 10.5)], u))

    elif nama == "pembelian":
        # keranjang belanja dengan panah masuk
        p.drawPolyline(_poli([(3, 4.5), (6, 4.5), (8.6, 14.5), (18.4, 14.5)], u))
        p.drawPolyline(_poli([(6.6, 7.5), (20, 7.5), (18.4, 14.5)], u))
        p.drawEllipse(_r(9.4, 17.4, 2.6, 2.6, u))
        p.drawEllipse(_r(16, 17.4, 2.6, 2.6, u))

    elif nama == "biaya":
        # koin dengan tanda minus (pengeluaran)
        p.drawEllipse(_r(3.5, 3.5, 17, 17, u))
        p.drawLine(_p(8, 12, u), _p(16, 12, u))

    elif nama == "kontrak":
        # dokumen dengan pita segel di sisi kanan
        p.drawRoundedRect(_r(3.5, 2, 13, 16, u), 1.6, 1.6)
        p.drawLine(_p(6.5, 6.2, u), _p(13.5, 6.2, u))
        p.drawLine(_p(6.5, 9, u), _p(13.5, 9, u))
        p.drawLine(_p(6.5, 11.8, u), _p(10.5, 11.8, u))
        p.drawEllipse(_r(12.2, 12.4, 4.2, 4.2, u))
        p.drawLine(_p(12.9, 16.2, u), _p(12.9, 19.2, u))
        p.drawLine(_p(15.7, 16.2, u), _p(15.7, 19.2, u))
        p.drawLine(_p(12.9, 19.2, u), _p(14.3, 18.2, u))
        p.drawLine(_p(15.7, 19.2, u), _p(14.3, 18.2, u))

    elif nama == "mitra":
        # dua orang berdampingan (pelanggan & pemasok)
        p.drawEllipse(_r(2.6, 5.6, 5.6, 5.6, u))
        p.drawArc(_r(0.9, 12.4, 9, 8.6, u), 0, 180 * 16)
        p.drawEllipse(_r(13.4, 5.6, 5.6, 5.6, u))
        p.drawArc(_r(11.7, 12.4, 9, 8.6, u), 0, 180 * 16)
        p.drawLine(_p(10.6, 8.6, u), _p(11.2, 8.6, u))
        p.drawLine(_p(10.6, 12, u), _p(11.2, 12, u))

    elif nama == "bank":
        p.drawPolyline(_poli([(3, 9.5), (12, 4), (21, 9.5)], u))
        p.drawLine(_p(4.5, 9.5, u), _p(19.5, 9.5, u))
        for x in (6.8, 12, 17.2):
            p.drawLine(_p(x, 11, u), _p(x, 17, u))
        p.drawLine(_p(3.5, 18.5, u), _p(20.5, 18.5, u))

    elif nama == "produk":
        p.drawPolyline(_poli([(3.5, 8), (12, 3.5), (20.5, 8), (20.5, 16.5),
                              (12, 21), (3.5, 16.5), (3.5, 8)], u))
        p.drawLine(_p(12, 12.5, u), _p(12, 21, u))
        p.drawLine(_p(3.5, 8, u), _p(12, 12.5, u))
        p.drawLine(_p(20.5, 8, u), _p(12, 12.5, u))

    elif nama == "aset":
        # gedung pabrik dengan cerobong
        p.drawPolyline(_poli([(3, 20.5), (3, 11.5), (8.6, 11.5), (8.6, 7.6),
                              (12.6, 10), (12.6, 7.6), (16.6, 10),
                              (16.6, 20.5), (3, 20.5)], u))
        p.drawLine(_p(2, 20.5, u), _p(21.4, 20.5, u))
        p.drawLine(_p(18.6, 20.5, u), _p(18.6, 5.2, u))
        p.drawLine(_p(17.2, 5.2, u), _p(20, 5.2, u))
        for x in (5.6, 9.6):
            p.drawPoint(_p(x, 15, u))
        p.drawRect(_r(13.4, 15.4, 2.4, 5.1, u))

    elif nama == "uang":
        # uang kertas dengan simbol Rp
        p.drawRoundedRect(_r(2.6, 6.4, 18.8, 11.2, u), 1.8 * u, 1.8 * u)
        p.drawEllipse(_r(8.6, 9.4, 6.8, 5.2, u))
        p.drawLine(_p(12, 9.4, u), _p(12, 14.6, u))
        p.drawLine(_p(10.6, 11, u), _p(13.4, 11, u))
        p.drawLine(_p(10.6, 12.9, u), _p(13.4, 12.9, u))
        p.drawLine(_p(10.6, 11, u), _p(10.6, 14.6, u))
        p.drawPoint(_p(5.6, 12, u))
        p.drawPoint(_p(18.4, 12, u))

    elif nama == "payroll":
        # kartu identitas pegawai
        p.drawEllipse(_r(3.8, 6.2, 6.2, 6.2, u))
        p.drawArc(_r(1.8, 13.4, 10.2, 8.4, u), 0, 180 * 16)
        p.drawRoundedRect(_r(13, 6.2, 7.6, 12.4, u), 1.4 * u, 1.4 * u)
        p.drawLine(_p(15, 10, u), _p(18.6, 10, u))
        p.drawLine(_p(15, 13, u), _p(18.6, 13, u))
        p.drawLine(_p(15, 16, u), _p(18.6, 16, u))

    elif nama == "dimensi":
        p.drawEllipse(_r(3.5, 3.5, 17, 17, u))
        p.drawEllipse(_r(8.2, 8.2, 7.6, 7.6, u))
        p.drawEllipse(_r(11.2, 11.2, 1.6, 1.6, u))

    elif nama == "periode":
        # kalender dengan centang = periode yang sudah ditutup
        p.drawRoundedRect(_r(4, 5.5, 16, 15, u), 2 * u, 2 * u)
        p.drawLine(_p(4, 10.5, u), _p(20, 10.5, u))
        p.drawLine(_p(8.5, 3, u), _p(8.5, 6.8, u))
        p.drawLine(_p(15.5, 3, u), _p(15.5, 6.8, u))
        p.drawPolyline(_poli([(8.6, 15.2), (11.2, 17.8), (16, 13)], u))

    elif nama == "konsolidasi":
        p.drawPolyline(_poli([(12, 3), (21, 8), (12, 13), (3, 8), (12, 3)], u))
        p.drawPolyline(_poli([(3, 12.5), (12, 17.5), (21, 12.5)], u))
        p.drawPolyline(_poli([(3, 16.8), (12, 21.8), (21, 16.8)], u))

    elif nama == "laporan":
        p.drawPolyline(_poli([(4.5, 4), (4.5, 20), (20.5, 20)], u))
        p.drawRect(_r(7.5, 12.5, 3.2, 7.5, u))
        p.drawRect(_r(12.6, 8.5, 3.2, 11.5, u))
        p.drawRect(_r(17.7, 14.5, 3.2, 5.5, u))

    elif nama == "pajak":
        # dokumen dengan simbol persen yang lebih terbaca
        p.drawPolyline(_poli([(6, 3.5), (15, 3.5), (19, 7.5), (19, 20.5),
                              (6, 20.5), (6, 3.5)], u))
        p.drawPolyline(_poli([(15, 3.5), (15, 7.5), (19, 7.5)], u))
        p.drawEllipse(_r(8.6, 10.4, 3.4, 3.4, u))
        p.drawEllipse(_r(13.2, 15.2, 3.4, 3.4, u))
        p.drawLine(_p(15.6, 10.6, u), _p(9.4, 18.4, u))

    elif nama == "checklist":
        p.drawRoundedRect(_r(4, 4, 16, 16, u), 2.6 * u, 2.6 * u)
        p.drawPolyline(_poli([(8.2, 12.4), (11, 15.2), (16.2, 9)], u))

    elif nama == "pengguna":
        # orang dengan tanda centang akses di sampingnya
        p.drawEllipse(_r(4.2, 4.2, 7.4, 7.4, u))
        p.drawArc(_r(2, 13, 11.8, 10.5, u), 0, 180 * 16)
        p.drawEllipse(_r(14.6, 12.6, 6.6, 6.6, u))
        p.drawPolyline(_poli([(16.6, 15.9), (17.9, 17.3), (19.6, 14.6)], u))

    elif nama == "audit":
        p.drawRoundedRect(_r(5, 3.5, 14, 17, u), 2 * u, 2 * u)
        for y in (8.5, 12, 15.5):
            p.drawPoint(_p(8.6, y, u))
            p.drawLine(_p(11.2, y, u), _p(16, y, u))

    elif nama == "recycle":
        # tiga panah daur ulang
        p.drawArc(_r(3.5, 3.5, 17, 17, u), 40 * 16, 100 * 16)
        p.drawArc(_r(3.5, 3.5, 17, 17, u), 160 * 16, 100 * 16)
        p.drawArc(_r(3.5, 3.5, 17, 17, u), 280 * 16, 100 * 16)
        p.drawPolyline(_poli([(14.6, 3.2), (18.4, 5.6), (16.2, 9.6)], u))
        p.drawPolyline(_poli([(3.4, 13.2), (3.9, 17.6), (8.3, 17.1)], u))
        p.drawPolyline(_poli([(19.6, 13.4), (19.2, 17.8), (14.8, 17.3)], u))

    elif nama == "impor":
        p.drawLine(_p(12, 3.5, u), _p(12, 14.5, u))
        p.drawPolyline(_poli([(7.5, 10), (12, 14.5), (16.5, 10)], u))
        p.drawPolyline(_poli([(4, 15), (4, 20.5), (20, 20.5), (20, 15)], u))

    elif nama == "ekspor":
        p.drawLine(_p(12, 14.5, u), _p(12, 3.5, u))
        p.drawPolyline(_poli([(7.5, 8), (12, 3.5), (16.5, 8)], u))
        p.drawPolyline(_poli([(4, 15), (4, 20.5), (20, 20.5), (20, 15)], u))

    elif nama == "coa":
        p.drawPolyline(_poli([(4.5, 5), (4.5, 19.5), (12, 19.5)], u))
        p.drawPolyline(_poli([(4.5, 5), (12, 5), (12, 19.5)], u))
        p.drawPolyline(_poli([(12, 5), (19.5, 5), (19.5, 19.5), (12, 19.5)], u))
        p.drawLine(_p(7.5, 9.5, u), _p(9.5, 9.5, u))
        p.drawLine(_p(7.5, 13, u), _p(9.5, 13, u))
        p.drawLine(_p(15, 9.5, u), _p(17, 9.5, u))
        p.drawLine(_p(15, 13, u), _p(17, 13, u))

    elif nama == "perusahaan":
        # gedung kantor bertingkat
        p.drawPolyline(_poli([(3.5, 20.5), (3.5, 6.5), (13, 6.5), (13, 20.5)], u))
        p.drawPolyline(_poli([(13, 11), (20.5, 11), (20.5, 20.5)], u))
        p.drawLine(_p(2.2, 20.5, u), _p(21.8, 20.5, u))
        for x in (6.2, 10.2):
            for y in (9.2, 12.6, 16):
                p.drawPoint(_p(x, y, u))
        for y in (13.6, 17):
            p.drawPoint(_p(16.8, y, u))
        p.drawLine(_p(7.2, 6.5, u), _p(7.2, 3.8, u))
        p.drawLine(_p(7.2, 3.8, u), _p(11.4, 3.8, u))

    elif nama == "lan":
        p.drawEllipse(_r(9, 2.5, 6, 6, u))
        p.drawEllipse(_r(2.5, 15, 6, 6, u))
        p.drawEllipse(_r(15.5, 15, 6, 6, u))
        p.drawLine(_p(12, 8.5, u), _p(12, 12, u))
        p.drawLine(_p(5.5, 15, u), _p(12, 12, u))
        p.drawLine(_p(18.5, 15, u), _p(12, 12, u))

    elif nama == "pengaturan":
        # roda gigi bergerigi
        luar = 9.6 * u
        dalam = 6.9 * u
        pusat = 12 * u
        jalur = QPainterPath()
        jumlah = 8
        for i in range(jumlah * 2):
            a = math.radians(i * (360 / (jumlah * 2)))
            r = luar if i % 2 == 0 else dalam
            titik = QPointF(pusat + r * math.cos(a), pusat + r * math.sin(a))
            if i == 0:
                jalur.moveTo(titik)
            else:
                jalur.lineTo(titik)
        jalur.closeSubpath()
        p.drawPath(jalur)
        p.drawEllipse(_r(9.2, 9.2, 5.6, 5.6, u))

    elif nama == "bantuan":
        p.drawEllipse(_r(3.5, 3.5, 17, 17, u))
        p.drawArc(_r(8.4, 7, 7.2, 6.4, u), 200 * 16, -230 * 16)
        p.drawLine(_p(12, 13.2, u), _p(12, 14.6, u))
        p.drawPoint(_p(12, 17.6, u))

    elif nama == "keluar":
        p.drawPolyline(_poli([(12.5, 3.5), (5, 3.5), (5, 20.5), (12.5, 20.5)], u))
        p.drawLine(_p(10.5, 12, u), _p(20, 12, u))
        p.drawPolyline(_poli([(16.5, 8.5), (20, 12), (16.5, 15.5)], u))

    # ---------------------------------------------------------------- aksi
    elif nama == "tambah":
        p.drawLine(_p(12, 5, u), _p(12, 19, u))
        p.drawLine(_p(5, 12, u), _p(19, 12, u))

    elif nama == "simpan":
        # disket (simpan)
        p.drawPolyline(_poli([(5, 3.5), (16, 3.5), (20.5, 8), (20.5, 20.5),
                              (3.5, 20.5), (3.5, 5), (5, 3.5)], u))
        p.drawRect(_r(7.5, 3.5, 8, 6, u))
        p.drawRect(_r(7.5, 14, 9, 6.5, u))
        p.drawLine(_p(12, 15.6, u), _p(12, 18.6, u))
        p.drawLine(_p(10.4, 17.1, u), _p(13.6, 17.1, u))

    elif nama == "hapus":
        p.drawLine(_p(4, 6.8, u), _p(20, 6.8, u))
        p.drawPolyline(_poli([(6.6, 6.8), (7.3, 20.5), (16.7, 20.5), (17.4, 6.8)], u))
        p.drawPolyline(_poli([(9.6, 6.8), (9.6, 3.8), (14.4, 3.8), (14.4, 6.8)], u))

    elif nama == "cetak":
        p.drawPolyline(_poli([(7, 9), (7, 3.5), (17, 3.5), (17, 9)], u))
        p.drawRoundedRect(_r(3.5, 9, 17, 8, u), 1.5 * u, 1.5 * u)
        p.drawRect(_r(7, 15, 10, 5.5, u))

    elif nama == "segarkan":
        p.drawArc(_r(4, 4, 16, 16, u), 60 * 16, 280 * 16)
        p.drawPolyline(_poli([(15.5, 3.5), (20, 5.5), (18.5, 10)], u))

    elif nama == "mata":
        # mata simetris dengan pupil di tengah
        jalur = QPainterPath(_p(2.8, 12, u))
        jalur.quadTo(_p(12, 5.6, u), _p(21.2, 12, u))
        jalur.quadTo(_p(12, 18.4, u), _p(2.8, 12, u))
        p.drawPath(jalur)
        p.drawEllipse(_r(9.3, 9.3, 5.4, 5.4, u))
        p.drawEllipse(_r(11.3, 11.3, 1.4, 1.4, u))

    elif nama == "kalender":
        p.drawRoundedRect(_r(4, 5.5, 16, 15, u), 2 * u, 2 * u)
        p.drawLine(_p(4, 10.5, u), _p(20, 10.5, u))
        p.drawLine(_p(8.5, 3, u), _p(8.5, 6.8, u))
        p.drawLine(_p(15.5, 3, u), _p(15.5, 6.8, u))
        p.drawPoint(_p(8.6, 14.5, u))
        p.drawPoint(_p(12, 14.5, u))

    elif nama == "transfer":
        p.drawLine(_p(4, 9, u), _p(20, 9, u))
        p.drawPolyline(_poli([(16, 5.5), (20, 9), (16, 12.5)], u))
        p.drawLine(_p(20, 15, u), _p(4, 15, u))
        p.drawPolyline(_poli([(8, 11.5), (4, 15), (8, 18.5)], u))

    elif nama == "peringatan":
        p.drawPolyline(_poli([(12, 3.8), (21.2, 20.2), (2.8, 20.2), (12, 3.8)], u))
        p.drawLine(_p(12, 10, u), _p(12, 14.8, u))
        p.drawPoint(_p(12, 17.6, u))

    elif nama == "info":
        p.drawEllipse(_r(3.5, 3.5, 17, 17, u))
        p.drawLine(_p(12, 11, u), _p(12, 16.5, u))
        p.drawPoint(_p(12, 7.8, u))

    elif nama == "kunci":
        p.drawRoundedRect(_r(5, 10, 14, 10.5, u), 2 * u, 2 * u)
        p.drawArc(_r(8, 4, 8, 9.5, u), 0, 180 * 16)
        p.drawLine(_p(12, 14, u), _p(12, 16.8, u))

    elif nama == "buka":
        p.drawRoundedRect(_r(5, 10, 14, 10.5, u), 2 * u, 2 * u)
        p.drawArc(_r(8, 4, 8, 9.5, u), 20 * 16, 160 * 16)
        p.drawLine(_p(12, 14, u), _p(12, 16.8, u))

    elif nama == "waktu":
        p.drawEllipse(_r(3.5, 3.5, 17, 17, u))
        p.drawPolyline(_poli([(12, 7), (12, 12.4), (16, 14.6)], u))

    elif nama == "laporan_kecil":
        # garis tren naik (untuk grafik mini)
        p.drawPolyline(_poli([(3.5, 17.5), (8.5, 11.5), (13, 14.5), (20.5, 6.5)], u))
        p.drawPolyline(_poli([(16, 6.5), (20.5, 6.5), (20.5, 11)], u))

    elif nama == "dokumen":
        # berkas dengan lipatan sudut
        p.drawPolyline(_poli([(5.5, 3.5), (14, 3.5), (18.5, 8), (18.5, 20.5),
                              (5.5, 20.5), (5.5, 3.5)], u))
        p.drawPolyline(_poli([(14, 3.5), (14, 8), (18.5, 8)], u))
        p.drawLine(_p(8.5, 12.5, u), _p(15.5, 12.5, u))
        p.drawLine(_p(8.5, 16, u), _p(15.5, 16, u))

    elif nama == "panah_kiri":
        p.drawLine(_p(15.5, 5, u), _p(8, 12, u))
        p.drawLine(_p(8, 12, u), _p(15.5, 19, u))

    elif nama == "panah_kanan":
        p.drawLine(_p(8.5, 5, u), _p(16, 12, u))
        p.drawLine(_p(16, 12, u), _p(8.5, 19, u))

    elif nama == "nonaktif":
        # Lingkaran bergaris miring: lambang umum untuk keadaan dimatikan.
        p.drawEllipse(_r(4, 4, 16, 16, u))
        p.drawLine(_p(7.6, 7.6, u), _p(16.4, 16.4, u))

    elif nama == "aktif":
        # Lingkaran dengan tanda centang: keadaan dinyalakan.
        p.drawEllipse(_r(4, 4, 16, 16, u))
        p.drawPolyline(_poli([(8, 12.4), (11, 15.4), (16.4, 8.8)], u))

    elif nama == "panah_bawah":
        p.drawLine(_p(5, 8.5, u), _p(12, 16, u))
        p.drawLine(_p(12, 16, u), _p(19, 8.5, u))

    else:
        # ikon tidak dikenal: tampilkan kotak kosong bergaris tipis
        p.drawRoundedRect(_r(5, 5, 14, 14, u), 2 * u, 2 * u)


_NAMA = {
    "dashboard", "analisis", "pencarian", "jurnal", "penjualan", "pembelian",
    "biaya", "bank", "mitra", "kontrak", "produk", "aset", "payroll", "dimensi", "periode",
    "konsolidasi", "laporan", "pajak", "checklist", "pengguna", "audit",
    "recycle", "impor", "ekspor", "coa", "perusahaan", "lan", "pengaturan",
    "bantuan", "keluar", "tambah", "simpan", "hapus", "cetak", "segarkan",
    "mata", "kalender", "transfer", "peringatan", "info", "uang", "kunci",
    "buka", "dokumen", "waktu", "laporan_kecil",
    "panah_kiri", "panah_kanan", "panah_bawah",
    "nonaktif", "aktif",
}


def pixmap(nama: str, warna: str = WARNA_GELAP, ukuran: int = 20) -> QPixmap:
    """Pixmap ikon; hasil digambar ulang lalu disimpan di cache."""
    kunci = ("pixmap", nama, warna, ukuran)
    if kunci in _CACHE:
        return _CACHE[kunci]

    pix = QPixmap(ukuran, ukuran)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing, True)
    pena = QPen(QColor(warna))
    pena.setWidthF(max(1.35, ukuran / 15.0))
    pena.setCapStyle(Qt.RoundCap)
    pena.setJoinStyle(Qt.RoundJoin)
    p.setPen(pena)
    p.setBrush(Qt.NoBrush)
    _gambar(nama, p, ukuran / 24.0)
    p.end()

    _CACHE[kunci] = pix
    return pix


def ikon(nama: str, warna: str = WARNA_GELAP, ukuran: int = 20) -> QIcon:
    """QIcon dari ikon garis; aman dipanggil berulang (memakai cache)."""
    kunci = ("ikon", nama, warna, ukuran)
    if kunci not in _CACHE:
        _CACHE[kunci] = QIcon(pixmap(nama, warna, ukuran))
    return _CACHE[kunci]


def semua_nama() -> list:
    return sorted(_NAMA)
