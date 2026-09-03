"""Authentication endpoints.

Accounts are provisioned by administrators, so there is deliberately no
registration endpoint here and none anywhere else in the API.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.auth.errors import (
    CREDENTIALS_ERROR,
    INACTIVE_ERROR,
    AuthErrorCode,
    auth_error,
    too_many_attempts_error,
)
from app.auth.jwt import decode_access_token
from app.auth.scheme import oauth2_scheme
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    ChangePasswordResponse,
    LoginRequest,
    LoginResponse,
    PasswordPolicy,
)
from app.schemas.common import Message
from app.schemas.user import UserProfile
from app.services.auth_service import AuthService
from app.utils.rate_limit import login_buckets

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=LoginResponse, summary="Sign in")
def login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> LoginResponse:
    """Exchange a username or email plus password for an access token.

    Repeated failures are throttled. Sign-in is the only endpoint a stranger
    can call over and over, so without a limit a weak password is only a
    matter of time.
    """
    client_ip = request.client.host if request.client else "unknown"
    buckets = login_buckets(payload.identifier, client_ip)

    for limiter, key in buckets:
        allowed, retry_after = limiter.check(key)
        if not allowed:
            raise too_many_attempts_error(retry_after)

    service = AuthService(db)
    user, error = service.authenticate(payload.identifier, payload.password)

    if user is None or error == "account_inactive":
        # A deactivated account counts too: it is still a password guess, and
        # treating it differently would make lockout reveal the account state.
        for limiter, key in buckets:
            limiter.record_failure(key)

    if error == "account_inactive":
        raise INACTIVE_ERROR
    if user is None:
        raise CREDENTIALS_ERROR

    # A correct password clears the slate, so honest mistyping never
    # accumulates towards a lockout.
    for limiter, key in buckets:
        limiter.reset(key)

    token, expires_in = service.issue_token(user)
    return LoginResponse(
        access_token=token,
        expires_in=expires_in,
        user=service.to_profile(user),
    )


@router.post("/logout", response_model=Message, summary="Sign out")
def logout(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Message:
    """Revoke the presented token so it cannot be used again.

    Deliberately tolerant: signing out with a token that is already expired or
    invalid still succeeds, because the outcome the caller wanted is the
    outcome they get. There is nothing to reveal and nothing to retry.
    """
    if token:
        payload, _error = decode_access_token(token)
        if payload:
            AuthService(db).revoke_token(payload)

    return Message(detail="You have been signed out.")


@router.get("/me", response_model=UserProfile, summary="Current user profile")
def read_current_user(user: User = Depends(get_current_user)) -> UserProfile:
    """Return the signed-in user profile; used to restore a session on reload."""
    return AuthService.to_profile(user)


@router.post(
    "/change-password",
    response_model=ChangePasswordResponse,
    summary="Change your own password",
)
def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChangePasswordResponse:
    """Replace the caller password, then end every session they hold.

    On success the current token stops validating immediately, so the client
    must discard it and sign in again with the new password.
    """
    service = AuthService(db)
    error = service.change_password(
        user, payload.current_password, payload.new_password
    )

    if error == "invalid_credentials":
        raise auth_error(
            AuthErrorCode.INVALID_CREDENTIALS,
            "Your current password is incorrect.",
        )

    return ChangePasswordResponse(
        detail="Your password has been changed. Please sign in again.",
        signed_out=True,
    )


@router.get(
    "/password-policy",
    response_model=PasswordPolicy,
    summary="Password rules enforced by the API",
)
def password_policy() -> PasswordPolicy:
    """Let the UI show exactly the rules the API will enforce."""
    return PasswordPolicy()
