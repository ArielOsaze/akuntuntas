"""
AkunTuntas - Pembatasan Fitur Menurut Paket Lisensi
====================================================
Paket Standar hanya memuat fitur dasar. Halaman yang termasuk fitur lanjutan
disembunyikan seluruhnya, bukan sekadar dinonaktifkan, supaya tidak ada
tombol yang bisa diklik lalu menampilkan pesan penolakan.

Halaman lanjutan juga dijaga di sisi halamannya sendiri: bila dibuka lewat
jalan lain (misalnya dari pencarian atau dari tombol di halaman lain),
halaman itu menampilkan keterangan bahwa fitur tersebut tersedia pada paket
Enterprise.
"""
from __future__ import annotations

from PySide6.QtWidgets import QVBoxLayout, QWidget

from . import theme
from . import widgets as w
from .theme import C

# Halaman yang hanya tersedia pada paket Enterprise.
HALAMAN_ENTERPRISE = {
    "dimensi": ("Dimensi & Biaya", "dimensi"),
    "konsolidasi": ("Konsolidasi Grup", "konsolidasi"),
    "pajak_lanjutan": ("Pajak Lanjutan", "pajak_lanjutan"),
}


def boleh_buka(lisensi, kode: str) -> bool:
    """Apakah halaman tertentu boleh dibuka pada paket lisensi ini."""
    if kode not in HALAMAN_ENTERPRISE:
        return True
    if lisensi is None:
        return False
    return lisensi.enterprise


def halaman_terkunci(nama_fitur: str) -> QWidget:
    """
    Halaman pengganti untuk fitur yang tidak tersedia pada paket ini.

    Dipakai bila halaman lanjutan sampai terbuka juga, supaya pengguna
    mendapat keterangan yang jelas alih-alih halaman kosong.
    """
    halaman = QWidget()
    lay = QVBoxLayout(halaman)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(0)

    kepala = QWidget()
    theme.latar(kepala, f"background: {C.SURFACE}; "
                        f"border-bottom: 1px solid {C.BORDER};")
    kl = QVBoxLayout(kepala)
    kl.setContentsMargins(26, 20, 26, 18)
    kl.addWidget(w.PageHeader(
        nama_fitur,
        "Fitur ini tersedia pada paket Enterprise."))
    lay.addWidget(kepala)

    isi = QWidget()
    il = QVBoxLayout(isi)
    il.setContentsMargins(26, 24, 26, 24)
    il.setSpacing(14)

    panel = w.InfoBanner(
        f"{nama_fitur} hanya tersedia pada lisensi AkunTuntas Enterprise. "
        "Paket Standar memuat pembukuan, pajak, dan laporan keuangan dasar.\n\n"
        "Untuk memakai fitur ini, tingkatkan lisensi Anda ke Enterprise. "
        "Hubungi akuntuntas@gmail.com untuk informasi peningkatan paket.",
        tingkat="warning", judul="Fitur paket Enterprise")
    il.addWidget(panel)
    il.addStretch()
    lay.addWidget(isi, 1)

    return halaman
