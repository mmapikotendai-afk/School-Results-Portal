"""The session cookie, and the CSRF token that has to accompany it.

Why a cookie at all. The token used to live in localStorage, which has two
properties that matter: any script on the page can read it, and it survives
the browser closing. The first makes cross-site scripting worth far more to
an attacker than it should be; the second means the next person to use a
shared staff-room machine is still signed in as the last one. An httpOnly
cookie is unreadable to script and, without an expiry, is discarded when the
browser closes.

Why CSRF protection comes with it. A cookie is attached by the browser to
every request to this origin, including one triggered by another site. The
bearer header never was, which is why it needed no such defence. The scheme
here is the double submit: a second, readable cookie carries a random value,
and unsafe requests must echo it in a header. Another origin can cause the
request but cannot read the cookie to echo it.
"""

import secrets

from fastapi import Request, Response

from app.config import settings

# Requests that cannot change anything do not need the CSRF token.
SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}


def issue_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def attach_session(response: Response, token: str, max_age: int) -> str:
    """Set the session and CSRF cookies. Returns the CSRF token."""
    csrf = issue_csrf_token()

    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=token,
        max_age=max_age,
        httponly=True,                      # unreadable to JavaScript
        secure=settings.cookie_secure,
        samesite=settings.SESSION_COOKIE_SAMESITE,
        path="/",
    )
    # Readable on purpose: the page has to echo it back in a header.
    response.set_cookie(
        key=settings.CSRF_COOKIE_NAME,
        value=csrf,
        max_age=max_age,
        httponly=False,
        secure=settings.cookie_secure,
        samesite=settings.SESSION_COOKIE_SAMESITE,
        path="/",
    )
    return csrf


def clear_session(response: Response) -> None:
    for name in (settings.SESSION_COOKIE_NAME, settings.CSRF_COOKIE_NAME):
        response.delete_cookie(key=name, path="/")


def token_from_request(request: Request) -> str | None:
    """The session token carried by this request, cookie first."""
    return request.cookies.get(settings.SESSION_COOKIE_NAME)


def csrf_is_valid(request: Request) -> bool:
    """Whether an unsafe, cookie-authenticated request may proceed.

    A request authenticated by the Authorization header is exempt: the browser
    never attaches that header on its own, so it cannot be forged from another
    origin in the first place.
    """
    if request.method in SAFE_METHODS:
        return True

    authorization = request.headers.get("authorization", "")
    if authorization.lower().startswith("bearer "):
        return True

    cookie = request.cookies.get(settings.CSRF_COOKIE_NAME)
    if not cookie:
        # No CSRF cookie means no cookie session either; the request will be
        # rejected for want of authentication rather than here.
        return request.cookies.get(settings.SESSION_COOKIE_NAME) is None

    sent = request.headers.get(settings.CSRF_HEADER_NAME, "")
    return bool(sent) and secrets.compare_digest(sent, cookie)
