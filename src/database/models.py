import os
from pathlib import Path
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    create_engine,
    func,
    inspect,
    text,
)
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.orm.exc import DetachedInstanceError
from dotenv import load_dotenv

try:
    from auth.passwords import create_password_hash
except ImportError:
    from src.auth.passwords import create_password_hash

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = PROJECT_ROOT / ".env"

load_dotenv(ENV_FILE)

_PASSWORD_PLACEHOLDERS = {
    "GANTI_DENGAN_PASSWORD_POSTGRES_ANDA",
    "PASSWORD_POSTGRES_ANDA",
    "<PASSWORD_ANDA>",
    "<PASSWORD>",
}

_LOCAL_HOST_ALIASES = {
    "localhost",
    "127.0.0.1",
    "::1",
    "0.0.0.0",
}

_SSLMODE_STRICT_VALUES = {
    "require",
    "verify-ca",
    "verify-full",
}

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    full_name = Column(String, nullable=True)
    email = Column(String, unique=True, nullable=True)
    phone = Column(String, nullable=True)
    status = Column(String, nullable=False, server_default='aktif')
    last_login = Column(DateTime(timezone=True), nullable=True)
    last_logout = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    password_record = relationship("UserPassword", back_populates="user", uselist=False, cascade="all, delete-orphan")
    pin_record = relationship("UserPin", back_populates="user", uselist=False, cascade="all, delete-orphan")
    role_links = relationship("UserRole", back_populates="user", cascade="all, delete-orphan")

    @property
    def nama(self) -> str | None:
        return self.full_name

    @nama.setter
    def nama(self, value: str | None) -> None:
        self.full_name = value

    @property
    def role(self) -> str | None:
        try:
            role_links = self.role_links
        except DetachedInstanceError:
            return getattr(self, "_cached_role", None)

        if not role_links:
            self._cached_role = None
            return None

        for role_link in role_links:
            role = getattr(role_link, "role", None)
            role_name = getattr(role, "role_name", None)
            if role_name:
                self._cached_role = role_name
                return role_name

        self._cached_role = None
        return None


class Role(Base):
    __tablename__ = 'roles'

    id = Column(Integer, primary_key=True)
    role_name = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=True)

    user_links = relationship("UserRole", back_populates="role", cascade="all, delete-orphan")
    permission_links = relationship("RolePermission", back_populates="role", cascade="all, delete-orphan")


class Permission(Base):
    __tablename__ = 'permissions'

    id = Column(Integer, primary_key=True)
    permission_name = Column(String, unique=True, nullable=False)

    role_links = relationship("RolePermission", back_populates="permission", cascade="all, delete-orphan")


class UserRole(Base):
    __tablename__ = 'user_roles'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    role_id = Column(Integer, ForeignKey('roles.id', ondelete='CASCADE'), nullable=False)

    user = relationship("User", back_populates="role_links")
    role = relationship("Role", back_populates="user_links")


class RolePermission(Base):
    __tablename__ = 'role_permissions'

    role_id = Column(Integer, ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True)
    permission_id = Column(Integer, ForeignKey('permissions.id', ondelete='CASCADE'), primary_key=True)

    role = relationship("Role", back_populates="permission_links")
    permission = relationship("Permission", back_populates="role_links")


class UserPassword(Base):
    __tablename__ = 'user_passwords'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True)
    password_hash = Column(String, nullable=False)
    password_salt = Column(String, nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="password_record")


class UserPin(Base):
    __tablename__ = 'user_pins'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True)
    pin_hash = Column(String, nullable=False)
    pin_salt = Column(String, nullable=False)
    failed_attempts = Column(Integer, nullable=False, server_default='0')
    locked_until = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="pin_record")


class LoginAttempt(Base):
    __tablename__ = 'login_attempts'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    ip_address = Column(String, nullable=True)
    success = Column(Boolean, nullable=False)
    attempt_time = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class UserSession(Base):
    __tablename__ = 'user_sessions'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    access_token = Column(String, nullable=False)
    refresh_token = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    expired_at = Column(DateTime(timezone=True), nullable=False)


