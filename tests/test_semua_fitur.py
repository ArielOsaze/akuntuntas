"""
Uji menyeluruh seluruh fitur AkunTuntas.
Jalankan: python tests/test_semua_fitur.py
"""
import os
import shutil
import sys
import tempfile
import traceback

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

DATA_UJI = os.path.join(tempfile.gettempdir(), "akuntansiid_uji")
shutil.rmtree(DATA_UJI, ignore_errors=True)
os.environ["AKUNTANSIID_DATA"] = DATA_UJI

from akuntansi_id import db, services, modules as M, modules_sales as S, modules_ops as O  # noqa: E402
from akuntansi_id.core import accounting as acc, tax_engine as tx, analyzer as an  # noqa: E402
from akuntansi_id.core import security as sec  # noqa: E402

LULUS = 0
GAGAL = 0
CATATAN = []


def cek(nama, kondisi, detail=""):
    global LULUS, GAGAL
    if kondisi:
        LULUS += 1
        print(f"  OK    {nama}")
    else:
        GAGAL += 1
        CATATAN.append(f"{nama}: {detail}")
        print(f"  GAGAL {nama}  {detail}")


def jalankan(nama, fungsi):
    try:
        fungsi()
    except Exception as e:
        global GAGAL
        GAGAL += 1
        CATATAN.append(f"{nama}: {type(e).__name__}: {e}")
        print(f"  GAGAL {nama}: {type(e).__name__}: {e}")
        traceback.print_exc(limit=3)


def bagian(judul):
    print()
    print("=" * 72)
    print(judul)
    print("=" * 72)


# ==========================================================================
bagian("PERSIAPAN & KEAMANAN")
db.init_db()
sec.ensure_default_admin()
M.inisialisasi_izin()

cek("Database terinisialisasi", db.q1("SELECT 1") is not None)
cek("Admin default dibuat", sec.count_users() == 1)

hasil = sec.login("admin", "admin123")
cek("Login berhasil", hasil.ok)
cek("Mode awal pemula", hasil.app_mode == "beginner")
cek("Wajib ganti password", hasil.must_change_pw)

gagal_login = sec.login("admin", "password_salah")
cek("Password salah ditolak", not gagal_login.ok)

skor, label, _ = sec.password_strength("Kucing#Lari9Kencang")
cek("Password kuat terdeteksi", skor >= 3, f"skor={skor}")

try:
    sec.change_password(hasil.user_id, "admin123", "lemah")
    cek("Password lemah ditolak", False)
except ValueError:
    cek("Password lemah ditolak", True)

sec.change_password(hasil.user_id, "admin123", "Akuntan#2026Aman")
cek("Ganti password berhasil", sec.login("admin", "Akuntan#2026Aman").ok)

uid2 = sec.create_user("staf1", "Staf#Kuat2026", "Budi Staf", "staff")
cek("Pengguna baru dibuat", uid2 > 0)
sec.update_user_mode(uid2, "expert")
row = db.q1("SELECT app_mode FROM users WHERE id=?", (uid2,))
cek("Mode pengguna tersimpan", row["app_mode"] == "expert")


# ==========================================================================
bagian("PERUSAHAAN & BAGAN AKUN")
cid = services.create_company(
    "PT Uji Lengkap", "pt", npwp="01.234.567.8-901.000",
    nama_pemilik="Direktur Utama", kota="Jakarta", tahun_buku_awal="2026-01-01",
    status_pkp=True, skema_pph="pasal31e")

jml_akun = db.scalar("SELECT COUNT(*) FROM accounts WHERE company_id=?", (cid,))
cek("Perusahaan dibuat", cid > 0)
cek("Bagan akun PT terisi", jml_akun >= 90, f"jumlah={jml_akun}")

cid_umkm = services.create_company("Toko Uji UMKM", "umkm_op",
                                   nama_pemilik="Pemilik UMKM",
                                   tahun_buku_awal="2026-01-01")
akun_umkm = db.scalar("SELECT COUNT(*) FROM accounts WHERE company_id=?", (cid_umkm,))
cek("Bagan akun UMKM lebih ringkas", 20 < akun_umkm < jml_akun,
    f"umkm={akun_umkm} pt={jml_akun}")

services.set_saldo_awal(cid, {"1002": 500_000_000, "1201": 100_000_000,
                              "3001": 600_000_000})
cek_saldo = services.cek_keseimbangan_saldo_awal(cid)
cek("Saldo awal seimbang", cek_saldo["seimbang"])

try:
    services.create_account(cid, "1001", "Duplikat", "Aset")
    cek("Kode akun duplikat ditolak", False)
except ValueError:
    cek("Kode akun duplikat ditolak", True)

akun_baru = services.create_account(cid, "6024", "Beban Uji", "Beban",
                                    "Beban Operasional", "", "Debit")
cek("Akun baru dapat dibuat", akun_baru > 0)


# ==========================================================================
bagian("JURNAL & VALIDASI DOUBLE-ENTRY")
jml_awal = db.scalar("SELECT COUNT(*) FROM journal_entries WHERE company_id=?", (cid,))

services.simpan_jurnal_manual(cid, "2026-01-02", "BKM-001", "Setoran modal tambahan", [
    {"kode_akun": "1002", "debit": 50_000_000, "kredit": 0},
    {"kode_akun": "3001", "debit": 0, "kredit": 50_000_000}])
cek("Jurnal seimbang tersimpan",
    db.scalar("SELECT COUNT(*) FROM journal_entries WHERE company_id=?", (cid,)) > jml_awal)

try:
    services.simpan_jurnal_manual(cid, "2026-01-03", "X-001", "Tidak seimbang", [
        {"kode_akun": "1002", "debit": 1_000_000, "kredit": 0},
        {"kode_akun": "3001", "debit": 0, "kredit": 500_000}])
    cek("Jurnal tidak seimbang ditolak", False)
except ValueError:
    cek("Jurnal tidak seimbang ditolak", True)

try:
    services.simpan_jurnal_manual(cid, "2026-01-03", "X-002", "Debit kredit sekaligus", [
        {"kode_akun": "1002", "debit": 1_000_000, "kredit": 1_000_000},
        {"kode_akun": "3001", "debit": 1_000_000, "kredit": 0}])
    cek("Debit+kredit sekaligus ditolak", False)
except ValueError:
    cek("Debit+kredit sekaligus ditolak", True)

try:
    services.simpan_jurnal_manual(cid, "2026-01-03", "X-003", "Baris tunggal", [
        {"kode_akun": "1002", "debit": 1_000_000, "kredit": 0}])
    cek("Jurnal satu baris ditolak", False)
except ValueError:
    cek("Jurnal satu baris ditolak", True)

nomor = M.nomor_berikut(cid, "JU", 2026)
cek("Nomor jurnal otomatis", nomor.startswith("JU/2026/"), nomor)


# ==========================================================================
bagian("MITRA USAHA")
cust = M.buat_mitra(cid, "PT Pelanggan Utama", "customer",
                    npwp="02.111.222.3-444.000", email="beli@pelanggan.co.id",
                    telepon="021-5551234", alamat="Jl. Sudirman 1", kota="Jakarta",
                    termin_hari=30, batas_kredit=100_000_000)
vend = M.buat_mitra(cid, "CV Pemasok Terpercaya", "vendor",
                    npwp="03.222.333.4-555.000", termin_hari=14,
                    nama_bank="BCA", rekening_bank="9876543210")
cek("Customer dibuat", cust > 0)
cek("Vendor dibuat", vend > 0)
cek("Daftar customer", len(M.daftar_mitra(cid, "customer")) == 1)
cek("Daftar vendor", len(M.daftar_mitra(cid, "vendor")) == 1)

M.ubah_mitra(cust, nama="PT Pelanggan Utama (Revisi)")
cek("Mitra dapat diubah",
    M.get_mitra(cust)["nama"] == "PT Pelanggan Utama (Revisi)")

cek("Pencarian mitra berfungsi", len(M.daftar_mitra(cid, cari="Pelanggan")) == 1)

mitra_keduanya = M.buat_mitra(cid, "PT Mitra Ganda", "keduanya")
cek("Mitra tipe keduanya", len(M.daftar_mitra(cid, "customer")) == 2)


# ==========================================================================
bagian("PRODUK, GUDANG & PERSEDIAAN")
gudang2 = M.buat_gudang(cid, "Gudang Bandung", lokasi="Bandung", pic="Andi")
cek("Gudang kedua dibuat", gudang2 > 0)

