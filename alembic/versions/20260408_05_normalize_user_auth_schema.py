"""normalize user auth schema

Revision ID: 20260408_05
Revises: 20260407_04
Create Date: 2026-04-08 10:30:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from typing import Any


revision = "20260408_05"
down_revision = "20260407_04"
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

    user_columns = _column_names(inspector, "users")

    if "full_name" not in user_columns:
        op.add_column("users", sa.Column("full_name", sa.String(), nullable=True))
    if "email" not in user_columns:
        op.add_column("users", sa.Column("email", sa.String(), nullable=True))
    if "phone" not in user_columns:
        op.add_column("users", sa.Column("phone", sa.String(), nullable=True))
    if "deleted_at" not in user_columns:
        op.add_column("users", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))

    unique_constraints = {
        constraint["name"]
        for constraint in inspector.get_unique_constraints("users")
        if constraint.get("name")
    }
    if "uq_users_email" not in unique_constraints:
        op.create_unique_constraint("uq_users_email", "users", ["email"])

    if not _table_exists(inspector, "roles"):
        op.create_table(
            "roles",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("role_name", sa.String(), nullable=False),
            sa.Column("description", sa.String(), nullable=True),
            sa.UniqueConstraint("role_name", name="uq_roles_role_name"),
        )

    if not _table_exists(inspector, "permissions"):
        op.create_table(
            "permissions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("permission_name", sa.String(), nullable=False),
            sa.UniqueConstraint("permission_name", name="uq_permissions_permission_name"),
        )

    if not _table_exists(inspector, "user_passwords"):
        op.create_table(
            "user_passwords",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("password_hash", sa.String(), nullable=False),
            sa.Column("password_salt", sa.String(), nullable=False),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.UniqueConstraint("user_id", name="uq_user_passwords_user_id"),
        )

    if not _table_exists(inspector, "user_pins"):
        op.create_table(
            "user_pins",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("pin_hash", sa.String(), nullable=False),
            sa.Column("pin_salt", sa.String(), nullable=False),
            sa.Column("failed_attempts", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.UniqueConstraint("user_id", name="uq_user_pins_user_id"),
        )

    if not _table_exists(inspector, "user_roles"):
        op.create_table(
            "user_roles",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("role_id", sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
            sa.UniqueConstraint("user_id", "role_id", name="uq_user_roles_user_role"),
        )

    if not _table_exists(inspector, "role_permissions"):
        op.create_table(
            "role_permissions",
            sa.Column("role_id", sa.Integer(), nullable=False),
            sa.Column("permission_id", sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["permission_id"], ["permissions.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("role_id", "permission_id", name="pk_role_permissions"),
        )

    if not _table_exists(inspector, "login_attempts"):
        op.create_table(
            "login_attempts",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), nullable=True),
            sa.Column("ip_address", sa.String(), nullable=True),
            sa.Column("success", sa.Boolean(), nullable=False),
            sa.Column(
                "attempt_time",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        )

    if not _table_exists(inspector, "user_sessions"):
        op.create_table(
            "user_sessions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("access_token", sa.String(), nullable=False),
            sa.Column("refresh_token", sa.String(), nullable=True),
            sa.Column("ip_address", sa.String(), nullable=True),
            sa.Column("user_agent", sa.String(), nullable=True),
            sa.Column("expired_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        )

    if not _table_exists(inspector, "audit_logs"):
        op.create_table(
            "audit_logs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), nullable=True),
            sa.Column("action", sa.String(), nullable=False),
            sa.Column("action_type", sa.String(), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("ip_address", sa.String(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        )

    op.execute("UPDATE users SET full_name = nama WHERE full_name IS NULL AND nama IS NOT NULL")

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


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if _table_exists(inspector, "audit_logs"):
        op.drop_table("audit_logs")
    if _table_exists(inspector, "user_sessions"):
        op.drop_table("user_sessions")
    if _table_exists(inspector, "login_attempts"):
        op.drop_table("login_attempts")
    if _table_exists(inspector, "role_permissions"):
        op.drop_table("role_permissions")
    if _table_exists(inspector, "user_roles"):
        op.drop_table("user_roles")
    if _table_exists(inspector, "user_pins"):
        op.drop_table("user_pins")
    if _table_exists(inspector, "user_passwords"):
        op.drop_table("user_passwords")
    if _table_exists(inspector, "permissions"):
        op.drop_table("permissions")
    if _table_exists(inspector, "roles"):
        op.drop_table("roles")

    if _table_exists(inspector, "users"):
        columns = _column_names(inspector, "users")

        unique_constraints = {
            constraint["name"]
            for constraint in inspector.get_unique_constraints("users")
            if constraint.get("name")
        }
        if "uq_users_email" in unique_constraints:
            op.drop_constraint("uq_users_email", "users", type_="unique")

        if "deleted_at" in columns:
            op.drop_column("users", "deleted_at")
        if "phone" in columns:
            op.drop_column("users", "phone")
        if "email" in columns:
            op.drop_column("users", "email")
        if "full_name" in columns:
            op.drop_column("users", "full_name")
