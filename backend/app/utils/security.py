"""Password hashing and password policy.

bcrypt is used directly rather than through a wrapper library: it is the only
thing needed here, and the cost factor stays explicit and auditable.
"""

import re
import secrets
from typing import List, Optional, Sequence

import bcrypt

from app.config import settings

# bcrypt silently ignores anything past 72 bytes, so a longer password would
# be weaker than it looks. Reject rather than truncate.
MAX_PASSWORD_BYTES = 72

# Twelve, not eight. Guidance has moved away from forcing symbols and mixed
# case - they produce Password1! and nothing else - towards length plus a
# blocklist. Twelve also matches the length of the temporary passwords this
# module generates, so the rule the school is held to is the rule the system
# itself meets.
MIN_PASSWORD_LENGTH = 12

# Passwords a guesser tries first. Not a dictionary: a short list of the
# shapes that actually appear in a school, checked case-insensitively and
# with trailing digits stripped, so "school2026" is caught by "school".
COMMON_PASSWORDS = {
    "password", "passw0rd", "qwerty", "qwertyuiop", "letmein", "welcome",
    "admin", "administrator", "root", "login", "iloveyou", "monkey",
    "dragon", "sunshine", "princess", "football", "abc", "abcd", "abcdef",
    "abcdefg", "abcdefgh", "asdf", "asdfgh", "zxcvbn", "1q2w3e4r",
    "changeme", "secret", "temp", "temporary", "default", "test", "testing",
    "demo", "guest", "user", "pass", "master",
    # The ones a school portal specifically invites.
    "school", "results", "portal", "resultsportal", "schoolportal",
    "teacher", "teachers", "student", "students", "learner", "class",
    "mathematics", "maths", "english", "presbyterian", "highschool",
    "zimbabwe", "harare", "term", "exam", "examination", "report",
    "reportcard", "marks", "grade", "grades",
}

# Words the school itself puts in front of everyone, which is exactly what
# makes them the first guess. Extended at runtime from the configured school
# name so a rename carries through without a code change.
def _school_words() -> set:
    words = {"presbyterian", "results", "portal", "school"}
    for part in re.split(r"[^A-Za-z]+", settings.SCHOOL_NAME or ""):
        if len(part) >= 4:
            words.add(part.lower())
    return words

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


def _reduce(value: str) -> str:
    """Strip a password down to the part a guesser would recognise.

    Lowercased, with separators and trailing digits removed, so school2026,
    School_2026 and SCHOOL all reduce to the same word and are caught by one
    blocklist entry rather than needing a variant of each.
    """
    text = re.sub(r"[^a-z0-9]+", "", (value or "").lower())
    return re.sub(r"\d+$", "", text)


def password_policy_errors(
    password: str, identifiers: Optional[Sequence[str]] = None
) -> List[str]:
    """Return every way a password falls short. Empty list means acceptable.

    `identifiers` are the things this particular person is known by - their
    email, student or employee number, and name. A password containing any of
    them is refused, because STU-003 as a password is the realistic failure in
    a school and no complexity rule catches it.
    """
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

    reduced = _reduce(password)

    if reduced and reduced in COMMON_PASSWORDS:
        errors.append(
            "That password is one of the first a stranger would try. Choose "
            "something that is not a common word."
        )
    elif reduced and reduced in _school_words():
        errors.append(
            "That password is built from the school's own name. Choose "
            "something unrelated to the school."
        )

    # Identifiers keep their digits: STU-003 reduces to stu003, not stu. The
    # digits are most of what makes a student number guessable, and dropping
    # them left "STU-003abcdef" looking like an acceptable password.
    flat = re.sub(r"[^a-z0-9]+", "", (password or "").lower())
    for identifier in identifiers or []:
        piece = re.sub(r"[^a-z0-9]+", "", (identifier or "").lower())
        if len(piece) >= 4 and piece in flat:
            errors.append(
                "Password must not contain your name, email address or "
                "student or staff number."
            )
            break

    if re.fullmatch(r"(.)\1+", password or ""):
        errors.append("Password must not be the same character repeated.")

    return errors


def identifiers_for(user) -> List[str]:
    """The strings a password must not be built from, for one account."""
    values = [getattr(user, "email", None), getattr(user, "username", None),
              getattr(user, "full_name", None)]
    student = getattr(user, "student", None)
    teacher = getattr(user, "teacher", None)
    if student is not None:
        values += [student.student_number, student.first_name, student.last_name]
    if teacher is not None:
        values += [teacher.employee_number, teacher.first_name, teacher.last_name]

    out: List[str] = []
    for value in values:
        if not value:
            continue
        out.append(str(value))
        # An email's local part is what people actually reuse.
        if "@" in str(value):
            out.append(str(value).split("@", 1)[0])
    return out


def describe_password_policy() -> str:
    """One sentence describing the rules, for hints and error messages."""
    return (
        f"At least {MIN_PASSWORD_LENGTH} characters, including a letter and a "
        "number. Not a common word, the school's name, or your own name or "
        "number."
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
