"""API router package."""

from app.routers.auth_router import router as auth_router
from app.routers.data_quality_router import router as data_quality_router
from app.routers.employee_router import router as employee_router
from app.routers.health import router as health_router
from app.routers.reference_router import router as reference_router

__all__ = [
    "auth_router",
    "data_quality_router",
    "employee_router",
    "health_router",
    "reference_router",
]