class AuditLog(Base):
    __tablename__ = 'audit_logs'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    action = Column(String, nullable=False)
    action_type = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    ip_address = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class HrEmployeeGroup(Base):
    __tablename__ = "hr_employee_groups"

    id = Column(Integer, primary_key=True)
    code = Column(String(16), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    sort_order = Column(Integer, nullable=False, server_default="0")
    is_active = Column(Boolean, nullable=False, server_default="true")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    employees = relationship("HrEmployee", back_populates="current_group")
    group_histories = relationship("HrEmployeeGroupHistory", back_populates="employee_group")


class HrEmploymentType(Base):
    __tablename__ = "hr_employment_types"

    id = Column(Integer, primary_key=True)
    code = Column(String(24), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, server_default="true")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    contracts = relationship("HrEmploymentContract", back_populates="employment_type")


class HrPayScheme(Base):
    __tablename__ = "hr_pay_schemes"

    id = Column(Integer, primary_key=True)
    code = Column(String(32), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    unit = Column(String(32), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, server_default="true")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    payroll_profiles = relationship("HrPayrollProfile", back_populates="pay_scheme")
    wage_rates = relationship("HrWageRate", back_populates="pay_scheme")


class HrJobFamily(Base):
    __tablename__ = "hr_job_families"

    id = Column(Integer, primary_key=True)
    code = Column(String(32), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, server_default="true")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    assignments = relationship("HrEmployeeAssignment", back_populates="job_family")
    outputs = relationship("HrWorkOutput", back_populates="job_family")


class HrDepartment(Base):
    __tablename__ = "hr_departments"

    id = Column(Integer, primary_key=True)
    code = Column(String(32), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    parent_id = Column(Integer, ForeignKey("hr_departments.id", ondelete="SET NULL"), nullable=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, server_default="true")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    parent = relationship("HrDepartment", remote_side=[id])
    assignments = relationship("HrEmployeeAssignment", back_populates="department")


class HrPosition(Base):
    __tablename__ = "hr_positions"

    id = Column(Integer, primary_key=True)
    code = Column(String(32), unique=True, nullable=False)
    title = Column(String(120), nullable=False)
    level = Column(String(64), nullable=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, server_default="true")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    assignments = relationship("HrEmployeeAssignment", back_populates="position")


class HrWorkLocation(Base):
    __tablename__ = "hr_work_locations"

    id = Column(Integer, primary_key=True)
    code = Column(String(32), unique=True, nullable=False)
    name = Column(String(120), nullable=False)
    location_type = Column(String(32), nullable=False)
    parent_id = Column(Integer, ForeignKey("hr_work_locations.id", ondelete="SET NULL"), nullable=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, server_default="true")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    parent = relationship("HrWorkLocation", remote_side=[id])
    assignments = relationship("HrEmployeeAssignment", back_populates="work_location")


class HrEmployee(Base):
    __tablename__ = "hr_employees"
    __table_args__ = (
        UniqueConstraint("employee_no", name="uq_hr_employees_employee_no"),
        UniqueConstraint("linked_user_id", name="uq_hr_employees_linked_user_id"),
        CheckConstraint(
            "employment_status IN ('active', 'inactive', 'resigned', 'terminated', 'retired')",
            name="ck_hr_employees_employment_status",
        ),
        Index("ix_hr_employees_current_group_id", "current_group_id"),
        Index("ix_hr_employees_full_name", "full_name"),
    )

    id = Column(Integer, primary_key=True)
    employee_no = Column(String(32), nullable=False)
    full_name = Column(String(160), nullable=False)
    preferred_name = Column(String(100), nullable=True)
    linked_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    current_group_id = Column(Integer, ForeignKey("hr_employee_groups.id", ondelete="RESTRICT"), nullable=False)
    family_status = Column(String(8), nullable=True)
    employment_status = Column(String(24), nullable=False, server_default="active")
    join_date = Column(Date, nullable=True)
    exit_date = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    linked_user = relationship("User", foreign_keys=[linked_user_id])
    created_by_user = relationship("User", foreign_keys=[created_by_user_id])
    updated_by_user = relationship("User", foreign_keys=[updated_by_user_id])
    current_group = relationship("HrEmployeeGroup", back_populates="employees")
    identity = relationship("HrEmployeeIdentity", back_populates="employee", uselist=False, cascade="all, delete-orphan")
    addresses = relationship("HrEmployeeAddress", back_populates="employee", cascade="all, delete-orphan")
    family_members = relationship("HrEmployeeFamily", back_populates="employee", cascade="all, delete-orphan")
    group_histories = relationship("HrEmployeeGroupHistory", back_populates="employee", cascade="all, delete-orphan")
    contracts = relationship("HrEmploymentContract", back_populates="employee", cascade="all, delete-orphan")
    assignments = relationship(
        "HrEmployeeAssignment",
        back_populates="employee",
        cascade="all, delete-orphan",
        foreign_keys="HrEmployeeAssignment.employee_id",
    )
    movements = relationship("HrEmployeeMovement", back_populates="employee", cascade="all, delete-orphan")
    wage_rates = relationship("HrWageRate", back_populates="employee", cascade="all, delete-orphan")
    payroll_profiles = relationship("HrPayrollProfile", back_populates="employee", cascade="all, delete-orphan")
    bpjs_enrollments = relationship("HrBpjsEnrollment", back_populates="employee", cascade="all, delete-orphan")


class HrEmployeeIdentity(Base):
    __tablename__ = "hr_employee_identities"
    __table_args__ = (
        UniqueConstraint("employee_id", name="uq_hr_employee_identities_employee_id"),
        UniqueConstraint("nik", name="uq_hr_employee_identities_nik"),
    )

    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("hr_employees.id", ondelete="CASCADE"), nullable=False)
    nik = Column(String(32), nullable=True)
    kk_number = Column(String(32), nullable=True)
    birth_place = Column(String(100), nullable=True)
    birth_date = Column(Date, nullable=True)
    gender = Column(String(16), nullable=True)
    religion = Column(String(32), nullable=True)
    education_level = Column(String(64), nullable=True)
    marital_status = Column(String(32), nullable=True)
    tax_number = Column(String(32), nullable=True)
    phone = Column(String(32), nullable=True)
    email = Column(String(120), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    employee = relationship("HrEmployee", back_populates="identity")


class HrEmployeeAddress(Base):
    __tablename__ = "hr_employee_addresses"
    __table_args__ = (
        CheckConstraint("address_type IN ('ktp', 'domicile', 'emergency')", name="ck_hr_employee_addresses_type"),
        Index("ix_hr_employee_addresses_employee_id", "employee_id"),
    )

    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("hr_employees.id", ondelete="CASCADE"), nullable=False)
    address_type = Column(String(24), nullable=False)
    address_line = Column(Text, nullable=False)
    village = Column(String(100), nullable=True)
    district = Column(String(100), nullable=True)
    regency = Column(String(100), nullable=True)
    province = Column(String(100), nullable=True)
    postal_code = Column(String(16), nullable=True)
    is_primary = Column(Boolean, nullable=False, server_default="false")

    employee = relationship("HrEmployee", back_populates="addresses")


class HrEmployeeFamily(Base):
    __tablename__ = "hr_employee_families"
    __table_args__ = (Index("ix_hr_employee_families_employee_id", "employee_id"),)

    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("hr_employees.id", ondelete="CASCADE"), nullable=False)
    relationship_type = Column(String(32), nullable=False)
    full_name = Column(String(160), nullable=False)
    birth_date = Column(Date, nullable=True)
    gender = Column(String(16), nullable=True)
    occupation = Column(String(100), nullable=True)
    is_dependent = Column(Boolean, nullable=False, server_default="false")
    notes = Column(Text, nullable=True)

    employee = relationship("HrEmployee", back_populates="family_members")


class HrEmployeeGroupHistory(Base):
    __tablename__ = "hr_employee_group_histories"
    __table_args__ = (
        UniqueConstraint("employee_id", "effective_start", name="uq_hr_group_history_employee_start"),
        CheckConstraint("effective_end IS NULL OR effective_end >= effective_start", name="ck_hr_group_history_date_range"),
        Index("ix_hr_group_histories_employee_id", "employee_id"),
        Index("ix_hr_group_histories_group_id", "employee_group_id"),
    )

    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("hr_employees.id", ondelete="CASCADE"), nullable=False)
    employee_group_id = Column(Integer, ForeignKey("hr_employee_groups.id", ondelete="RESTRICT"), nullable=False)
    effective_start = Column(Date, nullable=False)
    effective_end = Column(Date, nullable=True)
    reason = Column(String(160), nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    employee = relationship("HrEmployee", back_populates="group_histories")
    employee_group = relationship("HrEmployeeGroup", back_populates="group_histories")
    created_by_user = relationship("User")


class HrEmploymentContract(Base):
    __tablename__ = "hr_employment_contracts"
    __table_args__ = (
        UniqueConstraint("employee_id", "contract_no", name="uq_hr_contracts_employee_contract_no"),
        CheckConstraint("end_date IS NULL OR end_date >= start_date", name="ck_hr_contracts_date_range"),
        Index("ix_hr_contracts_employee_id", "employee_id"),
        Index("ix_hr_contracts_type_id", "employment_type_id"),
    )

    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("hr_employees.id", ondelete="CASCADE"), nullable=False)
    employment_type_id = Column(Integer, ForeignKey("hr_employment_types.id", ondelete="RESTRICT"), nullable=False)
    contract_no = Column(String(64), nullable=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    probation_end_date = Column(Date, nullable=True)
    exit_reason = Column(String(160), nullable=True)
    document_ref = Column(String(255), nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    employee = relationship("HrEmployee", back_populates="contracts")
    employment_type = relationship("HrEmploymentType", back_populates="contracts")
    created_by_user = relationship("User")


class HrEmployeeAssignment(Base):
    __tablename__ = "hr_employee_assignments"
    __table_args__ = (
        CheckConstraint("effective_end IS NULL OR effective_end >= effective_start", name="ck_hr_assignments_date_range"),
        Index("ix_hr_assignments_employee_id", "employee_id"),
        Index("ix_hr_assignments_department_id", "department_id"),
        Index("ix_hr_assignments_work_location_id", "work_location_id"),
    )

    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("hr_employees.id", ondelete="CASCADE"), nullable=False)
    department_id = Column(Integer, ForeignKey("hr_departments.id", ondelete="RESTRICT"), nullable=False)
    position_id = Column(Integer, ForeignKey("hr_positions.id", ondelete="RESTRICT"), nullable=True)
    job_family_id = Column(Integer, ForeignKey("hr_job_families.id", ondelete="RESTRICT"), nullable=False)
    work_location_id = Column(Integer, ForeignKey("hr_work_locations.id", ondelete="RESTRICT"), nullable=True)
    supervisor_employee_id = Column(Integer, ForeignKey("hr_employees.id", ondelete="SET NULL"), nullable=True)
    effective_start = Column(Date, nullable=False)
    effective_end = Column(Date, nullable=True)
    is_primary = Column(Boolean, nullable=False, server_default="true")
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    employee = relationship("HrEmployee", back_populates="assignments", foreign_keys=[employee_id])
    supervisor_employee = relationship("HrEmployee", foreign_keys=[supervisor_employee_id])
    department = relationship("HrDepartment", back_populates="assignments")
    position = relationship("HrPosition", back_populates="assignments")
    job_family = relationship("HrJobFamily", back_populates="assignments")
    work_location = relationship("HrWorkLocation", back_populates="assignments")
    created_by_user = relationship("User")


class HrEmployeeMovement(Base):
    __tablename__ = "hr_employee_movements"
    __table_args__ = (
        CheckConstraint(
            "movement_type IN ('join', 'transfer', 'promotion', 'demotion', 'group_change', 'resignation', 'termination', 'retirement')",
            name="ck_hr_movements_type",
        ),
        Index("ix_hr_movements_employee_id", "employee_id"),
        Index("ix_hr_movements_effective_date", "effective_date"),
    )

    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("hr_employees.id", ondelete="CASCADE"), nullable=False)
    movement_type = Column(String(32), nullable=False)
    effective_date = Column(Date, nullable=False)
    from_assignment_id = Column(Integer, ForeignKey("hr_employee_assignments.id", ondelete="SET NULL"), nullable=True)
    to_assignment_id = Column(Integer, ForeignKey("hr_employee_assignments.id", ondelete="SET NULL"), nullable=True)
    reason = Column(Text, nullable=True)
    approved_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    employee = relationship("HrEmployee", back_populates="movements")
    from_assignment = relationship("HrEmployeeAssignment", foreign_keys=[from_assignment_id])
    to_assignment = relationship("HrEmployeeAssignment", foreign_keys=[to_assignment_id])
    approved_by_user = relationship("User", foreign_keys=[approved_by_user_id])
    created_by_user = relationship("User", foreign_keys=[created_by_user_id])


