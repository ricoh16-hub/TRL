from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date
from typing import Any

from pydantic import BaseModel
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models.document import EmployeeDocument
from app.models.employee import Employee, EmployeeIdentity
from app.models.employment import EmployeeAssignment, EmployeeContract, EmployeeStatusHistory
from app.models.family import EmployeeFamilyMember
from app.models.movement import EmployeeMovement
from app.models.payroll import EmployeePayProfile
from app.models.reference import EmploymentStatus
from app.repositories import employee_repository
from app.schemas.employee_schema import (
    EmployeeAddressResponse,
    EmployeeAssignmentResponse,
    EmployeeAttendanceSummary,
    EmployeeBpjsResponse,
    EmployeeContractResponse,
    EmployeeDetailResponse,
    EmployeeDocumentResponse,
    EmployeeFamilyCreate,
    EmployeeFamilyResponse,
    EmployeeIdentityResponse,
    EmployeeListPageResponse,
    EmployeeListResponse,
    EmployeeMovementResponse,
    EmployeeMutationRequest,
    EmployeePayrollSummary,
    EmployeeProfileResponse,
    EmployeeStatusChangeRequest,
    EmployeeStatusResponse,
)
from app.services import audit_service

Payload = Mapping[str, Any] | BaseModel

NIK_IDENTITY_TYPES = {"NIK", "KTP"}
INACTIVE_STATUS_CODES = {"KELUAR", "NONAKTIF", "MENINGGAL"}


class EmployeeServiceError(Exception):
    """Base exception for employee service failures."""


class EmployeeNotFoundError(EmployeeServiceError):
    """Raised when the requested employee does not exist."""


class EmployeeConflictError(EmployeeServiceError):
    """Raised when a unique business key already exists."""


class EmployeeValidationError(EmployeeServiceError):
    """Raised when a business rule cannot be satisfied."""


def _payload_to_dict(payload: Payload, *, exclude_unset: bool = False) -> dict[str, Any]:
    if isinstance(payload, BaseModel):
        return payload.model_dump(exclude_unset=exclude_unset)
    return dict(payload)


def _snapshot(instance: Any) -> dict[str, Any]:
    return {
        column.name: getattr(instance, column.name)
        for column in instance.__table__.columns
    }


def _get_required_employee(session: Session, employee_id: int) -> Employee:
    employee = employee_repository.get_employee_by_id(session, employee_id)
    if employee is None:
        raise EmployeeNotFoundError(f"Employee {employee_id} tidak ditemukan.")
    return employee


def _ensure_employee_no_unique(
    session: Session,
    employee_no: str,
    *,
    exclude_employee_id: int | None = None,
) -> None:
    stmt = select(Employee).where(Employee.employee_no == employee_no)
    if exclude_employee_id is not None:
        stmt = stmt.where(Employee.employee_id != exclude_employee_id)
    if session.scalar(stmt) is not None:
        raise EmployeeConflictError(f"Employee no {employee_no} sudah digunakan.")


def _extract_nik_values(payload: dict[str, Any]) -> list[str]:
    nik_values: list[str] = []

    direct_nik = payload.get("nik")
    if direct_nik:
        nik_values.append(str(direct_nik))

    identity_type = str(payload.get("identity_type") or "").upper()
    identity_number = payload.get("identity_number")
    if identity_type in NIK_IDENTITY_TYPES and identity_number:
        nik_values.append(str(identity_number))

    for identity_payload in payload.get("identities") or []:
        identity = _payload_to_dict(identity_payload)
        nested_nik = identity.get("nik")
        if nested_nik:
            nik_values.append(str(nested_nik))
            continue

        nested_type = str(identity.get("identity_type") or "").upper()
        nested_number = identity.get("identity_number")
        if nested_type in NIK_IDENTITY_TYPES and nested_number:
            nik_values.append(str(nested_number))

    return list(dict.fromkeys(nik_values))


