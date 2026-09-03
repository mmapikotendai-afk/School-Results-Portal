"""Authentication request and response schemas.

There is deliberately no registration schema: accounts are provisioned by
administrators through the admin router, never by the public.
"""

from typing import Optional

from pydantic import BaseModel, Field, model_validator

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
