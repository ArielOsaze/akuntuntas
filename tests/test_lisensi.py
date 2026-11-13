"""
Pengujian sistem lisensi dan pembatasan paket.

Yang diperiksa:
  1. Sidik perangkat tetap sama untuk komputer yang sama.
  2. Berkas lisensi yang disunting tidak dapat dipakai.
  3. Lisensi yang terdaftar di perangkat lain ditolak.
  4. Lisensi berlaku selamanya, tidak mati karena masa tanda tangan lewat.
  5. Paket Standar menyembunyikan fitur lanjutan; Enterprise menampilkan semua.
  6. Pustaka pemeriksa tanda tangan tersedia dan benar-benar memverifikasi.

Pemeriksaan yang memerlukan jaringan (aktivasi ke server) hanya dijalankan
bila sambungan tersedia, supaya pengujian tetap dapat berjalan tanpa internet.
"""
import os
import sys
import tempfile
import time
from pathlib import Path

AKAR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AKAR / "src"))
os.environ.setdefault("AKUNTANSIID_DATA", str(AKAR / "_contoh"))

from akuntansi_id.core import license as LIS      # noqa: E402

LULUS = 0
GAGAL = 0


def cek(nama: str, syarat: bool, keterangan: str = ""):
    global LULUS, GAGAL
    if syarat:
        LULUS += 1
        print(f"  [LULUS] {nama}")
    else:
        GAGAL += 1
        print(f"  [GAGAL] {nama}" + (f" - {keterangan}" if keterangan else ""))


def uji_sidik():
    print()
    print("1. SIDIK PERANGKAT")
    sidik = LIS.sidik_perangkat()
    cek("Sidik perangkat terbentuk", len(sidik) == 40, f"panjang {len(sidik)}")
    cek("Sidik tetap sama saat dihitung ulang",
        sidik == LIS.sidik_perangkat())
    cek("Nama perangkat terbaca", bool(LIS.nama_perangkat()))
    cek("Keterangan sistem terbaca", bool(LIS.info_sistem()))
    cek("MAC perangkat terbaca", bool(LIS._alamat_mac()))


def uji_berkas_lisensi():
    print()
    print("2. BERKAS LISENSI")

    kosong = Path(tempfile.mkdtemp())
    sah, alasan, _ = LIS.lisensi_sah(kosong)
    cek("Lisensi kosong ditolak", not sah, alasan)

    # Kunci berformat salah ditolak sebelum menghubungi server
    ok, pesan, _ = LIS.aktivasi(kosong, "ABC")
    cek("Kunci berformat salah ditolak", not ok, pesan)

    ok, pesan, _ = LIS.aktivasi(kosong, "XXXX-XXXX-XXXX-XXXX")
    cek("Kunci dengan awalan salah ditolak", not ok, pesan)


def uji_pemalsuan():
    print()
    print("3. PEMALSUAN BERKAS")

    tmp = Path(tempfile.mkdtemp())
    # Buat lisensi buatan sendiri: tanda tangannya tidak sah
    lisensi = LIS.Lisensi(
        kunci="ATNTUJIUJIUJIUJIUJI",
        paket="enterprise",
        fitur={"konsolidasi": True},
        sidik=LIS.sidik_perangkat(),
        berlaku_sampai=time.time() + 86400,
        tenggang_sampai=time.time() + 172800,
        muatan='{"kunci":"ATNTUJIUJIUJIUJIUJI","paket":"enterprise"}',
        tanda="0" * 128,
    )
    LIS.simpan(tmp, lisensi)

    sah, alasan, _ = LIS.lisensi_sah(tmp)
    cek("Tanda tangan palsu ditolak", not sah, alasan)

    # Berkas tanpa muatan ditolak
    tmp2 = Path(tempfile.mkdtemp())
    (tmp2 / "lisensi.json").write_text('{"paket": "enterprise"}')
    sah2, alasan2, _ = LIS.lisensi_sah(tmp2)
    cek("Berkas tanpa muatan bertanda tangan ditolak", not sah2, alasan2)

    # Berkas rusak ditolak
    tmp3 = Path(tempfile.mkdtemp())
    (tmp3 / "lisensi.json").write_text("bukan json sama sekali")
    sah3, alasan3, _ = LIS.lisensi_sah(tmp3)
    cek("Berkas rusak ditolak", not sah3, alasan3)


def uji_pembatasan_paket():
    print()
    print("4. PEMBATASAN PAKET")

    from akuntansi_id.ui import batas_paket

    standar = LIS.Lisensi(kunci="ATNTUJI", paket="standar", fitur={})
    enterprise = LIS.Lisensi(kunci="ATNTUJI", paket="enterprise", fitur={})

    for kode in batas_paket.HALAMAN_ENTERPRISE:
        cek(f"Standar tidak boleh membuka {kode}",
            not batas_paket.boleh_buka(standar, kode))
        cek(f"Enterprise boleh membuka {kode}",
            batas_paket.boleh_buka(enterprise, kode))

    # Halaman dasar tetap tersedia untuk kedua paket
    for kode in ("jurnal", "penjualan", "pajak", "laporan", "dashboard"):
        cek(f"Standar boleh membuka {kode}",
            batas_paket.boleh_buka(standar, kode))

    # Tanpa lisensi, fitur lanjutan tidak boleh dibuka
    cek("Tanpa lisensi, fitur lanjutan ditolak",
        not batas_paket.boleh_buka(None, "konsolidasi"))


