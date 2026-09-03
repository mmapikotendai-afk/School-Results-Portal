"""Student profiles. The student number is the key every upload matches on."""

from datetime import date
from typing import List, Optional

from sqlalchemy import Date, Enum, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import Gender
from app.models.mixins import TimestampMixin


class Student(Base, TimestampMixin):
    """A learner enrolled at the school."""

    __tablename__ = "students"
    __table_args__ = (
        # Class lists and roll-call ordering.
        Index("ix_students_class_last_name", "class_id", "last_name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    # Unique and immutable. Printed on report cards and used to match every
    # row of every CSV upload back to the correct learner.
    student_number: Mapped[str] = mapped_column(
        String(32), unique=True, index=True, nullable=False
    )

    first_name: Mapped[str] = mapped_column(String(80), nullable=False)
    last_name: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    date_of_birth: Mapped[Optional[date]] = mapped_column(Date)
    gender: Mapped[Optional[Gender]] = mapped_column(Enum(Gender))

    # A student may be between classes (newly admitted, or graduated), so the
    # class is nullable and never cascades a delete.
    class_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("classes.id", ondelete="SET NULL")
    )

    user: Mapped["User"] = relationship(back_populates="student")  # noqa: F821
    school_class: Mapped[Optional["SchoolClass"]] = relationship(  # noqa: F821
        back_populates="students"
    )
    subject_enrollments: Mapped[List["StudentSubject"]] = relationship(  # noqa: F821
        back_populates="student", cascade="all, delete-orphan"
    )
    results: Mapped[List["Result"]] = relationship(  # noqa: F821
        back_populates="student", cascade="all, delete-orphan"
    )

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def level(self):
        """The education level this student sits at, taken from their class."""
        return self.school_class.level if self.school_class else None

    def __repr__(self) -> str:
        return f"<Student {self.student_number} {self.full_name}>"
