"""School information, logo upload and the administrator dashboard."""

import io
import re
import secrets
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies.auth import require_admin
from app.models.school_settings import SchoolSettings
from app.schemas.common import Message
from app.schemas.school import DashboardStats, SchoolSettingsRead, SchoolSettingsUpdate
from app.services.school_service import DashboardService, SchoolService

router = APIRouter(
    prefix="/admin",
    tags=["Administration - School"],
    dependencies=[Depends(require_admin)],
)

# Raster and vector formats a report card generator can embed.
ALLOWED_LOGO_TYPES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/svg+xml": ".svg",
    "image/webp": ".webp",
}
MAX_LOGO_BYTES = 2 * 1024 * 1024

# The opening bytes each raster format must actually begin with. The declared
# content type arrives from the client and can say anything, so it decides
# nothing on its own: the file has to look like what it claims to be.
_MAGIC = {
    ".png": (b"\x89PNG\r\n\x1a\n",),
    ".jpg": (b"\xff\xd8\xff",),
    ".webp": (b"RIFF",),
}

# An SVG is a document, not a picture: it can carry script, event handlers and
# external references, and a browser opening it directly will run them in this
# API's origin - which is where the signed-in user's token lives. Anything that
# can execute is refused rather than sanitised, because a sanitiser that misses
# one construct is worse than a rule that admits only inert drawings.
_SVG_FORBIDDEN = (
    b"<script",
    b"javascript:",
    b"<foreignobject",
    b"<iframe",
    b"<embed",
    b"<object",
    b"<use",
    b"<handler",
    b"<set",
    b"<animate",
    b"data:text/html",
    b"&#",  # entity encoding used to smuggle the words above past a scan
)

# on* attributes: onload, onclick, onerror and the rest.
_SVG_EVENT_ATTR = re.compile(rb"\bon[a-z]+\s*=")


def _reject(message: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)


def _verify_image_bytes(contents: bytes, extension: str) -> None:
    """Confirm the upload really is the kind of image it says it is."""
    if extension == ".svg":
        head = contents.lstrip()[:1024].lower()
        if not (head.startswith(b"<?xml") or head.startswith(b"<svg") or b"<svg" in head):
            raise _reject("That file does not look like an SVG image.")

        lowered = contents.lower()
        if _SVG_EVENT_ATTR.search(lowered) or any(t in lowered for t in _SVG_FORBIDDEN):
            raise _reject(
                "That SVG contains script or embedded content and cannot be used as "
                "a logo. Save it as a plain image (PNG is a good choice) and upload "
                "that instead."
            )
        return

    expected = _MAGIC.get(extension)
    if expected and not any(contents.startswith(sig) for sig in expected):
        raise _reject(
            "That file is not a valid image, or its contents do not match its type."
        )

    # The right opening bytes are not enough. A file can carry a correct PNG
    # header and be truncated or corrupt after it - which passes a signature
    # check, is stored happily, and only surfaces later when a report card
    # tries to embed it. Decode it here instead, so a bad crest is refused at
    # the moment somebody uploads it rather than discovered downstream.
    try:
        from PIL import Image

        Image.open(io.BytesIO(contents)).verify()
    except ImportError:  # pragma: no cover - Pillow ships with fpdf2
        pass
    except Exception:
        raise _reject(
            "That image could not be read - it may be incomplete or corrupted. "
            "Try opening it, saving it again, and uploading the new file."
        ) from None


def _logo_dir() -> Path:
    path = Path(settings.UPLOAD_DIR) / "logos"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _to_read(record: SchoolSettings) -> SchoolSettingsRead:
    return SchoolSettingsRead(
        id=record.id,
        school_name=record.school_name,
        logo_path=record.logo_path,
        # Served by the static mount in main.py, so the browser can show it.
        logo_url=f"/uploads/{record.logo_path}" if record.logo_path else None,
        address=record.address,
        phone=record.phone,
        email=record.email,
        motto=record.motto,
        report_show_position=record.report_show_position,
        report_unenrolled=record.report_unenrolled,
        report_watermark=record.report_watermark,
        updated_at=record.updated_at,
    )


@router.get("/school", response_model=SchoolSettingsRead, summary="School information")
def get_school(db: Session = Depends(get_db)) -> SchoolSettingsRead:
    return _to_read(SchoolService(db).get_or_create(settings.SCHOOL_NAME))


@router.put("/school", response_model=SchoolSettingsRead, summary="Update school information")
def update_school(
    payload: SchoolSettingsUpdate, db: Session = Depends(get_db)
) -> SchoolSettingsRead:
    """The name and crest set here are what appear on generated report cards."""
    return _to_read(SchoolService(db).update(payload))


@router.post(
    "/school/logo", response_model=SchoolSettingsRead, summary="Upload the school logo"
)
async def upload_logo(
    file: UploadFile = File(...), db: Session = Depends(get_db)
) -> SchoolSettingsRead:
    """Store the crest and point school_settings at it.

    The filename is generated rather than taken from the upload: a client
    supplied name could contain path separators and escape the upload
    directory. Only the declared type decides the extension.
    """
    extension = ALLOWED_LOGO_TYPES.get((file.content_type or "").lower())
    if extension is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The logo must be a PNG, JPEG, SVG or WebP image.",
        )

    contents = await file.read()
    if len(contents) > MAX_LOGO_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="The logo must be 2 MB or smaller.",
        )
    if not contents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="The uploaded file is empty."
        )

    # The declared type chose the extension; now make the bytes prove it.
    _verify_image_bytes(contents, extension)

    service = SchoolService(db)
    previous = service.get_or_create(settings.SCHOOL_NAME).logo_path

    filename = f"logo-{secrets.token_hex(8)}{extension}"
    (_logo_dir() / filename).write_bytes(contents)

    record = service.set_logo(f"logos/{filename}")

    # Remove the file the record no longer points at, so replacing the crest
    # repeatedly does not fill the disk.
    if previous and previous != record.logo_path:
        stale = Path(settings.UPLOAD_DIR) / previous
        try:
            stale.unlink(missing_ok=True)
        except OSError:
            pass  # a leftover file is not worth failing the request over

    return _to_read(record)


@router.delete("/school/logo", response_model=Message, summary="Remove the school logo")
def delete_logo(db: Session = Depends(get_db)) -> Message:
    service = SchoolService(db)
    record = service.get_or_create(settings.SCHOOL_NAME)

    if record.logo_path:
        try:
            (Path(settings.UPLOAD_DIR) / record.logo_path).unlink(missing_ok=True)
        except OSError:
            pass
        service.set_logo(None)

    return Message(detail="The school logo has been removed.")


@router.get("/dashboard", response_model=DashboardStats, summary="Administrator dashboard")
def dashboard(db: Session = Depends(get_db)) -> DashboardStats:
    """Head counts, the current examination and submission progress, in one call."""
    return DashboardService(db).stats()
