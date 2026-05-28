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
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")

from app.core.config import get_settings  # noqa: E402
from app.database.connection import Base  # noqa: E402

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


target_metadata = Base.metadata


def get_database_url() -> str:
    settings = get_settings()
    admin_user = os.getenv("DB_ADMIN_USER", "").strip()
    admin_password = os.getenv("DB_ADMIN_PASSWORD", "").strip()
    if admin_user and admin_password and settings.db_name:
        return URL.create(
            drivername="postgresql+psycopg2",
            username=admin_user,
            password=admin_password,
            host=settings.db_host,
            port=settings.db_port,
            database=settings.db_name,
        ).render_as_string(hide_password=False)

    database_url = os.getenv("DATABASE_URL", "").strip()
    if database_url:
        return database_url

    return settings.sqlalchemy_database_url


def run_migrations_offline() -> None:
    url = get_database_url()
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
    configuration["sqlalchemy.url"] = get_database_url()

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
