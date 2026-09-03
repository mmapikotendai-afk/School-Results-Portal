"""Examination sittings and their submission deadlines."""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import DateTime, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import ExaminationStatus
from app.models.mixins import CreatedAtMixin


class Examination(Base, CreatedAtMixin):
    """One examination for one term, for example "End of Term 1 Examination".

    The status is the gate on the whole workflow: teachers may only upload
    while SUBMISSION_OPEN, and students may only see marks once PUBLISHED.
    """

    __tablename__ = "examinations"
    __table_args__ = (
        UniqueConstraint("term_id", "name", name="uq_examinations_term_name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    term_id: Mapped[int] = mapped_column(
        ForeignKey("terms.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)

    # Submissions after this moment are recorded as LATE.
    submission_deadline: Mapped[Optional[datetime]] = mapped_column(DateTime, index=True)

    status: Mapped[ExaminationStatus] = mapped_column(
        Enum(ExaminationStatus),
        default=ExaminationStatus.DRAFT,
        nullable=False,
        index=True,
    )

    # Publication is a deliberate act by a named person, never a side effect
    # of a deadline passing, so both the moment and the administrator are kept.
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    published_by_id: Mapped[Optional[int]] = mapped_column(
        "published_by", ForeignKey("users.id", ondelete="SET NULL")
    )

    term: Mapped["Term"] = relationship(back_populates="examinations")  # noqa: F821
    results: Mapped[List["Result"]] = relationship(  # noqa: F821
        back_populates="examination", cascade="all, delete-orphan"
    )
    submissions: Mapped[List["ResultSubmission"]] = relationship(  # noqa: F821
        back_populates="examination", cascade="all, delete-orphan"
    )
    published_by: Mapped[Optional["User"]] = relationship(  # noqa: F821
        foreign_keys=[published_by_id]
    )

    @property
    def is_open_for_submission(self) -> bool:
        return self.status == ExaminationStatus.SUBMISSION_OPEN

    @property
    def is_published(self) -> bool:
        return self.status == ExaminationStatus.PUBLISHED

    def __repr__(self) -> str:
        return f"<Examination {self.name} ({self.status.value})>"
