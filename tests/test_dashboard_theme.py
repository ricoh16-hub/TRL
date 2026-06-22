import os
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication, QToolButton, QWidget

from src.ui.dashboard import (
    CHARGING_ACCENT,
    CHARGING_MODE_LABEL,
    ChangePasswordDialog,
    DashboardBackground,
    DashboardForm,
    LoginGlassPanel,
    NOT_CHARGING_MODE_LABEL,
    UserAddDialog,
    UserEditDialog,
    _charging_theme_palette,
    _resolve_charging_state,
)
from src.ui.hris_dashboard_data import (
    HRIS_GROUP_BREAKDOWN_FALLBACK,
    HRIS_SUMMARY_DEFAULTS,
    HRIS_SUMMARY_TABLES,
    current_user_has_permission,
    export_hris_quality_issues,
    format_hris_quality_issue_row,
    map_hris_role_to_dashboard_role,
    read_hris_employee_detail,
    read_hris_employee_id_for_issue,
    read_hris_group_breakdown,
    read_hris_quality_issues,
    read_hris_summary,
    update_hris_quality_issue_statuses,
)


def _get_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_resolve_charging_state_handles_missing_info() -> None:
    assert _resolve_charging_state(None) is False
    assert _resolve_charging_state({}) is False


def test_resolve_charging_state_reads_boolean_flag() -> None:
    assert _resolve_charging_state({"charging": True}) is True
    assert _resolve_charging_state({"charging": False}) is False


def test_resolve_charging_state_reads_integer_flag() -> None:
    assert _resolve_charging_state({"charging": 1}) is True
    assert _resolve_charging_state({"charging": 0}) is False


def test_charging_theme_palette_for_charging_mode() -> None:
    palette = _charging_theme_palette(True)

    assert palette["accent"] == CHARGING_ACCENT
    assert palette["hover"] == "#3AA8F5"
    assert palette["pressed"] == "#2A96E0"
    assert palette["badge_label"] == CHARGING_MODE_LABEL


def test_charging_theme_palette_for_standard_mode() -> None:
    palette = _charging_theme_palette(False)

    assert palette["accent"] == "#FFFFFF"
    assert palette["hover"] == "#DDE6F2"
    assert palette["pressed"] == "#AEBBCC"
    assert palette["badge_label"] == NOT_CHARGING_MODE_LABEL


