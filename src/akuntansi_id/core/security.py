"""
AkunTuntas - Keamanan, Autentikasi & Manajemen Pengguna
========================================================
Karena aplikasi ini menyimpan data pembukuan (rahasia perusahaan), akses
WAJIB melalui login.

Metode keamanan:
- Password di-hash dengan PBKDF2-HMAC-SHA256, 480.000 iterasi, salt acak 16 byte
  (rekomendasi NIST SP 800-63B). Password TIDAK PERNAH disimpan sebagai teks biasa.
- Pembatasan percobaan login (rate limiting) untuk mencegah brute force.
- Setiap aktivitas penting dicatat di audit_log (jejak audit untuk kebutuhan
  pemeriksaan pajak - Pasal 28 UU KUP).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from .. import config, db

PBKDF2_ITERATIONS = 480_000
SALT_BYTES = 16


# ==========================================================================
# HASHING PASSWORD
# ==========================================================================
def hash_password(password: str, salt: Optional[bytes] = None) -> tuple[str, str]:
    """Kembalikan (hash_b64, salt_b64)."""
    if salt is None:
        salt = secrets.token_bytes(SALT_BYTES)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return base64.b64encode(dk).decode(), base64.b64encode(salt).decode()


def verify_password(password: str, hash_b64: str, salt_b64: str) -> bool:
    try:
        salt = base64.b64decode(salt_b64)
    except Exception:
        return False
    candidate, _ = hash_password(password, salt)
    return hmac.compare_digest(candidate, hash_b64)


# ==========================================================================
# KEBIJAKAN PASSWORD
# ==========================================================================
def password_strength(password: str) -> tuple[int, str, list[str]]:
    """Skor 0-4, label, dan daftar saran perbaikan."""
    issues: list[str] = []
    score = 0
    if len(password) >= 8:
        score += 1
    else:
        issues.append(f"Minimal {config.MIN_PASSWORD_LENGTH} karakter.")
    if len(password) >= 12:
        score += 1
    if re.search(r"[A-Z]", password) and re.search(r"[a-z]", password):
        score += 1
    else:
        issues.append("Gabungkan huruf besar dan huruf kecil.")
    if re.search(r"\d", password):
        score += 1
    else:
        issues.append("Tambahkan minimal satu angka.")
    if re.search(r"[^A-Za-z0-9]", password):
        score += 1
    else:
        issues.append("Tambahkan simbol (mis. ! @ # $ %).")
    if password.lower() in {
        "password", "12345678", "admin123", "qwerty123", "11111111",
        "akuntansi", "administrator", "password123",
    }:
        score = 0
        issues.append("Password terlalu umum dan mudah ditebak.")

    score = min(score, 4)
    label = ["Sangat Lemah", "Lemah", "Cukup", "Kuat", "Sangat Kuat"][score]
    return score, label, issues


def is_password_acceptable(password: str) -> tuple[bool, list[str]]:
    if len(password) < config.MIN_PASSWORD_LENGTH:
        return False, [f"Password minimal {config.MIN_PASSWORD_LENGTH} karakter."]
    score, _, issues = password_strength(password)
    if score < 2:
        return False, issues
    return True, []


# ==========================================================================
# HASIL LOGIN
# ==========================================================================
@dataclass
class LoginResult:
    ok: bool
    user_id: Optional[int] = None
    username: str = ""
    full_name: str = ""
    role: str = "owner"
    app_mode: str = "beginner"
    mode_dipilih: bool = False
    must_change_pw: bool = False
    message: str = ""
    attempts_left: int = config.MAX_LOGIN_ATTEMPTS


# ==========================================================================
# MANAJEMEN PENGGUNA
# ==========================================================================
def count_users() -> int:
    return int(db.scalar("SELECT COUNT(*) FROM users", default=0))


def ensure_default_admin() -> None:
    """Buat akun admin pertama bila belum ada user sama sekali."""
    if count_users() > 0:
        return
    h, s = hash_password(config.DEFAULT_ADMIN_PASSWORD)
    db.ex(
        "INSERT INTO users(username, full_name, password_hash, salt, role, "
        "must_change_pw, app_mode) VALUES(?,?,?,?,?,?,?)",
        (config.DEFAULT_ADMIN_USER, "Administrator", h, s, "owner", 1, "beginner"),
    )
    db.log_action(None, "system", None, "user.create", "users",
                  config.DEFAULT_ADMIN_USER, "Akun admin awal dibuat.")


def create_user(username: str, password: str, full_name: str = "",
                role: str = "staff", email: str = "",
                app_mode: str = "beginner", must_change: bool = 1) -> int:
    username = username.strip()
    if not username:
        raise ValueError("Nama pengguna tidak boleh kosong.")
    if db.q1("SELECT 1 FROM users WHERE username = ? COLLATE NOCASE", (username,)):
        raise ValueError(f"Nama pengguna '{username}' sudah dipakai.")
    ok, issues = is_password_acceptable(password)
    if not ok:
        raise ValueError(" ".join(issues))
    h, s = hash_password(password)
    with db.tx() as conn:
        cur = conn.execute(
            "INSERT INTO users(username, full_name, email, password_hash, salt, role, "
            "must_change_pw, app_mode) VALUES(?,?,?,?,?,?,?,?)",
            (username, full_name, email, h, s, role, must_change, app_mode),
        )
        uid = cur.lastrowid
    db.log_action(uid, username, None, "user.create", "users", uid)
    return uid


def change_password(user_id: int, old_password: str, new_password: str) -> None:
    row = db.q1("SELECT username, password_hash, salt FROM users WHERE id=?", (user_id,))
    if row is None:
        raise ValueError("Pengguna tidak ditemukan.")
    if not verify_password(old_password, row["password_hash"], row["salt"]):
        raise ValueError("Password lama tidak sesuai.")
    if verify_password(new_password, row["password_hash"], row["salt"]):
        raise ValueError("Password baru tidak boleh sama dengan password lama.")
    ok, issues = is_password_acceptable(new_password)
    if not ok:
        raise ValueError(" ".join(issues))
    h, s = hash_password(new_password)
    db.ex("UPDATE users SET password_hash=?, salt=?, must_change_pw=0, "
          "updated_at=datetime('now','localtime') WHERE id=?", (h, s, user_id))
    db.log_action(user_id, row["username"], None, "user.change_password", "users", user_id)


def reset_password(user_id: int, new_password: str, actor_id: Optional[int] = None,
                   actor_name: str = "", password_aktor: str = "") -> None:
    """
    Ganti password pengguna oleh pengelola akun.

    Password pengelola yang sedang masuk wajib disertakan. Tanpa
    pemeriksaan ini, siapa pun yang sudah masuk dapat mengganti password
    akun lain, termasuk akun pemilik, sehingga jalan masuk ke aplikasi
    dapat diambil alih tanpa diketahui pemiliknya.

    Parameter password_aktor diisi password pengelola yang sedang masuk,
    untuk dipastikan bahwa memang pengelola itu sendiri yang meminta.
    """
    if not actor_id:
        raise ValueError(
            "Penggantian password harus dilakukan oleh pengelola akun "
            "yang sedang masuk.")

    if not password_aktor:
        raise ValueError("Password Anda wajib diisi untuk melanjutkan.")

    baris = db.q1("SELECT username, password_hash, salt, is_active "
                  "FROM users WHERE id=?", (actor_id,))
    if baris is None:
        raise ValueError("Akun pengelola tidak ditemukan.")
    if not baris["is_active"]:
        raise ValueError("Akun pengelola sedang dinonaktifkan.")
    if not verify_password(password_aktor, baris["password_hash"],
                           baris["salt"]):
        db.log_login(baris["username"], False, actor_id,
                     f"Password pengelola salah saat mengganti password "
                     f"pengguna id {user_id}.")
        raise ValueError("Password Anda salah. Perubahan dibatalkan.")

    ok, issues = is_password_acceptable(new_password)
    if not ok:
        raise ValueError(" ".join(issues))
    h, s = hash_password(new_password)
    db.ex("UPDATE users SET password_hash=?, salt=?, must_change_pw=1, "
          "failed_attempts=0, locked_until=NULL WHERE id=?", (h, s, user_id))
    db.log_action(actor_id, actor_name, None, "user.reset_password",
                  "users", user_id)


def list_users() -> list:
    return db.q("SELECT id, username, full_name, email, jabatan, role, is_active, "
                "must_change_pw, app_mode, last_login, created_at FROM users "
                "ORDER BY id")


def update_user_mode(user_id: int, mode: str) -> None:
    """Simpan mode pilihan pengguna dan tandai sudah pernah memilih.

    Penanda ini membuat pertanyaan mode hanya muncul sekali - setelah itu
    mode tersimpan dan dapat diubah kapan saja dari menu Pengaturan.
    """
    if mode not in ("beginner", "expert"):
        raise ValueError("Mode tidak dikenal.")
    db.ex("UPDATE users SET app_mode=?, mode_dipilih=1 WHERE id=?", (mode, user_id))


def set_user_active(user_id: int, active: bool, actor_id=None, actor_name="") -> None:
    if not active:
        owners = int(db.scalar("SELECT COUNT(*) FROM users WHERE role='owner' AND is_active=1"))
        target = db.q1("SELECT role FROM users WHERE id=?", (user_id,))
        if target and target["role"] == "owner" and owners <= 1:
            raise ValueError("Tidak dapat menonaktifkan satu-satunya pemilik akun.")
    db.ex("UPDATE users SET is_active=? WHERE id=?", (1 if active else 0, user_id))
    db.log_action(actor_id, actor_name, None,
                  "user.activate" if active else "user.deactivate", "users", user_id)


# ==========================================================================
# LOGIN
# ==========================================================================
def login(username: str, password: str) -> LoginResult:
    username = (username or "").strip()
    if not username:
        return LoginResult(ok=False, message="Nama pengguna belum diisi.")

    row = db.q1("SELECT * FROM users WHERE username = ? COLLATE NOCASE", (username,))
    if row is None:
        # Jangan ungkap apakah username ada atau tidak (mencegah user enumeration)
        db.log_login(username, False, None,
                     "Nama pengguna tidak dikenal.")
        return LoginResult(ok=False, message="Nama pengguna atau password salah.")

    if not row["is_active"]:
        db.log_login(username, False, row["id"], "Akun sedang dinonaktifkan.")
        return LoginResult(ok=False, message="Akun ini dinonaktifkan. Hubungi pemilik akun.")

    # Cek penguncian
    if row["locked_until"]:
        try:
            locked_until = datetime.fromisoformat(row["locked_until"])
            if datetime.now() < locked_until:
                sisa = int((locked_until - datetime.now()).total_seconds())
                db.log_login(username, False, row["id"],
                             f"Percobaan saat akun terkunci (sisa {sisa} detik).")
                return LoginResult(
                    ok=False,
                    message=f"Akun terkunci sementara. Coba lagi dalam {sisa} detik.",
                )
        except ValueError:
            pass

    if not verify_password(password, row["password_hash"], row["salt"]):
        attempts = int(row["failed_attempts"]) + 1
        remaining = max(0, config.MAX_LOGIN_ATTEMPTS - attempts)
        if attempts >= config.MAX_LOGIN_ATTEMPTS:
            until = datetime.now() + timedelta(seconds=config.LOCKOUT_SECONDS)
            db.ex("UPDATE users SET failed_attempts=?, locked_until=? WHERE id=?",
                  (attempts, until.isoformat(timespec="seconds"), row["id"]))
            db.log_action(row["id"], username, None, "login.locked", "users",
                          row["id"],
                          f"Akun dikunci setelah {attempts} percobaan gagal.",
                          db.KATEGORI_KEAMANAN)
            return LoginResult(
                ok=False,
                message=f"Terlalu banyak percobaan gagal. Akun dikunci "
                        f"{config.LOCKOUT_SECONDS // 60} menit.",
            )
        db.ex("UPDATE users SET failed_attempts=? WHERE id=?", (attempts, row["id"]))
        db.log_login(username, False, row["id"],
                     f"Password salah (percobaan ke-{attempts}).")
        return LoginResult(
            ok=False,
            message=f"Nama pengguna atau password salah. "
                    f"Sisa percobaan: {remaining}.",
            attempts_left=remaining,
        )

    # Sukses
    db.ex("UPDATE users SET failed_attempts=0, locked_until=NULL, "
          "last_login=datetime('now','localtime') WHERE id=?", (row["id"],))
    db.log_login(username, True, row["id"], "Berhasil masuk aplikasi.")
    return LoginResult(
        ok=True,
        user_id=row["id"],
        username=row["username"],
        full_name=row["full_name"] or row["username"],
        role=row["role"],
        app_mode=row["app_mode"] if "app_mode" in row.keys() else "beginner",
        mode_dipilih=bool(row["mode_dipilih"]) if "mode_dipilih" in row.keys() else False,
        must_change_pw=bool(row["must_change_pw"]),
        message="Login berhasil.",
    )


def logout(user_id: Optional[int], username: str) -> None:
    db.log_action(user_id, username, None, "logout", "users", user_id or "",
                  "Keluar dari aplikasi.", db.KATEGORI_KEAMANAN)


def recent_audit(limit: int = 200, kategori: str = None) -> list:
    """
    Jejak audit terbaru, dapat disaring per kategori.

    kategori diisi "keamanan" untuk log masuk/keluar aplikasi, "data" untuk
    perubahan data pembukuan, "administrasi" untuk pengelolaan pengguna dan
    perusahaan, atau None untuk seluruhnya.
    """
    if kategori:
        baris = db.q(
            """SELECT id, ts, username, kategori,
                      action AS action, action AS aksi,
                      entity AS entity, entity AS objek,
                      entity_id, detail,
                      detail AS keterangan,
                      COALESCE(ip_or_host, '') AS sumber
               FROM audit_log WHERE kategori=?
               ORDER BY id DESC LIMIT ?""", (kategori, limit))
    else:
        baris = db.q(
            """SELECT id, ts, username, kategori,
                      action AS action, action AS aksi,
                      entity AS entity, entity AS objek,
                      entity_id, detail,
                      detail AS keterangan,
                      COALESCE(ip_or_host, '') AS sumber
               FROM audit_log ORDER BY id DESC LIMIT ?""", (limit,))
    return baris


def hitung_per_kategori() -> dict:
    """Jumlah catatan per kategori, untuk keterangan di tiap tab."""
    hasil = {k: 0 for k in db.KATEGORI_AUDIT}
    for r in db.q("SELECT kategori, COUNT(*) AS n FROM audit_log "
                  "GROUP BY kategori"):
        hasil[r["kategori"]] = r["n"]
    return hasil


def is_first_run() -> bool:
    return count_users() == 0
