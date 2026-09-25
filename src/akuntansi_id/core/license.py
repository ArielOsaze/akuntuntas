"""
AkunTuntas - Lisensi & Aktivasi Perangkat
==========================================
Lisensi diperiksa ke server saat aktivasi, lalu hasilnya ditandatangani
secara digital. Tanda tangan itu disimpan di komputer dan diperiksa setiap
aplikasi dibuka, sehingga aplikasi tetap dapat dipakai tanpa internet.

Kunci privat penanda tangan tidak pernah ada di dalam aplikasi. Yang
ditanam di sini hanya kunci publiknya, yang memang boleh diketahui siapa
saja. Dengan begitu berkas lisensi tidak dapat dipalsukan dengan menyunting
isi komputer.
"""
from __future__ import annotations

import hashlib
import json
import platform
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

# Alamat layanan lisensi. Kunci publik dipakai untuk memeriksa tanda tangan
# dari server; kunci privatnya hanya ada di server.
ALAMAT_SERVER = "https://cumirppxywzkbrzlvknr.supabase.co/functions/v1/license"
KUNCI_PUBLIK = "8b30ad980677f67994f196db6732e3dbb8da1e9816d95fd46174f01a557e2a75"

# Lama satu tanda tangan berlaku sebelum aplikasi perlu menghubungi server
# lagi. Selama masa itu aplikasi dapat dipakai sepenuhnya tanpa internet.
HARI_BERLAKU = 30
# Tambahan waktu setelah masa berlaku habis, untuk memberi kesempatan
# menghubungkan komputer ke internet sebelum aplikasi menolak dibuka.
HARI_TENGGANG = 7

BATAS_WAKTU_SERVER = 12


# ==========================================================================
# SIDIK PERANGKAT
# ==========================================================================
def _nama_komputer() -> str:
    try:
        return socket.gethostname()
    except Exception:
        return "tanpa-nama"


def _nomor_volume() -> str:
    """
    Nomor seri volume sistem.

    Nilai ini menempel pada pemasangan Windows, bukan pada berkas aplikasi,
    sehingga menyalin folder aplikasi ke komputer lain menghasilkan sidik
    yang berbeda.
    """
    if sys.platform != "win32":
        return ""

    try:
        keluaran = subprocess.run(
            ["cmd", "/c", "vol", "C:"],
            capture_output=True, text=True, timeout=6,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        ).stdout
    except Exception:
        return ""

    for baris in keluaran.splitlines():
        if "Serial Number" in baris or "Nomor Seri" in baris:
            return baris.split("is", 1)[-1].strip().replace("-", "")
    return ""


def _nomor_prosesor_wmic() -> str:
    """
    Nomor prosesor dengan cara lama, hanya lewat wmic.

    Dipakai untuk menghitung ulang sidik perangkat versi lama. Pada
    Windows 11 versi 24H2 ke atas perintah wmic sudah dihapus, sehingga
    hasilnya kosong; keadaan itu memang yang terjadi saat sidik lama
    dihitung, jadi harus tetap sama persis.
    """
    if sys.platform != "win32":
        return platform.processor()

    try:
        keluaran = subprocess.run(
            ["wmic", "cpu", "get", "ProcessorId"],
            capture_output=True, text=True, timeout=8,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        ).stdout
        baris = [b.strip() for b in keluaran.splitlines() if b.strip()]
        return baris[1] if len(baris) > 1 else ""
    except Exception:
        return ""


def _nomor_prosesor() -> str:
    """
    Nomor prosesor.

    Sejak Windows 11 versi 24H2, perintah wmic sudah dihapus, sehingga
    pembacaan lewat wmic menghasilkan kosong. PowerShell dipakai lebih
    dulu, dan wmic hanya sebagai cadangan untuk Windows lama.
    """
    if sys.platform != "win32":
        return platform.processor()

    # Cara utama: PowerShell (tersedia di seluruh Windows yang didukung).
    try:
        keluaran = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "(Get-CimInstance Win32_Processor).ProcessorId"],
            capture_output=True, text=True, timeout=10,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        ).stdout.strip()
        if keluaran:
            return keluaran.splitlines()[0].strip()
    except Exception:
        pass

    # Cadangan: wmic, untuk Windows versi lama yang belum punya PowerShell
    # atau bila PowerShell diblokir kebijakan.
    try:
        keluaran = subprocess.run(
            ["wmic", "cpu", "get", "ProcessorId"],
            capture_output=True, text=True, timeout=8,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        ).stdout
        baris = [b.strip() for b in keluaran.splitlines() if b.strip()]
        if len(baris) > 1:
            return baris[1]
    except Exception:
        pass

    return ""