def test_dashboard_glass_surfaces_render_both_charging_states() -> None:
    _get_app()
    widgets = [DashboardBackground(), LoginGlassPanel(5.0)]

    try:
        for widget in widgets:
            widget.resize(320, 180)
            for charging in (False, True):
                widget.set_charging(charging)
                pixmap = QPixmap(widget.size())
                pixmap.fill(Qt.GlobalColor.transparent)
                widget.render(pixmap)
                image = pixmap.toImage()

                assert image.pixelColor(widget.width() // 2, widget.height() // 2).alpha() > 0
    finally:
        for widget in widgets:
            widget.close()


def test_dashboard_dialogs_render_both_charging_states() -> None:
    _get_app()

    for charging in (False, True):
        parent = QWidget()
        parent._charging = charging  # type: ignore[attr-defined]
        dialogs = [
            ChangePasswordDialog("operator", parent),
            UserAddDialog(parent),
            UserEditDialog(
                username="operator",
                nama="Operator",
                role="Operator",
                status="Active",
                parent=parent,
            ),
        ]

        try:
            for dialog in dialogs:
                dialog.resize(dialog.sizeHint())
                pixmap = QPixmap(dialog.size())
                pixmap.fill(Qt.GlobalColor.transparent)
                dialog.render(pixmap)
                image = pixmap.toImage()

                assert "background: transparent" in dialog.styleSheet()
                assert image.pixelColor(dialog.width() // 2, dialog.height() // 2).alpha() > 0
        finally:
            for dialog in dialogs:
                dialog.close()
            parent.close()


def test_user_edit_dialog_can_clear_failed_verification_fields() -> None:
    _get_app()
    dialog = UserEditDialog(
        username="operator",
        nama="Operator",
        role="Operator",
        status="Active",
    )

    try:
        close_btn = dialog.findChild(QToolButton, "dashboardDialogClose")
        assert close_btn is not None
        assert close_btn.accessibleName() == "Close"
        assert dialog.windowFlags() & Qt.WindowType.FramelessWindowHint

        dialog._old_password_input.setText("wrong-password")  # type: ignore[attr-defined]
        dialog._old_pin_input.setText("123456")  # type: ignore[attr-defined]

        dialog.reset_password_verification()
        dialog.reset_pin_verification()

        assert dialog._old_password_input.text() == ""  # type: ignore[attr-defined]
        assert dialog._old_pin_input.text() == ""  # type: ignore[attr-defined]
    finally:
        dialog.close()


def test_hris_quality_permission_allows_active_superior_and_administrator() -> None:
    dashboard = DashboardForm.__new__(DashboardForm)
    dashboard._current_user_has_permission = lambda _module, _action: None  # type: ignore[method-assign]

    dashboard._get_current_user_access_profile = lambda: ("Superior", "Active")  # type: ignore[method-assign]
    assert dashboard._can_current_user_manage_hris_quality() is True

    dashboard._get_current_user_access_profile = lambda: ("Administrator", "Active")  # type: ignore[method-assign]
    assert dashboard._can_current_user_manage_hris_quality() is True


def test_hris_quality_permission_blocks_inactive_or_lower_roles() -> None:
    dashboard = DashboardForm.__new__(DashboardForm)
    dashboard._current_user_has_permission = lambda _module, _action: None  # type: ignore[method-assign]

    dashboard._get_current_user_access_profile = lambda: ("Administrator", "Inactive")  # type: ignore[method-assign]
    assert dashboard._can_current_user_manage_hris_quality() is False

    dashboard._get_current_user_access_profile = lambda: ("Operator", "Active")  # type: ignore[method-assign]
    assert dashboard._can_current_user_manage_hris_quality() is False


def test_hris_quality_permission_prefers_database_permission() -> None:
    dashboard = DashboardForm.__new__(DashboardForm)

    dashboard._current_user_has_permission = lambda module, action: (module, action) == ("data_quality", "update")  # type: ignore[method-assign]
    dashboard._get_current_user_access_profile = lambda: ("Operator", "Active")  # type: ignore[method-assign]

    assert dashboard._can_current_user_manage_hris_quality() is True


def test_hris_quality_permission_database_denial_blocks_admin_fallback() -> None:
    dashboard = DashboardForm.__new__(DashboardForm)

    dashboard._current_user_has_permission = lambda _module, _action: False  # type: ignore[method-assign]
    dashboard._get_current_user_access_profile = lambda: ("Administrator", "Active")  # type: ignore[method-assign]

    assert dashboard._can_current_user_manage_hris_quality() is False


def test_hris_quality_export_permission_uses_database_permission() -> None:
    dashboard = DashboardForm.__new__(DashboardForm)

    dashboard._current_user_has_permission = lambda module, action: (module, action) == ("data_quality", "export")  # type: ignore[method-assign]
    dashboard._get_current_user_access_profile = lambda: ("Operator", "Active")  # type: ignore[method-assign]

    assert dashboard._can_current_user_export_hris_quality() is True


def test_hris_quality_export_permission_database_denial_blocks_auditor_fallback() -> None:
    dashboard = DashboardForm.__new__(DashboardForm)

    dashboard._current_user_has_permission = lambda _module, _action: False  # type: ignore[method-assign]
    dashboard._get_current_user_access_profile = lambda: ("Auditor", "Active")  # type: ignore[method-assign]

    assert dashboard._can_current_user_export_hris_quality() is False


def test_user_management_allows_active_superior_without_status_text(monkeypatch) -> None:  # noqa: ANN001
    class FakeResult:
        def mappings(self) -> "FakeResult":
            return self

        def first(self) -> dict[str, object]:
            return {
                "user_id": 7,
                "is_active": True,
                "is_locked": False,
                "status": None,
                "role_names": ["SUPER_ADMIN"],
            }

    class FakeSession:
        def execute(self, _statement, _params):  # noqa: ANN001, ANN201
            return FakeResult()

        def close(self) -> None:
            pass

    dashboard = DashboardForm.__new__(DashboardForm)
    dashboard._user = type("UserStub", (), {"id": 7, "role": "Operator", "status": "nonaktif"})()

    monkeypatch.setattr("src.ui.dashboard.Session", lambda: FakeSession())
    monkeypatch.setattr("src.ui.dashboard._is_hris_auth_schema", lambda _session: True)

    assert dashboard._get_current_user_access_profile() == ("Superior", "Active")
    assert dashboard._can_current_user_manage_user_actions() is True


def test_user_management_allows_active_administrator_actions() -> None:
    dashboard = DashboardForm.__new__(DashboardForm)
    dashboard._get_current_user_access_profile = lambda: ("Administrator", "Active")  # type: ignore[method-assign]

    assert dashboard._can_current_user_manage_user_actions() is True


def test_user_management_blocks_inactive_or_operator_actions() -> None:
    dashboard = DashboardForm.__new__(DashboardForm)

    dashboard._get_current_user_access_profile = lambda: ("Administrator", "Inactive")  # type: ignore[method-assign]
    assert dashboard._can_current_user_manage_user_actions() is False

    dashboard._get_current_user_access_profile = lambda: ("Operator", "Active")  # type: ignore[method-assign]
    assert dashboard._can_current_user_manage_user_actions() is False


def test_user_management_new_user_role_scope_by_current_role() -> None:
    dashboard = DashboardForm.__new__(DashboardForm)

    dashboard._get_current_user_access_profile = lambda: ("Superior", "Active")  # type: ignore[method-assign]
    assert dashboard._allowed_roles_for_new_user() == ["Superior", "Administrator", "Operator", "Auditor"]
    assert dashboard._can_current_user_assign_new_user_role("Superior") is True

    dashboard._get_current_user_access_profile = lambda: ("Administrator", "Active")  # type: ignore[method-assign]
    assert dashboard._allowed_roles_for_new_user() == ["Administrator", "Operator", "Auditor"]
    assert dashboard._can_current_user_assign_new_user_role("Superior") is False
    assert dashboard._can_current_user_assign_new_user_role("Operator") is True

    dashboard._get_current_user_access_profile = lambda: ("Operator", "Active")  # type: ignore[method-assign]
    assert dashboard._allowed_roles_for_new_user() == ["Operator", "Auditor"]
    assert dashboard._can_current_user_assign_new_user_role("Administrator") is False
    assert dashboard._can_current_user_assign_new_user_role("Auditor") is True

    dashboard._get_current_user_access_profile = lambda: ("Auditor", "Active")  # type: ignore[method-assign]
    assert dashboard._allowed_roles_for_new_user() == ["Auditor"]
    assert dashboard._can_current_user_assign_new_user_role("Operator") is False
    assert dashboard._can_current_user_assign_new_user_role("Auditor") is True


def test_user_management_audit_writes_structured_schema(monkeypatch) -> None:  # noqa: ANN001
    class FakeSession:
        def __init__(self) -> None:
            self.calls = []

        def execute(self, statement, params):  # noqa: ANN001, ANN201
            self.calls.append((str(statement), params))
            return SimpleNamespace(rowcount=1)

    session = FakeSession()
    dashboard = DashboardForm.__new__(DashboardForm)
    dashboard.current_user_id = lambda: 7  # type: ignore[method-assign]
    dashboard._current_actor_label = lambda: "admin (Superior)"  # type: ignore[method-assign]
    dashboard._current_actor_username = lambda: "admin"  # type: ignore[method-assign]

    monkeypatch.setattr("src.ui.dashboard._table_exists", lambda _session, table_name: table_name == "audit_logs")
    monkeypatch.setattr(
        "src.ui.dashboard._table_columns",
        lambda _session, _table_name: {
            "user_id",
            "module_name",
            "action_name",
            "table_name",
            "record_id",
            "old_data",
            "new_data",
            "created_at",
        },
    )

    dashboard._write_user_management_audit(
        session,
        action_name="role_changed",
        target_user_id=10,
        target_username="operator01",
        description="Role changed by admin (Superior) for user 'operator01': Auditor -> Operator.",
        old_data={"role": "Auditor"},
        new_data={"role": "Operator"},
    )

    sql, params = session.calls[0]
    assert "INSERT INTO audit_logs" in sql
    assert params["user_id"] == 7
    assert params["module_name"] == "user_management"
    assert params["action_name"] == "role_changed"
    assert params["record_id"] == "10"
    assert "Role changed by admin" in params["new_data"]
    assert '"actor_username": "admin"' in params["new_data"]
    assert '"role": "Operator"' in params["new_data"]


def test_user_management_audit_writes_legacy_schema(monkeypatch) -> None:  # noqa: ANN001
    class FakeSession:
        def __init__(self) -> None:
            self.added = []

        def add(self, value):  # noqa: ANN001, ANN201
            self.added.append(value)

    session = FakeSession()
    dashboard = DashboardForm.__new__(DashboardForm)
    dashboard.current_user_id = lambda: 7  # type: ignore[method-assign]
    dashboard._current_actor_label = lambda: "admin (Superior)"  # type: ignore[method-assign]
    dashboard._current_actor_username = lambda: "admin"  # type: ignore[method-assign]

    monkeypatch.setattr("src.ui.dashboard._table_exists", lambda _session, table_name: table_name == "audit_logs")
    monkeypatch.setattr(
        "src.ui.dashboard._table_columns",
        lambda _session, _table_name: {"user_id", "action", "action_type", "description", "created_at"},
    )

    dashboard._write_user_management_audit(
        session,
        action_name="user_created",
        target_user_id=10,
        target_username="operator01",
        description="User created by admin (Superior): 'operator01' with role Operator and status Active.",
        new_data={"role": "Operator", "status": "Active"},
    )

    audit_log = session.added[0]
    assert audit_log.user_id == 7
    assert audit_log.action == "user_management.user_created"
    assert audit_log.action_type == "user_management"
    assert audit_log.description.startswith("User created by admin")


def test_dashboard_logout_records_last_logout(monkeypatch) -> None:  # noqa: ANN001
    class FakeSession:
        def __init__(self) -> None:
            self.calls = []
            self.committed = False
            self.closed = False
            self.rolled_back = False

        def execute(self, statement, params):  # noqa: ANN001, ANN201
            self.calls.append((str(statement), params))
            return SimpleNamespace(rowcount=1)

        def commit(self) -> None:
            self.committed = True

        def rollback(self) -> None:
            self.rolled_back = True

        def close(self) -> None:
            self.closed = True

    session = FakeSession()
    dashboard = DashboardForm.__new__(DashboardForm)
    dashboard._logout_recorded = False
    dashboard.current_user_id = lambda: 12  # type: ignore[method-assign]

    monkeypatch.setattr("src.ui.dashboard.Session", lambda: session)
    monkeypatch.setattr("src.ui.dashboard._is_hris_auth_schema", lambda _session: False)
    monkeypatch.setattr(
        "src.ui.dashboard._table_columns",
        lambda _session, _table_name: {"id", "last_logout", "updated_at"},
    )

    dashboard._record_current_user_logout()

    sql, params = session.calls[0]
    assert "last_logout = CURRENT_TIMESTAMP" in sql
    assert "updated_at = CURRENT_TIMESTAMP" in sql
    assert "WHERE id = :user_id" in sql
    assert params["user_id"] == 12
    assert session.committed is True
    assert session.closed is True
    assert dashboard._logout_recorded is True


def test_hris_data_warning_label_only_renders_when_summary_warns() -> None:
    _get_app()
    dashboard = DashboardForm.__new__(DashboardForm)
    dashboard._dashboard_badges = []

    assert dashboard._make_hris_data_warning_label({"data_warning": "0"}) is None

    label = dashboard._make_hris_data_warning_label({"data_warning": "1"})

    assert label is not None
    assert "Data sync warning" in label.text()
    assert label in dashboard._dashboard_badges


def test_hris_quality_export_audit_writes_new_schema_payload(monkeypatch, tmp_path) -> None:  # noqa: ANN001
    class FakeSession:
        def __init__(self) -> None:
            self.calls = []
            self.closed = False
            self.committed = False

        def execute(self, statement, params):  # noqa: ANN001, ANN201
            self.calls.append((str(statement), params))

        def commit(self) -> None:
            self.committed = True

        def rollback(self) -> None:
            raise AssertionError("rollback should not be called")

        def close(self) -> None:
            self.closed = True

    class NowStub:
        def strftime(self, _fmt: str) -> str:
            return "20260528_101500"

    class DateTimeStub:
        @staticmethod
        def now() -> NowStub:
            return NowStub()

    session = FakeSession()
    monkeypatch.setattr("src.ui.hris_dashboard_data.datetime", DateTimeStub)

    output_path = export_hris_quality_issues(
        [
            {
                "issue_id": 1,
                "employee_id": 2,
                "severity": "BLOCKING",
                "status": "OPEN",
                "issue": "Missing Identity",
                "employee": "EMP-1 - Staff",
                "division": "DIV A",
                "age_days": "3d",
                "sla": "Overdue 1d",
                "observed": "-",
                "recommendation": "Review source",
            }
        ],
        reports_dir=tmp_path,
        session_factory=lambda: session,
        table_exists=lambda _session, table_name: table_name == "audit_logs",
        table_columns=lambda _session, _table_name: {
            "user_id",
            "module_name",
            "action_name",
            "table_name",
            "record_id",
            "new_data",
            "created_at",
        },
        user_id=42,
        status_filter="OPEN",
        severity_filter="BLOCKING",
        search_text="nik",
    )

    assert output_path.name == "hris_quality_filtered_20260528_101500.csv"
    assert len(session.calls) == 1
    sql, params = session.calls[0]
    assert "'data_quality', 'export', 'data_quality_issues'" in sql
    assert params["user_id"] == 42
    assert params["record_id"] == "hris_quality_filtered_20260528_101500.csv"
    assert '"row_count": 1' in params["new_data"]
    assert '"status": "OPEN"' in params["new_data"]
    assert '"severity": "BLOCKING"' in params["new_data"]
    assert '"search": "nik"' in params["new_data"]
    assert session.committed is True
    assert session.closed is True


def test_read_hris_group_breakdown_returns_fallback_and_closes_session() -> None:
    class FakeSession:
        def __init__(self) -> None:
            self.closed = False

        def execute(self, _statement):  # noqa: ANN001, ANN201
            raise RuntimeError("database unavailable")

        def close(self) -> None:
            self.closed = True

    session = FakeSession()

    rows = read_hris_group_breakdown(lambda: session, lambda _session, _table_name: False)

    assert rows == HRIS_GROUP_BREAKDOWN_FALLBACK
    assert session.closed is True


def test_read_hris_summary_returns_defaults_and_closes_session_without_tables() -> None:
    class FakeSession:
        def __init__(self) -> None:
            self.closed = False

        def close(self) -> None:
            self.closed = True

    session = FakeSession()

    summary = read_hris_summary(
        lambda: session,
        lambda _session, _table_name: False,
        lambda _session, _table_name: set(),
    )

    assert summary["employees"] == "0"
    assert summary["data_warning"] == "0"
    assert session.closed is True


def test_read_hris_quality_issues_returns_empty_and_closes_session_on_error() -> None:
    class FakeSession:
        def __init__(self) -> None:
            self.closed = False

        def execute(self, _statement, _params):  # noqa: ANN001, ANN201
            raise RuntimeError("database unavailable")

        def close(self) -> None:
            self.closed = True

    session = FakeSession()

    rows = read_hris_quality_issues(
        lambda: session,
        lambda _session, table_name: table_name == "data_quality_issues",
        status_value="OPEN",
        severity_value="ALL",
        search_value="nik",
    )

    assert rows == []
    assert session.closed is True


def test_read_hris_employee_detail_returns_none_and_closes_session_on_error() -> None:
    class FakeSession:
        def __init__(self) -> None:
            self.closed = False

        def execute(self, _statement, _params):  # noqa: ANN001, ANN201
            raise RuntimeError("database unavailable")

        def close(self) -> None:
            self.closed = True

    session = FakeSession()

    detail = read_hris_employee_detail(
        lambda: session,
        lambda _session, table_name: table_name == "employees",
        employee_id=1,
        issue_id=2,
    )

    assert detail is None
    assert session.closed is True


def test_read_hris_employee_id_for_issue_returns_zero_and_closes_session_on_error() -> None:
    class FakeSession:
        def __init__(self) -> None:
            self.closed = False

        def execute(self, _statement, _params):  # noqa: ANN001, ANN201
            raise RuntimeError("database unavailable")

        def close(self) -> None:
            self.closed = True

    session = FakeSession()

    employee_id = read_hris_employee_id_for_issue(lambda: session, issue_id=10)

    assert employee_id == 0
    assert session.closed is True


def test_update_hris_quality_issue_statuses_rolls_back_and_closes_session_on_error() -> None:
    class FakeSession:
        def __init__(self) -> None:
            self.closed = False
            self.rolled_back = False

        def execute(self, _statement, _params):  # noqa: ANN001, ANN201
            raise RuntimeError("database unavailable")

        def rollback(self) -> None:
            self.rolled_back = True

        def close(self) -> None:
            self.closed = True

    session = FakeSession()

    updated, error_message = update_hris_quality_issue_statuses(
        lambda: session,
        lambda _session, table_name: table_name == "data_quality_issues",
        lambda _session, _table_name: set(),
        user_id=42,
        issue_ids=[1, 2],
        status="FIXED",
    )

    assert updated is False
    assert "database unavailable" in error_message
    assert session.rolled_back is True
    assert session.closed is True


def test_current_user_has_permission_returns_none_and_closes_when_schema_missing() -> None:
    class FakeSession:
        def __init__(self) -> None:
            self.closed = False

        def close(self) -> None:
            self.closed = True

    session = FakeSession()

    result = current_user_has_permission(
        lambda: session,
        lambda _session, _table_name: False,
        lambda _session, _table_name: set(),
        user_id=42,
        module_name="data_quality",
        action_name="update",
    )

    assert result is None
    assert session.closed is True


def test_format_hris_quality_issue_row_calculates_sla() -> None:
    row = format_hris_quality_issue_row(
        issue_id=10,
        employee_id=20,
        severity="BLOCKING",
        status="OPEN",
        issue="Missing Identity",
        employee="EMP-1 - Staff",
        division="DIV A",
        age_days=3,
        observed="-",
        recommendation="Review source",
    )

    assert row["sla"] == "Overdue 1d"
    assert row["age_days"] == "3d"


def test_map_hris_role_to_dashboard_role_prefers_canonical_dashboard_roles() -> None:
    assert map_hris_role_to_dashboard_role(["SUPER_ADMIN", "HR_VIEWER"]) == "Superior"
    assert map_hris_role_to_dashboard_role(["HR_ADMIN"]) == "Administrator"
    assert map_hris_role_to_dashboard_role(["OPERATOR"]) == "Operator"
    assert map_hris_role_to_dashboard_role(["HR_VIEWER"]) == "Auditor"
    assert map_hris_role_to_dashboard_role([]) == "Operator"


def test_hris_summary_defaults_include_warning_flag() -> None:
    summary = dict(HRIS_SUMMARY_DEFAULTS)

    summary["data_warning"] = "1"

    assert HRIS_SUMMARY_DEFAULTS["data_warning"] == "0"
    assert HRIS_SUMMARY_DEFAULTS["employees"] == "0"


def test_hris_summary_tables_include_quality_and_attendance_sources() -> None:
    assert "data_quality_issues" in HRIS_SUMMARY_TABLES
    assert "employee_attendance_daily" in HRIS_SUMMARY_TABLES
    assert "employee_work_outputs" in HRIS_SUMMARY_TABLES
