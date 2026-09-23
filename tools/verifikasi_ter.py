"""
Ekstrak tabel TER (Tarif Efektif Rata-rata) PPh 21 dari salinan resmi
PMK 168/2023, lalu bandingkan dengan tabel yang dipakai aplikasi.

Sumber: docs/pajak2026/PMK168_2023.pdf (salinan dari pajak.go.id)
Halaman 10 = TER A, 11 = TER B, 12 = TER C.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pdfplumber

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "src"))

from akuntansi_id.core import tax_engine as tx

PDF = AKAR / "docs" / "pajak2026" / "PMK168_2023.pdf"
HALAMAN = {"A": 9, "B": 10, "C": 11}


def angka(teks) -> int:
    return int(str(teks).replace(".", "").strip())


def persen(teks) -> float:
    return round(float(str(teks).replace("%", "").replace(",", ".").strip()) / 100, 6)


def ekstrak(kategori: str) -> list:
    """Ambil seluruh lapisan satu kategori TER dari PDF.

    Baris terakhir tabel berbunyi "lebih dari 1.400.000.000 → 34%",
    artinya batas atas tak terhingga; baris itu disimpan sebagai inf.
    """
    hasil: list = []
    with pdfplumber.open(PDF) as pdf:
        page = pdf.pages[HALAMAN[kategori]]
        for tabel in page.extract_tables():
            if not tabel or len(tabel[0]) < 5:
                continue
            for row in tabel:
                if not row or row[0] in ("No", None, ""):
                    continue
                if not str(row[0]).strip().isdigit():
                    continue
                batas = row[3]
                tarif = row[4]
                if batas in (None, "") or tarif in (None, ""):
                    continue
                if "lebih" in str(row[1]).lower():
                    hasil.append((float("inf"), persen(tarif)))
                else:
                    hasil.append((angka(batas), persen(tarif)))
    return hasil


def main() -> int:
    if not PDF.exists():
        print(f"Berkas tidak ditemukan: {PDF}")
        return 2

    kode = {"A": tx.TER_TABLE_A, "B": tx.TER_TABLE_B, "C": tx.TER_TABLE_C}
    semua_cocok = True

    for kategori in ("A", "B", "C"):
        dok = ekstrak(kategori)
        print(f"\n=== TER {kategori} ===")
        print(f"dokumen resmi: {len(dok)} lapisan")
        print(f"kode aplikasi: {len(kode[kategori])} lapisan")

        # Bandingkan hanya pada batas yang sama (abaikan lapisan tak terhingga)
        peta_dok = {b: t for b, t in dok}
        beda = []
        for b, t in kode[kategori]:
            if b in peta_dok and abs(peta_dok[b] - t) > 1e-9:
                beda.append((b, t, peta_dok[b]))

        if beda:
            semua_cocok = False
            print(f"PERBEDAAN: {len(beda)} lapisan")
            for b, t_kode, t_dok in beda[:10]:
                print(f"   batas {b:>15,}  kode={t_kode*100:>6.2f}%  "
                      f"dokumen={t_dok*100:>6.2f}%")
            if len(beda) > 10:
                print(f"   ... dan {len(beda) - 10} lainnya")
        else:
            print("COCOK dengan dokumen resmi")

    print()
    print("=" * 70)
    if semua_cocok:
        print("HASIL: seluruh tabel TER cocok dengan PMK 168/2023")
    else:
        print("HASIL: ADA KETIDAKSESUAIAN — tabel kode perlu diperbaiki")
    print("=" * 70)
    return 0 if semua_cocok else 1


if __name__ == "__main__":
    sys.exit(main())