def _ensure_nik_unique(
    session: Session,
    nik: str,
    *,
    exclude_employee_id: int | None = None,
) -> None:
    stmt = select(EmployeeIdentity).where(
        func.upper(EmployeeIdentity.identity_type).in_(NIK_IDENTITY_TYPES),
        EmployeeIdentity.identity_number == nik,
    )
    if exclude_employee_id is not None:
        stmt = stmt.where(EmployeeIdentity.employee_id != exclude_employee_id)

    if session.scalar(stmt) is not None:
        raise EmployeeConflictError(f"NIK {nik} sudah digunakan.")


def _create_identity_records(
    session: Session,
    employee_id: int,
    payload: dict[str, Any],
) -> list[EmployeeIdentity]:
    created: list[EmployeeIdentity] = []
    for identity_payload in payload.get("identities") or []:
        identity_data = _payload_to_dict(identity_payload)
        identity_data["employee_id"] = employee_id
        identity = EmployeeIdentity(
            **{
                key: value
                for key, value in identity_data.items()
                if key in EmployeeIdentity.__table__.columns.keys()
                and key not in {"identity_id", "created_at"}
            },
        )
        session.add(identity)
        created.append(identity)

    if created:
        session.flush()

    return created


def _get_status_by_code(session: Session, code: str) -> EmploymentStatus:
    status = session.scalar(
        select(EmploymentStatus).where(func.upper(EmploymentStatus.code) == code.upper()),
    )
    if status is None:
        raise EmployeeValidationError(f"Employment status {code} belum tersedia di master data.")
    return status


def _get_status_by_id(session: Session, employment_status_id: int) -> EmploymentStatus:
    status = session.get(EmploymentStatus, employment_status_id)
    if status is None:
        raise EmployeeValidationError(
            f"Employment status id {employment_status_id} tidak ditemukan.",
        )
    return status


def _current_assignment(employee: Employee) -> EmployeeAssignment | None:
    current_items = [assignment for assignment in employee.assignments if assignment.is_current]
    if current_items:
        return sorted(
            current_items,
            key=lambda item: (item.start_date, item.assignment_id),
            reverse=True,
        )[0]
    if not employee.assignments:
        return None
    return sorted(
        employee.assignments,
        key=lambda item: (item.start_date, item.assignment_id),
        reverse=True,
    )[0]


def _current_status(employee: Employee) -> EmployeeStatusHistory | None:
    if not employee.status_histories:
        return None
    return sorted(
        employee.status_histories,
        key=lambda item: (item.effective_date, item.status_history_id),
        reverse=True,
    )[0]


def _current_contract(employee: Employee) -> EmployeeContract | None:
    if not employee.contracts:
        return None
    active_contracts = [contract for contract in employee.contracts if contract.end_date is None]
    source = active_contracts or employee.contracts
    return sorted(
        source,
        key=lambda item: (item.start_date, item.contract_id),
        reverse=True,
    )[0]


def _current_pay_profile(employee: Employee) -> EmployeePayProfile | None:
    if not employee.pay_profiles:
        return None
    return sorted(
        employee.pay_profiles,
        key=lambda item: (item.effective_date, item.pay_profile_id),
        reverse=True,
    )[0]


def _bpjs_status(employee: Employee) -> str:
    if not employee.bpjs_records:
        return "BELUM ADA"
    if any(record.active_status for record in employee.bpjs_records):
        return "AKTIF"
    return "NONAKTIF"


def _data_completeness(employee: Employee) -> float:
    checks = [
        employee.employee_no,
        employee.full_name,
        employee.gender,
        employee.birth_place,
        employee.birth_date,
        employee.religion_id,
        employee.education_id,
        employee.marital_status_id,
        employee.mobile_phone,
        employee.identities,
        employee.addresses,
        _current_assignment(employee),
        _current_status(employee),
        employee.bpjs_records,
        employee.documents,
    ]
    completed = sum(1 for item in checks if bool(item))
    return round((completed / len(checks)) * 100, 2)


