from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.routers.attendance_router import router as attendance_router
from app.routers.auth_router import router as auth_router
from app.routers.data_quality_router import router as data_quality_router
from app.routers.employee_router import router as employee_router
from app.routers.health import router as health_router
from app.routers.reference_router import router as reference_router


def create_app() -> FastAPI:
    settings = get_settings()
    settings.validate_security()
    api = FastAPI(
        title=settings.app_name,
        version="0.1.0",
    )

    if settings.environment.lower() == "development":
        api.add_middleware(
            CORSMiddleware,
            allow_origin_regex=r"^http://(localhost|127\.0\.0\.1):\d+$",
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    api.include_router(health_router)
    api.include_router(auth_router)
    api.include_router(reference_router)
    api.include_router(employee_router)
    api.include_router(attendance_router)
    api.include_router(data_quality_router)

    return api


app = create_app()
