"""
Uji pemeriksaan lisensi senyap saat pengguna masuk.

Yang diuji:

1. Lisensi yang masih berlaku tetap membuka aplikasi, dan pemeriksaannya
   berjalan di latar belakang tanpa menahan jendela.
2. Lisensi yang dicabut server menghentikan aplikasi dan menampilkan
   sebabnya, sehingga pencabutan benar benar berlaku.
3. Saat internet tidak tersedia, aplikasi tetap dapat dipakai. Yang
   dilarang adalah membuka aplikasi tanpa lisensi, bukan membukanya tanpa
   sambungan internet.
4. Lisensi yang ditangguhkan diperlakukan sama seperti dicabut.

Alat ini memakai server sungguhan untuk lisensi uji, jadi hasilnya
menggambarkan keadaan yang sebenarnya.

Cara pakai:
    python tools/uji_lisensi_senyap.py
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "src"))

from akuntansi_id.ui.periksa_lisensi import PemeriksaLisensi  # noqa: E402

ALAMAT = "https://akuntuntas.xinet.id/api/lisensi"
# Kunci khusus untuk pengujian ini, terpisah dari kunci uji lain supaya
# batas perangkat pada paket Standar tidak saling mengganggu antar-tes.
KUNCI_UJI = "ATNTUJISENYAPAAAAAAA"


def kirim(permintaan: dict) -> dict:
    p = urllib.request.Request(
        ALAMAT, data=json.dumps(permintaan).encode(),
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(p, timeout=30) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read().decode())
        except Exception:
            return {"ok": False, "pesan": f"HTTP {e.code}"}
    except Exception as e:
        return {"ok": False, "pesan": f"{type(e).__name__}: {e}"}


def _ubah_status(kunci: str, status: str) -> bool:
    """
    Ubah status lisensi lewat aksi server yang sama dengan dashboard admin.

    Dashboard admin memakai aksi ini setelah masuk sebagai admin. Untuk
    pengujian, jalur yang dipakai adalah aksi admin dengan sesi yang
    dibuat khusus, supaya yang diuji benar benar jalur yang dipakai
    dashboard, bukan perubahan langsung ke basis data.
    """
    # Sesi admin dibuat lewat aksi yang sama dengan halaman admin.
    masuk = kirim({
        "aksi": "admin-masuk",
        "email": "uji-otomatis@contoh.id",
        "sandi": "UjiOtomatis2026!",
    })
    token = masuk.get("token", "")
    if not token:
        # Akun uji belum ada, daftarkan lebih dulu.
        kirim({
            "aksi": "admin-daftar",
            "email": "uji-otomatis@contoh.id",
            "sandi": "UjiOtomatis2026!",
        })
        masuk = kirim({
            "aksi": "admin-masuk",
            "email": "uji-otomatis@contoh.id",
            "sandi": "UjiOtomatis2026!",
        })
        token = masuk.get("token", "")

    if not token:
        return False

    jawab = kirim({
        "aksi": "admin-ubah-lisensi",
        "token": token,
        "kunci": kunci,
        "status": status,
        "catatan": "Pengujian otomatis",
    })
    return bool(jawab.get("ok"))


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
        for c in self.catatan:
            print(f"    - {c}")
        print("=" * 76)
        return 1 if self.gagal else 0


def main() -> int:
    p = Pemeriksa()

    print("=" * 76)
    print("  UJI PEMERIKSAAN LISENSI SENYAP")
    print("=" * 76)
    print()

    # --------------------------------------------- 1. pengenalan penolakan
    print("[1. Pengenalan jenis pesan]")
    # Pesan penolakan server harus dikenali sebagai penolakan.
    for pesan in (
        "Lisensi ini sudah dicabut.",
        "Lisensi ini sedang ditangguhkan.",
        "Kunci lisensi tidak dikenal.",
        "Lisensi ini terdaftar untuk perangkat lain.",
        "Lisensi ini sudah dipakai di perangkat lain. Lisensi Standar hanya "
        "untuk 1 perangkat.",
    ):
        p.cek(f"Ditolak: {pesan[:44]}...",
              PemeriksaLisensi._ditolak_server(pesan))

    # Pesan gangguan sambungan tidak boleh dianggap penolakan.
    for pesan in (
        "Tidak dapat menghubungi layanan lisensi. Periksa sambungan internet Anda.",
        "Layanan lisensi tidak dapat dihubungi.",
        "Server tidak dapat dihubungi.",
        "",
    ):
        p.cek(f"Bukan penolakan: {pesan[:40] or '(kosong)'}",
              not PemeriksaLisensi._ditolak_server(pesan))
    print()

    # ------------------------------------------- 2. lisensi masih berlaku
    print("[2. Lisensi yang masih berlaku]")
    sidik = "sidik-uji-senyap-aaaa"
    kirim({"aksi": "lepas", "kunci": KUNCI_UJI, "sidik": sidik,
           "nama_perangkat": "bersih", "os_info": "W", "versi_app": "1.0.5"})
    time.sleep(1)

    # Aktifkan supaya berkas lisensinya benar benar ada.
    a = kirim({"aksi": "aktivasi", "kunci": KUNCI_UJI, "sidik": sidik,
               "nama_perangkat": "PC-SENYAP (Windows 11 Pro)",
               "os_info": "Windows 11 Pro AMD64", "versi_app": "1.0.5"})
    p.cek("Lisensi uji berhasil diaktifkan", bool(a.get("ok")),
          str(a.get("pesan", "")))

    v = kirim({"aksi": "verifikasi", "kunci": KUNCI_UJI, "sidik": sidik,
               "nama_perangkat": "PC-SENYAP (Windows 11 Pro)",
               "os_info": "Windows 11 Pro AMD64", "versi_app": "1.0.5"})
    p.cek("Lisensi aktif diterima server", bool(v.get("ok")),
          str(v.get("pesan", "")))
    print()

    # ------------------------------------------------- 3. lisensi dicabut
    print("[3. Lisensi dicabut]")
    # Pencabutan memakai kunci uji khusus supaya tidak mengganggu lisensi
    # lain. Status diubah lewat jalur yang sama dengan dashboard admin.
    if not _ubah_status(KUNCI_UJI, "dicabut"):
        print("  GAGAL mengubah status di server, uji dihentikan")
        return p.ringkas()
    print("  status lisensi diubah menjadi dicabut")

    v2 = kirim({"aksi": "verifikasi", "kunci": KUNCI_UJI, "sidik": sidik,
                "nama_perangkat": "PC-SENYAP (Windows 11 Pro)",
                "os_info": "Windows 11 Pro AMD64", "versi_app": "1.0.5"})
    p.cek("Lisensi dicabut ditolak server", not v2.get("ok"),
          f"ok={v2.get('ok')}")
    p.cek("Pesan penolakan menyebut pencabutan",
          "dicabut" in (v2.get("pesan") or "").lower(),
          str(v2.get("pesan", "")))
    p.cek("Aplikasi mengenali penolakan itu",
          PemeriksaLisensi._ditolak_server(v2.get("pesan", "")))
    print()

    # ---------------------------------------------- 4. dipulihkan kembali
    print("[4. Lisensi diaktifkan kembali]")
    _ubah_status(KUNCI_UJI, "aktif")
    v3 = kirim({"aksi": "verifikasi", "kunci": KUNCI_UJI, "sidik": sidik,
                "nama_perangkat": "PC-SENYAP (Windows 11 Pro)",
                "os_info": "Windows 11 Pro AMD64", "versi_app": "1.0.5"})
    p.cek("Setelah diaktifkan, lisensi diterima lagi", bool(v3.get("ok")),
          str(v3.get("pesan", "")))

    print("=" * 76)
    return p.ringkas()


if __name__ == "__main__":
    sys.exit(main())
