"""HTTP routers, aggregated onto a single versioned API router."""

from fastapi import APIRouter

from app.config import settings
from app.routers import (
    admin_academic,
    admin_accounts,
    admin_catalog,
    admin_results,
    admin_school,
    admin_submissions,
    admin_students,
    admin_teachers,
    auth,
    health,
    student_results,
    teacher_portal,
)

api_router = APIRouter(prefix=settings.API_V1_PREFIX)

api_router.include_router(health.router)
api_router.include_router(auth.router)

# Administrator portal. Every one of these routers is gated by require_admin.
api_router.include_router(admin_accounts.router)
api_router.include_router(admin_students.router)
api_router.include_router(admin_teachers.router)
api_router.include_router(admin_catalog.router)
api_router.include_router(admin_academic.router)
api_router.include_router(admin_results.router)
api_router.include_router(admin_school.router)
api_router.include_router(admin_submissions.router)

# Teacher portal. Every subject-scoped route checks the assignment first.
api_router.include_router(teacher_portal.router)

# Student portal. Publication is enforced in the service layer.
api_router.include_router(student_results.router)

# Feature routers still to come: teacher uploads, results, report cards.
__all__ = ["api_router"]
