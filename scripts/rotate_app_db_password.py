# pyright: reportMissingImports=false, reportMissingModuleSource=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportCallIssue=false

from __future__ import annotations

import secrets
from pathlib import Path

import psycopg2
from psycopg2 import sql
from dotenv import dotenv_values

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = PROJECT_ROOT / ".env"


def load_current_env() -> dict[str, str]:
    raw_env = dotenv_values(ENV_PATH)
    env = {str(key): str(value) for key, value in raw_env.items() if value is not None}
    required = ["DB_USER", "DB_PASSWORD", "DB_HOST", "DB_PORT", "DB_NAME"]
    missing = [key for key in required if not env.get(key)]
    if missing:
        raise RuntimeError(f"Konfigurasi .env belum lengkap: {', '.join(missing)}")
    return {key: env[key] for key in required}


def write_env(current: dict[str, str], new_password: str) -> None:
    lines = [
        f"DB_USER={current['DB_USER']}",
        f'DB_PASSWORD="{new_password}"',
        f"DB_HOST={current['DB_HOST']}",
        f"DB_PORT={current['DB_PORT']}",
        f"DB_NAME={current['DB_NAME']}",
        "DB_CONNECT_TIMEOUT=10",
        "DB_APP_NAME=python-apps-12R",
        "# DB_SSLMODE=prefer",
    ]
    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="ascii")


def main() -> None:
    current = load_current_env()
    new_password = secrets.token_urlsafe(24)

    conn = psycopg2.connect(
        host=current["DB_HOST"],
        port=int(current["DB_PORT"]),
        dbname=current["DB_NAME"],
        user=current["DB_USER"],
        password=current["DB_PASSWORD"],
    )
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute(
                sql.SQL("ALTER ROLE {} WITH PASSWORD %s").format(sql.Identifier(current["DB_USER"])),
                (new_password,),
            )
    finally:
        conn.close()

    write_env(current, new_password)
    print("APP_DB_PASSWORD_ROTATED")
    print(f"ENV_UPDATED={ENV_PATH}")


if __name__ == "__main__":
    main()
