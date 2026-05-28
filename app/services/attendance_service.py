from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date
from decimal import Decimal
from typing import Any

from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.attendance import EmployeeAttendanceDaily, EmployeeWorkOutput
from app.models.employee import Employee
from app.models.reference import AttendanceCode, JobFamily
from app.schemas.attendance_schema import (
    AttendanceCreate,
    AttendanceResponse,
    AttendanceSummaryResponse,
    WorkOutputCreate,
    WorkOutputResponse,
)
from app.services import audit_service

Payload = Mapping[str, Any] | BaseModel
PRESENT_CODES = {"H", "PRESENT", "HADIR"}
EXCEPTION_CODES = {"I", "IZIN", "S", "SAKIT", "CT", "CUTI", "A", "ALPA", "ABSENT"}


class AttendanceServiceError(Exception):
    """Base exception for attendance service failures."""


class AttendanceValidationError(AttendanceServiceError):
    """Raised when attendance/work output input is invalid."""


class AttendanceConflictError(AttendanceServiceError):
    """Raised when a unique attendance record already exists."""


def _payload_to_dict(payload: Payload) -> dict[str, Any]:
    if isinstance(payload, BaseModel):
        return payload.model_dump()
    return dict(payload)


def _snapshot(instance: Any) -> dict[str, Any]:
    return {column.name: getattr(instance, column.name) for column in instance.__table__.columns}


def _require_employee(session: Session, employee_id: int) -> Employee:
    employee = session.get(Employee, employee_id)
    if employee is None:
        raise AttendanceValidationError(f"Employee {employee_id} tidak ditemukan.")
    return employee


def _require_attendance_code(session: Session, attendance_code_id: int) -> AttendanceCode:
    code = session.get(AttendanceCode, attendance_code_id)
    if code is None:
        raise AttendanceValidationError(f"Attendance code {attendance_code_id} tidak ditemukan.")
    return code


def _require_job_family(session: Session, job_family_id: int | None) -> JobFamily | None:
    if job_family_id is None:
        return None
    job_family = session.get(JobFamily, job_family_id)
    if job_family is None:
        raise AttendanceValidationError(f"Job family {job_family_id} tidak ditemukan.")
    return job_family


def _attendance_response(record: EmployeeAttendanceDaily) -> AttendanceResponse:
    code = record.attendance_code
    return AttendanceResponse(
        attendance_id=record.attendance_id,
        employee_id=record.employee_id,
        attendance_code_id=record.attendance_code_id,
        attendance_code=code.code if code else None,
        attendance_date=record.attendance_date,
        hk_value=code.hk_value if code else Decimal("0"),
        work_hours=record.work_hours,
        overtime_hours=record.overtime_hours,
        notes=record.notes,
        created_at=record.created_at,
    )


def _work_output_response(record: EmployeeWorkOutput) -> WorkOutputResponse:
    return WorkOutputResponse(
        work_output_id=record.work_output_id,
        employee_id=record.employee_id,
        job_family_id=record.job_family_id,
        job_family=record.job_family.name if record.job_family else None,
        work_date=record.work_date,
        work_group_code=record.work_group_code,
        activity_name=record.activity_name,
        quantity=record.quantity,
        unit_name=record.unit_name,
        notes=record.notes,
        created_at=record.created_at,
    )


def create_attendance(
    session: Session,
    payload: AttendanceCreate | Payload,
    *,
    user_id: int | None = None,
    ip_address: str | None = None,
) -> AttendanceResponse:
    values = _payload_to_dict(payload)
    employee_id = int(values["employee_id"])
    attendance_date = values["attendance_date"]
    _require_employee(session, employee_id)
    _require_attendance_code(session, int(values["attendance_code_id"]))

    existing = session.scalar(
        select(EmployeeAttendanceDaily).where(
            EmployeeAttendanceDaily.employee_id == employee_id,
            EmployeeAttendanceDaily.attendance_date == attendance_date,
        )
    )
    if existing is not None:
        raise AttendanceConflictError("Absensi employee pada tanggal tersebut sudah ada.")

    record = EmployeeAttendanceDaily(**values)
    session.add(record)
    session.flush()
    session.refresh(record, attribute_names=["attendance_code"])
    audit_service.create_audit_log(
        session,
        module_name="attendance",
        action_name="create",
        table_name="employee_attendance_daily",
        record_id=record.attendance_id,
        new_data=_snapshot(record),
        user_id=user_id,
        ip_address=ip_address,
    )
    return _attendance_response(record)


