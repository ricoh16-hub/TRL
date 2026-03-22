import os
from pathlib import Path
from sqlalchemy import Column, DateTime, Integer, String, create_engine, func, inspect, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import declarative_base, sessionmaker
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
    password = Column(String, nullable=True)
    password_hash = Column(String, nullable=True)
    password_salt = Column(String, nullable=True)
    role = Column(String, default='user')
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


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
if DATABASE_URL:
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
        if "password_hash" not in existing_columns:
            connection.execute(text("ALTER TABLE users ADD COLUMN password_hash VARCHAR"))
        if "password_salt" not in existing_columns:
            connection.execute(text("ALTER TABLE users ADD COLUMN password_salt VARCHAR"))
        if "password" in existing_columns:
            connection.execute(text("ALTER TABLE users ALTER COLUMN password DROP NOT NULL"))

        rows = connection.execute(
            text(
                "SELECT id, password FROM users "
                "WHERE password IS NOT NULL AND (password_hash IS NULL OR password_salt IS NULL)"
            )
        ).mappings().all()

        for row in rows:
            password = row["password"]
            if not password:
                continue

            salt, password_hash = create_password_hash(str(password))
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

if __name__ == "__main__":
    test_connection()
    init_db()
    print("Koneksi PostgreSQL berhasil dan tabel siap digunakan.")