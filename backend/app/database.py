"""SQLAlchemy engine, session factory and declarative base.

The engine is driven entirely by settings.sqlalchemy_database_uri, so the
same code runs on the local MySQL and on the hosted Postgres a deployment
hands over through DATABASE_URL.
"""

import logging
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

logger = logging.getLogger(__name__)

engine = create_engine(
    settings.sqlalchemy_database_uri,
    # Both databases drop connections that have sat idle, and a pooled
    # connection that died while parked is indistinguishable from a live one
    # until it is used. Checking on checkout costs a round trip and saves an
    # error the user would have seen.
    pool_pre_ping=True,
    pool_recycle=settings.DB_POOL_RECYCLE,
    # Deliberately small. A hosted Postgres on a free or entry tier allows far
    # fewer connections than a local MySQL, and every worker keeps its own
    # pool - so the ceiling is pool_size + max_overflow, multiplied by workers.
    # Exhausting the provider's limit takes the whole application down, where
    # a queue here only makes a request wait.
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
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
