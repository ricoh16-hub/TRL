from __future__ import annotations

from app.seed import HR_ADMIN_PERMISSION_KEYS, HR_VIEWER_PERMISSION_KEYS, SUPER_ADMIN_PERMISSION_KEYS
from app.services.audit_service import _json_safe


def test_audit_json_safe_masks_sensitive_hris_fields() -> None:
    payload = _json_safe(
        {
            "identity_number": "3201010101010001",
            "bpjs_number": "0001234567890",
            "bank_account_no": "9876543210",
            "full_name": "Alice",
            "nested": {"password_hash": "abcdef123456"},
        }
    )

    assert payload["identity_number"] == "***0001"
    assert payload["bpjs_number"] == "***7890"
    assert payload["bank_account_no"] == "***3210"
    assert payload["full_name"] == "Alice"
    assert payload["nested"]["password_hash"] == "***3456"


def test_seed_permission_matrix_covers_manpower_operations() -> None:
    expected = {
        "employee:view",
        "employee:create",
        "employee:update",
        "employee:change_status",
        "employee:delete",
        "employee:export",
        "data_quality:view",
        "manpower:view",
        "manpower:manage",
        "attendance:view",
        "attendance:manage",
        "work_output:view",
        "work_output:manage",
    }

    assert expected.issubset(set(SUPER_ADMIN_PERMISSION_KEYS))
    assert "employee:delete" not in set(HR_ADMIN_PERMISSION_KEYS)
    assert {"attendance:manage", "work_output:manage", "manpower:view"}.issubset(set(HR_ADMIN_PERMISSION_KEYS))
    assert "manpower:manage" not in set(HR_ADMIN_PERMISSION_KEYS)
    assert {"attendance:view", "work_output:view", "employee:export", "data_quality:view", "manpower:view"}.issubset(
        set(HR_VIEWER_PERMISSION_KEYS)
    )
    assert "attendance:manage" not in set(HR_VIEWER_PERMISSION_KEYS)
