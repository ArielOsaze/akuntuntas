"""
Perbaiki pola pembersihan layout: simpan widget ke variabel lokal sebelum
dilepas dari induknya.

Pola lama:
    if item.widget() is not None:
        item.widget().setParent(None)
        item.widget().deleteLater()   # item.widget() sudah None

Pola baru:
    wdg = item.widget()
    if wdg is not None:
        wdg.setParent(None)
        wdg.deleteLater()
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent

POLA = re.compile(
    r"(?P<indent>[ \t]+)if item\.widget\(\) is not None:\n"
    r"(?P=indent)[ \t]+item\.widget\(\)\.setParent\(None\)\n"
    r"(?P=indent)[ \t]+item\.widget\(\)\.deleteLater\(\)")

GANTI = (r"\g<indent>wdg = item.widget()\n"
         r"\g<indent>if wdg is not None:\n"
         r"\g<indent>    wdg.setParent(None)\n"
         r"\g<indent>    wdg.deleteLater()")


def main() -> int:
    tulis = "--tulis" in sys.argv
    total = 0
    for p in sorted((AKAR / "src").rglob("*.py")):
        t = p.read_text(encoding="utf-8")
        baru, n = POLA.subn(GANTI, t)
        if n:
            total += n
            print(f"{'DIPERBARUI' if tulis else 'PERLU'} "
                  f"{p.relative_to(AKAR)}: {n} tempat")
            if tulis:
                p.write_text(baru, encoding="utf-8")
    print(f"\nTotal: {total} tempat")
    return 0


if __name__ == "__main__":
    sys.exit(main())
