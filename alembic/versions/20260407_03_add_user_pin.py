"""add user pin hash and salt

Revision ID: 20260407_03
Revises: 20260313_02
Create Date: 2026-04-07 00:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260407_03"
down_revision = "20260313_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "users" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("users")}

    if "pin_hash" not in existing_columns:
        op.add_column(
            "users",
            sa.Column("pin_hash", sa.String(), nullable=True),
        )

    if "pin_salt" not in existing_columns:
        op.add_column(
            "users",
            sa.Column("pin_salt", sa.String(), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "users" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("users")}

    if "pin_salt" in existing_columns:
        op.drop_column("users", "pin_salt")

    if "pin_hash" in existing_columns:
        op.drop_column("users", "pin_hash")
