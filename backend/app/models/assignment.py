"""Teacher subject assignment."""

from typing import List

from sqlalchemy import Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import CreatedAtMixin


class TeacherSubject(Base, CreatedAtMixin):
    """Makes one teacher responsible for one subject in one academic year.

    A teacher may hold several assignments, and a subject may be assigned to
    several teachers. Each assignment produces a row in result_submissions
    for every examination, which is how submissions are tracked and chased.
    """

    __tablename__ = "teacher_subjects"
    __table_args__ = (
        UniqueConstraint(
            "teacher_id", "subject_id", "academic_year_id", name="uq_teacher_subject_year"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    teacher_id: Mapped[int] = mapped_column(
        ForeignKey("teachers.id", ondelete="CASCADE"), nullable=False
    )
    subject_id: Mapped[int] = mapped_column(
        ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    academic_year_id: Mapped[int] = mapped_column(
        ForeignKey("academic_years.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    # Unassigning sets this False rather than deleting the row. A deletion
    # would cascade into result_submissions and destroy the record of what
    # this teacher submitted for past examinations.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    teacher: Mapped["Teacher"] = relationship(back_populates="subject_assignments")  # noqa: F821
    subject: Mapped["Subject"] = relationship(back_populates="teacher_assignments")  # noqa: F821
    academic_year: Mapped["AcademicYear"] = relationship(  # noqa: F821
        back_populates="teacher_assignments"
    )
    submissions: Mapped[List["ResultSubmission"]] = relationship(  # noqa: F821
        back_populates="assignment", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<TeacherSubject teacher={self.teacher_id} subject={self.subject_id}>"
