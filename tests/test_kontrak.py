"""
Uji modul Kontrak & Kerja Sama.

Memeriksa nomor kontrak otomatis, masa berlaku, bentuk imbalan non-tunai,
termin, dasar hukum, perhitungan pajak, dan pembacaan dokumen.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

AKAR = Path(__file__).resolve().parents[1]
os.environ["AKUNTANSIID_DATA"] = str(AKAR / "_contoh")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(AKAR / "src"))

from akuntansi_id import db, kontrak as kt  # noqa: E402


def main() -> int:
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

    db.init_db()
    from akuntansi_id.core import security as sec
    sec.ensure_default_admin()

    # perusahaan uji
    ada = db.q1("SELECT id FROM companies ORDER BY id LIMIT 1")
    if ada:
        cid = ada["id"]
    else:
        cid = db.ex(
            "INSERT INTO companies(nama, bentuk, tahun_pajak, npwp) "
            "VALUES('Uji Kontrak','umkm_op','2026','')").lastrowid
    db.ex("DELETE FROM kontrak WHERE company_id=?", (cid,))

    # ------------------------------------------------------- nomor
    n1 = kt.nomor_berikut(cid, "kerja_sama", "2026-03-01")
    cek("Nomor kontrak berformat benar",
        n1 == "001/KTR/KS/2026", f"dapat {n1!r}")

    kid = kt.simpan(cid, {
        "judul": "Kerja Sama Uji", "jenis": "kerja_sama",
        "tanggal_mulai": "2026-03-01", "nilai": 10_000_000}, user="uji")
    n2 = kt.nomor_berikut(cid, "kerja_sama", "2026-03-01")
    cek("Nomor kedua berurutan", n2 == "002/KTR/KS/2026", f"dapat {n2!r}")

    n_mou = kt.nomor_berikut(cid, "mou", "2026-03-01")
    cek("Nomor MoU memakai kode jenis", n_mou == "001/KTR/MOU/2026",
        f"dapat {n_mou!r}")

    # ------------------------------------------------------- simpan
    k = kt.ambil(kid)
    cek("Kontrak tersimpan", k is not None)
    cek("Judul tersimpan", k and k["judul"] == "Kerja Sama Uji")
    cek("Dasar hukum terisi otomatis",
        k and len(k["dasar_hukum"]) > 40, f"dapat {len(k['dasar_hukum'] if k else '')}")

    # ------------------------------------------------------ barter
    kb = kt.simpan(cid, {
        "judul": "Barter Uji", "jenis": "kerja_sama",
        "bentuk_imbalan": "barang", "pihak_kedua": "Koperasi Uji",
        "tanggal_mulai": "2026-02-01", "nilai_barang": 50_000_000})
    kb_data = kt.ambil(kb)
    cek("Bentuk imbalan barang tersimpan",
        kb_data and kb_data["bentuk_imbalan"] == "barang")
    cek("Nilai barang tersimpan",
        kb_data and kb_data["nilai_barang"] == 50_000_000)
    cek("Nilai total barter terhitung",
        kb_data and kb_data.get("nilai_total") == 50_000_000,
        f"dapat {kb_data.get('nilai_total') if kb_data else None}")

    # --------------------------------------------------- tukar jasa
    kj = kt.simpan(cid, {
        "judul": "Tukar Jasa Uji", "jenis": "jasa",
        "bentuk_imbalan": "jasa", "pihak_kedua": "Vendor Jasa",
        "tanggal_mulai": "2026-02-01", "nilai_jasa": 75_000_000})
    kj_data = kt.ambil(kj)
    cek("Nilai jasa tersimpan",
        kj_data and kj_data["nilai_jasa"] == 75_000_000,
        f"dapat {kj_data.get('nilai_jasa') if kj_data else None}")
    cek("Nilai total tukar jasa terhitung",
        kj_data and kj_data.get("nilai_total") == 75_000_000,
        f"dapat {kj_data.get('nilai_total') if kj_data else None}")

    kt.simpan_item(kb, [
        {"arah": "kita_beri", "nama": "Beras", "jumlah": 10,
         "satuan": "karung", "nilai_satuan": 500_000},
        {"arah": "kita_terima", "nama": "Pupuk", "jumlah": 20,
         "satuan": "sak", "nilai_satuan": 250_000}])
    item = kt.item(kb)
    cek("Dua item barter tersimpan", len(item) == 2, f"dapat {len(item)}")
    cek("Total item dihitung", item and item[0]["total"] == 5_000_000,
        f"dapat {item[0]['total'] if item else 0}")

    # ------------------------------------------------------ termin
    kt2 = kt.simpan(cid, {
        "judul": "Termin Uji", "jenis": "sewa",
        "tanggal_mulai": "2026-01-01", "nilai": 120_000_000,
        "skema_bayar": "termin", "jumlah_termin": 4, "termin_hari": 90})
    termin = kt.termin(kt2)
    cek("Empat termin dibuat", len(termin) == 4, f"dapat {len(termin)}")
    total_termin = sum(t["nilai"] for t in termin)
    cek("Total termin sama dengan nilai kontrak",
        total_termin == 120_000_000, f"dapat {total_termin}")
    cek("Termin punya jatuh tempo", all(t["jatuh_tempo"] for t in termin))
    if termin:
        kt.tandai_termin_dibayar(termin[0]["id"])
        t0 = kt.termin(kt2)[0]
        cek("Termin dapat ditandai dibayar", t0["dibayar"] == 1)

    # ------------------------------------------------------- pajak
    h_sewa = kt.hitung_pajak(100_000_000, "sewa", "uang")
    cek("Sewa kena PPh 4(2) 10%",
        h_sewa["pph_pasal"] == "PPh Pasal 4(2)" and h_sewa["pph"] == 10_000_000,
        f"dapat {h_sewa['pph']}")

    h_jasa = kt.hitung_pajak(50_000_000, "jasa", "uang")
    cek("Jasa kena PPh 23 2%",
        h_jasa["pph_pasal"] == "PPh Pasal 23" and h_jasa["pph"] == 1_000_000,
        f"dapat {h_jasa['pph']}")

    h_ppn = kt.hitung_pajak(10_000_000, "jasa", "uang", kena_ppn=True)
    cek("PPN dihitung saat dipilih", h_ppn["ppn"] == 1_100_000,
        f"dapat {h_ppn['ppn']}")

    h_barter = kt.hitung_pajak(50_000_000, "kerja_sama", "barang")
    cek("Barter tidak dipotong PPh", h_barter["pph"] == 0)

    # -------------------------------------------------- dasar hukum
    d_mou = kt.dasar_hukum("mou", "uang")
    cek("Dasar hukum MoU menyebut KUHPerdata", "KUHPerdata" in d_mou)
    d_barang = kt.dasar_hukum("kerja_sama", "barang")
    cek("Dasar hukum barter menyebut tukar menukar",
        "tukar menukar" in d_barang.lower() or "Tukar menukar" in d_barang)
    cek("Dasar hukum barter menyebut PPN", "PPN" in d_barang)

    # ------------------------------------------------------ daftar
    daftar = kt.daftar(cid)
    cek("Daftar mengembalikan semua kontrak", len(daftar) == 4,
        f"dapat {len(daftar)}")
    cek("Daftar memuat kolom kondisi", daftar and "kondisi" in daftar[0])

    cari = kt.daftar(cid, cari="Barter")
    cek("Pencarian menyaring hasil", len(cari) == 1, f"dapat {len(cari)}")

    per_jenis = kt.daftar(cid, jenis="sewa")
    cek("Penyaringan jenis bekerja", len(per_jenis) == 1,
        f"dapat {len(per_jenis)}")

    # ---------------------------------------------------- ringkasan
    r = kt.ringkasan(cid)
    cek("Ringkasan menghitung jumlah", r["jumlah"] == 4, f"dapat {r['jumlah']}")
    cek("Ringkasan menghitung nilai", r["total_nilai"] == 255_000_000,
        f"dapat {r['total_nilai']}")
    # Kontrak yang masa berlakunya sudah lewat tidak boleh ikut terhitung
    # aktif, supaya kartu Aktif dan Sudah Berakhir tidak saling bertentangan.
    cek("Kontrak aktif dan berakhir saling melengkapi",
        r["aktif"] + r["sudah_berakhir"] == r["jumlah"],
        f"{r['aktif']} + {r['sudah_berakhir']} != {r['jumlah']}")

    # ------------------------------------------------------ hapus
    kt.hapus(kt2, cid)
    cek("Kontrak terhapus dari daftar", len(kt.daftar(cid)) == 3,
        f"dapat {len(kt.daftar(cid))}")

    # ----------------------------------------------------- dokumen
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "kontrak.txt"
        p.write_text(
            "NOTA KESEPAHAMAN\nNomor: 077/MOU/UJI/2026\n\n"
            "Perjanjian mulai berlaku pada 5 April 2026 dan berakhir pada "
            "31 Desember 2026.\n\nNilai kerja sama Rp150.000.000.", encoding="utf-8")
        teks = kt.baca_dokumen(str(p))
        cek("Dokumen TXT terbaca", len(teks) > 50, f"dapat {len(teks)}")

        hasil = kt.urai_teks(teks)
        cek("Nomor terbaca dari dokumen",
            hasil.get("nomor") == "077/MOU/UJI/2026", f"dapat {hasil.get('nomor')!r}")
        cek("Jenis MoU terdeteksi", hasil.get("jenis") == "mou",
            f"dapat {hasil.get('jenis')!r}")
        cek("Tanggal mulai terbaca", hasil.get("tanggal_mulai") == "2026-04-05",
            f"dapat {hasil.get('tanggal_mulai')!r}")
        cek("Tanggal akhir terbaca", hasil.get("tanggal_akhir") == "2026-12-31",
            f"dapat {hasil.get('tanggal_akhir')!r}")
        cek("Nilai terbaca", hasil.get("nilai") == 150_000_000,
            f"dapat {hasil.get('nilai')!r}")
        cek("Dasar hukum ikut disarankan", bool(hasil.get("dasar_hukum")))

    print()
    print(f"LULUS: {lulus}   GAGAL: {gagal}")
    return 1 if gagal else 0


if __name__ == "__main__":
    sys.exit(main())
