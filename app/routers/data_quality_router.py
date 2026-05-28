from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.permissions import require_permission
from app.database.connection import get_db
from app.models.auth import User
from app.models.employee import Employee
from app.models.governance import DataQualityIssue
from app.schemas.governance_schema import (
    DataQualityIssueResponse,
    DataQualityIssueUpdateRequest,
    DataQualitySummaryResponse,
)

router = APIRouter(
    prefix="/data-quality",
    tags=["data-quality"],
    dependencies=[Depends(require_permission("data_quality", "view"))],
)

DbSession = Annotated[Session, Depends(get_db)]
IssueId = Annotated[int, Path(gt=0)]
DataQualityUpdater = Annotated[User, Depends(require_permission("data_quality", "update"))]


def _issue_response(issue: DataQualityIssue) -> DataQualityIssueResponse:
    employee = issue.employee
    return DataQualityIssueResponse(
        issue_id=issue.issue_id,
        issue_key=issue.issue_key,
        issue_code=issue.issue_code,
        severity=issue.severity,
        status=issue.status,
        employee_id=issue.employee_id,
        employee_no=employee.employee_no if employee else None,
        full_name=employee.full_name if employee else None,
        source_period=issue.source_period,
        source_reference=issue.source_reference,
        observed_value=issue.observed_value,
        recommendation=issue.recommendation,
        first_seen_at=issue.first_seen_at,
        last_seen_at=issue.last_seen_at,
        resolved_at=issue.resolved_at,
    )


@router.get("/issues", response_model=list[DataQualityIssueResponse])
def get_data_quality_issues(
    db: DbSession,
    status: Annotated[str | None, Query(max_length=16)] = "OPEN",
    severity: Annotated[str | None, Query(max_length=16)] = None,
    issue_code: Annotated[str | None, Query(max_length=64)] = None,
    source_period: Annotated[str | None, Query(max_length=32)] = None,
    employee_id: Annotated[int | None, Query(gt=0)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[DataQualityIssueResponse]:
    stmt = select(DataQualityIssue).outerjoin(Employee).order_by(
        DataQualityIssue.severity.desc(),
        DataQualityIssue.issue_code.asc(),
        Employee.employee_no.asc(),
        DataQualityIssue.issue_id.asc(),
    )
    if status:
        stmt = stmt.where(DataQualityIssue.status == status.upper())
    if severity:
        stmt = stmt.where(DataQualityIssue.severity == severity.upper())
    if issue_code:
        stmt = stmt.where(DataQualityIssue.issue_code == issue_code.upper())
    if source_period:
        stmt = stmt.where(DataQualityIssue.source_period == source_period)
    if employee_id is not None:
        stmt = stmt.where(DataQualityIssue.employee_id == employee_id)

    offset = (page - 1) * limit
    issues = db.scalars(stmt.offset(offset).limit(limit)).all()
    return [_issue_response(issue) for issue in issues]


@router.get("/summary", response_model=DataQualitySummaryResponse)
def get_data_quality_summary(
    db: DbSession,
    source_period: Annotated[str | None, Query(max_length=32)] = None,
) -> DataQualitySummaryResponse:
    base_filters = [DataQualityIssue.status == "OPEN"]
    if source_period:
        base_filters.append(DataQualityIssue.source_period == source_period)

    open_total = db.scalar(select(func.count()).select_from(DataQualityIssue).where(*base_filters)) or 0
    watch_total = (
        db.scalar(
            select(func.count()).select_from(DataQualityIssue).where(
                *base_filters,
                DataQualityIssue.severity == "REVIEW",
            ),
        )
        or 0
    )

    severity_rows = db.execute(
        select(DataQualityIssue.severity, func.count())
        .where(*base_filters)
        .group_by(DataQualityIssue.severity)
        .order_by(DataQualityIssue.severity.asc()),
    ).all()
    code_rows = db.execute(
        select(DataQualityIssue.issue_code, func.count())
        .where(*base_filters)
        .group_by(DataQualityIssue.issue_code)
        .order_by(DataQualityIssue.issue_code.asc()),
    ).all()

    return DataQualitySummaryResponse(
        source_period=source_period,
        open_total=open_total,
        watch_total=watch_total,
        by_severity={str(key): int(value) for key, value in severity_rows},
        by_code={str(key): int(value) for key, value in code_rows},
    )


@router.patch("/issues/{issue_id}", response_model=DataQualityIssueResponse)
def update_data_quality_issue(
    issue_id: IssueId,
    payload: DataQualityIssueUpdateRequest,
    db: DbSession,
    _current_user: DataQualityUpdater,
) -> DataQualityIssueResponse:
    issue = db.get(DataQualityIssue, issue_id)
    if issue is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Data quality issue {issue_id} tidak ditemukan.",
        )

    if payload.status is not None:
        issue.status = payload.status
        issue.resolved_at = datetime.now(UTC) if payload.status == "RESOLVED" else None
    if payload.recommendation is not None:
        issue.recommendation = payload.recommendation

    db.commit()
    db.refresh(issue)
    return _issue_response(issue)


__all__ = ["router"]
