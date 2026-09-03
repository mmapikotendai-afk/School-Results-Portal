"""Health-check endpoints used by the frontend and by deployment probes."""

from datetime import datetime, timezone

from fastapi import APIRouter, status

from app import __version__
from app.config import settings
from app.database import check_database_connection
from app.schemas.common import HealthStatus

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthStatus, summary="Service health check")
def health_check() -> HealthStatus:
    """Report API liveness and MySQL connectivity.

    Always returns 200 so the frontend can render a useful status banner even
    while the database is still being configured.
    """
    db_ok, db_error = check_database_connection()
    return HealthStatus(
        status="ok" if db_ok else "degraded",
        service=settings.APP_NAME,
        version=__version__,
        environment=settings.ENVIRONMENT,
        database="connected" if db_ok else "disconnected",
        database_error=db_error if not db_ok else None,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/ping", status_code=status.HTTP_200_OK, summary="Lightweight liveness probe")
def ping() -> dict[str, str]:
    """Cheap liveness check that does not touch the database."""
    return {"message": "pong"}
