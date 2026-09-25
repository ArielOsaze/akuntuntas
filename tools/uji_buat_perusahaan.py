"""
Uji alur membuat perusahaan dari keadaan benar-benar kosong.

Yang diuji bukan hanya halaman tampil, tetapi sampai datanya tersimpan:
mulai dari basis data tanpa perusahaan, mengisi formulir seperti pengguna,
menekan tombol Buat Perusahaan, lalu memastikan perusahaan itu benar-benar
ada di basis data beserta bagan akunnya.

Keadaan ini yang dialami pengguna saat aplikasi baru dipasang di komputer
lain: belum ada apa pun, dan langkah pertama adalah membuat profil
perusahaan.

Cara pakai:
    python tools/uji_buat_perusahaan.py
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "src"))

os.environ["QT_QPA_PLATFORM"] = "offscreen"

# Folder data sementara supaya data asli tidak tersentuh.
FOLDER = Path(tempfile.mkdtemp(prefix="akuntuntas_buat_"))
os.environ["LOCALAPPDATA"] = str(FOLDER)

from PySide6.QtCore import QDate  # noqa: E402
from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: E402

app = QApplication.instance() or QApplication([])

from akuntansi_id import db  # noqa: E402


class Pemeriksa:
    def __init__(self):
        self.lulus = 0
        self.gagal = 0
        self.catatan: list[str] = []

    def cek(self, nama: str, syarat: bool, keterangan: str = ""):
        if syarat:
            self.lulus += 1
            print(f"  [LULUS] {nama}")
        else:
            self.gagal += 1
            print(f"  [GAGAL] {nama}"
                  + (f" — {keterangan}" if keterangan else ""))
            self.catatan.append(nama)

    def ringkas(self) -> int:
        print()
        print("=" * 76)
        print(f"  HASIL: {self.lulus} LULUS, {self.gagal} GAGAL")
        if self.catatan:
            print()
            print("  Yang gagal:")
            for c in self.catatan:
                print(f"    - {c}")
        print("=" * 76)
        return 1 if self.gagal else 0


def main() -> int:
    p = Pemeriksa()

    print("=" * 76)
    print("  UJI MEMBUAT PERUSAHAAN DARI KEADAAN KOSONG")
    print("=" * 76)
    print()

    # ------------------------------------------------------------- siapkan
    print("[Persiapan]")
    db.init_db()
    jumlah_awal = db.scalar("SELECT COUNT(*) FROM companies")
    p.cek("Basis data kosong sebelum diuji", jumlah_awal == 0,
          f"perusahaan={jumlah_awal}")
    print()

    from akuntansi_id.ui.pages.coa_page import PerusahaanPage

    class Konteks:
        company_id = None
        company = None
        tahun = 2026
        lisensi = None

        def muat_perusahaan(self):
            pass

    # ------------------------------------------------------ buka halaman
    print("[1. Halaman Data Perusahaan dibuka]")
    halaman = PerusahaanPage(Konteks())
    halaman.resize(1200, 780)
    halaman.muat()
    halaman.show()
    app.processEvents()
    p.cek("Halaman terbangun tanpa galat", halaman is not None)
    p.cek("Formulir perusahaan baru tampil",
          hasattr(halaman, "inp_nama") and halaman.inp_nama.isVisible())

    # ---------------------------------------------------------- isi form
    print()
    print("[2. Formulir diisi seperti pengguna]")
    halaman.inp_nama.setText("CV Uji Perusahaan")
    halaman.inp_npwp.setText("01.234.567.8-901.000")
    halaman.inp_pemilik.setText("Ariel Budi")
    halaman.inp_alamat.setText("Jalan Uji Nomor 1")
    halaman.inp_kota.setText("Jakarta")
    halaman.inp_mulai.setDate(QDate(2026, 1, 1))
    app.processEvents()

    kode = halaman._kode_bentuk()
    p.cek("Bentuk badan usaha terbaca", bool(kode), f"kode='{kode}'")

    # --------------------------------------------------------- tekan buat
    print()
    print("[3. Tombol Buat Perusahaan ditekan]")

    # Kotak pesan ditutup otomatis supaya uji tidak berhenti menunggu.
    pesan: list[tuple[str, str]] = []

    def tangkap_klik(tipe, judul, teks, *a, **k):
        pesan.append((judul, teks))
        return QMessageBox.Ok

    asli_info = QMessageBox.information
    asli_critical = QMessageBox.critical
    QMessageBox.information = staticmethod(
        lambda *a, **k: tangkap_klik("info", *a[1:3]) or QMessageBox.Ok)
    QMessageBox.critical = staticmethod(
        lambda *a, **k: tangkap_klik("critical", *a[1:3]) or QMessageBox.Ok)

    try:
        halaman._buat()
    except Exception as e:
        p.cek("Tombol tidak menimbulkan galat", False,
              f"{type(e).__name__}: {e}")
    finally:
        QMessageBox.information = asli_info
        QMessageBox.critical = asli_critical

    app.processEvents()

    if pesan:
        print(f"  pesan ke pengguna: {pesan[0][0]} — {pesan[0][1][:60]}...")

    galat = [j for j, _ in pesan if "critical" in j.lower()]
    p.cek("Tidak ada pesan galat", not galat, str(galat))

    # ------------------------------------------------- data benar tersimpan
    print()
    print("[4. Data benar-benar tersimpan]")
    jumlah = db.scalar("SELECT COUNT(*) FROM companies")
    p.cek("Perusahaan tercatat di basis data", jumlah == 1,
          f"perusahaan={jumlah}")

    if jumlah:
        c = db.q1("SELECT * FROM companies LIMIT 1")
        p.cek("Nama perusahaan benar",
              c["nama"] == "CV Uji Perusahaan", f"nama='{c['nama']}'")
        p.cek("Bentuk badan usaha benar",
              c["bentuk"] == kode, f"bentuk='{c['bentuk']}' kode='{kode}'")
        p.cek("NPWP tersimpan",
              (c["npwp"] or "") == "01.234.567.8-901.000",
              f"npwp='{c['npwp']}'")
        p.cek("Nama pemilik tersimpan",
              (c["nama_pemilik"] or "") == "Ariel Budi",
              f"pemilik='{c['nama_pemilik']}'")
        p.cek("Kota tersimpan", (c["kota"] or "") == "Jakarta",
              f"kota='{c['kota']}'")

        akun = db.scalar(
            "SELECT COUNT(*) FROM accounts WHERE company_id=?", (c["id"],))
        p.cek("Bagan akun dibuat otomatis", akun > 0, f"akun={akun}")

    # ---------------------------------------------- konteks ikut berubah
    print()
    print("[5. Konteks aplikasi ikut berubah]")
    p.cek("Perusahaan aktif terpasang di konteks",
          halaman.ctx.company_id is not None,
          f"company_id={halaman.ctx.company_id}")

    # ------------------------------------------- halaman berubah tampilan
    print()
    print("[6. Halaman berubah menampilkan profil perusahaan]")
    halaman.muat()
    app.processEvents()
    p.cek("Formulir perusahaan baru tidak tampil lagi",
          not hasattr(halaman, "inp_nama")
          or not halaman.inp_nama.isVisible())

    # ------------------------------------------------------ buat kedua kali
    print()
    print("[7. Membuat perusahaan kedua (paket Enterprise)]")
    # Penambahan badan usaha kedua hanya tersedia pada paket Enterprise,
    # jadi konteksnya diberi lisensi Enterprise lebih dulu.
    lisensi_uji = type("L", (), {
        "paket": "enterprise",
        "enterprise": True,
        "fitur": {"multi_entitas": True},
        "punya": lambda self, bagian: True,
    })()

    konteks2 = Konteks()
    konteks2.company_id = None
    konteks2.lisensi = lisensi_uji
    halaman2 = PerusahaanPage(konteks2)
    halaman2.resize(1200, 780)
    halaman2.muat()
    app.processEvents()
    halaman2.inp_nama.setText("PT Uji Kedua")
    app.processEvents()

    QMessageBox.information = staticmethod(
        lambda *a, **k: QMessageBox.Ok)
    QMessageBox.critical = staticmethod(
        lambda *a, **k: QMessageBox.Ok)
    try:
        halaman2._buat()
    except Exception as e:
        p.cek("Perusahaan kedua dibuat tanpa galat", False,
              f"{type(e).__name__}: {e}")
    finally:
        QMessageBox.information = asli_info
        QMessageBox.critical = asli_critical

    app.processEvents()
    jumlah2 = db.scalar("SELECT COUNT(*) FROM companies")
    p.cek("Perusahaan kedua tersimpan", jumlah2 == 2,
          f"perusahaan={jumlah2}")

    # ------------------------------------------------------------ kosong
    print()
    print("[8. Nama kosong ditolak]")
    konteks3 = Konteks()
    halaman3 = PerusahaanPage(konteks3)
    halaman3.resize(1200, 780)
    halaman3.muat()
    app.processEvents()
    halaman3.inp_nama.setText("   ")
    app.processEvents()
    jumlah_sebelum = db.scalar("SELECT COUNT(*) FROM companies")
    QMessageBox.warning = staticmethod(lambda *a, **k: QMessageBox.Ok)
    try:
        halaman3._buat()
    except Exception:
        pass
    app.processEvents()
    jumlah_sesudah = db.scalar("SELECT COUNT(*) FROM companies")
    p.cek("Perusahaan tanpa nama tidak tersimpan",
          jumlah_sesudah == jumlah_sebelum,
          f"sebelum={jumlah_sebelum} sesudah={jumlah_sesudah}")

    return p.ringkas()


if __name__ == "__main__":
    # Jendela offscreen tetap hidup setelah pengujian selesai, sehingga
    # proses tidak pernah berhenti sendiri. Keluar secara tegas supaya
    # alat ini dapat dipakai dari rangkaian otomatis.
    kode = main()
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(kode)
