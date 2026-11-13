"""
Uji fitur dua halaman berdampingan.

Memeriksa panel kedua dapat dibuka dan ditutup, halaman di dalamnya dapat
diganti tanpa menumpuk widget lama, tautan di panel kanan tidak memindahkan
halaman kiri, dan kedua sisi menyegarkan diri setelah data berubah.
"""
import os
import shutil
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
_DIR_UJI = Path(__file__).parent.parent / "_ujidua"
if _DIR_UJI.exists():
    shutil.rmtree(_DIR_UJI, ignore_errors=True)
os.environ["AKUNTANSIID_DATA"] = str(_DIR_UJI)

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from PySide6.QtWidgets import QApplication

from akuntansi_id import config, db, services
from akuntansi_id.core import security as sec
from akuntansi_id.core.license import Lisensi
from akuntansi_id.ui import popup, theme
from akuntansi_id.ui.main_window import MainWindow

lulus = 0
gagal = 0


def cek(nama, kondisi, detail=""):
    global lulus, gagal
    if kondisi:
        lulus += 1
        print(f"OK     {nama}")
    else:
        gagal += 1
        print(f"GAGAL  {nama}  {detail}")


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    theme.pasang_font(app)
    theme.palet_terang(app)
    app.setStyleSheet(theme.stylesheet())
    popup.beri_tahu = lambda *a, **k: None
    popup.peringatkan = lambda *a, **k: None
    popup.galat = lambda *a, **k: None
    popup.tanya = lambda *a, **k: False

    config.ensure_dirs()
    db.init_db()
    sec.ensure_default_admin()
    perusahaan = services.list_companies(aktif_saja=False)
    cid = (perusahaan[0]["id"] if perusahaan else
           services.create_company("PT Uji Dua Halaman", "pt", pkp=False))
    hasil = sec.login("admin", config.DEFAULT_ADMIN_PASSWORD)
    lisensi = Lisensi(kunci="ATNTUJI", paket="enterprise", fitur={})

    jendela = MainWindow(hasil, lisensi=lisensi)
    jendela.ctx.company_id = cid
    jendela.ctx.company = services.get_company(cid)
    jendela.resize(1760, 1000)
    jendela.show()
    app.processEvents()

    jendela._navigasi("penjualan")
    app.processEvents()
    kiri = jendela.halaman["penjualan"]

    cek("panel kedua tersembunyi sebelum diminta",
        not jendela.panel_kanan.isVisible())
    cek("tombol dua halaman tidak tercentang",
        not jendela.btn_dua.isChecked() and not jendela.a_dua.isChecked())

    jendela.btn_dua.click()
    app.processEvents()
    cek("panel kedua terbuka dari tombol baris status",
        jendela.panel_kanan.isVisible())
    cek("menu Tampilan ikut tercentang", jendela.a_dua.isChecked())
    cek("halaman kedua terpasang",
        jendela._kode_kanan != "" and
        jendela.panel_kanan.tumpuk.count() == 1,
        f"kode={jendela._kode_kanan!r} isi={jendela.panel_kanan.tumpuk.count()}")
    cek("pemilih halaman kedua memuat menu",
        jendela.panel_kanan.pilih.count() >= 20,
        str(jendela.panel_kanan.pilih.count()))

    combo = jendela.panel_kanan.pilih
    idx = combo.findData("biaya")
    cek("Biaya tersedia di pemilih halaman kedua", idx >= 0)
    combo.setCurrentIndex(idx)
    app.processEvents()
    cek("halaman kedua berganti ke Biaya",
        jendela._kode_kanan == "biaya" and
        type(jendela.panel_kanan.tumpuk.currentWidget()).__name__ == "BiayaPage")
    cek("halaman lama tidak menumpuk",
        jendela.panel_kanan.tumpuk.count() == 1,
        str(jendela.panel_kanan.tumpuk.count()))
    cek("halaman kiri tetap Penjualan",
        jendela.stack.currentWidget() is kiri and
        jendela._kode_aktif == "penjualan")

    # Tautan di panel kanan harus mengganti isi panel kanan, bukan kiri.
    jendela._pindah_dari_kanan("bank")
    app.processEvents()
    cek("tautan di panel kanan membuka halaman di panel kanan",
        jendela._kode_kanan == "bank" and
        jendela._kode_aktif == "penjualan")
    cek("pindah dari panel kanan tidak menumpuk halaman",
        jendela.panel_kanan.tumpuk.count() == 1)

    # Data berubah: kedua sisi harus memuat ulang, angka tidak boleh basi.
    halaman_kanan = jendela.panel_kanan.tumpuk.currentWidget()
    panggilan = {"kiri": 0, "kanan": 0}
    asli_kiri = kiri.muat
    asli_kanan = halaman_kanan.muat

    def hitung_kiri():
        panggilan["kiri"] += 1
        asli_kiri()

    def hitung_kanan():
        panggilan["kanan"] += 1
        asli_kanan()

    kiri.muat = hitung_kiri
    halaman_kanan.muat = hitung_kanan
    db._naikkan_revisi()
    jendela._navigasi("penjualan")
    app.processEvents()
    cek("halaman kiri dimuat ulang setelah data berubah",
        panggilan["kiri"] == 1, str(panggilan))
    cek("halaman kedua dimuat ulang setelah data berubah",
        panggilan["kanan"] == 1, str(panggilan))

    # Menutup panel mengembalikan halaman kiri seperti semula.
    jendela.panel_kanan.tutup_diminta.emit()
    app.processEvents()
    cek("panel kedua tertutup",
        not jendela.panel_kanan.isVisible())
    cek("centang tombol dan menu ikut dilepas",
        not jendela.btn_dua.isChecked() and not jendela.a_dua.isChecked())
    cek("halaman kiri tetap utuh setelah panel ditutup",
        jendela.stack.currentWidget() is kiri and
        jendela._kode_aktif == "penjualan")

    # Membuka lagi mengingat halaman terakhir dan tidak membuat ulang.
    jendela.a_dua.trigger()
    app.processEvents()
    cek("panel kedua dibuka lagi dari menu",
        jendela.panel_kanan.isVisible() and
        jendela._kode_kanan == "bank")
    cek("membuka lagi memakai halaman yang sama",
        jendela.panel_kanan.tumpuk.currentWidget() is halaman_kanan)

    cek("pintasan dua halaman tersedia",
        jendela.a_dua.shortcut().toString() == "Ctrl+Shift+D",
        jendela.a_dua.shortcut().toString())

    # Pada jendela sempit, halaman digeser mendatar, bukan dihimpit.
    jendela.resize(1180, 760)
    app.processEvents()
    cek("jendela menyempit tanpa mengubah halaman kiri",
        jendela._kode_aktif == "penjualan")
    cek("isi kiri dapat digeser mendatar saat sempit",
        jendela.gulir_kiri.horizontalScrollBar().maximum() > 0,
        str(jendela.gulir_kiri.horizontalScrollBar().maximum()))

    print(f"HASIL: {lulus} LULUS, {gagal} GAGAL")
    return 1 if gagal else 0


if __name__ == "__main__":
    sys.exit(main())
