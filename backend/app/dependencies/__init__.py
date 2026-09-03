"""Reusable FastAPI dependencies."""

from app.dependencies.auth import (
    get_current_active_user,
    get_current_user,
    require_admin,
    require_roles,
    require_staff,
    require_student,
    require_teacher,
)

__all__ = [
    "get_current_active_user",
    "get_current_user",
    "require_admin",
    "require_roles",
    "require_staff",
    "require_student",
    "require_teacher",
]
