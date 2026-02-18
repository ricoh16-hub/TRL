from db import get_connection

username = input("Username yang mau dihapus: ").strip()

conn = get_connection()
cur = conn.cursor()

cur.execute("DELETE FROM user_login WHERE username = ?", (username,))
conn.commit()

print(f"User '{username}' dihapus jika memang ada di database.")
conn.close()
