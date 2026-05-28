"""add native attendance and work output tables

Revision ID: 20260527_03
Revises: 20260527_02
Create Date: 2026-05-27 00:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260527_03"
down_revision = "20260527_02"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table_name)


def upgrade() -> None:
    if not _has_table("employee_attendance_daily"):
        op.create_table(
            "employee_attendance_daily",
            sa.Column("attendance_id", sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column("employee_id", sa.BigInteger(), nullable=False),
            sa.Column("attendance_code_id", sa.BigInteger(), nullable=False),
            sa.Column("attendance_date", sa.Date(), nullable=False),
            sa.Column("work_hours", sa.Numeric(5, 2), nullable=False, server_default="0"),
            sa.Column("overtime_hours", sa.Numeric(5, 2), nullable=False, server_default="0"),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["attendance_code_id"], ["attendance_codes.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["employee_id"], ["employees.employee_id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("attendance_id"),
            sa.UniqueConstraint("employee_id", "attendance_date", name="uq_employee_attendance_employee_date"),
        )
    if not _has_table("employee_work_outputs"):
        op.create_table(
            "employee_work_outputs",
            sa.Column("work_output_id", sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column("employee_id", sa.BigInteger(), nullable=False),
            sa.Column("job_family_id", sa.BigInteger(), nullable=True),
            sa.Column("work_date", sa.Date(), nullable=False),
            sa.Column("work_group_code", sa.String(length=80), nullable=True),
            sa.Column("activity_name", sa.String(length=160), nullable=False),
            sa.Column("quantity", sa.Numeric(14, 2), nullable=False, server_default="0"),
            sa.Column("unit_name", sa.String(length=40), nullable=False),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["employee_id"], ["employees.employee_id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["job_family_id"], ["job_families.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("work_output_id"),
        )

    op.execute("CREATE INDEX IF NOT EXISTS ix_employee_attendance_date ON employee_attendance_daily(attendance_date)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_employee_attendance_employee_id ON employee_attendance_daily(employee_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_employee_work_outputs_work_date ON employee_work_outputs(work_date)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_employee_work_outputs_employee_id ON employee_work_outputs(employee_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_employee_work_outputs_job_family_id ON employee_work_outputs(job_family_id)")


def downgrade() -> None:
    op.drop_table("employee_work_outputs")
    op.drop_table("employee_attendance_daily")
