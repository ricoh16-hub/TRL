
import sqlite3
from pathlib import Path

DB_PATH = Path("security.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    try:
        with open("schema.sql", "r", encoding="utf-8") as f:
            schema_sql = f.read()
        conn.executescript(schema_sql)
        conn.commit()
        print("Database dan tabel berhasil dibuat / di-update.")
        print(f"Lokasi file database: {DB_PATH.resolve()}")
    finally:
        conn.close()

if __name__ == "__main__":
    init_db()
