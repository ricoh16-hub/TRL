from __future__ import annotations

import csv
import json
import logging
from collections.abc import Callable
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, TypedDict

from sqlalchemy import inspect, text

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPORTS_DIR = PROJECT_ROOT / "reports"

HrisGroupBreakdownRow = tuple[str, str, str, str]
HRIS_AUTH_SCHEMA_COLUMNS = {"user_id", "username", "password_hash", "is_active", "is_locked"}
HRIS_SUMMARY_DEFAULTS: dict[str, str] = {
    "employees": "0",
    "active_employees": "0",
    "inactive_employees": "0",
    "groups": "5",
    "employment_types": "0",
    "pay_schemes": "0",
    "job_families": "12",
    "departments": "0",
    "active_assignments": "0",
    "assignment_missing": "0",
    "open_contracts": "0",
    "contracts_expiring_30": "0",
    "payroll_profiles": "0",
    "payroll_missing": "0",
    "bpjs_health_active": "0",
    "bpjs_tk_active": "0",
    "bpjs_missing": "0",
    "identity_missing": "0",
    "address_missing": "0",
    "document_count": "0",
    "document_missing": "0",
    "movements_30d": "0",
    "attendance_today": "0",
    "attendance_present_today": "0",
    "attendance_exception_today": "0",
    "attendance_codes": "0",
    "work_outputs_mtd": "0",
    "work_output_quantity_mtd": "0",
    "latest_snapshot": "MVP schema siap",
    "permissions": "17",
    "data_completeness": "0%",
    "companies": "0",
    "estates": "0",
    "divisions": "0",
    "positions": "0",
    "quality_watch": "0",
    "data_quality_score": "100%",
    "future_assignment_starts": "0",
    "source_date_reviews": "0",
    "age_review": "0",
    "duplicate_employee_no": "0",
    "duplicate_identity": "0",
    "duplicate_current_assignments": "0",
    "contract_conflicts": "0",
    "quality_open_total": "0",
    "quality_open_blocking": "0",
    "quality_open_review": "0",
    "quality_open_info": "0",
    "quality_overdue": "0",
    "latest_import_batch": "Belum ada",
    "latest_import_rows": "0",
    "data_warning": "0",
}
HRIS_SUMMARY_TABLES: tuple[str, ...] = (
    "employees",
    "employee_identities",
    "employee_addresses",
    "employee_assignments",
    "employee_status_histories",
    "employee_contracts",
    "employee_bpjs",
    "bpjs_types",
    "employee_documents",
    "employee_pay_profiles",
    "employee_movements",
    "employee_categories",
    "employment_statuses",
    "employment_types",
    "pay_types",
    "job_families",
    "attendance_codes",
    "companies",
    "estates",
    "divisions",
    "positions",
    "permissions",
    "data_quality_issues",
    "import_batches",
    "hr_attendance_daily",
    "hr_work_outputs",
    "employee_attendance_daily",
    "employee_work_outputs",
)

HRIS_GROUP_BREAKDOWN_FALLBACK: list[HrisGroupBreakdownRow] = [
    ("STF", "Staff", "Pimpinan, asisten, KTU, HRGA, controller.", "Core"),
    ("BLN", "Bulanan Non Staff", "Mandor, krani, operator, driver.", "Ops"),
    ("PHT/SKU", "Karyawan Tetap", "SKU, PHT, tenaga tetap lapangan.", "Fixed"),
    ("PHL/KHL", "Harian Lepas", "Tenaga HK, KHL, alias historis BHL.", "Daily"),
    ("BRG", "Borongan", "Tenaga output atau grup kerja.", "Output"),
]


class HrisQualityIssueRow(TypedDict):
    issue_id: int
    employee_id: int
    severity: str
    status: str
    issue: str
    employee: str
    division: str
    age_days: str
    sla: str
    observed: str
    recommendation: str


def format_hris_value(value: object) -> str:
    if isinstance(value, str):
        return value
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return str(value)
    if number.is_integer():
        return f"{int(number):,}".replace(",", ".")
    return f"{number:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def hris_summary_int(summary: dict[str, str], key: str) -> int:
    raw_value = str(summary.get(key, "0"))
    digits = "".join(character for character in raw_value if character.isdigit())
    return int(digits or "0")


def table_columns(session: object, table_name: str) -> set[str]:
    try:
        bind = getattr(session, "get_bind")()
        return {str(column["name"]) for column in inspect(bind).get_columns(table_name)}
    except Exception:
        return set()


def table_exists(session: object, table_name: str) -> bool:
    try:
        bind = getattr(session, "get_bind")()
        return bool(inspect(bind).has_table(table_name))
    except Exception:
        return False


def is_hris_auth_schema(session: object) -> bool:
    return HRIS_AUTH_SCHEMA_COLUMNS.issubset(table_columns(session, "users"))


