from datetime import datetime, timezone

from sqlalchemy.orm import Session
from src.database.models import User

try:
    from auth.passwords import create_password_hash
except ImportError:
    from src.auth.passwords import create_password_hash

def create_user(session: Session, username: str, password: str, role: str = 'user'):
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