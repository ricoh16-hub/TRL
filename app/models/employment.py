from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, Index, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.employee import Employee
    from app.models.organization import Division, Estate, Position
    from app.models.reference import EmployeeCategory, EmploymentStatus, EmploymentType


class EmployeeAssignment(Base):
    __tablename__ = "employee_assignments"
    __table_args__ = (
        Index(
            "uq_employee_assignments_current_employee",
            "employee_id",
            unique=True,
            postgresql_where=text("is_current IS TRUE"),
        ),
    )

    assignment_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    employee_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("employees.employee_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    estate_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("estates.estate_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    division_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("divisions.division_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    position_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("positions.position_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    category_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("employee_categories.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_current: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        index=True,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
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

    employee: Mapped[Employee] = relationship("Employee", back_populates="assignments")
    estate: Mapped[Estate] = relationship("Estate")
    division: Mapped[Division] = relationship("Division")
    position: Mapped[Position] = relationship("Position")
    category: Mapped[EmployeeCategory] = relationship("EmployeeCategory")


class EmployeeStatusHistory(Base):
    __tablename__ = "employee_status_histories"
    __table_args__ = (
        Index(
            "ix_employee_status_histories_employee_effective",
            "employee_id",
            "effective_date",
        ),
    )

    status_history_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    employee_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("employees.employee_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    employment_status_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("employment_statuses.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    effective_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    employee: Mapped[Employee] = relationship("Employee", back_populates="status_histories")
    employment_status: Mapped[EmploymentStatus] = relationship("EmploymentStatus")


class EmployeeContract(Base):
    __tablename__ = "employee_contracts"

    contract_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    employee_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("employees.employee_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    employment_type_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("employment_types.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    contract_no: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    salary_type: Mapped[str | None] = mapped_column(String(60), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
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

    employee: Mapped[Employee] = relationship("Employee", back_populates="contracts")
    employment_type: Mapped[EmploymentType] = relationship("EmploymentType")


__all__ = [
    "EmployeeAssignment",
    "EmployeeContract",
    "EmployeeStatusHistory",
]
