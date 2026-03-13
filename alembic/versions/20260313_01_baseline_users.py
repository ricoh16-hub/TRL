"""baseline users schema

Revision ID: 20260313_01
Revises: 
Create Date: 2026-03-13 10:45:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

from src.auth.passwords import create_password_hash


revision = "20260313_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    table_names = inspector.get_table_names()

    if "users" not in table_names:
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("username", sa.String(), nullable=False),
            sa.Column("password", sa.String(), nullable=True),
            sa.Column("password_hash", sa.String(), nullable=True),
            sa.Column("password_salt", sa.String(), nullable=True),
            sa.Column("role", sa.String(), nullable=True),
            sa.UniqueConstraint("username", name="uq_users_username"),
        )
        return

    existing_columns = {column["name"] for column in inspector.get_columns("users")}

    if "password_hash" not in existing_columns:
        op.add_column("users", sa.Column("password_hash", sa.String(), nullable=True))
    if "password_salt" not in existing_columns:
        op.add_column("users", sa.Column("password_salt", sa.String(), nullable=True))
    if "password" in existing_columns:
        op.alter_column("users", "password", existing_type=sa.String(), nullable=True)

    rows = bind.execute(
        sa.text(
            "SELECT id, password FROM users "
            "WHERE password IS NOT NULL AND (password_hash IS NULL OR password_salt IS NULL)"
        )
    ).mappings().all()

    for row in rows:
        password = row["password"]
        if not password:
            continue

        salt, password_hash = create_password_hash(str(password))
        bind.execute(
            sa.text(
                "UPDATE users "
                "SET password_hash = :password_hash, password_salt = :password_salt, password = NULL "
                "WHERE id = :user_id"
            ),
            {
                "password_hash": password_hash,
                "password_salt": salt,
                "user_id": row["id"],
            },
        )

    unique_constraints = {constraint["name"] for constraint in inspector.get_unique_constraints("users") if constraint.get("name")}
    if "uq_users_username" not in unique_constraints:
        op.create_unique_constraint("uq_users_username", "users", ["username"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "users" in inspector.get_table_names():
        op.drop_table("users")
