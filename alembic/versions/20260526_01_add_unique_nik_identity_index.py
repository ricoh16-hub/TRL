"""add unique nik identity index

Revision ID: 20260526_01
Revises: c1f9c61c5a2f
Create Date: 2026-05-26 00:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260526_01"
down_revision = "c1f9c61c5a2f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "uq_employee_identities_nik_number",
        "employee_identities",
        ["identity_number"],
        unique=True,
        postgresql_where=sa.text("upper(identity_type) IN ('NIK', 'KTP')"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_employee_identities_nik_number",
        table_name="employee_identities",
        postgresql_where=sa.text("upper(identity_type) IN ('NIK', 'KTP')"),
    )
