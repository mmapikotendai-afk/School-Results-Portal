"""Authentication: JWT issuing/decoding, error shapes and the bearer scheme."""

from app.auth.errors import AuthErrorCode, auth_error
from app.auth.jwt import TokenError, create_access_token, decode_access_token
from app.auth.scheme import oauth2_scheme

__all__ = [
    "AuthErrorCode",
    "TokenError",
    "auth_error",
    "create_access_token",
    "decode_access_token",
    "oauth2_scheme",
]
