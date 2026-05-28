from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.permissions import require_permission
from app.database.connection import get_db
from app.models.auth import User
from app.schemas.attendance_schema import (
    AttendanceCreate,
    AttendanceResponse,
    AttendanceSummaryResponse,
    WorkOutputCreate,
    WorkOutputResponse,
)
from app.services import attendance_service

router = APIRouter(prefix="/manpower", tags=["manpower"])

DbSession = Annotated[Session, Depends(get_db)]
CurrentAttendanceViewer = Annotated[User, Depends(require_permission("attendance", "view"))]
CurrentAttendanceManager = Annotated[User, Depends(require_permission("attendance", "manage"))]
CurrentWorkOutputViewer = Annotated[User, Depends(require_permission("work_output", "view"))]
CurrentWorkOutputManager = Annotated[User, Depends(require_permission("work_output", "manage"))]


def _client_ip(request: Request) -> str | None:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else None


def _handle_error(error: Exception) -> HTTPException:
    if isinstance(error, attendance_service.AttendanceConflictError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))
    if isinstance(error, attendance_service.AttendanceValidationError):
        return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error))
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Terjadi kesalahan saat memproses data manpower.",
    )


def _commit_or_raise(session: Session) -> None:
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Data tidak dapat disimpan karena melanggar constraint database.",
        ) from error


@router.get("/attendance", response_model=list[AttendanceResponse])
def list_attendance(
    db: DbSession,
    _current_user: CurrentAttendanceViewer,
    start_date: Annotated[date, Query()],
    end_date: Annotated[date, Query()],
    employee_id: Annotated[int | None, Query(gt=0)] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 200,
) -> list[AttendanceResponse]:
    return attendance_service.list_attendance(
        db,
        start_date=start_date,
        end_date=end_date,
        employee_id=employee_id,
        limit=limit,
    )


@router.get("/attendance/summary", response_model=AttendanceSummaryResponse)
def attendance_summary(
    db: DbSession,
    _current_user: CurrentAttendanceViewer,
    start_date: Annotated[date, Query()],
    end_date: Annotated[date, Query()],
    employee_id: Annotated[int | None, Query(gt=0)] = None,
) -> AttendanceSummaryResponse:
    return attendance_service.summarize_attendance(
        db,
        start_date=start_date,
        end_date=end_date,
        employee_id=employee_id,
    )


@router.post("/attendance", response_model=AttendanceResponse, status_code=status.HTTP_201_CREATED)
def create_attendance(
    payload: AttendanceCreate,
    db: DbSession,
    current_user: CurrentAttendanceManager,
    request: Request,
) -> AttendanceResponse:
    try:
        response = attendance_service.create_attendance(
            db,
            payload,
            user_id=current_user.user_id,
            ip_address=_client_ip(request),
        )
        _commit_or_raise(db)
        return response
    except attendance_service.AttendanceServiceError as error:
        db.rollback()
        raise _handle_error(error) from error


@router.get("/work-outputs", response_model=list[WorkOutputResponse])
def list_work_outputs(
    db: DbSession,
    _current_user: CurrentWorkOutputViewer,
    start_date: Annotated[date, Query()],
    end_date: Annotated[date, Query()],
    employee_id: Annotated[int | None, Query(gt=0)] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 200,
) -> list[WorkOutputResponse]:
    return attendance_service.list_work_outputs(
        db,
        start_date=start_date,
        end_date=end_date,
        employee_id=employee_id,
        limit=limit,
    )


@router.post("/work-outputs", response_model=WorkOutputResponse, status_code=status.HTTP_201_CREATED)
def create_work_output(
    payload: WorkOutputCreate,
    db: DbSession,
    current_user: CurrentWorkOutputManager,
    request: Request,
) -> WorkOutputResponse:
    try:
        response = attendance_service.create_work_output(
            db,
            payload,
            user_id=current_user.user_id,
            ip_address=_client_ip(request),
        )
        _commit_or_raise(db)
        return response
    except attendance_service.AttendanceServiceError as error:
        db.rollback()
        raise _handle_error(error) from error


__all__ = ["router"]
