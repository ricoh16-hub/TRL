from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.reference import JobFamily


class Company(Base):
    __tablename__ = "companies"

    company_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    company_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    company_name: Mapped[str] = mapped_column(String(180), nullable=False)
    company_alias: Mapped[str | None] = mapped_column(String(80), nullable=True)
    npwp: Mapped[str | None] = mapped_column(String(40), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    email: Mapped[str | None] = mapped_column(String(120), nullable=True)
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

    estates: Mapped[list[Estate]] = relationship(
        "Estate",
        back_populates="company",
        cascade="all, delete-orphan",
    )


class Estate(Base):
    __tablename__ = "estates"

    estate_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    company_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("companies.company_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    estate_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    estate_name: Mapped[str] = mapped_column(String(180), nullable=False)
    region: Mapped[str | None] = mapped_column(String(120), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_hectare: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
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

    company: Mapped[Company] = relationship("Company", back_populates="estates")
    divisions: Mapped[list[Division]] = relationship(
        "Division",
        back_populates="estate",
        cascade="all, delete-orphan",
    )


class Division(Base):
    __tablename__ = "divisions"

    division_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    estate_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("estates.estate_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    division_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    division_name: Mapped[str] = mapped_column(String(180), nullable=False)
    division_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    hectare_area: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
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

    estate: Mapped[Estate] = relationship("Estate", back_populates="divisions")


class Position(Base):
    __tablename__ = "positions"

    position_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    job_family_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("job_families.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    position_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    position_name: Mapped[str] = mapped_column(String(180), nullable=False)
    level_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    is_staff: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
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

    job_family: Mapped["JobFamily"] = relationship("JobFamily", back_populates="positions")


__all__ = [
    "Company",
    "Division",
    "Estate",
    "Position",
]
