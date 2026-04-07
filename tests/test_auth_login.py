from types import SimpleNamespace
from sqlalchemy.exc import SQLAlchemyError

import src.auth.login as login_module


class FakeQuery:
    def __init__(self, user: SimpleNamespace | None, users: list[SimpleNamespace] | None = None) -> None:
        self.user = user
        self.users = users or ([] if user is None else [user])
        self.username: str | None = None

    def filter_by(self, **kwargs: str) -> "FakeQuery":
        self.username = kwargs.get("username")
        return self

    def first(self) -> SimpleNamespace | None:
        if self.user is None:
            return None
        if self.username != self.user.username:
            return None
        return self.user

    def all(self) -> list[SimpleNamespace]:
        return self.users


class FakeSession:
    def __init__(self, user: SimpleNamespace | None, users: list[SimpleNamespace] | None = None) -> None:
        self.user = user
        self.users = users or ([] if user is None else [user])
        self.closed = False
        self.committed = False

    def query(self, _model: object) -> FakeQuery:
        return FakeQuery(self.user, self.users)

    def close(self) -> None:
        self.closed = True

    def commit(self) -> None:
        self.committed = True


def test_authenticate_returns_none_for_unknown_user(monkeypatch) -> None:
    fake_session = FakeSession(None)
    monkeypatch.setattr(login_module, "Session", lambda: fake_session)

    authenticated_user = login_module.authenticate("tidak-ada", "secret")

    assert authenticated_user is None
    assert fake_session.closed is True


def test_authenticate_accepts_hashed_password(monkeypatch) -> None:
    salt, password_hash = login_module.create_password_hash("secret")
    user = SimpleNamespace(
        username="alice",
        password=None,
        password_hash=password_hash,
        password_salt=salt,
    )
    fake_session = FakeSession(user)
    monkeypatch.setattr(login_module, "Session", lambda: fake_session)

    authenticated_user = login_module.authenticate("alice", "secret")

    assert authenticated_user is user
    assert fake_session.committed is False
    assert fake_session.closed is True


def test_authenticate_migrates_legacy_plaintext_password(monkeypatch) -> None:
    user = SimpleNamespace(
        username="legacy-user",
        password="secret",
        password_hash=None,
        password_salt=None,
    )
    fake_session = FakeSession(user)
    monkeypatch.setattr(login_module, "Session", lambda: fake_session)

    authenticated_user = login_module.authenticate("legacy-user", "secret")

    assert authenticated_user is user
    assert fake_session.committed is True
    assert fake_session.closed is True
    assert user.password is None
    assert isinstance(user.password_hash, str)
    assert isinstance(user.password_salt, str)


def test_authenticate_returns_none_for_hashed_password_mismatch(monkeypatch) -> None:
    salt, password_hash = login_module.create_password_hash("secret")
    user = SimpleNamespace(
        username="alice",
        password=None,
        password_hash=password_hash,
        password_salt=salt,
    )
    fake_session = FakeSession(user)
    monkeypatch.setattr(login_module, "Session", lambda: fake_session)

    authenticated_user = login_module.authenticate("alice", "wrong-password")

    assert authenticated_user is None
    assert fake_session.closed is True
    assert fake_session.committed is False


def test_authenticate_returns_none_for_plaintext_password_mismatch(monkeypatch) -> None:
    user = SimpleNamespace(
        username="legacy-user",
        password="secret",
        password_hash=None,
        password_salt=None,
    )
    fake_session = FakeSession(user)
    monkeypatch.setattr(login_module, "Session", lambda: fake_session)

    authenticated_user = login_module.authenticate("legacy-user", "wrong-password")

    assert authenticated_user is None
    assert fake_session.closed is True
    assert fake_session.committed is False
    assert user.password == "secret"
    assert user.password_hash is None
    assert user.password_salt is None


