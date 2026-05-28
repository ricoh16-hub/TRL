from __future__ import annotations

from argparse import ArgumentParser
from collections.abc import Sequence
from decimal import Decimal
from secrets import token_urlsafe
from typing import Any, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.auth import Permission, Role, RolePermission, User, UserRole
from app.models.movement import DEFAULT_MOVEMENT_TYPES
from app.models.reference import (
    AttendanceCode,
    BpjsType,
    DocumentType,
    EducationLevel,
    EmployeeCategory,
    EmploymentStatus,
    EmploymentType,
    JobFamily,
    MaritalStatus,
    MovementType,
    PayType,
    Religion,
)

ModelT = TypeVar("ModelT")

SeedRow = dict[str, Any]
SeedStats = dict[str, tuple[int, int]]

EMPLOYEE_PERMISSIONS: tuple[tuple[str, str, str], ...] = (
    ("employee", "view", "Melihat daftar dan detail karyawan."),
    ("employee", "create", "Membuat data karyawan."),
    ("employee", "update", "Mengubah data karyawan, mutasi, keluarga, dan dokumen."),
    ("employee", "change_status", "Mengubah status kerja karyawan."),
    ("employee", "delete", "Menonaktifkan karyawan melalui soft delete."),
    ("employee", "export", "Ekspor data karyawan."),
    ("data_quality", "update", "Mengubah workflow issue kualitas data HRIS."),
    ("data_quality", "export", "Ekspor issue kualitas data HRIS."),
    ("attendance", "view", "Melihat absensi, HK, dan ringkasan kehadiran."),
    ("attendance", "manage", "Membuat dan mengoreksi absensi karyawan."),
    ("work_output", "view", "Melihat output kerja dan produktivitas manpower."),
    ("work_output", "manage", "Membuat dan mengoreksi output kerja."),
)

SUPER_ADMIN_PERMISSION_KEYS = tuple(
    f"{module}:{action}" for module, action, _description in EMPLOYEE_PERMISSIONS
)
HR_ADMIN_PERMISSION_KEYS = tuple(
    key
    for key in SUPER_ADMIN_PERMISSION_KEYS
    if key not in {"employee:delete"}
)
HR_VIEWER_PERMISSION_KEYS = tuple(
    key
    for key in SUPER_ADMIN_PERMISSION_KEYS
    if key.endswith(":view") or key == "employee:export"
)

ROLE_DEFINITIONS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "SUPER_ADMIN",
        "Akses penuh untuk setup awal dan administrasi sistem.",
        SUPER_ADMIN_PERMISSION_KEYS,
    ),
    (
        "HR_ADMIN",
        "Akses operasional HR untuk mengelola data karyawan.",
        HR_ADMIN_PERMISSION_KEYS,
    ),
    (
        "HR_VIEWER",
        "Akses baca untuk audit dan monitoring HR.",
        HR_VIEWER_PERMISSION_KEYS,
    ),
)


def reference_row(
    code: str,
    name: str,
    description: str | None = None,
    **extra: Any,
) -> SeedRow:
    return {
        "code": code,
        "name": name,
        "description": description,
        "is_active": True,
        **extra,
    }


def upsert_rows(
    session: Session,
    model: type[ModelT],
    lookup_field: str,
    rows: Sequence[SeedRow],
) -> tuple[int, int]:
    created = 0
    updated = 0
    lookup_column = getattr(model, lookup_field)

    for row in rows:
        lookup_value = row[lookup_field]
        instance = session.scalar(select(model).where(lookup_column == lookup_value))
        if instance is None:
            session.add(model(**row))  # type: ignore[call-arg]
            created += 1
            continue

        for field_name, value in row.items():
            setattr(instance, field_name, value)
        updated += 1

    return created, updated


