from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session
from sqlalchemy.orm import selectinload
try:
    from database.models import Role, User, UserPassword, UserPin, UserRole
except ImportError:
    from src.database.models import Role, User, UserPassword, UserPin, UserRole

CANONICAL_ROLES: tuple[str, ...] = (
    "Superior",
    "Administrator",
    "Operator",
    "Auditor",
)

ROLE_MAPPING: dict[str, str] = {
    "super admin": "Superior",
    "superadmin": "Superior",
    "superior": "Superior",
    "admin": "Administrator",
    "administrator": "Administrator",
    "manager": "Administrator",
    "staff": "Administrator",
    "operator": "Operator",
    "viewer": "Auditor",
    "auditor": "Auditor",
}

try:
    from auth.passwords import create_password_hash, create_pin_hash, verify_pin_code
except ImportError:
    from src.auth.passwords import create_password_hash, create_pin_hash, verify_pin_code


def _validate_pin_format(pin: str) -> str:
    normalized_pin = pin.strip()
    if not normalized_pin.isdigit() or len(normalized_pin) != 6:
        raise ValueError('PIN harus tepat 6 digit angka.')
    return normalized_pin


def normalize_role_name(role_name: str) -> str:
    normalized_key = " ".join(role_name.strip().lower().split())
    mapped_role = ROLE_MAPPING.get(normalized_key)
    if mapped_role is None:
        supported = ", ".join(CANONICAL_ROLES)
        raise ValueError(f"Role tidak valid. Gunakan salah satu: {supported}.")
    return mapped_role


def _normalize_status(status: str) -> str:
    normalized_status = status.strip().lower()
    if normalized_status not in {"aktif", "nonaktif"}:
        raise ValueError("Status harus Aktif atau Nonaktif.")
    return normalized_status


def _ensure_pin_unique(session: Session, pin: str, exclude_user_id: int | None = None) -> None:
    users = session.query(User).all()
    pin_records = {
        record.user_id: record
        for record in session.query(UserPin).all()
        if getattr(record, 'user_id', None) is not None
    }

    for existing_user in users:
        if exclude_user_id is not None and existing_user.id == exclude_user_id:
            continue

        pin_hash = str(getattr(existing_user, 'pin_hash', '') or '')
        pin_salt = str(getattr(existing_user, 'pin_salt', '') or '')

        pin_record = pin_records.get(existing_user.id)
        if pin_record is not None:
            pin_hash = pin_record.pin_hash
            pin_salt = pin_record.pin_salt

        if pin_hash and pin_salt and verify_pin_code(pin, pin_salt, pin_hash):
            raise ValueError('PIN sudah dipakai user lain. Gunakan PIN berbeda.')


def _get_or_create_role(session: Session, role_name: str) -> Role:
    normalized_role_name = normalize_role_name(role_name)
    role = session.query(Role).filter_by(role_name=normalized_role_name).first()
    if role is None:
        role = Role(role_name=normalized_role_name)
        session.add(role)
        session.flush()
    return role


def _sync_user_role(session: Session, user: User, role_name: str) -> None:
    role = _get_or_create_role(session, role_name)
    for existing_link in list(user.role_links):
        session.delete(existing_link)
    session.flush()

    role_link = UserRole(user=user, role=role)
    session.add(role_link)
    user.role_links = [role_link]


def _upsert_password_record(session: Session, user: User, password_hash: str, password_salt: str) -> None:
    record = session.query(UserPassword).filter_by(user_id=user.id).first()
    if record is None:
        record = UserPassword(
            user_id=user.id,
            password_hash=password_hash,
            password_salt=password_salt,
            updated_at=datetime.now(timezone.utc),
        )
        session.add(record)
        return

    record.password_hash = password_hash
    record.password_salt = password_salt
    record.updated_at = datetime.now(timezone.utc)


