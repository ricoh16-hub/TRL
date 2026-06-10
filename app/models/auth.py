from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.audit import AuditLog
    from app.models.employee import Employee


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    employee_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("employees.employee_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    username: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    pin_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    failed_login_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    is_locked: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_logout: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    employee: Mapped[Employee | None] = relationship("Employee", back_populates="users")
    user_roles: Mapped[list[UserRole]] = relationship(
        "UserRole",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    audit_logs: Mapped[list[AuditLog]] = relationship("AuditLog", back_populates="user")


class Role(Base):
    __tablename__ = "roles"

    role_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    role_name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    user_roles: Mapped[list[UserRole]] = relationship(
        "UserRole",
        back_populates="role",
        cascade="all, delete-orphan",
    )
    role_permissions: Mapped[list[RolePermission]] = relationship(
        "RolePermission",
        back_populates="role",
        cascade="all, delete-orphan",
    )


class Permission(Base):
    __tablename__ = "permissions"
    __table_args__ = (
        UniqueConstraint("module_name", "action_name", name="uq_permissions_module_action"),
    )

    permission_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    module_name: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    action_name: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    role_permissions: Mapped[list[RolePermission]] = relationship(
        "RolePermission",
        back_populates="permission",
        cascade="all, delete-orphan",
    )


class RolePermission(Base):
    __tablename__ = "role_permissions"
    __table_args__ = (
        UniqueConstraint("role_id", "permission_id", name="uq_role_permissions_role_permission"),
    )

    role_permission_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    role_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("roles.role_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    permission_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("permissions.permission_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    role: Mapped[Role] = relationship("Role", back_populates="role_permissions")
    permission: Mapped[Permission] = relationship(
        "Permission",
        back_populates="role_permissions",
    )


class UserRole(Base):
    __tablename__ = "user_roles"
    __table_args__ = (
        UniqueConstraint("user_id", "role_id", name="uq_user_roles_user_role"),
    )

    user_role_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("roles.role_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    user: Mapped[User] = relationship("User", back_populates="user_roles")
    role: Mapped[Role] = relationship("Role", back_populates="user_roles")


__all__ = [
    "Permission",
    "Role",
    "RolePermission",
    "User",
    "UserRole",
]