p1 = M.buat_produk(cid, "Kopi Arabika 250g", kode="P0001", harga_beli=45000,
                   harga_jual=75000, metode_hpp="fifo", stok_minimum=20, qty_awal=100)
p2 = M.buat_produk(cid, "Gula Premium 1kg", kode="P0002", harga_beli=15000,
                   harga_jual=25000, metode_hpp="average", qty_awal=50)
p3 = M.buat_produk(cid, "Jasa Konsultasi IT", kode="P0003", tipe="jasa",
                   harga_jual=500000)
cek("Produk FIFO dibuat", p1 > 0)
cek("Produk Average dibuat", p2 > 0)
cek("Produk jasa dibuat", p3 > 0)

try:
    M.buat_produk(cid, "Uji Salah", metode_hpp="metode_aneh")
    cek("Metode HPP salah ditolak", False)
except ValueError:
    cek("Metode HPP salah ditolak", True)

saldo = M.saldo_stok(cid, p1)
cek("Stok awal tercatat", saldo["qty"] == 100, f"qty={saldo['qty']}")
cek("Nilai stok benar", saldo["nilai_total"] == 100 * 45000,
    f"nilai={saldo['nilai_total']}")

M.stok_masuk(cid, p1, 50, 50000, "2026-01-10", keterangan="Pembelian batch 2")
saldo = M.saldo_stok(cid, p1)
cek("Stok masuk menambah qty", saldo["qty"] == 150, f"qty={saldo['qty']}")

r = M.stok_keluar(cid, p1, 30, "2026-01-15")
cek("FIFO mengonsumsi lapisan tertua", r["hpp"] == 30 * 45000,
    f"hpp={r['hpp']} target={30 * 45000}")

r = M.stok_keluar(cid, p1, 90, "2026-01-20")
target = 70 * 45000 + 20 * 50000
cek("FIFO lintas lapisan benar", r["hpp"] == target,
    f"hpp={r['hpp']} target={target}")

saldo = M.saldo_stok(cid, p1)
cek("Sisa stok FIFO benar", saldo["qty"] == 30, f"qty={saldo['qty']}")

M.stok_masuk(cid, p2, 50, 20000, "2026-01-10")
saldo = M.saldo_stok(cid, p2)
target_avg = int((50 * 15000 + 50 * 20000) / 100)
cek("Average cost dihitung benar", saldo["hpp_satuan"] == target_avg,
    f"avg={saldo['hpp_satuan']} target={target_avg}")

try:
    M.stok_keluar(cid, p1, 99999, "2026-01-25")
    cek("Stok tidak cukup ditolak", False)
except ValueError:
    cek("Stok tidak cukup ditolak", True)

M.penyesuaian_stok(cid, p2, 105, "2026-01-31", alasan="Stock opname Januari")
saldo = M.saldo_stok(cid, p2)
cek("Penyesuaian stok berfungsi", abs(saldo["qty"] - 105) < 0.01,
    f"qty={saldo['qty']}")

M.transfer_stok(cid, p1, 10, M.gudang_utama(cid), gudang2, "2026-02-01")
s1 = M.saldo_stok(cid, p1, M.gudang_utama(cid))
s2 = M.saldo_stok(cid, p1, gudang2)
cek("Transfer antar gudang", abs(s2["qty"] - 10) < 0.01, f"gudang2={s2['qty']}")

kartu = M.kartu_stok(cid, p1)
cek("Kartu stok mencatat mutasi", len(kartu) >= 5, f"baris={len(kartu)}")

cek("Daftar stok berfungsi", len(M.daftar_stok(cid)) >= 2)


# ==========================================================================
bagian("PENJUALAN: SO → INVOICE → RECEIPT")
so = S.buat_sales_order(cid, "2026-02-01", [
    {"product_id": p1, "qty": 20, "harga_satuan": 75000, "diskon_persen": 5},
    {"product_id": p3, "qty": 3, "harga_satuan": 500000},
], partner_id=cust, jenis_ppn="12% DPP Nilai Lain (11/12)", user_id=1)
so_row = db.q1("SELECT * FROM sales_orders WHERE id=?", (so,))
cek("Sales order dibuat", so > 0)
cek("SO punya nomor otomatis", so_row["nomor"].startswith("SO/2026/"),
    so_row["nomor"])
cek("SO punya baris", len(S.detail_so(so)) == 2)

S.ubah_status_so(so, "dikonfirmasi")
cek("Status SO dapat diubah",
    db.q1("SELECT status FROM sales_orders WHERE id=?", (so,))["status"] == "dikonfirmasi")

inv = S.buat_invoice(cid, "2026-02-05", [
    {"product_id": p1, "qty": 20, "harga_satuan": 75000, "diskon_persen": 5},
    {"product_id": p3, "qty": 3, "harga_satuan": 500000},
], partner_id=cust, jenis_ppn="12% DPP Nilai Lain (11/12)", so_id=so, user_id=1)
inv_row = S.get_invoice(inv)
cek("Invoice dibuat dari SO", inv > 0)
cek("Invoice punya nomor otomatis", inv_row["nomor"].startswith("INV/2026/"))
cek("Diskon diterapkan",
    inv_row["subtotal"] == (20 * 75000 - int(20 * 75000 * 0.05)) + 3 * 500000,
    f"subtotal={inv_row['subtotal']}")
cek("PPN dihitung (efektif 11%)",
    inv_row["ppn"] == int(round((inv_row["dpp"]) * 11 / 100)),
    f"ppn={inv_row['ppn']} dpp={inv_row['dpp']}")
cek("Jatuh tempo otomatis +30 hari", inv_row["jatuh_tempo"] == "2026-03-07",
    inv_row["jatuh_tempo"])
cek("Status awal terkirim", inv_row["status"] == "terkirim")
cek("Sisa = total", inv_row["sisa"] == inv_row["total"])

jurnal_inv = db.q1("SELECT * FROM journal_entries WHERE id=?",
                   (inv_row["journal_entry_id"],))
cek("Jurnal invoice dibuat", jurnal_inv is not None)
if jurnal_inv:
    baris_jurnal = services.detail_jurnal(jurnal_inv["id"])
    td = sum(b["debit"] for b in baris_jurnal)
    tk = sum(b["kredit"] for b in baris_jurnal)
    cek("Jurnal invoice seimbang", td == tk, f"debit={td} kredit={tk}")

stok_p1 = M.saldo_stok(cid, p1)
cek("Stok berkurang karena penjualan", stok_p1["qty"] == 10, f"qty={stok_p1['qty']}")

hpp_total = sum(i["hpp"] for i in S.detail_invoice(inv))
cek("HPP tercatat pada invoice", hpp_total > 0, f"hpp={hpp_total}")

# Pembayaran sebagian
setengah = inv_row["total"] // 2
rcv1 = S.terima_pembayaran(cid, "2026-02-15", setengah,
                           [{"invoice_id": inv, "jumlah": setengah}],
                           partner_id=cust, akun_kas="1002", metode="Transfer",
                           referensi="TRF-001", user_id=1)
inv_row = S.get_invoice(inv)
cek("Pembayaran sebagian tercatat", inv_row["dibayar"] == setengah)
cek("Status menjadi sebagian", inv_row["status"] == "sebagian",
    inv_row["status"])
cek("Sisa piutang benar", inv_row["sisa"] == inv_row["total"] - setengah)

cek("Alokasi penerimaan tercatat", len(S.alokasi_penerimaan(rcv1)) == 1)

# Pelunasan
S.terima_pembayaran(cid, "2026-03-01", inv_row["sisa"],
                    [{"invoice_id": inv, "jumlah": inv_row["sisa"]}],
                    partner_id=cust, akun_kas="1002", user_id=1)
inv_row = S.get_invoice(inv)
cek("Pelunasan mengubah status lunas", inv_row["status"] == "lunas")
cek("Sisa menjadi nol", inv_row["sisa"] == 0)

try:
    S.terima_pembayaran(cid, "2026-03-02", 1_000_000,
                        [{"invoice_id": inv, "jumlah": 1_000_000}], user_id=1)
    cek("Kelebihan alokasi ditolak", False)
except ValueError:
    cek("Kelebihan alokasi ditolak", True)

# Nota kredit
M.stok_masuk(cid, p1, 200, 45000, "2026-03-08", keterangan="Restock sebelum uji")
inv2 = S.buat_invoice(cid, "2026-03-10",
                      [{"product_id": p1, "qty": 5, "harga_satuan": 75000}],
                      partner_id=cust, jenis_ppn="Non-PKP/Tidak Dipungut", user_id=1)
