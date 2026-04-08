try:
    from database.models import Session, User, UserPassword, UserPin
except ImportError:
    from src.database.models import Session, User, UserPassword, UserPin

try:
    from auth.passwords import create_password_hash, verify_password, verify_pin_code
except ImportError:
    from src.auth.passwords import create_password_hash, verify_password, verify_pin_code

from typing import Optional
from sqlalchemy.exc import SQLAlchemyError


def _upsert_password_record(session, user: 'User', password_hash: str, password_salt: str) -> None:
    user_id = getattr(user, "id", None)
    if user_id is None:
        return

    record = session.query(UserPassword).filter_by(user_id=user_id).first()
    if record is None:
        if not hasattr(session, "add"):
            return
        session.add(
            UserPassword(
                user_id=user_id,
                password_hash=password_hash,
                password_salt=password_salt,
            )
        )
        return

    record.password_hash = password_hash
    record.password_salt = password_salt


def authenticate(username: str, password: str, session=None) -> Optional['User']:
    close_session = False
    if session is None:
        session = Session()
        close_session = True

    # CRITICAL: Pre-load role_links using joinedload for single-user query efficiency
    from sqlalchemy.orm import joinedload
    user = session.query(User).options(joinedload(User.role_links)).filter_by(username=username).first()

    if user is None:
        if close_session:
            session.close()
        return None

    authenticated = False
    password_hash = getattr(user, "password_hash", None)
    password_salt = getattr(user, "password_salt", None)
    user_id = getattr(user, "id", None)

    if user_id is not None and (not password_hash or not password_salt):
        password_record = session.query(UserPassword).filter_by(user_id=user_id).first()
        if password_record is not None:
            password_hash = password_record.password_hash
            password_salt = password_record.password_salt

    if password_hash and password_salt:
        authenticated = verify_password(password, password_salt, password_hash)
    elif user.password:
        authenticated = user.password == password
        if authenticated:
            salt, password_hash = create_password_hash(password)
            user.password_salt = salt
            user.password_hash = password_hash
            user.password = None
            _upsert_password_record(session, user, password_hash, salt)
            session.commit()

    if authenticated:
        getattr(user, "role", None)  # Prime role before session closes

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
        # CRITICAL: Pre-load role_links before closing session to prevent DetachedInstanceError
        # when accessing user.role property later
        from sqlalchemy.orm import selectinload
        users = session.query(User).options(selectinload(User.role_links)).all()
        pin_records = {
            record.user_id: record
            for record in session.query(UserPin).all()
            if getattr(record, "user_id", None) is not None
        }

        for user in users:
            user_pin_hash = getattr(user, "pin_hash", None)
            user_pin_salt = getattr(user, "pin_salt", None)

            pin_record = pin_records.get(getattr(user, "id", None))
            if pin_record is not None:
                user_pin_hash = pin_record.pin_hash
                user_pin_salt = pin_record.pin_salt

            if user_pin_hash and user_pin_salt and verify_pin_code(pin, user_pin_salt, user_pin_hash):
                # Prime role before returning (for immediate access after detach)
                getattr(user, "role", None)
                return user
        return None
    except SQLAlchemyError as error:
        raise RuntimeError(
            "Akses database user ditolak. Cek hak akses role aplikasi ke tabel users."
        ) from error
    finally:
        if close_session:
            session.close()
