from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.bpjs import EmployeeBpjs
    from app.models.document import EmployeeDocument
    from app.models.movement import EmployeeMovement
    from app.models.organization import Position


class ReferenceBaseMixin:
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
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


class Religion(ReferenceBaseMixin, Base):
    __tablename__ = "religions"


class EducationLevel(ReferenceBaseMixin, Base):
    __tablename__ = "education_levels"


class MaritalStatus(ReferenceBaseMixin, Base):
    __tablename__ = "marital_statuses"

    dependent_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )


class EmployeeCategory(ReferenceBaseMixin, Base):
    __tablename__ = "employee_categories"


class EmploymentStatus(ReferenceBaseMixin, Base):
    __tablename__ = "employment_statuses"


class EmploymentType(ReferenceBaseMixin, Base):
    __tablename__ = "employment_types"


class PayType(ReferenceBaseMixin, Base):
    __tablename__ = "pay_types"


class JobFamily(ReferenceBaseMixin, Base):
    __tablename__ = "job_families"

    positions: Mapped[list[Position]] = relationship("Position", back_populates="job_family")


class DocumentType(Base):
    __tablename__ = "document_types"

    document_type_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    document_type_name: Mapped[str] = mapped_column(String(150), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    employee_documents: Mapped[list[EmployeeDocument]] = relationship(
        "EmployeeDocument",
        back_populates="document_type",
    )


class BpjsType(Base):
    __tablename__ = "bpjs_types"

    bpjs_type_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    bpjs_type_name: Mapped[str] = mapped_column(String(150), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    employee_bpjs_records: Mapped[list[EmployeeBpjs]] = relationship(
        "EmployeeBpjs",
        back_populates="bpjs_type",
    )


class MovementType(ReferenceBaseMixin, Base):
    __tablename__ = "movement_types"

    employee_movements: Mapped[list[EmployeeMovement]] = relationship(
        "EmployeeMovement",
        back_populates="movement_type",
    )


class AttendanceCode(ReferenceBaseMixin, Base):
    __tablename__ = "attendance_codes"

    hk_value: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        default=0,
        server_default="0",
    )


__all__ = [
    "AttendanceCode",
    "BpjsType",
    "DocumentType",
    "EducationLevel",
    "EmployeeCategory",
    "EmploymentStatus",
    "EmploymentType",
    "JobFamily",
    "MaritalStatus",
    "MovementType",
    "PayType",
    "Religion",
]