inv2_row = S.get_invoice(inv2)
cn = S.buat_nota_kredit(cid, "2026-03-15", 100_000, inv2, cust, "retur",
                        "Barang rusak", user_id=1)
inv2_row = S.get_invoice(inv2)
cek("Nota kredit mengurangi total", inv2_row["total"] == 5 * 75000 - 100_000,
    f"total={inv2_row['total']}")
cek("Nota kredit tercatat", len(S.daftar_nota_kredit(cid, 2026)) == 1)

# Void penerimaan
S.void_penerimaan(rcv1, "Admin", 1)
inv_row = S.get_invoice(inv)
cek("Void penerimaan mengembalikan status",
    inv_row["status"] != "lunas", inv_row["status"])

# Void invoice
inv3 = S.buat_invoice(cid, "2026-04-01",
                      [{"product_id": p1, "qty": 2, "harga_satuan": 75000}],
                      partner_id=cust, jenis_ppn="Non-PKP/Tidak Dipungut", user_id=1)
stok_sebelum = M.saldo_stok(cid, p1)["qty"]
S.hapus_invoice(inv3, "Admin", 1)
stok_setelah = M.saldo_stok(cid, p1)["qty"]
cek("Void invoice mengembalikan stok", stok_setelah == stok_sebelum + 2,
    f"sebelum={stok_sebelum} sesudah={stok_setelah}")
cek("Invoice ter-void tidak muncul",
    all(r["id"] != inv3 for r in S.daftar_invoice(cid)))

# Refund
inv4 = S.buat_invoice(cid, "2026-04-05",
                      [{"product_id": p2, "qty": 10, "harga_satuan": 25000}],
                      partner_id=cust, jenis_ppn="Non-PKP/Tidak Dipungut", user_id=1)
cn2 = S.buat_nota_kredit(cid, "2026-04-10", 250_000, inv4, cust, "refund",
                         "Pengembalian dana", user_id=1)
cek("Refund tercatat", cn2 > 0)


# ==========================================================================
bagian("PEMBELIAN: PO → BILL → PAYMENT")
po = S.buat_purchase_order(cid, "2026-02-01", [
    {"product_id": p1, "qty": 100, "harga_satuan": 42000},
], partner_id=vend, user_id=1)
po_row = db.q1("SELECT * FROM purchase_orders WHERE id=?", (po,))
cek("Purchase order dibuat", po > 0)
cek("PO punya nomor otomatis", po_row["nomor"].startswith("PO/2026/"))
cek("PO punya baris", len(S.detail_po(po)) == 1)

S.ubah_status_po(po, "dikonfirmasi")
cek("Status PO dapat diubah",
    db.q1("SELECT status FROM purchase_orders WHERE id=?", (po,))["status"] == "dikonfirmasi")

stok_sebelum = M.saldo_stok(cid, p1)["qty"]
bill = S.buat_bill(cid, "2026-02-10", [
    {"product_id": p1, "qty": 100, "harga_satuan": 42000},
], partner_id=vend, nomor_vendor="SUP-2026-0456", jenis="Persediaan",
    jenis_ppn="12% DPP Nilai Lain (11/12)", po_id=po, user_id=1)
bill_row = S.get_bill(bill)
cek("Bill dibuat dari PO", bill > 0)
cek("Bill punya nomor otomatis", bill_row["nomor"].startswith("BILL/2026/"))
cek("Nomor vendor tersimpan", bill_row["nomor_vendor"] == "SUP-2026-0456")
cek("PPN masukan dihitung", bill_row["ppn"] > 0, f"ppn={bill_row['ppn']}")
cek("Jatuh tempo vendor +14 hari", bill_row["jatuh_tempo"] == "2026-02-24",
    bill_row["jatuh_tempo"])

stok_setelah = M.saldo_stok(cid, p1)["qty"]
cek("Stok bertambah dari pembelian", stok_setelah == stok_sebelum + 100,
    f"sebelum={stok_sebelum} sesudah={stok_setelah}")

jurnal_bill = db.q1("SELECT * FROM journal_entries WHERE id=?",
                    (bill_row["journal_entry_id"],))
cek("Jurnal bill dibuat", jurnal_bill is not None)
if jurnal_bill:
    baris = services.detail_jurnal(jurnal_bill["id"])
    cek("Jurnal bill seimbang",
        sum(b["debit"] for b in baris) == sum(b["kredit"] for b in baris))

# Pembayaran sebagian ke vendor
bayar1 = bill_row["total"] // 3
S.bayar_vendor(cid, "2026-02-20", bayar1, [{"bill_id": bill, "jumlah": bayar1}],
               partner_id=vend, akun_kas="1002", user_id=1)
bill_row = S.get_bill(bill)
cek("Pembayaran vendor sebagian", bill_row["dibayar"] == bayar1)
cek("Status bill sebagian", bill_row["status"] == "sebagian")

S.bayar_vendor(cid, "2026-02-24", bill_row["sisa"],
               [{"bill_id": bill, "jumlah": bill_row["sisa"]}],
               partner_id=vend, akun_kas="1002", user_id=1)
bill_row = S.get_bill(bill)
cek("Bill lunas", bill_row["status"] == "lunas" and bill_row["sisa"] == 0)

# Retur pembelian
bill2 = S.buat_bill(cid, "2026-03-01", [
    {"product_id": p2, "qty": 50, "harga_satuan": 14000},
], partner_id=vend, jenis="Persediaan", jenis_ppn="Non-PKP/Tidak Dipungut", user_id=1)
bill2_row = S.get_bill(bill2)
stok_sebelum = M.saldo_stok(cid, p2)["qty"]
S.retur_pembelian(cid, "2026-03-05", bill2,
                  [{"product_id": p2, "qty": 10, "harga_satuan": 14000}],
                  "Barang cacat", user_id=1)
bill2_row = S.get_bill(bill2)
stok_setelah = M.saldo_stok(cid, p2)["qty"]
cek("Retur mengurangi total bill", bill2_row["total"] == 50 * 14000 - 140000,
    f"total={bill2_row['total']}")
cek("Retur mengurangi stok", stok_setelah == stok_sebelum - 10)


# ==========================================================================
bagian("PIUTANG, UTANG & AGING")
inv_lama = S.buat_invoice(cid, "2026-05-01",
                          [{"product_id": p1, "qty": 5, "harga_satuan": 75000}],
                          partner_id=cust, jenis_ppn="Non-PKP/Tidak Dipungut",
                          jatuh_tempo="2026-05-31", user_id=1)

ag = S.aging_piutang(cid)
cek("Aging piutang menghitung total", ag["total"] > 0, f"total={ag['total']}")
cek("Aging punya kelompok umur", len(ag["kelompok"]) == 5)
cek("Aging punya rincian", len(ag["rincian"]) > 0)
cek("Aging per pelanggan", len(ag["per_pelanggan"]) > 0)

ag_utang = S.aging_utang(cid)
cek("Aging utang berfungsi", "kelompok" in ag_utang)

cek("Piutang per pelanggan", len(S.piutang_per_pelanggan(cid)) >= 1)
cek("Piutang jatuh tempo terdeteksi", isinstance(S.piutang_jatuh_tempo(cid, 365), list))
cek("Utang jatuh tempo terdeteksi", isinstance(S.utang_jatuh_tempo(cid, 365), list))

ring = M.ringkasan_mitra(cust)
cek("Ringkasan mitra: total invoice", ring["total_invoice"] > 0)
cek("Ringkasan mitra: piutang", ring["piutang"] > 0)
cek("Ringkasan mitra: kredit tersisa",
    ring["kredit_tersisa"] == max(0, 100_000_000 - ring["piutang"]))
cek("Riwayat mitra terisi", len(M.riwayat_mitra(cust)) > 0)


# ==========================================================================
bagian("BIAYA (EXPENSE MANAGEMENT)")
kat1 = O.buat_kategori_biaya(cid, "Operasional", akun_beban="6003",
                             batas_nilai=1_000_000, perlu_persetujuan=True)
kat2 = O.buat_kategori_biaya(cid, "Marketing", akun_beban="6009")
cek("Kategori biaya dibuat", kat1 > 0 and kat2 > 0)

e1 = O.ajukan_biaya(cid, "2026-03-10", "Tagihan listrik Maret", 800_000,
                    "6003", kat1, vendor="PLN", user_id=1)
e1_row = O.daftar_biaya(cid, 2026, cari="listrik")[0]
cek("Biaya diajukan", e1 > 0)
cek("Biaya di atas batas perlu persetujuan", e1_row["status"] == "diajukan",
    e1_row["status"])

