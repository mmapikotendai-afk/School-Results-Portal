"""Consistently shaped authentication and authorisation failures.

Every error carries a machine-readable code alongside the sentence shown to
the user, so the frontend can tell an expired session apart from a bad
password without parsing prose.
"""

from typing import Optional

from fastapi import HTTPException, status


class AuthErrorCode(str):
    INVALID_CREDENTIALS = "invalid_credentials"
    ACCOUNT_INACTIVE = "account_inactive"
    TOKEN_MISSING = "token_missing"
    TOKEN_EXPIRED = "token_expired"
    TOKEN_INVALID = "token_invalid"
    TOKEN_REVOKED = "token_revoked"
    INSUFFICIENT_ROLE = "insufficient_role"
    PASSWORD_MISMATCH = "password_mismatch"
    WEAK_PASSWORD = "weak_password"
    TOO_MANY_ATTEMPTS = "too_many_attempts"


def auth_error(
    code: str,
    message: str,
    status_code: int = status.HTTP_401_UNAUTHORIZED,
    headers: Optional[dict] = None,
) -> HTTPException:
    """Build an HTTPException whose detail is {code, message}."""
    default_headers = {"WWW-Authenticate": "Bearer"} if status_code == 401 else None
    return HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message},
        headers=headers or default_headers,
    )


CREDENTIALS_ERROR = auth_error(
    AuthErrorCode.INVALID_CREDENTIALS,
    "Incorrect username or password.",
)

INACTIVE_ERROR = auth_error(
    AuthErrorCode.ACCOUNT_INACTIVE,
    "This account has been deactivated. Please contact the school office.",
    status_code=status.HTTP_403_FORBIDDEN,
)

FORBIDDEN_ERROR = auth_error(
    AuthErrorCode.INSUFFICIENT_ROLE,
    "You do not have permission to perform this action.",
    status_code=status.HTTP_403_FORBIDDEN,
)


def too_many_attempts_error(retry_after: int) -> HTTPException:
    """Sign-in has been temporarily refused after repeated failures.

    The wording says nothing about whether the account exists, so a lockout
    cannot be used to enumerate accounts.
    """
    minutes = max(1, round(retry_after / 60))
    return auth_error(
        AuthErrorCode.TOO_MANY_ATTEMPTS,
        (
            "Too many sign-in attempts. Please wait about "
            f"{minutes} minute{'' if minutes == 1 else 's'} and try again."
        ),
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        headers={"Retry-After": str(retry_after)},
    )
