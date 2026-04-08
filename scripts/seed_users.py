#!/usr/bin/env python
"""Seed dataset RBAC/auth sesuai flow aplikasi saat ini.

Catatan penting:
- PIN wajib 6 digit angka, lalu disimpan sebagai hash (bukan plaintext).
- Mapping tabel "user_credentials" di requirement:
  - password_hash -> user_passwords
  - pin_hash + failed_attempts -> user_pins
  - last_login -> diwakili melalui login_attempts/audit_logs/user_sessions
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from sqlalchemy import text

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.auth.passwords import create_password_hash, create_pin_hash
from src.database.models import (
    AuditLog,
    LoginAttempt,
    Permission,
    Role,
    RolePermission,
    Session,
    User,
    UserPassword,
    UserPin,
    UserRole,
    UserSession,
)


ROLES = [
    {"id": 1, "role_name": "Super Admin", "description": "Akses penuh sistem"},
    {"id": 2, "role_name": "Admin", "description": "Kelola user & data"},
    {"id": 3, "role_name": "Manager", "description": "Monitoring & laporan"},
    {"id": 4, "role_name": "Staff", "description": "Input data"},
    {"id": 5, "role_name": "Viewer", "description": "Hanya melihat"},
]

PERMISSIONS = [
    {"id": 1, "permission_name": "create_user"},
    {"id": 2, "permission_name": "edit_user"},
    {"id": 3, "permission_name": "delete_user"},
    {"id": 4, "permission_name": "view_user"},
    {"id": 5, "permission_name": "create_report"},
    {"id": 6, "permission_name": "view_report"},
    {"id": 7, "permission_name": "export_data"},
    {"id": 8, "permission_name": "access_dashboard"},
]

ROLE_PERMISSIONS = [
    (1, 1), (1, 2), (1, 3), (1, 4), (1, 5), (1, 6), (1, 7), (1, 8),
    (2, 1), (2, 2), (2, 4), (2, 6), (2, 8),
    (3, 5), (3, 6), (3, 8),
    (4, 5), (4, 8),
    (5, 6), (5, 8),
]

USERS = [
    {
        "id": 1,
        "full_name": "Riko Sinaga",
        "username": "riko",
        "email": "riko@mail.com",
        "phone": "0811111111",
        "status": "active",
        "role_id": 1,
        "created_at": "2026-01-01T00:00:00",
    },
    {
        "id": 2,
        "full_name": "Andi Saputra",
        "username": "andi",
        "email": "andi@mail.com",
        "phone": "0812222222",
        "status": "active",
        "role_id": 2,
        "created_at": "2026-01-02T00:00:00",
    },
    {
        "id": 3,
        "full_name": "Budi Santoso",
        "username": "budi",
        "email": "budi@mail.com",
        "phone": "0813333333",
        "status": "active",
        "role_id": 3,
        "created_at": "2026-01-03T00:00:00",
    },
    {
        "id": 4,
        "full_name": "Siti Aminah",
        "username": "siti",
        "email": "siti@mail.com",
        "phone": "0814444444",
        "status": "active",
        "role_id": 4,
        "created_at": "2026-01-04T00:00:00",
    },
    {
        "id": 5,
        "full_name": "Joko Prasetyo",
        "username": "joko",
        "email": "joko@mail.com",
        "phone": "0815555555",
        "status": "inactive",
        "role_id": 5,
        "created_at": "2026-01-05T00:00:00",
    },
]

# Tetap 6 digit angka sesuai syarat.
USER_CREDENTIALS = [
    {
        "id": 1,
        "user_id": 1,
        "password_plain": "admin123",
        "pin_plain": "123123",
        "failed_attempts": 0,
    },
    {
        "id": 2,
        "user_id": 2,
        "password_plain": "andi123",
        "pin_plain": "234234",
        "failed_attempts": 1,
    },
    {
        "id": 3,
        "user_id": 3,
        "password_plain": "budi123",
        "pin_plain": "345345",
        "failed_attempts": 0,
    },
    {
        "id": 4,
        "user_id": 4,
        "password_plain": "siti123",
        "pin_plain": "456456",
        "failed_attempts": 2,
    },
    {
        "id": 5,
        "user_id": 5,
        "password_plain": "joko123",
        "pin_plain": "567567",
        "failed_attempts": 5,
    },
]

LOGIN_ATTEMPTS = [
    {"id": 1, "user_id": 1, "ip_address": "192.168.1.1", "success": True, "attempt_time": "2026-04-01T08:00:00"},
    {"id": 2, "user_id": 2, "ip_address": "192.168.1.2", "success": False, "attempt_time": "2026-04-01T08:55:00"},
    {"id": 3, "user_id": 2, "ip_address": "192.168.1.2", "success": True, "attempt_time": "2026-04-01T09:00:00"},
    {"id": 4, "user_id": 5, "ip_address": "192.168.1.5", "success": False, "attempt_time": "2026-03-30T06:50:00"},
    {"id": 5, "user_id": 5, "ip_address": "192.168.1.5", "success": False, "attempt_time": "2026-03-30T06:55:00"},
]

USER_SESSIONS = [
    {"id": 1, "user_id": 1, "access_token": "token123", "ip_address": "192.168.1.1", "user_agent": "Chrome", "expired_at": "2026-04-01T12:00:00"},
    {"id": 2, "user_id": 2, "access_token": "token234", "ip_address": "192.168.1.2", "user_agent": "Firefox", "expired_at": "2026-04-01T13:00:00"},
    {"id": 3, "user_id": 3, "access_token": "token345", "ip_address": "192.168.1.3", "user_agent": "Edge", "expired_at": "2026-04-01T14:00:00"},
]

AUDIT_LOGS = [
    {
        "id": 1,
        "user_id": 1,
        "action": "login",
        "action_type": "auth",
        "description": "Login berhasil",
        "ip_address": "192.168.1.1",
        "created_at": "2026-04-01T08:00:00",
    },
    {
        "id": 2,
        "user_id": 2,
        "action": "login_fail",
        "action_type": "auth",
        "description": "Password salah",
        "ip_address": "192.168.1.2",
        "created_at": "2026-04-01T08:55:00",
    },
    {
        "id": 3,
        "user_id": 2,
        "action": "login",
        "action_type": "auth",
        "description": "Login berhasil",
        "ip_address": "192.168.1.2",
        "created_at": "2026-04-01T09:00:00",
    },
    {
        "id": 4,
        "user_id": 3,
        "action": "view_report",
        "action_type": "activity",
        "description": "Melihat laporan bulanan",
        "ip_address": "192.168.1.3",
        "created_at": "2026-04-01T10:30:00",
    },
    {
        "id": 5,
        "user_id": 4,
        "action": "create_data",
        "action_type": "activity",
        "description": "Input data baru",
        "ip_address": "192.168.1.4",
        "created_at": "2026-04-01T11:15:00",
    },
]


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value).replace(tzinfo=timezone.utc)


def _validate_pin_6_digits(pin: str) -> None:
    if not pin.isdigit() or len(pin) != 6:
        raise ValueError(f"PIN tidak valid '{pin}'. PIN wajib 6 digit angka.")


def _clear_tables(session: Session) -> None:
    try:
        session.execute(
            text(
                """
                TRUNCATE TABLE
                    role_permissions,
                    user_roles,
                    user_sessions,
                    login_attempts,
                    audit_logs,
                    user_passwords,
                    user_pins,
                    permissions,
                    roles,
                    users
                RESTART IDENTITY CASCADE
                """
            )
        )
        return
    except Exception:
        session.rollback()

    # Fallback for restricted DB roles that cannot TRUNCATE.
    session.query(RolePermission).delete(synchronize_session=False)
    session.query(UserRole).delete(synchronize_session=False)
    session.query(UserSession).delete(synchronize_session=False)
    session.query(LoginAttempt).delete(synchronize_session=False)
    session.query(AuditLog).delete(synchronize_session=False)
    session.query(UserPassword).delete(synchronize_session=False)
    session.query(UserPin).delete(synchronize_session=False)
    session.query(Permission).delete(synchronize_session=False)
    session.query(Role).delete(synchronize_session=False)
    session.query(User).delete(synchronize_session=False)
    session.flush()


def _insert_roles_permissions(session: Session) -> None:
    session.add_all([Role(**row) for row in ROLES])
    session.add_all([Permission(**row) for row in PERMISSIONS])
    session.add_all([
        RolePermission(role_id=role_id, permission_id=permission_id)
        for role_id, permission_id in ROLE_PERMISSIONS
    ])


def _insert_users(session: Session) -> None:
    for row in USERS:
        session.add(
            User(
                id=row["id"],
                full_name=row["full_name"],
                username=row["username"],
                email=row["email"],
                phone=row["phone"],
                status=row["status"],
                created_at=_dt(row["created_at"]),
                updated_at=_dt(row["created_at"]),
            )
        )
        session.add(UserRole(user_id=row["id"], role_id=row["role_id"]))


def _insert_credentials(session: Session) -> None:
    for row in USER_CREDENTIALS:
        _validate_pin_6_digits(row["pin_plain"])

        password_salt, password_hash = create_password_hash(row["password_plain"])
        pin_salt, pin_hash = create_pin_hash(row["pin_plain"])

        session.add(
            UserPassword(
                id=row["id"],
                user_id=row["user_id"],
                password_hash=password_hash,
                password_salt=password_salt,
                updated_at=_dt("2026-04-01T00:00:00"),
            )
        )
        session.add(
            UserPin(
                id=row["id"],
                user_id=row["user_id"],
                pin_hash=pin_hash,
                pin_salt=pin_salt,
                failed_attempts=row["failed_attempts"],
                updated_at=_dt("2026-04-01T00:00:00"),
            )
        )


def _insert_activity(session: Session) -> None:
    for row in LOGIN_ATTEMPTS:
        session.add(
            LoginAttempt(
                id=row["id"],
                user_id=row["user_id"],
                ip_address=row["ip_address"],
                success=row["success"],
                attempt_time=_dt(row["attempt_time"]),
            )
        )

    for row in USER_SESSIONS:
        session.add(
            UserSession(
                id=row["id"],
                user_id=row["user_id"],
                access_token=row["access_token"],
                refresh_token=None,
                ip_address=row["ip_address"],
                user_agent=row["user_agent"],
                expired_at=_dt(row["expired_at"]),
            )
        )

    for row in AUDIT_LOGS:
        session.add(
            AuditLog(
                id=row["id"],
                user_id=row["user_id"],
                action=row["action"],
                action_type=row["action_type"],
                description=row["description"],
                ip_address=row["ip_address"],
                created_at=_dt(row["created_at"]),
            )
        )


def main() -> None:
    session = Session()
    try:
        _clear_tables(session)
        _insert_roles_permissions(session)
        session.flush()

        _insert_users(session)
        session.flush()

        _insert_credentials(session)
        session.flush()

        _insert_activity(session)
        session.commit()

        print("Seed selesai.")
        print(f"roles={len(ROLES)} permissions={len(PERMISSIONS)} role_permissions={len(ROLE_PERMISSIONS)}")
        print(f"users={len(USERS)} user_passwords={len(USER_CREDENTIALS)} user_pins={len(USER_CREDENTIALS)}")
        print(f"login_attempts={len(LOGIN_ATTEMPTS)} sessions={len(USER_SESSIONS)} audit_logs={len(AUDIT_LOGS)}")
        print("PIN rule tetap: 6 digit angka (disimpan sebagai hash).")
    except Exception as error:
        session.rollback()
        print(f"Seed gagal: {error}")
        raise SystemExit(1)
    finally:
        session.close()


if __name__ == "__main__":
    main()