def test_authenticate_with_external_session_does_not_close(monkeypatch) -> None:
    salt, password_hash = login_module.create_password_hash("secret")
    user = SimpleNamespace(
        username="alice",
        password=None,
        password_hash=password_hash,
        password_salt=salt,
    )
    fake_session = FakeSession(user)
    monkeypatch.setattr(login_module, "Session", lambda: fake_session)

    authenticated_user = login_module.authenticate("alice", "secret", session=fake_session)

    assert authenticated_user is user
    assert fake_session.closed is False


def test_authenticate_returns_none_when_user_has_no_password_fields(monkeypatch) -> None:
    user = SimpleNamespace(
        username="alice",
        password=None,
        password_hash=None,
        password_salt=None,
    )
    fake_session = FakeSession(user)
    monkeypatch.setattr(login_module, "Session", lambda: fake_session)

    authenticated_user = login_module.authenticate("alice", "secret")

    assert authenticated_user is None
    assert fake_session.closed is True


def test_authenticate_unknown_user_with_external_session_does_not_close(monkeypatch) -> None:
    fake_session = FakeSession(None)
    monkeypatch.setattr(login_module, "Session", lambda: fake_session)

    authenticated_user = login_module.authenticate("tidak-ada", "secret", session=fake_session)

    assert authenticated_user is None
    assert fake_session.closed is False


def test_verify_pin_returns_matching_user(monkeypatch) -> None:
    pin_salt, pin_hash = login_module.create_password_hash("123456")
    user = SimpleNamespace(
        id=1,
        username="alice",
        pin_hash=pin_hash,
        pin_salt=pin_salt,
    )
    fake_session = FakeSession(user, users=[user])
    monkeypatch.setattr(login_module, "Session", lambda: fake_session)
    monkeypatch.setattr(login_module, "verify_pin_code", lambda pin, salt, stored_hash: pin == "123456")

    authenticated_user = login_module.verify_pin("123456")

    assert authenticated_user is user
    assert fake_session.closed is True


def test_verify_pin_returns_none_when_no_match(monkeypatch) -> None:
    user = SimpleNamespace(
        id=1,
        username="alice",
        pin_hash="hash",
        pin_salt="salt",
    )
    fake_session = FakeSession(user, users=[user])
    monkeypatch.setattr(login_module, "Session", lambda: fake_session)
    monkeypatch.setattr(login_module, "verify_pin_code", lambda *_args, **_kwargs: False)

    authenticated_user = login_module.verify_pin("123456")

    assert authenticated_user is None
    assert fake_session.closed is True


def test_verify_pin_rejects_invalid_format() -> None:
    assert login_module.verify_pin("12345") is None
    assert login_module.verify_pin("12ab56") is None


def test_verify_pin_with_external_session_does_not_close(monkeypatch) -> None:
    user_without_pin = SimpleNamespace(
        id=1,
        username="alice",
        pin_hash=None,
        pin_salt=None,
    )
    user_with_pin = SimpleNamespace(
        id=2,
        username="bob",
        pin_hash="hash",
        pin_salt="salt",
    )
    fake_session = FakeSession(user_with_pin, users=[user_without_pin, user_with_pin])
    monkeypatch.setattr(login_module, "verify_pin_code", lambda pin, *_args, **_kwargs: pin == "123456")

    authenticated_user = login_module.verify_pin("123456", session=fake_session)

    assert authenticated_user is user_with_pin
    assert fake_session.closed is False


def test_verify_pin_raises_runtime_error_when_query_fails(monkeypatch) -> None:
    class BrokenQuery:
        def all(self):
            raise SQLAlchemyError("boom")

    class BrokenSession:
        def __init__(self) -> None:
            self.closed = False

        def query(self, _model: object):
            return BrokenQuery()

        def close(self) -> None:
            self.closed = True

    broken_session = BrokenSession()
    monkeypatch.setattr(login_module, "Session", lambda: broken_session)

    try:
        login_module.verify_pin("123456")
    except RuntimeError as error:
        assert "Akses database user ditolak" in str(error)
    else:
        raise AssertionError("Expected RuntimeError when query fails")

    assert broken_session.closed is True