e2 = O.ajukan_biaya(cid, "2026-03-11", "Iklan Instagram", 500_000,
                    "6009", kat2, user_id=1)
e2_row = [b for b in O.daftar_biaya(cid, 2026) if b["id"] == e2][0]
cek("Biaya di bawah batas langsung disetujui", e2_row["status"] == "disetujui",
    e2_row["status"])

O.setujui_biaya(e1, True, "Manager", "Disetujui untuk dibayar")
e1_row = [b for b in O.daftar_biaya(cid, 2026) if b["id"] == e1][0]
cek("Persetujuan biaya berfungsi", e1_row["status"] == "disetujui")

O.bayar_biaya(e1, "2026-03-15", user_id=1)
e1_row = [b for b in O.daftar_biaya(cid, 2026) if b["id"] == e1][0]
cek("Pembayaran biaya berfungsi", e1_row["dibayar"] == 1)
cek("Jurnal biaya dibuat", e1_row["journal_entry_id"] is not None)

try:
    O.bayar_biaya(e1, user_id=1)
    cek("Biaya ganda ditolak", False)
except ValueError:
    cek("Biaya ganda ditolak", True)

cek("Ringkasan biaya per kategori", len(O.ringkasan_biaya(cid, 2026)) >= 1)

# Reimbursement
e3 = O.ajukan_biaya(cid, "2026-03-20", "Reimbursement transport", 350_000,
                    "6011", None, tipe="reimbursement", diajukan_oleh="Budi",
                    user_id=1)
e3_row = [b for b in O.daftar_biaya(cid, 2026) if b["id"] == e3][0]
cek("Reimbursement perlu persetujuan", e3_row["status"] == "diajukan",
    e3_row["status"])

# Biaya berkala
e4 = O.ajukan_biaya(cid, "2026-03-25", "Sewa kantor bulanan", 5_000_000,
                    "6006", None, tipe="berkala", user_id=1)
cek("Biaya berkala dibuat", e4 > 0)


# ==========================================================================
bagian("KAS & BANK")
kas_utama = O.daftar_kas_bank(cid)
cek("Akun kas/bank awal tersedia", len(kas_utama) >= 1, f"jumlah={len(kas_utama)}")

bank_baru = O.buat_kas_bank(cid, "Bank Mandiri Operasional", "bank",
                            nama_bank="Mandiri", nomor_rekening="1122334455",
                            saldo_awal=0, user_id=1)
cek("Rekening bank baru dibuat", bank_baru > 0)

kas_kecil = O.buat_kas_bank(cid, "Kas Kecil", "kas", user_id=1)
cek("Kas kecil dibuat", kas_kecil > 0)

ewallet = O.buat_kas_bank(cid, "GoPay Bisnis", "ewallet", user_id=1)
cek("E-wallet dibuat", ewallet > 0)

daftar_kb = O.daftar_kas_bank(cid)
cek("Daftar kas/bank lengkap", len(daftar_kb) >= 4, f"jumlah={len(daftar_kb)}")

saldo_kb = O.saldo_kas_bank(cid)
cek("Ringkasan saldo kas/bank", "total" in saldo_kb)

try:
    O.transfer_kas_bank(cid, "2026-04-01", "1001", "1001", 1_000_000)
    cek("Transfer ke rekening sama ditolak", False)
except ValueError:
    cek("Transfer ke rekening sama ditolak", True)

try:
    O.transfer_kas_bank(cid, "2026-04-01", "1002", "1002", 1_000_000)
    cek("Transfer antar rekening beda ditolak dengan benar", False)
except ValueError as e:
    cek("Transfer antar rekening beda ditolak dengan benar", "tidak boleh sama" in str(e))


# ==========================================================================
bagian("REKONSILIASI BANK")
bank_row = db.q1("SELECT * FROM bank_accounts WHERE company_id=? ORDER BY id LIMIT 1",
                 (cid,))
csv_mutasi = (
    "tanggal;uraian;referensi;debit;kredit;saldo\n"
    "2026-04-05;Transfer dari pelanggan;TRF-A;15000000;0;15000000\n"
    "2026-04-08;Pembayaran listrik;PLN-B;0;800000;14200000\n"
    "2026-04-10;Biaya administrasi bank;ADM-C;0;50000;14150000\n"
)
hasil_impor = O.impor_mutasi_dari_csv(cid, bank_row["id"], csv_mutasi)
cek("Impor mutasi CSV berhasil", hasil_impor["berhasil"] == 3,
    f"hasil={hasil_impor}")

hasil_ulang = O.impor_mutasi_dari_csv(cid, bank_row["id"], csv_mutasi)
cek("Deteksi duplikat impor berfungsi",
    hasil_ulang["duplikat"] == 3 and hasil_ulang["berhasil"] == 0,
    f"hasil={hasil_ulang}")

mutasi = O.daftar_mutasi_bank(cid, bank_row["id"])
cek("Mutasi bank tersimpan", len(mutasi) == 3, f"jumlah={len(mutasi)}")
cek("Status mutasi awal 'belum'", all(m["status"] == "belum" for m in mutasi))

belum = O.mutasi_belum_cocok(cid, bank_row["id"])
cek("Daftar mutasi belum cocok", len(belum) == 3)

O.jurnal_dari_mutasi(cid, mutasi[0]["id"], "1101", user_id=1)
mutasi = O.daftar_mutasi_bank(cid, bank_row["id"])
tercocok = [m for m in mutasi if m["status"] == "tercocok"]
cek("Jurnal dari mutasi berhasil", len(tercocok) == 1, f"tercocok={len(tercocok)}")

O.cocokkan_mutasi(mutasi[1]["id"], None, user_id=1)
mutasi = O.daftar_mutasi_bank(cid, bank_row["id"])
dikecualikan = [m for m in mutasi if m["status"] == "dikecualikan"]
cek("Mutasi dapat dikecualikan", len(dikecualikan) == 1)

rec = O.buat_rekonsiliasi(cid, bank_row["id"], "2026-04", 14_150_000, "Admin")
cek("Rekonsiliasi bank dibuat", rec > 0)
rec_row = db.q1("SELECT * FROM bank_reconciliations WHERE id=?", (rec,))
cek("Selisih rekonsiliasi dihitung", "selisih" in rec_row.keys())

O.selesaikan_rekonsiliasi(rec, "Sudah ditelusuri", user_id=1)
rec_row = db.q1("SELECT * FROM bank_reconciliations WHERE id=?", (rec,))
cek("Rekonsiliasi dapat diselesaikan", rec_row["status"] == "selesai")

cek("Daftar rekonsiliasi", len(O.daftar_rekonsiliasi(cid)) == 1)


# ==========================================================================
bagian("DIMENSI: COST CENTER, PROYEK, CABANG")
cc1 = O.buat_cost_center(cid, "Marketing", penanggung_jawab="Sari",
                         anggaran=20_000_000)
cc2 = O.buat_cost_center(cid, "Produksi", anggaran=50_000_000)
prj1 = O.buat_proyek(cid, "Website Redesign", nilai_kontrak=75_000_000,
                     tanggal_mulai="2026-01-01", partner_id=cust)
prj2 = O.buat_proyek(cid, "Aplikasi Mobile", nilai_kontrak=150_000_000,
                     tanggal_mulai="2026-02-01")
cab1 = O.buat_cabang(cid, "Cabang Bandung", kota="Bandung",
                     penanggung_jawab="Andi")
cek("Cost center dibuat", cc1 > 0 and cc2 > 0)
cek("Proyek dibuat", prj1 > 0 and prj2 > 0)
cek("Cabang dibuat", cab1 > 0)
cek("Daftar cost center", len(O.daftar_cost_center(cid)) == 2)
cek("Daftar proyek", len(O.daftar_proyek(cid)) == 2)
cek("Daftar cabang", len(O.daftar_cabang(cid)) == 1)

# Biaya dengan dimensi
e_dim = O.ajukan_biaya(cid, "2026-04-01", "Iklan proyek website", 2_000_000,
                       "6009", kat2, cost_center_id=cc1, project_id=prj1,
                       branch_id=cab1, user_id=1)
cek("Biaya dengan dimensi dibuat", e_dim > 0)

laporan_dim = O.laba_rugi_dimensi(cid, 2026, "cost_center")
cek("Laporan per cost center", len(laporan_dim) == 2)
laporan_prj = O.laba_rugi_dimensi(cid, 2026, "proyek")
cek("Laporan per proyek", len(laporan_prj) == 2)


