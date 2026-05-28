from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, Index, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.reference import EducationLevel, MaritalStatus, Religion

if TYPE_CHECKING:
    from app.models.attendance import EmployeeAttendanceDaily, EmployeeWorkOutput
    from app.models.auth import User
    from app.models.bpjs import EmployeeBpjs
    from app.models.document import EmployeeDocument
    from app.models.employment import EmployeeAssignment, EmployeeContract, EmployeeStatusHistory
    from app.models.family import EmployeeFamilyMember
    from app.models.movement import EmployeeMovement
    from app.models.payroll import EmployeePayProfile


class Employee(Base):
    __tablename__ = "employees"

    employee_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    employee_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(180), nullable=False, index=True)
    gender: Mapped[str | None] = mapped_column(String(20), nullable=True)
    birth_place: Mapped[str | None] = mapped_column(String(120), nullable=True)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    religion_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("religions.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    education_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("education_levels.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    marital_status_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("marital_statuses.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    blood_type: Mapped[str | None] = mapped_column(String(5), nullable=True)
    mobile_phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    email: Mapped[str | None] = mapped_column(String(120), nullable=True)
    photo_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    religion: Mapped[Religion | None] = relationship("Religion")
    education: Mapped[EducationLevel | None] = relationship("EducationLevel")
    marital_status: Mapped[MaritalStatus | None] = relationship("MaritalStatus")
    identities: Mapped[list[EmployeeIdentity]] = relationship(
        "EmployeeIdentity",
        back_populates="employee",
        cascade="all, delete-orphan",
    )
    addresses: Mapped[list[EmployeeAddress]] = relationship(
        "EmployeeAddress",
        back_populates="employee",
        cascade="all, delete-orphan",
    )
    family_members: Mapped[list[EmployeeFamilyMember]] = relationship(
        "EmployeeFamilyMember",
        back_populates="employee",
        cascade="all, delete-orphan",
    )
    assignments: Mapped[list[EmployeeAssignment]] = relationship(
        "EmployeeAssignment",
        back_populates="employee",
        cascade="all, delete-orphan",
    )
    status_histories: Mapped[list[EmployeeStatusHistory]] = relationship(
        "EmployeeStatusHistory",
        back_populates="employee",
        cascade="all, delete-orphan",
    )
    contracts: Mapped[list[EmployeeContract]] = relationship(
        "EmployeeContract",
        back_populates="employee",
        cascade="all, delete-orphan",
    )
    movements: Mapped[list[EmployeeMovement]] = relationship(
        "EmployeeMovement",
        back_populates="employee",
        cascade="all, delete-orphan",
    )
    bpjs_records: Mapped[list[EmployeeBpjs]] = relationship(
        "EmployeeBpjs",
        back_populates="employee",
        cascade="all, delete-orphan",
    )
    documents: Mapped[list[EmployeeDocument]] = relationship(
        "EmployeeDocument",
        back_populates="employee",
        cascade="all, delete-orphan",
    )
    pay_profiles: Mapped[list[EmployeePayProfile]] = relationship(
        "EmployeePayProfile",
        back_populates="employee",
        cascade="all, delete-orphan",
    )
    attendance_records: Mapped[list[EmployeeAttendanceDaily]] = relationship(
        "EmployeeAttendanceDaily",
        back_populates="employee",
        cascade="all, delete-orphan",
    )
    work_outputs: Mapped[list[EmployeeWorkOutput]] = relationship(
        "EmployeeWorkOutput",
        back_populates="employee",
        cascade="all, delete-orphan",
    )
    users: Mapped[list[User]] = relationship("User", back_populates="employee")


class EmployeeIdentity(Base):
    __tablename__ = "employee_identities"
    __table_args__ = (
        Index(
            "uq_employee_identities_nik_number",
            "identity_number",
            unique=True,
            postgresql_where=text("upper(identity_type) IN ('NIK', 'KTP')"),
        ),
    )

    identity_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    employee_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("employees.employee_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    identity_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    identity_number: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    issue_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expire_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    employee: Mapped[Employee] = relationship("Employee", back_populates="identities")


class EmployeeAddress(Base):
    __tablename__ = "employee_addresses"

    address_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    employee_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("employees.employee_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    address_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    address_text: Mapped[str] = mapped_column(Text, nullable=False)
    province: Mapped[str | None] = mapped_column(String(120), nullable=True)
    regency: Mapped[str | None] = mapped_column(String(120), nullable=True)
    district: Mapped[str | None] = mapped_column(String(120), nullable=True)
    village: Mapped[str | None] = mapped_column(String(120), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    employee: Mapped[Employee] = relationship("Employee", back_populates="addresses")


__all__ = [
    "Employee",
    "EmployeeAddress",
    "EmployeeIdentity",
]
