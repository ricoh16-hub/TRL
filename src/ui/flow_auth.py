from datetime import datetime, timedelta, timezone
from secrets import token_urlsafe
from typing import Any, Optional, cast

try:
    from database.models import AuditLog, LoginAttempt, Permission, RolePermission, Session, User, UserPassword, UserPin, UserRole, UserSession
except ImportError:
    from src.database.models import AuditLog, LoginAttempt, Permission, RolePermission, Session, User, UserPassword, UserPin, UserRole, UserSession

try:
    from auth.passwords import verify_password, verify_pin_code
except ImportError:
    from src.auth.passwords import verify_password, verify_pin_code


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
    if not username or not password:
        return None

    session: Any = Session()
    try:
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

        if str(getattr(user, "username", "")) != username:
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
    finally:
        session.close()