# ==========================================================================
bagian("TATA KELOLA: IZIN, RIWAYAT, RECYCLE BIN")
izin_owner = M.izin_peran("owner")
izin_staf = M.izin_peran("staff")
izin_viewer = M.izin_peran("viewer")
cek("Owner punya semua izin", len(izin_owner) == 50, f"jumlah={len(izin_owner)}")
cek("Staf izin terbatas", len(izin_staf) < len(izin_owner),
    f"staff={len(izin_staf)}")
cek("Viewer paling terbatas", len(izin_viewer) < len(izin_staf),
    f"viewer={len(izin_viewer)}")

cek("Staf bisa buat jurnal", "jurnal.buat" in izin_staf)
cek("Staf tidak bisa hapus jurnal", "jurnal.hapus" not in izin_staf)
cek("Viewer tidak bisa input", "jurnal.buat" not in izin_viewer)

M.set_izin_pengguna(uid2, "jurnal.hapus", True)
cek("Izin khusus pengguna ditambahkan",
    "jurnal.hapus" in M.izin_pengguna(uid2, "staff"))

M.set_izin_pengguna(uid2, "jurnal.hapus", False)
cek("Izin khusus pengguna dicabut",
    "jurnal.hapus" not in M.izin_pengguna(uid2, "staff"))

M.set_izin_peran("staff", "laporan.ekspor", True)
cek("Izin peran dapat diubah", "laporan.ekspor" in M.izin_peran("staff"))
M.set_izin_peran("staff", "laporan.ekspor", False)

cek("Modul izin terdaftar", len(M.modul_izin()) >= 15,
    f"modul={len(M.modul_izin())}")

# Riwayat perubahan
riwayat = O.riwayat_perubahan(cid, limit=100)
cek("Riwayat perubahan tercatat", len(riwayat) > 0, f"jumlah={len(riwayat)}")

# Soft delete + recycle bin
cust_hapus = M.buat_mitra(cid, "Customer Akan Dihapus", "customer")
M.hapus_mitra(cust_hapus, "Admin")
cek("Soft delete mitra berfungsi",
    M.get_mitra(cust_hapus)["deleted_at"] is not None)
cek("Mitra terhapus tidak muncul di daftar",
    all(m["id"] != cust_hapus for m in M.daftar_mitra(cid)))

recycle = O.daftar_recycle_bin(cid)
cek("Recycle bin terisi", len(recycle) >= 1, f"jumlah={len(recycle)}")

item_recycle = [r for r in recycle if r["tabel"] == "partners" and
                r["record_id"] == cust_hapus]
if item_recycle:
    hasil_pulih = O.pulihkan_dari_recycle(item_recycle[0]["id"], "Admin")
    cek("Pemulihan dari recycle bin", hasil_pulih["dipulihkan"])
    cek("Mitra aktif kembali",
        all(m["id"] != cust_hapus for m in M.daftar_mitra(cid)) is False)

# Riwayat per record
hist = O.riwayat_perubahan(cid, "partners", cust_hapus)
cek("Riwayat per record tersedia", len(hist) >= 1, f"jumlah={len(hist)}")


# ==========================================================================
bagian("DOKUMEN & LAMPIRAN")
berkas_uji = os.path.join(DATA_UJI, "lampiran_uji.txt")
with open(berkas_uji, "w", encoding="utf-8") as f:
    f.write("Ini berkas lampiran uji untuk invoice.\n" * 10)

doc1 = O.lampirkan_dokumen(cid, "invoices", inv, berkas_uji, "invoice",
                           "Bukti invoice", "Admin")
cek("Dokumen dilampirkan", doc1 > 0)
cek("Dokumen tercatat", len(O.daftar_dokumen(cid, "invoices", inv)) == 1)

doc_row = db.q1("SELECT * FROM documents WHERE id=?", (doc1,))
cek("Berkas tersalin ke folder lampiran", os.path.isfile(doc_row["path_berkas"]))

doc2 = O.lampirkan_dokumen(cid, "invoices", inv, berkas_uji, "faktur",
                           "Faktur pajak", "Admin")
cek("Versi dokumen kedua tersimpan",
    len(O.daftar_dokumen(cid, "invoices", inv)) == 2)
doc2_row = db.q1("SELECT * FROM documents WHERE id=?", (doc2,))
cek("Penamaan versi berbeda", doc2_row["path_berkas"] != doc_row["path_berkas"])

O.hapus_dokumen(doc1, "Admin")
cek("Dokumen dapat dihapus", len(O.daftar_dokumen(cid, "invoices", inv)) == 1)


# ==========================================================================
bagian("TRANSAKSI BERULANG")
tmpl = O.buat_template_berulang(cid, "Sewa Kantor Bulanan", "expense",
                                "2026-01-01", {
                                    "uraian": "Sewa kantor",
                                    "jumlah": 5_000_000,
                                    "akun_beban": "6006",
                                }, frekuensi="bulanan", maks_kali=3)
cek("Template berulang dibuat", tmpl > 0)
cek("Daftar template", len(O.daftar_template_berulang(cid)) == 1)

hasil_jalan = O.jalankan_template_berulang(cid, "2026-03-31", user_id=1)
cek("Template berulang dijalankan", hasil_jalan["jumlah_dibuat"] >= 1,
    f"dibuat={hasil_jalan['jumlah_dibuat']} gagal={hasil_jalan['jumlah_gagal']}")
cek("Tidak ada kegagalan template", hasil_jalan["jumlah_gagal"] == 0,
    str(hasil_jalan["gagal"]))

tmpl_row = db.q1("SELECT * FROM recurring_templates WHERE id=?", (tmpl,))
cek("Jumlah terbuat tercatat", tmpl_row["jumlah_terbuat"] >= 1)

# Template jurnal
tmpl_j = O.buat_template_berulang(cid, "Penyusutan Bulanan", "jurnal",
                                  "2026-01-31", {
                                      "keterangan": "Penyusutan bulanan",
                                      "baris": [
                                          {"kode_akun": "6007", "debit": 1_000_000,
                                           "kredit": 0},
                                          {"kode_akun": "1202", "debit": 0,
                                           "kredit": 1_000_000},
                                      ],
                                  }, frekuensi="bulanan", maks_kali=2)
hasil_j2 = O.jalankan_template_berulang(cid, "2026-02-28", user_id=1)
cek("Template jurnal berjalan", hasil_j2["jumlah_dibuat"] >= 1)

O.hapus_template_berulang(tmpl_j)
cek("Template dapat dihapus",
    len(O.daftar_template_berulang(cid)) == 1)


# ==========================================================================
bagian("PENGINGAT (REMINDER)")
rem = O.buat_reminder(cid, "Bayar sewa gudang", "2026-05-01", tipe="umum",
                      jumlah=3_000_000, hari_ingat=7)
cek("Pengingat dibuat", rem > 0)
cek("Daftar pengingat", len(O.daftar_reminder(cid)) >= 1)

jumlah_rem_piutang = O.buat_reminder_dari_piutang(cid, 365)
cek("Pengingat piutang otomatis dibuat", jumlah_rem_piutang >= 1,
    f"dibuat={jumlah_rem_piutang}")

jumlah_rem_utang = O.buat_reminder_dari_utang(cid, 365)
cek("Pengingat utang otomatis dibuat", isinstance(jumlah_rem_utang, int))

O.selesaikan_reminder(rem)
row_rem = db.q1("SELECT status FROM reminders WHERE id=?", (rem,))
cek("Pengingat dapat diselesaikan", row_rem["status"] == "selesai")

cek("Pengingat jatuh tempo", isinstance(O.reminder_jatuh_tempo(cid, 365), list))


# ==========================================================================
bagian("TUTUP BUKU & BUKA BUKU")
cek("Periode awal terbuka", O.status_periode(cid, "2026-01") == "terbuka")

daftar_periode = O.daftar_periode(cid, 2026)
cek("Daftar periode 12 bulan", len(daftar_periode) == 12)
cek("Periode punya data laba", all("laba" in p for p in daftar_periode))

hasil_tutup = O.tutup_buku(cid, "2026-01", "Admin", user_id=1,
                           buat_jurnal_penutup=True)
cek("Tutup buku berhasil", hasil_tutup["periode"] == "2026-01")
cek("Status menjadi tertutup", O.status_periode(cid, "2026-01") == "tertutup")
cek("Jurnal penutup dibuat", hasil_tutup["journal_entry_id"] is not None)

try:
    O.tutup_buku(cid, "2026-01", "Admin", user_id=1)
    cek("Tutup buku ganda ditolak", False)
except ValueError:
    cek("Tutup buku ganda ditolak", True)

try:
    O.buka_buku(cid, "2026-02", "Admin", user_id=1)
    cek("Buka periode terbuka ditolak", False)
