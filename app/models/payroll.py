from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.reference import EmployeeCategory, PayType

if TYPE_CHECKING:
    from app.models.employee import Employee


class WageRate(Base):
    __tablename__ = "wage_rates"

    wage_rate_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    category_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("employee_categories.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    pay_type_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("pay_types.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    unit_name: Mapped[str] = mapped_column(String(60), nullable=False)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    expired_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    category: Mapped[EmployeeCategory] = relationship("EmployeeCategory")
    pay_type: Mapped[PayType] = relationship("PayType")
    employee_pay_profiles: Mapped[list[EmployeePayProfile]] = relationship(
        "EmployeePayProfile",
        back_populates="wage_rate",
    )


class EmployeePayProfile(Base):
    __tablename__ = "employee_pay_profiles"

    pay_profile_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    employee_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("employees.employee_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    wage_rate_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("wage_rates.wage_rate_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    rice_kg: Mapped[Decimal] = mapped_column(
        Numeric(8, 2),
        nullable=False,
        default=0,
        server_default="0",
    )
    bank_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    bank_account_no: Mapped[str | None] = mapped_column(String(80), nullable=True)
    bank_account_name: Mapped[str | None] = mapped_column(String(180), nullable=True)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    employee: Mapped[Employee] = relationship("Employee", back_populates="pay_profiles")
    wage_rate: Mapped[WageRate] = relationship(
        "WageRate",
        back_populates="employee_pay_profiles",
    )


__all__ = [
    "EmployeePayProfile",
    "WageRate",
]
