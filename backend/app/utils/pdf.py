"""Shared PDF helpers.

Kept in utils so both the report card renderer and the export renderers can use
them without importing each other.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def draw_logo(
    pdf,
    logo_path: Optional[str],
    *,
    x: float,
    y: float,
    h: Optional[float] = None,
    w: Optional[float] = None,
) -> bool:
    """Draw the school crest, or carry on without it.

    Give `h` or `w`, not both: fpdf scales the other side to keep the crest's
    proportions, so a tall badge and a wide one both come out undistorted.

    Returns True if the crest was drawn.

    The crest is decoration; the marks are the document. So *any* problem
    reading it is swallowed here and the page is rendered without it.

    This is deliberately a bare `Exception`. The narrower list this replaced -
    RuntimeError, FileNotFoundError, ValueError - looked careful but missed the
    failure that actually happens: a file that exists and is readable but is
    not a decodable image raises PIL's UnidentifiedImageError, which descends
    from OSError and so slipped straight through. The result was a 500 on every
    report card in the school until somebody replaced the crest. There is no
    image failure worth losing a report card over.
    """
    if not logo_path:
        return False

    size = {"h": h} if h is not None else {}
    if w is not None:
        size["w"] = w

    try:
        pdf.image(logo_path, x=x, y=y, **size)
        return True
    except Exception as exc:  # noqa: BLE001 - see the docstring
        logger.warning(
            "School crest could not be embedded (%s: %s). "
            "The document is being produced without it.",
            type(exc).__name__,
            exc,
        )
        return False
