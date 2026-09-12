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
from app.database import check_database_connection
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
        logger.info("MySQL connection established (%s).", settings.MYSQL_DATABASE)
    else:
        logger.warning("MySQL unavailable - the API will still serve /health. %s", error)

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
# MySQL raises ProgrammingError (1146), SQLite raises OperationalError.
_MISSING_SCHEMA = ("doesn't exist", "no such table", "no such column", "unknown column")

CONNECTION_MESSAGE = (
    "The database is currently unavailable. Please check the MySQL connection "
    "settings in backend/.env and try again."
)
SCHEMA_MESSAGE = (
    "The database schema is not set up. From the backend directory, run:  "
    "python -m scripts.init_db"
)


def _database_message(exc: Exception) -> str:
    """Tell a fresh install apart from a connectivity problem.

    Both are 503s, but the fixes are entirely different, and guessing wrong
    sends someone to check credentials that were never the problem.
    """
    text = str(exc).lower()
    return SCHEMA_MESSAGE if any(m in text for m in _MISSING_SCHEMA) else CONNECTION_MESSAGE


@app.exception_handler(OperationalError)
@app.exception_handler(ProgrammingError)
async def database_unavailable_handler(request: Request, exc: Exception):
    """Turn an unreachable database or a missing schema into a clean 503.

    Without this the client sees an opaque 500 and a stack trace whenever the
    database is unreachable or the tables have not been created - which is the
    normal state of a fresh install, before setup has been done.
    """
    logger.error("Database error on %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": _database_message(exc)},
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
