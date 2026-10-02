"""
Periksa apakah perbesaran huruf membuat unsur saling bertabrakan.

Ukuran huruf pada overlay diperbesar supaya tetap terbaca di layar
ponsel. Unsur teks pada overlay tidak memakai lebar tetap, jadi
memperbesar huruf membuat unsur itu ikut membesar. Hal yang perlu
diperiksa karena itu bukan apakah teks terpotong, melainkan apakah unsur
yang membesar itu mendorong atau menimpa unsur lain.

Tiga hal yang diperiksa:
  1. Unsur yang keluar dari batas layar
  2. Unsur yang bertumpuk dengan unsur lain yang tidak seharusnya
  3. Unsur yang bertumpuk dengan kotak kamera

Pengukuran dilakukan dengan Chrome, karena Chrome itulah yang dipakai
menampilkan overlay.

Cara pakai:
    python tools/periksa_luber_teks.py
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

# Unsur yang diperiksa, dikelompokkan. Unsur dalam kelompok yang sama
# memang boleh berdampingan, jadi tidak diperiksa terhadap sesamanya.
UNSUR = [
    [".merek-nama", "nama merek", "kepala"],
    [".merek-slogan", "slogan merek", "kepala"],
    [".slide-judul", "judul slide", "slide"],
    [".slide-keterangan", "keterangan slide", "slide"],
    [".slide-label", "label slide", "slide"],
    [".ajakan-label", "label ajakan", "ajakan"],
    [".ajakan-situs", "alamat situs", "ajakan"],
    [".kaki-butir", "butir kaki", "kaki"],
    [".penunjuk-judul", "judul penunjuk", "kaki"],
    [".penunjuk-kecil", "kecil penunjuk", "kaki"],
    [".cam-nama", "nama di kamera", "kamera"],
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
                nama: p[1],
                kelompok: p[2],
                ada: true,
                kiri: Math.round(r.left), atas: Math.round(r.top),
                kanan: Math.round(r.right), bawah: Math.round(r.bottom),
                lebar: Math.round(r.width), tinggi: Math.round(r.height),
                huruf: getComputedStyle(el).fontSize
            });
        }

        // Kotak kamera, untuk memeriksa tabrakan.
        const cam = document.querySelector(".cam");
        let kotakKamera = null;
        if (cam) {
            const c = cam.getBoundingClientRect();
            kotakKamera = {
                kiri: Math.round(c.left), atas: Math.round(c.top),
                kanan: Math.round(c.right), bawah: Math.round(c.bottom)
            };
        }

        const pre = document.createElement("pre");
        pre.id = "hasil-ukur";
        pre.textContent = JSON.stringify({
            unsur: hasil,
            kotakKamera: kotakKamera,
            lebar: window.innerWidth,
            tinggi: window.innerHeight
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


def tumpang(a: dict, b: dict) -> tuple[int, int]:
    """Lebar dan tinggi bagian yang bertumpuk."""
    kiri = max(a["kiri"], b["kiri"])
    kanan = min(a["kanan"], b["kanan"])
    atas = max(a["atas"], b["atas"])
    bawah = min(a["bawah"], b["bawah"])
    if kanan <= kiri or bawah <= atas:
        return 0, 0
    return kanan - kiri, bawah - atas


def utama() -> int:
    chrome = cari_chrome()
    if not chrome:
        print("  GAGAL Chrome tidak ditemukan")
        return 1

    isi = OVERLAY.read_text(encoding="utf-8")
    skrip = SKRIP % json.dumps(UNSUR, ensure_ascii=False)
    isi = isi.replace("</body>", skrip + "\n</body>", 1)

    folder = Path(tempfile.mkdtemp(prefix="ukur_overlay_"))
    tujuan = folder / "live_overlay"
    shutil.copytree(OVERLAY.parent, tujuan, dirs_exist_ok=True)
    (tujuan / "overlay.html").write_text(isi, encoding="utf-8")

    print("=" * 78)
    print("  PERIKSA TABRAKAN UNSUR SETELAH HURUF DIPERBESAR")
    print("=" * 78)
    print()
    print("  Mengukur dengan Chrome...")

    keluaran = subprocess.run(
        [chrome, "--headless=new", "--disable-gpu", "--no-sandbox",
         "--window-size=1080,1920", "--virtual-time-budget=6000",
         "--dump-dom", (tujuan / "overlay.html").as_uri()],
        capture_output=True, text=True, timeout=180)

    dom = keluaran.stdout
    m = re.search(r'<pre id="hasil-ukur">(.*?)</pre>', dom, re.DOTALL)

    if not m:
        print("  GAGAL hasil pengukuran tidak ditemukan")
        shutil.rmtree(folder, ignore_errors=True)
        return 1

    teks = (m.group(1).replace("&quot;", '"').replace("&amp;", "&")
            .replace("&lt;", "<").replace("&gt;", ">"))

    try:
        d = json.loads(teks)
    except json.JSONDecodeError as e:
        print(f"  GAGAL membaca hasil: {e}")
        shutil.rmtree(folder, ignore_errors=True)
        return 1

    shutil.rmtree(folder, ignore_errors=True)

    lebar, tinggi = d["lebar"], d["tinggi"]
    unsur = [u for u in d["unsur"] if u.get("ada")]

    print(f"  jendela: {lebar}x{tinggi}")
    print()
    print(f"  {'unsur':20} {'posisi':>22} {'ukuran':>10}  keadaan")
    print("  " + "-" * 72)

    gagal = []

    for u in unsur:
        posisi = f"{u['kiri']},{u['atas']}-{u['kanan']},{u['bawah']}"
        ukuran = f"{u['lebar']}x{u['tinggi']}"

        masalah = []

        # 1. Keluar batas layar
        if u["kiri"] < 0 or u["atas"] < 0:
            masalah.append("keluar kiri/atas")
        if u["kanan"] > lebar or u["bawah"] > tinggi:
            masalah.append("keluar kanan/bawah")

        # 2. Bertumpuk dengan unsur lain dari kelompok berbeda
        for v in unsur:
            if v["nama"] == u["nama"]:
                continue
            if v["kelompok"] == u["kelompok"]:
                continue
            w, h = tumpang(u, v)
            if w > 4 and h > 4:
                masalah.append(f"bertumpuk {v['nama']} ({w}x{h})")

        # 3. Bertumpuk dengan kotak kamera
        kamera = d.get("kotakKamera")
        if kamera and u["kelompok"] != "kamera":
            w, h = tumpang(u, kamera)
            if w > 4 and h > 4:
                masalah.append(f"masuk kotak kamera ({w}x{h})")

        ket = "aman" if not masalah else "; ".join(masalah)
        if masalah:
            gagal.append((u["nama"], ket, u["huruf"]))

        print(f"  {u['nama'][:20]:20} {posisi:>22} {ukuran:>10}  {ket}")

    print()
    print("=" * 78)
    if not gagal:
        print("  LULUS: tidak ada unsur yang bertabrakan atau keluar layar")
        print("  HASIL: 1 LULUS, 0 GAGAL")
    else:
        print(f"  GAGAL: {len(gagal)} unsur bermasalah")
        for nama, ket, huruf in gagal:
            print(f"    {nama} (huruf {huruf}): {ket}")
        print(f"  HASIL: 0 LULUS, {len(gagal)} GAGAL")
    print("=" * 78)

    return 0 if not gagal else 1


if __name__ == "__main__":
    sys.exit(utama())
