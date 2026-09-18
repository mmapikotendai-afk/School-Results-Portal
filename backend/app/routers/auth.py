"""Authentication endpoints.

Accounts are provisioned by administrators, so there is deliberately no
registration endpoint here and none anywhere else in the API.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
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
from app.auth.session import attach_session, clear_session, token_from_request
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    ChangePasswordResponse,
    LoginRequest,
    LoginResponse,
    PasswordPolicy,
    PasswordResetRequestCreate,
)
from app.schemas.common import Message
from app.schemas.user import UserProfile
from app.services.auth_service import AuthService
from app.services.lockout_service import LockoutService
from app.utils.security import identifiers_for, password_policy_errors
from app.services.password_reset_service import ACKNOWLEDGEMENT, PasswordResetService
from app.utils.rate_limit import login_buckets, reset_request_buckets

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=LoginResponse, summary="Sign in")
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> LoginResponse:
    """Exchange a username or email plus password for an access token.

    Repeated failures are throttled. Sign-in is the only endpoint a stranger
    can call over and over, so without a limit a weak password is only a
    matter of time.
    """
    client_ip = request.client.host if request.client else "unknown"
    buckets = login_buckets(payload.identifier, client_ip)
    lockout = LockoutService(db)

    # The durable lock is checked first, and before the password is examined.
    # Verifying the password and then refusing would betray, through response
    # time, whether the guess was right.
    locked, retry_after = lockout.status(payload.identifier)
    if locked:
        raise too_many_attempts_error(retry_after)

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

        locked_now, retry_after = lockout.record_failure(payload.identifier)
        if locked_now:
            raise too_many_attempts_error(retry_after)

    if error == "account_inactive":
        raise INACTIVE_ERROR
    if user is None:
        raise CREDENTIALS_ERROR

    # A correct password clears the slate, so honest mistyping never
    # accumulates towards a lockout.
    for limiter, key in buckets:
        limiter.reset(key)
    lockout.clear(payload.identifier)

    token, expires_in = service.issue_token(user)

    # The session travels as an httpOnly cookie: unreadable to script, and
    # gone when the browser closes. The token is still returned in the body
    # so that API clients and the interactive docs keep working unchanged.
    csrf = attach_session(response, token, expires_in)
    response.headers["X-CSRF-Token"] = csrf

    return LoginResponse(
        access_token=token,
        expires_in=expires_in,
        user=service.to_profile(user),
    )


@router.post("/logout", response_model=Message, summary="Sign out")
def logout(
    request: Request,
    response: Response,
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Message:
    """Revoke the presented token so it cannot be used again.

    Deliberately tolerant: signing out with a token that is already expired or
    invalid still succeeds, because the outcome the caller wanted is the
    outcome they get. There is nothing to reveal and nothing to retry.
    """
    token = token_from_request(request) or token
    if token:
        payload, _error = decode_access_token(token)
        if payload:
            AuthService(db).revoke_token(payload)

    # Cleared whatever happened above: a caller who asked to be signed out
    # should not still be holding a session cookie afterwards.
    clear_session(response)
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
    response: Response,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChangePasswordResponse:
    """Replace the caller password, then end every session they hold.

    On success the current token stops validating immediately, so the client
    must discard it and sign in again with the new password.
    """
    # The shape rules ran in the schema. This one needs the account: a
    # password may not be built from the holder's own name, email, student or
    # staff number, which is the reuse a school actually sees.
    personal = password_policy_errors(
        payload.new_password, identifiers_for(user)
    )
    if personal:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=" ".join(personal)
        )

    service = AuthService(db)
    error = service.change_password(
        user, payload.current_password, payload.new_password
    )

    if error == "invalid_credentials":
        raise auth_error(
            AuthErrorCode.INVALID_CREDENTIALS,
            "Your current password is incorrect.",
        )

    # The token version has moved on, so every token this account holds is
    # already dead. Clearing the cookie makes the browser agree.
    clear_session(response)
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


@router.post(
    "/password-reset-request",
    response_model=Message,
    summary="Ask the school office to reissue your password",
)
def request_password_reset(
    payload: PasswordResetRequestCreate,
    request: Request,
    db: Session = Depends(get_db),
) -> Message:
    """Record that somebody cannot sign in and needs new credentials.

    This does not reset anything. It puts a request in front of the school
    office, who reissue the password themselves - the same act they can
    already perform from the Students and Teachers pages. Accounts here are
    issued rather than registered, and a learner may have no mailbox of their
    own, so a self-service reset link would assume something that is not true
    of this school.

    The reply is the same sentence whatever happened: account found, account
    unknown, account deactivated, or a request already open. Otherwise the
    sign-in screen would become a way to discover who holds an account.
    """
    client_ip = request.client.host if request.client else "unknown"

    for limiter, key in reset_request_buckets(payload.identifier, client_ip):
        allowed, retry_after = limiter.check(key)
        if not allowed:
            raise too_many_attempts_error(retry_after)
        limiter.record_failure(key)

    PasswordResetService(db).raise_request(payload.identifier, payload.message)
    return Message(detail=ACKNOWLEDGEMENT)