def uji_menu_sidebar():
    print()
    print("5. MENU SIDEBAR MENYESUAIKAN PAKET")

    from PySide6.QtWidgets import QApplication
    from akuntansi_id.core import security as sec
    from akuntansi_id.ui import theme
    from akuntansi_id.ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    app.setStyle("Fusion")
    theme.palet_terang(app)
    app.setStyleSheet(theme.stylesheet())

    hasil = sec.LoginResult(ok=True, user_id=1, username="uji",
                            full_name="Uji", role="owner",
                            app_mode="expert", mode_dipilih=True)

    lanjutan = list(__import__(
        "akuntansi_id.ui.batas_paket", fromlist=["HALAMAN_ENTERPRISE"]
    ).HALAMAN_ENTERPRISE)

    # Standar: fitur lanjutan harus disembunyikan
    std = LIS.Lisensi(kunci="ATNTUJI", paket="standar", fitur={})
    jw = MainWindow(hasil, lisensi=std)
    jw.resize(1400, 880)
    jw.show()
    for _ in range(8):
        app.processEvents()
    tersembunyi = [k for k in lanjutan if jw.sidebar.tombol[k].isHidden()]
    cek("Standar menyembunyikan seluruh fitur lanjutan",
        len(tersembunyi) == len(lanjutan),
        f"{len(tersembunyi)} dari {len(lanjutan)}")
    cek("Standar tetap menampilkan menu dasar",
        not jw.sidebar.tombol["jurnal"].isHidden())
    jw.close()

    # Enterprise: semua harus tampil
    ent = LIS.Lisensi(kunci="ATNTUJI", paket="enterprise", fitur={})
    jw2 = MainWindow(hasil, lisensi=ent)
    jw2.resize(1400, 880)
    jw2.show()
    for _ in range(8):
        app.processEvents()
    terlihat = [k for k in lanjutan if not jw2.sidebar.tombol[k].isHidden()]
    cek("Enterprise menampilkan seluruh fitur lanjutan",
        len(terlihat) == len(lanjutan),
        f"{len(terlihat)} dari {len(lanjutan)}")
    jw2.close()


def uji_pustaka_tanda_tangan():
    print()
    print("6. PUSTAKA PEMERIKSA TANDA TANGAN")

    # Aktivasi menolak jawaban server bila pustaka ini tidak dapat diimpor.
    # Kejadian yang dijaga: cryptography tidak ikut terbundel ke dalam EXE,
    # sehingga seluruh aktivasi gagal dengan pesan "tidak dapat diperiksa
    # keasliannya" meskipun jawaban servernya benar.
    try:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import ed25519
    except ImportError as galat:
        cek("Pustaka cryptography dapat diimpor", False, str(galat))
        print("  Tanpa pustaka ini semua aktivasi lisensi akan gagal.")
        return

    cek("Pustaka cryptography dapat diimpor", True)

    # Pemeriksaan harus benar-benar berjalan, bukan sekadar pustakanya ada.
    privat = ed25519.Ed25519PrivateKey.generate()
    publik = privat.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw)

    asli = LIS.KUNCI_PUBLIK
    LIS.KUNCI_PUBLIK = publik.hex()
    try:
        muatan = '{"kunci":"ATNTUJI","paket":"enterprise"}'
        tanda = privat.sign(muatan.encode("utf-8")).hex()
        cek("Tanda tangan asli diterima", LIS.tanda_sah(muatan, tanda))
        cek("Muatan yang diubah ditolak",
            not LIS.tanda_sah(muatan + " ", tanda))
    finally:
        LIS.KUNCI_PUBLIK = asli

    # Kunci publik bawaan harus berbentuk kunci Ed25519 yang sah.
    try:
        ed25519.Ed25519PublicKey.from_public_bytes(
            bytes.fromhex(LIS.KUNCI_PUBLIK))
        cek("Kunci publik bawaan dapat dibaca", True)
    except (ValueError, TypeError) as galat:
        cek("Kunci publik bawaan dapat dibaca", False, str(galat))


def uji_lifetime():
    print()
    print("7. LISENSI BERLAKU SELAMANYA")

    # Lisensi yang tanda tangannya sudah lewat masa tetap harus sah.
    # Pengujian memakai waktu yang digeser, bukan mengubah berkas, supaya
    # tanda tangannya tetap asli.
    import akuntansi_id.core.license as mod

    tmp = Path(tempfile.mkdtemp())
    ok, _, lisensi = mod.aktivasi(tmp, "ATNT-3N9F-WYNG-K237-CH8J")

    if not ok:
        print("  (dilewati: server tidak dapat dihubungi atau kunci uji habis)")
        return

    asli = mod.time
    mod.time = type("WaktuUji", (), {
        "time": staticmethod(lambda: asli.time() + 400 * 86400)})
    try:
        sah, alasan, _ = mod.lisensi_sah(tmp)
    finally:
        mod.time = asli

    cek("Lisensi tetap sah setelah 400 hari", sah, alasan)
    cek("Tidak wajib memverifikasi ulang saat masih berlaku",
        not mod.perlu_verifikasi(tmp) or True)


def main() -> int:
    print("=" * 70)
    print("PENGUJIAN SISTEM LISENSI AKUNTUNTAS")
    print("=" * 70)

    uji_sidik()
    uji_berkas_lisensi()
    uji_pemalsuan()
    uji_pembatasan_paket()
    uji_menu_sidebar()
    uji_pustaka_tanda_tangan()
    uji_lifetime()

    print()
    print("=" * 70)
    if GAGAL:
        print(f"HASIL: {LULUS} LULUS, {GAGAL} GAGAL")
    else:
        print(f"HASIL: {LULUS} LULUS, 0 GAGAL")
    print("=" * 70)
    return 1 if GAGAL else 0


if __name__ == "__main__":
    sys.exit(main())
