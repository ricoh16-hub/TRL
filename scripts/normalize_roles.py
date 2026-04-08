#!/usr/bin/env python
"""Normalize legacy roles to the canonical 4-role model.

Mapping:
- Super Admin / SUPERADMIN -> Superior
- Admin / Manager / Staff -> Administrator
- Viewer -> Auditor
- Unknown roles -> Operator
"""

from __future__ import annotations

import os
import sys
from collections.abc import Iterable

from sqlalchemy import inspect, text

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.crud import CANONICAL_ROLES, normalize_role_name
from src.database.models import Role, Session as SessionMaker, UserRole


LEGACY_SQL_MAP = {
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


def _iter_legacy_roles(role_rows: Iterable[Role]) -> list[str]:
    legacy_names: list[str] = []
    for role in role_rows:
        role_name = str(getattr(role, "role_name", "") or "").strip()
        if role_name and role_name not in CANONICAL_ROLES:
            legacy_names.append(role_name)
    return legacy_names


def normalize_roles() -> None:
    session = SessionMaker()
    try:
        # Ensure canonical role rows exist.
        canonical_roles: dict[str, Role] = {}
        for role_name in CANONICAL_ROLES:
            role = session.query(Role).filter_by(role_name=role_name).first()
            if role is None:
                role = Role(role_name=role_name)
                session.add(role)
                session.flush()
            canonical_roles[role_name] = role

        # Normalize user_roles links to canonical role IDs.
        updated_links = 0
        deleted_duplicate_links = 0
        for link in session.query(UserRole).all():
            role = getattr(link, "role", None)
            role_name = str(getattr(role, "role_name", "") or "").strip()
            if not role_name:
                continue

            try:
                normalized = normalize_role_name(role_name)
            except ValueError:
                normalized = "Operator"

            target_role = canonical_roles[normalized]
            if link.role_id == target_role.id:  # type: ignore[comparison-overlap]
                continue

            existing = (
                session.query(UserRole)
                .filter(UserRole.user_id == link.user_id, UserRole.role_id == target_role.id)
                .first()
            )
            if existing is not None:
                session.delete(link)
                deleted_duplicate_links += 1
                continue

            link.role_id = target_role.id
            updated_links += 1

        session.flush()

        # Normalize legacy users.role text column if present.
        inspector = inspect(session.bind)
        if inspector is not None:
            user_columns = {column["name"] for column in inspector.get_columns("users")}
            if "role" in user_columns:
                sql_case_lines = "\n".join(
                    [f"WHEN lower(trim(role)) = '{old}' THEN '{new}'" for old, new in LEGACY_SQL_MAP.items()]
                )
                session.execute(
                    text(
                        f"""
                        UPDATE users
                        SET role = CASE
                            {sql_case_lines}
                            ELSE 'Operator'
                        END
                        WHERE role IS NOT NULL AND trim(role) <> ''
                        """
                    )
                )
        # Delete legacy role rows after remapping links.
        all_roles = session.query(Role).all()
        legacy_roles = _iter_legacy_roles(all_roles)
        removed_legacy_roles = 0
        for role_name in legacy_roles:
            role_obj = session.query(Role).filter_by(role_name=role_name).first()
            if role_obj is None:
                continue
            session.delete(role_obj)
            removed_legacy_roles += 1

        session.commit()
        print("Role normalization completed.")
        print(f"Canonical roles: {', '.join(CANONICAL_ROLES)}")
        print(f"Updated user_roles links: {updated_links}")
        print(f"Deleted duplicate user_roles links: {deleted_duplicate_links}")
        print(f"Removed legacy role rows: {removed_legacy_roles}")
    except Exception as error:
        session.rollback()
        raise RuntimeError(f"Failed to normalize roles: {error}") from error
    finally:
        session.close()


if __name__ == "__main__":
    normalize_roles()
