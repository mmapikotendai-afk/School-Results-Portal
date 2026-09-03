"""Reusable model mixins."""

from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column


class CreatedAtMixin:
    """Adds a database-managed creation timestamp."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


class TimestampMixin:
    """Adds database-managed created and updated timestamps.

    updated_at is maintained by SQLAlchemy on flush rather than by a native
    ON UPDATE CURRENT_TIMESTAMP clause, so it stays correct for every write
    that goes through the ORM.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
