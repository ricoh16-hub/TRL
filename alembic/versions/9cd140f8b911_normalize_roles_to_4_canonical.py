"""normalize_roles_to_4_canonical

Revision ID: 9cd140f8b911
Revises: 20260408_06
Create Date: 2026-04-08 16:43:15.363017

Normalize legacy 5-role model (Super Admin, Admin, Manager, Staff, Viewer)
to canonical 4-role model (Superior, Administrator, Operator, Auditor).

Mapping:
- Super Admin / SUPERADMIN -> Superior
- Admin / Manager / Staff -> Administrator
- Viewer -> Auditor
- Unknown -> Operator
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9cd140f8b911'
down_revision = '20260408_06'
branch_labels = None
depends_on = None


ROLE_MAPPING = {
    "super admin": "Superior",
    "superadmin": "Superior",
    "admin": "Administrator",
    "administrator": "Administrator",
    "manager": "Administrator",
    "staff": "Administrator",
    "operator": "Operator",
    "viewer": "Auditor",
    "auditor": "Auditor",
}

LEGACY_ROLES = ["Super Admin", "SUPERADMIN", "Admin", "Manager", "Staff", "Viewer"]
CANONICAL_ROLES = ["Superior", "Administrator", "Operator", "Auditor"]
REVERSE_MAP = {
    "Superior": "Super Admin",
    "Administrator": "Admin",
    "Operator": "Operator",
    "Auditor": "Viewer",
}


def upgrade() -> None:
    # Create canonical roles if not exist.
    for role_name in CANONICAL_ROLES:
        op.execute(
            f"INSERT INTO roles (role_name) VALUES ('{role_name}') ON CONFLICT (role_name) DO NOTHING"
        )

    # Remap user_roles to canonical role IDs.
    sql_case_lines = "\n            ".join(
        [f"WHEN r.role_name = '{old}' THEN '{new}'" for old, new in ROLE_MAPPING.items()]
    )

    op.execute(
        f"""
        UPDATE user_roles ur
        SET role_id = (
            SELECT id FROM roles
            WHERE role_name = CASE
                {sql_case_lines}
                ELSE 'Operator'
            END
        )
        FROM roles r
        WHERE ur.role_id = r.id
        AND r.role_name NOT IN ({', '.join([f"'{r}'" for r in CANONICAL_ROLES])})
        """
    )

    # Delete legacy role rows.
    op.execute(
        f"""
        DELETE FROM roles
        WHERE role_name NOT IN ({', '.join([f"'{r}'" for r in CANONICAL_ROLES])})
        """
    )


def downgrade() -> None:
    # Recreate legacy roles.
    legacy_roles_to_add = [
        ("Super Admin", "Akses penuh sistem"),
        ("Admin", "Kelola user & data"),
        ("Manager", "Monitoring & laporan"),
        ("Staff", "Input data"),
        ("Viewer", "Hanya melihat"),
    ]
    for role_name, description in legacy_roles_to_add:
        op.execute(
            f"INSERT INTO roles (role_name, description) VALUES ('{role_name}', '{description}') ON CONFLICT (role_name) DO NOTHING"
        )

    # Remap user_roles back to legacy role IDs.
    reverse_sql_case = "\n            ".join(
        [f"WHEN r.role_name = '{canon}' THEN '{legacy}'" for canon, legacy in REVERSE_MAP.items()]
    )

    op.execute(
        f"""
        UPDATE user_roles ur
        SET role_id = (
            SELECT id FROM roles
            WHERE role_name = CASE
                {reverse_sql_case}
                ELSE 'Operator'
            END
        )
        FROM roles r
        WHERE ur.role_id = r.id
        AND r.role_name IN ({', '.join([f"'{r}'" for r in CANONICAL_ROLES])})
        """
    )