except ValueError:
    cek("Buka periode terbuka ditolak", True)

O.buka_buku(cid, "2026-01", "Admin", user_id=1, hapus_jurnal_penutup=True)
cek("Buka buku berhasil", O.status_periode(cid, "2026-01") == "terbuka")

cek("Periode tertutup terakhir", isinstance(O.periode_tertutup_sampai(cid), str))


# ==========================================================================
bagian("PENOMORAN OTOMATIS")
nomor1 = M.nomor_berikut(cid, "INV", 2026)
nomor2 = M.nomor_berikut(cid, "INV", 2026)
cek("Nomor berurutan", nomor1 != nomor2, f"{nomor1} vs {nomor2}")

M.set_pola_nomor(cid, "SO", "SALES", "SALES-{tahun}-{urut:05d}", True)
nomor_so = M.nomor_berikut(cid, "SO", 2026)
cek("Pola nomor khusus berfungsi", nomor_so.startswith("SALES-2026-"),
    nomor_so)

pratinjau = M.pratinjau_nomor(cid, "PO")
nomor_po = M.nomor_berikut(cid, "PO", 2026)
cek("Pratinjau sesuai nomor berikutnya", pratinjau == nomor_po,
    f"pratinjau={pratinjau} aktual={nomor_po}")

daftar_pola = M.daftar_pola_nomor(cid)
cek("Daftar pola nomor lengkap", len(daftar_pola) >= 15,
    f"jumlah={len(daftar_pola)}")

nomor_tahun_lain = M.nomor_berikut(cid, "INV", 2027)
cek("Reset nomor tiap tahun", "/2027/" in nomor_tahun_lain, nomor_tahun_lain)


# ==========================================================================
bagian("IMPOR MASSAL")
csv_customer = (
    "nama;npwp;email;telepon;alamat;kota\n"
    "PT Impor Satu;04.111.222.3-444.000;satu@impor.co.id;021-1111;Jl. A;Jakarta\n"
    "PT Impor Dua;05.222.333.4-555.000;dua@impor.co.id;021-2222;Jl. B;Bandung\n"
    "PT Pelanggan Utama (Revisi);02.111.222.3-444.000;;;;\n"
)
hasil_impor_cust = O.impor_mitra_massal(cid, csv_customer, "customer", user_id=1)
cek("Impor customer: 2 berhasil", hasil_impor_cust["berhasil"] == 2,
    str(hasil_impor_cust))
cek("Impor customer: 1 duplikat terdeteksi",
    hasil_impor_cust["duplikat"] == 1, str(hasil_impor_cust))

csv_produk = (
    "kode;nama;satuan;tipe;harga_beli;harga_jual;stok\n"
    "P0100;Teh Hijau 100g;box;barang;25000;40000;80\n"
    "P0101;Kopi Robusta 250g;box;barang;35000;60000;60\n"
    "P0001;Kopi Arabika 250g;pcs;barang;45000;75000;10\n"
)
hasil_impor_prod = O.impor_produk_massal(cid, csv_produk, user_id=1)
cek("Impor produk: 2 berhasil", hasil_impor_prod["berhasil"] == 2,
    str(hasil_impor_prod))
cek("Impor produk: 1 duplikat",
    hasil_impor_prod["duplikat"] == 1, str(hasil_impor_prod))

csv_jurnal = (
    "tanggal;no_bukti;keterangan;kode_akun;debit;kredit\n"
    "2026-06-01;IMP-001;Penerimaan jasa;1002;25000000;0\n"
    "2026-06-01;IMP-001;Pendapatan jasa;4001;0;25000000\n"
    "2026-06-02;IMP-002;Setoran modal;1002;10000000;0\n"
    "2026-06-02;IMP-002;Modal disetor;3001;0;10000000\n"
)
hasil_impor_jurnal = O.impor_jurnal_massal(cid, csv_jurnal, user_id=1)
cek("Impor jurnal: 2 entri", hasil_impor_jurnal["berhasil"] == 2,
    str(hasil_impor_jurnal))

cek("Template CSV customer", len(O.template_csv("customer")) > 0)
cek("Template CSV produk", len(O.template_csv("produk")) > 0)
cek("Template CSV jurnal", len(O.template_csv("jurnal")) > 0)


# ==========================================================================
bagian("PENCARIAN GLOBAL & FILTER LANJUTAN")
hasil_cari = O.cari_global(cid, "Pelanggan")
cek("Pencarian global menemukan hasil", len(hasil_cari) > 0,
    f"jumlah={len(hasil_cari)}")
jenis_ditemukan = {h["jenis"] for h in hasil_cari}
cek("Pencarian lintas entitas", len(jenis_ditemukan) >= 1,
    str(jenis_ditemukan))

hasil_cari_kosong = O.cari_global(cid, "x")
cek("Pencarian terlalu pendek diabaikan", len(hasil_cari_kosong) == 0)

f1 = O.filter_invoice_lanjutan(cid, status="belum_lunas")
cek("Filter invoice belum lunas", all(i["status"] not in ("lunas", "batal")
                                      for i in f1), f"jumlah={len(f1)}")

f2 = O.filter_invoice_lanjutan(cid, jumlah_min=100_000)
cek("Filter invoice jumlah minimum", all(i["total"] >= 100_000 for i in f2))

f3 = O.filter_invoice_lanjutan(cid, tanggal_dari="2026-01-01",
                               tanggal_sampai="2026-12-31")
cek("Filter invoice rentang tanggal", len(f3) > 0)

f4 = O.filter_invoice_lanjutan(cid, urut="jumlah_desc", limit=3)
cek("Filter dengan urutan & limit", len(f4) <= 3)

f5 = O.filter_jurnal_lanjutan(cid, sumber="manual")
cek("Filter jurnal per sumber", all(j["sumber"] == "manual" for j in f5))

f6 = O.filter_jurnal_lanjutan(cid, tanggal_dari="2026-01-01",
                              tanggal_sampai="2026-12-31")
cek("Filter jurnal rentang tanggal", len(f6) > 0)


# ==========================================================================
bagian("KONSOLIDASI MULTI-ENTITAS")
grup = O.buat_grup_entitas("Grup Usaha Uji", "Uji konsolidasi")
cek("Grup entitas dibuat", grup > 0)

O.tambah_anggota_grup(grup, cid, 100.0)
O.tambah_anggota_grup(grup, cid_umkm, 80.0)
cek("Anggota grup ditambahkan", len(O.anggota_grup(grup)) == 2)

konsol = O.laporan_konsolidasi(grup, 2026)
cek("Konsolidasi dihitung", konsol["jumlah_entitas"] == 2)
cek("Konsolidasi punya total aset", konsol["total"]["aset"] > 0,
    f"aset={konsol['total']['aset']}")
cek("Konsolidasi per entitas", len(konsol["per_entitas"]) == 2)
cek("Catatan eliminasi tersedia", len(konsol["catatan"]) > 0)


# ==========================================================================
bagian("AKSES JARINGAN LOKAL (LAN)")
info = O.info_lan()
cek("Konfigurasi LAN tersedia", "port" in info)
cek("IP lokal terdeteksi", len(info["ip_lokal"]) > 0, info["ip_lokal"])

O.set_lan(aktif=True, port=9090, mode="server")
info = O.info_lan()
cek("Konfigurasi LAN dapat diubah", info["aktif"] == 1 and info["port"] == 9090)

token = O.token_lan_baru()
cek("Token LAN dibuat", len(token) > 20)

O.set_lan(mode="client", server_host="192.168.1.100", server_port=9090)
info = O.info_lan()
cek("Mode client dapat diatur", info["mode"] == "client")

try:
    O.set_lan(mode="mode_salah")
    cek("Mode LAN salah ditolak", False)
except ValueError:
    cek("Mode LAN salah ditolak", True)

uji = O.uji_koneksi_lan("127.0.0.1", 1, timeout=0.5)
cek("Uji koneksi LAN berfungsi", "ok" in uji)


# ==========================================================================
bagian("LAPORAN & ANALISIS")
lr = acc.laba_rugi(cid, 2026)
cek("Laba rugi dihitung", lr.pendapatan_usaha > 0,
    f"pendapatan={lr.pendapatan_usaha}")
cek("HPP terhitung", lr.hpp >= 0)
cek("Laba kotor konsisten", lr.laba_kotor == lr.pendapatan_usaha - lr.hpp)
cek("Laba operasional konsisten",
    lr.laba_operasional == lr.laba_kotor - lr.beban_operasional)

