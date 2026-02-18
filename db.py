from pathlib import Path
import sqlite3

DB_PATH = Path("security.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row   # supaya bisa akses row["username"]
    return conn
