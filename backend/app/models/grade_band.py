"""The school's grading scale, held as data rather than code.

A band says: at or above this percentage, the grade is this, and the remark
reads like this. Schools do not share one scale and do change theirs, so the
scale lives in the database where an administrator can edit it, not in a
constant a developer has to redeploy.
"""

from decimal import Decimal

from sqlalchemy import Boolean, Enum, Index, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.enums import EducationLevel
from app.models.mixins import TimestampMixin


class GradeBand(Base, TimestampMixin):
    """One band of the grading scale, for one education level."""

    __tablename__ = "grade_bands"
    __table_args__ = (
        # One meaning per symbol within a level: two bands both called "A"
        # would make the scale ambiguous.
        UniqueConstraint("level", "grade", name="uq_grade_band_level_grade"),
        # The lookup is always "highest band at or below this mark".
        Index("ix_grade_bands_level_min", "level", "min_marks"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    level: Mapped[EducationLevel] = mapped_column(Enum(EducationLevel), nullable=False)

    # Inclusive lower bound, as a percentage. The band runs from here up to the
    # next band above it, so the scale needs no upper bound per row and cannot
    # develop gaps when one is edited.
    min_marks: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)

    grade: Mapped[str] = mapped_column(String(4), nullable=False)
    remark: Mapped[str] = mapped_column(String(80), nullable=False)

    # Whether this band counts as a pass, for pass rates and report cards.
    is_pass: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<GradeBand {self.level.value} {self.grade} >= {self.min_marks}>"
