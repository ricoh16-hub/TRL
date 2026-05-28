from __future__ import annotations

from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.models.attendance import EmployeeAttendanceDaily, EmployeeWorkOutput
from app.models.employee import Employee
from app.models.reference import AttendanceCode, JobFamily
from app.schemas.attendance_schema import AttendanceCreate, WorkOutputCreate
from app.services import attendance_service


class FakeSession:
    def __init__(self) -> None:
        self.employee = Employee(employee_id=10, employee_no="E-10", full_name="Alice", is_active=True)
        self.code = AttendanceCode(id=2, code="H", name="Hadir", hk_value=Decimal("1"))
        self.job_family = JobFamily(id=3, code="PANEN", name="Panen")
        self.added: list[object] = []
        self.flushed = False

    def get(self, model, key):
        if model is Employee and key == self.employee.employee_id:
            return self.employee
        if model is AttendanceCode and key == self.code.id:
            return self.code
        if model is JobFamily and key == self.job_family.id:
            return self.job_family
        return None

    def scalar(self, _statement):
        return None

    def add(self, record: object) -> None:
        self.added.append(record)
        if isinstance(record, EmployeeAttendanceDaily):
            record.attendance_id = 100
            record.attendance_code = self.code
        if isinstance(record, EmployeeWorkOutput):
            record.work_output_id = 200
            record.job_family = self.job_family

    def flush(self) -> None:
        self.flushed = True

    def refresh(self, _record: object, attribute_names=None) -> None:
        return None


def test_create_attendance_writes_audit_with_masked_payload(monkeypatch) -> None:
    fake_session = FakeSession()
    audit_calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        attendance_service.audit_service,
        "create_audit_log",
        lambda _session, **kwargs: audit_calls.append(kwargs),
    )

    response = attendance_service.create_attendance(
        fake_session,
        AttendanceCreate(
            employee_id=10,
            attendance_code_id=2,
            attendance_date=date(2026, 5, 27),
            work_hours=Decimal("7"),
        ),
        user_id=7,
        ip_address="10.0.0.1",
    )

    assert response.attendance_id == 100
    assert response.attendance_code == "H"
    assert response.hk_value == Decimal("1")
    assert fake_session.flushed is True
    assert audit_calls[0]["module_name"] == "attendance"
    assert audit_calls[0]["user_id"] == 7


def test_create_work_output_validates_job_family_and_audits(monkeypatch) -> None:
    fake_session = FakeSession()
    audit_calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        attendance_service.audit_service,
        "create_audit_log",
        lambda _session, **kwargs: audit_calls.append(kwargs),
    )

    response = attendance_service.create_work_output(
        fake_session,
        WorkOutputCreate(
            employee_id=10,
            job_family_id=3,
            work_date=date(2026, 5, 27),
            activity_name="Panen TBS",
            quantity=Decimal("1234.5"),
            unit_name="kg",
        ),
    )

    assert response.work_output_id == 200
    assert response.job_family == "Panen"
    assert response.quantity == Decimal("1234.5")
    assert audit_calls[0]["module_name"] == "work_output"


def test_create_attendance_rejects_missing_employee() -> None:
    fake_session = FakeSession()

    with pytest.raises(attendance_service.AttendanceValidationError):
        attendance_service.create_attendance(
            fake_session,
            {"employee_id": 999, "attendance_code_id": 2, "attendance_date": date(2026, 5, 27)},
        )


class SummarySession:
    def __init__(self) -> None:
        self.present_code = SimpleNamespace(code="H", hk_value=Decimal("1"))
        self.absent_code = SimpleNamespace(code="A", hk_value=Decimal("0"))
        self.rows = [
            (
                SimpleNamespace(work_hours=Decimal("7"), overtime_hours=Decimal("1")),
                self.present_code,
            ),
            (
                SimpleNamespace(work_hours=Decimal("0"), overtime_hours=Decimal("0")),
                self.absent_code,
            ),
        ]

    def execute(self, _statement):
        return self

    def all(self):
        return self.rows

    def scalar(self, _statement):
        return 3


def test_summarize_attendance_calculates_hk_and_absent_gap() -> None:
    summary = attendance_service.summarize_attendance(
        SummarySession(),
        start_date=date(2026, 5, 1),
        end_date=date(2026, 5, 31),
    )

    assert summary.records == 2
    assert summary.present == 1
    assert summary.exception == 1
    assert summary.absent == 1
    assert summary.total_hk == Decimal("1")
    assert summary.work_hours == Decimal("7")
    assert summary.overtime_hours == Decimal("1")