def seed_master_data(session: Session) -> SeedStats:
    stats: SeedStats = {}

    stats["religions"] = upsert_rows(
        session,
        Religion,
        "code",
        [
            reference_row("ISLAM", "Islam"),
            reference_row("KRISTEN", "Kristen"),
            reference_row("KATOLIK", "Katolik"),
            reference_row("HINDU", "Hindu"),
            reference_row("BUDDHA", "Buddha"),
            reference_row("KONGHUCU", "Konghucu"),
        ],
    )
    stats["education_levels"] = upsert_rows(
        session,
        EducationLevel,
        "code",
        [
            reference_row("SD", "SD"),
            reference_row("SMP", "SMP"),
            reference_row("SMA", "SMA"),
            reference_row("SMK", "SMK"),
            reference_row("D3", "D3"),
            reference_row("S1", "S1"),
            reference_row("S2", "S2"),
        ],
    )
    stats["marital_statuses"] = upsert_rows(
        session,
        MaritalStatus,
        "code",
        [
            reference_row("TK", "Tidak Kawin", dependent_count=0),
            reference_row("K0", "Kawin 0 Tanggungan", dependent_count=0),
            reference_row("K1", "Kawin 1 Tanggungan", dependent_count=1),
            reference_row("K2", "Kawin 2 Tanggungan", dependent_count=2),
            reference_row("K3", "Kawin 3 Tanggungan", dependent_count=3),
        ],
    )
    stats["employee_categories"] = upsert_rows(
        session,
        EmployeeCategory,
        "code",
        [
            reference_row("STF", "Staff"),
            reference_row("BLN", "Bulanan"),
            reference_row("SKU", "PHT/SKU"),
            reference_row("PHL", "PHL/KHL/BHL"),
            reference_row("BRG", "Borongan"),
        ],
    )
    stats["employment_statuses"] = upsert_rows(
        session,
        EmploymentStatus,
        "code",
        [
            reference_row("AKTIF", "Aktif"),
            reference_row("CUTI", "Cuti"),
            reference_row("KELUAR", "Keluar"),
            reference_row("NONAKTIF", "Nonaktif"),
            reference_row("MENINGGAL", "Meninggal"),
            reference_row("MANGKIR", "Mangkir"),
        ],
    )
    stats["employment_types"] = upsert_rows(
        session,
        EmploymentType,
        "code",
        [
            reference_row("PKWTT", "PKWTT"),
            reference_row("PKWT", "PKWT"),
            reference_row("KHL", "KHL"),
            reference_row("PROBATION", "Probation"),
            reference_row("BORONGAN", "Borongan"),
        ],
    )
    stats["pay_types"] = upsert_rows(
        session,
        PayType,
        "code",
        [
            reference_row("BULANAN", "Bulanan"),
            reference_row("HK", "HK"),
            reference_row("BORONGAN", "Borongan"),
            reference_row("PREMI", "Premi"),
        ],
    )
    stats["job_families"] = upsert_rows(
        session,
        JobFamily,
        "code",
        [
            reference_row("PANEN", "Panen"),
            reference_row("RAWAT", "Rawat"),
            reference_row("PUPUK", "Pupuk"),
            reference_row("TRAKSI", "Traksi"),
            reference_row("BENGKEL", "Bengkel"),
            reference_row("ADMIN", "Admin"),
            reference_row("SECURITY", "Security"),
            reference_row("SIPIL", "Sipil"),
        ],
    )
    stats["document_types"] = upsert_rows(
        session,
        DocumentType,
        "document_type_name",
        [
            {"document_type_name": "KTP", "description": "Kartu Tanda Penduduk"},
            {"document_type_name": "KK", "description": "Kartu Keluarga"},
            {"document_type_name": "NPWP", "description": "Nomor Pokok Wajib Pajak"},
            {"document_type_name": "BPJS_KESEHATAN", "description": "Dokumen BPJS Kesehatan"},
            {
                "document_type_name": "BPJS_KETENAGAKERJAAN",
                "description": "Dokumen BPJS Ketenagakerjaan",
            },
            {"document_type_name": "KONTRAK", "description": "Dokumen kontrak kerja"},
            {"document_type_name": "SK", "description": "Surat keputusan"},
            {"document_type_name": "FOTO", "description": "Foto karyawan"},
        ],
    )
    stats["bpjs_types"] = upsert_rows(
        session,
        BpjsType,
        "bpjs_type_name",
        [
            {"bpjs_type_name": "BPJS KESEHATAN", "description": "BPJS Kesehatan"},
            {
                "bpjs_type_name": "BPJS KETENAGAKERJAAN",
                "description": "BPJS Ketenagakerjaan",
            },
        ],
    )
    stats["attendance_codes"] = upsert_rows(
        session,
        AttendanceCode,
        "code",
        [
            reference_row("H", "Hadir", hk_value=Decimal("1.00")),
            reference_row("S", "Sakit", hk_value=Decimal("0.00")),
            reference_row("I", "Izin", hk_value=Decimal("0.00")),
            reference_row("A", "Alpa", hk_value=Decimal("0.00")),
            reference_row("CT", "Cuti", hk_value=Decimal("0.00")),
        ],
    )
    stats["movement_types"] = upsert_rows(
        session,
        MovementType,
        "code",
        [reference_row(code, name) for code, name in DEFAULT_MOVEMENT_TYPES],
    )

    return stats


