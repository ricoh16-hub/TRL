from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, TypeVar

from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.bpjs import EmployeeBpjs
from app.models.document import EmployeeDocument
from app.models.employee import Employee
from app.models.employment import EmployeeAssignment, EmployeeContract, EmployeeStatusHistory
from app.models.family import EmployeeFamilyMember
from app.models.movement import EmployeeMovement
from app.models.payroll import EmployeePayProfile, WageRate

ModelT = TypeVar("ModelT")
Payload = Mapping[str, Any]


def _payload_to_dict(payload: Payload) -> dict[str, Any]:
    return dict(payload)


def _column_data(
    model: type[ModelT],
    payload: Payload,
    *,
    exclude: set[str] | None = None,
) -> dict[str, Any]:
    excluded = exclude or set()
    column_names = {column.name for column in model.__table__.columns}  # type: ignore[attr-defined]
    values = _payload_to_dict(payload)
    return {
        key: value
        for key, value in values.items()
        if key in column_names and key not in excluded
    }


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
) -> Sequence[Employee]:
    stmt = (
        select(Employee)
        .options(
            selectinload(Employee.assignments).joinedload(EmployeeAssignment.division),
            selectinload(Employee.assignments).joinedload(EmployeeAssignment.position),
            selectinload(Employee.assignments).joinedload(EmployeeAssignment.category),
            selectinload(Employee.status_histories).joinedload(
                EmployeeStatusHistory.employment_status,
            ),
            selectinload(Employee.bpjs_records).joinedload(EmployeeBpjs.bpjs_type),
        )
        .order_by(Employee.full_name.asc(), Employee.employee_no.asc())
        .offset(offset)
        .limit(limit)
    )

    if is_active is not None:
        stmt = stmt.where(Employee.is_active.is_(is_active))

    if search:
        search_pattern = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                Employee.employee_no.ilike(search_pattern),
                Employee.full_name.ilike(search_pattern),
                Employee.mobile_phone.ilike(search_pattern),
                Employee.email.ilike(search_pattern),
            ),
        )

    if division_id is not None:
        stmt = stmt.where(
            Employee.assignments.any(
                and_(
                    EmployeeAssignment.division_id == division_id,
                    EmployeeAssignment.is_current.is_(True),
                ),
            ),
        )

    if category_id is not None:
        stmt = stmt.where(
            Employee.assignments.any(
                and_(
                    EmployeeAssignment.category_id == category_id,
                    EmployeeAssignment.is_current.is_(True),
                ),
            ),
        )

    if status_id is not None:
        stmt = stmt.where(
            Employee.status_histories.any(
                EmployeeStatusHistory.employment_status_id == status_id,
            ),
        )

    return session.scalars(stmt).all()


def count_employees(
    session: Session,
    *,
    search: str | None = None,
    division_id: int | None = None,
    category_id: int | None = None,
    status_id: int | None = None,
    is_active: bool | None = True,
) -> int:
    stmt = select(func.count(Employee.employee_id))

    if is_active is not None:
        stmt = stmt.where(Employee.is_active.is_(is_active))

    if search:
        search_pattern = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                Employee.employee_no.ilike(search_pattern),
                Employee.full_name.ilike(search_pattern),
                Employee.mobile_phone.ilike(search_pattern),
                Employee.email.ilike(search_pattern),
            ),
        )

    if division_id is not None:
        stmt = stmt.where(
            Employee.assignments.any(
                and_(
                    EmployeeAssignment.division_id == division_id,
                    EmployeeAssignment.is_current.is_(True),
                ),
            ),
        )

    if category_id is not None:
        stmt = stmt.where(
            Employee.assignments.any(
                and_(
                    EmployeeAssignment.category_id == category_id,
                    EmployeeAssignment.is_current.is_(True),
                ),
            ),
        )

    if status_id is not None:
        stmt = stmt.where(
            Employee.status_histories.any(
                EmployeeStatusHistory.employment_status_id == status_id,
            ),
        )

    return int(session.scalar(stmt) or 0)


def get_employee_by_id(session: Session, employee_id: int) -> Employee | None:
    return session.get(Employee, employee_id)


def get_employee_detail(session: Session, employee_id: int) -> Employee | None:
    stmt = (
        select(Employee)
        .where(Employee.employee_id == employee_id)
        .options(
            joinedload(Employee.religion),
            joinedload(Employee.education),
            joinedload(Employee.marital_status),
            selectinload(Employee.identities),
            selectinload(Employee.addresses),
            selectinload(Employee.assignments).joinedload(EmployeeAssignment.estate),
            selectinload(Employee.assignments).joinedload(EmployeeAssignment.division),
            selectinload(Employee.assignments).joinedload(EmployeeAssignment.position),
            selectinload(Employee.assignments).joinedload(EmployeeAssignment.category),
            selectinload(Employee.status_histories).joinedload(
                EmployeeStatusHistory.employment_status,
            ),
            selectinload(Employee.contracts).joinedload(EmployeeContract.employment_type),
            selectinload(Employee.family_members).joinedload(EmployeeFamilyMember.relation),
            selectinload(Employee.bpjs_records).joinedload(EmployeeBpjs.bpjs_type),
            selectinload(Employee.documents).joinedload(EmployeeDocument.document_type),
            selectinload(Employee.movements).joinedload(EmployeeMovement.movement_type),
            selectinload(Employee.movements).joinedload(EmployeeMovement.from_estate),
            selectinload(Employee.movements).joinedload(EmployeeMovement.from_division),
            selectinload(Employee.movements).joinedload(EmployeeMovement.from_position),
            selectinload(Employee.movements).joinedload(EmployeeMovement.to_estate),
            selectinload(Employee.movements).joinedload(EmployeeMovement.to_division),
            selectinload(Employee.movements).joinedload(EmployeeMovement.to_position),
            selectinload(Employee.pay_profiles)
            .joinedload(EmployeePayProfile.wage_rate)
            .joinedload(WageRate.pay_type),
        )
    )
    return session.scalar(stmt)