nr = acc.neraca(cid, 2026)
cek("Neraca seimbang", nr.seimbang,
    f"aset={nr.total_aset} L+E={nr.total_liabilitas_ekuitas} selisih={nr.selisih}")

cek_tb = acc.total_neraca_saldo(cid, 2026)
cek("Total debit = total kredit", cek_tb["seimbang"],
    f"debit={cek_tb['debit']} kredit={cek_tb['kredit']}")

ak = acc.arus_kas(cid, 2026)
cek("Arus kas dihitung", "total_operasi" in dir(ak))
cek("Arus kas seimbang", ak.seimbang, f"selisih={ak.selisih}")

bb = acc.buku_besar(cid, "1002", 2026)
cek("Buku besar berfungsi", len(bb) > 0, f"baris={len(bb)}")

perubahan = acc.perubahan_ekuitas(cid, 2026)
cek("Perubahan ekuitas", len(perubahan) > 0)

ringkasan = acc.ringkasan_bulanan(cid, 2026)
cek("Ringkasan bulanan 12 bulan", len(ringkasan) == 12)

kpi = acc.dashboard_kpi(cid, 2026)
cek("KPI dashboard", kpi["omzet"] > 0)
cek("KPI menyertakan kas", "kas" in kpi)

analisis = an.analisis_kesehatan(cid, 2026)
cek("Analisis kesehatan berjalan", analisis.skor >= 0)
cek("Analisis punya temuan", len(analisis.temuan) > 0)
cek("Analisis punya ringkasan", len(analisis.ringkasan) > 0)
cek("Neraca seimbang → tidak ada temuan kritis neraca",
    not any("Neraca tidak seimbang" in t.judul for t in analisis.temuan),
    f"kritis={analisis.jumlah_kritis}")

proyeksi = an.proyeksi_sederhana(cid, 2026)
cek("Proyeksi berfungsi", "proyeksi_laba_tahun" in proyeksi)

simulasi = an.simulasi_skenario(cid, 2026, 20.0, -10.0)
cek("Simulasi skenario", simulasi["laba_baru"] != simulasi["laba_sekarang"])


# ==========================================================================
bagian("PERPAJAKAN")
omzet = acc.omzet_setahun(cid, 2026)
cek("Omzet terhitung", omzet > 0, f"omzet={omzet}")

pph_badan = services.hitung_pph_badan_tahunan(cid, 2026)
cek("PPh Badan dihitung", pph_badan["pph_terutang"] >= 0)
cek("Skema PPh teridentifikasi", len(pph_badan["skema"]) > 0)

rekon = services.hitung_rekonsiliasi(cid, 2026)
cek("Rekonsiliasi fiskal dihitung", rekon.pkp >= 0, f"pkp={rekon.pkp}")

r31e = tx.hitung_pph_badan(3_000_000_000, 300_000_000)
cek("Pasal 31E omzet ≤4,8M: tarif 11%",
    r31e.pph_terutang == 300_000_000 * 11 // 100,
    f"pph={r31e.pph_terutang}")

r31e2 = tx.hitung_pph_badan(20_000_000_000, 2_000_000_000)
fasilitas = int(4_800_000_000 / 20_000_000_000 * 2_000_000_000)
target = int(fasilitas * 0.11) + int((2_000_000_000 - fasilitas) * 0.22)
cek("Pasal 31E proporsional benar",
    abs(r31e2.pph_terutang - target) < 1000,
    f"pph={r31e2.pph_terutang} target={target}")

