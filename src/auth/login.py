try:
    from database.models import Session, User
except ImportError:
    from src.database.models import Session, User

try:
    from auth.passwords import create_password_hash, verify_password
except ImportError:
    from src.auth.passwords import create_password_hash, verify_password

from typing import Optional
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