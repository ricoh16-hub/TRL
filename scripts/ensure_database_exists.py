from __future__ import annotations

import os
from pathlib import Path

import psycopg2
from dotenv import dotenv_values


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = PROJECT_ROOT / ".env"


def _env_value(env: dict[str, str], key: str, default: str = "") -> str:
    value = os.getenv(key)
    if value is not None and value.strip() != "":
        return value.strip()
    return env.get(key, default).strip()


def load_config() -> dict[str, str]:
    raw_env = dotenv_values(ENV_PATH)
    env = {str(key): str(value) for key, value in raw_env.items() if value is not None}

    host = _env_value(env, "DB_HOST", "localhost")
    port = _env_value(env, "DB_PORT", "5432")
    target_db = _env_value(env, "DB_NAME", "GBR")

    admin_user = _env_value(env, "DB_ADMIN_USER")
    admin_password = _env_value(env, "DB_ADMIN_PASSWORD")

    user = admin_user or _env_value(env, "DB_USER")
    password = admin_password or _env_value(env, "DB_PASSWORD")

    if not user or not password:
        raise RuntimeError("Kredensial database tidak lengkap. Set DB_ADMIN_* atau DB_USER/DB_PASSWORD.")

    return {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "target_db": target_db,
    }


def main() -> None:
    config = load_config()

    conn = psycopg2.connect(
        host=config["host"],
        port=int(config["port"]),
        dbname="postgres",
        user=config["user"],
        password=config["password"],
    )
    conn.autocommit = True

    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (config["target_db"],))
            exists = cursor.fetchone() is not None

            if exists:
                print(f"DATABASE_EXISTS={config['target_db']}")
                return

            cursor.execute(f'CREATE DATABASE "{config["target_db"]}"')
            print(f"DATABASE_CREATED={config['target_db']}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
