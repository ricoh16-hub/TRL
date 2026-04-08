import os
from pathlib import Path
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, create_engine, func, inspect, text
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
    password_plaintext = Column(String, nullable=True)  # Temporary plaintext storage (for display only)
    pin_plaintext = Column(String, nullable=True)  # Temporary plaintext storage (for display only)
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