def role_names_from_value(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value else []
    if isinstance(value, (list, tuple, set)):
        return [str(item) for item in value if item]
    return [str(value)]


def map_hris_role_to_dashboard_role(role_names: list[str]) -> str:
    normalized_roles = {role_name.strip().upper() for role_name in role_names}
    if "SUPER_ADMIN" in normalized_roles:
        return "Superior"
    if {"HR_ADMIN", "ADMIN", "ADMINISTRATOR"} & normalized_roles:
        return "Administrator"
    if {"OPERATOR", "HR_OPERATOR"} & normalized_roles:
        return "Operator"
    if {"HR_VIEWER", "VIEWER", "AUDITOR"} & normalized_roles:
        return "Auditor"
    if role_names:
        return role_names[0]
    return "Operator"


def read_hris_summary(
    session_factory: Callable[[], Any],
    table_exists: Callable[[object, str], bool],
    table_columns: Callable[[object, str], set[str]],
) -> dict[str, str]:
    summary = dict(HRIS_SUMMARY_DEFAULTS)
    session = session_factory()
    today = date.today()
    params = {
        "today": today,
        "month_start": today.replace(day=1),
        "contract_cutoff": today + timedelta(days=30),
        "movement_cutoff": today - timedelta(days=30),
    }

    def read_scalar(sql: str, default: str = "0", *, formatted: bool = True) -> str:
        try:
            value = session.execute(text(sql), params).scalar()
        except Exception as error:
            summary["data_warning"] = "1"
            logger.warning("Failed to read HRIS summary scalar: %s", error)
            return default
        if value is None:
            return default
        if formatted:
            return format_hris_value(value)
        return str(value)

    def read_int(sql: str, default: int = 0) -> int:
        try:
            value = session.execute(text(sql), params).scalar()
        except Exception as error:
            summary["data_warning"] = "1"
            logger.warning("Failed to read HRIS summary integer: %s", error)
            return default
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return default

    try:
        new_tables = {
            table_name: table_exists(session, table_name)
            for table_name in HRIS_SUMMARY_TABLES
        }

        if new_tables["employees"]:
            summary["employees"] = read_scalar("SELECT COUNT(*) FROM employees")
            if new_tables["employee_status_histories"] and new_tables["employment_statuses"]:
                latest_status_sql = """
                    WITH latest_status AS (
                        SELECT DISTINCT ON (employee_id)
                            employee_id,
                            employment_status_id
                        FROM employee_status_histories
                        ORDER BY employee_id, effective_date DESC, status_history_id DESC
                    )
                    SELECT COUNT(*)
                    FROM employees e
                    LEFT JOIN latest_status ls ON ls.employee_id = e.employee_id
                    LEFT JOIN employment_statuses s ON s.id = ls.employment_status_id
                    WHERE COALESCE(s.code, CASE WHEN e.is_active THEN 'AKTIF' ELSE 'NONAKTIF' END) = 'AKTIF'
                """
                inactive_status_sql = latest_status_sql.replace("= 'AKTIF'", "<> 'AKTIF'")
                summary["active_employees"] = read_scalar(latest_status_sql)
                summary["inactive_employees"] = read_scalar(inactive_status_sql)
            else:
                summary["active_employees"] = read_scalar(
                    "SELECT COUNT(*) FROM employees WHERE is_active = true"
                )
                summary["inactive_employees"] = read_scalar(
                    "SELECT COUNT(*) FROM employees WHERE is_active = false"
                )

            if new_tables["employee_identities"]:
                summary["identity_missing"] = read_scalar(
                    """
                    SELECT COUNT(*)
                    FROM employees e
                    WHERE e.is_active = true
                      AND NOT EXISTS (
                          SELECT 1 FROM employee_identities i
                          WHERE i.employee_id = e.employee_id
                      )
                    """
                )
            if new_tables["employee_addresses"]:
                summary["address_missing"] = read_scalar(
                    """
                    SELECT COUNT(*)
                    FROM employees e
                    WHERE e.is_active = true
                      AND NOT EXISTS (
                          SELECT 1 FROM employee_addresses a
                          WHERE a.employee_id = e.employee_id
                      )
                    """
                )
            if new_tables["employee_assignments"]:
                summary["active_assignments"] = read_scalar(
                    """
                    SELECT COUNT(*)
                    FROM employee_assignments
                    WHERE is_current = true
                      AND (end_date IS NULL OR end_date >= :today)
                    """
                )
                summary["assignment_missing"] = read_scalar(
                    """
                    SELECT COUNT(*)
                    FROM employees e
                    WHERE e.is_active = true
                      AND NOT EXISTS (
                          SELECT 1 FROM employee_assignments a
                          WHERE a.employee_id = e.employee_id
                            AND a.is_current = true
                            AND (a.end_date IS NULL OR a.end_date >= :today)
                      )
                    """
                )
            if new_tables["employee_pay_profiles"]:
                summary["payroll_profiles"] = read_scalar("SELECT COUNT(*) FROM employee_pay_profiles")
                summary["payroll_missing"] = read_scalar(
                    """
                    SELECT COUNT(*)
                    FROM employees e
                    WHERE e.is_active = true
                      AND NOT EXISTS (
                          SELECT 1 FROM employee_pay_profiles p
                          WHERE p.employee_id = e.employee_id
                      )
                    """
                )
            if new_tables["employee_bpjs"]:
                summary["bpjs_missing"] = read_scalar(
                    """
                    SELECT COUNT(*)
                    FROM employees e
                    WHERE e.is_active = true
                      AND NOT EXISTS (
                          SELECT 1 FROM employee_bpjs b
                          WHERE b.employee_id = e.employee_id
                            AND b.active_status = true
                      )
                    """
                )
                if new_tables["bpjs_types"]:
                    summary["bpjs_health_active"] = read_scalar(
                        """
                        SELECT COUNT(DISTINCT b.employee_id)
                        FROM employee_bpjs b
                        JOIN bpjs_types t ON t.bpjs_type_id = b.bpjs_type_id
                        WHERE b.active_status = true
                          AND upper(t.bpjs_type_name) LIKE '%KESEHATAN%'
                        """
                    )
                    summary["bpjs_tk_active"] = read_scalar(
                        """
                        SELECT COUNT(DISTINCT b.employee_id)
                        FROM employee_bpjs b
                        JOIN bpjs_types t ON t.bpjs_type_id = b.bpjs_type_id
                        WHERE b.active_status = true
                          AND upper(t.bpjs_type_name) LIKE '%KETENAGAKERJAAN%'
                        """
                    )
            if new_tables["employee_documents"]:
                summary["document_count"] = read_scalar("SELECT COUNT(*) FROM employee_documents")
                summary["document_missing"] = read_scalar(
                    """
                    SELECT COUNT(*)
                    FROM employees e
                    WHERE e.is_active = true
                      AND NOT EXISTS (
                          SELECT 1 FROM employee_documents d
                          WHERE d.employee_id = e.employee_id
                      )
                    """
                )
            if new_tables["employee_movements"]:
                summary["movements_30d"] = read_scalar(
                    "SELECT COUNT(*) FROM employee_movements WHERE movement_date >= :movement_cutoff"
                )

            summary["data_completeness"] = read_scalar(
                """
                WITH score AS (
                    SELECT
                        e.employee_id,
                        (
                            CASE WHEN e.mobile_phone IS NOT NULL OR e.email IS NOT NULL THEN 1 ELSE 0 END +
                            CASE WHEN EXISTS (
                                SELECT 1 FROM employee_identities i
                                WHERE i.employee_id = e.employee_id
                            ) THEN 1 ELSE 0 END +
                            CASE WHEN EXISTS (
                                SELECT 1 FROM employee_addresses a
                                WHERE a.employee_id = e.employee_id
                            ) THEN 1 ELSE 0 END +
                            CASE WHEN EXISTS (
                                SELECT 1 FROM employee_assignments asg
                                WHERE asg.employee_id = e.employee_id
                                  AND asg.is_current = true
                            ) THEN 1 ELSE 0 END +
                            CASE WHEN EXISTS (
                                SELECT 1 FROM employee_bpjs b
                                WHERE b.employee_id = e.employee_id
                                  AND b.active_status = true
                            ) THEN 1 ELSE 0 END
                        ) AS point
                    FROM employees e
                    WHERE e.is_active = true
                )
                SELECT COALESCE(ROUND(AVG(point) * 20), 0) FROM score
                """,
                "0",
            ) + "%"

            duplicate_employee_no = read_int(
                """
                SELECT COUNT(*)
                FROM (
                    SELECT employee_no
                    FROM employees
                    GROUP BY employee_no
                    HAVING COUNT(*) > 1
                ) duplicate_no
                """
            )
            age_review = read_int(
                """
                SELECT COUNT(*)
                FROM employees
                WHERE is_active = true
                  AND birth_date IS NOT NULL
                  AND (
                      birth_date > :today - INTERVAL '17 years'
                      OR birth_date < :today - INTERVAL '70 years'
                  )
                """
            )
            duplicate_identity = 0
            duplicate_current_assignments = 0
            future_assignment_starts = 0
            source_date_reviews = 0
            contract_conflicts = 0
            if new_tables["employee_identities"]:
                duplicate_identity = read_int(
                    """
                    SELECT COUNT(*)
                    FROM (
                        SELECT identity_number
                        FROM employee_identities
                        WHERE identity_number IS NOT NULL
                        GROUP BY identity_number
                        HAVING COUNT(*) > 1
                    ) duplicate_identity
                    """
                )
            if new_tables["employee_assignments"]:
                duplicate_current_assignments = read_int(
                    """
                    SELECT COUNT(*)
                    FROM (
                        SELECT employee_id
                        FROM employee_assignments
                        WHERE is_current = true
                          AND (end_date IS NULL OR end_date >= :today)
                        GROUP BY employee_id
                        HAVING COUNT(*) > 1
                    ) duplicate_assignment
                    """
                )
                future_assignment_starts = read_int(
                    """
                    SELECT COUNT(*)
                    FROM employee_assignments
                    WHERE is_current = true
                      AND start_date > :today
                    """
                )
                source_date_reviews = read_int(
                    """
                    SELECT COUNT(*)
                    FROM employee_assignments
                    WHERE notes LIKE '%review_original_join_date=%'
                    """
                )
            if new_tables["employee_contracts"]:
                contract_conflicts = read_int(
                    """
                    SELECT COUNT(*)
                    FROM (
                        SELECT employee_id
                        FROM employee_contracts
                        WHERE end_date IS NULL
                        GROUP BY employee_id
                        HAVING COUNT(*) > 1
                    ) duplicate_contract
                    """
                )

            quality_watch = (
                duplicate_employee_no
                + duplicate_identity
                + duplicate_current_assignments
                + contract_conflicts
                + future_assignment_starts
                + source_date_reviews
                + age_review
            )
            active_total = read_int(
                """
                SELECT COUNT(*)
                FROM employees
                WHERE is_active = true
                """,
                1,
            )
            weighted_issues = (
                (duplicate_employee_no + duplicate_identity + duplicate_current_assignments + contract_conflicts) * 10
                + (future_assignment_starts + age_review) * 2
                + source_date_reviews
            )
            quality_score = max(0, round(100 - ((weighted_issues / max(active_total, 1)) * 100)))
            summary["quality_watch"] = format_hris_value(quality_watch)
            summary["data_quality_score"] = f"{quality_score}%"
            summary["future_assignment_starts"] = format_hris_value(future_assignment_starts)
            summary["source_date_reviews"] = format_hris_value(source_date_reviews)
            summary["age_review"] = format_hris_value(age_review)
            summary["duplicate_employee_no"] = format_hris_value(duplicate_employee_no)
            summary["duplicate_identity"] = format_hris_value(duplicate_identity)
            summary["duplicate_current_assignments"] = format_hris_value(duplicate_current_assignments)
            summary["contract_conflicts"] = format_hris_value(contract_conflicts)

            if new_tables["data_quality_issues"]:
                quality_blocking = read_int(
                    """
                    SELECT COUNT(*)
                    FROM data_quality_issues
                    WHERE status = 'OPEN'
                      AND severity = 'BLOCKING'
                    """
                )
                quality_review = read_int(
                    """
                    SELECT COUNT(*)
                    FROM data_quality_issues
                    WHERE status = 'OPEN'
                      AND severity = 'REVIEW'
                    """
                )
                quality_info = read_int(
                    """
                    SELECT COUNT(*)
                    FROM data_quality_issues
                    WHERE status = 'OPEN'
                      AND severity = 'INFO'
                    """
                )
                quality_overdue = read_int(
                    """
                    SELECT COUNT(*)
                    FROM data_quality_issues
                    WHERE status IN ('OPEN', 'VERIFIED')
                      AND (
                          (severity = 'BLOCKING' AND first_seen_at < now() - INTERVAL '2 days')
                          OR (severity = 'REVIEW' AND first_seen_at < now() - INTERVAL '7 days')
                          OR (severity = 'INFO' AND first_seen_at < now() - INTERVAL '30 days')
                      )
                    """
                )
                quality_watch = quality_blocking + quality_review
                quality_weighted = (quality_blocking * 10) + (quality_review * 2)
                quality_score = max(0, round(100 - ((quality_weighted / max(active_total, 1)) * 100)))
                summary["quality_open_blocking"] = format_hris_value(quality_blocking)
                summary["quality_open_review"] = format_hris_value(quality_review)
                summary["quality_open_info"] = format_hris_value(quality_info)
                summary["quality_overdue"] = format_hris_value(quality_overdue)
                summary["quality_open_total"] = format_hris_value(
                    quality_blocking + quality_review + quality_info
                )
                summary["quality_watch"] = format_hris_value(quality_watch)
                summary["data_quality_score"] = f"{quality_score}%"
                summary["source_date_reviews"] = read_scalar(
                    """
                    SELECT COUNT(*)
                    FROM data_quality_issues
                    WHERE status = 'OPEN'
                      AND issue_code = 'SOURCE_DATE_REVIEW'
                    """
                )

        if new_tables["employee_categories"]:
            summary["groups"] = read_scalar(
                "SELECT COUNT(*) FROM employee_categories WHERE is_active = true",
                summary["groups"],
            )
        if new_tables["employment_types"]:
            summary["employment_types"] = read_scalar(
                "SELECT COUNT(*) FROM employment_types WHERE is_active = true"
            )
        if new_tables["pay_types"]:
            summary["pay_schemes"] = read_scalar("SELECT COUNT(*) FROM pay_types WHERE is_active = true")
        if new_tables["job_families"]:
            summary["job_families"] = read_scalar(
                "SELECT COUNT(*) FROM job_families WHERE is_active = true",
                summary["job_families"],
            )
        if new_tables["attendance_codes"]:
            summary["attendance_codes"] = read_scalar(
                "SELECT COUNT(*) FROM attendance_codes WHERE is_active = true"
            )
        if new_tables["employee_contracts"]:
            summary["open_contracts"] = read_scalar(
                "SELECT COUNT(*) FROM employee_contracts WHERE end_date IS NULL OR end_date >= :today"
            )
            summary["contracts_expiring_30"] = read_scalar(
                "SELECT COUNT(*) FROM employee_contracts WHERE end_date BETWEEN :today AND :contract_cutoff"
            )
        if new_tables["companies"]:
            summary["companies"] = read_scalar("SELECT COUNT(*) FROM companies WHERE is_active = true")
        if new_tables["estates"]:
            summary["estates"] = read_scalar("SELECT COUNT(*) FROM estates WHERE is_active = true")
        if new_tables["divisions"]:
            summary["divisions"] = read_scalar("SELECT COUNT(*) FROM divisions WHERE is_active = true")
            summary["departments"] = summary["divisions"]
        if new_tables["positions"]:
            summary["positions"] = read_scalar("SELECT COUNT(*) FROM positions WHERE is_active = true")
        if new_tables["permissions"]:
            permission_columns = table_columns(session, "permissions")
            if {"module_name", "action_name"}.issubset(permission_columns):
                summary["permissions"] = read_scalar(
                    "SELECT COUNT(*) FROM permissions WHERE module_name = 'employee'",
                    summary["permissions"],
                )
            elif "permission_name" in permission_columns:
                summary["permissions"] = read_scalar(
                    "SELECT COUNT(*) FROM permissions WHERE permission_name LIKE 'hr.%'",
                    summary["permissions"],
                )

        if new_tables["import_batches"]:
            latest_import = session.execute(
                text(
                    """
                    SELECT import_batch_id, source_period, imported_rows, finished_at
                    FROM import_batches
                    ORDER BY finished_at DESC NULLS LAST, import_batch_id DESC
                    LIMIT 1
                    """
                )
            ).mappings().first()
            if latest_import is not None:
                summary["latest_import_batch"] = (
                    f"#{latest_import['import_batch_id']} - {latest_import['source_period']}"
                )
                summary["latest_import_rows"] = format_hris_value(latest_import["imported_rows"])

        if new_tables["employee_attendance_daily"]:
            summary["attendance_today"] = read_scalar(
                "SELECT COUNT(*) FROM employee_attendance_daily WHERE attendance_date = :today"
            )
            summary["attendance_present_today"] = read_scalar(
                """
                SELECT COUNT(*)
                FROM employee_attendance_daily a
                JOIN attendance_codes c ON c.id = a.attendance_code_id
                WHERE a.attendance_date = :today
                  AND (upper(c.code) IN ('H', 'PRESENT', 'HADIR') OR c.hk_value > 0)
                """
            )
            summary["attendance_exception_today"] = read_scalar(
                """
                SELECT COUNT(*)
                FROM employee_attendance_daily a
                JOIN attendance_codes c ON c.id = a.attendance_code_id
                WHERE a.attendance_date = :today
                  AND upper(c.code) IN ('I', 'IZIN', 'S', 'SAKIT', 'CT', 'CUTI', 'A', 'ALPA', 'ABSENT')
                  AND c.hk_value <= 0
                """
            )
        elif new_tables["hr_attendance_daily"]:
            summary["attendance_today"] = read_scalar(
                "SELECT COUNT(*) FROM hr_attendance_daily WHERE attendance_date = :today"
            )
            summary["attendance_present_today"] = read_scalar(
                """
                SELECT COUNT(*)
                FROM hr_attendance_daily
                WHERE attendance_date = :today
                  AND status = 'present'
                """
            )
            summary["attendance_exception_today"] = read_scalar(
                """
                SELECT COUNT(*)
                FROM hr_attendance_daily
                WHERE attendance_date = :today
                  AND status IN ('absent', 'leave', 'sick', 'permit')
                """
            )

        if new_tables["employee_work_outputs"]:
            summary["work_outputs_mtd"] = read_scalar(
                "SELECT COUNT(*) FROM employee_work_outputs WHERE work_date >= :month_start"
            )
            summary["work_output_quantity_mtd"] = read_scalar(
                """
                SELECT COALESCE(SUM(quantity), 0)
                FROM employee_work_outputs
                WHERE work_date >= :month_start
                """
            )
        elif new_tables["hr_work_outputs"]:
            summary["work_outputs_mtd"] = read_scalar(
                "SELECT COUNT(*) FROM hr_work_outputs WHERE work_date >= :month_start"
            )
            summary["work_output_quantity_mtd"] = read_scalar(
                """
                SELECT COALESCE(SUM(quantity), 0)
                FROM hr_work_outputs
                WHERE work_date >= :month_start
                """
            )

        if table_exists(session, "hr_employees") and summary["employees"] == "0":
            summary.update(
                {
                    "employees": read_scalar("SELECT COUNT(*) FROM hr_employees"),
                    "active_employees": read_scalar(
                        "SELECT COUNT(*) FROM hr_employees WHERE employment_status = 'active'"
                    ),
                    "inactive_employees": read_scalar(
                        "SELECT COUNT(*) FROM hr_employees WHERE employment_status <> 'active'"
                    ),
                }
            )
    except Exception:
        summary["data_warning"] = "1"
        logger.exception("Failed to read HRIS summary")
    finally:
        session.close()
    return summary



def read_hris_group_breakdown(
    session_factory: Callable[[], Any],
    table_exists: Callable[[object, str], bool],
) -> list[HrisGroupBreakdownRow]:
    session = session_factory()
    try:
        if table_exists(session, "employee_categories"):
            rows = session.execute(
                text(
                    """
                    SELECT
                        c.code,
                        c.name,
                        COALESCE(c.description, 'Kategori manpower aktif.') AS description,
                        COALESCE(COUNT(a.employee_id), 0) AS headcount
                    FROM employee_categories c
                    LEFT JOIN employee_assignments a
                        ON a.category_id = c.id
                       AND a.is_current = true
                       AND (a.end_date IS NULL OR a.end_date >= CURRENT_DATE)
                    WHERE c.is_active = true
                    GROUP BY c.id, c.code, c.name, c.description
                    ORDER BY c.code ASC
                    """
                )
            ).mappings()
            result = [
                (
                    str(row["code"]),
                    str(row["name"]),
                    str(row["description"]),
                    f"{format_hris_value(row['headcount'])} aktif",
                )
                for row in rows
            ]
            return result or HRIS_GROUP_BREAKDOWN_FALLBACK

        rows = session.execute(
            text(
                """
                SELECT
                    g.code,
                    g.name,
                    COALESCE(COUNT(e.id), 0) AS headcount
                FROM hr_employee_groups g
                LEFT JOIN hr_employees e
                    ON e.current_group_id = g.id
                   AND e.employment_status = 'active'
                WHERE g.is_active = true
                GROUP BY g.id, g.code, g.name, g.sort_order
                ORDER BY g.sort_order ASC, g.code ASC
                """
            )
        ).mappings()
        result = [
            (
                str(row["code"]),
                str(row["name"]),
                "Kategori aktif dan dipisah dari legal status serta payroll scheme.",
                f"{format_hris_value(row['headcount'])} aktif",
            )
            for row in rows
        ]
        return result or HRIS_GROUP_BREAKDOWN_FALLBACK
    except Exception:
        logger.exception("Failed to read HRIS group breakdown")
        return HRIS_GROUP_BREAKDOWN_FALLBACK
    finally:
        session.close()


def read_hris_quality_issues(
    session_factory: Callable[[], Any],
    table_exists: Callable[[object, str], bool],
    *,
    status_value: str = "OPEN",
    severity_value: str = "ALL",
    search_value: str = "",
    limit: int = 80,
) -> list[HrisQualityIssueRow]:
    session = session_factory()
    try:
        if not table_exists(session, "data_quality_issues"):
            return []
        normalized_status = status_value.strip().upper() or "OPEN"
        normalized_severity = severity_value.strip().upper() or "ALL"
        normalized_search = search_value.strip().lower()
        status_filter = "" if normalized_status == "ALL" else "AND i.status = :status_value"
        severity_filter = "" if normalized_severity == "ALL" else "AND i.severity = :severity_value"
        search_filter = """
            AND (
                lower(COALESCE(e.employee_no, '')) LIKE :search_value
                OR lower(COALESCE(e.full_name, '')) LIKE :search_value
                OR lower(COALESCE(d.division_name, '')) LIKE :search_value
                OR lower(COALESCE(i.issue_code, '')) LIKE :search_value
                OR lower(replace(COALESCE(i.issue_code, ''), '_', ' ')) LIKE :search_value
                OR lower(COALESCE(i.observed_value, '')) LIKE :search_value
            )
        """ if normalized_search else ""
        rows = session.execute(
            text(
                f"""
                SELECT
                    i.issue_id,
                    COALESCE(i.employee_id, 0) AS employee_id,
                    i.severity,
                    i.status,
                    i.issue_code,
                    GREATEST(0, EXTRACT(DAY FROM now() - i.first_seen_at)::int) AS age_days,
                    COALESCE(e.employee_no, '-') AS employee_no,
                    COALESCE(e.full_name, '-') AS full_name,
                    COALESCE(d.division_name, '-') AS division_name,
                    COALESCE(i.observed_value, '-') AS observed_value,
                    COALESCE(i.recommendation, '-') AS recommendation
                FROM data_quality_issues i
                LEFT JOIN employees e ON e.employee_id = i.employee_id
                LEFT JOIN employee_assignments a
                    ON a.employee_id = e.employee_id
                   AND a.is_current = true
                LEFT JOIN divisions d ON d.division_id = a.division_id
                WHERE 1 = 1
                {status_filter}
                {severity_filter}
                {search_filter}
                ORDER BY
                    CASE i.severity
                        WHEN 'BLOCKING' THEN 1
                        WHEN 'REVIEW' THEN 2
                        ELSE 3
                    END,
                    CASE i.status
                        WHEN 'OPEN' THEN 1
                        WHEN 'VERIFIED' THEN 2
                        WHEN 'IGNORED' THEN 3
                        ELSE 4
                    END,
                    i.issue_code,
                    d.division_name,
                    e.employee_no
                LIMIT :limit
                """
            ),
            {
                "limit": limit,
                "status_value": normalized_status,
                "severity_value": normalized_severity,
                "search_value": f"%{normalized_search}%",
            },
        ).mappings()
        return [
            format_hris_quality_issue_row(
                issue_id=int(row["issue_id"]),
                employee_id=int(row["employee_id"] or 0),
                severity=str(row["severity"]),
                status=str(row["status"]),
                issue=str(row["issue_code"]).replace("_", " ").title(),
                employee=f"{row['employee_no']} - {row['full_name']}",
                division=str(row["division_name"]),
                age_days=int(row["age_days"] or 0),
                observed=str(row["observed_value"]),
                recommendation=str(row["recommendation"]),
            )
            for row in rows
        ]
    except Exception:
        logger.exception("Failed to read HRIS quality issues")
        return []
    finally:
        session.close()


def read_hris_employee_detail(
    session_factory: Callable[[], Any],
    table_exists: Callable[[object, str], bool],
    *,
    employee_id: int,
    issue_id: int | None = None,
) -> dict[str, str] | None:
    session = session_factory()
    try:
        if not table_exists(session, "employees"):
            return None
        row = session.execute(
            text(
                """
                WITH current_assignment AS (
                    SELECT DISTINCT ON (a.employee_id)
                        a.employee_id,
                        a.start_date,
                        COALESCE(d.division_name, '-') AS division_name,
                        COALESCE(p.position_name, '-') AS position_name,
                        COALESCE(c.name, '-') AS category_name,
                        COALESCE(es.estate_name, '-') AS estate_name
                    FROM employee_assignments a
                    LEFT JOIN divisions d ON d.division_id = a.division_id
                    LEFT JOIN positions p ON p.position_id = a.position_id
                    LEFT JOIN employee_categories c ON c.id = a.category_id
                    LEFT JOIN estates es ON es.estate_id = a.estate_id
                    WHERE a.is_current = true
                    ORDER BY a.employee_id, a.start_date DESC NULLS LAST, a.assignment_id DESC
                ),
                latest_status AS (
                    SELECT DISTINCT ON (h.employee_id)
                        h.employee_id,
                        h.effective_date,
                        COALESCE(s.code, '-') AS status_code,
                        COALESCE(s.name, '-') AS status_name
                    FROM employee_status_histories h
                    LEFT JOIN employment_statuses s ON s.id = h.employment_status_id
                    ORDER BY h.employee_id, h.effective_date DESC, h.status_history_id DESC
                ),
                current_contract AS (
                    SELECT DISTINCT ON (c.employee_id)
                        c.employee_id,
                        c.contract_no,
                        c.start_date,
                        c.end_date,
                        COALESCE(t.name, '-') AS employment_type
                    FROM employee_contracts c
                    LEFT JOIN employment_types t ON t.id = c.employment_type_id
                    WHERE c.end_date IS NULL OR c.end_date >= CURRENT_DATE
                    ORDER BY c.employee_id, c.start_date DESC NULLS LAST, c.contract_id DESC
                ),
                issue_summary AS (
                    SELECT
                        employee_id,
                        COUNT(*) FILTER (WHERE status = 'OPEN') AS open_issues,
                        COUNT(*) FILTER (WHERE status = 'OPEN' AND severity = 'BLOCKING') AS blocking_issues,
                        COUNT(*) FILTER (WHERE status = 'OPEN' AND severity = 'REVIEW') AS review_issues,
                        COUNT(*) FILTER (WHERE status = 'OPEN' AND severity = 'INFO') AS info_issues
                    FROM data_quality_issues
                    GROUP BY employee_id
                )
                SELECT
                    e.employee_id,
                    e.employee_no,
                    e.full_name,
                    COALESCE(e.gender, '-') AS gender,
                    COALESCE(e.birth_place, '-') AS birth_place,
                    COALESCE(e.birth_date::text, '-') AS birth_date,
                    CASE WHEN e.is_active THEN 'Aktif' ELSE 'Tidak aktif' END AS active_flag,
                    COALESCE(r.name, '-') AS religion,
                    COALESCE(ed.name, '-') AS education,
                    COALESCE(ms.code, '-') AS marital_status,
                    COALESCE(ca.estate_name, '-') AS estate_name,
                    COALESCE(ca.division_name, '-') AS division_name,
                    COALESCE(ca.position_name, '-') AS position_name,
                    COALESCE(ca.category_name, '-') AS category_name,
                    COALESCE(ca.start_date::text, '-') AS assignment_start,
                    COALESCE(ls.status_code, '-') AS status_code,
                    COALESCE(ls.status_name, '-') AS status_name,
                    COALESCE(ls.effective_date::text, '-') AS status_effective,
                    COALESCE(cc.employment_type, '-') AS employment_type,
                    COALESCE(cc.contract_no, '-') AS contract_no,
                    COALESCE(cc.start_date::text, '-') AS contract_start,
                    COALESCE(cc.end_date::text, '-') AS contract_end,
                    (SELECT COUNT(*) FROM employee_identities i WHERE i.employee_id = e.employee_id) AS identity_count,
                    (SELECT COUNT(*) FROM employee_addresses a WHERE a.employee_id = e.employee_id) AS address_count,
                    (SELECT COUNT(*) FROM employee_bpjs b WHERE b.employee_id = e.employee_id AND b.active_status = true) AS bpjs_count,
                    (SELECT COUNT(*) FROM employee_documents d WHERE d.employee_id = e.employee_id) AS document_count,
                    COALESCE(iq.open_issues, 0) AS open_issues,
                    COALESCE(iq.blocking_issues, 0) AS blocking_issues,
                    COALESCE(iq.review_issues, 0) AS review_issues,
                    COALESCE(iq.info_issues, 0) AS info_issues
                FROM employees e
                LEFT JOIN religions r ON r.id = e.religion_id
                LEFT JOIN education_levels ed ON ed.id = e.education_id
                LEFT JOIN marital_statuses ms ON ms.id = e.marital_status_id
                LEFT JOIN current_assignment ca ON ca.employee_id = e.employee_id
                LEFT JOIN latest_status ls ON ls.employee_id = e.employee_id
                LEFT JOIN current_contract cc ON cc.employee_id = e.employee_id
                LEFT JOIN issue_summary iq ON iq.employee_id = e.employee_id
                WHERE e.employee_id = :employee_id
                """
            ),
            {"employee_id": employee_id},
        ).mappings().first()
        if row is None:
            return None

        issue_row = None
        if issue_id is not None:
            issue_row = session.execute(
                text(
                    """
                    SELECT issue_code, severity, status, observed_value, recommendation
                    FROM data_quality_issues
                    WHERE issue_id = :issue_id
                    """
                ),
                {"issue_id": issue_id},
            ).mappings().first()

        detail = {key: str(value) for key, value in row.items()}
        if issue_row is not None:
            detail.update(
                {
                    "issue_code": str(issue_row["issue_code"]).replace("_", " ").title(),
                    "issue_severity": str(issue_row["severity"]),
                    "issue_status": str(issue_row["status"]),
                    "issue_observed": str(issue_row["observed_value"] or "-"),
                    "issue_recommendation": str(issue_row["recommendation"] or "-"),
                }
            )
        else:
            detail.update(
                {
                    "issue_code": "-",
                    "issue_severity": "-",
                    "issue_status": "-",
                    "issue_observed": "-",
                    "issue_recommendation": "-",
                }
            )
        return detail
    except Exception:
        logger.exception("Failed to read HRIS employee detail")
        return None
    finally:
        session.close()


def read_hris_employee_id_for_issue(
    session_factory: Callable[[], Any],
    *,
    issue_id: int,
) -> int:
    session = session_factory()
    try:
        row = session.execute(
            text(
                """
                SELECT employee_id
                FROM data_quality_issues
                WHERE issue_id = :issue_id
                """
            ),
            {"issue_id": issue_id},
        ).first()
        return int(row[0] or 0) if row is not None else 0
    except Exception:
        logger.exception("Failed to read HRIS issue employee id")
        return 0
    finally:
        session.close()


def write_hris_quality_audit(
    session: object,
    table_exists: Callable[[object, str], bool],
    table_columns: Callable[[object, str], set[str]],
    *,
    user_id: int | None,
    issue_id: int,
    issue_code: str,
    previous_status: str,
    new_status: str,
) -> None:
    try:
        if not table_exists(session, "audit_logs"):
            return
        columns = table_columns(session, "audit_logs")
        description = (
            f"Data quality issue {issue_id} ({issue_code}) status changed "
            f"from {previous_status} to {new_status}."
        )
        if {"module_name", "action_name", "table_name", "record_id"}.issubset(columns):
            session.execute(
                text(
                    """
                    INSERT INTO audit_logs (
                        user_id, module_name, action_name, table_name, record_id, new_data, created_at
                    )
                    VALUES (
                        :user_id, 'data_quality', 'change_status', 'data_quality_issues',
                        :record_id, CAST(:new_data AS json), now()
                    )
                    """
                ),
                {
                    "user_id": user_id,
                    "record_id": str(issue_id),
                    "new_data": json.dumps({"from": previous_status, "to": new_status}, ensure_ascii=True),
                },
            )
            return
        if {"action", "action_type", "description"}.issubset(columns):
            session.execute(
                text(
                    """
                    INSERT INTO audit_logs (user_id, action, action_type, description, created_at)
                    VALUES (:user_id, 'data_quality.change_status', :action_type, :description, now())
                    """
                ),
                {
                    "user_id": user_id,
                    "action_type": new_status,
                    "description": description,
                },
            )
    except Exception:
        logger.exception("Failed to write HRIS quality audit")


def write_hris_quality_export_audit(
    session: object,
    table_exists: Callable[[object, str], bool],
    table_columns: Callable[[object, str], set[str]],
    *,
    user_id: int | None,
    output_path: Path,
    row_count: int,
    status_filter: str,
    severity_filter: str,
    search_text: str,
) -> None:
    try:
        if not table_exists(session, "audit_logs"):
            return
        columns = table_columns(session, "audit_logs")
        export_payload = {
            "file": str(output_path),
            "row_count": row_count,
            "filters": {
                "status": status_filter,
                "severity": severity_filter,
                "search": search_text,
            },
        }
        description = (
            f"Exported {row_count} data quality issue rows to {output_path.name}. "
            f"Filters: status={status_filter}, severity={severity_filter}, search={search_text or '-'}."
        )
        if {"module_name", "action_name", "table_name", "record_id"}.issubset(columns):
            session.execute(
                text(
                    """
                    INSERT INTO audit_logs (
                        user_id, module_name, action_name, table_name, record_id, new_data, created_at
                    )
                    VALUES (
                        :user_id, 'data_quality', 'export', 'data_quality_issues',
                        :record_id, CAST(:new_data AS json), now()
                    )
                    """
                ),
                {
                    "user_id": user_id,
                    "record_id": output_path.name,
                    "new_data": json.dumps(export_payload, ensure_ascii=True),
                },
            )
            return
        if {"action", "action_type", "description"}.issubset(columns):
            session.execute(
                text(
                    """
                    INSERT INTO audit_logs (user_id, action, action_type, description, created_at)
                    VALUES (:user_id, 'data_quality.export', 'EXPORT', :description, now())
                    """
                ),
                {
                    "user_id": user_id,
                    "description": description,
                },
            )
    except Exception:
        logger.exception("Failed to write HRIS quality export audit")


def update_hris_quality_issue_statuses(
    session_factory: Callable[[], Any],
    table_exists: Callable[[object, str], bool],
    table_columns: Callable[[object, str], set[str]],
    *,
    user_id: int | None,
    issue_ids: list[int],
    status: str,
) -> tuple[bool, str]:
    normalized_status = status.strip().upper()
    if normalized_status not in {"OPEN", "VERIFIED", "FIXED", "IGNORED"}:
        return (False, "Invalid Data Quality status.")
    if not issue_ids:
        return (True, "")

    session = session_factory()
    try:
        if not table_exists(session, "data_quality_issues"):
            return (True, "")
        issue_rows = session.execute(
            text(
                """
                SELECT issue_id, issue_code, severity, status
                FROM data_quality_issues
                WHERE issue_id = ANY(:issue_ids)
                """
            ),
            {"issue_ids": issue_ids},
        ).mappings().all()
        if not issue_rows:
            return (True, "")
        target_issue_ids = [int(row["issue_id"]) for row in issue_rows]
        session.execute(
            text(
                """
                UPDATE data_quality_issues
                SET status = :status,
                    resolved_at = CASE WHEN :status = 'FIXED' THEN now() ELSE NULL END,
                    updated_at = now()
                WHERE issue_id = ANY(:issue_ids)
                """
            ),
            {"issue_ids": target_issue_ids, "status": normalized_status},
        )
        for issue_row in issue_rows:
            write_hris_quality_audit(
                session,
                table_exists,
                table_columns,
                user_id=user_id,
                issue_id=int(issue_row["issue_id"]),
                issue_code=str(issue_row["issue_code"]),
                previous_status=str(issue_row["status"]),
                new_status=normalized_status,
            )
        session.commit()
        return (True, "")
    except Exception as error:
        session.rollback()
        logger.exception("Failed to update HRIS quality issue statuses")
        return (False, str(error))
    finally:
        session.close()


def export_hris_quality_issues(
    rows: list[HrisQualityIssueRow],
    *,
    reports_dir: Path,
    session_factory: Callable[[], Any],
    table_exists: Callable[[object, str], bool],
    table_columns: Callable[[object, str], set[str]],
    user_id: int | None,
    status_filter: str,
    severity_filter: str,
    search_text: str,
) -> Path:
    reports_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = reports_dir / f"hris_quality_filtered_{timestamp}.csv"
    with output_path.open("w", newline="", encoding="utf-8-sig") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=[
                "issue_id",
                "employee_id",
                "severity",
                "status",
                "issue",
                "employee",
                "division",
                "age_days",
                "sla",
                "observed",
                "recommendation",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    session = session_factory()
    try:
        write_hris_quality_export_audit(
            session,
            table_exists,
            table_columns,
            user_id=user_id,
            output_path=output_path,
            row_count=len(rows),
            status_filter=status_filter,
            severity_filter=severity_filter,
            search_text=search_text,
        )
        session.commit()
    except Exception:
        session.rollback()
        logger.exception("Failed to audit HRIS quality export")
    finally:
        session.close()
    return output_path


def current_user_has_permission(
    session_factory: Callable[[], Any],
    table_exists: Callable[[object, str], bool],
    table_columns: Callable[[object, str], set[str]],
    *,
    user_id: int,
    module_name: str,
    action_name: str,
) -> bool | None:
    if user_id <= 0:
        return None

    session = session_factory()
    try:
        required_tables = {"permissions", "role_permissions", "user_roles", "roles"}
        if not all(table_exists(session, table_name) for table_name in required_tables):
            return None
        permission_columns = table_columns(session, "permissions")
        if {"module_name", "action_name", "permission_id"}.issubset(permission_columns):
            value = session.execute(
                text(
                    """
                    SELECT 1
                    FROM permissions p
                    JOIN role_permissions rp ON rp.permission_id = p.permission_id
                    JOIN user_roles ur ON ur.role_id = rp.role_id
                    WHERE ur.user_id = :user_id
                      AND p.module_name = :module_name
                      AND p.action_name = :action_name
                    LIMIT 1
                    """
                ),
                {
                    "user_id": user_id,
                    "module_name": module_name,
                    "action_name": action_name,
                },
            ).scalar()
            return value is not None
        if "permission_name" in permission_columns:
            permission_name = f"{module_name}:{action_name}"
            value = session.execute(
                text(
                    """
                    SELECT 1
                    FROM permissions p
                    JOIN role_permissions rp ON rp.permission_id = p.id
                    JOIN user_roles ur ON ur.role_id = rp.role_id
                    WHERE ur.user_id = :user_id
                      AND p.permission_name = :permission_name
                    LIMIT 1
                    """
                ),
                {"user_id": user_id, "permission_name": permission_name},
            ).scalar()
            return value is not None
    except Exception:
        logger.exception("Failed to read current user permission")
        return None
    finally:
        session.close()
    return None


def format_hris_quality_issue_row(
    *,
    issue_id: int,
    employee_id: int,
    severity: str,
    status: str,
    issue: str,
    employee: str,
    division: str,
    age_days: int,
    observed: str,
    recommendation: str,
) -> HrisQualityIssueRow:
    due_days = {"BLOCKING": 2, "REVIEW": 7, "INFO": 30}.get(severity, 30)
    remaining_days = due_days - age_days
    sla_text = f"Overdue {abs(remaining_days)}d" if remaining_days < 0 else f"On Track {remaining_days}d"
    return {
        "issue_id": issue_id,
        "employee_id": employee_id,
        "severity": severity,
        "status": status,
        "issue": issue,
        "employee": employee,
        "division": division,
        "age_days": f"{age_days}d",
        "sla": sla_text,
        "observed": observed,
        "recommendation": recommendation,
    }
