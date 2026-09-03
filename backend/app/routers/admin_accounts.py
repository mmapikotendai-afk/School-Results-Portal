"""Administrator-only account management.

Every endpoint here is gated by require_admin, which is checked on the server
regardless of what the frontend chose to render.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import require_admin
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.common import Message
from app.schemas.user import (
    AccountCreate,
    AccountStatusUpdate,
    AdminPasswordReset,
    UserRead,
)
from app.services.account_service import AccountService

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
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a teacher or student account",
)
def create_account(payload: AccountCreate, db: Session = Depends(get_db)) -> User:
    """Provision an account. This is the only route by which accounts appear."""
    user, problem = AccountService(db).create_account(payload)
    if problem:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=problem)
    return user


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


@router.post(
    "/{user_id}/reset-password",
    response_model=Message,
    summary="Issue a new password for an account",
)
def reset_password(
    user_id: int,
    payload: AdminPasswordReset,
    db: Session = Depends(get_db),
) -> Message:
    """Set a new password and end every session that account holds."""
    user = _get_user(db, user_id)
    AccountService(db).reset_password(user, payload.new_password)
    return Message(
        detail=(
            f"A new password has been set for {user.email}. They will be asked "
            "to change it from Settings."
        )
    )


def _get_user(db: Session, user_id: int) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Account not found."
        )
    return user
