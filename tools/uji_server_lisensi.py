"""
Uji apakah lisensi dapat dipakai berulang di perangkat lain.

Yang diuji ke server sungguhan:

1. Lisensi paket Standar (batas 1 perangkat) diaktifkan di perangkat
   pertama. Harus berhasil.
2. Kunci yang sama dicoba diaktifkan di perangkat kedua. Harus DITOLAK,
   karena batas paket Standar hanya satu perangkat.
3. Perangkat pertama dilepas, lalu perangkat kedua dicoba lagi. Harus
   berhasil, karena perangkat pertama sudah tidak dipakai.
4. Kunci yang sama dicoba lagi di perangkat ketiga setelah kuota terisi.
   Harus ditolak.

Alat ini memakai kunci lisensi uji yang dibuat khusus untuk pengujian dan
tidak mengganggu lisensi pelanggan.

Cara pakai:
    python tools/uji_server_lisensi.py
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

ALAMAT = "https://akuntuntas.xinet.id/api/lisensi"
KUNCI_UJI = "ATNTUJI2AAAA3BBB4CCC"


def kirim(permintaan: dict) -> dict:
    badan = json.dumps(permintaan).encode("utf-8")
    panggilan = urllib.request.Request(
        ALAMAT, data=badan,
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(panggilan, timeout=30) as jawaban:
            return json.loads(jawaban.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read().decode("utf-8"))
        except (ValueError, OSError):
            return {"ok": False, "pesan": f"HTTP {e.code}"}
    except Exception as e:
        return {"ok": False, "pesan": f"{type(e).__name__}: {e}"}


class Pemeriksa:
    def __init__(self):
        self.lulus = 0
        self.gagal = 0
        self.catatan: list[str] = []

    def cek(self, nama: str, syarat: bool, keterangan: str = ""):
        if syarat:
            self.lulus += 1
            print(f"  [AMAN] {nama}")
        else:
            self.gagal += 1
            print(f"  [BOCOR] {nama}"
                  + (f" — {keterangan}" if keterangan else ""))
            self.catatan.append(nama)

    def ringkas(self) -> int:
        print()
        print("=" * 76)
        print(f"  HASIL: {self.lulus} AMAN, {self.gagal} BOCOR")
        if self.catatan:
            print()
            print("  Celah yang ditemukan:")
            for c in self.catatan:
                print(f"    - {c}")
        print("=" * 76)
        return 1 if self.gagal else 0


def main() -> int:
    p = Pemeriksa()

    print("=" * 76)
    print("  UJI SERVER: LISENSI TIDAK BOLEH DIPAKAI BERULANG")
    print("=" * 76)
    print()

    sidik1 = "sidik-uji-perangkat-pertama-aaaaaaaa"
    sidik2 = "sidik-uji-perangkat-kedua-bbbbbbbb"
    sidik3 = "sidik-uji-perangkat-ketiga-cccccccc"

    # ---------------------------------------------------------- perangkat 1
    print("[1. Aktifkan di perangkat pertama]")
    j = kirim({
        "aksi": "aktivasi", "kunci": KUNCI_UJI, "sidik": sidik1,
        "nama_perangkat": "PC-UJI-1 (Windows 11 Pro)",
        "os_info": "Windows 11 Pro AMD64", "versi_app": "1.0.2",
    })
    print(f"  jawaban: ok={j.get('ok')} pesan={j.get('pesan', '-')}")
    p.cek("Aktivasi perangkat pertama berhasil", bool(j.get("ok")),
          str(j.get("pesan", "")))

    # ---------------------------------------------------------- perangkat 2
    print()
    print("[2. Coba kunci yang sama di perangkat kedua]")
    j2 = kirim({
        "aksi": "aktivasi", "kunci": KUNCI_UJI, "sidik": sidik2,
        "nama_perangkat": "PC-UJI-2 (Windows 11 Pro)",
        "os_info": "Windows 11 Pro AMD64", "versi_app": "1.0.2",
    })
    print(f"  jawaban: ok={j2.get('ok')} pesan={j2.get('pesan', '-')}")
    p.cek("Perangkat kedua DITOLAK", not j2.get("ok"),
          "lisensi dapat dipakai di perangkat kedua!")

    # ---------------------------------------------------------- lepas
    print()
    print("[3. Lepas perangkat pertama, lalu coba perangkat kedua]")
    j3 = kirim({
        "aksi": "lepas", "kunci": KUNCI_UJI, "sidik": sidik1,
        "nama_perangkat": "PC-UJI-1 (Windows 11 Pro)",
        "os_info": "Windows 11 Pro AMD64", "versi_app": "1.0.2",
    })
    print(f"  lepas: ok={j3.get('ok')} pesan={j3.get('pesan', '-')}")

    j4 = kirim({
        "aksi": "aktivasi", "kunci": KUNCI_UJI, "sidik": sidik2,
        "nama_perangkat": "PC-UJI-2 (Windows 11 Pro)",
        "os_info": "Windows 11 Pro AMD64", "versi_app": "1.0.2",
    })
    print(f"  aktivasi ulang: ok={j4.get('ok')} pesan={j4.get('pesan', '-')}")
    p.cek("Setelah dilepas, perangkat kedua dapat dipakai",
          bool(j4.get("ok")), str(j4.get("pesan", "")))

    # ---------------------------------------------------------- perangkat 3
    print()
    print("[4. Coba perangkat ketiga saat kuota terisi]")
    j5 = kirim({
        "aksi": "aktivasi", "kunci": KUNCI_UJI, "sidik": sidik3,
        "nama_perangkat": "PC-UJI-3 (Windows 11 Pro)",
        "os_info": "Windows 11 Pro AMD64", "versi_app": "1.0.2",
    })
    print(f"  jawaban: ok={j5.get('ok')} pesan={j5.get('pesan', '-')}")
    p.cek("Perangkat ketiga DITOLAK", not j5.get("ok"),
          "lisensi dapat dipakai di perangkat ketiga!")

    # ---------------------------------------------------------- tanpa kunci
    print()
    print("[5. Kunci tidak dikenal]")
    j6 = kirim({
        "aksi": "aktivasi", "kunci": "ATNTPALSUPALSUPALSUPALS",
        "sidik": sidik1, "nama_perangkat": "PC-UJI-1",
        "os_info": "Windows 11", "versi_app": "1.0.2",
    })
    print(f"  jawaban: ok={j6.get('ok')} pesan={j6.get('pesan', '-')}")
    p.cek("Kunci palsu DITOLAK", not j6.get("ok"), str(j6.get("pesan", "")))

    # ------------------------------------------------- bersihkan
    print()
    print("[6. Membersihkan data uji]")
    j7 = kirim({
        "aksi": "lepas", "kunci": KUNCI_UJI, "sidik": sidik2,
        "nama_perangkat": "PC-UJI-2", "os_info": "Windows 11",
        "versi_app": "1.0.2",
    })
    print(f"  lepas perangkat uji: ok={j7.get('ok')}")

    return p.ringkas()


if __name__ == "__main__":
    sys.exit(main())
