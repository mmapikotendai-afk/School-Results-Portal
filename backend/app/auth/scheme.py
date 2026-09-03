"""The bearer-token scheme used to protect endpoints.

`auto_error=False` lets dependencies raise their own, consistently shaped error.
"""

from fastapi.security import OAuth2PasswordBearer

from app.config import settings

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_PREFIX}/auth/login",
    auto_error=False,
)
