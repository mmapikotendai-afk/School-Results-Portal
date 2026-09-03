"""School information used to brand report cards and the portal."""

from typing import Optional

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.mixins import TimestampMixin


class SchoolSettings(Base, TimestampMixin):
    """Single-row table holding the school identity.

    Administrators edit this rather than redeploying, so the crest, name and
    contact details on generated report cards can be changed from the portal.
    """

    __tablename__ = "school_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    school_name: Mapped[str] = mapped_column(String(200), nullable=False)

    # Path relative to the uploads directory, not a filesystem absolute path.
    logo_path: Mapped[Optional[str]] = mapped_column(String(255))

    address: Mapped[Optional[str]] = mapped_column(String(255))
    phone: Mapped[Optional[str]] = mapped_column(String(40))
    email: Mapped[Optional[str]] = mapped_column(String(255))
    motto: Mapped[Optional[str]] = mapped_column(String(255))

    # --- Report card format -------------------------------------------------
    # Schools differ on what belongs on a report card, so the format is
    # configuration rather than something baked into the renderer.

    # Whether a student's position in their class is printed.
    report_show_position: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )

    # What to do with a subject the student is not enrolled in: "omit" leaves
    # it off entirely, "blank" prints the row with empty marks so the report
    # matches a standard subject list. A mark is never invented either way.
    report_unenrolled: Mapped[str] = mapped_column(
        String(10), default="omit", nullable=False
    )

    # Background watermark: "logo", "name" or "none".
    report_watermark: Mapped[str] = mapped_column(
        String(10), default="name", nullable=False
    )

    def __repr__(self) -> str:
        return f"<SchoolSettings {self.school_name}>"
