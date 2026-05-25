from sqlalchemy.orm import configure_mappers

from src.database.models import Base, HrEmployee, HrEmployeeGroup, HrPayScheme


def test_hris_tables_are_registered_in_metadata() -> None:
    expected_tables = {
        "hr_employees",
        "hr_employee_groups",
        "hr_employment_types",
        "hr_pay_schemes",
        "hr_job_families",
        "hr_employee_group_histories",
        "hr_employment_contracts",
        "hr_employee_assignments",
        "hr_wage_rates",
        "hr_attendance_daily",
        "hr_work_outputs",
        "hr_manpower_snapshots",
        "hr_manpower_snapshot_lines",
        "hr_bpjs_enrollments",
    }

    assert expected_tables.issubset(Base.metadata.tables)


def test_hris_employee_keeps_manpower_group_separate_from_pay_scheme() -> None:
    employee_columns = HrEmployee.__table__.columns.keys()
    group_columns = HrEmployeeGroup.__table__.columns.keys()
    pay_scheme_columns = HrPayScheme.__table__.columns.keys()

    assert "current_group_id" in employee_columns
    assert "family_status" in employee_columns
    assert "code" in group_columns
    assert "unit" in pay_scheme_columns
    assert "pay_scheme_id" not in employee_columns


def test_hris_orm_mappers_configure_without_ambiguous_relationships() -> None:
    configure_mappers()
