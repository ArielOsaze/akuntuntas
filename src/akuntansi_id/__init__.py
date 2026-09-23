"""AkunTuntas - Pembukuan & Pajak Perusahaan Indonesia."""

# Catatan: config sengaja tidak diimpor di sini. Modul config membaca
# AKUNTANSIID_DATA saat pertama dimuat, sehingga impor di level paket akan
# mengunci folder data sebelum argumen --data diproses.

__all__ = ["APP_NAME", "APP_VERSION", "APP_LONG_NAME"]


def __getattr__(nama: str):
    """Ambil konstanta identitas aplikasi tanpa memuat config lebih awal."""
    if nama not in ("APP_NAME", "APP_VERSION", "APP_LONG_NAME"):
        raise AttributeError(f"module {__name__!r} has no attribute {nama!r}")
    import importlib
    return getattr(importlib.import_module(".config", __name__), nama)


def __dir__():
    return sorted(__all__)
