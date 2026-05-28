from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_endpoint_smoke() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_openapi_endpoint_smoke() -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    body = response.json()
    assert body["info"]["title"]
    assert "/auth/login" in body["paths"]


def test_login_invalid_credentials_smoke() -> None:
    response = client.post(
        "/auth/login",
        json={
            "username": "__smoke_missing_user__",
            "password": "__invalid_password__",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Username atau password tidak valid."


def test_reference_endpoint_requires_auth_smoke() -> None:
    response = client.get("/references/companies")

    assert response.status_code == 401
    assert response.json()["detail"] == "Bearer token wajib dikirim."
