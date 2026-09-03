"""JSON Web Token creation and verification."""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError

from app.config import settings


class TokenError(str):
    """Machine-readable reasons a token was rejected."""

    EXPIRED = "token_expired"
    INVALID = "token_invalid"


def create_access_token(
    user_id: int,
    role: str,
    token_version: int,
    expires_delta: Optional[timedelta] = None,
    extra_claims: Optional[Dict[str, Any]] = None,
) -> Tuple[str, str, datetime]:
    """Mint a signed access token.

    Returns (token, jti, expires_at). The jti lets a single token be revoked
    at logout; the version claim lets every token for a user be invalidated
    at once when their password changes.
    """
    now = datetime.now(timezone.utc)
    expires_at = now + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    jti = str(uuid.uuid4())

    payload: Dict[str, Any] = {
        "sub": str(user_id),
        "role": role,
        "ver": token_version,
        "jti": jti,
        "iat": now,
        "exp": expires_at,
        "type": "access",
    }
    if extra_claims:
        payload.update(extra_claims)

    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, jti, expires_at


def decode_access_token(token: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Decode and verify a token.

    Returns (payload, error). An expired token is reported separately from a
    malformed or badly signed one, so the client can say "your session ended"
    rather than "something went wrong".
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["exp", "sub"]},
        )
    except ExpiredSignatureError:
        return None, TokenError.EXPIRED
    except InvalidTokenError:
        return None, TokenError.INVALID

    if payload.get("type") != "access":
        return None, TokenError.INVALID

    return payload, None
