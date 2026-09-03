"""Student subject enrollment - the authority on which results a student gets."""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Index, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import EnrollmentStatus


class StudentSubject(Base):
    """Links a student to a subject for one academic year.

    A result upload is rejected for any student and subject pair with no
    ACTIVE row here, which is what stops a student receiving marks for a
    subject they do not study.

    Dropping a subject sets status to INACTIVE and stamps dropped_at. The row
    is never deleted, so the enrollment history and every result already
    recorded against it remain intact.
    """

    __tablename__ = "student_subjects"
    __table_args__ = (
        UniqueConstraint(
            "student_id", "subject_id", "academic_year_id", name="uq_student_subject_year"
        ),
        # The hot path when validating an upload: who studies this subject
        # this year.
        Index("ix_student_subjects_year_subject_status", "academic_year_id", "subject_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), nullable=False
    )
    subject_id: Mapped[int] = mapped_column(
        ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    academic_year_id: Mapped[int] = mapped_column(
        ForeignKey("academic_years.id", ondelete="RESTRICT"), nullable=False
    )

    status: Mapped[EnrollmentStatus] = mapped_column(
        Enum(EnrollmentStatus), default=EnrollmentStatus.ACTIVE, nullable=False, index=True
    )

    enrolled_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    dropped_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    student: Mapped["Student"] = relationship(back_populates="subject_enrollments")  # noqa: F821
    subject: Mapped["Subject"] = relationship(back_populates="student_enrollments")  # noqa: F821
    academic_year: Mapped["AcademicYear"] = relationship(  # noqa: F821
        back_populates="student_enrollments"
    )

    @property
    def is_active(self) -> bool:
        return self.status == EnrollmentStatus.ACTIVE

    def __repr__(self) -> str:
        return f"<StudentSubject student={self.student_id} subject={self.subject_id}>"
