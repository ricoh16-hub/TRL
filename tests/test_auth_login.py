from types import SimpleNamespace
from sqlalchemy.exc import SQLAlchemyError

import src.auth.login as login_module


class FakeQuery:
    def __init__(self, user: SimpleNamespace | None, users: list[SimpleNamespace] | None = None) -> None:
        self.user = user
        self.users = users or ([] if user is None else [user])
        self.username: str | None = None

    def options(self, *args, **kwargs):
        """Support eager-loading options (joinedload, selectinload), just return self for chaining."""
        return self

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


class AdvancedFakeQuery:
    def __init__(self, records: list[object]) -> None:
        self.records = records
        self.filters: dict[str, object] = {}

    def options(self, *args, **kwargs):
        """Support eager-loading options (joinedload, selectinload), just return self for chaining."""
        return self

    def filter_by(self, **kwargs: object) -> "AdvancedFakeQuery":
        self.filters = kwargs
        return self

    def first(self):
        for record in self.records:
            if all(getattr(record, key, None) == value for key, value in self.filters.items()):
                return record
        return None

    def all(self) -> list[object]:
        return self.records


class AdvancedFakeSession:
    def __init__(
        self,
        users: list[object],
        password_records: list[object] | None = None,
        pin_records: list[object] | None = None,
    ) -> None:
        self.users = users
        self.password_records = password_records or []
        self.pin_records = pin_records or []
        self.added: list[object] = []
        self.closed = False
        self.committed = False

    def query(self, model: object) -> AdvancedFakeQuery:
        if model is login_module.User:
            return AdvancedFakeQuery(self.users)
        if model is login_module.UserPassword:
            return AdvancedFakeQuery(self.password_records)
        if model is login_module.UserPin:
            return AdvancedFakeQuery(self.pin_records)
        return AdvancedFakeQuery([])

    def add(self, record: object) -> None:
        self.added.append(record)
        if isinstance(record, login_module.UserPassword):
            self.password_records.append(record)

    def commit(self) -> None:
        self.committed = True

    def close(self) -> None:
        self.closed = True


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
        def options(self, *args, **kwargs):
            """Support eager-loading options, just return self for chaining."""
            return self

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


def test_authenticate_uses_normalized_password_record(monkeypatch) -> None:
    salt, password_hash = login_module.create_password_hash("secret")
    user = SimpleNamespace(
        id=10,
        username="alice",
        password=None,
        password_hash=None,
        password_salt=None,
    )
    password_record = SimpleNamespace(user_id=10, password_hash=password_hash, password_salt=salt)
    fake_session = AdvancedFakeSession(users=[user], password_records=[password_record])
    monkeypatch.setattr(login_module, "Session", lambda: fake_session)

    authenticated_user = login_module.authenticate("alice", "secret")

    assert authenticated_user is user
    assert fake_session.closed is True


def test_authenticate_prefers_normalized_password_record_over_plaintext(monkeypatch) -> None:
    user = SimpleNamespace(
        id=11,
        username="legacy-user",
        password="secret",
        password_hash=None,
        password_salt=None,
    )
    old_salt, old_hash = login_module.create_password_hash("lama")
    existing_record = SimpleNamespace(user_id=11, password_hash=old_hash, password_salt=old_salt)
    fake_session = AdvancedFakeSession(users=[user], password_records=[existing_record])
    monkeypatch.setattr(login_module, "Session", lambda: fake_session)

    authenticated_user = login_module.authenticate("legacy-user", "secret")

    assert authenticated_user is None
    assert fake_session.committed is False
    assert existing_record.password_hash == old_hash
    assert existing_record.password_salt == old_salt


def test_authenticate_legacy_migration_inserts_password_record_when_missing(monkeypatch) -> None:
    user = SimpleNamespace(
        id=13,
        username="legacy-new",
        password="secret",
        password_hash=None,
        password_salt=None,
    )
    fake_session = AdvancedFakeSession(users=[user], password_records=[])
    monkeypatch.setattr(login_module, "Session", lambda: fake_session)

    authenticated_user = login_module.authenticate("legacy-new", "secret")

    assert authenticated_user is user
    assert fake_session.committed is True
    assert len(fake_session.password_records) == 1
    inserted = fake_session.password_records[0]
    assert inserted.user_id == 13


def test_verify_pin_uses_normalized_pin_record(monkeypatch) -> None:
    user = SimpleNamespace(
        id=12,
        username="bob",
        pin_hash=None,
        pin_salt=None,
    )
    pin_record = SimpleNamespace(user_id=12, pin_hash="hash", pin_salt="salt")
    fake_session = AdvancedFakeSession(users=[user], pin_records=[pin_record])
    monkeypatch.setattr(login_module, "Session", lambda: fake_session)
    monkeypatch.setattr(login_module, "verify_pin_code", lambda pin, *_args, **_kwargs: pin == "123456")

    authenticated_user = login_module.verify_pin("123456")

    assert authenticated_user is user
    assert fake_session.closed is True


def test_upsert_password_record_returns_without_add_method() -> None:
    user = SimpleNamespace(id=20)

    class SessionWithoutAdd:
        def query(self, _model: object):
            class _Query:
                def filter_by(self, **_kwargs):
                    return self

                def first(self):
                    return None

            return _Query()

    session = SessionWithoutAdd()
    login_module._upsert_password_record(session, user, "hash", "salt")


def test_upsert_password_record_updates_existing_record() -> None:
    existing_record = SimpleNamespace(user_id=21, password_hash="old-hash", password_salt="old-salt")
    session = AdvancedFakeSession(users=[], password_records=[existing_record])
    user = SimpleNamespace(id=21)

    login_module._upsert_password_record(session, user, "new-hash", "new-salt")

    assert existing_record.password_hash == "new-hash"
    assert existing_record.password_salt == "new-salt"


def test_authenticate_primes_role_before_internal_session_closes(monkeypatch) -> None:
    salt, password_hash = login_module.create_password_hash("secret")

    class RoleAwareUser:
        def __init__(self) -> None:
            self.username = "alice"
            self.password = None
            self.password_hash = password_hash
            self.password_salt = salt
            self.role_accessed = False

        @property
        def role(self):
            self.role_accessed = True
            return "admin"

    user = RoleAwareUser()
    fake_session = FakeSession(user)
    monkeypatch.setattr(login_module, "Session", lambda: fake_session)

    authenticated_user = login_module.authenticate("alice", "secret")

    assert authenticated_user is user
    assert user.role_accessed is True
    assert fake_session.closed is True