from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.permissions import require_permission
from app.database.connection import get_db
from app.models.family import FamilyRelation
from app.models.organization import Company, Division, Estate, Position
from app.models.reference import (
    AttendanceCode,
    BpjsType,
    DocumentType,
    EducationLevel,
    EmployeeCategory,
    EmploymentStatus,
    EmploymentType,
    JobFamily,
    MaritalStatus,
    MovementType,
    PayType,
    Religion,
)
from app.schemas.reference_schema import ReferenceItemResponse

router = APIRouter(
    prefix="/references",
    tags=["references"],
    dependencies=[Depends(require_permission("employee", "view"))],
)

DbSession = Annotated[Session, Depends(get_db)]


def _active_filter(stmt, model: type, active_only: bool):
    if active_only and hasattr(model, "is_active"):
        return stmt.where(model.is_active.is_(True))
    return stmt


def _master_rows(
    db: Session,
    model: type,
    *,
    active_only: bool,
) -> list[ReferenceItemResponse]:
    stmt = _active_filter(select(model).order_by(model.code.asc()), model, active_only)
    rows = db.scalars(stmt).all()
    return [
        ReferenceItemResponse(
            id=row.id,
            code=row.code,
            name=row.name,
            description=row.description,
        )
        for row in rows
    ]


def _special_rows(
    db: Session,
    model: type,
    *,
    id_attr: str,
    code_attr: str,
    name_attr: str,
    active_only: bool,
) -> list[ReferenceItemResponse]:
    code_column = getattr(model, code_attr)
    stmt = _active_filter(select(model).order_by(code_column.asc()), model, active_only)
    rows = db.scalars(stmt).all()
    return [
        ReferenceItemResponse(
            id=getattr(row, id_attr),
            code=str(getattr(row, code_attr)),
            name=str(getattr(row, name_attr)),
            description=getattr(row, "description", None),
        )
        for row in rows
    ]


@router.get("/religions", response_model=list[ReferenceItemResponse])
def get_religions(db: DbSession, active_only: Annotated[bool, Query()] = True) -> list[ReferenceItemResponse]:
    return _master_rows(db, Religion, active_only=active_only)


@router.get("/education-levels", response_model=list[ReferenceItemResponse])
def get_education_levels(db: DbSession, active_only: Annotated[bool, Query()] = True) -> list[ReferenceItemResponse]:
    return _master_rows(db, EducationLevel, active_only=active_only)


@router.get("/marital-statuses", response_model=list[ReferenceItemResponse])
def get_marital_statuses(db: DbSession, active_only: Annotated[bool, Query()] = True) -> list[ReferenceItemResponse]:
    return _master_rows(db, MaritalStatus, active_only=active_only)


@router.get("/employee-categories", response_model=list[ReferenceItemResponse])
def get_employee_categories(db: DbSession, active_only: Annotated[bool, Query()] = True) -> list[ReferenceItemResponse]:
    return _master_rows(db, EmployeeCategory, active_only=active_only)


@router.get("/employment-statuses", response_model=list[ReferenceItemResponse])
def get_employment_statuses(db: DbSession, active_only: Annotated[bool, Query()] = True) -> list[ReferenceItemResponse]:
    return _master_rows(db, EmploymentStatus, active_only=active_only)


@router.get("/employment-types", response_model=list[ReferenceItemResponse])
def get_employment_types(db: DbSession, active_only: Annotated[bool, Query()] = True) -> list[ReferenceItemResponse]:
    return _master_rows(db, EmploymentType, active_only=active_only)


@router.get("/pay-types", response_model=list[ReferenceItemResponse])
def get_pay_types(db: DbSession, active_only: Annotated[bool, Query()] = True) -> list[ReferenceItemResponse]:
    return _master_rows(db, PayType, active_only=active_only)


@router.get("/job-families", response_model=list[ReferenceItemResponse])
def get_job_families(db: DbSession, active_only: Annotated[bool, Query()] = True) -> list[ReferenceItemResponse]:
    return _master_rows(db, JobFamily, active_only=active_only)


