import importlib
import os
import tempfile


def test_sqlite_engine_no_postgres_connect_args(monkeypatch, tmp_path):
    # Arrange: point DATABASE_URL to a local sqlite file and opt-in
    db_path = tmp_path / "test_sqlite.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("ALLOW_SQLITE_DEV", "1")

    # Act: import and reload the models module so it creates the engine with current env
    import src.database.models as models
    importlib.reload(models)

    # Assert: engine dialect is sqlite and a connection can be opened (no TypeError from bad connect_args)
    assert models.engine is not None
    assert models.engine.dialect.name in {"sqlite"}

    conn = models.engine.connect()
    conn.close()
