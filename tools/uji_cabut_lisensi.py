"""
Uji pencabutan lisensi: status diubah, aplikasi menolak, lalu dipulihkan.

Yang ditiru adalah kejadian yang sesungguhnya:

1. Pelanggan mengaktifkan lisensi di komputernya, lalu memakai aplikasi.
2. Penjual menemukan penyalahgunaan dan mencabut lisensi itu.
3. Pelanggan membuka aplikasi dan masuk kembali. Aplikasi memeriksa
   lisensi ke server, menerima penolakan, lalu menutup akses.

Jalur dashboard admin tidak dapat dipakai alat otomatis, karena
pendaftaran pengelola lisensi sengaja dibatasi hanya untuk email yang
sudah terdaftar. Pembatasan itu memang yang diinginkan: tanpa itu, siapa
pun dapat mendaftar lalu mencabut lisensi orang lain.

Karena itu status lisensi uji diubah langsung pada basis data server,
lalu jalur aplikasi yang sebenarnya dipakai untuk memeriksa apakah
penolakannya bekerja. Lisensi uji dipulihkan ke keadaan aktif di akhir.

Cara pakai:
    python tools/uji_cabut_lisensi.py
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR / "src"))

from akuntansi_id.ui.periksa_lisensi import PemeriksaLisensi  # noqa: E402

ALAMAT = "https://akuntuntas.xinet.id/api/lisensi"
PROYEK = "cumirppxywzkbrzlvknr"
KUNCI = "ATNTUJICABUTAAAAAAAA"
SIDIK = "sidik-uji-cabut-ffff"


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


def ubah_status(status: str) -> bool:
    """
    Ubah status lisensi uji pada basis data server.

    Kunci API dibaca dari penyimpanan alat, bukan ditulis di berkas ini,
    supaya kunci itu tidak ikut tersimpan bersama kode proyek.
    """
    p = Path.home() / "AppData/Local/hermes/mcp-tokens/supabase.json"
    if not p.exists():
        return False
    kunci_api = json.loads(p.read_text(encoding="utf-8")).get("access_token")
    if not kunci_api:
        return False

    perintah = (f"UPDATE licenses SET status='{status}' "
                f"WHERE license_key='{KUNCI}';")
    badan = json.dumps({"query": perintah}).encode()
    panggilan = urllib.request.Request(
        f"https://api.supabase.com/v1/projects/{PROYEK}/database/query",
        data=badan,
        headers={"Authorization": f"Bearer {kunci_api}",
                 "Content-Type": "application/json"},
        method="POST")
    try:
        with urllib.request.urlopen(panggilan, timeout=40) as r:
            r.read()
        return True
    except Exception:
        return False


class Pemeriksa:
    def __init__(self):
        self.lulus = 0
        self.gagal = 0

    def cek(self, nama: str, syarat: bool, keterangan: str = ""):
        if syarat:
            self.lulus += 1
            print(f"  [LULUS] {nama}")
        else:
            self.gagal += 1
            print(f"  [GAGAL] {nama}"
                  + (f" — {keterangan}" if keterangan else ""))

    def ringkas(self) -> int:
        print()
        print("=" * 76)
        print(f"  HASIL: {self.lulus} LULUS, {self.gagal} GAGAL")
        print("=" * 76)
        return 1 if self.gagal else 0


def main() -> int:
    p = Pemeriksa()

    print("=" * 76)
    print("  UJI PENCABUTAN LISENSI")
    print("=" * 76)
    print()

    # ------------------------------------------------------ 1. aktifkan
    print("[1. Lisensi diaktifkan dan dipakai]")
    kirim({"aksi": "lepas", "kunci": KUNCI, "sidik": SIDIK,
           "nama_perangkat": "bersih", "os_info": "W", "versi_app": "1.0.5"})

    a = kirim({"aksi": "aktivasi", "kunci": KUNCI, "sidik": SIDIK,
               "nama_perangkat": "PC-UJI (Windows 11 Pro)",
               "os_info": "Windows 11 Pro AMD64", "versi_app": "1.0.5"})
    p.cek("Aktivasi berhasil", bool(a.get("ok")), str(a.get("pesan", "")))

    v1 = kirim({"aksi": "verifikasi", "kunci": KUNCI, "sidik": SIDIK,
                "nama_perangkat": "PC-UJI (Windows 11 Pro)",
                "os_info": "Windows 11 Pro AMD64", "versi_app": "1.0.5"})
    p.cek("Aplikasi dapat dipakai sebelum dicabut", bool(v1.get("ok")),
          str(v1.get("pesan", "")))
    print()

    # ---------------------------------------------------------- 2. cabut
    print("[2. Lisensi dicabut]")
    if not ubah_status("dicabut"):
        print("  GAGAL mengubah status, uji dihentikan")
        return p.ringkas()
    print("  status lisensi diubah menjadi dicabut")

    v2 = kirim({"aksi": "verifikasi", "kunci": KUNCI, "sidik": SIDIK,
                "nama_perangkat": "PC-UJI (Windows 11 Pro)",
                "os_info": "Windows 11 Pro AMD64", "versi_app": "1.0.5"})
    p.cek("Lisensi dicabut DITOLAK server", not v2.get("ok"),
          f"ok={v2.get('ok')}")
    p.cek("Pesan penolakan menyebut pencabutan",
          "dicabut" in (v2.get("pesan") or "").lower(),
          str(v2.get("pesan", "")))
    p.cek("Aplikasi mengenali penolakan itu",
          PemeriksaLisensi._ditolak_server(v2.get("pesan", "")))

    # Aktivasi ulang juga harus ditolak.
    a2 = kirim({"aksi": "aktivasi", "kunci": KUNCI, "sidik": "sidik-baru-9999",
                "nama_perangkat": "PC-LAIN (Windows 11 Pro)",
                "os_info": "Windows 11 Pro AMD64", "versi_app": "1.0.5"})
    p.cek("Lisensi dicabut tidak bisa diaktifkan ulang", not a2.get("ok"),
          f"ok={a2.get('ok')}")
    print()

    # ------------------------------------------------------ 3. pulihkan
    print("[3. Lisensi diaktifkan kembali]")
    ubah_status("aktif")
    v3 = kirim({"aksi": "verifikasi", "kunci": KUNCI, "sidik": SIDIK,
                "nama_perangkat": "PC-UJI (Windows 11 Pro)",
                "os_info": "Windows 11 Pro AMD64", "versi_app": "1.0.5"})
    p.cek("Setelah diaktifkan, lisensi diterima lagi", bool(v3.get("ok")),
          str(v3.get("pesan", "")))

    # Bersihkan perangkat uji.
    kirim({"aksi": "lepas", "kunci": KUNCI, "sidik": SIDIK,
           "nama_perangkat": "bersih", "os_info": "W", "versi_app": "1.0.5"})

    return p.ringkas()


if __name__ == "__main__":
    sys.exit(main())
