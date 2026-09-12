"""A small in-process rate limiter, used to slow password guessing.

Sign-in is the one endpoint an unauthenticated stranger may call repeatedly,
so it is the one place brute force is possible. Everything else behind the
API already requires a token.

Scope, stated plainly: this counter lives in the memory of one process. Run
the API under several workers and each keeps its own tally, so the effective
limit multiplies by the worker count. That is still far better than nothing,
but a deployment behind more than one worker should put a shared limiter
(nginx, or Redis) in front of it. It is deliberately not backed by the
database: a failed sign-in should not write a row, or the limiter itself
becomes a way to fill the disk.
"""

import threading
import time
from typing import Dict, List, Tuple


class SlidingWindowLimiter:
    """Counts recent failures per key and reports when a key is locked out.

    Only failures are counted. A correct password clears the key, so somebody
    who mistypes a few times and then succeeds is never penalised.
    """

    def __init__(self, max_attempts: int, window_seconds: int) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._hits: Dict[str, List[float]] = {}
        self._lock = threading.Lock()

    def _prune(self, key: str, now: float) -> List[float]:
        """Drop timestamps that have fallen out of the window."""
        recent = [t for t in self._hits.get(key, []) if now - t < self.window_seconds]
        if recent:
            self._hits[key] = recent
        else:
            self._hits.pop(key, None)
        return recent

    def check(self, key: str) -> Tuple[bool, int]:
        """Return (allowed, seconds_until_retry) without recording anything."""
        now = time.monotonic()
        with self._lock:
            recent = self._prune(key, now)
            if len(recent) < self.max_attempts:
                return True, 0
            # Locked out until the oldest hit in the window expires.
            retry_after = int(self.window_seconds - (now - recent[0])) + 1
            return False, max(retry_after, 1)

    def record_failure(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            self._prune(key, now)
            self._hits.setdefault(key, []).append(now)

    def reset(self, key: str) -> None:
        """Forget a key's failures, called once a sign-in succeeds."""
        with self._lock:
            self._hits.pop(key, None)

    def clear(self) -> None:
        """Drop every counter. Used by tests, not by the application."""
        with self._lock:
            self._hits.clear()


LOGIN_WINDOW_SECONDS = 15 * 60

# Per account: five wrong passwords in fifteen minutes is well past honest
# mistyping, and still leaves a forgetful teacher room to get it right.
LOGIN_MAX_PER_IDENTIFIER = 5

# Per address, deliberately far looser. A school is usually one public address
# for the whole staff room, so a tight per-address limit would let five wrong
# passwords - spread across five different people - lock out everybody at once.
# This is set to catch one machine working through a list of accounts, not to
# punish a shared connection.
LOGIN_MAX_PER_IP = 40

identifier_limiter = SlidingWindowLimiter(LOGIN_MAX_PER_IDENTIFIER, LOGIN_WINDOW_SECONDS)
ip_limiter = SlidingWindowLimiter(LOGIN_MAX_PER_IP, LOGIN_WINDOW_SECONDS)


def login_buckets(identifier: str, client_ip: str):
    """The two counters a sign-in attempt is measured against.

    Counting the account name stops one account being hammered from many
    addresses; counting the address stops one address working through a list
    of accounts. Both are needed, and neither alone is enough.

    Returns (limiter, key) pairs so the caller can check, record and reset
    each without caring which is which.
    """
    return (
        (identifier_limiter, f"id:{(identifier or '').strip().lower()}"),
        (ip_limiter, f"ip:{client_ip or 'unknown'}"),
    )


# --- Password reset requests -------------------------------------------------
#
# The other endpoint a stranger may call without a token. It writes a row, so
# it is throttled harder than sign-in: the cost of abuse here is a queue the
# office has to wade through, not a guessed password.
RESET_WINDOW_SECONDS = 60 * 60

# Per identifier. Asking three times in an hour is already more than anybody
# needs; the office cannot act faster than that anyway.
RESET_MAX_PER_IDENTIFIER = 3

# Per address, looser for the same reason sign-in is: a whole staff room can
# share one public address.
RESET_MAX_PER_IP = 15

reset_identifier_limiter = SlidingWindowLimiter(
    RESET_MAX_PER_IDENTIFIER, RESET_WINDOW_SECONDS
)
reset_ip_limiter = SlidingWindowLimiter(RESET_MAX_PER_IP, RESET_WINDOW_SECONDS)


def reset_request_buckets(identifier: str, client_ip: str):
    """The two counters a password reset request is measured against.

    Unlike sign-in, every attempt counts - not just failures. There is no
    "success" to reset the counter on, because the endpoint deliberately
    reports the same outcome whether or not the account exists.
    """
    return (
        (reset_identifier_limiter, f"reset-id:{(identifier or '').strip().lower()}"),
        (reset_ip_limiter, f"reset-ip:{client_ip or 'unknown'}"),
    )
