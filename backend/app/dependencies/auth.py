"""Dependencies that resolve and authorise the current user.

This is the backend half of access control. Frontend route guards only
decide what to render; every protected endpoint re-checks the token and the
role here, so a crafted request cannot reach data the UI would have hidden.
"""

from typing import Optional

from fastapi import Depends
from sqlalchemy.orm import Session

from app.auth.errors import (
    FORBIDDEN_ERROR,
    INACTIVE_ERROR,
    AuthErrorCode,
    auth_error,
)
from app.auth.jwt import TokenError, decode_access_token
from app.auth.scheme import oauth2_scheme
from app.database import get_db
from app.models.enums import UserRole
from app.models.revoked_token import RevokedToken
from app.models.user import User


def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Resolve a bearer token to a User, rejecting it at four separate gates.

    1. Signature and expiry     - is the token genuine and still in date?
    2. Revocation list          - was this exact token signed out?
    3. Token version            - has the password changed since it was issued?
    4. Account state            - is the account still active?
    """
    if not token:
        raise auth_error(
            AuthErrorCode.TOKEN_MISSING, "Authentication is required."
        )

    payload, error = decode_access_token(token)
    if error == TokenError.EXPIRED:
        raise auth_error(
            AuthErrorCode.TOKEN_EXPIRED,
            "Your session has expired. Please sign in again.",
        )
    if payload is None:
        raise auth_error(
            AuthErrorCode.TOKEN_INVALID, "Your session is no longer valid."
        )

    jti = payload.get("jti")
    if jti and db.query(RevokedToken.id).filter(RevokedToken.jti == jti).first():
        raise auth_error(
            AuthErrorCode.TOKEN_REVOKED,
            "You have been signed out. Please sign in again.",
        )

    try:
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError):
        raise auth_error(
            AuthErrorCode.TOKEN_INVALID, "Your session is no longer valid."
        ) from None

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise auth_error(
            AuthErrorCode.TOKEN_INVALID, "Your session is no longer valid."
        )

    # A password change bumps token_version, retiring every token minted before it.
    if payload.get("ver") != user.token_version:
        raise auth_error(
            AuthErrorCode.TOKEN_REVOKED,
            "Your password was changed. Please sign in again.",
        )

    if not user.is_active:
        raise INACTIVE_ERROR

    return user


def get_current_active_user(user: User = Depends(get_current_user)) -> User:
    """Alias kept for readability at call sites. get_current_user already
    rejects inactive accounts, so this is the same guarantee under a clearer name.
    """
    return user


def require_roles(*roles: UserRole):
    """Build a dependency that admits only the given roles.

    Usage:
        @router.get("/", dependencies=[Depends(require_roles(UserRole.ADMIN))])

    or, when the endpoint needs the user object:
        user: User = Depends(require_roles(UserRole.ADMIN))
    """
    allowed = set(roles)

    def _check_role(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed:
            raise FORBIDDEN_ERROR
        return user

    return _check_role


# Ready-made guards for the three roles.
require_admin = require_roles(UserRole.ADMIN)
require_teacher = require_roles(UserRole.TEACHER)
require_student = require_roles(UserRole.STUDENT)
require_staff = require_roles(UserRole.ADMIN, UserRole.TEACHER)
