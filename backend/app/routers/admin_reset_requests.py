"""The school office's password reset queue. Administrator only.

Approving a request reissues the credentials through the same service the
Students and Teachers pages already use, so there is one path that changes a
password and one place where that behaviour lives.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies.auth import require_admin
from app.models.enums import ResetRequestStatus
from app.models.password_reset import PasswordResetRequest
from app.models.user import User
from app.schemas.auth import PasswordResetDecision, PasswordResetRequestRead
from app.schemas.user import CredentialDelivery
from app.services.password_reset_service import PasswordResetService

router = APIRouter(
    prefix="/admin/reset-requests",
    tags=["Administration"],
    dependencies=[Depends(require_admin)],
)


def _read(row: PasswordResetRequest) -> PasswordResetRequestRead:
    """Flatten the account onto the row so the queue reads in one pass."""
    user = row.user
    return PasswordResetRequestRead(
        id=row.id,
        status=row.status,
        submitted_identifier=row.submitted_identifier,
        message=row.message,
        created_at=row.created_at,
        user_id=row.user_id,
        full_name=user.full_name if user else None,
        email=user.email if user else None,
        username=user.username if user else None,
        role=user.role if user else None,
        is_active=user.is_active if user else False,
        resolved_at=row.resolved_at,
        resolved_by=row.resolved_by.full_name if row.resolved_by else None,
        resolution_note=row.resolution_note,
    )


def _get(db: Session, request_id: int) -> PasswordResetRequest:
    row = PasswordResetService(db).get(request_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="That request no longer exists."
        )
    return row


@router.get("", response_model=List[PasswordResetRequestRead], summary="The reset queue")
def list_requests(
    request_status: Optional[ResetRequestStatus] = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
) -> List[PasswordResetRequestRead]:
    """Everyone who has asked for their password to be reissued, newest first."""
    return [_read(row) for row in PasswordResetService(db).list_requests(request_status)]


@router.get("/pending-count", summary="How many requests are waiting")
def pending_count(db: Session = Depends(get_db)) -> dict:
    """A single number, so the dashboard can badge the queue cheaply."""
    return {"pending": PasswordResetService(db).pending_count()}


@router.post(
    "/{request_id}/approve",
    response_model=CredentialDelivery,
    summary="Reissue this person's password",
)
def approve(
    request_id: int,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> CredentialDelivery:
    """Generate a new temporary password, email it, and close the request.

    Nobody chooses or sees the password: it is generated, hashed, sent and
    dropped. Every session the account holds ends immediately, and the holder
    must set their own password at next sign-in.
    """
    row = _get(db, request_id)

    delivery, error = PasswordResetService(db).approve(row, user)
    if error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)

    # Same shape the Students and Teachers pages already read, so the admin UI
    # reports a reset from the queue exactly as it reports a manual resend.
    holder = row.user
    domain = (settings.STUDENT_EMAIL_DOMAIN or "").strip().lower()
    real_mailbox = bool(domain) and not holder.email.strip().lower().endswith(f"@{domain}")

    return CredentialDelivery(
        email=holder.email,
        status=delivery.status,
        sent=delivery.sent,
        sent_at=holder.email_sent_at,
        detail=delivery.detail,
        can_resend=real_mailbox,
    )


@router.post(
    "/{request_id}/decline",
    response_model=PasswordResetRequestRead,
    summary="Refuse this request",
)
def decline(
    request_id: int,
    payload: PasswordResetDecision,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> PasswordResetRequestRead:
    """Close a request without changing anything.

    For the case where the office has spoken to the person and handled it
    another way, or does not believe the request came from the account holder.
    """
    row = _get(db, request_id)

    error = PasswordResetService(db).decline(row, user, payload.note)
    if error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)

    return _read(row)
