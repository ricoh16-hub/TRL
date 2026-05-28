from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    app_name: str = "PT GBR Plantation HRIS & Manpower Control System"
    environment: str = "development"

    database_url: str | None = Field(default=None, validation_alias="DATABASE_URL")
    db_user: str | None = Field(default=None, validation_alias="DB_USER")
    db_password: SecretStr | None = Field(default=None, validation_alias="DB_PASSWORD")
    db_host: str = Field(default="localhost", validation_alias="DB_HOST")
    db_port: int = Field(default=5432, validation_alias="DB_PORT")
    db_name: str | None = Field(default=None, validation_alias="DB_NAME")

    jwt_secret_key: SecretStr = Field(
        default=SecretStr("change-this-secret-in-env"),
        validation_alias="JWT_SECRET_KEY",
    )
    jwt_algorithm: str = Field(default="HS256", validation_alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(
        default=60,
        validation_alias="ACCESS_TOKEN_EXPIRE_MINUTES",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def sqlalchemy_database_url(self) -> str:
        if self.database_url:
            return self.database_url

        missing = [
            name
            for name, value in {
                "DB_USER": self.db_user,
                "DB_PASSWORD": self.db_password,
                "DB_NAME": self.db_name,
            }.items()
            if value is None or value == ""
        ]
        if missing:
            missing_text = ", ".join(missing)
            raise ValueError(f"DATABASE_URL is required, or provide fallback values: {missing_text}")

        password = self.db_password.get_secret_value() if self.db_password else None
        return URL.create(
            drivername="postgresql+psycopg2",
            username=self.db_user,
            password=password,
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
        ).render_as_string(hide_password=False)

    @property
    def jwt_secret_value(self) -> str:
        return self.jwt_secret_key.get_secret_value()

    def validate_security(self) -> None:
        if self.environment.lower() in {"development", "local", "test"}:
            return

        if self.jwt_secret_value == "change-this-secret-in-env":
            raise ValueError("JWT_SECRET_KEY wajib diisi untuk environment non-development.")
        if len(self.jwt_secret_value.encode("utf-8")) < 32:
            raise ValueError("JWT_SECRET_KEY minimal 32 byte untuk environment non-development.")


@lru_cache
def get_settings() -> Settings:
    return Settings()
