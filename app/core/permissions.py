from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.auth import Permission, Role, RolePermission, User, UserRole
from app.services import auth_service

bearer_scheme = HTTPBearer(auto_error=False)

DbSession = Annotated[Session, Depends(get_db)]
BearerCredentials = Annotated[
    HTTPAuthorizationCredentials | None,
    Depends(bearer_scheme),
]


def _get_bearer_token(credentials: HTTPAuthorizationCredentials | None) -> str:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token wajib dikirim.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials


def _handle_auth_error(error: auth_service.AuthServiceError) -> None:
    if isinstance(error, auth_service.InvalidTokenError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(error),
            headers={"WWW-Authenticate": "Bearer"},
        ) from error
    if isinstance(error, auth_service.UserLockedError):
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail=str(error)) from error
    if isinstance(error, auth_service.UserInactiveError):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error)) from error

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Autentikasi tidak valid.",
        headers={"WWW-Authenticate": "Bearer"},
    ) from error


def _user_has_permission(
    session: Session,
    *,
    user_id: int,
    module_name: str,
    action_name: str,
) -> bool:
    stmt = (
        select(Permission.permission_id)
        .join(RolePermission, RolePermission.permission_id == Permission.permission_id)
        .join(Role, Role.role_id == RolePermission.role_id)
        .join(UserRole, UserRole.role_id == Role.role_id)
        .where(
            UserRole.user_id == user_id,
            Permission.module_name == module_name,
            Permission.action_name == action_name,
        )
        .limit(1)
    )
    return session.scalar(stmt) is not None


def require_permission(module_name: str, action_name: str) -> Callable[..., User]:
    def dependency(db: DbSession, credentials: BearerCredentials) -> User:
        token = _get_bearer_token(credentials)
        try:
            user = auth_service.get_current_user(db, token)
        except auth_service.AuthServiceError as error:
            _handle_auth_error(error)

        if not _user_has_permission(
            db,
            user_id=user.user_id,
            module_name=module_name,
            action_name=action_name,
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission {module_name}:{action_name} dibutuhkan.",
            )

        return user

    return dependency


__all__ = ["require_permission"]