def list_attendance(
    session: Session,
    *,
    start_date: date,
    end_date: date,
    employee_id: int | None = None,
    limit: int = 200,
) -> list[AttendanceResponse]:
    stmt = (
        select(EmployeeAttendanceDaily)
        .where(
            EmployeeAttendanceDaily.attendance_date >= start_date,
            EmployeeAttendanceDaily.attendance_date <= end_date,
        )
        .options(joinedload(EmployeeAttendanceDaily.attendance_code))
        .order_by(EmployeeAttendanceDaily.attendance_date.desc(), EmployeeAttendanceDaily.attendance_id.desc())
        .limit(limit)
    )
    if employee_id is not None:
        stmt = stmt.where(EmployeeAttendanceDaily.employee_id == employee_id)
    return [_attendance_response(record) for record in session.scalars(stmt).all()]


def summarize_attendance(
    session: Session,
    *,
    start_date: date,
    end_date: date,
    employee_id: int | None = None,
) -> AttendanceSummaryResponse:
    stmt = (
        select(EmployeeAttendanceDaily, AttendanceCode)
        .join(AttendanceCode, AttendanceCode.id == EmployeeAttendanceDaily.attendance_code_id)
        .where(
            EmployeeAttendanceDaily.attendance_date >= start_date,
            EmployeeAttendanceDaily.attendance_date <= end_date,
        )
    )
    if employee_id is not None:
        stmt = stmt.where(EmployeeAttendanceDaily.employee_id == employee_id)

    rows: Sequence[tuple[EmployeeAttendanceDaily, AttendanceCode]] = session.execute(stmt).all()
    present = 0
    exception = 0
    total_hk = Decimal("0")
    work_hours = Decimal("0")
    overtime_hours = Decimal("0")
    for record, code in rows:
        normalized_code = (code.code or "").strip().upper()
        if normalized_code in PRESENT_CODES or code.hk_value > 0:
            present += 1
        if normalized_code in EXCEPTION_CODES and code.hk_value <= 0:
            exception += 1
        total_hk += code.hk_value or Decimal("0")
        work_hours += record.work_hours or Decimal("0")
        overtime_hours += record.overtime_hours or Decimal("0")

    active_employee_count = int(session.scalar(select(func.count()).select_from(Employee).where(Employee.is_active.is_(True))) or 0)
    records = len(rows)
    absent = max(active_employee_count - records, 0) if employee_id is None else 0
    return AttendanceSummaryResponse(
        period_start=start_date,
        period_end=end_date,
        records=records,
        present=present,
        exception=exception,
        absent=absent,
        total_hk=total_hk,
        work_hours=work_hours,
        overtime_hours=overtime_hours,
    )


def create_work_output(
    session: Session,
    payload: WorkOutputCreate | Payload,
    *,
    user_id: int | None = None,
    ip_address: str | None = None,
) -> WorkOutputResponse:
    values = _payload_to_dict(payload)
    _require_employee(session, int(values["employee_id"]))
    _require_job_family(session, values.get("job_family_id"))

    record = EmployeeWorkOutput(**values)
    session.add(record)
    session.flush()
    if record.job_family_id is not None:
        session.refresh(record, attribute_names=["job_family"])
    audit_service.create_audit_log(
        session,
        module_name="work_output",
        action_name="create",
        table_name="employee_work_outputs",
        record_id=record.work_output_id,
        new_data=_snapshot(record),
        user_id=user_id,
        ip_address=ip_address,
    )
    return _work_output_response(record)


def list_work_outputs(
    session: Session,
    *,
    start_date: date,
    end_date: date,
    employee_id: int | None = None,
    limit: int = 200,
) -> list[WorkOutputResponse]:
    stmt = (
        select(EmployeeWorkOutput)
        .where(
            EmployeeWorkOutput.work_date >= start_date,
            EmployeeWorkOutput.work_date <= end_date,
        )
        .options(joinedload(EmployeeWorkOutput.job_family))
        .order_by(EmployeeWorkOutput.work_date.desc(), EmployeeWorkOutput.work_output_id.desc())
        .limit(limit)
    )
    if employee_id is not None:
        stmt = stmt.where(EmployeeWorkOutput.employee_id == employee_id)
    return [_work_output_response(record) for record in session.scalars(stmt).all()]


__all__ = [
    "AttendanceConflictError",
    "AttendanceServiceError",
    "AttendanceValidationError",
    "create_attendance",
    "create_work_output",
    "list_attendance",
    "list_work_outputs",
    "summarize_attendance",
]
