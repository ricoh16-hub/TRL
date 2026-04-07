from datetime import datetime, timezone

from sqlalchemy.orm import Session
try:
    from database.models import User
except ImportError:
    from src.database.models import User

try:
    from auth.passwords import create_password_hash, create_pin_hash, verify_pin_code
except ImportError:
    from src.auth.passwords import create_password_hash, create_pin_hash, verify_pin_code


def _validate_pin_format(pin: str) -> str:
    normalized_pin = pin.strip()
    if not normalized_pin.isdigit() or len(normalized_pin) != 6:
        raise ValueError('PIN harus tepat 6 digit angka.')
    return normalized_pin


def _ensure_pin_unique(session: Session, pin: str, exclude_user_id: int | None = None) -> None:
    users = session.query(User).all()
    for existing_user in users:
        if exclude_user_id is not None and existing_user.id == exclude_user_id:
            continue

        if existing_user.pin_hash and existing_user.pin_salt:
            if verify_pin_code(pin, existing_user.pin_salt, existing_user.pin_hash):
                raise ValueError('PIN sudah dipakai user lain. Gunakan PIN berbeda.')


def create_user(session: Session, username: str, password: str, role: str = 'user', pin: str = ''):
    username = username.strip()
    role = role.strip() or 'user'
    if not username:
        raise ValueError('Username tidak boleh kosong.')

    salt, password_hash = create_password_hash(password)
    user = User(
        username=username,
        password=None,
        password_hash=password_hash,
        password_salt=salt,
        role=role,
        updated_at=datetime.now(timezone.utc),
    )

    if pin.strip():
        normalized_pin = _validate_pin_format(pin)
        _ensure_pin_unique(session, normalized_pin)
        pin_salt, pin_hash = create_pin_hash(normalized_pin)
        user.pin_salt = pin_salt
        user.pin_hash = pin_hash

    session.add(user)
    session.commit()
    return user

def read_users(session: Session):
    return session.query(User).all()

def update_user(session: Session, user_id: int, **kwargs):
    user = session.get(User, user_id)
    if user is None:
        raise ValueError('User tidak ditemukan.')

    for key, value in kwargs.items():
        if key == 'password':
            if value:
                salt, password_hash = create_password_hash(value)
                user.password = None
                user.password_hash = password_hash
                user.password_salt = salt
            continue

        if key == 'username' and isinstance(value, str):
            value = value.strip()
            if not value:
                raise ValueError('Username tidak boleh kosong.')

        if key == 'role' and isinstance(value, str):
            value = value.strip() or 'user'

        setattr(user, key, value)
    user.updated_at = datetime.now(timezone.utc)
    session.commit()
    return user

def delete_user(session: Session, user_id: int):
    user = session.get(User, user_id)
    if user is None:
        raise ValueError('User tidak ditemukan.')
    session.delete(user)
    session.commit()


def set_user_pin(session: Session, user_id: int, pin: str):
    user = session.get(User, user_id)
    if user is None:
        raise ValueError('User tidak ditemukan.')

    normalized_pin = _validate_pin_format(pin)
    _ensure_pin_unique(session, normalized_pin, exclude_user_id=user_id)
    pin_salt, pin_hash = create_pin_hash(normalized_pin)
    user.pin_salt = pin_salt
    user.pin_hash = pin_hash
    user.updated_at = datetime.now(timezone.utc)
    session.commit()
    return user