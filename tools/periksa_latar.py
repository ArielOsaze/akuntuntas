"""Periksa aturan stylesheet yang menular ke widget di dalamnya.

Cara pakai:
    python tools/periksa_latar.py            # laporkan saja
    python tools/periksa_latar.py --perbaiki # perbaiki otomatis

Qt menerapkan stylesheet pada widget DAN seluruh anaknya. Deklarasi tanpa
selector seperti "background: #FFF;" karena itu ikut menimpa latar tombol,
kotak isian, dan tabel di dalamnya — akibatnya tombol berlatar biru bisa
berubah pucat dengan teks putih yang tidak terbaca. Aturan semacam ini harus
dikunci ke wadahnya saja lewat widgets.latar().
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
FOLDER = AKAR / "src" / "akuntansi_id" / "ui"

POLA = re.compile(r"([A-Za-z_][\w.]*)\.setStyleSheet\(\s*")


def baca_argumen(teks: str, mulai: int) -> tuple:
    """Ambil isi argumen setStyleSheet mulai posisi '('.

    Mengembalikan (posisi_setelah_buka, isi_teks). Isi dipakai untuk
    menilai apakah aturan menular; posisi dipakai saat mengganti kode.
    """
    i = teks.index("(", mulai) + 1
    n = len(teks)
    while i < n and teks[i] in " \t\r\n":
        i += 1
    isi_mulai = i

    # baca rangkaian literal string yang mungkin tersambung beberapa baris
    j = i
    while j < n:
        while j < n and teks[j] in " \t\r\n":
            j += 1
        if j < n and teks[j] in "fF":
            j += 1
        if j >= n or teks[j] not in "\"'":
            break
        kutip = teks[j]
        j += 1
        while j < n and teks[j] != kutip:
            if teks[j] == "\\":
                j += 1
            j += 1
        j += 1
    return isi_mulai, teks[isi_mulai:j]


def tanpa_selector(isi: str) -> bool:
    """True bila deklarasi latar tidak dibungkus selector apa pun.

    Latar transparan aman: sifatnya mewarisi kehendak induk, bukan menimpa
    warna. Yang berbahaya adalah latar berwarna tanpa selector karena ikut
    menimpa latar tombol dan kotak isian di dalam wadah tersebut.

    Placeholder f-string (mis. {C.BG}) dilepas lebih dulu supaya tidak
    tertukar dengan kurung buka blok CSS.
    """
    bersih = re.sub(r"\{[^{}:]*\}", "", isi)
    if "{" in bersih:
        return False
    if "background" not in bersih:
        return False
    return "transparent" not in bersih.replace(" ", "").lower()


def periksa(berkas: Path) -> list:
    teks = berkas.read_text(encoding="utf-8")
    temuan = []
    for cocok in POLA.finditer(teks):
        wadah = cocok.group(1)
        if wadah.endswith("latar") or "latar(" in teks[max(0, cocok.start() - 8):cocok.start()]:
            continue
        posisi_isi, isi = baca_argumen(teks, cocok.start())
        if not isi or not tanpa_selector(isi):
            continue
        baris = teks[:cocok.start()].count("\n") + 1
        temuan.append((baris, cocok.start(), posisi_isi, wadah, isi))
    return temuan


def perbaiki(berkas: Path, temuan: list) -> int:
    """Ganti X.setStyleSheet( menjadi theme.latar(X, — sisa argumen tetap.

    Pendekatan ini tidak menyentuh isi argumen sama sekali, sehingga
    string yang tersambung beberapa baris pun tetap utuh.
    """
    teks = berkas.read_text(encoding="utf-8")
    jumlah = 0
    for _, mulai, akhir, wadah, _ in reversed(temuan):
        # akhir berisi posisi setelah '(' beserta spasi sesudahnya
        teks = teks[:mulai] + f"theme.latar({wadah}, " + teks[akhir:]
        jumlah += 1
    if jumlah:
        berkas.write_text(teks, encoding="utf-8")
    return jumlah


def main() -> int:
    mode_perbaiki = "--perbaiki" in sys.argv
    total = 0
    for berkas in sorted(FOLDER.rglob("*.py")):
        temuan = periksa(berkas)
        if not temuan:
            continue
        for baris, _, _, wadah, isi in temuan:
            print(f"  [MENULAR] {berkas.name}:{baris} {wadah}.setStyleSheet("
                  f"'{isi[:58]}')")
        total += len(temuan)
        if mode_perbaiki:
            n = perbaiki(berkas, temuan)
            print(f"           -> {n} aturan dikunci ke wadahnya")

    print()
    if not total:
        print("HASIL: tidak ada aturan stylesheet yang menular")
        return 0
    if mode_perbaiki:
        print(f"HASIL: {total} aturan diperbaiki")
        return 0
    print(f"HASIL: {total} aturan masih menular ke widget di dalamnya")
    return 1


if __name__ == "__main__":
    sys.exit(main())
