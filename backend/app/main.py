"""FastAPI application entrypoint.

Run locally with:  uvicorn app.main:app --reload
"""

import logging
from contextlib import asynccontextmanager

from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import OperationalError, ProgrammingError

from app import __version__
from app.config import settings
from app.database import check_database_connection, engine
from app.routers import api_router

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Report configuration and database status on startup."""
    logger.info("Starting %s v%s (%s)", settings.APP_NAME, __version__, settings.ENVIRONMENT)

    if not settings.is_configured:
        logger.warning(
            "Incomplete configuration: set SECRET_KEY and MYSQL_* in backend/.env "
            "(copy backend/.env.example to backend/.env)."
        )

    if settings.DEBUG and settings.ENVIRONMENT.lower() in {"production", "prod"}:
        logger.warning(
            "DEBUG is on while ENVIRONMENT is %s. Set DEBUG=false in production "
            "so error detail and the API docs are not exposed.",
            settings.ENVIRONMENT,
        )
    if not _DOCS_PUBLISHED:
        logger.info("API docs withdrawn (/docs, /redoc, /openapi.json) for %s.",
                    settings.ENVIRONMENT)

    connected, error = check_database_connection()
    if connected:
        # Report the database actually connected to, not MYSQL_DATABASE.
        # DATABASE_URL overrides the assembled URL entirely, so the two
        # disagree the moment it is set - and a startup line naming the
        # wrong database sends anyone debugging to the wrong data.
        logger.info("Database connection established (%s, %s).", engine.url.get_backend_name(), engine.url.database)
    else:
        logger.warning("Database unavailable - the API will still serve /health. %s", error)

    yield
    logger.info("Shutting down %s.", settings.APP_NAME)


# The interactive docs enumerate every route, its parameters and its schemas to
# anyone who asks, with no token required. That is exactly what you want while
# building and exactly what you do not want facing the internet, so they are
# published in development and withdrawn everywhere else.
_DOCS_PUBLISHED = settings.DEBUG or settings.ENVIRONMENT.lower() in {
    "development",
    "dev",
    "local",
}

app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "API for managing student subject enrollment, teacher CSV result uploads, "
        "result validation and correction, publishing, and report card generation."
    ),
    version=__version__,
    lifespan=lifespan,
    docs_url="/docs" if _DOCS_PUBLISHED else None,
    redoc_url="/redoc" if _DOCS_PUBLISHED else None,
    openapi_url="/openapi.json" if _DOCS_PUBLISHED else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    # Every download names its own file in Content-Disposition, and a browser
    # cannot read that header cross-origin unless it is exposed here. Without
    # it the report cards and mark sheets still download, but under whatever
    # fallback name the frontend guessed. In development the Vite proxy makes
    # the call same-origin and this never applies; in production it always does.
    expose_headers=["Content-Disposition"],
)

# Wording that means "the table or column is not there", across engines:
# MySQL raises ProgrammingError (1146), SQLite raises OperationalError, and
# Postgres says 'relation "x" does not exist' or 'column "x" does not exist'.
_MISSING_SCHEMA = (
    "doesn't exist",
    "does not exist",
    "no such table",
    "no such column",
    "unknown column",
)

CONNECTION_MESSAGE = (
    "The database is currently unavailable. Please try again in a moment."
)
SCHEMA_MESSAGE = (
    "The database schema is not set up. From the backend directory, run:  "
    "python -m scripts.init_db"
)
QUERY_MESSAGE = (
    "The server could not complete that request. The problem has been logged."
)


def _is_missing_schema(exc: Exception) -> bool:
    text = str(exc).lower()
    return any(marker in text for marker in _MISSING_SCHEMA)


@app.exception_handler(OperationalError)
async def database_unavailable_handler(request: Request, exc: Exception):
    """An unreachable database, or a missing table on SQLite, as a clean 503.

    OperationalError is what a dropped connection, a refused login or a
    database that is still waking up all raise. Those are genuinely the
    database being unavailable, and "try again" is honest advice for them.
    """
    logger.error("Database unavailable on %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": SCHEMA_MESSAGE if _is_missing_schema(exc) else CONNECTION_MESSAGE},
    )


@app.exception_handler(ProgrammingError)
async def database_query_handler(request: Request, exc: Exception):
    """A missing schema as a 503, and any other rejected query as a 500.

    ProgrammingError means the database was reachable and refused the SQL.
    That used to be reported as "the database is unavailable", which sent
    whoever read it to check connection settings that were never wrong - the
    real cause was a query Postgres rejects and MySQL had let through. A query
    the database will not run is a bug in the application, not an outage, and
    it is reported as one.
    """
    if _is_missing_schema(exc):
        logger.error("Missing schema on %s %s: %s", request.method, request.url.path, exc)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": SCHEMA_MESSAGE},
        )

    logger.exception("Query rejected on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": QUERY_MESSAGE},
    )


@app.middleware("http")
async def secure_uploaded_files(request: Request, call_next):
    """Serve uploaded files as inert content.

    The crest is the one file a person can put on this server. Upload
    validation already refuses anything that can execute, but a stored file is
    served straight back to browsers, so it is worth making that path safe
    twice over: no content-type sniffing, no scripts, no framing. A logo needs
    none of those, and without them a file that somehow got past validation
    still cannot run in this origin - which is where signed-in tokens live.
    """
    response = await call_next(request)
    if request.url.path.startswith("/uploads"):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; style-src 'unsafe-inline'; img-src data: blob:; "
            "sandbox"
        )
        response.headers["X-Frame-Options"] = "DENY"
    return response


app.include_router(api_router)

# Uploaded files (the school crest today, result CSVs later) are served from
# /uploads so the browser and the report card generator can both reach them.
_uploads = Path(settings.UPLOAD_DIR)
_uploads.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(_uploads)), name="uploads")


@app.get("/", tags=["Root"], summary="API root")
def root() -> dict[str, str]:
    """Point callers at the docs and the versioned API."""
    return {
        "service": settings.APP_NAME,
        "version": __version__,
        "docs": "/docs",
        "health": f"{settings.API_V1_PREFIX}/health",
    }