class HrWageRate(Base):
    __tablename__ = "hr_wage_rates"
    __table_args__ = (
        UniqueConstraint("employee_id", "pay_scheme_id", "effective_start", name="uq_hr_wage_rates_employee_scheme_start"),
        CheckConstraint("effective_end IS NULL OR effective_end >= effective_start", name="ck_hr_wage_rates_date_range"),
        CheckConstraint("base_amount >= 0", name="ck_hr_wage_rates_base_amount"),
        Index("ix_hr_wage_rates_employee_id", "employee_id"),
    )

    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("hr_employees.id", ondelete="CASCADE"), nullable=True)
    pay_scheme_id = Column(Integer, ForeignKey("hr_pay_schemes.id", ondelete="RESTRICT"), nullable=False)
    effective_start = Column(Date, nullable=False)
    effective_end = Column(Date, nullable=True)
    base_amount = Column(Numeric(14, 2), nullable=False)
    premium_amount = Column(Numeric(14, 2), nullable=False, server_default="0")
    currency = Column(String(3), nullable=False, server_default="IDR")
    notes = Column(Text, nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    employee = relationship("HrEmployee", back_populates="wage_rates")
    pay_scheme = relationship("HrPayScheme", back_populates="wage_rates")
    created_by_user = relationship("User")


class HrPayrollProfile(Base):
    __tablename__ = "hr_payroll_profiles"
    __table_args__ = (UniqueConstraint("employee_id", name="uq_hr_payroll_profiles_employee_id"),)

    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("hr_employees.id", ondelete="CASCADE"), nullable=False)
    pay_scheme_id = Column(Integer, ForeignKey("hr_pay_schemes.id", ondelete="RESTRICT"), nullable=False)
    bank_name = Column(String(100), nullable=True)
    bank_account_no = Column(String(64), nullable=True)
    bank_account_name = Column(String(160), nullable=True)
    tax_status = Column(String(16), nullable=True)
    is_bpjs_tk_active = Column(Boolean, nullable=False, server_default="false")
    is_bpjs_health_active = Column(Boolean, nullable=False, server_default="false")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    employee = relationship("HrEmployee", back_populates="payroll_profiles")
    pay_scheme = relationship("HrPayScheme", back_populates="payroll_profiles")