def _nomor_disk() -> str:
    """
    Nomor seri fisik cakram sistem.

    Ciri ini melekat pada perangkat keras, bukan pada pemasangan Windows,
    sehingga jauh lebih sukar ditiru daripada nama komputer. Bila cakram
    sistem berupa cakram virtual, nomor ini dapat berubah setelah mesin
    dipulihkan; karena itu kegagalan pembacaan tidak dianggap penolakan,
    hanya membuat sidik perangkat berubah.
    """
    if sys.platform != "win32":
        return ""

    try:
        keluaran = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "(Get-CimInstance Win32_DiskDrive | Where-Object {$_.Index -eq 0})"
             ".SerialNumber"],
            capture_output=True, text=True, timeout=10,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        ).stdout.strip()
        if keluaran:
            return keluaran.splitlines()[0].strip()
    except Exception:
        pass

    return ""


def _alamat_mac() -> str:
    try:
        nomor = hex(__import__("uuid").getnode())
        return nomor
    except Exception:
        return ""


def _sidik_dari(ciri: list[str]) -> str:
    bahan = "|".join(ciri)
    return hashlib.sha256(bahan.encode("utf-8")).hexdigest()[:40]


def sidik_perangkat() -> str:
    """
    Sidik yang mewakili satu komputer.

    Gabungan beberapa ciri perangkat diambil sidiknya, sehingga perangkat
    yang sama selalu menghasilkan sidik yang sama, sedangkan komputer lain
    menghasilkan sidik berbeda.

    Ciri dipilih dari yang paling sukar ditiru. Nama komputer dan alamat
    MAC ikut disertakan, tetapi keduanya mudah diubah pengguna, sehingga
    tidak diandalkan sendirian. Nomor seri cakram dan nomor prosesor
    melekat pada perangkat keras dan menjadi penentu utama.
    """
    return _sidik_dari([
        _nomor_disk(),
        _nomor_volume(),
        _nomor_prosesor(),
        _nama_komputer(),
        _alamat_mac(),
        platform.machine(),
    ])


def sidik_perangkat_versi_lama() -> str:
    """
    Sidik perangkat sebagaimana dihitung sebelum nomor seri cakram dipakai.

    Dihitung hanya untuk mengenali lisensi yang sudah terbit dan sudah
    terdaftar di server dengan sidik versi lama. Tanpa ini, seluruh
    pelanggan yang sudah mengaktifkan lisensi akan ditolak setelah aplikasi
    diperbarui, dan perangkat mereka akan terhitung sebagai perangkat baru
    di server.
    """
    return _sidik_dari([
        _nama_komputer(),
        _nomor_volume(),
        _nomor_prosesor_wmic(),
        _alamat_mac(),
        platform.machine(),
    ])


def sidik_cocok(sidik_tersimpan: str) -> bool:
    """
    Apakah sidik tersimpan mewakili perangkat ini.

    Sidik versi lama tetap diterima agar lisensi yang sudah terbit tidak
    perlu diaktifkan ulang. Pemeriksaan ini tidak melonggarkan keamanan:
    keduanya sama-sama memerlukan ciri perangkat yang sama, hanya berbeda
    pada ikut sertanya nomor seri cakram.
    """
    if not sidik_tersimpan:
        return False
    return sidik_tersimpan in (sidik_perangkat(), sidik_perangkat_versi_lama())