def _upsert_pin_record(session: Session, user: User, pin_hash: str, pin_salt: str) -> None:
    record = session.query(UserPin).filter_by(user_id=user.id).first()
    if record is None:
        record = UserPin(
            user_id=user.id,
            pin_hash=pin_hash,
            pin_salt=pin_salt,
            failed_attempts=0,
            updated_at=datetime.now(timezone.utc),
        )
        session.add(record)
        return

    record.pin_hash = pin_hash
    record.pin_salt = pin_salt
    record.failed_attempts = 0
    record.updated_at = datetime.now(timezone.utc)


def create_user(
    session: Session,
    username: str,
    password: str,
    role: str = 'Operator',
    pin: str = '',
    nama: str = '',
    status: str = 'aktif',
) -> User:
    username = username.strip()
    nama = nama.strip()
    normalized_role = normalize_role_name(role)
    normalized_status = _normalize_status(status)
    if not username:
        raise ValueError('Username tidak boleh kosong.')

    salt, password_hash = create_password_hash(password)
    password_plaintext = password
    user = User(
        username=username,
        full_name=nama or None,
        password_plaintext=password_plaintext,
        status=normalized_status,
        updated_at=datetime.now(timezone.utc),
    )

    pin_payload: tuple[str, str] | None = None
    normalized_pin_value: str | None = None

    if pin.strip():
        normalized_pin = _validate_pin_format(pin)
        _ensure_pin_unique(session, normalized_pin)
        pin_salt, pin_hash = create_pin_hash(normalized_pin)
        pin_payload = (pin_hash, pin_salt)
        normalized_pin_value = normalized_pin

    session.add(user)
    session.flush()

    _upsert_password_record(session, user, password_hash, salt)
    _sync_user_role(session, user, normalized_role)
    if pin_payload is not None:
        _upsert_pin_record(session, user, pin_payload[0], pin_payload[1])
        user.pin_plaintext = normalized_pin_value

    session.commit()
    return user

def read_users(session: Session) -> list[User]:
    return (
        session.query(User)
        .options(
            selectinload(User.role_links).selectinload(UserRole.role),
            selectinload(User.password_record),
            selectinload(User.pin_record),
        )
        .all()
    )

def update_user(session: Session, user_id: int, **kwargs: Any) -> User:
    user = session.get(User, user_id)
    if user is None:
        raise ValueError('User tidak ditemukan.')

    for key, value in kwargs.items():
        if key == 'password':
            if value:
                salt, password_hash = create_password_hash(value)
                _upsert_password_record(session, user, password_hash, salt)
                user.password_plaintext = str(value)
            continue

        if key == 'username' and isinstance(value, str):
            value = value.strip()
            if not value:
                raise ValueError('Username tidak boleh kosong.')

        if key == 'role' and isinstance(value, str):
            normalized_role = normalize_role_name(value)
            _sync_user_role(session, user, normalized_role)
            continue

        if key == 'nama' and isinstance(value, str):
            value = value.strip() or None
            user.full_name = value
            continue

        if key == 'full_name' and isinstance(value, str):
            user.full_name = value.strip() or None
            continue

        if key == 'status' and isinstance(value, str):
            value = _normalize_status(value)

        setattr(user, key, value)
    user.updated_at = datetime.now(timezone.utc)
    session.commit()
    return user

def delete_user(session: Session, user_id: int) -> None:
    user = session.get(User, user_id)
    if user is None:
        raise ValueError('User tidak ditemukan.')
    session.delete(user)
    session.commit()


def set_user_pin(session: Session, user_id: int, pin: str) -> User:
    user = session.get(User, user_id)
    if user is None:
        raise ValueError('User tidak ditemukan.')

    normalized_pin = _validate_pin_format(pin)
    _ensure_pin_unique(session, normalized_pin, exclude_user_id=user_id)
    pin_salt, pin_hash = create_pin_hash(normalized_pin)
    _upsert_pin_record(session, user, pin_hash, pin_salt)
    user.pin_plaintext = normalized_pin
    user.updated_at = datetime.now(timezone.utc)
    session.commit()
    return user