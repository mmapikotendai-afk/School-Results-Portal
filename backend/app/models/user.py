"""User accounts. Accounts are created by administrators only."""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import EmailDeliveryStatus, UserRole
from app.models.mixins import TimestampMixin


class User(Base, TimestampMixin):
    """An authenticated portal user: ADMIN, TEACHER or STUDENT.

    Only the bcrypt hash of the password is ever stored; the plaintext is
    discarded as soon as it has been hashed in app/utils/security.py.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Sign-in identifiers. Email is required; username is an optional shorter
    # alias, so staff can sign in with either. Both are matched case-insensitively
    # by the service layer, which stores them lowercased.
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(64), unique=True, index=True)

    # bcrypt hash only. The plaintext is discarded the moment it is hashed.
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # Display name. Students and teachers also carry structured names on their
    # profile rows; an ADMIN has no profile row, so the name lives here.
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)

    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    # Set when an administrator issues or resets credentials. Surfaced only in
    # Settings > Security, never as a login-time notification.
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Bumped on every password change and on "sign out everywhere". Access
    # tokens carry the version they were minted with, so every token issued
    # before the change stops validating immediately.
    token_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    password_changed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Delivery record for the credential email. This tracks whether the
    # temporary password reached the holder, which is the difference between
    # "the account is ready" and "the account exists but nobody can get in".
    # The password itself is never recorded here, or anywhere else.
    email_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    email_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    email_delivery_status: Mapped[EmailDeliveryStatus] = mapped_column(
        Enum(EmailDeliveryStatus),
        default=EmailDeliveryStatus.NOT_SENT,
        nullable=False,
    )
    # Why the last attempt failed, so an administrator can act on it. Provider
    # text only - it never carries the message body or the password.
    email_last_error: Mapped[Optional[str]] = mapped_column(String(255))

    student: Mapped[Optional["Student"]] = relationship(  # noqa: F821
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    teacher: Mapped[Optional["Teacher"]] = relationship(  # noqa: F821
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )

    # Results this user uploaded, and corrections this user made. Both are
    # audit trails, so neither cascades a delete.
    uploaded_results: Mapped[List["Result"]] = relationship(  # noqa: F821
        back_populates="uploaded_by", foreign_keys="Result.uploaded_by_id"
    )
    result_changes: Mapped[List["ResultAuditLog"]] = relationship(  # noqa: F821
        back_populates="changed_by"
    )

    @property
    def display_identifier(self) -> str:
        """What the user typed to sign in, preferring the shorter alias."""
        return self.username or self.email

    def __repr__(self) -> str:
        return f"<User {self.email} ({self.role.value})>"
