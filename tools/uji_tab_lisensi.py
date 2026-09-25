"""
Uji tab Lisensi & Keamanan di halaman Pengaturan.

Tab ini baru. Yang diperiksa: tabnya ada, isinya terbentuk, dan seluruh
keterangannya muncul tanpa galat. Pemeriksaan memakai data lisensi
sementara supaya data asli pengguna tidak tersentuh.

Cara pakai:
    python tools/uji_tab_lisensi.py
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "src"))

FOLDER = Path(tempfile.mkdtemp(prefix="akuntuntas_tab_lisensi_"))
os.environ["LOCALAPPDATA"] = str(FOLDER)

from PySide6.QtWidgets import QApplication  # noqa: E402

from akuntansi_id import config, db  # noqa: E402
from akuntansi_id.ui import theme  # noqa: E402
from akuntansi_id.ui.pages import pengaturan  # noqa: E402


def main() -> int:
    app = QApplication([])
    theme.palet_terang(app)
    app.setStyleSheet(theme.stylesheet())

    db.init_db()

    lulus = 0
    gagal = 0

    def cek(nama: str, syarat: bool, keterangan: str = ""):
        nonlocal lulus, gagal
        if syarat:
            lulus += 1
            print(f"  [LULUS] {nama}")
        else:
            gagal += 1
            print(f"  [GAGAL] {nama}" + (f" — {keterangan}" if keterangan else ""))

    print("=" * 74)
    print("  UJI TAB LISENSI & KEAMANAN")
    print("=" * 74)
    print()

    # Halaman Pengaturan memerlukan konteks aplikasi. Konteksnya disusun
    # sederhana karena yang diuji hanya tab lisensi.
    from akuntansi_id.core import license as LIS

    class Konteks:
        """Konteks sekecil mungkin, hanya yang dipakai halaman ini."""

        def __init__(self):
            self.lisensi = None
            self.perusahaan = None
            self.pengguna = None
            self.tahun = 2026
            self.beginner = True
            self.data_dir = Path(config.DATA_DIR)

    ctx = Konteks()

    halaman = pengaturan.PengaturanPage(ctx)
    halaman.resize(1180, 760)

    # ---------------------------------------------------- 1. tab ada
    print("[1. Tab tersedia]")
    judul = [halaman.tabs.tabText(i) for i in range(halaman.tabs.count())]
    print(f"    tab: {judul}")
    cek("Tab Lisensi & Keamanan ada",
          any("Lisensi" in j for j in judul))
    idx_lisensi = next((i for i, j in enumerate(judul) if "Lisensi" in j), -1)
    cek("Tab dapat dipilih", idx_lisensi >= 0)
    print()

    # ---------------------------- 2. tanpa lisensi: keterangan muncul
    print("[2. Keadaan belum ada lisensi]")
    try:
        halaman.tabs.setCurrentIndex(idx_lisensi)
        app.processEvents()
        cek("Tab terbuka tanpa galat", True)
    except Exception as e:
        cek("Tab terbuka tanpa galat", False, f"{type(e).__name__}: {e}")
    print()

    # ---------------------------- 3. dengan lisensi: isi lengkap
    print("[3. Keadaan ada lisensi]")
    # Tulis lisensi bertanda tangan sungguhan dari server tidak mungkin di
    # sini, jadi objek lisensinya disiapkan langsung lalu disimpan.
    from datetime import datetime, timedelta, timezone

    sekarang = datetime.now(timezone.utc)
    muatan = json.dumps({
        "kunci": "ATNTUJITABLISENSIAAA",
        "sidik": LIS.sidik_perangkat(),
        "paket": "enterprise",
        "fitur": {"dimensi": True},
        "pemilik": "Uji Tab",
        "diterbitkan": sekarang.isoformat(),
        "berlaku_sampai": (sekarang + timedelta(days=170)).isoformat(),
        "tenggang_sampai": (sekarang + timedelta(days=350)).isoformat(),
    })
    (Path(config.DATA_DIR) / "lisensi.json").write_text(
        json.dumps({"muatan": muatan, "tanda": "00" * 64}), encoding="utf-8")

    # Baca langsung tanpa pemeriksaan tanda tangan, karena yang diuji
    # tampilannya, bukan keamanannya.
    asli_tanda = LIS.tanda_sah
    asli_sidik = LIS.sidik_cocok
    LIS.tanda_sah = lambda m, t: True
    LIS.sidik_cocok = lambda s: True
    try:
        halaman.tabs.setCurrentIndex(0)
        app.processEvents()
        halaman.tabs.setCurrentIndex(idx_lisensi)
        app.processEvents()

        # Kumpulkan seluruh teks yang tampil.
        def semua_teks(widget) -> str:
            from PySide6.QtWidgets import QLabel
            bagian = []
            for anak in widget.findChildren(QLabel):
                bagian.append(anak.text())
            return "\n".join(bagian)

        teks = semua_teks(halaman.tab_lisensi)
        cek("Kunci lisensi tampil", "ATNTUJITABLISENSIAAA" in teks)
        cek("Paket tampil", "Enterprise" in teks)
        cek("Pemilik tampil", "Uji Tab" in teks)
        cek("Keadaan lisensi dijelaskan",
              "Lisensi aktif" in teks or "Menunggu" in teks or "Perlu" in teks)
        print()

        # ------------------------------------- 4. keterangan keamanan
        print("[4. Keterangan perlindungan]")
        for butir in ("terikat pada perangkat", "bertanda tangan",
                      "diperiksa saat masuk", "Percobaan aktivasi",
                      "Jam komputer", "tanpa internet"):
            cek(f"Menjelaskan: {butir}", butir.lower() in teks.lower())
        print()

        # ------------------------------------------- 5. tombol tindakan
        print("[5. Tombol tindakan]")
        from PySide6.QtWidgets import QPushButton
        tombol = [b.text() for b in halaman.tab_lisensi.findChildren(QPushButton)]
        print(f"    tombol: {tombol}")
        cek("Tombol periksa lisensi ada",
              any("Periksa" in t for t in tombol))
        cek("Tombol lepas perangkat ada",
              any("Lepas" in t for t in tombol))
    finally:
        LIS.tanda_sah = asli_tanda
        LIS.sidik_cocok = asli_sidik

    print()
    print("=" * 74)
    print(f"  HASIL: {lulus} LULUS, {gagal} GAGAL")
    print("=" * 74)
    return 1 if gagal else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(line_buffering=True)
    kode = main()
    sys.stdout.flush()
    os._exit(kode)
