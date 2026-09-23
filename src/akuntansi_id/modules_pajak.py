"""Fitur pajak lanjutan: faktur pajak, uang muka, meterai, PBJT, kurs, PPh 15.

Cara pakai:
    from akuntansi_id import modules_pajak as P
    P.buat_uang_muka(cid, "diterima", "2026-03-01", 50_000_000, partner_id=pel)

Modul ini melengkapi modul penjualan/pembelian dengan hal-hal yang sering
diminta saat pemeriksaan pajak: nomor seri faktur pajak, uang muka, bea
meterai, pajak daerah, kurs valuta asing, dan PPh Pasal 15.
"""

from __future__ import annotations

from typing import Optional

from . import config, db, services
from .core import accounting as acc
from .core import tax_engine as tx
from .modules import catat_riwayat, hari_ini, nomor_berikut


# ==========================================================================
# NOMOR SERI FAKTUR PAJAK (NSFP)
# ==========================================================================
def tambah_nsfp(company_id: int, tahun: int, nomor_awal: str,
                nomor_akhir: str, catatan: str = "") -> int:
    """Catat rentang NSFP yang diberikan DJP kepada PKP."""
    if not nomor_awal.strip() or not nomor_akhir.strip():
        raise ValueError("Nomor awal dan akhir wajib diisi.")
    awal = _angka_seri(nomor_awal)
    akhir = _angka_seri(nomor_akhir)
    if akhir < awal:
        raise ValueError("Nomor akhir tidak boleh lebih kecil dari nomor awal.")

    with db.tx() as conn:
        cur = conn.execute(
            """INSERT INTO nsfp(company_id, tahun, nomor_awal, nomor_akhir,
               terpakai, catatan) VALUES(?,?,?,?,?,?)""",
            (company_id, int(tahun), nomor_awal.strip(), nomor_akhir.strip(),
             0, catatan.strip()))
        nsfp_id = cur.lastrowid
    catat_riwayat(company_id, "nsfp", nsfp_id, "create", None, "", "", "",
                  f"NSFP {nomor_awal}-{nomor_akhir}")
    return nsfp_id


def _angka_seri(teks: str) -> int:
    """Ambil bagian angka dari nomor seri, mis. '010.000-26.00000001'."""
    angka = "".join(c for c in str(teks) if c.isdigit())
    return int(angka) if angka else 0


def daftar_nsfp(company_id: int, tahun: Optional[int] = None) -> list:
    sql = "SELECT * FROM nsfp WHERE company_id=?"
    p = [company_id]
    if tahun:
        sql += " AND tahun=?"
        p.append(tahun)
    sql += " ORDER BY tahun DESC, id DESC"
    return db.q(sql, p)


def nsfp_tersedia(company_id: int, tahun: int) -> int:
    """Sisa nomor seri yang belum dipakai pada tahun tersebut."""
    total = int(db.scalar(
        """SELECT COALESCE(SUM(1 + CAST(
               (LENGTH(REPLACE(REPLACE(nomor_akhir,'.',''),'-','')) -
                LENGTH(REPLACE(REPLACE(nomor_awal,'.',''),'-',''))) AS INTEGER)),0)
           FROM nsfp WHERE company_id=? AND tahun=?""", (company_id, tahun),
        default=0))
    terpakai = int(db.scalar(
        "SELECT COUNT(*) FROM faktur_pajak WHERE company_id=? AND "
        "jenis='keluaran' AND deleted_at IS NULL AND substr(tanggal,1,4)=?",
        (company_id, str(tahun)), default=0))
    return max(0, total - terpakai)


def hapus_nsfp(nsfp_id: int, oleh: str = "") -> None:
    row = db.q1("SELECT company_id FROM nsfp WHERE id=?", (nsfp_id,))
    if row is None:
        raise ValueError("NSFP tidak ditemukan.")
    db.ex("DELETE FROM nsfp WHERE id=?", (nsfp_id,))
    catat_riwayat(row["company_id"], "nsfp", nsfp_id, "delete", None, oleh,
                  "", "", "NSFP dihapus")