class HrAttendanceDaily(Base):
    __tablename__ = "hr_attendance_daily"
    __table_args__ = (
        UniqueConstraint("employee_id", "attendance_date", name="uq_hr_attendance_employee_date"),
        CheckConstraint(
            "status IN ('present', 'absent', 'leave', 'sick', 'permit', 'holiday', 'off')",
            name="ck_hr_attendance_status",
        ),
        CheckConstraint("work_hours >= 0", name="ck_hr_attendance_work_hours"),
        Index("ix_hr_attendance_date", "attendance_date"),
    )

    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("hr_employees.id", ondelete="CASCADE"), nullable=False)
    attendance_date = Column(Date, nullable=False)
    status = Column(String(24), nullable=False)
    work_hours = Column(Numeric(5, 2), nullable=False, server_default="0")
    check_in_at = Column(DateTime(timezone=True), nullable=True)
    check_out_at = Column(DateTime(timezone=True), nullable=True)
    source = Column(String(32), nullable=True)
    notes = Column(Text, nullable=True)
    approved_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    employee = relationship("HrEmployee")
    approved_by_user = relationship("User", foreign_keys=[approved_by_user_id])
    created_by_user = relationship("User", foreign_keys=[created_by_user_id])


class HrWorkOutput(Base):
    __tablename__ = "hr_work_outputs"
    __table_args__ = (
        CheckConstraint("quantity >= 0", name="ck_hr_work_outputs_quantity"),
        Index("ix_hr_work_outputs_work_date", "work_date"),
        Index("ix_hr_work_outputs_employee_id", "employee_id"),
        Index("ix_hr_work_outputs_work_group_code", "work_group_code"),
    )

    id = Column(Integer, primary_key=True)
    work_date = Column(Date, nullable=False)
    employee_id = Column(Integer, ForeignKey("hr_employees.id", ondelete="SET NULL"), nullable=True)
    work_group_code = Column(String(64), nullable=True)
    job_family_id = Column(Integer, ForeignKey("hr_job_families.id", ondelete="RESTRICT"), nullable=False)
    activity_name = Column(String(120), nullable=False)
    block_code = Column(String(64), nullable=True)
    quantity = Column(Numeric(14, 3), nullable=False)
    unit = Column(String(32), nullable=False)
    rate_amount = Column(Numeric(14, 2), nullable=True)
    total_amount = Column(Numeric(14, 2), nullable=True)
    notes = Column(Text, nullable=True)
    verified_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    employee = relationship("HrEmployee")
    job_family = relationship("HrJobFamily", back_populates="outputs")
    verified_by_user = relationship("User", foreign_keys=[verified_by_user_id])
    created_by_user = relationship("User", foreign_keys=[created_by_user_id])


