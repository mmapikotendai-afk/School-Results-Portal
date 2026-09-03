"""User-facing schemas.

Note the absence of any public registration schema. Accounts are created by
administrators through AccountCreate on the admin router.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.enums import UserRole
from app.utils.security import MAX_PASSWORD_BYTES, MIN_PASSWORD_LENGTH, password_policy_errors


class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=150)
    role: UserRole


class AccountCreate(UserBase):
    """Administrator-only account provisioning.

    An initial password is set by the administrator and the account is flagged
    must_change_password, so the holder replaces it from Settings > Security.
    """

    username: Optional[str] = Field(default=None, min_length=3, max_length=64)
    password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=MAX_PASSWORD_BYTES)

    # Role-specific identifiers, required for TEACHER and STUDENT respectively.
    student_number: Optional[str] = Field(default=None, max_length=32)
    employee_number: Optional[str] = Field(default=None, max_length=32)
    first_name: Optional[str] = Field(default=None, max_length=80)
    last_name: Optional[str] = Field(default=None, max_length=80)
    class_id: Optional[int] = None

    @field_validator("password")
    @classmethod
    def _policy(cls, value: str) -> str:
        errors = password_policy_errors(value)
        if errors:
            raise ValueError(" ".join(errors))
        return value

    @field_validator("username")
    @classmethod
    def _normalise_username(cls, value: Optional[str]) -> Optional[str]:
        return value.strip().lower() if value else None


class UserRead(UserBase):
    """Output shape.

    email is a plain str here, not EmailStr: the value has already been
    validated on the way in, and a derived sign-in identifier for a learner
    without a mailbox is not required to be a deliverable address. Re-validating
    on output turned reading a profile into a 500.
    """

    model_config = ConfigDict(from_attributes=True)

    email: str
    id: int
    username: Optional[str] = None
    is_active: bool
    created_at: datetime


class UserProfile(UserRead):
    """The authenticated user own profile, with role-specific identifiers."""

    must_change_password: bool = False
    student_number: Optional[str] = None
    employee_number: Optional[str] = None
    class_name: Optional[str] = None
    password_changed_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None


class AccountStatusUpdate(BaseModel):
    """Activate or deactivate an account. Deactivation ends every session."""

    is_active: bool


class AdminPasswordReset(BaseModel):
    """Administrator issues a new password, for example after it is forgotten."""

    new_password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=MAX_PASSWORD_BYTES)

    @field_validator("new_password")
    @classmethod
    def _policy(cls, value: str) -> str:
        errors = password_policy_errors(value)
        if errors:
            raise ValueError(" ".join(errors))
        return value
