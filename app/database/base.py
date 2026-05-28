from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""


# Import all ORM models here so Alembic autogenerate can discover every table
# through Base.metadata after importing this module.
import app.models  # noqa: E402,F401