def create_employee(session: Session, payload: Payload) -> Employee:
    employee = Employee(
        **_column_data(
            Employee,
            payload,
            exclude={"employee_id", "created_at", "updated_at"},
        ),
    )
    session.add(employee)
    session.flush()
    return employee


def update_employee(
    session: Session,
    employee_id: int,
    payload: Payload,
) -> Employee | None:
    employee = get_employee_by_id(session, employee_id)
    if employee is None:
        return None

    values = _column_data(
        Employee,
        payload,
        exclude={"employee_id", "created_at", "updated_at"},
    )
    for field_name, value in values.items():
        setattr(employee, field_name, value)

    session.flush()
    return employee


def soft_delete_employee(session: Session, employee_id: int) -> Employee | None:
    employee = get_employee_by_id(session, employee_id)
    if employee is None:
        return None

    employee.is_active = False
    session.flush()
    return employee


def change_employee_status(session: Session, payload: Payload) -> EmployeeStatusHistory:
    status_history = EmployeeStatusHistory(
        **_column_data(
            EmployeeStatusHistory,
            payload,
            exclude={"status_history_id", "created_at"},
        ),
    )
    session.add(status_history)
    session.flush()
    return status_history


def create_assignment(session: Session, payload: Payload) -> EmployeeAssignment:
    assignment = EmployeeAssignment(
        **_column_data(
            EmployeeAssignment,
            payload,
            exclude={"assignment_id", "created_at", "updated_at"},
        ),
    )
    session.add(assignment)
    session.flush()
    return assignment


def create_movement(session: Session, payload: Payload) -> EmployeeMovement:
    movement = EmployeeMovement(
        **_column_data(
            EmployeeMovement,
            payload,
            exclude={"movement_id", "created_at"},
        ),
    )
    session.add(movement)
    session.flush()
    return movement


def add_family_member(session: Session, payload: Payload) -> EmployeeFamilyMember:
    family_member = EmployeeFamilyMember(
        **_column_data(
            EmployeeFamilyMember,
            payload,
            exclude={"family_member_id", "created_at", "updated_at"},
        ),
    )
    session.add(family_member)
    session.flush()
    return family_member


def add_document(session: Session, payload: Payload) -> EmployeeDocument:
    document = EmployeeDocument(
        **_column_data(
            EmployeeDocument,
            payload,
            exclude={"document_id", "uploaded_at"},
        ),
    )
    session.add(document)
    session.flush()
    return document


def get_employee_history(session: Session, employee_id: int) -> dict[str, Sequence[Any]]:
    assignments = session.scalars(
        select(EmployeeAssignment)
        .where(EmployeeAssignment.employee_id == employee_id)
        .options(
            joinedload(EmployeeAssignment.estate),
            joinedload(EmployeeAssignment.division),
            joinedload(EmployeeAssignment.position),
            joinedload(EmployeeAssignment.category),
        )
        .order_by(desc(EmployeeAssignment.start_date), desc(EmployeeAssignment.assignment_id)),
    ).all()
    status_histories = session.scalars(
        select(EmployeeStatusHistory)
        .where(EmployeeStatusHistory.employee_id == employee_id)
        .options(joinedload(EmployeeStatusHistory.employment_status))
        .order_by(
            desc(EmployeeStatusHistory.effective_date),
            desc(EmployeeStatusHistory.status_history_id),
        ),
    ).all()
    contracts = session.scalars(
        select(EmployeeContract)
        .where(EmployeeContract.employee_id == employee_id)
        .options(joinedload(EmployeeContract.employment_type))
        .order_by(desc(EmployeeContract.start_date), desc(EmployeeContract.contract_id)),
    ).all()
    movements = session.scalars(
        select(EmployeeMovement)
        .where(EmployeeMovement.employee_id == employee_id)
        .options(
            joinedload(EmployeeMovement.movement_type),
            joinedload(EmployeeMovement.from_estate),
            joinedload(EmployeeMovement.from_division),
            joinedload(EmployeeMovement.from_position),
            joinedload(EmployeeMovement.to_estate),
            joinedload(EmployeeMovement.to_division),
            joinedload(EmployeeMovement.to_position),
        )
        .order_by(desc(EmployeeMovement.movement_date), desc(EmployeeMovement.movement_id)),
    ).all()

    return {
        "assignments": assignments,
        "status_histories": status_histories,
        "contracts": contracts,
        "movements": movements,
    }


__all__ = [
    "add_document",
    "add_family_member",
    "change_employee_status",
    "count_employees",
    "create_assignment",
    "create_employee",
    "create_movement",
    "get_employee_by_id",
    "get_employee_detail",
    "get_employee_history",
    "get_employee_list",
    "soft_delete_employee",
    "update_employee",
]
