from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session
from sqlalchemy.orm import selectinload
try:
    from database.models import LoginAttempt, Role, User, UserPassword, UserPin, UserRole, UserSession
except ImportError:
    from src.database.models import LoginAttempt, Role, User, UserPassword, UserPin, UserRole, UserSession

CANONICAL_ROLES: tuple[str, ...] = (
    "Superior",
    "Administrator",
    "Operator",
    "Auditor",
)

ROLE_MAPPING: dict[str, str] = {
    "super admin": "Superior",
    "superadmin": "Superior",
    "superior": "Superior",
    "admin": "Administrator",
    "administrator": "Administrator",
    "manager": "Administrator",
    "staff": "Administrator",
    "operator": "Operator",
    "viewer": "Auditor",
    "auditor": "Auditor",
}

try:
    from auth.passwords import create_password_hash, create_pin_hash, verify_pin_code
except ImportError:
    from src.auth.passwords import create_password_hash, create_pin_hash, verify_pin_code

try:
    from app.core.security import hash_password as create_bcrypt_hash
except ImportError:
    create_bcrypt_hash = None  # type: ignore[assignment]


HRIS_AUTH_SCHEMA_COLUMNS = {"user_id", "username", "password_hash", "is_active", "is_locked"}


def _table_columns(session: Session, table_name: str) -> set[str]:
    try:
        return {str(column["name"]) for column in inspect(session.connection()).get_columns(table_name)}
    except Exception:
        return set()


def _table_exists(session: Session, table_name: str) -> bool:
    try:
        return bool(inspect(session.connection()).has_table(table_name))
    except Exception:
        return False


def _is_hris_auth_schema(session: Session) -> bool:
    return HRIS_AUTH_SCHEMA_COLUMNS.issubset(_table_columns(session, "users"))


def _hash_hris_secret(secret: str) -> str:
    if not secret:
        raise ValueError("Password tidak boleh kosong.")
    if create_bcrypt_hash is None:
        raise RuntimeError("Hasher bcrypt HRIS tidak tersedia.")
    return str(create_bcrypt_hash(secret))


def _desktop_role_to_hris_role(role_name: str) -> str:
    normalized_role = normalize_role_name(role_name)
    if normalized_role == "Superior":
        return "SUPER_ADMIN"
    if normalized_role == "Administrator":
        return "HR_ADMIN"
    return "HR_VIEWER"


def _hris_role_table_pk(session: Session) -> str:
    columns = _table_columns(session, "roles")
    return "role_id" if "role_id" in columns else "id"


def _get_or_create_hris_role_id(session: Session, role_name: str) -> int:
    hris_role = _desktop_role_to_hris_role(role_name)
    role_pk = _hris_role_table_pk(session)
    row = session.execute(
        text(f"SELECT {role_pk} AS role_id FROM roles WHERE role_name = :role_name"),
        {"role_name": hris_role},
    ).mappings().first()
    if row is not None:
        return int(row["role_id"])

    insert_columns = _table_columns(session, "roles")
    if "description" in insert_columns:
        row = session.execute(
            text(
                f"""
                INSERT INTO roles (role_name, description)
                VALUES (:role_name, :description)
                RETURNING {role_pk} AS role_id
                """
            ),
            {
                "role_name": hris_role,
                "description": f"Desktop mapped role for {normalize_role_name(role_name)}.",
            },
        ).mappings().one()
    else:
        row = session.execute(
            text(
                f"""
                INSERT INTO roles (role_name)
                VALUES (:role_name)
                RETURNING {role_pk} AS role_id
                """
            ),
            {"role_name": hris_role},
        ).mappings().one()
    return int(row["role_id"])


def _sync_hris_user_role(session: Session, user_id: int, role_name: str) -> None:
    role_id = _get_or_create_hris_role_id(session, role_name)
    session.execute(text("DELETE FROM user_roles WHERE user_id = :user_id"), {"user_id": user_id})
    session.execute(
        text(
            """
            INSERT INTO user_roles (user_id, role_id)
            VALUES (:user_id, :role_id)
            ON CONFLICT DO NOTHING
            """
        ),
        {"user_id": user_id, "role_id": role_id},
    )


