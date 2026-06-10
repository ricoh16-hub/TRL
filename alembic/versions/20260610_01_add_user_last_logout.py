"""Add last logout timestamp to users.

Revision ID: 20260610_01
Revises: 20260527_03
Create Date: 2026-06-10
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260610_01"
down_revision = "20260527_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("users")}

    if "last_logout" not in columns:
        op.add_column("users", sa.Column("last_logout", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("users")}

    if "last_logout" in columns:
        op.drop_column("users", "last_logout")
