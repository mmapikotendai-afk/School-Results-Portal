"""Raising and settling password reset requests.

Two rules shape this module.

First, the sign-in screen must not become a way to find out who holds an
account here. Every outcome of `raise_request` - account found, account
unknown, account deactivated, request already open - returns the same thing to
the caller, and the router says the same sentence regardless. A stranger
typing addresses learns nothing.

Second, nothing here resets a password. Approving a request calls the same
ProvisioningService.reissue_credentials an administrator can already trigger
by hand, so there is one code path that changes a credential and one place
where that behaviour is defined.
"""

import logging
from typing import List, Optional, Tuple

from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.models.enums import ResetRequestStatus
from app.models.password_reset import PasswordResetRequest
from app.models.user import User
from app.services.provisioning_service import DeliveryResult, ProvisioningService
from app.services.academic_service import utcnow

logger = logging.getLogger(__name__)

# What every caller of raise_request is told, whatever actually happened.
ACKNOWLEDGEMENT = (
    "If that account exists, the school office has been notified and will "
    "reissue your password. You will receive an email once they have."
)


class PasswordResetService:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ------------------------------------------------------------ raising

    def find_account(self, identifier: str) -> Optional[User]:
        """Resolve a username or email address to an account.

        Matched case-insensitively on both, because somebody typing their own
        address at a login prompt should not have to remember how it was
        capitalised when the office created it.
        """
        needle = (identifier or "").strip().lower()
        if not needle:
            return None

        return (
            self.db.query(User)
            .filter(
                or_(
                    func.lower(User.email) == needle,
                    func.lower(User.username) == needle,
                )
            )
            .first()
        )

    def open_request_for(self, user: User) -> Optional[PasswordResetRequest]:
        """The request this user already has outstanding, if any."""
        return (
            self.db.query(PasswordResetRequest)
            .filter(
                PasswordResetRequest.user_id == user.id,
                PasswordResetRequest.status == ResetRequestStatus.PENDING,
            )
            .first()
        )

    def raise_request(
        self, identifier: str, message: Optional[str] = None
    ) -> None:
        """Record that somebody has asked for their password to be reissued.

        Returns nothing on purpose. The caller has no outcome to report,
        because reporting one would disclose whether the account exists.

        A second request while one is still pending updates the existing row
        rather than adding another, so somebody clicking twice does not give
        the office two identical jobs to work through.
        """
        user = self.find_account(identifier)

        if user is None:
            logger.info("Password reset requested for unknown identifier.")
            return

        # A deactivated account is not reinstated by asking for a password.
        # Leaving the row uncreated keeps the queue to work the office can
        # actually act on.
        if not user.is_active:
            logger.info("Password reset requested for a deactivated account (id=%s).", user.id)
            return

        existing = self.open_request_for(user)
        if existing is not None:
            existing.submitted_identifier = identifier.strip()[:255]
            if message:
                existing.message = message.strip()[:500]
            self.db.commit()
            return

        self.db.add(
            PasswordResetRequest(
                user_id=user.id,
                submitted_identifier=identifier.strip()[:255],
                message=(message or "").strip()[:500] or None,
                status=ResetRequestStatus.PENDING,
            )
        )
        self.db.commit()

    # ----------------------------------------------------------- settling

    def list_requests(
        self, status: Optional[ResetRequestStatus] = None, limit: int = 100
    ) -> List[PasswordResetRequest]:
        """The queue, newest first, optionally narrowed to one status."""
        query = self.db.query(PasswordResetRequest).options(
            joinedload(PasswordResetRequest.user),
            joinedload(PasswordResetRequest.resolved_by),
        )
        if status is not None:
            query = query.filter(PasswordResetRequest.status == status)
        return (
            query.order_by(PasswordResetRequest.created_at.desc()).limit(limit).all()
        )

    def pending_count(self) -> int:
        return (
            self.db.query(PasswordResetRequest)
            .filter(PasswordResetRequest.status == ResetRequestStatus.PENDING)
            .count()
        )

    def get(self, request_id: int) -> Optional[PasswordResetRequest]:
        return (
            self.db.query(PasswordResetRequest)
            .options(
                joinedload(PasswordResetRequest.user),
                joinedload(PasswordResetRequest.resolved_by),
            )
            .filter(PasswordResetRequest.id == request_id)
            .first()
        )

    def approve(
        self, request: PasswordResetRequest, acting_user: User
    ) -> Tuple[Optional[DeliveryResult], Optional[str]]:
        """Reissue the credentials this request asked for.

        Returns (delivery, error). The credential change and the resolution
        are committed together: a row marked approved whose password was never
        actually reissued would tell the office a lie they cannot see through.
        """
        if request.status != ResetRequestStatus.PENDING:
            return None, (
                f"That request was already {request.status.value.lower()}."
            )

        if not request.user.is_active:
            return None, (
                "That account is deactivated. Reactivate it first if this "
                "person should be able to sign in."
            )

        # Generates a temporary password, invalidates every session the
        # account holds, and emails the holder. Same path as the manual
        # resend an administrator can already use.
        delivery = ProvisioningService(self.db).reissue_credentials(request.user)

        request.status = ResetRequestStatus.APPROVED
        request.resolved_at = utcnow()
        request.resolved_by_id = acting_user.id
        self.db.commit()

        return delivery, None

    def decline(
        self, request: PasswordResetRequest, acting_user: User, note: Optional[str] = None
    ) -> Optional[str]:
        """Refuse a request, with a reason. Returns an error, or None."""
        if request.status != ResetRequestStatus.PENDING:
            return f"That request was already {request.status.value.lower()}."

        request.status = ResetRequestStatus.DECLINED
        request.resolved_at = utcnow()
        request.resolved_by_id = acting_user.id
        request.resolution_note = (note or "").strip()[:500] or None
        self.db.commit()
        return None