def _ensure_hris_username_unique(
    session: Session,
    username: str,
    exclude_user_id: int | None = None,
) -> None:
    params: dict[str, object] = {"username": username}
    where_clause = "username = :username"
    if exclude_user_id is not None:
        where_clause += " AND user_id <> :exclude_user_id"
        params["exclude_user_id"] = exclude_user_id
    exists = session.execute(
        text(f"SELECT 1 FROM users WHERE {where_clause} LIMIT 1"),
        params,
    ).scalar()
    if exists is not None:
        raise ValueError("Username sudah digunakan.")


def _fetch_hris_user(session: Session, user_id: int) -> SimpleNamespace:
    row = session.execute(
        text(
            """
            SELECT user_id, username, full_name, status, is_active, is_locked, password_hash, pin_hash
            FROM users
            WHERE user_id = :user_id
            """
        ),
        {"user_id": user_id},
    ).mappings().first()
    if row is None:
        raise ValueError("User tidak ditemukan.")
    return SimpleNamespace(
        id=int(row["user_id"]),
        user_id=int(row["user_id"]),
        username=str(row.get("username") or ""),
        full_name=row.get("full_name"),
        nama=row.get("full_name"),
        status="aktif" if bool(row.get("is_active")) else "nonaktif",
        password_hash=row.get("password_hash"),
        pin_hash=row.get("pin_hash"),
    )


def _create_hris_user(
    session: Session,
    username: str,
    password: str,
    role: str,
    pin: str,
    nama: str,
    status: str,
) -> SimpleNamespace:
    normalized_status = _normalize_status(status)
    if not username:
        raise ValueError("Username tidak boleh kosong.")
    _ensure_hris_username_unique(session, username)
    normalized_pin = _validate_pin_format(pin) if pin.strip() else ""

    columns = _table_columns(session, "users")
    insert_columns = ["username", "password_hash", "failed_login_count", "is_locked", "is_active"]
    values = [":username", ":password_hash", "0", "false", ":is_active"]
    params: dict[str, object] = {
        "username": username,
        "password_hash": _hash_hris_secret(password),
        "is_active": normalized_status == "aktif",
    }
    if "pin_hash" in columns and normalized_pin:
        insert_columns.append("pin_hash")
        values.append(":pin_hash")
        params["pin_hash"] = _hash_hris_secret(normalized_pin)
    if "full_name" in columns:
        insert_columns.append("full_name")
        values.append(":full_name")
        params["full_name"] = nama or None
    if "status" in columns:
        insert_columns.append("status")
        values.append(":status")
        params["status"] = normalized_status

    row = session.execute(
        text(
            f"""
            INSERT INTO users ({", ".join(insert_columns)})
            VALUES ({", ".join(values)})
            RETURNING user_id
            """
        ),
        params,
    ).mappings().one()
    user_id = int(row["user_id"])
    _sync_hris_user_role(session, user_id, role)
    session.commit()
    return _fetch_hris_user(session, user_id)