def nama_windows() -> str:
    """
    Nama Windows yang benar, termasuk membedakan Windows 10 dan 11.

    platform.release() selalu mengembalikan "10" untuk Windows 11, karena
    Windows 11 memakai nomor versi yang sama (10.0). Yang membedakan adalah
    nomor build: Windows 11 dimulai dari build 22000. Tanpa pemeriksaan
    build, seluruh pengguna Windows 11 terdeteksi sebagai Windows 10.
    """
    if sys.platform != "win32":
        return f"{platform.system()} {platform.release()}"

    versi = platform.version()  # mis. "10.0.26200"
    build = 0
    try:
        bagian = versi.split(".")
        if len(bagian) >= 3:
            build = int(bagian[2])
    except (ValueError, IndexError):
        build = 0

    if build >= 22000:
        nama = "Windows 11"
    elif build >= 10240:
        nama = "Windows 10"
    else:
        nama = f"Windows {platform.release()}"

    # Edisi (Home, Pro, Enterprise) diambil dari registry, karena hanya
    # tersedia di sana. Kegagalan pembacaan tidak dianggap masalah.
    edisi = ""
    try:
        import winreg
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Windows NT\CurrentVersion",
        ) as k:
            edisi = str(winreg.QueryValueEx(k, "EditionID")[0])
    except Exception:
        edisi = ""

    edisi_rapi = {
        "Core": "Home",
        "CoreSingleLanguage": "Home",
        "Professional": "Pro",
        "Enterprise": "Enterprise",
        "Education": "Education",
    }.get(edisi, edisi)

    return f"{nama} {edisi_rapi}".strip()


def nama_perangkat() -> str:
    return f"{_nama_komputer()} ({nama_windows()})"


def info_sistem() -> str:
    return f"{nama_windows()} {platform.machine()}"


