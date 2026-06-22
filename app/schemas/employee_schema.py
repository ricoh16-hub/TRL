from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class SchemaBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class EmployeeIdentityCreate(BaseModel):
    identity_type: str = Field(..., min_length=1, max_length=40)
    identity_number: str = Field(..., min_length=1, max_length=80)
    issue_date: date | None = None
    expire_date: date | None = None
    is_primary: bool = False


class EmployeeCreate(BaseModel):
    employee_no: str = Field(..., min_length=1, max_length=64)
    full_name: str = Field(..., min_length=1, max_length=180)
    gender: str | None = Field(default=None, max_length=20)
    birth_place: str | None = Field(default=None, max_length=120)
    birth_date: date | None = None
    religion_id: int | None = None
    education_id: int | None = None
    marital_status_id: int | None = None
    blood_type: str | None = Field(default=None, max_length=5)
    mobile_phone: str | None = Field(default=None, max_length=40)
    email: str | None = Field(default=None, max_length=120)
    photo_path: str | None = Field(default=None, max_length=255)
    is_active: bool = True
    status_effective_date: date | None = None
    identities: list[EmployeeIdentityCreate] = Field(default_factory=list)


class EmployeeUpdate(BaseModel):
    employee_no: str | None = Field(default=None, min_length=1, max_length=64)
    full_name: str | None = Field(default=None, min_length=1, max_length=180)
    gender: str | None = Field(default=None, max_length=20)
    birth_place: str | None = Field(default=None, max_length=120)
    birth_date: date | None = None
    religion_id: int | None = None
    education_id: int | None = None
    marital_status_id: int | None = None
    blood_type: str | None = Field(default=None, max_length=5)
    mobile_phone: str | None = Field(default=None, max_length=40)
    email: str | None = Field(default=None, max_length=120)
    photo_path: str | None = Field(default=None, max_length=255)
    is_active: bool | None = None


class EmployeeStatusChangeRequest(BaseModel):
    employee_id: int | None = None
    employment_status_id: int
    effective_date: date
    notes: str | None = None
    approved_by: str | None = Field(default=None, max_length=120)


class EmployeeMutationRequest(BaseModel):
    employee_id: int | None = None
    movement_type_id: int
    movement_date: date
    from_estate_id: int | None = None
    from_division_id: int | None = None
    from_position_id: int | None = None
    to_estate_id: int | None = None
    to_division_id: int | None = None
    to_position_id: int | None = None
    notes: str | None = None
    approved_by: str | None = Field(default=None, max_length=120)


class EmployeeFamilyCreate(BaseModel):
    employee_id: int | None = None
    relation_id: int
    full_name: str = Field(..., min_length=1, max_length=180)
    gender: str | None = Field(default=None, max_length=20)
    birth_place: str | None = Field(default=None, max_length=120)
    birth_date: date | None = None
    education_level: str | None = Field(default=None, max_length=120)
    dependent_flag: bool = False
    notes: str | None = None


class EmployeeDocumentCreate(BaseModel):
    employee_id: int | None = None
    document_type_id: int
    file_name: str = Field(..., min_length=1, max_length=255)
    file_path: str = Field(..., min_length=1, max_length=500)
    uploaded_by: str | None = Field(default=None, max_length=120)
    notes: str | None = None


class EmployeeListResponse(SchemaBase):
    employee_id: int
    employee_no: str
    full_name: str
    current_division: str | None = None
    current_position: str | None = None
    category: str | None = None
    status: str | None = None
    bpjs_status: str | None = None
    data_completeness: float = Field(default=0, ge=0, le=100)


class EmployeeListPageResponse(SchemaBase):
    items: list[EmployeeListResponse] = Field(default_factory=list)
    page: int = Field(ge=1)
    limit: int = Field(ge=1)
    total: int = Field(ge=0)
    pages: int = Field(ge=0)


class EmployeeProfileResponse(SchemaBase):
    employee_id: int
    employee_no: str
    full_name: str
    gender: str | None = None
    birth_place: str | None = None
    birth_date: date | None = None
    religion: str | None = None
    education: str | None = None
    marital_status: str | None = None
    blood_type: str | None = None
    mobile_phone: str | None = None
    email: str | None = None
    photo_path: str | None = None
    is_active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None


class EmployeeIdentityResponse(SchemaBase):
    identity_id: int
    identity_type: str
    identity_number: str
    issue_date: date | None = None
    expire_date: date | None = None
    is_primary: bool


class EmployeeAddressResponse(SchemaBase):
    address_id: int
    address_type: str
    address_text: str
    province: str | None = None
    regency: str | None = None
    district: str | None = None
    village: str | None = None
    postal_code: str | None = None
    is_primary: bool


