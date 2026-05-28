from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.employee import Employee


class ImportBatch(Base):
    __tablename__ = "import_batches"

    import_batch_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source_period: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    source_files: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    files_checksum: Mapped[str] = mapped_column(String(128), nullable=False)
    source_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    unique_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    imported_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    date_reviews: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="SUCCESS", server_default="SUCCESS")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class DataQualityIssue(Base):
    __tablename__ = "data_quality_issues"
    __table_args__ = (
        Index("ix_data_quality_issues_status", "status"),
        Index("ix_data_quality_issues_severity", "severity"),
        Index("ix_data_quality_issues_employee_id", "employee_id"),
        Index("ix_data_quality_issues_source_period", "source_period"),
    )

    issue_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    issue_key: Mapped[str] = mapped_column(String(180), unique=True, nullable=False)
    issue_code: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="OPEN", server_default="OPEN")
    employee_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("employees.employee_id", ondelete="SET NULL"),
        nullable=True,
    )
    source_period: Mapped[str] = mapped_column(String(32), nullable=False)
    source_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    observed_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    employee: Mapped[Employee | None] = relationship("Employee")
