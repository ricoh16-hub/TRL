"""Service package for business logic."""

from app.services.audit_service import create_audit_log
from app.services.attendance_service import (
    AttendanceConflictError,
    AttendanceServiceError,
    AttendanceValidationError,
    create_attendance,
    create_work_output,
    list_attendance,
    list_work_outputs,
    summarize_attendance,
)
from app.services.auth_service import (
    AuthServiceError,
    InvalidCredentialsError,
    InvalidTokenError,
    UserInactiveError,
    UserLockedError,
    authenticate_user,
    get_current_user,
    to_user_response,
)

__all__ = [
    "AuthServiceError",
    "AttendanceConflictError",
    "AttendanceServiceError",
    "AttendanceValidationError",
    "InvalidCredentialsError",
    "InvalidTokenError",
    "UserInactiveError",
    "UserLockedError",
    "authenticate_user",
    "create_audit_log",
    "create_attendance",
    "create_work_output",
    "get_current_user",
    "list_attendance",
    "list_work_outputs",
    "summarize_attendance",
    "to_user_response",
]
