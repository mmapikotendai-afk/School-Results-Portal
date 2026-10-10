from http.cookies import SimpleCookie

import pytest
from starlette.requests import Request
from starlette.responses import Response

from app.auth.session import attach_session, csrf_is_valid
from app.config import settings


def test_cookies_are_session_only_and_secure_in_production(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    response = Response()
    attach_session(response, "test-token")
    cookies = SimpleCookie()
    for header in response.headers.getlist("set-cookie"):
        cookies.load(header)
    for cookie in cookies.values():
        assert not cookie["max-age"]
        assert not cookie["expires"]
        assert cookie["secure"]
        assert cookie["samesite"] == "lax"
    assert cookies[settings.SESSION_COOKIE_NAME]["httponly"]
    assert not cookies[settings.CSRF_COOKIE_NAME]["httponly"]


@pytest.mark.parametrize("authorization", [None, "Bearer invalid", "Basic ignored"])
@pytest.mark.parametrize("csrf", [None, "wrong", "correct"])
def test_cookie_auth_always_requires_matching_csrf(authorization, csrf):
    headers = [(b"cookie", f"{settings.SESSION_COOKIE_NAME}=session; "
                f"{settings.CSRF_COOKIE_NAME}=correct".encode())]
    if authorization:
        headers.append((b"authorization", authorization.encode()))
    if csrf:
        headers.append((settings.CSRF_HEADER_NAME.lower().encode(), csrf.encode()))
    request = Request({"type": "http", "method": "POST", "path": "/", "headers": headers})
    assert csrf_is_valid(request) is (csrf == "correct")


def test_bearer_only_request_does_not_require_csrf():
    request = Request({"type": "http", "method": "POST", "path": "/",
                       "headers": [(b"authorization", b"Bearer test")]})
    assert csrf_is_valid(request)


def test_missing_csrf_cookie_rejected():
    request = Request({"type": "http", "method": "POST", "path": "/",
                       "headers": [(b"cookie", f"{settings.SESSION_COOKIE_NAME}=session".encode())]})
    assert not csrf_is_valid(request)


def test_invalid_bearer_cannot_bypass_middleware(client):
    response = client.post("/api/v1/auth/logout", headers={
        "Cookie": f"{settings.SESSION_COOKIE_NAME}=session; {settings.CSRF_COOKIE_NAME}=correct",
        "Authorization": "Bearer invalid",
    })
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "csrf_failed"


def test_health_unavailable_is_safe_503(client, monkeypatch):
    monkeypatch.setattr("app.routers.health.check_database_connection",
                        lambda: (False, "password=private host=internal.example"))
    response = client.get("/api/v1/health")
    assert response.status_code == 503
    assert response.json()["database"] == "disconnected"
    assert response.json()["status"] == "degraded"
    assert "private" not in response.text and "internal.example" not in response.text
    assert client.get("/api/v1/ping").status_code == 200


def test_health_available(client, monkeypatch):
    monkeypatch.setattr("app.routers.health.check_database_connection", lambda: (True, None))
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["database_error"] is None


def test_database_connection_error_is_sanitized(monkeypatch):
    from app import database

    def unavailable():
        raise RuntimeError("password=private host=internal.example")

    monkeypatch.setattr(database.engine, "connect", unavailable)
    assert database.check_database_connection() == (False, "The database is currently unavailable.")


def test_logo_is_served_as_image(client, tmp_path):
    from io import BytesIO
    from PIL import Image
    from app.dependencies.auth import require_admin
    from app.models.user import User
    from app.models.enums import UserRole

    client.app.dependency_overrides[require_admin] = lambda: User(id=1, role=UserRole.ADMIN)
    image = BytesIO()
    Image.new("RGB", (2, 2)).save(image, format="PNG")
    uploaded = client.post("/api/v1/admin/school/logo", files={
        "file": ("test.png", image.getvalue(), "image/png"),
    })
    assert uploaded.status_code == 200
    response = client.get(uploaded.json()["logo_url"])
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.content == image.getvalue()


def test_login_cookie_and_bearer_flows_and_revocation(client, db):
    from app.models.user import User
    from app.models.enums import UserRole
    from app.utils.security import hash_password

    db.add(User(email="login@example.com", username="login", full_name="Test Login",
                password_hash=hash_password("ReviewPassword!234"), role=UserRole.ADMIN))
    db.commit()
    login = client.post("/api/v1/auth/login", json={
        "identifier": "login", "password": "ReviewPassword!234",
    })
    assert login.status_code == 200
    token = login.json()["access_token"]
    assert all("max-age" not in h.lower() and "expires=" not in h.lower()
               for h in login.headers.get_list("set-cookie"))
    assert client.get("/api/v1/auth/me").status_code == 200
    csrf = client.cookies.get(settings.CSRF_COOKIE_NAME)
    assert client.post("/api/v1/auth/logout", headers={"Authorization": "Bearer invalid"}).status_code == 403
    logout = client.post("/api/v1/auth/logout", headers={settings.CSRF_HEADER_NAME: csrf})
    assert logout.status_code == 200
    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401

    login = client.post("/api/v1/auth/login", json={
        "identifier": "login", "password": "ReviewPassword!234",
    })
    token = login.json()["access_token"]
    client.cookies.clear()
    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 200
    assert client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"}).status_code == 200
