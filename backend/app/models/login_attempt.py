"""Failed sign-in attempts, counted somewhere that survives a restart.

The in-process limiter in app/utils/rate_limit.py slows a guesser down while
the process lives. That is most of the protection on a machine that stays up,
and almost none of it on a free hosting tier, where the service sleeps after
fifteen minutes of quiet and wakes as a fresh process with empty counters. A
guesser only has to wait.

So the count that matters is kept here, in a row.

Attempts are keyed on the identifier as typed, not on a resolved account. If
only real accounts were counted, a lockout would prove an account exists, and
the sign-in screen would become the account-enumeration oracle that the rest
of the authentication code takes care not to be. Counting the typed string
means a stranger learns nothing from being locked out.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class LoginAttempt(Base):
    """One row per identifier anybody has failed to sign in as."""

    __tablename__ = "login_attempts"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Lowercased and trimmed, so Admin@School.edu and admin@school.edu are the
    # same subject. Never joined to users: the identifier may match nothing.
    identifier: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )

    failed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    first_failed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    last_failed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Set when the threshold is reached. A row whose lock has expired is kept
    # rather than deleted, so a repeat offender is visible to an administrator.
    locked_until: Mapped[Optional[datetime]] = mapped_column(DateTime, index=True)

    # Lifetime totals, never reset by a successful sign-in, so the office can
    # see that an account has been attacked even after the holder got in.
    lockout_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_locked_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<LoginAttempt {self.identifier} failed={self.failed_count}>"
