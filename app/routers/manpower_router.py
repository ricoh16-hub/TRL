from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.permissions import require_permission
from app.database.connection import get_db
from app.schemas.manpower_schema import ManpowerSummaryResponse
from app.services import manpower_service

router = APIRouter(prefix="/manpower", tags=["manpower"])

DbSession = Annotated[Session, Depends(get_db)]


@router.get(
    "/summary",
    response_model=ManpowerSummaryResponse,
    dependencies=[Depends(require_permission("manpower", "view"))],
)
def get_manpower_summary(db: DbSession) -> ManpowerSummaryResponse:
    return manpower_service.get_manpower_summary(db)


__all__ = ["router"]
