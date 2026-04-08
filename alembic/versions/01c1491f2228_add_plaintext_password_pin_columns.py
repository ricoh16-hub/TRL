"""add_plaintext_password_pin_columns

Revision ID: 01c1491f2228
Revises: 9cd140f8b911
Create Date: 2026-04-08 17:13:36.160626
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '01c1491f2228'
down_revision = '9cd140f8b911'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('password_plaintext', sa.String(), nullable=True))
    op.add_column('users', sa.Column('pin_plaintext', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'pin_plaintext')
    op.drop_column('users', 'password_plaintext')
