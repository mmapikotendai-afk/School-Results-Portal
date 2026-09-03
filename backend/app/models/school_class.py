"""Classes (forms and streams), for example 1C, Form 4A or Lower 6 Sciences."""

from typing import List

from sqlalchemy import Boolean, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import EducationLevel
from app.models.mixins import CreatedAtMixin


class SchoolClass(Base, CreatedAtMixin):
    """A teaching class a student belongs to.

    Named SchoolClass in Python to avoid shadowing the builtin sense of
    "class"; the table itself is "classes". Every class is created by an
    administrator at runtime - no class names are hard-coded anywhere.
    """

    __tablename__ = "classes"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Free text, so any naming convention works: "1C", "Form 4A",
    # "Lower 6 Commercials", "Upper 6 Sciences".
    name: Mapped[str] = mapped_column(String(60), unique=True, index=True, nullable=False)

    # Drives grading bands and report card layout.
    level: Mapped[EducationLevel] = mapped_column(
        Enum(EducationLevel), nullable=False, index=True
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    students: Mapped[List["Student"]] = relationship(back_populates="school_class")  # noqa: F821

    def __repr__(self) -> str:
        return f"<SchoolClass {self.name} ({self.level.value})>"