@router.get("/movement-types", response_model=list[ReferenceItemResponse])
def get_movement_types(db: DbSession, active_only: Annotated[bool, Query()] = True) -> list[ReferenceItemResponse]:
    return _master_rows(db, MovementType, active_only=active_only)


@router.get("/attendance-codes", response_model=list[ReferenceItemResponse])
def get_attendance_codes(db: DbSession, active_only: Annotated[bool, Query()] = True) -> list[ReferenceItemResponse]:
    return _master_rows(db, AttendanceCode, active_only=active_only)


@router.get("/document-types", response_model=list[ReferenceItemResponse])
def get_document_types(db: DbSession) -> list[ReferenceItemResponse]:
    return _special_rows(
        db,
        DocumentType,
        id_attr="document_type_id",
        code_attr="document_type_name",
        name_attr="document_type_name",
        active_only=False,
    )


@router.get("/bpjs-types", response_model=list[ReferenceItemResponse])
def get_bpjs_types(db: DbSession) -> list[ReferenceItemResponse]:
    return _special_rows(
        db,
        BpjsType,
        id_attr="bpjs_type_id",
        code_attr="bpjs_type_name",
        name_attr="bpjs_type_name",
        active_only=False,
    )


@router.get("/family-relations", response_model=list[ReferenceItemResponse])
def get_family_relations(db: DbSession) -> list[ReferenceItemResponse]:
    return _special_rows(
        db,
        FamilyRelation,
        id_attr="relation_id",
        code_attr="relation_code",
        name_attr="relation_name",
        active_only=False,
    )


@router.get("/companies", response_model=list[ReferenceItemResponse])
def get_companies(db: DbSession, active_only: Annotated[bool, Query()] = True) -> list[ReferenceItemResponse]:
    return _special_rows(
        db,
        Company,
        id_attr="company_id",
        code_attr="company_code",
        name_attr="company_name",
        active_only=active_only,
    )


@router.get("/estates", response_model=list[ReferenceItemResponse])
def get_estates(db: DbSession, active_only: Annotated[bool, Query()] = True) -> list[ReferenceItemResponse]:
    return _special_rows(
        db,
        Estate,
        id_attr="estate_id",
        code_attr="estate_code",
        name_attr="estate_name",
        active_only=active_only,
    )


@router.get("/divisions", response_model=list[ReferenceItemResponse])
def get_divisions(
    db: DbSession,
    active_only: Annotated[bool, Query()] = True,
    estate_id: Annotated[int | None, Query(gt=0)] = None,
) -> list[ReferenceItemResponse]:
    stmt = select(Division).order_by(Division.division_code.asc())
    if active_only:
        stmt = stmt.where(Division.is_active.is_(True))
    if estate_id is not None:
        stmt = stmt.where(Division.estate_id == estate_id)

    rows = db.scalars(stmt).all()
    return [
        ReferenceItemResponse(
            id=row.division_id,
            code=row.division_code,
            name=row.division_name,
            description=row.division_type,
        )
        for row in rows
    ]


@router.get("/positions", response_model=list[ReferenceItemResponse])
def get_positions(
    db: DbSession,
    active_only: Annotated[bool, Query()] = True,
    job_family_id: Annotated[int | None, Query(gt=0)] = None,
) -> list[ReferenceItemResponse]:
    stmt = select(Position).order_by(Position.level_order.asc(), Position.position_code.asc())
    if active_only:
        stmt = stmt.where(Position.is_active.is_(True))
    if job_family_id is not None:
        stmt = stmt.where(Position.job_family_id == job_family_id)

    rows = db.scalars(stmt).all()
    return [
        ReferenceItemResponse(
            id=row.position_id,
            code=row.position_code,
            name=row.position_name,
            description=None,
        )
        for row in rows
    ]


__all__ = ["router"]
