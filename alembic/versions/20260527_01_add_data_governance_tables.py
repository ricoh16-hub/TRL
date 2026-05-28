"""add data governance tables

Revision ID: 20260527_01
Revises: 20260526_01
Create Date: 2026-05-27 00:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260527_01"
down_revision = "20260526_01"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    bind = op.get_bind()
    return sa.inspect(bind).has_table(table_name)


def upgrade() -> None:
    if not _has_table("import_batches"):
        op.create_table(
            "import_batches",
            sa.Column("import_batch_id", sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column("source_period", sa.String(length=32), nullable=False),
            sa.Column("source_files", sa.JSON(), nullable=False, server_default=sa.text("'[]'::jsonb")),
            sa.Column("files_checksum", sa.String(length=128), nullable=False),
            sa.Column("source_rows", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("unique_rows", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("imported_rows", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("date_reviews", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("status", sa.String(length=24), nullable=False, server_default="SUCCESS"),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.PrimaryKeyConstraint("import_batch_id"),
        )
    if not _has_table("data_quality_issues"):
        op.create_table(
            "data_quality_issues",
            sa.Column("issue_id", sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column("issue_key", sa.String(length=180), nullable=False),
            sa.Column("issue_code", sa.String(length=64), nullable=False),
            sa.Column("severity", sa.String(length=16), nullable=False),
            sa.Column("status", sa.String(length=16), nullable=False, server_default="OPEN"),
            sa.Column("employee_id", sa.BigInteger(), nullable=True),
            sa.Column("source_period", sa.String(length=32), nullable=False),
            sa.Column("source_reference", sa.String(length=255), nullable=True),
            sa.Column("observed_value", sa.Text(), nullable=True),
            sa.Column("recommendation", sa.Text(), nullable=True),
            sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.CheckConstraint("severity IN ('BLOCKING', 'REVIEW', 'INFO')", name="ck_data_quality_issues_severity"),
            sa.CheckConstraint("status IN ('OPEN', 'VERIFIED', 'FIXED', 'IGNORED')", name="ck_data_quality_issues_status"),
            sa.ForeignKeyConstraint(["employee_id"], ["employees.employee_id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("issue_id"),
            sa.UniqueConstraint("issue_key"),
        )

    op.execute("CREATE INDEX IF NOT EXISTS ix_import_batches_source_period ON import_batches(source_period)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_import_batches_started_at ON import_batches(started_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_data_quality_issues_status ON data_quality_issues(status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_data_quality_issues_severity ON data_quality_issues(severity)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_data_quality_issues_employee_id ON data_quality_issues(employee_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_data_quality_issues_source_period ON data_quality_issues(source_period)")
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_employee_assignments_one_current "
        "ON employee_assignments(employee_id) WHERE is_current = true"
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_employee_contracts_one_open "
        "ON employee_contracts(employee_id) WHERE end_date IS NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_employee_contracts_one_open")
    op.execute("DROP INDEX IF EXISTS uq_employee_assignments_one_current")
    op.drop_table("data_quality_issues")
    op.drop_table("import_batches")
