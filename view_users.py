from db import get_connection

conn = get_connection()
cur = conn.cursor()

cur.execute("SELECT user_id, username, full_name, role, is_active, is_locked FROM user_login")
rows = cur.fetchall()

print("=== DATA USER DALAM user_login ===")
if not rows:
    print("(Belum ada user)")
else:
    for r in rows:
        print(dict(r))

conn.close()
