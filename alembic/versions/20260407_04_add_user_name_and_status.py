"""add user nama and status

Revision ID: 20260407_04
Revises: 20260407_03
Create Date: 2026-04-07 00:00:01
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260407_04"
down_revision = "20260407_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "users" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("users")}

    if "nama" not in existing_columns:
        op.add_column("users", sa.Column("nama", sa.String(), nullable=True))

    if "status" not in existing_columns:
        op.add_column("users", sa.Column("status", sa.String(), nullable=True, server_default="aktif"))

    op.execute("UPDATE users SET status = 'aktif' WHERE status IS NULL OR status = ''")
    op.alter_column("users", "status", existing_type=sa.String(), nullable=False, server_default="aktif")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "users" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("users")}

    if "status" in existing_columns:
        op.drop_column("users", "status")

    if "nama" in existing_columns:
        op.drop_column("users", "nama")
