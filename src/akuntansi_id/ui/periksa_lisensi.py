"""
Pemeriksaan lisensi senyap saat pengguna masuk.

Lisensi diperiksa ke server setiap kali halaman masuk dibuka, tanpa
mengganggu pengguna. Pemeriksaan ini yang membuat pencabutan lisensi
berlaku: selama aplikasi tidak pernah menghubungi server, lisensi yang
sudah dicabut tetap dapat dipakai.

Tiga hal yang dijaga:

1. Pemeriksaan berjalan di latar belakang, sehingga jendela masuk tidak
   pernah membeku menunggu jawaban server.
2. Bila internet tidak tersedia, aplikasi tetap dapat dipakai. Yang
   dilarang adalah membuka aplikasi tanpa lisensi, bukan membukanya tanpa
   internet.
3. Lisensi yang dicabut atau ditangguhkan langsung menghentikan aplikasi,
   dengan keterangan yang menyebutkan sebabnya dan langkah yang dapat
   ditempuh pengguna.
"""
from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from ..core import license as LIS


class PemeriksaLisensi(QThread):
    """
    Periksa lisensi ke server tanpa menahan antarmuka.

    Sinyal hasil membawa tiga keterangan: apakah lisensi masih berlaku,
    pesan yang perlu disampaikan kepada pengguna, dan apakah pesannya
    berupa penolakan yang menghentikan pemakaian.
    """

    #: berlaku, pesan, ditolak
    selesai = Signal(bool, str, bool)

    def __init__(self, data_dir, parent=None):
        super().__init__(parent)
        self.data_dir = data_dir

    def run(self):
        try:
            terhubung, pesan = LIS.perbarui(self.data_dir)
        except Exception as e:
            # Kegagalan tak terduga tidak boleh menghentikan aplikasi.
            terhubung, pesan = False, f"{type(e).__name__}: {e}"

        if terhubung:
            # Lisensi masih berlaku menurut server.
            self.selesai.emit(True, "", False)
            return

        # Tidak terhubung ke server bukan alasan menolak. Periksa apakah
        # penolakannya berasal dari server atau hanya gangguan sambungan.
        if self._ditolak_server(pesan):
            self.selesai.emit(False, pesan, True)
        else:
            self.selesai.emit(True, pesan, False)

    @staticmethod
    def _ditolak_server(pesan: str) -> bool:
        """
        Apakah pesan berasal dari penolakan server, bukan gangguan sambungan.

        Pemeriksaan ini memakai penanda yang sama dengan pemeriksaan lisensi,
        sehingga keduanya tidak dapat berbeda pendapat tentang pesan yang
        sama.
        """
        return LIS.ditolak_server({"pesan": pesan})
