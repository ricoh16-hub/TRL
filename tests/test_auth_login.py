from types import SimpleNamespace

import src.auth.login as login_module


class FakeQuery:
    def __init__(self, user: SimpleNamespace | None) -> None:
        self.user = user
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


class FakeSession:
    def __init__(self, user: SimpleNamespace | None) -> None:
        self.user = user
        self.closed = False
        self.committed = False

    def query(self, _model: object) -> FakeQuery:
        return FakeQuery(self.user)

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


def test_authenticate_unknown_user_with_external_session_does_not_close(monkeypatch) -> None:
    fake_session = FakeSession(None)
    monkeypatch.setattr(login_module, "Session", lambda: fake_session)

    authenticated_user = login_module.authenticate("tidak-ada", "secret", session=fake_session)

    assert authenticated_user is None
    assert fake_session.closed is False