def _update_hris_user(session: Session, user_id: int, **kwargs: Any) -> SimpleNamespace:
    _fetch_hris_user(session, user_id)
    assignments: list[str] = []
    params: dict[str, object] = {"user_id": user_id}

    for key, value in kwargs.items():
        if key == "password":
            if value:
                assignments.append("password_hash = :password_hash")
                params["password_hash"] = _hash_hris_secret(str(value))
            continue
        if key == "role" and isinstance(value, str):
            _sync_hris_user_role(session, user_id, value)
            continue
        if key == "username" and isinstance(value, str):
            username = value.strip()
            if not username:
                raise ValueError("Username tidak boleh kosong.")
            _ensure_hris_username_unique(session, username, exclude_user_id=user_id)
            assignments.append("username = :username")
            params["username"] = username
            continue
        if key in {"nama", "full_name"} and isinstance(value, str) and "full_name" in _table_columns(session, "users"):
            assignments.append("full_name = :full_name")
            params["full_name"] = value.strip() or None
            continue
        if key == "status" and isinstance(value, str):
            normalized_status = _normalize_status(value)
            assignments.append("is_active = :is_active")
            params["is_active"] = normalized_status == "aktif"
            if "status" in _table_columns(session, "users"):
                assignments.append("status = :status")
                params["status"] = normalized_status

    if "updated_at" in _table_columns(session, "users"):
        assignments.append("updated_at = CURRENT_TIMESTAMP")
    if assignments:
        session.execute(
            text(f"UPDATE users SET {', '.join(assignments)} WHERE user_id = :user_id"),
            params,
        )
    session.commit()
    return _fetch_hris_user(session, user_id)


def _delete_hris_user(session: Session, user_id: int) -> None:
    _fetch_hris_user(session, user_id)
    for table_name in ("user_sessions", "user_roles"):
        if _table_exists(session, table_name):
            session.execute(text(f"DELETE FROM {table_name} WHERE user_id = :user_id"), {"user_id": user_id})
    for table_name in ("login_attempts", "audit_logs"):
        if _table_exists(session, table_name) and "user_id" in _table_columns(session, table_name):
            session.execute(text(f"UPDATE {table_name} SET user_id = NULL WHERE user_id = :user_id"), {"user_id": user_id})
    if _table_exists(session, "hr_employees") and "linked_user_id" in _table_columns(session, "hr_employees"):
        session.execute(
            text("UPDATE hr_employees SET linked_user_id = NULL WHERE linked_user_id = :user_id"),
            {"user_id": user_id},
        )
    session.execute(text("DELETE FROM users WHERE user_id = :user_id"), {"user_id": user_id})
    session.commit()


def _set_hris_user_pin(session: Session, user_id: int, pin: str) -> SimpleNamespace:
    _fetch_hris_user(session, user_id)
    normalized_pin = _validate_pin_format(pin)
    session.execute(
        text(
            """
            UPDATE users
            SET pin_hash = :pin_hash, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = :user_id
            """
        ),
        {"pin_hash": _hash_hris_secret(normalized_pin), "user_id": user_id},
    )
    session.commit()
    return _fetch_hris_user(session, user_id)


def _validate_pin_format(pin: str) -> str:
    normalized_pin = pin.strip()
    if not normalized_pin.isdigit() or len(normalized_pin) != 6:
        raise ValueError('PIN harus tepat 6 digit angka.')
    return normalized_pin


def normalize_role_name(role_name: str) -> str:
    normalized_key = " ".join(role_name.strip().lower().split())
    mapped_role = ROLE_MAPPING.get(normalized_key)
    if mapped_role is None:
        supported = ", ".join(CANONICAL_ROLES)
        raise ValueError(f"Role tidak valid. Gunakan salah satu: {supported}.")
    return mapped_role


def _normalize_status(status: str) -> str:
    normalized_status = status.strip().lower()
    if normalized_status not in {"aktif", "nonaktif"}:
        raise ValueError("Status harus Aktif atau Nonaktif.")
    return normalized_status


def _ensure_pin_unique(session: Session, pin: str, exclude_user_id: int | None = None) -> None:
    users = session.query(User).all()
    pin_records = {
        record.user_id: record
        for record in session.query(UserPin).all()
        if getattr(record, 'user_id', None) is not None
    }

    for existing_user in users:
        if exclude_user_id is not None and existing_user.id == exclude_user_id:
            continue

        pin_hash = str(getattr(existing_user, 'pin_hash', '') or '')
        pin_salt = str(getattr(existing_user, 'pin_salt', '') or '')

        pin_record = pin_records.get(existing_user.id)
        if pin_record is not None:
            pin_hash = pin_record.pin_hash
            pin_salt = pin_record.pin_salt

        if pin_hash and pin_salt and verify_pin_code(pin, pin_salt, pin_hash):
            raise ValueError('PIN sudah dipakai user lain. Gunakan PIN berbeda.')