def _assignment_response(assignment: EmployeeAssignment) -> EmployeeAssignmentResponse:
    return EmployeeAssignmentResponse(
        assignment_id=assignment.assignment_id,
        estate_id=assignment.estate_id,
        estate_name=assignment.estate.estate_name if assignment.estate else None,
        division_id=assignment.division_id,
        division_name=assignment.division.division_name if assignment.division else None,
        position_id=assignment.position_id,
        position_name=assignment.position.position_name if assignment.position else None,
        category_id=assignment.category_id,
        category_name=assignment.category.name if assignment.category else None,
        start_date=assignment.start_date,
        end_date=assignment.end_date,
        is_current=assignment.is_current,
        notes=assignment.notes,
    )


def _status_response(status: EmployeeStatusHistory) -> EmployeeStatusResponse:
    return EmployeeStatusResponse(
        status_history_id=status.status_history_id,
        employment_status_id=status.employment_status_id,
        status_name=status.employment_status.name if status.employment_status else None,
        effective_date=status.effective_date,
        notes=status.notes,
        approved_by=status.approved_by,
    )


def _contract_response(contract: EmployeeContract) -> EmployeeContractResponse:
    return EmployeeContractResponse(
        contract_id=contract.contract_id,
        employment_type_id=contract.employment_type_id,
        employment_type_name=contract.employment_type.name if contract.employment_type else None,
        contract_no=contract.contract_no,
        start_date=contract.start_date,
        end_date=contract.end_date,
        salary_type=contract.salary_type,
        notes=contract.notes,
    )


def _family_response(member: EmployeeFamilyMember) -> EmployeeFamilyResponse:
    return EmployeeFamilyResponse(
        family_member_id=member.family_member_id,
        relation_id=member.relation_id,
        relation_name=member.relation.relation_name if member.relation else None,
        full_name=member.full_name,
        gender=member.gender,
        birth_place=member.birth_place,
        birth_date=member.birth_date,
        education_level=member.education_level,
        dependent_flag=member.dependent_flag,
        notes=member.notes,
    )


def _document_response(document: EmployeeDocument) -> EmployeeDocumentResponse:
    return EmployeeDocumentResponse(
        document_id=document.document_id,
        employee_id=document.employee_id,
        document_type_id=document.document_type_id,
        document_type_name=(
            document.document_type.document_type_name if document.document_type else None
        ),
        file_name=document.file_name,
        file_path=document.file_path,
        uploaded_by=document.uploaded_by,
        uploaded_at=document.uploaded_at,
        notes=document.notes,
    )


def _movement_response(movement: EmployeeMovement) -> EmployeeMovementResponse:
    return EmployeeMovementResponse(
        movement_id=movement.movement_id,
        movement_type_id=movement.movement_type_id,
        movement_type_name=movement.movement_type.name if movement.movement_type else None,
        from_estate_id=movement.from_estate_id,
        from_division_id=movement.from_division_id,
        from_position_id=movement.from_position_id,
        to_estate_id=movement.to_estate_id,
        to_division_id=movement.to_division_id,
        to_position_id=movement.to_position_id,
        movement_date=movement.movement_date,
        notes=movement.notes,
        approved_by=movement.approved_by,
        created_at=movement.created_at,
    )


def to_list_response(employee: Employee) -> EmployeeListResponse:
    assignment = _current_assignment(employee)
    status = _current_status(employee)
    return EmployeeListResponse(
        employee_id=employee.employee_id,
        employee_no=employee.employee_no,
        full_name=employee.full_name,
        current_division=assignment.division.division_name if assignment and assignment.division else None,
        current_position=assignment.position.position_name if assignment and assignment.position else None,
        category=assignment.category.name if assignment and assignment.category else None,
        status=status.employment_status.name if status and status.employment_status else None,
        bpjs_status=_bpjs_status(employee),
        data_completeness=_data_completeness(employee),
    )


