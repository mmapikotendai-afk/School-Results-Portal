"""Server-side token revocation, so logout genuinely invalidates a token.

A JWT is self-contained: without a record of what has been revoked, a token
stays valid until it expires no matter what the client does with it. Each
issued token carries a unique jti, and signing out records that jti here.

Rows are only useful until the token would have expired anyway, so the table
stays small and is swept on each logout.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class RevokedToken(Base):
    """One access token that must no longer be accepted."""

    __tablename__ = "revoked_tokens"
    __table_args__ = (
        # The sweep that deletes tokens which have expired on their own.
        Index("ix_revoked_tokens_expires_at", "expires_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    # The jti claim of the revoked token.
    jti: Mapped[str] = mapped_column(String(36), unique=True, index=True, nullable=False)

    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )

    # When the token would have expired anyway; the row can be swept after this.
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    revoked_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<RevokedToken {self.jti}>"
