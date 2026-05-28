import importlib
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> TestClient:
    db_path = tmp_path / "api_smoke.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+pysqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-for-ci-only-32-bytes")
    monkeypatch.setenv("ENVIRONMENT", "test")

    for module_name in [
        "app.database.connection",
        "app.core.permissions",
        "app.services.auth_service",
        "app.main",
        "app.routers.auth_router",
        "app.routers.data_quality_router",
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


def test_data_quality_endpoint_requires_auth_smoke(client: TestClient) -> None:
    response = client.get("/data-quality/issues")

    assert response.status_code == 401
    assert response.json()["detail"] == "Bearer token wajib dikirim."


def test_authenticated_data_quality_workflow_smoke(client: TestClient) -> None:
    connection = importlib.import_module("app.database.connection")
    security = importlib.import_module("app.core.security")
    auth_models = importlib.import_module("app.models.auth")
    governance_models = importlib.import_module("app.models.governance")

    with connection.SessionLocal() as session:
        view_permission = auth_models.Permission(
            permission_id=1,
            module_name="data_quality",
            action_name="view",
            description="view data quality",
        )
        update_permission = auth_models.Permission(
            permission_id=2,
            module_name="data_quality",
            action_name="update",
            description="update data quality",
        )
        role = auth_models.Role(role_id=1, role_name="DQ_ADMIN", description=None)
        user = auth_models.User(
            user_id=1,
            username="dq_admin",
            password_hash=security.hash_password("secret-password"),
            failed_login_count=0,
            is_locked=False,
            is_active=True,
        )
        session.add_all(
            [
                view_permission,
                update_permission,
                role,
                user,
                auth_models.RolePermission(
                    role_permission_id=1,
                    role_id=1,
                    permission_id=1,
                ),
                auth_models.RolePermission(
                    role_permission_id=2,
                    role_id=1,
                    permission_id=2,
                ),
                auth_models.UserRole(user_role_id=1, user_id=1, role_id=1),
                governance_models.DataQualityIssue(
                    issue_id=1,
                    issue_key="AGE_REVIEW:1",
                    issue_code="AGE_REVIEW",
                    severity="REVIEW",
                    status="OPEN",
                    source_period="Maret 2026",
                    observed_value="1942-09-20 / 83 tahun",
                    recommendation="Verifikasi ulang tanggal lahir.",
                ),
            ]
        )
        session.commit()

    login_response = client.post(
        "/auth/login",
        json={"username": "dq_admin", "password": "secret-password"},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    summary_response = client.get("/data-quality/summary", headers=headers)
    assert summary_response.status_code == 200
    assert summary_response.json()["open_total"] == 1
    assert summary_response.json()["watch_total"] == 1

    update_response = client.patch(
        "/data-quality/issues/1",
        headers=headers,
        json={
            "status": "RESOLVED",
            "recommendation": "Sudah diverifikasi dengan dokumen HR.",
        },
    )

    assert update_response.status_code == 200
    body = update_response.json()
    assert body["status"] == "RESOLVED"
    assert body["resolved_at"] is not None
    assert body["recommendation"] == "Sudah diverifikasi dengan dokumen HR."
