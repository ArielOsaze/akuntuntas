"""Uji tampilan kotak saldo awal: apakah angka yang diketik benar-benar terlihat."""

from __future__ import annotations

import os
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
os.environ["AKUNTANSIID_DATA"] = str(AKAR / "_contoh")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(AKAR / "src"))

from PySide6.QtWidgets import QApplication  # noqa: E402

def main() -> int:
    app = QApplication.instance() or QApplication([])

    from akuntansi_id.ui import theme  # noqa: E402
    app.setStyleSheet(theme.stylesheet())

    from akuntansi_id.ui.pages import coa_page  # noqa: E402

    class Ctx:
        company_id = 1
        tahun = 2026

    dlg = coa_page.DialogSaldoAwal(Ctx())
    dlg.resize(980, 700)
    dlg.show()
    for _ in range(12):
        app.processEvents()

    print("=== KEADAAN AWAL (nilai dari basis data) ===")
    for kode in ("1001", "1002", "1003"):
        inp = dlg.inputs.get(kode)
        if inp:
            print(f"  {kode}: nilai={inp.nilai():>12,}  teks={inp.text()!r:>14}  "
                  f"tinggi={inp.height()}  terlihat={inp.isVisible()}")

    print()
    print("=== SETELAH DIKETIK (seperti pengguna mengetik) ===")
    inp = dlg.inputs["1001"]
    inp.clear()
    for ch in "1000000":
        inp.setText(inp.text() + ch)
        app.processEvents()
    print(f"  1001: nilai={inp.nilai():>12,}  teks={inp.text()!r}")

    for _ in range(8):
        app.processEvents()

    print()
    print("=== UKURAN KOTAK ===")
    print(f"  tinggi kotak : {inp.height()} px")
    print(f"  tinggi ideal : {inp.sizeHint().height()} px")
    fm = inp.fontMetrics()
    print(f"  tinggi huruf : {fm.height()} px")
    perlu = fm.height() + 18 + 2
    print(f"  perlu (huruf + padding + garis): {perlu} px")
    if inp.height() < perlu:
        print(f"  >> TERPOTONG: kotak {inp.height()} px < perlu {perlu} px")
    else:
        print("  >> cukup")

    keluar = AKAR / "_uji_saldo_awal.png"
    dlg.grab().save(str(keluar))
    print(f"\ntangkapan disimpan: {keluar}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
