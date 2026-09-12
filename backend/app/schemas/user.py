"""User-facing schemas.

Note the absence of any public registration schema. Accounts are created by
administrators through AccountCreate on the admin router.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.enums import EmailDeliveryStatus, UserRole


class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=150)
    role: UserRole


class AccountCreate(UserBase):
    """Administrator-only account provisioning.

    There is no password field. A temporary one is generated on the server,
    hashed, and emailed to the holder; the account is flagged
    must_change_password so it is replaced on first use. Nobody - including
    the administrator creating the account - ever sees the stored password.
    """

    username: Optional[str] = Field(default=None, min_length=3, max_length=64)

    # Role-specific identifiers, required for TEACHER and STUDENT respectively.
    student_number: Optional[str] = Field(default=None, max_length=32)
    employee_number: Optional[str] = Field(default=None, max_length=32)
    first_name: Optional[str] = Field(default=None, max_length=80)
    last_name: Optional[str] = Field(default=None, max_length=80)
    class_id: Optional[int] = None

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


class CredentialDelivery(BaseModel):
    """Whether the temporary password reached the account holder.

    Deliberately says nothing about what the password was. The administrator
    is told which address was used and whether it was accepted; if it was not,
    the remedy is Resend, which issues a fresh password rather than revealing
    the old one.
    """

    email: str
    status: EmailDeliveryStatus
    sent: bool
    sent_at: Optional[datetime] = None
    detail: str

    # False when there is no mailbox to send to, so the UI does not offer a
    # button that cannot work.
    can_resend: bool = True


class AccountProvisioned(BaseModel):
    """Response to an administrator after an account is created or resent."""

    user_id: int
    full_name: str
    role: UserRole
    delivery: CredentialDelivery
    detail: str
