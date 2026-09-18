"""Sign-in lockout, counted in the database rather than in memory.

Why this exists alongside the in-process limiter: that one lives in the
memory of a single worker, and the deployment target sleeps after fifteen
minutes without traffic. Every sleep, deploy or restart hands the guesser a
fresh set of counters. A row does not forget.

Two rules shape the design.

Attempts are keyed on the identifier exactly as typed, lowercased. Not on a
resolved account - if only real accounts were counted, being locked out would
prove an account exists, and the sign-in screen would give away the very thing
the rest of the authentication code is careful never to reveal.

A lock refuses the attempt before the password is examined. Checking the
password first and then refusing would leak, through response time, whether
the guess was right.
"""

from datetime import datetime, timedelta
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from app.config import settings
from app.models.login_attempt import LoginAttempt


def _utcnow() -> datetime:
    """Naive UTC, matching how every other timestamp here is stored."""
    return datetime.utcnow()


def normalise(identifier: str) -> str:
    return (identifier or "").strip().lower()[:255]


class LockoutService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _row(self, identifier: str) -> Optional[LoginAttempt]:
        return (
            self.db.query(LoginAttempt)
            .filter(LoginAttempt.identifier == normalise(identifier))
            .first()
        )

    # ------------------------------------------------------------- reading

    def status(self, identifier: str) -> Tuple[bool, int]:
        """Return (locked, seconds_remaining) for this identifier."""
        row = self._row(identifier)
        if row is None or row.locked_until is None:
            return False, 0

        remaining = (row.locked_until - _utcnow()).total_seconds()
        if remaining <= 0:
            return False, 0
        return True, int(remaining) + 1

    def remaining_attempts(self, identifier: str) -> int:
        """How many failures are left before this identifier locks."""
        row = self._row(identifier)
        if row is None:
            return settings.LOGIN_MAX_FAILURES
        return max(0, settings.LOGIN_MAX_FAILURES - self._live_count(row))

    def _live_count(self, row: LoginAttempt) -> int:
        """Failures still inside the counting window.

        A failure older than the window is not held against anybody: somebody
        who mistypes once a month should never accumulate a lockout.
        """
        if row.last_failed_at is None:
            return 0
        window = timedelta(minutes=settings.LOGIN_FAILURE_WINDOW_MINUTES)
        if _utcnow() - row.last_failed_at > window:
            return 0
        return row.failed_count

    # ------------------------------------------------------------- writing

    def record_failure(self, identifier: str) -> Tuple[bool, int]:
        """Count one failed attempt. Returns (locked_now, seconds_remaining).

        Committed immediately. A failure that is only counted if the rest of
        the request succeeds is a failure a guesser can avoid paying for.
        """
        key = normalise(identifier)
        if not key:
            return False, 0

        now = _utcnow()
        row = self._row(key)
        if row is None:
            row = LoginAttempt(identifier=key, failed_count=0, first_failed_at=now)
            self.db.add(row)

        # An expired window starts the count again rather than adding to it.
        if row.last_failed_at is not None:
            window = timedelta(minutes=settings.LOGIN_FAILURE_WINDOW_MINUTES)
            if now - row.last_failed_at > window:
                row.failed_count = 0
                row.first_failed_at = now

        row.failed_count += 1
        row.last_failed_at = now

        locked_now = False
        if row.failed_count >= settings.LOGIN_MAX_FAILURES:
            row.locked_until = now + timedelta(minutes=settings.LOCKOUT_MINUTES)
            row.lockout_count += 1
            row.last_locked_at = now
            locked_now = True

        self.db.commit()

        if locked_now:
            return True, settings.LOCKOUT_MINUTES * 60
        return False, 0

    def clear(self, identifier: str) -> None:
        """Forget the failures for an identifier, after a correct password.

        The lifetime lockout_count is deliberately left alone, so an
        administrator can still see that an account was attacked even though
        its holder has since signed in successfully.
        """
        row = self._row(identifier)
        if row is None:
            return
        row.failed_count = 0
        row.first_failed_at = None
        row.last_failed_at = None
        row.locked_until = None
        self.db.commit()

    def unlock(self, identifier: str) -> bool:
        """Release a lock by hand, for an administrator helping a colleague.

        Both counters have to be released, not just this one. The in-process
        limiter reached its own threshold on the same failures, and clearing
        only the row left the account still refused - which looks, from the
        outside, exactly like an unlock that did not work.
        """
        from app.utils.rate_limit import identifier_limiter

        row = self._row(identifier)
        identifier_limiter.reset(f"id:{normalise(identifier)}")

        if row is None or row.locked_until is None:
            return False
        row.failed_count = 0
        row.first_failed_at = None
        row.last_failed_at = None
        row.locked_until = None
        self.db.commit()
        return True

    def locked_identifiers(self, limit: int = 50):
        """Everything currently locked, newest first, for the office to see."""
        return (
            self.db.query(LoginAttempt)
            .filter(LoginAttempt.locked_until.isnot(None))
            .filter(LoginAttempt.locked_until > _utcnow())
            .order_by(LoginAttempt.last_locked_at.desc())
            .limit(limit)
            .all()
        )
