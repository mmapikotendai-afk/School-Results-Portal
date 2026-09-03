"""Examinable subjects."""

from typing import List

from sqlalchemy import Boolean, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import SubjectLevel
from app.models.mixins import CreatedAtMixin


class Subject(Base, CreatedAtMixin):
    """A subject offered by the school.

    The level lets one catalogue serve both halves of the school: an O-Level
    only subject, an A-Level only subject, or one offered at both.
    """

    __tablename__ = "subjects"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)

    level: Mapped[SubjectLevel] = mapped_column(
        Enum(SubjectLevel), default=SubjectLevel.BOTH, nullable=False, index=True
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    student_enrollments: Mapped[List["StudentSubject"]] = relationship(  # noqa: F821
        back_populates="subject"
    )
    teacher_assignments: Mapped[List["TeacherSubject"]] = relationship(  # noqa: F821
        back_populates="subject"
    )
    results: Mapped[List["Result"]] = relationship(back_populates="subject")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Subject {self.code} {self.name}>"