# ==========================================================================
# FAKTUR PAJAK (KELUARAN & MASUKAN)
# ==========================================================================
def buat_faktur_pajak(company_id: int, jenis: str, tanggal: str,
                      lawan_nama: str, dpp: int, ppn: int = None,
                      lawan_npwp: str = "", nomor_seri: str = "",
                      status: str = "normal", faktur_diganti: str = "",
                      invoice_id: Optional[int] = None,
                      bill_id: Optional[int] = None,
                      keterangan: str = "", user_id=None,
                      username: str = "") -> int:
    """Catat faktur pajak keluaran atau masukan."""
    if jenis not in ("keluaran", "masukan"):
        raise ValueError("Jenis faktur pajak harus keluaran atau masukan.")
    if status not in ("normal", "pengganti", "batal"):
        raise ValueError("Status faktur harus normal, pengganti, atau batal.")
    dpp = int(round(float(dpp or 0)))
    if dpp <= 0:
        raise ValueError("DPP harus lebih besar dari nol.")
    if ppn is None:
        ppn = int(round(dpp * config.RATE_VAT_EFFECTIVE_NORMAL))
    ppn = int(round(float(ppn or 0)))

    if jenis == "keluaran" and status == "normal" and not nomor_seri.strip():
        nomor_seri = _nomor_seri_berikut(company_id, tanggal)

    with db.tx() as conn:
        cur = conn.execute(
            """INSERT INTO faktur_pajak(company_id, jenis, nomor_seri, tanggal,
               lawan_nama, lawan_npwp, dpp, ppn, status, faktur_diganti,
               invoice_id, bill_id, keterangan)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (company_id, jenis, nomor_seri.strip(), tanggal, lawan_nama.strip(),
             lawan_npwp.strip(), dpp, ppn, status, faktur_diganti.strip(),
             invoice_id, bill_id, keterangan.strip()))
        fp_id = cur.lastrowid
    catat_riwayat(company_id, "faktur_pajak", fp_id, "create", user_id,
                  username, "", "", f"Faktur pajak {jenis} {nomor_seri}")
    return fp_id


def _nomor_seri_berikut(company_id: int, tanggal: str) -> str:
    """Ambil nomor seri berikutnya dari rentang NSFP yang tersedia."""
    tahun = int(tanggal[:4])
    baris = db.q(
        "SELECT * FROM nsfp WHERE company_id=? AND tahun=? ORDER BY id",
        (company_id, tahun))
    if not baris:
        return ""

    dipakai = {r["nomor_seri"] for r in db.q(
        "SELECT nomor_seri FROM faktur_pajak WHERE company_id=? AND "
        "jenis='keluaran' AND deleted_at IS NULL AND substr(tanggal,1,4)=?",
        (company_id, str(tahun)))}

    for n in baris:
        awal = _angka_seri(n["nomor_awal"])
        akhir = _angka_seri(n["nomor_akhir"])
        for nomor in range(awal, akhir + 1):
            teks = str(nomor).zfill(len("".join(
                c for c in n["nomor_awal"] if c.isdigit())))
            if teks not in dipakai:
                return teks
    return ""


def daftar_faktur_pajak(company_id: int, jenis: str = "",
                        tahun: Optional[int] = None) -> list:
    sql = """SELECT * FROM faktur_pajak WHERE company_id=?
             AND deleted_at IS NULL"""
    p = [company_id]
    if jenis:
        sql += " AND jenis=?"
        p.append(jenis)
    if tahun:
        sql += " AND substr(tanggal,1,4)=?"
        p.append(str(tahun))
    sql += " ORDER BY tanggal DESC, id DESC"
    return db.q(sql, p)


def hapus_faktur_pajak(fp_id: int, oleh: str = "") -> None:
    row = db.q1("SELECT company_id FROM faktur_pajak WHERE id=?", (fp_id,))
    if row is None:
        raise ValueError("Faktur pajak tidak ditemukan.")
    db.ex("UPDATE faktur_pajak SET deleted_at=datetime('now','localtime') "
          "WHERE id=?", (fp_id,))
    catat_riwayat(row["company_id"], "faktur_pajak", fp_id, "delete", None,
                  oleh, "", "", "Faktur pajak dihapus")


def rekap_faktur_pajak(company_id: int, tahun: int) -> dict:
    """Ringkasan faktur pajak setahun: jumlah dan total PPN per jenis."""
    hasil = {}
    for jenis in ("keluaran", "masukan"):
        baris = daftar_faktur_pajak(company_id, jenis, tahun)
        aktif = [b for b in baris if b["status"] != "batal"]
        hasil[jenis] = {
            "jumlah": len(aktif),
            "dpp": sum(int(b["dpp"] or 0) for b in aktif),
            "ppn": sum(int(b["ppn"] or 0) for b in aktif),
        }
    hasil["selisih_ppn"] = hasil["keluaran"]["ppn"] - hasil["masukan"]["ppn"]
    return hasil


# ==========================================================================
# UANG MUKA / PANJAR (DP)
# ==========================================================================
def buat_uang_muka(company_id: int, jenis: str, tanggal: str, jumlah: int,
                   partner_id: Optional[int] = None, nama_lawan: str = "",
                   akun_kas: str = "1001", akun_uang_muka: str = "",
                   keterangan: str = "", buat_jurnal: bool = True,
                   user_id=None, username: str = "") -> int:
    """
    Catat uang muka diterima dari pelanggan atau dibayar ke pemasok.

    Uang muka diterima menambah kas dan menambah kewajiban (utang uang muka);
    uang muka dibayar mengurangi kas dan menambah aset (piutang uang muka).
    """
    if jenis not in ("diterima", "dibayar"):
        raise ValueError("Jenis uang muka harus diterima atau dibayar.")
    jumlah = int(round(float(jumlah or 0)))
    if jumlah <= 0:
        raise ValueError("Jumlah uang muka harus lebih besar dari nol.")

    mitra = db.q1("SELECT * FROM partners WHERE id=?", (partner_id,)) \
        if partner_id else None
    nama = nama_lawan.strip() or (mitra["nama"] if mitra else "Tanpa Nama")

    if not akun_uang_muka:
        akun_uang_muka = _akun_uang_muka(company_id, jenis)

    nomor = nomor_berikut(company_id, "DP")
    with db.tx() as conn:
        cur = conn.execute(
            """INSERT INTO uang_muka(company_id, jenis, nomor, tanggal,
               partner_id, nama_lawan, jumlah, terpakai, akun_kas,
               akun_uang_muka, keterangan)
               VALUES(?,?,?,?,?,?,?,0,?,?,?)""",
            (company_id, jenis, nomor, tanggal, partner_id, nama, jumlah,
             akun_kas, akun_uang_muka, keterangan.strip()))
        um_id = cur.lastrowid

    if buat_jurnal:
        if jenis == "diterima":
            baris = [
                {"kode_akun": akun_kas, "debit": jumlah, "kredit": 0,
                 "catatan": f"Uang muka diterima {nomor}"},
                {"kode_akun": akun_uang_muka, "debit": 0, "kredit": jumlah,
                 "catatan": f"Uang muka dari {nama}"},
            ]
        else:
            baris = [
                {"kode_akun": akun_uang_muka, "debit": jumlah, "kredit": 0,
                 "catatan": f"Uang muka dibayar {nomor}"},
                {"kode_akun": akun_kas, "debit": 0, "kredit": jumlah,
                 "catatan": f"Uang muka ke {nama}"},
            ]
        acc.simpan_jurnal(company_id, tanggal, nomor,
                          f"Uang muka {'diterima dari' if jenis == 'diterima' else 'dibayar ke'} {nama}",
                          baris, sumber="penyesuaian", user_id=user_id)

    catat_riwayat(company_id, "uang_muka", um_id, "create", user_id, username,
                  "", "", f"{nomor} - {nama}")
    return um_id


def _akun_uang_muka(company_id: int, jenis: str) -> str:
    """
    Akun uang muka: aset bila dibayar lebih dulu, kewajiban bila diterima.
    Memakai akun bawaan bagan akun agar langsung masuk neraca.
    """
    kode = "1111" if jenis == "dibayar" else "2011"
    if db.q1("SELECT kode FROM accounts WHERE company_id=? AND kode=?",
             (company_id, kode)):
        return kode

    if jenis == "dibayar":
        services.create_account(
            company_id, kode, "Uang Muka Pembelian", "Aset", "",
            "Aset Lancar Lain", "Debit", "Deductible/Taxable",
            "Uang muka yang dibayarkan ke pemasok sebelum barang diterima.",
            0, True)
    else:
        services.create_account(
            company_id, kode, "Uang Muka Pelanggan", "Liabilitas", "",
            "Utang Usaha", "Kredit", "Deductible/Taxable",
            "Uang muka yang diterima dari pelanggan sebelum barang dikirim.",
            0, True)
    return kode


def daftar_uang_muka(company_id: int, jenis: str = "",
                     hanya_sisa: bool = False) -> list:
    sql = """SELECT * FROM uang_muka WHERE company_id=? AND deleted_at IS NULL"""
    p = [company_id]
    if jenis:
        sql += " AND jenis=?"
        p.append(jenis)
    if hanya_sisa:
        sql += " AND (jumlah - terpakai) > 0"
    sql += " ORDER BY tanggal DESC, id DESC"
    return db.q(sql, p)


def pakai_uang_muka(um_id: int, tanggal: str, jumlah: int,
                    invoice_id: Optional[int] = None,
                    bill_id: Optional[int] = None, user_id=None) -> int:
    """Pakai uang muka untuk melunasi sebagian atau seluruh invoice/bill."""
    um = db.q1("SELECT * FROM uang_muka WHERE id=?", (um_id,))
    if um is None:
        raise ValueError("Uang muka tidak ditemukan.")
    sisa = int(um["jumlah"] or 0) - int(um["terpakai"] or 0)
    jumlah = int(round(float(jumlah or 0)))
    if jumlah <= 0:
        raise ValueError("Jumlah pemakaian harus lebih besar dari nol.")
    if jumlah > sisa:
        raise ValueError(f"Jumlah melebihi sisa uang muka ({sisa:,}).")
    if not invoice_id and not bill_id:
        raise ValueError("Pilih invoice atau bill yang dilunasi.")

    with db.tx() as conn:
        cur = conn.execute(
            """INSERT INTO uang_muka_pakai(uang_muka_id, invoice_id, bill_id,
               jumlah, tanggal) VALUES(?,?,?,?,?)""",
            (um_id, invoice_id, bill_id, jumlah, tanggal))
        pakai_id = cur.lastrowid
        conn.execute("UPDATE uang_muka SET terpakai=terpakai+? WHERE id=?",
                     (jumlah, um_id))

    # jurnal: uang muka berkurang, piutang/utang berkurang
    um2 = db.q1("SELECT * FROM uang_muka WHERE id=?", (um_id,))
    if um2["jenis"] == "diterima":
        baris = [
            {"kode_akun": um2["akun_uang_muka"], "debit": jumlah, "kredit": 0,
             "catatan": "Uang muka dipakai"},
            {"kode_akun": "1101", "debit": 0, "kredit": jumlah,
             "catatan": "Pelunasan piutang dengan uang muka"},
        ]
    else:
        baris = [
            {"kode_akun": "2101", "debit": jumlah, "kredit": 0,
             "catatan": "Pelunasan utang dengan uang muka"},
            {"kode_akun": um2["akun_uang_muka"], "debit": 0, "kredit": jumlah,
             "catatan": "Uang muka dipakai"},
        ]
    acc.simpan_jurnal(um2["company_id"], tanggal, f"DP-PAKAI-{um_id}",
                      f"Pemakaian uang muka {um2['nomor']}", baris,
                      sumber="penyesuaian", user_id=user_id)
    return pakai_id


def hapus_uang_muka(um_id: int, oleh: str = "") -> None:
    row = db.q1("SELECT company_id, terpakai FROM uang_muka WHERE id=?",
                (um_id,))
    if row is None:
        raise ValueError("Uang muka tidak ditemukan.")
    if int(row["terpakai"] or 0) > 0:
        raise ValueError("Uang muka sudah dipakai sehingga tidak dapat dihapus.")
    db.ex("UPDATE uang_muka SET deleted_at=datetime('now','localtime') "
          "WHERE id=?", (um_id,))
    catat_riwayat(row["company_id"], "uang_muka", um_id, "delete", None, oleh,
                  "", "", "Uang muka dihapus")


# ==========================================================================
# BEA METERAI
# ==========================================================================
def catat_meterai(company_id: int, tanggal: str, dokumen: str,
                  nilai_dokumen: int, jumlah_berkas: int = 1,
                  akun_beban: str = "6023", keterangan: str = "",
                  buat_jurnal: bool = True, user_id=None) -> int:
    """Catat bea meterai atas dokumen dan bebankan ke biaya."""
    hasil = tx.hitung_meterai(nilai_dokumen, jumlah_berkas)
    if not hasil["kena"]:
        raise ValueError(hasil["keterangan"])

    with db.tx() as conn:
        cur = conn.execute(
            """INSERT INTO bea_meterai(company_id, tanggal, dokumen,
               nilai_dokumen, jumlah_berkas, tarif, total, akun_beban,
               keterangan) VALUES(?,?,?,?,?,?,?,?,?)""",
            (company_id, tanggal, dokumen.strip(), hasil["nilai_dokumen"],
             hasil["jumlah_berkas"], hasil["per_berkas"], hasil["total"],
             akun_beban, keterangan.strip()))
        meterai_id = cur.lastrowid

    if buat_jurnal:
        baris = [
            {"kode_akun": akun_beban, "debit": hasil["total"], "kredit": 0,
             "catatan": f"Bea meterai {dokumen}"},
            {"kode_akun": "1001", "debit": 0, "kredit": hasil["total"],
             "catatan": "Pembelian meterai"},
        ]
        acc.simpan_jurnal(company_id, tanggal, f"MTR-{meterai_id}",
                          f"Bea meterai {dokumen}", baris,
                          sumber="penyesuaian", user_id=user_id)
    return meterai_id


def daftar_meterai(company_id: int, tahun: Optional[int] = None) -> list:
    sql = "SELECT * FROM bea_meterai WHERE company_id=? AND deleted_at IS NULL"
    p = [company_id]
    if tahun:
        sql += " AND substr(tanggal,1,4)=?"
        p.append(str(tahun))
    sql += " ORDER BY tanggal DESC, id DESC"
    return db.q(sql, p)


def hapus_meterai(meterai_id: int) -> None:
    db.ex("UPDATE bea_meterai SET deleted_at=datetime('now','localtime') "
          "WHERE id=?", (meterai_id,))


# ==========================================================================
# PAJAK DAERAH (PBJT)
# ==========================================================================
def catat_pajak_daerah(company_id: int, jenis: str, tanggal: str, dpp: int,
                       tarif_persen: float = None, invoice_id: Optional[int] = None,
                       keterangan: str = "", user_id=None) -> int:
    """Catat pajak daerah yang dipungut atas penjualan."""
    hasil = tx.hitung_pbjt(jenis, dpp, tarif_persen)
    with db.tx() as conn:
        cur = conn.execute(
            """INSERT INTO pajak_daerah(company_id, jenis, tanggal, dpp, tarif,
               pajak, invoice_id, keterangan) VALUES(?,?,?,?,?,?,?,?)""",
            (company_id, jenis, tanggal, hasil["dpp"], hasil["tarif"],
             hasil["pajak"], invoice_id, keterangan.strip()))
        pd_id = cur.lastrowid

    # jurnal: kas bertambah, utang pajak daerah bertambah
    baris = [
        {"kode_akun": "1001", "debit": hasil["pajak"], "kredit": 0,
         "catatan": f"Pungutan {hasil['nama']}"},
        {"kode_akun": "2101", "debit": 0, "kredit": hasil["pajak"],
         "catatan": f"Utang {hasil['nama']}"},
    ]
    acc.simpan_jurnal(company_id, tanggal, f"PBJT-{pd_id}",
                      f"Pajak daerah {hasil['nama']}", baris,
                      sumber="penyesuaian", user_id=user_id)
    return pd_id


def daftar_pajak_daerah(company_id: int, tahun: Optional[int] = None) -> list:
    sql = """SELECT * FROM pajak_daerah WHERE company_id=?
             AND deleted_at IS NULL"""
    p = [company_id]
    if tahun:
        sql += " AND substr(tanggal,1,4)=?"
        p.append(str(tahun))
    sql += " ORDER BY tanggal DESC, id DESC"
    return db.q(sql, p)


def hapus_pajak_daerah(pd_id: int) -> None:
    db.ex("UPDATE pajak_daerah SET deleted_at=datetime('now','localtime') "
          "WHERE id=?", (pd_id,))


# ==========================================================================
# KURS MATA UANG ASING
# ==========================================================================
def set_kurs(company_id: int, mata_uang: str, tanggal: str, kurs: float,
             keterangan: str = "") -> int:
    """Simpan kurs mata uang asing pada tanggal tertentu."""
    kode = (mata_uang or "").upper()
    if kode not in config.MATA_UANG:
        raise ValueError(f"Mata uang {kode} belum didukung.")
    if kode == "IDR":
        raise ValueError("Kurs rupiah selalu 1.")
    if float(kurs) <= 0:
        raise ValueError("Kurs harus lebih besar dari nol.")

    with db.tx() as conn:
        conn.execute(
            """INSERT INTO kurs(company_id, mata_uang, tanggal, kurs, keterangan)
               VALUES(?,?,?,?,?)
               ON CONFLICT(company_id, mata_uang, tanggal)
               DO UPDATE SET kurs=excluded.kurs, keterangan=excluded.keterangan""",
            (company_id, kode, tanggal, float(kurs), keterangan.strip()))
        row = db.q1("SELECT id FROM kurs WHERE company_id=? AND mata_uang=? "
                    "AND tanggal=?", (company_id, kode, tanggal))
    return row["id"] if row else 0


def kurs_terakhir(company_id: int, mata_uang: str,
                  tanggal: str = "") -> float:
    """Kurs terbaru sebelum atau pada tanggal tersebut."""
    kode = (mata_uang or "").upper()
    if kode == "IDR":
        return 1.0
    tanggal = tanggal or hari_ini()
    row = db.q1(
        """SELECT kurs FROM kurs WHERE company_id=? AND mata_uang=?
           AND tanggal<=? ORDER BY tanggal DESC LIMIT 1""",
        (company_id, kode, tanggal))
    if row:
        return float(row["kurs"])
    return float(config.KURS_CONTOH.get(kode, 0))


def daftar_kurs(company_id: int, mata_uang: str = "") -> list:
    sql = "SELECT * FROM kurs WHERE company_id=?"
    p = [company_id]
    if mata_uang:
        sql += " AND mata_uang=?"
        p.append(mata_uang.upper())
    sql += " ORDER BY tanggal DESC, mata_uang"
    return db.q(sql, p)


# ==========================================================================
# PPh PASAL 15
# ==========================================================================
def catat_pph15(company_id: int, jenis: str, tanggal: str,
                peredaran_bruto: int, keterangan: str = "",
                buat_jurnal: bool = True, user_id=None) -> int:
    """Catat PPh Pasal 15 atas peredaran bruto pelayaran/penerbangan."""
    hasil = tx.hitung_pph15(jenis, peredaran_bruto)
    with db.tx() as conn:
        cur = conn.execute(
            """INSERT INTO pph15(company_id, jenis, tanggal, peredaran_bruto,
               tarif, pph, keterangan) VALUES(?,?,?,?,?,?,?)""",
            (company_id, jenis, tanggal, hasil["peredaran_bruto"],
             hasil["tarif"], hasil["pph_terutang"], keterangan.strip()))
        pph_id = cur.lastrowid

    if buat_jurnal and hasil["pph_terutang"] > 0:
        baris = [
            {"kode_akun": "6023", "debit": hasil["pph_terutang"], "kredit": 0,
             "catatan": f"PPh 15 {hasil['nama']}"},
            {"kode_akun": "2005", "debit": 0, "kredit": hasil["pph_terutang"],
             "catatan": "Utang PPh 15"},
        ]
        acc.simpan_jurnal(company_id, tanggal, f"PPH15-{pph_id}",
                          f"PPh Pasal 15 {hasil['nama']}", baris,
                          sumber="penyesuaian", user_id=user_id)
    return pph_id


def daftar_pph15(company_id: int, tahun: Optional[int] = None) -> list:
    sql = "SELECT * FROM pph15 WHERE company_id=? AND deleted_at IS NULL"
    p = [company_id]
    if tahun:
        sql += " AND substr(tanggal,1,4)=?"
        p.append(str(tahun))
    sql += " ORDER BY tanggal DESC, id DESC"
    return db.q(sql, p)


def hapus_pph15(pph_id: int) -> None:
    db.ex("UPDATE pph15 SET deleted_at=datetime('now','localtime') WHERE id=?",
          (pph_id,))


# ==========================================================================
# JURNAL BALIK (REVERSING ENTRY)
# ==========================================================================
def tandai_jurnal_balik(company_id: int, entry_id: int, tanggal_balik: str,
                        keterangan: str = "", user_id=None) -> int:
    """Tandai jurnal akrual agar dibalik otomatis pada tanggal tertentu."""
    entry = db.q1("SELECT * FROM journal_entries WHERE id=? AND company_id=?",
                  (entry_id, company_id))
    if entry is None:
        raise ValueError("Jurnal tidak ditemukan.")
    if not tanggal_balik:
        raise ValueError("Tanggal balik wajib diisi.")

    with db.tx() as conn:
        cur = conn.execute(
            """INSERT INTO jurnal_balik(company_id, entry_id, tanggal_balik,
               keterangan) VALUES(?,?,?,?)""",
            (company_id, entry_id, tanggal_balik, keterangan.strip()))
        jb_id = cur.lastrowid
    return jb_id


def daftar_jurnal_balik(company_id: int, belum_saja: bool = True) -> list:
    sql = """SELECT jb.*, je.no_bukti, je.tanggal AS tanggal_asli,
                    je.keterangan AS ket_asli
             FROM jurnal_balik jb
             JOIN journal_entries je ON je.id = jb.entry_id
             WHERE jb.company_id=?"""
    if belum_saja:
        sql += " AND jb.sudah_dibuat=0"
    sql += " ORDER BY jb.tanggal_balik"
    return db.q(sql, (company_id,))


def jalankan_jurnal_balik(company_id: int, user_id=None) -> dict:
    """
    Buat jurnal balik untuk semua akrual yang tanggal baliknya sudah tiba.
    Jurnal balik membalik debit dan kredit agar beban akrual tidak dihitung
    dua kali pada periode berikutnya.
    """
    daftar = daftar_jurnal_balik(company_id, belum_saja=True)
    hari = hari_ini()
    dibuat, dilewati = 0, 0
    for jb in daftar:
        if (jb["tanggal_balik"] or "") > hari:
            dilewati += 1
            continue

        baris_asli = db.q(
            "SELECT kode_akun, debit, kredit, catatan FROM journal_lines "
            "WHERE entry_id=?", (jb["entry_id"],))
        if not baris_asli:
            continue

        # balik: debit menjadi kredit dan sebaliknya
        baris = [{"kode_akun": b["kode_akun"], "debit": b["kredit"],
                  "kredit": b["debit"],
                  "catatan": f"Balik: {b['catatan'] or ''}".strip()}
                 for b in baris_asli]
        entry_id = acc.simpan_jurnal(
            company_id, jb["tanggal_balik"], f"RB-{jb['id']}",
            f"Jurnal balik {jb['no_bukti'] or ''}".strip(), baris,
            sumber="penyesuaian", user_id=user_id)
        db.ex("UPDATE jurnal_balik SET sudah_dibuat=1, entry_balik_id=? "
              "WHERE id=?", (entry_id, jb["id"]))
        dibuat += 1
    return {"dibuat": dibuat, "dilewati": dilewati}
