"""create HRIS and manpower control schema

Revision ID: 20260525_01
Revises: 01c1491f2228
Create Date: 2026-05-25 00:00:00
"""
from __future__ import annotations

from typing import Any

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260525_01"
down_revision = "01c1491f2228"
branch_labels = None
depends_on = None


HR_PERMISSIONS = (
    "hr.employee.view",
    "hr.employee.create",
    "hr.employee.update",
    "hr.employee.delete",
    "hr.identity.view",
    "hr.identity.manage",
    "hr.attendance.view",
    "hr.attendance.manage",
    "hr.payroll.view",
    "hr.payroll.manage",
    "hr.manpower.view",
    "hr.manpower.manage",
    "hr.work_output.view",
    "hr.work_output.manage",
    "hr.bpjs.view",
    "hr.bpjs.manage",
    "hr.audit.view",
)


def _table_exists(inspector: Any, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _seed_lookups() -> None:
    op.execute(
        """
        INSERT INTO hr_employee_groups (code, name, description, sort_order)
        VALUES
            ('STF', 'Staff', 'Pimpinan, asisten, KTU, HRGA, controller, pengawas, dan administratif level staff.', 10),
            ('BLN', 'Karyawan Bulanan Non Staff', 'Mandor, krani, operator, driver, security, dan tenaga umum bulanan non-staff.', 20),
            ('PHT/SKU', 'Karyawan Tetap Non Staff', 'SKU, PHT, tenaga tetap lapangan, dan karyawan tetap operasional non-staff.', 30),
            ('PHL/KHL', 'Karyawan Harian Lepas', 'Tenaga harian lepas berbasis HK. BHL disimpan sebagai alias historis.', 40),
            ('BRG', 'Borongan', 'Tenaga berbasis output atau grup kerja seperti panen, muat buah, pruning, semprot, dan parit.', 50)
        ON CONFLICT (code) DO UPDATE SET
            name = EXCLUDED.name,
            description = EXCLUDED.description,
            sort_order = EXCLUDED.sort_order
        """
    )

    op.execute(
        """
        INSERT INTO hr_employment_types (code, name, description)
        VALUES
            ('PKWTT', 'PKWTT', 'Perjanjian kerja waktu tidak tertentu.'),
            ('PKWT', 'PKWT', 'Perjanjian kerja waktu tertentu.'),
            ('PROBATION', 'Probation', 'Masa percobaan atau orientasi.'),
            ('KHL', 'KHL', 'Hubungan kerja harian lepas.'),
            ('BORONGAN', 'Borongan', 'Hubungan kerja berbasis output atau grup kerja.')
        ON CONFLICT (code) DO UPDATE SET
            name = EXCLUDED.name,
            description = EXCLUDED.description
        """
    )

    op.execute(
        """
        INSERT INTO hr_pay_schemes (code, name, unit, description)
        VALUES
            ('MONTHLY', 'Bulanan', 'bulan', 'Upah tetap bulanan.'),
            ('HK', 'Harian Kerja', 'HK', 'Upah berdasarkan hari kerja.'),
            ('KG_PANEN', 'Kg Panen', 'kg', 'Upah atau premi berdasarkan kilogram panen.'),
            ('OUTPUT', 'Borongan Output', 'output', 'Upah berbasis hasil kerja atau grup borongan.')
        ON CONFLICT (code) DO UPDATE SET
            name = EXCLUDED.name,
            unit = EXCLUDED.unit,
            description = EXCLUDED.description
        """
    )

    op.execute(
        """
        INSERT INTO hr_job_families (code, name, description)
        VALUES
            ('PANEN', 'Panen', 'Potong buah, kutip brondolan, muat buah, dan aktivitas panen terkait.'),
            ('RAWAT', 'Rawat', 'Perawatan tanaman dan gawangan.'),
            ('PUPUK', 'Pupuk', 'Pemupukan dan pendukungnya.'),
            ('SEMPROT', 'Semprot', 'Penyemprotan dan pengendalian gulma.'),
            ('PRUNING', 'Pruning', 'Tunas, pruning, dan pemeliharaan pelepah.'),
            ('TRAKSI', 'Traksi', 'Transport, alat berat, operator, driver, dan mekanisasi.'),
            ('BENGKEL', 'Bengkel', 'Perawatan kendaraan, alat, dan mesin.'),
            ('KANTOR', 'Kantor', 'Administrasi, HRGA, KTU, keuangan, controller, dan fungsi kantor.'),
            ('GUDANG', 'Gudang', 'Gudang, logistik, material, dan inventory.'),
            ('BIBITAN', 'Bibitan', 'Pembibitan dan nursery.'),
            ('SECURITY', 'Security', 'Keamanan estate, pabrik, dan fasilitas.'),
            ('SURVEY_GIS', 'Survey/GIS', 'Survey, pemetaan, GIS, dan data spasial.')
        ON CONFLICT (code) DO UPDATE SET
            name = EXCLUDED.name,
            description = EXCLUDED.description
        """
    )


def _seed_permissions() -> None:
    op.execute(
        """
        SELECT setval(
            pg_get_serial_sequence('permissions', 'id'),
            COALESCE((SELECT MAX(id) FROM permissions), 0) + 1,
            false
        )
        """
    )

    for permission in HR_PERMISSIONS:
        op.execute(
            f"""
            INSERT INTO permissions (permission_name)
            VALUES ('{permission}')
            ON CONFLICT (permission_name) DO NOTHING
            """
        )

    superior_permissions = ", ".join(f"'{permission}'" for permission in HR_PERMISSIONS)
    administrator_permissions = ", ".join(
        f"'{permission}'"
        for permission in HR_PERMISSIONS
        if permission not in {"hr.employee.delete", "hr.payroll.manage"}
    )
    auditor_permissions = ", ".join(
        f"'{permission}'"
        for permission in HR_PERMISSIONS
        if permission.endswith(".view")
    )

    op.execute(
        f"""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r
        CROSS JOIN permissions p
        WHERE r.role_name = 'Superior'
          AND p.permission_name IN ({superior_permissions})
        ON CONFLICT (role_id, permission_id) DO NOTHING
        """
    )
    op.execute(
        f"""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r
        CROSS JOIN permissions p
        WHERE r.role_name = 'Administrator'
          AND p.permission_name IN ({administrator_permissions})
        ON CONFLICT (role_id, permission_id) DO NOTHING
        """
    )
    op.execute(
        f"""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r
        CROSS JOIN permissions p
        WHERE r.role_name = 'Auditor'
          AND p.permission_name IN ({auditor_permissions})
        ON CONFLICT (role_id, permission_id) DO NOTHING
        """
    )


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if not _table_exists(inspector, "hr_employee_groups"):
        op.create_table(
            "hr_employee_groups",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("code", sa.String(length=16), nullable=False),
            sa.Column("name", sa.String(length=100), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.UniqueConstraint("code", name="uq_hr_employee_groups_code"),
        )

    if not _table_exists(inspector, "hr_employment_types"):
        op.create_table(
            "hr_employment_types",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("code", sa.String(length=24), nullable=False),
            sa.Column("name", sa.String(length=100), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.UniqueConstraint("code", name="uq_hr_employment_types_code"),
        )

    if not _table_exists(inspector, "hr_pay_schemes"):
        op.create_table(
            "hr_pay_schemes",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("code", sa.String(length=32), nullable=False),
            sa.Column("name", sa.String(length=100), nullable=False),
            sa.Column("unit", sa.String(length=32), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.UniqueConstraint("code", name="uq_hr_pay_schemes_code"),
        )

    if not _table_exists(inspector, "hr_job_families"):
        op.create_table(
            "hr_job_families",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("code", sa.String(length=32), nullable=False),
            sa.Column("name", sa.String(length=100), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.UniqueConstraint("code", name="uq_hr_job_families_code"),
        )

    if not _table_exists(inspector, "hr_departments"):
        op.create_table(
            "hr_departments",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("code", sa.String(length=32), nullable=False),
            sa.Column("name", sa.String(length=100), nullable=False),
            sa.Column("parent_id", sa.Integer(), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.ForeignKeyConstraint(["parent_id"], ["hr_departments.id"], ondelete="SET NULL"),
            sa.UniqueConstraint("code", name="uq_hr_departments_code"),
        )

    if not _table_exists(inspector, "hr_positions"):
        op.create_table(
            "hr_positions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("code", sa.String(length=32), nullable=False),
            sa.Column("title", sa.String(length=120), nullable=False),
            sa.Column("level", sa.String(length=64), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.UniqueConstraint("code", name="uq_hr_positions_code"),
        )

    if not _table_exists(inspector, "hr_work_locations"):
        op.create_table(
            "hr_work_locations",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("code", sa.String(length=32), nullable=False),
            sa.Column("name", sa.String(length=120), nullable=False),
            sa.Column("location_type", sa.String(length=32), nullable=False),
            sa.Column("parent_id", sa.Integer(), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.ForeignKeyConstraint(["parent_id"], ["hr_work_locations.id"], ondelete="SET NULL"),
            sa.UniqueConstraint("code", name="uq_hr_work_locations_code"),
        )

    _seed_lookups()

    if not _table_exists(inspector, "hr_employees"):
        op.create_table(
            "hr_employees",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("employee_no", sa.String(length=32), nullable=False),
            sa.Column("full_name", sa.String(length=160), nullable=False),
            sa.Column("preferred_name", sa.String(length=100), nullable=True),
            sa.Column("linked_user_id", sa.Integer(), nullable=True),
            sa.Column("current_group_id", sa.Integer(), nullable=False),
            sa.Column("family_status", sa.String(length=8), nullable=True),
            sa.Column("employment_status", sa.String(length=24), nullable=False, server_default="active"),
            sa.Column("join_date", sa.Date(), nullable=True),
            sa.Column("exit_date", sa.Date(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_by_user_id", sa.Integer(), nullable=True),
            sa.Column("updated_by_user_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.CheckConstraint(
                "employment_status IN ('active', 'inactive', 'resigned', 'terminated', 'retired')",
                name="ck_hr_employees_employment_status",
            ),
            sa.ForeignKeyConstraint(["linked_user_id"], ["users.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["current_group_id"], ["hr_employee_groups.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="SET NULL"),
            sa.UniqueConstraint("employee_no", name="uq_hr_employees_employee_no"),
            sa.UniqueConstraint("linked_user_id", name="uq_hr_employees_linked_user_id"),
        )
        op.create_index("ix_hr_employees_current_group_id", "hr_employees", ["current_group_id"])
        op.create_index("ix_hr_employees_full_name", "hr_employees", ["full_name"])

    if not _table_exists(inspector, "hr_employee_identities"):
        op.create_table(
            "hr_employee_identities",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("employee_id", sa.Integer(), nullable=False),
            sa.Column("nik", sa.String(length=32), nullable=True),
            sa.Column("kk_number", sa.String(length=32), nullable=True),
            sa.Column("birth_place", sa.String(length=100), nullable=True),
            sa.Column("birth_date", sa.Date(), nullable=True),
            sa.Column("gender", sa.String(length=16), nullable=True),
            sa.Column("religion", sa.String(length=32), nullable=True),
            sa.Column("education_level", sa.String(length=64), nullable=True),
            sa.Column("marital_status", sa.String(length=32), nullable=True),
            sa.Column("tax_number", sa.String(length=32), nullable=True),
            sa.Column("phone", sa.String(length=32), nullable=True),
            sa.Column("email", sa.String(length=120), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.ForeignKeyConstraint(["employee_id"], ["hr_employees.id"], ondelete="CASCADE"),
            sa.UniqueConstraint("employee_id", name="uq_hr_employee_identities_employee_id"),
            sa.UniqueConstraint("nik", name="uq_hr_employee_identities_nik"),
        )

    if not _table_exists(inspector, "hr_employee_addresses"):
        op.create_table(
            "hr_employee_addresses",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("employee_id", sa.Integer(), nullable=False),
            sa.Column("address_type", sa.String(length=24), nullable=False),
            sa.Column("address_line", sa.Text(), nullable=False),
            sa.Column("village", sa.String(length=100), nullable=True),
            sa.Column("district", sa.String(length=100), nullable=True),
            sa.Column("regency", sa.String(length=100), nullable=True),
            sa.Column("province", sa.String(length=100), nullable=True),
            sa.Column("postal_code", sa.String(length=16), nullable=True),
            sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.CheckConstraint("address_type IN ('ktp', 'domicile', 'emergency')", name="ck_hr_employee_addresses_type"),
            sa.ForeignKeyConstraint(["employee_id"], ["hr_employees.id"], ondelete="CASCADE"),
        )
        op.create_index("ix_hr_employee_addresses_employee_id", "hr_employee_addresses", ["employee_id"])

    if not _table_exists(inspector, "hr_employee_families"):
        op.create_table(
            "hr_employee_families",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("employee_id", sa.Integer(), nullable=False),
            sa.Column("relationship_type", sa.String(length=32), nullable=False),
            sa.Column("full_name", sa.String(length=160), nullable=False),
            sa.Column("birth_date", sa.Date(), nullable=True),
            sa.Column("gender", sa.String(length=16), nullable=True),
            sa.Column("occupation", sa.String(length=100), nullable=True),
            sa.Column("is_dependent", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(["employee_id"], ["hr_employees.id"], ondelete="CASCADE"),
        )
        op.create_index("ix_hr_employee_families_employee_id", "hr_employee_families", ["employee_id"])

    if not _table_exists(inspector, "hr_employee_group_histories"):
        op.create_table(
            "hr_employee_group_histories",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("employee_id", sa.Integer(), nullable=False),
            sa.Column("employee_group_id", sa.Integer(), nullable=False),
            sa.Column("effective_start", sa.Date(), nullable=False),
            sa.Column("effective_end", sa.Date(), nullable=True),
            sa.Column("reason", sa.String(length=160), nullable=True),
            sa.Column("created_by_user_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.CheckConstraint("effective_end IS NULL OR effective_end >= effective_start", name="ck_hr_group_history_date_range"),
            sa.ForeignKeyConstraint(["employee_id"], ["hr_employees.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["employee_group_id"], ["hr_employee_groups.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
            sa.UniqueConstraint("employee_id", "effective_start", name="uq_hr_group_history_employee_start"),
        )
        op.create_index("ix_hr_group_histories_employee_id", "hr_employee_group_histories", ["employee_id"])
        op.create_index("ix_hr_group_histories_group_id", "hr_employee_group_histories", ["employee_group_id"])

    if not _table_exists(inspector, "hr_employment_contracts"):
        op.create_table(
            "hr_employment_contracts",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("employee_id", sa.Integer(), nullable=False),
            sa.Column("employment_type_id", sa.Integer(), nullable=False),
            sa.Column("contract_no", sa.String(length=64), nullable=True),
            sa.Column("start_date", sa.Date(), nullable=False),
            sa.Column("end_date", sa.Date(), nullable=True),
            sa.Column("probation_end_date", sa.Date(), nullable=True),
            sa.Column("exit_reason", sa.String(length=160), nullable=True),
            sa.Column("document_ref", sa.String(length=255), nullable=True),
            sa.Column("created_by_user_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.CheckConstraint("end_date IS NULL OR end_date >= start_date", name="ck_hr_contracts_date_range"),
            sa.ForeignKeyConstraint(["employee_id"], ["hr_employees.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["employment_type_id"], ["hr_employment_types.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
            sa.UniqueConstraint("employee_id", "contract_no", name="uq_hr_contracts_employee_contract_no"),
        )
        op.create_index("ix_hr_contracts_employee_id", "hr_employment_contracts", ["employee_id"])
        op.create_index("ix_hr_contracts_type_id", "hr_employment_contracts", ["employment_type_id"])

    if not _table_exists(inspector, "hr_employee_assignments"):
        op.create_table(
            "hr_employee_assignments",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("employee_id", sa.Integer(), nullable=False),
            sa.Column("department_id", sa.Integer(), nullable=False),
            sa.Column("position_id", sa.Integer(), nullable=True),
            sa.Column("job_family_id", sa.Integer(), nullable=False),
            sa.Column("work_location_id", sa.Integer(), nullable=True),
            sa.Column("supervisor_employee_id", sa.Integer(), nullable=True),
            sa.Column("effective_start", sa.Date(), nullable=False),
            sa.Column("effective_end", sa.Date(), nullable=True),
            sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_by_user_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.CheckConstraint("effective_end IS NULL OR effective_end >= effective_start", name="ck_hr_assignments_date_range"),
            sa.ForeignKeyConstraint(["employee_id"], ["hr_employees.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["department_id"], ["hr_departments.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["position_id"], ["hr_positions.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["job_family_id"], ["hr_job_families.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["work_location_id"], ["hr_work_locations.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["supervisor_employee_id"], ["hr_employees.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        )
        op.create_index("ix_hr_assignments_employee_id", "hr_employee_assignments", ["employee_id"])
        op.create_index("ix_hr_assignments_department_id", "hr_employee_assignments", ["department_id"])
        op.create_index("ix_hr_assignments_work_location_id", "hr_employee_assignments", ["work_location_id"])

    if not _table_exists(inspector, "hr_employee_movements"):
        op.create_table(
            "hr_employee_movements",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("employee_id", sa.Integer(), nullable=False),
            sa.Column("movement_type", sa.String(length=32), nullable=False),
            sa.Column("effective_date", sa.Date(), nullable=False),
            sa.Column("from_assignment_id", sa.Integer(), nullable=True),
            sa.Column("to_assignment_id", sa.Integer(), nullable=True),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("approved_by_user_id", sa.Integer(), nullable=True),
            sa.Column("created_by_user_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.CheckConstraint(
                "movement_type IN ('join', 'transfer', 'promotion', 'demotion', 'group_change', 'resignation', 'termination', 'retirement')",
                name="ck_hr_movements_type",
            ),
            sa.ForeignKeyConstraint(["employee_id"], ["hr_employees.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["from_assignment_id"], ["hr_employee_assignments.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["to_assignment_id"], ["hr_employee_assignments.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["approved_by_user_id"], ["users.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        )
        op.create_index("ix_hr_movements_employee_id", "hr_employee_movements", ["employee_id"])
        op.create_index("ix_hr_movements_effective_date", "hr_employee_movements", ["effective_date"])

    if not _table_exists(inspector, "hr_wage_rates"):
        op.create_table(
            "hr_wage_rates",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("employee_id", sa.Integer(), nullable=True),
            sa.Column("pay_scheme_id", sa.Integer(), nullable=False),
            sa.Column("effective_start", sa.Date(), nullable=False),
            sa.Column("effective_end", sa.Date(), nullable=True),
            sa.Column("base_amount", sa.Numeric(14, 2), nullable=False),
            sa.Column("premium_amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
            sa.Column("currency", sa.String(length=3), nullable=False, server_default="IDR"),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_by_user_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.CheckConstraint("effective_end IS NULL OR effective_end >= effective_start", name="ck_hr_wage_rates_date_range"),
            sa.CheckConstraint("base_amount >= 0", name="ck_hr_wage_rates_base_amount"),
            sa.ForeignKeyConstraint(["employee_id"], ["hr_employees.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["pay_scheme_id"], ["hr_pay_schemes.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
            sa.UniqueConstraint("employee_id", "pay_scheme_id", "effective_start", name="uq_hr_wage_rates_employee_scheme_start"),
        )
        op.create_index("ix_hr_wage_rates_employee_id", "hr_wage_rates", ["employee_id"])

    if not _table_exists(inspector, "hr_payroll_profiles"):
        op.create_table(
            "hr_payroll_profiles",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("employee_id", sa.Integer(), nullable=False),
            sa.Column("pay_scheme_id", sa.Integer(), nullable=False),
            sa.Column("bank_name", sa.String(length=100), nullable=True),
            sa.Column("bank_account_no", sa.String(length=64), nullable=True),
            sa.Column("bank_account_name", sa.String(length=160), nullable=True),
            sa.Column("tax_status", sa.String(length=16), nullable=True),
            sa.Column("is_bpjs_tk_active", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("is_bpjs_health_active", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.ForeignKeyConstraint(["employee_id"], ["hr_employees.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["pay_scheme_id"], ["hr_pay_schemes.id"], ondelete="RESTRICT"),
            sa.UniqueConstraint("employee_id", name="uq_hr_payroll_profiles_employee_id"),
        )

    if not _table_exists(inspector, "hr_attendance_daily"):
        op.create_table(
            "hr_attendance_daily",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("employee_id", sa.Integer(), nullable=False),
            sa.Column("attendance_date", sa.Date(), nullable=False),
            sa.Column("status", sa.String(length=24), nullable=False),
            sa.Column("work_hours", sa.Numeric(5, 2), nullable=False, server_default="0"),
            sa.Column("check_in_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("check_out_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("source", sa.String(length=32), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("approved_by_user_id", sa.Integer(), nullable=True),
            sa.Column("created_by_user_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.CheckConstraint(
                "status IN ('present', 'absent', 'leave', 'sick', 'permit', 'holiday', 'off')",
                name="ck_hr_attendance_status",
            ),
            sa.CheckConstraint("work_hours >= 0", name="ck_hr_attendance_work_hours"),
            sa.ForeignKeyConstraint(["employee_id"], ["hr_employees.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["approved_by_user_id"], ["users.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
            sa.UniqueConstraint("employee_id", "attendance_date", name="uq_hr_attendance_employee_date"),
        )
        op.create_index("ix_hr_attendance_date", "hr_attendance_daily", ["attendance_date"])

    if not _table_exists(inspector, "hr_work_outputs"):
        op.create_table(
            "hr_work_outputs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("work_date", sa.Date(), nullable=False),
            sa.Column("employee_id", sa.Integer(), nullable=True),
            sa.Column("work_group_code", sa.String(length=64), nullable=True),
            sa.Column("job_family_id", sa.Integer(), nullable=False),
            sa.Column("activity_name", sa.String(length=120), nullable=False),
            sa.Column("block_code", sa.String(length=64), nullable=True),
            sa.Column("quantity", sa.Numeric(14, 3), nullable=False),
            sa.Column("unit", sa.String(length=32), nullable=False),
            sa.Column("rate_amount", sa.Numeric(14, 2), nullable=True),
            sa.Column("total_amount", sa.Numeric(14, 2), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("verified_by_user_id", sa.Integer(), nullable=True),
            sa.Column("created_by_user_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.CheckConstraint("quantity >= 0", name="ck_hr_work_outputs_quantity"),
            sa.ForeignKeyConstraint(["employee_id"], ["hr_employees.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["job_family_id"], ["hr_job_families.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["verified_by_user_id"], ["users.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        )
        op.create_index("ix_hr_work_outputs_work_date", "hr_work_outputs", ["work_date"])
        op.create_index("ix_hr_work_outputs_employee_id", "hr_work_outputs", ["employee_id"])
        op.create_index("ix_hr_work_outputs_work_group_code", "hr_work_outputs", ["work_group_code"])

    if not _table_exists(inspector, "hr_manpower_snapshots"):
        op.create_table(
            "hr_manpower_snapshots",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("snapshot_date", sa.Date(), nullable=False),
            sa.Column("scope_code", sa.String(length=64), nullable=False),
            sa.Column("title", sa.String(length=160), nullable=False),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_by_user_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
            sa.UniqueConstraint("snapshot_date", "scope_code", name="uq_hr_manpower_snapshots_date_scope"),
        )

    if not _table_exists(inspector, "hr_manpower_snapshot_lines"):
        op.create_table(
            "hr_manpower_snapshot_lines",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("snapshot_id", sa.Integer(), nullable=False),
            sa.Column("employee_group_id", sa.Integer(), nullable=False),
            sa.Column("job_family_id", sa.Integer(), nullable=True),
            sa.Column("department_id", sa.Integer(), nullable=True),
            sa.Column("work_location_id", sa.Integer(), nullable=True),
            sa.Column("headcount", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.CheckConstraint("headcount >= 0", name="ck_hr_manpower_snapshot_lines_headcount"),
            sa.ForeignKeyConstraint(["snapshot_id"], ["hr_manpower_snapshots.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["employee_group_id"], ["hr_employee_groups.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["job_family_id"], ["hr_job_families.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["department_id"], ["hr_departments.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["work_location_id"], ["hr_work_locations.id"], ondelete="RESTRICT"),
            sa.UniqueConstraint(
                "snapshot_id",
                "employee_group_id",
                "job_family_id",
                "department_id",
                "work_location_id",
                name="uq_hr_manpower_snapshot_lines_dimension",
            ),
        )

    if not _table_exists(inspector, "hr_bpjs_enrollments"):
        op.create_table(
            "hr_bpjs_enrollments",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("employee_id", sa.Integer(), nullable=False),
            sa.Column("bpjs_type", sa.String(length=24), nullable=False),
            sa.Column("membership_no", sa.String(length=64), nullable=True),
            sa.Column("registered_date", sa.Date(), nullable=True),
            sa.Column("effective_date", sa.Date(), nullable=True),
            sa.Column("end_date", sa.Date(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.CheckConstraint("bpjs_type IN ('health', 'employment')", name="ck_hr_bpjs_type"),
            sa.ForeignKeyConstraint(["employee_id"], ["hr_employees.id"], ondelete="CASCADE"),
            sa.UniqueConstraint("employee_id", "bpjs_type", name="uq_hr_bpjs_employee_type"),
        )

    _seed_permissions()


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    for permission in HR_PERMISSIONS:
        op.execute(
            f"""
            DELETE FROM role_permissions
            WHERE permission_id IN (
                SELECT id FROM permissions WHERE permission_name = '{permission}'
            )
            """
        )
        op.execute(f"DELETE FROM permissions WHERE permission_name = '{permission}'")

    tables = [
        "hr_bpjs_enrollments",
        "hr_manpower_snapshot_lines",
        "hr_manpower_snapshots",
        "hr_work_outputs",
        "hr_attendance_daily",
        "hr_payroll_profiles",
        "hr_wage_rates",
        "hr_employee_movements",
        "hr_employee_assignments",
        "hr_employment_contracts",
        "hr_employee_group_histories",
        "hr_employee_families",
        "hr_employee_addresses",
        "hr_employee_identities",
        "hr_employees",
        "hr_work_locations",
        "hr_positions",
        "hr_departments",
        "hr_job_families",
        "hr_pay_schemes",
        "hr_employment_types",
        "hr_employee_groups",
    ]
    for table_name in tables:
        if _table_exists(inspector, table_name):
            op.drop_table(table_name)
