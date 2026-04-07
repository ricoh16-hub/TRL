try:
    from database.models import Session, User
except ImportError:
    from src.database.models import Session, User

try:
    from auth.passwords import create_password_hash, verify_password, verify_pin_code
except ImportError:
    from src.auth.passwords import create_password_hash, verify_password, verify_pin_code

from typing import Optional
from sqlalchemy.exc import SQLAlchemyError


def authenticate(username: str, password: str, session=None) -> Optional['User']:
    close_session = False
    if session is None:
        session = Session()
        close_session = True

    user = session.query(User).filter_by(username=username).first()

    if user is None:
        if close_session:
            session.close()
        return None

    authenticated = False

    if user.password_hash and user.password_salt:
        authenticated = verify_password(password, user.password_salt, user.password_hash)
    elif user.password:
        authenticated = user.password == password
        if authenticated:
            salt, password_hash = create_password_hash(password)
            user.password_salt = salt
            user.password_hash = password_hash
            user.password = None
            session.commit()

    if close_session:
        session.close()
    return user if authenticated else None


def verify_pin(pin: str, session=None) -> Optional['User']:
    """Verifikasi PIN 6 digit. Return User yang cocok, None jika salah atau belum diatur."""
    if not pin or not pin.isdigit() or len(pin) != 6:
        return None

    close_session = False
    if session is None:
        session = Session()
        close_session = True

    try:
        users = session.query(User).all()
        for user in users:
            user_pin_hash = getattr(user, "pin_hash", None)
            user_pin_salt = getattr(user, "pin_salt", None)
            if user_pin_hash and user_pin_salt and verify_pin_code(pin, user_pin_salt, user_pin_hash):
                return user
        return None
    except SQLAlchemyError as error:
        raise RuntimeError(
            "Akses database user ditolak. Cek hak akses role aplikasi ke tabel users."
        ) from error
    finally:
        if close_session:
            session.close()