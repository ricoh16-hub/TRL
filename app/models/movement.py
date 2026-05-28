from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.reference import MovementType

if TYPE_CHECKING:
    from app.models.employee import Employee
    from app.models.organization import Division, Estate, Position


DEFAULT_MOVEMENT_TYPES: tuple[tuple[str, str], ...] = (
    ("MASUK", "Masuk"),
    ("MUTASI", "Mutasi"),
    ("PROMOSI", "Promosi"),
    ("DEMOSI", "Demosi"),
    ("CUTI", "Cuti"),
    ("KELUAR", "Keluar"),
    ("PERUBAHAN_DATA", "Perubahan Data"),
)


class EmployeeMovement(Base):
    __tablename__ = "employee_movements"

    movement_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    employee_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("employees.employee_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    movement_type_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("movement_types.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    from_estate_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("estates.estate_id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    from_division_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("divisions.division_id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    to_estate_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("estates.estate_id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    to_division_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("divisions.division_id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    from_position_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("positions.position_id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    to_position_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("positions.position_id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    movement_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    employee: Mapped[Employee] = relationship("Employee", back_populates="movements")
    movement_type: Mapped[MovementType] = relationship(
        "MovementType",
        back_populates="employee_movements",
    )
    from_estate: Mapped[Estate | None] = relationship("Estate", foreign_keys=[from_estate_id])
    from_division: Mapped[Division | None] = relationship(
        "Division",
        foreign_keys=[from_division_id],
    )
    to_estate: Mapped[Estate | None] = relationship("Estate", foreign_keys=[to_estate_id])
    to_division: Mapped[Division | None] = relationship("Division", foreign_keys=[to_division_id])
    from_position: Mapped[Position | None] = relationship(
        "Position",
        foreign_keys=[from_position_id],
    )
    to_position: Mapped[Position | None] = relationship("Position", foreign_keys=[to_position_id])


__all__ = [
    "DEFAULT_MOVEMENT_TYPES",
    "EmployeeMovement",
    "MovementType",
]
