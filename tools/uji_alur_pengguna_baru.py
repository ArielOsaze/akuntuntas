"""
Uji alur lengkap: masuk aplikasi lalu buka halaman Data Perusahaan.

Yang ditiru adalah pengalaman pengguna baru: aplikasi baru dipasang,
belum ada perusahaan, lalu pengguna masuk dan mengikuti panduan untuk
membuat profil perusahaan.

Alat ini menjalankan aplikasi dengan basis data kosong, masuk memakai akun
bawaan, membuka halaman Data Perusahaan, mengisi formulir, menekan tombol
Buat Perusahaan, lalu memeriksa datanya tersimpan.

Cara pakai:
    python tools/uji_alur_pengguna_baru.py
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "src"))

os.environ["QT_QPA_PLATFORM"] = "offscreen"

FOLDER = Path(tempfile.mkdtemp(prefix="akuntuntas_alur_"))
os.environ["LOCALAPPDATA"] = str(FOLDER)

from PySide6.QtCore import QDate  # noqa: E402
from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: E402

app = QApplication.instance() or QApplication([])

from akuntansi_id import config, db  # noqa: E402
from akuntansi_id.core import security as sec  # noqa: E402


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
    print("  UJI ALUR PENGGUNA BARU")
    print("=" * 76)
    print()

    # ------------------------------------------------------------- siapkan
    print("[Persiapan]")
    db.init_db()
    sec.ensure_default_admin()

    jumlah_user = db.scalar("SELECT COUNT(*) FROM users")
    p.cek("Akun bawaan dibuat otomatis", jumlah_user >= 1,
          f"pengguna={jumlah_user}")
    p.cek("Belum ada perusahaan",
          db.scalar("SELECT COUNT(*) FROM companies") == 0)
    print()

    # ---------------------------------------------------------- masuk akun
    print("[1. Masuk memakai akun bawaan]")
    nama_user = config.DEFAULT_ADMIN_USER
    sandi = config.DEFAULT_ADMIN_PASSWORD

    pengguna = sec.login(nama_user, sandi)
    p.cek("Akun bawaan dapat dipakai masuk",
          bool(pengguna and pengguna.ok),
          f"pesan='{pengguna.message if pengguna else '-'}'")
    if not (pengguna and pengguna.ok):
        return p.ringkas()
    p.cek("Peran akun adalah pemilik", pengguna.role == "owner",
          f"role='{pengguna.role}'")
    p.cek("Akun baru meminta ganti sandi",
          pengguna.must_change_pw,
          "sandi bawaan wajib diganti saat pertama masuk")
    print()

    # -------------------------------------------------- halaman perusahaan
    print("[2. Halaman Data Perusahaan dibuka]")
    from akuntansi_id.ui.pages.coa_page import PerusahaanPage

    class Konteks:
        company_id = None
        company = None
        tahun = 2026
        lisensi = None

        def muat_perusahaan(self):
            pass

    halaman = PerusahaanPage(Konteks())
    halaman.resize(1280, 820)
    halaman.muat()
    halaman.show()
    app.processEvents()

    from PySide6.QtWidgets import QLabel, QLineEdit, QPushButton

    label = [x.text() for x in halaman.findChildren(QLabel)
             if x.isVisible() and x.text().strip()]
    isian = [x for x in halaman.findChildren(QLineEdit) if x.isVisible()]
    tombol = [x for x in halaman.findChildren(QPushButton)
              if x.isVisible() and "Buat Perusahaan" in x.text()]

    p.cek("Judul halaman tampil",
          any("Data Perusahaan" in t for t in label))
    p.cek("Petunjuk langkah pertama tampil",
          any("Buat Profil Perusahaan" in t for t in label))
    p.cek("Kolom isian tersedia", len(isian) >= 4, f"isian={len(isian)}")
    p.cek("Tombol Buat Perusahaan tersedia", len(tombol) == 1,
          f"tombol={len(tombol)}")
    print()

    # ---------------------------------------------------------- isi data
    print("[3. Formulir diisi dan disimpan]")
    halaman.inp_nama.setText("Toko Berkah Jaya")
    halaman.inp_npwp.setText("02.345.678.9-012.000")
    halaman.inp_pemilik.setText("Ariel Budi")
    halaman.inp_alamat.setText("Jalan Merdeka 10")
    halaman.inp_kota.setText("Bandung")
    halaman.inp_mulai.setDate(QDate(2026, 1, 1))
    app.processEvents()

    kode_bentuk = halaman._kode_bentuk()
    p.cek("Bentuk badan usaha terbaca", bool(kode_bentuk),
          f"kode='{kode_bentuk}'")

    pesan: list[str] = []
    asli_info = QMessageBox.information
    asli_critical = QMessageBox.critical
    QMessageBox.information = staticmethod(
        lambda *a, **k: pesan.append(f"info: {a[2][:50]}") or QMessageBox.Ok)
    QMessageBox.critical = staticmethod(
        lambda *a, **k: pesan.append(f"critical: {a[2][:80]}") or QMessageBox.Ok)

    try:
        halaman._buat()
    except Exception as e:
        p.cek("Tombol tidak menimbulkan galat", False,
              f"{type(e).__name__}: {e}")
    finally:
        QMessageBox.information = asli_info
        QMessageBox.critical = asli_critical

    app.processEvents()
    galat = [x for x in pesan if x.startswith("critical")]
    p.cek("Tidak ada pesan galat", not galat, str(galat))
    if pesan:
        print(f"  pesan: {pesan[0][:70]}")
    print()

    # ------------------------------------------------- data benar tersimpan
    print("[4. Data tersimpan di basis data]")
    jumlah = db.scalar("SELECT COUNT(*) FROM companies")
    p.cek("Perusahaan tercatat", jumlah == 1, f"perusahaan={jumlah}")

    if jumlah:
        c = db.q1("SELECT * FROM companies LIMIT 1")
        p.cek("Nama benar", c["nama"] == "Toko Berkah Jaya",
              f"nama='{c['nama']}'")
        p.cek("Bentuk badan benar", c["bentuk"] == kode_bentuk,
              f"bentuk='{c['bentuk']}'")
        p.cek("NPWP benar",
              (c["npwp"] or "") == "02.345.678.9-012.000",
              f"npwp='{c['npwp']}'")
        p.cek("Pemilik benar",
              (c["nama_pemilik"] or "") == "Ariel Budi",
              f"pemilik='{c['nama_pemilik']}'")
        p.cek("Kota benar", (c["kota"] or "") == "Bandung",
              f"kota='{c['kota']}'")

        akun = db.scalar(
            "SELECT COUNT(*) FROM accounts WHERE company_id=?", (c["id"],))
        p.cek("Bagan akun dibuat otomatis", akun > 0, f"akun={akun}")

        # Periksa bagan akun sesuai bentuk badan usaha.
        jenis = db.q(
            "SELECT DISTINCT tipe FROM accounts WHERE company_id=?",
            (c["id"],))
        tipe = sorted(r["tipe"].lower() for r in jenis)
        p.cek("Bagan akun memuat aset dan kewajiban",
              any("aset" in t for t in tipe)
              and any("liabilitas" in t or "kewajiban" in t for t in tipe),
              f"tipe={tipe}")

    # ------------------------------------------------- jejak audit tercatat
    print()
    print("[5. Jejak audit tercatat]")
    jejak = db.q("SELECT action, detail FROM audit_log "
                 "WHERE action LIKE '%compan%' OR action LIKE '%entitas%' "
                 "OR entity LIKE '%compan%' "
                 "ORDER BY id DESC LIMIT 5")
    p.cek("Pembuatan perusahaan tercatat di jejak audit", len(jejak) > 0,
          f"catatan={len(jejak)}")
    if jejak:
        print(f"  catatan: {jejak[0]['action']} — "
              f"{(jejak[0]['detail'] or '')[:50]}")

    return p.ringkas()


if __name__ == "__main__":
    kode = main()
    sys.stdout.flush()
    os._exit(kode)
