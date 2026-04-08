"""drop legacy user columns

Revision ID: 20260408_06
Revises: 20260408_05
Create Date: 2026-04-08 11:30:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from typing import Any


revision = "20260408_06"
down_revision = "20260408_05"
branch_labels = None
depends_on = None


def _table_exists(inspector: Any, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _column_names(inspector: Any, table_name: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if not _table_exists(inspector, "users"):
        return

    columns = _column_names(inspector, "users")

    if "nama" in columns and "full_name" in columns:
        op.execute("UPDATE users SET full_name = nama WHERE full_name IS NULL AND nama IS NOT NULL")

    if "role" in columns and _table_exists(inspector, "roles") and _table_exists(inspector, "user_roles"):
        op.execute(
            """
            INSERT INTO roles (role_name)
            SELECT DISTINCT role
            FROM users
            WHERE role IS NOT NULL AND role <> ''
            ON CONFLICT (role_name) DO NOTHING
            """
        )
        op.execute(
            """
            INSERT INTO user_roles (user_id, role_id)
            SELECT u.id, r.id
            FROM users u
            JOIN roles r ON r.role_name = u.role
            WHERE u.role IS NOT NULL AND u.role <> ''
            ON CONFLICT (user_id, role_id) DO NOTHING
            """
        )

    if {
        "password_hash",
        "password_salt",
    }.issubset(columns) and _table_exists(inspector, "user_passwords"):
        op.execute(
            """
            INSERT INTO user_passwords (user_id, password_hash, password_salt, updated_at)
            SELECT id, password_hash, password_salt, COALESCE(updated_at, CURRENT_TIMESTAMP)
            FROM users
            WHERE password_hash IS NOT NULL AND password_salt IS NOT NULL
            ON CONFLICT (user_id)
            DO UPDATE SET
                password_hash = EXCLUDED.password_hash,
                password_salt = EXCLUDED.password_salt,
                updated_at = EXCLUDED.updated_at
            """
        )

    if {"pin_hash", "pin_salt"}.issubset(columns) and _table_exists(inspector, "user_pins"):
        op.execute(
            """
            INSERT INTO user_pins (user_id, pin_hash, pin_salt, failed_attempts, locked_until, updated_at)
            SELECT id, pin_hash, pin_salt, 0, NULL, COALESCE(updated_at, CURRENT_TIMESTAMP)
            FROM users
            WHERE pin_hash IS NOT NULL AND pin_salt IS NOT NULL
            ON CONFLICT (user_id)
            DO UPDATE SET
                pin_hash = EXCLUDED.pin_hash,
                pin_salt = EXCLUDED.pin_salt,
                updated_at = EXCLUDED.updated_at
            """
        )

    for column_name in ["password", "password_hash", "password_salt", "pin_hash", "pin_salt", "role", "nama"]:
        if column_name in columns:
            op.drop_column("users", column_name)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if not _table_exists(inspector, "users"):
        return

    columns = _column_names(inspector, "users")

    if "nama" not in columns:
        op.add_column("users", sa.Column("nama", sa.String(), nullable=True))
    if "role" not in columns:
        op.add_column("users", sa.Column("role", sa.String(), nullable=True))
    if "password" not in columns:
        op.add_column("users", sa.Column("password", sa.String(), nullable=True))
    if "password_hash" not in columns:
        op.add_column("users", sa.Column("password_hash", sa.String(), nullable=True))
    if "password_salt" not in columns:
        op.add_column("users", sa.Column("password_salt", sa.String(), nullable=True))
    if "pin_hash" not in columns:
        op.add_column("users", sa.Column("pin_hash", sa.String(), nullable=True))
    if "pin_salt" not in columns:
        op.add_column("users", sa.Column("pin_salt", sa.String(), nullable=True))

    op.execute("UPDATE users SET nama = full_name WHERE nama IS NULL AND full_name IS NOT NULL")

    if _table_exists(inspector, "user_passwords"):
        op.execute(
            """
            UPDATE users u
            SET password_hash = up.password_hash,
                password_salt = up.password_salt
            FROM user_passwords up
            WHERE up.user_id = u.id
            """
        )

    if _table_exists(inspector, "user_pins"):
        op.execute(
            """
            UPDATE users u
            SET pin_hash = up.pin_hash,
                pin_salt = up.pin_salt
            FROM user_pins up
            WHERE up.user_id = u.id
            """
        )

    if _table_exists(inspector, "user_roles") and _table_exists(inspector, "roles"):
        op.execute(
            """
            UPDATE users u
            SET role = r.role_name
            FROM user_roles ur
            JOIN roles r ON r.id = ur.role_id
            WHERE ur.user_id = u.id
            """
        )
