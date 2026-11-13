"""
Uji input nominal besar.

Nominal rupiah di atas Rp2,1 miliar pernah membuat aplikasi berhenti karena
sinyal Qt memakai int 32-bit. Uji ini memastikan nominal besar dapat
diketik, nominal di luar batas ditolak dengan keterangan, dan masukan
ribuan digit tidak menjatuhkan aplikasi.
"""
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
_DIR_UJI = Path(__file__).parent.parent / "_ujibatas_nominal"
if _DIR_UJI.exists():
    import shutil
    shutil.rmtree(_DIR_UJI, ignore_errors=True)
os.environ["AKUNTANSIID_DATA"] = str(_DIR_UJI)

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from PySide6.QtWidgets import QApplication

from akuntansi_id import config, db, services
from akuntansi_id.core import security as sec
from akuntansi_id.ui import popup, widgets as w
from akuntansi_id.ui.pages.penjualan import PanelItem

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

    peringatan = []
    popup.peringatkan = (
        lambda *a, **k: peringatan.append(a[2] if len(a) > 2 else ""))

    config.ensure_dirs()
    db.init_db()
    sec.ensure_default_admin()
    perusahaan = services.list_companies(aktif_saja=False)
    cid = (perusahaan[0]["id"] if perusahaan else
           services.create_company("PT Uji Nominal", "pt", pkp=False))

    inp = w.InputRupiah()
    nilai = []
    inp.valueChanged.connect(nilai.append)

    inp.setText("3000000000")
    app.processEvents()
    cek("nominal 3 miliar tidak menjatuhkan aplikasi",
        nilai and nilai[-1] == 3_000_000_000, f"nilai={nilai[-1:]}")
    cek("pemisah ribuan tampil benar",
        inp.text() == "3.000.000.000", inp.text())

    inp.setText("999999999999999")
    app.processEvents()
    cek("nominal tepat di batas diterima",
        inp.nilai() == w.BATAS_NOMINAL, f"{inp.nilai():,}")

    inp.setText("0003000000000")
    app.processEvents()
    cek("nol di depan tidak dianggap melewati batas",
        inp.nilai() == 3_000_000_000, f"{inp.nilai():,}")

    sebelum = inp.nilai()
    inp.setText("1000000000000000")
    app.processEvents()
    cek("nominal melewati batas dikembalikan ke nilai sebelumnya",
        inp.nilai() == sebelum, f"{inp.nilai():,}")
    cek("penyebab penolakan dijelaskan ke pengguna",
        any("melebihi batas maksimum" in p for p in peringatan),
        str(peringatan))

    try:
        inp.setText("9" * 5000)
        app.processEvents()
        cek("masukan 5000 digit tidak membuat aplikasi berhenti", True)
    except Exception as e:
        cek("masukan 5000 digit tidak membuat aplikasi berhenti", False,
            f"{type(e).__name__}: {e}")

    kelas = type("Konteks", (), {"company_id": cid})
    panel = PanelItem(kelas())
    total = []
    panel.total_berubah.connect(total.append)
    harga = panel.tabel.cellWidget(0, 4)
    harga.setText("3000000000")
    app.processEvents()
    cek("subtotal 3 miliar diumumkan tanpa OverflowError",
        total and total[-1] == 3_000_000_000, f"total={total[-1:]}")
    cek("panel menyimpan harga 3 miliar",
        panel.baris_data[0]["harga_satuan"] == 3_000_000_000)

    print(f"HASIL: {lulus} LULUS, {gagal} GAGAL")
    return 1 if gagal else 0


if __name__ == "__main__":
    sys.exit(main())