def to_detail_response(employee: Employee) -> EmployeeDetailResponse:
    assignment = _current_assignment(employee)
    status = _current_status(employee)
    contract = _current_contract(employee)
    pay_profile = _current_pay_profile(employee)
    wage_rate = pay_profile.wage_rate if pay_profile else None

    return EmployeeDetailResponse(
        profile=EmployeeProfileResponse(
            employee_id=employee.employee_id,
            employee_no=employee.employee_no,
            full_name=employee.full_name,
            gender=employee.gender,
            birth_place=employee.birth_place,
            birth_date=employee.birth_date,
            religion=employee.religion.name if employee.religion else None,
            education=employee.education.name if employee.education else None,
            marital_status=employee.marital_status.name if employee.marital_status else None,
            blood_type=employee.blood_type,
            mobile_phone=employee.mobile_phone,
            email=employee.email,
            photo_path=employee.photo_path,
            is_active=employee.is_active,
            created_at=employee.created_at,
            updated_at=employee.updated_at,
        ),
        identities=[
            EmployeeIdentityResponse.model_validate(identity)
            for identity in employee.identities
        ],
        addresses=[
            EmployeeAddressResponse.model_validate(address)
            for address in employee.addresses
        ],
        current_assignment=_assignment_response(assignment) if assignment else None,
        current_status=_status_response(status) if status else None,
        current_contract=_contract_response(contract) if contract else None,
        family_members=[_family_response(member) for member in employee.family_members],
        bpjs=[
            EmployeeBpjsResponse(
                employee_bpjs_id=record.employee_bpjs_id,
                bpjs_type_id=record.bpjs_type_id,
                bpjs_type_name=record.bpjs_type.bpjs_type_name if record.bpjs_type else None,
                bpjs_number=record.bpjs_number,
                active_status=record.active_status,
                registered_date=record.registered_date,
                notes=record.notes,
            )
            for record in employee.bpjs_records
        ],
        documents=[_document_response(document) for document in employee.documents],
        movements=[_movement_response(movement) for movement in employee.movements],
        payroll_summary=(
            EmployeePayrollSummary(
                pay_profile_id=pay_profile.pay_profile_id,
                wage_rate_id=pay_profile.wage_rate_id,
                pay_type=wage_rate.pay_type.name if wage_rate and wage_rate.pay_type else None,
                amount=wage_rate.amount if wage_rate else None,
                unit_name=wage_rate.unit_name if wage_rate else None,
                rice_kg=pay_profile.rice_kg,
                bank_name=pay_profile.bank_name,
                bank_account_no=pay_profile.bank_account_no,
                bank_account_name=pay_profile.bank_account_name,
                effective_date=pay_profile.effective_date,
            )
            if pay_profile
            else None
        ),
        attendance_summary=EmployeeAttendanceSummary(),
    )


def get_employee_list(
    session: Session,
    *,
    search: str | None = None,
    division_id: int | None = None,
    category_id: int | None = None,
    status_id: int | None = None,
    is_active: bool | None = True,
    offset: int = 0,
    limit: int = 100,
) -> list[EmployeeListResponse]:
    employees = employee_repository.get_employee_list(
        session,
        search=search,
        division_id=division_id,
        category_id=category_id,
        status_id=status_id,
        is_active=is_active,
        offset=offset,
        limit=limit,
    )
    return [to_list_response(employee) for employee in employees]


def get_employee_page(
    session: Session,
    *,
    search: str | None = None,
    division_id: int | None = None,
    category_id: int | None = None,
    status_id: int | None = None,
    is_active: bool | None = True,
    page: int = 1,
    limit: int = 100,
) -> EmployeeListPageResponse:
    offset = (page - 1) * limit
    total = employee_repository.count_employees(
        session,
        search=search,
        division_id=division_id,
        category_id=category_id,
        status_id=status_id,
        is_active=is_active,
    )
    items = get_employee_list(
        session,
        search=search,
        division_id=division_id,
        category_id=category_id,
        status_id=status_id,
        is_active=is_active,
        offset=offset,
        limit=limit,
    )
    pages = (total + limit - 1) // limit if total else 0
    return EmployeeListPageResponse(
        items=items,
        page=page,
        limit=limit,
        total=total,
        pages=pages,
    )


