#!/usr/bin/env python
"""Print and optionally export an HRIS data quality snapshot for PT GBR manpower data."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.database.models import engine  # noqa: E402
from scripts.hris_data_governance import (  # noqa: E402
    DEFAULT_REPORT_PATH,
    ensure_governance_tables,
    ensure_governance_tables_with_admin,
    export_review_csv,
    sync_data_quality_issues,
)

RULES: tuple[tuple[str, str, str], ...] = (
    (
        "employees",
        "Total karyawan",
        "SELECT COUNT(*) FROM employees",
    ),
    (
        "active_employees",
        "Karyawan aktif",
        "SELECT COUNT(*) FROM employees WHERE is_active = true",
    ),
    (
        "inactive_employees",
        "Karyawan tidak aktif",
        "SELECT COUNT(*) FROM employees WHERE is_active = false",
    ),
    (
        "missing_assignment",
        "Aktif tanpa assignment current",
        """
        SELECT COUNT(*)
        FROM employees e
        WHERE e.is_active = true
          AND NOT EXISTS (
              SELECT 1
              FROM employee_assignments a
              WHERE a.employee_id = e.employee_id
                AND a.is_current = true
          )
        """,
    ),
    (
        "duplicate_current_assignment",
        "Karyawan dengan assignment current ganda",
        """
        SELECT COUNT(*)
        FROM (
            SELECT employee_id
            FROM employee_assignments
            WHERE is_current = true
            GROUP BY employee_id
            HAVING COUNT(*) > 1
        ) duplicate_assignment
        """,
    ),
    (
        "multiple_open_contracts",
        "Karyawan dengan kontrak terbuka ganda",
        """
        SELECT COUNT(*)
        FROM (
            SELECT employee_id
            FROM employee_contracts
            WHERE end_date IS NULL
            GROUP BY employee_id
            HAVING COUNT(*) > 1
        ) duplicate_contract
        """,
    ),
    (
        "duplicate_employee_no",
        "Nomor karyawan duplikat",
        """
        SELECT COUNT(*)
        FROM (
            SELECT employee_no
            FROM employees
            GROUP BY employee_no
            HAVING COUNT(*) > 1
        ) duplicate_no
        """,
    ),
    (
        "duplicate_identity",
        "Nomor identitas duplikat",
        """
        SELECT COUNT(*)
        FROM (
            SELECT identity_number
            FROM employee_identities
            WHERE identity_number IS NOT NULL
            GROUP BY identity_number
            HAVING COUNT(*) > 1
        ) duplicate_identity
        """,
    ),
    (
        "future_assignment_start",
        "Tanggal aktif assignment di masa depan",
        """
        SELECT COUNT(*)
        FROM employee_assignments
        WHERE is_current = true
          AND start_date > CURRENT_DATE
        """,
    ),
    (
        "source_date_review",
        "Tanggal sumber dinormalisasi ke tanggal snapshot",
        """
        SELECT COUNT(*)
        FROM employee_assignments
        WHERE notes LIKE '%review_original_join_date=%'
        """,
    ),
    (
        "age_review",
        "Usia aktif perlu verifikasi",
        """
        SELECT COUNT(*)
        FROM employees
        WHERE is_active = true
          AND birth_date IS NOT NULL
          AND (
              birth_date > CURRENT_DATE - INTERVAL '17 years'
              OR birth_date < CURRENT_DATE - INTERVAL '70 years'
          )
        """,
    ),
    (
        "missing_identity",
        "Aktif tanpa nomor identitas",
        """
        SELECT COUNT(*)
        FROM employees e
        WHERE e.is_active = true
          AND NOT EXISTS (
              SELECT 1 FROM employee_identities i
              WHERE i.employee_id = e.employee_id
          )
        """,
    ),
    (
        "missing_address",
        "Aktif tanpa alamat",
        """
        SELECT COUNT(*)
        FROM employees e
        WHERE e.is_active = true
          AND NOT EXISTS (
              SELECT 1 FROM employee_addresses a
              WHERE a.employee_id = e.employee_id
          )
        """,
    ),
)


EXPORT_QUERIES: tuple[str, ...] = (
    """
    SELECT
        'NORMALIZED_FUTURE_JOIN_DATE' AS issue_code,
        'REVIEW' AS severity,
        e.employee_id,
        e.employee_no,
        e.full_name,
        COALESCE(d.division_name, '-') AS current_division,
        COALESCE(p.position_name, '-') AS current_position,
        a.start_date::text AS observed_value,
        'Tanggal sumber lebih besar dari snapshot Maret 2026; start aktif dinormalisasi dan tanggal asli disimpan di notes.' AS recommendation
    FROM employee_assignments a
    JOIN employees e ON e.employee_id = a.employee_id
    LEFT JOIN divisions d ON d.division_id = a.division_id
    LEFT JOIN positions p ON p.position_id = a.position_id
    WHERE a.notes LIKE '%review_original_join_date=%'
    """,
    """
    SELECT
        'AGE_REVIEW' AS issue_code,
        'REVIEW' AS severity,
        e.employee_id,
        e.employee_no,
        e.full_name,
        COALESCE(d.division_name, '-') AS current_division,
        COALESCE(p.position_name, '-') AS current_position,
        CONCAT(e.birth_date::text, ' / ', EXTRACT(YEAR FROM age(CURRENT_DATE, e.birth_date))::int, ' tahun') AS observed_value,
        'Verifikasi ulang tanggal lahir di dokumen HR resmi.' AS recommendation
    FROM employees e
    LEFT JOIN employee_assignments a ON a.employee_id = e.employee_id AND a.is_current = true
    LEFT JOIN divisions d ON d.division_id = a.division_id
    LEFT JOIN positions p ON p.position_id = a.position_id
    WHERE e.is_active = true
      AND e.birth_date IS NOT NULL
      AND (
          e.birth_date > CURRENT_DATE - INTERVAL '17 years'
          OR e.birth_date < CURRENT_DATE - INTERVAL '70 years'
      )
    """,
    """
    SELECT
        'MISSING_IDENTITY' AS issue_code,
        'INFO' AS severity,
        e.employee_id,
        e.employee_no,
        e.full_name,
        COALESCE(d.division_name, '-') AS current_division,
        COALESCE(p.position_name, '-') AS current_position,
        '-' AS observed_value,
        'Lengkapi KTP/NIK jika tersedia di dokumen HR.' AS recommendation
    FROM employees e
    LEFT JOIN employee_assignments a ON a.employee_id = e.employee_id AND a.is_current = true
    LEFT JOIN divisions d ON d.division_id = a.division_id
    LEFT JOIN positions p ON p.position_id = a.position_id
    WHERE e.is_active = true
      AND NOT EXISTS (
          SELECT 1 FROM employee_identities i
          WHERE i.employee_id = e.employee_id
      )
    """,
    """
    SELECT
        'MISSING_ADDRESS' AS issue_code,
        'INFO' AS severity,
        e.employee_id,
        e.employee_no,
        e.full_name,
        COALESCE(d.division_name, '-') AS current_division,
        COALESCE(p.position_name, '-') AS current_position,
        '-' AS observed_value,
        'Lengkapi alamat domisili jika tersedia di dokumen HR.' AS recommendation
    FROM employees e
    LEFT JOIN employee_assignments a ON a.employee_id = e.employee_id AND a.is_current = true
    LEFT JOIN divisions d ON d.division_id = a.division_id
    LEFT JOIN positions p ON p.position_id = a.position_id
    WHERE e.is_active = true
      AND NOT EXISTS (
          SELECT 1 FROM employee_addresses ad
          WHERE ad.employee_id = e.employee_id
      )
    """,
    """
    SELECT
        'DUPLICATE_EMPLOYEE_NO' AS issue_code,
        'BLOCKING' AS severity,
        e.employee_id,
        e.employee_no,
        e.full_name,
        '-' AS current_division,
        '-' AS current_position,
        e.employee_no AS observed_value,
        'Nomor karyawan harus unik.' AS recommendation
    FROM employees e
    WHERE e.employee_no IN (
        SELECT employee_no
        FROM employees
        GROUP BY employee_no
        HAVING COUNT(*) > 1
    )
    """,
    """
    SELECT
        'DUPLICATE_IDENTITY' AS issue_code,
        'BLOCKING' AS severity,
        e.employee_id,
        e.employee_no,
        e.full_name,
        '-' AS current_division,
        '-' AS current_position,
        'masked' AS observed_value,
        'Nomor identitas harus unik; cek dokumen sumber.' AS recommendation
    FROM employee_identities i
    JOIN employees e ON e.employee_id = i.employee_id
    WHERE i.identity_number IN (
        SELECT identity_number
        FROM employee_identities
        GROUP BY identity_number
        HAVING COUNT(*) > 1
    )
    """,
)


def scalar(connection, sql: str) -> int:
    value = connection.execute(text(sql)).scalar()
    return int(value or 0)


def export_review_rows(connection, output_path: Path) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "issue_code",
        "severity",
        "employee_id",
        "employee_no",
        "full_name",
        "current_division",
        "current_position",
        "observed_value",
        "recommendation",
    ]
    rows: list[dict[str, object]] = []
    for query in EXPORT_QUERIES:
        rows.extend(dict(row) for row in connection.execute(text(query)).mappings())

    rows.sort(
        key=lambda row: (
            str(row.get("severity") or ""),
            str(row.get("issue_code") or ""),
            str(row.get("current_division") or ""),
            str(row.get("employee_no") or ""),
        )
    )
    with output_path.open("w", newline="", encoding="utf-8-sig") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate PT GBR HRIS data quality.")
    parser.add_argument(
        "--export",
        nargs="?",
        const=str(DEFAULT_REPORT_PATH),
        default=None,
        help="Export row-level review CSV. Uses reports/hris_data_quality_review_maret_2026.csv by default.",
    )
    return parser.parse_args()


def main() -> None:
    if engine is None:
        raise RuntimeError("Database engine belum siap. Cek konfigurasi .env.")

    args = parse_args()
    ensure_governance_tables_with_admin()
    with engine.connect() as connection:
        ensure_governance_tables(connection)
        results = [(key, label, scalar(connection, sql)) for key, label, sql in RULES]
    with engine.begin() as connection:
        sync_stats = sync_data_quality_issues(connection)
        exported_rows = export_review_csv(connection, Path(args.export)) if args.export else None

    blocking_keys = {
        "missing_assignment",
        "duplicate_current_assignment",
        "multiple_open_contracts",
        "duplicate_employee_no",
        "duplicate_identity",
    }
    review_keys = {"future_assignment_start", "source_date_review", "age_review"}
    blocking_total = sum(value for key, _, value in results if key in blocking_keys)
    review_total = sum(value for key, _, value in results if key in review_keys)

    print("HRIS Data Quality Snapshot")
    print("source_period=Maret 2026")
    for key, label, value in results:
        status = "OK"
        if key in blocking_keys and value:
            status = "BLOCKING"
        elif key in review_keys and value:
            status = "REVIEW"
        print(f"{key}={value} | {status} | {label}")
    print(f"blocking_total={blocking_total}")
    print(f"review_total={review_total}")
    print(f"governance_open_total={sync_stats['open_total']}")
    print(f"governance_watch_total={sync_stats['watch_total']}")
    if exported_rows is not None:
        print(f"review_export={Path(args.export)}")
        print(f"review_export_rows={exported_rows}")


if __name__ == "__main__":
    main()
