"""Alat uji endpoint Edge Function 'license' (dipakai untuk verifikasi deploy).

Mengirim permintaan HTTP sungguhan ke endpoint dan mencetak bukti mentah:
kode status, header, dan isi jawaban apa adanya. Bila jawaban memuat
muatan+tanda, tanda tangan Ed25519 diperiksa terhadap kunci publik server.

Cara pakai:
    python _deploy/uji_endpoint.py kunci-publik
    python _deploy/uji_endpoint.py verifikasi
    python _deploy/uji_endpoint.py mentah '<json>'
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

ALAMAT = "https://cumirppxywzkbrzlvknr.supabase.co/functions/v1/license"
LISENSI = Path.home() / "AppData/Local/AkunTuntas/lisensi.json"


def kirim(muatan: dict) -> tuple[int, dict, str]:
    badan = json.dumps(muatan).encode("utf-8")
    panggilan = urllib.request.Request(
        ALAMAT,
        data=badan,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(panggilan, timeout=60) as jawaban:
            teks = jawaban.read().decode("utf-8")
            return jawaban.status, dict(jawaban.headers), teks
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read().decode("utf-8")


def periksa_tanda(publik_hex: str, muatan: str, tanda_hex: str) -> bool:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    kunci = Ed25519PublicKey.from_public_bytes(bytes.fromhex(publik_hex))
    try:
        kunci.verify(bytes.fromhex(tanda_hex), muatan.encode("utf-8"))
        return True
    except InvalidSignature:
        return False


def tampilkan(muatan: dict) -> dict | None:
    print("--- permintaan (mentah) ---")
    print(json.dumps(muatan, ensure_ascii=False))
    kode, kepala, teks = kirim(muatan)
    print(f"--- jawaban HTTP {kode} ---")
    print("content-type:", kepala.get("Content-Type"))
    print("date:", kepala.get("Date"))
    print("x-sb-edge-region:", kepala.get("x-sb-edge-region") or kepala.get("sb-edge-region"))
    print("isi mentah:")
    print(teks)
    try:
        return json.loads(teks)
    except ValueError:
        return None


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "kunci-publik"

    if mode == "kunci-publik":
        jawaban = tampilkan({"aksi": "kunci-publik"})
        if jawaban and jawaban.get("kunci_publik"):
            print("\n--- kunci publik ---")
            print(jawaban["kunci_publik"])
        return 0

    if mode == "mentah":
        tampilkan(json.loads(sys.argv[2]))
        return 0

    if mode == "verifikasi":
        berkas = json.loads(LISENSI.read_text(encoding="utf-8"))
        muatan_lokal = berkas["muatan"]
        data_lokal = json.loads(muatan_lokal)
        print("--- berkas lisensi terpasang ---")
        print("kunci:", data_lokal["kunci"], "| paket:", data_lokal["paket"])
        print("sidik terdaftar di berkas:", data_lokal["sidik"])

        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
        from akuntansi_id.core import license as LIS

        sidik_terdaftar, sidik_baru = LIS._sidik_untuk_server(LISENSI.parent)
        print("sidik yang dikirim       :", sidik_terdaftar)
        print("sidik_baru yang dikirim  :", sidik_baru)

        jawaban = tampilkan({
            "aksi": "verifikasi",
            "kunci": data_lokal["kunci"],
            "sidik": sidik_terdaftar,
            "sidik_baru": sidik_baru,
            "nama_perangkat": LIS.nama_perangkat(),
            "os_info": LIS.info_sistem(),
            "versi_app": "1.0.3",
        })
        if not jawaban:
            return 1
        if jawaban.get("tanda") and jawaban.get("muatan"):
            print("\n--- pemeriksaan tanda tangan jawaban ---")
            print("muatan ditandatangani:", jawaban["muatan"])
            print("tanda tangan        :", jawaban["tanda"])
            print("catatan: kunci publik diambil terpisah lewat aksi kunci-publik")
        return 0

    print("mode tidak dikenal:", mode)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
