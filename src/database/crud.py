from sqlalchemy.orm import Session
from src.database.models import User

def create_user(session: Session, username: str, password: str, role: str = 'user'):
    user = User(username=username, password=password, role=role)
    session.add(user)
    session.commit()
    return user

def read_users(session: Session):
    return session.query(User).all()

def update_user(session: Session, user_id: int, **kwargs):
    user = session.query(User).get(user_id)
    for key, value in kwargs.items():
        setattr(user, key, value)
    session.commit()
    return user

def delete_user(session: Session, user_id: int):
    user = session.query(User).get(user_id)
    session.delete(user)
    session.commit()