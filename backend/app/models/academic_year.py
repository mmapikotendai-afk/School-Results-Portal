"""Academic years and the terms inside them."""

from datetime import date
from typing import List, Optional

from sqlalchemy import Boolean, Date, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AcademicYear(Base):
    """A school year, for example "2026".

    Subject enrollment and teacher assignment are both scoped to a year, so a
    student can change subjects between years without losing past records.
    """

    __tablename__ = "academic_years"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(40), unique=True, index=True, nullable=False)
    start_date: Mapped[Optional[date]] = mapped_column(Date)
    end_date: Mapped[Optional[date]] = mapped_column(Date)

    # Exactly one year should be active; enforced in the service layer.
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    terms: Mapped[List["Term"]] = relationship(
        back_populates="academic_year", cascade="all, delete-orphan"
    )
    student_enrollments: Mapped[List["StudentSubject"]] = relationship(  # noqa: F821
        back_populates="academic_year"
    )
    teacher_assignments: Mapped[List["TeacherSubject"]] = relationship(  # noqa: F821
        back_populates="academic_year"
    )

    def __repr__(self) -> str:
        return f"<AcademicYear {self.name}>"


class Term(Base):
    """A term within an academic year, for example "Term 1"."""

    __tablename__ = "terms"
    __table_args__ = (
        UniqueConstraint("academic_year_id", "name", name="uq_terms_year_name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    academic_year_id: Mapped[int] = mapped_column(
        ForeignKey("academic_years.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(40), nullable=False)
    start_date: Mapped[Optional[date]] = mapped_column(Date)
    end_date: Mapped[Optional[date]] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    academic_year: Mapped["AcademicYear"] = relationship(back_populates="terms")
    examinations: Mapped[List["Examination"]] = relationship(  # noqa: F821
        back_populates="term", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Term {self.name}>"
