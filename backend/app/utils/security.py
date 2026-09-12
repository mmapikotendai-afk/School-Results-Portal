"""Password hashing and password policy.

bcrypt is used directly rather than through a wrapper library: it is the only
thing needed here, and the cost factor stays explicit and auditable.
"""

import re
import secrets
from typing import List

import bcrypt

from app.config import settings

# bcrypt silently ignores anything past 72 bytes, so a longer password would
# be weaker than it looks. Reject rather than truncate.
MAX_PASSWORD_BYTES = 72
MIN_PASSWORD_LENGTH = 8

# Work factor, from BCRYPT_ROUNDS in the environment. Clamped to a floor of
# 10 so a misconfiguration cannot silently weaken every stored password.
BCRYPT_ROUNDS = max(10, settings.BCRYPT_ROUNDS)


def hash_password(plain_password: str) -> str:
    """Return a salted bcrypt hash. The plaintext is never persisted."""
    password_bytes = plain_password.encode("utf-8")
    if len(password_bytes) > MAX_PASSWORD_BYTES:
        raise ValueError(
            f"Password must be at most {MAX_PASSWORD_BYTES} bytes long."
        )
    salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    return bcrypt.hashpw(password_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Check a plain password against a stored bcrypt hash.

    Returns False rather than raising on a malformed hash, so a corrupted row
    cannot turn a failed login into a server error.
    """
    if not plain_password or not password_hash:
        return False
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8")[:MAX_PASSWORD_BYTES],
            password_hash.encode("utf-8"),
        )
    except (ValueError, TypeError):
        return False


def password_policy_errors(password: str) -> List[str]:
    """Return every way a password falls short. Empty list means acceptable."""
    errors: List[str] = []

    if len(password) < MIN_PASSWORD_LENGTH:
        errors.append(
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters long."
        )
    if len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        errors.append(f"Password must be at most {MAX_PASSWORD_BYTES} bytes long.")
    if not re.search(r"[A-Za-z]", password):
        errors.append("Password must contain at least one letter.")
    if not re.search(r"\d", password):
        errors.append("Password must contain at least one number.")
    if password.strip() != password:
        errors.append("Password must not start or end with a space.")

    return errors


def describe_password_policy() -> str:
    """One sentence describing the rules, for hints and error messages."""
    return (
        f"At least {MIN_PASSWORD_LENGTH} characters, "
        "including a letter and a number."
    )


# Ambiguous characters are left out so a password read aloud, or off a printed
# slip, cannot be mistyped: no 0/O, no 1/l/I.
_UNAMBIGUOUS_LETTERS = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
_UNAMBIGUOUS_DIGITS = "23456789"


def generate_temporary_password(length: int = 12) -> str:
    """A random one-time password that satisfies the policy above.

    Built from the CSPRNG, never from a seeded or time-based source. The value
    is returned to the caller, hashed, emailed, and then dropped: it is not
    stored, logged or recoverable afterwards.
    """
    length = max(MIN_PASSWORD_LENGTH, length)
    # Two digits guarantee the "must contain a number" rule, and the shuffle
    # keeps them from always landing at the end.
    characters = [secrets.choice(_UNAMBIGUOUS_DIGITS) for _ in range(2)]
    characters += [secrets.choice(_UNAMBIGUOUS_LETTERS) for _ in range(length - 2)]

    # secrets.SystemRandom, not random.shuffle: the ordering is part of the
    # secret and must come from the same source as the characters.
    secrets.SystemRandom().shuffle(characters)
    return "".join(characters)
