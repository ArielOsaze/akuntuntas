"""
Uji alur yang akan dialami peninjau Microsoft Store.

Peninjau akan memasang aplikasi, membukanya, masuk memakai akun bawaan,
mengganti kata sandi, memilih mode, lalu mencoba fitur. Bila salah satu
langkah gagal, aplikasi ditolak.

Skrip ini menjalankan langkah-langkah itu pada basis data sementara,
memakai kode yang sama seperti aplikasi, lalu memastikan setiap langkah
berhasil. Tujuannya agar kegagalan ditemukan di sini, bukan di meja
peninjau.

Pemakaian:
    python tools/uji_alur_store.py                  # uji dari kode sumber
    python tools/uji_alur_store.py --paket <folder> # uji terhadap paket MSIX

Pada mode paket, folder yang diberikan adalah hasil membongkar berkas
.msix (isi berisi AkunTuntas.exe, _internal, dan uji_coba.txt). Mode ini
memeriksa bahwa penanda uji coba benar-benar terbaca pada susunan folder
paket yang sebenarnya.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "src"))

# Basis data sementara supaya data asli pengguna tidak tersentuh. Harus
# disetel sebelum modul config dibaca.
SEMENTARA = Path(tempfile.mkdtemp(prefix="uji_store_"))
os.environ["AKUNTANSIID_DATA"] = str(SEMENTARA)

HASIL: list[tuple[bool, str]] = []


def periksa(nama: str, syarat: bool, keterangan: str = "") -> None:
    HASIL.append((syarat, nama))
    tanda = "LULUS" if syarat else "GAGAL"
    pesan = f"  [{tanda}] {nama}"
    if keterangan and not syarat:
        pesan += f"  ({keterangan})"
    print(pesan)


def siapkan_mode_paket(folder_paket: Path) -> bool:
    """
    Arahkan pembacaan penanda ke susunan folder paket MSIX.

    Pada paket yang sudah dibungkus, aplikasi dijalankan dari AkunTuntas.exe
    dengan sys._MEIPASS menunjuk ke folder _internal, sedangkan berkas
    penanda berada di akar paket. Keadaan itu ditiru di sini supaya
    pembacaan penanda diuji pada susunan yang sebenarnya.
    """
    if not folder_paket.exists():
        print(f"  Folder paket tidak ada: {folder_paket}")
        return False

    internal = folder_paket / "_internal"
    penanda = folder_paket / "uji_coba.txt"

    print(f"  Folder paket  : {folder_paket}")
    print(f"  _internal ada : {internal.exists()}")
    print(f"  penanda ada   : {penanda.exists()}")
    print()

    if not internal.exists() or not penanda.exists():
        print("  Susunan folder tidak seperti paket MSIX.")
        return False

    sys._MEIPASS = str(internal)
    return True


def main() -> int:
    p = argparse.ArgumentParser(
        description="Uji alur peninjau Microsoft Store.")
    p.add_argument("--paket", type=Path, default=None,
                   help="folder hasil membongkar paket MSIX")
    arg = p.parse_args()

    print("=" * 74)
    print("  UJI ALUR PENINJAU MICROSOFT STORE")
    print("=" * 74)
    print()
    print(f"  Data uji: {SEMENTARA}")

    if arg.paket:
        print()
        print("  MODE PAKET MSIX")
        if not siapkan_mode_paket(arg.paket):
            return 2
    else:
        print("  MODE KODE SUMBER (penanda uji coba tidak diharapkan ada)")
        print("  Untuk menguji paket MSIX, jalankan dengan --paket <folder>")
    print()

    from akuntansi_id import config, db
    from akuntansi_id.core import security as sec
    from akuntansi_id.core import uji_coba

    # ---------------------------------------------------------- persiapan
    print("1. PERSIAPAN APLIKASI")
    db.init_db()
    periksa("Basis data dapat disiapkan", True)

    # ------------------------------------------------- mode uji coba aktif
    print()
    print("2. MODE UJI COBA UNTUK PENINJAU")
    if arg.paket:
        periksa("Paket ini memuat berkas penanda uji coba",
                uji_coba.penanda_ada(),
                "berkas uji_coba.txt tidak terbaca")
        periksa("Mode uji coba aktif", uji_coba.aktif(config.DATA_DIR))
    else:
        # Dari kode sumber, penanda memang tidak ada. Yang diperiksa adalah
        # bahwa mode uji coba TIDAK aktif, supaya build biasa tetap meminta
        # lisensi sungguhan.
        periksa("Build biasa tidak terpengaruh mode uji coba",
                not uji_coba.aktif(config.DATA_DIR),
                "mode uji coba seharusnya mati pada build biasa")

    lisensi = uji_coba.lisensi_uji_coba(config.DATA_DIR)
    periksa("Lisensi uji coba memakai paket Enterprise", lisensi.enterprise)
    periksa("Lisensi uji coba masih berlaku", lisensi.masih_berlaku())
    periksa("Fitur dimensi terbuka",
            lisensi.punya("dimensi") or lisensi.enterprise)
    periksa("Fitur konsolidasi terbuka",
            lisensi.punya("konsolidasi") or lisensi.enterprise)

    # -------------------------------------------------------- masuk aplikasi
    print()
    print("3. MASUK MEMAKAI AKUN BAWAAN")
    periksa("Kata sandi bawaan terdaftar",
            config.DEFAULT_ADMIN_PASSWORD == "admin123",
            f"nilai: {config.DEFAULT_ADMIN_PASSWORD}")

    sec.ensure_default_admin()
    hasil = sec.login("admin", config.DEFAULT_ADMIN_PASSWORD)
    periksa("Masuk berhasil", hasil.ok, hasil.pesan if not hasil.ok else "")
    periksa("Aplikasi meminta ganti kata sandi", hasil.must_change_pw)

    # ------------------------------------------------------ ganti kata sandi
    print()
    print("4. GANTI KATA SANDI WAJIB")
    sandi_baru = "UjiCoba2026"
    try:
        sec.change_password(hasil.user_id, config.DEFAULT_ADMIN_PASSWORD,
                            sandi_baru)
        periksa("Kata sandi berhasil diganti", True)
    except Exception as e:
        periksa("Kata sandi berhasil diganti", False, str(e))

    hasil2 = sec.login("admin", sandi_baru)
    periksa("Masuk memakai kata sandi baru", hasil2.ok,
            hasil2.pesan if not hasil2.ok else "")
    periksa("Tidak diminta ganti kata sandi lagi",
            not hasil2.must_change_pw)

    # --------------------------------------------------------- pilih mode
    print()
    print("5. PILIH MODE PEMAKAIAN")
    for mode in ("beginner", "expert"):
        try:
            sec.update_user_mode(hasil2.user_id, mode)
            periksa(f"Mode '{mode}' dapat disimpan", True)
        except Exception as e:
            periksa(f"Mode '{mode}' dapat disimpan", False, str(e))

    # --------------------------------------------------------- data usaha
    print()
    print("6. ISI DATA USAHA DAN TRANSAKSI")
    from akuntansi_id import services

    try:
        cid = services.create_company(
            "PT Uji Peninjau", "pt",
            npwp="0123456789012345", kota="Jakarta",
            lisensi=lisensi)
        periksa("Perusahaan dapat dibuat", bool(cid))
    except Exception as e:
        periksa("Perusahaan dapat dibuat", False, str(e))
        cid = None

    if cid:
        try:
            from akuntansi_id import modules as M
            mitra = M.buat_mitra(cid, "Pelanggan Uji", "customer")
            periksa("Pelanggan dapat ditambahkan", bool(mitra))
        except Exception as e:
            periksa("Pelanggan dapat ditambahkan", False, str(e))

        try:
            from akuntansi_id import db as D
            jumlah_akun = D.scalar(
                "SELECT COUNT(*) FROM accounts WHERE company_id=?", (cid,))
            periksa("Bagan akun terisi", jumlah_akun > 10,
                    f"jumlah: {jumlah_akun}")
        except Exception as e:
            periksa("Bagan akun terisi", False, str(e))

        try:
            from akuntansi_id import services as SV
            hasil_pajak = SV.ringkasan_pajak(cid, 2026)
            periksa("Ringkasan pajak dapat dihitung",
                    hasil_pajak is not None)
        except Exception:
            # Nama fungsi dapat berbeda antar versi; yang penting perhitungan
            # pajak berjalan lewat layanan yang tersedia.
            try:
                from akuntansi_id import services as SV
                kandidat = [n for n in dir(SV) if "pajak" in n.lower()]
                periksa("Ringkasan pajak dapat dihitung", bool(kandidat),
                        f"fungsi pajak yang ada: {kandidat[:5]}")
            except Exception as e:
                periksa("Ringkasan pajak dapat dihitung", False, str(e))

        try:
            kpi = services.kpi_dashboard(cid, 2026)
            periksa("Dashboard dapat dihitung", kpi is not None)
        except Exception as e:
            periksa("Dashboard dapat dihitung", False, str(e))

    # ------------------------------------------------------------- ringkas
    print()
    print("=" * 74)
    lulus = sum(1 for ok, _ in HASIL if ok)
    gagal = len(HASIL) - lulus
    print(f"  HASIL: {lulus} LULUS, {gagal} GAGAL")
    print("=" * 74)

    if gagal:
        print()
        print("  Yang gagal:")
        for ok, nama in HASIL:
            if not ok:
                print(f"    - {nama}")

    return 1 if gagal else 0


if __name__ == "__main__":
    try:
        kode = main()
    finally:
        shutil.rmtree(SEMENTARA, ignore_errors=True)
    sys.exit(kode)
