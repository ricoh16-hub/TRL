from database.models import Session, User

from typing import Optional
def authenticate(username: str, password: str, session=None) -> Optional['User']:
    close_session = False
    if session is None:
        session = Session()
        close_session = True
    user = session.query(User).filter_by(username=username, password=password).first()
    if close_session:
        session.close()
    return user