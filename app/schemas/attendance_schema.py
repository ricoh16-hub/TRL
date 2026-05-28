from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class SchemaBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class AttendanceCreate(BaseModel):
    employee_id: int = Field(..., gt=0)
    attendance_code_id: int = Field(..., gt=0)
    attendance_date: date
    work_hours: Decimal = Field(default=Decimal("0"), ge=0, le=24)
    overtime_hours: Decimal = Field(default=Decimal("0"), ge=0, le=24)
    notes: str | None = None


class AttendanceResponse(SchemaBase):
    attendance_id: int
    employee_id: int
    attendance_code_id: int
    attendance_code: str | None = None
    attendance_date: date
    hk_value: Decimal = Decimal("0")
    work_hours: Decimal
    overtime_hours: Decimal
    notes: str | None = None
    created_at: datetime | None = None


class AttendanceSummaryResponse(BaseModel):
    period_start: date
    period_end: date
    records: int
    present: int
    exception: int
    absent: int
    total_hk: Decimal
    work_hours: Decimal
    overtime_hours: Decimal


class WorkOutputCreate(BaseModel):
    employee_id: int = Field(..., gt=0)
    job_family_id: int | None = Field(default=None, gt=0)
    work_date: date
    work_group_code: str | None = Field(default=None, max_length=80)
    activity_name: str = Field(..., min_length=1, max_length=160)
    quantity: Decimal = Field(default=Decimal("0"), ge=0)
    unit_name: str = Field(..., min_length=1, max_length=40)
    notes: str | None = None


class WorkOutputResponse(SchemaBase):
    work_output_id: int
    employee_id: int
    job_family_id: int | None = None
    job_family: str | None = None
    work_date: date
    work_group_code: str | None = None
    activity_name: str
    quantity: Decimal
    unit_name: str
    notes: str | None = None
    created_at: datetime | None = None


__all__ = [
    "AttendanceCreate",
    "AttendanceResponse",
    "AttendanceSummaryResponse",
    "WorkOutputCreate",
    "WorkOutputResponse",
]
