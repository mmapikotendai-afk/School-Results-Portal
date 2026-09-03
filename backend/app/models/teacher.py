"""Teacher profiles."""

from typing import List, Optional

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import TimestampMixin


class Teacher(Base, TimestampMixin):
    """A member of the teaching staff."""

    __tablename__ = "teachers"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    employee_number: Mapped[str] = mapped_column(
        String(32), unique=True, index=True, nullable=False
    )

    first_name: Mapped[str] = mapped_column(String(80), nullable=False)
    last_name: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    department: Mapped[Optional[str]] = mapped_column(String(80))
    phone: Mapped[Optional[str]] = mapped_column(String(32))

    user: Mapped["User"] = relationship(back_populates="teacher")  # noqa: F821
    subject_assignments: Mapped[List["TeacherSubject"]] = relationship(  # noqa: F821
        back_populates="teacher", cascade="all, delete-orphan"
    )
    submissions: Mapped[List["ResultSubmission"]] = relationship(  # noqa: F821
        back_populates="teacher", cascade="all, delete-orphan"
    )

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def __repr__(self) -> str:
        return f"<Teacher {self.employee_number} {self.full_name}>"
