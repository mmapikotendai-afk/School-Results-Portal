"""Administrator-only account management.

Every endpoint here is gated by require_admin, which is checked on the server
regardless of what the frontend chose to render.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies.auth import require_admin
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.user import (
    AccountCreate,
    AccountProvisioned,
    AccountStatusUpdate,
    CredentialDelivery,
    UserRead,
)
from app.services.account_service import AccountService
from app.services import email_service
from app.services.provisioning_service import ProvisioningService

router = APIRouter(
    prefix="/admin/accounts",
    tags=["Administration"],
    dependencies=[Depends(require_admin)],
)


@router.get("", response_model=List[UserRead], summary="List accounts")
def list_accounts(
    role: Optional[UserRole] = Query(default=None),
    include_inactive: bool = Query(default=True),
    db: Session = Depends(get_db),
) -> List[User]:
    return AccountService(db).list_accounts(role=role, include_inactive=include_inactive)


@router.post(
    "",
    response_model=AccountProvisioned,
    status_code=status.HTTP_201_CREATED,
    summary="Create an admin, teacher or student account",
)
def create_account(
    payload: AccountCreate, db: Session = Depends(get_db)
) -> AccountProvisioned:
    """Provision an account and email its temporary password to the holder.

    This is the only route by which accounts appear: there is no public
    registration, and no way for a user to create their own.

    The response reports whether the credential email was delivered. It does
    not contain the password, and there is no field in which it could.
    """
    # Checked before anything is written: the password is generated, hashed
    # and dropped, so an address that cannot receive mail produces an account
    # nobody can ever sign in as.
    undeliverable = email_service.verify_deliverable(str(payload.email))
    if undeliverable:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"That email address cannot receive mail. {undeliverable}",
        )

    user, password, problem = AccountService(db).create_account(payload)
    if problem:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=problem)

    kept, result = ProvisioningService(db).deliver_or_discard(user, password)
    del password
    if not kept:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "The account was not created: its credentials could not be emailed. "
                f"{result.error or result.detail}"
            ),
        )

    return AccountProvisioned(
        user_id=user.id,
        full_name=user.full_name,
        role=user.role,
        delivery=_delivery(user, result),
        detail=result.detail,
    )


@router.post(
    "/{user_id}/resend-credentials",
    response_model=CredentialDelivery,
    summary="Resend login credentials",
)
def resend_credentials(user_id: int, db: Session = Depends(get_db)) -> CredentialDelivery:
    """Issue a new temporary password and email it to the account holder.

    Replaces the administrator password reset that used to take a typed
    password. Nobody chooses this value and nobody sees it but the holder:
    it is generated, hashed, sent, and dropped. The previous password stops
    working the moment the hash is replaced, and every session the account
    holds is ended.
    """
    user = _get_user(db, user_id)
    result = ProvisioningService(db).reissue_credentials(user)
    return _delivery(user, result)


@router.patch(
    "/{user_id}/status",
    response_model=UserRead,
    summary="Activate or deactivate an account",
)
def set_account_status(
    user_id: int,
    payload: AccountStatusUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> User:
    user = _get_user(db, user_id)

    # Locking yourself out is never the intent, and there may be no other
    # administrator left to undo it.
    if user.id == admin.id and not payload.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot deactivate your own account.",
        )

    return AccountService(db).set_active(user, payload.is_active)


def _delivery(user: User, result) -> CredentialDelivery:
    """The delivery outcome, in the shape the admin UI reads."""
    domain = (settings.STUDENT_EMAIL_DOMAIN or "").strip().lower()
    real_mailbox = bool(domain) and not user.email.strip().lower().endswith(f"@{domain}")
    return CredentialDelivery(
        email=user.email,
        status=result.status,
        sent=result.sent,
        sent_at=user.email_sent_at,
        detail=result.detail,
        can_resend=real_mailbox,
    )


def _get_user(db: Session, user_id: int) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Account not found."
        )
    return user
