"""SQLAlchemy engine, session factory and declarative base for MySQL."""

import logging
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

logger = logging.getLogger(__name__)

engine = create_engine(
    settings.sqlalchemy_database_uri,
    pool_pre_ping=True,      # transparently recycles connections MySQL has dropped
    pool_recycle=3600,       # MySQL closes idle connections after wait_timeout
    pool_size=10,
    max_overflow=20,
    echo=settings.DEBUG and settings.ENVIRONMENT == "development",
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    """Declarative base class shared by every ORM model."""


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a request-scoped database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_database_connection() -> tuple[bool, str | None]:
    """Ping the database. Returns (is_connected, error_message)."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True, None
    except Exception as exc:  # noqa: BLE001 - surfaced through the health endpoint
        logger.warning("Database health check failed: %s", exc)
        return False, str(exc)


def init_db() -> None:
    """Create any missing tables.

    Convenient for local development. Production schema changes should be
    handled by a migration tool (e.g. Alembic) once the schema stabilises.
    """
    from app import models  # noqa: F401  - registers models on the metadata

    Base.metadata.create_all(bind=engine)
