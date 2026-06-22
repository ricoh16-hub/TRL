from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.bpjs import EmployeeBpjs
from app.models.employee import Employee
from app.models.employment import EmployeeAssignment, EmployeeStatusHistory
from app.schemas.manpower_schema import (
    ManpowerBreakdownItem,
    ManpowerCoverageResponse,
    ManpowerSummaryResponse,
)
from app.services.employee_service import _current_assignment, _current_status


@dataclass
class _Bucket:
    headcount: int = 0
    active: int = 0
    inactive: int = 0


def _employee_rows(session: Session) -> Iterable[Employee]:
    stmt = (
        select(Employee)
        .options(
            selectinload(Employee.assignments).joinedload(EmployeeAssignment.estate),
            selectinload(Employee.assignments).joinedload(EmployeeAssignment.division),
            selectinload(Employee.assignments).joinedload(EmployeeAssignment.category),
            selectinload(Employee.status_histories).joinedload(
                EmployeeStatusHistory.employment_status,
            ),
            selectinload(Employee.bpjs_records).joinedload(EmployeeBpjs.bpjs_type),
        )
        .order_by(Employee.full_name.asc(), Employee.employee_no.asc())
    )
    return session.scalars(stmt).all()


def _add_bucket(
    buckets: dict[tuple[str, str], _Bucket],
    *,
    key: str | None,
    label: str | None,
    active: bool,
) -> None:
    normalized_key = key or "__missing__"
    normalized_label = label or "Belum terisi"
    bucket = buckets[(normalized_key, normalized_label)]
    bucket.headcount += 1
    if active:
        bucket.active += 1
    else:
        bucket.inactive += 1


def _breakdown_response(buckets: dict[tuple[str, str], _Bucket]) -> list[ManpowerBreakdownItem]:
    rows = [
        ManpowerBreakdownItem(
            key=key,
            label=label,
            headcount=bucket.headcount,
            active=bucket.active,
            inactive=bucket.inactive,
        )
        for (key, label), bucket in buckets.items()
    ]
    return sorted(rows, key=lambda item: (-item.headcount, item.label))


def get_manpower_summary(session: Session) -> ManpowerSummaryResponse:
    employees = list(_employee_rows(session))
    status_buckets: dict[tuple[str, str], _Bucket] = defaultdict(_Bucket)
    estate_buckets: dict[tuple[str, str], _Bucket] = defaultdict(_Bucket)
    division_buckets: dict[tuple[str, str], _Bucket] = defaultdict(_Bucket)
    category_buckets: dict[tuple[str, str], _Bucket] = defaultdict(_Bucket)

    with_assignment = 0
    active_headcount = 0

    for employee in employees:
        active = bool(employee.is_active)
        if active:
            active_headcount += 1

        assignment = _current_assignment(employee)
        status = _current_status(employee)
        if assignment is not None:
            with_assignment += 1

        status_ref = status.employment_status if status else None
        _add_bucket(
            status_buckets,
            key=status_ref.code if status_ref else None,
            label=status_ref.name if status_ref else None,
            active=active,
        )
        _add_bucket(
            estate_buckets,
            key=str(assignment.estate_id) if assignment else None,
            label=assignment.estate.estate_name if assignment and assignment.estate else None,
            active=active,
        )
        _add_bucket(
            division_buckets,
            key=str(assignment.division_id) if assignment else None,
            label=assignment.division.division_name if assignment and assignment.division else None,
            active=active,
        )
        _add_bucket(
            category_buckets,
            key=str(assignment.category_id) if assignment else None,
            label=assignment.category.name if assignment and assignment.category else None,
            active=active,
        )

    total = len(employees)
    without_assignment = total - with_assignment
    coverage = round((with_assignment / total) * 100, 2) if total else 0.0

    return ManpowerSummaryResponse(
        total_headcount=total,
        active_headcount=active_headcount,
        inactive_headcount=total - active_headcount,
        status_breakdown=_breakdown_response(status_buckets),
        estate_breakdown=_breakdown_response(estate_buckets),
        division_breakdown=_breakdown_response(division_buckets),
        category_breakdown=_breakdown_response(category_buckets),
        coverage=ManpowerCoverageResponse(
            with_assignment=with_assignment,
            without_assignment=without_assignment,
            assignment_coverage=coverage,
        ),
    )


__all__ = ["get_manpower_summary"]
