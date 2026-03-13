"""contoh pola migration aman

File ini hanya contoh. Jangan taruh di alembic/versions kecuali memang ingin dijalankan.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "example_safe_revision"
down_revision = "20260313_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # EXPAND: tambah kolom nullable lebih dulu
    op.add_column("users", sa.Column("display_name", sa.String(), nullable=True))

    # MIGRATE DATA: isi nilai dari username
    op.execute(sa.text("UPDATE users SET display_name = username WHERE display_name IS NULL"))

    # CONTRACT: ketatkan constraint setelah data aman
    op.alter_column("users", "display_name", existing_type=sa.String(), nullable=False)


def downgrade() -> None:
    # Rollback sederhana karena kolom ini masih bisa dibuang tanpa kehilangan sistem inti
    op.drop_column("users", "display_name")
