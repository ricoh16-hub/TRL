from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt

from app.core.config import get_settings


class TokenDecodeError(Exception):
    """Raised when a JWT access token is invalid or expired."""


def hash_password(password: str) -> str:
    password_bytes = password.encode("utf-8")
    return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(
    subject: str | int,
    *,
    additional_claims: dict[str, Any] | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    expires_at = now + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    claims: dict[str, Any] = {
        "sub": str(subject),
        "iat": now,
        "exp": expires_at,
    }
    if additional_claims:
        claims.update(additional_claims)

    return jwt.encode(
        claims,
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.PyJWTError as error:
        raise TokenDecodeError("Token tidak valid atau sudah kedaluwarsa.") from error

    if not payload.get("sub"):
        raise TokenDecodeError("Token tidak memiliki subject.")

    return payload


__all__ = [
    "TokenDecodeError",
    "create_access_token",
    "decode_access_token",
    "hash_password",
    "verify_password",
]
