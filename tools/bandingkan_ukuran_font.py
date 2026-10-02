"""
Bandingkan tata letak overlay antara dua ukuran huruf.

Ukuran huruf pada overlay diperbesar supaya tetap terbaca di layar
ponsel. Perbesaran itu berisiko mengubah tata letak, jadi perlu
dibandingkan dengan keadaan sebelumnya: apakah ada unsur yang bergeser
sampai bertabrakan atau keluar dari batasnya.

Cara kerja: halaman diukur dua kali oleh Chrome, sekali dengan ukuran
huruf lama dan sekali dengan ukuran huruf baru, lalu hasilnya
dibandingkan. Chrome dipakai karena Chrome itulah yang menampilkan
overlay.

Cara pakai:
    python tools/bandingkan_ukuran_font.py
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
OVERLAY = AKAR / "live_overlay" / "overlay.html"

CHROME = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]

# Ukuran huruf sebelum diperbesar.
FONT_LAMA = {
    ".kaki-butir": 26, ".penunjuk-judul": 25, ".kaki-pemisah": 24,
    ".slide-keterangan": 22, ".butir": 21, ".pil": 21,
    ".merek-slogan": 20, ".ajakan-label": 18, ".kaki-ikon": 18,
    ".slide-label": 17, ".alamat": 17, ".cam-nama": 17,
    ".penunjuk-kecil": 16, ".slide-angka-label": 15,
    ".alamat-gembok": 15, ".butir-centang": 15,
}

# Unsur yang diukur.
UNSUR = [
    [".merek-nama", "nama merek"],
    [".merek-slogan", "slogan merek"],
    [".kepala", "kepala"],
    [".panggung", "panggung slide"],
    [".slide-label", "label slide"],
    [".slide-judul", "judul slide"],
    [".slide-keterangan", "keterangan slide"],
    [".ajakan", "kotak ajakan"],
    [".ajakan-label", "label ajakan"],
    [".ajakan-situs", "alamat situs"],
    [".kaki", "kaki"],
    [".kaki-butir", "butir kaki"],
    [".penunjuk", "penunjuk"],
    [".penunjuk-judul", "judul penunjuk"],
    [".cam", "kotak kamera"],
]

SKRIP = """
<script>
window.addEventListener("load", function () {
    setTimeout(function () {
        const daftar = %s;
        const hasil = [];
        for (const p of daftar) {
            const el = document.querySelector(p[0]);
            if (!el) { hasil.push({nama: p[1], ada: false}); continue; }
            const r = el.getBoundingClientRect();
            hasil.push({
                nama: p[1], ada: true,
                kiri: Math.round(r.left), atas: Math.round(r.top),
                kanan: Math.round(r.right), bawah: Math.round(r.bottom),
                lebar: Math.round(r.width), tinggi: Math.round(r.height)
            });
        }
        const pre = document.createElement("pre");
        pre.id = "hasil-ukur";
        pre.textContent = JSON.stringify({
            unsur: hasil,
            lebar: window.innerWidth, tinggi: window.innerHeight
        });
        document.body.appendChild(pre);
    }, 2500);
});
</script>
"""


def cari_chrome() -> str | None:
    for jalur in CHROME:
        if Path(jalur).exists():
            return jalur
    return shutil.which("chrome")


def ukur(chrome: str, isi: str) -> dict | None:
    """Ukur halaman dengan Chrome, kembalikan hasilnya."""
    skrip = SKRIP % json.dumps(UNSUR, ensure_ascii=False)
    halaman = isi.replace("</body>", skrip + "\n</body>", 1)

    folder = Path(tempfile.mkdtemp(prefix="banding_font_"))
    tujuan = folder / "live_overlay"
    shutil.copytree(OVERLAY.parent, tujuan, dirs_exist_ok=True)
    (tujuan / "overlay.html").write_text(halaman, encoding="utf-8")

    try:
        keluaran = subprocess.run(
            [chrome, "--headless=new", "--disable-gpu", "--no-sandbox",
             "--window-size=1080,1920", "--virtual-time-budget=6000",
             "--dump-dom", (tujuan / "overlay.html").as_uri()],
            capture_output=True, text=True, timeout=180)
    finally:
        shutil.rmtree(folder, ignore_errors=True)

    m = re.search(r'<pre id="hasil-ukur">(.*?)</pre>',
                  keluaran.stdout, re.DOTALL)
    if not m:
        return None

    teks = (m.group(1).replace("&quot;", '"').replace("&amp;", "&")
            .replace("&lt;", "<").replace("&gt;", ">"))
    try:
        return json.loads(teks)
    except json.JSONDecodeError:
        return None


def utama() -> int:
    chrome = cari_chrome()
    if not chrome:
        print("  GAGAL Chrome tidak ditemukan")
        return 1

    asli = OVERLAY.read_text(encoding="utf-8")

    # Susun versi font lama.
    lama = asli
    for pemilih, ukuran in FONT_LAMA.items():
        pola = re.compile(
            re.escape(pemilih) + r'\s*\{([^}]*?font-size:\s*)(\d+)(px)',
            re.DOTALL)
        m = pola.search(lama)
        if m:
            lama = lama[:m.start(2)] + str(ukuran) + lama[m.end(2):]

    print("=" * 78)
    print("  BANDINGKAN TATA LETAK: FONT LAMA vs FONT BARU")
    print("=" * 78)
    print()
    print("  Mengukur versi font lama...")
    hasil_lama = ukur(chrome, lama)
    if not hasil_lama:
        print("  GAGAL pengukuran font lama")
        return 1

    print("  Mengukur versi font baru...")
    hasil_baru = ukur(chrome, asli)
    if not hasil_baru:
        print("  GAGAL pengukuran font baru")
        return 1

    print(f"  jendela: {hasil_baru['lebar']}x{hasil_baru['tinggi']}")
    print()

    peta_lama = {u["nama"]: u for u in hasil_lama["unsur"] if u.get("ada")}
    peta_baru = {u["nama"]: u for u in hasil_baru["unsur"] if u.get("ada")}

    print(f"  {'unsur':18} {'lebar lama':>11} {'lebar baru':>11} "
          f"{'selisih':>8}  {'kanan lama':>10} {'kanan baru':>10}  keadaan")
    print("  " + "-" * 86)

    membesar = []
    geser = []
    keluar = []

    for u in hasil_baru["unsur"]:
        nama = u["nama"]
        if not u.get("ada") or nama not in peta_lama:
            continue

        a = peta_lama[nama]
        dl = u["lebar"] - a["lebar"]
        dt = u["tinggi"] - a["tinggi"]

        tanda = ""
        if dl > 2 or dt > 2:
            tanda = f"membesar +{dl}x{dt}"
            membesar.append((nama, dl, dt))
        elif dl < -2 or dt < -2:
            tanda = f"menyusut {dl}x{dt}"
            geser.append((nama, dl, dt))

        # Keluar dari batas jendela
        if (u["kanan"] > hasil_baru["lebar"] or u["bawah"] > hasil_baru["tinggi"]
                or u["kiri"] < 0 or u["atas"] < 0):
            tanda = (tanda + " KELUAR BATAS").strip()
            keluar.append(nama)

        print(f"  {nama[:18]:18} {a['lebar']:>11} {u['lebar']:>11} "
              f"{dl:>8}  {a['kanan']:>10} {u['kanan']:>10}  {tanda}")

    print()
    print("=" * 78)

    gagal = 0

    if keluar:
        print(f"  MASALAH: {len(keluar)} unsur keluar dari batas layar")
        for nama in keluar:
            print(f"    {nama}")
        gagal += len(keluar)
    else:
        print("  tidak ada unsur yang keluar dari batas layar")

    if membesar:
        print()
        print(f"  {len(membesar)} unsur membesar karena huruf diperbesar:")
        for nama, dl, dt in membesar:
            print(f"    {nama:18} +{dl} x +{dt} piksel")

    # Periksa jarak TEKS ke kotak kamera.
    #
    # Wadah seperti kepala, panggung, ajakan, dan kaki memang menumpuk
    # dengan kotak kamera secara rancangan: kotak kamera sengaja
    # diletakkan di atas panggung. Yang tidak boleh menumpuk adalah
    # teksnya, karena teks yang tertutup tidak terbaca penonton.
    WADAH = {"kepala", "panggung slide", "kotak ajakan", "kaki",
             "penunjuk", "kotak kamera"}

    cam = peta_baru.get("kotak kamera")
    if cam:
        print()
        print(f"  Jarak TEKS ke kotak kamera (kiri kotak = {cam['kiri']}):")
        ada_teks = False
        for u in hasil_baru["unsur"]:
            nama = u["nama"]
            if not u.get("ada") or nama in WADAH:
                continue
            # Hanya teks yang sejajar tegak dengan kotak kamera.
            if u["atas"] < cam["bawah"] and u["bawah"] > cam["atas"]:
                ada_teks = True
                jarak = cam["kiri"] - u["kanan"]
                ket = "aman" if jarak >= 0 else "TERTUTUP"
                if jarak < 0:
                    gagal += 1
                print(f"    {nama:18} kanan={u['kanan']:5}  "
                      f"jarak={jarak:5}  {ket}")
        if not ada_teks:
            print("    tidak ada teks yang sejajar dengan kotak kamera")

    print()
    print("=" * 78)
    if gagal == 0:
        print("  LULUS: perbesaran huruf tidak merusak tata letak")
        print("  HASIL: 1 LULUS, 0 GAGAL")
    else:
        print(f"  GAGAL: {gagal} masalah tata letak ditemukan")
        print(f"  HASIL: 0 LULUS, {gagal} GAGAL")
    print("=" * 78)

    return 0 if gagal == 0 else 1


if __name__ == "__main__":
    sys.exit(utama())
