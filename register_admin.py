from datetime import datetime

from db import get_connection
from security import create_password_hash, create_pin_hash

def register_admin():
    print("=== Registrasi User Pertama (ADMIN) ===")

    username = input("Username admin          : ").strip()
    password = input("Password login admin    : ").strip()
    full_name = input("Nama lengkap admin      : ").strip()
    email = input("Email admin             : ").strip()
    pin = input("PIN lock (6 digit angka): ").strip()

    # Validasi sederhana PIN
    if not (len(pin) == 6 and pin.isdigit()):
        print("PIN harus 6 digit angka. Registrasi dibatalkan.")
        return

    # Buat hash password & PIN
    pwd_salt, pwd_hash = create_password_hash(password)
    pin_salt, pin_hash = create_pin_hash(pin)

    conn = get_connection()
    try:
        cur = conn.cursor()

        # Cek apakah sudah ada user admin sebelumnya
        cur.execute("SELECT COUNT(*) AS cnt FROM user_login")
        row = cur.fetchone()
        if row["cnt"] > 0:
            print("Sudah ada user di tabel user_login.")
            print("Script ini sebaiknya hanya digunakan untuk user pertama.")
            return

        # Insert ke user_login
        cur.execute("""
            INSERT INTO user_login
                (username, password_hash, password_salt,
                 full_name, email, role, is_active, is_locked,
                 failed_attempt, created_at, created_by)
            VALUES
                (?, ?, ?, ?, ?, ?, 1, 0, 0, ?, ?)
        """, (
            username,
            pwd_hash,
            pwd_salt,
            full_name,
            email,
            "admin",  # role admin
            datetime.now(),
            "SYSTEM"
        ))

        user_id = cur.lastrowid  # ambil user_id yang baru dibuat

        # Insert ke user_lock
        cur.execute("""
            INSERT INTO user_lock
                (user_id, pin_hash, pin_salt,
                 is_locked, failed_attempt, max_attempt,
                 updated_at, updated_by)
            VALUES
                (?, ?, ?, 0, 0, 10, ?, ?)
        """, (
            user_id,
            pin_hash,
            pin_salt,
            datetime.now(),
            user_id
        ))

        conn.commit()
        print("\n=== BERHASIL ===")
        print(f"User admin '{username}' berhasil dibuat dengan user_id = {user_id}.")
        print("Password login dan PIN 6 digit sudah disimpan (dalam bentuk hash).")

    finally:
        conn.close()

if __name__ == "__main__":
    register_admin()
