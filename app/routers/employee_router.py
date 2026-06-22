from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.permissions import require_permission
from app.database.connection import get_db
from app.models.auth import User
from app.schemas.employee_schema import (
    EmployeeDetailResponse,
    EmployeeDocumentCreate,
    EmployeeDocumentResponse,
    EmployeeFamilyCreate,
    EmployeeFamilyResponse,
    EmployeeListPageResponse,
    EmployeeListResponse,
    EmployeeMutationRequest,
    EmployeeStatusChangeRequest,
    EmployeeStatusResponse,
)
from app.schemas.employee_schema import EmployeeCreate, EmployeeUpdate
from app.services import employee_service

router = APIRouter(prefix="/employees", tags=["employees"])

DbSession = Annotated[Session, Depends(get_db)]
EmployeeId = Annotated[int, Path(gt=0)]
CurrentEmployeeCreator = Annotated[User, Depends(require_permission("employee", "create"))]
CurrentEmployeeUpdater = Annotated[User, Depends(require_permission("employee", "update"))]
CurrentEmployeeStatusChanger = Annotated[
    User,
    Depends(require_permission("employee", "change_status")),
]
CurrentEmployeeDeleter = Annotated[User, Depends(require_permission("employee", "delete"))]


def _handle_service_error(error: Exception) -> HTTPException:
    if isinstance(error, employee_service.EmployeeNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    if isinstance(error, employee_service.EmployeeConflictError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))
    if isinstance(error, employee_service.EmployeeValidationError):
        return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error))
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Terjadi kesalahan saat memproses data employee.",
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


def _client_ip(request: Request) -> str | None:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()

    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()

    return request.client.host if request.client else None


def _detail_completeness(detail: EmployeeDetailResponse) -> float:
    profile = detail.profile
    checks = [
        profile.employee_no,
        profile.full_name,
        profile.gender,
        profile.birth_place,
        profile.birth_date,
        profile.religion,
        profile.education,
        profile.marital_status,
        profile.mobile_phone,
        detail.identities,
        detail.addresses,
        detail.current_assignment,
        detail.current_status,
        detail.bpjs,
        detail.documents,
    ]
    completed = sum(1 for item in checks if bool(item))
    return round((completed / len(checks)) * 100, 2)


def _bpjs_status(detail: EmployeeDetailResponse) -> str:
    if not detail.bpjs:
        return "BELUM ADA"
    if any(item.active_status for item in detail.bpjs):
        return "AKTIF"
    return "NONAKTIF"


@router.get(
    "",
    response_model=EmployeeListPageResponse,
    dependencies=[Depends(require_permission("employee", "view"))],
)
def get_employees(
    db: DbSession,
    search: Annotated[str | None, Query(max_length=120)] = None,
    division_id: Annotated[int | None, Query(gt=0)] = None,
    category_id: Annotated[int | None, Query(gt=0)] = None,
    status_id: Annotated[int | None, Query(gt=0)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> EmployeeListPageResponse:
    return employee_service.get_employee_page(
        db,
        search=search,
        division_id=division_id,
        category_id=category_id,
        status_id=status_id,
        page=page,
        limit=limit,
    )


@router.get(
    "/{employee_id}",
    response_model=EmployeeListResponse,
    dependencies=[Depends(require_permission("employee", "view"))],
)
def get_employee(employee_id: EmployeeId, db: DbSession) -> EmployeeListResponse:
    detail = employee_service.get_employee_detail(db, employee_id)
    if detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee {employee_id} tidak ditemukan.",
        )

    return EmployeeListResponse(
        employee_id=detail.profile.employee_id,
        employee_no=detail.profile.employee_no,
        full_name=detail.profile.full_name,
        current_division=(
            detail.current_assignment.division_name if detail.current_assignment else None
        ),
        current_position=(
            detail.current_assignment.position_name if detail.current_assignment else None
        ),
        category=detail.current_assignment.category_name if detail.current_assignment else None,
        status=detail.current_status.status_name if detail.current_status else None,
        bpjs_status=_bpjs_status(detail),
        data_completeness=_detail_completeness(detail),
    )


@router.get(
    "/{employee_id}/detail",
    response_model=EmployeeDetailResponse,
    dependencies=[Depends(require_permission("employee", "view"))],
)
def get_employee_detail(employee_id: EmployeeId, db: DbSession) -> EmployeeDetailResponse:
    detail = employee_service.get_employee_detail(db, employee_id)
    if detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee {employee_id} tidak ditemukan.",
        )
    return detail