def get_employee_detail(session: Session, employee_id: int) -> EmployeeDetailResponse | None:
    employee = employee_repository.get_employee_detail(session, employee_id)
    return to_detail_response(employee) if employee else None


def create_employee(
    session: Session,
    payload: Payload,
    *,
    user_id: int | None = None,
    ip_address: str | None = None,
) -> EmployeeDetailResponse:
    values = _payload_to_dict(payload)
    employee_no = str(values["employee_no"])
    _ensure_employee_no_unique(session, employee_no)
    for nik in _extract_nik_values(values):
        _ensure_nik_unique(session, nik)

    employee = employee_repository.create_employee(session, values)
    identities = _create_identity_records(session, employee.employee_id, values)

    status_history: EmployeeStatusHistory | None = None
    if employee.is_active:
        active_status = _get_status_by_code(session, "AKTIF")
        status_history = employee_repository.change_employee_status(
            session,
            {
                "employee_id": employee.employee_id,
                "employment_status_id": active_status.id,
                "effective_date": values.get("status_effective_date") or date.today(),
                "notes": "Initial active status",
            },
        )

    audit_service.create_audit_log(
        session,
        module_name="employee",
        action_name="create",
        table_name="employees",
        record_id=employee.employee_id,
        new_data={
            "employee": _snapshot(employee),
            "identities": [_snapshot(identity) for identity in identities],
            "initial_status": _snapshot(status_history) if status_history else None,
        },
        user_id=user_id,
        ip_address=ip_address,
    )

    detail = employee_repository.get_employee_detail(session, employee.employee_id)
    if detail is None:
        raise EmployeeValidationError("Employee berhasil dibuat tetapi gagal dimuat ulang.")
    return to_detail_response(detail)


def update_employee(
    session: Session,
    employee_id: int,
    payload: Payload,
    *,
    user_id: int | None = None,
    ip_address: str | None = None,
) -> EmployeeDetailResponse:
    employee = _get_required_employee(session, employee_id)
    values = _payload_to_dict(payload, exclude_unset=True)

    if "employee_no" in values and values["employee_no"] != employee.employee_no:
        _ensure_employee_no_unique(
            session,
            str(values["employee_no"]),
            exclude_employee_id=employee_id,
        )
    for nik in _extract_nik_values(values):
        _ensure_nik_unique(session, nik, exclude_employee_id=employee_id)

    old_data = _snapshot(employee)
    updated = employee_repository.update_employee(session, employee_id, values)
    if updated is None:
        raise EmployeeNotFoundError(f"Employee {employee_id} tidak ditemukan.")

    audit_service.create_audit_log(
        session,
        module_name="employee",
        action_name="update",
        table_name="employees",
        record_id=employee_id,
        old_data=old_data,
        new_data=_snapshot(updated),
        user_id=user_id,
        ip_address=ip_address,
    )

    detail = employee_repository.get_employee_detail(session, employee_id)
    if detail is None:
        raise EmployeeNotFoundError(f"Employee {employee_id} tidak ditemukan.")
    return to_detail_response(detail)


def soft_delete_employee(
    session: Session,
    employee_id: int,
    *,
    user_id: int | None = None,
    ip_address: str | None = None,
) -> EmployeeDetailResponse:
    employee = _get_required_employee(session, employee_id)
    old_data = _snapshot(employee)
    updated = employee_repository.soft_delete_employee(session, employee_id)
    if updated is None:
        raise EmployeeNotFoundError(f"Employee {employee_id} tidak ditemukan.")

    audit_service.create_audit_log(
        session,
        module_name="employee",
        action_name="soft_delete",
        table_name="employees",
        record_id=employee_id,
        old_data=old_data,
        new_data=_snapshot(updated),
        user_id=user_id,
        ip_address=ip_address,
    )

    detail = employee_repository.get_employee_detail(session, employee_id)
    if detail is None:
        raise EmployeeNotFoundError(f"Employee {employee_id} tidak ditemukan.")
    return to_detail_response(detail)


