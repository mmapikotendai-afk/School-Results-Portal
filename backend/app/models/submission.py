"""Result submission tracking.

One row per (examination, teacher subject assignment). Together the rows
answer the questions the submission monitor asks:

  - which teacher is responsible for which subject   -> assignment, teacher, subject
  - which examination is being submitted             -> examination
  - whether results have been submitted              -> status, submitted_at
  - submission date and time                         -> submitted_at
  - who uploaded the results                         -> submitted_by
  - whether the submission is overdue                -> is_overdue
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import SubmissionStatus
from app.models.mixins import TimestampMixin


class ResultSubmission(Base, TimestampMixin):
    """The submission state of one teacher and subject for one examination."""

    __tablename__ = "result_submissions"
    __table_args__ = (
        UniqueConstraint(
            "examination_id", "teacher_subject_id", name="uq_submission_exam_assignment"
        ),
        # The monitor screen: outstanding submissions for one examination.
        Index("ix_result_submissions_exam_status", "examination_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    examination_id: Mapped[int] = mapped_column(
        ForeignKey("examinations.id", ondelete="CASCADE"), nullable=False
    )

    # The assignment being tracked. Teacher and subject are denormalised
    # alongside it so the monitor can filter and sort without extra joins,
    # and so the record still reads correctly if the assignment is revised.
    teacher_subject_id: Mapped[int] = mapped_column(
        ForeignKey("teacher_subjects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    teacher_id: Mapped[int] = mapped_column(
        ForeignKey("teachers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    subject_id: Mapped[int] = mapped_column(
        ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    status: Mapped[SubmissionStatus] = mapped_column(
        Enum(SubmissionStatus), default=SubmissionStatus.PENDING, nullable=False, index=True
    )

    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, index=True)

    # The account that performed the upload. Usually the responsible teacher,
    # but an administrator may upload on their behalf, which is worth recording.
    submitted_by_id: Mapped[Optional[int]] = mapped_column(
        "submitted_by", ForeignKey("users.id", ondelete="SET NULL"), index=True
    )

    # Progress counters, refreshed by the service layer after each upload.
    expected_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    submitted_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    notes: Mapped[Optional[str]] = mapped_column(String(255))

    examination: Mapped["Examination"] = relationship(back_populates="submissions")  # noqa: F821
    assignment: Mapped["TeacherSubject"] = relationship(  # noqa: F821
        back_populates="submissions"
    )
    teacher: Mapped["Teacher"] = relationship(back_populates="submissions")  # noqa: F821
    subject: Mapped["Subject"] = relationship()  # noqa: F821
    submitted_by: Mapped[Optional["User"]] = relationship(  # noqa: F821
        foreign_keys=[submitted_by_id]
    )

    @property
    def is_submitted(self) -> bool:
        return self.status in (SubmissionStatus.SUBMITTED, SubmissionStatus.LATE)

    @property
    def is_overdue(self) -> bool:
        """True when the deadline has passed and the submission is incomplete.

        A submission already marked LATE stays overdue; one completed on time
        never becomes overdue, however long ago the deadline was.
        """
        if self.status == SubmissionStatus.LATE:
            return True
        if self.status == SubmissionStatus.SUBMITTED:
            return False

        deadline = self.examination.submission_deadline if self.examination else None
        if deadline is None:
            return False

        # Deadlines are stored naive in MySQL; compare against naive UTC.
        return datetime.now(timezone.utc).replace(tzinfo=None) > deadline

    def __repr__(self) -> str:
        return (
            f"<ResultSubmission exam={self.examination_id} "
            f"teacher={self.teacher_id} subject={self.subject_id} {self.status.value}>"
        )
