"""Password reset requests, raised by the account holder and settled by the office.

The portal issues accounts rather than letting people register, and a learner
may have no mailbox of their own - STUDENT_EMAIL_DOMAIN exists precisely
because of that. A self-service reset link would assume an inbox every user
controls privately, which is not true here, so a request is a row somebody in
the office looks at rather than an email the system sends on its own.

Nothing on this table can change a password. Approving one calls the same
credential reissue an administrator can already trigger by hand; the row only
records that somebody asked, and what was decided.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import ResetRequestStatus


class PasswordResetRequest(Base):
    """One request from one account holder to have their password reissued."""

    __tablename__ = "password_reset_requests"
    __table_args__ = (
        # The monitor reads pending requests newest first.
        Index("ix_password_reset_requests_status_created", "status", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # What the person actually typed on the sign-in screen. Kept as given so
    # the office can see that somebody is trying the wrong identifier - a
    # teacher using a personal address the school does not hold, say - which
    # the resolved account alone would not show.
    submitted_identifier: Mapped[str] = mapped_column(String(255), nullable=False)

    # Optional note from the requester: "my phone was stolen", and so on.
    message: Mapped[Optional[str]] = mapped_column(String(500))

    status: Mapped[ResetRequestStatus] = mapped_column(
        Enum(ResetRequestStatus), default=ResetRequestStatus.PENDING, nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # Set when an administrator approves or declines. Both are deliberate acts
    # and both are attributed, so a reset can always be traced to a person.
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    resolved_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    resolution_note: Mapped[Optional[str]] = mapped_column(String(500))

    user: Mapped["User"] = relationship(foreign_keys=[user_id])  # noqa: F821
    resolved_by: Mapped[Optional["User"]] = relationship(  # noqa: F821
        foreign_keys=[resolved_by_id]
    )

    def __repr__(self) -> str:
        return f"<PasswordResetRequest {self.id} {self.status.value}>"
