"""Credential delivery for provisioned accounts.

Sits between account creation and the email service. Two jobs:

  deliver_new_credentials   email the password an account was just created with
  reissue_credentials       mint a fresh password, replace the hash, email it

Both record the outcome on the user row (email_sent, email_sent_at,
email_delivery_status) so an administrator can see which accounts never
received their details, and both are written so that a delivery failure never
undoes the account. An account that exists but whose email bounced is a
recoverable situation; an account silently rolled back after the administrator
was told it was created is not.

The plaintext password lives in a local variable for the length of one call:
long enough to hash and to render into the message, and no longer. It is not
returned to the caller, not written to the database, and not logged.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from app.models.enums import EmailDeliveryStatus
from app.models.user import User
from app.services import email_service
from app.services.email_service import DeliveryResult
from app.utils.security import generate_temporary_password, hash_password

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    """Naive UTC, matching how the DATETIME columns are stored."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ProvisioningService:
    """Issue and deliver account credentials."""

    def __init__(self, db: Session) -> None:
        self.db = db

    # ------------------------------------------------------------ recording

    def record_delivery(self, user: User, result: DeliveryResult) -> None:
        """Stamp the outcome of a delivery attempt onto the account.

        Committed by the caller along with whatever else it is writing, so a
        created account and its delivery record land in the same transaction.
        """
        user.email_delivery_status = result.status
        user.email_sent = result.sent
        user.email_last_error = result.error
        if result.sent:
            user.email_sent_at = _utcnow()

    # ------------------------------------------------------------ first send

    def deliver_new_credentials(
        self, user: User, temporary_password: str
    ) -> DeliveryResult:
        """Email the credentials a newly created account was issued with.

        Never raises: the account already exists by the time this runs, and the
        administrator needs to be told the truth about delivery rather than
        having the creation fail retrospectively.
        """
        result = email_service.send_account_credentials(
            user, temporary_password, reissued=False
        )
        self.record_delivery(user, result)
        self.db.commit()
        self.db.refresh(user)
        return result

    def deliver_or_discard(
        self, user: User, temporary_password: str
    ) -> Tuple[bool, DeliveryResult]:
        """Email the credentials, and delete the account if they cannot be sent.

        Returns (kept, result).

        This is the stricter counterpart to `deliver_new_credentials`. The
        password an account is created with is generated, hashed and
        discarded, so it exists in exactly one place afterwards: the message.
        If that message cannot be sent, the account has a password nobody
        knows and nobody can recover - it is not a usable account, it is a row
        that has to be found and cleaned up later.

        A FAILED delivery therefore takes the account with it. The
        administrator is told the address did not work and can correct it and
        try again, which is the outcome they wanted anyway.

        SKIPPED is deliberately not a discard. It means no attempt was made -
        normally because delivery is switched off - which is an administrator's
        configuration choice, not a bad address. Deleting accounts because the
        mail system is turned off would make the portal unusable offline.
        """
        result = email_service.send_account_credentials(
            user, temporary_password, reissued=False
        )

        if result.status == EmailDeliveryStatus.FAILED:
            # Cascades to the student/teacher row and its enrollments.
            self.db.delete(user)
            self.db.commit()
            logger.warning(
                "Discarded a new account for %s: credentials could not be delivered (%s).",
                user.email,
                result.error,
            )
            return False, result

        self.record_delivery(user, result)
        self.db.commit()
        self.db.refresh(user)
        return True, result

    # --------------------------------------------------------------- resend

    def reissue_credentials(self, user: User) -> DeliveryResult:
        """Generate a new temporary password, store its hash, and email it.

        Resending is deliberately not "send the same password again": the
        original plaintext is gone, and keeping a copy so it could be resent is
        exactly the thing this design refuses to do. So a resend mints a new
        password, which also has the effect of invalidating the old one.

        The previous password stops working the moment the hash is replaced,
        and every session the account holds is ended by the token version bump.
        """
        password = generate_temporary_password()

        user.password_hash = hash_password(password)
        user.must_change_password = True
        # Any session opened with the old password dies here. Tokens carry the
        # version they were minted with and are rejected on mismatch.
        user.token_version += 1
        user.email_delivery_status = EmailDeliveryStatus.PENDING
        self.db.commit()

        result = email_service.send_account_credentials(user, password, reissued=True)
        self.record_delivery(user, result)
        self.db.commit()
        self.db.refresh(user)

        # `password` goes out of scope here and is never persisted.
        return result

    # ---------------------------------------------------------------- status

    @staticmethod
    def summarise(user: User) -> Optional[str]:
        """One line an administrator can act on, or None when all is well."""
        status = user.email_delivery_status
        if status == EmailDeliveryStatus.SENT:
            return None
        if status == EmailDeliveryStatus.SKIPPED:
            return (
                "No email was sent. Check that email delivery is enabled and "
                "that the account has a real email address."
            )
        if status == EmailDeliveryStatus.FAILED:
            return (
                "The account was created, but the credentials could not be "
                "delivered by email."
            )
        return "No credential email has been sent for this account yet."
