from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.config import get_settings
from app.core.security import (
    TokenDecodeError,
    create_access_token,
    decode_access_token,
    verify_password,
)
from app.models.auth import User, UserRole
from app.schemas.auth_schema import AuthLoginResponse, AuthUserResponse

MAX_FAILED_LOGIN = 5


class AuthServiceError(Exception):
    """Base exception for auth service failures."""


class InvalidCredentialsError(AuthServiceError):
    """Raised when username or password is invalid."""


class UserInactiveError(AuthServiceError):
    """Raised when the user exists but is inactive."""


class UserLockedError(AuthServiceError):
    """Raised when the user is locked."""


class InvalidTokenError(AuthServiceError):
    """Raised when an access token cannot be used."""


def _user_query() -> select[tuple[User]]:
    return select(User).options(
        selectinload(User.user_roles).joinedload(UserRole.role),
        joinedload(User.employee),
    )


def get_user_by_username(session: Session, username: str) -> User | None:
    return session.scalar(_user_query().where(User.username == username.strip()))


def get_user_by_id(session: Session, user_id: int) -> User | None:
    return session.scalar(_user_query().where(User.user_id == user_id))


def to_user_response(user: User) -> AuthUserResponse:
    return AuthUserResponse(
        user_id=user.user_id,
        employee_id=user.employee_id,
        username=user.username,
        is_active=user.is_active,
        is_locked=user.is_locked,
        failed_login_count=user.failed_login_count,
        last_login=user.last_login,
        roles=[user_role.role.role_name for user_role in user.user_roles if user_role.role],
    )


def authenticate_user(
    session: Session,
    *,
    username: str,
    password: str,
) -> AuthLoginResponse:
    user = get_user_by_username(session, username)
    if user is None:
        raise InvalidCredentialsError("Username atau password tidak valid.")

    if not user.is_active:
        raise UserInactiveError("User tidak aktif.")

    if user.is_locked:
        raise UserLockedError("User terkunci.")

    if not verify_password(password, user.password_hash):
        user.failed_login_count += 1
        if user.failed_login_count >= MAX_FAILED_LOGIN:
            user.is_locked = True
            session.flush()
            raise UserLockedError("User terkunci karena gagal login 5 kali.")

        session.flush()
        raise InvalidCredentialsError("Username atau password tidak valid.")

    user.failed_login_count = 0
    user.last_login = datetime.now(UTC)
    session.flush()

    settings = get_settings()
    access_token = create_access_token(
        user.user_id,
        additional_claims={"username": user.username},
    )
    return AuthLoginResponse(
        access_token=access_token,
        expires_in=settings.access_token_expire_minutes * 60,
        user=to_user_response(user),
    )


def get_current_user(session: Session, token: str) -> User:
    try:
        payload = decode_access_token(token)
    except TokenDecodeError as error:
        raise InvalidTokenError(str(error)) from error
    try:
        user_id = int(payload["sub"])
    except (TypeError, ValueError) as error:
        raise InvalidTokenError("Subject token tidak valid.") from error

    user = get_user_by_id(session, user_id)
    if user is None:
        raise InvalidTokenError("User token tidak ditemukan.")
    if not user.is_active:
        raise UserInactiveError("User tidak aktif.")
    if user.is_locked:
        raise UserLockedError("User terkunci.")

    return user


__all__ = [
    "AuthServiceError",
    "InvalidCredentialsError",
    "InvalidTokenError",
    "UserInactiveError",
    "UserLockedError",
    "authenticate_user",
    "get_current_user",
    "get_user_by_id",
    "get_user_by_username",
    "to_user_response",
]
