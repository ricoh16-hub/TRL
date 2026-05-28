from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.reference import BpjsType

if TYPE_CHECKING:
    from app.models.employee import Employee


class EmployeeBpjs(Base):
    __tablename__ = "employee_bpjs"

    employee_bpjs_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    employee_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("employees.employee_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    bpjs_type_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("bpjs_types.bpjs_type_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    bpjs_number: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    active_status: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    registered_date: Mapped[date | None] = mapped_column(Date, nullable=True)
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

    employee: Mapped[Employee] = relationship("Employee", back_populates="bpjs_records")
    bpjs_type: Mapped[BpjsType] = relationship(
        "BpjsType",
        back_populates="employee_bpjs_records",
    )


__all__ = [
    "BpjsType",
    "EmployeeBpjs",
]
