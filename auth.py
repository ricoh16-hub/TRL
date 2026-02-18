from datetime import datetime
from db import get_connection
from security import verify_pin, verify_password

# Fungsi: verifikasi PIN 6 digit untuk user tertentu
def verify_user_pin(username: str, pin: str) -> bool:
    conn = get_connection()
    try:
        cur = conn.cursor()

        # Ambil data user dan pin
        cur.execute("""
            SELECT ul.user_id,
                   ul.username,
                   lk.pin_hash,
                   lk.pin_salt,
                   lk.is_locked,
                   lk.failed_attempt,
                   lk.max_attempt
              FROM user_login ul
              JOIN user_lock lk ON ul.user_id = lk.user_id
             WHERE ul.username = ?
        """, (username,))
        row = cur.fetchone()

        if row is None:
            print("User atau PIN belum diset.")
            return False

        user_id = row["user_id"]

        # Jika PIN sudah dikunci
        if row["is_locked"]:
            print("PIN user ini sudah terkunci. Hubungi admin.")
            # Log event
            cur.execute("""
                INSERT INTO trans_login_lock (user_id, event_time, event_type, credential_type, reason)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, datetime.now(), "PIN_DENIED_LOCKED", "PIN_LOCK", "PIN sudah locked, user mencoba lagi"))
            conn.commit()
            return False

        # Verifikasi PIN
        ok = verify_pin(pin, row["pin_salt"], row["pin_hash"])

        if ok:
            # Reset gagal
            cur.execute("""
                UPDATE user_lock
                   SET failed_attempt = 0,
                       lockout_until = NULL
                 WHERE user_id = ?
            """, (user_id,))
            # Log sukses
            cur.execute("""
                INSERT INTO trans_login_lock (user_id, event_time, event_type, credential_type, reason)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, datetime.now(), "PIN_SUCCESS", "PIN_LOCK", "PIN benar"))
            conn.commit()
            print("PIN benar.")
            return True
        else:
            failed = row["failed_attempt"] + 1
            is_locked = 1 if failed >= row["max_attempt"] else 0

            cur.execute("""
                UPDATE user_lock
                   SET failed_attempt = ?, is_locked = ?
                 WHERE user_id = ?
            """, (failed, is_locked, user_id))

            # Log gagal
            reason = f"PIN salah ke-{failed}"
            event_type = "PIN_FAIL_LOCKED" if is_locked else "PIN_FAIL"

            cur.execute("""
                INSERT INTO trans_login_lock (user_id, event_time, event_type, credential_type, reason)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, datetime.now(), event_type, "PIN_LOCK", reason))

            conn.commit()

            print(f"PIN salah. Percobaan ke {failed}.")
            if is_locked:
                print("PIN telah dikunci karena melebihi batas percobaan.")
            return False

    finally:
        conn.close()

# Fungsi: verifikasi login (username + password)
def login_user(username: str, password: str) -> bool:
    conn = get_connection()
    try:
        cur = conn.cursor()

        cur.execute("""
            SELECT user_id,
                   username,
                   password_hash,
                   password_salt,
                   is_active,
                   is_locked,
                   failed_attempt
              FROM user_login
             WHERE username = ?
        """, (username,))
        row = cur.fetchone()

        if row is None:
            print("User tidak ditemukan.")
            return False

        user_id = row["user_id"]

        if not row["is_active"]:
            print("Akun tidak aktif.")
            # Log
            cur.execute("""
                INSERT INTO trans_login_lock (user_id, event_time, event_type, credential_type, reason)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, datetime.now(), "LOGIN_DENIED_INACTIVE", "LOGIN", "Akun tidak aktif"))
            conn.commit()
            return False

        if row["is_locked"]:
            print("Akun login dikunci. Hubungi admin.")
            # Log
            cur.execute("""
                INSERT INTO trans_login_lock (user_id, event_time, event_type, credential_type, reason)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, datetime.now(), "LOGIN_DENIED_LOCKED", "LOGIN", "Akun login terkunci"))
            conn.commit()
            return False

        ok = verify_password(password, row["password_salt"], row["password_hash"])

        if ok:
            # Reset gagal, set last_login_at
            cur.execute("""
                UPDATE user_login
                   SET failed_attempt = 0,
                       last_login_at = ?
                 WHERE user_id = ?
            """, (datetime.now(), user_id))

            # Log sukses
            cur.execute("""
                INSERT INTO trans_login_lock (user_id, event_time, event_type, credential_type, reason)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, datetime.now(), "LOGIN_SUCCESS", "LOGIN", "Login berhasil"))

            conn.commit()
            print("Login berhasil.")
            return True
        else:
            failed = row["failed_attempt"] + 1
            # Contoh policy: lock akun login jika salah 5x
            is_locked = 1 if failed >= 5 else 0

            cur.execute("""
                UPDATE user_login
                   SET failed_attempt = ?, is_locked = ?, last_failed_at = ?
                 WHERE user_id = ?
            """, (failed, is_locked, datetime.now(), user_id))

            reason = f"Password salah ke-{failed}"
            event_type = "LOGIN_FAIL_LOCKED" if is_locked else "LOGIN_FAIL"

            cur.execute("""
                INSERT INTO trans_login_lock (user_id, event_time, event_type, credential_type, reason)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, datetime.now(), event_type, "LOGIN", reason))

            conn.commit()

            print(f"Password salah. Kesalahan ke {failed}.")
            if is_locked:
                print("Akun login telah dikunci karena terlalu banyak percobaan.")
            return False

    finally:
        conn.close()
