from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.schemas.auth_schema import AuthLoginRequest, AuthLoginResponse, AuthUserResponse
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])
bearer_scheme = HTTPBearer(auto_error=False)

DbSession = Annotated[Session, Depends(get_db)]
BearerCredentials = Annotated[
    HTTPAuthorizationCredentials | None,
    Depends(bearer_scheme),
]


def _auth_exception(error: Exception) -> HTTPException:
    if isinstance(error, auth_service.InvalidCredentialsError):
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(error),
            headers={"WWW-Authenticate": "Bearer"},
        )
    if isinstance(error, auth_service.InvalidTokenError):
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(error),
            headers={"WWW-Authenticate": "Bearer"},
        )
    if isinstance(error, auth_service.UserLockedError):
        return HTTPException(status_code=status.HTTP_423_LOCKED, detail=str(error))
    if isinstance(error, auth_service.UserInactiveError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error))

    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Terjadi kesalahan saat autentikasi.",
    )


def get_current_auth_user(
    db: DbSession,
    credentials: BearerCredentials,
) -> AuthUserResponse:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token wajib dikirim.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user = auth_service.get_current_user(db, credentials.credentials)
    except auth_service.AuthServiceError as error:
        raise _auth_exception(error) from error

    return auth_service.to_user_response(user)


@router.post("/login", response_model=AuthLoginResponse)
def login(payload: AuthLoginRequest, db: DbSession) -> AuthLoginResponse:
    try:
        result = auth_service.authenticate_user(
            db,
            username=payload.username,
            password=payload.password,
        )
        db.commit()
        return result
    except auth_service.AuthServiceError as error:
        # Failed login attempts mutate failed_login_count / is_locked.
        db.commit()
        raise _auth_exception(error) from error


@router.get("/me", response_model=AuthUserResponse)
def me(current_user: Annotated[AuthUserResponse, Depends(get_current_auth_user)]) -> AuthUserResponse:
    return current_user


__all__ = ["get_current_auth_user", "router"]
