"""Authentication request and response schemas.

There is deliberately no registration schema: accounts are provisioned by
administrators through the admin router, never by the public.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enums import ResetRequestStatus, UserRole
from app.schemas.user import UserProfile
from app.utils.security import (
    MAX_PASSWORD_BYTES,
    MIN_PASSWORD_LENGTH,
    describe_password_policy,
    password_policy_errors,
)


class LoginRequest(BaseModel):
    """Credentials posted by the sign-in form.

    One identifier field accepts either a username or an email address, so the
    form can offer a single box rather than making the user pick.
    """

    identifier: str = Field(
        min_length=1,
        max_length=255,
        description="Username or email address",
        examples=["teacher@school.edu"],
    )
    password: str = Field(min_length=1, max_length=MAX_PASSWORD_BYTES)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Token lifetime in seconds")


class LoginResponse(Token):
    """Token plus profile, so the client can route by role without a second call."""

    user: UserProfile


class ChangePasswordRequest(BaseModel):
    """Self-service password change from Settings > Security."""

    current_password: str = Field(min_length=1, max_length=MAX_PASSWORD_BYTES)
    new_password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=MAX_PASSWORD_BYTES)
    confirm_password: str = Field(min_length=1, max_length=MAX_PASSWORD_BYTES)

    @model_validator(mode="after")
    def _check(self):
        if self.new_password != self.confirm_password:
            raise ValueError("The new password and its confirmation do not match.")
        if self.new_password == self.current_password:
            raise ValueError("The new password must be different from the current one.")

        errors = password_policy_errors(self.new_password)
        if errors:
            raise ValueError(" ".join(errors))
        return self


class ChangePasswordResponse(BaseModel):
    """Password changes end the session, so the client must sign in again."""

    detail: str
    signed_out: bool = True


class PasswordPolicy(BaseModel):
    """Advertised so the UI can show the same rules the API enforces."""

    min_length: int = MIN_PASSWORD_LENGTH
    max_bytes: int = MAX_PASSWORD_BYTES
    description: str = Field(default_factory=describe_password_policy)


class SessionInfo(BaseModel):
    """Security tab data: when the password last changed, when we last saw you."""

    password_changed_at: Optional[str] = None
    last_login_at: Optional[str] = None
    must_change_password: bool = False


class PasswordResetRequestCreate(BaseModel):
    """What somebody locked out of their account sends from the sign-in screen.

    The identifier is whatever they use to sign in - a username or an email
    address. It is not validated as an email, because most learners sign in
    with a derived username rather than a mailbox of their own.
    """

    identifier: str = Field(min_length=1, max_length=255)
    message: Optional[str] = Field(default=None, max_length=500)

    @field_validator("identifier")
    @classmethod
    def _trim(cls, value: str) -> str:
        trimmed = (value or "").strip()
        if not trimmed:
            raise ValueError("Enter the username or email address you sign in with.")
        return trimmed


class PasswordResetRequestRead(BaseModel):
    """One row of the office's reset queue."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    status: ResetRequestStatus
    submitted_identifier: str
    message: Optional[str] = None
    created_at: datetime

    # Who is asking. Flattened from the account so the queue is readable
    # without the client having to fetch each user separately.
    user_id: int
    full_name: Optional[str] = None
    email: Optional[str] = None
    username: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: bool = True

    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    resolution_note: Optional[str] = None


class PasswordResetDecision(BaseModel):
    """An administrator's reason for declining a request."""

    note: Optional[str] = Field(default=None, max_length=500)