def change_employee_status(
    session: Session,
    payload: EmployeeStatusChangeRequest | Payload,
    *,
    user_id: int | None = None,
    ip_address: str | None = None,
) -> EmployeeStatusResponse:
    values = _payload_to_dict(payload)
    employee = _get_required_employee(session, int(values["employee_id"]))
    employment_status = _get_status_by_id(session, int(values["employment_status_id"]))

    old_employee_data = _snapshot(employee)
    status_history = employee_repository.change_employee_status(session, values)
    if employment_status.code.upper() in INACTIVE_STATUS_CODES:
        employee.is_active = False
        session.flush()
    elif employment_status.code.upper() == "AKTIF":
        employee.is_active = True
        session.flush()

    audit_service.create_audit_log(
        session,
        module_name="employee",
        action_name="change_status",
        table_name="employee_status_histories",
        record_id=status_history.status_history_id,
        old_data={"employee": old_employee_data},
        new_data={
            "employee": _snapshot(employee),
            "status_history": _snapshot(status_history),
        },
        user_id=user_id,
        ip_address=ip_address,
    )

    status_history.employment_status = employment_status
    return _status_response(status_history)


def create_assignment(
    session: Session,
    payload: Payload,
    *,
    user_id: int | None = None,
    ip_address: str | None = None,
) -> EmployeeAssignmentResponse:
    values = _payload_to_dict(payload)
    _get_required_employee(session, int(values["employee_id"]))
    assignment = employee_repository.create_assignment(session, values)

    audit_service.create_audit_log(
        session,
        module_name="employee",
        action_name="create_assignment",
        table_name="employee_assignments",
        record_id=assignment.assignment_id,
        new_data=_snapshot(assignment),
        user_id=user_id,
        ip_address=ip_address,
    )

    detail = employee_repository.get_employee_detail(session, assignment.employee_id)
    if detail:
        for item in detail.assignments:
            if item.assignment_id == assignment.assignment_id:
                return _assignment_response(item)
    return _assignment_response(assignment)


def mutate_employee(
    session: Session,
    payload: EmployeeMutationRequest | Payload,
    *,
    user_id: int | None = None,
    ip_address: str | None = None,
) -> EmployeeDetailResponse:
    values = _payload_to_dict(payload)
    employee_id = int(values["employee_id"])
    _get_required_employee(session, employee_id)

    current_assignment = session.scalar(
        select(EmployeeAssignment)
        .where(
            EmployeeAssignment.employee_id == employee_id,
            EmployeeAssignment.is_current.is_(True),
        )
        .order_by(desc(EmployeeAssignment.start_date), desc(EmployeeAssignment.assignment_id)),
    )
    if current_assignment is None:
        raise EmployeeValidationError("Mutasi membutuhkan assignment aktif.")

    movement_date = values["movement_date"]
    from_estate_id = values.get("from_estate_id") or current_assignment.estate_id
    from_division_id = values.get("from_division_id") or current_assignment.division_id
    from_position_id = values.get("from_position_id") or current_assignment.position_id
    to_estate_id = values.get("to_estate_id") or current_assignment.estate_id
    to_division_id = values.get("to_division_id") or current_assignment.division_id
    to_position_id = values.get("to_position_id") or current_assignment.position_id

    old_assignment_data = _snapshot(current_assignment)
    current_assignment.is_current = False
    current_assignment.end_date = movement_date
    session.flush()

    new_assignment = employee_repository.create_assignment(
        session,
        {
            "employee_id": employee_id,
            "estate_id": to_estate_id,
            "division_id": to_division_id,
            "position_id": to_position_id,
            "category_id": current_assignment.category_id,
            "start_date": movement_date,
            "is_current": True,
            "notes": values.get("notes"),
        },
    )
    movement = employee_repository.create_movement(
        session,
        {
            **values,
            "from_estate_id": from_estate_id,
            "from_division_id": from_division_id,
            "from_position_id": from_position_id,
            "to_estate_id": to_estate_id,
            "to_division_id": to_division_id,
            "to_position_id": to_position_id,
        },
    )

    audit_service.create_audit_log(
        session,
        module_name="employee",
        action_name="mutation",
        table_name="employee_movements",
        record_id=movement.movement_id,
        old_data={"assignment": old_assignment_data},
        new_data={
            "closed_assignment": _snapshot(current_assignment),
            "new_assignment": _snapshot(new_assignment),
            "movement": _snapshot(movement),
        },
        user_id=user_id,
        ip_address=ip_address,
    )

    detail = employee_repository.get_employee_detail(session, employee_id)
    if detail is None:
        raise EmployeeNotFoundError(f"Employee {employee_id} tidak ditemukan.")
    return to_detail_response(detail)