def _get_or_create_role(session: Session, role_name: str) -> Role:
    normalized_role_name = normalize_role_name(role_name)
    role = session.query(Role).filter_by(role_name=normalized_role_name).first()
    if role is None:
        role = Role(role_name=normalized_role_name)
        session.add(role)
        session.flush()
    return role


def _ensure_username_unique(
    session: Session,
    username: str,
    exclude_user_id: int | None = None,
) -> None:
    query = session.query(User).filter(User.username == username)
    if exclude_user_id is not None:
        query = query.filter(User.id != exclude_user_id)
    if query.first() is not None:
        raise ValueError("Username sudah digunakan.")


def _sync_user_role(session: Session, user: User, role_name: str) -> None:
    role = _get_or_create_role(session, role_name)
    for existing_link in list(user.role_links):
        session.delete(existing_link)
    session.flush()

    role_link = UserRole(user=user, role=role)
    session.add(role_link)
    user.role_links = [role_link]


def _upsert_password_record(session: Session, user: User, password_hash: str, password_salt: str) -> None:
    record = session.query(UserPassword).filter_by(user_id=user.id).first()
    if record is None:
        record = UserPassword(
            user_id=user.id,
            password_hash=password_hash,
            password_salt=password_salt,
            updated_at=datetime.now(timezone.utc),
        )
        session.add(record)
        return

    record.password_hash = password_hash
    record.password_salt = password_salt
    record.updated_at = datetime.now(timezone.utc)


def _upsert_pin_record(session: Session, user: User, pin_hash: str, pin_salt: str) -> None:
    record = session.query(UserPin).filter_by(user_id=user.id).first()
    if record is None:
        record = UserPin(
            user_id=user.id,
            pin_hash=pin_hash,
            pin_salt=pin_salt,
            failed_attempts=0,
            updated_at=datetime.now(timezone.utc),
        )
        session.add(record)
        return

    record.pin_hash = pin_hash
    record.pin_salt = pin_salt
    record.failed_attempts = 0
    record.updated_at = datetime.now(timezone.utc)


def create_user(
    session: Session,
    username: str,
    password: str,
    role: str = 'Operator',
    pin: str = '',
    nama: str = '',
    status: str = 'aktif',
) -> User:
    username = username.strip()
    nama = nama.strip()
    normalized_role = normalize_role_name(role)
    normalized_status = _normalize_status(status)
    if _is_hris_auth_schema(session):
        return _create_hris_user(session, username, password, normalized_role, pin, nama, normalized_status)  # type: ignore[return-value]
    if not username:
        raise ValueError('Username tidak boleh kosong.')
    _ensure_username_unique(session, username)

    salt, password_hash = create_password_hash(password)
    user = User(
        username=username,
        full_name=nama or None,
        status=normalized_status,
        updated_at=datetime.now(timezone.utc),
    )

    pin_payload: tuple[str, str] | None = None

    if pin.strip():
        normalized_pin = _validate_pin_format(pin)
        _ensure_pin_unique(session, normalized_pin)
        pin_salt, pin_hash = create_pin_hash(normalized_pin)
        pin_payload = (pin_hash, pin_salt)

    session.add(user)
    session.flush()

    _upsert_password_record(session, user, password_hash, salt)
    _sync_user_role(session, user, normalized_role)
    if pin_payload is not None:
        _upsert_pin_record(session, user, pin_payload[0], pin_payload[1])

    session.commit()
    return user