@router.post(
    "",
    response_model=EmployeeDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_employee(
    payload: EmployeeCreate,
    db: DbSession,
    current_user: CurrentEmployeeCreator,
    request: Request,
) -> EmployeeDetailResponse:
    try:
        result = employee_service.create_employee(
            db,
            payload,
            user_id=current_user.user_id,
            ip_address=_client_ip(request),
        )
        _commit_or_raise(db)
        return result
    except employee_service.EmployeeServiceError as error:
        db.rollback()
        raise _handle_service_error(error) from error


@router.put(
    "/{employee_id}",
    response_model=EmployeeDetailResponse,
)
def update_employee(
    employee_id: EmployeeId,
    payload: EmployeeUpdate,
    db: DbSession,
    current_user: CurrentEmployeeUpdater,
    request: Request,
) -> EmployeeDetailResponse:
    try:
        result = employee_service.update_employee(
            db,
            employee_id,
            payload,
            user_id=current_user.user_id,
            ip_address=_client_ip(request),
        )
        _commit_or_raise(db)
        return result
    except employee_service.EmployeeServiceError as error:
        db.rollback()
        raise _handle_service_error(error) from error


@router.patch(
    "/{employee_id}/status",
    response_model=EmployeeStatusResponse,
)
def change_employee_status(
    employee_id: EmployeeId,
    payload: EmployeeStatusChangeRequest,
    db: DbSession,
    current_user: CurrentEmployeeStatusChanger,
    request: Request,
) -> EmployeeStatusResponse:
    values = payload.model_dump()
    values["employee_id"] = employee_id
    try:
        result = employee_service.change_employee_status(
            db,
            values,
            user_id=current_user.user_id,
            ip_address=_client_ip(request),
        )
        _commit_or_raise(db)
        return result
    except employee_service.EmployeeServiceError as error:
        db.rollback()
        raise _handle_service_error(error) from error


@router.post(
    "/{employee_id}/mutation",
    response_model=EmployeeDetailResponse,
)
def mutate_employee(
    employee_id: EmployeeId,
    payload: EmployeeMutationRequest,
    db: DbSession,
    current_user: CurrentEmployeeUpdater,
    request: Request,
) -> EmployeeDetailResponse:
    values = payload.model_dump()
    values["employee_id"] = employee_id
    try:
        result = employee_service.mutate_employee(
            db,
            values,
            user_id=current_user.user_id,
            ip_address=_client_ip(request),
        )
        _commit_or_raise(db)
        return result
    except employee_service.EmployeeServiceError as error:
        db.rollback()
        raise _handle_service_error(error) from error


@router.post(
    "/{employee_id}/family",
    response_model=EmployeeFamilyResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_family_member(
    employee_id: EmployeeId,
    payload: EmployeeFamilyCreate,
    db: DbSession,
    current_user: CurrentEmployeeUpdater,
    request: Request,
) -> EmployeeFamilyResponse:
    values = payload.model_dump()
    values["employee_id"] = employee_id
    try:
        result = employee_service.add_family_member(
            db,
            values,
            user_id=current_user.user_id,
            ip_address=_client_ip(request),
        )
        _commit_or_raise(db)
        return result
    except employee_service.EmployeeServiceError as error:
        db.rollback()
        raise _handle_service_error(error) from error


@router.post(
    "/{employee_id}/documents",
    response_model=EmployeeDocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_document(
    employee_id: EmployeeId,
    payload: EmployeeDocumentCreate,
    db: DbSession,
    current_user: CurrentEmployeeUpdater,
    request: Request,
) -> EmployeeDocumentResponse:
    values = payload.model_dump()
    values["employee_id"] = employee_id
    try:
        result = employee_service.add_document(
            db,
            values,
            user_id=current_user.user_id,
            ip_address=_client_ip(request),
        )
        _commit_or_raise(db)
        return result
    except employee_service.EmployeeServiceError as error:
        db.rollback()
        raise _handle_service_error(error) from error


@router.delete(
    "/{employee_id}",
    status_code=status.HTTP_200_OK,
)
def delete_employee(
    employee_id: EmployeeId,
    db: DbSession,
    current_user: CurrentEmployeeDeleter,
    request: Request,
) -> dict[str, Any]:
    try:
        employee_service.soft_delete_employee(
            db,
            employee_id,
            user_id=current_user.user_id,
            ip_address=_client_ip(request),
        )
        _commit_or_raise(db)
        return {
            "status": "success",
            "message": "Employee dinonaktifkan melalui soft delete.",
            "data": {"employee_id": employee_id},
        }
    except employee_service.EmployeeServiceError as error:
        db.rollback()
        raise _handle_service_error(error) from error


__all__ = ["router"]
