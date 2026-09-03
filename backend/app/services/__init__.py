"""Business-logic layer. Routers stay thin; the rules live here."""

from app.services.auth_service import AuthService

__all__ = ["AuthService"]
