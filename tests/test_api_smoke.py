import importlib
import sys
from datetime import date
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
        "app.routers.manpower_router",
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
    data_quality_router = importlib.import_module("app.routers.data_quality_router")
    audit_calls: list[dict[str, object]] = []

    def fake_audit_log(_session, **kwargs):
        audit_calls.append(kwargs)
        return None

    data_quality_router.audit_service.create_audit_log = fake_audit_log

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
                governance_models.DataQualityIssue(
                    issue_id=2,
                    issue_key="MISSING_BPJS:2",
                    issue_code="MISSING_BPJS",
                    severity="INFO",
                    status="OPEN",
                    source_period="April 2026",
                    observed_value="BPJS kosong",
                    recommendation="Lengkapi nomor BPJS.",
                ),
                governance_models.DataQualityIssue(
                    issue_id=3,
                    issue_key="AGE_REVIEW:3",
                    issue_code="AGE_REVIEW",
                    severity="REVIEW",
                    status="RESOLVED",
                    source_period="April 2026",
                    observed_value="1950-01-01 / 76 tahun",
                    recommendation="Sudah diverifikasi.",
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
    summary_body = summary_response.json()
    assert summary_body["status"] == "OPEN"
    assert summary_body["total"] == 2
    assert summary_body["open_total"] == 2
    assert summary_body["watch_total"] == 1
    assert summary_body["by_severity"] == {"INFO": 1, "REVIEW": 1}

    period_summary_response = client.get(
        "/data-quality/summary",
        headers=headers,
        params={"source_period": "Maret 2026"},
    )
    assert period_summary_response.status_code == 200
    period_summary_body = period_summary_response.json()
    assert period_summary_body["source_period"] == "Maret 2026"
    assert period_summary_body["total"] == 1
    assert period_summary_body["open_total"] == 1
    assert period_summary_body["by_code"] == {"AGE_REVIEW": 1}

    resolved_summary_response = client.get(
        "/data-quality/summary",
        headers=headers,
        params={"status": "RESOLVED", "severity": "REVIEW"},
    )
    assert resolved_summary_response.status_code == 200
    resolved_summary_body = resolved_summary_response.json()
    assert resolved_summary_body["status"] == "RESOLVED"
    assert resolved_summary_body["severity"] == "REVIEW"
    assert resolved_summary_body["total"] == 1
    assert resolved_summary_body["open_total"] == 0
    assert resolved_summary_body["by_code"] == {"AGE_REVIEW": 1}

    period_issues_response = client.get(
        "/data-quality/issues",
        headers=headers,
        params={"source_period": "Maret 2026"},
    )
    assert period_issues_response.status_code == 200
    period_issues_body = period_issues_response.json()
    assert [issue["issue_id"] for issue in period_issues_body] == [1]

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
    assert len(audit_calls) == 1
    audit_call = audit_calls[0]
    assert audit_call["user_id"] == 1
    assert audit_call["module_name"] == "data_quality"
    assert audit_call["action_name"] == "update_issue"
    assert audit_call["table_name"] == "data_quality_issues"
    assert audit_call["record_id"] == 1
    assert audit_call["ip_address"] == "testclient"

    old_data = audit_call["old_data"]
    new_data = audit_call["new_data"]
    assert old_data["status"] == "OPEN"
    assert old_data["recommendation"] == "Verifikasi ulang tanggal lahir."
    assert old_data["resolved_at"] is None
    assert new_data["status"] == "RESOLVED"
    assert new_data["recommendation"] == "Sudah diverifikasi dengan dokumen HR."
    assert new_data["resolved_at"] is not None


def test_authenticated_manpower_summary_and_employee_page_smoke(client: TestClient) -> None:
    connection = importlib.import_module("app.database.connection")
    security = importlib.import_module("app.core.security")
    auth_models = importlib.import_module("app.models.auth")
    employee_models = importlib.import_module("app.models.employee")
    employment_models = importlib.import_module("app.models.employment")
    organization_models = importlib.import_module("app.models.organization")
    reference_models = importlib.import_module("app.models.reference")

    with connection.SessionLocal() as session:
        employee_view = auth_models.Permission(
            permission_id=10,
            module_name="employee",
            action_name="view",
            description="view employees",
        )
        manpower_view = auth_models.Permission(
            permission_id=11,
            module_name="manpower",
            action_name="view",
            description="view manpower",
        )
        role = auth_models.Role(role_id=10, role_name="HR_VIEW", description=None)
        user = auth_models.User(
            user_id=10,
            username="hr_view",
            password_hash=security.hash_password("secret-password"),
            failed_login_count=0,
            is_locked=False,
            is_active=True,
        )
        company = organization_models.Company(
            company_id=10,
            company_code="GBR",
            company_name="PT GBR",
            is_active=True,
        )
        estate = organization_models.Estate(
            estate_id=10,
            company_id=10,
            estate_code="EST-1",
            estate_name="Estate 1",
            is_active=True,
        )
        division = organization_models.Division(
            division_id=10,
            estate_id=10,
            division_code="DIV-1",
            division_name="Divisi 1",
            is_active=True,
        )
        category = reference_models.EmployeeCategory(
            id=10,
            code="SKU",
            name="PHT/SKU",
            is_active=True,
        )
        status = reference_models.EmploymentStatus(
            id=10,
            code="AKTIF",
            name="Aktif",
            is_active=True,
        )
        job_family = reference_models.JobFamily(
            id=10,
            code="PANEN",
            name="Panen",
            is_active=True,
        )
        position = organization_models.Position(
            position_id=10,
            job_family_id=10,
            position_code="P-1",
            position_name="Pemanen",
            level_order=1,
            is_staff=False,
            is_active=True,
        )
        employee = employee_models.Employee(
            employee_id=10,
            employee_no="EMP-10",
            full_name="Alice Staff",
            is_active=True,
        )
        session.add_all(
            [
                employee_view,
                manpower_view,
                role,
                user,
                auth_models.RolePermission(
                    role_permission_id=10,
                    role_id=10,
                    permission_id=10,
                ),
                auth_models.RolePermission(
                    role_permission_id=11,
                    role_id=10,
                    permission_id=11,
                ),
                auth_models.UserRole(user_role_id=10, user_id=10, role_id=10),
                company,
                estate,
                division,
                category,
                status,
                job_family,
                position,
                employee,
                employment_models.EmployeeAssignment(
                    assignment_id=10,
                    employee_id=10,
                    estate_id=10,
                    division_id=10,
                    position_id=10,
                    category_id=10,
                    start_date=date(2026, 5, 1),
                    is_current=True,
                ),
                employment_models.EmployeeStatusHistory(
                    status_history_id=10,
                    employee_id=10,
                    employment_status_id=10,
                    effective_date=date(2026, 5, 1),
                ),
            ]
        )
        session.commit()

    login_response = client.post(
        "/auth/login",
        json={"username": "hr_view", "password": "secret-password"},
    )
    assert login_response.status_code == 200
    headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

    employee_response = client.get("/employees", headers=headers)
    assert employee_response.status_code == 200
    employee_body = employee_response.json()
    assert employee_body["total"] == 1
    assert employee_body["page"] == 1
    assert employee_body["pages"] == 1
    assert employee_body["items"][0]["employee_no"] == "EMP-10"

    manpower_response = client.get("/manpower/summary", headers=headers)
    assert manpower_response.status_code == 200
    manpower_body = manpower_response.json()
    assert manpower_body["total_headcount"] == 1
    assert manpower_body["active_headcount"] == 1
    assert manpower_body["coverage"]["assignment_coverage"] == 100
    assert manpower_body["estate_breakdown"][0]["label"] == "Estate 1"