def seed_auth_data(
    session: Session,
    *,
    admin_username: str = "admin",
    admin_password: str | None = None,
    reset_admin_password: bool = False,
) -> tuple[SeedStats, str | None]:
    stats: SeedStats = {}
    created_permissions = 0
    updated_permissions = 0
    permission_by_key: dict[str, Permission] = {}

    for module_name, action_name, description in EMPLOYEE_PERMISSIONS:
        permission = session.scalar(
            select(Permission).where(
                Permission.module_name == module_name,
                Permission.action_name == action_name,
            ),
        )
        if permission is None:
            permission = Permission(
                module_name=module_name,
                action_name=action_name,
                description=description,
            )
            session.add(permission)
            created_permissions += 1
        else:
            permission.description = description
            updated_permissions += 1

        permission_by_key[f"{module_name}:{action_name}"] = permission

    stats["permissions"] = (created_permissions, updated_permissions)

    created_roles = 0
    updated_roles = 0
    role_by_name: dict[str, Role] = {}
    for role_name, description, _ in ROLE_DEFINITIONS:
        role = session.scalar(select(Role).where(Role.role_name == role_name))
        if role is None:
            role = Role(role_name=role_name, description=description)
            session.add(role)
            created_roles += 1
        else:
            role.description = description
            updated_roles += 1
        role_by_name[role_name] = role

    session.flush()
    stats["roles"] = (created_roles, updated_roles)

    created_role_permissions = 0
    updated_role_permissions = 0
    for role_name, _, permission_keys in ROLE_DEFINITIONS:
        role = role_by_name[role_name]
        for permission_key in permission_keys:
            permission = permission_by_key[permission_key]
            existing = session.scalar(
                select(RolePermission).where(
                    RolePermission.role_id == role.role_id,
                    RolePermission.permission_id == permission.permission_id,
                ),
            )
            if existing is None:
                session.add(
                    RolePermission(
                        role_id=role.role_id,
                        permission_id=permission.permission_id,
                    ),
                )
                created_role_permissions += 1
            else:
                updated_role_permissions += 1

    stats["role_permissions"] = (created_role_permissions, updated_role_permissions)

    generated_password: str | None = None
    admin = session.scalar(select(User).where(User.username == admin_username))
    if admin_password is None:
        generated_password = token_urlsafe(18)
        admin_password = generated_password

    if admin is None:
        admin = User(
            username=admin_username,
            password_hash=hash_password(admin_password),
            failed_login_count=0,
            is_locked=False,
            is_active=True,
        )
        session.add(admin)
        stats["users"] = (1, 0)
    else:
        if reset_admin_password:
            admin.password_hash = hash_password(admin_password)
        admin.is_active = True
        admin.is_locked = False
        admin.failed_login_count = 0
        stats["users"] = (0, 1)
        if not reset_admin_password:
            generated_password = None

    session.flush()

    super_admin = role_by_name["SUPER_ADMIN"]
    existing_user_role = session.scalar(
        select(UserRole).where(
            UserRole.user_id == admin.user_id,
            UserRole.role_id == super_admin.role_id,
        ),
    )
    if existing_user_role is None:
        session.add(UserRole(user_id=admin.user_id, role_id=super_admin.role_id))
        stats["user_roles"] = (1, 0)
    else:
        stats["user_roles"] = (0, 1)

    return stats, generated_password


def print_stats(stats: SeedStats) -> None:
    for table_name, (created, updated) in stats.items():
        print(f"{table_name}: created={created}, updated={updated}")


def main() -> None:
    from app.database.connection import SessionLocal

    parser = ArgumentParser(description="Seed master data for PT GBR HRIS.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run seed logic and rollback instead of committing changes.",
    )
    parser.add_argument(
        "--with-auth",
        action="store_true",
        help="Seed employee permissions, HR roles, and an initial admin user.",
    )
    parser.add_argument(
        "--admin-username",
        default="admin",
        help="Initial admin username when --with-auth is used.",
    )
    parser.add_argument(
        "--admin-password",
        default=None,
        help="Initial admin password. If omitted, a secure temporary password is generated.",
    )
    parser.add_argument(
        "--reset-admin-password",
        action="store_true",
        help="Reset existing admin password to --admin-password or a generated temporary password.",
    )
    args = parser.parse_args()

    with SessionLocal() as session:
        try:
            stats = seed_master_data(session)
            generated_admin_password: str | None = None
            if args.with_auth:
                auth_stats, generated_admin_password = seed_auth_data(
                    session,
                    admin_username=args.admin_username,
                    admin_password=args.admin_password,
                    reset_admin_password=args.reset_admin_password,
                )
                stats.update(auth_stats)
            if args.dry_run:
                session.rollback()
                print("Dry run completed. No changes committed.")
            else:
                session.commit()
                print("Seed completed.")
            print_stats(stats)
            if generated_admin_password:
                print(f"temporary_admin_username={args.admin_username}")
                print(f"temporary_admin_password={generated_admin_password}")
        except Exception:
            session.rollback()
            raise


if __name__ == "__main__":
    main()