r22 = tx.hitung_pph_badan(60_000_000_000, 2_000_000_000)
cek("Omzet >50M pakai tarif 22%",
    r22.pph_terutang == 2_000_000_000 * 22 // 100, f"pph={r22.pph_terutang}")

ppn = tx.hitung_ppn(10_000_000, "12% DPP Nilai Lain (11/12)")
cek("PPN efektif 11%", ppn.ppn == 1_100_000, f"ppn={ppn.ppn}")
cek("DPP nilai lain 11/12", ppn.dpp_faktur == int(round(10_000_000 * 11 / 12)),
    f"dpp={ppn.dpp_faktur}")

ppn_mewah = tx.hitung_ppn(100_000_000, "12% DPP Penuh (Mewah)")
cek("PPN mewah 12% DPP penuh", ppn_mewah.ppn == 12_000_000)

ppn_nol = tx.hitung_ppn(10_000_000, "Non-PKP/Tidak Dipungut")
cek("Non-PKP tanpa PPN", ppn_nol.ppn == 0)

ter = tx.pph21_bulanan_ter(8_000_000, "TK/0")
cek("PPh 21 TER kategori A", ter.kategori_ter == "A", ter.kategori_ter)
cek("PPh 21 TER tarif benar", ter.tarif_ter == 0.015, f"tarif={ter.tarif_ter}")

cek("Pemetaan TER K/1 ke kategori B",
    tx.ter_category("K/1") == "B", tx.ter_category("K/1"))
cek("Pemetaan TER K/3 ke kategori C",
    tx.ter_category("K/3") == "C", tx.ter_category("K/3"))
cek("Pemetaan TER TK/0 ke kategori A",
    tx.ter_category("TK/0") == "A")

harian1 = tx.pph21_harian_ter(400_000)
cek("TER harian ≤450rb bebas pajak", harian1.pph21_ter == 0)
harian2 = tx.pph21_harian_ter(1_000_000)
cek("TER harian 0,5%", harian2.pph21_ter == 5_000, f"pph={harian2.pph21_ter}")

setahun = tx.pph21_setahun(120_000_000, "K/1")
cek("PPh 21 setahun dihitung", setahun.pph21_setahun > 0)
cek("Biaya jabatan dibatasi Rp6 juta",
    tx.biaya_jabatan(200_000_000) == 6_000_000,
    f"biaya={tx.biaya_jabatan(200_000_000)}")

bpjs = tx.hitung_bpjs(10_000_000)
cek("BPJS karyawan dihitung", bpjs.total_karyawan > 0)
cek("BPJS perusahaan dihitung", bpjs.total_perusahaan > 0)

pph23 = tx.hitung_pph23(10_000_000, "jasa")
cek("PPh 23 jasa 2%", pph23.pajak == 200_000, f"pajak={pph23.pajak}")

pph23b = tx.hitung_pph23(10_000_000, "bunga")
cek("PPh 23 bunga 15%", pph23b.pajak == 1_500_000)

pph4 = tx.hitung_pph4_final(100_000_000, "sewa_tanah")
cek("PPh 4(2) sewa 10%", pph4.pajak == 10_000_000)

pph22 = tx.hitung_pph22(100_000_000, "impor_api")
cek("PPh 22 impor 2,5%", pph22.pajak == 2_500_000)

pph26 = tx.hitung_pph26(100_000_000)
cek("PPh 26 20%", pph26.pajak == 20_000_000)

sanksi_bunga = tx.hitung_bunga_keterlambatan(10_000_000, 3)
cek("Bunga keterlambatan dihitung", sanksi_bunga["bunga"] > 0)
cek("Total = pokok + bunga",
    sanksi_bunga["total_bayar"] == 10_000_000 + sanksi_bunga["bunga"])

sanksi_denda = tx.hitung_sanksi_telat_lapor("badan")
cek("Denda SPT badan Rp1 juta", sanksi_denda["denda"] == 1_000_000)

sanksi_kb = tx.hitung_sanksi_kurang_bayar(10_000_000, 24)
cek("Sanksi kurang bayar 2%/bulan", sanksi_kb["bunga"] == 10_000_000 * 0.02 * 24,
    f"bunga={sanksi_kb['bunga']}")

cek("Pembulatan PKP ribuan ke bawah",
    tx.round_down_thousand(1_234_567) == 1_234_000)

status_pkp = tx.status_pkp(5_000_000_000, False)
cek("Deteksi wajib PKP", status_pkp["wajib_pkp"] and status_pkp["level"] == "danger")

rekap = tx.rekap_ppn(10_000_000, 4_000_000)
cek("Rekap PPN kurang bayar", rekap["kurang_bayar"] == 6_000_000)
rekap2 = tx.rekap_ppn(4_000_000, 10_000_000)
cek("Rekap PPN lebih bayar", rekap2["lebih_bayar"] == 6_000_000)

# Pajak potput & setoran
potput = services.simpan_pajak(cid, "2026-07-01", "PPh23-JASA", 10_000_000,
                               None, "2026-07", user_id=1)
cek("Pajak potput dicatat", potput > 0)

bayar_pajak = services.catat_pembayaran_pajak(
    cid, "PPh23", "2026-07", "2026-08-10", 200_000, "NTPN123456", user_id=1)
cek("Setoran pajak dicatat", bayar_pajak > 0)

cek("Daftar pajak", len(services.list_pajak(cid, 2026)) >= 1)
cek("Daftar setoran", len(services.list_pembayaran_pajak(cid, 2026)) >= 1)

deadline = services.deadline_pajak(cid)
cek("Deadline pajak dihitung", len(deadline) > 0)


# ==========================================================================
bagian("ASET TETAP & PENYUSUTAN")
aset1 = services.simpan_aset(cid, "AT-0001", "Laptop Tim Dev", "2026-01-15",
                             25_000_000, "Kelompok 1", "Garis Lurus", 4, 0, 0,
                             user_id=1)
aset2 = services.simpan_aset(cid, "AT-0002", "Kendaraan Operasional",
                             "2026-02-01", 250_000_000, "Kelompok 2",
                             "Garis Lurus", 8, 0, 0, user_id=1)
cek("Aset tetap dibuat", aset1 > 0 and aset2 > 0)

hasil_susut = services.hitung_penyusutan_tahun(cid, 2026, user_id=1)
cek("Penyusutan dihitung", len(hasil_susut) == 2, f"jumlah={len(hasil_susut)}")

rekap_susut = services.rekap_penyusutan(cid, 2026)
cek("Rekap penyusutan", rekap_susut["total_komersial"] > 0,
    f"komersial={rekap_susut['total_komersial']}")
cek("Penyusutan fiskal dihitung", rekap_susut["total_fiskal"] > 0)

susut_laptop = [h for h in hasil_susut if h["kode_aset"] == "AT-0001"][0]
cek("Prorata bulan perolehan", susut_laptop["bulan"] == 12,
    f"bulan={susut_laptop['bulan']}")

susut_kendaraan = [h for h in hasil_susut if h["kode_aset"] == "AT-0002"][0]
cek("Prorata Februari = 11 bulan", susut_kendaraan["bulan"] == 11,
    f"bulan={susut_kendaraan['bulan']}")

cek("Daftar aset", len(services.list_aset(cid)) == 2)


# ==========================================================================
bagian("PAYROLL")
emp1 = services.simpan_karyawan(cid, "Andi Wijaya", 12_000_000, "Programmer",
                                "K/1", 2_000_000)
emp2 = services.simpan_karyawan(cid, "Siti Nurhaliza", 8_000_000, "Admin",
                                "TK/0", 500_000)
cek("Karyawan didaftarkan", emp1 > 0 and emp2 > 0)
cek("Daftar karyawan", len(services.list_karyawan(cid)) == 2)

payroll = services.hitung_payroll_bulanan(cid, "2026-08", {}, user_id=1,
                                          posting=True)
cek("Payroll dihitung", payroll["total_bruto"] > 0,
    f"bruto={payroll['total_bruto']}")
cek("PPh 21 dipotong", payroll["total_pph21"] >= 0,
    f"pph21={payroll['total_pph21']}")
cek("Take home pay dihitung", payroll["total_thp"] > 0)
cek("Beban perusahaan dihitung", payroll["total_beban"] > payroll["total_bruto"])

detail = services.detail_payroll(payroll["run_id"])
cek("Detail payroll tersimpan", len(detail) == 2)

run_row = db.q1("SELECT * FROM payroll_runs WHERE id=?", (payroll["run_id"],))
cek("Payroll ter-posting", run_row["status"] == "posted")
cek("Jurnal payroll dibuat", run_row["journal_entry_id"] is not None)

if run_row["journal_entry_id"]:
    baris = services.detail_jurnal(run_row["journal_entry_id"])
    cek("Jurnal payroll seimbang",
        sum(b["debit"] for b in baris) == sum(b["kredit"] for b in baris),
        f"d={sum(b['debit'] for b in baris)} k={sum(b['kredit'] for b in baris)}")

# Payroll Desember (skema setahun)
payroll_des = services.hitung_payroll_bulanan(cid, "2026-12", {}, user_id=1,
                                              posting=True)
cek("Payroll Desember berjalan", payroll_des["total_bruto"] > 0)
detail_des = services.detail_payroll(payroll_des["run_id"])
cek("Desember pakai perhitungan setahun",
    "Setahun" in (detail_des[0]["metode_pph21"] or ""),
    detail_des[0]["metode_pph21"])

cek("Daftar payroll", len(services.list_payroll(cid, 2026)) == 2)

# Bonus
payroll_bonus = services.hitung_payroll_bulanan(cid, "2026-09",
                                                {emp1: 10_000_000}, user_id=1)
cek("Bonus masuk perhitungan", payroll_bonus["total_bruto"] > 0)


# ==========================================================================
bagian("CHECKLIST KEPATUHAN")
items = services.list_checklist(cid)
cek("Checklist default terisi", len(items) >= 14, f"jumlah={len(items)}")

services.update_checklist(items[0]["id"], status="Selesai", pic="Budi",
                          catatan="Sudah direkonsiliasi")
item_row = db.q1("SELECT * FROM checklist_items WHERE id=?", (items[0]["id"],))
cek("Checklist dapat diubah", item_row["status"] == "Selesai")

item_baru = services.tambah_checklist(cid, "Bulanan", "Kustom", "Cek uji khusus")
cek("Item checklist ditambahkan", item_baru > 0)
services.hapus_checklist(item_baru)
cek("Item checklist dihapus",
    len(services.list_checklist(cid)) == len(items))


# ==========================================================================
bagian("BACKUP & PEMULIHAN")
path_backup = db.create_backup("Uji cadangan")
cek("Cadangan dibuat", os.path.isfile(path_backup))
cek("Cadangan tercatat di database",
    db.scalar("SELECT COUNT(*) FROM backups") >= 1)
cek("Ukuran cadangan wajar", os.path.getsize(path_backup) > 10_000,
    f"ukuran={os.path.getsize(path_backup)}")


# ==========================================================================
bagian("MULTI-PERUSAHAAN")
daftar_perusahaan = services.list_companies()
cek("Dua perusahaan terdaftar", len(daftar_perusahaan) == 2,
    f"jumlah={len(daftar_perusahaan)}")

comp1 = services.get_company(cid)
services.update_company(cid, nama="PT Uji Lengkap (Revisi)",
                        alamat="Jl. Baru 123", telepon="021-9999999")
comp1 = services.get_company(cid)
cek("Data perusahaan dapat diubah", comp1["nama"] == "PT Uji Lengkap (Revisi)")
cek("Alamat tersimpan", comp1["alamat"] == "Jl. Baru 123")

services.update_company(cid, status_pkp=True, nomor_pkp="01.234.567.8-901.000")
cek("Status PKP tersimpan",
    services.get_company(cid)["nomor_pkp"] == "01.234.567.8-901.000")

lr_umkm = acc.laba_rugi(cid_umkm, 2026)
cek("Perusahaan kedua terpisah", lr_umkm.pendapatan_usaha == 0,
    f"pendapatan={lr_umkm.pendapatan_usaha}")


# ==========================================================================
bagian("INTEGRITAS AKHIR")
cek_final = acc.total_neraca_saldo(cid, 2026)
cek("SEMUA JURNAL SEIMBANG", cek_final["seimbang"],
    f"selisih={cek_final['selisih']}")

nr_final = acc.neraca(cid, 2026)
cek("NERACA SEIMBANG", nr_final.seimbang,
    f"aset={nr_final.total_aset} L+E={nr_final.total_liabilitas_ekuitas} "
    f"selisih={nr_final.selisih}")

tdk_seimbang = acc.cek_jurnal_tidak_seimbang(cid)
cek("Tidak ada jurnal tidak seimbang", len(tdk_seimbang) == 0,
    f"jumlah={len(tdk_seimbang)}")

ak_final = acc.arus_kas(cid, 2026)
cek("ARUS KAS SEIMBANG", ak_final.seimbang, f"selisih={ak_final.selisih}")

analisis_final = an.analisis_kesehatan(cid, 2026)
cek("Tidak ada temuan kritis pembukuan",
    not any(t.kategori == "Pembukuan" and t.tingkat == "kritis"
            for t in analisis_final.temuan),
    str([t.judul for t in analisis_final.temuan if t.tingkat == "kritis"]))


# ==========================================================================
print()
print("=" * 72)
print(f"HASIL AKHIR: {LULUS} LULUS, {GAGAL} GAGAL")
print("=" * 72)
if CATATAN:
    print()
    print("Rincian kegagalan:")
    for c in CATATAN:
        print(f"  - {c}")

sys.exit(0 if GAGAL == 0 else 1)
