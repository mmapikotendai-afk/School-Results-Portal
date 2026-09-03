"""Authentication business logic: sign in, sign out, change password."""

import secrets
from datetime import datetime, timezone
from typing import Optional, Tuple

from sqlalchemy import delete, or_
from sqlalchemy.orm import Session

from app.auth.jwt import create_access_token
from app.config import settings
from app.models.revoked_token import RevokedToken
from app.models.user import User
from app.schemas.user import UserProfile
from app.utils.security import hash_password, verify_password


class AuthService:
    """Credential verification, session issuing and revocation."""

    def __init__(self, db: Session) -> None:
        self.db = db

    # ---------------------------------------------------------------- lookup

    def get_by_identifier(self, identifier: str) -> Optional[User]:
        """Find a user by either email or username, case-insensitively."""
        normalised = identifier.strip().lower()
        if not normalised:
            return None
        return (
            self.db.query(User)
            .filter(or_(User.email == normalised, User.username == normalised))
            .first()
        )

    # ------------------------------------------------------------ sign in

    def authenticate(self, identifier: str, password: str) -> Tuple[Optional[User], Optional[str]]:
        """Verify credentials.

        Returns (user, error_code). "No such user" and "wrong password" both
        return invalid_credentials so the response cannot be used to discover
        which accounts exist. An inactive account is only reported as such
        after the password has been verified, for the same reason.
        """
        user = self.get_by_identifier(identifier)

        if user is None:
            # Spend roughly the same time as a real verification would, so the
            # response time does not reveal whether the account exists.
            verify_password(password, _DUMMY_HASH)
            return None, "invalid_credentials"

        if not verify_password(password, user.password_hash):
            return None, "invalid_credentials"

        if not user.is_active:
            return None, "account_inactive"

        return user, None

    def issue_token(self, user: User) -> Tuple[str, int]:
        """Mint an access token for a verified user and stamp the login time."""
        token, _jti, _expires_at = create_access_token(
            user_id=user.id, role=user.role.value, token_version=user.token_version
        )
        user.last_login_at = _utcnow()
        self.db.commit()
        return token, settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60

    # ------------------------------------------------------------ sign out

    def revoke_token(self, payload: dict) -> None:
        """Record a token as revoked so it stops being accepted immediately.

        A JWT cannot be recalled once issued, so signing out has to be tracked
        on the server or the token would stay usable until it expired.
        """
        jti = payload.get("jti")
        if not jti:
            return

        already = self.db.query(RevokedToken.id).filter(RevokedToken.jti == jti).first()
        if already:
            return

        exp = payload.get("exp")
        expires_at = (
            datetime.fromtimestamp(exp, tz=timezone.utc).replace(tzinfo=None)
            if exp
            else _utcnow()
        )

        sub = payload.get("sub")
        self.db.add(
            RevokedToken(
                jti=jti,
                user_id=int(sub) if sub else None,
                expires_at=expires_at,
            )
        )
        self.purge_expired_tokens()
        self.db.commit()

    def purge_expired_tokens(self) -> None:
        """Drop revocation rows for tokens that have since expired anyway."""
        self.db.execute(delete(RevokedToken).where(RevokedToken.expires_at < _utcnow()))

    def revoke_all_sessions(self, user: User) -> None:
        """Invalidate every token ever issued to this user.

        Bumping the version is enough on its own: each token carries the
        version it was minted with, and the dependency rejects any mismatch.
        """
        user.token_version += 1

    # ---------------------------------------------------- change password

    def change_password(
        self, user: User, current_password: str, new_password: str
    ) -> Optional[str]:
        """Replace a user password. Returns an error code, or None on success.

        On success every existing session is invalidated, so the user must
        sign in again with the new password - including on other devices.
        """
        if not verify_password(current_password, user.password_hash):
            return "invalid_credentials"

        user.password_hash = hash_password(new_password)
        user.password_changed_at = _utcnow()
        user.must_change_password = False
        self.revoke_all_sessions(user)
        self.db.commit()
        return None

    # ------------------------------------------------------------ profile

    @staticmethod
    def to_profile(user: User) -> UserProfile:
        """Build the profile payload, including role-specific identifiers."""
        return UserProfile(
            id=user.id,
            email=user.email,
            username=user.username,
            full_name=user.full_name,
            role=user.role,
            is_active=user.is_active,
            must_change_password=user.must_change_password,
            created_at=user.created_at,
            password_changed_at=user.password_changed_at,
            last_login_at=user.last_login_at,
            student_number=user.student.student_number if user.student else None,
            employee_number=user.teacher.employee_number if user.teacher else None,
            class_name=(
                user.student.school_class.name
                if user.student and user.student.school_class
                else None
            ),
        )


def _utcnow() -> datetime:
    """Naive UTC, matching how MySQL DATETIME columns are stored here."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


# A throwaway hash at the configured work factor. Verifying against it makes
# the "no such user" path cost the same as a genuine password check, so
# response time cannot be used to discover which accounts exist. Generated at
# import so it always tracks BCRYPT_ROUNDS.
_DUMMY_HASH = hash_password(secrets.token_urlsafe(24))