def create_movement(
    session: Session,
    payload: EmployeeMutationRequest | Payload,
    *,
    user_id: int | None = None,
    ip_address: str | None = None,
) -> EmployeeMovementResponse:
    values = _payload_to_dict(payload)
    _get_required_employee(session, int(values["employee_id"]))
    movement = employee_repository.create_movement(session, values)

    audit_service.create_audit_log(
        session,
        module_name="employee",
        action_name="create_movement",
        table_name="employee_movements",
        record_id=movement.movement_id,
        new_data=_snapshot(movement),
        user_id=user_id,
        ip_address=ip_address,
    )

    detail = employee_repository.get_employee_detail(session, movement.employee_id)
    if detail:
        for item in detail.movements:
            if item.movement_id == movement.movement_id:
                return _movement_response(item)
    return _movement_response(movement)


def add_family_member(
    session: Session,
    payload: EmployeeFamilyCreate | Payload,
    *,
    user_id: int | None = None,
    ip_address: str | None = None,
) -> EmployeeFamilyResponse:
    values = _payload_to_dict(payload)
    _get_required_employee(session, int(values["employee_id"]))
    family_member = employee_repository.add_family_member(session, values)

    audit_service.create_audit_log(
        session,
        module_name="employee",
        action_name="add_family_member",
        table_name="employee_family_members",
        record_id=family_member.family_member_id,
        new_data=_snapshot(family_member),
        user_id=user_id,
        ip_address=ip_address,
    )

    detail = employee_repository.get_employee_detail(session, family_member.employee_id)
    if detail:
        for item in detail.family_members:
            if item.family_member_id == family_member.family_member_id:
                return _family_response(item)
    return _family_response(family_member)


def add_document(
    session: Session,
    payload: Payload,
    *,
    user_id: int | None = None,
    ip_address: str | None = None,
) -> EmployeeDocumentResponse:
    values = _payload_to_dict(payload)
    _get_required_employee(session, int(values["employee_id"]))
    document = employee_repository.add_document(session, values)

    audit_service.create_audit_log(
        session,
        module_name="employee",
        action_name="upload_document",
        table_name="employee_documents",
        record_id=document.document_id,
        new_data=_snapshot(document),
        user_id=user_id,
        ip_address=ip_address,
    )

    detail = employee_repository.get_employee_detail(session, document.employee_id)
    if detail:
        for item in detail.documents:
            if item.document_id == document.document_id:
                return _document_response(item)
    return _document_response(document)


def get_employee_history(session: Session, employee_id: int) -> dict[str, Sequence[Any]]:
    _get_required_employee(session, employee_id)
    return employee_repository.get_employee_history(session, employee_id)


__all__ = [
    "EmployeeConflictError",
    "EmployeeNotFoundError",
    "EmployeeServiceError",
    "EmployeeValidationError",
    "add_document",
    "add_family_member",
    "change_employee_status",
    "create_assignment",
    "create_employee",
    "create_movement",
    "get_employee_detail",
    "get_employee_history",
    "get_employee_list",
    "get_employee_page",
    "mutate_employee",
    "soft_delete_employee",
    "to_detail_response",
    "to_list_response",
    "update_employee",
]