def read_users(session: Session) -> list[User]:
    if _is_hris_auth_schema(session):
        rows = session.execute(
            text(
                """
                SELECT user_id, username, full_name, email, phone, status,
                       is_active, password_hash, pin_hash, created_at, updated_at
                FROM users
                ORDER BY user_id ASC
                """
            )
        ).mappings().all()
        role_rows = session.execute(
            text(
                """
                SELECT ur.user_id, r.role_name
                FROM user_roles ur
                JOIN roles r ON r.role_id = ur.role_id
                ORDER BY ur.user_id, r.role_name
                """
            )
        ).mappings().all()
        role_names_by_user_id: dict[int, list[str]] = {}
        for role_row in role_rows:
            role_names_by_user_id.setdefault(int(role_row["user_id"]), []).append(str(role_row["role_name"]))

        users: list[User] = []
        for row in rows:
            role_names = role_names_by_user_id.get(int(row["user_id"]), [])
            role_name = role_names[0] if role_names else "HR_VIEWER"
            user = SimpleNamespace(
                id=int(row["user_id"]),
                user_id=int(row["user_id"]),
                username=str(row.get("username") or ""),
                full_name=row.get("full_name"),
                nama=row.get("full_name"),
                email=row.get("email"),
                phone=row.get("phone"),
                status="aktif" if bool(row.get("is_active")) else "nonaktif",
                role=role_name,
                created_at=row.get("created_at"),
                updated_at=row.get("updated_at"),
                password_record=SimpleNamespace(password_hash=row.get("password_hash")),
                pin_record=SimpleNamespace(pin_hash=row.get("pin_hash")),
            )
            users.append(user)  # type: ignore[arg-type]
        return users
    return (
        session.query(User)
        .options(
            selectinload(User.role_links).selectinload(UserRole.role),
            selectinload(User.password_record),
            selectinload(User.pin_record),
        )
        .all()
    )

def update_user(session: Session, user_id: int, **kwargs: Any) -> User:
    if _is_hris_auth_schema(session):
        return _update_hris_user(session, user_id, **kwargs)  # type: ignore[return-value]

    user = session.get(User, user_id)
    if user is None:
        raise ValueError('User tidak ditemukan.')

    for key, value in kwargs.items():
        if key == 'password':
            if value:
                salt, password_hash = create_password_hash(value)
                _upsert_password_record(session, user, password_hash, salt)
            continue

        if key == 'username' and isinstance(value, str):
            value = value.strip()
            if not value:
                raise ValueError('Username tidak boleh kosong.')
            _ensure_username_unique(session, value, exclude_user_id=user_id)

        if key == 'role' and isinstance(value, str):
            normalized_role = normalize_role_name(value)
            _sync_user_role(session, user, normalized_role)
            continue

        if key == 'nama' and isinstance(value, str):
            value = value.strip() or None
            user.full_name = value
            continue

        if key == 'full_name' and isinstance(value, str):
            user.full_name = value.strip() or None
            continue

        if key == 'status' and isinstance(value, str):
            value = _normalize_status(value)

        setattr(user, key, value)
    user.updated_at = datetime.now(timezone.utc)
    session.commit()
    return user

def delete_user(session: Session, user_id: int) -> None:
    if _is_hris_auth_schema(session):
        _delete_hris_user(session, user_id)
        return

    user = session.get(User, user_id)
    if user is None:
        raise ValueError('User tidak ditemukan.')
    session.query(UserSession).filter_by(user_id=user_id).delete(synchronize_session=False)
    session.query(LoginAttempt).filter_by(user_id=user_id).update(
        {"user_id": None},
        synchronize_session=False,
    )
    session.delete(user)
    session.commit()


def set_user_pin(session: Session, user_id: int, pin: str) -> User:
    if _is_hris_auth_schema(session):
        return _set_hris_user_pin(session, user_id, pin)  # type: ignore[return-value]

    user = session.get(User, user_id)
    if user is None:
        raise ValueError('User tidak ditemukan.')

    normalized_pin = _validate_pin_format(pin)
    _ensure_pin_unique(session, normalized_pin, exclude_user_id=user_id)
    pin_salt, pin_hash = create_pin_hash(normalized_pin)
    _upsert_pin_record(session, user, pin_hash, pin_salt)
    user.updated_at = datetime.now(timezone.utc)
    session.commit()
    return user
