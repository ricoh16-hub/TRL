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