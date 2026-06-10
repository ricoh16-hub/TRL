from __future__ import annotations

from pydantic import BaseModel, Field


class ManpowerBreakdownItem(BaseModel):
    key: str
    label: str
    headcount: int = Field(ge=0)
    active: int = Field(ge=0)
    inactive: int = Field(ge=0)


class ManpowerCoverageResponse(BaseModel):
    with_assignment: int = Field(ge=0)
    without_assignment: int = Field(ge=0)
    assignment_coverage: float = Field(ge=0, le=100)


class ManpowerSummaryResponse(BaseModel):
    total_headcount: int = Field(ge=0)
    active_headcount: int = Field(ge=0)
    inactive_headcount: int = Field(ge=0)
    status_breakdown: list[ManpowerBreakdownItem] = Field(default_factory=list)
    estate_breakdown: list[ManpowerBreakdownItem] = Field(default_factory=list)
    division_breakdown: list[ManpowerBreakdownItem] = Field(default_factory=list)
    category_breakdown: list[ManpowerBreakdownItem] = Field(default_factory=list)
    coverage: ManpowerCoverageResponse


__all__ = [
    "ManpowerBreakdownItem",
    "ManpowerCoverageResponse",
    "ManpowerSummaryResponse",
]
