"""
Kontrak & Kerja Sama
====================

Pengelolaan perjanjian dengan mitra: nomor kontrak, masa berlaku, nilai,
bentuk imbalan (uang maupun barang/jasa), termin pembayaran, dan dasar
hukumnya.

Bentuk kerja sama yang didukung mencakup kerja sama non-tunai seperti barter
barang, tukar jasa, dan bagi hasil. Nilai barang pada barter tetap dicatat
karena secara fiskal penyerahan barang merupakan objek PPN dan PPh.

Dasar hukum yang disarankan otomatis mengikuti jenis dan bentuk imbalannya,
mengacu pada:
- KUHPerdata Pasal 1313, 1320, 1338 (perjanjian, syarat sah, kebebasan
  berkontrak dan pacta sunt servanda)
- KUHPerdata Pasal 1457 (jual beli) dan Pasal 1548 (sewa menyewa)
- UU 7/2014 Pasal 33-51 (perjanjian dagang, keagenan, waralaba, distributor)
- UU 13/2003 Pasal 50-66 jo. UU 6/2023 (perjanjian kerja dan alih daya)
- PP 35/2021 (PKWT, alih daya, waktu kerja)
- PMK 68/2022 (PPh Pasal 4(2) sewa tanah/bangunan)
- PMK 81/2024 dan PMK 131/2024 (PPh Pasal 23 jasa dan sewa)
- UU 42/2009 jo. UU 7/2021 Pasal 1A (PPN atas penyerahan barang/jasa)
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional

from . import db


JENIS_KONTRAK = {
    "kerja_sama": "Kerja Sama Usaha",
    "mou": "Nota Kesepahaman (MoU)",
    "jual_beli": "Jual Beli",
    "sewa": "Sewa Menyewa",
    "jasa": "Pemberian Jasa",
    "distributor": "Keagenan & Distributor",
    "waralaba": "Waralaba",
    "kerja": "Perjanjian Kerja",
    "alih_daya": "Alih Daya (Outsourcing)",
    "pinjam_pakai": "Pinjam Pakai",
    "bagi_hasil": "Bagi Hasil",
    "lainnya": "Lainnya",
}

BENTUK_IMBALAN = {
    "uang": "Uang",
    "barang": "Barang (Barter)",
    "jasa": "Jasa (Tukar Jasa)",
    "barang_jasa": "Barang dan Jasa",
    "bagi_hasil": "Bagi Hasil",
    "tanpa_imbalan": "Tanpa Imbalan",
}

STATUS_KONTRAK = {
    "draf": "Draf",
    "aktif": "Aktif",
    "selesai": "Selesai",
    "berakhir": "Berakhir",
    "dibatalkan": "Dibatalkan",
}

PERAN = {
    "pemberi": "Kita Pemberi",
    "penerima": "Kita Penerima",
    "setara": "Setara / Bersama",
}

SKEMA_BAYAR = {
    "lump_sum": "Sekaligus",
    "termin": "Bertahap (Termin)",
    "bulanan": "Bulanan",
    "bagi_hasil": "Bagi Hasil",
    "barter": "Tukar Barang/Jasa",
    "tanpa_bayar": "Tanpa Pembayaran",
}

# Dasar hukum per jenis kontrak, dipakai sebagai saran otomatis.
DASAR_HUKUM = {
    "kerja_sama": (
        "KUHPerdata Pasal 1313 dan Pasal 1338 (perjanjian dan asas kebebasan "
        "berkontrak); KUHPerdata Pasal 1320 (syarat sah perjanjian); "
        "UU 7/2014 Pasal 33-36 tentang perjanjian dagang."
    ),
    "mou": (
        "KUHPerdata Pasal 1313 dan Pasal 1320; MoU umumnya mengikat secara "
        "moral pada tahap penjajakan, dan mengikat penuh setelah ditindaklanjuti "
        "perjanjian definitif. Bila memuat hak dan kewajiban yang pasti, MoU "
        "dapat mengikat menurut Pasal 1338."
    ),
    "jual_beli": (
        "KUHPerdata Pasal 1457-1540 (jual beli), khususnya Pasal 1457 "
        "(pengertian) dan Pasal 1474 (kewajiban penjual); "
        "UU 42/2009 Pasal 4 dan Pasal 4A (PPN atas penyerahan barang)."
    ),
    "sewa": (
        "KUHPerdata Pasal 1548-1600 (sewa menyewa), khususnya Pasal 1548 dan "
        "Pasal 1560; untuk sewa tanah/bangunan dikenai PPh Pasal 4(2) final "
        "10% menurut PMK 68/2022."
    ),
    "jasa": (
        "KUHPerdata Pasal 1601 dan Pasal 1617; PPh Pasal 23 sebesar 2% dari "
        "nilai bruto menurut PMK 81/2024 dan PMK 131/2024; "
        "PPN atas jasa menurut UU 42/2009 jo. UU 7/2021 Pasal 1A."
    ),
    "distributor": (
        "UU 7/2014 Pasal 42-45 tentang keagenan dan Pasal 46-51 tentang "
        "distributor; KUHPerdata Pasal 1338."
    ),
    "waralaba": (
        "UU 7/2014 Pasal 33-41 tentang waralaba; Peraturan Pemerintah "
        "42/2007 tentang Waralaba; Permendag 07/2013 tentang Pengembangan "
        "Kemitraan."
    ),
    "kerja": (
        "UU 13/2003 Pasal 50-66 sebagaimana diubah UU 6/2023 tentang Cipta "
        "Kerja; PP 35/2021 Pasal 8-16 (PKWT) dan Pasal 17-21 (alih daya); "
        "PPh Pasal 21 atas penghasilan pekerja menurut PMK 168/2023."
    ),
    "alih_daya": (
        "UU 13/2003 Pasal 64-66 jo. UU 6/2023; PP 35/2021 Pasal 17-21 "
        "(syarat alih daya dan perlindungan pekerja); PPh Pasal 23 atas jasa "
        "alih daya."
    ),
    "pinjam_pakai": (
        "KUHPerdata Pasal 1740-1753 (pinjam pakai); tanpa imbalan sehingga "
        "bukan objek PPN maupun PPh selama tidak ada pembayaran."
    ),
    "bagi_hasil": (
        "KUHPerdata Pasal 1338 dan Pasal 1618-1651 (persekutuan perdata); "
        "UU 7/2014 Pasal 33; bagi hasil tidak termasuk objek PPN menurut "
        "UU 42/2009 Pasal 4A karena bukan penyerahan barang/jasa biasa."
    ),
    "lainnya": "KUHPerdata Pasal 1313, Pasal 1320, dan Pasal 1338.",
}

# Tambahan dasar hukum menurut bentuk imbalan non-tunai.
DASAR_HUKUM_IMBALAN = {
    "barang": (
        "Tukar menukar diatur KUHPerdata Pasal 1541-1546. Secara fiskal "
        "penyerahan barang tetap dianggap penyerahan menurut UU 42/2009 "
        "Pasal 1A sehingga terutang PPN atas nilai pasar barang."
    ),
    "jasa": (
        "Tukar jasa dinilai berdasarkan harga pasar menurut UU 42/2009 "
        "Pasal 1A angka 2 dan PMK 75/2010; imbalan jasa kepada pihak lain "
        "dipotong PPh Pasal 23 sebesar 2% dari nilai bruto."
    ),
    "bagi_hasil": (
        "Pembagian hasil diatur KUHPerdata Pasal 1618-1651; bagian yang "
        "diterima bukan objek PPN sepanjang bukan penyerahan barang/jasa."
    ),
    "tanpa_imbalan": (
        "Pinjam pakai tanpa imbalan diatur KUHPerdata Pasal 1740-1753; tidak "
        "ada objek pajak selama benar-benar tanpa pembayaran atau manfaat "
        "yang dapat dinilai."
    ),
}


def _hari_ini() -> str:
    return date.today().isoformat()


def _tanggal(teks: str) -> Optional[date]:
    if not teks:
        return None
    try:
        return datetime.strptime(teks[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


# ==========================================================================
# NOMOR KONTRAK
# ==========================================================================
def nomor_berikut(company_id: int, jenis: str = "kerja_sama",
                  tanggal: str = None) -> str:
    """
    Nomor kontrak berurutan per perusahaan, per jenis, per tahun.

    Format: {kode}/{urut:03d}/{kode_jenis}/{tahun}
    Contoh: 001/KTR/KS/2026
    """
    tanggal = tanggal or _hari_ini()
    tahun = tanggal[:4]
    kode_jenis = {
        "kerja_sama": "KS", "mou": "MOU", "jual_beli": "JB",
        "sewa": "SW", "jasa": "JS", "distributor": "AG",
        "waralaba": "WR", "kerja": "PK", "alih_daya": "AD",
        "pinjam_pakai": "PP", "bagi_hasil": "BH",
    }.get(jenis, "KTR")

    pola = f"%/{kode_jenis}/{tahun}"
    baris = db.q(
        "SELECT nomor FROM kontrak WHERE company_id=? AND nomor LIKE ? "
        "ORDER BY nomor DESC", (company_id, pola))
    urut = 1
    for r in baris:
        bagian = r["nomor"].split("/")
        if bagian and bagian[0].isdigit():
            urut = int(bagian[0]) + 1
            break
    return f"{urut:03d}/KTR/{kode_jenis}/{tahun}"


# ==========================================================================
# DASAR HUKUM
# ==========================================================================
def dasar_hukum(jenis: str, bentuk_imbalan: str = "uang") -> str:
    """Susun dasar hukum menurut jenis kontrak dan bentuk imbalannya."""
    bagian = [DASAR_HUKUM.get(jenis, DASAR_HUKUM["lainnya"])]
    tambahan = DASAR_HUKUM_IMBALAN.get(bentuk_imbalan)
    if tambahan:
        bagian.append(tambahan)
    return " ".join(bagian)


# ==========================================================================
# PAJAK
# ==========================================================================
def hitung_pajak(nilai: int, jenis: str, bentuk_imbalan: str,
                 kena_ppn: bool = False, persen_ppn: float = 11.0) -> dict:
    """
    Hitung potongan pajak yang melekat pada satu kontrak.

    Angka ini hanya estimasi untuk perencanaan; pemotongan sebenarnya
    mengikuti dokumen tagihan dan status lawan transaksi.
    """
    pph_pasal = ""
    tarif_pph = 0.0
    nilai = max(0, int(nilai or 0))

    if bentuk_imbalan in ("barang", "barang_jasa", "tanpa_imbalan"):
        pph_pasal = ""
    elif jenis == "sewa":
        pph_pasal, tarif_pph = "PPh Pasal 4(2)", 10.0
    elif jenis in ("jasa", "alih_daya"):
        pph_pasal, tarif_pph = "PPh Pasal 23", 2.0
    elif jenis == "bagi_hasil":
        pph_pasal, tarif_pph = "PPh Pasal 23", 2.0
    elif jenis == "kerja":
        pph_pasal, tarif_pph = "PPh Pasal 21", 0.0

    pph = int(round(nilai * tarif_pph / 100)) if tarif_pph else 0
    ppn = int(round(nilai * persen_ppn / 100)) if kena_ppn else 0

    return {
        "nilai": nilai,
        "pph_pasal": pph_pasal,
        "tarif_pph": tarif_pph,
        "pph": pph,
        "kena_ppn": bool(kena_ppn),
        "tarif_ppn": persen_ppn if kena_ppn else 0.0,
        "ppn": ppn,
        "nilai_setelah_pajak": nilai - pph,
        "nilai_dengan_ppn": nilai + ppn,
    }


# ==========================================================================
# SIMPAN & UBAH
# ==========================================================================
def simpan(company_id: int, data: dict, user: str = "") -> int:
    """
    Simpan kontrak baru atau perbarui yang sudah ada.

    Mengembalikan id kontrak. Nomor dibuat otomatis bila tidak diisi.
    """
    jenis = data.get("jenis", "kerja_sama")
    bentuk = data.get("bentuk_imbalan", "uang")
    nomor = (data.get("nomor") or "").strip()
    if not nomor:
        nomor = nomor_berikut(company_id, jenis, data.get("tanggal_mulai"))

    hukum = (data.get("dasar_hukum") or "").strip() or dasar_hukum(jenis, bentuk)
    nilai = int(data.get("nilai") or 0)
    nilai_barang = int(data.get("nilai_barang") or 0)
    nilai_jasa = int(data.get("nilai_jasa") or 0)

    # Nilai perjanjian dipakai untuk pajak dan ringkasan. Kerja sama non-tunai
    # tidak mengisi kolom nilai, jadi nilai barang atau jasa yang ditukar
    # dipakai sebagai dasar agar perjanjiannya tidak tercatat bernilai nol.
    dasar_nilai = nilai or nilai_barang or nilai_jasa

    pajak = hitung_pajak(dasar_nilai, jenis, bentuk, bool(data.get("kena_ppn")))

    kolom = {
        "company_id": company_id,
        "nomor": nomor,
        "judul": data.get("judul", "").strip(),
        "jenis": jenis,
        "bentuk_imbalan": bentuk,
        "partner_id": data.get("partner_id"),
        "pihak_kedua": data.get("pihak_kedua", "").strip(),
        "peran_kita": data.get("peran_kita", "pemberi"),
        "tanggal_mulai": data.get("tanggal_mulai") or _hari_ini(),
        "tanggal_akhir": data.get("tanggal_akhir") or None,
        "tanggal_tanda_tangan": data.get("tanggal_tanda_tangan") or None,
        "opsi_perpanjangan": 1 if data.get("opsi_perpanjangan") else 0,
        "pemberitahuan_berakhir_hari": int(
            data.get("pemberitahuan_berakhir_hari") or 30),
        "nilai": nilai,
        "nilai_barang": nilai_barang,
        "nilai_jasa": nilai_jasa,
        "mata_uang": data.get("mata_uang", "IDR"),
        "skema_bayar": data.get("skema_bayar", "lump_sum"),
        "jumlah_termin": int(data.get("jumlah_termin") or 1),
        "termin_hari": int(data.get("termin_hari") or 0),
        "persentase_bagi_hasil": data.get("persentase_bagi_hasil"),
        "pph_pasal": pajak["pph_pasal"],
        "tarif_pph": pajak["tarif_pph"],
        "kena_ppn": 1 if data.get("kena_ppn") else 0,
        "status": data.get("status", "aktif"),
        "alasan_berakhir": data.get("alasan_berakhir", ""),
        "dokumen_path": data.get("dokumen_path", ""),
        "dokumen_nama": data.get("dokumen_nama", ""),
        "catatan": data.get("catatan", ""),
        "dasar_hukum": hukum,
        "dibuat_oleh": user or data.get("dibuat_oleh", ""),
    }

    kid = data.get("id")
    if kid:
        pasangan = ", ".join(f"{k}=?" for k in kolom)
        db.ex(
            f"UPDATE kontrak SET {pasangan}, "
            "updated_at=datetime('now','localtime') WHERE id=? AND company_id=?",
            (*kolom.values(), int(kid), company_id))
        return int(kid)

    nama_kolom = ", ".join(kolom)
    tanda = ", ".join("?" for _ in kolom)
    kid = db.ex(
        f"INSERT INTO kontrak ({nama_kolom}) VALUES ({tanda})",
        tuple(kolom.values())).lastrowid

    _buat_termin(kid, nilai, data)
    return int(kid)


def _buat_termin(kontrak_id: int, nilai: int, data: dict):
    """Buat jadwal termin bila skema pembayarannya bertahap."""
    if data.get("skema_bayar") != "termin":
        return
    jumlah = max(1, int(data.get("jumlah_termin") or 1))
    mulai = _tanggal(data.get("tanggal_mulai") or _hari_ini())
    jarak = int(data.get("termin_hari") or 30)
    persen = round(100 / jumlah, 2)

    for i in range(jumlah):
        jatuh = mulai + timedelta(days=jarak * (i + 1)) if mulai else None
        db.ex(
            "INSERT INTO kontrak_termin(kontrak_id, urutan, nama, persen, "
            "nilai, jatuh_tempo) VALUES (?,?,?,?,?,?)",
            (kontrak_id, i + 1, f"Termin {i + 1}", persen,
             int(round(nilai * persen / 100)),
             jatuh.isoformat() if jatuh else None))


def hapus(kontrak_id: int, company_id: int):
    db.ex("UPDATE kontrak SET deleted_at=datetime('now','localtime') "
          "WHERE id=? AND company_id=?", (kontrak_id, company_id))


def ambil(kontrak_id: int) -> Optional[dict]:
    """
    Satu kontrak beserta nilai gabungan dan kondisi masa berlakunya.

    Dibaca lewat view agar nilai barang barter dan nilai jasa yang ditukar
    ikut terhitung pada nilai totalnya.
    """
    r = db.q1("SELECT v.*, k.* FROM v_kontrak_aktif v "
              "JOIN kontrak k ON k.id = v.id "
              "WHERE v.id=? AND k.deleted_at IS NULL", (kontrak_id,))
    return dict(r) if r else None


def daftar(company_id: int, status: str = None, cari: str = None,
           jenis: str = None) -> list:
    """
    Daftar kontrak beserta kondisi masa berlakunya.

    Penyaringan dilakukan pada tabel asalnya, bukan pada view, karena view
    hanya memuat kolom yang ditampilkan dan tidak menyertakan deleted_at.
    """
    syarat = ["k.deleted_at IS NULL", "k.company_id=?"]
    nilai = [company_id]
    if status:
        syarat.append("k.status=?")
        nilai.append(status)
    if jenis:
        syarat.append("k.jenis=?")
        nilai.append(jenis)
    if cari:
        syarat.append("(k.nomor LIKE ? OR k.judul LIKE ? "
                      "OR k.pihak_kedua LIKE ? OR p.nama LIKE ?)")
        pola = f"%{cari}%"
        nilai += [pola, pola, pola, pola]

    baris = db.q(
        "SELECT v.* FROM v_kontrak_aktif v "
        "JOIN kontrak k ON k.id = v.id "
        "LEFT JOIN partners p ON p.id = k.partner_id "
        "WHERE " + " AND ".join(syarat) +
        " ORDER BY v.tanggal_mulai DESC, v.id DESC", tuple(nilai))
    return [dict(r) for r in baris]


def item(kontrak_id: int) -> list:
    return [dict(r) for r in db.q(
        "SELECT * FROM kontrak_item WHERE kontrak_id=? ORDER BY id",
        (kontrak_id,))]


def simpan_item(kontrak_id: int, daftar_item: list):
    """Ganti seluruh daftar barang/jasa pada satu kontrak."""
    db.ex("DELETE FROM kontrak_item WHERE kontrak_id=?", (kontrak_id,))
    for it in daftar_item:
        jumlah = float(it.get("jumlah") or 1)
        nilai_satuan = int(it.get("nilai_satuan") or 0)
        db.ex(
            "INSERT INTO kontrak_item(kontrak_id, arah, nama, jumlah, satuan, "
            "nilai_satuan, total, catatan) VALUES (?,?,?,?,?,?,?,?)",
            (kontrak_id, it.get("arah", "kita_beri"), it.get("nama", ""),
             jumlah, it.get("satuan", "unit"), nilai_satuan,
             int(round(jumlah * nilai_satuan)), it.get("catatan", "")))


def termin(kontrak_id: int) -> list:
    return [dict(r) for r in db.q(
        "SELECT * FROM kontrak_termin WHERE kontrak_id=? ORDER BY urutan",
        (kontrak_id,))]


def tandai_termin_dibayar(termin_id: int, tanggal: str = None):
    db.ex("UPDATE kontrak_termin SET dibayar=1, tanggal_bayar=? WHERE id=?",
          (tanggal or _hari_ini(), termin_id))


def simpan_berkas(kontrak_id: int, nama: str, path: str, jenis: str = "kontrak",
                  isi_terstruktur: str = "", ukuran: int = 0, user: str = ""):
    return db.ex(
        "INSERT INTO kontrak_berkas(kontrak_id, nama, path_berkas, jenis, "
        "isi_terstruktur, ukuran, diunggah_oleh) VALUES (?,?,?,?,?,?,?)",
        (kontrak_id, nama, path, jenis, isi_terstruktur, ukuran, user)).lastrowid


def berkas(kontrak_id: int) -> list:
    return [dict(r) for r in db.q(
        "SELECT * FROM kontrak_berkas WHERE kontrak_id=? ORDER BY id DESC",
        (kontrak_id,))]


# ==========================================================================
# RINGKASAN
# ==========================================================================
def ringkasan(company_id: int) -> dict:
    """Angka ringkas untuk kartu di halaman kontrak."""
    r = db.q1(
        "SELECT COUNT(*) AS jumlah, "
        # Nilai perjanjian menjumlahkan perjanjian uang, barter barang, dan
        # tukar jasa sekaligus. Memakai kolom nilai saja membuat kerja sama
        # non-tunai terhitung nol dan totalnya tampak lebih kecil.
        "COALESCE(SUM(nilai + nilai_barang + nilai_jasa), 0) AS total_nilai, "
        # Kontrak yang masa berlakunya sudah lewat tidak dihitung aktif,
        # supaya kartu ini tidak bertentangan dengan kartu Sudah Berakhir.
        "COALESCE(SUM(CASE WHEN status='aktif' AND (tanggal_akhir IS NULL "
        "  OR julianday(tanggal_akhir) >= julianday('now')) "
        "  THEN 1 ELSE 0 END), 0) AS aktif "
        "FROM kontrak WHERE company_id=? AND deleted_at IS NULL",
        (company_id,))
    segera = db.q1(
        "SELECT COUNT(*) AS n FROM v_kontrak_aktif "
        "WHERE company_id=? AND kondisi IN ('Segera Berakhir','Perlu Perhatian')",
        (company_id,))
    berakhir = db.q1(
        "SELECT COUNT(*) AS n FROM v_kontrak_aktif "
        "WHERE company_id=? AND kondisi='Sudah Berakhir'", (company_id,))
    return {
        "jumlah": r["jumlah"] or 0,
        "aktif": r["aktif"] or 0,
        "total_nilai": r["total_nilai"] or 0,
        "segera_berakhir": segera["n"] or 0,
        "sudah_berakhir": berakhir["n"] or 0,
    }


def yang_perlu_perhatian(company_id: int, hari: int = 60) -> list:
    """Kontrak yang berakhir dalam beberapa hari ke depan atau sudah lewat."""
    baris = db.q(
        "SELECT * FROM v_kontrak_aktif WHERE company_id=? "
        "AND (kondisi IN ('Segera Berakhir','Perlu Perhatian') "
        "     OR kondisi='Sudah Berakhir') "
        "ORDER BY tanggal_akhir",
        (company_id,))
    return [dict(r) for r in baris]


# ==========================================================================
# PARSING DOKUMEN
# ==========================================================================
POLA_NOMOR = (
    r"(?:nomor|no\.?|number)\s*[:\-]?\s*"
    r"([A-Z0-9][A-Z0-9\-/\.]{4,60})"
)
POLA_TANGGAL = (
    r"(\d{1,2}\s+(?:Januari|Februari|Maret|April|Mei|Juni|Juli|Agustus|"
    r"September|Oktober|November|Desember)\s+\d{4})"
)
BULAN_ID = {
    "januari": 1, "februari": 2, "maret": 3, "april": 4, "mei": 5, "juni": 6,
    "juli": 7, "agustus": 8, "september": 9, "oktober": 10, "november": 11,
    "desember": 12,
}


def _ke_iso(teks: str) -> Optional[str]:
    """Ubah tanggal berbahasa Indonesia menjadi format ISO."""
    import re
    m = re.search(POLA_TANGGAL, teks, re.IGNORECASE)
    if not m:
        return None
    bagian = m.group(1).split()
    if len(bagian) != 3:
        return None
    hari, bulan, tahun = bagian
    angka = BULAN_ID.get(bulan.lower())
    if not angka:
        return None
    try:
        return date(int(tahun), angka, int(hari)).isoformat()
    except ValueError:
        return None


def baca_dokumen(path: str) -> str:
    """Ambil teks dari berkas dokumen kontrak."""
    from pathlib import Path
    p = Path(path)
    if not p.exists():
        return ""
    ext = p.suffix.lower()
    try:
        if ext in (".txt", ".md"):
            return p.read_text(encoding="utf-8", errors="ignore")
        if ext == ".pdf":
            import fitz
            with fitz.open(p) as doc:
                return "\n".join(halaman.get_text() for halaman in doc)
        if ext == ".docx":
            import docx
            return "\n".join(par.text for par in docx.Document(p).paragraphs)
    except Exception:
        return ""
    return ""


def urai_teks(teks: str) -> dict:
    """
    Tarik data kontrak dari teks dokumen.

    Hasilnya berupa saran yang masih dapat disunting pengguna; penguraian
    ini tidak menggantikan pemeriksaan isi perjanjian.
    """
    import re
    hasil: dict = {}
    if not teks:
        return hasil

    m = re.search(POLA_NOMOR, teks, re.IGNORECASE)
    if m:
        hasil["nomor"] = m.group(1).strip().rstrip(".,;:")

    # Judul: baris yang memuat kata perjanjian atau kerja sama
    for baris in teks.splitlines():
        b = baris.strip()
        if 12 <= len(b) <= 120 and re.search(
                r"(perjanjian|kerja\s*sama|kesepahaman|mou|kontrak|"
                r"nota\s*kesepahaman)", b, re.IGNORECASE):
            hasil["judul"] = b
            break

    # Jenis kontrak
    rendah = teks.lower()
    if re.search(r"nota\s*kesepahaman|\bmou\b|memorandum", rendah):
        hasil["jenis"] = "mou"
    elif "waralaba" in rendah or "franchise" in rendah:
        hasil["jenis"] = "waralaba"
    elif "distributor" in rendah or "keagenan" in rendah:
        hasil["jenis"] = "distributor"
    elif "sewa" in rendah or "rental" in rendah:
        hasil["jenis"] = "sewa"
    elif "alih daya" in rendah or "outsourc" in rendah:
        hasil["jenis"] = "alih_daya"
    elif re.search(r"perjanjian\s*kerja|karyawan|pekerja", rendah):
        hasil["jenis"] = "kerja"
    elif re.search(r"jual\s*beli|pembelian", rendah):
        hasil["jenis"] = "jual_beli"
    elif re.search(r"bagi\s*hasil|profit\s*sharing", rendah):
        hasil["jenis"] = "bagi_hasil"
    elif "jasa" in rendah:
        hasil["jenis"] = "jasa"

    # Bentuk imbalan
    if re.search(r"barter|tukar\s*(menukar|barang)|in\s*kind", rendah):
        hasil["bentuk_imbalan"] = "barang"
    elif re.search(r"tukar\s*jasa", rendah):
        hasil["bentuk_imbalan"] = "jasa"
    elif re.search(r"bagi\s*hasil|profit\s*sharing|revenue\s*sharing", rendah):
        hasil["bentuk_imbalan"] = "bagi_hasil"
    elif re.search(r"tanpa\s*(imbalan|bayaran)|gratis|cuma-cuma", rendah):
        hasil["bentuk_imbalan"] = "tanpa_imbalan"

    # Tanggal: cari "mulai" dan "berakhir/selesai"
    for label, kunci in (("tanggal_mulai", r"(?:mulai|berlaku|efektif|terhitung)"),
                         ("tanggal_akhir", r"(?:berakhir|selesai|hingga|sampai)")):
        m2 = re.search(label and kunci + r"[^\n]{0,40}?" + POLA_TANGGAL,
                       teks, re.IGNORECASE)
        if m2:
            iso = _ke_iso(m2.group(0))
            if iso:
                hasil[label] = iso

    # Nilai rupiah
    for m3 in re.finditer(
            r"Rp\s*([\d.,]+)\s*(juta|miliar|milyar|ribu)?", teks, re.IGNORECASE):
        angka_teks = m3.group(1).replace(".", "").replace(",", ".")
        try:
            angka = float(angka_teks)
        except ValueError:
            continue
        satuan = (m3.group(2) or "").lower()
        if satuan == "juta":
            angka *= 1_000_000
        elif satuan in ("miliar", "milyar"):
            angka *= 1_000_000_000
        elif satuan == "ribu":
            angka *= 1_000
        if angka >= 100_000:
            hasil["nilai"] = int(angka)
            break

    if "jenis" in hasil:
        hasil["dasar_hukum"] = dasar_hukum(
            hasil["jenis"], hasil.get("bentuk_imbalan", "uang"))
    return hasil
