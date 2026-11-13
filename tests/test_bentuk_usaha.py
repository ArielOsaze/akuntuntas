"""
Uji antarmuka yang menyesuaikan bentuk badan usaha.

Cara pakai:
    python tests/test_bentuk_usaha.py

Yang diuji:
  1. Menu yang tidak dipakai suatu bentuk badan disembunyikan.
  2. Perhitungan pajak menyesuaikan bentuk badan (orang pribadi mendapat
     pembebasan Rp500 juta, badan tidak).
  3. Setiap bentuk badan dapat membuka halaman yang tersedia.
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "src"))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

lulus = gagal = 0


def cek(nama: str, syarat: bool, catatan: str = ""):
    global lulus, gagal
    if syarat:
        lulus += 1
        print(f"  [LULUS] {nama}")
    else:
        gagal += 1
        print(f"  [GAGAL] {nama}" + (f" - {catatan}" if catatan else ""))


def siapkan_data() -> Path:
    """Siapkan basis data contoh terpisah untuk pengujian."""
    folder = AKAR / "_ujibentuk"
    if folder.exists():
        shutil.rmtree(folder, ignore_errors=True)
    os.environ["AKUNTANSIID_DATA"] = str(folder)

    # buat_data_contoh.py menerima folder tujuan sebagai argumen
    import subprocess
    hasil = subprocess.run(
        [sys.executable, str(AKAR / "tools" / "buat_data_contoh.py"),
         str(folder)],
        capture_output=True, cwd=str(AKAR), text=True)
    if hasil.returncode != 0:
        print(f"gagal menyiapkan data contoh: {hasil.stderr[-300:]}")
    return folder


def menu_tersembunyi(sidebar) -> set:
    """
    Menu yang disembunyikan karena tidak relevan dengan bentuk badan.

    Menu di dalam kelompok yang sedang tertutup BUKAN menu tersembunyi:
    pengguna dapat membukanya dengan satu klik. Karena itu pemeriksaan
    dilakukan dengan membuka seluruh kelompok lebih dahulu.
    """
    for nama, (judul, wadah) in sidebar._grup.items():
        judul.blockSignals(True)
        judul.setChecked(True)
        judul.blockSignals(False)
        wadah.setVisible(True)
    return {k for k, t in sidebar.tombol.items() if not t.isVisible()}


def uji_menu_per_bentuk():
    """Menu menyesuaikan bentuk badan usaha."""
    print("1. MENU MENYESUAIKAN BENTUK BADAN USAHA")
    from PySide6.QtWidgets import QApplication
    from akuntansi_id import config
    from akuntansi_id.core import license as lisensi_mod
    from akuntansi_id.core import security as sec
    from akuntansi_id.ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])

    # Halaman lanjutan hanya tersedia pada paket Enterprise. Pemeriksaan
    # bentuk badan usaha memakai paket Enterprise supaya yang terlihat
    # hanya pengaruh bentuk badan usaha.
    lisensi = lisensi_mod.Lisensi(kunci="ATNTUJI", paket="enterprise", fitur={})

    harapan = {
        "umkm_op": {"konsolidasi", "payroll"},
        "pt_perorangan": {"konsolidasi"},
        "pt": set(),
        "cv": set(),
        "koperasi": set(),
    }

    for bentuk, seharusnya_disembunyikan in harapan.items():
        hasil = sec.LoginResult(ok=True, user_id=1, username="uji",
                                full_name="Uji", role="owner",
                                app_mode="expert", mode_dipilih=True)
        jw = MainWindow(hasil, lisensi=lisensi)
        jw.resize(1400, 880)
        jw.show()
        for _ in range(6):
            app.processEvents()

        jw.sidebar.terapkan_bentuk(bentuk)
        for _ in range(4):
            app.processEvents()

        sembunyi = menu_tersembunyi(jw.sidebar)
        nama = config.ENTITY_TYPES[bentuk]["singkat"]
        cek(f"{nama}: menu tidak relevan disembunyikan",
            sembunyi == seharusnya_disembunyikan,
            f"dapat {sorted(sembunyi)}, harap {sorted(seharusnya_disembunyikan)}")

        # seluruh menu yang relevan harus tetap tersedia
        tersedia = [k for k in jw.sidebar.tombol if k not in sembunyi]
        cek(f"{nama}: masih ada menu yang dapat dipakai", len(tersedia) >= 26,
            f"hanya {len(tersedia)} menu")
        jw.close()


def uji_akun_bawaan_per_bentuk():
    """Akun bawaan setiap formulir harus ada dan benar pada bagan akun."""
    print()
    print("2. AKUN BAWAAN SESUAI BAGAN AKUN PER BENTUK BADAN")
    from PySide6.QtWidgets import QApplication
    from akuntansi_id import coa, db, services
    from akuntansi_id.core import license as lisensi_mod
    from akuntansi_id.ui.main_window import AppContext
    from akuntansi_id.ui.pages.aset import DialogAset
    from akuntansi_id.ui.pages.entitas import DialogTemplateBerulang
    from akuntansi_id.ui.pages.pembelian import DialogBill

    app = QApplication.instance() or QApplication([])
    lisensi = lisensi_mod.Lisensi(kunci="ATNTUJI", paket="enterprise", fitur={})

    # Peran -> kode yang benar pada masing-masing bagan akun. Kode yang
    # berbeda antar-template pernah tertukar: 1201 berarti Peralatan pada
    # UMKM tetapi Tanah pada PT, sedangkan 1104 berarti Pajak Dibayar
    # Dimuka pada PT Perorangan.
    harapan = {
        "umkm_op": {
            "persediaan": "1102", "aset_peralatan": "1201",
            "akum_penyusutan": "1202", "beban_penyusutan": "6007",
            "sewa": "6002", "beban_umum": "6011",
            "beban_gaji": "6001", "beban_jasa": "6006",
            "biaya_bank": "6009", "saldo_laba": "3101",
            "utang_ppn_keluaran": "2101", "utang_pph": "2102",
            "utang_pajak_daerah": "2103",
        },
        "pt_perorangan": {
            "persediaan": "1102", "aset_peralatan": "1201",
            "akum_penyusutan": "1202", "beban_penyusutan": "6007",
            "sewa": "6002", "beban_umum": "6011",
            "beban_gaji": "6001", "beban_jasa": "6006",
            "biaya_bank": "6009", "saldo_laba": "3101",
            "utang_ppn_keluaran": "2101", "utang_pph": "2102",
            "utang_pajak_daerah": "2103", "utang_pph_badan": "2301",
        },
        "pt": {
            "persediaan": "1104", "aset_peralatan": "1208",
            "akum_penyusutan": "1209", "beban_penyusutan": "6019",
            "sewa": "6006", "beban_umum": "6023",
            "beban_gaji": "6001", "beban_jasa": "6012",
            "biaya_bank": "6013", "saldo_laba": "3004",
            "utang_ppn_keluaran": "2003", "utang_pph": "2005",
            "utang_pajak_daerah": "2014", "utang_pph_badan": "2007",
        },
    }
    for bentuk, peran_harapan in harapan.items():
        cid = services.create_company(f"Uji Akun {bentuk}", bentuk,
                                      lisensi=lisensi)
        nama = bentuk
        for peran, kode_benar in peran_harapan.items():
            kode = coa.kode_akun_bawaan(cid, peran)
            cek(f"{nama}: akun peran {peran} = {kode_benar}", kode == kode_benar,
                f"dapat {kode}")

        # Formulir harus langsung memilih akun yang ada pada bagan akun
        # perusahaan, bukan kode bawaan template lain.
        ctx = AppContext(company_id=cid,
                         company=services.get_company(cid),
                         beginner=False, lisensi=lisensi)
        d_aset = DialogAset(ctx)
        d_bill = DialogBill(ctx)
        d_template = DialogTemplateBerulang(ctx)
        cek(f"{nama}: dialog aset memakai akun yang benar",
            (d_aset.cmb_akun_aset.currentData(),
             d_aset.cmb_akun_akum.currentData(),
             d_aset.cmb_akun_beban.currentData())
            == (peran_harapan["aset_peralatan"],
                peran_harapan["akum_penyusutan"],
                peran_harapan["beban_penyusutan"]),
            f"dapat {d_aset.cmb_akun_aset.currentData()}, "
            f"{d_aset.cmb_akun_akum.currentData()}, "
            f"{d_aset.cmb_akun_beban.currentData()}")
        cek(f"{nama}: dialog pembelian persediaan memakai akun yang benar",
            d_bill.cmb_akun.currentData() == peran_harapan["persediaan"],
            f"dapat {d_bill.cmb_akun.currentData()}")
        cek(f"{nama}: template berulang memakai akun yang benar",
            (d_template.cmb_debit.currentData(),
             d_template.cmb_kredit.currentData())
            == (peran_harapan["sewa"], "1001"),
            f"dapat {d_template.cmb_debit.currentData()}, "
            f"{d_template.cmb_kredit.currentData()}")
        d_aset.deleteLater()
        d_bill.deleteLater()
        d_template.deleteLater()

        for peran in peran_harapan.values():
            ada = db.q1("SELECT 1 FROM accounts WHERE company_id=? AND kode=?",
                        (cid, peran))
            cek(f"{nama}: akun {peran} ada di bagan akun", bool(ada))
        for _ in range(3):
            app.processEvents()

        # Jurnal penutup harus memindahkan laba ke akun Saldo Laba milik
        # template bentuk usaha itu, bukan ke kode tetap milik template lain.
        services.simpan_jurnal_manual(
            cid, "2026-06-30", f"UJI-PENDAPATAN-{bentuk}", "Uji pendapatan",
            [{"kode_akun": "1001", "debit": 100_000, "kredit": 0},
             {"kode_akun": "4001", "debit": 0, "kredit": 100_000}])
        services.simpan_jurnal_manual(
            cid, "2026-06-30", f"UJI-BEBAN-{bentuk}", "Uji beban",
            [{"kode_akun": peran_harapan["beban_umum"], "debit": 40_000,
              "kredit": 0},
             {"kode_akun": "1001", "debit": 0, "kredit": 40_000}])
        jp = services.buat_jurnal_penutup(cid, 2026)
        isi_jp = db.q("SELECT kode_akun, debit, kredit FROM journal_lines "
                      "WHERE entry_id=?", (jp,))
        total_debit = sum(int(b["debit"] or 0) for b in isi_jp)
        total_kredit = sum(int(b["kredit"] or 0) for b in isi_jp)
        cek(f"{nama}: jurnal penutup seimbang",
            total_debit == total_kredit == 100_000,
            f"debit={total_debit}, kredit={total_kredit}")
        baris_laba = [b for b in isi_jp
                      if b["kode_akun"] == peran_harapan["saldo_laba"]]
        cek(f"{nama}: laba ditutup ke akun {peran_harapan['saldo_laba']}",
            len(baris_laba) == 1
            and int(baris_laba[0]["kredit"] or 0) == 60_000,
            f"dapat {[(b['kode_akun'], b['debit'], b['kredit']) for b in isi_jp]}")


def uji_pajak_per_bentuk():
    """Pajak menyesuaikan bentuk badan usaha."""
    print()
    print("3. PAJAK MENYESUAIKAN BENTUK BADAN")
    from akuntansi_id import config
    from akuntansi_id.core import tax_engine as tx

    cek("setiap bentuk badan punya keterangan pajak",
        all("pajak" in v for v in config.FITUR_PER_BENTUK.values()))

    # Orang pribadi: omzet sampai Rp500 juta tidak dikenai pajak
    op = tx.hitung_pph_final_umkm(1_000_000_000, bentuk_badan="umkm_op",
                                  final_eligible_dikonfirmasi=True,
                                  omzet_kumulatif_op=0)
    cek("orang pribadi: layak memakai PPh Final", op.layak)
    cek("orang pribadi: dasar pengenaan Rp500 juta (bebas Rp500 juta)",
        op.dasar_pengenaan == 500_000_000,
        f"dapat {op.dasar_pengenaan:,.0f}")
    cek("orang pribadi: pajak Rp2,5 juta",
        op.pph_final == 2_500_000, f"dapat {op.pph_final:,.0f}")

    # Badan: seluruh omzet jadi dasar pengenaan
    badan = tx.hitung_pph_final_umkm(1_000_000_000, bentuk_badan="pt",
                                     final_eligible_dikonfirmasi=True)
    cek("badan: dasar pengenaan seluruh omzet",
        badan.dasar_pengenaan == 1_000_000_000,
        f"dapat {badan.dasar_pengenaan:,.0f}")
    cek("badan: pajak Rp5 juta",
        badan.pph_final == 5_000_000, f"dapat {badan.pph_final:,.0f}")
    cek("badan tidak mendapat pembebasan Rp500 juta",
        badan.pph_final > op.pph_final,
        "pajak badan seharusnya lebih besar daripada orang pribadi")

    # Omzet di atas Rp4,8 miliar tidak boleh memakai PPh Final
    besar = tx.hitung_pph_final_umkm(5_000_000_000, bentuk_badan="umkm_op",
                                     final_eligible_dikonfirmasi=True)
    cek("omzet di atas Rp4,8 miliar tidak layak PPh Final", not besar.layak)


def uji_halaman_per_bentuk():
    """Halaman yang tersedia dapat dibuka pada setiap bentuk badan."""
    print()
    print("4. HALAMAN DAPAT DIBUKA PADA SETIAP BENTUK BADAN")
    from PySide6.QtWidgets import QApplication
    from akuntansi_id import config
    from akuntansi_id.core import license as lisensi_mod
    from akuntansi_id.core import security as sec
    from akuntansi_id.ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])

    # Paket Enterprise dipakai agar seluruh halaman lanjutan ikut diuji.
    lisensi = lisensi_mod.Lisensi(kunci="ATNTUJI", paket="enterprise", fitur={})

    for bentuk in config.ENTITY_TYPES:
        hasil = sec.LoginResult(ok=True, user_id=1, username="uji",
                                full_name="Uji", role="owner",
                                app_mode="beginner", mode_dipilih=True)
        jw = MainWindow(hasil, lisensi=lisensi)
        jw.resize(1400, 880)
        jw.show()
        for _ in range(6):
            app.processEvents()
        jw.sidebar.terapkan_bentuk(bentuk)
        for _ in range(4):
            app.processEvents()

        # uji seluruh menu yang relevan, termasuk yang ada di kelompok tertutup
        tersedia = [k for k in jw.sidebar.tombol
                    if k not in menu_tersembunyi(jw.sidebar)]
        gagal_buka = []
        for kode in tersedia:
            try:
                jw._navigasi(kode)
                for _ in range(3):
                    app.processEvents()
            except Exception as e:
                gagal_buka.append(f"{kode}: {e}")

        nama = config.ENTITY_TYPES[bentuk]["singkat"]
        cek(f"{nama}: seluruh {len(tersedia)} halaman dapat dibuka",
            not gagal_buka, "; ".join(gagal_buka[:2]))
        jw.close()


def main() -> int:
    print("=" * 66)
    print("UJI ANTARMUKA PER BENTUK BADAN USAHA")
    print("=" * 66)
    print()

    folder = siapkan_data()
    try:
        uji_menu_per_bentuk()
        uji_akun_bawaan_per_bentuk()
        uji_pajak_per_bentuk()
        uji_halaman_per_bentuk()
    finally:
        shutil.rmtree(folder, ignore_errors=True)

    print()
    print("=" * 66)
    print(f"RINGKASAN: {lulus} lulus, {gagal} gagal")
    print("=" * 66)
    return 1 if gagal else 0


if __name__ == "__main__":
    sys.exit(main())
