from datetime import datetime, timedelta, timezone
from secrets import token_urlsafe
from types import SimpleNamespace
from typing import Any, Optional, cast

from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError

try:
    import bcrypt
except ImportError:  # pragma: no cover - bcrypt is part of the normal app environment
    bcrypt = None  # type: ignore[assignment]

try:
    from database.models import AuditLog, LoginAttempt, Permission, RolePermission, Session, User, UserPassword, UserPin, UserRole, UserSession
except ImportError:
    from src.database.models import AuditLog, LoginAttempt, Permission, RolePermission, Session, User, UserPassword, UserPin, UserRole, UserSession

try:
    from auth.passwords import create_password_hash, verify_password, verify_pin_code
except ImportError:
    from src.auth.passwords import create_password_hash, verify_password, verify_pin_code

try:
    from app.core.security import verify_password as verify_bcrypt_password
except ImportError:  # pragma: no cover - desktop legacy deployments may not ship app package
    verify_bcrypt_password = None  # type: ignore[assignment]

HRIS_AUTH_SCHEMA_COLUMNS = {"user_id", "username", "password_hash", "is_active", "is_locked"}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_int(value: object) -> int | None:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None


def _as_str(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _save_login_attempt(session: Any, user_id: int | None, success: bool, ip_address: str | None) -> None:
    session.add(LoginAttempt(user_id=user_id, success=success, ip_address=ip_address))


def _save_audit_log(session: Any, user_id: int | None, action: str, description: str, ip_address: str | None) -> None:
    session.add(
        AuditLog(
            user_id=user_id,
            action=action,
            action_type="auth",
            description=description,
            ip_address=ip_address,
        )
    )


def _upsert_password_record(session: Any, user_id: int, password_hash: str, password_salt: str) -> None:
    password_record = session.query(UserPassword).filter_by(user_id=user_id).first()
    if password_record is None:
        session.add(
            UserPassword(
                user_id=user_id,
                password_hash=password_hash,
                password_salt=password_salt,
            )
        )
        return

    password_record.password_hash = password_hash
    password_record.password_salt = password_salt


def _table_columns(session: Any, table_name: str) -> set[str]:
    try:
        bind = session.get_bind()
        return {str(column["name"]) for column in inspect(bind).get_columns(table_name)}
    except Exception:
        return set()


def _is_hris_auth_schema(session: Any) -> bool:
    return HRIS_AUTH_SCHEMA_COLUMNS.issubset(_table_columns(session, "users"))


def _verify_bcrypt_secret(secret: str, secret_hash: str) -> bool:
    if verify_bcrypt_password is None:
        if bcrypt is None:
            return False
        try:
            return bool(bcrypt.checkpw(secret.encode("utf-8"), secret_hash.encode("utf-8")))
        except ValueError:
            return False
    return bool(verify_bcrypt_password(secret, secret_hash))


def _map_hris_role_to_desktop_role(role_names: list[str]) -> str:
    normalized_roles = {role_name.strip().upper() for role_name in role_names}
    if "SUPER_ADMIN" in normalized_roles:
        return "Superior"
    if {"HR_ADMIN", "ADMIN", "ADMINISTRATOR"} & normalized_roles:
        return "Administrator"
    if {"HR_VIEWER", "VIEWER", "AUDITOR"} & normalized_roles:
        return "Auditor"
    if role_names:
        return role_names[0]
    return "Operator"


def _load_hris_roles_for_user(session: Any, user_id: int) -> list[str]:
    role_columns = _table_columns(session, "roles")
    user_role_columns = _table_columns(session, "user_roles")
    if not {"role_id", "role_name"}.issubset(role_columns):
        return []
    if not {"user_id", "role_id"}.issubset(user_role_columns):
        return []

    rows = session.execute(
        text(
            """
            SELECT r.role_name
            FROM user_roles ur
            JOIN roles r ON r.role_id = ur.role_id
            WHERE ur.user_id = :user_id
            ORDER BY r.role_name
            """
        ),
        {"user_id": user_id},
    ).all()
    return [str(row[0]) for row in rows if row[0]]


def _load_hris_permissions_for_user(session: Any, user_id: int) -> list[str]:
    user_role_columns = _table_columns(session, "user_roles")
    permission_columns = _table_columns(session, "permissions")
    role_permission_columns = _table_columns(session, "role_permissions")
    if not {"user_id", "role_id"}.issubset(user_role_columns):
        return []
    if not {"permission_id", "module_name", "action_name"}.issubset(permission_columns):
        return []
    if not {"role_id", "permission_id"}.issubset(role_permission_columns):
        return []

    rows = session.execute(
        text(
            """
            SELECT DISTINCT p.module_name || ':' || p.action_name AS permission_name
            FROM user_roles ur
            JOIN role_permissions rp ON rp.role_id = ur.role_id
            JOIN permissions p ON p.permission_id = rp.permission_id
            WHERE ur.user_id = :user_id
            ORDER BY permission_name
            """
        ),
        {"user_id": user_id},
    ).all()
    return [str(row[0]) for row in rows if row[0]]


def _make_hris_user(session: Any, user_id: int) -> Optional[User]:
    row = session.execute(
        text(
            """
            SELECT user_id, username, is_active, is_locked, failed_login_count, last_login,
                   created_at, updated_at
            FROM users
            WHERE user_id = :user_id
            """
        ),
        {"user_id": user_id},
    ).mappings().first()
    if row is None:
        return None

    role_names = _load_hris_roles_for_user(session, user_id)
    permissions = _load_hris_permissions_for_user(session, user_id)
    is_active = bool(row.get("is_active"))
    is_locked = bool(row.get("is_locked"))
    status = "locked" if is_locked else "aktif" if is_active else "nonaktif"
    username = str(row.get("username") or "")
    compat_user = SimpleNamespace(
        id=int(row["user_id"]),
        user_id=int(row["user_id"]),
        username=username,
        full_name=username.replace("_", " ").title(),
        nama=username.replace("_", " ").title(),
        role=_map_hris_role_to_desktop_role(role_names),
        roles=role_names,
        status=status,
        is_active=is_active,
        is_locked=is_locked,
        failed_login_count=_as_int(row.get("failed_login_count")) or 0,
        last_login=row.get("last_login"),
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
        _cached_permissions=permissions,
    )
    return cast(User, compat_user)


def _save_hris_auth_audit(
    session: Any,
    user_id: int | None,
    action_name: str,
    ip_address: str | None,
) -> None:
    audit_columns = _table_columns(session, "audit_logs")
    required_columns = {
        "user_id",
        "module_name",
        "action_name",
        "table_name",
        "record_id",
        "old_data",
        "new_data",
        "ip_address",
    }
    if not required_columns.issubset(audit_columns):
        return

    session.execute(
        text(
            """
            INSERT INTO audit_logs (
                user_id, module_name, action_name, table_name, record_id,
                old_data, new_data, ip_address
            )
            VALUES (
                :user_id, 'auth', :action_name, 'users', :record_id,
                NULL, NULL, :ip_address
            )
            """
        ),
        {
            "user_id": user_id,
            "action_name": action_name,
            "record_id": str(user_id) if user_id is not None else None,
            "ip_address": ip_address,
        },
    )


def _increment_hris_failed_login(session: Any, user_id: int) -> None:
    session.execute(
        text(
            """
            UPDATE users
            SET failed_login_count = failed_login_count + 1,
                is_locked = CASE WHEN failed_login_count + 1 >= 5 THEN true ELSE is_locked END,
                updated_at = now()
            WHERE user_id = :user_id
            """
        ),
        {"user_id": user_id},
    )


def _reset_hris_failed_login(session: Any, user_id: int) -> None:
    session.execute(
        text(
            """
            UPDATE users
            SET failed_login_count = 0,
                is_locked = false,
                last_login = now(),
                updated_at = now()
            WHERE user_id = :user_id
            """
        ),
        {"user_id": user_id},
    )


def _verify_pin_step_hris(session: Any, pin: str, ip_address: str | None) -> Optional[User]:
    rows = session.execute(
        text(
            """
            SELECT user_id, pin_hash, is_active, is_locked
            FROM users
            WHERE pin_hash IS NOT NULL
            ORDER BY user_id
            """
        )
    ).mappings().all()

    for row in rows:
        if not bool(row.get("is_active")) or bool(row.get("is_locked")):
            continue
        user_id = _as_int(row.get("user_id"))
        pin_hash = _as_str(row.get("pin_hash"))
        if user_id is None or not pin_hash:
            continue
        if _verify_bcrypt_secret(pin, pin_hash):
            _save_hris_auth_audit(session, user_id, "pin_success", ip_address)
            session.commit()
            return _make_hris_user(session, user_id)

    _save_hris_auth_audit(session, None, "pin_failed", ip_address)
    session.commit()
    return None


def _authenticate_credentials_step_hris(
    session: Any,
    pin_user: User,
    username: str,
    password: str,
    ip_address: str | None,
) -> Optional[User]:
    user_id = _as_int(getattr(pin_user, "user_id", None)) or _as_int(getattr(pin_user, "id", None))
    if user_id is None:
        return None

    row = session.execute(
        text(
            """
            SELECT user_id, username, password_hash, is_active, is_locked
            FROM users
            WHERE user_id = :user_id
            """
        ),
        {"user_id": user_id},
    ).mappings().first()
    if row is None:
        _save_hris_auth_audit(session, user_id, "login_failed", ip_address)
        session.commit()
        return None

    if not bool(row.get("is_active")) or bool(row.get("is_locked")):
        _save_hris_auth_audit(session, user_id, "login_rejected", ip_address)
        session.commit()
        return None

    user_username = str(row.get("username") or "").strip()
    if user_username.lower() != username.strip().lower():
        _increment_hris_failed_login(session, user_id)
        _save_hris_auth_audit(session, user_id, "login_failed", ip_address)
        session.commit()
        return None

    password_hash = _as_str(row.get("password_hash"))
    if not password_hash or not _verify_bcrypt_secret(password, password_hash):
        _increment_hris_failed_login(session, user_id)
        _save_hris_auth_audit(session, user_id, "login_failed", ip_address)
        session.commit()
        return None

    _reset_hris_failed_login(session, user_id)
    _save_hris_auth_audit(session, user_id, "login_success", ip_address)
    session.commit()
    return _make_hris_user(session, user_id)


def _load_permissions_for_user(session: Any, user_id: int) -> list[str]:
    role_links = cast(list[Any], session.query(UserRole).filter_by(user_id=user_id).all())
    role_ids: set[int] = set()
    for role_link in role_links:
        role_id = _as_int(getattr(role_link, "role_id", None))
        if role_id is not None:
            role_ids.add(role_id)
    if not role_ids:
        return []

    permission_links = [
        link for link in session.query(RolePermission).all() if getattr(link, "role_id", None) in role_ids
    ]
    permission_ids: set[int] = set()
    for link in permission_links:
        permission_id = _as_int(getattr(link, "permission_id", None))
        if permission_id is not None:
            permission_ids.add(permission_id)
    if not permission_ids:
        return []

    permissions = cast(list[Any], session.query(Permission).all())
    permission_names: set[str] = set()
    for permission in permissions:
        permission_obj_id = _as_int(getattr(permission, "id", None))
        permission_name = _as_str(getattr(permission, "permission_name", None))
        if permission_obj_id is not None and permission_obj_id in permission_ids and permission_name is not None:
            permission_names.add(permission_name)
    return sorted(permission_names)


def verify_pin_step(pin: str, ip_address: str | None = None) -> Optional[User]:
    """Step 1: PIN verification with failed-attempt tracking and account lock policy."""
    if not pin or not pin.isdigit() or len(pin) != 6:
        return None

    session: Any = Session()
    try:
        if _is_hris_auth_schema(session):
            return _verify_pin_step_hris(session, pin, ip_address)

        user_pins = cast(list[Any], session.query(UserPin).all())
        for pin_record in user_pins:
            user_id = _as_int(getattr(pin_record, "user_id", None))
            if user_id is None:
                continue

            locked_until_raw = getattr(pin_record, "locked_until", None)
            locked_until = locked_until_raw if isinstance(locked_until_raw, datetime) else None
            if locked_until is not None and locked_until > _utc_now():
                # Skip locked account and continue checking other PIN records.
                continue

            pin_hash = _as_str(getattr(pin_record, "pin_hash", None))
            pin_salt = _as_str(getattr(pin_record, "pin_salt", None))
            if not pin_hash or not pin_salt:
                continue

            if verify_pin_code(pin, pin_salt, pin_hash):
                user = session.query(User).filter_by(id=user_id).first()
                if user is None:
                    _save_login_attempt(session, user_id=user_id, success=False, ip_address=ip_address)
                    session.commit()
                    return None

                pin_record.failed_attempts = 0
                pin_record.locked_until = None
                _save_login_attempt(session, user_id=user_id, success=True, ip_address=ip_address)
                _save_audit_log(session, user_id=user_id, action="pin_success", description="PIN valid", ip_address=ip_address)
                session.commit()

                getattr(user, "role", None)
                return user

        _save_login_attempt(session, user_id=None, success=False, ip_address=ip_address)
        _save_audit_log(session, user_id=None, action="pin_failed", description="PIN tidak cocok untuk user manapun", ip_address=ip_address)
        session.commit()
        return None
    except SQLAlchemyError as error:
        session.rollback()
        raise RuntimeError(
            "Akses database autentikasi gagal. "
            "Schema auth desktop dan HRIS perlu disinkronkan."
        ) from error
    finally:
        session.close()


def authenticate_credentials_step(
    pin_user: Optional[User],
    username: str,
    password: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> Optional[User]:
    """Step 2-5: Username/password check, session creation, role/permission loading, and audit log."""
    if pin_user is None:
        return None
    username_input = (username or "").strip()
    if not username_input or not password:
        return None

    session: Any = Session()
    try:
        if _is_hris_auth_schema(session):
            return _authenticate_credentials_step_hris(
                session=session,
                pin_user=pin_user,
                username=username_input,
                password=password,
                ip_address=ip_address,
            )

        user_id = _as_int(getattr(pin_user, "id", None))
        if user_id is None:
            return None

        user = session.query(User).filter_by(id=user_id).first()
        if user is None:
            _save_login_attempt(session, user_id=user_id, success=False, ip_address=ip_address)
            session.commit()
            return None

        status = str(getattr(user, "status", "aktif") or "aktif").lower()
        if status in {"locked", "suspended", "nonaktif", "inactive"}:
            _save_login_attempt(session, user_id=user_id, success=False, ip_address=ip_address)
            _save_audit_log(session, user_id=user_id, action="login_rejected", description=f"status akun: {status}", ip_address=ip_address)
            session.commit()
            return None

        user_username = str(getattr(user, "username", "") or "").strip()
        if user_username.lower() != username_input.lower():
            pin_record = session.query(UserPin).filter_by(user_id=user_id).first()
            if pin_record is not None:
                failed_attempts = _as_int(getattr(pin_record, "failed_attempts", 0)) or 0
                pin_record.failed_attempts = failed_attempts + 1
            _save_login_attempt(session, user_id=user_id, success=False, ip_address=ip_address)
            _save_audit_log(session, user_id=user_id, action="login_failed", description="username tidak cocok dengan PIN user", ip_address=ip_address)
            session.commit()
            return None

        password_hash = _as_str(getattr(user, "password_hash", None))
        password_salt = _as_str(getattr(user, "password_salt", None))
        if not password_hash or not password_salt:
            password_record = session.query(UserPassword).filter_by(user_id=user_id).first()
            if password_record is not None:
                password_hash = _as_str(getattr(password_record, "password_hash", None))
                password_salt = _as_str(getattr(password_record, "password_salt", None))

        authenticated = False
        if password_hash and password_salt:
            authenticated = verify_password(password, password_salt, password_hash)
            if not authenticated:
                password_plaintext = _as_str(getattr(user, "password_plaintext", None))
                if password_plaintext and password_plaintext == password:
                    repaired_salt, repaired_hash = create_password_hash(password)
                    _upsert_password_record(session, user_id, repaired_hash, repaired_salt)
                    authenticated = True

        pin_record = session.query(UserPin).filter_by(user_id=user_id).first()
        if not authenticated:
            if pin_record is not None:
                failed_attempts = _as_int(getattr(pin_record, "failed_attempts", 0)) or 0
                next_failed_attempts = failed_attempts + 1
                pin_record.failed_attempts = next_failed_attempts
                if next_failed_attempts >= 5:
                    pin_record.locked_until = _utc_now() + timedelta(minutes=5)
            _save_login_attempt(session, user_id=user_id, success=False, ip_address=ip_address)
            _save_audit_log(session, user_id=user_id, action="login_failed", description="username/password tidak valid", ip_address=ip_address)
            session.commit()
            return None

        if pin_record is not None:
            pin_record.failed_attempts = 0
            pin_record.locked_until = None

        access_token = token_urlsafe(24)
        refresh_token = token_urlsafe(32)
        expired_at = _utc_now() + timedelta(hours=8)
        session.add(
            UserSession(
                user_id=user_id,
                access_token=access_token,
                refresh_token=refresh_token,
                ip_address=ip_address,
                user_agent=user_agent,
                expired_at=expired_at,
            )
        )

        permissions = _load_permissions_for_user(session, user_id)
        setattr(user, "_cached_permissions", permissions)
        getattr(user, "role", None)

        _save_login_attempt(session, user_id=user_id, success=True, ip_address=ip_address)
        _save_audit_log(session, user_id=user_id, action="login_success", description="login berhasil", ip_address=ip_address)
        session.commit()
        return user
    except SQLAlchemyError as error:
        session.rollback()
        raise RuntimeError(
            "Akses database autentikasi gagal. "
            "Schema auth desktop dan HRIS perlu disinkronkan."
        ) from error
    finally:
        session.close()
