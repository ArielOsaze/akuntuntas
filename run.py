"""Peluncur AkunTuntas — untuk pemakaian dari source atau setelah dibundel."""
import os
import sys

# pastikan paket dapat ditemukan saat dijalankan langsung
_ini = os.path.dirname(os.path.abspath(__file__))
_src = os.path.join(_ini, "src")
if os.path.isdir(_src) and _src not in sys.path:
    sys.path.insert(0, _src)

from akuntansi_id.__main__ import main

if __name__ == "__main__":
    sys.exit(main())