class HrManpowerSnapshot(Base):
    __tablename__ = "hr_manpower_snapshots"
    __table_args__ = (UniqueConstraint("snapshot_date", "scope_code", name="uq_hr_manpower_snapshots_date_scope"),)

    id = Column(Integer, primary_key=True)
    snapshot_date = Column(Date, nullable=False)
    scope_code = Column(String(64), nullable=False)
    title = Column(String(160), nullable=False)
    notes = Column(Text, nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    created_by_user = relationship("User")
    lines = relationship("HrManpowerSnapshotLine", back_populates="snapshot", cascade="all, delete-orphan")


class HrManpowerSnapshotLine(Base):
    __tablename__ = "hr_manpower_snapshot_lines"
    __table_args__ = (
        UniqueConstraint(
            "snapshot_id",
            "employee_group_id",
            "job_family_id",
            "department_id",
            "work_location_id",
            name="uq_hr_manpower_snapshot_lines_dimension",
        ),
        CheckConstraint("headcount >= 0", name="ck_hr_manpower_snapshot_lines_headcount"),
    )

    id = Column(Integer, primary_key=True)
    snapshot_id = Column(Integer, ForeignKey("hr_manpower_snapshots.id", ondelete="CASCADE"), nullable=False)
    employee_group_id = Column(Integer, ForeignKey("hr_employee_groups.id", ondelete="RESTRICT"), nullable=False)
    job_family_id = Column(Integer, ForeignKey("hr_job_families.id", ondelete="RESTRICT"), nullable=True)
    department_id = Column(Integer, ForeignKey("hr_departments.id", ondelete="RESTRICT"), nullable=True)
    work_location_id = Column(Integer, ForeignKey("hr_work_locations.id", ondelete="RESTRICT"), nullable=True)
    headcount = Column(Integer, nullable=False, server_default="0")
    notes = Column(Text, nullable=True)

    snapshot = relationship("HrManpowerSnapshot", back_populates="lines")
    employee_group = relationship("HrEmployeeGroup")
    job_family = relationship("HrJobFamily")
    department = relationship("HrDepartment")
    work_location = relationship("HrWorkLocation")


class HrBpjsEnrollment(Base):
    __tablename__ = "hr_bpjs_enrollments"
    __table_args__ = (
        UniqueConstraint("employee_id", "bpjs_type", name="uq_hr_bpjs_employee_type"),
        CheckConstraint("bpjs_type IN ('health', 'employment')", name="ck_hr_bpjs_type"),
    )

    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("hr_employees.id", ondelete="CASCADE"), nullable=False)
    bpjs_type = Column(String(24), nullable=False)
    membership_no = Column(String(64), nullable=True)
    registered_date = Column(Date, nullable=True)
    effective_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    is_active = Column(Boolean, nullable=False, server_default="true")
    notes = Column(Text, nullable=True)

    employee = relationship("HrEmployee", back_populates="bpjs_enrollments")


