from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AuthLoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=80)
    password: str = Field(..., min_length=1, max_length=255)


class AuthUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    employee_id: int | None = None
    username: str
    is_active: bool
    is_locked: bool
    failed_login_count: int
    last_login: datetime | None = None
    roles: list[str] = Field(default_factory=list)


class AuthLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: AuthUserResponse


__all__ = [
    "AuthLoginRequest",
    "AuthLoginResponse",
    "AuthUserResponse",
]
