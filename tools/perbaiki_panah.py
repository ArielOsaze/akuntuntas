"""
Perbaiki teks tampil yang kehilangan tanda panah.

Pola rusaknya: "kata<spasi><spasi>kata" yang seharusnya "kata -> kata".
Daftar perbaikan ditulis eksplisit per lokasi agar tidak ada penggantian
yang salah sasaran pada teks lain.
"""
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parents[1] / "src" / "akuntansi_id"

# (berkas, teks lama, teks baru)
PERBAIKAN = [
    ("coa.py",
     "Jika hasilnya positif  kurang bayar, setor dengan kode billing MP.",
     "Jika hasilnya positif -> kurang bayar, setor dengan kode billing MP."),
    ("coa.py",
     "Jika negatif  lebih bayar, dapat dikompensasikan ke masa berikutnya",
     "Jika negatif -> lebih bayar, dapat dikompensasikan ke masa berikutnya"),
    ("login.py",
     "<b>Pengaturan  Pengguna</b> dan mereset password Anda.",
     "<b>Pengaturan -> Pengguna</b> dan mereset password Anda."),
    ("login.py",
     "<b>Pengaturan  Preferensi</b>. Data pembukuan tidak terpengaruh.",
     "<b>Pengaturan -> Preferensi</b>. Data pembukuan tidak terpengaruh."),
    ("ui/main_window.py",
     "alur: login  (ganti password)  (pilih mode)  jendela utama.",
     "alur: login -> (ganti password) -> (pilih mode) -> jendela utama."),
    ("ui/pages/biaya_bank.py",
     "Alur: Ajukan  Setujui  Bayar.",
     "Alur: Ajukan -> Setujui -> Bayar."),
    ("ui/pages/biaya_bank.py",
     "Saldo bertambah  DEBIT akun kas/bank, KREDIT akun lawan.",
     "Saldo bertambah -> DEBIT akun kas/bank, KREDIT akun lawan."),
    ("ui/pages/biaya_bank.py",
     "Saldo berkurang  DEBIT akun lawan, KREDIT akun kas/bank.",
     "Saldo berkurang -> DEBIT akun lawan, KREDIT akun kas/bank."),
    ("ui/pages/pajak.py",
     "Biaya entertainment tanpa daftar nominatif  koreksi positif",
     "Biaya entertainment tanpa daftar nominatif -> koreksi positif"),
    ("ui/pages/pajak.py",
     "Sumbangan yang tidak memenuhi syarat  koreksi positif",
     "Sumbangan yang tidak memenuhi syarat -> koreksi positif"),
    ("ui/pages/pajak.py",
     "Penghasilan dividen yang dikecualikan  koreksi negatif",
     "Penghasilan dividen yang dikecualikan -> koreksi negatif"),
    ("ui/pages/pajak.py",
     "Penghasilan sewa tanah yang sudah dikenai PPh Final  koreksi negatif",
     "Penghasilan sewa tanah yang sudah dikenai PPh Final -> koreksi negatif"),
    ("ui/pages/pembelian.py",
     "Alur: Purchase Order  Bill  Pembayaran ke Vendor.",
     "Alur: Purchase Order -> Bill -> Pembayaran ke Vendor."),
    ("ui/pages/penjualan.py",
     "Alur: Sales Order  Invoice  Penerimaan Pembayaran.",
     "Alur: Sales Order -> Invoice -> Penerimaan Pembayaran."),
    ("ui/pages/penjualan.py",
     "Lihat di menu Pengaturan  Pengingat.",
     "Lihat di menu Pengaturan -> Pengingat."),
]


def main() -> int:
    gagal = 0
    for relatif, lama, baru in PERBAIKAN:
        p = AKAR / relatif
        if not p.exists():
            print(f"  lewat  {relatif}: berkas tidak ada")
            gagal += 1
            continue
        t = p.read_text(encoding="utf-8")
        if lama not in t:
            print(f"  lewat  {relatif}: teks lama tidak ditemukan")
            gagal += 1
            continue
        p.write_text(t.replace(lama, baru), encoding="utf-8")
        print(f"  ubah   {relatif}")

    print()
    print(f"selesai: {len(PERBAIKAN) - gagal} diubah, {gagal} gagal")
    return 1 if gagal else 0


if __name__ == "__main__":
    sys.exit(main())