def _resolve_database_url() -> tuple[str, str, str]:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if database_url:
        return database_url, "DATABASE_URL", ""

    db_user = os.getenv("DB_USER", "").strip()
    db_password = os.getenv("DB_PASSWORD", "")
    db_host = os.getenv("DB_HOST", "localhost").strip() or "localhost"
    db_port_raw = os.getenv("DB_PORT", "5432").strip() or "5432"
    db_name = os.getenv("DB_NAME", "GBR").strip() or "GBR"

    if db_user and db_password:
        if db_password in _PASSWORD_PLACEHOLDERS or db_password.upper().startswith("GANTI_DENGAN"):
            return "", "DB_*", "DB_PASSWORD masih placeholder. Ganti dengan password PostgreSQL Anda di file .env"

        try:
            db_port = int(db_port_raw)
        except ValueError as error:
            raise RuntimeError("DB_PORT harus berupa angka.") from error

        url_object = URL.create(
            "postgresql+psycopg2",
            username=db_user,
            password=db_password,
            host=db_host,
            port=db_port,
            database=db_name,
        )
        return url_object.render_as_string(hide_password=False), "DB_*", ""

    return "", "", ""


DATABASE_URL, DATABASE_CONFIG_SOURCE, DATABASE_CONFIG_ERROR = _resolve_database_url()


def _build_connect_args() -> dict[str, object]:
    connect_args: dict[str, object] = {
        "connect_timeout": int(os.getenv("DB_CONNECT_TIMEOUT", "10")),
        "application_name": os.getenv("DB_APP_NAME", "python-apps-12R"),
    }

    sslmode = os.getenv("DB_SSLMODE", "").strip()
    if sslmode:
        connect_args["sslmode"] = sslmode

    return connect_args


def _auto_migrate_enabled() -> bool:
    return os.getenv("DB_AUTO_MIGRATE", "0").strip().lower() in {"1", "true", "yes", "on"}


def _centralized_mode_enabled() -> bool:
    return os.getenv("DB_CENTRAL_MODE", "0").strip().lower() in {"1", "true", "yes", "on"}


def _centralized_ssl_required() -> bool:
    return os.getenv("DB_CENTRAL_REQUIRE_SSL", "1").strip().lower() in {"1", "true", "yes", "on"}


def _validate_centralized_database_target() -> None:
    if not _centralized_mode_enabled() or not DATABASE_URL:
        return

    try:
        parsed_url = make_url(DATABASE_URL)
    except Exception as error:
        raise RuntimeError("DATABASE_URL tidak valid untuk mode database terpusat.") from error

    host = (parsed_url.host or "").strip().lower()
    if not host:
        raise RuntimeError("DB_HOST wajib diisi saat DB_CENTRAL_MODE aktif.")

    if host in _LOCAL_HOST_ALIASES:
        raise RuntimeError(
            "DB_CENTRAL_MODE aktif, tetapi host masih lokal. "
            "Gunakan host server PostgreSQL terpusat (misal IP LAN/hostname server)."
        )

    if _auto_migrate_enabled():
        raise RuntimeError(
            "DB_CENTRAL_MODE aktif, tetapi DB_AUTO_MIGRATE masih aktif. "
            "Set DB_AUTO_MIGRATE=0 dan jalankan migrasi lewat user admin terpisah."
        )

    if _centralized_ssl_required():
        sslmode = str(_build_connect_args().get("sslmode", "")).strip().lower()
        if sslmode not in _SSLMODE_STRICT_VALUES:
            raise RuntimeError(
                "Mode terpusat membutuhkan koneksi TLS. "
                "Set DB_SSLMODE ke salah satu: require, verify-ca, verify-full."
            )

engine = None
if DATABASE_URL:  # pragma: no branch
    # For SQLite URLs the DB-API does not accept PostgreSQL connect args
    try:
        parsed = make_url(DATABASE_URL)
    except Exception:
        parsed = None

    if parsed is not None and parsed.drivername and parsed.drivername.startswith("sqlite"):
        # SQLite: avoid passing postgres-specific connect args
        sqlite_connect_args: dict[str, object] = {}
        # If using pysqlite and running in threaded app, allow same-thread checks to be relaxed
        sqlite_connect_args["check_same_thread"] = False

        engine = create_engine(
            DATABASE_URL,
            connect_args=sqlite_connect_args,
            future=True,
        )
    else:
        engine = create_engine(
            DATABASE_URL,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
            pool_timeout=30,
            pool_recycle=1800,
            pool_use_lifo=True,
            connect_args=_build_connect_args(),
            future=True,
        )

