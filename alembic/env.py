# pyright: reportMissingImports=false, reportMissingModuleSource=false, reportUnknownVariableType=false

from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import URL
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

load_dotenv(PROJECT_ROOT / ".env")

from src.database.models import Base  # noqa: E402

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


target_metadata = Base.metadata


def resolve_migration_url() -> str:
    explicit_url = os.getenv("DB_MIGRATION_URL", "").strip()
    if explicit_url:
        return explicit_url

    database_url = os.getenv("DATABASE_URL", "").strip()
    if database_url:
        return database_url

    db_host = os.getenv("DB_HOST", "localhost").strip() or "localhost"
    db_port = int(os.getenv("DB_PORT", "5432").strip() or "5432")
    db_name = os.getenv("DB_NAME", "GBR").strip() or "GBR"

    admin_user = os.getenv("DB_ADMIN_USER", "").strip()
    admin_password = os.getenv("DB_ADMIN_PASSWORD", "")
    if admin_user and admin_password:
        return URL.create(
            "postgresql+psycopg2",
            username=admin_user,
            password=admin_password,
            host=db_host,
            port=db_port,
            database=db_name,
        ).render_as_string(hide_password=False)

    app_user = os.getenv("DB_USER", "").strip()
    app_password = os.getenv("DB_PASSWORD", "")
    if app_user and app_password:
        return URL.create(
            "postgresql+psycopg2",
            username=app_user,
            password=app_password,
            host=db_host,
            port=db_port,
            database=db_name,
        ).render_as_string(hide_password=False)

    raise RuntimeError("Konfigurasi URL migrasi belum lengkap. Set DB_MIGRATION_URL atau DB_ADMIN_USER/DB_ADMIN_PASSWORD.")


def run_migrations_offline() -> None:
    url = resolve_migration_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = resolve_migration_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        future=True,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
