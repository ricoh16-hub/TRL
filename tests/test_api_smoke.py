import importlib
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> TestClient:
    db_path = tmp_path / "api_smoke.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+pysqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-for-ci-only")
    monkeypatch.setenv("ENVIRONMENT", "test")

    for module_name in [
        "app.database.connection",
        "app.main",
        "app.routers.auth_router",
        "app.routers.reference_router",
        "app.routers.employee_router",
        "app.routers.attendance_router",
    ]:
        sys.modules.pop(module_name, None)

    config = importlib.import_module("app.core.config")
    config.get_settings.cache_clear()

    models = importlib.import_module("app.models")
    connection = importlib.import_module("app.database.connection")
    api = importlib.import_module("app.main").app

    assert models is not None
    connection.Base.metadata.create_all(bind=connection.engine)
    try:
        yield TestClient(api)
    finally:
        connection.Base.metadata.drop_all(bind=connection.engine)


def test_health_endpoint_smoke(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_openapi_endpoint_smoke(client: TestClient) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    body = response.json()
    assert body["info"]["title"]
    assert "/auth/login" in body["paths"]


def test_login_invalid_credentials_smoke(client: TestClient) -> None:
    response = client.post(
        "/auth/login",
        json={
            "username": "__smoke_missing_user__",
            "password": "__invalid_password__",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Username atau password tidak valid."


def test_reference_endpoint_requires_auth_smoke(client: TestClient) -> None:
    response = client.get("/references/companies")

    assert response.status_code == 401
    assert response.json()["detail"] == "Bearer token wajib dikirim."
