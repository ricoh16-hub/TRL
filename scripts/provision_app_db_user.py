# pyright: reportMissingImports=false, reportMissingModuleSource=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportCallIssue=false

from __future__ import annotations

import secrets
from pathlib import Path

import psycopg2
from psycopg2 import sql
from dotenv import dotenv_values

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = PROJECT_ROOT / ".env"
APP_USER = "app_client"
APP_DB = "app_db"


def load_admin_config() -> dict[str, str]:
    raw_env = dotenv_values(ENV_PATH)
    env = {str(key): str(value) for key, value in raw_env.items() if value is not None}

    admin_user = env.get("DB_ADMIN_USER", "postgres")
    admin_password = env.get("DB_ADMIN_PASSWORD") or env.get("DB_PASSWORD")
    host = env.get("DB_HOST", "localhost")
    port = env.get("DB_PORT", "5432")
    db_name = env.get("DB_NAME", APP_DB)

    if not admin_password:
        raise RuntimeError("DB_ADMIN_PASSWORD belum tersedia di .env")

    return {
        "user": str(admin_user),
        "password": str(admin_password),
        "host": str(host),
        "port": str(port),
        "dbname": str(db_name),
    }


def write_app_env(password: str, cfg: dict[str, str]) -> None:
    lines = [
        f"DB_USER={APP_USER}",
        f'DB_PASSWORD="{password}"',
        f"DB_HOST={cfg['host']}",
        f"DB_PORT={cfg['port']}",
        f"DB_NAME={cfg['dbname']}",
        "DB_CONNECT_TIMEOUT=10",
        "DB_APP_NAME=python-apps-12R",
        "# DB_SSLMODE=prefer",
        "# DB_ADMIN_USER=postgres",
        "# DB_ADMIN_PASSWORD=GANTI_PASSWORD_ADMIN_HANYA_UNTUK_PROVISIONING",
    ]
    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="ascii")


def main() -> None:
    cfg = load_admin_config()
    app_password = secrets.token_urlsafe(24)

    conn = psycopg2.connect(
        host=cfg["host"],
        port=int(cfg["port"]),
        user=cfg["user"],
        password=cfg["password"],
        dbname=cfg["dbname"],
    )
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (APP_USER,))
            exists = cur.fetchone() is not None

            if exists:
                cur.execute(
                    sql.SQL("ALTER ROLE {} LOGIN PASSWORD %s").format(sql.Identifier(APP_USER)),
                    (app_password,),
                )
            else:
                cur.execute(
                    sql.SQL("CREATE ROLE {} LOGIN PASSWORD %s").format(sql.Identifier(APP_USER)),
                    (app_password,),
                )

            cur.execute(sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(sql.Identifier(APP_DB), sql.Identifier(APP_USER)))
            cur.execute(sql.SQL("GRANT USAGE, CREATE ON SCHEMA public TO {}").format(sql.Identifier(APP_USER)))
            cur.execute(sql.SQL("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {}").format(sql.Identifier(APP_USER)))
            cur.execute(sql.SQL("GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO {}").format(sql.Identifier(APP_USER)))
            cur.execute(sql.SQL("ALTER DEFAULT PRIVILEGES FOR USER {} IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {}").format(sql.Identifier(cfg["user"]), sql.Identifier(APP_USER)))
            cur.execute(sql.SQL("ALTER DEFAULT PRIVILEGES FOR USER {} IN SCHEMA public GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO {}").format(sql.Identifier(cfg["user"]), sql.Identifier(APP_USER)))
    finally:
        conn.close()

    write_app_env(app_password, cfg)
    print("APP_DB_USER_READY")
    print(f"ENV_UPDATED={ENV_PATH}")


if __name__ == "__main__":
    main()
