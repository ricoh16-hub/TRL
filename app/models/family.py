from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.employee import Employee


class FamilyRelation(Base):
    __tablename__ = "family_relations"

    relation_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    relation_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    relation_name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    family_members: Mapped[list[EmployeeFamilyMember]] = relationship(
        "EmployeeFamilyMember",
        back_populates="relation",
    )


class EmployeeFamilyMember(Base):
    __tablename__ = "employee_family_members"

    family_member_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    employee_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("employees.employee_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    relation_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("family_relations.relation_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    full_name: Mapped[str] = mapped_column(String(180), nullable=False, index=True)
    gender: Mapped[str | None] = mapped_column(String(20), nullable=True)
    birth_place: Mapped[str | None] = mapped_column(String(120), nullable=True)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    education_level: Mapped[str | None] = mapped_column(String(120), nullable=True)
    dependent_flag: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
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

    employee: Mapped[Employee] = relationship("Employee", back_populates="family_members")
    relation: Mapped[FamilyRelation] = relationship(
        "FamilyRelation",
        back_populates="family_members",
    )


__all__ = [
    "EmployeeFamilyMember",
    "FamilyRelation",
]
