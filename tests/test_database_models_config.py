import pytest
from sqlalchemy.exc import OperationalError, ProgrammingError

from src.database import models as db_models


def test_resolve_database_url_prefers_database_url(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg2://user:pass@db:5432/app")

    url, source, error = db_models._resolve_database_url()

    assert url == "postgresql+psycopg2://user:pass@db:5432/app"
    assert source == "DATABASE_URL"
    assert error == ""


def test_resolve_database_url_rejects_placeholder_password(monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("DB_USER", "app_client")
    monkeypatch.setenv("DB_PASSWORD", "PASSWORD_POSTGRES_ANDA")

    url, source, error = db_models._resolve_database_url()

    assert url == ""
    assert source == "DB_*"
    assert "placeholder" in error


def test_resolve_database_url_raises_for_invalid_port(monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("DB_USER", "app_client")
    monkeypatch.setenv("DB_PASSWORD", "s3cret")
    monkeypatch.setenv("DB_PORT", "not-a-number")

    with pytest.raises(RuntimeError, match="DB_PORT harus berupa angka"):
        db_models._resolve_database_url()


def test_resolve_database_url_builds_from_db_components(monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("DB_USER", "app_client")
    monkeypatch.setenv("DB_PASSWORD", "s3cret")
    monkeypatch.setenv("DB_HOST", "127.0.0.5")
    monkeypatch.setenv("DB_PORT", "5432")
    monkeypatch.setenv("DB_NAME", "GBR")

    url, source, error = db_models._resolve_database_url()

    assert url.startswith("postgresql+psycopg2://app_client:s3cret@127.0.0.5:5432/GBR")
    assert source == "DB_*"
    assert error == ""


def test_build_connect_args_includes_ssl(monkeypatch) -> None:
    monkeypatch.setenv("DB_CONNECT_TIMEOUT", "12")
    monkeypatch.setenv("DB_APP_NAME", "unit-test")
    monkeypatch.setenv("DB_SSLMODE", "require")

    connect_args = db_models._build_connect_args()

    assert connect_args == {
        "connect_timeout": 12,
        "application_name": "unit-test",
        "sslmode": "require",
    }


def test_feature_toggles(monkeypatch) -> None:
    monkeypatch.setenv("DB_AUTO_MIGRATE", "1")
    monkeypatch.setenv("DB_CENTRAL_MODE", "true")
    monkeypatch.setenv("DB_CENTRAL_REQUIRE_SSL", "yes")

    assert db_models._auto_migrate_enabled() is True
    assert db_models._centralized_mode_enabled() is True
    assert db_models._centralized_ssl_required() is True


def test_masked_database_url_hides_password() -> None:
    masked = db_models._masked_database_url("postgresql+psycopg2://alice:secret@db:5432/app")

    assert "secret" not in masked
    assert "***" in masked


def test_validate_centralized_target_rejects_local_host(monkeypatch) -> None:
    monkeypatch.setenv("DB_CENTRAL_MODE", "1")
    monkeypatch.setattr(db_models, "DATABASE_URL", "postgresql+psycopg2://u:p@localhost:5432/app")

    with pytest.raises(RuntimeError, match="host masih lokal"):
        db_models._validate_centralized_database_target()


def test_validate_centralized_target_rejects_auto_migrate(monkeypatch) -> None:
    monkeypatch.setenv("DB_CENTRAL_MODE", "1")
    monkeypatch.setenv("DB_AUTO_MIGRATE", "1")
    monkeypatch.setattr(db_models, "DATABASE_URL", "postgresql+psycopg2://u:p@db-server:5432/app")

    with pytest.raises(RuntimeError, match="DB_AUTO_MIGRATE masih aktif"):
        db_models._validate_centralized_database_target()


def test_validate_centralized_target_requires_strict_ssl(monkeypatch) -> None:
    monkeypatch.setenv("DB_CENTRAL_MODE", "1")
    monkeypatch.setenv("DB_AUTO_MIGRATE", "0")
    monkeypatch.setenv("DB_CENTRAL_REQUIRE_SSL", "1")
    monkeypatch.setenv("DB_SSLMODE", "disable")
    monkeypatch.setattr(db_models, "DATABASE_URL", "postgresql+psycopg2://u:p@db-server:5432/app")

    with pytest.raises(RuntimeError, match="membutuhkan koneksi TLS"):
        db_models._validate_centralized_database_target()


def test_init_db_raises_when_config_error(monkeypatch) -> None:
    monkeypatch.setattr(db_models, "DATABASE_CONFIG_ERROR", "konfigurasi rusak")

    with pytest.raises(RuntimeError, match="konfigurasi rusak"):
        db_models.init_db()


def test_init_db_raises_when_database_not_configured(monkeypatch) -> None:
    monkeypatch.setattr(db_models, "DATABASE_CONFIG_ERROR", "")
    monkeypatch.setattr(db_models, "DATABASE_URL", "")
    monkeypatch.setattr(db_models, "engine", None)

    with pytest.raises(RuntimeError, match="Konfigurasi PostgreSQL belum lengkap"):
        db_models.init_db()


def test_test_connection_raises_when_database_not_configured(monkeypatch) -> None:
    monkeypatch.setattr(db_models, "DATABASE_URL", "")
    monkeypatch.setattr(db_models, "engine", None)

    with pytest.raises(RuntimeError, match="Konfigurasi PostgreSQL belum lengkap"):
        db_models.test_connection()


def test_resolve_database_url_returns_empty_when_not_configured(monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("DB_USER", raising=False)
    monkeypatch.delenv("DB_PASSWORD", raising=False)

    url, source, error = db_models._resolve_database_url()

    assert url == ""
    assert source == ""
    assert error == ""


def test_masked_database_url_invalid_returns_placeholder() -> None:
    masked = db_models._masked_database_url("not-a-valid-db-url")

    assert masked == "<DATABASE_URL tidak valid>"


def test_validate_centralized_target_rejects_invalid_url(monkeypatch) -> None:
    monkeypatch.setenv("DB_CENTRAL_MODE", "1")
    monkeypatch.setattr(db_models, "DATABASE_URL", "%%%")

    with pytest.raises(RuntimeError, match="DATABASE_URL tidak valid"):
        db_models._validate_centralized_database_target()


def test_validate_centralized_target_returns_when_mode_disabled(monkeypatch) -> None:
    monkeypatch.setenv("DB_CENTRAL_MODE", "0")
    monkeypatch.setattr(db_models, "DATABASE_URL", "postgresql+psycopg2://u:p@db-server:5432/app")

    db_models._validate_centralized_database_target()


def test_validate_centralized_target_rejects_empty_host(monkeypatch) -> None:
    monkeypatch.setenv("DB_CENTRAL_MODE", "1")
    monkeypatch.setattr(db_models, "DATABASE_URL", "postgresql+psycopg2://u:p@:5432/app")

    with pytest.raises(RuntimeError, match="DB_HOST wajib diisi"):
        db_models._validate_centralized_database_target()


def test_validate_centralized_target_allows_strict_ssl(monkeypatch) -> None:
    monkeypatch.setenv("DB_CENTRAL_MODE", "1")
    monkeypatch.setenv("DB_CENTRAL_REQUIRE_SSL", "1")
    monkeypatch.setenv("DB_AUTO_MIGRATE", "0")
    monkeypatch.setenv("DB_SSLMODE", "require")
    monkeypatch.setattr(db_models, "DATABASE_URL", "postgresql+psycopg2://u:p@db-server:5432/app")

    db_models._validate_centralized_database_target()


def test_validate_centralized_target_allows_when_ssl_not_required(monkeypatch) -> None:
    monkeypatch.setenv("DB_CENTRAL_MODE", "1")
    monkeypatch.setenv("DB_CENTRAL_REQUIRE_SSL", "0")
    monkeypatch.setenv("DB_AUTO_MIGRATE", "0")
    monkeypatch.setattr(db_models, "DATABASE_URL", "postgresql+psycopg2://u:p@db-server:5432/app")

    db_models._validate_centralized_database_target()


class _FakeSelectResult:
    def mappings(self):
        return self

    def all(self):
        return [{"id": 1, "password": "legacy"}]


class _FakeConnection:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object] | None]] = []

    def execute(self, statement, params=None):
        sql = str(statement)
        self.calls.append((sql, params))
        if "SELECT id, password FROM users" in sql:
            return _FakeSelectResult()
        return None


class _FakeBeginContext:
    def __init__(self, connection: _FakeConnection) -> None:
        self.connection = connection

    def __enter__(self):
        return self.connection

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeEngine:
    def __init__(self) -> None:
        self.connection = _FakeConnection()

    def begin(self):
        return _FakeBeginContext(self.connection)


def test_run_user_table_migration_updates_legacy_passwords(monkeypatch) -> None:
    fake_engine = _FakeEngine()

    class _Inspector:
        @staticmethod
        def get_table_names():
            return ["users"]

        @staticmethod
        def get_columns(_table):
            return [{"name": "id"}, {"name": "password"}]

    monkeypatch.setattr(db_models, "engine", fake_engine)
    monkeypatch.setattr(db_models, "inspect", lambda _engine: _Inspector())
    monkeypatch.setattr(db_models, "create_password_hash", lambda _pwd: ("salt", "hash"))

    db_models._run_user_table_migration()

    executed_sql = "\n".join(sql for sql, _ in fake_engine.connection.calls)
    assert "ADD COLUMN password_hash" in executed_sql
    assert "ADD COLUMN password_salt" in executed_sql
    assert "ALTER COLUMN password DROP NOT NULL" in executed_sql
    assert "UPDATE users" in executed_sql


def test_run_user_table_migration_returns_when_engine_none(monkeypatch) -> None:
    monkeypatch.setattr(db_models, "engine", None)

    db_models._run_user_table_migration()


def test_run_user_table_migration_returns_when_users_table_missing(monkeypatch) -> None:
    fake_engine = _FakeEngine()

    class _Inspector:
        @staticmethod
        def get_table_names():
            return ["other_table"]

        @staticmethod
        def get_columns(_table):
            return [{"name": "id"}]

    monkeypatch.setattr(db_models, "engine", fake_engine)
    monkeypatch.setattr(db_models, "inspect", lambda _engine: _Inspector())

    db_models._run_user_table_migration()

    assert fake_engine.connection.calls == []


def test_run_user_table_migration_skips_column_alterations_when_columns_exist(monkeypatch) -> None:
    class _EmptySelectResult:
        def mappings(self):
            return self

        def all(self):
            return []

    class _Conn:
        def __init__(self) -> None:
            self.calls: list[tuple[str, dict[str, object] | None]] = []

        def execute(self, statement, params=None):
            sql = str(statement)
            self.calls.append((sql, params))
            if "SELECT id, password FROM users" in sql:
                return _EmptySelectResult()
            return None

    class _Begin:
        def __init__(self, conn: _Conn) -> None:
            self._conn = conn

        def __enter__(self):
            return self._conn

        def __exit__(self, exc_type, exc, tb):
            return False

    class _Engine:
        def __init__(self) -> None:
            self.connection = _Conn()

        def begin(self):
            return _Begin(self.connection)

    class _Inspector:
        @staticmethod
        def get_table_names():
            return ["users"]

        @staticmethod
        def get_columns(_table):
            return [
                {"name": "id"},
                {"name": "password"},
                {"name": "password_hash"},
                {"name": "password_salt"},
            ]

    fake_engine = _Engine()
    monkeypatch.setattr(db_models, "engine", fake_engine)
    monkeypatch.setattr(db_models, "inspect", lambda _engine: _Inspector())

    db_models._run_user_table_migration()

    executed_sql = "\n".join(sql for sql, _ in fake_engine.connection.calls)
    assert "ADD COLUMN password_hash" not in executed_sql
    assert "ADD COLUMN password_salt" not in executed_sql
    assert "ALTER COLUMN password DROP NOT NULL" in executed_sql


def test_run_user_table_migration_skips_empty_password(monkeypatch) -> None:
    class _SelectResult:
        def mappings(self):
            return self

        def all(self):
            return [{"id": 1, "password": ""}]

    class _Conn:
        def __init__(self) -> None:
            self.calls: list[tuple[str, dict[str, object] | None]] = []

        def execute(self, statement, params=None):
            sql = str(statement)
            self.calls.append((sql, params))
            if "SELECT id, password FROM users" in sql:
                return _SelectResult()
            return None

    class _Begin:
        def __init__(self, conn: _Conn) -> None:
            self._conn = conn

        def __enter__(self):
            return self._conn

        def __exit__(self, exc_type, exc, tb):
            return False

    class _Engine:
        def __init__(self) -> None:
            self.connection = _Conn()

        def begin(self):
            return _Begin(self.connection)

    class _Inspector:
        @staticmethod
        def get_table_names():
            return ["users"]

        @staticmethod
        def get_columns(_table):
            return [{"name": "id"}, {"name": "password"}]

    fake_engine = _Engine()
    monkeypatch.setattr(db_models, "engine", fake_engine)
    monkeypatch.setattr(db_models, "inspect", lambda _engine: _Inspector())
    monkeypatch.setattr(db_models, "create_password_hash", lambda _pwd: ("salt", "hash"))

    db_models._run_user_table_migration()

    executed_sql = "\n".join(sql for sql, _ in fake_engine.connection.calls)
    assert "UPDATE users" not in executed_sql


def test_run_user_table_migration_skips_password_nullable_change_when_column_missing(monkeypatch) -> None:
    class _EmptySelectResult:
        def mappings(self):
            return self

        def all(self):
            return []

    class _Conn:
        def __init__(self) -> None:
            self.calls: list[tuple[str, dict[str, object] | None]] = []

        def execute(self, statement, params=None):
            sql = str(statement)
            self.calls.append((sql, params))
            if "SELECT id, password FROM users" in sql:
                return _EmptySelectResult()
            return None

    class _Begin:
        def __init__(self, conn: _Conn) -> None:
            self._conn = conn

        def __enter__(self):
            return self._conn

        def __exit__(self, exc_type, exc, tb):
            return False

    class _Engine:
        def __init__(self) -> None:
            self.connection = _Conn()

        def begin(self):
            return _Begin(self.connection)

    class _Inspector:
        @staticmethod
        def get_table_names():
            return ["users"]

        @staticmethod
        def get_columns(_table):
            return [{"name": "id"}, {"name": "password_hash"}, {"name": "password_salt"}]

    fake_engine = _Engine()
    monkeypatch.setattr(db_models, "engine", fake_engine)
    monkeypatch.setattr(db_models, "inspect", lambda _engine: _Inspector())

    db_models._run_user_table_migration()

    executed_sql = "\n".join(sql for sql, _ in fake_engine.connection.calls)
    assert "ALTER COLUMN password DROP NOT NULL" not in executed_sql


def test_init_db_handles_password_auth_failed(monkeypatch) -> None:
    monkeypatch.setattr(db_models, "DATABASE_CONFIG_ERROR", "")
    monkeypatch.setattr(db_models, "DATABASE_CONFIG_SOURCE", "DB_*")
    monkeypatch.setattr(db_models, "DATABASE_URL", "postgresql+psycopg2://u:p@db:5432/app")
    monkeypatch.setattr(db_models, "engine", object())
    monkeypatch.setattr(db_models, "_validate_centralized_database_target", lambda: None)
    monkeypatch.setattr(
        db_models,
        "test_connection",
        lambda: (_ for _ in ()).throw(
            OperationalError("SELECT 1", {}, Exception("password authentication failed for user"))
        ),
    )

    with pytest.raises(RuntimeError, match="username/password salah"):
        db_models.init_db()


def test_init_db_handles_programming_error(monkeypatch) -> None:
    monkeypatch.setattr(db_models, "DATABASE_CONFIG_ERROR", "")
    monkeypatch.setattr(db_models, "DATABASE_URL", "postgresql+psycopg2://u:p@db:5432/app")
    monkeypatch.setattr(db_models, "engine", object())
    monkeypatch.setattr(db_models, "_validate_centralized_database_target", lambda: None)
    monkeypatch.setattr(
        db_models,
        "test_connection",
        lambda: (_ for _ in ()).throw(ProgrammingError("SELECT 1", {}, Exception("permission denied"))),
    )

    with pytest.raises(RuntimeError, match="Migrasi schema membutuhkan privilege owner/admin"):
        db_models.init_db()


def test_init_db_handles_generic_operational_error(monkeypatch) -> None:
    monkeypatch.setattr(db_models, "DATABASE_CONFIG_ERROR", "")
    monkeypatch.setattr(db_models, "DATABASE_CONFIG_SOURCE", "DB_*")
    monkeypatch.setattr(db_models, "DATABASE_URL", "postgresql+psycopg2://u:p@db:5432/app")
    monkeypatch.setattr(db_models, "engine", object())
    monkeypatch.setattr(db_models, "_validate_centralized_database_target", lambda: None)
    monkeypatch.setattr(
        db_models,
        "test_connection",
        lambda: (_ for _ in ()).throw(OperationalError("SELECT 1", {}, Exception("connection refused"))),
    )

    with pytest.raises(RuntimeError, match="Koneksi PostgreSQL gagal"):
        db_models.init_db()


def test_init_db_runs_create_all_and_migration_when_enabled(monkeypatch) -> None:
    called = {"create_all": False, "migrate": False}

    monkeypatch.setattr(db_models, "DATABASE_CONFIG_ERROR", "")
    monkeypatch.setattr(db_models, "DATABASE_URL", "postgresql+psycopg2://u:p@db:5432/app")
    monkeypatch.setattr(db_models, "engine", object())
    monkeypatch.setattr(db_models, "_validate_centralized_database_target", lambda: None)
    monkeypatch.setattr(db_models, "test_connection", lambda: True)
    monkeypatch.setattr(db_models, "_auto_migrate_enabled", lambda: True)
    monkeypatch.setattr(
        db_models.Base.metadata,
        "create_all",
        lambda *, bind: called.__setitem__("create_all", bind is not None),
    )
    monkeypatch.setattr(
        db_models,
        "_run_user_table_migration",
        lambda: called.__setitem__("migrate", True),
    )

    db_models.init_db()

    assert called["create_all"] is True
    assert called["migrate"] is True


def test_init_db_skips_auto_migration_when_disabled(monkeypatch) -> None:
    called = {"create_all": False, "migrate": False}

    monkeypatch.setattr(db_models, "DATABASE_CONFIG_ERROR", "")
    monkeypatch.setattr(db_models, "DATABASE_URL", "postgresql+psycopg2://u:p@db:5432/app")
    monkeypatch.setattr(db_models, "engine", object())
    monkeypatch.setattr(db_models, "_validate_centralized_database_target", lambda: None)
    monkeypatch.setattr(db_models, "test_connection", lambda: True)
    monkeypatch.setattr(db_models, "_auto_migrate_enabled", lambda: False)
    monkeypatch.setattr(
        db_models.Base.metadata,
        "create_all",
        lambda *, bind: called.__setitem__("create_all", bind is not None),
    )
    monkeypatch.setattr(
        db_models,
        "_run_user_table_migration",
        lambda: called.__setitem__("migrate", True),
    )

    db_models.init_db()

    assert called["create_all"] is False
    assert called["migrate"] is False


def test_test_connection_success(monkeypatch) -> None:
    class _Conn:
        def __init__(self) -> None:
            self.executed: list[str] = []

        def execute(self, statement):
            self.executed.append(str(statement))

    class _Context:
        def __init__(self, conn: _Conn) -> None:
            self._conn = conn

        def __enter__(self):
            return self._conn

        def __exit__(self, exc_type, exc, tb):
            return False

    class _Engine:
        def __init__(self) -> None:
            self.conn = _Conn()

        def connect(self):
            return _Context(self.conn)

    engine = _Engine()
    monkeypatch.setattr(db_models, "DATABASE_URL", "postgresql+psycopg2://u:p@db:5432/app")
    monkeypatch.setattr(db_models, "engine", engine)

    assert db_models.test_connection() is True
    assert engine.conn.executed == ["SELECT 1"]