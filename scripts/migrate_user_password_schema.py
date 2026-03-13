# pyright: reportMissingImports=false, reportMissingModuleSource=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportCallIssue=false

from __future__ import annotations

import os
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import psycopg2
from dotenv import dotenv_values

from src.auth.passwords import create_password_hash
ENV_PATH = PROJECT_ROOT / ".env"


def load_config() -> dict[str, str]:
    raw_env = dotenv_values(ENV_PATH)
    env = {str(key): str(value) for key, value in raw_env.items() if value is not None}

    config = {
        "host": os.getenv("DB_HOST") or env.get("DB_HOST", "localhost"),
        "port": os.getenv("DB_PORT") or env.get("DB_PORT", "5432"),
        "dbname": os.getenv("DB_NAME") or env.get("DB_NAME", "app_db"),
        "user": os.getenv("DB_ADMIN_USER") or env.get("DB_ADMIN_USER", "postgres"),
        "password": os.getenv("DB_ADMIN_PASSWORD") or env.get("DB_ADMIN_PASSWORD", ""),
    }

    if not config["password"]:
        raise RuntimeError("DB_ADMIN_PASSWORD belum diset di environment/.env untuk migrasi schema.")

    return config


def main() -> None:
    config = load_config()
    conn = psycopg2.connect(
        host=config["host"],
        port=int(config["port"]),
        dbname=config["dbname"],
        user=config["user"],
        password=config["password"],
    )
    conn.autocommit = True

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS password_hash VARCHAR,
                ADD COLUMN IF NOT EXISTS password_salt VARCHAR
                """
            )
            cur.execute("ALTER TABLE users ALTER COLUMN password DROP NOT NULL")
            cur.execute(
                """
                SELECT id, password
                FROM users
                WHERE password IS NOT NULL
                  AND (password_hash IS NULL OR password_salt IS NULL)
                """
            )
            rows = cur.fetchall()

            for user_id, password in rows:
                salt, password_hash = create_password_hash(str(password))
                cur.execute(
                    """
                    UPDATE users
                    SET password_hash = %s,
                        password_salt = %s,
                        password = NULL
                    WHERE id = %s
                    """,
                    (password_hash, salt, user_id),
                )
    finally:
        conn.close()

    print("USER_PASSWORD_SCHEMA_MIGRATED")


if __name__ == "__main__":
    main()
