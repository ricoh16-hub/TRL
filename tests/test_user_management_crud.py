from sqlalchemy import create_engine
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.auth.passwords import verify_password, verify_pin_code
from src.database.crud import create_user, delete_user, read_users, set_user_pin, update_user
from src.database.models import Base, LoginAttempt, UserPassword, UserPin, UserSession


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _hris_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE users (
                    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username VARCHAR UNIQUE NOT NULL,
                    full_name VARCHAR,
                    email VARCHAR,
                    phone VARCHAR,
                    status VARCHAR,
                    password_hash VARCHAR NOT NULL,
                    pin_hash VARCHAR,
                    failed_login_count INTEGER NOT NULL DEFAULT 0,
                    is_locked BOOLEAN NOT NULL DEFAULT 0,
                    is_active BOOLEAN NOT NULL DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE roles (
                    role_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    role_name VARCHAR UNIQUE NOT NULL,
                    description TEXT
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE user_roles (
                    user_role_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    role_id INTEGER NOT NULL,
                    UNIQUE (user_id, role_id)
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE login_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    success BOOLEAN NOT NULL
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE user_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    access_token VARCHAR NOT NULL,
                    expired_at TIMESTAMP NOT NULL
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    action VARCHAR NOT NULL
                )
                """
            )
        )
    return sessionmaker(bind=engine)()


def test_user_management_create_update_and_delete_user() -> None:
    session = _session()
    try:
        user = create_user(
            session,
            username="riko01",
            nama="Riko Sinaga",
            password="Start123!",
            role="Operator",
            status="aktif",
            pin="123456",
        )

        password_record = session.query(UserPassword).filter_by(user_id=user.id).one()
        pin_record = session.query(UserPin).filter_by(user_id=user.id).one()
        assert verify_password("Start123!", password_record.password_salt, password_record.password_hash)
        assert verify_pin_code("123456", pin_record.pin_salt, pin_record.pin_hash)

        updated = update_user(
            session,
            user.id,
            username="riko02",
            nama="Riko Updated",
            password="Next123!",
            role="Administrator",
            status="nonaktif",
        )
        set_user_pin(session, user.id, "654321")

        assert updated.username == "riko02"
        assert updated.full_name == "Riko Updated"
        assert updated.role == "Administrator"
        assert updated.status == "nonaktif"

        refreshed_password = session.query(UserPassword).filter_by(user_id=user.id).one()
        refreshed_pin = session.query(UserPin).filter_by(user_id=user.id).one()
        assert verify_password("Next123!", refreshed_password.password_salt, refreshed_password.password_hash)
        assert verify_pin_code("654321", refreshed_pin.pin_salt, refreshed_pin.pin_hash)

        session.add(
            UserSession(
                user_id=user.id,
                access_token="access",
                refresh_token="refresh",
                expired_at=updated.updated_at,
            )
        )
        session.add(LoginAttempt(user_id=user.id, success=True))
        session.commit()

        delete_user(session, user.id)

        assert read_users(session) == []
        assert session.query(UserSession).count() == 0
        assert session.query(LoginAttempt).one().user_id is None
    finally:
        session.close()


def test_user_management_rejects_duplicate_username_on_create_and_update() -> None:
    session = _session()
    try:
        first = create_user(session, "first", "Password1!", pin="111111")
        second = create_user(session, "second", "Password2!", pin="222222")

        try:
            create_user(session, "first", "Password3!", pin="333333")
        except ValueError as error:
            assert "Username" in str(error)
        else:
            raise AssertionError("duplicate username create should fail")

        try:
            update_user(session, second.id, username=first.username)
        except ValueError as error:
            assert "Username" in str(error)
        else:
            raise AssertionError("duplicate username update should fail")
    finally:
        session.close()


def test_user_management_supports_hris_user_id_schema() -> None:
    session = _hris_session()
    try:
        user = create_user(
            session,
            username="hris01",
            nama="HRIS User",
            password="Start123!",
            role="Superior",
            status="aktif",
            pin="123456",
        )
        assert user.id == user.user_id

        rows = read_users(session)
        assert len(rows) == 1
        assert rows[0].username == "hris01"
        assert rows[0].role == "SUPER_ADMIN"

        updated = update_user(
            session,
            user.id,
            username="hris02",
            nama="HRIS Updated",
            password="Next123!",
            role="Administrator",
            status="nonaktif",
        )
        set_user_pin(session, user.id, "654321")
        assert updated.username == "hris02"
        assert updated.status == "nonaktif"

        session.execute(
            text(
                """
                INSERT INTO user_sessions (user_id, access_token, expired_at)
                VALUES (:user_id, 'token', CURRENT_TIMESTAMP)
                """
            ),
            {"user_id": user.id},
        )
        session.execute(
            text("INSERT INTO login_attempts (user_id, success) VALUES (:user_id, 1)"),
            {"user_id": user.id},
        )
        session.commit()

        delete_user(session, user.id)

        assert session.execute(text("SELECT COUNT(*) FROM users")).scalar_one() == 0
        assert session.execute(text("SELECT COUNT(*) FROM user_sessions")).scalar_one() == 0
        assert session.execute(text("SELECT user_id FROM login_attempts")).scalar_one() is None
    finally:
        session.close()
