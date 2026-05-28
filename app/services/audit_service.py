from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models.audit import AuditLog


SENSITIVE_AUDIT_KEYS = {
    "address_text",
    "bank_account_name",
    "bank_account_no",
    "bpjs_number",
    "email",
    "file_path",
    "identity_number",
    "mobile_phone",
    "new_password",
    "new_pin",
    "old_password",
    "old_pin",
    "password",
    "password_hash",
    "password_salt",
    "pin",
    "pin_hash",
    "pin_salt",
}


def _mask_sensitive(key: str, value: Any) -> Any:
    if key.lower() not in SENSITIVE_AUDIT_KEYS or value in (None, ""):
        return value
    text_value = str(value)
    if len(text_value) <= 4:
        return "***"
    return f"***{text_value[-4:]}"


def _json_safe(value: Any) -> Any:
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, BaseModel):
        return _json_safe(value.model_dump())
    if isinstance(value, dict):
        return {
            str(key): _json_safe(_mask_sensitive(str(key), item))
            for key, item in value.items()
        }
    if isinstance(value, list | tuple):
        return [_json_safe(item) for item in value]
    return value


def create_audit_log(
    db: Session,
    user_id: int | None = None,
    module_name: str = "",
    action_name: str = "",
    table_name: str | None = None,
    record_id: str | int | None = None,
    old_data: dict[str, Any] | None = None,
    new_data: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    if not module_name or not action_name:
        raise ValueError("module_name dan action_name wajib diisi untuk audit log.")

    audit_log = AuditLog(
        user_id=user_id,
        module_name=module_name,
        action_name=action_name,
        table_name=table_name,
        record_id=str(record_id) if record_id is not None else None,
        old_data=_json_safe(old_data) if old_data is not None else None,
        new_data=_json_safe(new_data) if new_data is not None else None,
        ip_address=ip_address,
    )
    db.add(audit_log)
    db.flush()
    return audit_log


__all__ = ["create_audit_log"]
