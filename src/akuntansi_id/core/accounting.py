"""
AkunTuntas - Mesin Akuntansi (General Ledger & Laporan Keuangan)
=================================================================
Mengimplementasikan siklus akuntansi lengkap:
  jurnal  buku besar  neraca saldo  laporan keuangan  arus kas

Semua laporan diturunkan dari SATU sumber: tabel journal_lines.
Ini menjamin konsistensi antar laporan (tidak ada angka yang berbeda).

Dasar: PSAK 1 (penyajian laporan keuangan), PSAK 2 (arus kas),
       SAK EMKM (entitas mikro, kecil, menengah).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional

from .. import config, db
from . import tax_engine as tx


# ==========================================================================
# PERIODE
# ==========================================================================
def periode(tahun: int, bulan: Optional[int] = None) -> tuple[str, str]:
    """Kembalikan (tanggal_awal, tanggal_akhir) dalam format ISO."""
    if bulan is None:
        return f"{tahun}-01-01", f"{tahun}-12-31"
    if bulan == 12:
        return f"{tahun}-12-01", f"{tahun}-12-31"
    nxt = date(tahun, bulan + 1, 1)
    akhir = date.fromordinal(nxt.toordinal() - 1)
    return f"{tahun}-{bulan:02d}-01", akhir.isoformat()


def tanggal_sah(teks) -> tuple[bool, str]:
    """
    Periksa apakah teks berupa tanggal yang benar benar ada.

    Yang diperiksa bukan hanya bentuknya, tetapi juga apakah tanggalnya
    ada pada kalender. Tanggal seperti 2026-02-30 atau bulan 13 berbentuk
    benar tetapi tidak pernah ada. Bila lolos, entri jurnalnya tidak akan
    muncul pada laporan periode mana pun, sehingga angkanya hilang dari
    laporan tanpa ada yang menyadari.

    Mengembalikan (sah, alasan). Alasan berisi keterangan yang dapat
    ditampilkan kepada pengguna.
    """
    if teks is None:
        return False, "Tanggal wajib diisi."

    bersih = str(teks).strip()
    if not bersih:
        return False, "Tanggal wajib diisi."

    # Hanya bentuk YYYY-MM-DD yang diterima, supaya urutannya benar saat
    # dibandingkan di dalam basis data.
    if len(bersih) != 10 or bersih[4] != "-" or bersih[7] != "-":
        return False, ("Tanggal harus ditulis dengan bentuk YYYY-MM-DD, "
                       "misalnya 2026-01-31.")

    bagian = bersih.split("-")
    if not all(b.isdigit() and len(b) == n
               for b, n in zip(bagian, (4, 2, 2))):
        return False, ("Tanggal harus berupa angka dengan bentuk "
                       "YYYY-MM-DD, misalnya 2026-01-31.")

    try:
        date(int(bagian[0]), int(bagian[1]), int(bagian[2]))
    except ValueError:
        return False, (f"Tanggal {bersih} tidak ada pada kalender. "
                       "Periksa kembali bulan dan harinya.")

    return True, ""


# ==========================================================================
# VALIDASI JURNAL (DOUBLE-ENTRY)
# ==========================================================================
@dataclass
class ValidasiJurnal:
    valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    total_debit: int = 0
    total_kredit: int = 0
    selisih: int = 0


def validasi_jurnal(baris: list[dict],
                    company_id: Optional[int] = None) -> ValidasiJurnal:
    """
    Periksa kaidah double-entry sebelum menyimpan jurnal.

    Aturan yang diperiksa:
      1. Minimal 2 baris
      2. Setiap baris punya akun yang terdaftar
      3. Setiap baris hanya debit ATAU kredit (tidak keduanya, tidak nol)
      4. Total debit = total kredit
      5. Nilai bulat rupiah (tidak ada pecahan sen)

    Bila company_id diberikan, kode akun diperiksa terhadap bagan akun
    perusahaan itu. Tanpa pemeriksaan tersebut, jurnal dengan kode akun
    yang tidak dikenal tetap tersimpan, dan barisnya muncul tanpa nama akun
    di buku besar maupun laporan. Data seperti itu sulit dilacak asalnya
    karena tidak terhubung ke akun mana pun.
    """
    v = ValidasiJurnal()
    if len(baris) < 2:
        v.errors.append("Jurnal harus memiliki minimal 2 baris (satu debit, satu kredit).")

    # Daftar kode akun yang benar benar terdaftar, dibaca sekali saja.
    kode_dikenal: set[str] | None = None
    if company_id:
        try:
            kode_dikenal = {
                r["kode"] for r in db.q(
                    "SELECT kode FROM accounts WHERE company_id = ?",
                    (company_id,))
            }
        except Exception:
            # Bila daftar akun tidak dapat dibaca, pemeriksaan ini dilewati
            # supaya jurnal tidak tertolak hanya karena gangguan pembacaan.
            kode_dikenal = None

    for i, b in enumerate(baris, start=1):
        d = int(b.get("debit", 0) or 0)
        k = int(b.get("kredit", 0) or 0)
        if d == 0 and k == 0:
            v.errors.append(f"Baris {i}: nilai debit dan kredit keduanya nol.")
        if d > 0 and k > 0:
            v.errors.append(f"Baris {i}: tidak boleh mengisi debit dan kredit sekaligus.")
        if d < 0 or k < 0:
            v.errors.append(f"Baris {i}: nilai tidak boleh negatif. "
                            "Untuk mengurangi, tukar posisi debit/kredit.")
        kode = b.get("kode_akun")
        if not kode:
            v.errors.append(f"Baris {i}: akun belum dipilih.")
        elif kode_dikenal is not None and kode not in kode_dikenal:
            v.errors.append(
                f"Baris {i}: kode akun {kode} tidak ada pada bagan akun. "
                "Periksa kembali kode akunnya, atau tambahkan akun itu lebih "
                "dulu pada halaman Bagan Akun.")
        v.total_debit += d
        v.total_kredit += k

    v.selisih = v.total_debit - v.total_kredit
    if v.selisih != 0:
        v.errors.append(
            f"Jurnal TIDAK SEIMBANG. Total debit {tx.rupiah(v.total_debit)} "
            f"≠ total kredit {tx.rupiah(v.total_kredit)} "
            f"(selisih {tx.rupiah(abs(v.selisih))})."
        )
    v.valid = not v.errors
    return v


# ==========================================================================
# POSTING JURNAL
# ==========================================================================
def simpan_jurnal(company_id: int, tanggal: str, no_bukti: str, keterangan: str,
                  baris: list[dict], sumber: str = "manual",
                  ref_id: Optional[int] = None, user_id: Optional[int] = None,
                  validasi: bool = True) -> int:
    """Simpan satu bukti jurnal beserta barisnya secara atomik."""
    if validasi:
        # Pemeriksaan menyertakan kecocokan kode akun dengan bagan akun
        # perusahaan ini, supaya jurnal dengan akun tidak dikenal tertolak
        # sebelum tersimpan.
        v = validasi_jurnal(baris, company_id)
        if not v.valid:
            raise ValueError("\n".join(v.errors))

        # Tanggal diperiksa terpisah, karena tidak termasuk kaidah
        # double-entry. Entri bertanggal tidak sah tidak akan muncul pada
        # laporan periode mana pun, sehingga angkanya hilang tanpa jejak.
        sah, alasan = tanggal_sah(tanggal)
        if not sah:
            raise ValueError(alasan)

    with db.tx() as conn:
        cur = conn.execute(
            "INSERT INTO journal_entries(company_id, tanggal, no_bukti, keterangan, "
            "sumber, ref_id, created_by) VALUES(?,?,?,?,?,?,?)",
            (company_id, tanggal, no_bukti, keterangan, sumber, ref_id, user_id),
        )
        entry_id = cur.lastrowid
        for b in baris:
            kode = b["kode_akun"]
            akun = db.q1("SELECT nama FROM accounts WHERE company_id=? AND kode=?",
                         (company_id, kode))
            conn.execute(
                "INSERT INTO journal_lines(entry_id, company_id, kode_akun, nama_akun, "
                "debit, kredit, lawan_transaksi, npwp_nik, ref_pajak, catatan) "
                "VALUES(?,?,?,?,?,?,?,?,?,?)",
                (entry_id, company_id, kode, akun["nama"] if akun else b.get("nama_akun", ""),
                 int(b.get("debit", 0) or 0), int(b.get("kredit", 0) or 0),
                 b.get("lawan_transaksi", ""), b.get("npwp_nik", ""),
                 b.get("ref_pajak", ""), b.get("catatan", "")),
            )
    db.log_action(user_id, "", company_id, "journal.create", "journal_entries",
                  entry_id, f"{no_bukti}: {keterangan[:100]}")
    return entry_id


def hapus_jurnal(entry_id: int, user_id: Optional[int] = None) -> None:
    row = db.q1("SELECT company_id, no_bukti FROM journal_entries WHERE id=?", (entry_id,))
    with db.tx() as conn:
        conn.execute("DELETE FROM journal_lines WHERE entry_id=?", (entry_id,))
        conn.execute("DELETE FROM journal_entries WHERE id=?", (entry_id,))
    if row:
        db.log_action(user_id, "", row["company_id"], "journal.delete", "journal_entries",
                      entry_id, row["no_bukti"])


def nomor_bukti_berikut(company_id: int, prefix: str = "JU") -> str:
    """Buat nomor bukti berurutan, mis. JU-2026-0007."""
    tahun = datetime.now().year
    pola = f"{prefix}-{tahun}-%"
    n = int(db.scalar(
        "SELECT COUNT(*) FROM journal_entries WHERE company_id=? AND no_bukti LIKE ?",
        (company_id, pola),
    ))
    # hindari tabrakan bila ada penghapusan
    while True:
        kandidat = f"{prefix}-{tahun}-{n + 1:04d}"
        if not db.q1("SELECT 1 FROM journal_entries WHERE company_id=? AND no_bukti=?",
                     (company_id, kandidat)):
            return kandidat
        n += 1


# ==========================================================================
# NERACA SALDO
# ==========================================================================
@dataclass
class BarisNeracaSaldo:
    kode: str
    nama: str
    tipe: str
    grup_lr: str
    baris_neraca: str
    normal: str
    perlakuan_fiskal: str
    saldo_awal: int
    debit: int
    kredit: int
    saldo_akhir: int
    saldo_akhir_normal: int


def neraca_saldo(company_id: int, tahun: int, bulan: Optional[int] = None,
                 sampai_tanggal: Optional[str] = None) -> list[BarisNeracaSaldo]:
    """
    Neraca saldo per akun.
    saldo_akhir selalu dinyatakan pada sisi normal akun (selalu positif bila wajar).
    """
    awal, akhir = periode(tahun, bulan)
    batas = sampai_tanggal or akhir

    rows = db.q(
        """
        SELECT a.kode, a.nama, a.tipe, a.grup_lr, a.baris_neraca, a.normal,
               a.perlakuan_fiskal, a.saldo_awal,
               COALESCE(SUM(CASE WHEN jl.debit  > 0 THEN jl.debit  ELSE 0 END),0) AS d,
               COALESCE(SUM(CASE WHEN jl.kredit > 0 THEN jl.kredit ELSE 0 END),0) AS k
        FROM accounts a
        LEFT JOIN journal_entries je ON je.company_id = a.company_id
             AND je.tanggal BETWEEN ? AND ?
        LEFT JOIN journal_lines jl ON jl.entry_id = je.id AND jl.kode_akun = a.kode
        WHERE a.company_id = ? AND a.is_active = 1
        GROUP BY a.kode
        ORDER BY a.kode
        """,
        (awal, batas, company_id),
    )

    hasil: list[BarisNeracaSaldo] = []
    for r in rows:
        # saldo_awal disimpan sebagai nilai POSITIF pada sisi normal akun.
        # Untuk akun bersaldo normal Kredit, nilai itu harus diperlakukan
        # sebagai saldo kredit — bukan debit.
        if r["normal"] == "Kredit":
            saldo_awal_bertanda = -r["saldo_awal"]   # dalam konvensi debit-positif
        else:
            saldo_awal_bertanda = r["saldo_awal"]

        net = saldo_awal_bertanda + r["d"] - r["k"]   # bertanda: + = debit
        saldo_normal = (-net) if r["normal"] == "Kredit" else net

        hasil.append(BarisNeracaSaldo(
            kode=r["kode"], nama=r["nama"], tipe=r["tipe"], grup_lr=r["grup_lr"] or "",
            baris_neraca=r["baris_neraca"] or "", normal=r["normal"],
            perlakuan_fiskal=r["perlakuan_fiskal"],
            saldo_awal=r["saldo_awal"], debit=r["d"], kredit=r["k"],
            saldo_akhir=net, saldo_akhir_normal=saldo_normal,
        ))
    return hasil


def total_neraca_saldo(company_id: int, tahun: int, bulan: Optional[int] = None) -> dict:
    """Total debit & kredit untuk kontrol keseimbangan."""
    awal, akhir = periode(tahun, bulan)
    row = db.q1(
        """
        SELECT COALESCE(SUM(jl.debit),0) AS d, COALESCE(SUM(jl.kredit),0) AS k
        FROM journal_lines jl
        JOIN journal_entries je ON je.id = jl.entry_id
        WHERE jl.company_id = ? AND je.tanggal BETWEEN ? AND ?
        """,
        (company_id, awal, akhir),
    )
    d, k = (row["d"], row["k"]) if row else (0, 0)
    return {"debit": d, "kredit": k, "selisih": d - k, "seimbang": d == k}


def cek_jurnal_tidak_seimbang(company_id: int) -> list[dict]:
    """Cari nomor bukti yang tidak seimbang (harusnya kosong)."""
    rows = db.q(
        """
        SELECT je.no_bukti, je.tanggal, je.keterangan,
               SUM(jl.debit) AS d, SUM(jl.kredit) AS k
        FROM journal_entries je
        JOIN journal_lines jl ON jl.entry_id = je.id
        WHERE je.company_id = ?
        GROUP BY je.id
        HAVING ABS(SUM(jl.debit) - SUM(jl.kredit)) > 0.5
        """,
        (company_id,),
    )
    return [dict(r) for r in rows]


# ==========================================================================
# LABA RUGI
# ==========================================================================
@dataclass
class LabaRugi:
    pendapatan_usaha: int = 0
    hpp: int = 0
    laba_kotor: int = 0
    beban_operasional: int = 0
    laba_operasional: int = 0
    pendapatan_lain: int = 0
    beban_lain: int = 0
    laba_sebelum_pajak: int = 0
    beban_pajak: int = 0
    laba_bersih: int = 0
    margin_kotor: float = 0.0
    margin_operasional: float = 0.0
    margin_bersih: float = 0.0
    rincian_beban: list = field(default_factory=list)
    rincian_pendapatan: list = field(default_factory=list)


def _nilai_bertanda(b: BarisNeracaSaldo) -> int:
    """
    Nilai akun dengan tanda yang benar untuk penyajian laporan.

    Akun KONTRA (saldo normal berlawanan dengan tipe-nya) mengurangi kelompoknya:
      • Akumulasi Penyusutan (Aset, normal Kredit)   mengurangi aset
      • Retur & Potongan Penjualan (Pendapatan, normal Debit)  mengurangi pendapatan
      • Prive / Dividen (Ekuitas, normal Debit)      mengurangi ekuitas
      • Cadangan Kerugian Piutang (Aset, normal Kredit)  mengurangi piutang
    """
    normal_diharapkan = {
        "Aset": "Debit",
        "Beban": "Debit",
        "Liabilitas": "Kredit",
        "Ekuitas": "Kredit",
        "Pendapatan": "Kredit",
    }.get(b.tipe, "Debit")

    if b.normal == normal_diharapkan:
        return b.saldo_akhir_normal
    return -b.saldo_akhir_normal


def laba_rugi(company_id: int, tahun: int, bulan: Optional[int] = None,
              beban_pajak: Optional[int] = None) -> LabaRugi:
    """
    Laporan Laba Rugi bertahap (multiple-step) sesuai SAK EMKM/PSAK 1.
    """
    ns = neraca_saldo(company_id, tahun, bulan)
    lr = LabaRugi()

    def total_grup(nama_grup: str, tipe: str) -> int:
        return sum(_nilai_bertanda(b) for b in ns
                   if b.grup_lr == nama_grup and b.tipe == tipe)

    lr.pendapatan_usaha = total_grup("Pendapatan Usaha", "Pendapatan")
    lr.hpp = total_grup("HPP", "Beban")
    lr.laba_kotor = lr.pendapatan_usaha - lr.hpp
    lr.beban_operasional = total_grup("Beban Operasional", "Beban")
    lr.laba_operasional = lr.laba_kotor - lr.beban_operasional
    lr.pendapatan_lain = total_grup("Pendapatan Lain", "Pendapatan")
    lr.beban_lain = total_grup("Beban Lain", "Beban")
    lr.laba_sebelum_pajak = lr.laba_operasional + lr.pendapatan_lain - lr.beban_lain

    if beban_pajak is None:
        beban_pajak = estimasi_beban_pajak(company_id, tahun, lr.laba_sebelum_pajak)
    lr.beban_pajak = beban_pajak
    lr.laba_bersih = lr.laba_sebelum_pajak - lr.beban_pajak

    dasar = lr.pendapatan_usaha or 1
    lr.margin_kotor = lr.laba_kotor / dasar if lr.pendapatan_usaha else 0.0
    lr.margin_operasional = lr.laba_operasional / dasar if lr.pendapatan_usaha else 0.0
    lr.margin_bersih = lr.laba_bersih / dasar if lr.pendapatan_usaha else 0.0

    lr.rincian_beban = [
        (b.kode, b.nama, b.saldo_akhir_normal)
        for b in ns if b.tipe == "Beban" and b.saldo_akhir_normal != 0
    ]
    lr.rincian_pendapatan = [
        (b.kode, b.nama, b.saldo_akhir_normal)
        for b in ns if b.tipe == "Pendapatan" and b.saldo_akhir_normal != 0
    ]
    return lr


def estimasi_beban_pajak(company_id: int, tahun: int, laba_sebelum_pajak: int) -> int:
    """
    Estimasi beban pajak kini untuk Laba Rugi.
    Memakai skema pajak yang dipilih pada data perusahaan.
    """
    if laba_sebelum_pajak <= 0:
        return 0
    comp = db.q1("SELECT * FROM companies WHERE id=?", (company_id,))
    if comp is None:
        return 0
    omzet = omzet_setahun(company_id, tahun)

    if comp["skema_pph"] == "final_umkm" and comp["final_eligible"]:
        r = tx.hitung_pph_final_umkm(
            omzet_setahun=omzet,
            bentuk_badan=comp["bentuk"],
            final_eligible_dikonfirmasi=True,
        )
        return r.pph_final if r.layak else 0

    r = tx.hitung_pph_badan(omzet=omzet, pkp=tx.round_down_thousand(laba_sebelum_pajak))
    return r.pph_terutang


def omzet_setahun(company_id: int, tahun: int, bulan: Optional[int] = None) -> int:
    """Peredaran bruto = total pendapatan usaha (sebelum pajak final dikeluarkan)."""
    awal, akhir = periode(tahun, bulan)
    return int(db.scalar(
        """
        SELECT COALESCE(SUM(jl.kredit - jl.debit), 0)
        FROM journal_lines jl
        JOIN journal_entries je ON je.id = jl.entry_id
        JOIN accounts a ON a.company_id = jl.company_id AND a.kode = jl.kode_akun
        WHERE jl.company_id = ? AND je.tanggal BETWEEN ? AND ?
          AND a.grup_lr = 'Pendapatan Usaha'
        """,
        (company_id, awal, akhir),
    ))


def omzet_bulanan(company_id: int, tahun: int) -> list[int]:
    """Peredaran bruto per bulan (untuk pemantauan batas PKP)."""
    hasil = []
    for b in range(1, 13):
        hasil.append(omzet_setahun(company_id, tahun, b))
    return hasil


# ==========================================================================
# NERACA
# ==========================================================================
@dataclass
class Neraca:
    aset_lancar: dict = field(default_factory=dict)
    aset_tetap: dict = field(default_factory=dict)
    aset_lain: dict = field(default_factory=dict)
    total_aset_lancar: int = 0
    total_aset_tetap: int = 0
    total_aset_lain: int = 0
    total_aset: int = 0
    liabilitas_pendek: dict = field(default_factory=dict)
    liabilitas_panjang: dict = field(default_factory=dict)
    total_liabilitas_pendek: int = 0
    total_liabilitas_panjang: int = 0
    total_liabilitas: int = 0
    modal: int = 0
    saldo_laba: int = 0
    laba_tahun_berjalan: int = 0
    prive: int = 0
    total_ekuitas: int = 0
    total_liabilitas_ekuitas: int = 0
    selisih: int = 0
    seimbang: bool = False


def neraca(company_id: int, tahun: int, bulan: Optional[int] = None) -> Neraca:
    """
    Laporan Posisi Keuangan.
    Mengikuti persamaan: ASET = LIABILITAS + EKUITAS
    """
    ns = neraca_saldo(company_id, tahun, bulan)
    n = Neraca()

    def grup(baris: str, tipe: str) -> dict:
        return {b.kode: (b.nama, _nilai_bertanda(b))
                for b in ns if b.baris_neraca == baris and b.tipe == tipe}

    n.aset_lancar = grup("Kas & Bank", "Aset")
    n.aset_lancar.update(grup("Piutang Usaha", "Aset"))
    n.aset_lancar.update(grup("Persediaan", "Aset"))
    n.aset_lancar.update(grup("Aset Lancar Lain", "Aset"))
    n.aset_tetap = grup("Aset Tetap", "Aset")
    n.aset_tetap.update(grup("Akumulasi Penyusutan", "Aset"))
    n.aset_lain = grup("Aset Lain", "Aset")

    n.total_aset_lancar = sum(v for _, v in n.aset_lancar.values())
    n.total_aset_tetap = sum(v for _, v in n.aset_tetap.values())
    n.total_aset_lain = sum(v for _, v in n.aset_lain.values())
    n.total_aset = n.total_aset_lancar + n.total_aset_tetap + n.total_aset_lain

    n.liabilitas_pendek = grup("Utang Usaha", "Liabilitas")
    n.liabilitas_pendek.update(grup("Utang Pajak", "Liabilitas"))
    n.liabilitas_pendek.update(grup("Pinjaman Jangka Pendek", "Liabilitas"))
    n.liabilitas_panjang = grup("Pinjaman Jangka Panjang", "Liabilitas")

    n.total_liabilitas_pendek = sum(v for _, v in n.liabilitas_pendek.values())
    n.total_liabilitas_panjang = sum(v for _, v in n.liabilitas_panjang.values())
    n.total_liabilitas = n.total_liabilitas_pendek + n.total_liabilitas_panjang

    n.modal = sum(_nilai_bertanda(b) for b in ns if b.baris_neraca == "Modal")
    n.saldo_laba = sum(_nilai_bertanda(b) for b in ns if b.baris_neraca == "Saldo Laba")
    # Prive & Dividen bersaldo normal Debit pada tipe Ekuitas  bernilai negatif
    n.prive = -sum(_nilai_bertanda(b) for b in ns
                   if b.baris_neraca in ("Prive", "Dividen"))

    # Laba tahun berjalan pada neraca memakai laba SEBELUM pajak (komersial).
    # Alasannya: beban pajak kini baru mengurangi ekuitas SETELAH jurnal akrual
    # pajak dibuat (debit beban pajak, kredit utang pajak). Bila memakai laba
    # setelah pajak sementara utang pajaknya belum dicatat, neraca akan pincang.
    # Setelah jurnal akrual dibuat, kedua sisi tetap seimbang.
    n.laba_tahun_berjalan = laba_rugi(company_id, tahun, bulan, beban_pajak=0).laba_sebelum_pajak

    n.total_ekuitas = n.modal + n.saldo_laba + n.laba_tahun_berjalan - n.prive
    n.total_liabilitas_ekuitas = n.total_liabilitas + n.total_ekuitas
    n.selisih = n.total_aset - n.total_liabilitas_ekuitas
    n.seimbang = abs(n.selisih) < 1
    return n


# ==========================================================================
# ARUS KAS (METODE LANGSUNG - dari pergerakan kas)
# ==========================================================================
@dataclass
class ArusKas:
    operasi_masuk: list = field(default_factory=list)
    operasi_keluar: list = field(default_factory=list)
    total_operasi: int = 0
    investasi_masuk: list = field(default_factory=list)
    investasi_keluar: list = field(default_factory=list)
    total_investasi: int = 0
    pendanaan_masuk: list = field(default_factory=list)
    pendanaan_keluar: list = field(default_factory=list)
    total_pendanaan: int = 0
    kenaikan_kas: int = 0
    kas_awal: int = 0
    kas_akhir: int = 0
    selisih: int = 0
    seimbang: bool = False


def arus_kas(company_id: int, tahun: int, bulan: Optional[int] = None) -> ArusKas:
    """
    Laporan Arus Kas metode langsung (PSAK 2 / SAK EMKM).

    Logika: untuk setiap jurnal yang menyentuh akun kas/bank, lihat akun
    lawannya. Bila lawan = akun laba rugi  aktivitas operasi; bila lawan =
    aset tetap  investasi; bila lawan = liabilitas jangka panjang/modal 
    pendanaan.
    """
    awal, akhir = periode(tahun, bulan)
    ak = ArusKas()

    akun_kas = [r["kode"] for r in db.q(
        "SELECT kode FROM accounts WHERE company_id=? AND is_kas_bank=1", (company_id,))]
    if not akun_kas:
        akun_kas = ["1001", "1002", "1003", "1004", "1005"]

    tempat = ",".join("?" * len(akun_kas))
    entries = db.q(
        f"""
        SELECT DISTINCT je.id, je.tanggal, je.no_bukti, je.keterangan
        FROM journal_entries je
        JOIN journal_lines jl ON jl.entry_id = je.id
        WHERE je.company_id = ? AND je.tanggal BETWEEN ? AND ?
          AND jl.kode_akun IN ({tempat})
        ORDER BY je.tanggal, je.id
        """,
        (company_id, awal, akhir, *akun_kas),
    )

    kas_masuk = 0
    kas_keluar = 0
    for e in entries:
        lines = db.q(
            "SELECT jl.kode_akun, jl.nama_akun, jl.debit, jl.kredit "
            "FROM journal_lines jl WHERE jl.entry_id=?", (e["id"],))
        net_kas = 0
        lawan: list = []
        for l in lines:
            if l["kode_akun"] in akun_kas:
                net_kas += l["debit"] - l["kredit"]
            else:
                lawan.append(l)

        if net_kas == 0 or not lawan:
            continue

        # Klasifikasi berdasarkan akun lawan utama (nilai terbesar)
        lawan_utama = max(lawan, key=lambda x: abs(x["debit"] - x["kredit"]))
        info = db.q1(
            "SELECT tipe, baris_neraca, grup_lr FROM accounts "
            "WHERE company_id=? AND kode=?", (company_id, lawan_utama["kode_akun"]))
        tipe = info["tipe"] if info else ""
        baris = (info["baris_neraca"] if info else "") or ""
        grup = (info["grup_lr"] if info else "") or ""

        if baris in ("Aset Tetap", "Akumulasi Penyusutan", "Aset Lain"):
            kategori = "investasi"
        elif baris in ("Modal", "Pinjaman Jangka Panjang", "Pinjaman Jangka Pendek",
                       "Dividen", "Prive", "Saldo Laba"):
            kategori = "pendanaan"
        elif tipe in ("Pendapatan", "Beban") or grup:
            kategori = "operasi"
        else:
            kategori = "operasi"

        label = f"{e['no_bukti']} - {lawan_utama['nama_akun'] or lawan_utama['kode_akun']}"
        nilai = abs(net_kas)
        arah_masuk = net_kas > 0

        if kategori == "operasi":
            if arah_masuk:
                ak.operasi_masuk.append((label, nilai))
                kas_masuk += nilai
            else:
                ak.operasi_keluar.append((label, nilai))
                kas_keluar += nilai
        elif kategori == "investasi":
            (ak.investasi_masuk if arah_masuk else ak.investasi_keluar).append((label, nilai))
        else:
            (ak.pendanaan_masuk if arah_masuk else ak.pendanaan_keluar).append((label, nilai))

    ak.total_operasi = sum(v for _, v in ak.operasi_masuk) - sum(v for _, v in ak.operasi_keluar)
    ak.total_investasi = sum(v for _, v in ak.investasi_masuk) - sum(v for _, v in ak.investasi_keluar)
    ak.total_pendanaan = sum(v for _, v in ak.pendanaan_masuk) - sum(v for _, v in ak.pendanaan_keluar)
    ak.kenaikan_kas = ak.total_operasi + ak.total_investasi + ak.total_pendanaan

    kas_awal_row = db.q1(
        f"""SELECT COALESCE(SUM(jl.debit - jl.kredit),0) AS s
            FROM journal_lines jl JOIN journal_entries je ON je.id = jl.entry_id
            WHERE jl.company_id=? AND je.tanggal < ? AND jl.kode_akun IN ({tempat})""",
        (company_id, awal, *akun_kas))
    saldo_awal_akun = db.scalar(
        f"SELECT COALESCE(SUM(saldo_awal),0) FROM accounts "
        f"WHERE company_id=? AND kode IN ({tempat})", (company_id, *akun_kas))
    ak.kas_awal = int(saldo_awal_akun) + int(kas_awal_row["s"] if kas_awal_row else 0)

    kas_akhir_row = db.q1(
        f"""SELECT COALESCE(SUM(jl.debit - jl.kredit),0) AS s
            FROM journal_lines jl JOIN journal_entries je ON je.id = jl.entry_id
            WHERE jl.company_id=? AND je.tanggal <= ? AND jl.kode_akun IN ({tempat})""",
        (company_id, akhir, *akun_kas))
    ak.kas_akhir = int(saldo_awal_akun) + int(kas_akhir_row["s"] if kas_akhir_row else 0)
    ak.selisih = ak.kas_akhir - (ak.kas_awal + ak.kenaikan_kas)
    ak.seimbang = abs(ak.selisih) < 1
    return ak


# ==========================================================================
# LAPORAN PERUBAHAN EKUITAS
# ==========================================================================
def perubahan_ekuitas(company_id: int, tahun: int) -> list[dict]:
    """
    Laporan Perubahan Ekuitas (PSAK 1).
    Menjelaskan pergerakan modal, laba, dan dividen/prive selama periode.
    """
    awal, akhir = periode(tahun)
    baris: list[dict] = []

    # Saldo awal akun Modal & Saldo Laba (nilai positif pada sisi normal Kredit)
    modal_awal = int(db.scalar(
        "SELECT COALESCE(SUM(saldo_awal),0) FROM accounts "
        "WHERE company_id=? AND baris_neraca='Modal'", (company_id,)))
    saldo_laba_awal = int(db.scalar(
        "SELECT COALESCE(SUM(saldo_awal),0) FROM accounts "
        "WHERE company_id=? AND baris_neraca='Saldo Laba'", (company_id,)))

    setoran = -db.scalar(
        """SELECT COALESCE(SUM(jl.debit - jl.kredit),0) FROM journal_lines jl
           JOIN journal_entries je ON je.id=jl.entry_id
           JOIN accounts a ON a.company_id=jl.company_id AND a.kode=jl.kode_akun
           WHERE jl.company_id=? AND je.tanggal BETWEEN ? AND ? AND a.baris_neraca='Modal'""",
        (company_id, awal, akhir))
    dividen = db.scalar(
        """SELECT COALESCE(SUM(jl.debit - jl.kredit),0) FROM journal_lines jl
           JOIN journal_entries je ON je.id=jl.entry_id
           JOIN accounts a ON a.company_id=jl.company_id AND a.kode=jl.kode_akun
           WHERE jl.company_id=? AND je.tanggal BETWEEN ? AND ? AND a.baris_neraca='Dividen'""",
        (company_id, awal, akhir))
    prive = db.scalar(
        """SELECT COALESCE(SUM(jl.debit - jl.kredit),0) FROM journal_lines jl
           JOIN journal_entries je ON je.id=jl.entry_id
           JOIN accounts a ON a.company_id=jl.company_id AND a.kode=jl.kode_akun
           WHERE jl.company_id=? AND je.tanggal BETWEEN ? AND ? AND a.baris_neraca='Prive'""",
        (company_id, awal, akhir))

    laba = laba_rugi(company_id, tahun).laba_bersih

    baris = [
        {"uraian": "Saldo awal tahun - Modal", "nilai": modal_awal},
        {"uraian": "Saldo awal tahun - Saldo Laba", "nilai": saldo_laba_awal},
        {"uraian": "Setoran modal selama periode", "nilai": setoran},
        {"uraian": "Laba bersih periode berjalan", "nilai": laba},
        {"uraian": "Dividen dibagikan", "nilai": -dividen},
        {"uraian": "Prive (penarikan pemilik)", "nilai": -prive},
    ]
    baris.append({
        "uraian": "SALDO AKHIR EKUITAS",
        "nilai": modal_awal + saldo_laba_awal + setoran + laba - dividen - prive,
        "tebal": True,
    })
    return baris


# ==========================================================================
# RINGKASAN BULANAN
# ==========================================================================
def ringkasan_bulanan(company_id: int, tahun: int) -> list[dict]:
    """Kinerja per bulan: pendapatan, HPP, beban, laba, pajak dibayar."""
    hasil = []
    for b in range(1, 13):
        lr = laba_rugi(company_id, tahun, b, beban_pajak=0)
        pajak_dibayar = int(db.scalar(
            "SELECT COALESCE(SUM(jumlah),0) FROM tax_payments "
            "WHERE company_id=? AND masa=?",
            (company_id, f"{tahun}-{b:02d}")))
        ppn_net = int(db.scalar(
            """SELECT COALESCE(SUM(CASE WHEN a.kode='2003' OR a.kode='2101'
                        THEN jl.kredit - jl.debit ELSE 0 END),0)
               FROM journal_lines jl JOIN journal_entries je ON je.id=jl.entry_id
               JOIN accounts a ON a.company_id=jl.company_id AND a.kode=jl.kode_akun
               WHERE jl.company_id=? AND je.tanggal BETWEEN ? AND ?""",
            (company_id, f"{tahun}-{b:02d}-01", periode(tahun, b)[1])))
        hasil.append({
            "bulan": b,
            "nama": config.MONTH_NAMES_ID[b - 1],
            "pendapatan": lr.pendapatan_usaha,
            "hpp": lr.hpp,
            "laba_kotor": lr.laba_kotor,
            "beban": lr.beban_operasional,
            "laba_operasional": lr.laba_operasional,
            "pendapatan_lain": lr.pendapatan_lain,
            "beban_lain": lr.beban_lain,
            "laba_sebelum_pajak": lr.laba_sebelum_pajak,
            "pajak_dibayar": pajak_dibayar,
            "ppn_net": ppn_net,
        })
    return hasil


# ==========================================================================
# REKAP PPN
# ==========================================================================
def rekap_ppn_bulanan(company_id: int, tahun: int) -> list[dict]:
    """PPN keluaran, masukan, dan kurang/lebih bayar per masa pajak.

    Sumbernya tabel invoice dan bill - di situlah transaksi penjualan dan
    pembelian sebenarnya dicatat, lengkap dengan PPN-nya.
    """
    hasil = []
    for b in range(1, 13):
        awal, akhir = periode(tahun, b)
        keluaran = int(db.scalar(
            "SELECT COALESCE(SUM(ppn),0) FROM invoices "
            "WHERE company_id=? AND deleted_at IS NULL AND status != 'batal' "
            "AND tanggal BETWEEN ? AND ?",
            (company_id, awal, akhir)))
        masukan = int(db.scalar(
            "SELECT COALESCE(SUM(ppn),0) FROM bills "
            "WHERE company_id=? AND deleted_at IS NULL AND status != 'batal' "
            "AND tanggal BETWEEN ? AND ?",
            (company_id, awal, akhir)))
        dibayar = int(db.scalar(
            "SELECT COALESCE(SUM(jumlah),0) FROM tax_payments "
            "WHERE company_id=? AND jenis_pajak='PPN' AND masa=?",
            (company_id, f"{tahun}-{b:02d}")))
        r = tx.rekap_ppn(keluaran, masukan)
        r.update({"bulan": b, "nama": config.MONTH_NAMES_ID[b - 1],
                  "dibayar": dibayar, "sisa": r["kurang_bayar"] - dibayar})
        hasil.append(r)
    return hasil


# ==========================================================================
# BUKU BESAR
# ==========================================================================
def buku_besar(company_id: int, kode_akun: str, tahun: int,
               bulan: Optional[int] = None) -> list[dict]:
    """
    Riwayat mutasi satu akun dengan saldo berjalan.

    Saldo dinyatakan pada sisi normal akun, sama seperti pada neraca saldo.
    Akun bersaldo normal kredit, misalnya pendapatan dan utang, karena itu
    menunjukkan saldo positif saat bertambah. Tanpa penyesuaian ini, akun
    pendapatan menampilkan saldo negatif meskipun usahanya memperoleh
    pendapatan, sehingga angkanya sulit dibaca dan tampak seperti kerugian.
    """
    awal, akhir = periode(tahun, bulan)
    akun = db.q1("SELECT * FROM accounts WHERE company_id=? AND kode=?",
                 (company_id, kode_akun))
    if akun is None:
        return []

    # Saldo awal disimpan sebagai nilai positif pada sisi normal akun.
    # Untuk akun bersaldo normal kredit, nilainya harus dibalik lebih dulu
    # supaya penambahan berikutnya menghitung ke arah yang benar.
    def ke_net(nilai: int) -> int:
        return -nilai if akun["normal"] == "Kredit" else nilai

    def ke_normal(nilai: int) -> int:
        return -nilai if akun["normal"] == "Kredit" else nilai

    saldo_net = ke_net(akun["saldo_awal"])
    baris = [{
        "tanggal": awal, "no_bukti": "", "keterangan": "SALDO AWAL",
        "debit": 0, "kredit": 0, "saldo": ke_normal(saldo_net),
        "saldo_net": saldo_net, "awal": True,
    }]

    rows = db.q(
        """SELECT je.tanggal, je.no_bukti, je.keterangan, jl.debit, jl.kredit
           FROM journal_lines jl JOIN journal_entries je ON je.id=jl.entry_id
           WHERE jl.company_id=? AND jl.kode_akun=? AND je.tanggal BETWEEN ? AND ?
           ORDER BY je.tanggal, je.id""",
        (company_id, kode_akun, awal, akhir))

    for r in rows:
        saldo_net += r["debit"] - r["kredit"]
        baris.append({
            "tanggal": r["tanggal"], "no_bukti": r["no_bukti"],
            "keterangan": r["keterangan"], "debit": r["debit"],
            "kredit": r["kredit"], "saldo": ke_normal(saldo_net),
            "saldo_net": saldo_net, "awal": False,
        })
    return baris


# ==========================================================================
# JURNAL PENUTUP
# ==========================================================================
def buat_jurnal_penutup(company_id: int, tahun: int,
                        user_id: Optional[int] = None) -> Optional[int]:
    """
    Jurnal penutup: menutup akun pendapatan & beban ke Saldo Laba.
    Dijalankan setelah tutup buku tahun berjalan.
    """
    if db.q1("SELECT 1 FROM journal_entries WHERE company_id=? AND sumber='penutup' "
             "AND tanggal BETWEEN ? AND ?", (company_id, f"{tahun}-01-01", f"{tahun}-12-31")):
        raise ValueError(f"Jurnal penutup tahun {tahun} sudah pernah dibuat.")

    ns = neraca_saldo(company_id, tahun)
    baris: list[dict] = []
    for b in ns:
        if b.tipe in ("Pendapatan", "Beban") and b.saldo_akhir_normal != 0:
            if b.tipe == "Pendapatan":
                baris.append({"kode_akun": b.kode, "debit": b.saldo_akhir_normal,
                              "kredit": 0, "catatan": f"Menutup {b.nama}"})
            else:
                baris.append({"kode_akun": b.kode, "debit": 0,
                              "kredit": b.saldo_akhir_normal,
                              "catatan": f"Menutup {b.nama}"})
    if not baris:
        raise ValueError("Tidak ada akun pendapatan/beban bersaldo untuk ditutup.")

    laba = laba_rugi(company_id, tahun, beban_pajak=0).laba_sebelum_pajak
    akun_laba = db.q1("SELECT kode FROM accounts WHERE company_id=? "
                      "AND baris_neraca='Saldo Laba' LIMIT 1", (company_id,))
    # Bila akun Saldo Laba tidak ditemukan, dipakai akun Laba Tahun Berjalan
    # yang selalu ada pada bagan akun bawaan. Sebelumnya di sini tertulis
    # kode 3101 yang tidak ada pada bagan akun, sehingga jurnal penutup
    # gagal disimpan tepat pada keadaan yang paling membutuhkannya.
    kode_laba = akun_laba["kode"] if akun_laba else "3007"
    if laba >= 0:
        baris.append({"kode_akun": kode_laba, "debit": 0, "kredit": laba,
                      "catatan": "Laba periode berjalan dipindahkan ke Saldo Laba"})
    else:
        baris.append({"kode_akun": kode_laba, "debit": -laba, "kredit": 0,
                      "catatan": "Rugi periode berjalan dipindahkan ke Saldo Laba"})

    entry_id = simpan_jurnal(
        company_id, f"{tahun}-12-31", f"JP-{tahun}", f"Jurnal Penutup Tahun {tahun}",
        baris, sumber="penutup", user_id=user_id)
    return entry_id


# ==========================================================================
# DASHBOARD / KPI
# ==========================================================================
@dataclass
class _PphSederhana:
    """Hasil ringkas perhitungan PPh untuk kartu dashboard.

    Dipakai agar dashboard dapat menampilkan skema pajak yang benar untuk
    bentuk badan usaha apa pun tanpa bergantung pada satu jenis hasil.
    """

    skema: str
    pph_terutang: int


def _pph_pasal17_op(pkp: int) -> int:
    """
    Hitung PPh Orang Pribadi dengan tarif berlapis Pasal 17 UU HPP.

    Lapisan tarif: 5% sampai Rp60 juta, 15% sampai Rp250 juta, 25% sampai
    Rp500 juta, 30% sampai Rp5 miliar, dan 35% di atasnya.
    """
    lapisan = [
        (60_000_000, 0.05),
        (250_000_000, 0.15),
        (500_000_000, 0.25),
        (5_000_000_000, 0.30),
    ]
    pajak = 0
    sisa = max(0, pkp)
    batas_bawah = 0
    for batas_atas, tarif in lapisan:
        if sisa <= batas_bawah:
            break
        kena = min(sisa, batas_atas) - batas_bawah
        if kena > 0:
            pajak += int(round(kena * tarif))
        batas_bawah = batas_atas
    if sisa > batas_bawah:
        pajak += int(round((sisa - batas_bawah) * 0.35))
    return pajak


def dashboard_kpi(company_id: int, tahun: int, bulan: Optional[int] = None) -> dict:
    """
    Ringkasan angka kunci untuk dashboard.

    Skema pajak menyesuaikan bentuk badan usaha: orang pribadi memakai
    PPh Final UMKM atau tarif Pasal 17 Orang Pribadi, sedangkan badan
    memakai PPh Badan Pasal 31E. Menampilkan "Pasal 31E" pada usaha orang
    pribadi menyesatkan karena skema itu hanya berlaku untuk badan.
    """
    comp = db.q1("SELECT * FROM companies WHERE id=?",
                 (company_id,)) if company_id else None
    lr = laba_rugi(company_id, tahun, bulan)
    nr = neraca(company_id, tahun, bulan)
    omzet = omzet_setahun(company_id, tahun, bulan)
    pkp_status = tx.status_pkp(omzet, bool(comp["status_pkp"]) if comp else False)

    bentuk = comp["bentuk"] if comp else "umkm_op"
    badan = bentuk not in ("umkm_op",)

    kredit = int(db.scalar(
        "SELECT COALESCE(SUM(pajak),0) FROM tax_records "
        "WHERE company_id=? AND kredit_pph_badan=1 AND substr(tanggal,1,4)=?",
        (company_id, str(tahun))))

    if badan:
        pph = tx.hitung_pph_badan(omzet=omzet, pkp=max(0, lr.laba_sebelum_pajak),
                                  kredit_pajak=kredit)
    else:
        # Orang pribadi: PPh Final UMKM 0,5% bila layak; jika tidak, tarif
        # Pasal 17 dikenakan pada Penghasilan Kena Pajak.
        final = tx.hitung_pph_final_umkm(
            omzet, bentuk_badan=bentuk,
            final_eligible_dikonfirmasi=bool(comp["final_eligible"]) if comp else False,
            omzet_kumulatif_op=0)
        if final.layak:
            pph = _PphSederhana(
                skema="PPh Final UMKM 0,5%",
                pph_terutang=max(0, final.pph_final - kredit))
        else:
            pkp_op = max(0, lr.laba_sebelum_pajak)
            pajak = tx.hitung_pph_orang_pribadi_pasal17(pkp_op) \
                if hasattr(tx, "hitung_pph_orang_pribadi_pasal17") else None
            if pajak is None:
                # hitung bertingkat Pasal 17 untuk orang pribadi
                pajak = _pph_pasal17_op(pkp_op)
            pph = _PphSederhana(
                skema="PPh Orang Pribadi Pasal 17",
                pph_terutang=max(0, pajak - kredit))

    cek = total_neraca_saldo(company_id, tahun, bulan)
    akun_kas = {r["kode"] for r in db.q(
        "SELECT kode FROM accounts WHERE company_id=? AND is_kas_bank=1",
        (company_id,))}
    saldo_kas = sum(v for k, (_, v) in nr.aset_lancar.items() if k in akun_kas)

    return {
        "omzet": omzet,
        "laba_kotor": lr.laba_kotor,
        "laba_operasional": lr.laba_operasional,
        "laba_sebelum_pajak": lr.laba_sebelum_pajak,
        "laba_bersih": lr.laba_bersih,
        "margin_bersih": lr.margin_bersih,
        "margin_kotor": lr.margin_kotor,
        "total_aset": nr.total_aset,
        "total_liabilitas": nr.total_liabilitas,
        "total_ekuitas": nr.total_ekuitas,
        "kas": saldo_kas,
        "pph_terutang": pph.pph_terutang,
        "pph_skema": pph.skema,
        "selisih_neraca": nr.selisih,
        "selisih_jurnal": cek["selisih"],
        "status_pkp": pkp_status,
        "pkp_terpakai_persen": min(100.0, omzet / config.THRESHOLD_PKP * 100),
    }
