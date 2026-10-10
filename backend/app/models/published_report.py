"""The academic context of a report when its examination was published."""

from sqlalchemy import Boolean, ForeignKey, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.mixins import CreatedAtMixin


class PublishedReport(Base, CreatedAtMixin):
    __tablename__ = "published_reports"

    examination_id: Mapped[int] = mapped_column(
        ForeignKey("examinations.id", ondelete="CASCADE"), primary_key=True
    )
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), primary_key=True
    )
    # Deliberately not a foreign key: removing/renaming a class must not alter
    # its historical cohort. The name and level are also retained in context.
    class_id: Mapped[int | None] = mapped_column(Integer, index=True)
    rank_eligible: Mapped[bool] = mapped_column(Boolean, nullable=False)
    context: Mapped[dict] = mapped_column(JSON, nullable=False)
