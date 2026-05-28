"""drop plaintext credential columns

Revision ID: 20260527_02
Revises: 20260527_01
Create Date: 2026-05-27 00:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260527_02"
down_revision = "20260527_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS password_plaintext")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS pin_plaintext")


def downgrade() -> None:
    op.add_column("users", sa.Column("password_plaintext", sa.String(), nullable=True))
    op.add_column("users", sa.Column("pin_plaintext", sa.String(), nullable=True))
