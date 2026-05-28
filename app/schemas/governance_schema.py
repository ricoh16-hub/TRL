from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DataQualityIssueResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    issue_id: int
    issue_key: str
    issue_code: str
    severity: str
    status: str
    employee_id: int | None = None
    employee_no: str | None = None
    full_name: str | None = None
    source_period: str
    source_reference: str | None = None
    observed_value: str | None = None
    recommendation: str | None = None
    first_seen_at: datetime
    last_seen_at: datetime
    resolved_at: datetime | None = None


class DataQualitySummaryResponse(BaseModel):
    source_period: str | None = None
    open_total: int
    watch_total: int
    by_severity: dict[str, int]
    by_code: dict[str, int]


class DataQualityIssueUpdateRequest(BaseModel):
    status: Literal["OPEN", "RESOLVED", "IGNORED"] | None = None
    recommendation: str | None = Field(default=None, max_length=2000)


__all__ = [
    "DataQualityIssueResponse",
    "DataQualityIssueUpdateRequest",
    "DataQualitySummaryResponse",
]