# ==========================================================================
# BERKAS LISENSI LOKAL
# ==========================================================================
@dataclass
class Lisensi:
    """Isi lisensi yang sedang dipakai di komputer ini."""

    kunci: str = ""
    paket: str = ""
    fitur: dict = None
    pemilik: str = ""
    sidik: str = ""
    berlaku_sampai: float = 0.0
    tenggang_sampai: float = 0.0
    muatan: str = ""
    tanda: str = ""

    def __post_init__(self):
        if self.fitur is None:
            self.fitur = {}

    @classmethod
    def dari_muatan(cls, muatan: str, tanda: str) -> "Lisensi":
        """
        Susun lisensi dari muatan yang sudah ditandatangani server.

        Seluruh keterangan penting dibaca dari muatan bertanda tangan itu,
        bukan dari kolom terpisah di berkas. Dengan begitu menyunting kolom
        lain di berkas tidak mengubah apa yang diyakini aplikasi, karena
        nilai yang dipakai selalu berasal dari bagian yang tanda tangannya
        diperiksa.
        """
        try:
            isi = json.loads(muatan)
        except Exception:
            isi = {}

        return cls(
            kunci=isi.get("kunci", ""),
            paket=isi.get("paket", ""),
            fitur=isi.get("fitur", {}) or {},
            pemilik=isi.get("pemilik", ""),
            sidik=isi.get("sidik", ""),
            berlaku_sampai=_waktu(isi.get("berlaku_sampai")),
            tenggang_sampai=_waktu(isi.get("tenggang_sampai")),
            muatan=muatan,
            tanda=tanda,
        )

    @property
    def enterprise(self) -> bool:
        return self.paket == "enterprise"

    @property
    def nama_paket(self) -> str:
        return "Enterprise" if self.enterprise else "Standar"

    def punya(self, fitur: str) -> bool:
        """Apakah paket ini memuat fitur tertentu."""
        return bool(self.fitur.get(fitur))

    def masih_berlaku(self) -> bool:
        """Apakah keterangan lisensi lokal masih dalam masa berlaku."""
        return time.time() < self.berlaku_sampai

    def dalam_tenggang(self) -> bool:
        return self.masih_berlaku() or time.time() < self.tenggang_sampai

    def sisa_hari(self) -> int:
        """Sisa hari sebelum keterangan lisensi perlu diperbarui."""
        sisa = self.berlaku_sampai - time.time()
        return max(0, int(sisa // 86400))


def path_lisensi(data_dir: Path) -> Path:
    return data_dir / "lisensi.json"


def simpan(data_dir: Path, lisensi: Lisensi) -> None:
    """
    Simpan lisensi ke komputer.

    Yang disimpan hanya muatan bertanda tangan dan tanda tangannya. Kolom
    turunan tidak ikut ditulis supaya tidak ada nilai di berkas yang dapat
    disunting untuk mengubah arti lisensi.
    """
    data_dir.mkdir(parents=True, exist_ok=True)
    berkas = path_lisensi(data_dir)
    sementara = berkas.with_suffix(".tmp")
    sementara.write_text(json.dumps({
        "muatan": lisensi.muatan,
        "tanda": lisensi.tanda,
    }, indent=2), encoding="utf-8")
    sementara.replace(berkas)


def muat(data_dir: Path) -> Lisensi | None:
    """
    Baca lisensi yang tersimpan, atau None bila belum ada.

    Keterangan lisensi disusun ulang dari muatan yang ditandatangani server.
    Kolom lain di berkas tidak dipakai, sehingga menyuntingnya tidak
    berpengaruh terhadap paket maupun masa berlaku yang diyakini aplikasi.
    """
    berkas = path_lisensi(data_dir)
    if not berkas.exists():
        return None
    try:
        isi = json.loads(berkas.read_text(encoding="utf-8"))
    except Exception:
        return None

    muatan = isi.get("muatan", "")
    tanda = isi.get("tanda", "")
    if not muatan or not tanda:
        return None

    return Lisensi.dari_muatan(muatan, tanda)


def hapus(data_dir: Path) -> None:
    berkas = path_lisensi(data_dir)
    if berkas.exists():
        berkas.unlink()


# ==========================================================================
# PEMERIKSAAN TANDA TANGAN
# ==========================================================================
def tanda_sah(muatan: str, tanda_hex: str) -> bool:
    """
    Periksa tanda tangan server atas isi lisensi.

    Bila seseorang menyunting berkas lisensi untuk memperpanjang masa
    berlaku atau menaikkan paket, tanda tangannya tidak lagi cocok dan
    lisensi ditolak.
    """
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives.asymmetric import ed25519
    except ImportError:
        # Tanpa pustaka pemeriksa, lisensi dianggap tidak sah. Lebih baik
        # menolak daripada menerima berkas yang tidak dapat diperiksa.
        return False

    try:
        publik = ed25519.Ed25519PublicKey.from_public_bytes(
            bytes.fromhex(KUNCI_PUBLIK))
        publik.verify(bytes.fromhex(tanda_hex), muatan.encode("utf-8"))
        return True
    except (InvalidSignature, ValueError, TypeError):
        return False


def lisensi_sah(data_dir: Path) -> tuple[bool, str, Lisensi | None]:
    """
    Periksa lisensi yang tersimpan di komputer.

    Mengembalikan (sah, alasan, lisensi). Pemeriksaan berjalan tanpa
    internet: yang diperiksa adalah tanda tangan server dan kecocokan
    perangkat.

    Lisensi berlaku selamanya, jadi habisnya masa berlaku tanda tangan
    bukan alasan menolak membuka aplikasi. Yang perlu diperbarui hanya
    keterangan lokalnya; aplikasi tetap dapat dipakai dan pengguna
    diingatkan untuk menyambung internet.
    """
    lisensi = muat(data_dir)
    if lisensi is None:
        return False, "Lisensi belum diaktifkan di komputer ini.", None

    if not lisensi.kunci or not lisensi.tanda or not lisensi.muatan:
        return False, "Berkas lisensi tidak lengkap.", None

    if not tanda_sah(lisensi.muatan, lisensi.tanda):
        return False, ("Berkas lisensi tidak sah. Berkas ini mungkin sudah "
                       "diubah. Aktifkan ulang dengan kunci lisensi Anda."), None

    if not sidik_cocok(lisensi.sidik):
        return False, ("Lisensi ini terdaftar untuk perangkat lain. "
                       "Aktifkan ulang dengan kunci lisensi Anda."), None

    return True, "", lisensi


def perlu_verifikasi(data_dir: Path) -> bool:
    """
    Apakah lisensi perlu diperiksa ulang ke server.

    Lisensi tidak kedaluwarsa, tetapi keterangan lokalnya perlu diperbarui
    berkala supaya pencabutan lisensi (misalnya karena diperjualbelikan
    kembali) dapat berlaku. Selama belum tersambung, aplikasi tetap dapat
    dipakai.
    """
    lisensi = muat(data_dir)
    if lisensi is None:
        return False
    return not lisensi.masih_berlaku()


# ==========================================================================
# KOMUNIKASI DENGAN SERVER
# ==========================================================================
def _kirim(permintaan: dict) -> tuple[bool, dict]:
    """Kirim permintaan ke layanan lisensi, kembalikan (berhasil, jawaban)."""
    badan = json.dumps(permintaan).encode("utf-8")
    panggilan = urllib.request.Request(
        ALAMAT_SERVER,
        data=badan,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(
                panggilan, timeout=BATAS_WAKTU_SERVER) as jawaban:
            return True, json.loads(jawaban.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        # Server menjawab dengan penjelasan, misalnya lisensi sudah dipakai
        # di perangkat lain.
        try:
            return True, json.loads(e.read().decode("utf-8"))
        except (ValueError, OSError) as galat:
            _catat(f"Jawaban server tidak dapat dibaca (HTTP {e.code}): {galat}")
            return False, {"pesan": "Layanan lisensi tidak dapat dihubungi."}
    except Exception as galat:
        _catat(f"Gagal menghubungi layanan lisensi: {galat}")
        return False, {"pesan": ("Tidak dapat menghubungi layanan lisensi. "
                                 "Periksa sambungan internet Anda.")}


def _catat(pesan: str) -> None:
    """
    Tuliskan kegagalan layanan lisensi ke berkas catatan aplikasi.

    Kegagalan sambungan tidak boleh menghentikan aplikasi, tetapi juga tidak
    boleh hilang tanpa jejak: bila pengguna melaporkan masalah aktivasi,
    catatan ini yang menunjukkan penyebabnya.
    """
    try:
        from .. import config
        from datetime import datetime
        with open(config.LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] Lisensi: {pesan}\n")
    except Exception:
        # Pencatatan tidak boleh menggagalkan proses aktivasi.
        pass


def _sidik_untuk_server(data_dir: Path) -> tuple[str, str]:
    """
    Sidik yang dikirim ke server, beserta calon penggantinya.

    Sidik yang sudah terdaftar dipakai lebih dulu supaya perangkat yang
    sudah terdaftar tetap dikenali server meskipun cara menghitung sidik
    berubah. Tanpa ini, seluruh pelanggan yang sudah mengaktifkan lisensi
    akan dianggap perangkat baru setelah memperbarui aplikasi, dan pada
    paket Standar mereka langsung ditolak karena batas satu perangkat.

    Sidik terbaru ikut dikirim sebagai calon pengganti, sehingga server
    yang sudah diperbarui dapat menaikkan pengikatan perangkat ke ciri
    yang lebih sukar ditiru. Server yang belum diperbarui mengabaikan
    bagian itu tanpa menimbulkan masalah.
    """
    baru = sidik_perangkat()
    lisensi = muat(data_dir)
    if lisensi is not None and lisensi.sidik:
        return lisensi.sidik, baru
    return baru, baru


def aktivasi(data_dir: Path, kunci: str) -> tuple[bool, str, Lisensi | None]:
    """
    Aktifkan lisensi di komputer ini.

    Server memutuskan apakah kunci boleh dipakai di perangkat ini, lalu
    mengirim jawaban bertanda tangan yang disimpan di komputer.
    """
    kunci_bersih = "".join(c for c in kunci.upper() if c.isalnum())
    if len(kunci_bersih) != 20 or not kunci_bersih.startswith("ATNT"):
        return False, ("Format kunci lisensi tidak sesuai. Contoh yang benar: "
                       "ATNT-XXXX-XXXX-XXXX-XXXX"), None

    sidik_kirim, sidik_baru = _sidik_untuk_server(data_dir)
    terhubung, jawaban = _kirim({
        "aksi": "aktivasi",
        "kunci": kunci_bersih,
        "sidik": sidik_kirim,
        "sidik_baru": sidik_baru,
        "nama_perangkat": nama_perangkat(),
        "os_info": info_sistem(),
        "versi_app": _versi_app(),
    })

    if not terhubung:
        return False, jawaban.get("pesan", "Gagal menghubungi server."), None

    if not jawaban.get("ok"):
        return False, jawaban.get("pesan", "Lisensi ditolak."), None

    muatan_teks = jawaban.get("muatan", "")
    tanda = jawaban.get("tanda", "")

    if not tanda_sah(muatan_teks, tanda):
        return False, ("Jawaban server tidak dapat diperiksa keasliannya. "
                       "Hubungi pengembang."), None

    lisensi = Lisensi.dari_muatan(muatan_teks, tanda)
    simpan(data_dir, lisensi)
    return True, "", lisensi


def perbarui(data_dir: Path) -> tuple[bool, str]:
    """
    Perbarui masa berlaku lisensi dengan menghubungi server.

    Dipanggil berkala saat aplikasi dipakai. Bila internet tidak tersedia,
    lisensi lama tetap dipakai sampai masa tenggangnya habis.
    """
    lisensi = muat(data_dir)
    if lisensi is None:
        return False, "Lisensi belum diaktifkan."

    sidik_kirim, sidik_baru = _sidik_untuk_server(data_dir)
    terhubung, jawaban = _kirim({
        "aksi": "verifikasi",
        "kunci": lisensi.kunci,
        "sidik": sidik_kirim,
        "sidik_baru": sidik_baru,
        "nama_perangkat": nama_perangkat(),
        "os_info": info_sistem(),
        "versi_app": _versi_app(),
    })

    if not terhubung:
        return False, jawaban.get("pesan", "Server tidak dapat dihubungi.")

    if not jawaban.get("ok"):
        return False, jawaban.get("pesan", "Lisensi ditolak.")

    muatan_teks = jawaban.get("muatan", "")
    tanda = jawaban.get("tanda", "")

    if not tanda_sah(muatan_teks, tanda):
        return False, "Jawaban server tidak dapat diperiksa keasliannya."

    simpan(data_dir, Lisensi.dari_muatan(muatan_teks, tanda))
    return True, ""


def lepas(data_dir: Path) -> tuple[bool, str]:
    """
    Lepaskan perangkat ini dari lisensi.

    Dipakai saat pengguna pindah komputer. Setelah dilepas, kunci yang sama
    dapat diaktifkan di komputer lain.
    """
    lisensi = muat(data_dir)
    if lisensi is None:
        return False, "Lisensi belum diaktifkan."

    terhubung, jawaban = _kirim({
        "aksi": "lepas",
        "kunci": lisensi.kunci,
        "sidik": sidik_perangkat(),
        "nama_perangkat": nama_perangkat(),
    })

    if not terhubung:
        return False, jawaban.get("pesan", "Server tidak dapat dihubungi.")

    if not jawaban.get("ok"):
        return False, jawaban.get("pesan", "Gagal melepas perangkat.")

    hapus(data_dir)
    return True, "Perangkat ini sudah dilepas dari lisensi."


def _waktu(teks) -> float:
    """Ubah waktu berformat ISO dari server menjadi angka waktu lokal."""
    if not teks:
        return 0.0
    try:
        from datetime import datetime, timezone
        bersih = str(teks).replace("Z", "+00:00")
        return datetime.fromisoformat(bersih).replace(
            tzinfo=timezone.utc).timestamp()
    except Exception:
        return 0.0


def _versi_app() -> str:
    try:
        from .. import config
        return f"{config.APP_VERSION} ({config.APP_BUILD})"
    except Exception:
        return ""


# ==========================================================================
# KETERANGAN PAKET
# ==========================================================================
# Fitur yang hanya tersedia pada paket Enterprise. Daftar ini dipakai untuk
# memberi keterangan kepada pengguna, dan harus sejalan dengan penjagaan di
# ui/batas_paket.py. Fitur yang belum benar-benar ada di aplikasi tidak
# dicantumkan supaya keterangan paket tidak menjanjikan hal yang keliru.
FITUR_ENTERPRISE = {
    "konsolidasi": "Konsolidasi multi-entitas",
    "dimensi": "Dimensi biaya dan proyek",
    "pajak_lanjutan": "Pajak lanjutan",
    "audit_lanjutan": "Riwayat perubahan data",
    "multi_entitas": "Beberapa badan usaha",
}


def fitur_tersedia(lisensi: Lisensi | None, fitur: str) -> bool:
    """Apakah fitur tertentu boleh dipakai pada paket ini."""
    if lisensi is None:
        return False
    if lisensi.enterprise:
        return True
    return bool(lisensi.fitur.get(fitur))