class EmployeeAssignmentResponse(SchemaBase):
    assignment_id: int
    estate_id: int
    estate_name: str | None = None
    division_id: int
    division_name: str | None = None
    position_id: int
    position_name: str | None = None
    category_id: int
    category_name: str | None = None
    start_date: date
    end_date: date | None = None
    is_current: bool
    notes: str | None = None


class EmployeeStatusResponse(SchemaBase):
    status_history_id: int
    employment_status_id: int
    status_name: str | None = None
    effective_date: date
    notes: str | None = None
    approved_by: str | None = None


class EmployeeContractResponse(SchemaBase):
    contract_id: int
    employment_type_id: int
    employment_type_name: str | None = None
    contract_no: str
    start_date: date
    end_date: date | None = None
    salary_type: str | None = None
    notes: str | None = None


class EmployeeFamilyResponse(SchemaBase):
    family_member_id: int
    relation_id: int
    relation_name: str | None = None
    full_name: str
    gender: str | None = None
    birth_place: str | None = None
    birth_date: date | None = None
    education_level: str | None = None
    dependent_flag: bool
    notes: str | None = None


class EmployeeBpjsResponse(SchemaBase):
    employee_bpjs_id: int
    bpjs_type_id: int
    bpjs_type_name: str | None = None
    bpjs_number: str
    active_status: bool
    registered_date: date | None = None
    notes: str | None = None


class EmployeeDocumentResponse(SchemaBase):
    document_id: int
    employee_id: int
    document_type_id: int
    document_type_name: str | None = None
    file_name: str
    file_path: str
    uploaded_by: str | None = None
    uploaded_at: datetime
    notes: str | None = None


class EmployeeMovementResponse(SchemaBase):
    movement_id: int
    movement_type_id: int
    movement_type_name: str | None = None
    from_estate_id: int | None = None
    from_division_id: int | None = None
    from_position_id: int | None = None
    to_estate_id: int | None = None
    to_division_id: int | None = None
    to_position_id: int | None = None
    movement_date: date
    notes: str | None = None
    approved_by: str | None = None
    created_at: datetime | None = None


class EmployeePayrollSummary(SchemaBase):
    pay_profile_id: int | None = None
    wage_rate_id: int | None = None
    pay_type: str | None = None
    amount: Decimal | None = None
    unit_name: str | None = None
    rice_kg: Decimal | None = None
    bank_name: str | None = None
    bank_account_no: str | None = None
    bank_account_name: str | None = None
    effective_date: date | None = None


class EmployeeAttendanceSummary(SchemaBase):
    period: str | None = None
    present_days: Decimal = Decimal("0")
    sick_days: Decimal = Decimal("0")
    permit_days: Decimal = Decimal("0")
    absent_days: Decimal = Decimal("0")
    leave_days: Decimal = Decimal("0")
    total_hk: Decimal = Decimal("0")


class EmployeeDetailResponse(SchemaBase):
    profile: EmployeeProfileResponse
    identities: list[EmployeeIdentityResponse] = Field(default_factory=list)
    addresses: list[EmployeeAddressResponse] = Field(default_factory=list)
    current_assignment: EmployeeAssignmentResponse | None = None
    current_status: EmployeeStatusResponse | None = None
    current_contract: EmployeeContractResponse | None = None
    family_members: list[EmployeeFamilyResponse] = Field(default_factory=list)
    bpjs: list[EmployeeBpjsResponse] = Field(default_factory=list)
    documents: list[EmployeeDocumentResponse] = Field(default_factory=list)
    movements: list[EmployeeMovementResponse] = Field(default_factory=list)
    payroll_summary: EmployeePayrollSummary | None = None
    attendance_summary: EmployeeAttendanceSummary | None = None


__all__ = [
    "EmployeeAddressResponse",
    "EmployeeAssignmentResponse",
    "EmployeeAttendanceSummary",
    "EmployeeBpjsResponse",
    "EmployeeContractResponse",
    "EmployeeCreate",
    "EmployeeDetailResponse",
    "EmployeeDocumentCreate",
    "EmployeeDocumentResponse",
    "EmployeeFamilyCreate",
    "EmployeeFamilyResponse",
    "EmployeeIdentityResponse",
    "EmployeeIdentityCreate",
    "EmployeeListPageResponse",
    "EmployeeListResponse",
    "EmployeeMovementResponse",
    "EmployeeMutationRequest",
    "EmployeePayrollSummary",
    "EmployeeProfileResponse",
    "EmployeeStatusChangeRequest",
    "EmployeeStatusResponse",
    "EmployeeUpdate",
]
