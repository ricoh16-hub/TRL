from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Index, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.employee import Employee
    from app.models.reference import AttendanceCode, JobFamily


class EmployeeAttendanceDaily(Base):
    __tablename__ = "employee_attendance_daily"
    __table_args__ = (
        UniqueConstraint("employee_id", "attendance_date", name="uq_employee_attendance_employee_date"),
        Index("ix_employee_attendance_date", "attendance_date"),
        Index("ix_employee_attendance_employee_id", "employee_id"),
    )

    attendance_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("employees.employee_id", ondelete="CASCADE"),
        nullable=False,
    )
    attendance_code_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("attendance_codes.id", ondelete="RESTRICT"),
        nullable=False,
    )
    attendance_date: Mapped[date] = mapped_column(Date, nullable=False)
    work_hours: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=0, server_default="0")
    overtime_hours: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=0, server_default="0")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    employee: Mapped[Employee] = relationship("Employee", back_populates="attendance_records")
    attendance_code: Mapped[AttendanceCode] = relationship("AttendanceCode")


class EmployeeWorkOutput(Base):
    __tablename__ = "employee_work_outputs"
    __table_args__ = (
        Index("ix_employee_work_outputs_work_date", "work_date"),
        Index("ix_employee_work_outputs_employee_id", "employee_id"),
        Index("ix_employee_work_outputs_job_family_id", "job_family_id"),
    )

    work_output_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("employees.employee_id", ondelete="CASCADE"),
        nullable=False,
    )
    job_family_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("job_families.id", ondelete="SET NULL"),
        nullable=True,
    )
    work_date: Mapped[date] = mapped_column(Date, nullable=False)
    work_group_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    activity_name: Mapped[str] = mapped_column(String(160), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0, server_default="0")
    unit_name: Mapped[str] = mapped_column(String(40), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    employee: Mapped[Employee] = relationship("Employee", back_populates="work_outputs")
    job_family: Mapped[JobFamily | None] = relationship("JobFamily")


__all__ = ["EmployeeAttendanceDaily", "EmployeeWorkOutput"]
