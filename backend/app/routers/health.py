"""Health-check endpoints used by the frontend and by deployment probes."""

from datetime import datetime, timezone

from fastapi import APIRouter, Response, status

from app import __version__
from app.config import settings
from app.database import check_database_connection
from app.schemas.common import HealthStatus

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthStatus, summary="Service health check")
def health_check(response: Response) -> HealthStatus:
    """Report API liveness and MySQL connectivity.

    Returns 503 when the database is unavailable, with a safe public message.
    """
    db_ok, _db_error = check_database_connection()
    if not db_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return HealthStatus(
        status="ok" if db_ok else "degraded",
        service=settings.APP_NAME,
        version=__version__,
        environment=settings.ENVIRONMENT,
        database="connected" if db_ok else "disconnected",
        database_error="The database is currently unavailable." if not db_ok else None,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/ping", status_code=status.HTTP_200_OK, summary="Lightweight liveness probe")
def ping() -> dict[str, str]:
    """Cheap liveness check that does not touch the database."""
    return {"message": "pong"}