Session = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def _masked_database_url(url: str) -> str:
    try:
        return make_url(url).render_as_string(hide_password=True)
    except Exception:
        return "<DATABASE_URL tidak valid>"


def _run_user_table_migration() -> None:
    if engine is None:
        return

    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("users")}

    with engine.begin() as connection:
        if "full_name" not in existing_columns:  # pragma: no branch
            connection.execute(text("ALTER TABLE users ADD COLUMN full_name VARCHAR"))
        if "email" not in existing_columns:  # pragma: no branch
            connection.execute(text("ALTER TABLE users ADD COLUMN email VARCHAR"))
        if "phone" not in existing_columns:  # pragma: no branch
            connection.execute(text("ALTER TABLE users ADD COLUMN phone VARCHAR"))
        if "status" not in existing_columns:  # pragma: no branch
            connection.execute(text("ALTER TABLE users ADD COLUMN status VARCHAR DEFAULT 'aktif'"))
            connection.execute(text("ALTER TABLE users ALTER COLUMN status SET NOT NULL"))
        if "deleted_at" not in existing_columns:  # pragma: no branch
            connection.execute(text("ALTER TABLE users ADD COLUMN deleted_at TIMESTAMPTZ"))
        if "last_login" not in existing_columns:  # pragma: no branch
            connection.execute(text("ALTER TABLE users ADD COLUMN last_login TIMESTAMPTZ"))
        if "last_logout" not in existing_columns:  # pragma: no branch
            connection.execute(text("ALTER TABLE users ADD COLUMN last_logout TIMESTAMPTZ"))

        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS roles (
                    id SERIAL PRIMARY KEY,
                    role_name VARCHAR UNIQUE NOT NULL,
                    description VARCHAR
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS permissions (
                    id SERIAL PRIMARY KEY,
                    permission_name VARCHAR UNIQUE NOT NULL
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS user_passwords (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    password_hash VARCHAR NOT NULL,
                    password_salt VARCHAR NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS user_pins (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    pin_hash VARCHAR NOT NULL,
                    pin_salt VARCHAR NOT NULL,
                    failed_attempts INTEGER NOT NULL DEFAULT 0,
                    locked_until TIMESTAMPTZ,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS user_roles (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
                    UNIQUE (user_id, role_id)
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS role_permissions (
                    role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
                    permission_id INTEGER NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
                    PRIMARY KEY (role_id, permission_id)
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS login_attempts (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                    ip_address VARCHAR,
                    success BOOLEAN NOT NULL,
                    attempt_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    access_token VARCHAR NOT NULL,
                    refresh_token VARCHAR,
                    ip_address VARCHAR,
                    user_agent VARCHAR,
                    expired_at TIMESTAMPTZ NOT NULL
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                    action VARCHAR NOT NULL,
                    action_type VARCHAR,
                    description TEXT,
                    ip_address VARCHAR,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )

        if "nama" in existing_columns:  # pragma: no branch
            connection.execute(text("UPDATE users SET full_name = nama WHERE full_name IS NULL AND nama IS NOT NULL"))  # pragma: no cover
        if "password" in existing_columns:
            connection.execute(text("ALTER TABLE users ALTER COLUMN password DROP NOT NULL"))

        password_select_sql = None
        if "password" in existing_columns and "password_hash" in existing_columns and "password_salt" in existing_columns:
            password_select_sql = (
                "SELECT id, password FROM users "
                "WHERE password IS NOT NULL AND (password_hash IS NULL OR password_salt IS NULL)"
            )
        elif "password" in existing_columns:
            password_select_sql = "SELECT id, password FROM users WHERE password IS NOT NULL"

        rows = []
        if password_select_sql is not None:
            rows = connection.execute(text(password_select_sql)).mappings().all()

        for row in rows:
            password = row["password"]
            if not password:
                continue

            salt, password_hash = create_password_hash(str(password))
            if "password_hash" in existing_columns and "password_salt" in existing_columns:
                connection.execute(
                    text(
                        "UPDATE users "
                        "SET password_hash = :password_hash, password_salt = :password_salt, password = NULL "
                        "WHERE id = :user_id"
                    ),
                    {
                        "password_hash": password_hash,
                        "password_salt": salt,
                        "user_id": row["id"],
                    },
                )

            connection.execute(
                text(
                    """
                    INSERT INTO user_passwords (user_id, password_hash, password_salt, updated_at)
                    VALUES (:user_id, :password_hash, :password_salt, CURRENT_TIMESTAMP)
                    ON CONFLICT (user_id)
                    DO UPDATE SET
                        password_hash = EXCLUDED.password_hash,
                        password_salt = EXCLUDED.password_salt,
                        updated_at = EXCLUDED.updated_at
                    """
                ),
                {
                    "user_id": row["id"],
                    "password_hash": password_hash,
                    "password_salt": salt,
                },
            )

        if "password_hash" in existing_columns and "password_salt" in existing_columns:
            connection.execute(
                text(
                    """
                    INSERT INTO user_passwords (user_id, password_hash, password_salt, updated_at)
                    SELECT id, password_hash, password_salt, COALESCE(updated_at, CURRENT_TIMESTAMP)
                    FROM users
                    WHERE password_hash IS NOT NULL AND password_salt IS NOT NULL
                    ON CONFLICT (user_id)
                    DO UPDATE SET
                        password_hash = EXCLUDED.password_hash,
                        password_salt = EXCLUDED.password_salt,
                        updated_at = EXCLUDED.updated_at
                    """
                )
            )

        if "pin_hash" in existing_columns and "pin_salt" in existing_columns:
            connection.execute(
                text(
                    """
                    INSERT INTO user_pins (user_id, pin_hash, pin_salt, failed_attempts, locked_until, updated_at)
                    SELECT id, pin_hash, pin_salt, 0, NULL, COALESCE(updated_at, CURRENT_TIMESTAMP)
                    FROM users
                    WHERE pin_hash IS NOT NULL AND pin_salt IS NOT NULL
                    ON CONFLICT (user_id)
                    DO UPDATE SET
                        pin_hash = EXCLUDED.pin_hash,
                        pin_salt = EXCLUDED.pin_salt,
                        updated_at = EXCLUDED.updated_at
                    """
                )
            )

        if "role" in existing_columns:
            connection.execute(
                text(
                    """
                    INSERT INTO roles (role_name)
                    SELECT DISTINCT role
                    FROM users
                    WHERE role IS NOT NULL AND role <> ''
                    ON CONFLICT (role_name) DO NOTHING
                    """
                )
            )

            connection.execute(
                text(
                    """
                    INSERT INTO user_roles (user_id, role_id)
                    SELECT u.id, r.id
                    FROM users u
                    JOIN roles r ON r.role_name = u.role
                    WHERE u.role IS NOT NULL AND u.role <> ''
                    ON CONFLICT (user_id, role_id) DO NOTHING
                    """
                )
            )


def init_db() -> None:
    if DATABASE_CONFIG_ERROR:
        raise RuntimeError(DATABASE_CONFIG_ERROR)

    if not DATABASE_URL or engine is None:
        raise RuntimeError(
            "Konfigurasi PostgreSQL belum lengkap.\n"
            "Gunakan salah satu cara berikut:\n"
            "1) DATABASE_URL=postgresql+psycopg2://<user>:<password>@localhost:5432/GBR\n"
            "2) DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME\n"
            "Tips: jika password berisi karakter khusus (@, :, /), lebih aman pakai DB_*"
        )

    _validate_centralized_database_target()

    try:
        test_connection()
        if _auto_migrate_enabled():
            Base.metadata.create_all(bind=engine)
            _run_user_table_migration()
    except OperationalError as error:
        detail = str(error.orig) if getattr(error, "orig", None) else str(error)
        detail_lower = detail.lower()

        if "password authentication failed" in detail_lower:
            raise RuntimeError(
                "Koneksi PostgreSQL ditolak: username/password salah.\n"
                f"Sumber konfigurasi: {DATABASE_CONFIG_SOURCE}\n"
                f"DATABASE_URL aktif: {_masked_database_url(DATABASE_URL)}"
            ) from error

        raise RuntimeError(
            "Koneksi PostgreSQL gagal. Pastikan service PostgreSQL aktif dan parameter koneksi benar.\n"
            f"Sumber konfigurasi: {DATABASE_CONFIG_SOURCE}\n"
            f"DATABASE_URL aktif: {_masked_database_url(DATABASE_URL)}\n"
            f"Detail: {detail}"
        ) from error
    except ProgrammingError as error:
        detail = str(error.orig) if getattr(error, "orig", None) else str(error)
        raise RuntimeError(
            "Migrasi schema membutuhkan privilege owner/admin.\n"
            "Jalankan script migrasi admin, atau aktifkan DB_AUTO_MIGRATE hanya pada user owner schema.\n"
            f"Detail: {detail}"
        ) from error


def test_connection() -> bool:
    if not DATABASE_URL or engine is None:
        raise RuntimeError("Konfigurasi PostgreSQL belum lengkap.")

    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return True

if __name__ == "__main__":  # pragma: no cover
    test_connection()
    init_db()
    print("Koneksi PostgreSQL berhasil dan tabel siap digunakan.")
